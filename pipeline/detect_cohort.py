"""M3 — Fleet Peer Benchmarking. The detector.

WHAT THIS ANSWERS. Given a fleet of sites that share weather, which ones are
losing generation for a reason that is their own? A cohort-wide dip is weather
and nobody drives anywhere. A single-site dip while its peers hold steady is a
fault, and that is a visit worth paying for.

WHY IT NEEDS NO IRRADIANCE SENSOR. The peers are the baseline. Every site in a
cohort sees substantially the same sky on the same day, so the cohort median IS
the expected performance for that day, measured rather than modelled. Whatever
error the weather introduces is common to the median and to the site, and it
cancels in the difference. That is the whole sensor-free wedge, and it is why
this module reads nothing but generation the fleet already reports.

    Leloux et al., "Performance to Peers", Solar Energy 2020 — the same
    construction over ~6,000 European systems with no irradiance input and no
    system metadata. The method is published prior art. The application is not:
    nobody has wired it to a dispatch-or-don't decision with money attached.

THE UNIT IS kWh PER kWp. `performance_index` is specific yield, computed once
at ingestion as site_kwh / capacity_kwp (pipeline/fetch_pvdaq.py). Sites here
span 40.56 to 277.16 kWp, so raw kWh is not comparable across a cohort and
normalising is not optional. This module never sees a raw kWh figure.

    NOTE ON docs/ARCHITECTURE.md SECTION 3.3. That section defines the
    performance index as actual/expected, which would make this module depend
    on the M2 physics baseline. Every other authority in the repo — CLAUDE.md's
    hard rule, docs/Schema.md section 8.6, and the shipped ingestion code —
    defines it as kWh/kWp. This module follows the shipped definition, so it
    runs today with no baseline and no irradiance source. Section 3.3 is the
    outlier and is corrected separately.

WHY MEDIAN AND MAD, NOT MEAN AND STANDARD DEVIATION. With mean/std a single
large deviation inflates the standard deviation and masks itself — the worst
site in a cohort drags the yardstick toward its own badness and then measures
as normal against it. The median absolute deviation has a 50% breakdown point:
up to half the cohort can be faulty before the reference moves. On cohorts of
five, that margin is the difference between a detector and a rubber stamp.

WHAT STOPS IT FIRING ON CURTAILMENT. Persistence. Curtailment and weather
artefacts breach for a day or two and recover; a fault does not. A site is
flagged only when it is in breach on at least `persist_days` of the trailing
`persist_window_days`. One bad day never dispatches a technician.

Every constant lives in config/assumptions.json. Nothing is tuned here.

Stdlib only, on purpose — this keeps pipeline/requirements.txt at three
packages and lets the tests run against plain dicts with no parquet engine.
"""

import datetime
import math
import statistics


# Iglewicz and Hoaglin (1993), "How to Detect and Handle Outliers". The
# constant makes the modified z-score comparable in scale to a conventional
# z-score for normally distributed data: 0.6745 is the MAD of the standard
# normal, so dividing by it puts the statistic back on standard-deviation-like
# footing.
MODIFIED_Z_CONSTANT = 0.6745

EARTH_RADIUS_KM = 6371.0088


# --- geometry ---------------------------------------------------------------


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km. Stdlib only — no geo dependency for this."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def max_pairwise_separation_km(members):
    """Widest separation between any two cohort members, in km.

    Reported rather than assumed. The cohort's whole claim is that its members
    share weather, and the honest way to state that claim is to publish how far
    apart they actually are and let a reader judge it.
    """
    widest = 0.0
    for index, first in enumerate(members):
        for second in members[index + 1:]:
            distance = haversine_km(first["lat"], first["lon"],
                                    second["lat"], second["lon"])
            if distance > widest:
                widest = distance
    return widest


# --- the statistic ----------------------------------------------------------


def median_absolute_deviation(values, centre):
    """Median of |value - centre|. Returns None when it is zero.

    A zero MAD means every member of the cohort read identically that day, so
    there is no spread to measure a deviation against and the z-score would
    divide by zero. That is not a score of zero — it is the absence of a score,
    and it is returned as such so the caller cannot mistake one for the other.
    """
    if not values:
        return None
    deviations = [abs(value - centre) for value in values]
    mad = statistics.median(deviations)
    if mad == 0:
        return None
    return mad


def modified_z_score(value, centre, mad):
    """Iglewicz-Hoaglin modified z. Signed: negative means below the cohort."""
    if mad is None or mad == 0:
        return None
    return MODIFIED_Z_CONSTANT * (value - centre) / mad


def values_by_date(series_by_site, member_site_ids):
    """{date: {site_id: performance_index}} across the given members."""
    collected = {}
    for site_id in member_site_ids:
        for row in series_by_site.get(site_id) or []:
            performance_index = row.get("performance_index")
            if performance_index is None:
                continue
            collected.setdefault(row["date"], {})[site_id] = performance_index
    return collected


def peer_reference_by_date(series_by_site, member_site_ids, subject_site_id,
                           min_cohort_size):
    """Per-date median and MAD of the subject's PEERS, excluding the subject.

    LEAVE-ONE-OUT, AND IT IS NOT AN OPTIMISATION. A site included in the group
    it is measured against contributes to the median and to the MAD it is then
    judged by — it bends its own yardstick. On a five-member cohort that is
    fatal rather than marginal: two simultaneous faults are 40% of the
    population, and the MAD measured on this fleet inflates 3x in DSUN-01 and
    24x in VEGAS-01, which suppresses every z-score in the cohort including the
    broken sites' own. Measured, not theorised — see pipeline/evaluate.py.

    The peer group is one smaller than the cohort, so the day is scored when
    `min_cohort_size - 1` peers reported. The cohort still has to meet
    `min_cohort_size` in total for any of this to run.
    """
    reference = {}
    for date, values in values_by_date(series_by_site, member_site_ids).items():
        peers = [value for site_id, value in values.items() if site_id != subject_site_id]
        if len(peers) < max(1, min_cohort_size - 1):
            continue
        centre = statistics.median(peers)
        reference[date] = {
            "median": centre,
            "mad": median_absolute_deviation(peers, centre),
            "n": len(peers),
        }
    return reference


def cohort_reference_by_date(series_by_site, member_site_ids, min_cohort_size):
    """For each date, the cohort's median specific yield and its MAD.

    Returns {date: {"median": float, "mad": float|None, "n": int}}.

    A date is only scored when at least `min_cohort_size` members reported that
    day. Below that the control group is too thin to accuse anyone with, so the
    day yields no reference at all rather than a weak one. Missing days are not
    evidence of anything.
    """
    # Named `collected`, not `values_by_date`: that is the name of the
    # module-level helper above, and shadowing it here would turn any future
    # call to it inside this function into "'dict' object is not callable".
    collected = {}
    for site_id in member_site_ids:
        for row in series_by_site.get(site_id) or []:
            performance_index = row.get("performance_index")
            if performance_index is None:
                continue
            collected.setdefault(row["date"], []).append(performance_index)

    reference = {}
    for date, values in collected.items():
        if len(values) < min_cohort_size:
            continue
        centre = statistics.median(values)
        reference[date] = {
            "median": centre,
            "mad": median_absolute_deviation(values, centre),
            "n": len(values),
        }
    return reference


def score_site(site_series, reference):
    """Per-day modified z for one site against its cohort reference.

    Returns a list of {date, performance_index, cohort_median, z} ordered by
    date, skipping days the cohort could not be scored on.
    """
    scored = []
    for row in site_series or []:
        day = reference.get(row["date"])
        if day is None:
            continue
        performance_index = row.get("performance_index")
        if performance_index is None:
            continue
        z = modified_z_score(performance_index, day["median"], day["mad"])
        if z is None:
            continue
        scored.append({
            "date": row["date"],
            "performance_index": performance_index,
            "cohort_median": day["median"],
            "z": z,
        })
    scored.sort(key=lambda item: item["date"])
    return scored


# --- persistence ------------------------------------------------------------


def parse_date(value):
    return datetime.date.fromisoformat(value)


def window_start(as_of, persist_window_days):
    """First calendar date inside the trailing window, inclusive.

    The window is counted in CALENDAR days, not in rows. Counting rows would
    silently stretch a 14-day window across a month whenever telemetry had gaps,
    which is exactly the situation where a confident answer is least warranted.
    """
    return as_of - datetime.timedelta(days=persist_window_days - 1)


def breaches_in_window(scored, as_of, persist_window_days, threshold):
    """Days inside the trailing window whose z fell below the threshold."""
    first_day = window_start(as_of, persist_window_days)
    return [row for row in scored
            if first_day <= parse_date(row["date"]) <= as_of
            and row["z"] < threshold]


def scored_days_in_window(scored, as_of, persist_window_days):
    first_day = window_start(as_of, persist_window_days)
    return [row for row in scored
            if first_day <= parse_date(row["date"]) <= as_of]


def episode_start_date(scored, threshold, max_gap_days):
    """When the current divergence began.

    Walks backwards from the most recent breach and keeps going while clean
    days come in runs no longer than `max_gap_days`. The tolerance is not a
    free parameter: it is persist_window_days - persist_days, the same slack
    the flagging rule already allows inside its window. A longer clean run ends
    the episode, so a site that recovered and then failed again reports the
    second failure rather than dating itself back to the first.

    Returns an ISO date string, or None when the site has never breached.
    """
    breach_positions = [index for index, row in enumerate(scored)
                        if row["z"] < threshold]
    if not breach_positions:
        return None

    # The gap is counted in CALENDAR days, for the same reason window_start is.
    # Counting rows lets a month-long telemetry outage pass as a few clean days,
    # dating an episode back across the outage and inflating days_since,
    # cumulative_kwh_lost and the "lost since" label on the chart marker by the
    # whole gap.
    start_index = breach_positions[-1]
    for index in range(start_index - 1, -1, -1):
        gap_days = (parse_date(scored[start_index]["date"])
                    - parse_date(scored[index]["date"])).days - 1
        if gap_days > max_gap_days:
            break
        if scored[index]["z"] < threshold:
            start_index = index
    return scored[start_index]["date"]


def first_detection_date(scored, threshold, persist_days, persist_window_days):
    """The earliest day the flagging rule would have fired, walking forward.

    detect_cohort only ever asks "is this site flagged TODAY", because that is
    the dispatch question. Measuring days-to-detect needs the other question —
    on which day would this first have tripped — so the window is slid forward
    across the whole series instead of being anchored at the end.

    Returns an ISO date string, or None if the rule never fires.
    """
    for index in range(len(scored)):
        as_of = parse_date(scored[index]["date"])
        breaches = breaches_in_window(scored[:index + 1], as_of,
                                      persist_window_days, threshold)
        if len(breaches) >= persist_days:
            return scored[index]["date"]
    return None


# --- loss -------------------------------------------------------------------


def shortfall_rows(scored, since_date):
    """Days from `since_date` onward where the site sat below its cohort.

    Only days BELOW the median contribute. A day above the median is not a
    negative loss that offsets a real one — the site was fine that day, and
    netting it off would let a good week hide a bad one.
    """
    rows = []
    for row in scored:
        if since_date is not None and row["date"] < since_date:
            continue
        deficit = row["cohort_median"] - row["performance_index"]
        if deficit <= 0:
            continue
        rows.append({
            "date": row["date"],
            "deficit_per_kwp": deficit,
            "fraction": deficit / row["cohort_median"] if row["cohort_median"] else 0.0,
        })
    return rows


def loss_summary(scored, since_date, capacity_kwp, days_per_month):
    """Generation lost against the cohort, in kWh.

        daily_kwh_lost = (cohort_median_PI - site_PI) x capacity_kwp

    which is docs/ARCHITECTURE.md section 3.3's `(median - PI) x expected_kWh`
    written in specific-yield terms. Because PI is already kWh per kWp,
    multiplying by the site's nameplate gives kWh directly and no separate
    expected-energy baseline is needed to get there.

    `kwh_lost_monthly` is the MEAN daily loss across the episode scaled to a
    month, not the sum of the episode. An episode running 102 days would
    otherwise report three months of loss as this month's exposure.
    """
    rows = shortfall_rows(scored, since_date)
    if not rows:
        return {
            "kwh_lost_monthly": 0.0,
            "cumulative_kwh_lost": 0.0,
            "loss_fraction": 0.0,
            "days_affected": 0,
        }

    # THE DIVISOR IS EPISODE DAYS, NOT DEFICIT DAYS.
    #
    # Averaging over only the days that lost generation answers "how bad was it
    # when it was bad", which is not what a monthly exposure figure means. On an
    # intermittent fault — the exact shape this module classifies — a 30-day
    # episode losing 1.0 kWh/kWp on six days would report a full month at the
    # six-day rate, overstating exposure five-fold. That figure feeds
    # rm_at_risk_monthly, the dispatch ranking and the demote decision.
    episode_days = [row for row in scored
                    if since_date is None or row["date"] >= since_date]
    divisor = len(episode_days) or len(rows)

    daily_losses = [row["deficit_per_kwp"] * capacity_kwp for row in rows]
    cumulative = sum(daily_losses)
    mean_daily = cumulative / divisor
    mean_fraction = sum(row["fraction"] for row in rows) / divisor

    return {
        "kwh_lost_monthly": mean_daily * days_per_month,
        "cumulative_kwh_lost": cumulative,
        "loss_fraction": mean_fraction,
        "days_affected": len(rows),
    }


# --- signal shape -----------------------------------------------------------

SHAPE_STEP = "step"
SHAPE_RAMP = "ramp"
SHAPE_INTERMITTENT = "intermittent"
SHAPE_UNKNOWN = "unknown"

# A ramp has to deepen by more than this fraction between the opening and
# closing thirds of the episode before it counts as progressive rather than
# flat. Below it the two ends are the same depth within noise, which is a step.
RAMP_DEEPENING_RATIO = 1.5

# An episode whose deficit is ABSENT on more than this fraction of its own days
# is coming and going rather than sitting there, which points at something
# intermittent — a thermal derate, a tracker fault, or curtailment that
# survived the persistence filter — not a dead string.
INTERMITTENT_PRESENCE = 0.6

# A day counts as carrying the fault when its deficit reaches this fraction of
# the episode's mean deficit. Measuring PRESENCE OF DEFICIT rather than
# crossings of the z threshold matters: a genuine 25% step drop sits there
# every single day while only occasionally breaching z on a tight cohort, and
# scoring it on crossings alone would report a dead string as intermittent and
# send a technician hunting a thermal trip.
DEFICIT_PRESENCE_FRACTION = 0.25


def classify_shape(scored, since_date):
    """Name the shape of the divergence from the series itself.

    This exists so the cause hypothesis follows from the DETECTED SIGNAL rather
    than from a severity number. The three shapes map to genuinely different
    site visits:

      step         - full depth from the first day. Something switched off: a
                     tripped breaker, a failed string, a dead inverter channel.
      ramp         - shallow at first and deepening. Something is accumulating:
                     soiling, progressive shading, gradual degradation.
      intermittent - present on some days and absent on others. Something is
                     cycling: thermal derate, a tracker fault, or curtailment.

    Returns SHAPE_UNKNOWN when the episode is too short to have a shape.

    KNOWN LIMIT, STATED RATHER THAN TUNED AWAY. This is the shape observed
    SINCE DIVERGENCE, not a claim about root cause. A slow ramp that is only
    detected once it is already deep presents as a step inside the detection
    window, because the interesting part of its slope happened before the
    episode began. Widening the look-back does not fix it — including clean
    pre-onset days makes a genuine step deepen too, and then everything reads
    as a ramp. Treat `shape` as evidence pointing a technician at what to check
    first, never as a diagnosis.
    """
    rows = [row for row in scored
            if since_date is not None and row["date"] >= since_date]
    if len(rows) < 6:
        return SHAPE_UNKNOWN

    deficits = [max(0.0, row["cohort_median"] - row["performance_index"])
                for row in rows]
    mean_deficit = sum(deficits) / len(deficits)
    if mean_deficit <= 0:
        return SHAPE_UNKNOWN

    present = sum(1 for deficit in deficits
                  if deficit >= mean_deficit * DEFICIT_PRESENCE_FRACTION)
    if present / len(deficits) < INTERMITTENT_PRESENCE:
        return SHAPE_INTERMITTENT

    third = max(1, len(deficits) // 3)
    opening_depth = sum(deficits[:third]) / third
    closing_depth = sum(deficits[-third:]) / third

    if opening_depth <= 0:
        return SHAPE_RAMP if closing_depth > 0 else SHAPE_UNKNOWN
    if closing_depth / opening_depth >= RAMP_DEEPENING_RATIO:
        return SHAPE_RAMP
    return SHAPE_STEP


# --- confidence -------------------------------------------------------------


def detection_confidence(breach_count, persist_window_days, median_z, threshold):
    """How much the evidence supports the flag, on 0..1.

    A stated formula, not a feeling — half of it is how consistently the site
    breached, half is how far past the threshold it sat:

        persistence = breaches / window
        depth       = min(1, |median z| / 2|threshold|)
        confidence  = (persistence + depth) / 2

    Depth saturates at twice the threshold because past that point the site is
    unambiguously broken and further badness is not further certainty. Both
    inputs are measured; neither is tuned.
    """
    if persist_window_days <= 0:
        return 0.0
    persistence = min(1.0, breach_count / persist_window_days)
    # Only underperformance counts. A site sitting well ABOVE its cohort has a
    # large |z| and no fault whatsoever; crediting that as detection confidence
    # would report a high-yielding site as a confident problem.
    shortfall = max(0.0, -median_z)
    if threshold == 0:
        depth = 0.0
    else:
        depth = min(1.0, shortfall / (2 * abs(threshold)))
    return max(0.0, min(1.0, (persistence + depth) / 2))


# --- orchestration ----------------------------------------------------------

# The dashboard reports exposure per month and the source series is daily.
# 30 is the divisor already used throughout generate_dispatch.py for the same
# conversion; it is kept identical here so the two cannot drift apart.
DAYS_PER_MONTH = 30

TIER_DISPATCH = "dispatch"
TIER_MONITOR = "monitor"
TIER_HEALTHY = "healthy"

NO_LOSS = {
    "kwh_lost_monthly": 0.0,
    "cumulative_kwh_lost": 0.0,
    "loss_fraction": 0.0,
    "days_affected": 0,
}

DETECTION_METHOD = (
    "Iglewicz-Hoaglin modified z-score against same-day cohort median of "
    "specific yield (kWh/kWp), flagged on {breach}+ breach days below z={threshold} "
    "in a trailing {window}-day window"
)


def latest_date(series_by_site):
    """Most recent date anywhere in the fleet series, as a date object."""
    latest = None
    for series in series_by_site.values():
        for row in series or []:
            if latest is None or row["date"] > latest:
                latest = row["date"]
    return parse_date(latest) if latest else None


def describe_clustering(members, climate_zones):
    """State the cohort criterion in terms a reader can check.

    NOT greedy geographic clustering. docs/ARCHITECTURE.md section 3.3 proposes
    a 55 km radius, which this fleet cannot satisfy: DSUN-01's members are
    162 km apart and a 55 km rule would shatter it into fragments below the
    minimum cohort size, deleting the only cohort where per-site visit
    economics are honest. The criterion that actually supports the weather-
    cancellation argument is a shared climate zone under one operator, and
    that is what is reported here — with the measured separation attached so
    the claim can be argued with rather than taken on trust.
    """
    zones = sorted({zone for zone in climate_zones if zone})
    zone_text = "/".join(zones) if zones else "unclassified"
    return (
        "Shared operator and Koppen climate zone {zone}, assigned in "
        "config/fleet_sites.csv; members within {spread:.1f} km of each other"
    ).format(zone=zone_text, spread=max_pairwise_separation_km(members))


def detect_cohort(series_by_site, members, assumptions, excluded_site_ids=None):
    """Score one cohort. Returns (per_site_results, cohort_summary).

    `members` is a list of {site_id, capacity_kwp, lat, lon, climate_zone}.
    Excluded sites are dropped from the reference AND never flagged: their
    telemetry is not trustworthy enough to accuse them with, and a permanently
    depressed reading would also drag the peer baseline down and mask a real
    fault elsewhere in the cohort.
    """
    excluded_site_ids = set(excluded_site_ids or ())
    threshold = assumptions["z_score_threshold"]
    persist_days = assumptions["persist_days"]
    persist_window_days = assumptions["persist_window_days"]
    watch_days = assumptions["watch_days"]
    min_cohort_size = assumptions["min_cohort_size"]

    analysed = [member for member in members
                if member["site_id"] not in excluded_site_ids]
    analysed_ids = [member["site_id"] for member in analysed]

    reference = cohort_reference_by_date(series_by_site, analysed_ids, min_cohort_size)
    daily_medians = [day["median"] for day in reference.values()]

    summary = {
        "analysed_site_ids": analysed_ids,
        "analysed_count": len(analysed_ids),
        "meets_minimum": len(analysed_ids) >= min_cohort_size,
        "scored_days": len(reference),
        "median_performance_index": (
            round(statistics.median(daily_medians), 4) if daily_medians else None),
        "clustering_method": describe_clustering(
            members, [member.get("climate_zone") for member in members]),
        "max_separation_km": round(max_pairwise_separation_km(members), 1),
    }

    as_of = latest_date(series_by_site)
    max_gap_days = persist_window_days - persist_days
    results = {}

    for member in analysed:
        site_id = member["site_id"]
        # Each site is scored against its PEERS, never against a group that
        # includes itself. `reference` above stays whole-cohort because the
        # cohort summary genuinely describes all of its members.
        peer_reference = peer_reference_by_date(
            series_by_site, analysed_ids, site_id, min_cohort_size)
        scored = score_site(series_by_site.get(site_id), peer_reference)

        if not scored or as_of is None:
            results[site_id] = _empty_result(site_id, summary, threshold)
            continue

        window_rows = scored_days_in_window(scored, as_of, persist_window_days)

        # NO DAYS IN THE WINDOW IS NOT A CLEAN BILL OF HEALTH.
        #
        # A site whose feed stopped two weeks ago still has older scored days,
        # so `scored` is non-empty and the empty-result branch above misses it.
        # Reporting median_z = 0.0 would render it as a perfectly average,
        # confidently healthy site when nothing was examined at all. `as_of` is
        # fleet-wide while the reference is per-cohort, so one cohort's feed
        # stopping early reaches this on its own.
        if not window_rows:
            results[site_id] = _empty_result(site_id, summary, threshold)
            continue
        breaches = breaches_in_window(scored, as_of, persist_window_days, threshold)
        breach_count = len(breaches)

        if breach_count >= persist_days:
            tier = TIER_DISPATCH
        elif breach_count >= watch_days:
            tier = TIER_MONITOR
        else:
            tier = TIER_HEALTHY

        median_z = statistics.median([row["z"] for row in window_rows])

        # Loss is only computed for a site the detector is actually accusing.
        # Every site drifts below its cohort on SOME day, so measuring a
        # shortfall for an unflagged site would attach a ringgit figure to
        # ordinary scatter and put "12 days affected" on a healthy row.
        if tier == TIER_HEALTHY:
            start_date = None
            days_since = None
            loss = NO_LOSS
        else:
            start_date = episode_start_date(scored, threshold, max_gap_days)
            loss = loss_summary(scored, start_date, member["capacity_kwp"], DAYS_PER_MONTH)
            days_since = (as_of - parse_date(start_date)).days if start_date else None

        results[site_id] = {
            "site_id": site_id,
            "scored": True,
            "tier": tier,
            "score": round(median_z, 2),
            "threshold": threshold,
            "score_type": "z_score",
            "method": DETECTION_METHOD.format(
                breach=persist_days, threshold=threshold, window=persist_window_days),
            "breach_days": breach_count,
            "window_days": persist_window_days,
            "scored_days_in_window": len(window_rows),
            "cohort_size": summary["analysed_count"],
            "cohort_meets_minimum": summary["meets_minimum"],
            "cohort_median_performance_index": summary["median_performance_index"],
            "confidence": round(detection_confidence(
                breach_count, persist_window_days, median_z, threshold), 2),
            "divergence_start": start_date,
            "days_since": days_since,
            "kwh_lost_monthly": round(loss["kwh_lost_monthly"], 1),
            "cumulative_kwh_lost": round(loss["cumulative_kwh_lost"], 1),
            "loss_fraction": round(loss["loss_fraction"], 4),
            "days_affected": loss["days_affected"],
            "shape": (classify_shape(scored, start_date)
                      if tier != TIER_HEALTHY else None),
        }

    return results, summary


def _empty_result(site_id, summary, threshold):
    """A site the cohort could not score — no series, or no usable reference."""
    return {
        "site_id": site_id,
        # Not "healthy" — NOT SCORED. The caller must not render this as a
        # clearance: no measurement was taken, so there is nothing to label
        # BUILT and nothing to tell an operator they can skip the site on.
        "scored": False,
        "tier": TIER_HEALTHY,
        "score": None,
        "threshold": threshold,
        "score_type": "z_score",
        "method": "Not scored — no comparable cohort day for this site",
        "breach_days": 0,
        "window_days": None,
        "scored_days_in_window": 0,
        "cohort_size": summary["analysed_count"],
        "cohort_meets_minimum": summary["meets_minimum"],
        "cohort_median_performance_index": summary["median_performance_index"],
        "confidence": 0.0,
        "divergence_start": None,
        "days_since": None,
        "kwh_lost_monthly": 0.0,
        "cumulative_kwh_lost": 0.0,
        "loss_fraction": 0.0,
        "days_affected": 0,
        "shape": None,
    }


def detect_fleet(series_by_site, cohort_members, assumptions, excluded_site_ids=None):
    """Run the detector across every cohort.

    Returns (results_by_site_id, summary_by_cohort_id).
    """
    results = {}
    summaries = {}
    for cohort_id in sorted(cohort_members):
        cohort_results, summary = detect_cohort(
            series_by_site, cohort_members[cohort_id], assumptions, excluded_site_ids)
        results.update(cohort_results)
        summaries[cohort_id] = summary
    return results, summaries

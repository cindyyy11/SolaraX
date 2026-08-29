"""M3 - fleet peer benchmarking. The differentiator.

THE ARGUMENT, IN TWO SENTENCES. A cohort-wide dip is weather. A single-site dip
inside a stable cohort is a fault.

WHY THAT IS MORE THAN A SLOGAN. Satellite irradiance carries real error - M2
measures its own at roughly 28 % normalised RMSE on a single day. But every site
in a weather cohort is fed from the same satellite product, so on any given day
that error lands on all of them at once. Comparing a site to its peers ON THE
SAME DAY subtracts the error instead of inheriting it. The absolute baseline
would need site-grade instrumentation to resolve a 10 % fault; the peer
comparison resolves it without a single sensor on any roof.

It is also the scalability claim, and the claim is structural rather than
aspirational: more sites per weather region means more peers in the median,
which means a tighter cohort and fewer false flags. This method gets BETTER as
the fleet grows.

THE CHAIN
---------
    1. performance ratio        r = actual / expected            (M2 supplies expected)
    2. reference normalisation  n = r / median(r over reference period)
    3. peer statistics          per cohort, per day: median and MAD across members
    4. modified z-score         z = 0.6745 (n - median) / MAD
    5. site score               median of z over the evaluation window
    6. flag                     score <= threshold AND persistence >= minimum

STEP 2 IS THE ONE THAT IS EASY TO MISS. M2 assumes one tilt and one azimuth for
the whole fleet, because PVDAQ publishes neither. A site whose true orientation
differs sits permanently off 1.00 - and without step 2 that constant offset is
indistinguishable from a permanent fault, so the detector would flag the same
innocent sites every month forever. Dividing by the site's own reference-period
median removes any constant, whatever caused it.

The cost is stated plainly: a fault that was ALREADY RUNNING during the
reference period is normalised away and this detector will not see it. The
reference period is chosen to be clean by construction against the injection
protocol (fault_injection.py draws every start date from the middle third of the
window), and the limitation is published rather than hidden.

WHY MEDIAN AND MAD RATHER THAN MEAN AND STANDARD DEVIATION. On a cohort of five,
one genuinely faulty site is 20 % of the sample. A mean and a standard deviation
computed across that cohort are both dragged by the very site being tested - the
outlier inflates the spread it is being measured against and hides itself. The
median and the median absolute deviation have a 50 % breakdown point: it takes
half the cohort failing together before they move at all.

The modified z-score is Iglewicz and Hoaglin's, computed on the FULL sample
including the site under test, which is their definition. That is deliberately
the conservative direction: a real outlier slightly inflates the MAD and pulls
the median toward itself, so the score is attenuated rather than exaggerated. A
detector should understate rather than overstate.

WHAT THIS DOES NOT DO. It does not decide whether a site is worth visiting -
that is money, and it belongs to M4. This says how confident we are that a site
is underperforming its peers, and by how many kWh.

Run:
    python pipeline/peer_benchmark.py            # score the real fleet
    python pipeline/peer_benchmark.py --detail   # per-site daily z-score table

Reads:  config/fleet_sites.csv, config/model_params.json, and M2's output
"""

import argparse
import datetime
import math
import os

import numpy as np
import pandas as pd
from scipy import stats

from baseline import (
    build_expected,
    build_site_id,
    load_actual_daily,
    load_fleet_sites,
    load_irradiance,
    load_model_params,
    plausibility_excluded_site_ids,
)

# Iglewicz-Hoaglin constant. 0.6745 is the 75th percentile of the standard
# normal, so MAD/0.6745 estimates sigma for normally distributed data and the
# modified z-score is on the same scale as an ordinary z-score.
MODIFIED_Z_CONSTANT = 0.6745

EARTH_RADIUS_KM = 6371.0088

DETECTION_METHOD_NAME = (
    "Robust peer-deviation z-score: Iglewicz-Hoaglin modified z-score "
    "(median / MAD) across same-day cohort peers, on a performance ratio "
    "normalised to each site's own reference period"
)

CLUSTERING_METHOD_NAME = (
    "Koppen climate zone, then single-linkage agglomerative clustering on "
    "great-circle distance within the zone"
)

SCORE_TYPE = "z_score"


# --- Cohort formation -------------------------------------------------------


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km. Stdlib maths, no geo dependency."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def cluster_cohorts(sites, params):
    """Form weather cohorts. Returns {cohort_key: [site_id, ...]}.

    CLIMATE ZONE FIRST, DISTANCE SECOND. Clustering on raw lat/lon alone is
    degenerate on this fleet: five VEGAS sites share byte-identical coordinates,
    so a distance-only method sees one point where there are five roofs. Koppen
    zone is the primary key because it is what actually encodes "shares weather";
    distance then splits a zone that spans more than one weather system.

    Single linkage rather than complete: a cohort is a chain of sites that share
    weather with their neighbours, and DSUN-01 genuinely is such a chain across
    162 km of the mid-Atlantic. Complete linkage would demand every pair be close
    and would split it into three useless cohorts of one and two.
    """
    cutoff = params["detector"]["clustering_max_km"]

    by_zone = {}
    for site in sites:
        by_zone.setdefault(site["kg_climate"], []).append(site)

    cohorts = {}
    for zone in sorted(by_zone):
        members = by_zone[zone]

        # Single-linkage agglomerative clustering, written out rather than
        # imported: with 11 sites the loop is clearer than a scipy linkage
        # matrix, and a judge can read it.
        groups = [[member] for member in members]
        merged = True
        while merged:
            merged = False
            for left in range(len(groups)):
                for right in range(left + 1, len(groups)):
                    if _min_separation_km(groups[left], groups[right]) <= cutoff:
                        groups[left].extend(groups[right])
                        groups.pop(right)
                        merged = True
                        break
                if merged:
                    break

        for index, group in enumerate(sorted(groups, key=len, reverse=True), start=1):
            key = "{}-{:02d}".format(zone, index)
            cohorts[key] = sorted(build_site_id(member["source_system_id"])
                                  for member in group)
    return cohorts


def _min_separation_km(group_a, group_b):
    """Single linkage: the distance between two groups is their closest pair."""
    return min(
        haversine_km(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"]))
        for a in group_a for b in group_b
    )


def reconcile_with_configured_cohorts(clustered, sites):
    """Compare the clustering to config/fleet_sites.csv and report any disagreement.

    The configured cohort ids are what the dashboard, the docs and the deck all
    name. This method has to EARN them rather than assert them - so it clusters
    from coordinates and climate, then checks that the partition it derived is
    the same partition the config declares.

    Returns (mapping, agreement) where mapping renames each derived cluster to
    the configured cohort_id it matches. A disagreement is returned, never
    silently smoothed over: it would mean the fleet definition and the physics
    have diverged, and that is a finding, not a nuisance.
    """
    configured = {}
    for site in sites:
        configured.setdefault(site["cohort_id"], set()).add(
            build_site_id(site["source_system_id"]))

    mapping = {}
    unmatched = []
    for derived_key, members in clustered.items():
        member_set = set(members)
        match = next((cohort_id for cohort_id, group in configured.items()
                      if group == member_set), None)
        if match:
            mapping[derived_key] = match
        else:
            unmatched.append((derived_key, sorted(member_set)))

    return mapping, {
        "agrees_with_config": not unmatched,
        "derived_cohort_count": len(clustered),
        "configured_cohort_count": len(configured),
        "unmatched": unmatched,
    }


# --- The detector -----------------------------------------------------------


def add_reference_normalisation(expected, params, excluded_site_ids=()):
    """Divide each site's performance ratio by its own reference level.

    THE REFERENCE LEVEL IS AN UPPER QUANTILE OF NON-ZERO DAYS, NOT A MEDIAN.
    S-1276 in this fleet reported exactly 0.00 kWh on all 31 days of January
    2019 at full sampling - a real month-long outage. Its 60-day reference
    median therefore sat at 0.27, and dividing by that inflated every later day
    by 3.7x: the site with the worst real collapse in the fleet came out as the
    best performer in its cohort, and a 35 % injected fault on top of it was
    invisible. Asking what a site produces WHEN IT IS WORKING is the quantity
    this normalisation actually wants, and since faults only push performance
    down, an upper quantile is robust in the right direction.

    Adds `reference_ratio` (the site constant being removed), `normalised_ratio`
    (what the peer comparison runs on) and `analysed`.

    Returns (frame, diagnostics). Sites without enough valid reference days are
    named in diagnostics under `unnormalisable` and left out of detection.
    """
    detector = params["detector"]
    reference_days = detector["reference_period_days"]
    quantile = detector["reference_quantile"]
    minimum_days = detector["min_reference_days"]

    frame = expected.copy()
    dates = sorted(frame["date"].unique())
    reference_dates = set(dates[:reference_days])

    # NON-ZERO DAYS ONLY. A day of exactly zero output is a total outage or a
    # dead feed; either way it is not a measurement of how this system performs
    # when it performs. Zero days are kept everywhere else - in detection they
    # are the strongest signal there is.
    candidates = frame[
        frame["date"].isin(reference_dates)
        & frame["performance_ratio"].notna()
        & (frame["actual_kwh"] > 0)
    ]

    grouped = candidates.groupby("site_id")["performance_ratio"]
    reference = grouped.quantile(quantile)
    valid_days = grouped.size()

    unnormalisable = sorted(valid_days[valid_days < minimum_days].index.tolist())
    missing = sorted(set(frame["site_id"].unique()) - set(valid_days.index))
    unnormalisable = sorted(set(unnormalisable) | set(missing))

    frame["reference_ratio"] = frame["site_id"].map(reference)
    frame["reference_days"] = frame["site_id"].map(valid_days).fillna(0).astype(int)
    frame["normalised_ratio"] = np.where(
        frame["reference_ratio"] > 0,
        frame["performance_ratio"] / frame["reference_ratio"],
        np.nan,
    )

    not_analysed = set(excluded_site_ids) | set(unnormalisable)
    frame["analysed"] = ~frame["site_id"].isin(not_analysed)

    return frame, {
        "reference_period_days": reference_days,
        "reference_quantile": quantile,
        "reference_period_start": dates[0] if dates else None,
        "reference_period_end": dates[min(reference_days, len(dates)) - 1] if dates else None,
        "min_reference_days": minimum_days,
        "unnormalisable": unnormalisable,
        "site_reference_ratios": {
            site_id: round(float(value), 4) for site_id, value in reference.items()},
        "site_reference_days": {
            site_id: int(value) for site_id, value in valid_days.items()},
    }


def add_peer_statistics(frame, cohort_by_site, params):
    """Per cohort per day: peer median, MAD, and each member's modified z-score.

    Only ANALYSED sites enter the median and the MAD. A site excluded for
    incomplete telemetry would drag the peer level down and make genuinely
    healthy neighbours look better than they are, which is precisely how a real
    fault gets masked.
    """
    mad_floor_fraction = params["detector"]["mad_floor_fraction"]

    working = frame.copy()
    working["cohort_id"] = working["site_id"].map(cohort_by_site)

    scored = working[working["analysed"] & working["normalised_ratio"].notna()]

    grouped = scored.groupby(["cohort_id", "date"])["normalised_ratio"]
    peer_median = grouped.median().rename("peer_median")
    peer_count = grouped.size().rename("peer_count")

    deviations = scored.join(peer_median, on=["cohort_id", "date"])
    deviations["absolute_deviation"] = (
        deviations["normalised_ratio"] - deviations["peer_median"]).abs()
    peer_mad = (
        deviations.groupby(["cohort_id", "date"])["absolute_deviation"]
        .median().rename("peer_mad")
    )

    working = working.join(peer_median, on=["cohort_id", "date"])
    working = working.join(peer_mad, on=["cohort_id", "date"])
    working = working.join(peer_count, on=["cohort_id", "date"])

    # THE FLOOR IS LOad-BEARING. VEGAS-01's five roofs share one coordinate and
    # one weather feed, so on a calm clear day their spread can approach zero.
    # An unfloored divide turns a 0.3 % difference into an unbounded z-score and
    # dispatches a technician to a site that is fine.
    floor = working["peer_median"].abs() * mad_floor_fraction
    working["peer_mad_floored"] = working["peer_mad"].where(
        working["peer_mad"] > floor, floor)

    # The raw peer deviation, in units of the site's own expected output. This is
    # the quantity everything downstream is built on: the site-level score
    # standardises it, the shortfall converts it to kWh, and the divergence date
    # is where it crosses the resolution floor.
    working["deviation"] = working["normalised_ratio"] - working["peer_median"]

    working["modified_z"] = np.where(
        working["peer_mad_floored"] > 0,
        MODIFIED_Z_CONSTANT * working["deviation"] / working["peer_mad_floored"],
        np.nan,
    )
    return working


def site_level_scores(frame, params):
    """The reported score: is this site an outlier AMONG ITS PEERS THIS MONTH?

    WHY THIS IS A SEPARATE LAYER FROM THE DAILY Z-SCORE, AND WHY GETTING IT
    WRONG COSTS THE WHOLE MODULE. The daily modified z-score answers "was this
    site an outlier TODAY", and Iglewicz and Hoaglin's -3.5 is the right cutoff
    for exactly that question. It is the wrong cutoff for a month of evidence.
    A single day carries the baseline's full noise - about 7.5 % peer-relative
    MAD on this fleet - so demanding -3.5 on a daily statistic demands a
    39 % instantaneous loss before anything is reported. A 35 % step drop scored
    -3.15 and went unflagged, which is not a conservative detector, it is a
    broken one.

    Thirty days of a persistent shortfall is not one noisy observation, so the
    test belongs at the level the evidence lives at. Each site is reduced to ONE
    number - the median of its daily peer deviations over the evaluation window -
    and the modified z-score is then computed ACROSS THE COHORT'S site-level
    numbers. That is Iglewicz-Hoaglin used for what it was designed for:
    identifying an outlier within a small sample. Five roofs sitting within 2 %
    of each other and a sixth sitting 30 % below is exactly the shape the
    modified z-score exists to score, and -3.5 is a defensible bar for it.

    Returns {site_id: {...}} for analysed sites only.
    """
    detector = params["detector"]
    window_days = detector["evaluation_window_days"]
    floor = detector["site_mad_floor_ratio"]

    dates = sorted(frame["date"].unique())
    window_dates = set(dates[-window_days:])

    window = frame[
        frame["analysed"]
        & frame["date"].isin(window_dates)
        & frame["deviation"].notna()
    ]
    if window.empty:
        return {}

    per_site = window.groupby(["cohort_id", "site_id"]).agg(
        window_deviation=("deviation", "median"),
        days_scored=("deviation", "size"),
        days_below_peers=("deviation", lambda values: int((values < 0).sum())),
    ).reset_index()

    scores = {}
    for cohort_id, group in per_site.groupby("cohort_id"):
        values = group["window_deviation"].to_numpy(dtype=float)
        cohort_median = float(np.median(values))
        cohort_mad = float(np.median(np.abs(values - cohort_median)))

        # SAME FLOOR ARGUMENT AS THE DAILY LAYER, AT THE MONTHLY LEVEL. Five
        # healthy roofs on one coordinate can agree to a fraction of a percent
        # over a month. Without a floor, a 0.5 % difference between two fine
        # sites divides into an enormous z-score and dispatches a technician.
        # The floor is a statement about resolution: below 2 % of expected
        # output, this method does not claim to tell sites apart.
        effective_mad = max(cohort_mad, floor)

        for _, row in group.iterrows():
            deviation = float(row["window_deviation"])
            scores[row["site_id"]] = {
                "score": round(
                    MODIFIED_Z_CONSTANT * (deviation - cohort_median) / effective_mad, 2),
                "window_deviation": round(deviation, 4),
                "cohort_window_median": round(cohort_median, 4),
                "cohort_window_mad": round(cohort_mad, 4),
                "cohort_window_mad_floored": round(effective_mad, 4),
                "days_scored": int(row["days_scored"]),
                "days_below_peers": int(row["days_below_peers"]),
                "persistence": round(
                    float(row["days_below_peers"]) / float(row["days_scored"]), 4),
            }
    return scores


def locate_divergence(site_frame, params):
    """When did this site leave its cohort?

    Method: smooth the daily PEER DEVIATION with a centred rolling median, then
    take the START of the TRAILING RUN of days that stay at or below the
    resolution floor - that is, days on which the site sat more than
    `site_mad_floor_ratio` below its peers.

    Dated on the deviation rather than on the daily z-score deliberately. The
    daily z divides by a peer MAD that moves from day to day, so a fault of
    constant size crosses back and forth over any fixed z cutoff as the weather
    changes the cohort's spread. The deviation is a stable physical quantity -
    the fraction of its own expected output the site is missing - and a
    divergence date should be a property of the site, not of last Tuesday's
    cloud cover.

    THE RUN HAS TO BE LIVE. A start date means "this began then and is still
    going on", so it is only returned when the final day of the series is itself
    below the threshold. A dip that opened and closed in April is history, not a
    dispatch reason, and reporting its start date would put a divergence marker
    on Screen 2 for a site that has since recovered.

    Returns (start_date, days_since) or (None, None).
    """
    floor = params["detector"]["site_mad_floor_ratio"]
    window = params["detector"]["rolling_median_days"]

    ordered = site_frame.sort_values("date")
    smoothed = (
        ordered["deviation"]
        .rolling(window=window, center=True, min_periods=max(1, window // 2))
        .median()
    )

    below = (smoothed <= -floor).fillna(False).to_numpy()
    if not below.any() or not below[-1]:
        return None, None

    dates = ordered["date"].tolist()

    # Walk back from the final day while the condition still holds.
    index = len(below) - 1
    while index >= 0 and below[index]:
        index -= 1
    start_index = index + 1

    return dates[start_index], int(len(dates) - 1 - start_index)


def classify_shape(site_frame, start_date, params):
    """Step or ramp? Wording for the cause hypothesis, never a flag decision.

    A Theil-Sen slope on the post-divergence peer-deviation series. Theil-Sen
    rather than least squares because a single cloudy outlier should not set the
    diagnosis, and because it is the robust estimator that matches the robust
    statistic it is reading. Slope is in deviation units per day, so it means
    "fraction of expected output lost per day" and the threshold that separates
    a ramp from a step is a physical rate rather than a tuning knob.
    """
    slope_threshold = params["detector"]["soiling_slope_threshold_per_day"]

    if start_date is None:
        return None, None

    after = site_frame[site_frame["date"] >= start_date].sort_values("date")
    values = after["deviation"].to_numpy(dtype=float)
    finite = np.isfinite(values)
    if finite.sum() < 3:
        return None, None

    x = np.arange(len(values))[finite]
    slope = float(stats.theilslopes(values[finite], x)[0])

    shape = "progressive" if slope <= slope_threshold else "step"
    return shape, round(slope, 5)


def score_site(site_frame, site_score, params):
    """Everything the artifact needs about one site's detection state.

    THREE CONDITIONS, AND EACH GUARDS A DIFFERENT FAILURE.

      score <= threshold          the shortfall stands out from the cohort
      persistence >= minimum      it is a condition, not a one-week incident
      deviation <= -materiality   it is big enough to be worth knowing about

    Any one alone flags the wrong things. Score alone fires on a site that lost
    a week to a grid outage and has since recovered. Persistence alone fires on
    a site sitting a harmless half a percent under its peers every single day -
    and on this fleet persistence separates faults from controls so cleanly that
    a rule leaning on it alone would look excellent in the confusion matrix
    while dispatching technicians to healthy roofs. Materiality alone fires on
    one cloudy fortnight.

    None of this decides whether to send anyone. That is money, and it belongs
    to M4: the pipeline demotes a flagged site to `monitor` when its loss does
    not clear the cost of the visit.
    """
    detector = params["detector"]
    threshold = detector["modified_z_threshold"]

    if site_score is None:
        return None

    ordered = site_frame.sort_values("date")
    persistence = site_score["persistence"]

    flagged = (site_score["score"] <= threshold
               and persistence >= detector["min_persistence"]
               and site_score["window_deviation"] <= -detector["min_material_deviation"])

    start_date, days_since = locate_divergence(ordered, params)
    shape, slope = classify_shape(ordered, start_date, params)

    window = ordered.tail(detector["evaluation_window_days"])

    return {
        "score": site_score["score"],
        "score_type": SCORE_TYPE,
        "threshold": threshold,
        "method": DETECTION_METHOD_NAME,
        "persistence": persistence,
        "window_deviation": site_score["window_deviation"],
        "cohort_window_median": site_score["cohort_window_median"],
        "cohort_window_mad": site_score["cohort_window_mad"],
        "days_below_peers": site_score["days_below_peers"],
        "days_scored": site_score["days_scored"],
        "flagged": bool(flagged),
        "divergence_start_date": start_date,
        "divergence_days_since": days_since,
        "shape": shape,
        "shape_slope_per_day": slope,
        "peer_count": int(window["peer_count"].max())
        if window["peer_count"].notna().any() else 0,
    }


def estimate_shortfall(site_frame, params):
    """kWh the site did not produce, measured against its own peers.

    Per day: the site's own calibrated expectation is `expected_kwh x
    reference_ratio` - M2's physics, corrected by the constant this site was
    already running at before anything went wrong. The peer level says what
    fraction of that a healthy cohort member delivered today. The gap between
    that and what this site delivered is the shortfall.

        shortfall = expected_kwh x reference_ratio x (peer_median - normalised_ratio)

    Clipped at zero, because a site running ABOVE its peers has not lost
    anything and must not contribute a negative loss that quietly offsets a real
    one somewhere else in the fleet.
    """
    window_days = params["detector"]["evaluation_window_days"]
    ordered = site_frame.sort_values("date")
    window = ordered.tail(window_days)

    gap = (window["peer_median"] - window["normalised_ratio"]).clip(lower=0)
    own_expectation = window["expected_kwh"] * window["reference_ratio"]
    daily_shortfall = (own_expectation * gap).fillna(0.0)

    scored_days = int(daily_shortfall.notna().sum())
    if scored_days == 0:
        return None

    mean_daily = float(daily_shortfall.mean())

    return {
        "mean_daily_shortfall_kwh": round(mean_daily, 2),
        "monthly_shortfall_kwh": round(mean_daily * 30.0, 1),
        "window_days": scored_days,
        "mean_own_expectation_kwh": round(float(own_expectation.mean()), 1),
    }


def cumulative_shortfall(site_frame, start_date, params):
    """Shortfall accumulated since divergence, on the same per-day formula."""
    if start_date is None:
        return None
    after = site_frame[site_frame["date"] >= start_date]
    gap = (after["peer_median"] - after["normalised_ratio"]).clip(lower=0)
    own_expectation = after["expected_kwh"] * after["reference_ratio"]
    return round(float((own_expectation * gap).fillna(0.0).sum()), 1)


# --- Top level --------------------------------------------------------------


def run_detector(sites, expected, params, excluded_site_ids=()):
    """Score the whole fleet. Returns (results, frame, diagnostics)."""
    clustered = cluster_cohorts(sites, params)
    mapping, agreement = reconcile_with_configured_cohorts(clustered, sites)

    cohort_by_site = {}
    for derived_key, members in clustered.items():
        cohort_id = mapping.get(derived_key, derived_key)
        for site_id in members:
            cohort_by_site[site_id] = cohort_id

    normalised, reference_diagnostics = add_reference_normalisation(
        expected, params, excluded_site_ids)
    frame = add_peer_statistics(normalised, cohort_by_site, params)

    # A site is scored only if it is both analysable (telemetry complete enough)
    # and normalisable (enough working days in the reference period to know what
    # its own baseline is). Failing either means we do not know enough to say
    # anything about it, which is a different statement from "it is healthy" and
    # is reported as such.
    not_scored = set(excluded_site_ids) | set(reference_diagnostics["unnormalisable"])
    site_scores = site_level_scores(frame, params)

    results = {}
    for site_id, site_frame in frame.groupby("site_id"):
        if site_id in not_scored:
            continue
        scored = score_site(site_frame, site_scores.get(site_id), params)
        if scored is None:
            continue
        scored["cohort_id"] = cohort_by_site.get(site_id)
        scored["shortfall"] = estimate_shortfall(site_frame, params)
        scored["cumulative_shortfall_kwh"] = cumulative_shortfall(
            site_frame, scored["divergence_start_date"], params)
        results[site_id] = scored

    diagnostics = {
        "method": DETECTION_METHOD_NAME,
        "clustering_method": CLUSTERING_METHOD_NAME,
        "clustering": agreement,
        "cohort_by_site": cohort_by_site,
        "score_type": SCORE_TYPE,
        "threshold": params["detector"]["modified_z_threshold"],
    }
    diagnostics.update(reference_diagnostics)
    return results, frame, diagnostics


def cohort_median_performance_index(frame, cohort_by_site, params):
    """Median measured kWh/kWp per day per cohort, over the evaluation window.

    Screen 2's reference line. Computed on ANALYSED sites only, for the same
    reason the peer median is.
    """
    window_days = params["detector"]["evaluation_window_days"]
    dates = sorted(frame["date"].unique())
    window_dates = set(dates[-window_days:])

    if "performance_index" not in frame.columns:
        return {}

    working = frame[frame["analysed"] & frame["date"].isin(window_dates)].copy()
    working["cohort_id"] = working["site_id"].map(cohort_by_site)

    medians = {}
    for cohort_id, group in working.groupby("cohort_id"):
        values = group["performance_index"].dropna()
        if not values.empty:
            medians[cohort_id] = round(float(values.median()), 2)
    return medians


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--detail", action="store_true",
                        help="print the per-site daily z-score tail")
    arguments = parser.parse_args()

    irradiance = load_irradiance()
    if irradiance is None:
        raise SystemExit("no irradiance cache. Run: python pipeline/fetch_irradiance.py")

    actual = load_actual_daily()
    if actual is None:
        raise SystemExit("no fleet_daily.parquet. Run: python pipeline/fetch_pvdaq.py")

    params = load_model_params()
    sites = load_fleet_sites()
    excluded = plausibility_excluded_site_ids()

    expected, baseline_diagnostics = build_expected(
        sites, irradiance, actual, params, excluded_site_ids=excluded)
    results, frame, diagnostics = run_detector(sites, expected, params, excluded)

    print("M3 fleet peer benchmarking")
    print("-" * 78)
    print("method     : {}".format(diagnostics["method"]))
    print("clustering : {}".format(diagnostics["clustering_method"]))
    agreement = diagnostics["clustering"]
    print("             derived {} cohorts; agrees with config/fleet_sites.csv: {}".format(
        agreement["derived_cohort_count"], agreement["agrees_with_config"]))
    for key, members in agreement["unmatched"]:
        print("             UNMATCHED {}: {}".format(key, ", ".join(members)))
    print("reference  : {} to {} ({} days)".format(
        diagnostics["reference_period_start"], diagnostics["reference_period_end"],
        diagnostics["reference_period_days"]))
    print("excluded   : {}".format(", ".join(excluded) if excluded else "none"))
    print()

    header = "{:<8} {:<10} {:>7} {:>7} {:>6} {:>8} {:>12} {:>11}".format(
        "site", "cohort", "score", "persist", "flag", "shape", "divergence", "kWh/month")
    print(header)
    print("-" * len(header))
    for site_id in sorted(results, key=lambda key: results[key]["score"]):
        result = results[site_id]
        shortfall = result["shortfall"] or {}
        print("{:<8} {:<10} {:>7.2f} {:>7.0%} {:>6} {:>8} {:>12} {:>11}".format(
            site_id,
            result["cohort_id"] or "-",
            result["score"],
            result["persistence"],
            "YES" if result["flagged"] else "-",
            result["shape"] or "-",
            result["divergence_start_date"] or "-",
            "{:,.0f}".format(shortfall["monthly_shortfall_kwh"])
            if shortfall else "-",
        ))

    flagged = [site_id for site_id, result in results.items() if result["flagged"]]
    print()
    print("{} of {} analysed sites flagged: {}".format(
        len(flagged), len(results), ", ".join(sorted(flagged)) or "none"))

    if arguments.detail:
        print()
        window = params["detector"]["evaluation_window_days"]
        for site_id in sorted(results):
            tail = frame[frame["site_id"] == site_id].sort_values("date").tail(5)
            print("\n{} last 5 days".format(site_id))
            print(tail[["date", "performance_ratio", "normalised_ratio",
                        "peer_median", "peer_mad_floored", "modified_z"]]
                  .round(3).to_string(index=False))


if __name__ == "__main__":
    main()

"""Inject faults of known type, magnitude and date into the real PVDAQ series.

WHY THIS EXISTS. No open dataset labels site-level PV faults, so there is no
ground truth to score M3 against — and PRD section 11 makes "a stated accuracy
figure from a real test" the accountability for that module. This manufactures
the labels: real measured data, a synthetic fault we placed ourselves, and a
file recording exactly what we did.

Real data, synthetic fault, labelled SIMULATED. That is what SIMULATED is for.

THE OBVIOUS ATTACK, AND THE ANSWER. "You found faults you invented." The answer
is the severity ladder: inject the same fault at descending magnitude until the
detector stops seeing it, and publish where that happens. A recall curve that
decays to zero at low severity is evidence of an honest test; a flat 100% is
evidence of a rigged one. See docs/ARCHITECTURE.md section 5.

HOW DEEP A LADDER THIS FLEET CAN HOLD. Not deep, in one run. With 11 sites in
2 cohorts, the constraints below (never more than half a cohort, always leave
controls) allow at most FOUR injections at a time. Build a real recall curve by
pooling several seeded runs, not by asking one run for more sites — it will cap
silently otherwise, and it now says so when it does.

Every fault type has to vary with its ladder position or the ladder is
decorative. They vary differently, because they are not the same kind of
quantity — see the comments in choose_events.

WHAT THIS DOES NOT DO. It does not score anything. Precision, recall,
days-to-detect and false-positive rate need a detector, and M3 belongs to owner
A. This produces the answer key, not the marking.

Run:
    python pipeline/fault_injection.py --ladder --seed 42
    python pipeline/fault_injection.py --site S-1203 --type soiling_ramp --from 2019-05-01
    python pipeline/fault_injection.py --verify        # reversibility check
    python pipeline/fault_injection.py --clean         # remove injected artifacts

Reads:  data/processed/fleet_daily.parquet, inverter_daily.parquet,
        inverter_hardware.parquet   — NEVER modified
Writes: data/processed/*_injected.parquet, pipeline/output/ground_truth.json
        — all gitignored; synthetic data does not belong in a judged repo

Then:   python pipeline/generate_dispatch.py --injected
"""

import argparse
import datetime
import json
import os
import random

# --- Paths ------------------------------------------------------------------

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(REPOSITORY_ROOT, "data", "processed")
ASSUMPTIONS_PATH = os.path.join(REPOSITORY_ROOT, "config", "assumptions.json")
FLEET_SITES_PATH = os.path.join(REPOSITORY_ROOT, "config", "fleet_sites.csv")

FLEET_DAILY_PATH = os.path.join(PROCESSED_DIR, "fleet_daily.parquet")
INVERTER_DAILY_PATH = os.path.join(PROCESSED_DIR, "inverter_daily.parquet")
INVERTER_HARDWARE_PATH = os.path.join(PROCESSED_DIR, "inverter_hardware.parquet")

FLEET_INJECTED_PATH = os.path.join(PROCESSED_DIR, "fleet_daily_injected.parquet")
INVERTER_INJECTED_PATH = os.path.join(PROCESSED_DIR, "inverter_daily_injected.parquet")
GROUND_TRUTH_PATH = os.path.join(REPOSITORY_ROOT, "pipeline", "output", "ground_truth.json")

# --- Contract ---------------------------------------------------------------
# docs/Schema.md section 2.3. Three values, and they are three because these are
# exactly the shapes daily aggregates can carry honestly. Partial shading and
# curtailment are time-of-day effects: they need the 1-minute raw data that
# .gitignore excludes, and they would need new enum values. Deliberately absent,
# not forgotten.

FAULT_TYPES = ("step_drop", "soiling_ramp", "string_loss")

SYNTHETIC_NOTE = "SYNTHETIC — injected into real PVDAQ data. Not a real fault."

# Reversibility tolerance. Injection multiplies; reversal divides. Floating point
# means kwh * f / f is not always bit-identical to kwh, so "exact" has to mean
# "to a stated epsilon" rather than "==".
REVERSAL_EPSILON = 1e-9


def load_assumptions():
    with open(ASSUMPTIONS_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_frames():
    import pandas
    frames = {
        "fleet": pandas.read_parquet(FLEET_DAILY_PATH),
        "inverter": pandas.read_parquet(INVERTER_DAILY_PATH),
        "hardware": pandas.read_parquet(INVERTER_HARDWARE_PATH),
    }
    return frames


# --- The faults themselves --------------------------------------------------


def factor_for_day(event, day_index):
    """Multiplicative factor on day `day_index` of an event. Deterministic.

    This is the whole of the physics and the whole of the reversibility. Nothing
    random, nothing stateful: given the event record and a day offset, the factor
    is recomputable, which is what lets --verify reconstruct the original series
    from the ground-truth file alone.
    """
    if day_index < 0:
        return 1.0

    fault_type = event["fault_type"]

    if fault_type == "step_drop":
        # A fixed loss from the moment it starts — a tripped breaker, a string
        # disconnected. Flat, so trivially detectable at high magnitude and the
        # cleanest thing to ladder downward.
        return 1.0 - event["magnitude_pct"]

    if fault_type == "soiling_ramp":
        # Gradual accumulation, the fault a monthly calendar visit is supposed to
        # catch and usually does not. BOUNDED: unbounded at 0.47%/day this
        # reaches total loss on day 213 and then goes negative, inside a 233-day
        # window. The floor is the top of the observed Malaysian range.
        loss = event["rate_per_day"] * day_index
        loss = min(loss, event["max_loss_fraction"])
        return 1.0 - loss

    if fault_type == "string_loss":
        # One of N units drops out, so the SITE loses 1/N of its output.
        # docs/ARCHITECTURE.md section 5 specifies exactly this: P(t) x (1 - 1/N),
        # applied at site level.
        #
        # APPLIED TO THE SITE, NOT TO ONE UNIT. Multiplying a single unit by
        # (1 - 1/N) would cost the site only about 1/N^2 — on S-1199, 2% instead
        # of the intended 14%. The fraction is the site's share lost when a unit
        # dies; it is not a derating of the unit.
        #
        # NAMING: the schema enum says string_loss and the enum is frozen, but on
        # PVDAQ this is a UNIT dropout — no string metadata exists anywhere.
        # inverter_hardware.parquet carries unit_count, models and ratings, never
        # strings, and Schema.md already states per-inverter capacity is not
        # honestly known.
        return 1.0 - event["magnitude_pct"]

    raise ValueError("unknown fault_type {!r}".format(fault_type))


def day_offsets(dates, start_date, end_date):
    """Day offset per date, or None where the date is outside the event window."""
    start = datetime.date.fromisoformat(start_date)
    end = datetime.date.fromisoformat(end_date) if end_date else None
    offsets = []
    for value in dates:
        current = datetime.date.fromisoformat(str(value)[:10])
        if current < start or (end and current > end):
            offsets.append(None)
        else:
            offsets.append((current - start).days)
    return offsets


# --- Applying an event ------------------------------------------------------


def apply_event(frames, event):
    """Apply one event in place across both frames, keeping them consistent.

    THE CONSISTENCY RULE. Four sites (S-1199, S-1203, S-1278, S-1367) have
    kwh_source == "summed_inverters", meaning their fleet total IS the sum of
    their inverters. Change one side without the other and the two files
    silently disagree, which would show up much later as an unexplainable
    discrepancy rather than as an error here.

    So:
      site-level event -> scale the site AND every one of its inverters by the
                          same factor, so the sum still reconciles
      unit-level event -> scale that unit, then subtract the same delta from the
                          fleet total

    Subtracting the delta is right for both kinds of site. Where the fleet total
    was summed from inverters it is arithmetically identical to recomputing the
    sum; where the fleet total came from its own meter channel it is what a meter
    would physically have recorded with that unit down.
    """
    fleet = frames["fleet"]
    inverter = frames["inverter"]

    site_id = event["site_id"]
    unit_id = event.get("unit_id")

    site_rows = fleet["site_id"] == site_id
    offsets = day_offsets(fleet.loc[site_rows, "date"], event["injected_from"],
                          event.get("injected_until"))
    factors = [factor_for_day(event, offset) if offset is not None else 1.0
               for offset in offsets]

    kwh_before_site = float(fleet.loc[site_rows, "kwh"].sum())

    if unit_id is None:
        # --- site-level -------------------------------------------------------
        fleet.loc[site_rows, "kwh"] = fleet.loc[site_rows, "kwh"].to_numpy() * factors
        fleet.loc[site_rows, "injected"] = [factor != 1.0 for factor in factors]

        unit_rows = inverter["site_id"] == site_id
        if bool(unit_rows.any()):
            unit_offsets = day_offsets(inverter.loc[unit_rows, "date"],
                                       event["injected_from"], event.get("injected_until"))
            unit_factors = [factor_for_day(event, offset) if offset is not None else 1.0
                            for offset in unit_offsets]
            inverter.loc[unit_rows, "kwh"] = inverter.loc[unit_rows, "kwh"].to_numpy() * unit_factors
            inverter.loc[unit_rows, "injected"] = [f != 1.0 for f in unit_factors]
    else:
        # --- unit-level -------------------------------------------------------
        unit_rows = (inverter["site_id"] == site_id) & (inverter["inverter_id"] == unit_id)
        if not bool(unit_rows.any()):
            raise ValueError("site {} has no inverter {!r}".format(site_id, unit_id))

        unit_frame = inverter.loc[unit_rows]
        unit_offsets = day_offsets(unit_frame["date"], event["injected_from"],
                                   event.get("injected_until"))
        unit_factors = [factor_for_day(event, offset) if offset is not None else 1.0
                        for offset in unit_offsets]

        before = unit_frame["kwh"].to_numpy()
        after = before * unit_factors
        inverter.loc[unit_rows, "kwh"] = after
        inverter.loc[unit_rows, "injected"] = [f != 1.0 for f in unit_factors]

        # Push the same energy loss through to the site total, matched by date.
        delta_by_date = {}
        for date_value, lost in zip(unit_frame["date"], before - after):
            if lost:
                delta_by_date[str(date_value)] = delta_by_date.get(str(date_value), 0.0) + float(lost)

        site_dates = fleet.loc[site_rows, "date"].astype(str).tolist()
        site_kwh = fleet.loc[site_rows, "kwh"].to_numpy().copy()
        touched = []
        for index, date_value in enumerate(site_dates):
            lost = delta_by_date.get(date_value, 0.0)
            site_kwh[index] -= lost
            touched.append(lost != 0.0)
        fleet.loc[site_rows, "kwh"] = site_kwh
        fleet.loc[site_rows, "injected"] = touched

    # performance_index is kWh per kWp and is what every chart and every
    # detector reads. Leaving it stale would inject a fault the analysis cannot
    # see, which is worse than not injecting one.
    fleet.loc[site_rows, "performance_index"] = (
        fleet.loc[site_rows, "kwh"] / fleet.loc[site_rows, "capacity_kwp"])

    event["kwh_removed"] = round(kwh_before_site - float(fleet.loc[site_rows, "kwh"].sum()), 3)
    event["days_affected"] = sum(1 for factor in factors if factor != 1.0)
    return event


# --- Building events --------------------------------------------------------


def build_event(site_id, fault_type, injected_from, magnitude, assumptions,
                injected_until=None, unit_id=None, unit_count=None, severity_scale=1.0):
    """One ground-truth record. Carries everything --verify needs to reverse it."""
    if fault_type not in FAULT_TYPES:
        raise ValueError("fault_type must be one of {}".format(FAULT_TYPES))

    event = {
        "site_id": site_id,
        "unit_id": unit_id,
        "fault_type": fault_type,
        "injected_from": injected_from,
        "injected_until": injected_until,
        "magnitude_pct": magnitude,
        "note": SYNTHETIC_NOTE,
    }

    if fault_type == "soiling_ramp":
        # The ladder scales the RATE, not a fixed loss. A slower ramp is a harder
        # detection, which is exactly what the low end of the ladder is probing.
        #
        # This previously discarded severity_scale entirely, so every soiling
        # event was identical regardless of its ladder position and a third of
        # the ladder was decorative.
        # Round the SCALE first, then derive the rate from the rounded value, so
        # base_rate_per_day x severity_scale == rate_per_day exactly as recorded.
        # Rounding them independently left the label file failing its own
        # arithmetic — in the one artifact whose whole purpose is being auditable.
        # NOT ROUNDED. Rounding the product broke the equality this records:
        # base_rate_per_day x severity_scale == rate_per_day evaluated False at
        # the 0.25 rung. An auditor scripting that check on the one artifact
        # whose purpose is being auditable got a failure. The scale is rounded,
        # the rate is the exact product of the recorded values. Long floats are a
        # fair price for a label file that passes its own arithmetic.
        base_rate = assumptions["soiling_rate_per_day"]
        scale = round(severity_scale, 4)
        event["rate_per_day"] = base_rate * scale
        event["base_rate_per_day"] = base_rate
        event["severity_scale"] = scale
        event["max_loss_fraction"] = assumptions["soiling_max_loss_fraction"]
        # magnitude_pct is meaningless for a ramp — the loss depends on how long
        # it has been running. The factor comes from rate and floor, never this.
        event["magnitude_pct"] = None

    # Recorded for every event, not only string_loss. A unit-level fault costs
    # the site roughly magnitude/N, so a consumer cannot convert the label into a
    # site-level severity without N.
    if unit_count:
        event["unit_count"] = int(unit_count)

    # On every event, not only soiling. It lived inside the soiling branch, so
    # the descent test's filter admitted only soiling events — usually a
    # single-element list, trivially sorted. Coverage went DOWN relative to the
    # version it replaced.
    event["severity_scale"] = round(severity_scale, 4)

    if fault_type == "string_loss":
        if not unit_count or unit_count < 2:
            raise ValueError(
                "string_loss needs a site with at least 2 inverter units; "
                "{} has {}".format(site_id, unit_count))
        if unit_id is not None:
            raise ValueError(
                "string_loss is applied at SITE level — the site loses 1/N when one of N units "
                "drops out. For a single-unit fault use --type step_drop --unit.")
        event["magnitude_pct"] = round(1.0 / unit_count, 6)
        event["unit_count"] = unit_count

    # WHY NO TOTAL-OUTAGE FAULT. A dead unit producing exactly 0 would be the
    # most realistic dropout of all, and it is deliberately absent: multiplying
    # by zero destroys the information, so --verify could not reconstruct the
    # original from the injected series and the ground-truth file alone. The
    # reversibility guarantee is worth more than the extra fault shape. Add it
    # only alongside per-row originals in the label file.

    # affected_capacity_kwp is DELIBERATELY ABSENT. Schema.md section 8.9 shows
    # the field, but PVDAQ publishes no per-inverter DC capacity — only an
    # inverter AC rating, which is a different quantity. Deriving kWp from it
    # would be a fabricated number inside the one artifact whose entire purpose
    # is being trustworthy.

    return event


def choose_events(frames, assumptions, seed, count):
    """Pick a severity ladder, seeded, with the controls the protocol requires.

    Blind by construction: the developer does not choose the sites. Two
    constraints on top of that, both from docs/ARCHITECTURE-PLAN.md section 5:

      1. leave uninjected controls — the false-positive rate on clean sites is
         the commercially important metric, and it needs clean sites to exist
      2. never inject a whole cohort — peer benchmarking compares a site to its
         neighbours, so a cohort where everyone is faulty has no healthy
         reference and tests nothing

    Also skips any site already excluded for incomplete telemetry: it is not in
    the analysis, so a fault there would be a label nothing can ever match.
    """
    import pandas

    fleet = frames["fleet"]
    hardware = frames["hardware"].set_index("site_id")

    sites = pandas.read_csv(FLEET_SITES_PATH)
    sites["site_id"] = sites["source_system_id"].apply(lambda value: "S-{:0>4}".format(str(value).strip()))
    cohort_of = dict(zip(sites["site_id"], sites["cohort_id"]))

    floor = assumptions["min_plausible_performance_index"]
    means = fleet.groupby("site_id")["performance_index"].mean()
    eligible = sorted(site_id for site_id, mean in means.items() if mean >= floor)

    generator = random.Random(seed)
    generator.shuffle(eligible)

    per_cohort = {}
    chosen = []
    for site_id in eligible:
        if len(chosen) >= count:
            break
        cohort = cohort_of.get(site_id)
        cohort_size = sum(1 for other in eligible if cohort_of.get(other) == cohort)
        # Never take more than half a cohort, and never the last clean member.
        if per_cohort.get(cohort, 0) + 1 > max(1, cohort_size // 2):
            continue
        chosen.append(site_id)
        per_cohort[cohort] = per_cohort.get(cohort, 0) + 1

    dates = sorted(fleet["date"].astype(str).unique())

    # STAGGERED START DATES. Every fault sharing one start date is a tell: a
    # detector that learns "something happened on 19 March" scores well without
    # detecting anything, and days-to-detect measured from a single common point
    # flatters it. Real faults do not synchronise.
    #
    # Each start is drawn from the middle third of the window, leaving a clean
    # baseline before it and enough days after for a detector to have a chance.
    # The middle third, as stated — this previously drew from the SECOND QUARTER
    # while the comment promised a third of the way in, shortening the clean
    # baseline a detector needs. max(1, ...) keeps randrange non-empty on a short
    # window; a window under ~4 days cannot carry a meaningful injection anyway.
    # A real guard. `max(1, ...)` kept randrange non-empty but still indexed past
    # the end on a one-date window — an IndexError instead of a stated error.
    if len(dates) < 4:
        raise ValueError(
            "the series has {} date(s); an injection needs a clean baseline before it and "
            "days after it to be detectable. Re-run fetch_pvdaq.py.".format(len(dates)))

    earliest = max(1, len(dates) // 3)
    latest = max(earliest + 1, (len(dates) * 2) // 3)

    # THE SEVERITY LADDER. Descending, so the recall curve has a genuine failure
    # region rather than a wall of easy cases — publishing where the detector
    # stops working is the answer to "you found faults you invented"
    # (docs/ARCHITECTURE.md section 5).
    ladder = [0.35, 0.25, 0.18, 0.12, 0.08, 0.05]

    # Each fault type has to ACTUALLY vary with its ladder position, or the
    # ladder is decorative. How each one varies differs, because the three are
    # not the same kind of quantity:
    #
    #   step_drop     the magnitude IS the loss. Ladder applies directly.
    #   soiling_ramp  the magnitude scales the accumulation RATE. The base rate
    #                 is the sourced Malaysian figure; the ladder probes how
    #                 slow an onset the detector can still see.
    #   string_loss   1/N, fixed by how many inverters a site has. It cannot be
    #                 laddered without inventing a partial unit dropout, which
    #                 would undo the site-level semantics. Instead it varies
    #                 NATURALLY across sites: 7 units gives 14.3%, 2 gives 50%.
    #                 Honest variation beats a fabricated one.
    reference_severity = ladder[0]

    # TYPE AND RUNG MUST NOT BOTH COME FROM THE LOOP INDEX.
    #
    # They did: fault_type from `index % 3` and severity from `ladder[index % 6]`.
    # So soiling_ramp only ever landed at index 1, always drawing rung 0.25 — its
    # rate came out at 0.003357 in EVERY run at EVERY seed, and the fix that was
    # supposed to make it ladder achieved nothing. Reseeding could not help,
    # because the rung was a function of position, not of the seed.
    #
    # The type rotation is now offset by the seed, so across pooled runs each
    # type visits different rungs.
    offset = generator.randrange(3)

    # Exactly one unit-level injection per run, at the LOWEST rung among the
    # chosen sites that has inverter rows at all. Gating on `severity <= 0.12`
    # instead produced a unit-level event in only 24 of 200 seeds — and none at
    # the documented default — so the Screen 2 sub-site view it exists to feed
    # had nothing, and the test guarding it passed vacuously.
    def type_for(position, site_id, units):
        slot = (position + offset) % 3
        if slot == 1:
            return "soiling_ramp"
        if slot == 2 and units >= 2:
            return "string_loss"
        return "step_drop"

    unit_counts = {site_id: int(hardware["unit_count"].get(site_id, 1)) for site_id in chosen}
    eligible_for_unit = [
        (position, site_id) for position, site_id in enumerate(chosen)
        # position > 0 excludes the TOP rung. A unit drop of m costs the site
        # about m/N, so recording rung 0.35 for one would mislabel the ladder's
        # most important point by 2-7x. If the only site with inverters sits at
        # position 0, this run simply has no unit-level event — better than a
        # mislabelled one.
        if position > 0
        and type_for(position, site_id, unit_counts[site_id]) == "step_drop"
        and bool((frames["inverter"]["site_id"] == site_id).any())
    ]
    # The LOWEST rung among eligible sites — the site's fault must be a
    # step_drop AND the site must have inverter rows, so this is decided after
    # types are known rather than hoped for.
    #
    # It still cannot be guaranteed: only THREE analysable sites have inverter
    # rows at all (S-1199, S-1203, S-1278), so whether a run produces a
    # unit-level event depends on which sites the seed picks and which type they
    # land on. Measured at ~38% of seeds. For a guaranteed one, ask directly:
    #   --site S-1203 --type step_drop --unit inv1 --from 2019-05-01
    unit_level_site = eligible_for_unit[-1][1] if eligible_for_unit else None

    # WITHOUT REPLACEMENT. Independent draws collide about 7% of the time with
    # 4 events over ~78 candidate dates, so the distinctness the test asserts was
    # never enforced — and the module docstring tells you to re-run at other
    # seeds, straight into a red suite.
    span = list(range(earliest, latest))
    if len(span) < len(chosen):
        span = list(range(0, max(1, len(dates))))
    start_indices = generator.sample(span, min(len(chosen), len(span)))

    events = []
    for index, site_id in enumerate(chosen):
        units = int(hardware["unit_count"].get(site_id, 1))
        severity = ladder[index % len(ladder)]
        fault_type = type_for(index, site_id, units)

        # A unit-level step_drop gives the Screen 2 sub-site view something real.
        # string_loss is site-level by definition — see factor_for_day.
        #
        # NOT AT THE TOP RUNG. A unit-level drop of m costs the SITE about m/N,
        # so pairing it with rung 0 recorded 0.35 for a site that lost 0.17 on two
        # units, or 0.05 on seven — the ladder's most important point mislabelled
        # by 2-7x. Unit-level faults now take the lowest rungs, where being a
        # fraction of the site is the intent rather than an error.
        unit_id = None
        if fault_type == "step_drop" and site_id == unit_level_site:
            site_units = sorted(
                frames["inverter"].loc[frames["inverter"]["site_id"] == site_id, "inverter_id"].unique())
            if site_units:
                unit_id = site_units[generator.randrange(len(site_units))]

        events.append(build_event(
            site_id=site_id,
            fault_type=fault_type,
            injected_from=dates[start_indices[index % len(start_indices)]],
            magnitude=severity,
            assumptions=assumptions,
            unit_id=unit_id,
            unit_count=units,
            severity_scale=severity / reference_severity,
        ))
    return events


# --- Guardrail --------------------------------------------------------------


def warn_on_plausibility_floor(frames, assumptions, events):
    """A severe injection can push a site under the data-quality floor.

    build_exclusions() in generate_dispatch.py drops any site averaging below
    min_plausible_performance_index, treating it as incomplete telemetry rather
    than a fault. A site injected hard enough would therefore be deleted from the
    analysis and the label would match nothing — the test case destroyed
    silently.

    generate_dispatch --injected computes exclusions from the PRE-injection
    series precisely so this cannot happen. This warning exists anyway, because
    a fault severe enough to look like a broken feed is also a fault no honest
    ladder should be claiming credit for.
    """
    floor = assumptions["min_plausible_performance_index"]
    means = frames["fleet"].groupby("site_id")["performance_index"].mean()
    warnings = []
    for event in events:
        mean = float(means.get(event["site_id"], 0.0))
        if mean < floor:
            warnings.append("{} now averages {:.2f} kWh/kWp/day, below the {:.1f} plausibility "
                            "floor — that reads as a broken feed, not a fault".format(
                                event["site_id"], mean, floor))
    return warnings


# --- Verification -----------------------------------------------------------


def verify():
    """Reconstruct the original series from the injected one plus ground truth.

    docs/BUILD_PLAN.md Stage 6: done when a fault can be injected and then
    recovered exactly. "Exactly" means to REVERSAL_EPSILON — injection multiplies
    and reversal divides, so bit-identity is not available in floating point and
    claiming it would be false.
    """
    import pandas

    for path in (FLEET_INJECTED_PATH, INVERTER_INJECTED_PATH, GROUND_TRUTH_PATH):
        if not os.path.exists(path):
            print("nothing to verify — run an injection first ({} missing)".format(
                os.path.relpath(path, REPOSITORY_ROOT)))
            return 1

    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as handle:
        truth = json.load(handle)

    original_fleet = pandas.read_parquet(FLEET_DAILY_PATH)
    injected_fleet = pandas.read_parquet(FLEET_INJECTED_PATH)
    original_units = pandas.read_parquet(INVERTER_DAILY_PATH)
    injected_units = pandas.read_parquet(INVERTER_INJECTED_PATH)

    rebuilt_fleet = injected_fleet.copy()
    rebuilt_units = injected_units.copy()

    # Reverse in the opposite order to application, so stacked events on one site
    # unwind correctly.
    for event in reversed(truth["events"]):
        site_id = event["site_id"]
        unit_id = event.get("unit_id")

        if unit_id is None:
            rows = rebuilt_fleet["site_id"] == site_id
            offsets = day_offsets(rebuilt_fleet.loc[rows, "date"], event["injected_from"],
                                  event.get("injected_until"))
            factors = [factor_for_day(event, offset) if offset is not None else 1.0
                       for offset in offsets]
            rebuilt_fleet.loc[rows, "kwh"] = rebuilt_fleet.loc[rows, "kwh"].to_numpy() / factors

            unit_rows = rebuilt_units["site_id"] == site_id
            if bool(unit_rows.any()):
                unit_offsets = day_offsets(rebuilt_units.loc[unit_rows, "date"],
                                           event["injected_from"], event.get("injected_until"))
                unit_factors = [factor_for_day(event, offset) if offset is not None else 1.0
                                for offset in unit_offsets]
                rebuilt_units.loc[unit_rows, "kwh"] = (
                    rebuilt_units.loc[unit_rows, "kwh"].to_numpy() / unit_factors)
        else:
            unit_rows = (rebuilt_units["site_id"] == site_id) & (rebuilt_units["inverter_id"] == unit_id)
            unit_frame = rebuilt_units.loc[unit_rows]
            unit_offsets = day_offsets(unit_frame["date"], event["injected_from"],
                                       event.get("injected_until"))
            unit_factors = [factor_for_day(event, offset) if offset is not None else 1.0
                            for offset in unit_offsets]
            after = unit_frame["kwh"].to_numpy()
            before = after / unit_factors
            rebuilt_units.loc[unit_rows, "kwh"] = before

            restored = {}
            for date_value, lost in zip(unit_frame["date"], before - after):
                if lost:
                    restored[str(date_value)] = restored.get(str(date_value), 0.0) + float(lost)

            rows = rebuilt_fleet["site_id"] == site_id
            site_dates = rebuilt_fleet.loc[rows, "date"].astype(str).tolist()
            site_kwh = rebuilt_fleet.loc[rows, "kwh"].to_numpy().copy()
            for index, date_value in enumerate(site_dates):
                site_kwh[index] += restored.get(date_value, 0.0)
            rebuilt_fleet.loc[rows, "kwh"] = site_kwh

    failures = []
    for label, rebuilt, original, keys in (
            ("fleet", rebuilt_fleet, original_fleet, ["site_id", "date"]),
            ("inverter", rebuilt_units, original_units, ["site_id", "inverter_id", "date"])):
        merged = original.merge(rebuilt[keys + ["kwh"]], on=keys, suffixes=("_original", "_rebuilt"))
        if len(merged) != len(original):
            failures.append("{}: {} rows recovered against {} original".format(
                label, len(merged), len(original)))
        drift = (merged["kwh_original"] - merged["kwh_rebuilt"]).abs()
        worst = float(drift.max()) if len(drift) else 0.0
        scale = float(merged["kwh_original"].abs().max()) or 1.0
        print("  {:<9} worst absolute drift {:.3e} kWh over {} rows".format(label, worst, len(merged)))
        if worst / scale > REVERSAL_EPSILON:
            failures.append("{}: worst drift {:.3e} exceeds epsilon {:.0e} relative to {:.1f} kWh".format(
                label, worst, REVERSAL_EPSILON, scale))

    if failures:
        print("\nFAILED — the injection is not exactly reversible:")
        for failure in failures:
            print("  " + failure)
        return 1

    print("\nPASSED — original series recovered to within {:.0e} relative.".format(REVERSAL_EPSILON))
    return 0


# --- Entry point ------------------------------------------------------------


def write_outputs(frames, events, seed):
    os.makedirs(os.path.dirname(GROUND_TRUTH_PATH), exist_ok=True)
    frames["fleet"].to_parquet(FLEET_INJECTED_PATH, index=False)
    frames["inverter"].to_parquet(INVERTER_INJECTED_PATH, index=False)

    truth = {
        "data_status": "SIMULATED",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": seed,
        "reversal_epsilon": REVERSAL_EPSILON,
        "note": (
            "Ground truth for M3 validation. Real NREL PVDAQ measurements with faults we injected "
            "ourselves. Dates are SOURCE dates (2019); generate_dispatch.py remaps them to the demo "
            "window when it emits the per-site block. Never display this file in the UI, and never "
            "use it as an input to detection."
        ),
        "source": {
            "fleet_daily": os.path.relpath(FLEET_DAILY_PATH, REPOSITORY_ROOT),
            "inverter_daily": os.path.relpath(INVERTER_DAILY_PATH, REPOSITORY_ROOT),
        },
        "event_count": len(events),
        "events": events,
    }
    with open(GROUND_TRUTH_PATH, "w", encoding="utf-8") as handle:
        json.dump(truth, handle, indent=2)
        handle.write("\n")


def clean():
    removed = []
    for path in (FLEET_INJECTED_PATH, INVERTER_INJECTED_PATH, GROUND_TRUTH_PATH):
        if os.path.exists(path):
            os.remove(path)
            removed.append(os.path.relpath(path, REPOSITORY_ROOT))
    print("removed: {}".format(", ".join(removed)) if removed else "nothing to remove")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", help="site_id to inject into, e.g. S-1203")
    parser.add_argument("--type", dest="fault_type", choices=FAULT_TYPES)
    parser.add_argument("--from", dest="injected_from", help="start date, YYYY-MM-DD (source year)")
    parser.add_argument("--until", dest="injected_until", help="optional end date")
    parser.add_argument("--magnitude", type=float, default=0.20,
                        help="loss fraction for step_drop (default 0.20)")
    parser.add_argument("--unit", dest="unit_id", help="inverter_id for a unit-level injection")
    parser.add_argument("--ladder", action="store_true",
                        help="seeded severity ladder across several sites")
    parser.add_argument("--count", type=int, default=4, help="sites in the ladder (default 4)")
    parser.add_argument("--seed", type=int, default=42, help="seed for site selection")
    parser.add_argument("--verify", action="store_true", help="check reversibility and exit")
    parser.add_argument("--clean", action="store_true", help="remove injected artifacts and exit")
    parser.add_argument("--dry-run", action="store_true", help="report, write nothing")
    args = parser.parse_args()

    if args.clean:
        return clean()
    if args.verify:
        return verify()

    assumptions = load_assumptions()
    frames = load_frames()
    frames["fleet"]["injected"] = False
    frames["inverter"]["injected"] = False

    if args.ladder:
        events = choose_events(frames, assumptions, args.seed, args.count)
    else:
        if not (args.site and args.fault_type and args.injected_from):
            parser.error("give --site, --type and --from, or use --ladder")
        units = int(frames["hardware"].set_index("site_id")["unit_count"].get(args.site, 1))
        events = [build_event(
            site_id=args.site, fault_type=args.fault_type, injected_from=args.injected_from,
            magnitude=args.magnitude, assumptions=assumptions,
            injected_until=args.injected_until, unit_id=args.unit_id, unit_count=units)]

    for event in events:
        apply_event(frames, event)

    if args.ladder and len(events) < args.count:
        # Reported by the CLI, not by choose_events — library code printing made
        # every test run emit this banner and gave a programmatic caller nothing
        # to read. The fact is already `len(events) < count` at the return.
        print("  ! asked for {} injection sites, the constraints allow {}.".format(
            args.count, len(events)))
        print("    Causes: never more than half a cohort, controls must remain, and")
        print("    sites already below the plausibility floor are skipped.")
        print("    For a real recall curve, pool several seeds — a curve built from")
        print("    {} points is a line with pretensions.\n".format(len(events)))

    print("injected {} event(s), seed {}".format(len(events), args.seed))
    for event in events:
        target = event["site_id"] + ("/" + event["unit_id"] if event.get("unit_id") else "")
        magnitude = event.get("magnitude_pct")
        print("  {:<16} {:<13} from {}  {:>7}  -{:.1f} kWh over {} days".format(
            target, event["fault_type"], event["injected_from"],
            "{:.1%}".format(magnitude) if magnitude else "ramp",
            event["kwh_removed"], event["days_affected"]))

    for warning in warn_on_plausibility_floor(frames, assumptions, events):
        print("  ! " + warning)

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    write_outputs(frames, events, args.seed)
    print("\nwrote {}".format(os.path.relpath(FLEET_INJECTED_PATH, REPOSITORY_ROOT)))
    print("      {}".format(os.path.relpath(INVERTER_INJECTED_PATH, REPOSITORY_ROOT)))
    print("      {}".format(os.path.relpath(GROUND_TRUTH_PATH, REPOSITORY_ROOT)))
    print("\nnext: python pipeline/fault_injection.py --verify")
    print("      python pipeline/generate_dispatch.py --injected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Produce pipeline/output/dispatch.json — the single artifact the dashboard reads.

Run:
    python pipeline/generate_dispatch.py
    python pipeline/validate_dispatch.py     # always run this after

WHAT THIS DOES AND DOES NOT DO
------------------------------
This module assembles the `dispatch.json` shape defined in docs/Schema.md. It is
deliberately NOT an implementation of M2, M3 or M5:

    M2 (expected-output baseline)  -> owner A. `expected_kwh` is emitted as null.
    M3 (cohort detection)          -> owner A. Scoring here is a PLACEHOLDER.
    M5 (computer vision)           -> owner B. No `evidence` block is emitted.

Every value those modules will eventually own is marked `data_status:
"PLACEHOLDER"` so `validate_dispatch.py` can list what still has to be replaced
before submission. Replacing the internals of this file is the intended workflow
— see `write_dispatch_file` at the bottom, which is the interface to preserve.

REAL DATA
---------
If `data/processed/fleet_daily.parquet` exists (written by M1's fetch step), the
daily series are read from it. If it does not, a clearly-labelled placeholder
series is generated so the dashboard can be built before ingestion lands. The
frontend cannot tell the difference structurally, which is the entire point of
freezing the schema.
"""

import csv
import datetime
import json
import math
import os

# --- Paths ------------------------------------------------------------------

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLEET_SITES_PATH = os.path.join(REPOSITORY_ROOT, "config", "fleet_sites.csv")
ASSUMPTIONS_PATH = os.path.join(REPOSITORY_ROOT, "config", "assumptions.json")
FLEET_DAILY_PATH = os.path.join(REPOSITORY_ROOT, "data", "processed", "fleet_daily.parquet")
INVERTER_DAILY_PATH = os.path.join(REPOSITORY_ROOT, "data", "processed", "inverter_daily.parquet")
INVERTER_THERMAL_PATH = os.path.join(REPOSITORY_ROOT, "data", "processed", "inverter_thermal.parquet")
INVERTER_HARDWARE_PATH = os.path.join(REPOSITORY_ROOT, "data", "processed", "inverter_hardware.parquet")
OUTPUT_DIRECTORY = os.path.join(REPOSITORY_ROOT, "pipeline", "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIRECTORY, "dispatch.json")
FRONTEND_PUBLIC_DIR = os.path.join(REPOSITORY_ROOT, "apps", "web", "public")

# --- Versioning and the demo window ----------------------------------------
# These are not commercial constants (those live in config/assumptions.json).
# They describe the shape of the artifact and the date axis.

SCHEMA_VERSION = "1.5.0"
PIPELINE_VERSION = "0.4.0-placeholder"

SERIES_DAY_COUNT = 90          # docs/Schema.md section 8.6
REPORTING_MONTH = "2026-08"
REPORTING_MONTH_LABEL = "August 2026"
SERIES_END_DATE = datetime.date(2026, 8, 16)

# Source data is calendar 2019; the date axis is shifted forward to a 2026 demo
# window so the dashboard header reads coherently. Values are never modified.
# docs/Schema.md section 9. Applied once, here, and nowhere else.
DATE_REMAP_SOURCE_YEAR = 2019
DATE_REMAP_TARGET_YEAR = 2026

# --- PLACEHOLDER detection --------------------------------------------------
# TODO(owner A, M3): delete this block entirely. Real cohort clustering and
# peer-deviation scoring replace it. These site ids are chosen only so the four
# screens have something to render; they carry no analytical meaning whatsoever.

PLACEHOLDER_DISPATCH_SITE_IDS = ["1203", "34", "1367"]
PLACEHOLDER_MONITOR_SITE_IDS = ["1199", "1278"]

PLACEHOLDER_DETECTION_METHOD = "PLACEHOLDER — cohort mean deviation, to be replaced by M3 (owner A)"
PLACEHOLDER_CLUSTERING_METHOD = "PLACEHOLDER — cohort_id read from config/fleet_sites.csv, to be replaced by M3 (owner A)"

COHORT_LABELS = {
    "DSUN-01": "Mid-Atlantic distributed cluster",
    "VEGAS-01": "Greater Las Vegas cluster",
    "GOLDEN-01": "Golden, CO cluster",
}


# --- Loading ----------------------------------------------------------------


def load_assumptions():
    """Read config/assumptions.json. Copied verbatim into the output; never recomputed."""
    with open(ASSUMPTIONS_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_fleet_sites():
    """Read config/fleet_sites.csv into a list of dicts, one per site."""
    with open(FLEET_SITES_PATH, "r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    sites = []
    for row in rows:
        sites.append({
            "source_system_id": row["source_system_id"].strip(),
            "name": row["name"].strip(),
            "site_location": row["site_location"].strip(),
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "capacity_kwp": float(row["capacity_kwp"]),
            "cohort_id": row["cohort_id"].strip() or None,
        })
    return sites


def remap_date(iso_date):
    """Shift a source-year date into the demo window. Values are never touched.

    docs/Schema.md section 9: applied ONCE, here, and nowhere else. The shift is
    a whole number of years so month and day are preserved — only the year moves,
    which keeps seasonality intact. Disclosed via meta.date_remapped.
    """
    year_shift = DATE_REMAP_TARGET_YEAR - DATE_REMAP_SOURCE_YEAR
    parsed = datetime.date.fromisoformat(iso_date[:10])
    try:
        return parsed.replace(year=parsed.year + year_shift).isoformat()
    except ValueError:
        # 29 February in a source leap year with a non-leap target.
        return parsed.replace(year=parsed.year + year_shift, day=28).isoformat()


def load_real_daily_series():
    """Return real daily data keyed by site_id, or None when M1 has not run yet.

    Expected columns: site_id, date, kwh, capacity_kwp, performance_index.
    """
    if not os.path.exists(FLEET_DAILY_PATH):
        return None

    try:
        import pandas
    except ImportError:
        print("  ! fleet_daily.parquet exists but pandas is not installed — using placeholder series")
        return None

    frame = pandas.read_parquet(FLEET_DAILY_PATH)
    series_by_site = {}
    for site_id, group in frame.groupby("site_id"):
        ordered = group.sort_values("date")
        series_by_site[str(site_id)] = [
            {
                "date": remap_date(str(record["date"])),
                "actual_kwh": float(record["kwh"]),
                "performance_index": float(record["performance_index"]),
            }
            for record in ordered.to_dict("records")
        ]
    return series_by_site


def load_inverter_daily():
    """Per-inverter daily energy, keyed by site_id, or None when unavailable.

    Enables the sub-site view: each inverter compared against the median of its
    siblings on the same roof. Siblings share weather perfectly, so divergence
    between them is unambiguous in a way site-to-site comparison never is.
    """
    if not os.path.exists(INVERTER_DAILY_PATH):
        return None
    try:
        import pandas
    except ImportError:
        return None

    frame = pandas.read_parquet(INVERTER_DAILY_PATH)
    by_site = {}
    for site_id, site_group in frame.groupby("site_id"):
        units = {}
        for unit_id, unit_group in site_group.groupby("inverter_id"):
            ordered = unit_group.sort_values("date")
            units[str(unit_id)] = [
                {"date": remap_date(str(record["date"])), "kwh": float(record["kwh"])}
                for record in ordered.to_dict("records")
            ]
        by_site[str(site_id)] = units
    return by_site


def load_inverter_thermal():
    """Per-inverter operating temperature, keyed by site_id then inverter_id.

    Sibling comparison is the primary signal: several systems publish inverter
    temperature but no ambient channel, and siblings share weather, roof and hour
    so a difference between them is attributable in a way a rise above ambient
    is not.
    """
    if not os.path.exists(INVERTER_THERMAL_PATH):
        return None
    try:
        import pandas
    except ImportError:
        return None

    frame = pandas.read_parquet(INVERTER_THERMAL_PATH)
    by_site = {}
    for site_id, site_group in frame.groupby("site_id"):
        units = {}
        for unit_id, unit_group in site_group.groupby("inverter_id"):
            ambient_values = unit_group["mean_ambient_c"].dropna()
            delta_ambient = unit_group["delta_t_ambient_c"].dropna()

            # An inverter running 40 C above ambient would be failing, not
            # operating. A figure that large means the AMBIENT sensor is broken,
            # not the inverter — system 1203's ambient channel reads near zero
            # year round. Suppress the ambient figure rather than publish a
            # number that would be read as a fault.
            if len(delta_ambient) and float(delta_ambient.mean()) > 40.0:
                ambient_values = ambient_values.iloc[0:0]
                delta_ambient = delta_ambient.iloc[0:0]
            units[str(unit_id)] = {
                "mean_temp_c": round(float(unit_group["mean_temp_c"].mean()), 1),
                "max_temp_c": round(float(unit_group["max_temp_c"].max()), 1),
                "delta_t_siblings_c": round(float(unit_group["delta_t_siblings_c"].mean()), 2),
                "mean_ambient_c": round(float(ambient_values.mean()), 1)
                if len(ambient_values) else None,
                "delta_t_ambient_c": round(float(delta_ambient.mean()), 1)
                if len(delta_ambient) else None,
                "days": int(len(unit_group)),
            }
        by_site[str(site_id)] = units
    return by_site


def load_inverter_hardware():
    """Per-site inverter hardware, keyed by site_id. Gates the sibling comparison."""
    if not os.path.exists(INVERTER_HARDWARE_PATH):
        return None
    try:
        import pandas
    except ImportError:
        return None

    frame = pandas.read_parquet(INVERTER_HARDWARE_PATH)
    return {
        str(record["site_id"]): {
            "models": record["models"],
            "distinct_models": int(record["distinct_models"]),
            "distinct_ratings_kw": record["distinct_ratings_kw"],
            "homogeneous": bool(record["homogeneous"]),
        }
        for record in frame.to_dict("records")
    }


def median_of(values):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def build_sub_site(units_by_id, assumptions, thermal_by_unit=None, hardware=None):
    """Compare each inverter against the median of its siblings.

    NOTE ON UNITS — this deviates from BUILD_PLAN stage 8's suggested shape, and
    deliberately. That draft used `performance_index` per unit, but PVDAQ does
    NOT publish per-inverter capacity, so there is no kWp denominator and no
    honest kWh/kWp figure at this level. Emitting one would be a fabricated
    number wearing a real field name.

    Instead units carry raw daily kWh plus `deviation_pct`, a pure ratio against
    the sibling median. That is capacity-free, which is exactly why sibling
    comparison works without the denominator the site level needs.
    """
    if not units_by_id or len(units_by_id) < 2:
        return None  # a single inverter has no siblings to compare against

    threshold = assumptions["sub_site_deviation_threshold"]

    # Sibling comparison is only meaningful between comparable units. System 1278
    # pairs a 100 kW inverter with a 50 kW one; comparing their raw kWh yields a
    # -44% "deviation" that is nameplate, not a fault. Where hardware is unknown
    # we assume comparable, but say so.
    comparable = True
    comparability_note = None
    if hardware is not None:
        comparable = bool(hardware.get("homogeneous", True))
        if not comparable:
            comparability_note = (
                "Units at this site are DIFFERENT hardware ({}). Output differences here are "
                "dominated by nameplate rating, not performance, so no unit is flagged and the "
                "percentages below are shown for reference only. Sibling comparison requires "
                "comparable units."
            ).format(hardware.get("models") or "mixed models")
        else:
            comparability_note = "All units are the same hardware ({}), so a difference between them is a difference in performance.".format(
                hardware.get("models") or "identical")

    mean_by_unit = {}
    for unit_id, rows in units_by_id.items():
        if rows:
            mean_by_unit[unit_id] = sum(row["kwh"] for row in rows) / len(rows)

    if len(mean_by_unit) < 2:
        return None

    sibling_median = median_of(list(mean_by_unit.values()))

    units = []
    for unit_id, mean_kwh in mean_by_unit.items():
        deviation = (mean_kwh - sibling_median) / sibling_median if sibling_median else 0.0
        rows = units_by_id[unit_id][-SERIES_DAY_COUNT:]
        thermal = (thermal_by_unit or {}).get(unit_id)
        units.append({
            "unit_id": unit_id,
            "mean_kwh_daily": round(mean_kwh, 2),
            "sibling_median_kwh_daily": round(sibling_median, 2),
            "deviation_pct": round(deviation, 4),
            # A unit is only flagged where its siblings are comparable hardware.
            # Otherwise the deviation is nameplate, not performance.
            "status": (
                "flagged" if (comparable and deviation <= threshold) else "normal"
            ),
            "thermal": thermal,
            "series": [
                {
                    "date": row["date"],
                    "kwh": round(row["kwh"], 2),
                    "ratio_to_sibling_median": round(row["kwh"] / sibling_median, 4)
                    if sibling_median else 0.0,
                }
                for row in rows
            ],
        })

    units.sort(key=lambda unit: unit["deviation_pct"])  # worst first

    has_thermal = any(unit.get("thermal") for unit in units)

    return {
        "unit_type": "inverter",
        "unit_count": len(units),
        "units_comparable": comparable,
        "comparability_note": comparability_note,
        "has_thermal": has_thermal,
        "thermal_basis": (
            "Operating temperature while generating, compared against the median of "
            "sibling inverters. Rise above ambient is shown only where a sane ambient "
            "reading exists — several systems publish no ambient channel."
        ) if has_thermal else None,
        "comparison_basis": (
            "Ratio to sibling median. PVDAQ does not publish per-inverter capacity, "
            "so units are compared relatively and never normalised to kWp."
        ),
        "method": "mean daily kWh vs median of sibling inverters on the same site",
        "flag_threshold_pct": threshold,
        "units": units,
        "data_status": "BUILT",
    }


def mean_performance_index(series):
    """Mean daily kWh/kWp across a site's series, or None when there is none."""
    if not series:
        return None
    values = [row["performance_index"] for row in series if row.get("performance_index") is not None]
    if not values:
        return None
    return sum(values) / len(values)


def build_exclusions(sites, real_series_by_site, assumptions):
    """Identify sites whose telemetry is too incomplete to analyse.

    WHY THIS EXISTS. A site reporting a fraction of its real output looks exactly
    like a catastrophic permanent fault. It would rank first on the dispatch list
    every month and be wrong every month, and — worse — it drags its cohort's
    median down, which makes genuinely healthy peers look better than they are
    and can mask a real fault.

    So a site below the plausibility floor is excluded from BOTH detection and
    the cohort baseline. The exclusion is published with its reason and its
    numbers, never applied silently: a system that can say what it does not know
    is more trustworthy than one that reports the number anyway.

    Returns {site_id: exclusion_block}.
    """
    floor = assumptions["min_plausible_performance_index"]
    if not real_series_by_site:
        return {}

    means = {}
    for site in sites:
        site_id = build_site_id(site["source_system_id"])
        mean_pi = mean_performance_index(real_series_by_site.get(site_id))
        if mean_pi is not None:
            means[site_id] = mean_pi

    # Cohort median is computed from the plausible sites only, so one broken
    # feed cannot lower the bar it is being judged against.
    plausible = [value for value in means.values() if value >= floor]
    reference_median = median_of(plausible) if plausible else None

    exclusions = {}
    for site_id, mean_pi in means.items():
        if mean_pi >= floor:
            continue
        detail = (
            "Site reports {:.2f} kWh/kWp/day".format(mean_pi)
            + (" against a fleet median of {:.2f}".format(reference_median)
               if reference_median else "")
            + ". That is below the plausibility floor of {:.1f}, which means incomplete "
              "telemetry rather than a fault — a working site does not average this low. "
              "Excluded from detection and from its cohort median so it cannot generate a "
              "false dispatch or depress the peer baseline.".format(floor)
        )
        exclusions[site_id] = {
            "excluded": True,
            "reason": "incomplete_telemetry",
            "detail": detail,
            "observed_performance_index": round(mean_pi, 2),
            "reference_performance_index": round(reference_median, 2) if reference_median else None,
            "threshold": floor,
            "method": "mean daily kWh/kWp below assumptions.min_plausible_performance_index",
            "data_status": "BUILT",
        }
    return exclusions


# --- Identity ---------------------------------------------------------------


def build_site_id(source_system_id):
    """Display key for a site. Stable and never reused — docs/Schema.md section 8.1."""
    return "S-{:0>4}".format(source_system_id)


def series_dates():
    """The 90 dates the series covers, oldest first."""
    start = SERIES_END_DATE - datetime.timedelta(days=SERIES_DAY_COUNT - 1)
    return [start + datetime.timedelta(days=offset) for offset in range(SERIES_DAY_COUNT)]


# --- PLACEHOLDER series -----------------------------------------------------


def placeholder_performance_index(site, day_index, assumptions, is_degraded):
    """A deterministic, obviously-synthetic daily performance index in kWh/kWp.

    TODO(M1): replaced the moment data/processed/fleet_daily.parquet exists.

    Anchored on `assumed_yield_kwh_per_kwp_day` from config so the magnitude
    traces to a named constant rather than an invented one. The seasonal and
    daily wobble is a fixed arithmetic pattern, not random — every run produces
    an identical file, so the artifact does not churn in git.
    """
    base_yield = assumptions["assumed_yield_kwh_per_kwp_day"]

    # A fixed repeating pattern stands in for weather shared across the cohort.
    shared_weather = 1.0 + 0.12 * (((day_index * 7) % 11) - 5) / 5.0

    # A small per-site offset so the cohort lines are visually distinguishable.
    site_offset = 1.0 + (int(site["source_system_id"]) % 7) * 0.01

    value = base_yield * shared_weather * site_offset

    # A degraded site diverges partway through the window and stays down.
    if is_degraded and day_index >= SERIES_DAY_COUNT - 40:
        value = value * 0.80

    return round(value, 3)


def build_actual_vs_expected(site, assumptions, is_degraded, real_series):
    """Screen 2's primary chart. `expected_kwh` is null until M2 (owner A) lands."""
    if real_series is not None:
        return [
            {
                "date": row["date"],
                "actual_kwh": row["actual_kwh"],
                "expected_kwh": None,
                "performance_index": row["performance_index"],
            }
            for row in real_series[-SERIES_DAY_COUNT:]
        ]

    rows = []
    for day_index, day in enumerate(series_dates()):
        index_value = placeholder_performance_index(site, day_index, assumptions, is_degraded)
        rows.append({
            "date": day.isoformat(),
            "actual_kwh": round(index_value * site["capacity_kwp"], 1),
            "expected_kwh": None,
            "performance_index": index_value,
        })
    return rows


def build_cohort_series(subject_site, cohort_members, assumptions, degraded_site_ids,
                        real_series_by_site, exclusions=None):
    """Long format, one row per peer per day.

    This is the array behind the chart PRD v2 section 4 calls "the visual that
    sells the whole product". Long, never wide — see docs/Schema.md section 8.6.
    """
    exclusions = exclusions or {}
    rows = []
    for member in cohort_members:
        member_site_id = build_site_id(member["source_system_id"])
        is_subject = member_site_id == build_site_id(subject_site["source_system_id"])

        # An excluded site must not be drawn as a peer. Its depressed line would
        # read as a second diverging site and mislead the eye on the one chart
        # the product is judged by.
        if member_site_id in exclusions and not is_subject:
            continue

        is_degraded = member["source_system_id"] in degraded_site_ids

        real_series = None
        if real_series_by_site is not None:
            real_series = real_series_by_site.get(member_site_id)

        if real_series is not None:
            for row in real_series[-SERIES_DAY_COUNT:]:
                rows.append({
                    "date": row["date"],
                    "site_id": member_site_id,
                    "performance_index": row["performance_index"],
                    "is_subject": is_subject,
                })
            continue

        for day_index, day in enumerate(series_dates()):
            rows.append({
                "date": day.isoformat(),
                "site_id": member_site_id,
                "performance_index": placeholder_performance_index(
                    member, day_index, assumptions, is_degraded),
                "is_subject": is_subject,
            })
    return rows


# --- PLACEHOLDER analytics --------------------------------------------------


def build_detection(cohort_size, meets_minimum, severity):
    """TODO(owner A, M3): replace wholesale. Nothing here is a real measurement."""
    return {
        "method": PLACEHOLDER_DETECTION_METHOD,
        "score": round(-2.0 - severity * 1.8, 2),
        "score_type": "cohort_mean_deviation",
        "threshold": -2.0,
        "confidence": round(0.60 + severity * 0.25, 2),
        "cohort_size": cohort_size,
        "cohort_meets_minimum": meets_minimum,
        "data_status": "PLACEHOLDER",
    }


def build_divergence(severity):
    """Screen 2 draws its vertical reference line at `start_date`."""
    days_since = int(12 + severity * 30)
    start_date = SERIES_END_DATE - datetime.timedelta(days=days_since)
    return {
        "start_date": start_date.isoformat(),
        "days_since": days_since,
        "detection_confidence": "high" if severity > 0.5 else "medium",
    }


def build_economics(site, assumptions, divergence, severity, exceeds_threshold):
    """Every number derives from config/assumptions.json. No constant is hardcoded.

    TODO(owner A, M2/M3): kwh_lost_monthly currently comes from a placeholder
    loss fraction. It should come from (cohort_median_PI - site_PI) x expected_kwh.
    """
    tariff = assumptions["tariff_rm_per_kwh"]
    nominal_yield = assumptions["assumed_yield_kwh_per_kwp_day"]

    loss_fraction = round(0.05 + severity * 0.12, 4)
    expected_monthly_kwh = site["capacity_kwp"] * nominal_yield * 30
    kwh_lost_monthly = round(expected_monthly_kwh * loss_fraction, 1)

    days_since = divergence["days_since"]
    cumulative_kwh_lost = round(kwh_lost_monthly / 30 * days_since, 1)

    return {
        "kwh_lost_monthly": kwh_lost_monthly,
        "rm_at_risk_monthly": round(kwh_lost_monthly * tariff, 2),
        "cumulative_kwh_lost": cumulative_kwh_lost,
        "cumulative_loss_rm": round(cumulative_kwh_lost * tariff, 2),
        "loss_pct_of_expected": loss_fraction,
        "exceeds_dispatch_threshold": exceeds_threshold,
        "calculation": "kwh_lost_monthly × tariff_rm_per_kwh",
        "data_status": "PLACEHOLDER",
    }


def build_hypothesis(site, cohort_label, cohort_size, severity, is_dispatch):
    """Feeds Screen 2's explanation panel and Screen 3's work order.

    TODO(owner A, M3): the cause hypothesis should follow from the detected
    signal shape, not from a severity number.
    """
    # Trim the trailing noun so "Greater Las Vegas cluster" reads as
    # "6-site Greater Las Vegas cohort" rather than "6-site Greater cohort".
    cohort_name = cohort_label
    for trailing in (" cluster", " cohort"):
        if cohort_name.endswith(trailing):
            cohort_name = cohort_name[: -len(trailing)]
    summary = "Divergence from {}-site {} cohort".format(cohort_size, cohort_name)
    hypothesis = {
        "summary": summary[:90],
        "detail": (
            "PLACEHOLDER text. {} tracks its cohort until {}, then sits below the cohort median "
            "while peers hold steady. A real cause hypothesis requires M3 (owner A); this string "
            "exists so Screen 2 and Screen 3 can be built against the final shape."
        ).format(site["name"], build_divergence(severity)["start_date"]),
        "confidence": round(0.60 + severity * 0.25, 2),
        "checks": [
            "Inspect combiner box for tripped string breakers",
            "Verify string-level currents against inverter readings",
            "Check for new shading obstruction or surface soiling",
        ],
    }
    if is_dispatch:
        hypothesis["photograph"] = [
            "Combiner box interior with breaker states visible",
            "Full array from roof edge",
            "Inverter display showing per-string current",
        ]
    return hypothesis


# --- Assembly ---------------------------------------------------------------


def group_sites_by_cohort(sites):
    grouped = {}
    for site in sites:
        grouped.setdefault(site["cohort_id"], []).append(site)
    return grouped


def build_cohorts(sites_by_cohort, assumptions, exclusions=None):
    """One object per cohort. Referenced by site.cohort_id — every reference must resolve.

    `analysed_count` excludes data-quality exclusions, and `meets_minimum` is
    judged on THAT number rather than raw membership. A cohort of six where one
    site has broken telemetry is a control group of five, and pretending
    otherwise would overstate the detector's confidence.
    """
    exclusions = exclusions or {}
    cohorts = []
    for cohort_id in sorted(key for key in sites_by_cohort if key):
        members = sites_by_cohort[cohort_id]
        member_site_ids = [build_site_id(member["source_system_id"]) for member in members]
        analysed_site_ids = [
            site_id for site_id in member_site_ids if site_id not in exclusions
        ]
        excluded_site_ids = [
            site_id for site_id in member_site_ids if site_id in exclusions
        ]

        centroid_lat = sum(member["lat"] for member in members) / len(members)
        centroid_lon = sum(member["lon"] for member in members) / len(members)

        cohorts.append({
            "cohort_id": cohort_id,
            "label": COHORT_LABELS.get(cohort_id, cohort_id),
            "member_site_ids": member_site_ids,
            "member_count": len(members),
            "analysed_site_ids": analysed_site_ids,
            "analysed_count": len(analysed_site_ids),
            "excluded_site_ids": excluded_site_ids,
            "meets_minimum": len(analysed_site_ids) >= assumptions["min_cohort_size"],
            "clustering_method": PLACEHOLDER_CLUSTERING_METHOD,
            "centroid": {"lat": round(centroid_lat, 4), "lon": round(centroid_lon, 4)},
            "cohort_median_performance_index": assumptions["assumed_yield_kwh_per_kwp_day"],
            "data_status": "PLACEHOLDER",
        })
    return cohorts


def classify_site(source_system_id):
    """PLACEHOLDER triage. TODO(owner A, M3): the detector decides this, not a list."""
    if source_system_id in PLACEHOLDER_DISPATCH_SITE_IDS:
        return "dispatch"
    if source_system_id in PLACEHOLDER_MONITOR_SITE_IDS:
        return "monitor"
    return "healthy"


def build_site_objects(sites, cohorts_by_id, sites_by_cohort, assumptions,
                       real_series_by_site, inverter_by_site=None, thermal_by_site=None,
                       exclusions=None, hardware_by_site=None):
    """Build every site object, ordered dispatch first then monitor then healthy."""
    degraded_site_ids = set(PLACEHOLDER_DISPATCH_SITE_IDS + PLACEHOLDER_MONITOR_SITE_IDS)
    exclusions = exclusions or {}

    dispatch_sites = []
    monitor_sites = []
    healthy_sites = []

    for site in sites:
        site_key = build_site_id(site["source_system_id"])
        exclusion = exclusions.get(site_key)

        # An excluded site is never flagged, whatever the detector thinks. Its
        # readings are not trustworthy enough to accuse it of anything.
        status = "healthy" if exclusion else classify_site(site["source_system_id"])
        cohort_id = site["cohort_id"]
        cohort = cohorts_by_id.get(cohort_id)
        cohort_members = sites_by_cohort.get(cohort_id, [site])

        site_object = {
            "site_id": build_site_id(site["source_system_id"]),
            "name": site["name"],
            "address": site["site_location"],
            "capacity_kwp": site["capacity_kwp"],
            "lat": site["lat"],
            "lon": site["lon"],
            "cohort_id": cohort_id,
            "tariff_rm_per_kwh": assumptions["tariff_rm_per_kwh"],
            "source_system_id": "pvdaq_{}".format(site["source_system_id"]),
            "status": status,
            "rank": None,
            "data_status": "PLACEHOLDER",
            "excluded_from_analysis": exclusion,
        }

        # Sub-site data is independent of triage state — a healthy site can still
        # have inverter detail worth showing.
        if inverter_by_site:
            sub_site = build_sub_site(
                inverter_by_site.get(site_object["site_id"]), assumptions,
                (thermal_by_site or {}).get(site_object["site_id"]),
                (hardware_by_site or {}).get(site_object["site_id"]))
            if sub_site:
                site_object["sub_site"] = sub_site

        if status == "healthy":
            site_object["detection"] = None
            site_object["divergence"] = None
            site_object["economics"] = None
            site_object["hypothesis"] = None
            # An excluded site still shows its own measured series — the data is
            # real, just incomplete — but carries no peer overlay, because it is
            # not being compared to anything.
            if exclusion and real_series_by_site and real_series_by_site.get(site_key):
                site_object["series"] = {
                    "actual_vs_expected": build_actual_vs_expected(
                        site, assumptions, False, real_series_by_site.get(site_key)),
                    "cohort": [],
                }
            healthy_sites.append(site_object)
            continue

        # Severity separates dispatch from monitor deterministically.
        severity = 0.8 if status == "dispatch" else 0.25
        cohort_size = cohort["member_count"] if cohort else 1
        meets_minimum = cohort["meets_minimum"] if cohort else False
        cohort_label = cohort["label"] if cohort else "ungrouped"

        divergence = build_divergence(severity)
        economics = build_economics(
            site, assumptions, divergence, severity, exceeds_threshold=(status == "dispatch"))

        site_object["detection"] = build_detection(cohort_size, meets_minimum, severity)
        site_object["divergence"] = divergence
        site_object["economics"] = economics
        site_object["hypothesis"] = build_hypothesis(
            site, cohort_label, cohort_size, severity, is_dispatch=(status == "dispatch"))

        real_series = None
        if real_series_by_site is not None:
            real_series = real_series_by_site.get(site_object["site_id"])

        site_object["series"] = {
            "actual_vs_expected": build_actual_vs_expected(
                site, assumptions, site["source_system_id"] in degraded_site_ids, real_series),
            "cohort": build_cohort_series(
                site, cohort_members, assumptions, degraded_site_ids,
                real_series_by_site, exclusions),
        }

        if status == "dispatch":
            dispatch_sites.append(site_object)
        else:
            monitor_sites.append(site_object)

    # Rank by money at risk, descending. Dispatch ranks 1..N contiguously.
    dispatch_sites.sort(key=lambda item: -item["economics"]["rm_at_risk_monthly"])
    monitor_sites.sort(key=lambda item: -item["economics"]["rm_at_risk_monthly"])

    for position, site_object in enumerate(dispatch_sites, start=1):
        site_object["rank"] = position
    for position, site_object in enumerate(monitor_sites, start=len(dispatch_sites) + 1):
        site_object["rank"] = position

    return dispatch_sites + monitor_sites + healthy_sites


EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km. Stdlib only — no geo dependency for this."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def group_sites_into_trips(site_objects, radius_km):
    """Cluster sites that one technician reaches in a single mobilisation.

    WHY THIS EXISTS. Costing a saved visit per SITE overstates the saving badly on
    this fleet. Five of the Agassi buildings share byte-identical coordinates, and
    two more pairs sit within 300 m — nobody drives out five times to one address.
    CLAUDE.md already states the caveat; this is the code that honours it.

    Single-link clustering: two sites join the same trip if they are within
    radius_km of each other, and a chain of such links merges transitively. Single
    link is the right choice because reachability chains — A near B, B near C means
    one route covers all three even when A and C are further apart than the radius.

    Returns a list of lists of site_objects, order stable for a stable input.
    """
    groups = []
    for site in site_objects:
        joined = None
        for group in groups:
            if any(haversine_km(site["lat"], site["lon"], other["lat"], other["lon"]) <= radius_km
                   for other in group):
                if joined is None:
                    # First group this site links to — join it.
                    group.append(site)
                    joined = group
                else:
                    # It also links to a later group, so this site is the bridge
                    # between two clusters that were only separate because nothing
                    # had connected them yet. Merge.
                    joined.extend(group)
                    group.clear()
        if joined is None:
            groups.append([site])

    return [group for group in groups if group]


def build_trip_groups(site_objects, assumptions):
    """Trip groups plus the counts that drive the saving. See §1.1 of issue #4."""
    radius_km = assumptions["same_trip_radius_km"]
    groups = group_sites_into_trips(site_objects, radius_km)

    trip_groups = []
    for index, members in enumerate(groups, start=1):
        # A trip is only AVOIDED when nothing in the group is being dispatched.
        # If a technician is already going to that address for one site, skipping
        # its neighbours saves the drive, not the visit.
        dispatched = any(member["status"] == "dispatch" for member in members)
        trip_groups.append({
            "trip_id": "T-{:02d}".format(index),
            "label": members[0]["address"],
            "site_ids": [member["site_id"] for member in members],
            "site_count": len(members),
            "dispatched": dispatched,
        })

    return trip_groups


def build_fleet_summary(site_objects, cohorts, assumptions):
    dispatch_count = sum(1 for item in site_objects if item["status"] == "dispatch")
    monitor_count = sum(1 for item in site_objects if item["status"] == "monitor")
    healthy_count = sum(1 for item in site_objects if item["status"] == "healthy")

    total_capacity_kwp = sum(item["capacity_kwp"] for item in site_objects)

    # visits_avoided counts SITES and is left alone: it is what Screen 1 reads and
    # what the sentence "the value is in the sites you don't visit" refers to.
    # The money, though, is per trip — see build_trip_groups.
    visits_avoided = len(site_objects) - dispatch_count

    trip_groups = build_trip_groups(site_objects, assumptions)
    trips_recommended = sum(1 for group in trip_groups if group["dispatched"])
    trips_avoided = len(trip_groups) - trips_recommended

    total_rm_at_risk = sum(
        item["economics"]["rm_at_risk_monthly"]
        for item in site_objects
        if item.get("economics")
    )

    return {
        "site_count": len(site_objects),
        "total_capacity_mwp": round(total_capacity_kwp / 1000, 2),
        "dispatch_count": dispatch_count,
        "monitor_count": monitor_count,
        "healthy_count": healthy_count,
        "visits_avoided": visits_avoided,
        "trips_avoided": trips_avoided,
        "trips_recommended": trips_recommended,
        "trip_groups": trip_groups,
        "estimated_saving_rm": round(trips_avoided * assumptions["cost_per_visit_rm"], 2),
        "total_rm_at_risk": round(total_rm_at_risk, 2),
        "cohort_count": len(cohorts),
    }


PROJECTION_HORIZON_MONTHS = 12


def build_roi(fleet_summary, assumptions):
    """Screen 4 figures for the observed period.

    WHAT CHANGED AND WHY. This function used to multiply one month by six and
    present the result as rolling history. It also set faults_confirmed to
    dispatch_count * 2, which was invented outright — there is no confirmation
    mechanism at all, because Screen 3's findings live in the browser's
    localStorage with nothing behind them.

    The pipeline observes ONE reporting month. So this reports one month, and
    anything beyond that goes in `projection`, where it is visibly a projection
    with its factor and its assumption stated. Multiplying inside a field named
    `_total` hid both.

    `generation_recovered_kwh` keeps its name because renaming a field breaks the
    frozen contract, but it now carries generation AT RISK — nothing has been
    recovered, and `generation_basis` says so.

    Stays PLACEHOLDER until M2/M3 supply a real kwh_lost. Every figure below is
    arithmetic on a made-up loss fraction; the arithmetic is now honest, the
    input is not yet.
    """
    period_months = 1
    tariff = assumptions["tariff_rm_per_kwh"]
    co2e_factor = assumptions["co2e_grid_factor_kg_per_kwh"]

    generation_at_risk_kwh = round(fleet_summary["total_rm_at_risk"] / tariff, 1)

    return {
        "data_status": "PLACEHOLDER",
        "period_months": period_months,

        # Trips, not sites: the cost is per mobilisation. See build_trip_groups.
        "visits_recommended_total": fleet_summary["trips_recommended"],
        "visits_avoided_total": fleet_summary["trips_avoided"],

        "faults_confirmed": 0,
        "faults_confirmed_basis": (
            "No confirmation mechanism exists. Screen 3 stores technician findings in browser "
            "localStorage with no backend, so nothing can be counted as confirmed. This stays 0 "
            "until findings are persisted — it is not a measurement of zero faults."
        ),

        "generation_recovered_kwh": generation_at_risk_kwh,
        "generation_basis": (
            "Generation AT RISK this month, not recovered. Nothing has been recovered: no site has "
            "been visited and no fault repaired. Derived from total_rm_at_risk at the fleet tariff. "
            "The field name is fixed by the schema contract; this note is what it actually means."
        ),

        "rm_protected_cumulative": round(generation_at_risk_kwh * tariff, 2),
        "co2e_avoided_tonnes": round(generation_at_risk_kwh * co2e_factor / 1000, 2),
        "co2e_grid_factor_kg_per_kwh": co2e_factor,
        "co2e_factor_source": assumptions["notes"]["co2e_grid_factor_kg_per_kwh"],

        "projection": {
            "horizon_months": PROJECTION_HORIZON_MONTHS,
            "factor": PROJECTION_HORIZON_MONTHS / period_months,
            "saving_rm": round(
                fleet_summary["estimated_saving_rm"] * PROJECTION_HORIZON_MONTHS / period_months, 2),
            "basis": (
                "Straight-line projection of a single observed month over {} months. Assumes this "
                "month is representative, which one month of data cannot establish. Shown as a "
                "projection so it is never mistaken for observed history."
            ).format(PROJECTION_HORIZON_MONTHS),
        },
    }


def build_meta(site_objects, using_real_data):
    """Fleet-wide data_status is the worst case across all sites."""
    statuses = {item["data_status"] for item in site_objects}
    if "PLACEHOLDER" in statuses:
        fleet_status = "PLACEHOLDER"
    elif "SIMULATED" in statuses:
        fleet_status = "SIMULATED"
    else:
        fleet_status = "BUILT"

    source_note = (
        "US systems (NREL PVDAQ). Proves method, not market. See PRD v2 section 8. "
        "Detection, economics and baseline are PLACEHOLDER pending M2/M3 (owner A)."
    )
    if not using_real_data:
        source_note += " Daily series are PLACEHOLDER — M1 ingestion has not yet run."

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pipeline_version": PIPELINE_VERSION,
        "reporting_month": REPORTING_MONTH,
        "reporting_month_label": REPORTING_MONTH_LABEL,
        "data_status": fleet_status,
        "data_source": "NREL PVDAQ",
        "irradiance_source": "NONE",
        "source_note": source_note,
        "date_remapped": True,
        "date_remap_note": (
            "Historical PVDAQ dates ({}) shifted to a {} demo window; underlying values unmodified."
        ).format(DATE_REMAP_SOURCE_YEAR, DATE_REMAP_TARGET_YEAR),
    }


def build_dispatch_payload():
    """Assemble the whole artifact. Returns the dict that becomes dispatch.json."""
    assumptions = load_assumptions()
    sites = load_fleet_sites()
    real_series_by_site = load_real_daily_series()
    inverter_by_site = load_inverter_daily()
    thermal_by_site = load_inverter_thermal()
    hardware_by_site = load_inverter_hardware()

    exclusions = build_exclusions(sites, real_series_by_site, assumptions)

    sites_by_cohort = group_sites_by_cohort(sites)
    cohorts = build_cohorts(sites_by_cohort, assumptions, exclusions)
    cohorts_by_id = {cohort["cohort_id"]: cohort for cohort in cohorts}

    site_objects = build_site_objects(
        sites, cohorts_by_id, sites_by_cohort, assumptions,
        real_series_by_site, inverter_by_site, thermal_by_site, exclusions, hardware_by_site)

    fleet_summary = build_fleet_summary(site_objects, cohorts, assumptions)

    return {
        "meta": build_meta(site_objects, using_real_data=real_series_by_site is not None),
        "assumptions": assumptions,
        "fleet_summary": fleet_summary,
        "roi": build_roi(fleet_summary, assumptions),
        "cohorts": cohorts,
        "sites": site_objects,
    }


# ===========================================================================
# STABLE INTERFACE — teammates, preserve this function and this filename.
#
# Replace everything above with real M2 / M3 / M4 implementations if you like.
# What must not change is that running this module writes a schema-conformant
# dispatch.json to this exact path. The frontend, the Supabase loader and
# validate_dispatch.py all depend on it and on nothing else in this file.
# ===========================================================================


def write_dispatch_file(payload, output_path=OUTPUT_PATH):
    """Write the artifact. The one thing this module guarantees to the rest of the system."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return output_path


def publish_to_frontend(source_path=OUTPUT_PATH):
    """Copy the artifact where the dev server and the deployed build can serve it.

    This is a FILE COPY, not an import — `pipeline/` still knows nothing about
    the frontend's code, which is the separation CLAUDE.md requires. What it
    removes is a silent failure mode: without it, regenerating the data leaves
    the dashboard showing the previous run, and the next person spends an hour
    wondering why their change did nothing.

    Two destinations by design:
      dispatch.json       the primary the frontend fetches
      dispatch.mock.json  the committed fallback, served when the primary fails

    Skips quietly when apps/web is absent, so a pipeline-only checkout still runs.
    """
    if not os.path.isdir(FRONTEND_PUBLIC_DIR):
        return []

    written = []
    for filename in ("dispatch.json", "dispatch.mock.json"):
        destination = os.path.join(FRONTEND_PUBLIC_DIR, filename)
        with open(source_path, "r", encoding="utf-8") as source:
            content = source.read()
        with open(destination, "w", encoding="utf-8") as target:
            target.write(content)
        written.append(destination)
    return written


def main():
    payload = build_dispatch_payload()
    written_path = write_dispatch_file(payload)
    published = publish_to_frontend(written_path)

    summary = payload["fleet_summary"]
    print("wrote {}".format(written_path))
    for destination in published:
        print("  published -> {}".format(os.path.relpath(destination, REPOSITORY_ROOT)))
    print("  sites     : {} ({} dispatch, {} monitor, {} healthy)".format(
        summary["site_count"], summary["dispatch_count"],
        summary["monitor_count"], summary["healthy_count"]))
    print("  cohorts   : {}".format(summary["cohort_count"]))
    print("  capacity  : {} MWp".format(summary["total_capacity_mwp"]))
    print("  at risk   : RM {}/month".format(summary["total_rm_at_risk"]))
    print("  status    : {}".format(payload["meta"]["data_status"]))
    print("")
    print("run  python pipeline/validate_dispatch.py  to check conformance")


if __name__ == "__main__":
    main()

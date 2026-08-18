"""Assert that pipeline/output/dispatch.json conforms to docs/Schema.md.

Run:
    python pipeline/validate_dispatch.py
    python pipeline/validate_dispatch.py path/to/other.json

Exits non-zero on any failure. Implements every rule in docs/Schema.md section 10.

Run this before handing anything over. Rules 8 and 9 exist because Screen 2
fails silently without them — the chart renders empty rather than erroring, which
is the worst possible failure mode during a demo. Rule 15 is what stops
scaffolding shipping to a judge.
"""

import json
import os
import sys

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(REPOSITORY_ROOT, "pipeline", "output", "dispatch.json")

REQUIRED_TOP_LEVEL_KEYS = ["meta", "assumptions", "fleet_summary", "roi", "cohorts", "sites"]
EXPECTED_MAJOR_VERSION = "1"

VALID_DATA_STATUS = {"BUILT", "SIMULATED", "PLACEHOLDER"}
VALID_SITE_STATUS = {"dispatch", "monitor", "healthy"}
VALID_SCORE_TYPES = {"z_score", "isolation_forest", "cohort_mean_deviation", "other"}

FLAGGED_STATUSES = {"dispatch", "monitor"}
DETECTION_BLOCKS = ["detection", "divergence", "economics", "hypothesis"]


class Report:
    """Collects failures and placeholder sightings across every rule."""

    def __init__(self):
        self.failures = []
        self.placeholders = []

    def fail(self, rule_number, message):
        self.failures.append("rule {:>2}: {}".format(rule_number, message))

    def note_placeholder(self, location):
        self.placeholders.append(location)

    @property
    def passed(self):
        return not self.failures


# --- Rules ------------------------------------------------------------------


def check_top_level_keys(payload, report):
    """Rule 1 — all six top-level keys present."""
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in payload:
            report.fail(1, "missing top-level key {!r}".format(key))

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key == "sites":
            continue  # sites may be empty; the others may not
        value = payload.get(key)
        if value is None or (isinstance(value, (list, dict)) and len(value) == 0):
            report.fail(1, "top-level key {!r} is present but empty".format(key))


def check_schema_version(payload, report):
    """Rule 2 — schema_version matches the frontend's expected major version."""
    version = payload.get("meta", {}).get("schema_version")
    if not version:
        report.fail(2, "meta.schema_version is missing")
        return
    major = str(version).split(".")[0]
    if major != EXPECTED_MAJOR_VERSION:
        report.fail(2, "schema_version {!r} has major version {!r}, frontend expects {!r}".format(
            version, major, EXPECTED_MAJOR_VERSION))


def check_required_fields(payload, report):
    """Required keys must be PRESENT, per docs/Schema.md sections 3, 5, 6 and 8.1.

    Some may legitimately hold null (`cohort_id`, `rank`) — absence is the
    failure, not nullness. This catches the case where a site loses
    `capacity_kwp`: without it there is no kWh/kWp denominator, so the site
    silently drops off every chart instead of erroring.
    """
    required_by_block = {
        "meta": [
            "schema_version", "generated_at", "pipeline_version", "reporting_month",
            "reporting_month_label", "data_status", "data_source", "irradiance_source",
            "source_note", "date_remapped",
        ],
        "fleet_summary": [
            "site_count", "total_capacity_mwp", "dispatch_count", "monitor_count",
            "healthy_count", "visits_avoided", "estimated_saving_rm", "total_rm_at_risk",
            "cohort_count", "trips_avoided", "trips_recommended", "trip_groups",
        ],
        "roi": [
            "data_status", "period_months", "visits_recommended_total", "visits_avoided_total",
            "faults_confirmed", "generation_recovered_kwh", "rm_protected_cumulative",
        ],
    }

    for block_name, required_keys in required_by_block.items():
        block = payload.get(block_name)
        if not isinstance(block, dict):
            continue
        for key in required_keys:
            if key not in block:
                report.fail(1, "{}.{} is missing".format(block_name, key))

    site_required_keys = [
        "site_id", "name", "address", "capacity_kwp", "lat", "lon", "cohort_id",
        "tariff_rm_per_kwh", "source_system_id", "status", "rank", "data_status",
    ]
    for index, site in enumerate(payload.get("sites", [])):
        label = site.get("site_id") or "sites[{}]".format(index)
        for key in site_required_keys:
            if key not in site:
                report.fail(1, "site {} is missing required field {!r}".format(label, key))

        if site.get("status") not in VALID_SITE_STATUS:
            report.fail(13, "site {} has status {!r}, not one of {}".format(
                label, site.get("status"), sorted(VALID_SITE_STATUS)))

    if payload.get("meta", {}).get("date_remapped") and not payload["meta"].get("date_remap_note"):
        report.fail(1, "meta.date_remapped is true but date_remap_note is missing")


def check_site_ids_unique(payload, report):
    """Rule 3 — every site_id unique and non-empty."""
    seen = set()
    for index, site in enumerate(payload.get("sites", [])):
        site_id = site.get("site_id")
        if not site_id:
            report.fail(3, "sites[{}] has an empty or missing site_id".format(index))
            continue
        if site_id in seen:
            report.fail(3, "duplicate site_id {!r}".format(site_id))
        seen.add(site_id)


def check_status_counts(payload, report):
    """Rule 4 — dispatch + monitor + healthy == site_count."""
    summary = payload.get("fleet_summary", {})
    sites = payload.get("sites", [])

    parts = ["dispatch_count", "monitor_count", "healthy_count"]
    total = sum(summary.get(part, 0) for part in parts)
    site_count = summary.get("site_count")

    if site_count != len(sites):
        report.fail(4, "fleet_summary.site_count is {} but sites[] has {} entries".format(
            site_count, len(sites)))

    if total != site_count:
        report.fail(4, "{} + {} + {} = {} does not equal site_count {}".format(
            summary.get("dispatch_count"), summary.get("monitor_count"),
            summary.get("healthy_count"), total, site_count))

    for status in VALID_SITE_STATUS:
        declared = summary.get("{}_count".format(status))
        actual = sum(1 for site in sites if site.get("status") == status)
        if declared != actual:
            report.fail(4, "fleet_summary.{}_count is {} but {} sites carry that status".format(
                status, declared, actual))


def check_cohort_references(payload, report):
    """Rule 5 — every site.cohort_id resolves, or is null."""
    known_cohort_ids = {cohort.get("cohort_id") for cohort in payload.get("cohorts", [])}
    for site in payload.get("sites", []):
        cohort_id = site.get("cohort_id")
        if cohort_id is None:
            continue
        if cohort_id not in known_cohort_ids:
            report.fail(5, "site {} references unknown cohort_id {!r}".format(
                site.get("site_id"), cohort_id))


def check_cohort_membership(payload, report):
    """Rule 6 — every cohorts[].member_site_ids entry exists in sites."""
    known_site_ids = {site.get("site_id") for site in payload.get("sites", [])}
    for cohort in payload.get("cohorts", []):
        members = cohort.get("member_site_ids", [])
        for member_site_id in members:
            if member_site_id not in known_site_ids:
                report.fail(6, "cohort {} lists unknown member {!r}".format(
                    cohort.get("cohort_id"), member_site_id))
        if cohort.get("member_count") != len(members):
            report.fail(6, "cohort {} member_count is {} but lists {} members".format(
                cohort.get("cohort_id"), cohort.get("member_count"), len(members)))


def check_flagged_sites_have_blocks(payload, report):
    """Rule 7 — dispatch and monitor sites carry all four analysis blocks."""
    for site in payload.get("sites", []):
        if site.get("status") not in FLAGGED_STATUSES:
            continue
        for block_name in DETECTION_BLOCKS:
            if not site.get(block_name):
                report.fail(7, "site {} is {!r} but {} is missing or null".format(
                    site.get("site_id"), site.get("status"), block_name))


def check_cohort_series_present(payload, report):
    """Rule 8 — every dispatch and monitor site has a non-empty series.cohort."""
    for site in payload.get("sites", []):
        if site.get("status") not in FLAGGED_STATUSES:
            continue
        cohort_rows = (site.get("series") or {}).get("cohort") or []
        if not cohort_rows:
            report.fail(8, "site {} is {!r} but series.cohort is empty — Screen 2 would render blank".format(
                site.get("site_id"), site.get("status")))


def check_exactly_one_subject(payload, report):
    """Rule 9 — exactly one distinct site_id per series.cohort has is_subject true."""
    for site in payload.get("sites", []):
        cohort_rows = (site.get("series") or {}).get("cohort") or []
        if not cohort_rows:
            continue
        subject_ids = {row.get("site_id") for row in cohort_rows if row.get("is_subject")}
        if len(subject_ids) != 1:
            report.fail(9, "site {} has {} distinct subject site_ids in series.cohort, expected exactly 1".format(
                site.get("site_id"), len(subject_ids)))
        elif subject_ids != {site.get("site_id")}:
            report.fail(9, "site {} marks {!r} as the subject of its own cohort series".format(
                site.get("site_id"), next(iter(subject_ids))))


def check_performance_index_numeric(payload, report):
    """Rule 10 — performance_index present and numeric on every series.cohort row."""
    for site in payload.get("sites", []):
        cohort_rows = (site.get("series") or {}).get("cohort") or []
        for row_index, row in enumerate(cohort_rows):
            value = row.get("performance_index")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                report.fail(10, "site {} series.cohort[{}] has non-numeric performance_index {!r}".format(
                    site.get("site_id"), row_index, value))
                break  # one report per site is enough to act on


def check_threshold_agrees_with_status(payload, report):
    """Rule 11 — economics.exceeds_dispatch_threshold agrees with status == dispatch."""
    for site in payload.get("sites", []):
        economics = site.get("economics")
        if not economics:
            continue
        exceeds = economics.get("exceeds_dispatch_threshold")
        is_dispatch = site.get("status") == "dispatch"
        if bool(exceeds) != is_dispatch:
            report.fail(11, "site {} has status {!r} but exceeds_dispatch_threshold is {!r}".format(
                site.get("site_id"), site.get("status"), exceeds))


def check_dispatch_ranks_contiguous(payload, report):
    """Rule 12 — rank values within the dispatch group are contiguous from 1."""
    dispatch_ranks = [
        site.get("rank")
        for site in payload.get("sites", [])
        if site.get("status") == "dispatch"
    ]
    if not dispatch_ranks:
        return

    # Check for nulls BEFORE sorting. sorted() raises TypeError comparing None
    # against an int, which would crash the validator on exactly the malformed
    # input it exists to report on.
    if any(rank is None for rank in dispatch_ranks):
        report.fail(12, "a dispatch site has a null rank")
        return

    dispatch_ranks = sorted(dispatch_ranks)
    expected = list(range(1, len(dispatch_ranks) + 1))
    if dispatch_ranks != expected:
        report.fail(12, "dispatch ranks are {}, expected {}".format(dispatch_ranks, expected))

    for site in payload.get("sites", []):
        if site.get("status") == "healthy" and site.get("rank") is not None:
            report.fail(12, "healthy site {} has a non-null rank {!r}".format(
                site.get("site_id"), site.get("rank")))


def check_exclusions(payload, report):
    """A data-quality exclusion must be applied consistently everywhere.

    Half-applying it is worse than not applying it: a site excluded from the
    dispatch list but still drawn as a cohort peer would silently depress the
    baseline its neighbours are judged against.
    """
    excluded_site_ids = set()
    for site in payload.get("sites", []):
        exclusion = site.get("excluded_from_analysis")
        if not exclusion:
            continue
        site_id = site.get("site_id")
        excluded_site_ids.add(site_id)

        if site.get("status") != "healthy":
            report.fail(7, "site {} is excluded from analysis but has status {!r} — an "
                           "untrusted reading must never produce a flag".format(
                               site_id, site.get("status")))
        if site.get("rank") is not None:
            report.fail(12, "excluded site {} has a non-null rank".format(site_id))
        for field in ("reason", "detail", "observed_performance_index", "method"):
            if field not in exclusion:
                report.fail(1, "site {} exclusion is missing {!r} — an exclusion without a "
                               "stated reason is a silent one".format(site_id, field))

    # An excluded site must not appear as a peer in anyone else's overlay.
    for site in payload.get("sites", []):
        if site.get("site_id") in excluded_site_ids:
            continue
        for row in (site.get("series") or {}).get("cohort") or []:
            if row.get("site_id") in excluded_site_ids:
                report.fail(8, "site {} draws excluded site {} as a cohort peer".format(
                    site.get("site_id"), row.get("site_id")))
                break

    for cohort in payload.get("cohorts", []):
        members = cohort.get("member_site_ids", [])
        analysed = cohort.get("analysed_site_ids")
        if analysed is None:
            continue
        expected = [site_id for site_id in members if site_id not in excluded_site_ids]
        if sorted(analysed) != sorted(expected):
            report.fail(6, "cohort {} analysed_site_ids disagrees with the exclusion list".format(
                cohort.get("cohort_id")))
        if cohort.get("analysed_count") != len(analysed):
            report.fail(6, "cohort {} analysed_count is {} but lists {} analysed members".format(
                cohort.get("cohort_id"), cohort.get("analysed_count"), len(analysed)))


def walk_objects(node, path="$"):
    """Yield every (path, dict) pair in the payload, depth first."""
    if isinstance(node, dict):
        yield path, node
        for key, value in node.items():
            for result in walk_objects(value, "{}.{}".format(path, key)):
                yield result
    elif isinstance(node, list):
        for index, value in enumerate(node):
            for result in walk_objects(value, "{}[{}]".format(path, index)):
                yield result


def check_data_status_values(payload, report):
    """Rule 13 — every object carrying a data_status has a valid enum value.

    Also collects rule 15's placeholder census in the same pass.
    """
    for path, node in walk_objects(payload):
        if "data_status" not in node:
            continue
        value = node["data_status"]
        if value not in VALID_DATA_STATUS:
            report.fail(13, "{}.data_status is {!r}, not one of {}".format(
                path, value, sorted(VALID_DATA_STATUS)))
        elif value == "PLACEHOLDER":
            report.note_placeholder(path)


def check_confidence_range(payload, report):
    """Rule 14 — confidence values within 0 to 1 inclusive."""
    for path, node in walk_objects(payload):
        if "confidence" not in node:
            continue
        value = node["confidence"]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            report.fail(14, "{}.confidence is {!r}, not numeric".format(path, value))
        elif not 0.0 <= value <= 1.0:
            report.fail(14, "{}.confidence is {}, outside 0 to 1".format(path, value))


def check_score_types(payload, report):
    """Supporting check for section 2.4 — score_type must be a known enum value."""
    for site in payload.get("sites", []):
        detection = site.get("detection")
        if not detection:
            continue
        score_type = detection.get("score_type")
        if score_type not in VALID_SCORE_TYPES:
            report.fail(13, "site {} has score_type {!r}, not one of {}".format(
                site.get("site_id"), score_type, sorted(VALID_SCORE_TYPES)))


def check_trip_groups(payload, report):
    """Rule 18 — trip groups partition the fleet and agree with the saving.

    The saving is trips_avoided x cost_per_visit_rm, so a wrong grouping is a
    wrong headline number on Screen 4. Three ways it can go wrong silently: a
    site in two groups, a site in none, or the counts drifting from the groups
    they are supposed to summarise.
    """
    summary = payload.get("fleet_summary", {})
    groups = summary.get("trip_groups")
    if not isinstance(groups, list):
        report.fail(18, "fleet_summary.trip_groups is missing or not a list")
        return

    site_ids = [site.get("site_id") for site in payload.get("sites", [])]
    grouped = [site_id for group in groups for site_id in group.get("site_ids", [])]

    duplicates = {site_id for site_id in grouped if grouped.count(site_id) > 1}
    if duplicates:
        report.fail(18, "sites appear in more than one trip group: {}".format(sorted(duplicates)))

    missing = set(site_ids) - set(grouped)
    if missing:
        report.fail(18, "sites missing from every trip group: {}".format(sorted(missing)))

    # The other direction. A group naming a site that does not exist inflates
    # nothing on its own, but it means the grouping was not derived from this
    # fleet — so no conclusion drawn from it can be trusted.
    unknown = set(grouped) - set(site_ids)
    if unknown:
        report.fail(18, "trip groups name sites that do not exist: {}".format(sorted(unknown)))

    for group in groups:
        declared = group.get("site_count")
        actual = len(group.get("site_ids", []))
        if declared != actual:
            report.fail(18, "trip group {} says site_count {} but lists {}".format(
                group.get("trip_id"), declared, actual))
        # An empty group still counts toward trips_avoided, so it is free money.
        if actual == 0:
            report.fail(18, "trip group {} has no members".format(group.get("trip_id")))

    recommended = sum(1 for group in groups if group.get("dispatched"))
    avoided = len(groups) - recommended
    if summary.get("trips_recommended") != recommended:
        report.fail(18, "trips_recommended is {} but {} groups carry a dispatch".format(
            summary.get("trips_recommended"), recommended))
    if summary.get("trips_avoided") != avoided:
        report.fail(18, "trips_avoided is {} but {} groups carry no dispatch".format(
            summary.get("trips_avoided"), avoided))

    # A group holding a dispatched site is NOT avoided: the technician is already
    # going to that address. Getting this backwards doubles the headline saving.
    dispatched_ids = {
        site.get("site_id") for site in payload.get("sites", [])
        if site.get("status") == "dispatch"
    }
    for group in groups:
        holds_dispatch = bool(set(group.get("site_ids", [])) & dispatched_ids)
        if holds_dispatch != bool(group.get("dispatched")):
            report.fail(18, "trip group {} dispatched={} contradicts its members".format(
                group.get("trip_id"), group.get("dispatched")))

    # And finally the number this whole rule exists to protect. Everything above
    # checks the grouping; without this, a correct grouping can still sit beside
    # an arbitrary saving and pass. Screen 1 and Screen 4 both render it.
    cost_per_visit = payload.get("assumptions", {}).get("cost_per_visit_rm")
    declared_saving = summary.get("estimated_saving_rm")
    if isinstance(cost_per_visit, (int, float)) and isinstance(declared_saving, (int, float)):
        expected = avoided * cost_per_visit
        if abs(declared_saving - expected) > 0.01:
            report.fail(18, "estimated_saving_rm is {} but trips_avoided {} x cost_per_visit_rm {} "
                            "is {}".format(declared_saving, avoided, cost_per_visit, expected))


def check_roi_is_not_multiplied(payload, report):
    """Rule 19 — no roi figure is a silent multiple of a single observed month.

    This rule exists because a previous version of the pipeline multiplied one
    month by six and presented it as rolling history. A projection is legitimate;
    a projection hidden inside a field named `_total` is not. So anything beyond
    the observed period has to live in `projection`, where it is visible.
    """
    roi = payload.get("roi", {})
    summary = payload.get("fleet_summary", {})

    period = roi.get("period_months")
    if not isinstance(period, int) or period < 1:
        report.fail(19, "roi.period_months must be a positive integer, got {!r}".format(period))
        return

    # Never arithmetic on a value that may be absent: a validator that raises
    # tells the reader nothing, and rule 1 already reports the missing field.
    pairs = [
        ("visits_avoided_total", "trips_avoided"),
        ("visits_recommended_total", "trips_recommended"),
    ]
    for roi_key, summary_key in pairs:
        observed = summary.get(summary_key)
        total = roi.get(roi_key)
        if not isinstance(observed, int) or not isinstance(total, int):
            continue
        if total != observed * period:
            report.fail(19, "roi.{} is {} but {} x period_months is {}".format(
                roi_key, total, summary_key, observed * period))

    projection = roi.get("projection")
    if projection is not None:
        for key in ("horizon_months", "factor", "basis"):
            if key not in projection:
                report.fail(19, "roi.projection is missing {!r}".format(key))

    # faults_confirmed must never be derived from dispatch_count — it was once
    # dispatch_count * 2, which was invented. Nothing confirms a fault today.
    confirmed = roi.get("faults_confirmed")
    if confirmed and not roi.get("faults_confirmed_basis"):
        report.fail(19, "roi.faults_confirmed is {} with no faults_confirmed_basis "
                        "explaining what confirmed them".format(confirmed))


ALL_CHECKS = [
    check_top_level_keys,
    check_schema_version,
    check_required_fields,
    check_site_ids_unique,
    check_status_counts,
    check_cohort_references,
    check_cohort_membership,
    check_flagged_sites_have_blocks,
    check_cohort_series_present,
    check_exactly_one_subject,
    check_performance_index_numeric,
    check_threshold_agrees_with_status,
    check_dispatch_ranks_contiguous,
    check_exclusions,
    check_data_status_values,
    check_confidence_range,
    check_score_types,
    check_trip_groups,
    check_roi_is_not_multiplied,
]


# --- Runner -----------------------------------------------------------------


def validate(path):
    """Run every rule. Returns a process exit code."""
    if not os.path.exists(path):
        print("FAIL — {} does not exist.".format(path))
        print("Run  python pipeline/generate_dispatch.py  first.")
        return 1

    try:
        # utf-8-sig, not utf-8: a Windows editor may add a byte-order mark, and
        # rejecting an otherwise-valid file over an invisible character is a
        # confusing failure to hand a teammate.
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as error:
        print("FAIL — {} is not valid JSON: {}".format(path, error))
        return 1

    report = Report()
    for check in ALL_CHECKS:
        check(payload, report)

    print("validating {}".format(path))
    print("schema {} · {} sites · {} cohorts".format(
        payload.get("meta", {}).get("schema_version"),
        len(payload.get("sites", [])),
        len(payload.get("cohorts", []))))
    print("-" * 70)

    if report.failures:
        print("FAILED — {} problem(s):".format(len(report.failures)))
        for failure in report.failures:
            print("  {}".format(failure))
    else:
        print("PASSED — all {} rules satisfied.".format(len(ALL_CHECKS)))

    print_placeholder_warning(report)
    return 0 if report.passed else 1


def print_placeholder_warning(report):
    """Rule 15 — warn loudly, listing every PLACEHOLDER remaining, with a count."""
    if not report.placeholders:
        print("")
        print("No PLACEHOLDER values remain.")
        return

    print("")
    print("!" * 70)
    print("WARNING — {} PLACEHOLDER value(s) remain.".format(len(report.placeholders)))
    print("These MUST NOT survive to submission. See docs/Schema.md section 2.1.")
    print("!" * 70)

    grouped = {}
    for path in report.placeholders:
        # Collapse sites[0].detection, sites[1].detection, ... into one line.
        key = path.split("[")[0] if "[" in path else path
        remainder = path.split("].", 1)[-1] if "]." in path else ""
        label = "{}[].{}".format(key, remainder) if remainder else key
        grouped[label] = grouped.get(label, 0) + 1

    for label in sorted(grouped):
        print("  {:>4} x  {}".format(grouped[label], label))

    print("")
    print("Owners: detection/cohorts -> A (M3) · economics -> A (M2) + C (M4)")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    return validate(path)


if __name__ == "__main__":
    sys.exit(main())

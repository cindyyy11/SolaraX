"""Tests for validate_dispatch.py — the safety net for the whole data contract.

    python pipeline/test_validate_dispatch.py
    python -m unittest discover pipeline

WHY THESE EXIST. `validate_dispatch.py` is what stops a malformed dispatch.json
reaching the dashboard. But a validator with a broken rule is worse than no
validator: it prints PASSED while the data is wrong, and nobody looks again.
These tests break a known-good payload in one specific way each, and assert the
matching rule catches it. If someone refactors the validator and silently
disables a rule, a test goes red instead of a demo.

stdlib unittest on purpose — no pytest, so `pip install -r requirements.txt`
stays three packages.
"""

import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import validate_dispatch  # noqa: E402


def minimal_valid_payload():
    """The smallest payload that satisfies every rule.

    Two sites in one cohort: one flagged, one healthy. Small enough to read in
    full, complete enough to exercise the cross-field rules.
    """
    return {
        "meta": {
            "schema_version": "1.3.0",
            "generated_at": "2026-08-17T00:00:00Z",
            "pipeline_version": "test",
            "reporting_month": "2026-08",
            "reporting_month_label": "August 2026",
            "data_status": "SIMULATED",
            "data_source": "NREL PVDAQ",
            "irradiance_source": "NONE",
            "source_note": "test fixture",
            "date_remapped": True,
            "date_remap_note": "test",
        },
        "assumptions": {
            "tariff_rm_per_kwh": 0.4899,
            "cost_per_visit_rm": 1500,
            "dispatch_threshold_rm_per_month": 1500,
            "min_cohort_size": 5,
        },
        "fleet_summary": {
            "site_count": 2,
            "total_capacity_mwp": 0.3,
            "dispatch_count": 1,
            "monitor_count": 0,
            "healthy_count": 1,
            "visits_avoided": 1,
            "estimated_saving_rm": 1500,
            "total_rm_at_risk": 500.0,
            "cohort_count": 1,
        },
        "roi": {
            "data_status": "SIMULATED",
            "period_months": 6,
            "visits_recommended_total": 6,
            "visits_avoided_total": 6,
            "faults_confirmed": 2,
            "generation_recovered_kwh": 1000.0,
            "rm_protected_cumulative": 489.9,
        },
        "cohorts": [
            {
                "cohort_id": "TEST-01",
                "label": "Test cluster",
                "member_site_ids": ["S-0001", "S-0002"],
                "member_count": 2,
                "analysed_site_ids": ["S-0001", "S-0002"],
                "analysed_count": 2,
                "excluded_site_ids": [],
                "meets_minimum": False,
                "clustering_method": "test",
                "data_status": "SIMULATED",
            }
        ],
        "sites": [
            {
                "site_id": "S-0001",
                "name": "Flagged Site",
                "address": "Somewhere",
                "capacity_kwp": 200.0,
                "lat": 1.0,
                "lon": 2.0,
                "cohort_id": "TEST-01",
                "tariff_rm_per_kwh": 0.4899,
                "source_system_id": "pvdaq_1",
                "status": "dispatch",
                "rank": 1,
                "data_status": "SIMULATED",
                "detection": {
                    "method": "test",
                    "score": -3.0,
                    "score_type": "cohort_mean_deviation",
                    "threshold": -2.0,
                    "confidence": 0.8,
                    "cohort_size": 2,
                    "cohort_meets_minimum": False,
                    "data_status": "SIMULATED",
                },
                "divergence": {"start_date": "2026-07-01", "days_since": 30},
                "economics": {
                    "kwh_lost_monthly": 1000.0,
                    "rm_at_risk_monthly": 500.0,
                    "cumulative_kwh_lost": 1000.0,
                    "cumulative_loss_rm": 489.9,
                    "loss_pct_of_expected": 0.1,
                    "exceeds_dispatch_threshold": True,
                    "calculation": "test",
                    "data_status": "SIMULATED",
                },
                "hypothesis": {
                    "summary": "Test divergence",
                    "detail": "Test detail",
                    "confidence": 0.8,
                    "checks": ["check one"],
                    "photograph": ["photo one"],
                },
                "series": {
                    "actual_vs_expected": [
                        {"date": "2026-08-01", "actual_kwh": 800.0,
                         "expected_kwh": None, "performance_index": 4.0}
                    ],
                    "cohort": [
                        {"date": "2026-08-01", "site_id": "S-0001",
                         "performance_index": 4.0, "is_subject": True},
                        {"date": "2026-08-01", "site_id": "S-0002",
                         "performance_index": 4.5, "is_subject": False},
                    ],
                },
            },
            {
                "site_id": "S-0002",
                "name": "Healthy Site",
                "address": "Elsewhere",
                "capacity_kwp": 100.0,
                "lat": 1.1,
                "lon": 2.1,
                "cohort_id": "TEST-01",
                "tariff_rm_per_kwh": 0.4899,
                "source_system_id": "pvdaq_2",
                "status": "healthy",
                "rank": None,
                "data_status": "SIMULATED",
                "detection": None,
                "divergence": None,
                "economics": None,
                "hypothesis": None,
            },
        ],
    }


def run_checks(payload):
    """Run every rule against a payload and return the report."""
    report = validate_dispatch.Report()
    for check in validate_dispatch.ALL_CHECKS:
        check(payload, report)
    return report


def failures_mentioning(report, *fragments):
    """True when some failure mentions every fragment — keeps assertions specific."""
    return any(
        all(fragment.lower() in failure.lower() for fragment in fragments)
        for failure in report.failures
    )


class TestValidPayload(unittest.TestCase):
    def test_baseline_fixture_passes(self):
        """If this fails, every other test in the file is meaningless."""
        report = run_checks(minimal_valid_payload())
        self.assertTrue(report.passed, "fixture should be valid, got: {}".format(report.failures))

    def test_no_placeholders_in_fixture(self):
        report = run_checks(minimal_valid_payload())
        self.assertEqual(report.placeholders, [])


class TestStructuralRules(unittest.TestCase):
    def test_missing_top_level_key_is_caught(self):
        payload = minimal_valid_payload()
        del payload["roi"]
        self.assertTrue(failures_mentioning(run_checks(payload), "roi"))

    def test_wrong_schema_major_version_is_caught(self):
        payload = minimal_valid_payload()
        payload["meta"]["schema_version"] = "2.0.0"
        self.assertTrue(failures_mentioning(run_checks(payload), "schema_version"))

    def test_duplicate_site_id_is_caught(self):
        payload = minimal_valid_payload()
        payload["sites"][1]["site_id"] = "S-0001"
        self.assertTrue(failures_mentioning(run_checks(payload), "duplicate"))

    def test_missing_capacity_is_caught(self):
        """The exact failure that would silently drop a site off every chart."""
        payload = minimal_valid_payload()
        del payload["sites"][0]["capacity_kwp"]
        self.assertTrue(failures_mentioning(run_checks(payload), "capacity_kwp"))

    def test_status_counts_must_sum_to_site_count(self):
        payload = minimal_valid_payload()
        payload["fleet_summary"]["healthy_count"] = 99
        self.assertTrue(failures_mentioning(run_checks(payload), "site_count"))

    def test_dangling_cohort_reference_is_caught(self):
        payload = minimal_valid_payload()
        payload["sites"][0]["cohort_id"] = "NOPE-99"
        self.assertTrue(failures_mentioning(run_checks(payload), "unknown cohort_id"))

    def test_cohort_listing_a_nonexistent_member_is_caught(self):
        payload = minimal_valid_payload()
        payload["cohorts"][0]["member_site_ids"].append("S-9999")
        self.assertTrue(failures_mentioning(run_checks(payload), "unknown member"))


class TestFlaggedSiteRules(unittest.TestCase):
    def test_flagged_site_without_economics_is_caught(self):
        payload = minimal_valid_payload()
        payload["sites"][0]["economics"] = None
        self.assertTrue(failures_mentioning(run_checks(payload), "economics"))

    def test_flagged_site_with_empty_cohort_series_is_caught(self):
        """Rule 8 — Screen 2 renders blank rather than erroring without this."""
        payload = minimal_valid_payload()
        payload["sites"][0]["series"]["cohort"] = []
        self.assertTrue(failures_mentioning(run_checks(payload), "series.cohort is empty"))

    def test_two_subjects_in_one_cohort_series_is_caught(self):
        payload = minimal_valid_payload()
        payload["sites"][0]["series"]["cohort"][1]["is_subject"] = True
        self.assertTrue(failures_mentioning(run_checks(payload), "subject"))

    def test_non_numeric_performance_index_is_caught(self):
        payload = minimal_valid_payload()
        payload["sites"][0]["series"]["cohort"][0]["performance_index"] = "not a number"
        self.assertTrue(failures_mentioning(run_checks(payload), "performance_index"))

    def test_threshold_flag_must_agree_with_status(self):
        payload = minimal_valid_payload()
        payload["sites"][0]["economics"]["exceeds_dispatch_threshold"] = False
        self.assertTrue(failures_mentioning(run_checks(payload), "exceeds_dispatch_threshold"))

    def test_healthy_site_with_a_rank_is_caught(self):
        payload = minimal_valid_payload()
        payload["sites"][1]["rank"] = 2
        self.assertTrue(failures_mentioning(run_checks(payload), "non-null rank"))

    def test_confidence_outside_zero_to_one_is_caught(self):
        payload = minimal_valid_payload()
        payload["sites"][0]["detection"]["confidence"] = 1.5
        self.assertTrue(failures_mentioning(run_checks(payload), "confidence"))

    def test_invalid_data_status_is_caught(self):
        payload = minimal_valid_payload()
        payload["sites"][0]["data_status"] = "PROBABLY_FINE"
        self.assertTrue(failures_mentioning(run_checks(payload), "data_status"))


class TestExclusionRules(unittest.TestCase):
    """A half-applied exclusion is worse than none — it silently skews peers."""

    def excluded_payload(self):
        payload = minimal_valid_payload()
        payload["sites"][1]["excluded_from_analysis"] = {
            "excluded": True,
            "reason": "incomplete_telemetry",
            "detail": "test",
            "observed_performance_index": 1.1,
            "reference_performance_index": 4.0,
            "threshold": 2.0,
            "method": "test",
            "data_status": "BUILT",
        }
        # An excluded site must not be drawn as a peer.
        payload["sites"][0]["series"]["cohort"] = [
            row for row in payload["sites"][0]["series"]["cohort"]
            if row["site_id"] != "S-0002"
        ]
        payload["cohorts"][0]["analysed_site_ids"] = ["S-0001"]
        payload["cohorts"][0]["analysed_count"] = 1
        payload["cohorts"][0]["excluded_site_ids"] = ["S-0002"]
        return payload

    def test_correctly_applied_exclusion_passes(self):
        report = run_checks(self.excluded_payload())
        self.assertTrue(report.passed, "got: {}".format(report.failures))

    def test_excluded_site_may_not_be_flagged(self):
        payload = self.excluded_payload()
        payload["sites"][1]["status"] = "dispatch"
        self.assertTrue(failures_mentioning(run_checks(payload), "excluded"))

    def test_excluded_site_may_not_appear_as_a_peer(self):
        payload = self.excluded_payload()
        payload["sites"][0]["series"]["cohort"].append(
            {"date": "2026-08-01", "site_id": "S-0002",
             "performance_index": 1.1, "is_subject": False}
        )
        self.assertTrue(failures_mentioning(run_checks(payload), "cohort peer"))

    def test_exclusion_without_a_reason_is_caught(self):
        payload = self.excluded_payload()
        del payload["sites"][1]["excluded_from_analysis"]["reason"]
        self.assertTrue(failures_mentioning(run_checks(payload), "reason"))

    def test_analysed_count_must_agree_with_exclusions(self):
        payload = self.excluded_payload()
        payload["cohorts"][0]["analysed_count"] = 2
        self.assertTrue(failures_mentioning(run_checks(payload), "analysed_count"))


class TestPlaceholderCensus(unittest.TestCase):
    def test_placeholders_are_counted(self):
        """Rule 15 is what stops scaffolding shipping to a judge."""
        payload = minimal_valid_payload()
        payload["sites"][0]["detection"]["data_status"] = "PLACEHOLDER"
        report = run_checks(payload)
        self.assertEqual(len(report.placeholders), 1)


class TestFileLevelBehaviour(unittest.TestCase):
    def test_valid_file_exits_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "dispatch.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(minimal_valid_payload(), handle)
            self.assertEqual(validate_dispatch.validate(path), 0)

    def test_broken_file_exits_non_zero(self):
        payload = minimal_valid_payload()
        del payload["sites"][0]["capacity_kwp"]
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "dispatch.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            self.assertEqual(validate_dispatch.validate(path), 1)

    def test_missing_file_exits_non_zero(self):
        self.assertEqual(validate_dispatch.validate("does_not_exist.json"), 1)

    def test_byte_order_mark_is_tolerated(self):
        """A Windows editor adds a BOM; rejecting a valid file over an invisible
        character is a confusing thing to hand a teammate."""
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "dispatch.json")
            with open(path, "w", encoding="utf-8-sig") as handle:
                json.dump(minimal_valid_payload(), handle)
            self.assertEqual(validate_dispatch.validate(path), 0)

    def test_real_generated_artifact_is_valid(self):
        """Guards the actual file the dashboard serves, when one exists."""
        if not os.path.exists(validate_dispatch.DEFAULT_PATH):
            self.skipTest("no generated dispatch.json — run generate_dispatch.py first")
        self.assertEqual(validate_dispatch.validate(validate_dispatch.DEFAULT_PATH), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Tests for the artifact assembler — the functions that render M3's output.

This module had no unit tests at all while six of its functions were rewritten
to consume the detector. These cover the seam: given a detection result, does
the emitted schema block say what the detector actually found?

stdlib unittest, no pytest. Run:

    .venv/bin/python pipeline/test_generate_dispatch.py
"""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import generate_dispatch as gd


ASSUMPTIONS = {
    "tariff_rm_per_kwh": 0.4373,
    "assumed_yield_kwh_per_kwp_day": 3.8,
    "cost_per_visit_rm": 1500,
    "dispatch_threshold_rm_per_month": 1500,
    "min_cohort_size": 5,
    "min_plausible_performance_index": 2.0,
    "z_score_threshold": -3.5,
    "persist_days": 10,
    "persist_window_days": 14,
    "watch_days": 5,
    "same_trip_radius_km": 2.0,
    "projection_horizon_months": 12,
    "co2e_grid_factor_kg_per_kwh": 0.74,
    "notes": {"co2e_grid_factor_kg_per_kwh": "test note"},
}


def detection_result(**overrides):
    """A dispatch-tier detector result. Every test breaks exactly one field."""
    result = {
        "site_id": "S-0001",
        "scored": True,
        "tier": "dispatch",
        "score": -8.4,
        "threshold": -3.5,
        "score_type": "z_score",
        "method": "Iglewicz-Hoaglin modified z-score against same-day cohort median",
        "breach_days": 12,
        "window_days": 14,
        "scored_days_in_window": 14,
        "cohort_size": 5,
        "cohort_meets_minimum": True,
        "cohort_median_performance_index": 4.0,
        "confidence": 0.9,
        "divergence_start": "2026-07-01",
        "days_since": 46,
        "kwh_lost_monthly": 6000.0,
        "cumulative_kwh_lost": 9200.0,
        "loss_fraction": 0.25,
        "days_affected": 46,
        "shape": "step",
    }
    result.update(overrides)
    return result


def site(**overrides):
    base = {
        "source_system_id": "1203",
        "name": "Test Rooftop",
        "site_location": "Somewhere, NV",
        "lat": 36.1,
        "lon": -115.1,
        "capacity_kwp": 197.47,
        "cohort_id": "VEGAS-01",
        "climate_zone": "Bwh",
    }
    base.update(overrides)
    return base


class TestBuildDetection(unittest.TestCase):
    def test_detection_is_built_not_placeholder(self):
        block = gd.build_detection(detection_result())
        self.assertEqual(block["data_status"], "BUILT")

    def test_the_threshold_travels_with_the_score(self):
        """Without it the score is unreadable — docs/Schema.md section 8.2."""
        block = gd.build_detection(detection_result())
        self.assertEqual(block["threshold"], -3.5)
        self.assertEqual(block["score_type"], "z_score")

    def test_the_score_is_signed(self):
        block = gd.build_detection(detection_result(score=-8.4))
        self.assertLess(block["score"], 0)

    def test_a_thin_cohort_is_reported_not_hidden(self):
        block = gd.build_detection(detection_result(cohort_size=4, cohort_meets_minimum=False))
        self.assertEqual(block["cohort_size"], 4)
        self.assertFalse(block["cohort_meets_minimum"])


class TestBuildDivergence(unittest.TestCase):
    def test_start_date_is_the_detectors_not_a_derived_one(self):
        block = gd.build_divergence(detection_result(divergence_start="2026-03-09"))
        self.assertEqual(block["start_date"], "2026-03-09")

    def test_confidence_label_tracks_the_number(self):
        self.assertEqual(gd.build_divergence(
            detection_result(confidence=0.9))["detection_confidence"], "high")
        self.assertEqual(gd.build_divergence(
            detection_result(confidence=0.5))["detection_confidence"], "medium")
        self.assertEqual(gd.build_divergence(
            detection_result(confidence=0.1))["detection_confidence"], "low")


class TestBuildEconomics(unittest.TestCase):
    def test_ringgit_is_kwh_times_the_config_tariff(self):
        block = gd.build_economics(ASSUMPTIONS, detection_result(kwh_lost_monthly=1000.0))
        self.assertAlmostEqual(block["rm_at_risk_monthly"], round(1000.0 * 0.4373, 2))

    def test_loss_fraction_comes_from_the_detector(self):
        """It used to be a stated constant picked so the screens rendered."""
        block = gd.build_economics(ASSUMPTIONS, detection_result(loss_fraction=0.31))
        self.assertEqual(block["loss_pct_of_expected"], 0.31)

    def test_threshold_flag_is_derived_from_the_money(self):
        rich = gd.build_economics(ASSUMPTIONS, detection_result(kwh_lost_monthly=6000.0))
        self.assertTrue(rich["exceeds_dispatch_threshold"])

    def test_a_site_below_the_threshold_does_not_claim_to_exceed_it(self):
        """The bug this guards: after the tariff dropped 11%, both dispatched
        sites fell below RM 1500 while still claiming to exceed it, on a screen
        that prints the threshold."""
        poor = gd.build_economics(ASSUMPTIONS, detection_result(kwh_lost_monthly=100.0))
        self.assertFalse(poor["exceeds_dispatch_threshold"])

    def test_economics_is_built(self):
        block = gd.build_economics(ASSUMPTIONS, detection_result())
        self.assertEqual(block["data_status"], "BUILT")


class TestBuildHypothesis(unittest.TestCase):
    def test_shape_drives_the_checks(self):
        """The whole point of deriving the hypothesis from the signal: a step
        and a ramp send a technician to look at different things."""
        step = gd.build_hypothesis(site(), "Greater Las Vegas cluster",
                                   detection_result(shape="step"), True)
        ramp = gd.build_hypothesis(site(), "Greater Las Vegas cluster",
                                   detection_result(shape="ramp"), True)
        self.assertNotEqual(step["checks"], ramp["checks"])
        self.assertTrue(any("breaker" in check for check in step["checks"]))
        self.assertTrue(any("soiling" in check.lower() for check in ramp["checks"]))

    def test_an_unknown_shape_still_produces_usable_checks(self):
        block = gd.build_hypothesis(site(), "x cluster",
                                    detection_result(shape=None), True)
        self.assertTrue(block["checks"])

    def test_detail_carries_the_measured_evidence(self):
        block = gd.build_hypothesis(site(), "Greater Las Vegas cluster",
                                    detection_result(), True)
        self.assertIn("2026-07-01", block["detail"])
        self.assertIn("12", block["detail"])
        self.assertNotIn("PLACEHOLDER", block["detail"])

    def test_summary_stays_within_the_schema_limit(self):
        block = gd.build_hypothesis(site(), "A very long cohort label indeed cluster",
                                    detection_result(), True)
        self.assertLessEqual(len(block["summary"]), 90)

    def test_only_a_dispatch_gets_a_photograph_list(self):
        self.assertIn("photograph", gd.build_hypothesis(
            site(), "x cluster", detection_result(), True))
        self.assertNotIn("photograph", gd.build_hypothesis(
            site(), "x cluster", detection_result(), False))


class TestBuildCohorts(unittest.TestCase):
    def sites_by_cohort(self):
        return {"VEGAS-01": [site(source_system_id=str(1200 + i)) for i in range(5)]}

    def test_median_is_the_observed_value_not_the_assumption(self):
        """It used to emit assumed_yield_kwh_per_kwp_day, which made a config
        assumption masquerade as a measurement on the cohort chart."""
        summaries = {"VEGAS-01": {"median_performance_index": 4.93,
                                  "clustering_method": "measured", "analysed_count": 5}}
        cohorts = gd.build_cohorts(self.sites_by_cohort(), ASSUMPTIONS, {}, summaries)
        self.assertEqual(cohorts[0]["cohort_median_performance_index"], 4.93)
        self.assertNotEqual(cohorts[0]["cohort_median_performance_index"],
                            ASSUMPTIONS["assumed_yield_kwh_per_kwp_day"])

    def test_cohort_is_built_when_the_detector_scored_it(self):
        summaries = {"VEGAS-01": {"median_performance_index": 4.93,
                                  "clustering_method": "measured", "analysed_count": 5}}
        cohorts = gd.build_cohorts(self.sites_by_cohort(), ASSUMPTIONS, {}, summaries)
        self.assertEqual(cohorts[0]["data_status"], "BUILT")

    def test_cohort_without_a_summary_stays_placeholder(self):
        """A cohort the detector never scored must not claim to be BUILT."""
        cohorts = gd.build_cohorts(self.sites_by_cohort(), ASSUMPTIONS, {}, {})
        self.assertEqual(cohorts[0]["data_status"], "PLACEHOLDER")

    def test_meets_minimum_judges_analysed_members_not_raw_membership(self):
        by_cohort = self.sites_by_cohort()
        exclusions = {gd.build_site_id("1200"): {"reason": "incomplete_telemetry"}}
        cohorts = gd.build_cohorts(by_cohort, ASSUMPTIONS, exclusions, {})
        self.assertEqual(cohorts[0]["member_count"], 5)
        self.assertEqual(cohorts[0]["analysed_count"], 4)
        self.assertFalse(cohorts[0]["meets_minimum"])


class TestCohortMembership(unittest.TestCase):
    def test_climate_zone_reaches_the_detector(self):
        """Dropped by load_fleet_sites before M3, which made every cohort
        report its climate zone as 'unclassified'."""
        members = gd.build_cohort_membership([site()])
        self.assertEqual(members["VEGAS-01"][0]["climate_zone"], "Bwh")

    def test_site_id_convention_is_applied_on_this_side(self):
        members = gd.build_cohort_membership([site(source_system_id="34")])
        self.assertEqual(members["VEGAS-01"][0]["site_id"], gd.build_site_id("34"))


class TestBuildSiteObjects(unittest.TestCase):
    def scaffold(self, detections, exclusions=None):
        sites = [site(source_system_id="1203")]
        by_cohort = gd.group_sites_by_cohort(sites)
        cohorts = gd.build_cohorts(by_cohort, ASSUMPTIONS, exclusions or {}, {})
        by_id = {c["cohort_id"]: c for c in cohorts}
        return gd.build_site_objects(
            sites, by_id, by_cohort, ASSUMPTIONS, None,
            exclusions=exclusions or {}, detections=detections)

    def test_an_excluded_site_is_healthy_even_when_the_detector_flags_it(self):
        """Its readings are not trustworthy enough to accuse it with."""
        key = gd.build_site_id("1203")
        objects = self.scaffold(
            {key: detection_result(tier="dispatch")},
            exclusions={key: {"reason": "incomplete_telemetry"}})
        self.assertEqual(objects[0]["status"], "healthy")
        self.assertIsNone(objects[0]["detection"])

    def test_a_dispatch_below_its_own_threshold_is_demoted(self):
        """Status follows money. A site whose loss does not clear the cost of
        going is not a dispatch, whatever the detector thought of it."""
        key = gd.build_site_id("1203")
        objects = self.scaffold({key: detection_result(kwh_lost_monthly=10.0)})
        self.assertEqual(objects[0]["status"], "monitor")

    def test_a_site_the_detector_never_scored_is_healthy(self):
        objects = self.scaffold({})
        self.assertEqual(objects[0]["status"], "healthy")

    def test_site_data_status_is_built_when_the_series_is_real(self):
        """This test previously passed real_series=None and still expected
        BUILT — it encoded the bug the second review found, where a synthetic
        run shipped labelled as measured."""
        key = gd.build_site_id("1203")
        sites = [site(source_system_id="1203")]
        by_cohort = gd.group_sites_by_cohort(sites)
        cohorts = gd.build_cohorts(by_cohort, ASSUMPTIONS, {}, {})
        objects = gd.build_site_objects(
            sites, {c["cohort_id"]: c for c in cohorts}, by_cohort, ASSUMPTIONS,
            {key: [{"date": "2026-08-01", "actual_kwh": 100.0, "performance_index": 4.0}]},
            detections={key: detection_result()})
        self.assertEqual(objects[0]["data_status"], "BUILT")


class TestReviewFindings(unittest.TestCase):
    """One test per defect found in review. Each fails on the old behaviour."""

    def scaffold(self, detections, exclusions=None, sites=None):
        sites = sites or [site(source_system_id="1203")]
        by_cohort = gd.group_sites_by_cohort(sites)
        cohorts = gd.build_cohorts(by_cohort, ASSUMPTIONS, exclusions or {}, {})
        by_id = {c["cohort_id"]: c for c in cohorts}
        return gd.build_site_objects(
            sites, by_id, by_cohort, ASSUMPTIONS, None,
            exclusions=exclusions or {}, detections=detections)

    def test_a_monitor_whose_money_clears_the_bar_is_promoted(self):
        """Triage must promote as well as demote. The detector assigns monitor
        on breach COUNT while loss is measured over the whole episode, so a
        large site can reach monitor and still clear the threshold. Validator
        rule 11 fails outright on that combination."""
        key = gd.build_site_id("1203")
        objects = self.scaffold({key: detection_result(tier="monitor",
                                                       kwh_lost_monthly=20000.0)})
        self.assertEqual(objects[0]["status"], "dispatch")
        self.assertTrue(objects[0]["economics"]["exceeds_dispatch_threshold"])

    def test_status_and_threshold_never_disagree(self):
        """The invariant validator rule 11 enforces, asserted at the source."""
        key = gd.build_site_id("1203")
        for kwh in (10.0, 3000.0, 20000.0):
            objects = self.scaffold({key: detection_result(tier="monitor",
                                                           kwh_lost_monthly=kwh)})
            site_object = objects[0]
            exceeds = site_object["economics"]["exceeds_dispatch_threshold"]
            self.assertEqual(site_object["status"] == "dispatch", exceeds, kwh)

    def test_an_unscored_site_is_not_rendered_as_cleared(self):
        """A site the detector could not score has no measurement behind it, so
        it must not carry a BUILT detection block saying it stayed above the
        threshold — docs/Schema.md 8.2."""
        key = gd.build_site_id("1203")
        objects = self.scaffold({key: detection_result(scored=False, tier="healthy",
                                                       score=None)})
        self.assertIsNone(objects[0]["detection"])

    def test_a_cohort_with_no_scorable_day_is_not_labelled_built(self):
        """`.get(key, default)` does not fire when the key is present and None,
        which shipped a null median next to data_status BUILT."""
        by_cohort = {"VEGAS-01": [site(source_system_id=str(1200 + i)) for i in range(5)]}
        summaries = {"VEGAS-01": {"median_performance_index": None,
                                  "clustering_method": "x", "analysed_count": 5}}
        cohorts = gd.build_cohorts(by_cohort, ASSUMPTIONS, {}, summaries)
        self.assertIsNotNone(cohorts[0]["cohort_median_performance_index"])
        self.assertEqual(cohorts[0]["data_status"], "PLACEHOLDER")

    def test_a_site_with_no_cohort_is_skipped_not_crashed(self):
        """A blank cohort_id becomes None, which crashed sorted() on mixed key
        types and would otherwise have been scored as a real cohort."""
        members = gd.build_cohort_membership([
            site(source_system_id="1203"),
            site(source_system_id="9999", cohort_id=None),
        ])
        self.assertNotIn(None, members)
        self.assertEqual(sum(len(group) for group in members.values()), 1)


class TestSecondReviewFindings(unittest.TestCase):
    """One test per defect from the second review pass."""

    def build(self, detections, real_series=None, exclusions=None):
        sites = [site(source_system_id="1203")]
        by_cohort = gd.group_sites_by_cohort(sites)
        cohorts = gd.build_cohorts(by_cohort, ASSUMPTIONS, exclusions or {}, {})
        by_id = {c["cohort_id"]: c for c in cohorts}
        return gd.build_site_objects(
            sites, by_id, by_cohort, ASSUMPTIONS, real_series,
            exclusions=exclusions or {}, detections=detections)

    def test_a_site_with_no_real_series_is_not_labelled_built(self):
        """BUILT was hardcoded. A run with no fleet_daily.parquet — or with
        pandas absent, which load_real_daily_series treats the same way —
        shipped synthetic series labelled as measured, and the validator then
        reported no placeholders remaining."""
        key = gd.build_site_id("1203")
        objects = self.build({key: detection_result()}, real_series=None)
        self.assertEqual(objects[0]["data_status"], "PLACEHOLDER")

    def test_a_site_with_a_real_series_is_built(self):
        key = gd.build_site_id("1203")
        series = {key: [{"date": "2026-08-01", "actual_kwh": 100.0,
                         "performance_index": 4.0}]}
        objects = self.build({key: detection_result()}, real_series=series)
        self.assertEqual(objects[0]["data_status"], "BUILT")

    def test_detection_and_economics_inherit_the_sites_evidence_level(self):
        """They cannot be better-evidenced than the series they are computed
        from — a BUILT detection over a synthetic series is a false label."""
        key = gd.build_site_id("1203")
        objects = self.build({key: detection_result()}, real_series=None)
        self.assertEqual(objects[0]["detection"]["data_status"], "PLACEHOLDER")
        self.assertEqual(objects[0]["economics"]["data_status"], "PLACEHOLDER")

    def test_roi_is_not_built_without_real_data(self):
        summary = {"trips_recommended": 1, "trips_avoided": 2,
                   "estimated_saving_rm": 3000, "total_rm_at_risk": 1000.0}
        self.assertEqual(
            gd.build_roi(summary, ASSUMPTIONS, "PLACEHOLDER")["data_status"],
            "PLACEHOLDER")
        self.assertEqual(gd.build_roi(summary, ASSUMPTIONS)["data_status"], "BUILT")

    def test_a_measured_zero_median_is_kept_not_replaced(self):
        """`or default` substituted the config constant for a measured 0.0 —
        hiding exactly the situation worth seeing. The test is `is not None`."""
        by_cohort = {"VEGAS-01": [site(source_system_id=str(1200 + i)) for i in range(5)]}
        summaries = {"VEGAS-01": {"median_performance_index": 0.0,
                                  "clustering_method": "x", "analysed_count": 5}}
        cohorts = gd.build_cohorts(by_cohort, ASSUMPTIONS, {}, summaries)
        self.assertEqual(cohorts[0]["cohort_median_performance_index"], 0.0)
        self.assertEqual(cohorts[0]["data_status"], "BUILT")

    def test_the_module_imports_from_any_working_directory(self):
        """Bare `import detect_cohort` made generate_dispatch un-importable
        outside pipeline/ — which the FastAPI layer would hit immediately."""
        import subprocess
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r); import generate_dispatch; print('ok')"
             % os.path.join(root, "pipeline")],
            cwd=os.path.expanduser("~"), capture_output=True, text=True)
        self.assertIn("ok", result.stdout, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

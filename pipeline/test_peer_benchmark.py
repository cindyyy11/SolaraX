"""Tests for peer_benchmark.py — M3, the fleet peer-deviation detector.

    python pipeline/test_peer_benchmark.py
    python -m unittest discover pipeline

WHY THESE EXIST. M3 decides which sites a technician drives to. Its two failure
modes cost real money in opposite directions: a missed fault is a month of lost
generation, a false flag is a wasted truck roll on a healthy roof. Neither
announces itself - both produce a confident, well-formatted answer.

Most of these tests pin behaviour that was wrong at some point during the build
and would not have been caught by eyeballing a dashboard:

  - a site with a broken REFERENCE PERIOD inverting its own normalisation
  - a divergence date reported for a fault that had already recovered
  - an unfloored MAD turning a rounding difference into a dispatch
  - the textbook z-cutoff applied at the wrong aggregation level

stdlib unittest, matching the rest of the pipeline.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import peer_benchmark as pb  # noqa: E402
from baseline import load_model_params  # noqa: E402


def make_params(**detector_overrides):
    params = load_model_params()
    for key, value in detector_overrides.items():
        params["detector"][key] = value
    return params


def build_frame(site_ratios, days=120, cohort="C-01", capacity=100.0):
    """A synthetic expected/actual frame.

    `site_ratios` maps site_id -> callable(day_index) -> performance ratio.
    Expected output is a flat 100 kWh/day so shortfalls read directly in kWh.
    """
    rows = []
    for site_id, ratio_for in site_ratios.items():
        for day in range(days):
            date = (pd.Timestamp("2019-01-01") + pd.Timedelta(days=day)).strftime("%Y-%m-%d")
            ratio = ratio_for(day)
            rows.append({
                "site_id": site_id,
                "date": date,
                "expected_kwh": capacity,
                "actual_kwh": capacity * ratio,
                "performance_ratio": ratio,
                "performance_index": ratio * 5.0,
            })
    return pd.DataFrame(rows)


def prepared(frame, params, cohort_by_site, excluded=()):
    normalised, diagnostics = pb.add_reference_normalisation(frame, params, excluded)
    return pb.add_peer_statistics(normalised, cohort_by_site, params), diagnostics


class ClusteringTests(unittest.TestCase):

    def test_haversine_matches_a_known_distance(self):
        # Cherry Hill NJ to Cockeysville MD, about 147 km great-circle.
        distance = pb.haversine_km(39.9283, -75.0481, 39.4856, -76.6636)
        self.assertTrue(140 < distance < 155, distance)

    def test_identical_coordinates_are_zero_apart(self):
        self.assertAlmostEqual(
            pb.haversine_km(36.1952, -115.1582, 36.1952, -115.1582), 0.0)

    def test_clustering_reproduces_the_configured_fleet(self):
        """The cohort ids have to be EARNED, not asserted.

        The dashboard, the docs and the deck all name DSUN-01 and VEGAS-01.
        M3 derives its cohorts from climate zone and distance alone; if that
        derivation stopped matching the configured fleet, the artifact would be
        describing a grouping nobody documented.
        """
        from baseline import load_fleet_sites
        sites = load_fleet_sites()
        clustered = pb.cluster_cohorts(sites, load_model_params())
        _mapping, agreement = pb.reconcile_with_configured_cohorts(clustered, sites)

        self.assertTrue(agreement["agrees_with_config"], agreement["unmatched"])
        self.assertEqual(agreement["derived_cohort_count"], 2)

    def test_climate_zone_separates_before_distance_does(self):
        """Two sites 10 km apart in different Koppen zones are different cohorts.

        Distance-only clustering is degenerate on this fleet - five VEGAS roofs
        share one coordinate - so the zone has to be the primary key.
        """
        sites = [
            {"source_system_id": "1", "lat": 36.0, "lon": -115.0,
             "kg_climate": "Bwh", "capacity_kwp": 100},
            {"source_system_id": "2", "lat": 36.05, "lon": -115.0,
             "kg_climate": "Cfa", "capacity_kwp": 100},
        ]
        clustered = pb.cluster_cohorts(sites, load_model_params())
        self.assertEqual(len(clustered), 2)


class ReferenceNormalisationTests(unittest.TestCase):

    def test_constant_site_bias_is_removed(self):
        """A site permanently 30 % below the fleet assumption is not a fault.

        It is a roof whose true tilt differs from the one M2 assumes. Without
        this, the detector flags the same innocent sites every month forever.
        """
        frame = build_frame({
            "S-0001": lambda day: 0.70,
            "S-0002": lambda day: 1.00,
            "S-0003": lambda day: 1.05,
        })
        params = make_params()
        prepared_frame, _ = prepared(
            frame, params, {"S-0001": "C-01", "S-0002": "C-01", "S-0003": "C-01"})

        tail = prepared_frame[prepared_frame["site_id"] == "S-0001"].tail(30)
        self.assertTrue(np.allclose(tail["normalised_ratio"], 1.0, atol=1e-9))

    def test_zero_output_days_do_not_set_the_reference(self):
        """THE BUG THIS FLEET ACTUALLY HAD.

        S-1276 reported exactly 0.00 kWh on all 31 days of January 2019. Taking
        a median over the reference period put its reference at 0.27, so every
        later day was inflated 3.7x - the site with the worst real collapse in
        the fleet came out as its best performer, and a 35 % injected fault on
        top was invisible.
        """
        def broken_start(day):
            return 0.0 if day < 31 else 1.0

        frame = build_frame({
            "S-0001": broken_start,
            "S-0002": lambda day: 1.0,
            "S-0003": lambda day: 1.0,
        })
        params = make_params()
        _, diagnostics = prepared(
            frame, params, {"S-0001": "C-01", "S-0002": "C-01", "S-0003": "C-01"})

        self.assertAlmostEqual(diagnostics["site_reference_ratios"]["S-0001"], 1.0, places=6)

    def test_too_few_valid_reference_days_makes_a_site_unnormalisable(self):
        """Saying nothing beats scoring off a reference built from three days."""
        def mostly_dead(day):
            return 1.0 if day > 55 else 0.0

        frame = build_frame({
            "S-0001": mostly_dead,
            "S-0002": lambda day: 1.0,
            "S-0003": lambda day: 1.0,
        })
        params = make_params(min_reference_days=20)
        _, diagnostics = prepared(
            frame, params, {"S-0001": "C-01", "S-0002": "C-01", "S-0003": "C-01"})

        self.assertIn("S-0001", diagnostics["unnormalisable"])


class PeerStatisticTests(unittest.TestCase):

    def test_a_healthy_cohort_scores_near_zero(self):
        frame = build_frame({
            "S-0001": lambda day: 1.00,
            "S-0002": lambda day: 1.01,
            "S-0003": lambda day: 0.99,
            "S-0004": lambda day: 1.00,
            "S-0005": lambda day: 1.02,
        })
        params = make_params()
        cohort = {site: "C-01" for site in
                  ["S-0001", "S-0002", "S-0003", "S-0004", "S-0005"]}
        prepared_frame, _ = prepared(frame, params, cohort)
        scores = pb.site_level_scores(prepared_frame, params)

        for site_id, score in scores.items():
            self.assertLess(abs(score["score"]), 3.5, site_id)

    def test_mad_floor_stops_an_identical_cohort_exploding(self):
        """Five roofs on one coordinate can agree to a fraction of a percent.

        Unfloored, the divide turns a 0.2 % difference between healthy sites
        into an unbounded z-score and dispatches a technician.
        """
        frame = build_frame({
            "S-0001": lambda day: 0.998,
            "S-0002": lambda day: 1.000,
            "S-0003": lambda day: 1.000,
            "S-0004": lambda day: 1.000,
            "S-0005": lambda day: 1.000,
        })
        params = make_params()
        cohort = {site: "C-01" for site in
                  ["S-0001", "S-0002", "S-0003", "S-0004", "S-0005"]}
        prepared_frame, _ = prepared(frame, params, cohort)
        scores = pb.site_level_scores(prepared_frame, params)

        self.assertTrue(np.isfinite(scores["S-0001"]["score"]))
        self.assertLess(abs(scores["S-0001"]["score"]), 1.0)

    def test_a_single_dropped_site_becomes_the_outlier(self):
        """One of five loses 30 % from day 80. It must score well below its peers."""
        def stepped(day):
            return 1.0 if day < 80 else 0.70

        frame = build_frame({
            "S-0001": stepped,
            "S-0002": lambda day: 1.00,
            "S-0003": lambda day: 1.01,
            "S-0004": lambda day: 0.99,
            "S-0005": lambda day: 1.00,
        })
        params = make_params()
        cohort = {site: "C-01" for site in
                  ["S-0001", "S-0002", "S-0003", "S-0004", "S-0005"]}
        prepared_frame, _ = prepared(frame, params, cohort)
        scores = pb.site_level_scores(prepared_frame, params)

        self.assertLess(scores["S-0001"]["score"], params["detector"]["modified_z_threshold"])
        self.assertGreaterEqual(scores["S-0001"]["persistence"], 0.9)

    def test_excluded_sites_never_enter_the_peer_median(self):
        """A broken feed must not drag the bar its healthy neighbours are held to."""
        frame = build_frame({
            "S-0001": lambda day: 1.00,
            "S-0002": lambda day: 1.00,
            "S-9999": lambda day: 0.20,
        })
        params = make_params()
        cohort = {"S-0001": "C-01", "S-0002": "C-01", "S-9999": "C-01"}
        prepared_frame, _ = prepared(frame, params, cohort, excluded=["S-9999"])

        tail = prepared_frame[
            (prepared_frame["site_id"] == "S-0001")].tail(10)
        self.assertTrue(np.allclose(tail["peer_median"], 1.0, atol=1e-6))


class DivergenceTests(unittest.TestCase):

    def cohort_frame(self, subject):
        frame = build_frame({
            "S-0001": subject,
            "S-0002": lambda day: 1.00,
            "S-0003": lambda day: 1.00,
            "S-0004": lambda day: 1.00,
            "S-0005": lambda day: 1.00,
        })
        params = make_params()
        cohort = {site: "C-01" for site in
                  ["S-0001", "S-0002", "S-0003", "S-0004", "S-0005"]}
        prepared_frame, _ = prepared(frame, params, cohort)
        return prepared_frame[prepared_frame["site_id"] == "S-0001"], params

    def test_step_fault_is_dated_near_its_onset(self):
        site_frame, params = self.cohort_frame(lambda day: 1.0 if day < 80 else 0.7)
        start_date, days_since = pb.locate_divergence(site_frame, params)

        self.assertIsNotNone(start_date)
        onset = pd.Timestamp("2019-01-01") + pd.Timedelta(days=80)
        self.assertLess(abs((pd.Timestamp(start_date) - onset).days), 7)

    def test_a_recovered_fault_reports_no_divergence(self):
        """A dip that opened and closed in April is history, not a dispatch reason.

        Reporting its start date would put a divergence marker on Screen 2 for a
        site that has since recovered.
        """
        def recovered(day):
            return 0.70 if 60 <= day < 80 else 1.0

        site_frame, params = self.cohort_frame(recovered)
        start_date, _ = pb.locate_divergence(site_frame, params)
        self.assertIsNone(start_date)

    def test_a_healthy_site_has_no_divergence(self):
        site_frame, params = self.cohort_frame(lambda day: 1.0)
        self.assertEqual(pb.locate_divergence(site_frame, params), (None, None))

    def test_step_and_ramp_are_told_apart(self):
        step_frame, params = self.cohort_frame(lambda day: 1.0 if day < 60 else 0.7)
        step_start, _ = pb.locate_divergence(step_frame, params)
        step_shape, _ = pb.classify_shape(step_frame, step_start, params)

        ramp_frame, params = self.cohort_frame(
            lambda day: 1.0 if day < 60 else max(0.5, 1.0 - 0.008 * (day - 60)))
        ramp_start, _ = pb.locate_divergence(ramp_frame, params)
        ramp_shape, _ = pb.classify_shape(ramp_frame, ramp_start, params)

        self.assertEqual(step_shape, "step")
        self.assertEqual(ramp_shape, "progressive")


class ShortfallTests(unittest.TestCase):

    def test_shortfall_matches_the_arithmetic(self):
        """One of five loses 20 % against a flat 100 kWh/day expectation.

        The answer has to be 20 kWh/day, 600 kWh/month, and it has to be
        checkable by hand - PRD section 7's explainability requirement applies
        to the money as much as to the score.
        """
        def stepped(day):
            return 1.0 if day < 60 else 0.80

        frame = build_frame({
            "S-0001": stepped,
            "S-0002": lambda day: 1.00,
            "S-0003": lambda day: 1.00,
            "S-0004": lambda day: 1.00,
            "S-0005": lambda day: 1.00,
        })
        params = make_params()
        cohort = {site: "C-01" for site in
                  ["S-0001", "S-0002", "S-0003", "S-0004", "S-0005"]}
        prepared_frame, _ = prepared(frame, params, cohort)
        site_frame = prepared_frame[prepared_frame["site_id"] == "S-0001"]

        shortfall = pb.estimate_shortfall(site_frame, params)
        self.assertAlmostEqual(shortfall["mean_daily_shortfall_kwh"], 20.0, places=1)
        self.assertAlmostEqual(shortfall["monthly_shortfall_kwh"], 600.0, places=0)

    def test_an_over_performing_site_reports_no_loss(self):
        """A negative loss would quietly offset a real one elsewhere in the fleet."""
        frame = build_frame({
            "S-0001": lambda day: 1.30,
            "S-0002": lambda day: 1.00,
            "S-0003": lambda day: 1.00,
            "S-0004": lambda day: 1.00,
            "S-0005": lambda day: 1.00,
        })
        params = make_params()
        cohort = {site: "C-01" for site in
                  ["S-0001", "S-0002", "S-0003", "S-0004", "S-0005"]}
        prepared_frame, _ = prepared(frame, params, cohort)
        site_frame = prepared_frame[prepared_frame["site_id"] == "S-0001"]

        shortfall = pb.estimate_shortfall(site_frame, params)
        self.assertGreaterEqual(shortfall["mean_daily_shortfall_kwh"], 0.0)


class FlagRuleTests(unittest.TestCase):
    """All three conditions have to bind. Each guards a different failure."""

    def scored(self, subject, **overrides):
        frame = build_frame({
            "S-0001": subject,
            "S-0002": lambda day: 1.00,
            "S-0003": lambda day: 1.00,
            "S-0004": lambda day: 1.00,
            "S-0005": lambda day: 1.00,
        })
        params = make_params(**overrides)
        cohort = {site: "C-01" for site in
                  ["S-0001", "S-0002", "S-0003", "S-0004", "S-0005"]}
        prepared_frame, _ = prepared(frame, params, cohort)
        site_frame = prepared_frame[prepared_frame["site_id"] == "S-0001"]
        site_scores = pb.site_level_scores(prepared_frame, params)
        return pb.score_site(site_frame, site_scores.get("S-0001"), params)

    def test_a_real_sustained_fault_is_flagged(self):
        result = self.scored(lambda day: 1.0 if day < 80 else 0.70)
        self.assertTrue(result["flagged"])

    def test_a_trivial_but_perfectly_consistent_gap_is_not_flagged(self):
        """MATERIALITY. A site that drops 0.5 % after the reference period and
        stays there scores persistence 1.0 - it really is below its peers every
        single day. It is still not a maintenance visit, and a rule leaning on
        persistence alone would send someone.

        Note the gap has to DEVELOP to get here. A site that is 0.5 % low from
        day one is removed by the reference normalisation before the flag rule
        ever sees it, which is a second, earlier guard against the same mistake.
        """
        result = self.scored(lambda day: 1.0 if day < 60 else 0.995)
        self.assertGreaterEqual(result["persistence"], 0.9)
        self.assertFalse(result["flagged"])

    def test_a_constant_offset_present_from_day_one_yields_no_deviation(self):
        """The earlier guard: normalisation removes it, so persistence stays low."""
        result = self.scored(lambda day: 0.995)
        self.assertLess(result["persistence"], 0.5)
        self.assertFalse(result["flagged"])

    def test_a_brief_outage_that_recovered_is_not_flagged(self):
        """PERSISTENCE. One bad week inside the window is an incident, not a
        condition - and the technician would arrive to find nothing wrong."""
        result = self.scored(lambda day: 0.30 if 92 <= day < 99 else 1.0)
        self.assertFalse(result["flagged"])

    def test_a_healthy_site_is_not_flagged(self):
        result = self.scored(lambda day: 1.0)
        self.assertFalse(result["flagged"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

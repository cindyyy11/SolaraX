"""Tests for M3, the peer-benchmarking detector.

stdlib unittest on purpose — no pytest, so pip install -r requirements.txt
stays three packages. Run:

    .venv/bin/python pipeline/test_detect_cohort.py

Every test breaks exactly one thing about a known-good fixture, so a failure
names its own cause. The fixtures are hand-built series with arithmetic that
can be checked on paper — nothing here reads a parquet file.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import detect_cohort as dc


ASSUMPTIONS = {
    "z_score_threshold": -3.5,
    "persist_days": 10,
    "persist_window_days": 14,
    "watch_days": 5,
    "min_cohort_size": 5,
}

START = datetime.date(2026, 1, 1)


def dates(count, start=START):
    return [(start + datetime.timedelta(days=offset)).isoformat()
            for offset in range(count)]


def series(values, start=START):
    """[(pi, pi, ...)] -> the row shape load_real_daily_series produces."""
    return [{"date": day, "actual_kwh": value * 100.0, "performance_index": value}
            for day, value in zip(dates(len(values), start), values)]


def flat_cohort(site_count=5, day_count=40, level=4.0, jitter=0.01):
    """A cohort of healthy sites that track each other with a little spread.

    The jitter matters: with byte-identical peers the MAD is zero and no day
    can be scored at all, which is a real behaviour tested separately but a
    useless baseline for everything else.
    """
    cohort = {}
    for index in range(site_count):
        offset = (index - site_count // 2) * jitter
        cohort["S-%04d" % index] = series([level + offset] * day_count)
    return cohort


def members_for(cohort, capacity=100.0):
    return [{"site_id": site_id, "capacity_kwp": capacity,
             "lat": 36.0 + i * 0.01, "lon": -115.0, "climate_zone": "Bwh"}
            for i, site_id in enumerate(sorted(cohort))]


class TestTheStatistic(unittest.TestCase):
    def test_mad_of_identical_values_is_none_not_zero(self):
        """A zero MAD is the ABSENCE of a score, never a score of zero.

        Returning 0.0 would divide by zero downstream, or worse, be coerced to
        a z of 0 and report a byte-identical cohort as confidently healthy.
        """
        self.assertIsNone(dc.median_absolute_deviation([4.0, 4.0, 4.0], 4.0))

    def test_mad_is_the_median_absolute_deviation(self):
        # deviations from 4.0 are 2,1,0,1,2 -> median 1
        self.assertEqual(dc.median_absolute_deviation([2.0, 3.0, 4.0, 5.0, 6.0], 4.0), 1.0)

    def test_z_is_negative_when_the_site_is_below_its_cohort(self):
        z = dc.modified_z_score(3.0, 4.0, 1.0)
        self.assertLess(z, 0)
        self.assertAlmostEqual(z, 0.6745 * -1.0)

    def test_z_is_none_when_there_is_no_spread(self):
        self.assertIsNone(dc.modified_z_score(3.0, 4.0, None))

    def test_one_bad_site_does_not_move_the_reference(self):
        """The reason for median/MAD over mean/std, asserted rather than argued.

        Four peers at 4.0 and one site at 1.0. The mean would be dragged to
        3.4 and the standard deviation inflated to ~1.34, giving the broken
        site a z of about -1.8 — inside a conventional cutoff, so it would
        measure as normal against a yardstick it bent itself.
        """
        values = [4.0, 4.01, 3.99, 4.0, 1.0]
        centre = 4.0
        mad = dc.median_absolute_deviation(values, centre)
        z = dc.modified_z_score(1.0, centre, mad)
        self.assertLess(z, -3.5)


class TestCohortReference(unittest.TestCase):
    def test_day_below_minimum_cohort_size_is_not_scored(self):
        cohort = flat_cohort(site_count=4, day_count=5)
        reference = dc.cohort_reference_by_date(cohort, sorted(cohort), min_cohort_size=5)
        self.assertEqual(reference, {})

    def test_day_at_minimum_cohort_size_is_scored(self):
        cohort = flat_cohort(site_count=5, day_count=5)
        reference = dc.cohort_reference_by_date(cohort, sorted(cohort), min_cohort_size=5)
        self.assertEqual(len(reference), 5)

    def test_missing_day_for_one_site_drops_that_day_below_the_minimum(self):
        cohort = flat_cohort(site_count=5, day_count=5)
        cohort["S-0000"] = cohort["S-0000"][:-1]
        reference = dc.cohort_reference_by_date(cohort, sorted(cohort), min_cohort_size=5)
        self.assertEqual(len(reference), 4)

    def test_a_site_with_no_usable_reference_is_not_scored(self):
        cohort = flat_cohort(site_count=5, day_count=5, jitter=0.0)
        reference = dc.cohort_reference_by_date(cohort, sorted(cohort), min_cohort_size=5)
        scored = dc.score_site(cohort["S-0000"], reference)
        self.assertEqual(scored, [])


class TestPersistence(unittest.TestCase):
    def test_window_is_counted_in_calendar_days_not_rows(self):
        """A 14-day window must stay 14 calendar days across a telemetry gap.

        Counting rows would silently stretch the window over a month whenever
        data was missing — exactly when a confident answer is least warranted.
        """
        as_of = datetime.date(2026, 1, 31)
        self.assertEqual(dc.window_start(as_of, 14), datetime.date(2026, 1, 18))

    def test_breach_outside_the_window_does_not_count(self):
        scored = [{"date": d, "z": -9.0, "performance_index": 1.0, "cohort_median": 4.0}
                  for d in dates(30)]
        as_of = datetime.date.fromisoformat(scored[-1]["date"])
        breaches = dc.breaches_in_window(scored, as_of, 14, -3.5)
        self.assertEqual(len(breaches), 14)

    def test_a_breach_above_the_threshold_is_not_a_breach(self):
        scored = [{"date": d, "z": -3.4, "performance_index": 1.0, "cohort_median": 4.0}
                  for d in dates(14)]
        as_of = datetime.date.fromisoformat(scored[-1]["date"])
        self.assertEqual(dc.breaches_in_window(scored, as_of, 14, -3.5), [])


class TestEpisodeStart(unittest.TestCase):
    def build(self, z_values):
        return [{"date": d, "z": z, "performance_index": 4.0 - abs(z),
                 "cohort_median": 4.0}
                for d, z in zip(dates(len(z_values)), z_values)]

    def test_no_breach_means_no_episode(self):
        self.assertIsNone(dc.episode_start_date(self.build([0.0] * 20), -3.5, 4))

    def test_episode_starts_at_the_first_breach_of_a_clean_run(self):
        scored = self.build([0.0] * 10 + [-9.0] * 10)
        self.assertEqual(dc.episode_start_date(scored, -3.5, 4), scored[10]["date"])

    def test_a_short_clean_gap_does_not_split_the_episode(self):
        scored = self.build([0.0] * 5 + [-9.0] * 5 + [0.0] * 3 + [-9.0] * 5)
        self.assertEqual(dc.episode_start_date(scored, -3.5, 4), scored[5]["date"])

    def test_a_long_clean_gap_starts_a_new_episode(self):
        """A site that recovered and then failed again dates itself to the
        SECOND failure. Dating it to the first would bill this month for a
        fault that was already fixed."""
        scored = self.build([-9.0] * 5 + [0.0] * 10 + [-9.0] * 5)
        self.assertEqual(dc.episode_start_date(scored, -3.5, 4), scored[15]["date"])


class TestLoss(unittest.TestCase):
    def test_days_above_the_cohort_do_not_offset_days_below(self):
        """A good week must not cancel a bad one.

        Netting them would let a site that lost 100 kWh on Monday and gained
        100 on Tuesday report no loss at all, when in fact it needs a visit.
        """
        scored = [
            {"date": "2026-01-01", "z": -9.0, "performance_index": 3.0, "cohort_median": 4.0},
            {"date": "2026-01-02", "z": 9.0, "performance_index": 5.0, "cohort_median": 4.0},
        ]
        rows = dc.shortfall_rows(scored, "2026-01-01")
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["deficit_per_kwp"], 1.0)

    def test_monthly_loss_is_the_mean_day_scaled_not_the_episode_sum(self):
        """A 90-day episode must not report three months of loss as this month's.

        1.0 kWh/kWp/day short on a 100 kWp site is 100 kWh/day, so a month is
        3000 kWh however long the episode has been running.
        """
        scored = [{"date": d, "z": -9.0, "performance_index": 3.0, "cohort_median": 4.0}
                  for d in dates(90)]
        loss = dc.loss_summary(scored, scored[0]["date"], capacity_kwp=100.0,
                               days_per_month=30)
        self.assertAlmostEqual(loss["kwh_lost_monthly"], 3000.0)
        self.assertAlmostEqual(loss["cumulative_kwh_lost"], 9000.0)
        self.assertEqual(loss["days_affected"], 90)

    def test_loss_fraction_is_relative_to_the_cohort_median(self):
        scored = [{"date": d, "z": -9.0, "performance_index": 3.0, "cohort_median": 4.0}
                  for d in dates(10)]
        loss = dc.loss_summary(scored, scored[0]["date"], 100.0, 30)
        self.assertAlmostEqual(loss["loss_fraction"], 0.25)


class TestConfidence(unittest.TestCase):
    def test_a_site_above_its_cohort_gets_no_confidence(self):
        """Depth must count only underperformance.

        Using |z| would report a high-yielding site as a confident problem,
        because being far from the median in the GOOD direction is still far.
        """
        self.assertEqual(dc.detection_confidence(0, 14, median_z=9.0, threshold=-3.5), 0.0)

    def test_confidence_rises_with_persistence(self):
        low = dc.detection_confidence(5, 14, -4.0, -3.5)
        high = dc.detection_confidence(14, 14, -4.0, -3.5)
        self.assertGreater(high, low)

    def test_confidence_is_bounded_to_one(self):
        self.assertLessEqual(dc.detection_confidence(14, 14, -1000.0, -3.5), 1.0)


class TestShape(unittest.TestCase):
    def build(self, deficits):
        return [{"date": d, "z": -9.0 if deficit > 0 else 0.0,
                 "performance_index": 4.0 - deficit, "cohort_median": 4.0}
                for d, deficit in zip(dates(len(deficits)), deficits)]

    def test_a_flat_deficit_is_a_step(self):
        scored = self.build([1.0] * 20)
        self.assertEqual(dc.classify_shape(scored, scored[0]["date"]), dc.SHAPE_STEP)

    def test_a_deepening_deficit_is_a_ramp(self):
        scored = self.build([0.1 * (index + 1) for index in range(20)])
        self.assertEqual(dc.classify_shape(scored, scored[0]["date"]), dc.SHAPE_RAMP)

    def test_a_deficit_that_comes_and_goes_is_intermittent(self):
        scored = self.build([1.0, 0.0, 0.0, 1.0, 0.0, 0.0] * 4)
        self.assertEqual(dc.classify_shape(scored, scored[0]["date"]),
                         dc.SHAPE_INTERMITTENT)

    def test_too_short_to_have_a_shape(self):
        scored = self.build([1.0] * 3)
        self.assertEqual(dc.classify_shape(scored, scored[0]["date"]), dc.SHAPE_UNKNOWN)


class TestDetectCohort(unittest.TestCase):
    def faulty_cohort(self, drop=0.30, fault_days=20, day_count=40):
        cohort = flat_cohort(day_count=day_count)
        victim = "S-0000"
        rows = cohort[victim]
        for row in rows[-fault_days:]:
            row["performance_index"] = round(row["performance_index"] * (1 - drop), 4)
        return cohort, victim

    def test_a_sustained_drop_is_dispatched(self):
        cohort, victim = self.faulty_cohort()
        results, summary = dc.detect_cohort(cohort, members_for(cohort), ASSUMPTIONS)
        self.assertEqual(results[victim]["tier"], dc.TIER_DISPATCH)
        self.assertLess(results[victim]["score"], ASSUMPTIONS["z_score_threshold"])
        self.assertTrue(summary["meets_minimum"])

    def test_healthy_peers_are_not_flagged(self):
        cohort, victim = self.faulty_cohort()
        results, _ = dc.detect_cohort(cohort, members_for(cohort), ASSUMPTIONS)
        for site_id, result in results.items():
            if site_id != victim:
                self.assertEqual(result["tier"], dc.TIER_HEALTHY, site_id)

    def test_a_healthy_site_carries_no_loss_and_no_divergence(self):
        """Every site drifts below its cohort on SOME day. Attaching a ringgit
        figure to ordinary scatter would put 'days affected' on a healthy row."""
        cohort, victim = self.faulty_cohort()
        results, _ = dc.detect_cohort(cohort, members_for(cohort), ASSUMPTIONS)
        healthy = results["S-0001"]
        self.assertIsNone(healthy["divergence_start"])
        self.assertEqual(healthy["days_affected"], 0)
        self.assertEqual(healthy["kwh_lost_monthly"], 0.0)

    def test_a_brief_drop_is_monitored_not_dispatched(self):
        cohort, victim = self.faulty_cohort(fault_days=6)
        results, _ = dc.detect_cohort(cohort, members_for(cohort), ASSUMPTIONS)
        self.assertEqual(results[victim]["tier"], dc.TIER_MONITOR)

    def test_a_one_day_drop_never_dispatches_anyone(self):
        """The curtailment defence. One bad day is not a technician visit."""
        cohort, victim = self.faulty_cohort(fault_days=1)
        results, _ = dc.detect_cohort(cohort, members_for(cohort), ASSUMPTIONS)
        self.assertEqual(results[victim]["tier"], dc.TIER_HEALTHY)

    def test_a_cohort_wide_dip_flags_nobody(self):
        """THE CENTRAL CLAIM. Weather moves every site together, so the median
        moves with it and no deviation exists to detect. If this test ever
        fails, the product is flagging weather as faults."""
        cohort = flat_cohort(day_count=40)
        for rows in cohort.values():
            for row in rows[-20:]:
                row["performance_index"] = round(row["performance_index"] * 0.5, 4)
        results, _ = dc.detect_cohort(cohort, members_for(cohort), ASSUMPTIONS)
        for site_id, result in results.items():
            self.assertEqual(result["tier"], dc.TIER_HEALTHY, site_id)

    def test_an_excluded_site_is_never_flagged(self):
        cohort, victim = self.faulty_cohort()
        results, summary = dc.detect_cohort(
            cohort, members_for(cohort), ASSUMPTIONS, excluded_site_ids={victim})
        self.assertNotIn(victim, results)
        self.assertNotIn(victim, summary["analysed_site_ids"])

    def test_excluding_a_site_can_drop_the_cohort_below_its_minimum(self):
        """Both real cohorts sit at exactly five analysed members. One more
        exclusion and the control group is too thin to accuse anyone with —
        which must be reported, not silently tolerated."""
        cohort, victim = self.faulty_cohort()
        _, summary = dc.detect_cohort(
            cohort, members_for(cohort), ASSUMPTIONS, excluded_site_ids={victim})
        self.assertEqual(summary["analysed_count"], 4)
        self.assertFalse(summary["meets_minimum"])

    def test_the_reported_median_is_observed_not_assumed(self):
        cohort = flat_cohort(day_count=40, level=4.0)
        _, summary = dc.detect_cohort(cohort, members_for(cohort), ASSUMPTIONS)
        self.assertAlmostEqual(summary["median_performance_index"], 4.0, places=3)

    def test_clustering_method_reports_the_measured_separation(self):
        cohort = flat_cohort()
        _, summary = dc.detect_cohort(cohort, members_for(cohort), ASSUMPTIONS)
        self.assertIn("km", summary["clustering_method"])
        self.assertIn("Bwh", summary["clustering_method"])


class TestGeometry(unittest.TestCase):
    def test_identical_coordinates_are_zero_apart(self):
        self.assertAlmostEqual(dc.haversine_km(36.1, -115.1, 36.1, -115.1), 0.0)

    def test_separation_is_the_widest_pair_not_the_first(self):
        members = [
            {"lat": 36.0, "lon": -115.0},
            {"lat": 36.01, "lon": -115.0},
            {"lat": 37.0, "lon": -115.0},
        ]
        self.assertGreater(dc.max_pairwise_separation_km(members), 100)


class TestReviewFindings(unittest.TestCase):
    """One test per defect found in review. Each fails on the old behaviour."""

    def scored_rows(self, deficits, start=START):
        return [{"date": d, "z": -9.0 if deficit > 0 else 0.0,
                 "performance_index": 4.0 - deficit, "cohort_median": 4.0}
                for d, deficit in zip(dates(len(deficits), start), deficits)]

    def test_monthly_loss_averages_over_episode_days_not_just_bad_ones(self):
        """An intermittent fault losing 1.0 kWh/kWp on 6 of 30 days is 600
        kWh/month on a 100 kWp site, not 3000. Dividing by deficit days answers
        'how bad was it when it was bad', which is not a monthly exposure."""
        deficits = ([1.0] + [0.0] * 4) * 6
        scored = self.scored_rows(deficits)
        loss = dc.loss_summary(scored, scored[0]["date"], capacity_kwp=100.0,
                               days_per_month=30)
        self.assertAlmostEqual(loss["kwh_lost_monthly"], 600.0)
        self.assertAlmostEqual(loss["loss_fraction"], 0.05)

    def test_a_continuous_deficit_is_unchanged_by_that_divisor(self):
        scored = self.scored_rows([1.0] * 30)
        loss = dc.loss_summary(scored, scored[0]["date"], 100.0, 30)
        self.assertAlmostEqual(loss["kwh_lost_monthly"], 3000.0)

    def test_a_telemetry_outage_does_not_extend_the_episode_backwards(self):
        """The gap tolerance is CALENDAR days, matching window_start. Counting
        rows let a month-long outage pass as a few clean days and dated the
        episode back across the whole outage."""
        early = self.scored_rows([1.0] * 3, start=datetime.date(2026, 1, 1))
        late = self.scored_rows([1.0] * 5, start=datetime.date(2026, 3, 1))
        scored = early + late
        self.assertEqual(dc.episode_start_date(scored, -3.5, 4), late[0]["date"])

    def test_a_site_with_no_days_in_the_window_is_not_scored(self):
        """Its feed stopped. It has older scored days so the no-series branch
        misses it, and reporting median z of 0.0 would render a site nobody
        examined as confidently healthy."""
        cohort = flat_cohort(day_count=60)
        for site_id in cohort:
            if site_id != "S-0000":
                continue
            cohort[site_id] = cohort[site_id][:-30]
        results, _ = dc.detect_cohort(cohort, members_for(cohort), ASSUMPTIONS)
        self.assertFalse(results["S-0000"]["scored"])
        self.assertIsNone(results["S-0000"]["score"])

    def test_a_scored_site_says_so(self):
        cohort = flat_cohort(day_count=40)
        results, _ = dc.detect_cohort(cohort, members_for(cohort), ASSUMPTIONS)
        self.assertTrue(results["S-0000"]["scored"])

    def test_a_site_is_never_scored_against_a_group_containing_itself(self):
        """Leave-one-out. A site inside its own reference bends the yardstick it
        is judged by: measured on the real fleet, two faults in a five-site
        cohort inflate the MAD 3x in one cohort and 24x in the other, which
        suppresses the broken sites' own z-scores."""
        cohort = flat_cohort(site_count=5, day_count=40)
        for row in cohort["S-0000"][-20:]:
            row["performance_index"] = 1.0
        for row in cohort["S-0001"][-20:]:
            row["performance_index"] = 1.0

        with_self = dc.cohort_reference_by_date(cohort, sorted(cohort), 5)
        peers_only = dc.peer_reference_by_date(cohort, sorted(cohort), "S-0000", 5)
        last = sorted(with_self)[-1]
        self.assertLess(peers_only[last]["mad"] or 0.0, with_self[last]["mad"])

        results, _ = dc.detect_cohort(cohort, members_for(cohort), ASSUMPTIONS)
        self.assertNotEqual(results["S-0000"]["tier"], dc.TIER_HEALTHY)


if __name__ == "__main__":
    unittest.main(verbosity=2)

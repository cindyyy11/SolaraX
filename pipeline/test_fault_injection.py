"""Tests for fault_injection.py — the harness that manufactures M3's answer key.

    python pipeline/test_fault_injection.py

WHY THESE EXIST. Every accuracy figure M3 ever states rests on these labels being
right. A harness that injects one thing and records another produces a number
that looks rigorous and means nothing — and nobody would catch it, because the
label file is the only thing anyone checks the detector against.

So the tests here are mostly about agreement: that the factor applied matches the
factor recorded, that both frames still reconcile afterwards, and that the whole
thing reverses.

stdlib unittest, matching test_validate_dispatch.py. pandas is already a pipeline
dependency.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fault_injection  # noqa: E402


ASSUMPTIONS = {
    "soiling_rate_per_day": 0.0047,
    "soiling_max_loss_fraction": 0.60,
    "min_plausible_performance_index": 2.0,
}


def step_event(magnitude=0.20, **overrides):
    event = fault_injection.build_event(
        site_id="S-0001", fault_type="step_drop", injected_from="2019-03-01",
        magnitude=magnitude, assumptions=ASSUMPTIONS)
    event.update(overrides)
    return event


class TestFactors(unittest.TestCase):
    def test_nothing_happens_before_the_start_date(self):
        self.assertEqual(fault_injection.factor_for_day(step_event(), -1), 1.0)

    def test_step_drop_is_flat(self):
        event = step_event(magnitude=0.25)
        self.assertAlmostEqual(fault_injection.factor_for_day(event, 0), 0.75)
        self.assertAlmostEqual(fault_injection.factor_for_day(event, 200), 0.75)

    def test_soiling_accumulates(self):
        event = fault_injection.build_event(
            site_id="S-0001", fault_type="soiling_ramp", injected_from="2019-03-01",
            magnitude=None, assumptions=ASSUMPTIONS)
        self.assertAlmostEqual(fault_injection.factor_for_day(event, 0), 1.0)
        self.assertAlmostEqual(fault_injection.factor_for_day(event, 100), 1 - 0.47)

    def test_soiling_is_bounded_and_never_goes_negative(self):
        """Unbounded, 0.47%/day reaches total loss on day 213 — inside our
        233-day window — and then produces negative generation."""
        event = fault_injection.build_event(
            site_id="S-0001", fault_type="soiling_ramp", injected_from="2019-03-01",
            magnitude=None, assumptions=ASSUMPTIONS)
        for day in (213, 300, 5000):
            factor = fault_injection.factor_for_day(event, day)
            self.assertGreater(factor, 0.0)
            self.assertAlmostEqual(factor, 1 - ASSUMPTIONS["soiling_max_loss_fraction"])

    def test_string_loss_removes_one_unit_share(self):
        """The site loses 1/N when one of N units drops out — not 1/N of one
        unit, which would cost the site about 1/N squared."""
        event = fault_injection.build_event(
            site_id="S-0001", fault_type="string_loss", injected_from="2019-03-01",
            magnitude=None, assumptions=ASSUMPTIONS, unit_count=7)
        self.assertAlmostEqual(fault_injection.factor_for_day(event, 0), 1 - 1 / 7, places=5)

    def test_unknown_fault_type_raises(self):
        with self.assertRaises(ValueError):
            fault_injection.factor_for_day(step_event(fault_type="meteor_strike"), 0)


class TestEventConstruction(unittest.TestCase):
    def test_string_loss_needs_at_least_two_units(self):
        with self.assertRaises(ValueError):
            fault_injection.build_event(
                site_id="S-0034", fault_type="string_loss", injected_from="2019-03-01",
                magnitude=None, assumptions=ASSUMPTIONS, unit_count=1)

    def test_string_loss_refuses_a_unit_target(self):
        """It is a site-level fault by definition. Accepting a unit here is how
        the 1/N-squared bug got in the first time."""
        with self.assertRaises(ValueError):
            fault_injection.build_event(
                site_id="S-1199", fault_type="string_loss", injected_from="2019-03-01",
                magnitude=None, assumptions=ASSUMPTIONS, unit_count=7, unit_id="inv1")

    def test_no_fabricated_affected_capacity(self):
        """PVDAQ publishes no per-inverter DC capacity, only an AC rating. A kWp
        figure derived from it would be invented — inside the one artifact whose
        entire purpose is being trustworthy."""
        event = fault_injection.build_event(
            site_id="S-1199", fault_type="string_loss", injected_from="2019-03-01",
            magnitude=None, assumptions=ASSUMPTIONS, unit_count=7)
        self.assertNotIn("affected_capacity_kwp", event)

    def test_every_event_is_labelled_synthetic(self):
        self.assertIn("SYNTHETIC", step_event()["note"])


class TestWindowing(unittest.TestCase):
    def test_dates_outside_the_window_are_untouched(self):
        offsets = fault_injection.day_offsets(
            ["2019-02-28", "2019-03-01", "2019-03-05", "2019-04-01"],
            "2019-03-01", "2019-03-10")
        self.assertEqual(offsets, [None, 0, 4, None])

    def test_open_ended_window_runs_to_the_end(self):
        offsets = fault_injection.day_offsets(
            ["2019-02-28", "2019-03-01", "2019-12-31"], "2019-03-01", None)
        self.assertEqual(offsets, [None, 0, 305])


class TestAgainstRealData(unittest.TestCase):
    """Round-trip against the committed parquets. Skips cleanly without them."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(fault_injection.FLEET_DAILY_PATH):
            raise unittest.SkipTest("no fleet_daily.parquet — run fetch_pvdaq.py first")
        try:
            import pandas  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("pandas/pyarrow not installed — see the venv note in docs")

    def frames(self):
        frames = fault_injection.load_frames()
        frames["fleet"]["injected"] = False
        frames["inverter"]["injected"] = False
        return frames

    def test_real_frames_are_not_mutated_on_disk(self):
        import pandas
        before = pandas.read_parquet(fault_injection.FLEET_DAILY_PATH)["kwh"].sum()
        frames = self.frames()
        fault_injection.apply_event(frames, step_event(magnitude=0.5, site_id="S-1201"))
        after = pandas.read_parquet(fault_injection.FLEET_DAILY_PATH)["kwh"].sum()
        self.assertEqual(before, after)

    def test_site_injection_removes_energy(self):
        frames = self.frames()
        before = float(frames["fleet"].loc[frames["fleet"]["site_id"] == "S-1201", "kwh"].sum())
        event = fault_injection.apply_event(frames, step_event(magnitude=0.5, site_id="S-1201"))
        after = float(frames["fleet"].loc[frames["fleet"]["site_id"] == "S-1201", "kwh"].sum())
        self.assertLess(after, before)
        # kwh_removed is rounded to 3 dp for readability in the label file, so it
        # can sit up to 0.0005 from the exact delta. It is a reporting field —
        # reversal recomputes factors and never reads it.
        self.assertAlmostEqual(event["kwh_removed"], before - after, places=2)

    def test_performance_index_is_recomputed(self):
        """A stale index would inject a fault the detector cannot see."""
        frames = self.frames()
        fault_injection.apply_event(frames, step_event(magnitude=0.5, site_id="S-1201"))
        rows = frames["fleet"].loc[frames["fleet"]["site_id"] == "S-1201"]
        expected = rows["kwh"] / rows["capacity_kwp"]
        self.assertTrue(bool((rows["performance_index"] - expected).abs().max() < 1e-9))

    def test_summed_inverter_site_still_reconciles(self):
        """S-1199's fleet total IS the sum of its inverters. If an injection
        moves one side and not the other the two files disagree silently."""
        frames = self.frames()
        event = fault_injection.build_event(
            site_id="S-1199", fault_type="string_loss", injected_from="2019-03-19",
            magnitude=None, assumptions=fault_injection.load_assumptions(), unit_count=7)
        fault_injection.apply_event(frames, event)

        fleet = frames["fleet"]
        units = frames["inverter"]
        site_total = float(fleet.loc[fleet["site_id"] == "S-1199", "kwh"].sum())
        unit_total = float(units.loc[units["site_id"] == "S-1199", "kwh"].sum())
        self.assertAlmostEqual(site_total, unit_total, places=3)

    def test_unit_injection_moves_the_site_by_the_same_energy(self):
        frames = self.frames()
        fleet, units = frames["fleet"], frames["inverter"]
        site_before = float(fleet.loc[fleet["site_id"] == "S-1203", "kwh"].sum())
        unit_before = float(units.loc[(units["site_id"] == "S-1203")
                                      & (units["inverter_id"] == "inv1"), "kwh"].sum())

        fault_injection.apply_event(frames, step_event(
            magnitude=0.4, site_id="S-1203", unit_id="inv1"))

        site_after = float(fleet.loc[fleet["site_id"] == "S-1203", "kwh"].sum())
        unit_after = float(units.loc[(units["site_id"] == "S-1203")
                                     & (units["inverter_id"] == "inv1"), "kwh"].sum())
        self.assertAlmostEqual(site_before - site_after, unit_before - unit_after, places=3)

    def test_injected_rows_are_flagged(self):
        """A synthetic point must never be mistakable for a real measurement."""
        frames = self.frames()
        fault_injection.apply_event(frames, step_event(magnitude=0.3, site_id="S-1201"))
        touched = frames["fleet"].loc[frames["fleet"]["injected"]]
        self.assertGreater(len(touched), 0)
        self.assertTrue(bool((touched["site_id"] == "S-1201").all()))

    def test_ladder_leaves_controls_and_never_takes_a_whole_cohort(self):
        """False-positive rate on clean sites is the commercially important
        metric, and it needs clean sites to exist."""
        import collections
        import pandas

        frames = self.frames()
        assumptions = fault_injection.load_assumptions()
        events = fault_injection.choose_events(frames, assumptions, seed=42, count=4)

        injected = {event["site_id"] for event in events}
        all_sites = set(frames["fleet"]["site_id"].unique())
        self.assertTrue(all_sites - injected, "no uninjected control sites left")

        sites = pandas.read_csv(fault_injection.FLEET_SITES_PATH)
        cohort_of = {
            "S-{:0>4}".format(str(row.source_system_id).strip()): row.cohort_id
            for row in sites.itertuples()
        }
        per_cohort = collections.Counter(cohort_of.get(site_id) for site_id in injected)
        for cohort, count in per_cohort.items():
            members = sum(1 for site_id in all_sites if cohort_of.get(site_id) == cohort)
            self.assertLessEqual(count, max(1, members // 2),
                                 "cohort {} has {} of {} injected".format(cohort, count, members))

    def test_ladder_start_dates_are_staggered(self):
        """Every fault sharing one start date is a tell: a detector that learns
        "something happened on 19 March" scores well without detecting
        anything, and days-to-detect from one common point flatters it."""
        frames = self.frames()
        events = fault_injection.choose_events(frames, fault_injection.load_assumptions(),
                                               seed=42, count=4)
        starts = {event["injected_from"] for event in events}
        self.assertGreater(len(starts), 1, "all faults start on the same date")

    def test_soiling_rate_scales_with_ladder_position(self):
        """It previously discarded severity_scale, so every soiling event was
        identical regardless of ladder position — a third of the ladder was
        decorative. A slower ramp is a harder detection, which is the point."""
        assumptions = fault_injection.load_assumptions()
        base = assumptions["soiling_rate_per_day"]
        severe = fault_injection.build_event(
            site_id="S-0001", fault_type="soiling_ramp", injected_from="2019-03-01",
            magnitude=None, assumptions=assumptions, severity_scale=1.0)
        mild = fault_injection.build_event(
            site_id="S-0001", fault_type="soiling_ramp", injected_from="2019-03-01",
            magnitude=None, assumptions=assumptions, severity_scale=0.25)
        self.assertAlmostEqual(severe["rate_per_day"], base, places=6)
        self.assertLess(mild["rate_per_day"], severe["rate_per_day"])
        # A milder ramp must actually be harder to see at a fixed horizon.
        self.assertGreater(fault_injection.factor_for_day(mild, 60),
                           fault_injection.factor_for_day(severe, 60))

    def test_string_loss_varies_by_site_rather_than_being_faked(self):
        """1/N is fixed by hardware, so it cannot be laddered without inventing
        a partial unit dropout — which would undo the site-level semantics.
        Honest variation across sites beats a fabricated one."""
        assumptions = fault_injection.load_assumptions()
        seven = fault_injection.build_event(
            site_id="S-1199", fault_type="string_loss", injected_from="2019-03-01",
            magnitude=None, assumptions=assumptions, unit_count=7)
        two = fault_injection.build_event(
            site_id="S-1203", fault_type="string_loss", injected_from="2019-03-01",
            magnitude=None, assumptions=assumptions, unit_count=2)
        self.assertAlmostEqual(seven["magnitude_pct"], 1 / 7, places=5)
        self.assertAlmostEqual(two["magnitude_pct"], 0.5, places=5)

    def test_ladder_never_targets_an_already_excluded_site(self):
        """S-1367 sits below the plausibility floor, so it is not in the
        analysis. A label there could never be matched by anything."""
        frames = self.frames()
        assumptions = fault_injection.load_assumptions()
        events = fault_injection.choose_events(frames, assumptions, seed=7, count=6)
        self.assertNotIn("S-1367", {event["site_id"] for event in events})

    def test_ladder_descends_in_severity(self):
        """A flat ladder has no failure region, which is the whole defence
        against 'you found faults you invented'."""
        frames = self.frames()
        events = fault_injection.choose_events(frames, fault_injection.load_assumptions(),
                                               seed=42, count=4)
        steps = [event["magnitude_pct"] for event in events
                 if event["fault_type"] == "step_drop" and event["magnitude_pct"]]
        self.assertEqual(steps, sorted(steps, reverse=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)

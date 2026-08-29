"""Tests for baseline.py — M2, the sensor-free expected-output model.

    python pipeline/test_baseline.py
    python -m unittest discover pipeline

WHY THESE EXIST. The baseline decides what "expected" means, and every RM figure
in the product is a shortfall against it. A baseline that is quietly wrong does
not fail loudly - it produces a plausible number, and the whole dispatch queue
is then confidently wrong in the same direction.

Two properties matter more than the rest, and most of these tests are about them:

  1. The derate calibration must be UNMOVED by a minority of faulty site-days.
     If it moves, a fault lowers the bar it is judged against and hides itself.
  2. The derate must be FLEET-WIDE. A per-site fit is a free parameter that
     absorbs the fault entirely.

stdlib unittest on purpose, matching test_validate_dispatch.py - the pipeline
does not take a pytest dependency.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import baseline  # noqa: E402


def make_params(**overrides):
    """Model params with the real config's shape, cheap to perturb."""
    params = baseline.load_model_params()
    for key, value in overrides.items():
        params["baseline"][key] = value
    return params


def synthetic_frames(site_count=5, days=100, ratio=0.8):
    """A modelled/actual pair whose true derate is exactly `ratio`."""
    dates = [(pd.Timestamp("2019-01-01") + pd.Timedelta(days=offset)).strftime("%Y-%m-%d")
             for offset in range(days)]
    rows_modelled = []
    rows_actual = []
    for index in range(site_count):
        site_id = "S-{:04d}".format(index)
        for day, date in enumerate(dates):
            modelled = 100.0 + day        # varies, always well above the floor
            rows_modelled.append({"site_id": site_id, "date": date,
                                  "modelled_kwh_raw": modelled})
            rows_actual.append({"site_id": site_id, "date": date,
                                "actual_kwh": modelled * ratio})
    return pd.DataFrame(rows_modelled), pd.DataFrame(rows_actual)


class UtcOffsetTests(unittest.TestCase):
    """The offset only decides which local day an hour lands on."""

    def test_longitude_maps_to_expected_offsets(self):
        from fetch_irradiance import utc_offset_hours
        self.assertEqual(utc_offset_hours(-75.5511), -5)    # Delaware, EST
        self.assertEqual(utc_offset_hours(-115.1582), -8)   # Las Vegas, PST
        self.assertEqual(utc_offset_hours(101.44), 7)       # Klang, near MYT


class DerateCalibrationTests(unittest.TestCase):

    def test_recovers_a_known_derate(self):
        modelled, actual = synthetic_frames(ratio=0.83)
        derate, diagnostics = baseline.calibrate_system_derate(
            modelled, actual, make_params())
        self.assertAlmostEqual(derate, 0.83, places=6)
        self.assertEqual(diagnostics["site_days_dropped_below_floor"], 0)

    def test_a_minority_of_faulty_sites_does_not_move_the_derate(self):
        """THE LOAD-BEARING PROPERTY. Two of five sites lose 40 % of output.

        A mean would drop about 16 %, lowering the expected bar for every
        healthy site in the fleet and shrinking the very shortfall the product
        is trying to report. The median must not move at all.
        """
        modelled, actual = synthetic_frames(site_count=5, ratio=0.80)
        faulty = actual["site_id"].isin(["S-0000", "S-0001"])
        actual.loc[faulty, "actual_kwh"] *= 0.60

        derate, _ = baseline.calibrate_system_derate(modelled, actual, make_params())
        self.assertAlmostEqual(derate, 0.80, places=6)

    def test_excluded_sites_are_left_out_of_the_fit(self):
        modelled, actual = synthetic_frames(site_count=5, ratio=0.80)
        actual.loc[actual["site_id"] == "S-0000", "actual_kwh"] *= 0.10

        derate, diagnostics = baseline.calibrate_system_derate(
            modelled, actual, make_params(), excluded_site_ids=["S-0000"])
        self.assertAlmostEqual(derate, 0.80, places=6)
        self.assertEqual(diagnostics["sites_excluded_from_calibration"], ["S-0000"])

    def test_site_days_below_the_floor_are_dropped(self):
        modelled, actual = synthetic_frames(site_count=2, days=10, ratio=0.8)
        modelled.loc[0, "modelled_kwh_raw"] = 0.001

        _, diagnostics = baseline.calibrate_system_derate(
            modelled, actual, make_params(min_modelled_kwh_for_calibration=5.0))
        self.assertEqual(diagnostics["site_days_dropped_below_floor"], 1)

    def test_no_usable_site_days_is_a_named_failure(self):
        """Not a silent zero. A baseline with nothing to fit on must say so."""
        modelled, actual = synthetic_frames(site_count=1, days=3)
        modelled["modelled_kwh_raw"] = 0.0
        with self.assertRaises(SystemExit):
            baseline.calibrate_system_derate(modelled, actual, make_params())


class AccuracyReportTests(unittest.TestCase):

    def test_perfect_model_reports_zero_error(self):
        expected = pd.DataFrame({
            "site_id": ["S-0001"] * 5,
            "date": ["2019-01-0{}".format(day) for day in range(1, 6)],
            "expected_kwh": [100.0] * 5,
            "actual_kwh": [100.0] * 5,
            "performance_ratio": [1.0] * 5,
        })
        report = baseline.accuracy_report(expected, make_params())
        self.assertEqual(report["site_days_scored"], 5)
        self.assertAlmostEqual(report["mean_bias_error_pct"], 0.0)
        self.assertAlmostEqual(report["normalised_rmse_pct"], 0.0)

    def test_excluded_sites_do_not_count_against_model_accuracy(self):
        """A broken FEED is not a test of the MODEL.

        S-1367 reports about a quarter of its plausible output. Scored, it puts
        a 75 % error into the fleet figure and reports a data-collection problem
        as a modelling problem.
        """
        expected = pd.DataFrame({
            "site_id": ["S-0001"] * 3 + ["S-9999"] * 3,
            "date": ["2019-01-0{}".format(day) for day in range(1, 4)] * 2,
            "expected_kwh": [100.0] * 6,
            "actual_kwh": [100.0, 100.0, 100.0, 25.0, 25.0, 25.0],
            "performance_ratio": [1.0, 1.0, 1.0, 0.25, 0.25, 0.25],
        })
        scored = baseline.accuracy_report(expected, make_params(), ["S-9999"])
        self.assertEqual(scored["site_days_scored"], 3)
        self.assertAlmostEqual(scored["mean_absolute_error_pct"], 0.0)


class PhysicsTests(unittest.TestCase):
    """The pvlib chain, exercised on one site's worth of real irradiance."""

    @classmethod
    def setUpClass(cls):
        cls.irradiance = baseline.load_irradiance()
        if cls.irradiance is None:
            raise unittest.SkipTest(
                "no irradiance cache — run pipeline/fetch_irradiance.py")
        cls.params = baseline.load_model_params()
        cls.site = baseline.load_fleet_sites()[0]

    def hourly(self):
        site_id = baseline.build_site_id(self.site["source_system_id"])
        frame = self.irradiance[self.irradiance["site_id"] == site_id]
        return baseline.model_site_hourly(
            frame, float(self.site["lat"]), float(self.site["lon"]),
            float(self.site["capacity_kwp"]), self.params["baseline"])

    def test_output_is_never_negative(self):
        self.assertGreaterEqual(float(self.hourly().min()), 0.0)

    def test_night_produces_nothing(self):
        """Transposition models return a positive geometric term below the
        horizon. Night has to be forced to zero or the baseline expects output
        from a dark roof."""
        site_id = baseline.build_site_id(self.site["source_system_id"])
        frame = self.irradiance[self.irradiance["site_id"] == site_id].sort_values(
            "timestamp_utc")
        dark = frame["ghi_w_m2"].to_numpy() <= 0
        produced = self.hourly().to_numpy()
        self.assertTrue((produced[dark] == 0).all())

    def test_never_exceeds_nameplate_by_a_wide_margin(self):
        """PVWatts can exceed nameplate on a cold bright day, which is real.
        Twice nameplate is not - it means an irradiance or unit error."""
        capacity = float(self.site["capacity_kwp"])
        self.assertLess(float(self.hourly().max()), capacity * 2.0)


class WindowTrimTests(unittest.TestCase):
    """The UTC-to-local shift pulls in a partial day that has no measurement."""

    def test_modelled_days_outside_the_measured_window_are_dropped(self):
        irradiance = baseline.load_irradiance()
        actual = baseline.load_actual_daily()
        if irradiance is None or actual is None:
            self.skipTest("needs the irradiance cache and fleet_daily.parquet")

        sites = baseline.load_fleet_sites()
        expected, _ = baseline.build_expected(
            sites, irradiance, actual, baseline.load_model_params(),
            excluded_site_ids=baseline.plausibility_excluded_site_ids())

        self.assertEqual(set(expected["date"]) - set(actual["date"]), set())
        self.assertNotIn("2018-12-31", set(expected["date"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

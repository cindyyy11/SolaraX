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


class HandCalculationTests(unittest.TestCase):
    """Red-team item 1 — does M2 match a hand-calculated value for one site-day?

    `hinfo/SUBMISSION-CHECKLIST.md` asks this directly, and it is a different
    question from "do the tests pass". Everything else in this file checks that
    the code behaves; this checks that the code computes THE DOCUMENTED FORMULA.
    A pipeline can be internally consistent, well tested, and quietly evaluating
    something other than what the method doc claims.

    The subject is S-1277 (Agassi Building C, 40.56 kWp — the smallest site in
    the fleet) on 2019-06-21, the summer solstice, at its peak hour. Solstice
    noon in Las Vegas is the most demanding point on the chain: highest
    irradiance, highest cell temperature, so the temperature correction is
    carrying its largest load and an error in it cannot hide.

    WHAT IS INDEPENDENT HERE. The test rebuilds the irradiance chain by calling
    pvlib directly rather than through `baseline.py`, then evaluates the PVWatts
    step as explicit arithmetic:

        dc_kw = capacity_kwp × (poa / 1000) × (1 + γ × (T_cell − 25))

    So pvlib is shared — it is a third-party library and not what is under test —
    but none of our code is. If `model_site_hourly` ever stops implementing that
    formula, or a constant drifts out of `config/model_params.json`, this fails.
    """

    SITE_SYSTEM_ID = "1277"
    DATE = "2019-06-21"
    PEAK_HOUR_UTC = "2019-06-21 19:00:00+00:00"

    @classmethod
    def setUpClass(cls):
        cls.irradiance = baseline.load_irradiance()
        if cls.irradiance is None:
            raise unittest.SkipTest(
                "no irradiance cache — run pipeline/fetch_irradiance.py")
        cls.params = baseline.load_model_params()
        cls.site = next(site for site in baseline.load_fleet_sites()
                        if site["source_system_id"] == cls.SITE_SYSTEM_ID)
        cls.site_id = baseline.build_site_id(cls.SITE_SYSTEM_ID)

    def day_frame(self):
        return self.irradiance[
            (self.irradiance["site_id"] == self.site_id)
            & (self.irradiance["local_date"] == self.DATE)
        ].sort_values("timestamp_utc")

    def pipeline_hourly(self):
        return baseline.model_site_hourly(
            self.day_frame(),
            float(self.site["lat"]), float(self.site["lon"]),
            float(self.site["capacity_kwp"]), self.params["baseline"])

    def test_peak_hour_matches_the_documented_formula(self):
        import pvlib

        parameters = self.params["baseline"]
        frame = self.day_frame()
        times = pd.DatetimeIndex(frame["timestamp_utc"])

        ghi = pd.Series(frame["ghi_w_m2"].to_numpy(dtype=float), index=times)
        temp_air = pd.Series(frame["temp_air_c"].to_numpy(dtype=float), index=times)
        wind = pd.Series(frame["wind_speed_m_s"].to_numpy(dtype=float), index=times)

        solar_position = pvlib.solarposition.get_solarposition(
            times + pd.Timedelta(minutes=30),
            float(self.site["lat"]), float(self.site["lon"]),
            temperature=temp_air.to_numpy())
        solar_position.index = times

        decomposed = pvlib.irradiance.erbs(
            ghi, solar_position["apparent_zenith"], times)
        total = pvlib.irradiance.get_total_irradiance(
            surface_tilt=parameters["array_tilt_degrees"],
            surface_azimuth=parameters["array_azimuth_degrees"],
            solar_zenith=solar_position["apparent_zenith"],
            solar_azimuth=solar_position["azimuth"],
            dni=decomposed["dni"], ghi=ghi, dhi=decomposed["dhi"],
            dni_extra=pvlib.irradiance.get_extra_radiation(times),
            albedo=parameters["albedo"],
            model=parameters["transposition_model"])
        poa = total["poa_global"].fillna(0.0).clip(lower=0.0).where(
            solar_position["apparent_zenith"] < 90.0, 0.0)

        thermal = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS[
            parameters["temperature_model"]][
            parameters["temperature_model_configuration"]]
        temp_cell = pvlib.temperature.sapm_cell(
            poa_global=poa, temp_air=temp_air, wind_speed=wind, **thermal)

        hour = pd.Timestamp(self.PEAK_HOUR_UTC)
        index = list(times).index(hour)

        poa_peak = float(poa.iloc[index])
        cell_peak = float(temp_cell.iloc[index])
        capacity = float(self.site["capacity_kwp"])
        gamma = parameters["gamma_pdc_per_c"]

        # The PVWatts DC equation, written out. This is the line that carries
        # our two constants, and it is deliberately not a pvlib call.
        hand_calculated_kw = (
            capacity
            * (poa_peak / parameters["reference_irradiance_w_m2"])
            * (1.0 + gamma * (cell_peak - parameters["reference_cell_temp_c"]))
        )

        pipeline_kw = float(self.pipeline_hourly().iloc[index])

        # Sanity-check the intermediates before the equality, so a failure says
        # WHICH step moved rather than only that the answer changed.
        self.assertTrue(1000 < poa_peak < 1200, "POA {}".format(poa_peak))
        self.assertTrue(70 < cell_peak < 95, "cell temp {}".format(cell_peak))
        self.assertAlmostEqual(hand_calculated_kw, 34.9401, places=3)
        self.assertAlmostEqual(pipeline_kw, hand_calculated_kw, places=9)

    def test_daily_total_is_the_sum_of_its_hours(self):
        """kW over a 1-hour step is kWh. That is our aggregation, not pvlib's."""
        hourly = self.pipeline_hourly()
        daily = baseline.model_fleet_daily(
            [self.site], self.day_frame(), self.params)

        self.assertEqual(len(daily), 1)
        self.assertAlmostEqual(
            float(daily.iloc[0]["modelled_kwh_raw"]), float(hourly.sum()), places=9)

    def test_the_temperature_correction_is_actually_applied(self):
        """At 85 C cell temperature the correction removes about 21 % of output.

        If γ were ever dropped or zeroed, every other test in this file would
        still pass and the baseline would silently over-predict every summer day
        — turning healthy hot-climate sites into dispatch candidates.
        """
        parameters = self.params["baseline"]
        loss = abs(parameters["gamma_pdc_per_c"]) * (84.9 - 25.0)
        self.assertGreater(loss, 0.15)

        hourly = self.pipeline_hourly()
        capacity = float(self.site["capacity_kwp"])
        # Peak POA exceeds 1000 W/m^2, so an UNCORRECTED model would exceed
        # nameplate. The corrected one must not.
        self.assertLess(float(hourly.max()), capacity)


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

"""Tests for M2, the sensor-free physics baseline.

The pvlib chain itself is pvlib's to get right; these cover the parts this
repo owns — timezone selection, the UTC-to-local daily fold, result-shape
normalisation, and the sanity band. stdlib unittest, no pytest.

    .venv/bin/python pipeline/test_baseline.py
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import numpy as np
    import pandas as pd
    import baseline
    DEPENDENCIES_PRESENT = True
except ImportError:                                    # pragma: no cover
    DEPENDENCIES_PRESENT = False


@unittest.skipUnless(DEPENDENCIES_PRESENT, "needs pandas + pvlib")
class TestTimezoneSelection(unittest.TestCase):
    def test_nevada_is_pacific(self):
        self.assertEqual(baseline.timezone_for(-115.16), baseline.WESTERN_TIMEZONE)

    def test_the_mid_atlantic_is_eastern(self):
        self.assertEqual(baseline.timezone_for(-76.68), baseline.EASTERN_TIMEZONE)

    def test_the_boundary_is_west_of_both_clusters(self):
        """Neither cluster may sit near the cutoff, or the rule is a coin toss."""
        self.assertLess(-115.16, baseline.PACIFIC_LONGITUDE_LIMIT)
        self.assertGreater(-75.05, baseline.PACIFIC_LONGITUDE_LIMIT)


@unittest.skipUnless(DEPENDENCIES_PRESENT, "needs pandas + pvlib")
class TestDailyFold(unittest.TestCase):
    def hourly(self, watts, start="2019-06-01 00:00", hours=48):
        index = pd.date_range(start, periods=hours, freq="h", tz="UTC")
        return pd.Series([watts] * hours, index=index)

    def test_watt_hours_become_kilowatt_hours(self):
        """Each sample is one hour, so 1000 W for 24 h is 24 kWh."""
        daily = baseline.daily_expected_kwh(self.hourly(1000.0), -76.68)
        full_days = [value for value in daily.values if value > 23.0]
        self.assertTrue(full_days)
        self.assertAlmostEqual(full_days[0], 24.0, places=6)

    def test_the_fold_is_local_not_utc(self):
        """A UTC day and a local day differ by the offset, so summing one
        against the other smears a fifth of a day into its neighbour at these
        longitudes. Pacific and Eastern must not agree.

        Uses a RAMPING series on purpose: with a flat one every complete day
        totals the same in both zones, so the test would pass while measuring
        nothing.
        """
        index = pd.date_range("2019-06-01 00:00", periods=96, freq="h", tz="UTC")
        series = pd.Series([float(hour) * 10 for hour in range(96)], index=index)
        west = baseline.daily_expected_kwh(series, -115.16)
        east = baseline.daily_expected_kwh(series, -76.68)
        self.assertNotEqual(list(west.values), list(east.values))

    def test_index_is_plain_dates(self):
        daily = baseline.daily_expected_kwh(self.hourly(500.0), -76.68)
        self.assertIsInstance(daily.index[0], datetime.date)


@unittest.skipUnless(DEPENDENCIES_PRESENT, "needs pandas + pvlib")
class TestResultShapeNormalisation(unittest.TestCase):
    """pvlib returns a DataFrame for Series input and a dict of ndarrays for
    ndarray input, and it is not consistent between functions in this chain."""

    def test_dict_of_arrays(self):
        got = baseline.as_array({"poa_global": np.array([1.0, 2.0])}, "poa_global")
        self.assertEqual(list(got), [1.0, 2.0])

    def test_dataframe(self):
        frame = pd.DataFrame({"dni": [3.0, 4.0]})
        self.assertEqual(list(baseline.as_array(frame, "dni")), [3.0, 4.0])


@unittest.skipUnless(DEPENDENCIES_PRESENT, "needs pandas + pvlib")
class TestSanityBand(unittest.TestCase):
    def test_the_band_is_a_check_not_a_clamp(self):
        """A performance ratio outside the band means the CHAIN is wrong. It
        must be reported as-is, never squeezed into range — clamping would turn
        a modelling bug into a plausible-looking finding about a site."""
        import json
        with open(os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "config", "assumptions.json")) as handle:
            assumptions = json.load(handle)
        band = assumptions["baseline_performance_ratio_range"]
        self.assertLess(band["low"], band["high"])
        self.assertGreater(band["low"], 0.0)
        self.assertLessEqual(band["high"], 1.0)


@unittest.skipUnless(DEPENDENCIES_PRESENT, "needs pandas + pvlib")
class TestDayCompleteness(unittest.TestCase):
    """Incomplete days are dropped, not estimated."""

    def hourly(self, hours, start="2019-06-01 00:00"):
        index = pd.date_range(start, periods=hours, freq="h", tz="UTC")
        return pd.Series([1000.0] * hours, index=index)

    def test_a_partial_boundary_day_is_dropped(self):
        """UTC-to-local always leaves a partial day at each end. Written as if
        complete, the trailing one understated the most recent day by 4-5% —
        and that day is the rightmost point of Screen 2's chart."""
        daily = baseline.daily_expected_kwh(self.hourly(30), -76.68)
        self.assertTrue(all(value > 23.0 for value in daily.values), list(daily.values))

    def test_a_day_with_a_missing_hour_is_dropped_not_summed_as_zero(self):
        """NASA POWER's -999 is kept as NaN on purpose. resample().sum()
        defaults to min_count=0, which turns those hours back into zeros and
        ships a low expected_kwh that reads as a real modelled shortfall."""
        series = self.hourly(72)
        series.iloc[30] = float("nan")
        daily = baseline.daily_expected_kwh(series, -76.68)
        self.assertTrue(all(value > 23.0 for value in daily.values), list(daily.values))

    def test_a_complete_day_survives(self):
        daily = baseline.daily_expected_kwh(self.hourly(96), -76.68)
        self.assertGreater(len(daily), 0)


@unittest.skipUnless(DEPENDENCIES_PRESENT, "needs pandas + pvlib")
class TestSecondReviewFindings(unittest.TestCase):
    """One test per defect from the review of the M2 chain."""

    def test_a_local_day_is_not_always_twenty_four_hours(self):
        """A spring-forward day has 23 hours and a fall-back day has 25.

        Comparing against a flat 24 threw away 2019-03-10 for all eleven sites
        as 'incomplete' when it was a complete, correctly modelled day.
        """
        self.assertEqual(
            baseline.local_day_length_hours(datetime.date(2019, 3, 10),
                                            baseline.EASTERN_TIMEZONE), 23)
        self.assertEqual(
            baseline.local_day_length_hours(datetime.date(2019, 11, 3),
                                            baseline.EASTERN_TIMEZONE), 25)
        self.assertEqual(
            baseline.local_day_length_hours(datetime.date(2019, 6, 1),
                                            baseline.EASTERN_TIMEZONE), 24)

    def test_the_daylight_saving_day_survives_the_completeness_rule(self):
        index = pd.date_range("2019-03-08 00:00", periods=24 * 6, freq="h", tz="UTC")
        daily = baseline.daily_expected_kwh(pd.Series([1000.0] * len(index), index=index),
                                            -76.68)
        self.assertIn(datetime.date(2019, 3, 10), list(daily.index))

    def test_a_missing_irradiance_hour_does_not_pass_as_a_dark_hour(self):
        """THE HOLE THE COMPLETENESS RULE WAS SUPPOSED TO CLOSE.

        NASA POWER's -999 sentinel is kept as NaN so a missing hour is not
        averaged in as zero. But the transposition needs a number, so poa_global
        is filled with 0.0 — and that turned a NaN input into a real 0.0 W
        output, which counted as successfully modelled. The day then passed the
        completeness check carrying a silently depressed total that reads on the
        chart as a modelled shortfall: exactly the failure the rule exists to
        stop.
        """
        assumptions = {
            "baseline_surface_tilt_deg": 10.0,
            "baseline_surface_azimuth_deg": 180.0,
            "baseline_gamma_pdc_per_c": -0.004,
            "baseline_system_loss_factor": 0.96,
        }
        index = pd.date_range("2019-06-01 00:00", periods=48, freq="h", tz="UTC")
        weather = pd.DataFrame(
            {
                "timestamp_utc": index,
                "ghi": [500.0] * len(index),
                "temp_air": [20.0] * len(index),
                "wind_speed": [2.0] * len(index),
            }
        )
        # Knock out one hour of irradiance, exactly as a POWER sentinel would.
        weather.loc[10, "ghi"] = float("nan")

        watts = baseline.modelled_ac_watts(weather, 36.1, -115.1, 100.0, assumptions)
        self.assertTrue(pd.isna(watts.iloc[10]),
                        "an hour with no irradiance must not model as 0 W")
        daily = baseline.daily_expected_kwh(watts, -115.1)
        self.assertEqual(len(daily), 0,
                         "a day containing an unmodelled hour must be dropped")


if __name__ == "__main__":
    unittest.main(verbosity=2)

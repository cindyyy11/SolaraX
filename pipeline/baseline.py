"""M2 — the sensor-free physics baseline.

    .venv/bin/python pipeline/baseline.py            # report, write nothing
    .venv/bin/python pipeline/baseline.py --write    # -> data/processed/baseline_daily.parquet

WHAT IT IS FOR, AND WHAT IT IS NOT FOR. This models what each site SHOULD have
produced, from satellite irradiance and published physics, with no on-site
sensor anywhere in the chain. It is a CROSS-CHECK on M3, not a replacement for
it and not a prerequisite of it — M3 runs without this file and always did.

    M3 compares a site to its peers. That catches a single site failing, and
    it is blind to a whole cohort degrading together, because the peers move
    with it. This is the answer to exactly that blind spot: it has an
    absolute reference, so a cohort sinking as one still shows up against it.

    The trade runs the other way too. This needs array geometry that PVDAQ
    does not publish, so tilt and azimuth are assumed (config/assumptions.json).
    M3 needs no geometry at all. That is why M3 is the load-bearing detector
    and this is the corroborating one.

THE CHAIN, per docs/ARCHITECTURE.md section 3.2:

    NASA POWER hourly GHI, air temperature, wind speed
      -> pvlib.solarposition.get_solarposition
      -> pvlib.irradiance.erbs                     GHI split into DNI and DHI
      -> pvlib.irradiance.get_total_irradiance     plane-of-array
      -> pvlib.temperature.sapm_cell               open_rack_glass_glass
      -> pvlib.pvsystem.pvwatts_dc                 gamma_pdc from config
      -> x baseline_system_loss_factor             DC to AC
      -> resample to daily kWh in the site's LOCAL time

The local-time resample matters: PVDAQ's daily totals are local days, and
summing a UTC day against a local day would smear roughly a fifth of one
day's generation into its neighbour at these longitudes.
"""

import argparse
import datetime
import os
import sys

import numpy as np
import pandas as pd
import pvlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import generate_dispatch

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IRRADIANCE_PATH = os.path.join(REPOSITORY_ROOT, "data", "processed",
                               "irradiance_hourly.parquet")
OUTPUT_PATH = os.path.join(REPOSITORY_ROOT, "data", "processed",
                           "baseline_daily.parquet")

# The two clusters this fleet occupies. Derived from longitude rather than
# looked up, because the fleet spans exactly two US timezones and a lookup
# table would be a dependency for one branch. Stated so it is checkable, and it
# fails loudly below if a site ever lands between them.
PACIFIC_LONGITUDE_LIMIT = -100.0
WESTERN_TIMEZONE = "America/Los_Angeles"
EASTERN_TIMEZONE = "America/New_York"

WATTS_TO_KILOWATT_HOURS = 1000.0

# A local day is only written when EVERY one of its hours modelled
# successfully — 23, 24 or 25 of them depending on daylight saving.
# This single rule closes two holes at once:
#
#   1. NASA POWER's -999 sentinel is deliberately kept as NaN by
#      fetch_irradiance.py, precisely so missing hours are not averaged in as
#      zero. But NaN temperature or wind flows through sapm_cell and pvwatts_dc
#      to a NaN watt-hour, and Series.resample("D").sum() defaults to
#      min_count=0 — which turns those NaN hours back into zeros and ships a
#      low expected_kwh that reads on Screen 2 as a real modelled shortfall.
#      Exactly the failure the fetch script's comment says it is avoiding.
#
#   2. The UTC-to-local conversion always produces a partial day at each end:
#      a leading local day holding only the hours that fell inside the UTC
#      window, and a trailing one truncated by the same offset. Written as if
#      complete, the trailing one understates the most recent day by 4-5% —
#      and that day is the rightmost point of the chart.
#
# Comparing against a FLAT 24 got the second case right and the daylight-saving
# case wrong: a spring-forward local day has 23 hours, so 2019-03-10 was thrown
# away for all eleven sites as "incomplete" when it was nothing of the kind.
# The length of a local day is asked for, not assumed.
HOURS_PER_STANDARD_DAY = 24

# pvlib's SAPM cell-temperature parameters for the mounting named in
# ARCHITECTURE section 3.2.
TEMPERATURE_MODEL = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"][
    "open_rack_glass_glass"]


def as_array(container, key):
    """Pull one column out of a pvlib result as a plain numpy array.

    pvlib returns a DataFrame for Series input and a dict of ndarrays for
    ndarray input, and it is not consistent between functions in this chain —
    erbs gives a DataFrame here while get_total_irradiance gives a dict. This
    normalises both rather than depending on which one a version happens to
    hand back.
    """
    value = container[key]
    return np.asarray(value)


def timezone_for(longitude):
    return WESTERN_TIMEZONE if longitude < PACIFIC_LONGITUDE_LIMIT else EASTERN_TIMEZONE


def load_irradiance():
    if not os.path.exists(IRRADIANCE_PATH):
        raise SystemExit(
            "missing {}. Run pipeline/fetch_irradiance.py first.".format(
                os.path.relpath(IRRADIANCE_PATH, REPOSITORY_ROOT)))
    frame = pd.read_parquet(IRRADIANCE_PATH)
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
    return frame


def modelled_ac_watts(weather, latitude, longitude, capacity_kwp, assumptions):
    """Run the pvlib chain for one location. Returns an hourly AC watt series."""
    times = pd.DatetimeIndex(weather["timestamp_utc"])
    solar_position = pvlib.solarposition.get_solarposition(
        times, latitude, longitude,
        temperature=weather["temp_air"].to_numpy())

    # GHI is all POWER publishes. Erbs splits it into the direct and diffuse
    # components the transposition needs. A decomposition model is an
    # approximation and is the largest single source of error in this chain —
    # stated rather than hidden, and another reason M3 leads.
    decomposed = pvlib.irradiance.erbs(
        weather["ghi"].to_numpy(), solar_position["zenith"].to_numpy(), times)

    total = pvlib.irradiance.get_total_irradiance(
        surface_tilt=assumptions["baseline_surface_tilt_deg"],
        surface_azimuth=assumptions["baseline_surface_azimuth_deg"],
        solar_zenith=solar_position["apparent_zenith"].to_numpy(),
        solar_azimuth=solar_position["azimuth"].to_numpy(),
        dni=as_array(decomposed, "dni"),
        ghi=weather["ghi"].to_numpy(),
        dhi=as_array(decomposed, "dhi"),
    )
    # An hour is only modelled when every input it needs was present. NASA
    # POWER's -999 sentinel is kept as NaN by fetch_irradiance.py precisely so
    # a missing hour is not treated as a dark one, and that intent has to
    # survive this function.
    #
    # THE fillna BELOW USED TO DEFEAT IT. Zeroing a NaN GHI produced a real
    # 0.0 W rather than NaN, so the hour counted as successfully modelled and
    # the day passed the completeness check with a silently depressed total —
    # the exact failure the check exists to stop. NaN in temperature or wind
    # propagates on its own; GHI was the hole. The fill stays, because the
    # transposition needs a number, but the mask is taken BEFORE it and the
    # result is re-masked after.
    usable_hour = (
        weather["ghi"].notna()
        & weather["temp_air"].notna()
        & weather["wind_speed"].notna()
    ).to_numpy()

    poa_global = pd.Series(as_array(total, "poa_global"), index=times).fillna(0.0)

    cell_temperature = pvlib.temperature.sapm_cell(
        poa_global.to_numpy(),
        weather["temp_air"].to_numpy(),
        weather["wind_speed"].to_numpy(),
        **TEMPERATURE_MODEL)

    dc_watts = pvlib.pvsystem.pvwatts_dc(
        effective_irradiance=poa_global.to_numpy(),
        temp_cell=cell_temperature,
        pdc0=capacity_kwp * 1000.0,
        gamma_pdc=assumptions["baseline_gamma_pdc_per_c"])

    ac_watts = pd.Series(dc_watts, index=times) * assumptions["baseline_system_loss_factor"]
    ac_watts = ac_watts.clip(lower=0.0)
    return ac_watts.where(usable_hour)


def local_day_length_hours(day, timezone):
    """How many hours this particular local calendar day actually has.

    24 almost always; 23 on a spring-forward day and 25 on a fall-back one.
    Derived from the timezone rather than assumed, because assuming discards a
    real day twice a year.
    """
    start = pd.Timestamp(day, tz=timezone)
    end = pd.Timestamp(day + datetime.timedelta(days=1), tz=timezone)
    return int((end - start).total_seconds() // 3600)


def daily_expected_kwh(ac_watts, longitude):
    """Hourly AC watts (UTC) -> expected kWh per COMPLETE local calendar day.

    Incomplete days are dropped, not estimated. A partial day is not a low-yield
    day, and writing one as if it were complete puts a modelling artifact on the
    chart in the shape of a fault — which is the one thing this baseline exists
    to help distinguish.
    """
    timezone = timezone_for(longitude)
    local = ac_watts.tz_convert(timezone)

    # Each sample represents one hour, so watts and watt-hours coincide.
    totals = local.resample("D").sum(min_count=1) / WATTS_TO_KILOWATT_HOURS
    modelled_hours = local.notna().resample("D").sum()

    complete = pd.Series(
        [
            modelled_hours.loc[stamp] >= local_day_length_hours(stamp.date(), timezone)
            for stamp in totals.index
        ],
        index=totals.index,
    )

    daily = totals[complete]
    daily.index = daily.index.date
    return daily


def build_fleet_baseline(assumptions=None):
    """Expected daily kWh for every site. Returns a tidy frame."""
    assumptions = assumptions or generate_dispatch.load_assumptions()
    irradiance = load_irradiance()
    sites = generate_dispatch.load_fleet_sites()

    rows = []
    for site in sites:
        latitude = round(site["lat"], 4)
        longitude = round(site["lon"], 4)
        weather = irradiance[(irradiance["lat"] == latitude)
                             & (irradiance["lon"] == longitude)]
        if weather.empty:
            raise SystemExit(
                "no irradiance for {} at {},{} — re-run pipeline/fetch_irradiance.py".format(
                    site["source_system_id"], latitude, longitude))

        ac_watts = modelled_ac_watts(
            weather.sort_values("timestamp_utc"), latitude, longitude,
            site["capacity_kwp"], assumptions)
        daily = daily_expected_kwh(ac_watts, longitude)

        site_id = generate_dispatch.build_site_id(site["source_system_id"])
        for day, kwh in daily.items():
            rows.append({
                "site_id": site_id,
                "date": day.isoformat(),
                "expected_kwh": round(float(kwh), 2),
                "capacity_kwp": site["capacity_kwp"],
                "expected_performance_index": round(
                    float(kwh) / site["capacity_kwp"], 4),
            })
    return pd.DataFrame(rows)


def performance_ratios(baseline, assumptions):
    """Actual / expected per site over the window — the sanity check.

    docs/ARCHITECTURE.md section 3.2 puts a band on this. A modelled baseline
    implying a PR outside it is a bug in the chain, not a finding about the
    site, and it is reported loudly rather than clamped into range.
    """
    actual = generate_dispatch.load_real_daily_series()
    remapped = {}
    for _, row in baseline.iterrows():
        remapped.setdefault(row["site_id"], {})[
            generate_dispatch.remap_date(row["date"])] = row["expected_kwh"]

    results = []
    low = assumptions["baseline_performance_ratio_range"]["low"]
    high = assumptions["baseline_performance_ratio_range"]["high"]
    for site_id, series in sorted((actual or {}).items()):
        expected_by_date = remapped.get(site_id, {})
        pairs = [(row["actual_kwh"], expected_by_date.get(row["date"]))
                 for row in series]
        pairs = [(a, e) for a, e in pairs if e]
        if not pairs:
            continue
        total_actual = sum(a for a, _ in pairs)
        total_expected = sum(e for _, e in pairs)
        ratio = total_actual / total_expected if total_expected else None
        results.append({
            "site_id": site_id,
            "days": len(pairs),
            "performance_ratio": ratio,
            "in_band": bool(ratio is not None and low <= ratio <= high),
        })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true",
                        help="write data/processed/baseline_daily.parquet")
    args = parser.parse_args()

    assumptions = generate_dispatch.load_assumptions()
    baseline = build_fleet_baseline(assumptions)
    ratios = performance_ratios(baseline, assumptions)

    band = assumptions["baseline_performance_ratio_range"]
    print("M2 sensor-free baseline — pvlib chain on NASA POWER irradiance")
    print("=" * 62)
    print("  tilt {}deg  azimuth {}deg  gamma_pdc {}  system loss factor {}".format(
        assumptions["baseline_surface_tilt_deg"],
        assumptions["baseline_surface_azimuth_deg"],
        assumptions["baseline_gamma_pdc_per_c"],
        assumptions["baseline_system_loss_factor"]))
    print()
    print("  {:<9} {:>6} {:>9}  {}".format("site", "days", "PR", "sanity band {}-{}".format(
        band["low"], band["high"])))
    for row in ratios:
        print("  {:<9} {:>6} {:>8.1%}  {}".format(
            row["site_id"], row["days"], row["performance_ratio"],
            "ok" if row["in_band"] else "OUT OF BAND"))

    out_of_band = [row["site_id"] for row in ratios if not row["in_band"]]
    print()
    if out_of_band:
        print("  {} site(s) outside the band: {}".format(
            len(out_of_band), ", ".join(out_of_band)))
        print("  A PR outside the band means the CHAIN is wrong, not the site.")
    else:
        print("  every site inside the sanity band")

    if args.write:
        baseline.to_parquet(OUTPUT_PATH, index=False)
        print()
        print("wrote {} ({:.0f} KB, {:,} rows)".format(
            os.path.relpath(OUTPUT_PATH, REPOSITORY_ROOT),
            os.path.getsize(OUTPUT_PATH) / 1024, len(baseline)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

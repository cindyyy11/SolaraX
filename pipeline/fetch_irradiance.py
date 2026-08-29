"""Pull hourly satellite irradiance and weather from NASA POWER.

    .venv/bin/python pipeline/fetch_irradiance.py

Writes data/processed/irradiance_hourly.parquet — the only weather input the
M2 baseline uses. No pyranometer, ever; that is the wedge.

WHY NASA POWER AND NOT PVGIS. CLAUDE.md makes this a hard rule: one irradiance
source across every cohort, because M3's error-cancellation argument only holds
if cohort members share it. The PVGIS-ERA5 pull in data/ is a Malaysian
market-context artifact for the pitch, not a pipeline input — different job.

WHY HOURLY. docs/ARCHITECTURE.md section 3.2 specifies a chain that needs a
solar position and a plane-of-array transposition, and neither is meaningful on
a daily mean. Daily GHI would collapse a clear morning and an overcast
afternoon into the same number as a flat grey day.

COORDINATES ARE DEDUPLICATED. Five of the eleven sites share byte-identical
coordinates (the Agassi roofs), so eleven sites need seven requests. The cache
is keyed on the rounded coordinate, not on site_id.

Values are UTC. The local-time resampling that turns them into daily kWh
happens in baseline.py, where the site's timezone is known.
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.request

import pandas as pd

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLEET_SITES_PATH = os.path.join(REPOSITORY_ROOT, "config", "fleet_sites.csv")
OUTPUT_PATH = os.path.join(REPOSITORY_ROOT, "data", "processed",
                           "irradiance_hourly.parquet")

ENDPOINT = "https://power.larc.nasa.gov/api/temporal/hourly/point"

# ALLSKY_SFC_SW_DWN is global horizontal irradiance in W/m2. T2M is air
# temperature at 2 m in C. WS2M is wind speed at 2 m in m/s — the SAPM cell
# temperature model wants wind at module height, and 2 m is the closer of the
# two heights POWER publishes.
PARAMETERS = "ALLSKY_SFC_SW_DWN,T2M,WS2M"

# POWER uses -999 as its no-data sentinel. Left as NaN rather than zero: a
# missing hour is not a dark hour, and averaging zeros into a daily total would
# quietly depress the baseline on exactly the days data is worst.
MISSING_SENTINEL = -999.0

# The window CLAUDE.md pins the fleet to, in source-calendar dates.
DEFAULT_START = "20190101"
DEFAULT_END = "20190821"

REQUEST_PAUSE_SECONDS = 1.0
MAX_ATTEMPTS = 3


def load_coordinates():
    """Unique (lat, lon) pairs across the fleet, with the sites at each."""
    frame = pd.read_csv(FLEET_SITES_PATH)
    frame["lat_key"] = frame["lat"].round(4)
    frame["lon_key"] = frame["lon"].round(4)
    grouped = {}
    for record in frame.to_dict("records"):
        key = (record["lat_key"], record["lon_key"])
        grouped.setdefault(key, []).append(str(record["source_system_id"]))
    return grouped


def build_url(latitude, longitude, start, end):
    return ("{endpoint}?parameters={parameters}&community=RE"
            "&longitude={lon}&latitude={lat}&start={start}&end={end}&format=JSON").format(
                endpoint=ENDPOINT, parameters=PARAMETERS,
                lon=longitude, lat=latitude, start=start, end=end)


def fetch_point(latitude, longitude, start, end):
    """One POWER request, with retries. Returns the parameter dict."""
    url = build_url(latitude, longitude, start, end)
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                payload = json.load(response)
            return payload["properties"]["parameter"]
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as error:
            last_error = error
            if attempt < MAX_ATTEMPTS:
                time.sleep(REQUEST_PAUSE_SECONDS * attempt * 2)
    raise SystemExit("NASA POWER failed for {},{} after {} attempts: {}".format(
        latitude, longitude, MAX_ATTEMPTS, last_error))


def to_frame(parameters, latitude, longitude):
    """POWER's {param: {YYYYMMDDHH: value}} -> a tidy hourly frame in UTC."""
    frame = pd.DataFrame({
        "ghi": pd.Series(parameters["ALLSKY_SFC_SW_DWN"]),
        "temp_air": pd.Series(parameters["T2M"]),
        "wind_speed": pd.Series(parameters["WS2M"]),
    })
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d%H", utc=True)
    frame = frame.sort_index()
    frame = frame.mask(frame <= MISSING_SENTINEL)
    frame["lat"] = latitude
    frame["lon"] = longitude
    frame.index.name = "timestamp_utc"
    return frame.reset_index()


def fetch_fleet(start, end):
    coordinates = load_coordinates()
    print("{} unique coordinate(s) for the fleet".format(len(coordinates)))
    frames = []
    for index, ((latitude, longitude), systems) in enumerate(sorted(coordinates.items()), 1):
        print("  [{}/{}] {:.4f}, {:.4f}  systems {}".format(
            index, len(coordinates), latitude, longitude, ",".join(sorted(systems))))
        parameters = fetch_point(latitude, longitude, start, end)
        frames.append(to_frame(parameters, latitude, longitude))
        time.sleep(REQUEST_PAUSE_SECONDS)
    return pd.concat(frames, ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", default=DEFAULT_START, help="YYYYMMDD")
    parser.add_argument("--end", default=DEFAULT_END, help="YYYYMMDD")
    args = parser.parse_args()

    frame = fetch_fleet(args.start, args.end)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    frame.to_parquet(OUTPUT_PATH, index=False)

    missing = frame["ghi"].isna().sum()
    print()
    print("wrote {}".format(os.path.relpath(OUTPUT_PATH, REPOSITORY_ROOT)))
    print("  rows          {:,}".format(len(frame)))
    print("  locations     {}".format(frame.groupby(["lat", "lon"]).ngroups))
    print("  span          {} .. {}".format(
        frame["timestamp_utc"].min().date(), frame["timestamp_utc"].max().date()))
    print("  missing GHI   {:,} ({:.2%})".format(missing, missing / len(frame)))
    print("  size          {:.0f} KB".format(os.path.getsize(OUTPUT_PATH) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

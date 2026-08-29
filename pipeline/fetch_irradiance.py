"""Pull satellite irradiance and ambient temperature for every fleet site.

WHY NASA POWER, AND WHY ONLY NASA POWER. `CLAUDE.md` makes this a hard rule:
one irradiance source across all cohorts. M3's error-cancellation argument is
that satellite irradiance carries error, but every site in a cohort shares that
error, so it cancels in the peer comparison. Mix two providers inside one cohort
and that argument is simply false — the residual is then provider bias, not
site health.

The PVGIS-Klang file in `data/` is a Malaysian market-context artifact for the
pitch. It is NOT a pipeline input. Different job, different file, no overlap.

WHAT THIS PULLS
---------------
Hourly, because a daily insolation total cannot be transposed onto a tilted
plane — transposition depends on solar geometry, which changes within the day.
Fetching daily GHI and multiplying by a fixed factor would be an invented
constant standing in for physics we can actually compute.

    ALLSKY_SFC_SW_DWN   global horizontal irradiance   Wh/m^2 per hour
    T2M                 air temperature at 2 m         degrees C
    WS2M                wind speed at 2 m              m/s

Wind matters more than it looks: it is the dominant cooling term in cell
temperature, and cell temperature is the correction that makes a summer baseline
honest. Leave it out and every hot-climate site looks like it is underperforming.

COORDINATE DEDUPLICATION
------------------------
VEGAS-01's five Agassi roofs share byte-identical coordinates, so they are one
request, not five. That is not an optimisation — it is the physical truth the
cohort argument rests on, and it is worth seeing in the fetch log.

Run:
    python pipeline/fetch_irradiance.py              # fetch and cache
    python pipeline/fetch_irradiance.py --force      # re-fetch, ignore cache
    python pipeline/fetch_irradiance.py --dry-run    # report, write nothing

Reads:  config/fleet_sites.csv
Writes: data/processed/irradiance_hourly.parquet
"""

import argparse
import csv
import datetime
import json
import os
import time
import urllib.error
import urllib.request

import pandas as pd

# --- Paths ------------------------------------------------------------------

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLEET_SITES_PATH = os.path.join(REPOSITORY_ROOT, "config", "fleet_sites.csv")
PROCESSED_DIR = os.path.join(REPOSITORY_ROOT, "data", "processed")
IRRADIANCE_PATH = os.path.join(PROCESSED_DIR, "irradiance_hourly.parquet")

# --- The window -------------------------------------------------------------
# Matches fetch_pvdaq.py exactly. If these ever disagree, the baseline silently
# loses days off one end and the shortfall it reports is a calendar artifact.

WINDOW_START = datetime.date(2019, 1, 1)
WINDOW_END = datetime.date(2019, 8, 21)

# --- Source -----------------------------------------------------------------

POWER_ENDPOINT = "https://power.larc.nasa.gov/api/temporal/hourly/point"
POWER_PARAMETERS = ("ALLSKY_SFC_SW_DWN", "T2M", "WS2M")
POWER_COMMUNITY = "RE"

# POWER's fill value for "no retrieval". It is NOT a measurement of -999.
POWER_MISSING_SENTINEL = -999.0

REQUEST_TIMEOUT_SECONDS = 120
RETRY_COUNT = 3
RETRY_BACKOFF_SECONDS = 5


def load_fleet_sites():
    with open(FLEET_SITES_PATH, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_site_id(source_system_id):
    """Must match generate_dispatch.build_site_id — the join key depends on it."""
    return "S-{:0>4}".format(source_system_id)


def utc_offset_hours(longitude):
    """Standard-time UTC offset, from longitude.

    WHY NOT AN IANA TIMEZONE. The only thing this offset does is decide which
    local calendar day an hourly irradiance sample belongs to, so it can be
    summed against a PVDAQ daily total built on the site's local `measured_on`
    stamp. That boundary falls at local midnight, where irradiance is zero for
    every site in this fleet on every date in the window.

    So a one-hour daylight-saving ambiguity moves a sample worth 0 Wh/m^2 from
    one day to the next. Naming a tz database, and taking on the dependency and
    the DST-history questions that come with it, would buy exactly nothing. The
    offset is recorded in the output so this reasoning stays checkable.
    """
    return int(round(longitude / 15.0))


def unique_locations(sites):
    """Group sites by coordinate. Returns {(lat, lon): [site_id, ...]}."""
    grouped = {}
    for site in sites:
        key = (float(site["lat"]), float(site["lon"]))
        grouped.setdefault(key, []).append(build_site_id(site["source_system_id"]))
    return grouped


def power_request_url(latitude, longitude):
    return (
        "{endpoint}?parameters={parameters}&community={community}"
        "&latitude={lat}&longitude={lon}&start={start}&end={end}"
        "&time-standard=UTC&format=JSON"
    ).format(
        endpoint=POWER_ENDPOINT,
        parameters=",".join(POWER_PARAMETERS),
        community=POWER_COMMUNITY,
        lat=latitude,
        lon=longitude,
        start=WINDOW_START.strftime("%Y%m%d"),
        end=WINDOW_END.strftime("%Y%m%d"),
    )


def fetch_point(latitude, longitude):
    """One POWER call. Retries on transport failure, never on a bad payload."""
    url = power_request_url(latitude, longitude)
    last_error = None

    for attempt in range(1, RETRY_COUNT + 1):
        try:
            with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise SystemExit(
        "NASA POWER failed for ({}, {}) after {} attempts: {}".format(
            latitude, longitude, RETRY_COUNT, last_error))


def parse_point(payload, latitude, longitude):
    """POWER's nested dict into a tidy frame indexed by UTC hour.

    Keys are 'YYYYMMDDHH' strings. Missing hours are published as -999, which
    must become NaN rather than a temperature 1000 degrees below absolute zero
    quietly entering a mean.
    """
    parameters = payload["properties"]["parameter"]

    for name in POWER_PARAMETERS:
        if name not in parameters:
            raise SystemExit(
                "NASA POWER returned no {} for ({}, {})".format(name, latitude, longitude))

    stamps = sorted(parameters[POWER_PARAMETERS[0]])
    frame = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(stamps, format="%Y%m%d%H", utc=True),
    })

    for name in POWER_PARAMETERS:
        column = parameters[name]
        frame[name] = [column.get(stamp) for stamp in stamps]

    frame = frame.replace(POWER_MISSING_SENTINEL, pd.NA)
    for name in POWER_PARAMETERS:
        frame[name] = pd.to_numeric(frame[name], errors="coerce")

    offset = utc_offset_hours(longitude)
    local = frame["timestamp_utc"] + pd.Timedelta(hours=offset)

    frame["lat"] = latitude
    frame["lon"] = longitude
    frame["utc_offset_hours"] = offset
    frame["local_date"] = local.dt.strftime("%Y-%m-%d")

    return frame.rename(columns={
        "ALLSKY_SFC_SW_DWN": "ghi_w_m2",
        "T2M": "temp_air_c",
        "WS2M": "wind_speed_m_s",
    })


def report_coverage(frame, label):
    """Say what came back. A silently short series is the failure mode here."""
    daylight = frame[frame["ghi_w_m2"] > 0]
    print("    {:<20} {:>6} hours, {:>4} missing GHI, {:>4} local days".format(
        label, len(frame), int(frame["ghi_w_m2"].isna().sum()),
        frame["local_date"].nunique()))
    if not daylight.empty:
        print("    {:<20} peak GHI {:.0f} W/m2, mean air temp {:.1f} C".format(
            "", daylight["ghi_w_m2"].max(), frame["temp_air_c"].mean()))


def fetch_all(dry_run=False):
    sites = load_fleet_sites()
    locations = unique_locations(sites)

    expected_days = (WINDOW_END - WINDOW_START).days + 1
    print("NASA POWER hourly - {} to {} ({} days)".format(
        WINDOW_START, WINDOW_END, expected_days))
    print("{} sites at {} distinct coordinates".format(len(sites), len(locations)))

    for (latitude, longitude), site_ids in sorted(locations.items()):
        shared = " (shared by {} sites)".format(len(site_ids)) if len(site_ids) > 1 else ""
        print("  {:>8.4f}, {:>9.4f}  {}{}".format(
            latitude, longitude, ", ".join(sorted(site_ids)), shared))

    if dry_run:
        print("\n--dry-run: nothing fetched, nothing written.")
        return None

    frames = []
    for (latitude, longitude), site_ids in sorted(locations.items()):
        print("\n  fetching {:.4f}, {:.4f} ...".format(latitude, longitude))
        payload = fetch_point(latitude, longitude)
        point = parse_point(payload, latitude, longitude)
        report_coverage(point, "{:.3f},{:.3f}".format(latitude, longitude))

        # One row per SITE per hour. The five Agassi roofs each get their own
        # rows off one request, so downstream code joins on site_id alone and
        # never has to know that a coordinate was shared.
        for site_id in sorted(site_ids):
            copy = point.copy()
            copy.insert(0, "site_id", site_id)
            frames.append(copy)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["site_id", "timestamp_utc"]).reset_index(drop=True)

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    combined.to_parquet(IRRADIANCE_PATH, index=False, compression="snappy")

    size_kb = os.path.getsize(IRRADIANCE_PATH) / 1024.0
    print("\nwrote {} ({:.0f} KB, {} rows, {} sites)".format(
        os.path.relpath(IRRADIANCE_PATH, REPOSITORY_ROOT),
        size_kb, len(combined), combined["site_id"].nunique()))
    if size_kb > 1024:
        print("  WARNING: past the ~1 MB per-file rule in CLAUDE.md. "
              "Drop the .gitignore exemption rather than letting history swell.")
    return combined


def load_irradiance(path=None):
    """Read the cached pull. Returns None when it has not been fetched yet."""
    path = path or IRRADIANCE_PATH
    if not os.path.exists(path):
        return None
    return pd.read_parquet(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true",
                        help="re-fetch even when the cache exists")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be fetched, write nothing")
    arguments = parser.parse_args()

    if os.path.exists(IRRADIANCE_PATH) and not arguments.force and not arguments.dry_run:
        cached = pd.read_parquet(IRRADIANCE_PATH)
        print("cached: {} ({} rows, {} sites). Use --force to re-fetch.".format(
            os.path.relpath(IRRADIANCE_PATH, REPOSITORY_ROOT),
            len(cached), cached["site_id"].nunique()))
        return

    fetch_all(dry_run=arguments.dry_run)


if __name__ == "__main__":
    main()

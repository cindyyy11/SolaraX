"""M1 — pull PVDAQ day files and aggregate to daily, per site and per inverter.

Run:
    python pipeline/fetch_pvdaq.py --dry-run
    python pipeline/fetch_pvdaq.py --systems 34
    python pipeline/fetch_pvdaq.py

Outputs:
    data/processed/fleet_daily.parquet     site_id, date, kwh, capacity_kwp, performance_index
    data/processed/inverter_daily.parquet  site_id, inverter_id, date, kwh, performance_index
    data/raw/_download_manifest.json       what was fetched, when

Nothing under data/ is ever committed.

THE FIVE STEPS THE RAW FORMAT FORCES
------------------------------------
A day file is NOT columns like `ac_power`. It is long-format EAV:
`measured_on, utc_measured_on, metric_id, value`. So:

  1. read metrics__system_<id> to map metric_id -> sensor_name
  2. select the AC power channel by REGEX (naming is inconsistent across systems:
     ac_power, ac_power_hW, inv1_ac_power_hW all occur)
  3. apply value * calc_scale + calc_offset to get physical watts
  4. pivot long -> wide
  5. integrate power over its own inferred interval -> kWh

Interval is inferred per file, never assumed. It is 15-minute on the systems
checked in Stage 2, but PVDAQ resolution varies by system.
"""

import argparse
import concurrent.futures
import csv
import datetime
import io
import json
import os
import re
import threading

import boto3
import pandas as pd
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import ClientError

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLEET_SITES_PATH = os.path.join(REPOSITORY_ROOT, "config", "fleet_sites.csv")
PROCESSED_DIRECTORY = os.path.join(REPOSITORY_ROOT, "data", "processed")
RAW_DIRECTORY = os.path.join(REPOSITORY_ROOT, "data", "raw")
FLEET_DAILY_PATH = os.path.join(PROCESSED_DIRECTORY, "fleet_daily.parquet")
INVERTER_DAILY_PATH = os.path.join(PROCESSED_DIRECTORY, "inverter_daily.parquet")
INVERTER_THERMAL_PATH = os.path.join(PROCESSED_DIRECTORY, "inverter_thermal.parquet")
INVERTER_HARDWARE_PATH = os.path.join(PROCESSED_DIRECTORY, "inverter_hardware.parquet")
MANIFEST_PATH = os.path.join(RAW_DIRECTORY, "_download_manifest.json")

BUCKET = "oedi-data-lake"
WINDOW_START = datetime.date(2019, 1, 1)
WINDOW_END = datetime.date(2019, 8, 21)
MAX_WORKERS = 16

# PVDAQ channel naming is inconsistent across systems, and a channel being
# DEFINED in the metrics table does not mean it carries any rows. Three distinct
# per-inverter conventions occur in this fleet alone:
#     system 1278  inv1_ac_power_hW
#     system 1200  inv1_ac_power        (plus an unused ac_power)
#     system 1367  ac_power_1           (digit suffix, no "inv" prefix)
# So: match generously, then let the DATA decide which candidate to use.

SYSTEM_AC_PATTERNS = [
    re.compile(r"^ac_power$", re.IGNORECASE),
    re.compile(r"^ac_power_(?:hW|kW|W)$", re.IGNORECASE),
    re.compile(r"^ac_power_metered(?:_hW|_kW|_W)?$", re.IGNORECASE),
]

INVERTER_AC_PATTERNS = [
    re.compile(r"^inv(\d+)_ac_power(?:_hW|_kW|_W)?$", re.IGNORECASE),
    re.compile(r"^ac_power_(\d+)$", re.IGNORECASE),
]

# Channel units vary too. Everything is normalised to watts before integrating.
UNIT_TO_WATTS = {"w": 1.0, "hw": 100.0, "kw": 1000.0, "mw": 1_000_000.0}

# Per-inverter temperature, and the site ambient reading where one exists.
# `inv4_dc_temp` occurs alongside `inv4_temp` on system 1199, so the middle
# segment is optional.
INVERTER_TEMP_PATTERN = re.compile(r"^inv(\d+)_(?:\w+_)?temp$", re.IGNORECASE)
AMBIENT_TEMP_PATTERN = re.compile(r"^ambient_temp", re.IGNORECASE)

# Sensor fault sentinels and physical bounds. -40 is the classic dead-sensor
# value (identical in C and F) and appears in system 1203's ambient channel; left
# in, it drags mean ambient to -30 C in Delaware in June.
TEMP_SENTINELS = {-40.0, -99.0, -999.0}
INVERTER_TEMP_RANGE = (-25.0, 120.0)
AMBIENT_TEMP_RANGE = (-25.0, 60.0)
MIN_THERMAL_SAMPLES = 4

# Fraction of an inverter's daily peak above which it counts as "generating".
# Temperature rise is only meaningful under load; at night everything sits at
# ambient and the average would be meaningless.
GENERATING_THRESHOLD = 0.05

_thread_local = threading.local()


def get_client():
    """boto3 clients are not thread-safe; give each worker its own."""
    if not hasattr(_thread_local, "client"):
        _thread_local.client = boto3.client("s3", config=Config(signature_version=UNSIGNED))
    return _thread_local.client


# --- Paths ------------------------------------------------------------------


def pvdata_key(system_id, day):
    """Partition folders use UNPADDED ints; the filename uses ZERO-PADDED dates."""
    return (
        "pvdaq/parquet/pvdata/system_id={id}/year={y}/month={m}/day={d}/"
        "system_{id}__date_{y}_{m:02d}_{d:02d}.snappy.000.parquet"
    ).format(id=system_id, y=day.year, m=day.month, d=day.day)


def metrics_key(system_id):
    return "pvdaq/parquet/metrics/metrics__system_{}__part000.parquet".format(system_id)


def date_range(start, end):
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += datetime.timedelta(days=1)
    return days


# --- Loading ----------------------------------------------------------------


INVERTERS_TABLE_KEY = (
    "pvdaq/parquet/inverters/part-00000-a9a6892f-3bca-42b7-a65e-2d8355306319-c000.snappy.parquet"
)
RATING_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*kW", re.IGNORECASE)


def write_inverter_hardware(sites):
    """Record whether each site's inverters are the SAME hardware.

    This gates the whole sub-site comparison. Comparing raw kWh between a 100 kW
    inverter and a 50 kW one produces a -44% "deviation" that is nameplate, not a
    fault — system 1278 does exactly that, and it reads as a convincing finding
    if nobody checks the hardware.

    Sibling comparison is only meaningful between comparable units.
    """
    frame, _ = read_parquet_object(INVERTERS_TABLE_KEY)
    wanted = {int(site["system_id"]) for site in sites}
    subset = frame[frame.system_id.isin(wanted)]

    rows = []
    for system_id in sorted(wanted):
        units = subset[subset.system_id == system_id]
        if units.empty:
            continue

        models = {str(value).strip() for value in units["model"]}
        ratings = set()
        for value in units["model"]:
            match = RATING_PATTERN.search(str(value))
            if match:
                ratings.add(float(match.group(1)))

        # One row means one model repeated `quantity` times — homogeneous by
        # construction. Several rows are only homogeneous if the model matches.
        homogeneous = len(units) == 1 or len(models) == 1

        quantities = pd.to_numeric(units["quantity"], errors="coerce").fillna(0)
        rows.append({
            "system_id": str(system_id),
            "site_id": "S-{:0>4}".format(system_id),
            "models": " | ".join(sorted(models)),
            "distinct_models": len(models),
            "distinct_ratings_kw": " | ".join(str(value) for value in sorted(ratings)) or "",
            "unit_count": int(quantities.sum()),
            "homogeneous": bool(homogeneous),
        })

    hardware_frame = pd.DataFrame(rows)
    if not hardware_frame.empty:
        hardware_frame.to_parquet(INVERTER_HARDWARE_PATH, index=False)
    return hardware_frame


def load_fleet():
    with open(FLEET_SITES_PATH, "r", encoding="utf-8", newline="") as handle:
        return [
            {
                "system_id": row["source_system_id"].strip(),
                "site_id": "S-{:0>4}".format(row["source_system_id"].strip()),
                "name": row["name"].strip(),
                "capacity_kwp": float(row["capacity_kwp"]),
                "cohort_id": row["cohort_id"].strip(),
            }
            for row in csv.DictReader(handle)
        ]


def read_parquet_object(key):
    body = get_client().get_object(Bucket=BUCKET, Key=key)["Body"].read()
    return pd.read_parquet(io.BytesIO(body)), len(body)


def load_channel_map(system_id):
    """metric_id -> (sensor_name, calc_scale, calc_offset). Without it, values are meaningless."""
    metrics, _ = read_parquet_object(metrics_key(system_id))
    channel_map = {}
    for record in metrics.to_dict("records"):
        scale = record.get("calc_scale")
        offset = record.get("calc_offset")
        raw_units = str(record.get("raw_units") or "").strip()
        units = str(record.get("units") or "").strip()

        # calc_scale DOCUMENTS a conversion that has already been performed on the
        # stored values. It must never be applied again. Verified two ways:
        #
        #   system 34   ac_power_hW          raw_units=W  units=W  scale=100
        #               raw max 99,500 vs 146,640 W nameplate = 0.68x  -> already W
        #   system 1200 ac_power_metered_kW  raw_units=kW units=W  scale=1000
        #               raw max 46,780 vs 51,840 W nameplate = 0.90x   -> already W
        #
        # Applying the scale gave 100x and 1000x errors respectively. The unit
        # suffix in the channel NAME is also unreliable (`_kW` holding watts), so
        # the `units` column is the only trustworthy field — and it is what the
        # stored value is already expressed in.
        channel_map[int(record["metric_id"])] = {
            "sensor_name": str(record.get("sensor_name") or ""),
            "calc_scale": float(scale) if not pd.isna(scale) else 1.0,  # recorded, not applied
            "calc_offset": 0.0 if pd.isna(offset) else float(offset),
            "raw_units": raw_units,
            "units": units,
        }
    return channel_map


def select_channels(channel_map):
    """Candidate AC power channels.

    Returns (system_candidates, inverter_metric_ids). `system_candidates` is an
    ordered list of metric_ids to try — earlier is preferred — because a channel
    may be defined and still carry no rows.
    """
    system_candidates = []
    inverter_metric_ids = {}

    for pattern in SYSTEM_AC_PATTERNS:
        for metric_id, info in sorted(channel_map.items()):
            if pattern.match(info["sensor_name"]) and metric_id not in system_candidates:
                system_candidates.append(metric_id)

    for pattern in INVERTER_AC_PATTERNS:
        for metric_id, info in sorted(channel_map.items()):
            match = pattern.match(info["sensor_name"])
            if match:
                inverter_metric_ids.setdefault("inv{}".format(match.group(1)), metric_id)

    # A whole-system channel wins over per-inverter ones, so drop any overlap.
    inverter_metric_ids = {
        unit: metric_id
        for unit, metric_id in inverter_metric_ids.items()
        if metric_id not in system_candidates
    }

    return system_candidates, inverter_metric_ids


# --- Aggregation ------------------------------------------------------------


def to_celsius(values, units):
    """Normalise a temperature series to Celsius so deltas are comparable.

    A delta in Fahrenheit is NOT a delta in Celsius — 18 degF of rise is 10 degC.
    Converting both sides before subtracting is the only way the number means
    what the label says.
    """
    unit = (units or "").strip().lower().lstrip("deg").strip()
    if unit in ("f", "degf", "fahrenheit"):
        return (values - 32.0) * 5.0 / 9.0
    if unit in ("k", "degk", "kelvin"):
        return values - 273.15
    return values  # already Celsius, or unlabelled and assumed so


def select_temperature_channels(channel_map):
    """Return (inverter_temp_metric_ids, ambient_metric_id)."""
    inverter_temps = {}
    ambient_metric_id = None
    for metric_id, info in sorted(channel_map.items()):
        name = info["sensor_name"]
        match = INVERTER_TEMP_PATTERN.match(name)
        if match:
            inverter_temps.setdefault("inv{}".format(match.group(1)), metric_id)
        elif AMBIENT_TEMP_PATTERN.match(name) and ambient_metric_id is None:
            ambient_metric_id = metric_id
    return inverter_temps, ambient_metric_id


def median_of_values(values):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def clean_temperature(series, valid_range):
    """Drop sensor sentinels and physically impossible readings."""
    cleaned = series[~series.isin(TEMP_SENTINELS)]
    low, high = valid_range
    return cleaned[(cleaned >= low) & (cleaned <= high)]


def timestamped_series(frame, metric_id, units, valid_range):
    """A cleaned, timestamp-indexed temperature series in Celsius, or None."""
    raw = frame.loc[frame["metric_id"] == metric_id]
    if raw.empty:
        return None
    series = pd.Series(
        to_celsius(raw["value"].astype(float), units).values,
        index=pd.to_datetime(raw["measured_on"]).values,
    )
    series = series[~series.index.duplicated(keep="first")]
    series = clean_temperature(series, valid_range)
    return series if len(series) else None


def thermal_rows_for_day(site, day, frame, channel_map, inverter_temps,
                         ambient_metric_id, inverter_power_ids):
    """Per-inverter operating temperature, compared against sibling inverters.

    SIBLING COMPARISON IS PRIMARY, ambient is secondary. Two reasons:
      - Several systems publish inverter temperature but NO ambient channel at
        all (1199 has seven inverter temps and no ambient), so requiring ambient
        throws away the richest thermal data in the fleet.
      - Siblings share the same weather, the same roof and the same hour, so a
        temperature difference between them is attributable in a way a rise above
        ambient never is — ambient rise is dominated by irradiance and load.

    `delta_t_ambient_c` is emitted only where a sane ambient reading exists.
    """
    if not inverter_temps:
        return []

    ambient = None
    if ambient_metric_id is not None:
        ambient = timestamped_series(
            frame, ambient_metric_id, channel_map[ambient_metric_id]["units"],
            AMBIENT_TEMP_RANGE)

    per_unit = {}
    for unit_id, temp_metric_id in sorted(inverter_temps.items()):
        unit_temp = timestamped_series(
            frame, temp_metric_id, channel_map[temp_metric_id]["units"],
            INVERTER_TEMP_RANGE)
        if unit_temp is None:
            continue

        # Restrict to timestamps where this inverter was generating; at night
        # everything sits at ambient and the average means nothing.
        power_metric_id = inverter_power_ids.get(unit_id)
        if power_metric_id is not None:
            power_raw = frame.loc[frame["metric_id"] == power_metric_id]
            if not power_raw.empty:
                power = pd.Series(
                    power_raw["value"].astype(float).values,
                    index=pd.to_datetime(power_raw["measured_on"]).values,
                )
                power = power[~power.index.duplicated(keep="first")]
                peak = power.max()
                if peak and peak > 0:
                    generating = power[power > peak * GENERATING_THRESHOLD].index
                    unit_temp = unit_temp.reindex(generating).dropna()

        if len(unit_temp) >= MIN_THERMAL_SAMPLES:
            per_unit[unit_id] = unit_temp

    if not per_unit:
        return []

    daily_means = {unit_id: float(series.mean()) for unit_id, series in per_unit.items()}
    sibling_median = median_of_values(list(daily_means.values()))

    rows = []
    for unit_id, series in per_unit.items():
        mean_temp = daily_means[unit_id]

        delta_ambient = None
        mean_ambient = None
        if ambient is not None:
            aligned = ambient.reindex(series.index).dropna()
            if len(aligned) >= MIN_THERMAL_SAMPLES:
                mean_ambient = round(float(aligned.mean()), 2)
                delta_ambient = round(float(series.reindex(aligned.index).mean() - aligned.mean()), 2)

        rows.append({
            "site_id": site["site_id"],
            "inverter_id": unit_id,
            "date": day.isoformat(),
            "mean_temp_c": round(mean_temp, 2),
            "max_temp_c": round(float(series.max()), 2),
            "sibling_median_temp_c": round(sibling_median, 2),
            "delta_t_siblings_c": round(mean_temp - sibling_median, 2),
            "mean_ambient_c": mean_ambient,
            "delta_t_ambient_c": delta_ambient,
            "n_samples": int(len(series)),
        })

    return rows


def integrate_to_kwh(frame, metric_id, info):
    """Integrate one channel's power over its own inferred interval, into kWh.

    Interval is derived from the timestamps present, never assumed — PVDAQ
    resolution varies by system and by era.
    """
    series = frame.loc[frame["metric_id"] == metric_id]
    if series.empty:
        return None, 0

    series = series.sort_values("measured_on")
    # Values are already expressed in `units`; convert that to watts. calc_scale
    # is deliberately NOT applied — see load_channel_map.
    unit_factor = UNIT_TO_WATTS.get(info["units"].lower(), 1.0)
    watts = (series["value"].astype(float) + info["calc_offset"]) * unit_factor
    watts = watts.clip(lower=0)  # negative AC power is a sensor artefact, not generation

    stamps = pd.to_datetime(series["measured_on"])
    hours = stamps.diff().dt.total_seconds().div(3600.0)

    # Trapezoid over each interval; the first sample has no preceding gap.
    energy_wh = (watts.shift() * hours).sum()
    if pd.isna(energy_wh):
        return None, len(series)
    return float(energy_wh) / 1000.0, len(series)


def fetch_one_day(site, day, channel_map, system_candidates, inverter_metric_ids,
                  inverter_temps=None, ambient_metric_id=None):
    """Return (site_row, inverter_rows, thermal_rows, bytes) for one system-day."""
    try:
        frame, size = read_parquet_object(pvdata_key(site["system_id"], day))
    except ClientError:
        return None  # a missing day is normal; coverage is uneven

    inverter_rows = []
    for inverter_id, metric_id in sorted(inverter_metric_ids.items()):
        kwh, samples = integrate_to_kwh(frame, metric_id, channel_map[metric_id])
        if kwh is None:
            continue
        inverter_rows.append({
            "site_id": site["site_id"],
            "inverter_id": inverter_id,
            "date": day.isoformat(),
            "kwh": round(kwh, 3),
            "n_samples": samples,
        })

    # Prefer the whole-system channel. Several systems (1278, 1199, 1200, 1202,
    # 1203) DEFINE ac_power in their metrics table but ship no rows for it, so
    # fall back to summing the per-inverter channels. Integration is linear, so
    # summing per-inverter kWh is equivalent to integrating their sum.
    site_kwh = None
    site_samples = 0
    source = None

    # Accept the first candidate that actually carries samples. Testing kWh > 0
    # would silently discard genuine zero-production days (outage, snow, a dark
    # winter day) and understate coverage.
    for metric_id in system_candidates:
        candidate_kwh, candidate_samples = integrate_to_kwh(
            frame, metric_id, channel_map[metric_id])
        if candidate_kwh is not None and candidate_samples > 0:
            site_kwh, site_samples = candidate_kwh, candidate_samples
            source = channel_map[metric_id]["sensor_name"]
            break

    if site_kwh is None and inverter_rows:
        site_kwh = sum(row["kwh"] for row in inverter_rows)
        site_samples = sum(row["n_samples"] for row in inverter_rows)
        source = "summed_inverters"

    site_row = None
    if site_kwh is not None:
        site_row = {
            "site_id": site["site_id"],
            "date": day.isoformat(),
            "kwh": round(site_kwh, 3),
            "capacity_kwp": site["capacity_kwp"],
            "performance_index": round(site_kwh / site["capacity_kwp"], 4),
            "n_samples": site_samples,
            "kwh_source": source,
        }

    thermal_rows = thermal_rows_for_day(
        site, day, frame, channel_map, inverter_temps or {},
        ambient_metric_id, inverter_metric_ids)

    return site_row, inverter_rows, thermal_rows, size


def fetch_system(site, days, verbose=True):
    """Pull every day for one system. A failure here logs and returns empty."""
    try:
        channel_map = load_channel_map(site["system_id"])
    except ClientError as error:
        print("  ! {} — metrics table unavailable ({}), skipping".format(
            site["site_id"], error.response.get("Error", {}).get("Code")))
        return [], [], 0

    system_candidates, inverter_metric_ids = select_channels(channel_map)
    inverter_temps, ambient_metric_id = select_temperature_channels(channel_map)
    if not system_candidates and not inverter_metric_ids:
        print("  ! {} — no AC power channel found, skipping".format(site["site_id"]))
        return [], [], [], 0

    site_rows = []
    inverter_rows = []
    thermal_rows = []
    total_bytes = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(fetch_one_day, site, day, channel_map,
                        system_candidates, inverter_metric_ids,
                        inverter_temps, ambient_metric_id): day
            for day in days
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
            except Exception as error:  # one bad day must not abort the system
                print("    ! {} {} — {}".format(site["site_id"], futures[future], error))
                continue
            if result is None:
                continue
            site_row, day_inverter_rows, day_thermal_rows, size = result
            if site_row:
                site_rows.append(site_row)
            inverter_rows.extend(day_inverter_rows)
            thermal_rows.extend(day_thermal_rows)
            total_bytes += size

    if verbose:
        print("  {} {:<40} {:>4} days  {:>2} inv  {:>2} thermal  {:>6.1f} MB".format(
            site["site_id"], site["name"][:40], len(site_rows),
            len(inverter_metric_ids), len(inverter_temps), total_bytes / (1024 * 1024)))

    return site_rows, inverter_rows, thermal_rows, total_bytes


# --- Dry run ----------------------------------------------------------------


def dry_run(sites, days):
    """Report what WOULD be fetched. Probes one real day per system for a size estimate."""
    print("DRY RUN — nothing will be downloaded")
    print("window : {} to {} ({} days)".format(WINDOW_START, WINDOW_END, len(days)))
    print("systems: {}".format(len(sites)))
    print("")

    total_estimate_bytes = 0
    for site in sites:
        probe_bytes = 0
        for probe_day in (days[0], days[len(days) // 2], days[-1]):
            try:
                _, size = read_parquet_object(pvdata_key(site["system_id"], probe_day))
                probe_bytes = max(probe_bytes, size)
            except ClientError:
                continue

        try:
            channel_map = load_channel_map(site["system_id"])
            _, inverter_metric_ids = select_channels(channel_map)
            inverter_count = len(inverter_metric_ids)
        except ClientError:
            inverter_count = 0

        estimate = probe_bytes * len(days)
        total_estimate_bytes += estimate
        print("  {} {:<44} ~{:>6.1f} MB  {:>2} inverter channels".format(
            site["site_id"], site["name"][:44], estimate / (1024 * 1024), inverter_count))

    print("")
    print("  files   : {} systems x {} days = {}".format(
        len(sites), len(days), len(sites) * len(days)))
    print("  estimate: {:.0f} MB".format(total_estimate_bytes / (1024 * 1024)))


# --- Output -----------------------------------------------------------------


def write_outputs(site_rows, inverter_rows, thermal_rows, total_bytes, sites):
    os.makedirs(PROCESSED_DIRECTORY, exist_ok=True)
    os.makedirs(RAW_DIRECTORY, exist_ok=True)

    fleet_frame = pd.DataFrame(site_rows).sort_values(["site_id", "date"])
    fleet_frame.to_parquet(FLEET_DAILY_PATH, index=False)

    inverter_frame = pd.DataFrame(inverter_rows)
    if not inverter_frame.empty:
        inverter_frame = inverter_frame.sort_values(["site_id", "inverter_id", "date"])
        inverter_frame.to_parquet(INVERTER_DAILY_PATH, index=False)

    thermal_frame = pd.DataFrame(thermal_rows)
    if not thermal_frame.empty:
        thermal_frame = thermal_frame.sort_values(["site_id", "inverter_id", "date"])
        thermal_frame.to_parquet(INVERTER_THERMAL_PATH, index=False)

    hardware_frame = write_inverter_hardware(sites)
    if not hardware_frame.empty:
        mixed = hardware_frame[~hardware_frame["homogeneous"]]
        if not mixed.empty:
            print("")
            print("MIXED INVERTER HARDWARE — sibling comparison suppressed for:")
            for record in mixed.to_dict("records"):
                print("  {}  models: {}  ratings: {} kW".format(
                    record["site_id"], record["models"], record["distinct_ratings_kw"]))

    manifest = {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_start": WINDOW_START.isoformat(),
        "window_end": WINDOW_END.isoformat(),
        "systems": [site["system_id"] for site in sites],
        "site_day_rows": len(fleet_frame),
        "inverter_day_rows": len(inverter_frame),
        "thermal_day_rows": len(thermal_frame),
        "bytes_downloaded": total_bytes,
        "source": "s3://{}/pvdaq/parquet/pvdata/".format(BUCKET),
        "note": "Raw PVDAQ. Never commit anything under data/.",
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return fleet_frame, inverter_frame, thermal_frame


# A fixed-tilt PV system cannot exceed roughly 10 kWh per kWp in a day anywhere
# on Earth. Anything above this is a units or scaling error, not a good day.
MAX_PLAUSIBLE_PI = 10.0
MIN_PLAUSIBLE_MEAN_PI = 2.0


def print_quality_report(fleet_frame, inverter_frame, sites, expected_days):
    print("")
    print("=" * 74)
    print("DATA QUALITY")
    print("=" * 74)
    print("{:<9} {:>6} {:>7} {:>8} {:>10}  {}".format(
        "site", "days", "gaps", "mean PI", "kWh total", "coverage"))
    print("-" * 74)

    for site in sites:
        rows = fleet_frame[fleet_frame["site_id"] == site["site_id"]]
        if rows.empty:
            print("{:<9} {:>6} {:>7} {:>8} {:>10}  NO DATA".format(site["site_id"], 0, "-", "-", "-"))
            continue
        gaps = expected_days - len(rows)
        coverage = len(rows) / expected_days
        print("{:<9} {:>6} {:>7} {:>8.2f} {:>10.0f}  {:>6.1%} {}".format(
            site["site_id"], len(rows), gaps, rows["performance_index"].mean(),
            rows["kwh"].sum(), coverage, "" if coverage >= 0.9 else "<-- below 0.9"))

    # A site averaging under this is not simply having a bad month — it usually
    # means only some of its inverter channels were captured.
    mean_by_site = fleet_frame.groupby("site_id")["performance_index"].mean()
    suspiciously_low = mean_by_site[mean_by_site < MIN_PLAUSIBLE_MEAN_PI]
    if not suspiciously_low.empty:
        print("")
        print("SUSPICIOUSLY LOW — mean below {} kWh/kWp/day:".format(MIN_PLAUSIBLE_MEAN_PI))
        for site_id, value in suspiciously_low.items():
            print("  {}  {:.2f}  — likely partial channel capture, verify before use".format(
                site_id, value))

    implausible = fleet_frame[fleet_frame["performance_index"] > MAX_PLAUSIBLE_PI]
    if not implausible.empty:
        print("")
        print("!" * 74)
        print("IMPLAUSIBLE VALUES — {} row(s) exceed {} kWh/kWp/day.".format(
            len(implausible), MAX_PLAUSIBLE_PI))
        print("No PV system on Earth does this. Suspect a units or scaling error,")
        print("not a good day. Affected sites: {}".format(
            ", ".join(sorted(implausible["site_id"].unique()))))
        print("max observed: {:.1f} kWh/kWp".format(implausible["performance_index"].max()))
        print("!" * 74)

    if "kwh_source" in fleet_frame.columns:
        print("")
        print("kWh source per site:")
        for site_id, group in fleet_frame.groupby("site_id"):
            sources = group["kwh_source"].value_counts().to_dict()
            print("  {}  {}".format(site_id, sources))

    if not inverter_frame.empty:
        print("")
        print("INVERTER-LEVEL DATA (enables sub-site detection):")
        for site_id, group in inverter_frame.groupby("site_id"):
            units = sorted(group["inverter_id"].unique())
            print("  {}  {} units: {}".format(site_id, len(units), ", ".join(units)))
    else:
        print("")
        print("No inverter-level data captured — sub-site detection not available.")


def main():
    parser = argparse.ArgumentParser(description="Pull PVDAQ and aggregate to daily.")
    parser.add_argument("--dry-run", action="store_true",
                        help="report file count and estimated MB without downloading")
    parser.add_argument("--systems", nargs="*", default=None,
                        help="limit to these source_system_id values")
    arguments = parser.parse_args()

    sites = load_fleet()
    if arguments.systems:
        wanted = set(arguments.systems)
        sites = [site for site in sites if site["system_id"] in wanted]
        if not sites:
            print("No matching systems in config/fleet_sites.csv")
            return 1

    days = date_range(WINDOW_START, WINDOW_END)

    if arguments.dry_run:
        dry_run(sites, days)
        return 0

    print("fetching {} system(s), {} to {} ({} days)".format(
        len(sites), WINDOW_START, WINDOW_END, len(days)))
    print("")

    all_site_rows = []
    all_inverter_rows = []
    all_thermal_rows = []
    total_bytes = 0

    for site in sites:
        site_rows, inverter_rows, thermal_rows, size = fetch_system(site, days)
        all_site_rows.extend(site_rows)
        all_inverter_rows.extend(inverter_rows)
        all_thermal_rows.extend(thermal_rows)
        total_bytes += size

    if not all_site_rows:
        print("")
        print("No data retrieved. Nothing written.")
        return 1

    fleet_frame, inverter_frame, thermal_frame = write_outputs(
        all_site_rows, all_inverter_rows, all_thermal_rows, total_bytes, sites)

    print_quality_report(fleet_frame, inverter_frame, sites, len(days))

    print("")
    print("wrote {} ({} rows)".format(FLEET_DAILY_PATH, len(fleet_frame)))
    if not inverter_frame.empty:
        print("wrote {} ({} rows)".format(INVERTER_DAILY_PATH, len(inverter_frame)))
    if not thermal_frame.empty:
        print("wrote {} ({} rows)".format(INVERTER_THERMAL_PATH, len(thermal_frame)))
    print("downloaded {:.1f} MB".format(total_bytes / (1024 * 1024)))
    print("")
    print("next: python pipeline/generate_dispatch.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

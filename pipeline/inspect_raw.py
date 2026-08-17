"""Stage 2 — inspect real PVDAQ files before writing any aggregation logic.

Run:
    python pipeline/inspect_raw.py            # default sample systems
    python pipeline/inspect_raw.py 34 1278    # specific systems

Downloads exactly one day per system, plus that system's metrics table, and
reports what is actually in them: column names, dtypes, row count, sample
interval, and — the question that decides whether sub-site detection is
possible at all — whether per-inverter or per-string channels exist.

docs/Schema.md describes the pipeline OUTPUT. This describes the raw INPUT.
They are not the same shape and must not be confused.
"""

import io
import re
import sys

import boto3
import pandas as pd
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import ClientError

BUCKET = "oedi-data-lake"
DEFAULT_SYSTEMS = ["34", "1278", "1369"]
SAMPLE_DATE = (2019, 1, 1)

# A channel belonging to one inverter or string rather than the whole system.
# PVDAQ naming is inconsistent, so match generously and report what matched.
PER_UNIT_PATTERN = re.compile(r"(inv[_\s]?\d+|_\d+$|string[_\s]?\d+|str[_\s]?\d+)", re.IGNORECASE)
TEMPERATURE_PATTERN = re.compile(r"(temp|temperature|_t_|celsius)", re.IGNORECASE)

client = boto3.client("s3", config=Config(signature_version=UNSIGNED))


def read_parquet(key):
    body = client.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    return pd.read_parquet(io.BytesIO(body)), len(body)


def pvdata_key(system_id, year, month, day):
    """Partition folders use UNPADDED ints; the filename uses ZERO-PADDED dates."""
    return (
        "pvdaq/parquet/pvdata/system_id={id}/year={y}/month={m}/day={d}/"
        "system_{id}__date_{y}_{m:02d}_{d:02d}.snappy.000.parquet"
    ).format(id=system_id, y=year, m=month, d=day)


def metrics_key(system_id):
    return "pvdaq/parquet/metrics/metrics__system_{}__part000.parquet".format(system_id)


def describe_metrics(system_id):
    """The channel dictionary. metric_id is meaningless without it."""
    try:
        metrics, size = read_parquet(metrics_key(system_id))
    except ClientError as error:
        print("  ! metrics table unavailable: {}".format(
            error.response.get("Error", {}).get("Code")))
        return None

    print("  metrics table: {} rows, {} bytes".format(len(metrics), size))
    print("  metrics columns: {}".format(list(metrics.columns)))

    name_column = "sensor_name" if "sensor_name" in metrics.columns else metrics.columns[1]
    names = [str(value) for value in metrics[name_column].tolist()]

    print("")
    print("  ALL CHANNELS ({}):".format(len(names)))
    for name in names:
        print("    - {}".format(name))

    per_unit = [name for name in names if PER_UNIT_PATTERN.search(name)]
    temperature = [name for name in names if TEMPERATURE_PATTERN.search(name)]

    print("")
    print("  >> PER-INVERTER / PER-STRING channels: {}".format(len(per_unit)))
    for name in per_unit:
        print("       {}".format(name))
    print("  >> TEMPERATURE channels: {}".format(len(temperature)))
    for name in temperature:
        print("       {}".format(name))

    return metrics


def describe_day(system_id):
    key = pvdata_key(system_id, *SAMPLE_DATE)
    try:
        frame, size = read_parquet(key)
    except ClientError as error:
        print("  ! no data for {}: {}".format(
            SAMPLE_DATE, error.response.get("Error", {}).get("Code")))
        return None

    print("  file: {:.0f} KB, {} rows".format(size / 1024, len(frame)))
    print("  columns and dtypes:")
    for column in frame.columns:
        print("    {:<20} {}".format(column, frame[column].dtype))

    if "measured_on" in frame.columns:
        stamps = pd.to_datetime(frame["measured_on"]).sort_values().unique()
        print("  distinct timestamps: {}".format(len(stamps)))
        if len(stamps) > 1:
            deltas = pd.Series(stamps).diff().dropna()
            print("  modal interval: {}".format(deltas.mode().iloc[0]))

    if "metric_id" in frame.columns:
        print("  distinct metric_id values: {}".format(frame["metric_id"].nunique()))

    print("")
    print("  FIRST 5 ROWS:")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print("    " + frame.head(5).to_string(index=False).replace("\n", "\n    "))

    return frame


def inspect(system_id):
    print("")
    print("=" * 78)
    print("SYSTEM {}".format(system_id))
    print("=" * 78)

    frame = describe_day(system_id)
    print("")
    metrics = describe_metrics(system_id)

    # The join that makes the raw values physical.
    if frame is not None and metrics is not None and "metric_id" in frame.columns:
        if "metric_id" in metrics.columns:
            present = set(frame["metric_id"].unique())
            defined = set(metrics["metric_id"].unique())
            print("")
            print("  metric_ids present in the day file : {}".format(len(present)))
            print("  metric_ids defined in metrics      : {}".format(len(defined)))
            unresolved = present - defined
            if unresolved:
                print("  ! {} metric_id(s) in the data have no metrics row: {}".format(
                    len(unresolved), sorted(unresolved)[:10]))
            else:
                print("  every metric_id in the data resolves to a channel name")


def main():
    systems = sys.argv[1:] or DEFAULT_SYSTEMS
    print("Stage 2 — inspecting {} for {:04d}-{:02d}-{:02d}".format(
        ", ".join(systems), *SAMPLE_DATE))
    for system_id in systems:
        inspect(system_id)


if __name__ == "__main__":
    main()

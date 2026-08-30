# CLAUDE.md — pipeline/

Loads automatically whenever a session works under this directory. Root-level rules,
direction, and the technical contract still apply — see [`../CLAUDE.md`](../CLAUDE.md).
This file holds only what is specific to fetching and processing PVDAQ/irradiance data;
it is irrelevant noise for frontend-only work, which is why it isn't in the root file.

## Environment

Python 3.11 preferred. Local is currently 3.14 — `pvlib` and `scikit-learn` may lack wheels for it.
If installs fail, create a 3.11 venv rather than compiling from source. Keep
`requirements.txt` current.

## Data source — PVDAQ on S3

Public, no credentials. `boto3` with `Config(signature_version=UNSIGNED)`, or DuckDB `httpfs`.

Bucket: `oedi-data-lake`
Catalogue: `pvdaq/csv/systems_20250729.csv`
Timeseries path pattern (Hive-partitioned, confirmed against the live bucket):

```
pvdaq/parquet/pvdata/system_id={id}/year={YYYY}/month={M}/day={D}/
  system_{id}__date_{YYYY}_{MM}_{DD}.snappy.000.parquet
```

Partition folders use **UNPADDED** integers (`month=1`, `day=1`); the filename uses **ZERO-PADDED**
dates (`date_2019_01_01`). Get this wrong and every path 404s.

One file per system per day, ~0.03–0.2 MB each depending on channel count. Parallelise or use
DuckDB — never serial.

> **The catalogue lies about coverage.** `first_timestamp` / `last_timestamp` do **not** imply
> continuous data, and do not reliably describe the *parquet* dataset — they likely describe the CSV
> one. System 1367 passes a 2019 filter and has a four-month hole; 1430 and 1433 both advertise
> `last_timestamp` in 2024 and have **no 2019 partition at all**. Always verify by listing before
> trusting a date range. Never assume two systems share a window.

## Commands

```
python explore_bucket.py <prefix>   # list S3 paths, no download
python fetch_pvdaq.py               # pull + aggregate to daily
python fetch_irradiance.py          # NASA POWER cache — M2 needs it
python baseline.py                  # M2 baseline + its measured accuracy
python peer_benchmark.py            # M3 detector over the real fleet
python score_detector.py            # M3 accuracy vs injected ground truth
python generate_dispatch.py         # produce dispatch.json
python validate_dispatch.py         # assert schema conformance
```

Run from the repo root as `python pipeline/<script>.py`, or from here as `python <script>.py`.

# SolaraX — Build Plan for Claude Code (v2)

Read `CLAUDE.md` and `docs/SCHEMA.md` before starting any stage.

Work through these stages **in order**. Each has a definition of done. Stop at
the end of each stage and report before starting the next — several stages
produce information that changes the one after it.

---

## Context you need up front

**The fleet has changed.** The earlier shortlist (systems 14596–14698) does not
exist in the S3 bucket. It has been replaced with verified systems.

Three cohorts, 13 sites. Every system below has been verified to have 2019
parquet partitions — catalogue metadata alone is not sufficient evidence (see
the warning at the end of this section).

Primary cohort — **DSUN-01**, five sites, one operator across MD / DE / NJ,
Köppen `Cfa`. All five have all twelve months of 2019:

| system_id | Name | kWp | Location | channels |
|---|---|---|---|---|
| 1203 | Distributed Sun — EJ DeSeta | 197.47 | Wilmington, DE | 23 |
| 1201 | Distributed Sun — 5 Executive Campus | 140.14 | Cherry Hill, NJ | 13 |
| 1199 | Distributed Sun — Hunt Valley | 52.92 | Cockeysville, MD | 37 |
| 1200 | Distributed Sun — BWI Hilton | 51.84 | Linthicum Heights, MD | 39 |
| 1202 | Distributed Sun — 6 Executive Campus | 51.84 | Cherry Hill, NJ | 40 |

**This is the cohort the product is actually about.** Five genuinely separate
C&I rooftops, one owner, ~162 km spread across three states, each a distinct
mobilisation. 1201 and 1202 sit 120 m apart on one office park, which is what
a real portfolio looks like — mostly scattered, occasionally clustered. Sits
exactly on `min_cohort_size: 5`, so it has zero margin: one dropout invalidates
it. Channel counts of 37–40 make these the best candidates for Stage 2's
sub-site question.

Secondary cohort — **VEGAS-01**, six sites, Köppen `Bwh`:

| system_id | Name | kWp | Location | channels |
|---|---|---|---|---|
| 1367 | City of Henderson — Aquatic Complex | 277.16 | Henderson, NV | 14 |
| 1278 | Agassi Prep — Building D | 171.36 | Las Vegas, NV | 26 |
| 34 | Agassi Prep — Building A | 146.64 | Las Vegas, NV | 15 |
| 35 | Agassi Prep — Gymnasium | 121.68 | Las Vegas, NV | 15 |
| 1276 | Agassi Prep — Building B | 68.48 | Las Vegas, NV | 15 |
| 1277 | Agassi Prep — Building C | 40.56 | Las Vegas, NV | 15 |

The five Agassi sites share **byte-identical coordinates** (36.1952, -115.1582)
— one school campus. Two consequences. On the map they stack perfectly: use
`Leaflet.markercluster` and let it spiderfy, and never jitter coordinates to
fake separation. On the economics, one technician covers all five roofs in a
single trip, so per-site `cost_per_visit_rm` overstates the saving here — this
cohort is a detector showcase (perfect weather control, irradiance error cancels
exactly), not an economics showcase. That is what DSUN-01 is for.

Below-minimum cohort — **GOLDEN-01**, two sites, Köppen `BSk`:

| system_id | Name | kWp | Location | 2019 coverage |
|---|---|---|---|---|
| 1332 | NREL Parking Garage | 1153.49 | Golden, CO | all 12 months |
| 1283 | NREL Research Support Facility II | 408.24 | Golden, CO | fragmented — see below |

Two sites is **far below** `min_cohort_size: 5`, which is the point: it makes
PRD §15's minimum-density weakness visible rather than hidden. Flag it, never
hide it. `meets_minimum` is `false`.

Reduced from the planned four. **1430 and 1433 have no 2019 parquet data at
all** — 1430 stops in 2017, 1433 in 2018. **1283 is fragmented inside 2019**:
March is missing entirely, February holds 14 non-contiguous days, April starts
on the 15th.

These two are also 75% of the fleet's download weight (≈594 MB of ≈790 MB) for
a cohort whose only job is to render a caution badge. Applying this document's
own instruction to pull selectively: **fetch GOLDEN-01 for the 90-day series
window only**, mark both sites `healthy`, and rely on SCHEMA §8.7 — healthy
sites omit `series.cohort` entirely. That drops the fleet to roughly 425 MB.

> **Warning, learned the hard way three times.** The catalogue's
> `first_timestamp` / `last_timestamp` columns do **not** imply continuous
> coverage, and do not even reliably describe the parquet dataset. 1367 passes
> a 2019 filter and has a four-month hole. 1430 and 1433 both advertise
> `last_timestamp` in 2024 and have no 2019 partition whatsoever. Always verify
> partitions by listing before trusting a date range. The catalogue likely
> describes the CSV dataset, not the parquet one.

Full details in `config/fleet_sites.csv` (13 rows, regenerated from the
catalogue). Note the catalogue contains a **duplicate row for 1332** — dedupe on
`system_id` when reading it.

**Target window: 1 Jan – 21 Aug 2019** (233 days), applied fleet-wide.

Estimated pull, from catalogue `dataset_size_mb ÷ years × 233`:

| Cohort | Sites | Window MB |
|---|---|---|
| DSUN-01 | 5 | ~120 |
| VEGAS-01 | 6 | ~77 |
| GOLDEN-01 | 2 | ~594 full → ~230 at the 90-day slice |
| **Total** | **13** | **~790 full → ~425 sliced** |

~3,029 files at full window. Verify with `--dry-run` in Stage 4 before pulling.

Narrowed from calendar-year 2019 after Stage 1. System **1367** stops on
**21 Aug 2019** and has no data again until a single orphan file on 31 Dec —
a ~4.3-month outage mid-life, not an install or decommission boundary. The
other five run the full year cleanly. A four-month flatline inside a stable
cohort is exactly M3's fault signature, so the window ends where 1367's data
does rather than shipping the fleet's loudest false positive. Values are
untouched; only the window is shorter. SCHEMA §8.6 needs 90 days of series,
so 233 days still leaves five months of run-up for baseline and cohort stats.

**Irradiance source: NASA POWER.** Not Open-Meteo, not PVGIS. Decided.

**S3 path pattern (confirmed):**
```
pvdaq/parquet/pvdata/system_id={id}/year={YYYY}/month={M}/day={D}/
  system_{id}__date_{YYYY}_{MM}_{DD}.snappy.000.parquet
```
Partition folders use **unpadded** integers (`month=1`). The filename uses
**zero-padded** dates (`date_2019_01_01`). Getting this wrong 404s every path.

---

## Two-level detection — the core design idea

SolaraX applies the same peer-comparison logic at two levels:

- **Site level** — a site is compared against other sites in its weather cohort.
  A single-site dip inside a stable cohort means fault, not weather.
- **Sub-site level** — within a flagged site, each inverter or sub-array is
  compared against its siblings on the same roof. Siblings share weather
  perfectly, so divergence is unambiguous.

The second level is only possible where the data carries per-inverter or
per-string channels. Stage 2 determines whether it does. **Do not fabricate
sub-site data if the channels aren't there** — fall back to site-level only and
say so on screen.

There is no panel-level position data anywhere in PVDAQ. Never render a panel
grid implying physical layout.

---

## Stage 1 — Verify coverage

Using `explore_bucket.py`, list `year=` folders for each of the six VEGAS-01
systems, then `month=` folders under `year=2019` for each.

**Done when:** a table shows, per system, which months of 2019 have data. If any
system is missing more than one month, report it — the fleet may need adjusting
before anything is downloaded.

No download code yet.

---

## Stage 2 — Inspect one real file (critical)

Download exactly one file: system 34, 2019, January 1. Print every column name,
its dtype, the row count, the time interval between rows, and the first five rows.

Then do the same for system 1278 (26 channels — most likely to carry sub-site
detail).

**Report specifically whether the data carries per-inverter or per-string
channels** — look for names like `inv1_ac_power`, `ac_power_2`,
`dc_current_string_3`, or any repeated column pattern with a numeric suffix.

**Done when:** the actual column names are known, and there is a clear yes/no on
sub-site granularity. This answer determines whether Stages 8 and 12 are built.

Do not write any aggregation logic before this. `SCHEMA.md` describes *output*,
not raw PVDAQ columns.

---

## Stage 3 — Environment

Create `pipeline/requirements.txt`: `boto3`, `pandas`, `pyarrow`, `duckdb`,
`requests`. Do not pin `pvlib` or `scikit-learn` — those belong to teammate A.

Local Python is 3.14, and `CLAUDE.md` targets 3.11. Test whether the above
install cleanly on 3.14. If any fail, create a 3.11 virtual environment and
document the setup in `README.md`.

**Done when:** a fresh `pip install -r pipeline/requirements.txt` succeeds and
the Python version in use is recorded in the README.

---

## Stage 4 — Fetch and aggregate

Write `pipeline/fetch_pvdaq.py`.

Read systems from `config/fleet_sites.csv`. For calendar year 2019, pull the
per-day parquet files for each VEGAS-01 system and aggregate to **one row per
site per day**.

**If Stage 2 found sub-site channels**, also write a second table with one row
per site per inverter per day. Do not discard that granularity during
aggregation — it cannot be recovered later without re-downloading.

Requirements:
- Prefer DuckDB with an explicitly constructed list of file paths. Do **not**
  glob across the whole bucket — one file per system per day means a wide glob
  triggers thousands of list operations.
- If using boto3 instead, parallelise with a thread pool. Serial downloads of
  ~2,200 files will take hours.
- `--dry-run` prints file count and total MB without downloading.
- `--systems` limits to a subset.
- Skip work already done so an interrupted run resumes.
- One failing system logs and continues; it must not abort the run.
- Write `data/processed/fleet_daily.parquet`:
  `site_id, date, kwh, capacity_kwp, performance_index`
  where `performance_index = kwh / capacity_kwp`.
- If applicable, write `data/processed/inverter_daily.parquet`:
  `site_id, inverter_id, date, kwh, performance_index`
- Write `data/raw/_download_manifest.json` recording what was fetched.

**Run `--dry-run --systems 34` first and report the output before downloading
anything.**

**Done when:** `fleet_daily.parquet` exists with ~2,190 rows, and a data-quality
report prints rows in/out, gaps per site, and date coverage per site.

---

## Stage 5 — Clean, normalise, remap dates

Write `pipeline/clean_normalise.py`.

- Handle missing days explicitly: log them, do not silently interpolate.
- Drop or flag days with physically impossible values (negative energy,
  implausible yields).
- **Date remapping:** shift the 2019 window forward to a 2026 demo window so the
  dashboard's "August 2026" header is coherent. Values must be completely
  unmodified — only the date axis moves. Apply the shift **once, here**. No other
  module may shift dates.
- Record the shift so `meta.date_remapped` and `meta.date_remap_note` can be
  populated per `SCHEMA.md` §3 and §9.

**Done when:** the processed dataset carries both original and remapped dates,
and the mapping is reversible and documented.

---

## Stage 6 — Fault injection

Write `pipeline/fault_injection.py`.

Injects a known synthetic fault into a chosen site from a chosen date. Modes:
- `step_drop` — sudden fixed percentage loss
- `soiling_ramp` — gradual linear degradation
- `string_loss` — fixed fraction of capacity offline

If inverter-level data exists, support injecting into a **single inverter** so
the sub-site view has something to show.

Outputs the modified dataset plus `pipeline/output/ground_truth.json` per
`SCHEMA.md` §8.9. Every injected point flagged so it can never be mistaken for
real data.

**Done when:** a fault can be injected and then recovered exactly from the ground
truth file. This is what teammate A needs for an accuracy figure.

---

## Stage 7 — Generate dispatch.json

Write `pipeline/generate_dispatch.py`, producing `pipeline/output/dispatch.json`
exactly per `docs/SCHEMA.md`.

**Critical constraint:** M2 (baseline), M3 (detector) and M5 (computer vision)
belong to teammates and must NOT be implemented. For anomaly scoring use a simple
cohort-mean deviation as a stand-in:

```
"method": "PLACEHOLDER — cohort mean deviation, to be replaced by M3 (owner A)"
"data_status": "PLACEHOLDER"
```

Set `expected_kwh` to `null` — that's M2's output.

All economics read from `config/assumptions.json`. No numeric constant in code.

Isolate the file-writing function at the bottom with a clear comment marking it
as the stable interface teammates must preserve.

**Done when:** `dispatch.json` exists, contains all six top-level keys, and both
cohorts appear with GOLDEN-01 flagged `meets_minimum: false`.

---

## Stage 8 — Sub-site block (only if Stage 2 found the channels)

Propose an addition to `docs/SCHEMA.md` — do not write it unilaterally, present
it for approval first. Suggested shape, on each flagged site:

```json
"sub_site": {
  "unit_type": "inverter",
  "unit_count": 4,
  "units": [
    {
      "unit_id": "inv_03",
      "performance_index": 3.12,
      "sibling_median": 4.01,
      "deviation_pct": -0.222,
      "status": "flagged",
      "series": [ { "date": "...", "performance_index": 3.12 } ]
    }
  ],
  "data_status": "BUILT"
}
```

Bump the schema to 1.2.0 with a changelog row. Omit the whole block where the
data doesn't support it — the frontend must render correctly without it.

**Done when:** the schema addition is agreed and `dispatch.json` populates it for
at least one site.

---

## Stage 9 — Validate

Write `pipeline/validate_dispatch.py` implementing every rule in `SCHEMA.md` §10.
Exit non-zero on failure. Print a loud warning listing every remaining
PLACEHOLDER with a count.

**Done when:** it passes against the generated file, and fails correctly when a
required field is removed by hand.

---

## Stage 10 — Frontend scaffold

Scaffold `frontend/` with **Vue 3 + Vite + ECharts + Leaflet**. Not React.

Build `frontend/src/api.js` as the single data-access layer reading
`dispatch.json`. Every component fetches through it, so the source can later be
switched to a Supabase REST endpoint by changing one file.

Copy the generated `dispatch.json` to `dispatch.mock.json`; `api.js` falls back to
the mock if the primary fetch fails.

Build a shared `DataStatusBadge` component rendering BUILT / SIMULATED /
PLACEHOLDER. **Every card that displays data must carry one.** This is a PRD §6
requirement and is currently missing from the existing screens.

Deploy the scaffold to Vercel and confirm the public URL loads.

**Done when:** a public URL renders, and `api.js` loads `dispatch.json`.

---

## Stage 11 — Screen 1, Dispatch

Per `docs/PRD.md` §4 Screen 1: fleet header (site count, total MWp, month), three
status groups (DISPATCH RECOMMENDED / MONITOR / HEALTHY), ranked rows showing
name, capacity, RM at risk, days since divergence, hypothesis summary, and the
footer line for visits avoided and estimated saving.

Give the footer real visual weight — the product's claim is as much about sites
not visited as sites visited.

Leave a correctly-sized placeholder for the Leaflet map; do not build it yet.

**Done when:** Screen 1 renders live from `dispatch.json` on the deployed URL.

---

## Stage 12 — Screen 2, Site Detail

**Order on the page matters and is not negotiable.** The cohort chart is the
differentiated technical work (PRD §5 M3) and must be the first thing visible.
Thermal and defect content is a supporting component (PRD §5 M5) and sits below.
Leading with imagery invites direct comparison against mature competitors on
their strongest ground.

**Block 1 — Cohort chart, full width, top of page.**
ECharts multi-line of `series.cohort`: x-axis date, y-axis `performance_index`.
Peers muted grey, `is_subject: true` in a strong accent colour. Vertical
reference line at `divergence.start_date`. Shade the region after it, annotated
with `economics.cumulative_loss_rm`.

**Block 2 — Explainability panel.**
Hypothesis summary and detail, confidence, `detection.method`, `detection.score`
with its `threshold`, cohort size, and the cohort caution badge where
`meets_minimum` is false.

**Block 3 — Sub-site breakdown** (only if `sub_site` exists).
**Ranked horizontal bars, one per inverter, ordered worst-first**, showing
deviation from sibling median. Colour by severity, small inline sparkline on each.
Click expands to that unit's 90-day trace plus any thermal evidence.

Do **not** render a panel grid. Grid layouts imply physical panel positions,
which do not exist in this dataset.

**Block 4 — Thermal evidence** (only if `evidence` exists).
The actual image with YOLOv8 bounding boxes overlaid, class and confidence per
box. Labelled SIMULATED. Must render nothing when evidence is absent.

**Done when:** a person outside the project can look at the cohort chart alone
and point to the diverging site without being told which it is. Screen must
render correctly when `sub_site` and `evidence` are both absent and
`expected_kwh` is null.

---

## Stage 13 — Screen 3, Work Order

Per `docs/PRD.md` §4 Screen 3. Exportable card: site, address, what to check,
supporting evidence, what to photograph.

**Two additions beyond the PRD text:**

1. **Verification method must be conditional on the hypothesis.** Where the
   hypothesis is electrical (inverter, string, breaker), the work order directs
   the technician to the combiner box and inverter display — no drone. Where it
   is module-level (soiling, hot spot, cracked glass, debris), it recommends a
   thermal pass before roof entry, on the PRD §5 grounds that a drone pass avoids
   work-at-height permits. Never imply every dispatch needs a drone.

2. **A findings section — this is the data flywheel and it is currently
   missing.** Fields: outcome (fault confirmed / nothing found / different cause),
   free-text note, estimated generation recovered. This closes the
   DETECT → VERIFY → CONFIRM → LEARN loop in PRD §4 and is what populates
   Screen 4's confirmed-fault and recovered-generation figures.

Add a one-line plain-language statement at the top explaining why this site was
selected over the others.

**Done when:** the card exports cleanly and the findings section persists input.

---

## Stage 14 — Screen 4, Fleet Health & ROI

Per `docs/PRD.md` §4 Screen 4 and `SCHEMA.md` §6. Rolling totals: visits
recommended, visits avoided, faults confirmed, generation recovered, cumulative
RM protected, CO2e avoided.

Include a visible **assumptions panel** listing every constant from
`config/assumptions.json` with its value and its note. This is the direct answer
to PRD §13 item 4.

Include a **pessimistic-case toggle** that recomputes the headline figures using
the low end of each `*_range` field. PRD §13 item 5 asks whether the conclusion
holds at the pessimistic end — a toggle demonstrates it rather than claiming it.

Label the whole screen's `data_status` honestly.

**Done when:** the screen renders, the assumptions panel is populated from config
rather than hardcoded, and the pessimistic toggle changes the numbers.

---

## Stage 15 — Handoff and README

Write `HANDOFF.md`:
- Schema summary and pointer to `docs/SCHEMA.md`
- The instruction: replace the internals of `generate_dispatch.py`, keep the
  writer function and output filename
- How to run `validate_dispatch.py` before handing anything over
- Every field currently `PLACEHOLDER`, with the owning teammate named
- One paragraph making clear that teammates integrate by writing into
  `dispatch.json`, not by calling the FastAPI layer — the API is downstream of
  their work, not an interface to it

Write `README.md`: what the project is, how to run the pipeline, Python version,
what is real versus simulated, and the date-remapping disclosure.

**Done when:** a teammate can clone the repo, run one command, and get a
populated dashboard without asking a question.

---

## Rules that apply throughout

- Commit after each stage.
- Never commit anything under `data/`.
- No commercial constant in code — always `config/assumptions.json`.
- No implementation of M2, M3 or M5.
- No fabricated data. Where real data is unavailable, omit the feature or label
  it SIMULATED — never invent numbers that look measured.
- Report at the end of each stage; do not chain stages without checking in.
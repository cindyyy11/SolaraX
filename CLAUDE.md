# CLAUDE.md — SolaraX

**SolaraX tells a solar asset owner which sites in their distributed fleet need a maintenance visit
this month, and which don't — protecting the margin on long-tenure O&M commitments.**

A triage layer for solar fleets. Not a monitoring dashboard, not a drone product, not a fire-safety
product. Team **CinCaiLah**, 5 members, **Track T1 — AI for Clean Energy**.

Deadline **31 Aug 2026, 23:59 MYT**. Current status, phase and blockers live in
[`PROGRESS.md`](./PROGRESS.md) — **read it after this file.**

---

## Repo map

```
SolaraX/
├── CLAUDE.md            ← you are here: rules, direction lock, technical contract
├── PROGRESS.md          ← status, phase, blockers  (the only file that goes stale by design)
├── README.md            ← public front door — judges' first impression
├── docs/                ← the product and how it's built
├── hinfo/               ← the competition: rules, rubric, submission state
├── config/              ← every commercial constant + the fleet definition
├── pipeline/            ← BATCH stage: ingestion → baseline → detection → ranking
├── apps/web/            ← SERVE stage: Vue 3 dashboard
└── data/                ← datasets on disk (see the data/ rule below)
```

| Read this | When you need |
|---|---|
| [`docs/SolaraX_PRD_v2.md`](./docs/SolaraX_PRD_v2.md) | **What we're building and why.** Authoritative product brief (v2, 11 Aug) |
| [`docs/Schema.md`](./docs/Schema.md) | **The `dispatch.json` data contract.** FROZEN — the one file that binds pipeline to frontend |
| [`docs/BUILD_PLAN.md`](./docs/BUILD_PLAN.md) | Stage-by-stage build order, the verified fleet, the target window |
| [`docs/ARCHITECTURE-PLAN.md`](./docs/ARCHITECTURE-PLAN.md) | **The agreed technical shape** — locked decisions, rejected alternatives, build order |
| [`docs/TECHNICAL.md`](./docs/TECHNICAL.md) | Stack, data strategy, module specs, technical weaknesses |
| [`docs/DATASETS.md`](./docs/DATASETS.md) | Which datasets and why — evidence for the choice |
| [`docs/RESEARCH.md`](./docs/RESEARCH.md) | Every sourced claim with a URL. **Cite from here or omit** |
| [`docs/DECISIONS.md`](./docs/DECISIONS.md) | Who decided what, when, and what's still open |
| [`hinfo/HACKATHON.md`](./hinfo/HACKATHON.md) | Competition rules, rubric, deadlines, live risks |
| [`hinfo/SUBMISSION-CHECKLIST.md`](./hinfo/SUBMISSION-CHECKLIST.md) | Deliverable-by-deliverable status |
| [`hinfo/maicnexus-extract/`](./hinfo/maicnexus-extract/) | Verbatim official rules as captured |
| [`config/fleet_sites.csv`](./config/fleet_sites.csv) | The 11 verified sites, two cohorts |
| [`data/`](./data/) | Reference data pulled into the repo — e.g. PVGIS-ERA5 at Bukit Raja/Klang |

---

## Direction lock — the project has pivoted twice

**Do not resurrect either earlier direction:**

1. **Drone flight-scheduling** (PRD v1, 10 Aug — deleted) — dropped because Raptor Maps already
   sells it, drone providers are the wrong buyer (paid per flight), and the money is in whether to
   mobilise at all, not in flight efficiency. Full reasoning: PRD v2 §1.
2. **Fire-risk intelligence / Bomba compliance** (deleted) — **explicitly superseded.** PRD v2:
   *"Fire-risk statistics from v1's research don't support v2's value proposition and are better
   left out… This is a yield and cost product, not a safety product."*

Both superseded directions were removed from the repo on 16 Aug. The reasoning that killed them is
preserved in PRD v2 §1 and [`docs/DECISIONS.md`](./docs/DECISIONS.md) — that is the part worth
keeping.

If a request pulls toward either, say so in two sentences and re-anchor on PRD v2.

**🔒 Settled 14 Aug — the buyer is the developer carrying the bundled O&M obligation**, i.e. whoever
pays for a site visit. O&M aggregators are future expansion, not the MVP target.

---

## Anti-goals

| Do NOT | Why |
|---|---|
| Fire-safety / Bomba framing, or any fire-risk statistic | Dropped in the v1→v2 pivot. Invites "why isn't this your real product?" |
| Drone flight-scheduling as the primary pitch | Raptor Maps' existing product — the reason v1 died |
| Lead with the image classifier (Module 5) | Commoditised; invites comparison to Sitemark/Scopito on their strongest ground. It's a verification step, not the innovation claim |
| Any claim requiring on-site irradiance sensors | Breaks sensor independence — the core technical wedge |
| Malaysian site names over American generation data | Fabrication. Real PVDAQ identity + a real Malaysian baseline panel — see `ARCHITECTURE-PLAN.md` §3.7 |
| Claims about a specific company's internal costs or contract terms | Public sources only. Category-level, never company-specific |
| **Repair-cost-aware ranking** | ⏸️ **Deferred by team agreement, 14 Aug.** Two unsolved prerequisites and no public repair data. Don't build it silently — and don't pretend the gap doesn't exist. See [`docs/TECHNICAL.md`](./docs/TECHNICAL.md) §5 |
| Live drone integration, auto flight booking, multi-tenant auth/billing, mobile app, SLA claims | Out of MVP scope — PRD v2 §14 |
| Render a panel grid on any screen | PVDAQ carries no panel-level position data. A grid implies a physical layout that does not exist |

---

## Module ownership — build only what is yours

| # | Module | One line | Owner |
|---|---|---|---|
| 1 | Fleet Data Ingestion | Real multi-site inverter data, keyed by `site_id` — a fleet, not a farm | C (**D covering**) |
| 2 | Sensor-Free Baseline | `pvlib` clear-sky + temperature correction from satellite irradiance | **A** |
| 3 | **Fleet Peer Benchmarking** ⭐ | **The differentiator.** Robust peer-deviation z-score (median/MAD). Cohort-wide dip = weather; single-site dip = fault | **A** |
| 4 | Economic Ranking | kWh lost × RP4 tariff → **RM/month at risk** → ranked dispatch threshold | C |
| 5 | Drone & Visual Verification | Defect class + confidence as evidence on a flagged site | **B** |
| 6 | Dispatch Dashboard | Four screens (PRD v2 §4), public URL, no login | D |
| 7 | API Layer | Serves the ranked queue without touching model code | D |
| 8 | Testing, Demo, Submission | Reproducibility, video, deliverables | E |

**DO NOT BUILD M2, M3 or M5.** They belong to A and B. If a task needs one, emit a `PLACEHOLDER`
value and a `TODO` comment naming the owner. Never write a real implementation of them.

**Fleet data detects, drone verifies.** The queue answers *where to go*; a flight answers *what's
wrong* once you're there.

---

## Architecture — three stages, strictly separated

1. **BATCH** (scheduled) — `pipeline/` ingests PVDAQ + irradiance, computes the baseline, detects
   anomalies, ranks economically. Produces ONE artifact: `pipeline/output/dispatch.json`.
2. **STORE** — `dispatch.json` is loaded into Supabase Postgres as precomputed rows.
   **`dispatch.json` remains canonical; Supabase is a serving layer**, never a second source of truth.
3. **SERVE** — the Vue frontend reads via REST, and **must fall back to the committed
   `dispatch.json`** if Supabase is unavailable. A judging window is not the moment to discover a
   hard dependency on a hosted service.

`pipeline/` and `apps/web/` never import from each other. The only thing crossing that line is
`dispatch.json`, and the frontend touches it through a single data-access module.

---

## The data contract

`docs/Schema.md` defines `dispatch.json` and is **FROZEN**. Field names and types do not change
without D confirming first. If a module needs a value that isn't there, add a field deliberately and
bump the version — never rename an existing one.

Teammates replacing the internals of `generate_dispatch.py` (M2/M3/M4) must keep producing that
exact shape. Run `pipeline/validate_dispatch.py` before handing anything over.

### `data_status` — two vocabularies, two layers

These are **not** interchangeable, and the distinction is deliberate.

| Layer | Values | Enforced by |
|---|---|---|
| **`dispatch.json` fields** | `BUILT` · `SIMULATED` · `PLACEHOLDER` | `validate_dispatch.py` rules 13 and 15 |
| **Deck, video, README claims** | BUILT · SIMULATED · **PLANNED** | PRD v2 §6, human review |

- `BUILT` — real data through a real model. The claim is fully earned.
- `SIMULATED` — real method, sample or synthetic input (injected faults, public defect datasets).
- `PLACEHOLDER` — **a value IS present and it is fake.** D's stand-in for a teammate's unbuilt
  module. Must not survive to submission; the validator counts every one remaining.
- `PLANNED` — **nothing is there.** A feature that isn't built. Correct for a deck slide, wrong for
  a `dispatch.json` field, because every required field carries a value that renders on screen.

---

## Hard rules

- **`dispatch.json` shape is FROZEN.** See above and `docs/Schema.md`.
- **Every commercial constant lives in `config/assumptions.json`.** No magic numbers in code, ever.
  Judges ask where a number came from; a clean config is the answer.
- **Performance values are ALWAYS normalised (kWh per kWp)**, never raw kWh. Sites range
  **40.56 – 1153.49 kWp** and must be comparable on one axis.
- **Do not fabricate data.** Real PVDAQ only, plus clearly-labelled synthetic fault injection.
  Where real data is unavailable, omit the feature or label it `SIMULATED` — never invent numbers
  that look measured.
- **`data/` — processed aggregates are committed, raw day-files are not.** The threshold is
  **~1 MB per file**, so it is checkable rather than a judgement call:
  - `data/processed/*.parquet` — **committed.** ~115 KB total, and it lets a teammate start on
    M2/M3 without a 40 MB pull. Regenerate with `pipeline/fetch_pvdaq.py`.
  - `data/raw/` — **never committed.** This is where bulk accumulates.
  - `data/*.json` reference pulls (e.g. PVGIS-ERA5 Klang) — committed.

  Parquet is binary, so git stores a **full copy on every change**, not a diff. At 115 KB that is
  fine for dozens of regenerations; if these files grow past ~1 MB, drop the exemption in
  `.gitignore` rather than letting history swell. History cannot be un-fattened without a rewrite.
- **Irradiance source is NASA POWER** for the pipeline: one source across all cohorts, because
  M3's error-cancellation argument only holds if cohort members share it. The PVGIS-Klang file is a
  **Malaysian market-context artifact for the pitch, not a pipeline input** — different job.
- **Never break the public-artifact rule** — no auth walls, no private repo during judging windows.

---

## Working rules

1. **PRD v2 is authoritative.** Don't propose reverting to a superseded direction.
2. **Cite or omit.** Every number traces to [`docs/RESEARCH.md`](./docs/RESEARCH.md) with a URL.
   Never invent a figure. §6 of that file lists what is *not* yet safe to ship.
3. **Every output must be explainable** — a named method and a formula, not a vibe. An LLM may
   explain a score; it must never compute one.
4. **Label everything** per the two-layer table above. No claim may imply more than what runs.
5. **Commit honestly and often.** Backdating is an explicit disqualification ground.
6. **English only**, all documentation and submission materials.
7. Before building anything, check it against the anti-goals above and name the rubric row it moves.
   If it moves none and isn't a listed module, deprioritise it.
8. **Chang Zhe's approved stack wins on conflict** — transcribed into
   [`docs/ARCHITECTURE-PLAN.md`](./docs/ARCHITECTURE-PLAN.md) §2 and restated below.

---

## Stack (confirmed — do not substitute)

- **Frontend:** Vue 3 + Vite + ECharts + Leaflet. NOT React, NOT Recharts.
- **Backend:** FastAPI + Pydantic
- **Pipeline:** Python + pandas + DuckDB + pvlib + scikit-learn + SciPy
- **Store:** Supabase Postgres · Parquet on disk for intermediates
- **CV:** YOLOv8 trained in Colab, exported ONNX, served via ONNX Runtime
- **Infra:** Vercel (frontend) · Hugging Face Spaces (API) · GitHub Actions

---

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

---

## The fleet — 11 sites, 2 cohorts, all carrying real data

Full detail in [`config/fleet_sites.csv`](./config/fleet_sites.csv) and
[`docs/BUILD_PLAN.md`](./docs/BUILD_PLAN.md).

| Cohort | Sites | Where | Köppen | Role |
|---|---|---|---|---|
| **DSUN-01** | 5 | MD / DE / NJ | `Cfa` | **Primary.** One operator, ~162 km spread — the distributed C&I story, and the only cohort where per-site visit economics are honest |
| **VEGAS-01** | 6 | NV | `Bwh` | Detector showcase. Five sites share byte-identical coordinates, so weather control is perfect and irradiance error cancels exactly |

**Target window: 1 Jan – 21 Aug 2019** (233 days), applied fleet-wide. Bounded by system 1367.
**Total 1.32 MWp**, 40.6 – 277.2 kWp per site — all genuine C&I rooftop scale.

**GOLDEN-01 was dropped on 19 Aug 2026.** Its two NREL Golden systems had no rows in the
processed data at all, while carrying 54% of the old headline capacity and rendering as
*healthy*. A site with no measurements cannot be called healthy. Every site now on screen has
real generation behind it. PRD §15's minimum-cohort weakness is still worth stating — it just
does not need two empty rows to make the point.

Two consequences worth remembering: VEGAS-01's shared coordinate means **one technician covers all
five Agassi roofs in a single trip**, so per-site `cost_per_visit_rm` overstates savings there — and
on a map those five markers stack perfectly. Use `Leaflet.markercluster` and let it spiderfy.
**Never jitter coordinates to fake separation.**

---

## Environment

Python 3.11 preferred. Local is currently 3.14 — `pvlib` and `scikit-learn` may lack wheels for it.
If installs fail, create a 3.11 venv rather than compiling from source. Keep
`pipeline/requirements.txt` current.

Frontend needs Node `^22.18.0 || >=24.12.0`.

---

## Commands

```
python pipeline/explore_bucket.py <prefix>   # list S3 paths, no download
python pipeline/fetch_pvdaq.py               # pull + aggregate to daily
python pipeline/generate_dispatch.py         # produce dispatch.json
python pipeline/validate_dispatch.py         # assert schema conformance
cd apps/web && npm run dev                   # dashboard
```

---

## Rubric — map every decision to a row

| Criterion | Weight | Where we earn it |
|---|---|---|
| Technical Feasibility | **25%** | Module 3 — the standout. Modules 2 and 5 support the case, don't lead with them |
| Commercial Viability | **25%** | Margin defence on bundled free-O&M contracts; RM/month output; the named buyer |
| Industry Relevance | **20%** | T1's *Clean Energy Asset Monitoring* sub-theme |
| Scalability | **15%** | Peer benchmarking gets **more** accurate as the fleet grows |
| ESG / National Impact | **15%** | Recovered generation → MWh → tCO₂e at **0.740 kgCO₂e/kWh** (Energy Commission 2024) |

Technical + Commercial are half the score. The Preliminary round cuts **300 teams to 30** and asks
*"is this a real attempt at solving a real problem with a real artifact?"* — won by shipping
something that runs, not by having the best idea.

---

## Style

Small functions, explicit names, no clever one-liners. This code gets handed to teammates mid-build
— readability beats brevity.

---

*Direction: PRD v2, 11 Aug 2026. Deadline: 31 Aug 2026, 23:59 MYT.*
*This file holds rules, direction and the technical contract — status belongs in
[`PROGRESS.md`](./PROGRESS.md).*

<div align="center">

# SolaraX

**Which sites in your solar fleet need a maintenance visit this month — and which don't.**

A triage layer for distributed solar fleets. No on-site sensors required.

[![CI](https://github.com/cindyyy11/SolaraX/actions/workflows/ci.yml/badge.svg)](https://github.com/cindyyy11/SolaraX/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Vue 3](https://img.shields.io/badge/vue-3-42b883.svg)](https://vuejs.org/)

Team **CinCaiLah** · MAIC Nexus Challenge 2026 · Track **T1 — AI for Clean Energy**

</div>

---

## Contents

- [The problem](#the-problem)
- [How it works](#how-it-works)
- [Quickstart](#quickstart)
- [Results](#results) — [baseline](#the-baseline-m2) · [detector](#the-detector-m3) · [scalability](#scalability--the-claim-measured)
- [What the method found on its own](#what-the-method-found-on-its-own)
- [Module status](#module-status)
- [Limitations](#limitations)
- [Project structure](#project-structure)
- [Documentation](#documentation)

---

## The problem

Malaysian solar developers sign bundled free-O&M obligations lasting up to 25 years — priced once,
delivered for decades. Those visits are scheduled by calendar, not by evidence. **A visit that finds
nothing is pure cost; a fault that sits unnoticed for six months is compounding lost generation.**

Global platforms (Sitemark, Raptor Maps, Scopito) price per-MW for utility scale and assume
site-grade instrumentation. A 300 kWp factory roof can carry neither. Any method that requires an
on-site pyranometer excludes most of this fleet.

## How it works

We predict what each site should have produced from **satellite weather alone**, with nothing
installed on any roof. Then we compare each site to its neighbours on the same day:

> ### A dip everyone shares is weather. A dip only one site has is a fault.

The size of the gap is the kWh lost, which becomes **RM/month at risk**. The output isn't a heatmap —
it's a list: *these sites, this month, this much money.* The value is as much in the sites you
**don't** visit as the ones you do.

**Why the peer layer is the technical claim, not the baseline.** Satellite irradiance carries real
error — ours measures 17.6 % on a single site-day, and no amount of model polish fixes that, because
it comes from resolving cloud timing across a ~50 km grid cell. But every site in a cohort is fed
from that same cell on the same day, so the error lands on all of them at once and *subtracts out* of
a peer comparison. The absolute baseline would need a sensor on every roof to resolve a 15 % fault.
The peer comparison resolves it without one.

That is also why accuracy **improves as the fleet grows** — [measured, not asserted](#scalability--the-claim-measured).

---

## Quickstart

**Pipeline** — Python 3.12 (3.11 also works).

```bash
pip install -r pipeline/requirements.txt

python pipeline/fetch_irradiance.py      # NASA POWER cache — run once, ~30 s
python pipeline/generate_dispatch.py     # writes dispatch.json, publishes to the frontend
python pipeline/validate_dispatch.py     # asserts schema conformance
python -m pytest pipeline/               # 108 tests
```

**Dashboard** — Node `^22.18.0 || >=24.12.0`.

```bash
cd apps/web
npm ci
npm run dev          # http://localhost:5173
```

Processed PVDAQ aggregates and the irradiance cache are committed, so the pipeline runs without
re-pulling 40 MB from S3. The dashboard reads the committed `dispatch.json` and falls back to a
second committed copy if its primary source is unavailable — a judging window is not the moment to
discover a hard dependency on a hosted service.

**Reproduce every number below:**

```bash
python pipeline/baseline.py --per-site      # M2 accuracy, per-site residuals
python pipeline/score_detector.py           # M3 accuracy, held out
python pipeline/scalability_study.py        # accuracy vs cohort size
```

---

## Results

Real generation data: **NREL PVDAQ**, 11 sites, 2 climate cohorts, 1.32 MWp, 233 days.
**We will not claim a number this repo cannot produce.**

### The baseline (M2)

*How well can you predict output with no sensors?* — 2,314 analysed site-days.

| Metric | Value |
|---|---|
| **R²** | **0.9008** |
| **Mean absolute error** | **17.57 %** |
| Normalised RMSE | 28.25 % |
| Median bias | −0.00 % |

Verified against a hand calculation at one site-day — S-1277 on the summer solstice, peak hour:

```
40.56 kWp × (1089.94/1000) × (1 + (−0.0035) × (84.90 − 25)) = 34.940074 kW
```

The pipeline agrees to **nine decimal places**.

### The detector (M3)

No open dataset labels site-level PV faults, so ground truth is manufactured: real measurements with
faults of known type, magnitude and date injected. **Labelled SIMULATED** — real method, synthetic
labels. The threshold is calibrated on one set of seeds and **reported on a disjoint set**.

| Metric | Value |
|---|---|
| Site-runs scored | 100 (40 faulted, **60 untouched controls**) |
| **Precision** | **86.7 %** |
| **Recall** | **65.0 %** |
| False-positive rate | 6.7 % |
| Cause-shape agreement | 88.5 % |

**Recall by injected severity — the ladder:**

| ≥ 30 % | 20–30 % | 10–20 % | Soiling ramp |
|:---:|:---:|:---:|:---:|
| **88.9 %** | 16.7 % | 45.5 % | **85.7 %** |

**The curve decaying is the point.** A recall curve that falls off at low severity is evidence of an
honest test; a flat 100 % would be evidence of a rigged one. The middle two rows rest on 6 and 11
events and their ordering is sampling noise, not a finding. The defensible summary: severe faults and
progressive soiling are caught reliably, and the floor is around 20 %.

### Scalability — the claim, measured

The rubric says peer benchmarking gets *more* accurate as the fleet grows. We tested it by shrinking
cohorts to every subset of each size and re-running only the peer comparison — 1,100 site-evaluations.

| Peers in cohort | **ROC AUC** | Precision | Recall |
|:---:|:---:|:---:|:---:|
| 3 | 0.855 | 84.2 % | 51.2 % |
| 4 | 0.897 | 78.2 % | 65.0 % |
| 5 | **0.913** | 86.7 % | 65.0 % |

AUC rises monotonically, and it is the headline **because it is threshold-free** — the operating
point was calibrated at cohort size 5, so a threshold-dependent metric alone would partly measure
that mismatch rather than the method's information content.

> **Ceiling, stated plainly:** the largest cohort in this fleet is 5 sites, so this is a measured
> trend across **3–5 peers**, not a demonstration at fleet scale.

### This month's fleet

**0 dispatch · 2 monitor · 9 healthy · RM 1,712/month at risk.**

Nothing clears the RM 1,500 visit threshold. That is the product working as designed — the detector
says something is wrong, the money says whether it is worth driving to.

---

## What the method found on its own

**S-1276 (Agassi Building B) has a real fault in the real data, and it is not one we injected.**

Its output runs 3.35 → 4.62 → 4.93 → 5.22 → 5.42 kWh/kWp/day from February to June, then drops to
**3.49 in July and 2.82 in August** — in Las Vegas, during the two months when output should peak.
The detector flags it at 90 % persistence and dates the divergence to early July.

The same site also reported **exactly 0.00 kWh on all 31 days of January** at full sampling. That one
broke our first attempt at the method, and finding out why made it better.

---

## Module status

Labelled **BUILT** (real data through a real model) / **SIMULATED** (real method, synthetic or sample
input) / **PLANNED** (not built). Live detail in [`PROGRESS.md`](./PROGRESS.md).

| # | Module | Status |
|:---:|---|---|
| 1 | Fleet data ingestion | ✅ **BUILT** — real NREL PVDAQ, 11 sites, 2 cohorts, 233 days |
| 2 | Sensor-free baseline | ✅ **BUILT** — pvlib on NASA POWER satellite irradiance |
| 3 | **Fleet peer benchmarking** ⭐ | ✅ **BUILT** — robust peer-deviation z-score |
| 4 | Economic ranking | ✅ **BUILT** — RP4 tariff, every constant sourced |
| 5 | Visual verification | 🟡 **SIMULATED** — classifier trained; not yet emitted into the artifact |
| 6 | Dashboard (Vue 3) | ✅ **BUILT** — four screens |
| 7 | API / hosted demo | ⬜ **PLANNED** — deploy config committed, URL not live ([`DEPLOY.md`](./DEPLOY.md)) |
| 8 | Testing & packaging | 🟡 108 tests + CI; demo video not started |

### Method, named

Every flag traces to a calculation a person can check by hand.
**An LLM may explain a score; it never computes one.**

| Module | Method |
|---|---|
| 2 — Sensor-free baseline | NASA POWER hourly GHI → Erbs decomposition → Hay-Davies transposition → SAPM cell temperature → PVWatts DC, scaled by one **fleet-wide** calibrated derate |
| 3 — Peer benchmarking ⭐ | **Robust peer-deviation z-score** — Iglewicz-Hoaglin modified z-score (median/MAD) across same-day cohort peers, on a reference-normalised performance ratio |
| 4 — Economic ranking | kWh lost × Malaysian **RP4** tariff → RM/month at risk → dispatch threshold |
| 5 — Visual verification | YOLOv8 classification as *evidence on an already-flagged site*, never as the detector |

---

## Limitations

Stated up front, because a method that cannot say what it misses is not a method.

- **The generation data is American** (NREL PVDAQ). It proves the method, not the market — no public
  per-site Malaysian PV time series exists, verified three ways in
  [`docs/RESEARCH.md`](./docs/RESEARCH.md) §5. The Malaysian *weather* half is real; the pilot is the ask.
- **Detection floor around 20 %.** Healthy sites genuinely spread ±7–9 % in peer-relative terms, and
  a shortfall has to clear that.
- **A fault present from day one is invisible** — the reference normalisation removes it by construction.
- **Correlated fleet-wide degradation is invisible to both layers.** If everything degrades together,
  the peer comparison sees nothing.
- **Fault labels are synthetic.** The defence is the decaying ladder and the 60 controls, not the labels.
- **Small cohorts degrade the statistic.** Five sites with two faults is 40 % contamination against
  MAD's 50 % breakdown point.

---

## Project structure

```
SolaraX/
├── config/          every commercial constant + model parameters + the fleet definition
├── pipeline/        BATCH: ingestion → baseline → detection → ranking → dispatch.json
├── apps/web/        SERVE: Vue 3 dashboard (ECharts + Leaflet)
├── data/            processed aggregates and the irradiance cache
├── docs/            the product and how it's built
└── hinfo/           the competition: rules, rubric, submission state
```

Three stages, strictly separated. `pipeline/` and `apps/web/` never import from each other — the only
thing crossing that line is **`dispatch.json`**, whose schema is frozen.

## Documentation

| Document | What it covers |
|---|---|
| [`docs/SolaraX_PRD_v2.md`](./docs/SolaraX_PRD_v2.md) | **Start here.** What we're building and why |
| [`docs/M2-M3-METHOD.md`](./docs/M2-M3-METHOD.md) | **The detection method** — formulas, measured accuracy, limitations |
| [`docs/Schema.md`](./docs/Schema.md) | The `dispatch.json` data contract (frozen) |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | Module-by-module design, with rejected alternatives |
| [`docs/RESEARCH.md`](./docs/RESEARCH.md) | Every sourced claim, with a URL |
| [`docs/DECISIONS.md`](./docs/DECISIONS.md) | Who decided what, when, and what's still open |
| [`HANDOFF.md`](./HANDOFF.md) | How to plug a module in without breaking anyone else's |
| [`DEPLOY.md`](./DEPLOY.md) | Getting the dashboard onto a public URL |
| [`PROGRESS.md`](./PROGRESS.md) | Current status, phase and blockers |

---

## Licence

[MIT](./LICENSE). IP remains with the team.

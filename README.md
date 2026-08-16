# SolaraX

**SolaraX tells a solar asset owner which sites in their distributed fleet need a maintenance visit
this month, and which don't — protecting the margin on long-tenure O&M commitments.**

Team **CinCaiLah** · MAIC Nexus Challenge 2026 · **Track T1 — AI for Clean Energy**

---

## The problem

Malaysian solar developers sign bundled free-O&M obligations lasting up to 25 years — priced once,
delivered for decades. Those visits are scheduled by calendar, not by evidence. A visit that finds
nothing is pure cost; a fault that sits unnoticed for six months is compounding lost generation.

Global platforms (Sitemark, Raptor Maps, Scopito) price per-MW for utility scale and assume
site-grade instrumentation. A 300 kWp factory roof can carry neither. **Any method that requires an
on-site pyranometer excludes most of this fleet.**

## The approach

SolaraX ingests inverter generation across a whole fleet, builds an expected-output baseline that
works **without on-site sensors**, and uses **the fleet itself as the control group** — sites in the
same weather region benchmark each other.

> A cohort-wide dip is weather. A single-site dip inside a stable cohort is a fault.
> The size of the gap is the kWh lost, which becomes **RM/month at risk**.

The output isn't a heatmap. It's a list: *these five sites, this month, this much money.* The value
is as much in the sites you **don't** visit as the ones you do.

**Why the cohort layer matters technically:** satellite irradiance carries error, but every site in a
cohort shares that error, so it cancels in the comparison. And accuracy *improves* as the fleet grows
— more sites per weather region means tighter cohorts and fewer false flags.

---

## Status — honest labelling

This project labels everything **BUILT** (real data, real model) / **SIMULATED** (real method,
sample input) / **PLANNED** (not yet built).

**As of 16 Aug 2026, the entire pipeline is PLANNED.** The architecture is designed and agreed; no
module is implemented yet. Live status: [`PROGRESS.md`](./PROGRESS.md).

| Component | Status |
|---|---|
| Architecture and method decisions | ✅ **Agreed** — [`docs/ARCHITECTURE-PLAN.md`](./docs/ARCHITECTURE-PLAN.md) |
| Real Malaysian satellite irradiance (PVGIS-ERA5, Bukit Raja/Klang) | ✅ **BUILT** — [`data/`](./data/) |
| Modules 1–8 | ⬜ **PLANNED** |

We will not claim a number this repo cannot produce.

---

## Method, named

| Module | Method |
|---|---|
| 2 — Sensor-free baseline | `pvlib` clear-sky (Ineichen–Perez) + temperature correction, from satellite irradiance (NASA POWER · PVGIS · Open-Meteo). Normalisation and filtering via **NREL RdTools** |
| 3 — Fleet peer benchmarking ⭐ | **Robust peer-deviation z-score** (median absolute deviation; Iglewicz–Hoaglin modified z-score) against a geographic weather cohort |
| 4 — Economic ranking | kWh lost × Malaysian **RP4** tariff (four-component + AFA) → RM/month at risk → dispatch threshold |
| 5 — Visual verification | YOLOv8 defect classification as *evidence on a flagged site*, never as the detector |

Every flag traces to a calculation a person can check by hand. **An LLM may explain a score; it never
computes one.**

### Known limitations, stated up front

- **The generation data is American** (NREL PVDAQ). It proves the method, not the market. No public
  per-site Malaysian PV time series exists — verified three ways in [`docs/RESEARCH.md`](./docs/RESEARCH.md) §5.
  The Malaysian *weather* half is real; the pilot is the ask.
- **Fault labels are synthetic.** No open dataset ships site-level fault labels, so accuracy comes
  from injecting faults of known type, magnitude and date into real series — with the failure region
  shown, not hidden.
- **Self-consumption curtailment is the hard problem.** C&I rooftops are clipped by on-site load, not
  only by faults. Mitigation is designed, not hand-waved — [`docs/ARCHITECTURE-PLAN.md`](./docs/ARCHITECTURE-PLAN.md) §3.4.
- **Correlated failure is a blind spot.** If a whole cohort degrades together, peer comparison sees
  nothing — which is why the absolute physics baseline exists alongside it.

---

## Repo map

```
SolaraX/
├── CLAUDE.md      rules and direction lock
├── PROGRESS.md    status, phase, blockers
├── docs/          the product and how it's built
├── hinfo/         the competition: rules, rubric, submission state
└── data/          real datasets pulled into the repo
```

Start with [`docs/PRD.md`](./docs/PRD.md) for what we're building, or
[`docs/ARCHITECTURE-PLAN.md`](./docs/ARCHITECTURE-PLAN.md) for how.

## Running it

⬜ **Not yet runnable.** Target: Modules 1→4 end-to-end from one command on a clean machine.
Instructions land here when that is true, not before.

## Licence

[MIT](./LICENSE). IP remains with the team.

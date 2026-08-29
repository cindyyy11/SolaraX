# TECHNICAL.md — how SolaraX is built

> Engineering reference: stack, data strategy, module specs, and the technical weaknesses we have
> answers for. Product spec lives in [`SolaraX_PRD_v2.md`](./SolaraX_PRD_v2.md); dataset
> evidence in [`DATASETS.md`](./DATASETS.md); sourced claims in [`RESEARCH.md`](./RESEARCH.md).
>
> **Verified 15 Aug 2026.** Two entries below changed recently — re-check before Phase 2.

---

## 1. Data strategy — three layers, each labelled

Full evidence and the dataset comparison are in [`DATASETS.md`](./DATASETS.md). The decision:

| Layer | What | Label |
|---|---|---|
| **A — Method proof** | PVDAQ California clusters (136 / 118 / 99 QA-pass sites in one weather region) + the HKUST Hong Kong 60-station rooftop set (CC0, 5-min inverter-level, 3 years, subtropical Asia) | **BUILT** — real measured data |
| **B — Malaysian anchoring** | Real satellite irradiance + temperature at real Malaysian coordinates (Bukit Raja/Klang, Senai, Nilai, Ipoh), run through the pvlib baseline | **BUILT** — real weather, real physics |
| **C — Fault ground truth** | Synthetic fault injection into real series: soiling ramps, string dropout, inverter outage, shading. No open dataset ships site-level fault labels | **SIMULATED** — say so on screen |
| *D — optional* | DOE Regional Test Centers: the only open data with **both** ground-measured and satellite irradiance at the same sites, 1-min, 4 climates incl. Orlando — lets us state a measured error bound on the sensor-free baseline | BUILT |

Two sites, two continents, two climates beats one. It converts *"your data is American"* from a
listed weakness into *"we validated across two climate zones."*

**Soiling injection rates are sourced, not invented** — Malaysian field studies measure up to
1.3%/day on flat modules and ~0.47%/day → 10.2% monthly ([`RESEARCH.md`](./RESEARCH.md) §3).

---

## 2. Stack

| Layer | Choice | Notes |
|---|---|---|
| Fleet data | **NREL PVDAQ via OEDI on AWS S3** | ⚠️ **The PVDAQ v3 REST API is decommissioned**; `developer.nrel.gov` retired 29 May 2026. Use `s3://oedi-data-lake/pvdaq/` — public Parquet, **no API key**, partitioned `parquet/pvdata/system_id=<id>/year=/month=/day=`. ⚠️ **Verified 16 Aug: data is long-format EAV (`metric_id`+`value`) at 1-minute resolution, and only 157 systems actually have time series — see [`ARCHITECTURE.md`](./ARCHITECTURE.md) §1.** Eight metadata tables (`site`, `system`, `inverters`, `modules`, `mount`, `meters`, `metrics`, `other_instruments`). Site list: `https://oedi-data-lake.s3.amazonaws.com/pvdaq/csv/systems_20250729.csv`. Helper: [`NREL/pvdaq_access`](https://github.com/NREL/pvdaq_access). Athena/PyAthena queries without bulk download. **Do not code against the old API.** |
| Irradiance / weather | **`pvlib.iotools`** | `get_nasa_power()` (global hourly), `get_pvgis_hourly()` / `get_pvgis_tmy()`. PVGIS-SARAH3 is 0.05°, 30-min, ±65° lat — Malaysia at 1–7°N is well inside. Also `get_cams()`, `get_era5()`, `get_merra2()`, NSRDB PSM4. **No pyranometer dependency — this is the wedge.** |
| Expected-output baseline | `pvlib` clear-sky (Ineichen–Perez or Simplified Solis) + temperature correction | Deliberately transparent and hand-checkable. IEC 61724-1's satellite-irradiance provision is the standards argument — ⬜ **still unsourced, see [`RESEARCH.md`](./RESEARCH.md) §6.** |
| Degradation / soiling analysis | **[NREL RdTools](https://github.com/NREL/rdtools)** | Already implements **clear-sky normalisation** — PR from modelled rather than measured irradiance, explicitly for when sensors are "misaligned, out of calibration, or unavailable." Use `analysis_chains.TrendAnalysis`; don't reimplement. ⚠️ See §5. |
| Anomaly detection | A **named** statistical method — peer-deviation z-score or isolation forest | Must be stated by name. Never "AI detects". |
| Vision model | Fine-tuned on ELPV / public RGB PV-defect sets | Secondary, verification only. |
| Economic layer | Config-driven named constants | ⚠️ **Tariff is not a single RM/kWh.** Malaysian non-domestic runs on the **RP4 structure since 1 Jul 2025** (in force to 31 Dec 2027): energy + capacity + network + retail charges, plus **AFA** (replaced ICPT; 3.59 sen/kWh in Jul 2026). Categories by supply voltage (LV/MV/HV). Source: `mytnb.com.my`. |
| Dashboard | Public URL, no login (Vercel / Streamlit / HF Space class) | The four screens in PRD v2 §4. |
| API | Simple REST/JSON between pipeline and dashboard | Frames the "plugs into an O&M ticketing system" story. |

**Note:** Chang Zhe's approved tech-stack and system-architecture slides (14 Aug) live in the team's
Canva deck, **not in this repo**. If they conflict with this table, they win — export them here and
reconcile. See [`DECISIONS.md`](./DECISIONS.md) §6.

---

## 3. Module specs

| # | Module | Build notes |
|---|---|---|
| 1 | **Fleet Data Ingestion** | Everything keyed by `site_id`. Every downstream module operates over a fleet, not a farm. Timestamp alignment, missing-value handling, unit consistency, per-site capacity normalisation. |
| 2 | **Sensor-Free Baseline** | Satellite irradiance + ambient temperature + system specs → expected output per site. Every flag must trace to a calculation checkable by hand. |
| 3 | **Fleet Peer Benchmarking** ⭐ | The differentiator. Cluster sites into weather/geo cohorts; compute a normalised performance index per site; measure divergence from the cohort distribution by a named method. Cohort-wide dip = weather. Single-site dip in a stable cohort = fault. Cohort membership also cancels satellite irradiance error, since the whole cohort shares it. |
| 4 | **Economic Ranking** | kWh/month lost × tariff → **RM/month at risk**, ranked against assumed cost-per-visit into a dispatch threshold. Every commercial constant in **one config file**, named and sourced. |
| 5 | **Drone & Visual Verification** | Defect class + confidence attached to a flagged site as evidence. Where imagery is unavailable, the flag stands on electrical evidence alone. |
| 6 | **Dispatch Dashboard** | Four screens, public URL, no login wall. |
| 7 | **API Layer** | Exposes the ranked queue so the dashboard never touches model code. |
| 8 | **Testing & Packaging** | Clean-environment reproducibility, demo recording, deliverables. |

---

## 4. Non-functional requirements

- **Explainability** — no module outputs a score without a traceable calculation. "Why is this site
  flagged" must have a numeric, named-method answer. An LLM may *explain* a score; it must never
  *compute* one.
- **Sensor independence** — no module hard-requires on-site irradiance. Satellite is the default
  path; on-site data is an optional accuracy upgrade.
- **Data provenance** — real public datasets only. No fabricated data. (This is why the Chile
  database is excluded — its values are simulated, not measured. See `DATASETS.md` §2.4.)
- **Reproducibility** — Modules 1→4 run end-to-end from one command on a clean machine.
- **Public accessibility** — dashboard and repo reachable without login throughout the judging
  window (early Sep 2026).

---

## 5. Technical weaknesses — have the answer ready

- **RdTools already does sensor-free PR.** A technical judge may know it and ask what's new. Answer:
  RdTools does **single-system** degradation and soiling. SolaraX adds the **cross-site cohort
  layer** — fleet as its own control group, so satellite error cancels — plus **economic ranking
  into a dispatch decision**. Neither exists in RdTools. Rehearse this.
- **Self-consumption curtailment is the hardest problem.** C&I rooftops under NEM/ATAP are sized to
  on-site demand, so output is often clipped by load, not faults. Cohorts help partly (neighbours
  share public holidays) but not fully (they don't share a production schedule). Tackle in Phase 1.
  Malaysian evidence: a Kuala Terengganu study measured a **~35% generation drop across the
  monsoon** — seasonal effects are large and real.
- **Cohort logic needs minimum fleet density** — below ~5 sites per weather region the control group
  is too weak. State the minimum; note it eases as the fleet grows. That's the scalability story,
  not a flaw.
- **Ground truth is limited** — no open dataset labels site-level faults, hence Layer C. Synthetic
  injection into real data is the standard approach and gives an honest precision/recall figure
  because we control the injection.
- **Correlated failure is a blind spot** — if a whole cohort degrades together (regional haze, a bad
  module batch), cohort comparison sees nothing. Module 2's absolute baseline catches fleet-wide
  drift; Module 3 catches site-specific faults. Complementary — that's why both exist.
- **Thermal imaging can't reliably detect microcracks** — electroluminescence is the standard for
  that. Don't claim otherwise.
- **The data is not Malaysian.** PVDAQ and HKUST prove the method; Layer B anchors it to real
  Malaysian weather. No public per-site Malaysian generation data exists — verified three ways
  ([`RESEARCH.md`](./RESEARCH.md) §5). The pilot is the ask.
- **Ranking ignores repair cost** — deferred by team agreement 14 Aug. A site could in principle top
  the queue where the fix costs more than the loss (~RM 46k inverter replacement against RM 1,900/mo
  loss), but most solar repairs pay back in months, and no public repair-invoice data exists to
  model from. It would sit in the CONFIRM step and needs component-level diagnosis first, which a
  drone can't give. **The team found this itself — that's a strength in Q&A.**

---

## 6. Validation design — decide before Phase 2

Module 3 must produce a **stated accuracy/precision figure from a real test run**, not an estimate.

1. **Free sanity check:** published Malaysian systems run at **PR 56–87%**, healthy C&I 75–85%
   ([`RESEARCH.md`](./RESEARCH.md) §2). If the baseline implies a Malaysian PR outside that band,
   the model is wrong.
2. **Hand-check:** does Module 2's output match a hand-calculated expected value for one sample day
   at one site?
3. **Injection test:** inject faults of known type, magnitude and start date into real series;
   measure detection precision, recall and days-to-detect.
4. **Real-world echo:** the Universiti Malaya study measured **86.74% vs 56.30% PR on two arrays at
   the same site, same weather** — a published Malaysian instance of exactly the divergence SolaraX
   detects. Useful as a slide, and as a shape to reproduce.

---

## 7. Architecture

⬜ **To be filled.** Chang Zhe's approved system-architecture slides are in Canva only. Export and
reproduce here as: ingestion → baseline → cohort detection → economics → API → dashboard. This also
becomes the technical architecture PDF (≤ 5 MB) for submission.

# Dataset options for SolaraX — evidence and comparison

> **Status: decision not yet made.** This file exists so the team can choose from evidence rather
> than assumption. Compiled 15 Aug 2026.
>
> Sources: my own analysis of NREL's live PVDAQ site metadata (`systems_20250729.csv`, 1,862 rows,
> downloaded and analysed 15 Aug 2026), plus Table 4 of **Chen, Li, Braid et al., "Open data sets
> for assessing photovoltaic system reliability", *Applied Energy* 395 (2025) 126132**
> ([open access](https://escholarship.org/content/qt1xr4f1fm/qt1xr4f1fm.pdf), CC-BY,
> authors from LBNL, NREL, Sandia and UCF/FSEC). Where the survey and the live metadata disagree,
> the live metadata wins and is marked.

---

## 1. What SolaraX actually needs from data

Module 3 is the differentiator, and it constrains everything. To do fleet peer benchmarking you need:

| Requirement | Why | Hard minimum |
|---|---|---|
| **Many sites in one weather region** | The cohort *is* the control group | ≥ 5 per region (PRD v2 §15); more is better |
| **Real measured generation** | "No fabricated data" is a non-functional requirement | Measured, not modelled |
| **Site coordinates + capacity + tilt/azimuth** | Needed to run the pvlib baseline (Module 2) | All four |
| **≥ 90 days continuous** | Screen 2 shows a 90-day actual-vs-expected chart | 90 days |
| **Sub-daily resolution** | Distinguishes curtailment from faults | ≤ 1 hour |
| C&I scale (100 kWp–2 MWp) | Matches the stated buyer | *Preferred, not essential* |
| Tropical/subtropical climate | Malaysia proxy | *Preferred, not essential* |
| Fault labels | Ground truth for an accuracy figure | *Nice to have — almost nothing has it* |

---

## 2. The candidates

### 2.1 NREL PVDAQ — ⭐ best cohort density, verified directly

I downloaded and analysed the live site metadata rather than trusting a summary. Note the survey
paper lists PVDAQ as "158 PV systems" — **that is out of date.** The current public metadata has:

| Metric | Value |
|---|---|
| Total systems | **1,862** |
| Passing NREL's own QA | **1,564** |
| Geographic clusters with ≥ 5 QA-pass systems (~55 km grouping) | **72** |
| Largest clusters | **136** (Los Angeles), **118** (Orange County), **99** (San Diego), **79** (Bay Area), 39 (Boston), 36 (Gaithersburg MD) |
| Systems in the 100–2,000 kWp C&I band | **28** — and only **2** clusters of ≥ 5 |
| Tropical (Köppen A) systems | **9 total, 7 passing** — all 4.5–11.7 kWp, Florida and Hawaii |
| Metadata fields | `system_id, latitude, longitude, elevation, dc_capacity_kW, kg_climate, tracking, type (roof/ground), azimuth, tilt, first/last timestamp, years, qa_status, qa_issue` |

**Verdict.** Superb for *proving the method* — a 136-system cohort in one weather region is far
beyond the ≥5 minimum, and the metadata has everything Module 2 needs. **But it cannot carry the
Malaysian or the C&I story**: the C&I band is nearly empty and there is effectively no tropical data.

Access: `s3://oedi-data-lake/pvdaq/` — public Parquet, no API key, partitioned
`system_id/year/month/day`. Site list: `https://oedi-data-lake.s3.amazonaws.com/pvdaq/csv/systems_20250729.csv`.
Helper: [`NREL/pvdaq_access`](https://github.com/NREL/pvdaq_access). ⚠️ The old v3 REST API is
decommissioned — do not code against it.

### 2.2 HKUST Hong Kong rooftop fleet — ⭐ best climate + resolution match

[Nature *Scientific Data*](https://www.nature.com/articles/s41597-025-04397-y) ·
[Dryad, CC0 1.0](https://datadryad.org/dataset/doi:10.5061/dryad.m37pvmd99) · 296 MB

- **60 grid-connected rooftop PV stations**, 2021–2023 (3 full years)
- **5-minute inverter-level** generation; 37 of the 60 also have **panel-level optimiser** data
- **1-minute on-site weather station** data
- Metadata in Brick schema (`.ttl`), queryable via SPARQL —
  [example queries](https://github.com/ZinanLin-Oscar/SPARQL-Example-for-PV-Brick-Model)
- **CC0 1.0 (public domain)** — no licence friction at all

**Verdict.** The single best climate match available openly: subtropical coastal Asia, monsoon-
influenced, humid. Rooftop, not utility farm. Sub-array granularity on most stations. **Caveat:
all 60 are on the HKUST campus**, so it is one weather region — a perfect single cohort for Module
3, but it will not exercise cross-cohort clustering.

### 2.3 The rest — from the *Applied Energy* survey, Table 4

| Dataset | Sites | Location | Period | Notes | Fit |
|---|---|---|---|---|---|
| **DOE Regional Test Centers** | 8 identical c-Si systems | Albuquerque, Denver, Las Vegas, **Orlando** | 2014–2019 | **1-minute data with BOTH ground-measured and satellite weather** | ⭐ Small, but uniquely able to **validate the satellite-vs-pyranometer wedge** directly |
| **CWRU/UCF SunSmart Schools** | 30 systems × 3 arrays = 90 | **Florida** | 2012–2016 | 10–12 kW PV+battery on public schools; DC current and voltage | Good — humid subtropical, closest US climate to Malaysia, and schools are non-residential buildings |
| **UCSD Microgrid** | **26 PV plants** | San Diego campus | 2015–2020 | Real AC power; downloadable from the paper's supplementary material | Good second campus-fleet cohort |
| **DKASC Alice Springs** | **38 systems** (2–10.5 kW) | Australia | **2009–2024** | Free open access, CSV; multi-technology demo site; higher resolution on request | Good — 15 years is the longest run available |
| **ARENA Yulara** | 5 systems (**22.6–1,058 kW**) | Australia | 2016–2024 | The **only** open set in the C&I capacity band | Narrow but on-scale |
| **INESC TEC** | 44 household units (1.1–3.7 kWp) | Portugal | 2011–2013 | 15-min smart meter, hourly series | Marginal — small, old, residential |
| **Elia Open Data** | 12 production sets | Belgium, Germany | 2018–2024 | Grid/market aggregates | ✗ Not per-site |
| **Stanford Benchmark** | 1 system (30.1 kW) | California | 2017–2019 | 1-min | ✗ Single site |

### 2.4 Also investigated, and why they're rejected

| Dataset | Why not |
|---|---|
| **Chile GCPV database** (103 systems) | Looks ideal on size, but the values are **capacity factors simulated with pvlib + ERA5/MERRA-2 reanalysis — not measured output.** Using it would breach "only real, public datasets. No fabricated data." **Do not use.** |
| **Sheffield Solar Microgen** (7,000+ UK systems) | Data is **cumulative kWh meter readings**, like a meter photo. Too coarse to detect divergence onset. |
| **GPVS-Faults** (Mendeley, 16 labelled fault scenarios, 2M samples) | Lab microgrid, **millisecond-level electrical waveforms** for inverter/IGBT/MPPT fault classification. Real fault labels, but the wrong granularity entirely — SolaraX triages monthly energy, not switching transients. |
| **Ausgrid Solar Home** (300 homes, NSW, 30-min, 2010–2013) | Usable as a large single-region cohort, but **gross meter only** (no inverter or DC detail), and the data is 13 years old. Fallback, not first choice. |
| **Kaggle "Solar Power Generation Data"** (2 Indian plants, 22 inverters each, 15-min) | Only **34 days**, and it is inverter-peers-within-one-plant rather than sites-within-a-fleet. Useful as a quick tropical sanity check, not as the backbone. |

---

## 3. Malaysian data — the honest position

**There is no public, per-site Malaysian PV generation dataset.** Verified 15 Aug 2026:

- `data.gov.my` — no energy or electricity generation datasets in the catalogue at all.
- **SEDA's National PV Monitoring System** (`pvms.seda.gov.my/pvportal/`) exists and is the official
  national monitoring portal, but it refused connection from here and shows no evidence of bulk
  export or an API.
- **SERIS (NUS Singapore)** runs a commercial monitoring platform across **150+ systems in
  Singapore, Australia, Cambodia, Germany, India, Indonesia, Malaysia, the Philippines and
  Vietnam.** Tropical fleet data therefore exists — it just isn't open. This is worth citing as
  evidence the market is real, and is a plausible pilot-partner conversation.

**Malaysian data we *can* legitimately use — and it's more than it sounds:**

| Source | What it gives | Access |
|---|---|---|
| **NASA POWER** | Hourly irradiance + temperature, global, at any Malaysian coordinate | `pvlib.iotools.get_nasa_power()` |
| **PVGIS-SARAH3** | **0.05° × 0.05°, 30-minute** satellite irradiance; coverage is ±65° lat/lon, so Malaysia at 1–7°N is well inside | `pvlib.iotools.get_pvgis_hourly()` |
| **PVGIS-ERA5** | Worldwide hourly fallback at 0.28° | same |

So the *weather half* of a Malaysian site model can be entirely real. Only the generation half
cannot.

---

## 4. Recommendation — a three-layer strategy

Each layer maps onto a BUILT / SIMULATED label you already committed to, which turns the data
story from a weakness into a credibility asset.

**Layer A — Method proof · BUILT · real measured data**
PVDAQ's dense California clusters (136 / 118 / 99 systems) give Module 3 its accuracy figure with
a control group an order of magnitude past the minimum. Add the **HKUST Hong Kong 60-station set**
as a second, non-US, subtropical validation. That converts the "your data is American" objection
into *"we validated on two continents and two climate zones"* — a much better answer than the one
PRD v2 currently plans to give.

**Layer B — Malaysian anchoring · BUILT · real Malaysian weather**
Run the Module 2 baseline on **real NASA POWER / PVGIS irradiance and temperature at real Malaysian
coordinates.** The PRD mockup already names Bukit Raja (Klang), Senai, Nilai and Ipoh — use their
actual lat/lon. Nothing is fabricated: real satellite weather, real physics, transparent pvlib.

**Layer C — Fault ground truth · SIMULATED · clearly labelled**
No open dataset ships site-level fault labels — PRD v2 §15 already names synthetic fault injection
as the answer, and this research confirms there is no alternative. Inject soiling ramps, string
dropouts, inverter outages and shading into real series. Because you control the injection, the
precision/recall figure is honest and defensible.

**Optional Layer D — validate the wedge itself.** The **DOE RTC** set is the only open data with
*both* ground-measured and satellite irradiance at the same sites, at 1-minute resolution, in four
climates including Orlando. Eight systems is small, but it lets you state a measured error bound on
the sensor-free baseline — the single most attackable claim in the product.

---

## 5. Tooling note — read before building Module 2

**[NREL RdTools](https://github.com/NREL/rdtools)** is an open-source Python library for PV
degradation and soiling analysis that already implements **clear-sky normalisation** — performance
ratio computed from *modelled* rather than site-measured irradiance, explicitly for cases where
"ground-based irradiance sensors are misaligned, out of calibration, **or unavailable**."

Two consequences, both important:

1. **Use it.** Don't reimplement normalise → filter → aggregate → analyse. `TrendAnalysis` in
   `analysis_chains.py` is the object-oriented entry point.
2. **⚠️ Be ready for the question.** A technical judge may know RdTools and ask what is new here.
   The answer must be crisp: RdTools does **single-system** degradation and soiling. SolaraX's
   contribution is the **cross-site cohort layer** — using the fleet as its own control group so
   satellite irradiance error cancels — plus the **economic ranking into a dispatch decision**.
   Neither exists in RdTools. Rehearse this; do not be caught out by it.

Related, also worth citing: NREL's **PV Fleet Performance Data Initiative** has analysed ~19,000–24,000
inverter channels across 8.5 GW and published a **median degradation of −0.75%/yr, ranging −0.5%/yr
in temperate zones to −0.88%/yr in hot climates.** Tier 1, citable, and directly supports the
"hotter climate degrades faster" angle for Malaysia.

---

## 6. Open questions before locking the choice

1. Download the HKUST Dryad archive and confirm the actual column names, per-station capacity and
   orientation metadata, and whether outages are flagged. The Dryad landing page doesn't list them.
2. Confirm PVDAQ data volume for one California cluster — 136 systems × years of 15-minute Parquet
   may be large. Consider Athena queries rather than bulk download.
3. Decide whether the demo fleet is HK (one real 60-site cohort) or PVDAQ (multiple real cohorts)
   or both. **Both is the strongest story and roughly the same work**, since ingestion is
   `site_id`-keyed by design.
4. ~~Check whether PVOutput.org has Malaysian systems.~~ **Checked 15 Aug 2026 — see §7.**

---

## 7. PVOutput.org — checked, and the nearest tropical fleet found anywhere

[PVOutput.org](https://pvoutput.org/) is a free crowd-sourced platform where owners upload live PV
output. Free API: **60 requests/hour** (300 if you donate), **5-minute** resolution, `Get System`
and `Get Status` services. Its [country statistics page](https://pvoutput.org/country.jsp) gives
registered systems per country.

**Malaysia does not appear in the top 25 countries** (checked 15 Aug 2026). So PVOutput does not
solve the Malaysian data gap either.

**But Thailand does: 218 systems, 8.710 MW registered** — averaging ~40 kWp, i.e. small-commercial
rather than residential scale. Thailand is tropical monsoon, the closest climate analogue to
Malaysia in any open source found in this entire review. For comparison, the only other tropical
entry is the Maldives at 5 systems.

**Worth investigating before Phase 2, with eyes open:**

| Upside | Risk |
|---|---|
| Genuinely tropical Southeast Asian, ~40 kWp average — the right climate *and* roughly the right scale | Crowd-sourced: data quality, gaps and mis-declared capacity are all unmanaged |
| 5-minute resolution, free API, systems have declared capacity and location | 60 req/hour throttle makes bulk history slow to pull |
| If clustered around Bangkok, that is a real multi-site tropical cohort | Check PVOutput's terms before any bulk download or redistribution |
| Open-source downloader exists: [openclimatefix/pvoutput](https://github.com/openclimatefix/pvoutput) | Unknown how many of the 218 have continuous history |

**Suggested framing if it works out:** PVDAQ proves the method at scale, Hong Kong proves it in a
subtropical Asian rooftop fleet, Thailand demonstrates it on tropical Southeast Asian sites, and
NASA POWER/PVGIS anchor the expected-output model to real Malaysian coordinates. The Malaysian
*pilot* remains the ask — which is what PRD v2 already says, now backed by an explicit search
showing no Malaysian per-site data is public.

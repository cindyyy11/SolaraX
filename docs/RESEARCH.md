# RESEARCH.md — evidence base for SolaraX (PRD v2)

> **Purpose.** Every factual claim SolaraX makes should trace to a line in this file with a URL.
> "Cite or omit" — see [`../CLAUDE.md`](../CLAUDE.md) §4.
>
> **Status: partial.** Sections 1–4 are done and verified 15 Aug 2026. Section 6 lists what still
> needs sourcing. The superseded fire-risk evidence base was **deleted from the repo on 16 Aug** —
> do not reintroduce it, and do not cite fire-risk statistics anywhere.
>
> **Tier key:** **T1** = public and checkable · **T2** = labelled assumption with a range ·
> **T3** = needs insider knowledge, delete or design around.

---

## 1. The buyer's obligation — the core of the thesis ✅ VERIFIED

This is the single most load-bearing claim in the product: that a developer signs a fixed-price
maintenance obligation lasting up to 25 years. **Confirmed directly from Solarvest's own product
page**, with exact wording.

| Product | Tenure | Upfront | O&M — Solarvest's exact words | Ownership |
|---|---|---|---|---|
| **Powerflex Lite** | up to **7 years** | "No upfront cost" | **"Free up to 7 years O&M"** | You own the asset on completion |
| **Powerflex Hybrid** | up to **12 years** | "No upfront cost" | **"Free up to 12 years O&M"** | Co-ownership with Solarvest during payment |
| **Powerlease** | up to **25 years** | "Zero investment" | **"Free up to 25 years O&M"** | You own the asset at end of lease |

**Tier 1.** Source: <https://solarvest.com/solar-financing/> (retrieved 15 Aug 2026).

> ⚠️ An earlier draft of `CLAUDE.md` flagged this as unverified. **It is verified.** PRD v2's
> "free O&M for up to 7, 12 and 25 years" is exactly right and directly quotable.

**How to use it:** cite as a *documented example of a market pattern*, never as a claim about
Solarvest's internal costs (that would be Tier 3). Note also that **Solarvest is both T1's industry
partner and a co-organiser of MAIC** — partner framing only.

---

## 2. Measured Malaysian PV performance — "the generation half" ✅

No Malaysian *time-series* is public (§5), but **measured performance results are published**, and
they give a real validation band for the Module 2 baseline.

| Study | System | Location | Period | Resolution | Performance ratio | Other measured results |
|---|---|---|---|---|---|---|
| **Saleheen et al.** — [*Energy & Buildings*-class study, cited in Sci. Rep. 2025](https://www.nature.com/articles/s41598-025-26765-9) | **232.5 kWp rooftop** | **Monash University Malaysia** | 2019 | **5-minute** | **85.4%** | CUF 14.85% · 301.5 MWh generated vs 305.0 MWh target · system efficiency 9.15% · **LCOE 0.396 MYR/kWh** · 177 t CO₂ avoided |
| **Universiti Malaya (PEARL lab)** — [*Scientific Reports* 15 (2025) s41598-025-26765-9](https://www.nature.com/articles/s41598-025-26765-9) | 3.575 kWp — Array 1 poly-Si, Array 2 mono-Si | Kuala Lumpur | **36 months**, Jan 2020 – Dec 2022 | — | **Array 1: 86.74%**<br>**Array 2: 56.30%** | Analysed per **IEC 61724**, 11 parameters · AC output 3,881.67 kWh vs 1,120.48 kWh · forecast degradation 10.58% / 11.99% |
| **Anang et al.** — [*Energy & Buildings* 248 (2021) 111182](https://www.sciencedirect.com/science/article/abs/pii/S0378778821004667) | 7.8 kWp rooftop | Kuala Terengganu | 2018–2019 (2 yrs) | — | best **75.72%** | Payback 5–7 years · 7.45 t CO₂/yr · **monsoon cut generation ~35%** in the wet period |
| Three GC-PV systems | 6.575 kWp combined | Malaysia | — | — | **83%** | Annual yield **1,033 kWh/kWp** · daily final yield 4.0–4.5 kWh/kWp |
| UKM system | 5.76 kWp | Bangi | — | — | **63.6 ± 1.0%** | Final yield **949.0 ± 0.5 kWh/kWp** |
| 5 kWp tropical system | 5 kWp | Malaysia | — | — | PV 73.12%, inverter 98.56% | Daily yield 2.51 kWh/kWp/day · capacity factor 10.47% |

### What this gives SolaraX

1. **A sanity band.** Real Malaysian systems run at roughly **PR 56%–87%**, with healthy C&I
   rooftop around **75–85%**. If the pvlib baseline implies a Malaysian PR outside that, the model
   is wrong. This is a free, citable validation check for Module 2.
2. **A same-site divergence example.** The Universiti Malaya study found **86.74% vs 56.30% on two
   arrays at the same site in the same weather.** That is precisely the signal SolaraX detects —
   a real Malaysian example, not a hypothetical.
3. **The closest Malaysian C&I reference case.** Monash's **232.5 kWp** rooftop at **5-minute
   resolution** is the nearest published analogue to the "300 kWp factory roof" in PRD v2, and it
   reports an LCOE in ringgit.
4. **The curtailment/monsoon problem, quantified.** Kuala Terengganu measured a **~35% generation
   drop during the tropical monsoon**. PRD v2 §15 names seasonal effects as a hard problem — now
   there is a number attached.

---

## 3. Malaysian soiling and degradation — inputs for fault simulation ✅

Layer C of the data strategy injects synthetic faults into real data
([`DATASETS.md`](./DATASETS.md) §4). These published Malaysian figures mean the injection
parameters are **sourced rather than invented**.

| Finding | Value | Use |
|---|---|---|
| Soiling rate, flat modules | up to **1.3% per day** | Upper bound for a soiling ramp |
| Soiling loss, field study | max **~0.47%/day**, **10.2% total monthly loss** | Realistic soiling injection rate |
| Malaysian dust character | **acidic and wet**; output reduction measured up to **58.67%** | Why Malaysian soiling ≠ desert soiling |
| Humidity | **80–90%** rainy season, ~47% dry season | Context for degradation modelling |
| Wind speed | **< 3 m/s** — low | Little natural cleaning; soiling persists |
| Long-term degradation | 9-year outdoor mono-Si study, Kuala Lumpur | Tropical degradation reference |
| NREL PV Fleets (global) | median **−0.75%/yr**, **−0.5%/yr temperate → −0.88%/yr hot climates** | Hot-climate degradation is measurably worse — supports the Malaysian case |

Sources: [Impact of Soiling Rate on Solar PV Panel in Malaysia](https://www.researchgate.net/publication/328742714_Impact_of_Soiling_Rate_on_Solar_Photovoltaic_Panel_in_Malaysia) ·
[Electrical Performance and Degradation of Field-Aged PV Modules in Tropical Climates](https://www.sciencedirect.com/science/article/pii/S2590174524001971) ·
[Long-Term Degradation and Defects of PV Modules in Tropical Climates: A Case Study of Malaysia, *IET RPG* 2026](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/rpg2.70198) ·
[NREL PV Fleet Performance Data Initiative](https://www.nrel.gov/pv/fleet-performance-data-initiative)

---

## 4. Malaysian market, policy and ESG numbers ✅

| Claim | Value | Source | Tier |
|---|---|---|---|
| **Grid emission factor** | **0.740 kgCO₂e/kWh** (Energy Commission, 2024); 0.758 in 2021 | [Suruhanjaya Tenaga, myenergystats](https://myenergystats.st.gov.my/documents/d/guest/grid-emission-factor-gef-in-malaysia) · [GEF projections 2025–2034, Single Buyer](https://singlebuyer.com.my/docs/default-source/about/gef-projection-publication_31122025v1.pdf) | **T1** — use this for the ESG row (15%) |
| Total installed solar PV | **5,777.73 MW** cumulative (LSS + FiT + NEM), as of 2025 | IEA-PVPS / Energy Commission | T1 |
| Rooftop solar | **1.72 GW as of July 2025 = ~40% of total installed *solar* capacity** | [TransitionZero](https://www.transitionzero.org/insights/tenaga-trends-how-were-monitoring-malaysias-evolving-rooftop-solar-landscape) | T1 — ⚠️ denominator is *solar* capacity, not all national capacity |
| Solar ATAP | Live **1 Jan 2026**; fixed quota removed, government retains reserve authority to impose limits for grid stability | SEDA / SolarQuarter | T1 |
| Electricity tariff structure | **RP4 in force 1 Jul 2025 → 31 Dec 2027**: energy + capacity + network + retail charges, plus **AFA** (replaced ICPT; 3.59 sen/kWh in July 2026). Non-domestic categorised by supply voltage (LV/MV/HV) | [myTNB](https://www.mytnb.com.my/business/understand-your-bill/pricing-tariff) | **T1** — Module 4 must model this, not a flat rate |
| IEA-PVPS Malaysia national statistics | Annual National Survey Reports: [2019](https://iea-pvps.org/wp-content/uploads/2020/08/NSR_Malaysia_2019.pdf) (390.51 MWac added in 2019), [2018](https://iea-pvps.org/wp-content/uploads/2020/01/NSR_Malaysia_2018.pdf), [2017](https://iea-pvps.org/wp-content/uploads/2020/01/National_Survey_Report_of_PV_Power_Applications_in_Malaysia-_2017.pdf), [2015](https://iea-pvps.org/wp-content/uploads/2020/01/National_Survey_Report_of_PV_Power_Applications_in_Malaysia_-_2015.pdf) | IEA-PVPS | T1 |

### The companies that hold the data

Relevant because it shows the buyer exists, has scale, and already runs O&M — and because it names
who a pilot conversation would be with.

| Company | Scale | O&M / monitoring position |
|---|---|---|
| **Solarvest** (T1 partner, MAIC co-organiser) | >**2,000 MW** ongoing + completed across 8 APAC countries; market cap ~RM1.78bn | O&M segment: 2–5 year workmanship warranty, **performance monitoring**, on-site support and repair. Powervest bundles free O&M up to 25 years (§1) |
| **Plus Xnergy** | — | C&I rooftop, end-to-end engineering |
| **Samaiden** | portfolio >**700 MWp**; market cap ~RM569m | Long-term O&M: performance monitoring, panel cleaning, corrective repairs |
| **Pekat** | market cap ~RM980m | Solar EPCC |
| **Cypark** | market cap ~RM753m | Large solar farms, EPCC |
| **SERIS** (NUS Singapore) | **150+ systems** monitored across Singapore, Australia, Cambodia, Germany, India, Indonesia, **Malaysia**, Philippines, Vietnam | Cloud-based real-time PV monitoring platform, tropical-tuned. **Tropical fleet data exists — it just isn't open.** Plausible pilot/data partner |

Sources: [Mordor Intelligence — Malaysia RE companies](https://www.mordorintelligence.com/industry-reports/malaysia-renewable-energy-market/companies) ·
[SERIS PV System Performance Monitoring](https://www.seris.nus.edu.sg/services/pv-system-performance-monitoring/)

---

## 5. What is *not* available — state this plainly, don't let a judge find it

**There is no public, per-site Malaysian PV generation time series.** Verified three independent
ways on 15 Aug 2026:

1. **`data.gov.my`** — no energy or electricity datasets in the catalogue at all.
2. **SEDA National PV Monitoring System** (`pvms.seda.gov.my/pvportal/`) — exists as the official
   national portal, but refused connection and shows no bulk export or API.
3. **PVOutput.org** — Malaysia does not appear in the top-25 countries by registered systems.
   (Thailand does: **218 systems, 8.710 MW** — the nearest tropical proxy found anywhere.)

**This is a finding, not a gap.** It is exactly why the pilot ask exists, and saying it plainly is
stronger than being asked. Full detail and the workaround in [`DATASETS.md`](./DATASETS.md).

---

## 6. Open items — do not ship these claims yet

- [ ] 🅿️ **PARKED — IEC 61724-1's satellite-irradiance provision.** *Appears in PRD v2 §5 and is
  **load-bearing for the entire sensor-free wedge.*** The standard defines monitoring classes A/B/C
  with decreasing accuracy requirements; the claim is that it permits satellite-derived irradiance
  in place of an on-site pyranometer for smaller commercial systems. **Nobody on the team has read
  the actual clause** — the standard is paywalled (~CHF 300 from IEC).
  **How to close it:** UTM/UKM library access, or the Malaysian adopted version **MS IEC 61724** via
  SIRIM, or an NREL / IEA-PVPS report that quotes the clause. Until then, don't state it as fact in
  the deck — say SolaraX *works with or without* on-site sensors, which needs no citation.
- [ ] **"96,000+ rooftop installations"** — CLAUDE.md and PRD v2 §2. Unverified. Try the IEA-PVPS
  National Survey Reports or SEDA.
- [ ] **Competitor per-MW pricing at utility scale** (Sitemark, Raptor Maps, Scopito) — directionally
  supported by their marketing; verify before asserting numbers.
- [ ] **Raptor Maps product names** (Production Analytics, Flight Scheduling, Solar Sentry) — PRD v2
  §1 rests the whole pivot rationale on these. Verify against raptormaps.com before the deck.
- [x] **tCO₂e avoided** — use **0.740 kgCO₂e/kWh** (§4) and show the arithmetic.

**By design, not gaps:**
- Cost per site visit, visit frequency, share of visits finding nothing → **T2**: labelled ranges,
  conclusion must hold at the pessimistic end.
- Repair cost per fault type → **T3**: no public repair invoices exist. Deferred by team decision,
  14 Aug ([`DECISIONS.md`](./DECISIONS.md) §2).

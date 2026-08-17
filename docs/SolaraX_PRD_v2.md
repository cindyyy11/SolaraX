# SolaraX v2 — Product Requirements Document
## Fleet Yield Assurance for Distributed C&I Solar
### MAIC Nexus Challenge 2026 · Track T1 (AI for Clean Energy)

**Team size:** 5 (at the competition cap — members can't be added later)
**Document date:** 11 Aug 2026
**Supersedes:** SolaraX PRD v1 (10 Aug 2026)
**Internal completion target:** 26 Aug 2026
**Submission lock:** ~1 Sep 2026 — *to be confirmed against R&R v2*

---

## 0. One-Sentence Summary

> **SolaraX tells a solar asset owner which sites in their distributed fleet need a maintenance visit this month, and which don't — protecting the margin on long-tenure O&M commitments.**

Useful shorthand when explaining the project quickly: it's a triage layer for solar fleets, not a monitoring dashboard and not a drone product.

---

## 1. How v2 Developed From v1

v1 set out to rank which rows a drone should fly first on a solar farm. The competitive research we ran afterwards surfaced three things worth building around, and v2 is the result. Most of the engineering plan survives intact — Modules 1, 2 and the computer vision work all carry forward. What moved is the customer and the unit of decision.

**Finding 1 — flight sequencing is already a solved product.** Raptor Maps sells inverter Production Analytics, a Flight Scheduling tool with a drone-provider network, and "Raptor Solar Sentry," marketed for scheduled *and event-driven* inspections. That's close enough to v1's thesis that we'd have struggled to differentiate. Better to know this now than in Q&A.

**Finding 2 — the buyer needed rethinking.** v1 pointed the product at drone service providers, who are paid per flight. Asking them to fly less works against their revenue model. The party who actually benefits from fewer, better-targeted visits is the asset owner carrying the maintenance obligation.

**Finding 3 — the savings sit somewhere else.** On a utility-scale farm, the cost is mobilisation: pilot, permits, travel, setup. Flying 20% of a site instead of 100% doesn't move much money. The decision worth optimising is one level up — *whether to send anyone to that site at all this month.*

### Where that leads

Distributed commercial and industrial rooftop is a different market from utility farms, and it's where these three findings point. The pivot is from **"which row do I fly first on this farm"** to **"which sites in my fleet of two hundred deserve a visit this month."**

That change is mostly a reframing of work already scoped, not a restart.

---

## 2. Project Overview

### Situation

Malaysia's rooftop solar segment reached roughly 1.72 GW by mid-2025 — about 40% of national installed capacity — across 96,000+ installations. Solar ATAP removed the national quota entirely from 1 January 2026, so that fleet is set to grow faster still.

These are not utility farms. They're hundreds of small, scattered, individually low-value sites: a 300 kWp factory roof in Shah Alam, an 800 kWp warehouse in Johor.

A significant share of them are financed through **solar-as-a-service models** — lease and PPA structures where the developer installs at no upfront cost to the customer and bundles free operations and maintenance for the full tenure. Malaysian examples are publicly documented: Solarvest's Powervest range advertises free O&M for up to 7, 12 and 25 years depending on product, and comparable structures exist across the region's solar developers.

### Issues Surfaced

- **Bundled free O&M is a fixed-price obligation against an uncertain cost.** It's priced at signing and delivered for up to 25 years. Every unnecessary site visit erodes that margin; every fault that goes unnoticed erodes generation — and under per-kWh lease structures, that lost generation is the asset owner's own revenue.
- **Free O&M scales linearly with fleet size.** Every added MWp adds maintenance labour. For a developer targeting a gigawatt-scale asset base, headcount becomes the growth constraint rather than capital.
- **Visits are scheduled by calendar, not by evidence.** A visit that finds nothing is pure cost. A fault that sits undetected for six months is compounding loss.
- **Global platforms don't serve this segment.** Sitemark, Raptor Maps and Scopito price per-MW for utility scale and assume site-grade instrumentation. A 300 kWp roof can't carry enterprise SaaS plus drone mobilisation. That's structural rather than an oversight, which is why the gap has stayed open — and it's the strongest form of the "why hasn't anyone done this" answer.
- **The standard method doesn't transfer down.** Utility-scale analysis compares actual output against expected output derived from on-site irradiance. Small C&I sites are typically specified to lower monitoring classes; IEC 61724-1 itself points smaller commercial users down the class hierarchy and permits satellite-derived irradiance as a substitute for on-site measurement. Any method that *requires* a pyranometer excludes most of this fleet.

### Solution

SolaraX ingests inverter generation data across a whole fleet, establishes an expected-output baseline that works without on-site sensors, and uses **the fleet itself as the control group** — sites in the same weather region benchmark each other. Divergence from cohort is scored, converted into estimated ringgit at risk, and ranked into a monthly dispatch list.

The output isn't a heatmap. It's a list: *these five sites, this month, this much money.*

---

## 3. Objectives

- **Turn one recurring decision into an evidence-based one** — which sites get a visit, which don't. *(the actual product)*
- **Work without on-site irradiance sensors** — satellite irradiance plus fleet peer benchmarking, so coverage isn't limited to well-instrumented sites. *(the technical wedge)*
- **Get better as the fleet grows** — more sites per weather region means tighter cohorts and fewer false flags. Value compounds with scale. *(the scalability answer, and the moat)*
- **Output ringgit, not risk scores** — every flag carries an estimated RM/month figure so a P&L owner can act without translating anything. *(the commercial answer)*
- **Keep every output explainable** — every number traces to a physics calculation or a named statistical method. *(the technical-credibility answer)*

---

## 4. What The Final Product Looks Like

This is the target to build toward. If a screen isn't described here, treat it as out of scope for the MVP.

### The workflow the product sits inside

```
   DETECT              TRIAGE              VERIFY              CONFIRM             LEARN
   ───────             ──────              ──────              ───────             ─────
   Fleet data     →    Rank by RM     →    Drone flight   →    Technician     →    Findings
   flags a site        at risk             or roof visit       fixes it            retrain model
                                           confirms cause
   (Modules 1-3)       (Module 4)          (Module 5)          (Module 6)          (future)
```

Drone and computer vision live at the **VERIFY** step. See Section 5, Module 5.

### Screen 1 — This Month's Dispatch List *(the landing screen)*

A fleet map on the left, a ranked list on the right.

```
FLEET: 47 sites · 18.2 MWp                          August 2026

  DISPATCH RECOMMENDED (4)
  1. Bukit Raja Warehouse      620 kWp   RM 4,180/mo at risk   ▲ 22 days
     String-level divergence from 6-site Klang cohort
  2. Senai Plant 2             410 kWp   RM 2,050/mo at risk   ▲ 9 days
     Fleet-wide soiling signal — cleaning candidate
  3. Nilai Distribution Ctr    880 kWp   RM 1,900/mo at risk   ▲ 41 days
  4. Ipoh Cold Storage         300 kWp   RM  740/mo at risk    ▲ 5 days

  MONITOR (6)          — deviation detected, below dispatch threshold
  HEALTHY (37)         — within cohort tolerance

  ─────────────────────────────────────────────────
  Visits avoided this month: 43        Est. saving: RM ██,███
```

The bottom line matters as much as the top. **The product's value is as much in the 37 sites you don't visit as the 4 you do.**

### Screen 2 — Site Detail *(why is this flagged)*

For any flagged site:
- Actual vs. expected generation, daily, last 90 days
- **The peer cohort overlaid** — the other sites in the same weather region. This is the visual that sells the whole product: five lines tracking together, one diverging.
- The date divergence began, and cumulative estimated loss since then
- Plain-language cause hypothesis with a confidence level
- Drone imagery evidence for this site, where it exists

### Screen 3 — Work Order *(what do I tell the technician)*

A single exportable card: site, address, what to check, what evidence supports the hypothesis, what to photograph, and a field for what was actually found. That last field is the data flywheel — confirmed findings retrain the model.

### Screen 4 — Fleet Health & ROI *(the Commercial Viability screen)*

Rolling totals: visits recommended, visits avoided, faults confirmed, generation recovered, cumulative RM protected. This is the screen a P&L owner opens. It should exist even if populated with demo data, clearly labelled as such.

---

## 5. Scope of Work — Core Modules

### Module 1 — Fleet Data Ingestion
Pull real inverter generation data (NREL PVDAQ) for **multiple systems**, structured as a fleet rather than a single site. Clean and normalise: timestamp alignment, missing-value handling, unit consistency, per-site capacity normalisation. Pull satellite irradiance and temperature for each site's coordinates (NASA POWER / PVGIS).

*Schema note: everything keyed by `site_id`. Every downstream module operates over a fleet, not a farm.*

### Module 2 — Sensor-Free Expected-Output Baseline
Given satellite irradiance, ambient temperature and system specs, compute expected output per site using `pvlib` (clear-sky model + temperature correction). Deliberately transparent — every flag traces back to a calculation that can be checked by hand.

*Worth documenting explicitly: IEC 61724-1 sanctions satellite-derived irradiance as a substitute for on-site measurement. This isn't a compromise, it's what makes fleet-wide coverage possible.*

### Module 3 — Fleet Peer Benchmarking & Anomaly Detection ⭐
**The differentiated technical work — the piece a technical judge will focus on.**

Cluster sites into cohorts by geographic and weather proximity. For each site, compute a normalised performance index, then measure divergence from its cohort's distribution using a named statistical method (peer-deviation z-score, isolation forest, or equivalent — state which one). A cohort-wide dip is weather. A single-site dip inside a stable cohort is a fault.

*Why it matters: it removes the on-site sensor dependency, it corrects for satellite irradiance error (the whole cohort shares the error, so it cancels), and its accuracy improves as the fleet grows. A single-site tool can't do this.*

### Module 4 — Economic Ranking Engine
Convert each anomaly into: estimated kWh/month lost × applicable tariff = **RM/month at risk**. Rank against an assumed cost-per-visit, and output a dispatch threshold rather than just a sorted list.

*Keep every commercial assumption as a named constant in a single config file rather than buried in code — judges tend to ask where these numbers came from, and a clean config makes that easy to answer.*

### Module 5 — Drone & Visual Verification Layer
**This is where the drone and CV work from v1 lives, and it has a clearer job in v2 than it did before.**

In v1, drone imagery was the primary detector and performance data pointed it at targets. In v2 the roles swap: **fleet data detects, drone verifies.** The dispatch queue answers *where to go*; a drone flight is one way of answering *what's actually wrong* once you're there.

This is arguably a better fit for C&I rooftop than for utility scale. Roof access requires work-at-height permits, harnesses and a safety briefing — a 15-minute drone pass over a 500 kWp roof avoids all of that. The drone is the cheap way to confirm a hypothesis before committing a technician to the roof.

**Build scope:**
- Classify drone thermal/RGB imagery for visible defects — hot spots, cracked glass, debris, soiling — using a model fine-tuned on public PV defect datasets (ELPV, public RGB damage sets)
- Return a defect class + confidence, attached to the flagged site as evidence in Screen 2
- Where imagery is unavailable for a flagged site, the flag stands on electrical evidence alone

**Honest framing for the pitch:** defect classification is a mature, commoditised capability. It's a supporting component that closes the loop, not the innovation claim. Leading with it would invite direct comparison against Sitemark and Scopito on their strongest ground.

### Module 6 — Dispatch Dashboard
The four screens in Section 4. Deployed to a public URL, loading without a login during the judging window.

### Module 7 — API Layer
Exposes the ranked dispatch queue as a simple API so the dashboard consumes it without touching model code. Also frames the integration story: this plugs into an O&M ticketing system.

### Module 8 — Testing, Demo Packaging & Submission
Validate against real data, confirm clean-environment reproducibility, record the demo, package deliverables.

---

## 6. Claim Discipline

A shared standard for every factual claim in the deck, summary, video and dashboard. Sorting claims into these three tiers before they ship is the simplest protection against a difficult Q&A.

**Tier 1 — Public and checkable.** Cite the source: published product pages, IEA-PVPS capacity figures, Energy Commission statistics, IEC standards, competitor marketing. A judge can verify it in seconds. Build the case on this tier.

**Tier 2 — Assumption, labelled and bounded.** Cost per site visit, current visit frequency, share of visits that find nothing. We don't have these figures. State them as assumptions with a range, and show the conclusion holds at the pessimistic end. A labelled assumption reads as rigour; false precision reads as guesswork.

**Tier 3 — Delete or design around.** Anything requiring insider knowledge we don't have. Rather than asserting that specific sites lack pyranometers, state that SolaraX works with or without them — which removes the dependency entirely.

**Carried over from v1:** every dashboard and video claim labelled BUILT (real data, real model), SIMULATED (real method, sample input), or PLANNED (not yet built).

### Positioning note

The pitch addresses **solar asset owners and O&M providers managing distributed C&I fleets** as a market, not any single company. Public financing products are fair to cite as documented examples of the market pattern. Framing it as an industry-wide problem is also the stronger commercial story — it makes the addressable market a category rather than one account.

---

## 7. Non-Functional Requirements

- **Explainability:** no module outputs a score without a traceable calculation. The answer to "why is this site flagged" should be a number and a method name.
- **Sensor independence:** no module hard-requires on-site irradiance data. Satellite is the default path; on-site data is an optional accuracy upgrade.
- **Data provenance:** only real, public datasets. No fabricated data.
- **Reproducibility:** Modules 1→4 run end-to-end from one command on a clean machine.
- **Public accessibility:** deployed dashboard and repo reachable without a login wall throughout the judging window. (The repo may be private outside judging windows — see R&R.)
- **Language:** all materials in English, per competition rules.

---

## 8. Assumptions

- NREL PVDAQ provides the real inverter data; multiple systems in a shared climate zone stand in for a Malaysian fleet. This is US data proving a method — worth stating plainly rather than describing it as a Malaysian model.
- Satellite irradiance from NASA POWER or PVGIS is accurate enough for cohort-relative comparison. Absolute accuracy matters less than expected, since cohort members share the error.
- Image classification runs on public PV defect datasets. No Malaysian drone footage is available for the MVP; label it SIMULATED.
- Commercial constants (visit cost, tariff, visit frequency) are Tier 2 assumptions in a config file, not facts.
- No live partner data and no partner interview. The pitch is built on public sources by design.
- The dashboard is a demo artifact — no auth, multi-tenancy or billing.

---

## 9. Deliverables

**Corrected against the official MAIC FAQ.**

| Item | Status | Notes |
|---|---|---|
| Pitch deck (PDF) | **Mandatory** | Confirm slide limit against R&R v2 |
| Written project summary | **Mandatory** | Confirm word limit against R&R v2 |
| AI usage disclosure | **Mandatory** | |
| Demo video URL | *Optional* | Can be added or updated later from the team dashboard |
| Artifact / repo URL or architecture PDF | *Optional* | **≤5 MB** if PDF |
| LinkedIn profiles | *Optional* | |

"Optional" here affects submission timing, not importance. Preliminary judging asks: *"Is this a real attempt at solving a real problem with a real artifact?"* The artifact is optional to submit and decisive to score. What optionality gives us is a triage order if we run short on 26 Aug — the three mandatory items come first and must be right.

**Supporting technical deliverables:**
- Cleaned multi-site dataset + preprocessing script (M1)
- Baseline model with documented formula (M2)
- Peer-benchmarking detector with a stated accuracy/precision figure from a real test run (M3)
- Economic ranking config with every assumption named and sourced (M4)
- Image classifier with a stated accuracy figure and SIMULATED labelling (M5)
- Deployed public dashboard URL (M6)
- Architecture diagram: ingestion → baseline → cohort detection → economics → API → dashboard (M7)
- README documenting real vs. simulated, and how to run locally (M8)

---

## 10. Rubric Mapping

Official criteria and weights, with an owner for each block of marks.

| Criterion | Weight | Where we earn it | Owner |
|---|---|---|---|
| Technical Feasibility | 25% | Module 3 (peer benchmarking) is the standout. Modules 2 and 5 are solid but conventional — support the case rather than lead with them | A |
| Commercial Viability | 25% | Margin defence on bundled O&M obligations; Screen 4 ROI view; a named buyer role with a real budget | E |
| Industry Relevance | 20% | "Clean Energy Asset Monitoring" is a listed T1 sub-theme; distributed C&I asset management is a live problem across Malaysian solar developers | E |
| Scalability | 15% | O&M headcount currently scales linearly with MWp; peer benchmarking gets *more* accurate as fleet size grows | C |
| ESG / National Impact | 15% | Recovered generation → MWh → tCO2e avoided; rooftop is ~40% of national capacity; NETR alignment | B |

**Note:** both rubric documents in the project folder carry these same five weighted criteria — they don't conflict. Data governance is worth a line under ESG (fleet benchmarking aggregates data across competing customers' sites, so it's worth stating who owns it and how cohorts avoid exposing one customer's production profile to another), though it isn't a scored category on its own.

---

## 11. Team Roles & Module Ownership

| Person | Primary modules | Accountable for |
|---|---|---|
| **A — AI/ML Lead** | M2 (Baseline), **M3 (Peer Benchmarking)** | The differentiated detector, with a stated accuracy figure from a real test |
| **B — Computer Vision Lead** | M5 (Drone & Visual Verification) | A working classifier with a stated accuracy figure and clear SIMULATED labelling. The CV build itself is largely unchanged from v1 — where it sits in the workflow is what moved. Spare capacity is well spent supporting M3's validation work and building the ESG impact numbers, both of which are currently thin |
| **C — Data Engineering Lead** | M1 (Fleet Ingestion), M4 (Economic Ranking) | Clean reproducible multi-site pipeline; the RM-denominated ranked queue |
| **D — Full-Stack Lead** | M6 (Dashboard), M7 (API) | Public deployed clickable demo URL showing all four screens |
| **E — Product/Commercial Lead** | M8, claim discipline, submission | All mandatory items uploaded and verified; every claim tier-sorted and sourced |

---

## 12. Phase Plan

### Phase 1 — Fleet Foundation (11–15 Aug)
- M1: multi-site dataset pulled, cleaned, `site_id` schema agreed and frozen
- M2: baseline runs on satellite irradiance, produces expected-vs-actual per site
- M5: classifier runs on sample images, returns flag + confidence
- **Milestone 1 (15 Aug): real numbers from real data across at least 5 sites.**

### Phase 2 — Detection & Economics (16–20 Aug)
- M3: cohorts defined; divergence detection produces a ranked, explainable list
- M4: deviations converted to RM/month with every assumption named in config
- M7: API returns the dispatch queue
- **Milestone 2 (20 Aug): one API call returns the final ranked dispatch list end-to-end.**

### Phase 3 — Dashboard & Demo (21–24 Aug)
- M6: all four screens built and deployed to a public URL
- M6: the cohort-overlay chart on Screen 2 is the single most persuasive visual in the product — worth extra polish
- M8: demo video script written, first draft recorded
- **Milestone 3 (24 Aug): someone outside the team opens the URL and understands the product in 15 seconds.**

### Phase 4 — Packaging (25–26 Aug)
- Deck assembled with real screenshots; every claim tier-sorted and sourced
- Demo video finalised; project summary and AI disclosure finalised
- Architecture PDF (≤5 MB) / repo README finalised, public access confirmed
- Full team red-team review (Section 13)
- **Milestone 4 (26 Aug): submission complete with 5 days of buffer.**

### Buffer (27–31 Aug)
Reserved for fixing whatever breaks under a practice pitch to someone outside the team. No new features in this window.

---

## 13. Acceptance Criteria / Red-Team Check

Run this together on 25 Aug.

1. Does M2's output match a hand-calculated expected value for at least one sample day at one site?
2. Does M3 produce a stated accuracy/precision number from a real test run, not an estimate?
3. Can we explain the cohort method — why a single-site dip inside a stable cohort means fault, not weather — in two sentences, to a non-technical listener?
4. Is every commercial assumption in M4 traceable to a named constant with a stated source or a labelled range?
5. Does the conclusion still hold at the pessimistic end of every Tier 2 range?
6. Does M5 state an accuracy figure and clearly label simulated input?
7. Does the full pipeline (M1→M4) run from a clean checkout with one command?
8. Is the dashboard URL public and loading without a login?
9. Does the demo video show the actual dashboard, not slides with narration?
10. Has every deck claim been sorted Tier 1 / Tier 2 / Tier 3, with Tier 3 items removed?

---

## 14. Out of Scope (hackathon MVP)

- Live drone flight integration or automated booking
- Multi-tenant accounts, authentication, billing
- Live or proprietary partner data
- Mobile app (web dashboard only)
- Production-grade scalability, load testing, SLAs
- Any claim about a specific company's internal cost structure or contract terms

---

## 15. Known Weaknesses — Worth Naming Before A Judge Does

Naming a limitation and having an answer for it consistently scores better than being caught out by it.

- **Self-consumption curtailment is the hardest technical problem.** C&I rooftops under NEM and Solar ATAP are sized to on-site demand, so generation is often clipped by load rather than by faults. A factory running a short shift or closing for a holiday looks like an anomaly. Peer cohorts help partially (neighbours share the public holiday) but not fully (they don't share the production schedule). Worth tackling in Phase 1 rather than discovering in Phase 2.
- **Cohort logic needs a minimum fleet density.** Below roughly 5 sites in a weather region, the control group is too weak to be meaningful. State the minimum — and note that the constraint eases as the fleet grows, which is the scalability story rather than a flaw.
- **The data is American.** PVDAQ proves the method, not the market. Say so plainly, and describe the pilot that would validate on Malaysian sites.
- **The economics rest on assumptions.** Labelled ranges, with the conclusion holding at the pessimistic end.
- **Ground truth for validation is limited.** PVDAQ doesn't ship fault annotations for most systems, so M3's accuracy figure needs a deliberate validation design — synthetic fault injection into real data is the usual approach. Worth deciding early.
- **Thermal imaging can't reliably detect microcracks.** Electroluminescence is the standard for those. Avoid any claim to the contrary — it's a detail a technical judge is likely to know.
- **Correlated failure is a blind spot.** If every site in a cohort degrades together — regional haze, a bad module batch across the fleet — peer benchmarking sees nothing unusual. The absolute physics baseline (M2) catches fleet-wide drift; the cohort layer catches site-specific faults. The two are complementary, which is why both exist.
- **This is a yield and cost product, not a safety product.** A monthly dispatch cadence can't prevent a fast-developing connector fire. Fire-risk statistics from v1's research don't support v2's value proposition and are better left out.

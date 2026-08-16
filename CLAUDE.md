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
├── CLAUDE.md            ← you are here: rules and direction lock
├── PROGRESS.md          ← status, phase, blockers  (the only file that goes stale by design)
├── README.md            ← public front door — judges' first impression
├── docs/                ← the product and how it's built
├── hinfo/               ← the competition: rules, rubric, submission state
└── data/                ← real datasets pulled into the repo
```

| Read this | When you need |
|---|---|
| [`docs/PRD.md`](./docs/PRD.md) | **What we're building and why.** Authoritative product brief (v2, 11 Aug) |
| [`docs/ARCHITECTURE-PLAN.md`](./docs/ARCHITECTURE-PLAN.md) | **The agreed technical shape** — locked decisions, rejected alternatives, build order |
| [`docs/TECHNICAL.md`](./docs/TECHNICAL.md) | Stack, data strategy, module specs, technical weaknesses |
| [`docs/DATASETS.md`](./docs/DATASETS.md) | Which datasets and why — evidence for the choice |
| [`docs/RESEARCH.md`](./docs/RESEARCH.md) | Every sourced claim with a URL. **Cite from here or omit** |
| [`docs/DECISIONS.md`](./docs/DECISIONS.md) | Who decided what, when, and what's still open |
| [`hinfo/HACKATHON.md`](./hinfo/HACKATHON.md) | Competition rules, rubric, deadlines, live risks |
| [`hinfo/SUBMISSION-CHECKLIST.md`](./hinfo/SUBMISSION-CHECKLIST.md) | Deliverable-by-deliverable status |
| [`hinfo/maicnexus-extract/`](./hinfo/maicnexus-extract/) | Verbatim official rules as captured |
| [`data/`](./data/) | Real data already pulled — e.g. PVGIS-ERA5 at Bukit Raja/Klang |

---

## Direction lock — the project has pivoted twice

**Do not resurrect either earlier direction:**

1. **Drone flight-scheduling** (PRD v1, 10 Aug — deleted) — dropped because Raptor Maps already
   sells it, drone providers are the wrong buyer (paid per flight), and the money is in whether to
   mobilise at all, not in flight efficiency. Full reasoning: [`docs/PRD.md`](./docs/PRD.md) §1.
2. **Fire-risk intelligence / Bomba compliance** (deleted) — **explicitly superseded.** PRD v2:
   *"Fire-risk statistics from v1's research don't support v2's value proposition and are better
   left out… This is a yield and cost product, not a safety product."*

Both superseded directions were removed from the repo on 16 Aug. The reasoning that killed them is
preserved in [`docs/PRD.md`](./docs/PRD.md) §1 and [`docs/DECISIONS.md`](./docs/DECISIONS.md) — that
is the part worth keeping.

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

---

## Working rules

1. **PRD v2 is authoritative.** Don't propose reverting to a superseded direction.
2. **Cite or omit.** Every number traces to [`docs/RESEARCH.md`](./docs/RESEARCH.md) with a URL.
   Never invent a figure. §6 of that file lists what is *not* yet safe to ship.
3. **Every output must be explainable** — a named method and a formula, not a vibe. An LLM may
   explain a score; it must never compute one.
4. **Label everything BUILT / SIMULATED / PLANNED** on any dashboard or demo material. No claim may
   imply more than what actually runs.
5. **Never break the public-artifact rule** — no auth walls, no private repo during judging windows.
6. **Commit honestly and often.** Backdating is an explicit disqualification ground.
7. **English only**, all documentation and submission materials.
8. Before building anything, check it against the anti-goals above and name the rubric row it moves.
   If it moves none and isn't a listed module, deprioritise it.
9. **Chang Zhe's approved stack wins on conflict** — transcribed into
   [`docs/ARCHITECTURE-PLAN.md`](./docs/ARCHITECTURE-PLAN.md) §2.

---

## The modules

Build in this order. Full specs in [`docs/TECHNICAL.md`](./docs/TECHNICAL.md) §3, architecture in
[`docs/ARCHITECTURE-PLAN.md`](./docs/ARCHITECTURE-PLAN.md).

| # | Module | One line |
|---|---|---|
| 1 | Fleet Data Ingestion | Real multi-site inverter data, keyed by `site_id` — a fleet, not a farm |
| 2 | Sensor-Free Baseline | `pvlib` clear-sky + temperature correction from satellite irradiance |
| 3 | **Fleet Peer Benchmarking** ⭐ | **The differentiator.** Robust peer-deviation z-score (median/MAD). Cohort-wide dip = weather; single-site dip = fault |
| 4 | Economic Ranking | kWh lost × RP4 tariff → **RM/month at risk** → ranked dispatch threshold |
| 5 | Drone & Visual Verification | Defect class + confidence as evidence on a flagged site |
| 6–8 | Dashboard · API · Packaging | Four screens (PRD v2 §4), public URL, no login |

**Fleet data detects, drone verifies.** The queue answers *where to go*; a flight answers *what's
wrong* once you're there.

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

*Direction: PRD v2, 11 Aug 2026. Deadline: 31 Aug 2026, 23:59 MYT.*
*This file holds rules and direction only — status belongs in [`PROGRESS.md`](./PROGRESS.md).*

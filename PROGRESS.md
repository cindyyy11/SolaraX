# PROGRESS.md — where SolaraX actually is

> **The only file in this repo that is meant to go stale.** Rules and direction live in
> [`CLAUDE.md`](./CLAUDE.md); this file is status and nothing else. Update it at the end of every
> working session — append to the log, don't rewrite history.

**Last updated: 16 Aug 2026** · **Deadline: 31 Aug 2026, 23:59 MYT** · **15 days left**

---

## Right now

| | |
|---|---|
| **Phase** | Phase 1 (Fleet Foundation) — **overdue**, was due 15 Aug |
| **Code written** | **None.** Modules 1–8 not started |
| **Architecture** | ✅ Agreed — [`docs/ARCHITECTURE-PLAN.md`](./docs/ARCHITECTURE-PLAN.md). Full `ARCHITECTURE.md` not yet written |
| **Repo** | Reorganised 16 Aug. **1 commit**, needs ≥3 over ≥2 calendar days |
| **Public URL** | None. Repo returns 404 to the public |

---

## 🔴 Blockers — in priority order

| # | Blocker | Why it's blocking | Owner |
|---|---|---|---|
| 1 | **PVDAQ S3 access unverified** | Every module downstream assumes `s3://oedi-data-lake/pvdaq/` is publicly readable with the claimed partitions and columns. If it isn't, the data plan changes. **Task 1, before any code** | — |
| 2 | **Repo has 1 commit, everything untracked** | Rules require **≥3 commits over ≥2 calendar days**, never backdated. Backdating is an explicit disqualification ground | — |
| 3 | **Repo is 404 to the public** | A private repo during the early-Sept judging window counts as **non-submission** | Cindy (repo owner) |
| 4 | **`README.md` carries no real content yet** | It is the judges' first impression of the artifact | — |
| 5 | **Deck + summary still describe PRD v1** | Different product from what we're building. See [`hinfo/HACKATHON.md`](./hinfo/HACKATHON.md) §6 Risk 1 | — |

---

## Milestones

| Milestone | Due | Status |
|---|---|---|
| M1: real numbers from real data across ≥5 sites | 15 Aug | 🔴 **Missed** |
| M2: one API call returns the ranked dispatch list end-to-end | 20 Aug | ⬜ Not started |
| M3: someone outside the team opens the URL and gets it in 15 seconds | 24 Aug | ⬜ Not started |
| M4: submission complete with 5 days buffer | 26 Aug | ⬜ Not started |

**Gate — 21 Aug:** if M1→M4 produces real dispatch output, add the HKUST dataset. If not, ship PVDAQ
plus the Malaysian baseline panel. See [`docs/ARCHITECTURE-PLAN.md`](./docs/ARCHITECTURE-PLAN.md) §3.2.

---

## Module status

| # | Module | Status |
|---|---|---|
| 1 | Fleet Data Ingestion | ⬜ Not started |
| 2 | Sensor-Free Baseline | ⬜ Not started |
| 3 | **Fleet Peer Benchmarking** ⭐ | ⬜ Not started — method decided (robust z-score, median/MAD) |
| 4 | Economic Ranking | ⬜ Not started — RP4 base rate found, components need a primary source |
| 5 | Drone & Visual Verification | ⬜ Not started |
| 6 | Dashboard (Vue 3) | ⬜ Not started |
| 7 | API / Supabase | ⬜ Not started |
| 8 | Testing & Packaging | ⬜ Not started |

---

## Log

Newest first. One entry per working session — what changed, what was decided, what broke.

### 16 Aug 2026 — architecture agreed, repo reorganised

- **Architecture designed and agreed.** [`docs/ARCHITECTURE-PLAN.md`](./docs/ARCHITECTURE-PLAN.md)
  written: locked decisions with rationale and rejected alternatives, build order, cut list.
- **Chang Zhe's approved stack found** at pages 21–23 of `hinfo/SolaraXMAICPitch.pdf` — it was never
  Canva-only. Transcribed and reconciled; it overrode two of the proposed choices (Vue 3 over
  Next.js, Supabase over static JSON).
- **Decisions locked:** Supabase only · Vue 3 + Vite · PVDAQ first with HKUST gated on 21 Aug ·
  robust peer-deviation z-score · real PVDAQ site identity + Malaysian baseline panel · RdTools for
  filters and normalisation but not as the pipeline spine.
- **Risk accepted knowingly:** Supabase free projects pause after 7 days of no API requests. With no
  JSON fallback, the nightly GitHub Action is a single point of failure for the judging window.
  Mitigations recorded in `ARCHITECTURE-PLAN.md` §3.5.
- **Verified:** pvlib 0.15.2 and RdTools 3.2.1 both run on Python 3.14 · RP4 base tariff
  45.4 sen/kWh · Supabase pause policy.
- **Repo reorganised** into `docs/` · `hinfo/` · `data/`. `CLAUDE.md` slimmed to rules and direction
  only; status split out into this file. Added a real `README.md` as the public front door.
- **Deleted:** `docs/HACKATHON-REQUIREMENTS.md` (a redirect stub whose content already lived in
  `hinfo/HACKATHON.md`) and the whole `archive/` folder — PRD v1 plus the superseded fire-risk
  evidence base. The reasoning that killed both directions is preserved in `docs/PRD.md` §1 and
  `docs/DECISIONS.md`, which is the part worth keeping; the fire-risk research was a liability in a
  publicly judged repo given it contradicts the current product.
- **Found in the repo:** `data/pvgis-bukit-raja-klang.json` — real PVGIS-ERA5 irradiance at
  3.08°N, 101.44°E. Real Malaysian weather data, already pulled, usable for the Module 2 baseline.

### 14 Aug 2026 — implementation greenlit

Tech stack and system architecture approved. Build phase opened. Buyer question settled: the
developer carrying the bundled O&M obligation. Repair-cost-aware ranking deferred by agreement.
Full history in [`docs/DECISIONS.md`](./docs/DECISIONS.md).

---

## Open questions

Tracked in detail in [`docs/DECISIONS.md`](./docs/DECISIONS.md) §7 and
[`hinfo/HACKATHON.md`](./hinfo/HACKATHON.md) §9. The ones that affect this week:

1. Can the deck and summary be re-uploaded before the lock? Everything about Risk 1 depends on it.
2. Who holds which of the five roles? Never recorded after the 10 Aug poll.
3. What is FastAPI's role — it isn't on the data path in the approved architecture diagram.
4. RP4 component rates from a TNB primary source, or ship as a labelled Tier-2 range.

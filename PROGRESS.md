# PROGRESS.md — where SolaraX actually is

> **The only file in this repo that is meant to go stale.** Rules and direction live in
> [`CLAUDE.md`](./CLAUDE.md); this file is status and nothing else. Update it at the end of every
> working session — append to the log, don't rewrite history.

**Last updated: 19 Aug 2026** · **Deadline: 31 Aug 2026, 23:59 MYT** · **12 days left**

---

## Right now

| | |
|---|---|
| **Phase** | Phase 2 — M1 shipped, M4 economics shipped, M2/M3 not started |
| **Code written** | Pipeline + 4 dashboard screens run on real data. **23 PLACEHOLDER values remain** |
| **Fleet** | **11 sites, 1.32 MWp, 2 cohorts**, 1 Jan – 21 Aug 2019, all carrying real generation |
| **Schema** | 1.5.0, frozen, 19 validator rules · 45 validator tests · 26 injection tests |
| **Public URL** | None yet |

---

## 🔴 Blockers — in priority order

| # | Blocker | Why it's blocking | Owner |
|---|---|---|---|
| 1 | **Repo is 404 to the public** | A private repo during the early-Sept judging window counts as **non-submission** | Cindy (repo owner) |
| 2 | **Deck + summary still describe PRD v1** | Different product from what we're building. See [`hinfo/HACKATHON.md`](./hinfo/HACKATHON.md) §6 Risk 1 | — |
| 3 | **M2 and M3 unbuilt** | Every RM figure is arithmetic on a placeholder loss fraction until the detector exists. This is the 25% Technical Feasibility row | Cindy (A) |

**Cleared:** ~~PVDAQ S3 unverified~~ · ~~1 commit~~ · ~~empty README~~ (16 Aug) · ~~no code~~ (17–19 Aug:
M1, M4, dashboard, harness all shipped).

---

## Milestones

| Milestone | Due | Status |
|---|---|---|
| M1: real numbers from real data across ≥5 sites | 15 Aug | ✅ **Met** (late, 17 Aug) — 11 sites, 2 cohorts |
| M2: one API call returns the ranked dispatch list end-to-end | 20 Aug | 🔴 **Will slip** — needs M2/M3 |
| M3: someone outside the team opens the URL and gets it in 15 seconds | 24 Aug | ⬜ Not started — no public URL |
| M4: submission complete with 5 days buffer | 26 Aug | ⬜ Not started |

~~**Gate — 21 Aug:** HKUST~~ ✅ **Closed 19 Aug — ship PVDAQ.** M2/M3 unbuilt, so the gate condition
failed; HKUST cannot exercise cross-cohort clustering anyway. See [`docs/DECISIONS.md`](./docs/DECISIONS.md).

---

## Module status

| # | Module | Status |
|---|---|---|
| 1 | Fleet Data Ingestion | ✅ **Built** — real PVDAQ, 11 sites, 2 cohorts (Chang Zhe covering; owned by C) |
| 2 | Sensor-Free Baseline | ⬜ Not started — `expected_kwh` is null, `irradiance_source` NONE (A) |
| 3 | **Fleet Peer Benchmarking** ⭐ | ⬜ Not started — flagged sites are a hardcoded list (A) |
| 4 | Economic Ranking | ✅ **Built** — trip-based saving, RP4 tariff sourced to ST. Inputs stay placeholder until M3 (C) |
| 5 | Drone & Visual Verification | ⬜ Not started — `evidence` block not emitted (B) |
| 6 | Dashboard (Vue 3) | ✅ **Built** — four screens, zero console errors (D) |
| 7 | API / Supabase | ⬜ Not started (D) |
| 8 | Testing & Packaging | 🟡 Partial — 71 pipeline tests; no demo video (E) |

**71 pipeline tests.** **Also built (C, supporting):** Malaysian reference cases · reproducible fleet-median script ·
fault-injection harness producing M3's ground truth.

---

## Log

Newest first. One entry per working session — what changed, what was decided, what broke.

### 19 Aug 2026 — tariff sourced, fleet corrected, two decisions closed

- **RP4 tariff corrected.** The AFA half was wrong in kind: ST sets it **monthly** and it has been
  negative in **9 of 14 months** of RP4 (range −8.91 to +3.80 sen/kWh). Our hardcoded +3.59 was
  July 2026's value frozen as structural, overstating the period mean by **12%**. Now RM 0.4373
  (45.40 − 1.67 mean), range RM 0.3649–0.4920 from published rates. Fleet at risk RM 3,808 → 3,399.
  Evidence: [`docs/RESEARCH.md`](./docs/RESEARCH.md) §4.1.
- **GOLDEN-01 dropped.** Its two NREL sites had **no rows in the processed data** while carrying 54%
  of headline capacity and showing as *healthy*. Fleet is now **11 sites, 1.32 MWp, 2 cohorts**.
- **HKUST gate closed early** — ship PVDAQ.
- **Fault-injection harness shipped** — three fault types, seeded ladder, exactly reversible to
  1e-9. This is the ground truth M3's accuracy figure depends on.
- **Fleet docs reconciled** — `CLAUDE.md`, `BUILD_PLAN.md`, `ARCHITECTURE.md`, `DATASETS.md` and
  `ARCHITECTURE-PLAN.md` all described an 8-site Las Vegas fleet that never shipped.

### 18 Aug 2026 — roles resolved, M4 economics corrected

- **Roles confirmed:** Cindy AI/ML (A) · Xin Rou CV (B) · MK Data (C) · Chang Zhe Full-Stack (D) ·
  Zhuo Heng Product (E).
- **Chang Zhe's pipeline + dashboard merged** (PR #1, #3).
- **M4 corrected** (PR #5): saving is per **trip** not per site — RM 16,500 → RM 7,500, because
  co-located sites are one mobilisation and a trip isn't avoided if you're already dispatching
  there. ROI no longer multiplies one month by six. Four overclaiming labels fixed.
- **Malaysian reference cases** (PR #3): four sites via PVGIS-ERA5, parameters enforced not assumed.

### 16 Aug 2026 (later) — PVDAQ verified, demo fleet changed, ARCHITECTURE.md written

**The load-bearing assumption was wrong, and finding out cost hours instead of days.**

- **Only 157 systems have downloadable Parquet, not 1,862.** `DATASETS.md`'s 136/118/99 California
  clusters are metadata rows with no time series behind them. Of the 157, **30 pass QA with coords**.
- **Data is long-format EAV** — `measured_on, utc_measured_on, metric_id, value`. `metric_id` is
  system-specific and only resolvable via a per-system `metrics` table carrying `calc_scale` /
  `calc_offset`. Ingestion needs a join, a pivot and a resample. Channel naming is inconsistent
  (`ac_power`, `ac_power_hW`, `ac_power_1`, `inv1_ac_power`).
- **Resolution is 1-minute**, not 15-minute. ~185 KB and 20,160 rows per system-day.
- **New demo fleet — greater Las Vegas.** 8 QA-pass sites within 37 km, **40.6–277.2 kWp** (genuine
  C&I rooftop, matching the stated buyer), **2,552 days of concurrent overlap**, **1.22 GB** total,
  and **per-inverter channels on systems 1278 / 1368 / 1369** — which makes the "string-level
  divergence" claim in PRD v2 §4 real rather than aspirational. This is a **better** fleet than the
  original plan, not a worse one.
- **Toolchain proven:** pandas 3.0.5 + pyarrow 25.0.1 install clean on Python 3.14.5.
- **Written:** [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — full module specs with working
  code, frozen schema, API contract, validation protocol, 9 decisions with rejected alternatives.
- **Corrected:** `TECHNICAL.md` §2 and `DATASETS.md` §2.1 now carry the verified reality.

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
2. ~~Who holds which of the five roles?~~ ✅ **Resolved 18 Aug** — Cindy AI/ML (A) · MK Data (C) ·
   Chang Zhe Full-Stack (D) · Zhuo Heng Product (E) · Xin Rou Computer Vision (B). See
   [`docs/DECISIONS.md`](./docs/DECISIONS.md) §1.
3. What is FastAPI's role — it isn't on the data path in the approved architecture diagram.
4. RP4 component rates from a TNB primary source, or ship as a labelled Tier-2 range.

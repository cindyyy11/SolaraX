# PROGRESS.md — where SolaraX actually is

> **The only file in this repo that is meant to go stale.** Rules and direction live in
> [`CLAUDE.md`](./CLAUDE.md); this file is status and nothing else. Update it at the end of every
> working session — append to the log, don't rewrite history.

**Last updated: 31 Aug 2026** · **Deadline: 31 Aug 2026, 23:59 MYT** · **today**

---

## Right now

| | |
|---|---|
| **Phase** | Phase 3 — M1, M2, M3, M4 and the dashboard all run on real data |
| **Code written** | Full BATCH pipeline end to end. **0 PLACEHOLDER values remain** — validator confirms |
| **Fleet** | **11 sites, 1.32 MWp, 2 cohorts**, 1 Jan – 21 Aug 2019, all carrying real generation |
| **Schema** | 1.6.0, frozen and UNCHANGED by M2/M3 · pipeline 0.5.0 · 19 validator rules · **108 pipeline tests** |
| **Public URL** | None yet — deploy config committed, needs the Vercel import ([`DEPLOY.md`](./DEPLOY.md)) |

---

## 🔴 Blockers — in priority order

| # | Blocker | Why it's blocking | Owner |
|---|---|---|---|
| 1 | **Repo is 404 to the public** | A private repo during the early-Sept judging window counts as **non-submission**. Unchanged since 16 Aug — now the single largest risk | Cindy (repo owner) |
| 2 | **Deck + summary still describe PRD v1** | Different product from what we're building. See [`hinfo/HACKATHON.md`](./hinfo/HACKATHON.md) §6 Risk 1 | — |
| 3 | **No public dashboard URL** | 🟡 **Config now exists** — `vercel.json` (with SPA rewrites) and `.github/workflows/ci.yml` are committed, and [`DEPLOY.md`](./DEPLOY.md) has the steps. Still needs someone with the Vercel account to import the project | D |
| 4 | ~~**`VisionEvidence` posts to `127.0.0.1:8000`**~~ | ✅ **Fixed 30 Aug.** The panel is gated on a configured vision service; localhost is a DEV-only default and is dead-code-eliminated from production builds. Local M5 work is unaffected | B / D |

**Cleared:** ~~PVDAQ S3 unverified~~ · ~~1 commit~~ · ~~empty README~~ (16 Aug) · ~~no code~~ (17–19 Aug) ·
~~**M2 and M3 unbuilt**~~ (30 Aug — both shipped, see log).

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
| 2 | Sensor-Free Baseline | ✅ **Built** — pvlib on NASA POWER. R² 0.90, MAE 17.6%. `irradiance_source` NASA POWER (A) |
| 3 | **Fleet Peer Benchmarking** ⭐ | ✅ **Built** — robust peer-deviation z-score. Precision 86.7%, recall 65.0% held out (A) |
| 4 | Economic Ranking | ✅ **Built** — trip-based saving, RP4 tariff sourced to ST. **Loss input is now measured, not assumed** (C) |
| 5 | Drone & Visual Verification | 🟡 Model + API + UI exist; `evidence` block still not emitted into `dispatch.json` (B) |
| 6 | Dashboard (Vue 3) | ✅ **Built** — four screens, zero console errors (D) |
| 7 | API / Supabase | ⬜ Not started (D) |
| 8 | Testing & Packaging | 🟡 Partial — 108 pipeline tests, CI on every push; no demo video (E) |

**108 pipeline tests** (was 71; +37 for M2/M3). **Also built (C, supporting):** Malaysian reference
cases · reproducible fleet-median script · fault-injection harness producing M3's ground truth.

---

## Log

Newest first. One entry per working session — what changed, what was decided, what broke.

### 31 Aug 2026 (later) — the last PLACEHOLDER was stale, not real; fixed at the source

`$.roi.data_status` had been hardcoded `"PLACEHOLDER"` in `pipeline/generate_dispatch.py`
since before M2/M3 existed, with a comment saying it stays that way "until M2/M3 supply a
real kwh_lost." M2 and M3 shipped on 30 Aug (see that entry below) and every flagged site's
`economics.data_status` has been `BUILT` since — the comment's own precondition was already
satisfied, but the hardcoded string never moved, so Fleet Health & ROI kept showing a
PLACEHOLDER badge over numbers that were by then real.

- **Fixed at the source, not papered over on screen.** `build_roi()` now derives
  `data_status` as the worst case across the `economics.data_status` of every site
  carrying a monthly loss figure — the same "worst case wins" pattern `build_meta()`
  already used for the fleet-wide status — instead of a frozen string. It will
  correctly regress to `SIMULATED` or `PLACEHOLDER` again if a future site's economics
  ever is, rather than silently staying `BUILT` forever.
- **`faults_confirmed: 0` stays 0 on purpose and does not drag the object back down.**
  There is still no backend behind Screen 3's findings, so nothing can be counted as
  confirmed — that is a structural fact stated in `faults_confirmed_basis`, not a
  fabricated measurement, and not a reason to keep the whole `roi` object mislabeled.
- **Regenerated and validated.** `python pipeline/generate_dispatch.py` then
  `python pipeline/validate_dispatch.py` — **20/20 rules pass, "No PLACEHOLDER values
  remain."** 116 pipeline tests still pass. Diff against the previous artifact is
  exactly two fields: `meta.generated_at` and `roi.data_status`; every number is
  unchanged, because none needed to be — see `pipeline/generate_dispatch.py`'s
  `build_roi()` docstring for the specifics. Published to
  `apps/web/public/dispatch.json` and `dispatch.mock.json`.

### 31 Aug 2026 — closed-loop operations intelligence: evidence timeline closed, Resilience/Reports/Judge Mode built

Continuing [`docs/superpowers/plans/2026-08-30-solarax-closed-loop-operations-intelligence-plan.md`](./docs/superpowers/plans/2026-08-30-solarax-closed-loop-operations-intelligence-plan.md).
Phases 1-3 (evidence/recovery foundation, Recovery Tracker, Intervention Optimizer) were already
built and committed going into this session. This session closed Phase 4 and built Phases 5-6.

- **Phase 4 closed.** The Evidence Timeline was wired into Scenario Lab and Vision Evidence but not
  into Work Order or Recovery. Added `services/workOrderRecords.ts` — the one place WorkOrderView's
  localStorage findings and RecoveryTracker now agree on a schema and a storage key, instead of a
  duplicated string literal. WorkOrderView now records a `work-order` evidence event on generation
  and on a technician-attributed completion (guarded on outcome + visit date + technician, so the
  checklist's autosave-on-tap never fires a false completion). RecoveryTracker now derives
  `completedAt` from that same record, so a logged visit moves recovery from `projected` to
  `pending` — never straight to `verified`, because there is still no post-work telemetry feed.
- **Phase 5 (Resilience) built.** New `/resilience` screen: six categories (generation, equipment,
  weather, grid, telemetry, communications), each traced to a real `dispatch.json` signal or
  reported `not-connected` — never a fabricated score. Weather reads cohort-wide correlated status
  as the same "cohort dip = weather" signal M3 uses. Cyber-physical readiness is a labelled-simulated
  taxonomy (8 examples across 4 categories, each stating what real telemetry it would need); two are
  also runnable, interactively, as new Scenario Lab entries (`telemetry-dropout`,
  `suspicious-control-pattern`, new `security` scenario group). Integration readiness reports what
  actually connects today (weather: NASA POWER, real; drone: gated on `isVisionApiConfigured()`) vs.
  what a production deployment would need (SCADA, grid, ERP, security — all `not-connected`, stated
  plainly).
- **Phase 6 (Reports, Judge Mode) built.** New `/reports` screen builds a per-site evidence package
  (decision, calculations, assumptions, source status, inspection evidence, work order, recovery)
  from state the product already computed — no second calculation of any figure — plus a fleet
  summary, with print/export and a retry path. Judge Mode is a docked (non-modal) overlay reachable
  from the nav rail: eight steps mirroring the design spec's operator workflow, routing through the
  same live screens with a real subject site resolved from the loaded dispatch artifact — never a
  separate demo dataset.
- **Verification:** 53 vitest tests passing (was 34; +19 for the new services), `vue-tsc --build`
  clean, lint clean, production build clean. Manually walked the full loop in a real Chrome tab:
  Dispatch → Judge Mode step-jump to a site's Scenario Lab → Work Order (filled and saved real
  findings) → back to Site Detail, confirmed Recovery Tracker read the saved visit and moved to
  `Recovery pending` with the correct next-eligible date, and the Evidence Timeline picked it up.
  Desktop confirmed visually; mobile viewport could not be confirmed visually this session — the
  browser tool's `resize_window` reported success but never changed the actual viewport in this
  environment (tried twice, fresh tabs both times). Hardened the mobile nav defensively instead
  (`overflow-x:auto` on the now-four-item nav row) rather than ship unverified.
- **Not built this session:** Phase 7's full desktop/mobile QA pass is partial (desktop only, see
  above) and there was no dedicated accessibility or reduced-motion pass beyond what Phase 4 already
  had. `docs/DECISIONS.md` still needs a decisions entry for the Resilience/Reports/Judge Mode scope
  if the team wants one on record.
- **Also noticed, not evidence-timeline related:** `RecoveryTracker.vue` picked up a `card--dark
  card--interactive` shared-class refactor from someone else's concurrent edit mid-session (visible
  style diff, not reverted — see the file).

**The bigger fact this session did not change:** per the blockers table above, the repo is still 404
to the public with no live URL, and the deadline in this file's own header is today.

### 30 Aug 2026 (later) — scalability measured, front door rewritten, deployment configured

- **The Scalability claim is now measured, not asserted.** `pipeline/scalability_study.py` shrinks
  each cohort to every subset of size k and re-runs only the peer comparison. **ROC AUC rises
  monotonically: 0.855 → 0.897 → 0.913** across 3, 4 and 5 peers, over 1,100 site-evaluations on the
  held-out seeds. AUC is the headline because it is threshold-free — the −0.5 operating point was
  calibrated at cohort size 5, so a threshold-dependent metric alone would partly measure that
  mismatch. Ceiling stated in the doc and the JSON: this is a trend across 3–5 peers, not a
  demonstration at fleet scale.
- **A prediction of ours was wrong and the doc says so.** Cohort MAD *rises* with cohort size rather
  than falling. That is the estimator becoming unbiased, not the cohort getting noisier: MAD from 3
  points is biased low, and since it divides the z-score, understating it inflates every score. Small
  cohorts do not merely have less information, they have overconfident statistics.
- **Red-team items 1, 2 and 3 closed** with evidence inline in `hinfo/SUBMISSION-CHECKLIST.md`.
  Item 1 is a hand calculation at S-1277's solstice peak hour agreeing to 9 decimal places.
- **README rewritten.** It still said *"As of 16 Aug 2026, the entire pipeline is PLANNED"* and
  *"Modules 1–8 ⬜ PLANNED"* — the public front door telling a judge we had nothing while the repo
  behind it had a working pipeline. Now carries the measured numbers, the honest limitations, and
  working run instructions. Also fixed the dead `docs/PRD.md` link.
- **Deployment configured.** `vercel.json` with **SPA rewrites** — without them a judge who refreshes
  a site-detail page gets a CDN 404, because the router uses `createWebHistory`. Plus cache headers
  so a regenerated `dispatch.json` is not served stale for the judging window.
  `.github/workflows/ci.yml` runs tests, schema validation, a check that the published artifact
  matches the pipeline output, and the frontend build. [`DEPLOY.md`](./DEPLOY.md) has the steps.
- **`VisionEvidence` mixed-content bug fixed.** It defaulted to `http://127.0.0.1:8000` and rendered
  unconditionally, so on an HTTPS deployment it would have failed for every judge. Localhost is now a
  DEV-only default and is dead-code-eliminated from production builds; the panel hides when no service
  is configured. Local M5 work is unchanged.
- **Corrected our own published figures.** The M2 numbers first written down were from before the
  fleet tilt was set to 10°. Now R² **0.9008**, MAE **17.57 %**, nRMSE **28.25 %**, derate **0.804**,
  fixed in every file that quoted them.
- Removed the stray empty root `package-lock.json`, which belonged to nothing and could confuse
  monorepo build detection.

**Still open, and the first one is worth more than everything above:** the repo is **still 404 to the
public**, which scores as non-submission; there is no live URL yet (config exists, needs the Vercel
import); and the deck and summary still describe PRD v1.

### 30 Aug 2026 — M2 and M3 shipped; 23 placeholders down to 1

Branch `feat/m2-m3-baseline-detector`. Full method: [`docs/M2-M3-METHOD.md`](./docs/M2-M3-METHOD.md).

- **M2 sensor-free baseline built.** NASA POWER hourly irradiance → pvlib (Erbs → Hay-Davies →
  SAPM cell temperature → PVWatts). **R² 0.9008, MAE 17.57 %, nRMSE 28.25 %** over 2,314 analysed
  site-days. One free parameter — the system derate — calibrated **fleet-wide, never per site**,
  because a per-site fit absorbs the fault it is supposed to reveal. Measured 0.804, moves only to
  0.758–0.780 under ten deliberately contaminated runs.
- **M3 peer benchmarking built.** Robust peer-deviation z-score (Iglewicz-Hoaglin modified z-score,
  median/MAD) on a reference-normalised performance ratio. **Precision 86.7 %, recall 65.0 %,
  FPR 6.7 %** on 100 held-out site-runs. Ladder: 88.9 % recall at ≥30 %, ~45 % at 10–20 %, 85.7 % on
  soiling ramps. Cause-shape agreement 88.5 %.
- **Cohorts are now derived, not declared.** Köppen zone then single-linkage great-circle clustering
  reproduces DSUN-01 and VEGAS-01 exactly from coordinates alone. The code checks that and reports a
  disagreement rather than smoothing it over.
- **The threshold is calibrated, not quoted.** Iglewicz-Hoaglin's textbook −3.5 **missed a 35 % step
  drop** on this fleet — a 5-site cohort with 2 faults is 40 % contamination against MAD's 50 %
  breakdown point, so the faults inflate the MAD they are measured against. Operating point now swept
  on calibration seeds and reported on disjoint test seeds.
- **Two real findings in the real data, neither planted.** S-1276 (Agassi Building B) reported
  **exactly 0.00 kWh for all 31 days of January 2019** at full sampling, and separately collapses from
  5.42 to 2.82 kWh/kWp/day across July–August — in Las Vegas, in peak season. The January outage broke
  the first version of the reference normalisation (median → 0.27, inflating every later day 3.7× and
  making the fleet's worst site look like its best). Fixed with a 75th-percentile reference over
  non-zero days.
- **`dispatch.json` is now `BUILT`.** 23 PLACEHOLDER values → **1**, and the one left is `$.roi`,
  which belongs to M4/C. Validator still passes all 19 rules. **Schema unchanged at 1.6.0** — M2 and
  M3 fill fields that were always in the contract, so the frontend needs no migration. Pipeline
  0.5.0.
- **Real-fleet result is 0 dispatch / 2 monitor / 9 healthy, RM 1,712 at risk.** Nothing clears the
  RM 1,500 visit threshold this month. That is the product working as designed, and the `--injected`
  run (labelled SIMULATED) gives the dispatch-flow demo.
- **Fixed a test blocker owned by nobody:** `pipeline/test_cv_model.py` ran module-level code at
  pytest **collection** time against a gitignored image path, so `pytest pipeline/` aborted and ran
  **zero** tests. Renamed to `cv_smoke_check.py` (M5 logic untouched). Suite went 0 → **105 passing**.
- **`pipeline/requirements.txt`** gained pvlib and scipy. It had uncommitted M5 additions in the
  working tree from someone else's session; those were preserved, not overwritten.

**Still open at the time of this entry:** the repo is still 404 to the public, there is no deploy
config of any kind, and `VisionEvidence` posts to `127.0.0.1:8000` from a screen that will be
served over HTTPS. The next entry closes the last two.

### 19 Aug 2026 — tariff sourced, fleet corrected, two decisions closed

- **RP4 tariff corrected.** The AFA half was wrong in kind: ST sets it **monthly** and it has been
  negative in **9 of 14 months** of RP4 (range −8.91 to +3.80 sen/kWh). Our hardcoded +3.59 was
  July 2026's value frozen as structural, overstating the period mean by **12%**. Now RM 0.4373
  (45.40 − 1.67 mean), range RM 0.3649–0.4920 from published rates. Fleet at risk RM 3,808 → 5,183 (the tariff cut it, then the placeholder loss fraction was restated as a stated 25% rather than derived from the threshold — see 19 Aug review fixes).
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

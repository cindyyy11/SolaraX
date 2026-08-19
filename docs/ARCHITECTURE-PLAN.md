# ARCHITECTURE-PLAN.md — agreed shape before the full architecture doc

> **What this file is.** The contested technical decisions, argued with rationale and rejected
> alternatives, plus the build order. It is the input to [`ARCHITECTURE.md`](./ARCHITECTURE.md)
> (⬜ not yet written — the full module-by-module doc with code samples, schemas, the API contract
> and the diagram, which also becomes the submission architecture PDF ≤5 MB).
>
> Product brief: [`./PRD.md`](./PRD.md) · Engineering reference:
> [`TECHNICAL.md`](./TECHNICAL.md) · Dataset evidence: [`DATASETS.md`](./DATASETS.md) ·
> Sourced claims: [`RESEARCH.md`](./RESEARCH.md) · History: [`DECISIONS.md`](./DECISIONS.md)
>
> **Drafted 16 Aug 2026.** Reconciled against Chang Zhe's approved tech-stack and system-architecture
> slides (§2). Where this disagrees with `TECHNICAL.md` or `DATASETS.md`, the disagreement is stated
> explicitly — those files have not yet been updated.

---

## 0. Context

16 days to the 31 Aug 2026 deadline, **zero code written**, 5-person team. The Preliminary round
cuts 300 teams to 30 on the question *"is this a real attempt at solving a real problem with a real
artifact?"* An elegant architecture nobody can finish is worth less than a blunt one that ships.

**Process note.** Three adversarial design subagents were spawned (minimalist / credibility-maximalist
/ curtailment-and-validation specialist) to attack these decisions independently. All three
terminated on an API session limit before reporting. The recommendations below are one person's
analysis plus direct verification — **they have not had an independent adversary.** Treat §3 as
arguable, not settled.

---

## 1. Verified facts

Checked directly, 16 Aug 2026.

| Claim | Result |
|---|---|
| pvlib Python support | 0.15.2, `requires_python >=3.10` — **local 3.14.5 is fine** |
| RdTools Python support | 3.2.1, `>=3.10`, explicitly classifies 3.14 — **fine** |
| RdTools dependency weight | Pulls `xgboost`, `arch`, `bayesian-filters`, `plotly`, `scikit-learn`, `statsmodels`, `matplotlib` — heavy against a "one command on a clean machine" promise |
| RP4 base tariff | **45.4 sen/kWh**, 1 Jul 2025 → 31 Dec 2027 |
| RP4 component split | capacity 4.55 + network 12.85 + energy 28.22 = 45.62 sen/kWh — ⚠️ **secondary source (consultant site), not TNB primary** |
| AFA | 3.59 sen/kWh (Jul 2026) — already sourced, [`RESEARCH.md`](./RESEARCH.md) §4 |
| **Supabase free-tier pausing** | **Free projects pause after 7 days with no API requests.** Judging is "early September", dates unpublished. See §3.5 — this is a live disqualification risk |

### ✅ Resolved 16 Aug — PVDAQ verified, and the data plan did change

The load-bearing assumption was checked directly. Access works; **the fleet does not.**

- Only **157 systems** have downloadable Parquet, not 1,862 — `DATASETS.md`'s 136/118/99 California
  clusters are metadata-only rows with no time series.
- Data is **long-format EAV** (`metric_id` + `value`), requiring a per-system metrics join and a
  pivot — not the wide table the docs imply.
- Resolution is **1-minute**, not the 15-minute `TECHNICAL.md` §2 claims.
- **The demo fleet as shipped is 11 sites in 2 cohorts** — DSUN-01 (5, MD/DE/NJ) and VEGAS-01
  (6, NV), 40.6–277.2 kWp, 1.32 MWp total, 1 Jan – 21 Aug 2019, with per-inverter channels on
  four of them. *Updated 19 Aug 2026 — broader than the 8-site Las Vegas plan written here.*

Full detail and corrections in [`ARCHITECTURE.md`](./ARCHITECTURE.md) §1. **This is a better fleet
than the original plan** — C&I rooftop in one weather region, which is the actual product target.

---

## 2. 🔒 The approved stack — Chang Zhe's slides, reconciled

**Found.** The tech-stack and system-architecture slides approved 14 Aug are **pages 21–23 of
[`../hinfo/SolaraXMAICPitch.pdf`](../hinfo/SolaraXMAICPitch.pdf)** (that file is an internal working document,
not the submitted deck). They are no longer an open item. Per
[`DECISIONS.md`](./DECISIONS.md) §6 they win on conflict, and they do:

| Layer | Approved choice |
|---|---|
| **Frontend** | **Vue 3 · Vite · ECharts · Leaflet** |
| **Backend / API** | FastAPI · Pydantic · ONNX Runtime |
| **Computer Vision** | YOLOv8 · Google Colab (fine-tune) · **Roboflow dataset, 281 labelled thermal frames** → exported `.onnx` |
| **Data & Storage** | **Supabase (Postgres)** · DuckDB · Parquet |
| **Analytics & ML** | Python · NumPy · pandas · **pvlib** · scikit-learn · SciPy |
| **Infra** | Vercel · **GitHub Actions** · pytest · Hugging Face Spaces |

**Approved data flow:** NREL PVDAQ + NASA POWER + **Open-Meteo** → Fleet-Ingestion (pandas) →
Parquet → DuckDB → pvlib Expected Output → Peer Benchmarking → Economic Ranking → **Supabase
Postgres (precomputed results)** → REST read → Vue frontend. Drone image upload → YOLOv8/ONNX →
detection results → Supabase. Model training is a **one-time** offline step, not in the batch path.

### What changed in this plan as a result

| Item | Was | Now |
|---|---|---|
| Frontend | Next.js | **Vue 3 + Vite** — his slides win |
| Data layer | Static JSON, no database | **Supabase Postgres** — his slides win, confirmed by team decision |
| Irradiance sources | NASA POWER + PVGIS | **+ Open-Meteo** — additive, adopted |
| CV dataset | ELPV / public RGB (`TECHNICAL.md` §2) | **Roboflow, 281 labelled thermal frames** — more concrete, adopted |
| DuckDB + Parquet | "query convenience only" | Promoted to a real component — no conflict |

**Minor correction to carry into `ARCHITECTURE.md`:** the architecture slide labels PVDAQ as
"Generation CSV". The decommissioned v3 REST API served CSV; **OEDI S3 serves Parquet**. Same source,
different format — the diagram should say Parquet.

**To clarify with Chang Zhe (non-blocking):** FastAPI is in the stack but is not on the data path in
the architecture diagram — the frontend reads Supabase directly over REST. Its role is presumably the
image-upload / ONNX inference endpoint. Confirm before `ARCHITECTURE.md` is final.

---

## 3. Decisions

### 3.1 Build vs borrow — borrow the parts, not the spine

**Use RdTools for `filtering` and `normalization` primitives only. Do NOT build the pipeline on
`analysis_chains.TrendAnalysis`.**

`TrendAnalysis` is built for *multi-year degradation trending* — its output is a degradation rate in
%/yr with confidence intervals. SolaraX needs *monthly, per-site, cohort-relative* divergence. Wrong
output shape, wrong time horizon. But `rdtools.filtering` (`clearsky_filter`, `csi_filter`,
`clip_filter`) and the normalization helpers do real work we would otherwise write badly — and
`clip_filter` is directly relevant to the curtailment problem in §3.4.

This is also the best available answer to *"what's actually new here?"* — **"we use NREL's own
normalisation and filters; the contribution is the cohort layer on top and the economic ranking."**
Stronger than either "we called a library" or "we reimplemented it".

| Rejected | Why |
|---|---|
| Full RdTools adoption (`TrendAnalysis` as the spine) | Wrong granularity — multi-year degradation, not monthly triage |
| Pure pvlib from scratch | Throws away the credibility asset for no schedule gain |

**Risk:** heavy dependency tree. **Mitigation:** clean-venv `pip install` test on day 1, pinned
versions, and RdTools calls behind a thin wrapper module so a failed install degrades to a local
implementation rather than blocking the pipeline.

### 3.2 🔒 Which fleet — PVDAQ first, HKUST gated on 21 Aug

**⚠️ This disagrees with [`DATASETS.md`](./DATASETS.md) §6.3's *"both is the strongest story and
roughly the same work."***

| | PVDAQ (California) | HKUST (Hong Kong) |
|---|---|---|
| Sites | 1,564 QA-pass, **72 clusters** of ≥5 — LA 136, OC 118, SD 99 | 60 stations, **all one campus** |
| Resolution | 15-min | **5-min**, 37 with panel-level optimiser data |
| Climate | US temperate / arid | **Subtropical Asian, monsoon, humid** — closest open analogue to Malaysia |
| Access | Parquet + flat CSV on S3 | 296 MB, **Brick `.ttl` + SPARQL** metadata |
| Exercises cohort *clustering*? | **Yes** — multiple cohorts | No — one cohort |
| Rubric row it moves | **Technical Feasibility (25%)** | **Industry Relevance (20%)** |

**Honest correction to an earlier draft of this argument:** HKUST *can* demonstrate the core
mechanism — *all 60 drop together = weather* vs *one drops alone = fault*. What it cannot do is
exercise the **clustering** step, or show the method generalises across weather regions.

**Decision: PVDAQ is the spine. HKUST is gated — add it only if M1→M4 produces real dispatch output
by 21 Aug.** Reasons:

1. **The accuracy figure is the thing that must not fail.** It is Module 3's entire claim and it
   lives on Technical Feasibility (25%). PVDAQ alone delivers it with real cross-cohort structure;
   HKUST adds nothing there.
2. **There is already a cheaper answer to "your data is American"** — the Malaysian baseline panel
   (§3.7): real satellite weather at real Malaysian coordinates through the real pvlib model,
   labelled BUILT. Costs nothing extra and is genuinely Malaysian.
3. **Nobody has checked HKUST's actual column names** ([`DATASETS.md`](./DATASETS.md) §6.1) — that is
   unbudgeted risk in a 16-day build.

**The architectural decision that makes this reversible:** define a **source adapter interface** over
one canonical schema, so adding HKUST is a ~100-line adapter rather than a refactor. This is "not
yet", not "never".

### 3.3 The detector — robust peer-deviation z-score

**One argument settles it: Module 4 needs kWh lost to produce RM.** A peer-deviation z-score's
numerator *is* the magnitude — the performance shortfall converts directly to kWh and then to
ringgit. **Isolation forest returns a rank with no physical unit**, so it would need a second model
bolted on just to reach money.

Secondary but real: **median/MAD, not mean/standard deviation.** Cohorts are small (≥5 sites),
distributions are skewed, and two simultaneous faults in one cohort mask each other under mean/std.

```
PI(i,t) = actual_kWh(i,t) / expected_kWh(i,t)              # performance index, per site per day
z(i,t)  = 0.6745 · (PI(i,t) − median_cohort(t)) / MAD_cohort(t)
```

**Named method:** robust peer-deviation z-score (median absolute deviation; Iglewicz–Hoaglin modified
z-score). Hand-checkable, one line, and the deviation carries the kWh.

**Two sentences for a non-technical judge:** *"We compare each site against its neighbours in the
same weather. If they all drop together it's the weather; if one drops alone that's a fault — and the
size of the gap tells us how much money it's losing."*

### 3.4 Self-consumption curtailment — the mitigation stack

Named in PRD v2 §15 as the hardest technical problem. Four layers, cheapest and highest-value first:

| # | Layer | Why |
|---|---|---|
| 1 | **Persistence + recovery test** | Curtailment *recovers* — the shift restarts, the holiday ends. Faults do not. Require N consecutive qualifying days before flagging. **Strongest and cheapest discriminator; makes the monthly cadence a feature.** |
| 2 | **Upper-envelope estimation** | Use a high quantile (p90) of the intraday performance index, not the mean. Load clipping removes generation from the *top* of the curve; soiling and string faults scale the *whole* curve |
| 3 | **Clear-sky-index filtering** | Restrict to stable-irradiance periods (RdTools `csi_filter`) |
| 4 | **Clip-plateau masking** | Explicit detection and masking (RdTools `clip_filter`) |

**The honest limitation, stated before a judge finds it:** PVDAQ sites are unlikely to exhibit much
self-consumption clipping, so this mitigation **cannot be demonstrated on the real data** — it must
be shown against *injected* curtailment alongside the injected faults, labelled **SIMULATED**.

**Answer to "how do you tell a fault from a factory that closed for a week?"** — *"A closed factory
recovers when it reopens and a fault doesn't, so we require the divergence to persist for several
qualifying days before we flag it. We also compare against the clear-sky upper envelope rather than
average output, because load clipping removes the peak while a fault scales the whole curve down."*

### 3.5 🔒 Data layer — Supabase Postgres

**Decision: Supabase only**, per Chang Zhe's slides and team agreement. The pipeline precomputes and
writes results; the Vue frontend reads them over PostgREST. This gives a real API for free and makes
the "plugs into an O&M ticketing system" story true rather than aspirational.

| Rejected | Why |
|---|---|
| Static JSON files, no database | Contradicts an approved decision, and forfeits the real-API story |
| Static JSON as a *fallback* alongside Supabase | Considered and declined — one code path is simpler |

> 🔴 **Residual risk, accepted knowingly.** Supabase free projects **pause after 7 days with no API
> requests**, and a paused project means the dashboard is unreachable during the judging window —
> which the rules count as **non-submission** ([`../hinfo/HACKATHON.md`](../hinfo/HACKATHON.md) §4).
> With no JSON fallback, **the nightly GitHub Action is now a single point of failure.**
>
> **Required mitigations — not optional:**
> 1. The nightly GitHub Actions batch must be running and green **before** the judging window opens.
> 2. Add an explicit lightweight keep-alive request to that workflow, so the pause timer resets even
>    if the data step is skipped or fails.
> 3. Set a calendar check on the Supabase project status for early September.

**Design the tables as a real contract**, so the shape survives if the runtime ever changes:
`fleet`, `sites`, `site_daily` (actual vs expected, 90 days), `cohorts`, `cohort_membership`,
`dispatch` (ranked queue, RM at risk, by month), `detections` (CV results).

### 3.6 Validation — designed to show its own failures

Inject into **real** series. Magnitudes sourced from [`RESEARCH.md`](./RESEARCH.md) §3.

| Fault | Injection form | Sourced magnitude |
|---|---|---|
| Soiling ramp | multiplicative, `P(t) · (1 − r·days)` | r = 0.47%/day → 10.2%/month (Malaysian field study) |
| String dropout | step, `P(t) · (1 − 1/N)` | N = strings from PVDAQ metadata |
| Inverter outage | `P(t) → 0` | total |
| Partial shading | time-of-day-localised multiplicative loss | — |
| **Curtailment (confounder)** | daytime clipping plateau, weekday-structured | the control case — **must NOT be flagged** |

**Severity ladder down to the detection floor**, so the recall curve has a genuine failure region.

**Report:** precision, recall, median days-to-detect, and **false-positive rate on un-injected
sites** — that last number is the commercially important one, because a false dispatch costs real
money.

**Answer to "you found faults you invented":** *show the failure region.* A recall curve that
degrades to zero at low severity is evidence of an honest test; a flat 100% is evidence of a rigged
one. Blind the evaluation — inject via a seeded script, evaluate without the label file in scope.

**Real-world echo, not a validation claim:** the Universiti Malaya study measuring 86.74% vs 56.30%
PR on two arrays at the same site in the same weather ([`RESEARCH.md`](./RESEARCH.md) §2) is a
published Malaysian instance of exactly this divergence. Use it as a slide, never as our accuracy
number.

### 3.7 🔒 Fleet identity on the dashboard

**Real PVDAQ site IDs and locations, labelled BUILT.** Malaysian RP4 tariff applied to the loss,
labelled as the Malaysian projection. Plus a separate panel running the pvlib baseline on **real
satellite weather at real Malaysian coordinates** (Bukit Raja/Klang, Senai, Nilai, Ipoh) — that half
is genuinely Malaysian and genuinely real, and it carries the pilot ask.

**No Malaysian site names over American generation data.** PRD v2 §4's Screen 1 mockup shows
*Bukit Raja Warehouse / Senai Plant 2 / Nilai Distribution Ctr / Ipoh Cold Storage* as if they were
the fleet. Rendering those labels over PVDAQ California output would breach the "no fabricated data"
NFR and the BUILT/SIMULATED discipline. **PRD v2 §4 needs updating to match.**

---

## 4. Build order

| Days | Work |
|---|---|
| **Day 1 (16 Aug)** | **Verify PVDAQ S3 access, partitions, columns.** Clean-venv install test. Create Supabase project. **Commit.** |
| 16–18 Aug | M1 ingestion + source adapter interface + canonical schema (frozen). M2 pvlib baseline. Hand-check M2 against one site-day |
| 19–21 Aug | M3 cohorts + robust z-score + curtailment stack. M4 economic ranking with RP4 config. Fault-injection harness ✅. ~~**21 Aug: HKUST gate decision (§3.2)**~~ ✅ **Closed 19 Aug — ship PVDAQ.** See [`DECISIONS.md`](./DECISIONS.md) |
| 22–24 Aug | Validation run → real precision/recall/days-to-detect. Supabase load + nightly GitHub Action green. Vue dashboard |
| 25–26 Aug | Deck, summary, demo video, `ARCHITECTURE.md` → PDF. Red-team ([PRD v2 §13](./PRD.md)) |
| 27–31 Aug | Buffer. No new features. **Confirm Supabase project is awake and the nightly action is green** |

**Cut order if it slips:** HKUST → Module 5 image classifier → Screen 3 work order → Screen 4 ROI.

**Never cut:** Module 3's stated accuracy figure, the one-command run, or the nightly keep-alive.

---

## 5. Target layout

```
SolaraX/
├── config/
│   ├── tariff_rp4.yaml           # every commercial constant — named, sourced, with a range
│   └── cohorts.yaml
├── src/
│   ├── ingest/                   # adapter interface + pvdaq.py (+ hkust.py if the gate opens)
│   ├── baseline/                 # pvlib clear-sky + temp correction; rdtools wrapper
│   ├── cohort/                   # clustering + robust z-score + curtailment filters
│   ├── economics/                # kWh → RM via RP4
│   ├── validation/               # fault injection + evaluation protocol
│   └── publish/                  # write precomputed results to Supabase
├── api/                          # FastAPI — image upload + ONNX inference
├── web/                          # Vue 3 · Vite · ECharts · Leaflet
├── .github/workflows/nightly.yml # batch refresh + Supabase keep-alive
├── run.py                        # the one command: M1→M4
└── docs/ARCHITECTURE.md          # the deliverable
```

---

## 6. Verification

Maps to [PRD v2 §13](./PRD.md) acceptance criteria.

1. `python run.py` from a clean checkout and clean venv runs M1→M4 and populates Supabase with real
   numbers — the one-command criterion.
2. M2's expected output for one site-day matches a hand calculation.
3. Malaysian baseline PR lands inside the published **56–87%** band
   ([`RESEARCH.md`](./RESEARCH.md) §2) — a free sanity check.
4. Validation harness emits precision / recall / days-to-detect / FP-rate, with a **visible failure
   region** at low severity.
5. Injected curtailment does **not** appear in the dispatch queue.
6. Dashboard URL loads with no login.
7. **The nightly GitHub Action has run green within the last 7 days** — §3.5.

---

## 7. Open items before `ARCHITECTURE.md` is written

| # | Item | Status |
|---|---|---|
| 1 | **PVDAQ S3 access verified** — partitions and column names | 🔴 The one unverified load-bearing assumption (§1) |
| 2 | **RP4 component rates re-sourced from TNB primary**, or shipped as a labelled Tier-2 range with the conclusion holding at the pessimistic end | ⚠️ Open |
| 3 | **FastAPI's role** confirmed with Chang Zhe — not on the data path in his diagram (§2) | ⚠️ Non-blocking |
| 4 | **IEC 61724-1 satellite clause stays parked** ([`RESEARCH.md`](./RESEARCH.md) §6). The architecture must not depend on it — say *"works with or without on-site sensors"*, which needs no citation | 🔒 Settled |
| 5 | **`DATASETS.md` §6.3 and `TECHNICAL.md` §1** updated to reflect §3.2 | ⚠️ Open |
| 6 | **PRD v2 §4 Screen 1 mockup** updated to reflect §3.7 | ⚠️ Open |
| 7 | **Commit today.** Repo has 1 commit and needs ≥3 across ≥2 calendar days. Backdating is an explicit disqualification ground ([`../hinfo/HACKATHON.md`](../hinfo/HACKATHON.md) §6 Risk 2) | 🔴 Open |
| ~~8~~ | ~~Chang Zhe's Canva slides~~ | ✅ **Closed** — found at `SolaraXMAICPitch.pdf` pp. 21–23, reconciled in §2 |

---

*Drafted 16 Aug 2026. Deadline: 31 Aug 2026, 23:59 MYT.*

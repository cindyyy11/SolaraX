# SolaraX — `dispatch.json` Schema

**Version:** 1.6.0
**Status:** FROZEN as of 15 Aug 2026
**Owner:** D (Full-Stack)
**Consumers:** `frontend/src/api.js` (all four screens)
**Producer:** `pipeline/generate_dispatch.py`

---

## 0. Purpose and the one rule

`dispatch.json` is the single artifact that connects the pipeline to the dashboard.
The pipeline writes it. The frontend reads it. Nothing else crosses that line.

> **The one rule:** field names and types in this document do not change without
> D confirming first. If a module needs a value that isn't here, the answer is to
> add a field deliberately and bump the version — not to rename an existing one.

Teammates replacing the internals of `generate_dispatch.py` (M2/M3/M4) must keep
producing this exact shape. `pipeline/validate_dispatch.py` asserts conformance;
run it before handing anything over.

---

## 1. Top-level structure

```json
{
  "meta":          { ... },
  "assumptions":   { ... },
  "fleet_summary": { ... },
  "roi":           { ... },
  "cohorts":       [ ... ],
  "sites":         [ ... ]
}
```

All six keys are **required**. `sites` may be empty; the others may not.

| Key | Type | Feeds |
|---|---|---|
| `meta` | object | Provenance banner, data-status badges |
| `assumptions` | object | Screen 4 assumptions panel |
| `fleet_summary` | object | Screen 1 header + footer |
| `roi` | object | Screen 4 rolling totals |
| `cohorts` | array | Screen 2 peer context, Screen 1 grouping |
| `sites` | array | Screens 1, 2, 3 |

### 1.1 Transport — canonical vs. serving

`dispatch.json` is **canonical**. Supabase is a **serving layer**, loaded *from*
that file — it is a transport optimisation, never a second source of truth. If
the two ever disagree, the file is right and Supabase is stale.

This does not weaken §0's one rule. The contract is still the shape below; only
the delivery path is allowed to vary.

| Path | Role |
|---|---|
| `pipeline/output/dispatch.json` | Canonical artifact. Everything else derives from it. |
| Supabase | Serving layer, loaded from the file. Faster reads, no schema authority. |

**The frontend must degrade to reading the file directly.** If Supabase is
unreachable, misconfigured or empty, `frontend/src/api.js` falls back to fetching
`dispatch.json` and the dashboard still renders. A judging window is not the
moment to discover a hard dependency on a hosted service. `api.js` remains the
only place that knows which path was used.

---

## 2. Enumerations

Define these once; every field below references them.

### 2.1 `data_status`

Per PRD §6. Appears on `meta` and on **every** site object. Screen components
render it as a badge — never omit it.

| Value | Meaning |
|---|---|
| `BUILT` | Real data through a real model. The claim is fully earned. |
| `SIMULATED` | Real method, sample or synthetic input (e.g. injected faults, public defect datasets). |
| `PLACEHOLDER` | D's temporary stand-in for a teammate's unbuilt module. **Must not survive to submission.** |

`PLACEHOLDER` is deliberately distinct from `SIMULATED`. A judge may reasonably
accept SIMULATED; PLACEHOLDER is an internal marker meaning "this is scaffolding."
`validate_dispatch.py` prints a loud warning listing every PLACEHOLDER remaining.

### 2.2 `status` (site triage state)

| Value | Screen 1 group | Rule |
|---|---|---|
| `dispatch` | DISPATCH RECOMMENDED | anomaly detected **and** `rm_at_risk_monthly` ≥ dispatch threshold |
| `monitor` | MONITOR | anomaly detected, below threshold |
| `healthy` | HEALTHY | within cohort tolerance |

### 2.3 `fault_type` (synthetic injection only)

| Value | Shape |
|---|---|
| `step_drop` | Sudden fixed % loss from a date |
| `soiling_ramp` | Gradual linear degradation from a date |
| `string_loss` | Fixed fraction of capacity offline |
| `none` | No fault injected (control site) |

### 2.4 `score_type`

`z_score` · `isolation_forest` · `cohort_mean_deviation` · `other`

M3's owner (A) states which. Screen 2 prints the raw name — do not prettify it in
the pipeline; the frontend handles display formatting.

---

## 3. `meta`

```json
"meta": {
  "schema_version": "1.1.0",
  "generated_at": "2026-08-15T09:14:02Z",
  "pipeline_version": "0.3.0",
  "reporting_month": "2026-08",
  "reporting_month_label": "August 2026",
  "data_status": "SIMULATED",
  "data_source": "NREL PVDAQ",
  "irradiance_source": "NASA POWER",
  "source_note": "US systems, single climate region. Proves method, not market. See PRD §8.",
  "date_remapped": true,
  "date_remap_note": "Historical PVDAQ dates shifted to a 2026 demo window; underlying values unmodified."
}
```

| Field | Type | Req | Notes |
|---|---|---|---|
| `schema_version` | string | ✅ | Semver. Frontend warns on major mismatch. |
| `generated_at` | ISO 8601 UTC | ✅ | Displayed in the footer. |
| `pipeline_version` | string | ✅ | Free-form; helps debugging across three people. |
| `reporting_month` | `YYYY-MM` | ✅ | Machine-sortable. |
| `reporting_month_label` | string | ✅ | Screen 1 header text. |
| `data_status` | enum §2.1 | ✅ | Fleet-wide worst case. If any site is PLACEHOLDER, this is PLACEHOLDER. |
| `data_source` | string | ✅ | Shown in provenance line. Generation data. |
| `irradiance_source` | string | ✅ | Which satellite irradiance service actually produced the numbers in this run — `NASA POWER`, `Open-Meteo`, `PVGIS`, or `NONE` if M2 has not landed. The architecture diagram shows more than one option, so naming the one used is the difference between provenance and a shrug. PRD §7 requires every number trace to a source. |
| `source_note` | string | ✅ | The honest caveat. PRD §15 wants this said plainly. |
| `date_remapped` | boolean | ✅ | See §9 — read this before deciding. |
| `date_remap_note` | string | ➖ | Required when `date_remapped` is `true`. |

---

## 4. `assumptions`

Echoed verbatim from `config/assumptions.json` so the JSON is self-describing and
Screen 4 needs no second fetch. **The pipeline copies this block; it never
recomputes or overrides it.**

```json
"assumptions": {
  "tariff_rm_per_kwh": 0.40,
  "assumed_yield_kwh_per_kwp_day": 3.8,
  "cost_per_visit_rm": 850,
  "dispatch_threshold_rm_per_month": 700,
  "min_cohort_size": 5,
  "baseline_visit_frequency_per_year": 12,
  "malaysia_reference_yield_kwh_per_kwp_day": 3.656,
  "malaysia_reference_yield_kwh_per_kwp_day_range": { "low": 3.523, "high": 3.901 },
  "same_trip_radius_km": 2.0,
  "projection_horizon_months": 12,
  "tier": "Tier 2 — labelled assumption, see PRD §6",
  "notes": {
    "tariff_rm_per_kwh": "Derived from PRD §4 Screen 1 worked figures.",
    "cost_per_visit_rm": "Assumption. Pessimistic-end sensitivity shown on Screen 4.",
    "min_cohort_size": "Below this, cohort logic is not meaningful. PRD §15."
  }
}
```

All numeric fields required — **validator rule 1 now enforces this** for `tariff_rm_per_kwh`, `cost_per_visit_rm`, `dispatch_threshold_rm_per_month`, `min_cohort_size`, `same_trip_radius_km` and `projection_horizon_months`. Before that check existed the validator printed PASSED on an artifact `generate_dispatch.py` then crashed on. `notes` optional but strongly encouraged — it is
literally the answer to "where did that number come from," which PRD §13 item 4
says will be asked.

### Screen 4 rendering rules

Two conventions the frontend depends on, so a new constant renders correctly:

- **Any scalar** in this block becomes a row in Screen 4's assumptions table,
  paired with its `notes` entry. A constant with no note renders a blank source
  cell, which is the thing PRD §13 item 4 warns about — always add the note.
- **A `<key>_range` object** is attached to that key's row and displayed beside
  the value. It does **not** automatically join the pessimistic-case toggle:
  that reads `tariff_rm_per_kwh_range` and `cost_per_visit_rm_range` by name.
  Adding a range for anything else is display-only, by design — the toggle
  models commercial downside, not model uncertainty.

### `malaysia_reference_yield_kwh_per_kwp_day` — 1.4.0

A **derived reference estimate**, not a measurement and not Tier 1: mean modelled
specific yield across four real Malaysian coordinates, PVGIS-ERA5 reanalysis
through PVGIS's physical PV model. It depends entirely on chosen tilt, mounting,
losses, technology, coordinates and averaging period.

**It is not interchangeable with `assumed_yield_kwh_per_kwp_day`.** That one is a
general sanity-check floor applied to the *US* fleet; this one is a Malaysian
modelled reference. They currently sit close together by coincidence. Merging
them would silently change what the sanity check means.

Method and provenance: [`MALAYSIA-REFERENCE.md`](./MALAYSIA-REFERENCE.md).
Regenerate with `pipeline/fetch_malaysia_reference.py`, which fails if
`assumptions.json` has drifted from the artifact.

---

## 5. `fleet_summary`

Drives Screen 1's header and its footer line.

```json
"fleet_summary": {
  "site_count": 10,
  "total_capacity_mwp": 5.42,
  "dispatch_count": 3,
  "monitor_count": 2,
  "healthy_count": 5,
  "visits_avoided": 7,
  "trips_avoided": 4,
  "trips_recommended": 2,
  "trip_groups": [
    { "trip_id": "T-01", "label": "Las Vegas, NV",
      "site_ids": ["S-0034", "S-0035"], "site_count": 2, "dispatched": true }
  ],
  "estimated_saving_rm": 6000,
  "total_rm_at_risk": 8170,
  "cohort_count": 2
}
```

| Field | Type | Req | Derivation |
|---|---|---|---|
| `site_count` | int | ✅ | `len(sites)` |
| `total_capacity_mwp` | float | ✅ | Σ `capacity_kwp` ÷ 1000, 2 dp |
| `dispatch_count` / `monitor_count` / `healthy_count` | int | ✅ | Must sum to `site_count` — validator asserts this |
| `visits_avoided` | int | ✅ | `site_count − dispatch_count`. Counts **sites** |
| `trips_avoided` | int | ✅ | Trip groups containing **no** dispatched site |
| `trips_recommended` | int | ✅ | Trip groups containing at least one |
| `trip_groups` | array | ✅ | See below. Must partition `sites` exactly |
| `estimated_saving_rm` | float | ✅ | **`trips_avoided × cost_per_visit_rm`** |
| `total_rm_at_risk` | float | ✅ | Σ `rm_at_risk_monthly` across dispatch + monitor |
| `cohort_count` | int | ✅ | `len(cohorts)` |

### `trip_groups` — 1.5.0

| Field | Type | Meaning |
|---|---|---|
| `trip_id` | string | `T-01`, stable within a run |
| `label` | string | Address of the first member, for display |
| `site_ids` | string[] | Members. Every site appears in exactly one group |
| `site_count` | int | `len(site_ids)` — validator asserts agreement |
| `dispatched` | bool | True when any member is being dispatched |

**Why the money is per trip, not per site.** Sites within
`assumptions.same_trip_radius_km` are reached in one mobilisation, so they cost
one visit between them. Five Agassi buildings share byte-identical coordinates;
counting a saved visit each overstated the fleet saving by more than half.

**A group holding a dispatched site is not avoided.** The technician is already
going to that address, so skipping its neighbours saves the drive, not the visit.
Validator rule 18 enforces this — inverting it inflates the headline number.

> `visits_avoided` and `estimated_saving_rm` carry the product's core claim
> (PRD §4: *"the value is as much in the 37 sites you don't visit"*). Give them
> visual weight on Screen 1 — they are not a footnote. Say **sites** when
> counting sites and **trips** when counting money; they are different numbers.

---

## 6. `roi`

Screen 4. Figures for the **observed** period.

```json
"roi": {
  "data_status": "PLACEHOLDER",
  "period_months": 1,
  "visits_recommended_total": 2,
  "visits_avoided_total": 4,
  "faults_confirmed": 0,
  "faults_confirmed_basis": "No confirmation mechanism exists — Screen 3 findings live in browser localStorage",
  "generation_recovered_kwh": 7772.8,
  "generation_basis": "Generation AT RISK this month, not recovered. Nothing has been visited or repaired.",
  "rm_protected_cumulative": 3807.89,
  "co2e_avoided_tonnes": 5.75,
  "co2e_grid_factor_kg_per_kwh": 0.74,
  "co2e_factor_source": "Malaysia grid emission factor, Energy Commission 2024",
  "projection": {
    "horizon_months": 12,
    "factor": 12.0,
    "saving_rm": 72000,
    "basis": "Straight-line projection of a single observed month. Assumes this month is representative."
  }
}
```

`period_months` **must be 1** while `meta` carries a single `reporting_month`
with no start/end window — nothing above 1 is corroborated by the rest of the
payload, and internal consistency alone does not settle it: scale every `_total`
by six and the arithmetic still agrees. Relax this only when the schema grows an
explicit reporting window, and check against that window instead.

All fields required except `projection`, the two `*_basis` fields and the two
`co2e_*` provenance fields — the last are required if `co2e_avoided_tonnes` is
present. ESG is 15% of the rubric (PRD §10); a stated factor with a source is the
difference between a scored point and a hand-wave.

### No hidden multiplication — 1.5.0

`period_months` is what the pipeline **observed**, not a window it would like to
claim. Every `_total` must equal its per-period value × `period_months`, and
validator rule 19 asserts it.

This rule exists because a previous version multiplied one month by six and
presented the result as rolling history, with `faults_confirmed = dispatch_count
× 2` invented outright. A projection is legitimate; a projection hidden inside a
field named `_total` is not. Anything beyond the observed period goes in
`projection`, where its horizon, factor and assumption are visible.

### Fields that mean less than their names suggest

Two names are fixed by this contract and cannot be renamed without a major bump,
so they carry a `_basis` sibling saying what they actually hold:

| Field | Reality | Basis field |
|---|---|---|
| `generation_recovered_kwh` | Generation **at risk** — nothing has been recovered | `generation_basis` |
| `faults_confirmed` | 0 until findings are persisted. Screen 3 writes to browser `localStorage` with no backend, so nothing can be counted as confirmed | `faults_confirmed_basis` |

A non-zero `faults_confirmed` without a basis is a rule 19 failure. **The UI must
render the basis, or use wording consistent with it** — a `_basis` field the
frontend ignores changes nothing a judge sees.

---

## 7. `cohorts`

```json
"cohorts": [
  {
    "cohort_id": "REGION-01",
    "label": "Klang Valley cluster",
    "member_site_ids": ["S-001", "S-002", "S-004", "S-007", "S-009", "S-011"],
    "member_count": 6,
    "meets_minimum": true,
    "clustering_method": "Koppen climate zone, then single-linkage agglomerative clustering on great-circle distance within the zone",
    "centroid": { "lat": 3.0733, "lon": 101.4489 },
    "cohort_median_performance_index": 3.61,
    "data_status": "BUILT"
  }
]
```

| Field | Type | Req | Notes |
|---|---|---|---|
| `cohort_id` | string | ✅ | Referenced by `site.cohort_id` — validator asserts every reference resolves |
| `label` | string | ✅ | Human-readable, used in hypothesis text |
| `member_site_ids` | string[] | ✅ | Must all exist in `sites` |
| `member_count` | int | ✅ | `len(member_site_ids)` |
| `meets_minimum` | boolean | ✅ | `member_count >= assumptions.min_cohort_size`. Frontend shows a caution badge when `false` — this is PRD §15's known weakness made visible rather than hidden |
| `clustering_method` | string | ✅ | Named method. PLACEHOLDER-prefixed until A delivers |
| `centroid` | object | ➖ | Map convenience |
| `cohort_median_performance_index` | float | ➖ | Screen 2 reference line |
| `data_status` | enum §2.1 | ✅ | |

---

## 8. `sites[]`

The main array. One object per site. Ordered by `rank` ascending, healthy sites last.

### 8.1 Identity block — always present

```json
{
  "site_id": "S-004",
  "name": "Bukit Raja Warehouse",
  "address": "Jalan Kebun Nenas, Bukit Raja, 41050 Klang, Selangor",
  "capacity_kwp": 620,
  "lat": 3.0733,
  "lon": 101.4489,
  "cohort_id": "REGION-01",
  "tariff_rm_per_kwh": 0.40,
  "source_system_id": "pvdaq_1276",
  "status": "dispatch",
  "rank": 1,
  "data_status": "SIMULATED"
}
```

| Field | Type | Req | Notes |
|---|---|---|---|
| `site_id` | string | ✅ | **Primary key across every module.** Stable, never reused. PRD §5 M1 freezes this. |
| `name` | string | ✅ | Display name |
| `address` | string | ✅ | Screen 3 work order needs it |
| `capacity_kwp` | float | ✅ | Denominator for every normalisation |
| `lat` / `lon` | float | ✅ | Map markers, cohort clustering, satellite irradiance lookup |
| `cohort_id` | string \| null | ✅ | `null` only if the site couldn't be assigned; frontend renders it ungrouped |
| `tariff_rm_per_kwh` | float | ✅ | Per-site, defaults to the fleet assumption. Allows future tariff variation without a schema change |
| `source_system_id` | string | ✅ | Traceability back to the PVDAQ system. Non-negotiable for the provenance story |

> The example value `pvdaq_1276` is not a made-up placeholder — system 1276 exists
> in the live bucket at
> `s3://oedi-data-lake/pvdaq/parquet/pvdata/system_id=1276/`.
> Keep it as the example. A worked example that resolves to real data is worth
> more than a tidy fake one, and it means anyone reading this doc can verify the
> provenance chain themselves in one listing call.
| `status` | enum §2.2 | ✅ | |
| `rank` | int \| null | ✅ | 1-based within dispatch group. `null` for healthy sites |
| `data_status` | enum §2.1 | ✅ | |

### 8.2 `detection` — required for `dispatch` and `monitor`, `null` for `healthy`

```json
"detection": {
  "method": "Robust peer-deviation z-score: Iglewicz-Hoaglin modified z-score (median / MAD) across same-day cohort peers, on a performance ratio normalised to each site's own reference period",
  "score": -1.72,
  "score_type": "z_score",
  "threshold": -0.5,
  "confidence": 0.9,
  "cohort_size": 6,
  "cohort_meets_minimum": true,
  "data_status": "BUILT"
}
```

| Field | Type | Req | Notes |
|---|---|---|---|
| `method` | string | ✅ | The named method. PRD §7: every flag answers "why" with a number **and** a method name |
| `score` | float | ✅ | Signed. Negative = underperforming |
| `score_type` | enum §2.4 | ✅ | |
| `threshold` | float | ✅ | What `score` was compared against. Without it the score is unreadable |
| `confidence` | float 0–1 | ✅ | Frontend formats as %. **As implemented this is _persistence_** — the fraction of the evaluation window on which the site sat below its cohort. Chosen because it is the one number here a reader can restate in words and check against the chart above it: `0.90` means "below its peers on 27 of the last 30 days". See [`M2-M3-METHOD.md`](./M2-M3-METHOD.md) |
| `cohort_size` | int | ✅ | |
| `cohort_meets_minimum` | boolean | ✅ | Mirrors the cohort flag for convenience |
| `data_status` | enum §2.1 | ✅ | |

### 8.3 `divergence` — required when `detection` is present

```json
"divergence": {
  "start_date": "2026-07-24",
  "days_since": 22,
  "detection_confidence": "high"
}
```

`start_date` (ISO date) and `days_since` (int) required. Screen 2 draws its
vertical reference line at `start_date` — if this is missing the chart loses its
most important annotation.

### 8.4 `economics` — required when `detection` is present

```json
"economics": {
  "kwh_lost_monthly": 10450,
  "rm_at_risk_monthly": 4180,
  "cumulative_kwh_lost": 7675,
  "cumulative_loss_rm": 3070,
  "loss_pct_of_expected": 0.148,
  "exceeds_dispatch_threshold": true,
  "calculation": "kwh_lost_monthly × tariff_rm_per_kwh",
  "data_status": "PLACEHOLDER"
}
```

| Field | Type | Req | Notes |
|---|---|---|---|
| `kwh_lost_monthly` | float | ✅ | Estimated monthly shortfall vs expected |
| `rm_at_risk_monthly` | float | ✅ | The Screen 1 headline number |
| `cumulative_kwh_lost` | float | ✅ | Since `divergence.start_date` |
| `cumulative_loss_rm` | float | ✅ | Screen 2 shaded-region annotation |
| `loss_pct_of_expected` | float 0–1 | ✅ | Sanity check — anything > 0.5 deserves scrutiny |
| `exceeds_dispatch_threshold` | boolean | ✅ | Must agree with `status`; validator asserts it |
| `calculation` | string | ✅ | Plain-text formula. PRD §7 explainability |
| `data_status` | enum §2.1 | ✅ | |

> Every number here derives from `assumptions`. No constant is ever hardcoded in
> `generate_dispatch.py`.

### 8.5 `hypothesis` — required when `detection` is present

Feeds Screen 2's explanation panel and Screen 3's work order.

```json
"hypothesis": {
  "summary": "String-level divergence from 6-site Klang cohort",
  "detail": "Site tracks its cohort until 24 Jul, then sits 15% below cohort median while peers hold steady. Pattern is consistent with a single string offline rather than soiling or weather.",
  "confidence": 0.81,
  "checks": [
    "Inspect combiner box for tripped string breakers",
    "Verify string-level currents against inverter readings",
    "Check for new shading obstruction on the east array"
  ],
  "photograph": [
    "Combiner box interior with breaker states visible",
    "Full array from roof edge, east elevation",
    "Inverter display showing per-string current"
  ]
}
```

`summary` (string, ≤ 90 chars — it renders on one Screen 1 line), `detail`,
`confidence` and `checks` (≥1 item) required. `photograph` required for
`dispatch` status only.

### 8.6 `series` — see §8.7 for who gets it

```json
"series": {
  "actual_vs_expected": [
    { "date": "2026-06-01", "actual_kwh": 2280.4, "expected_kwh": 2356.0, "performance_index": 3.68 }
  ],
  "cohort": [
    { "date": "2026-06-01", "site_id": "S-004", "performance_index": 3.68, "is_subject": true },
    { "date": "2026-06-01", "site_id": "S-002", "performance_index": 3.71, "is_subject": false }
  ]
}
```

**`actual_vs_expected`** — one row per site per day, 90 days.
`expected_kwh` comes from M2 and is populated as of 30 Aug 2026. It stays `null`
on any day the baseline could not produce a value for; the frontend renders the
actual line alone across that gap rather than breaking, and a gap is the truthful
rendering of a day we could not predict.

**`cohort`** — long format, one row per *peer* per day. This is the array behind
the chart PRD §4 calls *"the visual that sells the whole product."*

| Field | Type | Req | Notes |
|---|---|---|---|
| `date` | ISO date | ✅ | |
| `site_id` | string | ✅ | Peer identity — needed so lines are distinguishable |
| `performance_index` | float | ✅ | **kWh per kWp.** Never raw kWh — a 300 kWp and an 880 kWp site must share one axis |
| `is_subject` | boolean | ✅ | Exactly one site_id per site object has `true` |

> **Long format, not wide.** One `df.to_dict('records')` from pandas, and the
> frontend reshapes once inside `api.js`. Wide format breaks the moment cohort
> membership changes.

### 8.7 Who carries `series` — the denormalisation decision

| Status | `series.actual_vs_expected` | `series.cohort` |
|---|---|---|
| `dispatch` | ✅ required | ✅ required |
| `monitor` | ✅ required | ✅ required |
| `healthy` | ➖ optional | ❌ omit |

Peer data is duplicated across flagged sites. That is deliberate: at MVP scale
(≤ 15 sites, ≤ 4 flagged) the file stays small, and the frontend needs no join
logic. If the file passes ~5 MB, split site detail into `output/sites/{site_id}.json`
and keep the summary in `dispatch.json` — `api.js` absorbs that change alone.

### 8.8 `evidence` — optional, M5 (owner B)

```json
"evidence": {
  "has_imagery": true,
  "defect_class": "hotspot",
  "confidence": 0.74,
  "image_url": "/evidence/S-004_thermal_01.png",
  "captured_date": "2026-08-02",
  "model_note": "Fine-tuned on ELPV public dataset",
  "inference_mode": "batch",
  "data_status": "SIMULATED"
}
```

Omit entirely, or set `has_imagery: false`, when no imagery exists.
Per PRD §5 M5: *"where imagery is unavailable, the flag stands on electrical
evidence alone."* Screen 2 must render correctly with this key absent.

**`inference_mode`** — required whenever `evidence` is present.

| Value | Meaning |
|---|---|
| `batch` | Classified during a pipeline run. The value was baked into `dispatch.json` when it was generated. |
| `live` | Classified at request time via the upload path — a user supplied an image after generation, and this block was written back rather than produced by the batch run. |

This matters because it breaks an assumption that held everywhere else in this
document: **`live` evidence means the file is no longer the sole writer of its own
contents.** Everything else in `dispatch.json` is written once by
`generate_dispatch.py`; a `live` evidence block can appear or change without a
pipeline run.

Consequences worth stating rather than discovering:

- `meta.generated_at` no longer bounds the freshness of a `live` block. Screen 2
  should read `captured_date` for imagery recency, not `generated_at`.
- A `live` write must not alter any other field. Detection, economics and
  hypothesis stay as the pipeline produced them — imagery is corroborating
  evidence, never a trigger for re-ranking. The dispatch list does not reorder
  because someone uploaded a photo.
- Per §1.1, the canonical file is still the source of truth. If the live path
  writes to Supabase only, that evidence is lost on the next pipeline run — so
  the live path must write back to `dispatch.json`, or the block must be
  regenerable from wherever the upload was stored.

### 8.9 `ground_truth` — SIMULATED runs only

Written by `fault_injection.py`. Present only on sites carrying an injected fault.
**Never displayed in the UI.** It exists so A can score M3 against known answers
(PRD §13 item 2, §15).

```json
"ground_truth": {
  "fault_injected": true,
  "fault_type": "string_loss",
  "injected_from": "2026-07-24",
  "magnitude_pct": 0.15,
  "affected_capacity_kwp": 93,
  "note": "SYNTHETIC — injected into real PVDAQ data. Not a real fault."
}
```

`affected_capacity_kwp` is **deliberately omitted** by
`pipeline/fault_injection.py`. PVDAQ publishes no per-inverter DC capacity, only
an inverter AC rating — a different quantity — so a kWp figure derived from it
would be invented, inside the one artifact whose entire purpose is being
trustworthy.

### `ground_truth.json` — the standalone label file, 1.5.0

Mirrored to `pipeline/output/ground_truth.json` so A can load labels without
parsing the whole dispatch payload. **Gitignored** — synthetic data does not sit
in a judged repo beside real measurements; a seed regenerates it.

```json
{
  "data_status": "SIMULATED",
  "generated_at": "2026-08-19T...Z",
  "seed": 42,
  "reversal_epsilon": 1e-09,
  "note": "…never use as an input to detection…",
  "source": { "fleet_daily": "data/processed/fleet_daily.parquet", "…": "…" },
  "event_count": 4,
  "events": [
    {
      "site_id": "S-1276", "unit_id": null, "fault_type": "step_drop",
      "injected_from": "2019-05-12", "injected_until": null,
      "magnitude_pct": 0.35, "unit_count": 1, "severity_scale": 1.0,
      "kwh_removed": 10347.441, "days_affected": 102,
      "note": "SYNTHETIC — injected into real PVDAQ data. Not a real fault."
    }
  ]
}
```

Reproduce this exact record with `python pipeline/fault_injection.py --ladder
--seed 42`. The previous example was hand-edited and no invocation produced it.

**Start dates are staggered**, drawn from the seed across the middle third of the
window. They are not a fixed offset — every fault sharing one date is a tell a
detector can learn without detecting anything.

**`severity_scale`** is on every event — its rung on the ladder, 1.0 at the top.
`soiling_ramp` events additionally carry **`base_rate_per_day`** (the sourced
Malaysian figure), and their `rate_per_day` is **exactly** `base_rate_per_day ×
severity_scale` — the scale is rounded and the rate is the unrounded product of
the two recorded values, so `base * scale == rate` evaluates True. `magnitude_pct` is `null` for a ramp: the loss depends on how long it
has run.

**`unit_count` is present on every event at a site with inverters**, not only
`string_loss`. A unit-level fault of magnitude *m* costs the site roughly *m/N*,
so a consumer cannot convert the label to a site-level severity without N. Such
faults are placed at the ladder's **low** rungs, where being a fraction of the
site is the intent rather than a mislabelling.

**Dates here are SOURCE dates (2019).** `generate_dispatch.py` applies the §9
remap when it emits the per-site block, so the remap stays in exactly one place.

Each event carries everything needed to recompute its factor per day, which is
what makes `--verify` able to reconstruct the original series from the injected
series plus this file alone. `kwh_removed` and `days_affected` are reporting
fields; reversal never reads them.

**`string_loss` is applied at site level**, factor `1 − 1/unit_count`, matching
`ARCHITECTURE.md` §5's `P(t)·(1 − 1/N)`. It is the site's share lost when one of
N units drops out — not a derating of one unit, which would cost roughly 1/N².

**There is no total-outage fault.** A unit at exactly 0 is the most realistic
dropout of all and is deliberately absent: multiplying by zero destroys the
information, so the run would no longer be reversible. Add it only alongside
per-row originals in this file.

---

## 9. Date handling — decide this before Step 5

PVDAQ data is historical US data; its real timestamps will not be August 2026.
Two options:

**A — Remap dates** to a 2026 demo window. Screens read naturally and the pitch
flows. Set `meta.date_remapped: true` and state it in the README. Values are
unmodified — only the date axis is shifted.

**B — Show true historical dates.** Maximally honest, but a judge sees 2019 dates
on a screen headed "August 2026" and asks about it mid-demo.

**Recommendation: A, disclosed.** A labelled shift with unmodified values is a
Tier 2 move (PRD §6) and reads as rigour. An undisclosed shift is not — which is
exactly why `meta.date_remapped` is a required field rather than an optional one.

Whichever you pick, apply it once in `clean_normalise.py`. Never let two modules
shift dates independently.

---

## 10. Validation rules

`pipeline/validate_dispatch.py` asserts all of the following and exits non-zero on
any failure:

1. All six top-level keys present
2. `schema_version` matches the frontend's expected major version
3. Every `site_id` unique and non-empty
4. `dispatch_count + monitor_count + healthy_count == site_count`
5. Every `site.cohort_id` resolves to a `cohorts[].cohort_id`, or is `null`
6. Every `cohorts[].member_site_ids` entry exists in `sites`
7. Every `dispatch` and `monitor` site has non-null `detection`, `divergence`,
   `economics`, `hypothesis`
8. Every `dispatch` and `monitor` site has a non-empty `series.cohort`
9. Exactly one distinct `site_id` per site's `series.cohort` has `is_subject: true`
10. `performance_index` present and numeric on every `series.cohort` row
11. `economics.exceeds_dispatch_threshold` agrees with `status == "dispatch"`
12. `rank` values within dispatch group are contiguous from 1
13. Every object carrying a `data_status` has a valid enum value
14. `confidence` values within 0–1 inclusive
15. **Warn loudly** listing every `PLACEHOLDER` remaining, with a count

Rules 8 and 9 exist because Screen 2 fails silently without them. Rule 15 is what
stops scaffolding shipping to a judge.

---

## 11. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 15 Aug 2026 | Initial frozen schema (D) |
| 1.1.0 | 15 Aug 2026 | Added §1.1 transport note (canonical file vs. Supabase serving layer, with required frontend fallback). Added `meta.irradiance_source` and `evidence.inference_mode`. Confirmed the `pvdaq_1276` example resolves to a real bucket path. Additive only — no field renamed or removed (D) |
| 1.2.0 | 17 Aug 2026 | Added `sites[].sub_site` — per-inverter comparison against sibling median, with optional per-unit `thermal`. Deviates from BUILD_PLAN §8's draft by using `mean_kwh_daily` + `deviation_pct` instead of `performance_index`: PVDAQ publishes no per-inverter capacity, so a kWh/kWp figure at that level would be fabricated. Additive only (D) |
| 1.3.0 | 17 Aug 2026 | Added `sites[].excluded_from_analysis` and cohort `analysed_site_ids` / `analysed_count` / `excluded_site_ids`. A site whose telemetry falls below `assumptions.min_plausible_performance_index` is forced `healthy`, never ranked, and never drawn as a peer. `meets_minimum` is now judged on `analysed_count`, not raw membership. Additive only (D) |
| 1.4.0 | 18 Aug 2026 | Added `assumptions.malaysia_reference_yield_kwh_per_kwp_day` and its `_range`. Additive only — no field renamed, no type changed, no existing consumer affected. Screen 4's generic assumptions renderer picks both up without a frontend change; `Assumptions` in `apps/web/src/types/dispatch.ts` declares them as optional. **Raised by C, needs D's confirmation** per the frozen-contract rule (C) |
| 1.5.0 | 18 Aug 2026 | Added `fleet_summary.trips_avoided` / `trips_recommended` / `trip_groups`, `roi.projection`, `roi.generation_basis`, `roi.faults_confirmed_basis`, `assumptions.same_trip_radius_km` and `assumptions.projection_horizon_months`. **`estimated_saving_rm` changes basis from sites to trips** — the value moves, the type does not. New validator rules 18 and 19; rule 1 now covers the `assumptions` block. `roi.period_months` is pinned to 1 until the schema carries a reporting window. Also documents `ground_truth.json`'s top-level shape and adds `assumptions.soiling_rate_per_day` / `soiling_max_loss_fraction` for `pipeline/fault_injection.py`. Additive only; no field renamed or removed (C) |
| 1.6.0 | 19 Aug 2026 | `ground_truth.json` events gain `severity_scale` (every event) and `base_rate_per_day` (soiling); `unit_count` now on every event with inverters, not only `string_loss`; start dates staggered. `dispatch.json` unchanged — this bumps because the label file is a documented contract owner A loads against, and 1.4.0 set the precedent of a row for a purely additive field. Additive only (C) |

| — | 30 Aug 2026 | **No version change.** M2 and M3 shipped and now populate `expected_kwh`, `detection`, `divergence`, `hypothesis`, `cohorts[].clustering_method` and `cohorts[].cohort_median_performance_index` — every one of which was already in this contract. **No field was added, renamed, retyped or removed, so the frontend needed no migration.** What changed here is prose and examples that had gone stale: the illustrative `detection` and `cohorts` blocks now show real shipped values instead of PLACEHOLDER strings, and `confidence` is documented as the persistence figure it is implemented as. `meta.pipeline_version` moved 0.4.0-placeholder → 0.5.0, which is the correct place to record that the *producer* changed while the *contract* did not (A) |

Bump minor for additive optional fields. Bump major for anything that breaks an
existing consumer — and tell D and the frontend before you do.

**A row with no version is legitimate and this table now has one.** When the
values change but the contract does not, say so here rather than bumping — a
version number that moves without a consumer-visible change trains everyone to
ignore it.
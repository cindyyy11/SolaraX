# HANDOFF.md — plugging your module into SolaraX

For **A** (M2 baseline, M3 detector), **B** (M5 vision) and **C** (M4 economics).

Read [`CLAUDE.md`](./CLAUDE.md) first for the rules, then this for how to attach
your work without breaking anyone else's.

---

## The one thing that matters

**Everything integrates through one file: `pipeline/output/dispatch.json`.**

The pipeline writes it. The dashboard reads it. Nothing else crosses that line —
no shared imports, no function calls between halves, no database in the middle.

That means you can rewrite as much of the pipeline as you like, as long as the
file that comes out still has the shape in [`docs/Schema.md`](./docs/Schema.md).

> **You do not integrate by calling the API.** The API and the dashboard are
> *downstream* of your work — they read what you produce. If you find yourself
> wanting to call a frontend endpoint from a model, something has gone sideways.

---

## Run it first

```bash
pip install -r pipeline/requirements.txt

python pipeline/fetch_irradiance.py      # NASA POWER cache — M2 needs it, ~30 s, run once
python pipeline/generate_dispatch.py     # writes dispatch.json, publishes to the frontend
python pipeline/validate_dispatch.py     # 19 rules; exits non-zero on failure
python -m pytest pipeline/               # 105 tests across the whole pipeline
```

`generate_dispatch.py` runs without the irradiance cache, but it then falls back to the PLACEHOLDER
detector and stamps `meta.data_status` PLACEHOLDER. If you see that, you skipped step one.

Frontend:

```bash
cd apps/web
npm install
npm run dev          # http://localhost:5173
```

`generate_dispatch.py` copies the artifact into `apps/web/public/` automatically,
so the dashboard updates when you regenerate. You do not need to copy anything
by hand.

Optional — re-pull raw PVDAQ (~40 MB, a few minutes; only needed if the fleet
changes):

```bash
python pipeline/fetch_pvdaq.py --dry-run
python pipeline/fetch_pvdaq.py
```

---

## What to replace, and what must survive

Open `pipeline/generate_dispatch.py`. Replace whatever you need **above** this
line:

```python
# ===========================================================================
# STABLE INTERFACE — teammates, preserve this function and this filename.
# ===========================================================================
```

Two things must not change:

1. **`write_dispatch_file()`** and the output path `pipeline/output/dispatch.json`
2. **The shape of what it writes** — `docs/Schema.md`, currently **1.6.0**

Everything above that comment is scaffolding. Delete it freely.

**Always run `validate_dispatch.py` before you push.** It catches the failure
modes that otherwise show up as a blank chart during a demo rather than an error.

---

## What is PLACEHOLDER right now

**One value.** `validate_dispatch.py` lists them every run with a count.

| Where | What is fake | Owner |
|---|---|---|
| `roi.data_status` | The ROI block is labelled PLACEHOLDER. Its inputs are now measured, but `faults_confirmed` still has no confirmation mechanism — Screen 3 stores technician findings in browser localStorage with no backend | **C (M4)** |
| `sites[].evidence` | Not emitted at all. The UI slot exists and renders an honest empty state | **B (M5)** |

`sites[].evidence` is absent rather than PLACEHOLDER, which is correct: the schema makes it optional
and Screen 2 renders properly without it. It is listed here because it is still outstanding work, not
because it is a fake value.

**Cleared on 30 Aug** — all of these are now measured, so don't rebuild them:

| Where | Now |
|---|---|
| `sites[].detection` | Robust peer-deviation z-score. `confidence` is persistence — "below its peers on 27 of the last 30 days" |
| `sites[].economics` | `kwh_lost_monthly` is a measured peer-relative shortfall. M4's tariff and threshold arithmetic is untouched |
| `sites[].hypothesis` | Cause follows the Theil-Sen slope of the post-divergence deviation: step vs progressive, with different checks |
| `cohorts[].clustering_method` | Köppen zone then single-linkage great-circle clustering, verified to reproduce the configured fleet |
| `cohorts[].cohort_median_performance_index` | Measured per cohort (DSUN-01 4.61, VEGAS-01 5.10), was one flat constant for both |
| `series.actual_vs_expected[].expected_kwh` | M2's baseline. Populated on every row that has a measurement |
| Which sites are flagged | The detector decides. `PLACEHOLDER_DISPATCH_SITE_IDS` survives only as the no-irradiance-cache fallback |

**What is already real (`BUILT`)**, so don't rebuild it:

- All daily generation series — real PVDAQ, 11 sites, 1 Jan – 21 Aug 2019
- `sites[].sub_site` — per-inverter comparison against sibling median
- `sub_site.units[].thermal` — real operating temperatures
- `sites[].excluded_from_analysis` — the data-quality gate
- Every cohort membership, capacity, coordinate

---

## Traps in the raw PVDAQ data

Each of these produced a confident, plausible, **wrong** number before it was
caught. If you touch `fetch_pvdaq.py`, know about them.

1. **`calc_scale` is already applied.** It documents a conversion done upstream.
   Applying it gave 100x and 1000x errors. Use the `units` column only.
2. **Channel names lie about units.** `ac_power_hW` and `ac_power_metered_kW`
   both hold plain watts.
3. **A channel can be defined and hold zero rows.** Five sites declare `ac_power`
   and ship no data for it; their totals come from summing inverters.
4. **Three different per-inverter naming conventions** in one fleet:
   `inv1_ac_power_hW`, `inv1_ac_power`, `ac_power_1`. Plus `inv4_dc_temp`.
5. **`-40.0` is a dead-sensor sentinel**, identical in C and F. Left in, it
   reported ambient of -30 °C in Delaware in June.
6. **Inverters at one site may be different sizes.** System 1278 pairs a 100 kW
   with a 50 kW; comparing raw kWh gives a convincing -44% "fault" that is
   nameplate. Sibling comparison is gated on `sub_site.units_comparable`.
7. **The catalogue lies about coverage.** `first_timestamp` / `last_timestamp`
   do not imply continuous data and do not describe the parquet dataset. Systems
   1430 and 1433 advertise 2024 and have no 2019 partition at all.

Two guards in the quality report exist because of these: nothing above
10 kWh/kWp/day (physically impossible) and nothing averaging below 2.0
(partial capture). Keep them.

---

## For A — M2 and M3

**Both shipped 30 Aug.** Method, formulas, measured accuracy and stated limitations:
[`docs/M2-M3-METHOD.md`](./docs/M2-M3-METHOD.md).

```
pipeline/fetch_irradiance.py   NASA POWER hourly cache, 7 coordinates for 11 sites
pipeline/baseline.py           M2 — pvlib chain + one fleet-wide derate
pipeline/peer_benchmark.py     M3 — cohort clustering, z-score, divergence, shortfall
pipeline/score_detector.py     accuracy against the injected ground truth
config/model_params.json       every model constant, each with a sourcing note
```

They plug in through `generate_dispatch.run_analysis()`, which is the only place either module
touches the artifact. If you are changing the method, change it in those files — `generate_dispatch`
should not grow analysis logic.

Three things worth knowing if you touch them:

- **The derate is fleet-wide on purpose.** Making it per-site is the single most tempting change and
  it silently breaks the product: a per-site derate fits itself to whatever the site is producing, so
  a faulty site gets a lower bar and is declared healthy. There is a test that fails if it moves.
- **The z threshold is calibrated, not a constant.** It depends on cohort size and contamination rate.
  Re-run `score_detector.py --calibrate` if the fleet changes size.
- **`performance_index` is kWh per kWp**, not actual/expected. The detector uses `performance_ratio`
  (actual/expected), which is a separate quantity computed in `baseline.py` and never written to the
  schema. Don't conflate them — `performance_index` is the y-axis of Screen 2's chart.

---

## For B — M5

Emit an `evidence` block per `docs/Schema.md` §8.8. The UI slot is built and
currently renders "no imagery captured for this site", which is the required
behaviour when evidence is absent.

Two constraints:

- **Imagery never flags a site.** It is evidence on a site the electrical signal
  already flagged. Leading with it invites comparison to Sitemark and Scopito on
  their strongest ground — `CLAUDE.md` names that as an anti-goal.
- **A live upload must not alter detection, economics or ranking.** The dispatch
  list does not reorder because someone uploaded a photo. Use
  `inference_mode: "live"` and write only inside the `evidence` block.

Attaching an image to a specific inverter needs a schema bump to move `evidence`
onto `sub_site.units[]` — talk to D first.

---

## For C — M4

Every commercial constant lives in `config/assumptions.json` and is copied
verbatim into `dispatch.json` so Screen 4 can display it with its sourcing note.
**The pipeline copies that block; it never recomputes or overrides it.**

If you add a constant, add its `notes` entry too — Screen 4 renders the note
beside the value, and a number with no stated source is the thing a judge asks
about.

Ranges ending in `_range` drive Screen 4's pessimistic toggle. Keep that pattern.

---

## House rules that will bite you

- **Never commit anything under `data/raw/` or `data/processed/`.** The
  `.gitignore` covers it. Binary blobs are permanent once committed.
- **No magic numbers in code.** Commercial constants go in
  `config/assumptions.json`.
- **Performance values are always normalised** (kWh per kWp). Sites range
  40.56 – 277.16 kWp. (The old 1153.49 upper bound was GOLDEN-01, dropped 19 Aug.)
- **Do not fabricate data.** Where something is unavailable, omit the feature or
  label it. `PLACEHOLDER` means a fake value is present and must not ship;
  `SIMULATED` means real method, sample input.
- **Do not render a panel grid.** PVDAQ publishes no panel or string positions.

---

*Schema 1.6.0 · pipeline 0.5.0 · questions to D.*

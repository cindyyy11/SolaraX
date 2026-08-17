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

python pipeline/generate_dispatch.py     # writes dispatch.json, publishes to the frontend
python pipeline/validate_dispatch.py     # 17 rules; exits non-zero on failure
python pipeline/test_validate_dispatch.py  # 28 tests on the validator itself
```

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
2. **The shape of what it writes** — `docs/Schema.md`, currently **1.3.0**

Everything above that comment is scaffolding. Delete it freely.

**Always run `validate_dispatch.py` before you push.** It catches the failure
modes that otherwise show up as a blank chart during a demo rather than an error.

---

## What is PLACEHOLDER right now

25 values. `validate_dispatch.py` lists them every run with a count.

| Where | What is fake | Owner |
|---|---|---|
| `sites[].detection` | `score`, `threshold`, `confidence`, `method` — the whole block | **A (M3)** |
| `sites[].economics` | `kwh_lost_monthly` derives from a made-up loss fraction, not from a real shortfall | **A (M2)** + **C (M4)** |
| `sites[].hypothesis` | The cause text is a fixed string, not derived from any signal | **A (M3)** |
| `cohorts[].clustering_method` | Cohorts are read from `config/fleet_sites.csv`, not clustered | **A (M3)** |
| `series.actual_vs_expected[].expected_kwh` | **Always `null` — deliberate, not a bug.** It is M2's output | **A (M2)** |
| `sites[].evidence` | Not emitted at all. The UI slot exists and renders an honest empty state | **B (M5)** |
| Which sites are flagged | A hardcoded list of site ids in `PLACEHOLDER_DISPATCH_SITE_IDS` | **A (M3)** |

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

**M2.** Fill `series.actual_vs_expected[].expected_kwh`. It is `null` today and
the frontend already renders the actual line alone without it, so you can land
this incrementally.

**M3.** Replace `build_detection()`, `build_divergence()` and `classify_site()`.
Set `score_type` to whichever of the enum values you actually use — the frontend
prints the raw name.

Two things worth knowing before you start:

- **Cohort geometry varies a lot.** VEGAS-01's five Agassi sites share
  byte-identical coordinates (perfect weather control, irradiance error cancels
  exactly). DSUN-01 spans ~162 km across three states, so it cancels only
  partially. Clustering on raw lat/lon is degenerate on VEGAS-01 — consider the
  `kg_climate` Köppen column in `config/fleet_sites.csv` instead.
- **`performance_index` is kWh per kWp**, not actual/expected. If you want the
  ratio as a detector input, add it as a new field and bump the schema rather
  than redefining the existing one — it is the y-axis of Screen 2's chart.

Ground truth for an accuracy figure needs `fault_injection.py`, which does not
exist yet.

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
  40.56 – 1153.49 kWp.
- **Do not fabricate data.** Where something is unavailable, omit the feature or
  label it. `PLACEHOLDER` means a fake value is present and must not ship;
  `SIMULATED` means real method, sample input.
- **Do not render a panel grid.** PVDAQ publishes no panel or string positions.

---

*Schema 1.3.0 · questions to D.*

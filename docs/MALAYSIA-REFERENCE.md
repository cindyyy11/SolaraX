# Malaysian reference cases — method and provenance

**What it answers:** *"This is a Malaysian competition. Why is all your generation data American?"*

**The honest answer, in one line:** no openly reusable per-site Malaysian inverter time series
exists, so we prove the method on a real US fleet and model the Malaysian half from real Malaysian
satellite weather — and we never mix the two.

Artifact: [`data/malaysia_reference_cases.json`](../data/malaysia_reference_cases.json) ·
Generator: [`pipeline/fetch_malaysia_reference.py`](../pipeline/fetch_malaysia_reference.py)

---

## 1. What exists and what doesn't

Three distinct things get confused in this conversation. They are not interchangeable.

| | Available? | What we do with it |
|---|---|---|
| Malaysian **satellite weather** (irradiance, temperature) | ✅ Free, PVGIS-ERA5 | The reference cases below |
| Malaysian **published performance studies** | ✅ Several | Sanity band — [`RESEARCH.md`](./RESEARCH.md) §2 |
| Malaysian **per-site inverter time series** | ❌ None openly reusable | Nothing. This is the gap |

**Say this:** *"No openly reusable per-site Malaysian inverter-generation time series suitable for
fleet benchmarking."*

**Do not say:** *"No Malaysian data exists."* It is false and easily disproved.
[`RESEARCH.md`](./RESEARCH.md) §2 carries published Malaysian measured performance — including a
**232.5 kWp rooftop at Monash University Malaysia**, 2019, 5-minute resolution, **PR 85.4%**,
301.5 MWh generated. Overstating the gap invites a judge to produce that paper and undo the claim.

---

## 2. The four sites

Named in [`ARCHITECTURE-PLAN.md`](./ARCHITECTURE-PLAN.md) §3.7. Coordinates are the industrial and
commercial areas the names refer to, not town centres — the buyer is a C&I rooftop owner.

| Site | State | Lat | Lon | Modelled specific yield |
|---|---|---|---|---|
| Bukit Raja, Klang | Selangor | 3.0800 | 101.4400 | **3.90** kWh/kWp/day |
| Nilai | Negeri Sembilan | 2.8148 | 101.7990 | **3.67** |
| Ipoh | Perak | 4.5975 | 101.0901 | **3.53** |
| Senai | Johor | 1.6018 | 103.6689 | **3.52** |

**Range 3.52 – 3.90, mean 3.66 kWh/kWp/day.**

---

## 3. Model parameters — every one of these changes the answer

Set deliberately in `fetch_malaysia_reference.py` and copied into the artifact. **No PVGIS default
is accepted silently.**

| Parameter | Value | Why |
|---|---|---|
| Endpoint | `PVcalc` (v5_2) | Returns modelled PV *production*. `seriescalc` returns weather only |
| Radiation database | PVGIS-ERA5, **2005–2020** | A yield figure is meaningless without its averaging period |
| Reference system | 100 kWp | Arbitrary but fixed; everything is normalised to kWh/kWp/day |
| Mounting | **building-integrated** | Roof-mounted modules sit against a warm surface with restricted airflow, run hotter, and yield less. Our buyer owns rooftops |
| Tilt | **10°** | Malaysian rooftop practice — enough for rain to drain and self-clean, low wind load. At 1–5°N horizontal is already near the irradiance optimum, so 10° costs almost nothing |
| Azimuth | **0° (south)** | Malaysia sits just north of the equator |
| Technology | c-Si | Dominant C&I rooftop technology |
| System loss | 14% | PVGIS default — see the caveat below |

### The parameter sensitivity that matters

An earlier pass used PVGIS's defaults — **free-standing, 0° tilt** — and produced **3.67–4.09, mean
3.82**. The corrected roof-mounted 10° run gives **3.52–3.90, mean 3.66**.

**Roof-mounting alone costs about 4%.** Any Malaysian yield figure quoted without its mounting,
tilt and loss assumptions is not a number, it is a vibe.

### Known optimism in the 14% loss figure

[`RESEARCH.md`](./RESEARCH.md) §3 records that Malaysian soiling is **acidic and wet**, with measured
output reductions up to **58.67%** in extreme cases, and that hot-climate degradation runs
**−0.88%/yr** against −0.5%/yr temperate. PVGIS's 14% default is built on temperate assumptions, so
it is **optimistic for Malaysia**.

Left at the default on purpose, and flagged here, so these figures stay comparable to other
published PVGIS numbers rather than being quietly tuned by us. If a Malaysia-specific loss figure is
ever adopted, change it here and in `assumptions.json` together, and say so.

---

## 4. How this relates to the real fleet — and what it does not prove

Recompute the observed side yourself:

```bash
python pipeline/fleet_median.py
```

Real NREL PVDAQ measurements, 11 sites, 2,547 site-days, 1 Jan – 21 Aug 2019:

- **Fleet median 3.83 kWh/kWp/day** (10 sites; S-1367 excluded at 1.11, below the 2.0 plausibility floor)
- Per-site spread **3.52 – 4.76**

The modelled Malaysian range (**3.52 – 3.90**) falls **entirely inside** that observed spread.

**What that supports:** using the PVDAQ fleet to demonstrate the method. The sites we validate on
operate in the same specific-yield band a Malaysian C&I rooftop would.

**What it does not support:** any claim that the fleets are equivalent. One side is *measured* output
from specific hardware, under specific operations, in specific years. The other is *modelled*
reference output. Different quantities. The overlap is a **plausibility check**, not a proof of
transferability.

### Wording to use with judges

> The Malaysian reference cases overlap the observed specific-yield range of our real PVDAQ fleet.
> This supports using PVDAQ to demonstrate the method; it does not claim the fleets are
> operationally identical.

### Wording to avoid

> ~~"The US fleet is a quantitatively valid analogue for Malaysian conditions."~~ Overclaims.
> The comparison is measured-vs-modelled across different hardware, operations, years and windows.

---

## 5. Guardrails

- **These are not measurements.** No Malaysian site produced them. Never present them as such.
- **Never use them as detection ground truth.** A detector evaluated against a model it was derived
  from proves nothing. Ground truth comes from injecting known faults into real series
  (`fault_injection.py`, M3 validation).
- **Never label a PVDAQ site with a Malaysian name.** Explicit anti-goal in
  [`CLAUDE.md`](../CLAUDE.md): *"Malaysian site names over American generation data — Fabrication."*
- **`assumed_yield_kwh_per_kwp_day` (3.8) and `malaysia_reference_yield_kwh_per_kwp_day` (3.656) are
  different constants for different jobs.** The first is a general sanity check on the US fleet; the
  second is a Malaysian modelled reference. They are close by coincidence. **Do not merge them.**

---

## 6. Reproducing

```bash
python pipeline/fetch_malaysia_reference.py --dry-run   # print, write nothing
python pipeline/fetch_malaysia_reference.py             # rewrite the artifact
python pipeline/fleet_median.py                         # observed side, from parquet
```

No API key. PVGIS is a free public service of the European Commission's Joint Research Centre.

*Generated 18 Aug 2026 · owner C (Data) · issue [#2](https://github.com/cindyyy11/SolaraX/issues/2)*

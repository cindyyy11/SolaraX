# M2 and M3 — the baseline and the detector

> **Owner: A (Cindy).** Modules 2 and 3 of [`CLAUDE.md`](../CLAUDE.md)'s module table.
> Code: [`pipeline/baseline.py`](../pipeline/baseline.py) ·
> [`pipeline/peer_benchmark.py`](../pipeline/peer_benchmark.py) ·
> [`pipeline/fetch_irradiance.py`](../pipeline/fetch_irradiance.py) ·
> [`pipeline/score_detector.py`](../pipeline/score_detector.py)
> Constants: [`config/model_params.json`](../config/model_params.json)

This file exists because of PRD v2 §7: **every output must be explainable — a named method and a
formula, not a vibe.** Everything below is either a formula you can evaluate by hand or a number
measured by a script in this repo.

---

## The claim, in two sentences

We predict what each site should have produced from satellite weather alone, with nothing installed
on any roof. Then we compare each site to its neighbours on the same day: **a dip everyone shares is
weather, a dip only one site has is a fault.**

---

## Why the second sentence is the one that matters

M2's baseline carries real error — **17.6 % mean absolute error on a single site-day** (measured,
below). That is not good enough on its own to call a 15 % fault, and no amount of model polish fixes
it, because the error comes from NASA POWER resolving cloud timing across a ~50 km grid cell.

But **every site in a cohort is fed from the same satellite cell on the same day**, so that error
lands on all of them at once and *subtracts out* of a peer comparison. The absolute baseline would
need a pyranometer on every roof to resolve a 15 % fault. The peer comparison resolves it without a
single sensor.

This is also why the method **improves as the fleet grows**: more sites per weather region means more
peers in the median, a tighter cohort, and fewer false flags. It is a structural property, not a
roadmap promise.

---

## M2 — the sensor-free baseline

### The chain

| Step | Method | Why it is there |
|---|---|---|
| Irradiance | NASA POWER hourly `ALLSKY_SFC_SW_DWN`, `T2M`, `WS2M` | One source fleet-wide — the error-cancellation argument is false if cohort members use different providers |
| Solar position | `pvlib.solarposition`, evaluated at each hour's **midpoint** | POWER stamps an hourly mean at the hour's start; a low winter sun must not be sampled at its furthest point |
| Beam/diffuse split | `pvlib.irradiance.erbs` | POWER publishes GHI only, and a horizontal number cannot be transposed without knowing how much arrived as beam |
| Transposition | `pvlib.irradiance.get_total_irradiance`, Hay–Davies | Carries the circumsolar term; Perez needs airmass and coefficient lookups for accuracy this application cannot use |
| Cell temperature | `pvlib.temperature.sapm_cell`, `close_mount_glass_glass` | Roof-parallel mounting with restricted rear ventilation. Open-rack parameters would understate cell temperature and make every summer day look like underperformance |
| DC power | `pvlib.pvsystem.pvwatts_dc`, γ = −0.0035 /°C | Silicon loses ~0.35 %/°C above 25 °C. Skip it and every site "fails" in July and "over-performs" in January |
| Daily energy | Sum hourly kW over the site's **local** calendar day | Must match the local-time day `fetch_pvdaq.py` aggregated PVDAQ on, or the comparison is off by a partial day at both ends |

Hourly, not daily, because transposition depends on solar geometry that changes within the day.
Fetching daily GHI and multiplying by a fixed factor would be an invented constant standing in for
physics we can actually compute.

### The one free parameter

Everything above is physics with no room to fit. What remains — soiling, wiring and mismatch losses,
inverter efficiency, availability, nameplate tolerance — collapses into a single **system derate**:

```
expected_kwh = modelled_kwh_raw × derate
derate       = median over ALL analysed site-days of (measured / modelled)
```

**Calibrated once fleet-wide, never per site.** This restriction is the entire point. A per-site
derate is a free parameter that fits itself to whatever the site is actually producing, so a
genuinely faulty site gets a lower derate and is then declared healthy against its own lowered bar.
One fleet median cannot do that — it is robust to a minority of degraded site-days by construction,
and `test_baseline.py` pins exactly that: two of five sites losing 40 % must not move it at all.

**Measured derate: 0.804.** Across ten injected runs — each with four faults multiplied into the
fleet — it moves only to 0.758–0.780. That ~3 % drift under deliberate contamination is the check
that the robustness claim holds, rather than an assertion that it does.

Array tilt is handled the same way: **one fleet-wide 10°**, chosen by sweeping 5–30° against all
2,314 analysed site-days and taking the minimum nRMSE (28.25 % at 10°, 28.33 % at 15°, 29.40 % at
30°). The optimum is shallow, and 10° matches the ballasted low-tilt C&I rooftops these sites are.

### Measured accuracy

Against 2,314 analysed site-days (S-1367 excluded — see below):

| | |
|---|---|
| Mean bias error | −5.47 % |
| Median bias error | −0.00 % |
| **Mean absolute error** | **17.57 %** |
| Normalised RMSE | 28.25 % |
| RMSE | 96.7 kWh/day |
| R² | **0.9008** |

Reproduce with `python pipeline/baseline.py --per-site`.

### What it cannot do — stated, not buried

- **Correlated failure is invisible to it.** If the whole fleet degrades together, the fleet median
  moves with it and the absolute baseline sees nothing. This is the blind spot
  [`README.md`](../README.md) already names, and it is why the peer layer is not the only layer.
- **Tilt and azimuth are assumed, not measured.** PVDAQ publishes neither for any system in this
  fleet. A site whose true orientation differs carries a constant proportional error — which is what
  M3's reference normalisation removes. The upgrade path is per-site orientation fitting
  (`pvanalytics.system.infer_orientation_fit_pvwatts`); **not taken here**, because a per-site fit on
  a window that already contains a fault absorbs the fault into the geometry and reports the site
  healthy. It was tried during the build and the optima pinned to the sweep boundaries, which is a
  fit finding noise rather than tilt.

---

## M3 — fleet peer benchmarking

### Cohort formation

**Köppen climate zone first, great-circle distance second** (single-linkage, 250 km cutoff).

Clustering on raw lat/lon alone is degenerate on this fleet — five VEGAS roofs share byte-identical
coordinates, so a distance-only method sees one point where there are five buildings. Climate zone is
what actually encodes "shares weather"; distance then splits a zone spanning more than one weather
system. Single linkage rather than complete, because DSUN-01 genuinely is a chain of sites across
162 km of the mid-Atlantic, and complete linkage would shatter it into three useless cohorts.

The cohort ids are **earned, not asserted**: the code clusters from coordinates and climate, then
checks the partition it derived against `config/fleet_sites.csv`. It reproduces DSUN-01 and VEGAS-01
exactly, and a disagreement is reported rather than smoothed over.

### The four steps

**1. Performance ratio** — `r = actual_kwh / expected_kwh`, using M2's baseline.

**2. Reference normalisation** — `n = r / reference_level`, where the reference level is the
**75th percentile of the site's non-zero performance ratios over the first 60 days**.

This step removes any *constant* per-site offset — wrong assumed tilt, an unmodelled shading horizon,
a nameplate that is not what the catalogue says. Without it, the detector flags the same innocent
sites every month forever.

> **Why a 75th percentile and not a median — this was found the hard way.**
> S-1276 reported **exactly 0.00 kWh on all 31 days of January 2019** at full sampling: a real
> month-long outage, not a logger gap. Its 60-day reference *median* sat at 0.27, so dividing by it
> inflated every later day by 3.7×. The site with the worst genuine collapse in the fleet came out as
> the **best performer in its cohort**, and a 35 % injected fault on top of it was invisible. An
> upper quantile asks what a site produces *when it is working*, which is the quantity this
> normalisation actually wants — and since faults only push performance down, an upper quantile is
> robust in the correct direction.

The reference period is **clean by construction**: `fault_injection.py` draws every start date from
the middle third of the window, so on 233 days nothing is injected before day 77. A 60-day reference
has 17 days of margin.

**Stated cost:** a fault already running on day 1 is normalised away and this detector will not see
it. A site without at least 20 valid reference days is reported **un-normalisable** and left out of
detection with its reason — saying nothing beats scoring off a reference built from three days.

**3. Daily peer deviation** — for each cohort and each day:

```
deviation = n_site − median(n over analysed cohort members that day)
```

Only analysed sites enter the median. A site excluded for incomplete telemetry would drag the peer
level down and make genuinely healthy neighbours look better than they are — which is precisely how a
real fault gets masked.

**4. Site-level score** — each site reduces to **one number per month** (the median of its daily
deviations over the 30-day evaluation window), and the Iglewicz–Hoaglin modified z-score is computed
**across the cohort's site-level numbers**:

```
score = 0.6745 × (window_deviation − cohort_median) / cohort_MAD
```

MAD is floored at 2 % of expected output. VEGAS-01's five roofs share one coordinate and one weather
feed, and over a month they can agree to a fraction of a percent — at which point an unfloored divide
turns a harmless 0.5 % difference into a large z-score and dispatches a technician. The floor is a
statement about resolution: **below 2 % of expected output, this method does not claim to tell two
sites apart.**

> **Why median/MAD and not mean/standard deviation.** On a cohort of five, one faulty site is 20 % of
> the sample. A mean and a standard deviation are both dragged by the very site being tested — the
> outlier inflates the spread it is measured against and hides itself. Median and MAD have a 50 %
> breakdown point.

### The flag rule — three conditions, three different failures

```
flagged =  score       <= −0.5     the shortfall stands out from the cohort
       AND persistence >= 0.75     it is a condition, not a one-week incident
       AND deviation   <= −0.02    it is big enough to be worth knowing about
```

Any one alone flags the wrong things. **Score alone** fires on a site that lost a week to a grid
outage and has since recovered. **Persistence alone** fires on a site sitting a harmless half a
percent under its peers every day — and on this fleet persistence separates faults from controls so
cleanly that a rule leaning on it would look excellent in the confusion matrix while dispatching
technicians to healthy roofs. **Materiality alone** fires on one cloudy fortnight.

None of this decides whether to *send anyone*. That is money: the pipeline demotes a flagged site to
`monitor` when its loss does not clear the cost of the visit. **The detector says something is wrong;
the threshold says whether it is worth driving to.**

### The threshold is calibrated, not quoted

> **This is the single most important thing to be able to defend about M3.**

Iglewicz and Hoaglin recommend −3.5, and that is correct for their problem: **one** outlier in an
otherwise clean sample. It is wrong here, for a reason specific to small fleets. MAD has a 50 %
breakdown point, and a 5-site cohort carrying 2 faults is at 40 % contamination — close enough that
the faulty sites inflate the very MAD they are measured against, compressing every score toward zero.

At −3.5 this detector **missed a 35 % step drop**. That is not caution; it is a mis-specified test.

So the operating point was measured. `score_detector.py` sweeps the threshold on **calibration
seeds** and reports accuracy on a **disjoint set of test seeds** — picking the threshold and quoting
the accuracy on the same runs would be reporting how well a rule fits the data it was fitted to. F1
peaks at −0.5 and falls away on both sides, so it is an interior optimum rather than the edge of a
range.

**Re-run the calibration when the fleet changes size.** The right value depends on cohort size and
contamination rate, which is exactly why it is not a constant.

### Cause hypothesis

A robust **Theil–Sen slope** on the post-divergence deviation series. A flat line after an abrupt drop
is a component that left service (tripped breaker, blown fuse, one inverter of several offline); a
steady decline is something accumulating on the array (soiling, vegetation, new shading). Those imply
genuinely different first ten minutes on the roof, so the work-order checks differ too.

It is a **hypothesis** and it is worded as one. The detector knows the shape and size of the loss; it
does not know the cause, and a work order stating a cause as fact is how a technician ends up not
looking at the thing that was actually wrong.

### Divergence dating

The start of the **trailing run** where a 7-day rolling median of the deviation stays below the 2 %
resolution floor. Dated on the deviation rather than the z-score, because the z divides by a peer MAD
that moves daily — a fault of constant size would cross back and forth over any fixed z cutoff as the
weather changed the cohort's spread. **A divergence date should be a property of the site, not of
last Tuesday's cloud cover.**

The run must be **live**: a dip that opened and closed in April is history, not a dispatch reason, and
reporting its start date would put a divergence marker on Screen 2 for a site that has since
recovered.

---

## Measured accuracy — the answer key

`fault_injection.py` manufactures ground truth: real PVDAQ measurements with faults of known type,
magnitude and date multiplied in. `score_detector.py` marks the paper. Labelled **SIMULATED** — real
method, synthetic labels.

Reproduce:

```bash
python pipeline/score_detector.py
```

The no-argument run **is** the honest run: it calibrates on seeds 42–45 and reports on the disjoint
50–59, and the artifact it writes is the one quoted here. That is deliberate. An earlier version
defaulted to the calibration seeds with no split, so a bare run silently replaced the held-out
numbers with worse-provenance ones and nothing in the output said so.

Full output: [`pipeline/output/detector_accuracy.json`](../pipeline/output/detector_accuracy.json).

### Held-out results

Threshold chosen on seeds 42–45; every number below comes from the **ten disjoint test seeds 50–59**,
which the threshold never saw.

| | |
|---|---|
| Site-runs scored | 100 (40 with an injected fault, 60 controls) |
| **Precision** | **86.7 %** |
| **Recall** | **65.0 %** |
| F1 | 0.743 |
| False-positive rate | 6.7 % (4 of 60 controls) |
| Cause-shape agreement | 88.5 % of detected faults |
| Median days to detect | 34 |

### The ladder — recall by severity

| Injected severity | Detected | Recall |
|---|---|---|
| ≥ 30 % | 8/9 | **88.9 %** |
| 20–30 % | 1/6 | 16.7 % |
| 10–20 % | 5/11 | 45.5 % |
| Soiling ramp | 12/14 | 85.7 % |

**The curve decaying is the point.** A recall curve that falls off at low severity is evidence of an
honest test; a flat 100 % would be evidence of a rigged one. Recall without precision is free — a
detector that flags everything scores 100 % recall — so the false-positive count on **60 untouched
control sites** carries equal weight, and it is 4.

**The middle two rows are not monotonic, and that is sampling noise rather than a finding.** They rest
on 6 and 11 events; at those counts the confidence intervals overlap almost completely, and no
ordering between them is supported. Do not quote them against each other. The defensible summary is:
**severe faults are caught reliably, progressive soiling is caught reliably, and the floor is
somewhere around 20 %** — which is consistent with the ±7–9 % healthy peer spread a shortfall has to
clear.

Deepening the ladder needs more seeds, not a bigger single run: the injection protocol never touches
more than half a cohort and always leaves controls, which caps one run at four events on an 11-site
fleet.

---

## Does it actually get better as the fleet grows?

The Scalability rubric row (15 %) claims peer benchmarking **improves** with fleet size. That is a
testable statement, so it was tested rather than asserted.

`pipeline/scalability_study.py` takes the same injected runs, shrinks each cohort to every possible
subset of size *k*, and re-runs **only the peer comparison** — M2's baseline is untouched, because
the derate is fleet-wide and does not depend on how many peers a site has. 1,100 site-evaluations
across the ten held-out seeds.

| Peers in cohort | Evaluations | **ROC AUC** | Precision | Recall | FPR | Cohort MAD |
|---|---|---|---|---|---|---|
| 3 | 600 | **0.855** | 84.2 % | 51.2 % | 6.4 % | 0.0766 |
| 4 | 400 | **0.897** | 78.2 % | 65.0 % | 12.1 % | 0.0899 |
| 5 | 100 | **0.913** | 86.7 % | 65.0 % | 6.7 % | 0.1077 |

**AUC rises monotonically: 0.855 → 0.897 → 0.913.**

**Why AUC is the headline and not recall.** The −0.5 operating point was calibrated at cohort size 5.
A threshold-dependent metric alone would partly measure that mismatch at sizes 3 and 4 rather than the
method's information content — which is exactly the objection worth pre-empting. **ROC AUC does not
depend on any threshold**, so the trend cannot be an artifact of where the threshold sits. Precision
and false-positive rate are reported as colour and they are visibly noisier, which is the expected
consequence of a miscalibrated threshold, not a contradiction.

**Read the MAD column carefully — it moves the opposite way to intuition, and that is the
interesting part.** Median cohort MAD *rises* with cohort size (0.077 → 0.108). That is not the
cohort getting noisier. **MAD estimated from 3 points is biased low**, and since it is the z-score's
denominator, understating it *inflates* every score and destabilises the operating point. The rising
number is the estimator becoming unbiased. This was predicted the wrong way round when the study was
designed; the data corrected it, and the correction is a better argument than the original guess —
small cohorts do not just have less information, they have *overconfident* statistics.

**The mechanism** is contamination. One fault in a 3-site cohort is 33 % of the sample against MAD's
50 % breakdown point; in a 5-site cohort it is 20 %. More peers means the robust statistic stays
further from the point where it stops being robust.

> **Ceiling, stated plainly.** The largest analysed cohort in this fleet is 5 sites, so this is a
> measured trend across **3–5 peers** — not a demonstration at fleet scale. The contamination
> mechanism explains why it continues past 5; the data does not reach that far. Anyone quoting this
> should quote the range with it.

Reproduce: `python pipeline/scalability_study.py`. Full output:
[`pipeline/output/scalability.json`](../pipeline/output/scalability.json).

---

## Hand-calculated check

Red-team item 1 asks whether M2's output matches a hand-calculated value for one sample day at one
site — a different question from "do the tests pass". A pipeline can be internally consistent, well
tested, and quietly computing something other than what this document claims.

**S-1277** (Agassi Building C, 40.56 kWp — the smallest site in the fleet), **2019-06-21**, the
summer solstice, at its peak hour 19:00 UTC. Solstice noon in Las Vegas is the most demanding point
on the chain: highest irradiance and highest cell temperature, so the temperature correction is
carrying its largest load and an error in it cannot hide.

| Quantity | Value |
|---|---|
| Plane-of-array irradiance | 1089.94 W/m² |
| Cell temperature | 84.90 °C |
| Capacity | 40.56 kWp |
| γ | −0.0035 /°C |

```
dc_kw = 40.56 × (1089.94 / 1000) × (1 + (−0.0035) × (84.90 − 25))
      = 40.56 × 1.08994 × 0.79036
      = 34.940074 kW
```

**Pipeline output for that hour: 34.940074 kW.** Agreement to 9 decimal places.

Pinned in `test_baseline.py::HandCalculationTests`, which rebuilds the irradiance chain by calling
pvlib directly rather than through `baseline.py` — so the library is shared, but none of our code is.
If `model_site_hourly` stops implementing the documented formula, or a constant drifts out of
`config/model_params.json`, that test fails.

It also asserts the temperature correction is genuinely applied: at 84.9 °C it removes ~21 % of
output, and without it peak POA above 1000 W/m² would push the model **over nameplate**. If γ were
ever zeroed, every other test in the file would still pass while the baseline silently over-predicted
every summer day — turning healthy hot-climate sites into dispatch candidates.

---

## Honest limitations

1. **Detection floor around 20 % on this fleet.** The cohort's healthy sites genuinely spread ±7–9 %
   in peer-relative terms — different roof geometries against one fleet-wide assumption — and a
   shortfall has to clear that spread. A larger fleet, or per-site orientation fitting, tightens it —
   and the scalability study above measures the first half of that claim rather than assuming it.
2. **Faults present from day 1 are invisible.** Reference normalisation removes them by construction.
3. **Correlated fleet-wide degradation is invisible to both layers.**
4. **Small cohorts degrade the statistic.** Five sites with two faults is 40 % contamination against
   MAD's 50 % breakdown point. This is PRD §15's minimum-cohort weakness, quantified.
5. **The ground truth is synthetic.** No open dataset labels site-level PV faults. The defence is the
   ladder and the controls, not the labels.
6. **One month, one fleet, one climate pair.** 233 days across two Köppen zones is not a
   generalisation claim.

---

## Something the method found that nobody was looking for

**S-1276 (Agassi Building B) has a real fault in the real data**, and it is not injected.

Its performance index runs 3.35 → 4.62 → 4.93 → 5.22 → 5.42 kWh/kWp/day from February to June, then
drops to **3.49 in July and 2.82 in August** — in Las Vegas, during the two months of the year when
output should peak. The detector scores it −1.72 with **90 % persistence** and dates the divergence
to early July, estimating **2,828 kWh/month** at risk.

It does not clear the RM 1,500 dispatch threshold, so the pipeline lists it as `monitor` rather than
`dispatch` — which is the product working exactly as designed: a real anomaly, correctly sized,
correctly judged not worth a truck roll on its own this month.

It also had a **month-long total outage in January** that broke the first version of the reference
normalisation. One site, two genuine findings, neither of them planted.

---

*Method owner: A. Data contract: [`docs/Schema.md`](./Schema.md) — unchanged; M2 and M3 fill fields
that were always in it.*

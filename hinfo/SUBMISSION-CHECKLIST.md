# MAIC Nexus — Submission Checklist

**Project: SolaraX · Team CinCaiLah · Track T1 — AI for Clean Energy · Direction: PRD v2 (Fleet Yield Assurance)**

> Deliverable-by-deliverable tracker. Rules and rationale live in
> [`./HACKATHON.md`](./HACKATHON.md); this file is just status.
>
> **Deadline: 31 August 2026, 23:59 MYT — confirmed against the live terms page on 15 Aug 2026.**
> PRD v2's internal "~1 Sep, to be confirmed" note is resolved and should not be repeated.

---

## Key dates

| Date | Event |
|---|---|
| 11 Jun 2026 | Registration opened |
| 8 Aug 2026 | **We registered and submitted** — deck + project summary uploaded |
| 26 Aug 2026 | PRD v2's internal completion target — 5 days of buffer |
| **31 Aug 2026, 23:59 MYT** | **Applications close.** No extensions unless organisers decide otherwise in writing |
| Early Sep 2026 | **Preliminary judging (online).** ⚠️ Repo and demo must be public with no login wall throughout |
| End Sep 2026 | Preliminary results — **300 → 30 teams** |
| Oct 2026 | Semi-Final demo day, KL, in person — 30 → 10 teams |
| Nov 2026 | Grand Final, KL, in person |

**Cap:** 300 teams · **Fee paid:** RM 250 (fair early bird, registered 8 Aug) · **Team:** 5 members, at the cap — cannot add more.

---

## Mandatory at application

| Item | Official spec | Status |
|---|---|---|
| Pitch deck | PDF, **max 12 slides** | 🔴 **submitted at 21 pages — 9 over.** Also PRD v1 framing (drone-first, utility farms, fire slide). Needs a **rebuild to ≤ 12 slides on v2 positioning** |
| Written project summary | Plain text, **max 500 words** | 🔴 **~500 words, no margin.** Also fire-risk-led — framing PRD v2 drops. Text reproduced in [`DECISIONS.md`](../docs/DECISIONS.md) §3 |
| AI usage disclosure | 3 parts: tools-used multi-select, free-text tools & models, declaration checkbox | ⚠️ **"Tools & models" was showing a required-field error mid-submission** — verify it saved |
| Track selected and locked | One of T1–T6 | ✅ T1 Clean Energy. Cannot be changed |
| Malaysian citizen (MyKad) named | Full legal name + IC no. per member, plus **role on the team** | ⚠️ **unverified** — and the recorded roles may answer an open team question |

> ⚠️ **The 12-slide and 500-word limits are not on the public website.** They come from the
> organiser announcement *"One Month to Preliminary Round — Materials Lock 1 September"* (1 Aug
> 2026). Earlier internal docs concluded MAIC published no limits — **that was wrong.** See
> `./HACKATHON.md` §5.

**🔴 Blocking question:** are the deck and summary re-uploadable before the lock? The announcement
says mandatory items *"must be complete before the lock"* and optional items may be updated *"any
time before 1 September"* — which implies yes, but the wording is about optional items. **Confirm
on the dashboard first; everything else depends on it.** See `./HACKATHON.md` §6 Risk 1.

## Optional to submit, decisive to score

Per the announcement these may be added or updated any time before the lock.

| Item | Official spec | Status |
|---|---|---|
| Artifact / architecture PDF | GitHub repo, hosted demo, API endpoint, notebook, HuggingFace Space, or PDF (**≤ 5 MB**); must stay publicly accessible during judging | 🔴 **not ready** — `github.com/cindyyy11/SolaraX` returns **404 to the public**, has **1 commit**, contains **no code**. Needs ≥ 3 commits over ≥ 2 calendar days |
| Product demo video | MP4 or public URL, **max 3 minutes** | ⬜ not started. Must show the actual dashboard, not slides with narration |
| Team member profiles | **LinkedIn / GitHub links for each member** | ⬜ not started. WenHui's GitHub handle is still missing |

---

## Supporting technical deliverables (PRD v2 §9)

| Deliverable | Module | Status |
|---|---|---|
| Cleaned multi-site dataset + preprocessing script | M1 | ✅ 11 sites, 2 cohorts, 233 days. `pipeline/fetch_pvdaq.py` |
| Baseline model with documented formula | M2 | ✅ **Built.** pvlib on NASA POWER, R² 0.90, MAE 17.6%. Formula + hand-calculated check in [`docs/M2-M3-METHOD.md`](../docs/M2-M3-METHOD.md) |
| Peer-benchmarking detector with a stated accuracy figure from a real test | M3 | ✅ **Built.** Precision 86.7%, recall 65.0% on 100 held-out site-runs. `pipeline/output/detector_accuracy.json` |
| Economic ranking config, every assumption named and sourced | M4 | ✅ `config/assumptions.json`, RP4 sourced to ST. Loss input is now measured, not assumed |
| Image classifier with stated accuracy + SIMULATED labelling | M5 | ⬜ |
| Deployed public dashboard URL, 4 screens | M6 | ⬜ |
| Architecture diagram: ingestion → baseline → cohort → economics → API → dashboard | M7 | ⬜ (exists in Canva — export it) |
| README documenting real vs. simulated and how to run locally | M8 | ⬜ **`README.md` is currently empty** |
| `docs/RESEARCH.md` — every claim with a URL | — | ⬜ Not created. Blocks claim discipline (`../CLAUDE.md` §4) |

---

## Red-team check — run together on 25 Aug (PRD v2 §13)

1. ✅ **Closed.** M2 vs hand calculation, S-1277 on 2019-06-21 peak hour: 34.940074 kW both ways, agreement to 9 dp. Pinned in `test_baseline.py::HandCalculationTests`.
2. ✅ **Closed.** Precision 86.7%, recall 65.0%, FPR 6.7% over 100 site-runs on ten held-out seeds, with the threshold calibrated on a disjoint set. Ladder decays 88.9% at ≥30% to ~45% at 10-20%.
3. ✅ **Closed.** "We predict what each site should have produced from satellite weather alone, with nothing installed on any roof. Then we compare each site to its neighbours on the same day: a dip everyone shares is weather, a dip only one site has is a fault."
4. Is every commercial assumption in M4 traceable to a named constant with a stated source or labelled range?
5. Does the conclusion still hold at the pessimistic end of every Tier 2 range?
6. Does M5 state an accuracy figure and clearly label simulated input?
7. Does the full pipeline (M1→M4) run from a clean checkout with one command?
8. Is the dashboard URL public and loading without a login?
9. Does the demo video show the actual dashboard, not slides with narration?
10. Has every deck claim been sorted Tier 1 / 2 / 3, with Tier 3 items removed?

---

## Prizes and obligations

Pool **RM 388,000** — Champion RM 200,000 + equity · 1st RU RM 100,000 + equity · 2nd RU
RM 50,000 + equity · 5 category awards RM 5,000 each.

Top three must incorporate a Malaysian **Sdn. Bhd.** with at least one Malaysian director — a
condition precedent to receiving cash or equity. 90 days from award notification to register, a
further 60 days for equity onboarding. Cash is paid to the designated Malaysian citizen member's
verified account within 30 days of the Grand Final.

**IP stays with the team.** Organisers receive only a non-exclusive marketing licence.

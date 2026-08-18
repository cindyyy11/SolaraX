# Decision log — SolaraX / Team CinCaiLah

> **What this file is.** A reconstruction of what the team actually decided, when, and who
> decided it — compiled from the WhatsApp group export (*MAIC Nexus Hackathonzzz*, 24 Jun –
> 14 Aug 2026) plus the PRDs and the submitted deck. It exists so an agent (or a new teammate)
> can see the reasoning behind the current direction without re-reading two months of chat.
>
> Product rules live in [`../CLAUDE.md`](../CLAUDE.md). Competition rules live in
> [`../hinfo/HACKATHON.md`](../hinfo/HACKATHON.md). **This file records history and open threads — it is not
> authoritative for either.**
>
> Compiled 15 Aug 2026. Chat timestamps are MYT.

---

## 1. The team

Five members — **at the competition cap**. Nobody can be added mid-stage.

| Chat name | Also known as | GitHub | Notes |
|---|---|---|---|
| **Cindy** | ~ ~ Cindy | `cindyyy11` | Owns the repo and the MAIC account; ran registration, chases the group, made the initial commit |
| **WenHui** | ~ x r | *not given in chat* ⚠️ | Recruited the whole team; earlier self-described as frontend/presentation |
| **MK** | — | `mkuangdotcom` | UTM. Earlier self-described as backend + AI/ML; brought Chang Zhe and Zhuo Heng in |
| **Chang Zhe** | "Goh" | `goh1217` | UTM. Built the tech-stack and system-architecture slides; raised the repair-cost challenge |
| **Zhuo Heng** | — | `ZhuohengChew` | UTM. Authored **PRD v2**; answered the buyer question |

**Former members** (all left *before* the 8 Aug registration, so the registered roster is clean —
no mid-stage change problem): **Fang** (~ Mimosa) — withdrew 5 Aug, family medical emergency;
**Qian Wen** (UKM) — removed 1 Aug; **MY.Chai** — joined 1 Aug, withdrew 5 Aug, believed the
timeline was not achievable.

### Role assignment — ⚠️ unresolved

A roles poll ran on **10 Aug** with five options — AI/ML · Data · Full-Stack · Product ·
Computer Vision/AI — and each got exactly one vote. **The chat never records who took which
role.** PRD v2 §11 therefore uses anonymous placeholders A–E.

Indicative only, from earlier self-descriptions and observed work — **confirm before relying on
this**: MK → AI/ML or Data; Chang Zhe → architecture/infra; Zhuo Heng → Product; Cindy →
coordination/frontend; WenHui → frontend/presentation.

---

## 2. Decisions, in order

### 24 Jun 2026 — MAIC over NexHack
Group formed. NexHack 2026 was considered and dropped — its 28 Jun registration deadline was too
close and MAIC was judged the more significant national-level competition. **MAIC only.**

### 14 Jul — track must be picked at registration; early-bird tier missed
The team discovered a track must be selected *during* registration, not after. The RM 150 early
bird (to 15 Jul) was no longer reachable, so the target became the **RM 250 "fair early bird"
window closing 8 Aug** — which is why registration landed on 8 Aug rather than earlier.

### 16 Jul – 31 Jul — idea generation
Ideas raised and not pursued: a **Tai Chi motion-analysis app for elderly users** (T2, Fang);
**AI-powered Virtual Power Plant + distributed storage / P2P energy trading** to address grid
curtailment (Fang, 10-page research doc); **time-sensitive networking**; flood forecasting;
vehicle-to-traffic-light communication.

Three finalists emerged: **T1 Solar · T5 Flood · T5 Traffic.** Traffic was described as "the most
challenging idea" — the team was still looking for a way to build it.

### 2 Aug — 🔒 **Track and problem chosen: T1 Solar**
Poll result: **Solar 4 · Flood 3 · Traffic 0.** Locked at registration on 8 Aug and now
unchangeable.

### 5–6 Aug — team churn resolved
Fang and MY.Chai withdrew on the same day. MK brought in **Chang Zhe** and **Zhuo Heng** on 6 Aug,
restoring the team to five. WenHui, after weeks of recruiting: *"So tiring finding teammates."*

### 7–8 Aug — 🔒 **Names locked**
**Team name: CinCaiLah** (Cindy, 7 Aug). **Project name: SolaraX** (Chang Zhe, 8 Aug 00:05).

### 8 Aug — 🔒 **Registered and submitted**
Cindy registered the team and uploaded the deck and written project summary the same evening.
This is the submission MAIC currently holds. **It describes PRD v1, not what we are building
now** — see §3.

### 10 Aug — PRD v1 circulated; roles polled; GitHub handles collected
Cindy shared `SolaraX_PRD.md` (drone flight scheduling). Repo created the same day.

### 11 Aug — 🔒 **PRD v2 supersedes v1**
Zhuo Heng shipped `PRD.md`: the pivot from *"which row does the drone fly first on this
farm"* to *"which sites in my fleet deserve a visit this month."* Three reasons, all recorded in
PRD v2 §1 — flight sequencing is already Raptor Maps' product; drone providers are the wrong buyer
because they are paid per flight; and the money is in whether to mobilise at all, not in flight
efficiency. **This is the current direction.**

### 12–14 Aug — the repair-cost challenge → ⏸️ **deliberately deferred**

**Chang Zhe (12 Aug)** raised the sharpest technical objection so far: ranking sites by RM lost per
month against visit cost **never considers what the repair itself costs**. In principle a site
could top the queue where the fix costs more than the loss — an inverter replacement around
RM 46k against a site losing RM 1,900/month. Two reasons he still leaned toward leaving it out:
most solar repairs have strong ROI anyway (Bukit Raja loses RM 4,180/month against a ~RM 10k fix —
roughly 2.5 months' payback, which nobody skips for budget reasons), and **nobody publishes repair
invoices**, so any cost model would be invented numbers. He flagged it explicitly as something a
judge might raise.

**MK (12 Aug):** if the fault can be diagnosed, a fix / don't-fix calculation could follow.

**Zhuo Heng (13 Aug):** agreed it depends on diagnosis, and placed it precisely in the workflow.
The current chain is DETECT → TRIAGE → VERIFY → CONFIRM → LEARN. A drone reveals the *symptom*;
the actual damaged component is only known once the panel comes off the roof. So a repair decision
would sit in **CONFIRM**, and needs two things we do not have: a way to diagnose which component
failed, and a way to price the repair for that component.

**Chang Zhe (14 Aug):** it is an add-on, there is no solid solution to either blocker, **proceed
with the current approach.**

**Cindy (14 Aug):** *"let's not build it now but we can keep this thing in mind first."*

**Status: deferred by agreement, not overlooked.** This is a strong Q&A answer — it shows the team
found the limitation itself and reasoned about where it would live. Do not silently implement
repair-cost ranking; do not pretend the gap doesn't exist either.

### 14 Aug — 🔒 **Buyer question settled**

**Cindy asked:** who is the actual paying buyer — the O&M-bearing developer (Solarvest-type) or a
third-party O&M aggregator?

**Zhuo Heng answered:** *"the service can be sold to party who pay for a site visit. Our primary
customer will be the O&M-bearing developer and can approach to O&M aggregator for future
expansion."* Cindy accepted.

**Decision: the primary buyer is the developer carrying the bundled O&M obligation.** O&M
aggregators are a future expansion segment, not the MVP target. Commercial Viability is 25% of the
score — every commercial claim should point at this buyer.

### 14 Aug — 🔒 **Tech stack and architecture approved; implementation greenlit**
Chang Zhe completed the tech-stack and system-architecture slides. Cindy approved both and closed
the thread: *"so i think we can proceed with the implementation if there are no questions?"*
No objection was raised. **Build phase is open as of 14 Aug 2026.**

---

## 3. The gap nobody has closed yet

**What MAIC holds (8 Aug) ≠ what we are building (11 Aug onward).**

The submitted deck pitches drone-flight prioritisation on utility-scale farms — *"We tell you which
solar panels to check first"*, a growth path starting at *"Big solar farms"* with factory rooftops
only in Phase 2, RM 2,400/MW/year pricing, and a "Why fires start" slide. The submitted written
summary goes further, leading on fire statistics (84% of PV fire events equipment-driven, 79% of
high-risk connector faults with no thermal signature at inspection, BOMBA's Sept 2024 rooftop
guidelines).

PRD v2 §15 states the opposite position outright: *"Fire-risk statistics from v1's research don't
support v2's value proposition and are better left out… This is a yield and cost product, not a
safety product."*

**And there is a second, separate problem in the same artifact.** The organiser announcement of
1 Aug 2026 — *"One Month to Preliminary Round — Materials Lock 1 September"* — sets **max 12
slides** for the deck and **max 500 words** for the summary. It was circulated in this very chat on
8 Aug. Our deck is **21 pages** and the summary runs to roughly exactly **500 words**. Those limits
appear nowhere on the public MAIC website, which is almost certainly why nobody caught them.

Nobody in the chat has raised either issue. Both are **Risk 1** in
[`../hinfo/HACKATHON.md`](../hinfo/HACKATHON.md) §6 and need an owner. The good news is that the same
announcement indicates materials stay editable on the dashboard until the lock — so with 16 days
left this is recoverable, provided someone confirms it and starts the rebuild.

---

## 4. Other teams spotted on GitHub

MK's scouting, 31 Jul — public repos from what appear to be other MAIC entrants. Useful for knowing
what the T1 field looks like; **not** a reason to change direction.

| Project | Track | Repo | Focus |
|---|---|---|---|
| SolarPulse AI | T1 Clean Energy | `cloud8877-source/solarpulse-ai` | Post-install solar asset monitoring / O&M copilot |
| Heliopolis AI | T1 Clean Energy | `lewbei/heliopolis-ai` | Engineering due diligence — land titles, SLD, slope risk |
| FabPilot | T4 Manufacturing | `Zhe-cyber/fabpilot` | Predictive maintenance over MQTT |

**SolarPulse AI is the closest competitor** — same track, adjacent problem. Our differentiation is
the *fleet-as-control-group* method (PRD v2 Module 3) and the RM-denominated dispatch decision,
not monitoring itself.

---

## 5. References the team gathered

Shared in chat across 31 Jul – 10 Aug. Not yet tier-sorted — **do not cite any of these in a
deliverable until they are checked and recorded in a `docs/RESEARCH.md`** (see `CLAUDE.md` §4).

**Competitors / industry:** [Raptor Maps](https://raptormaps.com/) ·
[Sitemark](https://www.sitemark.com/) ·
[Sitemark's inspection-software roundup](https://www.sitemark.com/research/best-solar-inspection-software/) ·
[SmartHelio GAIA](https://smarthelio.com/gaia/) · [iFactory](http://ifactoryapp.com/industries/power-plant/drone-inspection-wind-turbines-solar-farms-ai)

**Open source / models:** [PV-Hawk](https://github.com/LukasBommes/PV-Hawk) ·
[yolov8s-seg-solar-panels](https://huggingface.co/finloop/yolov8s-seg-solar-panels) ·
[Roboflow solar datasets](https://universe.roboflow.com/search?q=utem%20solar)

**Malaysian policy / market:** [CREAM programme](https://www.singlebuyer.com.my/market/market-operations/programs/cream) ·
[P2P energy trading in Malaysia (Birmingham)](https://pure-oai.bham.ac.uk/ws/portalfiles/portal/218768639/Developing_Peer-to-Peer_P2P_Energy_Trading_Model_for_Malaysia_A_Review_and_Proposed_Implementation.pdf)

**Superseded — fire-risk direction only, do not reuse:**
[DOE fire safety guide](https://www.energy.gov/cmei/systems/guide-fire-safety-solar-systems) ·
[pv-magazine on solar fire risk](https://pv-magazine-usa.com/2026/05/13/solar-risks-internal-fire-regulatory-fines-and-battery-inaccuracies/) ·
[International Fire & Safety Journal](https://internationalfireandsafetyjournal.com/fire-safety-in-solar-installations-hidden-risks/)

---

## 6. Assets that live outside this repo ⚠️

These were shared as links in chat. They are **not backed up here** and an agent cannot read them.
If any is load-bearing, export it into the repo.

| Asset | Where | Holder |
|---|---|---|
| Pitch deck working file | Canva (`canva.link/rli612vi28p1ld8`) | Chang Zhe |
| **Tech stack + system architecture slides** (approved 14 Aug) | In the Canva deck | Chang Zhe |
| Research / ideas doc | Google Docs | Fang (former member) — ⚠️ access may be lost |
| UI wireframes | Figma board | Cindy |
| Team calls | Discord, Google Meet | — |

**The architecture slides are the highest-value item outside the repo.** They were formally
approved and nothing in the repo records what they contain.

---

## 7. Still open

| # | Question | Raised by | Status |
|---|---|---|---|
| 1 | Can the submitted deck and summary be re-uploaded before 31 Aug? | — (not yet raised in chat) | 🔴 Blocking — see §3 |
| 2 | Who holds which of the five roles? | Poll, 10 Aug | ⚠️ Unresolved |
| 3 | Repair-cost-aware ranking | Chang Zhe, 12 Aug | ⏸️ Deferred by agreement |
| 4 | How to diagnose which component failed | Zhuo Heng, 13 Aug | ⏸️ Open, prerequisite for #3 |
| 5 | How to price a repair per damaged component | Zhuo Heng, 13 Aug | ⏸️ Open, prerequisite for #3 |
| 6 | Was the AI usage disclosure submitted? | — | ⚠️ Unverified |
| 7 | WenHui's GitHub username | — | ⚠️ Missing |

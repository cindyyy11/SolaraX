# HACKATHON.md — MAIC Nexus Challenge 2026

> **What this file is.** The single, durable reference for everything about the *competition*
> — rules, rubric, dates, deliverables, and what our team has actually submitted so far. It is
> **direction-agnostic**: it stays true no matter how the product pivots. For the *product*, read
> [`CLAUDE.md`](../CLAUDE.md) and [`docs/PRD.md`](../docs/PRD.md). For who decided what
> and when, read [`docs/DECISIONS.md`](../docs/DECISIONS.md).
>
> **Verification status.** Everything marked ✅ was re-checked against the live
> [maicnexus.com](https://maicnexus.com/en) on **15 Aug 2026**. Items marked ⚠️ are unverified or
> disputed and are called out in §8 and §9. The official Rules & Regulations document
> (**R&R-MAIC-2026-v2**, May 2026) overrides this file, the FAQ, and every other page if they
> conflict — that precedence rule is itself published on the terms page.

---

## 1. At a glance

| | |
|---|---|
| **Competition** | MAIC Nexus Challenge 2026 — Malaysia AI Conference & Challenge |
| **Organisers** | Solara Global Media Sdn. Bhd. + Solarvest Holdings Berhad (jointly) |
| **Our team name** | **CinCaiLah** (registered 8 Aug 2026 on maicnexus.com) |
| **Our project** | SolaraX |
| **Track** | **T1 — AI for Clean Energy**, theme *Clean Energy Asset Monitoring* ✅ |
| **T1 industry partner** | **Solarvest** — also a co-organiser. Frame as partner, never competitor. |
| **Materials lock** | **1 September 2026, 00:00 MYT** ✅ — i.e. the same instant as the terms page's "31 Aug 23:59 MYT". Both published dates are correct. |
| **Days remaining** | 16 (as of 15 Aug 2026) |
| **Artifact repo** | `github.com/cindyyy11/SolaraX` — ⚠️ **currently returns 404 to the public** (see §6) |
| **Prize pool** | **RM 388,000** ✅ |
| **Funnel** | **300 teams enter → 30 advance → 10 reach the live final → 1 champion** ✅ |

---

## 2. Timeline

Published on maicnexus.com under an explicit caveat: *"Indicative timeline. Final dates confirmed
at application open."* ✅ The **31 Aug 23:59 MYT** deadline is stated on the terms page and is not
hedged — treat it as firm.

| Date | Event | Notes |
|---|---|---|
| 11 Jun 2026 | Launch event, registration opens | UOB Plaza 1, Kuala Lumpur |
| Jun 2026 | Applications open, free online AI Bootcamp begins | |
| 1 Aug 2026 | Organiser announcement: *"One Month to Preliminary Round — Materials Lock 1 September"* | ⚠️ **Carries hard limits that appear nowhere on the public site** — see §5. Circulated in the team chat 8 Aug. |
| 8 Aug 2026 | **We registered and submitted** | Team CinCaiLah, RM 250 paid 22:19 MYT — see §5 |
| **31 Aug 23:59 / 1 Sep 00:00 MYT** | **Materials lock. Applications close** ✅ | Same instant, both published. Everything mandatory must be complete. |
| **Early Sep 2026** | **Preliminary judging — online material review** | ⚠️ **This is the judging window.** Repo and demo must be public with no login wall throughout it. |
| End Sep 2026 | Preliminary results announced | **300 → 30 teams** |
| Oct 2026 | Semi-Final Demo Day, Kuala Lumpur (venue TBC) | 30 → 10 teams. In person, English. |
| Nov 2026 | Grand Final + AI Forum + Gala + Awards, Kuala Lumpur | 10 → champion |

**Internal target:** PRD v2 §12 sets **26 Aug** for submission-complete, leaving 5 days of buffer.
Hold that date — it is the only protection against a last-week failure.

### Stage names differ between official pages ⚠️

The terms page calls the stages **Application → Online Qualifier → University Semi-Final → Grand
Final**. The overview/homepage calls them **Preliminary → Semi-Final → Grand Final**. Same three
judged rounds; the naming is inconsistent on MAIC's own site. Use the overview naming in our own
materials, and don't read anything into "University" — eligibility has no academic requirement.

### What judges are told to ask at each stage

| Stage | The question |
|---|---|
| Preliminary | *"Is this a real attempt at solving a real problem with a real artifact?"* |
| Semi-Final | *"Is this team actually building something that works and can scale?"* |
| Grand Final | *"Is this team investable and is the product ready to commercialise?"* |

Note the escalation. The Preliminary round is won by **having something real that runs**, not by
having the best idea. The artifact is technically optional to submit and decisive to score.

---

## 3. Marking rubric ✅

Each criterion scored **1–10**, weighted to a **100-point** total.

| Criterion | Weight | What it is really asking |
|---|---|---|
| **Technical Feasibility** | **25%** | Can this be built, and is the method real and named? |
| **Commercial Viability** | **25%** | Does someone with a budget have a reason to pay? |
| **Industry Relevance** | **20%** | Does it sit squarely inside the declared track? |
| **Scalability** | **15%** | Does it get better/cheaper as it grows, or worse? |
| **ESG / National Impact** | **15%** | Does Malaysia benefit measurably? |

Technical + Commercial together are **half the score**. A brilliant model with no named buyer
scores the same as a great business plan with no working code — both lose half the marks.

**Working rule:** before building anything, name the rubric row it moves. If it doesn't move one
and isn't a listed module, deprioritise it.

Data governance is worth a line under ESG (fleet benchmarking aggregates data across competing
customers' sites — say who owns it and how cohorts avoid exposing one customer's production
profile to another), but it is **not** a scored category on its own.

---

## 4. Hard rules — any of these can disqualify

| Rule | Detail |
|---|---|
| **Public artifact** | Artifact links must be publicly accessible **without a login wall** during the judging window for the relevant stage. Private repos, gated demos, or auth-walled content **count as non-submission**. It may be private *outside* judging windows. |
| **Commit history** | Repositories used as artifacts must show **≥ 3 commits over ≥ 2 calendar days**, dated before the submission deadline. |
| **No backdating** | *"Plagiarism, fraudulent artifacts, or backdated commits used to fake development"* is an **explicit disqualification ground**. Never rewrite commit dates. |
| **English only** | All written materials — deck, summary, video, artifact documentation — and all spoken presentation and Q&A at Semi-Final and Grand Final. |
| **Track locked** | One industry from T1–T6, selected at submission, **cannot be changed**. Material divergence from the declared industry may be disqualified. |
| **One person, one team** | Being listed on two teams can disqualify **all** affected teams. |
| **Malaysian citizen** | Every team needs **≥ 1 Malaysian citizen (MyKad holder)**, designated by full legal name at application. PRs, expatriates and international students do **not** count. Malaysians living abroad **do**. |
| **Team changes** | Additions, removals and substitutions only **between stages** and only with **prior written organiser approval**. Mid-stage changes are not permitted. |
| **Team size** | 1–5 members. **We are at the 5-member cap — nobody can be added.** |
| **Honest representation** | Material misrepresentation in the application, fraudulent artifacts, or track misrepresentation at any stage are disqualification grounds. |

### How the track lock applies to our pivot

The lock is on the **industry (T1)**, not on the product idea. SolaraX moved from drone flight
scheduling to fleet yield assurance — both are squarely *Clean Energy Asset Monitoring* under T1,
so the pivot does **not** breach the track lock. What it does create is a materials problem: see §6.

---

## 5. Deliverables — official specs, and what we actually submitted

> ⚠️ **The binding format limits are not on the public website.** They come from the organiser
> announcement *"One Month to Preliminary Round — Materials Lock 1 September"* (published
> **1 Aug 2026**, circulated in the team chat 8 Aug). The public FAQ and terms pages state no page,
> slide, or word limits at all — checked 15 Aug. **Trust the announcement, and re-read the
> dashboard for any later notice.**

### Mandatory — must be complete before the lock

| Item | Official spec | Our status |
|---|---|---|
| **Pitch deck** | PDF, **max 12 slides** | 🔴 **Submitted 8 Aug at 21 pages — 9 over the limit.** Also PRD v1 framing (drone-first, utility farms, "Why fires start" slide), superseded 11 Aug |
| **Project summary** | Plain text, **max 500 words** | 🔴 **~500 words — at or fractionally over the cap.** Also fire-risk-led (84% equipment-driven fires, 79% of connector faults with no thermal signature, BOMBA guidelines) — framing PRD v2 explicitly drops |
| **AI disclosure statement** | How AI was used in building the submission | ⚠️ Partially verified — see the form breakdown below |
| **Track (T1)** | Locked at submission | ✅ Locked |
| **Malaysian citizen** | Team leader + each member give full legal name, IC no. (MyKad), nationality, university/company, **role on the team** | ⚠️ Verify on the dashboard |

### Optional — "strengthen your submission but won't block you"

Per the announcement these can be **added or updated any time before 1 September**.

| Item | Official spec | Our status |
|---|---|---|
| **Product demo video** | MP4 or public URL, **max 3 minutes** | ⬜ Not started. Must show the real dashboard, not narrated slides |
| **Artifact / architecture PDF** | GitHub repo, hosted demo, API endpoint, notebook, HuggingFace Space, **or** PDF upload. Must stay publicly accessible during judging. PDF **≤ 5 MB** | 🔴 Repo is 404 to the public, 1 commit, no code — see §6 |
| **Team member profiles** | **LinkedIn / GitHub links for each member** | ⬜ Not started. WenHui's GitHub handle is still unknown |

### The AI disclosure form (Step 05) — three required parts

Captured from the live application flow, 8 Aug:

1. **AI tools used** — multi-select: Code generation · Data analysis / model training · Writing &
   documentation · Design / visual assets · No AI tooling used. *(All four positive categories were
   ticked in our submission.)*
2. **Tools & models** — required free text, e.g. *"GitHub Copilot for code completion, Claude 3.5
   Sonnet for documentation drafting, GPT-4o for data preprocessing scripts."* ⚠️ This field was
   **showing a validation error (empty)** in the screenshot taken during our submission. Confirm it
   was filled before the form was accepted.
3. **Declaration** — required checkbox: *"The core problem statement, solution design, and
   intellectual contribution are original to our team. Any AI-generated outputs have been reviewed
   and validated by us, and we take full responsibility for all submitted work."*

MAIC states plainly: *"Transparency about tooling does not penalise your entry — judges evaluate
innovation and impact, not whether you used AI assistance."* **Disclose fully and specifically.**

### Application flow — 6 steps

Eligibility → **Team** → Industry → Materials → **AI Disclosure** → Review. The dashboard is
reached with the **team name + password**. Note that Step 02 captures a **"role on the team"** per
member — so the role assignment the team never wrote down in chat may already be recorded there.

---

## 6. Live risk register — the three things that can actually sink us

Ordered by severity. Owner and date must be filled in by the team.

### 🔴 Risk 1 — The submitted deck breaks a hard format limit, and describes the wrong product

Two problems in one artifact, both fixable, neither noticed by anyone in the team chat.

**1a — Format.** The official spec is **PDF, max 12 slides**. We submitted **21 pages**. Nine over.
The limit is published in the 1 Aug organiser announcement, not on the website, which is almost
certainly why it was missed. The project summary has the same shape of problem: **max 500 words**,
and ours runs to roughly exactly 500 — no margin.

**1b — Direction.** The deck and summary lodged on **8 Aug** pitch drone-flight scheduling on
utility farms with a fire-safety argument. **PRD v2 (11 Aug) is a different product** — different
buyer, different unit of decision, and an explicit instruction to leave fire statistics out. A
judge who reads the submitted summary and then opens the repo sees two different companies.

**Good news:** the announcement says mandatory items *"must be complete before the lock"* and that
optional items can be updated *"any time before 1 September"* — so materials are editable on the
dashboard right up to the lock. **This is very likely fixable, and there are 16 days to do it.**

**Action:**
1. Log into the dashboard and confirm the deck and summary are re-uploadable. If it is not obvious,
   email `support@maicnexus.com` — do this **first**, everything else depends on it.
2. Rebuild the deck for PRD v2 **at 12 slides or fewer**. This is a hard rewrite, not a trim — 12
   slides is tight for the story, so plan the cut deliberately.
3. Rewrite the summary for PRD v2 **under 500 words**, and count them.
4. If re-upload turns out to be locked: the repo README, architecture PDF and demo video become
   the only places judges see the real product. They must carry the v2 story completely, and the
   evolution should be explained in one honest line — never papered over.

### 🔴 Risk 2 — The commit rule is not yet satisfied

The repo has **1 commit** (10 Aug, "Initial commit"). The rule is **≥ 3 commits over ≥ 2 calendar
days**. Everything currently in the working tree — `CLAUDE.md`, both PRDs, the deck, all of
`docs/` — is **untracked and therefore not in the repo at all**.

Backdating to fix this later is an **explicit disqualification ground**. The only safe remedy is
real commits on real days, starting now. There are 16 days left, which is ample — but only if
someone starts today.

### 🔴 Risk 3 — The artifact repo is not publicly reachable

`https://github.com/cindyyy11/SolaraX` returns **HTTP 404** to an unauthenticated request
(checked 15 Aug 2026), meaning it is private, renamed, or deleted. That is permitted *now* — the
rules allow private outside judging windows — but during the **early-September judging window** a
private repo counts as **non-submission**.

**Action:** confirm the repo exists under that exact URL and set a hard calendar reminder to make
it public before the judging window opens, and to keep it public until results are announced.

---

## 7. Money, prizes and post-win obligations

**Registration fee** (paid once per team): RM 150 early bird to 15 Jul · RM 250 fair early bird
16 Jul – 8 Aug · RM 500 standard from 9 Aug. We registered on **8 Aug**, so the RM 250 tier
applied. Entry is capped at **300 teams**, first come first served.

**Prize pool: RM 388,000** ✅
- Champion — RM 200,000 cash + equity
- 1st Runner-up — RM 100,000 cash + equity
- 2nd Runner-up — RM 50,000 cash + equity
- 5 special category awards — RM 5,000 each, cash only
- All participants — merit certificate · All finalists — Huntier talent pipeline listing
- Top 3 — trophy + AI Forum and Expo access on Grand Final day

**Conditions attached to winning — read before accepting anything:**
- The top three must incorporate a Malaysian **Sdn. Bhd.** with at least one Malaysian director.
  Incorporation is a **condition precedent** to receiving cash or equity: 90 calendar days from
  award notification to register, a further 60 days to complete equity onboarding. Failing equity
  onboarding forfeits **only** the equity component, not the cash.
- Cash is paid to the **designated Malaysian citizen team member's** verified bank account, on
  behalf of the team, within 30 calendar days of the Grand Final.
- Teams accepting investment may be subject to time-limited co-investment rights — a right of
  first offer and a right of first refusal. These are benchmark-and-matching mechanisms only;
  teams are free to decline investment or raise elsewhere. Full terms sit in the stage-two
  participation agreement.
- A **two-tier agreement model** applies: basic participation terms at registration, then a
  stage-two agreement for Semi-Final teams covering confidentiality, IP, data-sharing and
  investment terms.

**Intellectual property:** all IP in submitted artifacts and materials **stays with the team**.
Organisers acquire no ownership — only a non-exclusive, royalty-free, worldwide licence to use
submitted materials for marketing, editorial and convening purposes, with attribution where
reasonable. Making the repo public for judging does not transfer anything. A LICENSE file (we have
MIT) clarifies reuse terms.

**Privacy:** personal data is processed under Malaysia's PDPA 2010. Participant data retained 24
months, finalist data 36 months. Consent withdrawal → `admin@maicnexus.com`, resolved within 14
days. **Governing law:** Malaysia; exclusive jurisdiction of the courts of Kuala Lumpur.

---

## 8. Corrections — our local extract has drifted from the live site

`hinfo/maicnexus-extract/` was captured earlier and is now **stale in two places**. It is still the
best verbatim record of the terms text, but do not cite these two figures from it:

| Claim | Local extract says | Live site says (15 Aug 2026) ✅ | Why it matters |
|---|---|---|---|
| Preliminary cut | 300 → **100** teams advance | *"300 teams enter. **30** advance. 10 reach the live final. One champion wins."* | The Preliminary cut is **~10%, not ~33%**. Three times harsher than our planning docs assumed. Plan for a 1-in-10 round. |
| Prize pool | "exceeds RM 370,000" | **"RM 388,000 Total Prize"** | Use RM 388,000. |

Resolved discrepancies, for the record:

| Question | Resolution |
|---|---|
| Deadline: 31 Aug or ~1 Sep? | **Both are right — same instant.** The terms page says applications close *31 Aug 2026, 23:59 MYT*; the 1 Aug organiser announcement says materials lock *1 Sep 2026, 00:00 MYT*. PRD v2's "~1 Sep, to be confirmed" was not an error. Use **31 Aug 23:59 MYT** in team materials to avoid an off-by-one-day reading. |
| Are there deck/summary size limits? | **Yes — max 12 slides, max 500 words**, from the 1 Aug announcement. The public FAQ and terms pages say nothing about limits, and earlier internal docs concluded "MAIC publishes no slide count or word limit". **That conclusion was wrong** and led to a 21-page deck being submitted. |
| R&R version | **R&R-MAIC-2026-v2**, dated May 2026 (the extract records it as v2.1, May 2026). Either way the R&R overrides all other pages. |

---

## 9. Open questions — verify these, do not guess

Each needs a named owner and an answer before 26 Aug.

1. **Can the pitch deck and project summary be re-uploaded before the lock?** The 1 Aug
   announcement strongly implies yes ("add or update them any time before 1 September"), but that
   sentence is written about the *optional* items. **Confirm on the dashboard before planning
   around it** — Risk 1 depends entirely on this answer.
2. **Is "max 12 slides" counted as PDF pages?** Our deck is 21 PDF pages. Assume pages = slides
   unless told otherwise, and design to 12.
3. **Was the "Tools & models" field of the AI disclosure actually filled?** It was showing a
   required-field error mid-submission (§5). Mandatory item — verify.
4. **What roles were recorded per member at registration?** Step 02 captured a "role on the team"
   field. That may already answer the question the team never settled in chat.
5. **Does the repo URL `github.com/cindyyy11/SolaraX` still exist**, and who has admin rights to
   flip it public?
6. **Exact Preliminary judging dates** — "early September" is all that is published. Ask, so the
   repo-public window is set precisely rather than guessed.
7. **Has anyone obtained R&R-MAIC-2026-v2 itself?** We are working from the public terms page, the
   FAQ, and one organiser announcement. The R&R overrides all of them. Download it into `docs/`.
8. **Are there later organiser announcements nobody has read?** The 1 Aug notice carried limits
   that exist nowhere else. Check the dashboard's announcements feed on a schedule, not once.

**Contacts:** `support@maicnexus.com` (general) · `admin@maicnexus.com` (data/privacy).

---

## 10. Where the source material lives

| Source | Location | Trust |
|---|---|---|
| Official rules, FAQ, tracks, rubric | [`hinfo/maicnexus-extract/`](./maicnexus-extract/) | Verbatim capture — authoritative **except** the two figures in §8 |
| The R&R PDF itself | Not yet obtained — see §9.6 | Overrides everything |
| Live site | https://maicnexus.com/en · [terms](https://maicnexus.com/en/terms) · [FAQ](https://maicnexus.com/en/faq) · [tracks](https://maicnexus.com/en/tracks) | Current; re-check before the final week |
| Our submitted deck | [`SolaraXMAICPitch.pdf`](./SolaraXMAICPitch.pdf) | Byte-identical to the file submitted 8 Aug — v1 framing |
| Our submitted summary | [`docs/DECISIONS.md`](../docs/DECISIONS.md) §8 Aug | Reproduced verbatim from the team chat |
| Team decision history | [`docs/DECISIONS.md`](../docs/DECISIONS.md) | Sourced from the WhatsApp export, 24 Jun – 14 Aug 2026 |
| Deliverable-by-deliverable tracker | [`docs/SUBMISSION-CHECKLIST.md`](./SUBMISSION-CHECKLIST.md) | |

---

## 11. Competition glossary

| Term | Meaning |
|---|---|
| **MAIC** | Malaysia AI Conference and Challenge |
| **R&R** | The official Rules and Regulations document (R&R-MAIC-2026-v2, May 2026). Overrides every other published page. |
| **Artifact** | A working, judge-accessible deliverable. For us: this repo + the deployed dashboard. |
| **MyKad** | Malaysian Identity Card. Holding one is the test of Malaysian citizenship for eligibility. |
| **Sdn. Bhd.** | *Sendirian Berhad* — Malaysian private limited company. Top-3 winners must incorporate one. |
| **T1–T6** | The six industry tracks. We are **T1, AI for Clean Energy**. |
| **MYT** | Malaysia Time, UTC+8. The deadline is stated in MYT. |
| **Solarvest** | T1's industry partner and a co-organiser. Partner framing only, never competitor. |
| **Huntier** | Talent-pipeline partner; all finalists get a listing. |

---

*Compiled 15 Aug 2026 from the WhatsApp team export (24 Jun – 14 Aug), `hinfo/maicnexus-extract/`,
and a live re-check of maicnexus.com. Deadline: **31 August 2026, 23:59 MYT**.*

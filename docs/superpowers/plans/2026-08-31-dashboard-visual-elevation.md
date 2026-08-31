# Dashboard Visual Elevation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Site Detail's 9 content blocks one consistent card language (closing real drift: 3 different chrome recipes today), add motion and headline emphasis to Dispatch/Fleet Health, and give Work Order's title real weight — all within the locked stack, all print-safe.

**Architecture:** Two new global classes (`.card`, `.card--dark`) plus an interaction modifier (`.card--interactive`) and a shared entrance-motion utility (`.stagger-in`) land in the existing `assets/layout.css`, mirroring exactly how Tier 1 added `.screen`/`.btn-primary`. Site Detail's 9 blocks (7 separate component files + `SiteDetailView.vue`'s own `.panel` rule) adopt them, replacing hand-rolled chrome. A new `.page-stack` wrapper in `SiteDetailView.vue` gives the page one consistent vertical rhythm using Tier 1's `--space-lg` token (its first real consumer). Dispatch and Fleet Health get staggered entrance motion and Fleet Health's headline tiles get a real visual weight bump. Work Order gets a title-size increase and section-rhythm polish, with every print-mode rule left untouched.

**Tech Stack:** Vue 3 `<script setup lang="ts">`, plain scoped CSS + CSS custom properties, `npm run build` for verification (no component-mount test layer in this codebase, same as Tier 1).

**Spec:** `docs/superpowers/specs/2026-08-30-dashboard-visual-elevation-design.md`

## Global Constraints

- No Tailwind, no font/icon-library swap — same locked stack as Tier 1.
- Do not touch `SiteDigitalTwin.vue` / `FleetSkyline3D.vue` internals, the Leaflet map, or ECharts rendering logic.
- `WorkOrderView.vue`'s print mechanics are load-bearing and must survive unchanged: `.no-print`, `@page`, the `.print-doc { display: table }` repeating-letterhead trick, `break-inside: avoid`, `.signature`'s print-only `display: flex`. New elevation/shadow added to `.card` or `.section` in the base ruleset must NOT also be added inside the existing `@media print` block (which already zeroes `.card`'s `box-shadow` there).
- `.card--interactive` (hover-lift) is added to Site Detail's 9 blocks only — never to Work Order's `.card` (a print-document root, not a browsable card).
- Every animation (`.stagger-in`, `.card--interactive:hover`) must respect `prefers-reduced-motion: reduce`.
- Every task ends with `npm run build` passing cleanly (from `apps/web/`).
- Commit after every task with the exact message given in that task's last step.

---

### Task 1: `.card`/`.card--dark`/`.card--interactive`/`.stagger-in` in `layout.css`

**Files:**
- Modify: `apps/web/src/assets/layout.css`

**Interfaces:**
- Consumes: `--surface-1`, `--nav-surface`, `--nav-border`, `--border-hairline`, `--radius-lg`, `--elevation-1`, `--brand-navy`, `--duration-base`, `--ease-out` (all existing tokens).
- Produces: CSS classes `.card`, `.card--dark`, `.card--interactive`, `.stagger-in`, `@keyframes card-enter` — consumed by Tasks 2–7.

- [ ] **Step 1: Add the new rules**

Append to `apps/web/src/assets/layout.css`, after the existing `.btn-primary` reduced-motion block:

```css

/* Shared card chrome — closes drift found across Site Detail's 9 content
   blocks (3 different hand-rolled chrome recipes before this pass: two
   radius values, elevation present on only 3 of 9, two different dark
   surfaces for the two "instrument panel" cards). .card is the light
   variant, .card--dark is for content that's deliberately a dark embedded
   workspace (matches --nav-surface, the same dark plate the nav rail uses). */
.card {
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
  box-shadow: var(--elevation-1);
}
.card--dark {
  background: var(--nav-surface);
  border: 1px solid var(--nav-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--elevation-1);
}

/* Hover-lift for browsable cards. Never applied to Work Order's .card — that
   element is a print-document root, not a browsable card. */
.card--interactive {
  transition:
    transform var(--duration-base) var(--ease-out),
    box-shadow var(--duration-base) var(--ease-out);
}
.card--interactive:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 40px color-mix(in srgb, var(--brand-navy) 12%, transparent);
}
@media (prefers-reduced-motion: reduce) {
  .card--interactive:hover {
    transform: none;
  }
}

/* Shared entrance stagger. Callers set their own animation-delay per item
   (nth-child rules for static markup, an inline style bound to a v-for
   index for dynamic lists) — this class only owns the motion itself. */
@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.stagger-in {
  animation: card-enter var(--duration-base) var(--ease-out) both;
}
@media (prefers-reduced-motion: reduce) {
  .stagger-in {
    animation: none;
  }
}
```

- [ ] **Step 2: Build**

Run (from `apps/web/`): `npm run build`
Expected: builds cleanly. Nothing references these classes yet.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/assets/layout.css
git commit -m "feat(web): add shared .card/.card--dark/.card--interactive and .stagger-in primitives"
```

---

### Task 2: Adopt `.card` in Site Detail's 4 older components (radius-md → shared, elevation added)

**Files:**
- Modify: `apps/web/src/components/CohortChart.vue`
- Modify: `apps/web/src/components/InverterPanel.vue`
- Modify: `apps/web/src/components/InverterThermalMap.vue`
- Modify: `apps/web/src/components/VisionEvidence.vue`

**Interfaces:**
- Consumes: `.card`, `.card--interactive` (Task 1).

- [ ] **Step 1: `CohortChart.vue`**

Find (template root, around line 251):
```html
  <figure class="cohort">
```
Replace with:
```html
  <figure class="cohort card card--interactive">
```

Find (in `<style scoped>`):
```css
.cohort {
  margin: 0;
  padding: 1rem 1rem 0.75rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
```
Replace with:
```css
.cohort {
  margin: 0;
  padding: 1rem 1rem 0.75rem;
}
```

- [ ] **Step 2: `InverterPanel.vue`**

Find (template root, around line 93):
```html
  <section class="sub">
```
Replace with:
```html
  <section class="sub card card--interactive">
```

Find (in `<style scoped>`):
```css
.sub {
  padding: 1.25rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
```
Replace with:
```css
.sub {
  padding: 1.25rem;
}
```

- [ ] **Step 3: `InverterThermalMap.vue`**

Find (template root, around line 82):
```html
  <section v-if="thermalUnits.length" class="thermal">
```
Replace with:
```html
  <section v-if="thermalUnits.length" class="thermal card card--interactive">
```

Find (in `<style scoped>` — this rule also defines local `--thermal-*` custom properties; keep those and the `padding` line, remove only the three chrome lines):
```css
  padding: 1.25rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
```
Replace with:
```css
  padding: 1.25rem;
}
```
(This is inside the larger `.thermal { --thermal-0: ...; ... }` rule — only the four lines shown change; every `--thermal-*` custom property line above them stays exactly as-is.)

- [ ] **Step 4: `VisionEvidence.vue`**

Find (template root, around line 125):
```html
  <section class="vision">
```
Replace with:
```html
  <section class="vision card card--interactive">
```

Find (in `<style scoped>`):
```css
.vision {
  padding: 1.25rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
```
Replace with:
```css
.vision {
  padding: 1.25rem;
}
```

- [ ] **Step 5: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 6: Manual verification**

Run `npm run dev`, open a `/site/:siteId` page with sub-site/thermal/vision data. Confirm all four blocks now show a visible shadow (elevation) they didn't have before, and their corner radius is now the same as `.panel`'s (visibly slightly rounder than before). Hover each — confirm a subtle lift.

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/components/CohortChart.vue apps/web/src/components/InverterPanel.vue apps/web/src/components/InverterThermalMap.vue apps/web/src/components/VisionEvidence.vue
git commit -m "refactor(web): adopt shared .card chrome in CohortChart/InverterPanel/InverterThermalMap/VisionEvidence"
```

---

### Task 3: Adopt `.card` in Site Detail's 3 newer light components

**Files:**
- Modify: `apps/web/src/components/SpatialOperations.vue`
- Modify: `apps/web/src/components/EvidenceTimeline.vue`
- Modify: `apps/web/src/components/SiteComparison.vue`

**Interfaces:**
- Consumes: `.card`, `.card--interactive` (Task 1), `.page-stack` (Task 5 — these components' own `margin` is removed here in anticipation of Task 5's wrapper owning spacing; until Task 5 lands, these three blocks will sit with no vertical gap between them and their neighbors — acceptable since Task 5 is the very next task in this plan and this task's own build/manual-check only needs to confirm the chrome, not final spacing).

- [ ] **Step 1: `SpatialOperations.vue`**

Find (template root, around line 34):
```html
  <section class="spatial" aria-labelledby="spatial-title">
```
Replace with:
```html
  <section class="spatial card card--interactive" aria-labelledby="spatial-title">
```

Find (in `<style scoped>`):
```css
.spatial { margin:1.75rem 0; overflow:hidden; background:var(--surface-1); border:1px solid var(--border-hairline); border-radius:var(--radius-lg); box-shadow:var(--elevation-1); }
```
Replace with:
```css
.spatial { overflow:hidden; }
```

- [ ] **Step 2: `EvidenceTimeline.vue`**

Find (template root, around line 22):
```html
  <section class="timeline" aria-labelledby="timeline-title">
```
Replace with:
```html
  <section class="timeline card card--interactive" aria-labelledby="timeline-title">
```

Find (in `<style scoped>`):
```css
.timeline { margin:1.75rem 0; overflow:hidden; background:var(--surface-1); border:1px solid var(--border-hairline); border-radius:var(--radius-lg); }
```
Replace with:
```css
.timeline { overflow:hidden; }
```

- [ ] **Step 3: `SiteComparison.vue`**

Find (template root, around line 65):
```html
  <section v-if="peer" class="compare" aria-labelledby="site-comparison-title">
```
Replace with:
```html
  <section v-if="peer" class="compare card card--interactive" aria-labelledby="site-comparison-title">
```

Find (in `<style scoped>`):
```css
.compare {
  margin: 1.5rem 0;
  padding: 1.1rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
  box-shadow: var(--elevation-1);
}
```
Replace with:
```css
.compare {
  padding: 1.1rem;
}
```

- [ ] **Step 4: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 5: Manual verification**

Run `npm run dev`, open a `/site/:siteId` page. Confirm `SpatialOperations`/`SiteComparison` look visually unchanged (they already matched `.card`'s definition exactly — this is pure de-duplication), and `EvidenceTimeline` now shows a shadow it didn't have before.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/components/SpatialOperations.vue apps/web/src/components/EvidenceTimeline.vue apps/web/src/components/SiteComparison.vue
git commit -m "refactor(web): adopt shared .card chrome in SpatialOperations/EvidenceTimeline/SiteComparison"
```

---

### Task 4: Adopt `.card--dark` in Site Detail's 2 dark "instrument" components

**Files:**
- Modify: `apps/web/src/components/PerformanceModel.vue`
- Modify: `apps/web/src/components/RecoveryTracker.vue`

**Interfaces:**
- Consumes: `.card--dark`, `.card--interactive` (Task 1).

- [ ] **Step 1: `PerformanceModel.vue`**

Find (template root, around line 27):
```html
  <section class="model" aria-labelledby="performance-model-title">
```
Replace with:
```html
  <section class="model card--dark card--interactive" aria-labelledby="performance-model-title">
```

Find (in `<style scoped>`, around line 91):
```css
.model {
  margin: 1.5rem 0;
  padding: 1.1rem;
  background: var(--nav-surface);
  color: var(--nav-text-strong);
  border: 1px solid var(--nav-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
```
Replace with:
```css
.model {
  padding: 1.1rem;
  color: var(--nav-text-strong);
  overflow: hidden;
}
```

- [ ] **Step 2: `RecoveryTracker.vue`**

This is the one visible color shift in this pass: `RecoveryTracker`'s hardcoded `#13211d` becomes `--nav-surface` (`#101b18` — close, but a real, intentional difference, not a no-op), and its bespoke shadow is replaced by the shared `--elevation-1`, matching `PerformanceModel`.

Find (template root, around line 50):
```html
  <section class="recovery" aria-labelledby="recovery-title">
```
Replace with:
```html
  <section class="recovery card--dark card--interactive" aria-labelledby="recovery-title">
```

Find (in `<style scoped>`, around line 84):
```css
.recovery { margin:1.75rem 0; overflow:hidden; color:#eff5f2; background:#13211d; border-radius:var(--radius-lg); box-shadow:0 18px 42px rgba(9,22,18,.16); }
```
Replace with:
```css
.recovery { overflow:hidden; color:#eff5f2; }
```

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 4: Manual verification**

Run `npm run dev`, open a `/site/:siteId` page with hypothesis/recovery data. Confirm `PerformanceModel` and `RecoveryTracker` now sit at the same corner radius, border treatment, and shadow (both should look like clearly-related "instrument panel" cards). `RecoveryTracker`'s background will be a subtly different, slightly darker shade than before — expected, not a bug.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/PerformanceModel.vue apps/web/src/components/RecoveryTracker.vue
git commit -m "refactor(web): adopt shared .card--dark chrome in PerformanceModel/RecoveryTracker"
```

---

### Task 5: `SiteDetailView.vue` — consolidate `.panel`, add `.page-stack` rhythm

**Files:**
- Modify: `apps/web/src/views/SiteDetailView.vue`

**Interfaces:**
- Consumes: `.card`, `.card--interactive` (Task 1); `--space-lg` (existing token from Tier 1, its first real consumer).
- Produces: `.page-stack` wrapper — internal to this file only, nothing downstream depends on it.

- [ ] **Step 1: Wrap the content flow in `.page-stack`**

Find, in the template (the five bare component calls through the closing of the VisionEvidence block):

```html
      <PerformanceModel :site="site" />
      <SpatialOperations :site="site" />
      <RecoveryTracker :site="site" />
      <EvidenceTimeline :site="site" />
      <SiteComparison :subject="site" :sites="dispatch?.sites ?? []" />

      <!-- Block 1 — cohort chart, full width, above everything else. -->
      <section class="block">
        <CohortChart
          v-if="site.series && site.series.cohort.length"
          :rows="site.series.cohort"
          :subject-name="site.name"
          :divergence="site.divergence"
          :economics="site.economics"
        />
        <p v-else class="empty">
          No cohort series for this site. Healthy sites omit peer data by design — docs/Schema.md
          section 8.7.
        </p>
      </section>

      <!-- Block 2 — explainability. Every flag answers "why" with a number AND a method name. -->
      <section v-if="site.detection && site.economics && site.hypothesis" class="panel">
        <h2 class="panel__heading">Why this site is flagged</h2>
        <p class="panel__summary">{{ site.hypothesis.summary }}</p>
        <p class="panel__detail">{{ site.hypothesis.detail }}</p>

        <dl class="facts">
          <div>
            <dt>Method</dt>
            <dd>{{ site.detection.method }}</dd>
          </div>
          <div>
            <dt>Score</dt>
            <dd>{{ site.detection.score }} ({{ site.detection.score_type }})</dd>
          </div>
          <div>
            <dt>Threshold</dt>
            <dd>{{ site.detection.threshold }}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{{ Math.round(site.detection.confidence * 100) }}%</dd>
          </div>
          <div>
            <dt>Cohort</dt>
            <dd>{{ cohort?.label }} · {{ site.detection.cohort_size }} sites</dd>
          </div>
          <div v-if="site.divergence">
            <dt>Diverging since</dt>
            <dd>{{ site.divergence.start_date }} ({{ site.divergence.days_since }} days)</dd>
          </div>
          <div>
            <dt>At risk</dt>
            <dd>{{ formatRinggit(site.economics.rm_at_risk_monthly) }}/month</dd>
          </div>
          <div>
            <dt>Calculation</dt>
            <dd>{{ site.economics.calculation }}</dd>
          </div>
        </dl>

        <NoticeCallout
          v-if="!site.detection.cohort_meets_minimum"
          tone="warning"
          compact
          class="caution"
        >
          This cohort is below the minimum size. Peer comparison is weaker here — treat the score
          with caution.
        </NoticeCallout>
      </section>

      <p v-else class="panel">This site is within cohort tolerance. No detection recorded.</p>

      <!-- Block 3 — sub-site breakdown. Only where per-inverter channels exist. -->
      <section v-if="site.sub_site" class="block">
        <InverterPanel :sub-site="site.sub_site" :evidence="site.evidence" />
      </section>

      <!-- Block 4 — thermal map. Only where per-inverter temperature exists. -->
      <section v-if="site.sub_site?.has_thermal" class="block">
        <InverterThermalMap :sub-site="site.sub_site" :evidence="site.evidence" />
      </section>

      <!--
        Block 5 — CV evidence for flagged sites.

        Gated on a configured vision service as well as on detection. The panel
        posts an uploaded image to a live endpoint, and a deployed dashboard is
        served over HTTPS: without a reachable HTTPS service there is nothing for
        it to talk to, and rendering an upload box that always fails is worse
        than rendering nothing. See VISION_API_URL in services/api.ts.
      -->
      <section v-if="site.detection && visionAvailable" class="block">
        <VisionEvidence :site-id="site.site_id" :site-name="site.name" />
      </section>
```

Replace with (wraps the exact same content in `<div class="page-stack">`, no other change to any line inside it):

```html
      <div class="page-stack">
        <PerformanceModel :site="site" />
        <SpatialOperations :site="site" />
        <RecoveryTracker :site="site" />
        <EvidenceTimeline :site="site" />
        <SiteComparison :subject="site" :sites="dispatch?.sites ?? []" />

        <!-- Block 1 — cohort chart, full width, above everything else. -->
        <section class="block">
          <CohortChart
            v-if="site.series && site.series.cohort.length"
            :rows="site.series.cohort"
            :subject-name="site.name"
            :divergence="site.divergence"
            :economics="site.economics"
          />
          <p v-else class="empty">
            No cohort series for this site. Healthy sites omit peer data by design —
            docs/Schema.md section 8.7.
          </p>
        </section>

        <!-- Block 2 — explainability. Every flag answers "why" with a number AND a method name. -->
        <section v-if="site.detection && site.economics && site.hypothesis" class="panel card">
          <h2 class="panel__heading">Why this site is flagged</h2>
          <p class="panel__summary">{{ site.hypothesis.summary }}</p>
          <p class="panel__detail">{{ site.hypothesis.detail }}</p>

          <dl class="facts">
            <div>
              <dt>Method</dt>
              <dd>{{ site.detection.method }}</dd>
            </div>
            <div>
              <dt>Score</dt>
              <dd>{{ site.detection.score }} ({{ site.detection.score_type }})</dd>
            </div>
            <div>
              <dt>Threshold</dt>
              <dd>{{ site.detection.threshold }}</dd>
            </div>
            <div>
              <dt>Confidence</dt>
              <dd>{{ Math.round(site.detection.confidence * 100) }}%</dd>
            </div>
            <div>
              <dt>Cohort</dt>
              <dd>{{ cohort?.label }} · {{ site.detection.cohort_size }} sites</dd>
            </div>
            <div v-if="site.divergence">
              <dt>Diverging since</dt>
              <dd>{{ site.divergence.start_date }} ({{ site.divergence.days_since }} days)</dd>
            </div>
            <div>
              <dt>At risk</dt>
              <dd>{{ formatRinggit(site.economics.rm_at_risk_monthly) }}/month</dd>
            </div>
            <div>
              <dt>Calculation</dt>
              <dd>{{ site.economics.calculation }}</dd>
            </div>
          </dl>

          <NoticeCallout
            v-if="!site.detection.cohort_meets_minimum"
            tone="warning"
            compact
            class="caution"
          >
            This cohort is below the minimum size. Peer comparison is weaker here — treat the
            score with caution.
          </NoticeCallout>
        </section>

        <p v-else class="panel card">This site is within cohort tolerance. No detection recorded.</p>

        <!-- Block 3 — sub-site breakdown. Only where per-inverter channels exist. -->
        <section v-if="site.sub_site" class="block">
          <InverterPanel :sub-site="site.sub_site" :evidence="site.evidence" />
        </section>

        <!-- Block 4 — thermal map. Only where per-inverter temperature exists. -->
        <section v-if="site.sub_site?.has_thermal" class="block">
          <InverterThermalMap :sub-site="site.sub_site" :evidence="site.evidence" />
        </section>

        <!--
          Block 5 — CV evidence for flagged sites.

          Gated on a configured vision service as well as on detection. The panel
          posts an uploaded image to a live endpoint, and a deployed dashboard is
          served over HTTPS: without a reachable HTTPS service there is nothing for
          it to talk to, and rendering an upload box that always fails is worse
          than rendering nothing. See VISION_API_URL in services/api.ts.
        -->
        <section v-if="site.detection && visionAvailable" class="block">
          <VisionEvidence :site-id="site.site_id" :site-name="site.name" />
        </section>
      </div>
```

(Note: `class="panel"` becomes `class="panel card"` on both the `<section>` and the fallback `<p>` — this consolidates `.panel`'s chrome into the shared class in the same step, since both are edited here anyway.)

- [ ] **Step 2: Add `.page-stack`, consolidate `.panel`, zero `.block`'s own margin**

Find (in `<style scoped>`):
```css
.block {
  margin: 1.5rem 0;
}
```
Replace with:
```css
.page-stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.block {
  margin: 0;
}
```

Find:
```css
.panel {
  padding: 1.25rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
  box-shadow: var(--elevation-1);
}
```
Replace with:
```css
.panel {
  padding: 1.25rem;
}
```

- [ ] **Step 3: Bump `.head__name` to match Dispatch's confidence**

Find:
```css
.head__name {
  margin: 0;
  max-width: 26ch;
  font-size: clamp(2rem, 3.5vw, 3.15rem);
  line-height: 1;
  letter-spacing: -0.04em;
  text-wrap: balance;
}
```
Replace with:
```css
.head__name {
  margin: 0;
  max-width: 26ch;
  font-size: clamp(2rem, 4vw, 3.7rem);
  line-height: 1;
  letter-spacing: -0.04em;
  text-wrap: balance;
}
```

- [ ] **Step 4: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 5: Manual verification**

Run `npm run dev`, open a `/site/:siteId` page with the fullest data (sub-site, thermal, vision, hypothesis all present). Confirm: all 9 content blocks now sit with one consistent gap between them (no doubled-up spacing, no blocks touching), the explainability panel's chrome is unchanged in appearance (its rule was already identical to `.card`'s), and the page title is now visibly bigger/bolder, matching Dispatch's H1 weight.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/views/SiteDetailView.vue
git commit -m "feat(web): add .page-stack rhythm and consolidate .panel into shared .card on Site Detail"
```

---

### Task 6: `DispatchView.vue` — entrance stagger on signal tiles and the priority queue

**Files:**
- Modify: `apps/web/src/views/DispatchView.vue`

**Interfaces:**
- Consumes: `.stagger-in` (Task 1).

- [ ] **Step 1: Add `.stagger-in` to the 4 signal-strip tiles**

Find each of the 4 `<article class="signal ...">` elements in the `#fleet-signals` section (their exact variant classes: `signal signal--primary` appears once, `signal signal--healthy` appears once, and there are two more with just `signal` — read the surrounding template to confirm the other two tiles' exact current class attributes before editing, since only the tile's `class` attribute changes, nothing else). Add `stagger-in` to each of the 4 tiles' existing `class` attribute (e.g. `class="signal signal--primary"` → `class="signal signal--primary stagger-in"`).

- [ ] **Step 2: Stagger the 4 tiles via `nth-child`**

Find, in `<style scoped>`, the existing `.signal-strip` rule, and add immediately after it:

```css
.signal-strip .signal:nth-child(1) {
  animation-delay: 0ms;
}
.signal-strip .signal:nth-child(2) {
  animation-delay: 40ms;
}
.signal-strip .signal:nth-child(3) {
  animation-delay: 80ms;
}
.signal-strip .signal:nth-child(4) {
  animation-delay: 120ms;
}
```

- [ ] **Step 3: Stagger the priority queue by v-for index**

Find:
```html
            <li v-for="site in orderedAttentionSites" :key="site.site_id">
```
Replace with:
```html
            <li
              v-for="(site, index) in orderedAttentionSites"
              :key="site.site_id"
              class="stagger-in"
              :style="{ animationDelay: `${Math.min(index, 8) * 30}ms` }"
            >
```

(The `Math.min(index, 8)` cap keeps the delay from growing unboundedly on a long list — nothing past the 9th item waits longer than the 8th did.)

- [ ] **Step 4: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 5: Manual verification**

Run `npm run dev`, open `/` with a hard refresh. Confirm the 4 signal tiles and the priority queue's list items fade/lift in with a visible stagger on load. Enable `prefers-reduced-motion: reduce` in DevTools' Rendering tab and hard-refresh again — confirm everything appears instantly, no animation.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/views/DispatchView.vue
git commit -m "feat(web): add staggered entrance motion to Dispatch signal tiles and priority queue"
```

---

### Task 7: `FleetHealthView.vue` — entrance stagger + headline-tile dominance

**Files:**
- Modify: `apps/web/src/views/FleetHealthView.vue`

**Interfaces:**
- Consumes: `.stagger-in` (Task 1), `--surface-selected` (existing token, already used for Tier 1's mobile nav active-state).

- [ ] **Step 1: Add `.stagger-in` to both tile groups**

Find:
```html
      <section class="tiles">
```
This section's tiles (`.tile`/`.tile--primary` elements inside it) each need `stagger-in` added to their existing `class` attribute — read the template to find each tile's exact current classes within both `<section class="tiles">` and `<section class="tiles tiles--secondary">`, and add `stagger-in` to each one's `class` list.

- [ ] **Step 2: Stagger both groups via `nth-child`, scoped per group**

Find, in `<style scoped>`, the existing `.tiles` rule, and add immediately after it:

```css
.tiles .tile:nth-child(1) {
  animation-delay: 0ms;
}
.tiles .tile:nth-child(2) {
  animation-delay: 40ms;
}
.tiles .tile:nth-child(3) {
  animation-delay: 80ms;
}
.tiles .tile:nth-child(4) {
  animation-delay: 120ms;
}
```

(This selector is scoped to `.tiles .tile`, so it applies independently within both `.tiles` and `.tiles.tiles--secondary` — each group's tiles stagger from 0ms again when they enter, which is correct since they're in different sections of the page, not one continuous list.)

- [ ] **Step 3: Give the two `tile--primary` tiles a visible weight bump**

Find:
```css
.tile--primary .tile__value {
  color: var(--action-text);
}
```
Replace with:
```css
.tile--primary {
  padding: 0.6rem 1rem 0.6rem 0.85rem;
  background: var(--surface-selected);
  border-radius: var(--radius-sm);
}

.tile--primary .tile__value {
  color: var(--action-text);
}
```

- [ ] **Step 4: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 5: Manual verification**

Run `npm run dev`, open `/fleet-health` with a hard refresh. Confirm tiles fade/lift in with a stagger, and the two primary tiles ("trips avoided," "saving") now sit on a visible light-amber background distinguishing them from the six secondary tiles. Confirm `prefers-reduced-motion: reduce` disables the entrance animation.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/views/FleetHealthView.vue
git commit -m "feat(web): add entrance motion and headline-tile weight to Fleet Health"
```

---

### Task 8: `WorkOrderView.vue` — title weight and section rhythm (print-safe)

**Files:**
- Modify: `apps/web/src/views/WorkOrderView.vue`

**Interfaces:**
- Consumes: existing tokens only. No new class from Task 1 is used here (Work Order's `.card` stays a print-document root, not a `.card`-class consumer, per the Global Constraints).

- [ ] **Step 1: Bump the title — flat rem increase, no `clamp`/`vw`**

Find:
```css
.card__title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
```
Replace with:
```css
.card__title {
  margin: 0;
  font-size: 1.85rem;
  font-weight: 650;
  line-height: 1.15;
  letter-spacing: -0.02em;
}
```

(A flat `rem` value, not a `clamp()`/`vw`-based one like the other three screens — this element is rendered inside `.print-doc`, and `vw` units resolve against the print page's viewport, which behaves inconsistently across browsers' print engines. A fixed `rem` size prints exactly as it renders on screen. `1.85rem` is a real but modest increase from `1.5rem` — appropriate for a document title, not a marketing hero headline.)

- [ ] **Step 2: Verify no `@media print` rule overrides `.card__title`**

Search `WorkOrderView.vue`'s `@media print` block (around line 1942 onward) for any `.card__title` rule. There should be none (the print styles only target `.card`, `.no-print`, `.print-doc*`, `break-inside`, and a handful of other selectors — `.card__title` inherits its screen size into print, which is correct and matches the plan's intent of a print-safe change). If one exists, stop and report — do not silently change print-only behavior.

- [ ] **Step 3: Loosen the vertical rhythm between `.section` blocks slightly**

Find the base `.section` rule's `margin-top`/`padding-top` values (search for `.section {` in the `<style scoped>` block — read the surrounding rule fully first, since this selector also carries the `border-top` divider and the `counter-increment` for numbering). Increase its top spacing by roughly 30-40% over its current value using the existing `--space-*` scale (e.g. if the current value is `1.5rem`, replace it with `var(--space-lg)` at `2rem` — pick the closest token to a genuine ~30-40% increase over whatever the actual current value turns out to be, do not invent a new arbitrary value). Do not touch the `border-top`, `counter-increment`, `break-inside`, or any other property in that rule — only the spacing value.

- [ ] **Step 4: Build**

Run: `npm run build`
Expected: builds cleanly.

- [ ] **Step 5: Manual verification — screen AND print**

Run `npm run dev`, open any `/site/:siteId/work-order` page.
- **Screen**: confirm the document title is visibly larger/bolder, and the numbered sections have slightly more breathing room between them without looking sparse.
- **Print**: open the browser's print preview (Ctrl/Cmd+P) or print-to-PDF. Confirm the repeating letterhead header/footer still appears on each page, the title still renders at its new size without overflowing or wrapping oddly, no floating-card shadow appears anywhere in the printed output, and `break-inside: avoid` still keeps each section from splitting across a page boundary.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/views/WorkOrderView.vue
git commit -m "feat(web): give Work Order's title real weight and loosen section rhythm, print-safe"
```

---

## Self-Review

**Spec coverage:**
1. `.card`/`.card--dark`/`.card--interactive` primitives — Task 1. ✅
2. Card-chrome adoption across all 9 Site Detail blocks (4 older + 3 newer light + 2 dark + `.panel`) — Tasks 2, 3, 4, 5. ✅
3. `.page-stack` rhythm using `--space-lg` — Task 5. ✅
4. Typography confidence — Task 5 (Site Detail) and Task 8 (Work Order). Fleet Health is explicitly OMITTED: verified during planning that `.head__title` already uses the identical `clamp(2rem, 4vw, 3.7rem)` scale as Dispatch, so the spec's blanket "Site Detail/Fleet Health/Work Order" framing is corrected here to the two screens that actually needed it.
5. Shared entrance-stagger motion on Dispatch and Fleet Health — Tasks 6, 7. ✅
6. Fleet Health headline-tile dominance — Task 7 Step 3. ✅
7. Work Order rhythm polish, print-safe — Task 8. ✅
8. Nav rail hover-lift — explicitly out of scope per the spec's own "lowest priority... if implementation time allows" framing; omitted from this plan given the deadline. Not silently dropped: recorded here for visibility.

**Placeholder scan:** every step carries literal before/after code and exact commands, except Task 6 Step 1, Task 7 Step 1, and Task 8 Step 3, which each instruct reading a short, specific span of the file to confirm exact current text before a small, precisely-described edit (adding one class name to a handful of elements; adjusting one spacing value using the existing token scale) — this is deliberate, not a placeholder: the plan was written from real reads of every other touched line, but these three spans are short enough and mechanical enough that prescribing exact line text here would have required pasting content already fully described in the step's own instructions with no ambiguity left in what to do.

**Type consistency:** `.card`/`.card--dark`/`.card--interactive`/`.stagger-in` are defined once in Task 1 and referenced by the identical names in every consuming task. `--space-lg` is consumed in Task 5 exactly as it was defined in the (separate, already-merged) Tier 1 plan — no renaming drift.

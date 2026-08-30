# Fleet Health UI Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface `trip_groups[]` and `cohorts[]` (already in the frozen `dispatch.json` schema but never rendered) on Screen 4 (`FleetHealthView.vue`), make its risk-by-site rows clickable, and polish loading/accessibility/responsive behavior.

**Architecture:** All logic additions are pure selector functions added to `apps/web/src/services/api.ts`'s existing "Selectors" section (the codebase's established single place for reshaping dispatch data, per its own header comment and the precedent of `isAssessed`/`cohortLines`/`findCohort`). `FleetHealthView.vue` calls these selectors from new `computed()` properties and renders two new sections plus small edits to two existing ones. No pipeline, schema, or route changes.

**Tech Stack:** Vue 3 `<script setup lang="ts">`, Vitest + `@vue/test-utils` (installed but unused so far — this codebase tests pure `.ts` selector modules directly, e.g. `components/fleetBasemap.spec.ts`, `services/httpError.spec.ts`; no component-mount tests exist yet, so this plan follows that precedent rather than introducing one), CSS custom properties from `apps/web/src/assets/theme.css`.

**Spec:** `docs/superpowers/specs/2026-08-30-fleet-health-ui-pass-design.md`

## Global Constraints

- No change to `pipeline/`, `docs/Schema.md`, `apps/web/src/types/dispatch.ts`, or `apps/web/src/router/index.ts`. Every field used here already exists in the frozen schema.
- No ECharts on this screen — stays in this page's existing hand-rolled CSS bar/tile idiom, matching `DispatchView.vue`.
- Site navigation uses the existing pattern: `{ name: 'site-detail', params: { siteId } }` (see `DispatchView.vue:126`, `components/SiteSearch.vue:37`). `RouterLink` needs no import — it's registered globally by `app.use(router)` in `main.ts`.
- New reshaping logic goes in `services/api.ts`'s Selectors section, never inline in the component — matches that section's own stated rule ("Reshaping lives here, never in components").
- Colors/spacing/radii come from existing CSS custom properties already used elsewhere in this file (`--status-good`, `--status-critical`, `--action-fill`, `--action-text`, `--border-hairline`, `--page-plane`, `--radius-sm`, `--radius-md`, `--text-muted`, `--text-secondary`) — no new hard-coded colors.
- Respect `prefers-reduced-motion: reduce` on any new animation (the skeleton shimmer).
- Test commands use `vitest run` explicitly (`npm run test:unit -- run <path>`) so they execute once rather than entering watch mode.

---

### Task 1: `sortedTripGroups` selector

**Files:**
- Modify: `apps/web/src/services/api.ts`
- Create: `apps/web/src/services/api.spec.ts`

**Interfaces:**
- Consumes: `TripGroup` from `@/types/dispatch` (`trip_id: string`, `label: string`, `site_ids: string[]`, `site_count: number`, `dispatched: boolean`)
- Produces: `export function sortedTripGroups(groups: TripGroup[]): TripGroup[]` — multi-site groups first, does not mutate its input.

- [ ] **Step 1: Write the failing test**

Create `apps/web/src/services/api.spec.ts`:

```ts
import { describe, expect, it } from 'vitest'

import { sortedTripGroups } from './api'
import type { TripGroup } from '@/types/dispatch'

function group(overrides: Partial<TripGroup>): TripGroup {
  return {
    trip_id: 'T-00',
    label: 'Test City',
    site_ids: ['S-0001'],
    site_count: 1,
    dispatched: false,
    ...overrides,
  }
}

describe('sortedTripGroups', () => {
  it('orders multi-site groups before single-site groups', () => {
    const groups = [
      group({ trip_id: 'T-01', site_count: 1 }),
      group({ trip_id: 'T-02', site_count: 5 }),
      group({ trip_id: 'T-03', site_count: 2 }),
    ]

    const sorted = sortedTripGroups(groups)

    expect(sorted.map((g) => g.trip_id)).toEqual(['T-02', 'T-03', 'T-01'])
  })

  it('does not mutate the input array', () => {
    const groups = [
      group({ trip_id: 'T-01', site_count: 1 }),
      group({ trip_id: 'T-02', site_count: 5 }),
    ]
    const original = [...groups]

    sortedTripGroups(groups)

    expect(groups).toEqual(original)
  })

  it('returns an empty array for an empty input', () => {
    expect(sortedTripGroups([])).toEqual([])
  })
})
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `npm run test:unit -- run src/services/api.spec.ts` (from `apps/web/`)
Expected: FAIL — `sortedTripGroups` is not exported from `./api`.

- [ ] **Step 3: Implement the selector**

In `apps/web/src/services/api.ts`, add `TripGroup` to the type-only import at the top of the file:

```ts
import type { Dispatch, Site, Cohort, CohortSeriesRow, SiteStatus, TripGroup } from '@/types/dispatch'
```

Then add this function in the `// --- Selectors ---` section, directly after `cohortLines` (before the `// --- Formatting ---` divider):

```ts
/**
 * Trip groups ranked by how many sites they cover. Multi-site groups are the
 * concrete evidence behind "trips avoided" — a technician reaching five roofs
 * in one visit is a more persuasive fact than a headline number, so it sorts
 * first.
 */
export function sortedTripGroups(groups: TripGroup[]): TripGroup[] {
  return [...groups].sort((a, b) => b.site_count - a.site_count)
}
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `npm run test:unit -- run src/services/api.spec.ts`
Expected: PASS — 3 tests.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/services/api.ts apps/web/src/services/api.spec.ts
git commit -m "feat(web): add sortedTripGroups selector for Fleet Health"
```

---

### Task 2: `cohortCoverage` selector

**Files:**
- Modify: `apps/web/src/services/api.ts`
- Modify: `apps/web/src/services/api.spec.ts`

**Interfaces:**
- Consumes: `Cohort[]`, `Site[]` from `@/types/dispatch`; `Site.excluded_from_analysis?.reason`
- Produces:
  ```ts
  export interface CohortCoverageRow {
    cohortId: string
    label: string
    memberCount: number
    analysedCount: number
    meetsMinimum: boolean
    dataStatus: DataStatus
    excludedSites: Array<{ siteId: string; name: string; reason: string }>
  }
  export function cohortCoverage(cohorts: Cohort[], sites: Site[]): CohortCoverageRow[]
  ```

- [ ] **Step 1: Write the failing test**

Add to `apps/web/src/services/api.spec.ts` — extend the top import and append a new `describe` block:

```ts
import { describe, expect, it } from 'vitest'

import { cohortCoverage, sortedTripGroups } from './api'
import type { Cohort, Site, TripGroup } from '@/types/dispatch'
```

```ts
function makeCohort(overrides: Partial<Cohort>): Cohort {
  return {
    cohort_id: 'C-00',
    label: 'Test Cohort',
    member_site_ids: ['S-0001'],
    member_count: 1,
    analysed_site_ids: ['S-0001'],
    analysed_count: 1,
    excluded_site_ids: [],
    meets_minimum: true,
    clustering_method: 'koppen_then_haversine',
    data_status: 'BUILT',
    ...overrides,
  }
}

function makeSite(overrides: Partial<Site>): Site {
  return {
    site_id: 'S-0000',
    name: 'Test Site',
    address: '1 Test Way',
    capacity_kwp: 100,
    lat: 0,
    lon: 0,
    cohort_id: 'C-00',
    tariff_rm_per_kwh: 0.5,
    source_system_id: '0000',
    status: 'healthy',
    rank: null,
    data_status: 'BUILT',
    ...overrides,
  }
}

describe('cohortCoverage', () => {
  it('reports analysed and member counts per cohort', () => {
    const cohorts = [
      makeCohort({
        cohort_id: 'C-01',
        member_count: 6,
        analysed_count: 5,
        excluded_site_ids: ['S-9999'],
      }),
    ]
    const sites = [makeSite({ site_id: 'S-9999', name: 'Excluded Site' })]

    const rows = cohortCoverage(cohorts, sites)

    expect(rows).toHaveLength(1)
    expect(rows[0]).toMatchObject({
      cohortId: 'C-01',
      memberCount: 6,
      analysedCount: 5,
      meetsMinimum: true,
    })
  })

  it('names excluded sites and their reason from excluded_from_analysis', () => {
    const cohorts = [makeCohort({ excluded_site_ids: ['S-9999'] })]
    const sites = [
      makeSite({
        site_id: 'S-9999',
        name: 'Henderson NV 6',
        excluded_from_analysis: {
          excluded: true,
          reason: 'Insufficient telemetry coverage',
          detail: 'Fewer than the minimum required days of generation data.',
          observed_performance_index: 1.11,
          reference_performance_index: 3.83,
          threshold: 0.5,
          method: 'coverage_ratio',
          data_status: 'BUILT',
        },
      }),
    ]

    const rows = cohortCoverage(cohorts, sites)

    expect(rows[0].excludedSites).toEqual([
      { siteId: 'S-9999', name: 'Henderson NV 6', reason: 'Insufficient telemetry coverage' },
    ])
  })

  it('falls back to a generic reason when a site carries no excluded_from_analysis detail', () => {
    const cohorts = [makeCohort({ excluded_site_ids: ['S-9999'] })]
    const sites = [makeSite({ site_id: 'S-9999', name: 'Untracked Site' })]

    const rows = cohortCoverage(cohorts, sites)

    expect(rows[0].excludedSites[0].reason).toBe('Excluded from peer analysis')
  })

  it('returns an empty excludedSites array when a cohort excludes nobody', () => {
    const cohorts = [makeCohort({ excluded_site_ids: [] })]

    const rows = cohortCoverage(cohorts, [])

    expect(rows[0].excludedSites).toEqual([])
  })
})
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `npm run test:unit -- run src/services/api.spec.ts`
Expected: FAIL — `cohortCoverage` is not exported from `./api`.

- [ ] **Step 3: Implement the selector**

In `apps/web/src/services/api.ts`, add `DataStatus` to the same type-only import updated in Task 1:

```ts
import type {
  Dispatch,
  Site,
  Cohort,
  CohortSeriesRow,
  SiteStatus,
  TripGroup,
  DataStatus,
} from '@/types/dispatch'
```

Add directly after `sortedTripGroups`:

```ts
export interface CohortCoverageRow {
  cohortId: string
  label: string
  memberCount: number
  analysedCount: number
  meetsMinimum: boolean
  dataStatus: DataStatus
  excludedSites: Array<{ siteId: string; name: string; reason: string }>
}

/**
 * Per-cohort analysis coverage — the Scalability rubric's "gets more accurate
 * as the fleet grows" claim, shown with real numbers instead of asserted in a
 * deck. A cohort excluding a site names it and why, rather than silently
 * shrinking `analysed_count` with no explanation on screen.
 */
export function cohortCoverage(cohorts: Cohort[], sites: Site[]): CohortCoverageRow[] {
  const siteById = new Map(sites.map((site) => [site.site_id, site]))

  return cohorts.map((cohort) => ({
    cohortId: cohort.cohort_id,
    label: cohort.label,
    memberCount: cohort.member_count,
    analysedCount: cohort.analysed_count,
    meetsMinimum: cohort.meets_minimum,
    dataStatus: cohort.data_status,
    excludedSites: cohort.excluded_site_ids.map((siteId) => {
      const site = siteById.get(siteId)
      return {
        siteId,
        name: site?.name ?? siteId,
        reason: site?.excluded_from_analysis?.reason ?? 'Excluded from peer analysis',
      }
    }),
  }))
}
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `npm run test:unit -- run src/services/api.spec.ts`
Expected: PASS — 7 tests total (3 from Task 1, 4 new).

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/services/api.ts apps/web/src/services/api.spec.ts
git commit -m "feat(web): add cohortCoverage selector for Fleet Health"
```

---

### Task 3: Render the trip-groups section

**Files:**
- Modify: `apps/web/src/views/FleetHealthView.vue`

**Interfaces:**
- Consumes: `sortedTripGroups` from `@/services/api` (Task 1); `dispatch.value.fleet_summary.trip_groups`; `assumptions.value.same_trip_radius_km`
- Produces: `tripGroups` computed, consumed by this task's own template only.

- [ ] **Step 1: Add the import and computed property**

In the `<script setup>` import line, add `sortedTripGroups`:

```ts
import { loadDispatch, formatRinggit, isAssessed, sortedTripGroups } from '@/services/api'
```

Add this computed after `assumptionRows` (the last computed in the file, just before `</script>`):

```ts
/** Trip groups ranked by how many sites they cover — see sortedTripGroups. */
const tripGroups = computed(() => sortedTripGroups(dispatch.value?.fleet_summary.trip_groups ?? []))
```

- [ ] **Step 2: Insert the template section**

In the `<template>`, insert this new `<section>` immediately after the fleet-split section's closing `</section>` (the one with `<h2 class="chart__title">Where the fleet sits this month</h2>`) and before `<section v-if="roi.projection" class="projection">`:

```html
<!-- Trip groups make "N trips avoided" concrete: which sites, reached together. -->
<section v-if="tripGroups.length" class="chart">
  <h2 class="chart__title">How the fleet groups into visits</h2>
  <ul class="trips">
    <li v-for="group in tripGroups" :key="group.trip_id" class="trips__row">
      <span class="trips__label">{{ group.label }}</span>
      <span class="trips__chip" :class="{ 'trips__chip--multi': group.site_count > 1 }">
        {{ group.site_count }} site{{ group.site_count === 1 ? '' : 's' }}, 1 visit
      </span>
      <span v-if="group.dispatched" class="trips__tag">dispatched — not counted as avoided</span>
    </li>
  </ul>
  <p class="chart__note">
    Sites within {{ assumptions?.same_trip_radius_km }} km are reached in one mobilisation. A
    group already carrying a dispatched site is not counted as avoided — the technician is going
    there regardless, so skipping its neighbours saves the drive, not the visit.
  </p>
</section>
```

- [ ] **Step 3: Add styles**

Add to the `<style scoped>` block, after the existing `.chart__note` rule (keeping the file's "Charts" section grouping):

```css
.trips {
  list-style: none;
  margin: 0;
  padding: 0;
}

.trips__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-hairline);
  font-size: 0.82rem;
}

.trips__row:last-child {
  border-bottom: none;
}

.trips__label {
  flex: 1 1 auto;
  min-width: 10rem;
  color: var(--text-secondary);
}

.trips__chip {
  flex: none;
  padding: 0.2em 0.6em;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-hairline);
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-muted);
}

/* Multi-site groups are the persuasive case — the same accent already
   reserved for the two headline "trips avoided / saving" tiles. */
.trips__chip--multi {
  border-color: var(--action-fill);
  color: var(--action-text);
}

.trips__tag {
  flex: none;
  font-size: 0.7rem;
  color: var(--text-muted);
}
```

- [ ] **Step 4: Type-check and build**

Run: `npm run build` (from `apps/web/`)
Expected: builds with no TypeScript errors.

- [ ] **Step 5: Manual verification against real data**

Run: `npm run dev`, open `/fleet-health`. Confirm:
- A "How the fleet groups into visits" section appears between the fleet-split bar and the "If this month repeats" projection box.
- Against the committed `pipeline/output/dispatch.json`, the first row is "Las Vegas, NV" with a highlighted "5 sites, 1 visit" chip; five more rows follow for the single-site trip groups.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/views/FleetHealthView.vue
git commit -m "feat(web): render trip-groups section on Fleet Health"
```

---

### Task 4: Render the cohort-coverage panel, side-by-side with Assumptions

**Files:**
- Modify: `apps/web/src/views/FleetHealthView.vue`

**Interfaces:**
- Consumes: `cohortCoverage` from `@/services/api` (Task 2); `DataStatusBadge` (already imported); `dispatch.value.cohorts`, `dispatch.value.sites`
- Produces: `cohortRows` computed, consumed by this task's own template only.

- [ ] **Step 1: Add the import and computed property**

Update the same import line touched in Task 3:

```ts
import { loadDispatch, formatRinggit, isAssessed, sortedTripGroups, cohortCoverage } from '@/services/api'
```

Add after the `tripGroups` computed added in Task 3:

```ts
/** Per-cohort analysis coverage — see cohortCoverage. */
const cohortRows = computed(() =>
  dispatch.value ? cohortCoverage(dispatch.value.cohorts, dispatch.value.sites) : [],
)
```

- [ ] **Step 2: Wrap the Assumptions section in a two-column panel and add the cohort panel beside it**

Find the existing Assumptions section:

```html
<!-- Every constant, its value, and where it came from. -->
<section class="assumptions">
```

Replace the opening through its matching `</section>` with the same content wrapped in a new `.panels` container, with a new cohort-coverage section as its first child. The full replacement:

```html
<div class="panels">
  <!-- Per-cohort analysis coverage — the Scalability claim, shown with real numbers. -->
  <section v-if="cohortRows.length" class="chart panels__item">
    <h2 class="chart__title">Cohort coverage</h2>
    <ul class="cohorts">
      <li v-for="cohort in cohortRows" :key="cohort.cohortId" class="cohorts__card">
        <div class="cohorts__head">
          <span class="cohorts__label">{{ cohort.label }}</span>
          <DataStatusBadge :status="cohort.dataStatus" small />
        </div>
        <p class="cohorts__count">
          {{ cohort.analysedCount }} of {{ cohort.memberCount }} sites analysed
        </p>
        <span
          class="cohorts__chip"
          :class="cohort.meetsMinimum ? 'cohorts__chip--good' : 'cohorts__chip--critical'"
        >
          {{ cohort.meetsMinimum ? 'meets minimum' : 'below minimum' }}
        </span>
        <p v-if="cohort.excludedSites.length" class="cohorts__excluded">
          Excluded from peer analysis:
          <span v-for="(site, index) in cohort.excludedSites" :key="site.siteId">
            {{ site.name }} ({{ site.reason }})<template
              v-if="index < cohort.excludedSites.length - 1"
              >, </template
            >
          </span>
        </p>
      </li>
    </ul>
    <p class="chart__note">
      Peer benchmarking's accuracy grows with cohort size — a cohort below its minimum member
      count still runs, but with less statistical confidence.
    </p>
  </section>

  <!-- Every constant, its value, and where it came from. -->
  <section class="assumptions panels__item">
    <h2 class="assumptions__title">Assumptions</h2>
    <p class="assumptions__lead">
      Read directly from <code>config/assumptions.json</code>, not hardcoded here.
      {{ assumptions?.tier }}
    </p>

    <table class="table">
      <thead>
        <tr>
          <th>Constant</th>
          <th class="table__num">Value</th>
          <th class="table__num">Range</th>
          <th>Source / rationale</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in assumptionRows" :key="row.key">
          <td>
            <code>{{ row.key }}</code>
          </td>
          <td class="table__num">{{ row.value }}</td>
          <td class="table__num">
            <template v-if="row.range">{{ row.range.low }} – {{ row.range.high }}</template>
            <template v-else>—</template>
          </td>
          <td class="table__note">{{ row.note || '—' }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</div>
```

- [ ] **Step 3: Add styles**

Adjust the existing `.assumptions` rule to drop its own top margin (the wrapping `.panels` container now controls that spacing), then add the new rules. Change:

```css
.assumptions {
  margin-top: 2.5rem;
  padding: 1.25rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
```

to:

```css
.assumptions {
  padding: 1.25rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
```

Then add, near the other section-level rules (after the `.chart` rules is a reasonable spot):

```css
.panels {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  margin-top: 2.5rem;
}

@media (min-width: 900px) {
  .panels {
    grid-template-columns: 1fr 1fr;
    align-items: start;
  }
}

.panels__item {
  margin-top: 0;
}

.cohorts {
  list-style: none;
  margin: 0 0 0.5rem;
  padding: 0;
  display: grid;
  gap: 0.9rem;
}

.cohorts__card {
  padding: 0.85rem 0.95rem;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  background: var(--page-plane);
}

.cohorts__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
}

.cohorts__label {
  font-weight: 600;
  font-size: 0.85rem;
}

.cohorts__count {
  margin: 0.35rem 0;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.cohorts__chip {
  display: inline-block;
  padding: 0.15em 0.55em;
  border-radius: var(--radius-sm);
  border: 1px solid currentColor;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.cohorts__chip--good {
  color: var(--status-good);
}

.cohorts__chip--critical {
  color: var(--status-critical);
}

.cohorts__excluded {
  margin: 0.5rem 0 0;
  font-size: 0.74rem;
  line-height: 1.5;
  color: var(--text-muted);
}
```

- [ ] **Step 4: Type-check and build**

Run: `npm run build`
Expected: builds with no TypeScript errors.

- [ ] **Step 5: Manual verification against real data**

Run: `npm run dev`, open `/fleet-health`, resize the window. Confirm:
- Below ~900px width, "Cohort coverage" stacks above "Assumptions", full width.
- At ≥900px, the two sit side by side.
- Against the committed `dispatch.json`: two cards render — "Mid-Atlantic distributed cluster" (5 of 5 analysed, meets minimum, no excluded line) and "Greater Las Vegas cluster" (5 of 6 analysed, meets minimum, one excluded-site line naming the Henderson site).

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/views/FleetHealthView.vue
git commit -m "feat(web): render cohort-coverage panel beside Assumptions on Fleet Health"
```

---

### Task 5: Clickable site rows in "Money at risk by site"

**Files:**
- Modify: `apps/web/src/views/FleetHealthView.vue`

**Interfaces:**
- Consumes: `riskBySite` (existing computed, already carries `siteId`); the `{ name: 'site-detail', params: { siteId } }` route from `router/index.ts`.
- Produces: none — this task is presentation-only, consumed by nothing downstream.

- [ ] **Step 1: Replace the plain label with a RouterLink**

Find in the template:

```html
<span class="bars__label">{{ item.name }}</span>
```

Replace with:

```html
<RouterLink :to="{ name: 'site-detail', params: { siteId: item.siteId } }" class="bars__label">
  {{ item.name }}
</RouterLink>
```

- [ ] **Step 2: Add interactive styles**

Find the existing `.bars__label` rule:

```css
.bars__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}
```

Replace with:

```css
.bars__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
  text-decoration: none;
}

.bars__label:hover,
.bars__label:focus-visible {
  color: var(--action-text);
  text-decoration: underline;
}

.bars__label:focus-visible {
  outline: 2px solid var(--action-text);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}
```

- [ ] **Step 3: Type-check and build**

Run: `npm run build`
Expected: builds with no TypeScript errors (`RouterLink` resolves globally via `app.use(router)` in `main.ts`, no import needed — same as `SiteDetailView.vue` and `WorkOrderView.vue`).

- [ ] **Step 4: Manual verification**

Run: `npm run dev`, open `/fleet-health`, click a site name under "Money at risk by site". Confirm it navigates to `/site/<that siteId>` and shows that site's detail page. Tab to a row with the keyboard and confirm a visible focus outline appears before activating it.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/views/FleetHealthView.vue
git commit -m "feat(web): make Fleet Health risk-by-site rows clickable"
```

---

### Task 6: Loading skeleton

**Files:**
- Modify: `apps/web/src/views/FleetHealthView.vue`

**Interfaces:**
- Consumes: existing `isLoading` ref.
- Produces: none.

- [ ] **Step 1: Replace the bare loading text**

Find:

```html
<p v-if="isLoading">Loading…</p>
```

Replace with:

```html
<div v-if="isLoading" class="skeleton" aria-busy="true" aria-live="polite">
  <span class="sr-only">Loading fleet health…</span>
  <div class="skeleton__block skeleton__block--header"></div>
  <div class="skeleton__block skeleton__block--case"></div>
  <div class="skeleton__row">
    <div v-for="n in 4" :key="n" class="skeleton__block skeleton__block--tile"></div>
  </div>
  <div class="skeleton__block skeleton__block--chart"></div>
</div>
```

- [ ] **Step 2: Add styles**

Add to the end of the `<style scoped>` block:

```css
.skeleton {
  padding-top: 1.5rem;
}

.skeleton__row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1px;
  margin-top: 1.5rem;
}

.skeleton__block {
  border-radius: var(--radius-md);
  background: linear-gradient(
    100deg,
    var(--page-plane) 40%,
    var(--border-hairline) 50%,
    var(--page-plane) 60%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.6s ease-in-out infinite;
}

.skeleton__block--header {
  height: 3.5rem;
  max-width: 26rem;
}

.skeleton__block--case {
  height: 3.25rem;
  margin-top: 1.25rem;
}

.skeleton__block--tile {
  height: 4.5rem;
}

.skeleton__block--chart {
  height: 10rem;
  margin-top: 1.75rem;
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton__block {
    animation: none;
    background: var(--page-plane);
  }
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

- [ ] **Step 3: Type-check and build**

Run: `npm run build`
Expected: builds with no TypeScript errors.

- [ ] **Step 4: Manual verification**

Run: `npm run dev`, open Chrome DevTools → Network tab → set throttling to "Slow 3G", then hard-reload `/fleet-health`. Confirm the skeleton renders (four tile-shaped blocks, a header bar, a case-toggle bar, a chart-shaped block) with a shimmer, and that it disappears without a layout jump once data loads. Re-check with `prefers-reduced-motion: reduce` emulated in DevTools' Rendering tab — the shimmer should stop animating.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/views/FleetHealthView.vue
git commit -m "feat(web): add loading skeleton to Fleet Health view"
```

---

### Task 7: Accessible label on the fleet-split visual

**Files:**
- Modify: `apps/web/src/views/FleetHealthView.vue`

**Note on scope vs. the design doc:** the design doc's polish section proposed `aria-label`s on `.bars__fill` and `.split__part` individually. On inspection, `.bars__fill` is purely decorative — the site name and ringgit value beside it are already plain visible (and so screen-reader-accessible) text, so labelling it would be redundant. `.split__part`'s per-segment count is likewise already available as plain text in the `.split__legend` list directly below it. The one real gap: the `.split` element itself carries `role="img"` with a static `aria-label="Fleet split by triage status"` that names the chart but never states its numbers, so a screen-reader user gets a label with no data from that element (sighted users get the data from the adjacent legend, which has no non-visual equivalent tying it to the image role). This task fixes that one gap rather than adding redundant labels elsewhere.

**Interfaces:**
- Consumes: existing `statusSplit` computed.
- Produces: `splitAriaLabel` computed, consumed by this task's own template only.

- [ ] **Step 1: Add the computed property**

Add after the `statusSplit` computed:

```ts
/** Screen-reader text for the role="img" split — the legend beside it is visual-only. */
const splitAriaLabel = computed(
  () =>
    `Fleet split by triage status: ${statusSplit.value
      .map((part) => `${part.label} — ${part.count} sites`)
      .join(', ')}`,
)
```

- [ ] **Step 2: Use it in the template**

Find:

```html
<div class="split" role="img" aria-label="Fleet split by triage status">
```

Replace with:

```html
<div class="split" role="img" :aria-label="splitAriaLabel">
```

- [ ] **Step 3: Type-check and build**

Run: `npm run build`
Expected: builds with no TypeScript errors.

- [ ] **Step 4: Manual verification**

Run: `npm run dev`, open `/fleet-health`, inspect the `.split` element in DevTools' Accessibility pane (or a screen reader). Confirm its accessible name now reads the full breakdown, e.g. "Fleet split by triage status: Monitor — 2 sites, Healthy — 9 sites" against the committed `dispatch.json`, not just the static caption.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/views/FleetHealthView.vue
git commit -m "fix(web): give the Fleet Health split chart a data-bearing aria-label"
```

---

## Self-Review

**Spec coverage:**
1. Trip groups section — Task 3. ✅
2. Cohort coverage panel — Task 4. ✅
3. Clickable risk-by-site rows — Task 5. ✅
4. Excluded-from-analysis notice, folded into the cohort panel — Task 4 (`cohorts__excluded`). ✅
5. Polish — loading skeleton (Task 6), accessibility (Task 7, scope note explains the one deviation from the design doc's literal wording), responsive two-column layout (Task 4, Step 2–3). ✅

**Placeholder scan:** no TBDs; every step carries literal code and exact commands.

**Type consistency:** `TripGroup`/`sortedTripGroups` (Task 1) and `CohortCoverageRow`/`cohortCoverage` (Task 2) are defined once and consumed with the same names and shapes in Tasks 3–4. `item.siteId` (Task 5) matches the existing `riskBySite` computed's shape, unchanged by this plan.

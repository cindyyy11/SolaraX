# Fleet Health & ROI — Full UI/UX Pass

## Goal

Screen 4 (`apps/web/src/views/FleetHealthView.vue`) is the screen a P&L owner opens (PRD v2 §4).
Three facts already live in `dispatch.json` but never render on this screen: `trip_groups[]`,
`cohorts[]`, and per-cohort `excluded_site_ids`. Their absence leaves the screen's most persuasive
concrete fact — five Las Vegas roofs reached in one technician visit — as an abstract number
("6 trips avoided") instead of a named, visible list. The screen is also a dead end: a flagged
site's name in "Money at risk by site" is plain text with no way to act on it.

This pass adds four content sections and a polish pass, entirely by rendering fields the schema
already carries. It changes no field, no type, no pipeline output, and no route. It supports the
**Commercial Viability** (25%) and **Scalability** (15%) rubric rows directly — the cohort panel
is the Scalability claim ("gets more accurate as the fleet grows") shown with real numbers instead
of asserted in a deck.

## Non-goals

- No pipeline, schema, or `dispatch.json` change. `roi.data_status` stays `PLACEHOLDER` on the
  current artifact (owned by M4/C) — this pass renders whatever `DataStatusBadge` already does
  with that value; it does not fabricate a fix.
- No new route. Clickable site rows navigate to the existing `/site/:siteId` route.
- No ECharts. This screen's existing idiom is hand-rolled CSS bars/tiles (matching
  `DispatchView.vue`); ECharts stays scoped to `CohortChart.vue` on Screen 2, per the router
  comment explaining why that bundle is lazy-loaded there specifically.
- No fabricated conversion figures (e.g. "equivalent to N cars off the road" for the CO₂e tile) —
  nothing in `docs/RESEARCH.md` currently sources one, and CLAUDE.md's "cite or omit" rule governs.

## Architecture and data flow

All additions are new `computed()` properties in `FleetHealthView.vue`'s existing `<script
setup>`, reading from the `dispatch` ref already loaded via `loadDispatch()`. No new service call,
no new component file except where called out below. This keeps `pipeline/` and `apps/web/`
separated exactly as CLAUDE.md requires — the view adapts an existing artifact, nothing more.

### 1. Trip groups section

New `<section class="chart">` (reusing the existing chart-card class) placed after "Where the
fleet sits this month" and before "Money at risk by site" — trip economics is the direct
explanation of the money-at-risk numbers that follow it.

```ts
const tripGroups = computed(() => dispatch.value?.fleet_summary.trip_groups ?? [])
```

Renders as a list, one row per group: `label`, a site-count chip, and — for groups with
`site_count > 1` — a visually distinct "N sites, 1 visit" badge using the existing `--action-fill`
accent (the same color already reserved for the two headline "trips avoided / saving" tiles, so
the visual vocabulary for "this is the core claim" stays consistent across the page). Groups where
`dispatched: true` get a small muted tag ("dispatched — not counted as avoided") so the schema's
own rule (a group holding a dispatched site is not avoided) is visible, not just enforced upstream.

No sorting requested by the schema; sort by `site_count` descending so the multi-site groups (the
persuasive cases) surface first.

### 2. Cohort coverage panel

New `<section class="chart">` placed after the trip groups section (or side-by-side with the
Assumptions panel at wide viewports — see Responsive below).

```ts
const cohortRows = computed(() => {
  if (!dispatch.value) return []
  return dispatch.value.cohorts.map((cohort) => ({
    id: cohort.cohort_id,
    label: cohort.label,
    analysed: cohort.analysed_count,
    members: cohort.member_count,
    meetsMinimum: cohort.meets_minimum,
    excludedIds: cohort.excluded_site_ids,
    dataStatus: cohort.data_status,
  }))
})
```

One card per cohort: label, "`analysed`/`members` analysed" as text (not a bar — two small integers
don't need one), and a small text chip for `meets_minimum` — "meets minimum" in
`var(--status-good)` when true, "below minimum" in `var(--status-critical)` when false — styled
like `DataStatusBadge`'s outlined-chip idiom (border in `currentColor`, no fill) rather than a
`NoticeCallout`, since a per-card fact belongs in the card, not in a full alert block. Then,
only when `excludedIds.length > 0`, a line naming which sites and why unavailable via
`dispatch.value.sites.find(...)`'s `excluded_from_analysis.reason` if present on that site object,
falling back to a generic "excluded from peer analysis" if the site-level detail isn't populated.
This is where governance transparency (point 4 of the original ask) lives — no separate section.

A `DataStatusBadge :status="cohort.data_status" small` on each card, consistent with every other
data-bearing card on the page.

### 3. Clickable site rows in "Money at risk by site"

`riskBySite` already carries `siteId`. Wrap each row's label in a `RouterLink`:

```html
<RouterLink :to="{ name: 'site-detail', params: { siteId: item.siteId } }" class="bars__label">
  {{ item.name }}
</RouterLink>
```

Matching the `router.push({ name: 'site-detail', params: { siteId } })` pattern already used in
`DispatchView.vue` and `SiteSearch.vue`. `.bars__label` gets a focus-visible outline and hover
underline added to its existing style block — currently plain text, so this is a net-new
interactive affordance, not a restyle.

### 4. Excluded-from-analysis notice

Folded into the cohort panel (§2) rather than a fifth section — a separate block for the same fact
the cohort panel already names per-cohort would be redundant, and the design principle across this
page is one fact, one place.

### 5. Polish

- **Loading state.** Replace `<p v-if="isLoading">Loading…</p>` with a skeleton matching the
  shape of the tiles/sections below it (a few `<div class="skeleton">` blocks with a subtle
  shimmer, sized to roughly match `.tiles`, `.case`, and one `.chart` block) so there's no layout
  jump when data arrives. Respect `prefers-reduced-motion` on the shimmer.
- **Accessibility.** `.bars__fill` and `.split__part` currently expose their value only via a
  hover `title` attribute (unreliable for screen readers). Add `aria-label` on each with the full
  sentence already used in the `title`, and mark the bar container `role="list"` /
  each row `role="listitem"` where appropriate given they're already semantic `<li>`s inside a
  `<ul>` — verify no redundant ARIA is added where the native list semantics already cover it.
- **Responsive.** At viewports ≥ ~900px, the cohort panel (§2) and the existing Assumptions panel
  sit in a two-column CSS grid; below that width both stack full-width as today. This is the only
  layout structure change — every other new section stays single-column, matching the page's
  existing top-to-bottom narrative shape.

## Error handling

No new failure modes: every new computed property follows the existing pattern of guarding on
`dispatch.value` being non-null and defaulting to an empty array, so a missing or malformed
`cohorts`/`trip_groups` array renders an empty section rather than throwing. Given the frozen
schema and `validate_dispatch.py`'s existing checks, `trip_groups` and `cohorts` are already
required-shape guarantees on any artifact that passed validation — these guards are defensive
consistency with the rest of the file, not a response to an anticipated real failure.

## Testing

- `apps/web` unit/component tests (Vitest, per existing `*.spec.ts` convention) for the three new
  computed properties (`tripGroups` sort order, `cohortRows` shape including the
  zero-excluded-sites case, and that `riskBySite` items still carry `siteId` for the new link).
- Manual check against the committed `pipeline/output/dispatch.json` (11 sites, 2 cohorts, 6 trip
  groups, VEGAS-01 excluding S-1367) to confirm the multi-site trip group and the excluded-site
  line both render correctly on real data, not just a fixture.
- `npm run build` to confirm no type errors from the new `RouterLink` usage or computed properties.

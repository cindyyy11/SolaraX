<script setup lang="ts">
/**
 * Screen 1 — This Month's Dispatch List. The landing screen.
 *
 * PRD v2 section 4: a fleet map on the left, a ranked list on the right, and a
 * footer carrying visits avoided and estimated saving. The footer is not a
 * footnote — "the product's value is as much in the sites you don't visit as the
 * ones you do" — so it gets real visual weight.
 *
 * The map is a correctly-sized placeholder for now. When Leaflet lands, the five
 * Agassi sites share byte-identical coordinates and will stack: use
 * markercluster and let it spiderfy. Never jitter coordinates to fake separation.
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { TriangleAlert, Diamond, CircleCheck, CircleSlash, Clock } from '@lucide/vue'
import {
  loadDispatch,
  sitesByStatus,
  sitesNotAssessed,
  isAssessed,
  formatRinggit,
  formatCapacity,
} from '@/services/api'
import type { Dispatch, Site, SiteStatus } from '@/types/dispatch'
import DataStatusBadge from '@/components/DataStatusBadge.vue'
import FleetMap from '@/components/FleetMap.vue'
import NoticeCallout from '@/components/NoticeCallout.vue'

const router = useRouter()

/** Highlighted site, shared between the list and the map in both directions. */
const activeSiteId = ref<string | null>(null)

function openSite(siteId: string): void {
  router.push({ name: 'site-detail', params: { siteId } })
}

const dispatch = ref<Dispatch | null>(null)
const source = ref<'primary' | 'fallback' | null>(null)
const loadError = ref<string | null>(null)
const isLoading = ref(true)

onMounted(async () => {
  try {
    const result = await loadDispatch()
    dispatch.value = result.dispatch
    source.value = result.source
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : String(error)
  } finally {
    isLoading.value = false
  }
})

/**
 * "not_assessed" is a DISPLAY group, not a schema value. The artifact only has
 * three statuses (see isAssessed in services/api.ts for why), so an excluded
 * site arrives labelled healthy and is separated out here.
 */
type GroupKey = SiteStatus | 'not_assessed'

const GROUPS: Array<{ key: GroupKey; heading: string; note: string }> = [
  { key: 'dispatch', heading: 'Dispatch recommended', note: 'above the dispatch threshold' },
  { key: 'monitor', heading: 'Monitor', note: 'deviation detected, below dispatch threshold' },
  { key: 'healthy', heading: 'Healthy', note: 'within cohort tolerance' },
  { key: 'not_assessed', heading: 'Not assessed', note: 'telemetry too incomplete to rule on' },
]

const groups = computed(() => {
  if (!dispatch.value) return []
  const payload = dispatch.value as Dispatch
  return GROUPS.map((group) => ({
    ...group,
    sites:
      group.key === 'not_assessed'
        ? sitesNotAssessed(payload)
        : sitesByStatus(payload, group.key as SiteStatus),
  })).filter((group) => group.key !== 'not_assessed' || group.sites.length > 0)
})

/**
 * Screen 1's headline answer is currently "no site is worth a visit". That is a
 * RESULT, not a gap — PRD v2 section 4: "the product's value is as much in the
 * sites you don't visit as the ones you do" — but rendered as a bare empty list
 * it reads as broken data.
 *
 * So the empty state states the conclusion and shows the closest call, which is
 * the evidence that the threshold is doing work rather than nothing having been
 * detected. Never close this gap by lowering the threshold.
 */
const dispatchVerdict = computed(() => {
  if (!dispatch.value || !summary.value) return null
  if (summary.value.dispatch_count > 0) return null

  const threshold = dispatch.value.assumptions.dispatch_threshold_rm_per_month
  const contenders = dispatch.value.sites
    .filter((site) => site.economics && site.status !== 'dispatch')
    .sort(
      (a, b) =>
        (b.economics?.rm_at_risk_monthly ?? 0) - (a.economics?.rm_at_risk_monthly ?? 0),
    )

  const nearest = contenders[0]
  const nearestRm = nearest?.economics?.rm_at_risk_monthly ?? 0

  return {
    threshold,
    assessed: dispatch.value.sites.filter(isAssessed).length,
    nearest: nearest
      ? {
          name: nearest.name,
          siteId: nearest.site_id,
          rm: nearestRm,
          shortfall: threshold - nearestRm,
          percentOfThreshold: Math.round((nearestRm / threshold) * 100),
        }
      : null,
  }
})

const summary = computed(() => dispatch.value?.fleet_summary ?? null)
const meta = computed(() => dispatch.value?.meta ?? null)

function cohortLabel(site: Site): string {
  const cohort = dispatch.value?.cohorts.find((item) => item.cohort_id === site.cohort_id)
  return cohort?.label ?? 'Ungrouped'
}

function cohortBelowMinimum(site: Site): boolean {
  const cohort = dispatch.value?.cohorts.find((item) => item.cohort_id === site.cohort_id)
  return cohort ? !cohort.meets_minimum : false
}

/**
 * One icon vocabulary, reused sitewide (DispatchView, FleetMap, InverterPanel):
 * triangle = needs action, diamond = watch it, circle-check = fine. Three
 * distinct silhouettes so the pairing works for a colorblind reader before
 * the color does any work at all — icon and text label both ship with every
 * use, per the same rule the row markup already followed with glyphs.
 */
const STATUS_ICON: Record<GroupKey, typeof TriangleAlert> = {
  dispatch: TriangleAlert,
  monitor: Diamond,
  healthy: CircleCheck,
  not_assessed: CircleSlash,
}
</script>

<template>
  <main class="screen">
    <p v-if="isLoading" class="state">Loading dispatch…</p>

    <p v-else-if="loadError" class="state state--error">
      Could not load dispatch data.<br />
      <span class="state__detail">{{ loadError }}</span>
    </p>

    <template v-else-if="dispatch && summary && meta">
      <header class="fleet-header">
        <div class="fleet-header__identity">
          <h1 class="fleet-header__title">This month's dispatch list</h1>
          <p class="fleet-header__month">{{ meta.reporting_month_label }}</p>
        </div>

        <dl class="fleet-header__stats">
          <div class="fleet-header__stat">
            <dt>Sites</dt>
            <dd>{{ summary.site_count }}</dd>
          </div>
          <div class="fleet-header__stat">
            <dt>Capacity</dt>
            <dd>{{ summary.total_capacity_mwp }} MWp</dd>
          </div>
          <div class="fleet-header__stat">
            <dt>Cohorts</dt>
            <dd>{{ summary.cohort_count }}</dd>
          </div>
        </dl>

        <DataStatusBadge :status="meta.data_status" />
      </header>

      <NoticeCallout v-if="source === 'fallback'" tone="warning" compact class="notice">
        Serving the committed fallback copy — the primary source was unreachable.
      </NoticeCallout>

      <div class="layout">
        <aside class="map-column">
          <FleetMap
            :sites="dispatch.sites"
            :active-site-id="activeSiteId"
            @select="activeSiteId = $event"
          />
        </aside>

        <section class="list">
          <section v-for="group in groups" :key="group.key" class="group">
            <h2 class="group__heading">
              <component
                :is="STATUS_ICON[group.key]"
                class="group__glyph"
                :class="`group__glyph--${group.key}`"
                :size="14"
                aria-hidden="true"
              />
              {{ group.heading }}
              <span class="group__count">({{ group.sites.length }})</span>
              <span class="group__note">— {{ group.note }}</span>
            </h2>

            <!--
              The zero here is the product's answer, not a missing row. Give it
              the weight of a result and show the closest call as evidence the
              threshold is what held it back.
            -->
            <div
              v-if="group.key === 'dispatch' && !group.sites.length && dispatchVerdict"
              class="verdict"
            >
              <p class="verdict__headline">
                No site clears {{ formatRinggit(dispatchVerdict.threshold) }}/month this month.
              </p>
              <p class="verdict__body">
                All {{ dispatchVerdict.assessed }} assessed sites cost more to visit than they are
                losing. That is the recommendation: send nobody, and keep
                {{ formatRinggit(summary.estimated_saving_rm) }} of mobilisation budget across
                {{ summary.trips_avoided }} trips that did not need to happen.
              </p>
              <p v-if="dispatchVerdict.nearest" class="verdict__nearest">
                <span class="verdict__nearest-label">Closest call</span>
                {{ dispatchVerdict.nearest.name }} —
                {{ formatRinggit(dispatchVerdict.nearest.rm) }}/mo at risk,
                <strong>{{ formatRinggit(dispatchVerdict.nearest.shortfall) }} short</strong>
                of the threshold ({{ dispatchVerdict.nearest.percentOfThreshold }}% of it). It is
                detected and ranked — it is not yet worth the trip.
              </p>
            </div>

            <p v-else-if="!group.sites.length" class="group__empty">No sites in this group.</p>

            <ol v-else class="rows">
              <li
                v-for="(site, rowIndex) in group.sites"
                :key="site.site_id"
                class="row"
                :class="{ 'row--active': site.site_id === activeSiteId }"
                :style="{ '--row-index': rowIndex }"
                tabindex="0"
                role="button"
                @mouseenter="activeSiteId = site.site_id"
                @focus="activeSiteId = site.site_id"
                @click="openSite(site.site_id)"
                @keydown.enter="openSite(site.site_id)"
              >
                <span class="row__rank">{{ site.rank ?? '—' }}</span>

                <span class="row__identity">
                  <span class="row__name">{{ site.name }}</span>
                  <span class="row__meta">
                    {{ formatCapacity(site.capacity_kwp) }}
                    <span class="row__divider">·</span>
                    {{ site.address }}
                    <span class="row__divider">·</span>
                    {{ cohortLabel(site) }}
                    <span
                      v-if="cohortBelowMinimum(site)"
                      class="row__caution"
                      title="Cohort is below the minimum size — peer comparison is weak here"
                    >
                      <TriangleAlert :size="11" aria-hidden="true" /> cohort below minimum
                    </span>
                    <span
                      v-if="site.excluded_from_analysis"
                      class="row__excluded"
                      :title="site.excluded_from_analysis.detail"
                    >
                      <CircleSlash :size="11" aria-hidden="true" /> excluded —
                      {{ site.excluded_from_analysis.reason.replace('_', ' ') }}
                    </span>
                  </span>
                  <span v-if="site.hypothesis" class="row__hypothesis">
                    {{ site.hypothesis.summary }}
                  </span>
                </span>

                <span class="row__money">
                  <template v-if="site.economics">
                    <span class="row__rm">{{ formatRinggit(site.economics.rm_at_risk_monthly) }}</span>
                    <span class="row__rm-unit">/mo at risk</span>
                  </template>
                  <span v-else class="row__rm-none">—</span>
                </span>

                <span class="row__days">
                  <template v-if="site.divergence">
                    <span class="row__days-value">
                      <Clock :size="12" aria-hidden="true" /> {{ site.divergence.days_since }}
                    </span>
                    <span class="row__days-unit">days diverging</span>
                  </template>
                </span>

                <span class="row__badge">
                  <DataStatusBadge :status="site.data_status" small />
                </span>
              </li>
            </ol>
          </section>

          <!-- The claim the product rests on. Deliberately given weight. -->
          <footer class="outcome">
            <div class="outcome__tile">
              <p class="outcome__value">{{ summary.visits_avoided }}</p>
              <p class="outcome__label">sites not visited this month</p>
            </div>
            <div class="outcome__tile">
              <p class="outcome__value">{{ formatRinggit(summary.estimated_saving_rm) }}</p>
              <!--
                Sites and ringgit have different denominators: co-located sites
                are one mobilisation, so the saving is per TRIP. Showing the
                site count beside the money without this line implies a
                per-site cost that was never charged.
              -->
              <p class="outcome__label">
                estimated saving — {{ summary.trips_avoided }} site trips avoided
              </p>
            </div>
            <div class="outcome__tile outcome__tile--secondary">
              <p class="outcome__value outcome__value--small">
                {{ formatRinggit(summary.total_rm_at_risk) }}
              </p>
              <p class="outcome__label">total at risk across flagged sites</p>
            </div>
          </footer>
        </section>
      </div>

      <footer class="provenance">
        <p>{{ meta.data_source }} · irradiance: {{ meta.irradiance_source }} · {{ meta.source_note }}</p>
        <p v-if="meta.date_remapped">{{ meta.date_remap_note }}</p>
        <p class="provenance__generated">
          Generated {{ meta.generated_at }} · pipeline {{ meta.pipeline_version }} · schema
          {{ meta.schema_version }}
        </p>
      </footer>
    </template>
  </main>
</template>

<style scoped>
.screen {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
}

.state {
  padding: 3rem 0;
  color: var(--text-secondary);
}

.state--error {
  color: var(--status-critical);
}

.state__detail {
  color: var(--text-muted);
  font-size: 0.85rem;
}

/* --- Header --- */
/* No eyebrow. The h1 is the page's actual name — "This month's dispatch
   list" — and carries its own weight rather than being introduced by a
   small caption above it. Fleet-wide stats read as a labeled stat row,
   not folded into the heading's sentence. */

.fleet-header {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 1.1rem;
  border-bottom: 1px solid var(--border-hairline);
}

.fleet-header__identity {
  min-width: 0;
}

.fleet-header__title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.01em;
}

.fleet-header__month {
  margin: 0.15rem 0 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.fleet-header__stats {
  display: flex;
  gap: 1.75rem;
  margin: 0 0 0 auto;
}

.fleet-header__stat {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.fleet-header__stat dt {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.fleet-header__stat dd {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.notice {
  margin: 1rem 0 0;
}

/* --- Layout --- */

.layout {
  display: grid;
  grid-template-columns: minmax(300px, 420px) 1fr;
  gap: 1.5rem;
  margin-top: 1.5rem;
  align-items: start;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}

.map-column {
  /* Clears the sticky brand nav (App.vue) plus a little breathing room. */
  position: sticky;
  top: calc(3.5rem + 1rem);
}

@media (max-width: 900px) {
  .map-column {
    position: static;
  }
}

/* --- Groups --- */

.group {
  margin-bottom: 2rem;
}

.group__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
  margin: 0 0 0.6rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.group__glyph {
  flex: none;
}

.group__glyph--dispatch {
  color: var(--status-critical);
}
.group__glyph--monitor {
  color: var(--status-warning);
}
.group__glyph--healthy {
  color: var(--status-good);
}
.group__glyph--not_assessed {
  color: var(--text-muted);
}

.group__count {
  color: var(--text-secondary);
}

.group__note {
  font-weight: 400;
  letter-spacing: 0;
  text-transform: none;
  color: var(--text-muted);
  font-size: 0.78rem;
}

.group__empty {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.85rem;
}

/*
   The "send nobody" verdict. Styled as a conclusion, not as an error: the good
   status colour, because a clean month IS the product working. An empty-list
   grey here would read as a fetch that failed.
*/
.verdict {
  border: 1px solid var(--border-hairline);
  border-left: 3px solid var(--status-good);
  border-radius: 6px;
  padding: 0.85rem 1rem;
}

.verdict__headline {
  margin: 0;
  font-size: 1rem;
  font-weight: 650;
  color: var(--text-primary);
}

.verdict__body {
  margin: 0.4rem 0 0;
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--text-secondary);
}

.verdict__nearest {
  margin: 0.75rem 0 0;
  padding-top: 0.7rem;
  border-top: 1px solid var(--border-hairline);
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--text-secondary);
}

.verdict__nearest-label {
  display: inline-block;
  margin-right: 0.45rem;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

/* --- Rows --- */

.rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.row {
  display: grid;
  grid-template-columns: 2rem 1fr auto auto auto;
  gap: 0.9rem;
  align-items: center;
  padding: 0.7rem 0.9rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-out),
    background-color var(--duration-fast) var(--ease-out);
  /* The one authored motion moment on this screen: rows settle into place on
     arrival, staggered by list position. A single entrance, not a per-element
     effect library — everything else in the product stays still.
     prefers-reduced-motion zeroes the duration globally (theme.css). */
  animation: row-enter var(--duration-base) var(--ease-out) both;
  animation-delay: calc(var(--row-index, 0) * 35ms);
}

/* Interaction state is a full-perimeter border + tint, deliberately not a
   colored border-left — that idiom is reserved for status callouts, and a
   row's status is already carried by its group icon, not by this border. */
.row:hover,
.row--active,
.row:focus-visible {
  border-color: var(--action-text);
  background: var(--callout-info-bg);
  outline: none;
}

@keyframes row-enter {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 720px) {
  .row {
    grid-template-columns: 1.6rem 1fr;
    row-gap: 0.4rem;
  }
  .row__money,
  .row__days,
  .row__badge {
    grid-column: 2;
    justify-self: start;
  }
}

.row__rank {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.row__identity {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.row__name {
  font-weight: 600;
  font-size: 0.95rem;
}

.row__meta {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.row__divider {
  margin: 0 0.25rem;
}

.row__caution {
  display: inline-flex;
  align-items: center;
  gap: 0.25em;
  color: var(--status-serious);
  margin-left: 0.3rem;
  font-weight: 600;
}

/* Not a triage state — a statement that this site is not being judged at all. */
.row__excluded {
  display: inline-flex;
  align-items: center;
  gap: 0.25em;
  color: var(--text-secondary);
  margin-left: 0.3rem;
  font-weight: 600;
  border-bottom: 1px dotted currentColor;
  cursor: help;
}

.row__hypothesis {
  font-size: 0.82rem;
  color: var(--text-secondary);
  margin-top: 0.15rem;
}

.row__money {
  text-align: right;
  white-space: nowrap;
}

.row__rm {
  font-weight: 700;
  font-size: 1rem;
  font-variant-numeric: tabular-nums;
}

.row__rm-unit,
.row__days-unit {
  display: block;
  font-size: 0.7rem;
  color: var(--text-muted);
}

.row__rm-none {
  color: var(--text-muted);
}

.row__days {
  text-align: right;
  white-space: nowrap;
}

.row__days-value {
  display: inline-flex;
  align-items: center;
  gap: 0.2em;
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

/* --- Outcome footer — the product's core claim --- */

.outcome {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1px;
  margin-top: 2.5rem;
  padding-top: 1.5rem;
  border-top: 2px solid var(--text-primary);
}

.outcome__tile {
  padding: 0.5rem 1rem 0.5rem 0;
}

/*
 * The one place on this screen brand color carries real weight: the two
 * headline numbers behind the product's actual claim — sites not visited,
 * money saved. Everywhere else on the page stays neutral so this stays
 * the moment that reads as "the point". The secondary "total at risk" tile
 * overrides back to neutral text below — it is context, not the headline.
 */
.outcome__value {
  margin: 0;
  font-size: 2.4rem;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.02em;
  color: var(--action-text);
}

.outcome__value--small {
  font-size: 1.6rem;
  color: var(--text-secondary);
}

.outcome__label {
  margin: 0.3rem 0 0;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.outcome__tile--secondary {
  align-self: end;
}

/* --- Provenance --- */

.provenance {
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-hairline);
  font-size: 0.75rem;
  line-height: 1.6;
  color: var(--text-muted);
}

.provenance p {
  margin: 0 0 0.3rem;
}

.provenance__generated {
  font-variant-numeric: tabular-nums;
}
</style>

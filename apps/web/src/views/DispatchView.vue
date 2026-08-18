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
import { loadDispatch, sitesByStatus, formatRinggit, formatCapacity } from '@/services/api'
import type { Dispatch, Site, SiteStatus } from '@/types/dispatch'
import DataStatusBadge from '@/components/DataStatusBadge.vue'
import FleetMap from '@/components/FleetMap.vue'

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

const GROUPS: Array<{ status: SiteStatus; heading: string; note: string }> = [
  { status: 'dispatch', heading: 'Dispatch recommended', note: 'above the dispatch threshold' },
  { status: 'monitor', heading: 'Monitor', note: 'deviation detected, below dispatch threshold' },
  { status: 'healthy', heading: 'Healthy', note: 'within cohort tolerance' },
]

const groups = computed(() => {
  if (!dispatch.value) return []
  return GROUPS.map((group) => ({
    ...group,
    sites: sitesByStatus(dispatch.value as Dispatch, group.status),
  }))
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

/** Glyph pairs with the text label so status never rests on color alone. */
const STATUS_GLYPH: Record<SiteStatus, string> = {
  dispatch: '▲',
  monitor: '◆',
  healthy: '●',
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
        <div>
          <p class="fleet-header__eyebrow">Fleet</p>
          <h1 class="fleet-header__title">
            {{ summary.site_count }} sites
            <span class="fleet-header__divider">·</span>
            {{ summary.total_capacity_mwp }} MWp
            <span class="fleet-header__divider">·</span>
            {{ summary.cohort_count }} cohorts
          </h1>
        </div>
        <div class="fleet-header__right">
          <p class="fleet-header__month">{{ meta.reporting_month_label }}</p>
          <DataStatusBadge :status="meta.data_status" />
        </div>
      </header>

      <p v-if="source === 'fallback'" class="notice">
        Serving the committed fallback copy — the primary source was unreachable.
      </p>

      <div class="layout">
        <aside class="map-column">
          <FleetMap
            :sites="dispatch.sites"
            :active-site-id="activeSiteId"
            @select="activeSiteId = $event"
          />
        </aside>

        <section class="list">
          <section v-for="group in groups" :key="group.status" class="group">
            <h2 class="group__heading">
              <span class="group__glyph" :class="`group__glyph--${group.status}`" aria-hidden="true">
                {{ STATUS_GLYPH[group.status] }}
              </span>
              {{ group.heading }}
              <span class="group__count">({{ group.sites.length }})</span>
              <span class="group__note">— {{ group.note }}</span>
            </h2>

            <p v-if="!group.sites.length" class="group__empty">No sites in this group.</p>

            <ol v-else class="rows">
              <li
                v-for="site in group.sites"
                :key="site.site_id"
                class="row"
                :class="{ 'row--active': site.site_id === activeSiteId }"
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
                    <span v-if="cohortBelowMinimum(site)" class="row__caution" title="Cohort is below the minimum size — peer comparison is weak here">
                      ⚠ cohort below minimum
                    </span>
                    <span
                      v-if="site.excluded_from_analysis"
                      class="row__excluded"
                      :title="site.excluded_from_analysis.detail"
                    >
                      ⊘ excluded — {{ site.excluded_from_analysis.reason.replace('_', ' ') }}
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
                    <span class="row__days-value">▲ {{ site.divergence.days_since }}</span>
                    <span class="row__days-unit">days</span>
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

.fleet-header {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: flex-end;
  justify-content: space-between;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-hairline);
}

.fleet-header__eyebrow {
  margin: 0 0 0.2rem;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.fleet-header__title {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 600;
  line-height: 1.2;
}

.fleet-header__divider {
  color: var(--text-muted);
  margin: 0 0.3rem;
  font-weight: 400;
}

.fleet-header__right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.4rem;
}

.fleet-header__month {
  margin: 0;
  font-size: 1rem;
  color: var(--text-secondary);
}

.notice {
  margin: 1rem 0 0;
  padding: 0.6rem 0.8rem;
  border-left: 3px solid var(--status-warning);
  background: var(--surface-1);
  color: var(--text-secondary);
  font-size: 0.85rem;
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
  position: sticky;
  top: 1.5rem;
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
  align-items: baseline;
  gap: 0.45rem;
  margin: 0 0 0.6rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
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
  transition: border-color 120ms ease;
}

.row:hover,
.row--active,
.row:focus-visible {
  border-color: var(--text-muted);
  outline: none;
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
  color: var(--status-serious);
  margin-left: 0.3rem;
  font-weight: 600;
}

/* Not a triage state — a statement that this site is not being judged at all. */
.row__excluded {
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

.outcome__value {
  margin: 0;
  font-size: 2.4rem;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.02em;
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

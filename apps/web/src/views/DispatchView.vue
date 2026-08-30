<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  CircleCheck,
  CircleSlash,
  Clock3,
  Diamond,
  List,
  Map,
  RefreshCw,
  TriangleAlert,
} from '@lucide/vue'
import {
  formatCapacity,
  formatRinggit,
  isAssessed,
  loadDispatch,
  sitesByStatus,
  sitesNotAssessed,
} from '@/services/api'
import type { Dispatch, Site, SiteStatus } from '@/types/dispatch'
import DataStatusBadge from '@/components/DataStatusBadge.vue'
import FleetMap from '@/components/FleetMap.vue'
import type { MapViewMode } from '@/components/fleetBasemap'
import NoticeCallout from '@/components/NoticeCallout.vue'
import DemoGuide from '@/components/DemoGuide.vue'

const router = useRouter()
const route = useRoute()
const dispatch = ref<Dispatch | null>(null)
const source = ref<'primary' | 'fallback' | null>(null)
const loadError = ref<string | null>(null)
const isLoading = ref(true)
const activeSiteId = ref<string | null>(null)
const mobilePanel = ref<'map' | 'queue'>('map')
const currentMapView = ref<MapViewMode>('map')

async function load(force = false): Promise<void> {
  isLoading.value = true
  loadError.value = null
  try {
    const result = await loadDispatch(force)
    dispatch.value = result.dispatch
    source.value = result.source
    const first = orderedAttentionSites.value[0]
    if (!activeSiteId.value && first) activeSiteId.value = first.site_id
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : String(error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  const querySite = typeof route.query.site === 'string' ? route.query.site : null
  const queryView = typeof route.query.view === 'string' ? route.query.view : null
  if (querySite) activeSiteId.value = querySite
  if (queryView === 'aerial' || queryView === '3d') currentMapView.value = queryView
  load()
})

watch([activeSiteId, currentMapView], ([site, view]) => {
  router.replace({
    query: {
      ...route.query,
      site: site || undefined,
      view: view === 'map' ? undefined : view,
    },
  })
})

const summary = computed(() => dispatch.value?.fleet_summary ?? null)
const meta = computed(() => dispatch.value?.meta ?? null)
const dispatchSites = computed(() =>
  dispatch.value ? sitesByStatus(dispatch.value, 'dispatch') : [],
)
const monitorSites = computed(() =>
  dispatch.value ? sitesByStatus(dispatch.value, 'monitor') : [],
)
const healthySites = computed(() =>
  dispatch.value ? sitesByStatus(dispatch.value, 'healthy') : [],
)
const unassessedSites = computed(() => (dispatch.value ? sitesNotAssessed(dispatch.value) : []))
const orderedAttentionSites = computed(() => [...dispatchSites.value, ...monitorSites.value])
const activeSite = computed(() =>
  dispatch.value?.sites.find((site) => site.site_id === activeSiteId.value),
)

const headline = computed(() => {
  const dispatchCount = dispatchSites.value.length
  const monitorCount = monitorSites.value.length
  if (dispatchCount > 0) {
    return `${dispatchCount} ${dispatchCount === 1 ? 'site needs' : 'sites need'} a maintenance decision.`
  }
  if (monitorCount > 0) {
    return `No trip is justified yet. ${monitorCount} ${monitorCount === 1 ? 'site is' : 'sites are'} on watch.`
  }
  return 'No site needs attention this month.'
})

const dispatchVerdict = computed(() => {
  if (!dispatch.value || dispatchSites.value.length > 0) return null
  const threshold = dispatch.value.assumptions.dispatch_threshold_rm_per_month
  const nearest = dispatch.value.sites
    .filter((site) => isAssessed(site) && site.economics)
    .sort(
      (a, b) => (b.economics?.rm_at_risk_monthly ?? 0) - (a.economics?.rm_at_risk_monthly ?? 0),
    )[0]
  return nearest
    ? { threshold, nearest, shortfall: threshold - (nearest.economics?.rm_at_risk_monthly ?? 0) }
    : null
})

function cohortLabel(site: Site): string {
  return (
    dispatch.value?.cohorts.find((cohort) => cohort.cohort_id === site.cohort_id)?.label ??
    'Ungrouped'
  )
}

function openSite(siteId: string): void {
  router.push({ name: 'site-detail', params: { siteId } })
}

function selectSite(siteId: string): void {
  activeSiteId.value = siteId
}

function reviewPriorities(): void {
  mobilePanel.value = 'queue'
  requestAnimationFrame(() => document.querySelector<HTMLElement>('#priority-queue')?.focus())
}

function iconFor(status: SiteStatus) {
  return status === 'dispatch' ? TriangleAlert : status === 'monitor' ? Diamond : CircleCheck
}
</script>

<template>
  <main id="main-content" class="command screen screen--wide" tabindex="-1">
    <section v-if="isLoading" class="load-state" aria-live="polite">
      <span class="load-state__pulse"></span>
      <div>
        <strong>Preparing fleet command</strong><span>Loading the latest dispatch artifact…</span>
      </div>
    </section>

    <section v-else-if="loadError" class="load-state load-state--error" role="alert">
      <TriangleAlert :size="24" aria-hidden="true" />
      <div>
        <strong>Dispatch data could not be loaded</strong><span>{{ loadError }}</span>
      </div>
      <button type="button" @click="load(true)">
        <RefreshCw :size="16" aria-hidden="true" /> Retry
      </button>
    </section>

    <template v-else-if="dispatch && summary && meta">
      <header id="fleet-decision" class="command-header">
        <div>
          <p class="command-header__month">{{ meta.reporting_month_label }} fleet decision</p>
          <h1>{{ headline }}</h1>
          <p class="command-header__summary">
            {{ summary.site_count }} sites across {{ summary.cohort_count }} climate cohorts ·
            {{ summary.total_capacity_mwp }} MWp under review
          </p>
        </div>
        <div class="command-header__actions">
          <span class="freshness"
            ><span></span> Pipeline {{ meta.pipeline_version }} ·
            {{ meta.data_status.toLowerCase() }}</span
          >
          <button type="button" class="btn-primary" @click="reviewPriorities">
            Review priorities <ArrowUpRight :size="17" aria-hidden="true" />
          </button>
        </div>
      </header>

      <NoticeCallout v-if="source === 'fallback'" tone="warning" compact class="notice">
        The live source is unavailable. You are viewing the committed fallback artifact.
      </NoticeCallout>

      <section id="fleet-signals" class="signal-strip" aria-label="Fleet summary">
        <article class="signal signal--primary">
          <span>Monthly value at risk</span>
          <strong>{{ formatRinggit(summary.total_rm_at_risk) }}</strong>
          <small>Across measured flagged sites</small>
        </article>
        <article class="signal">
          <span>Dispatch</span><strong>{{ summary.dispatch_count }}</strong
          ><small>Trips worth reviewing</small>
        </article>
        <article class="signal">
          <span>On watch</span><strong>{{ summary.monitor_count }}</strong
          ><small>Below dispatch threshold</small>
        </article>
        <article class="signal signal--healthy">
          <span>Cleared</span><strong>{{ summary.healthy_count }}</strong
          ><small>Assessed as healthy</small>
        </article>
      </section>

      <div class="mobile-switch" role="group" aria-label="Fleet workspace view">
        <button
          type="button"
          :aria-pressed="mobilePanel === 'map'"
          :class="{ active: mobilePanel === 'map' }"
          @click="mobilePanel = 'map'"
        >
          <Map :size="16" aria-hidden="true" /> Map
        </button>
        <button
          type="button"
          :aria-pressed="mobilePanel === 'queue'"
          :class="{ active: mobilePanel === 'queue' }"
          @click="mobilePanel = 'queue'"
        >
          <List :size="16" aria-hidden="true" /> Priority list
        </button>
      </div>

      <section class="workspace" aria-label="Fleet dispatch workspace">
        <div
          id="spatial-workspace"
          class="spatial-panel"
          :class="{ 'mobile-hidden': mobilePanel !== 'map' }"
        >
          <div class="panel-heading">
            <div>
              <h2>Fleet risk landscape</h2>
              <p>Geography, status, and economic exposure in one view.</p>
            </div>
            <span class="view-readout">{{
              currentMapView === '3d'
                ? '3D economic risk'
                : currentMapView === 'aerial'
                  ? 'Aerial evidence'
                  : '2D fleet context'
            }}</span>
          </div>
          <FleetMap
            :sites="dispatch.sites"
            :active-site-id="activeSiteId"
            :initial-view="currentMapView"
            @select="selectSite"
            @view-change="currentMapView = $event"
          />
          <div v-if="activeSite" class="selection-brief" aria-live="polite">
            <div
              class="selection-brief__status"
              :class="`selection-brief__status--${activeSite.status}`"
            >
              <component :is="iconFor(activeSite.status)" :size="18" aria-hidden="true" />
            </div>
            <div class="selection-brief__identity">
              <span>Selected site</span><strong>{{ activeSite.name }}</strong>
              <small
                >{{ formatCapacity(activeSite.capacity_kwp) }} ·
                {{ cohortLabel(activeSite) }}</small
              >
            </div>
            <div class="selection-brief__value">
              <span>At risk</span
              ><strong>{{
                activeSite.economics
                  ? formatRinggit(activeSite.economics.rm_at_risk_monthly)
                  : 'Not assessed'
              }}</strong>
            </div>
            <button type="button" @click="openSite(activeSite.site_id)">
              Evidence <ChevronRight :size="16" aria-hidden="true" />
            </button>
          </div>
        </div>

        <aside
          id="priority-queue"
          class="priority-panel"
          :class="{ 'mobile-hidden': mobilePanel !== 'queue' }"
          tabindex="-1"
        >
          <div class="panel-heading">
            <div>
              <h2>Priority queue</h2>
              <p>Ranked by the pipeline, with the reason visible.</p>
            </div>
            <DataStatusBadge :status="meta.data_status" small />
          </div>

          <div v-if="dispatchVerdict" class="threshold-verdict">
            <CheckCircle2 :size="19" aria-hidden="true" />
            <div>
              <strong>No site clears {{ formatRinggit(dispatchVerdict.threshold) }}/month.</strong>
              <span
                >{{ dispatchVerdict.nearest.name }} is closest, still
                {{ formatRinggit(dispatchVerdict.shortfall) }} short of justifying a trip.</span
              >
            </div>
          </div>

          <ol v-if="orderedAttentionSites.length" class="priority-list">
            <li v-for="site in orderedAttentionSites" :key="site.site_id">
              <button
                type="button"
                class="priority-card"
                :class="[
                  `priority-card--${site.status}`,
                  { active: site.site_id === activeSiteId },
                ]"
                @click="selectSite(site.site_id)"
                @dblclick="openSite(site.site_id)"
              >
                <span class="priority-card__rank">{{
                  String(site.rank ?? '—').padStart(2, '0')
                }}</span>
                <span class="priority-card__main">
                  <span class="priority-card__topline">
                    <strong>{{ site.name }}</strong>
                    <span>{{
                      site.economics ? formatRinggit(site.economics.rm_at_risk_monthly) : '—'
                    }}</span>
                  </span>
                  <span class="priority-card__reason">{{
                    site.hypothesis?.summary ?? 'Performance diverges from the fleet reference.'
                  }}</span>
                  <span class="priority-card__meta">
                    <component :is="iconFor(site.status)" :size="13" aria-hidden="true" />
                    {{ site.status }}
                    <span v-if="site.divergence"
                      ><Clock3 :size="12" aria-hidden="true" />
                      {{ site.divergence.days_since }} days</span
                    >
                    <span>{{ cohortLabel(site) }}</span>
                  </span>
                </span>
                <ChevronRight :size="18" aria-hidden="true" />
              </button>
            </li>
          </ol>
          <div v-else class="all-clear">
            <CircleCheck :size="22" aria-hidden="true" /><strong>Fleet clear</strong>
            <span>No assessed site requires attention this month.</span>
          </div>

          <details class="healthy-summary">
            <summary>
              <span
                ><CircleCheck :size="17" aria-hidden="true" /><strong
                  >{{ healthySites.length }} healthy sites</strong
                ></span
              >
              <span>No visit recommended</span>
            </summary>
            <ul>
              <li v-for="site in healthySites" :key="site.site_id">
                <button type="button" @click="selectSite(site.site_id)">
                  {{ site.name }}<span>{{ formatCapacity(site.capacity_kwp) }}</span>
                </button>
              </li>
            </ul>
          </details>

          <details v-if="unassessedSites.length" class="healthy-summary healthy-summary--muted">
            <summary>
              <span
                ><CircleSlash :size="17" aria-hidden="true" /><strong
                  >{{ unassessedSites.length }} not assessed</strong
                ></span
              ><span>Data quality exclusion</span>
            </summary>
            <ul>
              <li v-for="site in unassessedSites" :key="site.site_id">
                <button type="button" @click="selectSite(site.site_id)">
                  {{ site.name
                  }}<span>{{ site.excluded_from_analysis?.reason.replace('_', ' ') }}</span>
                </button>
              </li>
            </ul>
          </details>
        </aside>
      </section>

      <section id="fleet-outcome" class="fleet-outcome" aria-label="Operational outcome">
        <div>
          <span>Sites kept off the road</span><strong>{{ summary.visits_avoided }}</strong
          ><small>{{ summary.trips_avoided }} unnecessary site trips avoided</small>
        </div>
        <div>
          <span>Mobilisation budget retained</span
          ><strong>{{ formatRinggit(summary.estimated_saving_rm) }}</strong
          ><small>Estimated from avoided trips, not avoided sites</small>
        </div>
        <p>The product's value is also in the visits it confidently recommends against.</p>
      </section>

      <footer class="provenance">
        <p>
          {{ meta.data_source }} · irradiance: {{ meta.irradiance_source }} · {{ meta.source_note }}
        </p>
        <p v-if="meta.date_remapped">{{ meta.date_remap_note }}</p>
        <p>Generated {{ meta.generated_at }} · schema {{ meta.schema_version }}</p>
      </footer>
      <DemoGuide />
    </template>
  </main>
</template>

<style scoped>
.command {
  outline: none;
}
.load-state {
  display: flex;
  min-height: 60vh;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: var(--text-secondary);
}
.load-state div {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.load-state strong {
  color: var(--text-primary);
  font-family: var(--font-display);
  font-size: 1.1rem;
}
.load-state span {
  font-size: 0.85rem;
}
.load-state__pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--signal-live);
  box-shadow: 0 0 0 8px color-mix(in srgb, var(--signal-live) 16%, transparent);
  animation: pulse 1.6s var(--ease-out) infinite;
}
.load-state--error {
  flex-wrap: wrap;
  color: var(--status-critical);
}
.load-state--error button {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 44px;
  padding: 0 0.9rem;
  color: var(--text-primary);
  background: var(--surface-1);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  cursor: pointer;
}
.command-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 2rem;
}
.command-header__month {
  margin: 0 0 0.45rem;
  color: var(--action-text);
  font-size: 0.72rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.command-header h1 {
  max-width: 18ch;
  margin: 0;
  font-size: clamp(2rem, 4vw, 4.35rem);
  font-weight: 650;
  letter-spacing: -0.04em;
  line-height: 0.98;
  text-wrap: balance;
}
.command-header__summary {
  margin: 0.9rem 0 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
}
.command-header__actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.75rem;
}
.freshness {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  color: var(--text-muted);
  font-size: 0.72rem;
}
.freshness > span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--signal-live);
}
.notice {
  margin-top: 1rem;
}
.signal-strip {
  display: grid;
  grid-template-columns: 1.45fr repeat(3, minmax(0, 0.72fr));
  gap: 1px;
  margin-top: 2rem;
  overflow: hidden;
  background: var(--border-hairline);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
}
.signal {
  display: flex;
  min-height: 7.3rem;
  flex-direction: column;
  justify-content: flex-end;
  padding: 1rem 1.15rem;
  background: var(--surface-1);
}
.signal span {
  color: var(--text-muted);
  font-size: 0.72rem;
  font-weight: 650;
}
.signal strong {
  margin-top: auto;
  font: 650 clamp(1.6rem, 3vw, 2.7rem)/1 var(--font-display);
  letter-spacing: -0.035em;
}
.signal small {
  margin-top: 0.45rem;
  color: var(--text-muted);
  font-size: 0.68rem;
}
.signal--primary {
  background: var(--surface-emphasis);
}
.signal--primary strong {
  color: var(--status-critical);
}
.signal--healthy strong {
  color: var(--success-text);
}
.mobile-switch {
  display: none;
}
.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(330px, 0.78fr);
  gap: 1rem;
  margin-top: 1rem;
  align-items: start;
}
.spatial-panel,
.priority-panel {
  min-width: 0;
  padding: 1rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
  box-shadow: var(--elevation-1);
}
.panel-heading {
  display: flex;
  min-height: 3.2rem;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.85rem;
}
.panel-heading h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
}
.panel-heading p {
  margin: 0.25rem 0 0;
  color: var(--text-muted);
  font-size: 0.72rem;
}
.view-readout {
  padding: 0.4rem 0.55rem;
  color: var(--text-secondary);
  background: var(--surface-2);
  border-radius: var(--radius-sm);
  font-size: 0.65rem;
  font-weight: 650;
  white-space: nowrap;
}
.selection-brief {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  gap: 0.85rem;
  align-items: center;
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: var(--surface-2);
  border-radius: var(--radius-md);
}
.selection-brief__status {
  display: grid;
  width: 2.5rem;
  height: 2.5rem;
  place-items: center;
  border-radius: 10px;
}
.selection-brief__status--dispatch {
  color: var(--status-critical);
  background: var(--callout-critical-bg);
}
.selection-brief__status--monitor {
  color: var(--status-warning);
  background: var(--callout-warning-bg);
}
.selection-brief__status--healthy {
  color: var(--status-good);
  background: var(--callout-good-bg);
}
.selection-brief__identity,
.selection-brief__value {
  display: flex;
  min-width: 0;
  flex-direction: column;
}
.selection-brief span {
  color: var(--text-muted);
  font-size: 0.62rem;
  font-weight: 650;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.selection-brief strong {
  overflow: hidden;
  font-size: 0.83rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.selection-brief small {
  color: var(--text-muted);
  font-size: 0.67rem;
}
.selection-brief__value {
  text-align: right;
}
.selection-brief button {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  gap: 0.2rem;
  padding: 0 0.65rem;
  color: var(--text-primary);
  background: transparent;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  font: 650 0.72rem var(--font-display);
  cursor: pointer;
}
.priority-panel {
  max-height: 720px;
  overflow: auto;
}
.threshold-verdict {
  display: flex;
  gap: 0.7rem;
  margin-bottom: 0.7rem;
  padding: 0.75rem;
  color: var(--success-text);
  background: var(--callout-good-bg);
  border: 1px solid var(--callout-good-border);
  border-radius: var(--radius-md);
}
.threshold-verdict svg {
  flex: none;
}
.threshold-verdict div {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.threshold-verdict strong {
  font-size: 0.76rem;
}
.threshold-verdict span {
  color: var(--text-secondary);
  font-size: 0.68rem;
  line-height: 1.45;
}
.priority-list {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.priority-card {
  display: grid;
  width: 100%;
  grid-template-columns: 1.5rem minmax(0, 1fr) auto;
  gap: 0.65rem;
  align-items: center;
  padding: 0.85rem;
  color: var(--text-primary);
  text-align: left;
  background: var(--surface-2);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}
.priority-card:hover,
.priority-card.active {
  background: var(--surface-selected);
  border-color: var(--action-text);
}
.priority-card__rank {
  align-self: start;
  color: var(--text-muted);
  font-size: 0.68rem;
  font-weight: 750;
}
.priority-card__main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.38rem;
}
.priority-card__topline {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}
.priority-card__topline strong {
  font-size: 0.83rem;
}
.priority-card__topline > span {
  font-size: 0.8rem;
  font-weight: 750;
  white-space: nowrap;
}
.priority-card--dispatch .priority-card__topline > span {
  color: var(--status-critical);
}
.priority-card__reason {
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 0.72rem;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.priority-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  align-items: center;
  color: var(--text-muted);
  font-size: 0.63rem;
  text-transform: capitalize;
}
.priority-card__meta > span,
.priority-card__meta {
  display: flex;
  align-items: center;
}
.priority-card__meta > span {
  gap: 0.18rem;
}
.all-clear {
  display: flex;
  min-height: 10rem;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--success-text);
  text-align: center;
}
.all-clear span {
  margin-top: 0.25rem;
  color: var(--text-muted);
  font-size: 0.72rem;
}
.healthy-summary {
  margin-top: 0.7rem;
  border-top: 1px solid var(--border-hairline);
}
.healthy-summary summary {
  display: flex;
  min-height: 3.35rem;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.7rem;
}
.healthy-summary summary > span {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}
.healthy-summary summary strong {
  color: var(--text-primary);
  font-size: 0.76rem;
}
.healthy-summary ul {
  margin: 0;
  padding: 0 0 0.5rem;
  list-style: none;
}
.healthy-summary li + li {
  border-top: 1px solid var(--border-hairline);
}
.healthy-summary li button {
  display: flex;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: space-between;
  padding: 0.3rem 0.25rem;
  color: var(--text-secondary);
  background: transparent;
  border: 0;
  font: inherit;
  cursor: pointer;
}
.healthy-summary li button span {
  color: var(--text-muted);
  font-size: 0.65rem;
}
.healthy-summary--muted {
  opacity: 0.8;
}
.fleet-outcome {
  display: grid;
  grid-template-columns: 1fr 1.2fr minmax(250px, 1fr);
  gap: 1px;
  margin-top: 1rem;
  overflow: hidden;
  background: var(--border-hairline);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
}
.fleet-outcome > div,
.fleet-outcome > p {
  margin: 0;
  padding: 1.1rem;
  background: var(--surface-1);
}
.fleet-outcome > div {
  display: flex;
  flex-direction: column;
}
.fleet-outcome span {
  color: var(--text-muted);
  font-size: 0.68rem;
}
.fleet-outcome strong {
  margin: 0.35rem 0;
  font: 650 1.8rem/1 var(--font-display);
  color: var(--action-text);
}
.fleet-outcome small {
  color: var(--text-muted);
  font-size: 0.66rem;
}
.fleet-outcome p {
  display: flex;
  align-items: center;
  color: var(--text-secondary);
  font: 500 0.85rem/1.5 var(--font-display);
}
.provenance {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-hairline);
  color: var(--text-muted);
  font-size: 0.63rem;
  line-height: 1.5;
}
.provenance p {
  margin: 0.15rem 0;
}
@keyframes pulse {
  50% {
    opacity: 0.5;
    transform: scale(0.84);
  }
}
@media (max-width: 1100px) {
  .workspace {
    grid-template-columns: 1fr;
  }
  .priority-panel {
    max-height: none;
  }
  .command-header h1 {
    font-size: clamp(2rem, 6vw, 3.5rem);
  }
}
@media (max-width: 760px) {
  .command {
    padding: 1rem;
    overflow: hidden;
  }
  .command-header {
    align-items: flex-start;
    flex-direction: column;
  }
  .command-header > div:first-child {
    min-width: 0;
  }
  .command-header h1 {
    max-width: 12ch;
  }
  .command-header__summary {
    max-width: 34ch;
    line-height: 1.5;
  }
  .command-header__actions {
    width: 100%;
    align-items: stretch;
  }
  .freshness {
    order: 2;
    flex-wrap: wrap;
  }
  .btn-primary {
    width: 100%;
  }
  .signal-strip {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
  .signal {
    min-width: 0;
    min-height: 6.2rem;
    padding: 0.9rem;
  }
  .signal strong {
    font-size: clamp(1.45rem, 9vw, 2.2rem);
  }
  .mobile-switch {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.25rem;
    margin-top: 1rem;
    padding: 0.25rem;
    background: var(--surface-2);
    border-radius: var(--radius-md);
  }
  .mobile-switch button {
    display: inline-flex;
    min-height: 44px;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    color: var(--text-secondary);
    background: transparent;
    border: 0;
    border-radius: calc(var(--radius-md) - 2px);
    font: 650 0.76rem var(--font-display);
  }
  .mobile-switch button.active {
    color: var(--text-primary);
    background: var(--surface-1);
    box-shadow: var(--elevation-1);
  }
  .workspace {
    min-width: 0;
    margin-top: 0.55rem;
  }
  .mobile-hidden {
    display: none;
  }
  .spatial-panel,
  .priority-panel {
    min-width: 0;
    padding: 0.75rem;
  }
  .panel-heading .view-readout {
    display: none;
  }
  .selection-brief {
    grid-template-columns: auto minmax(0, 1fr) auto;
  }
  .selection-brief__value {
    display: none;
  }
  .fleet-outcome {
    grid-template-columns: 1fr;
  }
  .fleet-outcome p {
    min-height: 5rem;
  }
}
@media (prefers-reduced-motion: reduce) {
  .load-state__pulse {
    animation: fade 200ms var(--ease-out) infinite alternate;
  }
}
</style>

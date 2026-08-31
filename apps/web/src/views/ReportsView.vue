<script setup lang="ts">
/**
 * Reports — the fifth connected surface. Evidence packages for operators,
 * management and judging, built from state this product already computed
 * elsewhere (Screens 1-4, the Evidence Timeline, the Recovery Tracker) —
 * never a second calculation of the same figure.
 *
 * docs/superpowers/specs/2026-08-30-solarax-closed-loop-operations-intelligence-design.md
 */
import { computed, onMounted, ref } from 'vue'
import { FileDown, Printer, RotateCcw, TriangleAlert, Diamond, CircleCheck } from '@lucide/vue'
import { loadDispatch, formatRinggit } from '@/services/api'
import type { Dispatch, Site, SiteStatus } from '@/types/dispatch'
import { buildEvidencePackage, buildFleetReportSummary } from '@/services/reportsEngine'
import DataStatusBadge from '@/components/DataStatusBadge.vue'
import NoticeCallout from '@/components/NoticeCallout.vue'
import ScoreGauge from '@/components/ScoreGauge.vue'

const dispatch = ref<Dispatch | null>(null)
const isLoading = ref(true)
const selectedSiteId = ref('')
const printError = ref('')

onMounted(async () => {
  const result = await loadDispatch()
  dispatch.value = result.dispatch
  isLoading.value = false
  const firstFlagged = result.dispatch.sites.find((site) => site.status !== 'healthy')
  selectedSiteId.value = firstFlagged?.site_id ?? result.dispatch.sites[0]?.site_id ?? ''
})

const flaggedSites = computed(() => (dispatch.value ? dispatch.value.sites.filter((site) => site.status !== 'healthy') : []))
const selectedSite = computed<Site | undefined>(() => dispatch.value?.sites.find((site) => site.site_id === selectedSiteId.value))
const fleetSummary = computed(() => (dispatch.value ? buildFleetReportSummary(dispatch.value) : null))
const evidencePackage = computed(() => (dispatch.value && selectedSite.value ? buildEvidencePackage(dispatch.value, selectedSite.value) : null))

const STATUS_META: Record<SiteStatus, { label: string; icon: typeof TriangleAlert; tone: 'good' | 'warning' | 'critical' }> = {
  dispatch: { label: 'Dispatch this month', icon: TriangleAlert, tone: 'critical' },
  monitor: { label: 'Monitor', icon: Diamond, tone: 'warning' },
  healthy: { label: 'Healthy — no visit needed', icon: CircleCheck, tone: 'good' },
}
const selectedStatusMeta = computed(() => (selectedSite.value ? STATUS_META[selectedSite.value.status] : null))

/** Fleet composition as three proportions of one whole — the shape behind
 * the stat tiles above it, at a glance. */
const fleetProportions = computed(() => {
  if (!fleetSummary.value) return null
  const total = fleetSummary.value.siteCount || 1
  return {
    dispatch: (fleetSummary.value.dispatchCount / total) * 100,
    monitor: (fleetSummary.value.monitorCount / total) * 100,
    healthy: (fleetSummary.value.healthyCount / total) * 100,
  }
})

function exportPackage(): void {
  printError.value = ''
  try {
    window.print()
  } catch {
    printError.value = 'The browser print dialog could not open. Try again, or use your browser\'s print shortcut directly.'
  }
}
</script>

<template>
  <main class="screen screen--wide">
    <section v-if="isLoading" class="load-state" aria-live="polite">
      <span class="load-state__pulse"></span>
      <div><strong>Building the evidence package</strong><span>Loading the latest dispatch artifact…</span></div>
    </section>

    <template v-else-if="dispatch && fleetSummary">
      <header class="page-head no-print">
        <div>
          <h1>Reports</h1>
          <p>A readable evidence package built from what this product already computed — the decision, its calculations, its assumptions, every source's own status, inspection evidence, the work order and recovery status.</p>
        </div>
        <button type="button" class="btn-primary" @click="exportPackage"><Printer :size="15" aria-hidden="true" /> Print / export PDF</button>
      </header>

      <NoticeCallout v-if="printError" tone="critical" class="no-print">
        {{ printError }}
        <button type="button" class="retry" @click="exportPackage"><RotateCcw :size="13" aria-hidden="true" /> Try again</button>
      </NoticeCallout>

      <section class="fleet-summary" aria-labelledby="fleet-summary-title">
        <h2 id="fleet-summary-title">Fleet summary — {{ fleetSummary.reportingMonth }}</h2>
        <dl class="fleet-summary__grid">
          <div><dt>Sites</dt><dd>{{ fleetSummary.siteCount }}</dd></div>
          <div><dt>Dispatch</dt><dd>{{ fleetSummary.dispatchCount }}</dd></div>
          <div><dt>Monitor</dt><dd>{{ fleetSummary.monitorCount }}</dd></div>
          <div><dt>Healthy</dt><dd>{{ fleetSummary.healthyCount }}</dd></div>
          <div><dt>Total at risk</dt><dd>{{ formatRinggit(fleetSummary.totalRmAtRisk) }}/month</dd></div>
          <div><dt>Trips recommended</dt><dd>{{ fleetSummary.tripsRecommended }}</dd></div>
          <div><dt>Trips avoided</dt><dd>{{ fleetSummary.tripsAvoided }}</dd></div>
          <div><dt>Estimated saving</dt><dd>{{ formatRinggit(fleetSummary.estimatedSavingRm) }}/month</dd></div>
        </dl>
        <div v-if="fleetProportions" class="fleet-summary__bar" role="img" aria-label="Fleet composition: dispatch, monitor and healthy sites">
          <span class="tone--critical" :style="{ width: `${fleetProportions.dispatch}%` }" title="Dispatch"></span>
          <span class="tone--warning" :style="{ width: `${fleetProportions.monitor}%` }" title="Monitor"></span>
          <span class="tone--good" :style="{ width: `${fleetProportions.healthy}%` }" title="Healthy"></span>
        </div>
        <p class="fleet-summary__meta">Pipeline {{ fleetSummary.pipelineVersion }} · <DataStatusBadge :status="dispatch.meta.data_status" small /></p>
      </section>

      <section class="picker no-print" aria-labelledby="picker-title">
        <label id="picker-title" for="site-picker">Site evidence package</label>
        <select id="site-picker" v-model="selectedSiteId">
          <option v-for="site in flaggedSites" :key="site.site_id" :value="site.site_id">{{ site.name }} — {{ site.status }}</option>
          <option v-if="!flaggedSites.length" :value="dispatch.sites[0]?.site_id">{{ dispatch.sites[0]?.name }}</option>
        </select>
        <p v-if="!flaggedSites.length" class="picker__empty">No site is flagged this month — the package below is for context only.</p>
      </section>

      <article v-if="evidencePackage" class="package">
        <header class="package__head">
          <div><FileDown :size="18" aria-hidden="true" /><h2>{{ evidencePackage.siteName }} — evidence package</h2></div>
          <span>{{ evidencePackage.reportingMonth }} · generated {{ new Date(evidencePackage.generatedAt).toLocaleString() }}</span>
        </header>

        <section v-if="selectedSite" class="glance" aria-label="Decision at a glance">
          <div class="glance__decision">
            <span v-if="selectedStatusMeta" class="glance__badge" :class="`tone--${selectedStatusMeta.tone}`">
              <component :is="selectedStatusMeta.icon" :size="13" aria-hidden="true" />
              {{ selectedStatusMeta.label }}
            </span>
            <strong>{{ selectedSite.economics ? formatRinggit(selectedSite.economics.rm_at_risk_monthly) : 'RM 0' }}<small>/month at risk</small></strong>
          </div>
          <div v-if="selectedSite.detection" class="glance__gauge">
            <ScoreGauge :score="selectedSite.detection.confidence" tone="warning" :size="56" />
            <span>Detector confidence</span>
          </div>
          <div v-if="selectedSite.hypothesis" class="glance__gauge">
            <ScoreGauge :score="selectedSite.hypothesis.confidence" tone="critical" :size="56" />
            <span>Hypothesis confidence</span>
          </div>
          <div v-if="selectedSite.detection" class="glance__compare">
            <span>Detector score vs threshold</span>
            <div class="glance__compare-pair">
              <strong>{{ selectedSite.detection.score.toFixed(2) }}</strong>
              <em :class="selectedSite.status !== 'healthy' ? 'tone--critical' : 'tone--good'">
                {{ selectedSite.status !== 'healthy' ? 'exceeded' : 'within range' }}
              </em>
              <strong class="glance__compare-threshold">{{ selectedSite.detection.threshold.toFixed(2) }}</strong>
            </div>
            <small>{{ selectedSite.detection.method }} · {{ selectedSite.detection.score_type }}</small>
          </div>
        </section>

        <section v-for="section in evidencePackage.sections" :key="section.id" class="package__section">
          <h3>{{ section.title }}</h3>
          <dl>
            <div v-for="line in section.lines" :key="line.label">
              <dt>{{ line.label }}</dt>
              <dd>{{ line.value }} <DataStatusBadge v-if="line.dataStatus && line.dataStatus !== 'not-applicable'" :status="line.dataStatus" small /></dd>
            </div>
          </dl>
        </section>
      </article>
    </template>
  </main>
</template>

<style scoped>
.load-state { display:flex; min-height:40vh; flex-wrap:wrap; align-items:center; justify-content:center; gap:1rem; text-align:left; color:var(--text-secondary); }
.load-state div { display:flex; flex-direction:column; gap:.2rem; }
.load-state strong { color:var(--text-primary); font-family:var(--font-display); font-size:1.05rem; }
.load-state__pulse { width:12px; height:12px; border-radius:50%; background:var(--signal-live); box-shadow:0 0 0 8px color-mix(in srgb, var(--signal-live) 16%, transparent); animation:pulse 1.6s var(--ease-out) infinite; }
@keyframes pulse { 50% { opacity:.5; transform:scale(.84); } }

.page-head { display:flex; flex-wrap:wrap; align-items:flex-start; justify-content:space-between; gap:1rem; max-width:none; margin-bottom:1.5rem; }
.page-head h1 { margin:0; font-family:var(--font-display); font-size:clamp(1.7rem,3.4vw,2.4rem); letter-spacing:-.03em; }
.page-head p { max-width:70ch; margin:.6rem 0 0; color:var(--text-secondary); font-size:.9rem; line-height:1.6; }

.retry { display:inline-flex; align-items:center; gap:.3rem; margin-top:.4rem; padding:.35rem .6rem; color:inherit; background:transparent; border:1px solid currentColor; border-radius:var(--radius-sm); font:inherit; font-size:.72rem; font-weight:700; cursor:pointer; }

.fleet-summary { margin-bottom:1.5rem; padding:1.25rem; background:var(--surface-1); border:1px solid var(--border-hairline); border-radius:var(--radius-lg); }
.fleet-summary h2 { margin:0 0 .8rem; font-family:var(--font-display); font-size:1.2rem; letter-spacing:-.02em; }
.fleet-summary__grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:.8rem; margin:0; }
.fleet-summary__grid dt { color:var(--text-muted); font-size:.62rem; letter-spacing:.05em; text-transform:uppercase; }
.fleet-summary__grid dd { margin:.2rem 0 0; font-family:var(--font-display); font-size:1.15rem; letter-spacing:-.02em; }
.fleet-summary__bar { display:flex; height:8px; margin-top:.9rem; border-radius:var(--radius-full); overflow:hidden; background:var(--surface-2); }
.fleet-summary__bar span { display:block; height:100%; }
.fleet-summary__bar .tone--critical { background:var(--status-critical); }
.fleet-summary__bar .tone--warning { background:var(--status-warning); }
.fleet-summary__bar .tone--good { background:var(--status-good); }
.fleet-summary__meta { margin:1rem 0 0; padding-top:.8rem; border-top:1px solid var(--border-hairline); color:var(--text-muted); font-size:.72rem; display:flex; align-items:center; gap:.4rem; }

.picker { display:flex; flex-wrap:wrap; align-items:center; gap:.7rem; margin-bottom:1.25rem; }
.picker label { font-size:.72rem; font-weight:700; color:var(--text-secondary); }
.picker select { min-height:44px; padding:.5rem .65rem; color:var(--text-primary); background:var(--surface-1); border:1px solid var(--baseline); border-radius:var(--radius-sm); font:inherit; font-size:.82rem; }
.picker__empty { flex-basis:100%; margin:0; color:var(--text-muted); font-size:.75rem; }

.package { padding:1.5rem; background:var(--surface-1); border:1px solid var(--border-hairline); border-radius:var(--radius-lg); }
.package__head { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:.6rem; padding-bottom:1rem; border-bottom:2px solid var(--text-primary); }
.package__head > div { display:flex; align-items:center; gap:.5rem; }
.package__head h2 { margin:0; font-family:var(--font-display); font-size:1.3rem; letter-spacing:-.02em; }
.package__head span { color:var(--text-muted); font-size:.72rem; }
.package__section { margin-top:1.1rem; padding-top:1rem; border-top:1px solid var(--border-hairline); }
.package__section h3 { margin:0 0 .6rem; font-size:.66rem; font-weight:750; letter-spacing:.06em; text-transform:uppercase; color:var(--text-muted); }
.package__section dl { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:.6rem 1.5rem; margin:0; }
.package__section dt { color:var(--text-muted); font-size:.64rem; text-transform:uppercase; letter-spacing:.04em; }
.package__section dd { margin:.15rem 0 0; display:flex; align-items:center; gap:.4rem; font-size:.84rem; color:var(--text-primary); overflow-wrap:anywhere; }

/* Decision at a glance — the visual read before the report's text sections. */
.glance { display:grid; grid-template-columns:auto auto auto 1fr; align-items:center; gap:1.5rem; padding:1rem 0; margin-top:1rem; border-top:1px dashed var(--border-hairline); border-bottom:1px dashed var(--border-hairline); }
.glance__decision { display:flex; flex-direction:column; gap:.4rem; }
.glance__badge { display:inline-flex; align-items:center; gap:.35em; width:fit-content; padding:.25em .6em; border-radius:var(--radius-full); font-size:.66rem; font-weight:700; letter-spacing:.03em; text-transform:uppercase; }
.glance__badge.tone--critical { color:var(--status-critical); background:var(--callout-critical-bg); }
.glance__badge.tone--warning { color:var(--status-warning); background:var(--callout-warning-bg); }
.glance__badge.tone--good { color:var(--success-text); background:var(--callout-good-bg); }
.glance__decision strong { font-family:var(--font-display); font-size:1.7rem; letter-spacing:-.02em; }
.glance__decision strong small { margin-left:.3rem; color:var(--text-muted); font:600 .68rem var(--font-sans); letter-spacing:0; }
.glance__gauge { display:flex; flex-direction:column; align-items:center; gap:.35rem; }
.glance__gauge span { max-width:80px; color:var(--text-muted); font-size:.62rem; text-align:center; line-height:1.3; }
.glance__compare { min-width:180px; }
.glance__compare > span { display:block; margin-bottom:.4rem; color:var(--text-muted); font-size:.64rem; text-transform:uppercase; letter-spacing:.04em; }
.glance__compare-pair { display:flex; align-items:baseline; gap:.5rem; }
.glance__compare-pair strong { font-family:var(--font-display); font-size:1.1rem; }
.glance__compare-pair em { padding:.15rem .45rem; border-radius:var(--radius-sm); font-size:.62rem; font-style:normal; font-weight:700; text-transform:uppercase; }
.glance__compare-pair em.tone--critical { color:var(--status-critical); background:var(--callout-critical-bg); }
.glance__compare-pair em.tone--good { color:var(--success-text); background:var(--callout-good-bg); }
.glance__compare-threshold { color:var(--text-muted); }
.glance__compare small { display:block; margin-top:.35rem; color:var(--text-muted); font-size:.66rem; }
@media (max-width:720px) {
  .glance { grid-template-columns:repeat(2,1fr); }
}

@media print {
  .no-print { display:none !important; }
  .screen { padding:0; max-width:none; }
  .package { border:none; padding:0; }
  * { print-color-adjust:exact; -webkit-print-color-adjust:exact; }
  .package__section { break-inside:avoid; }
}
</style>

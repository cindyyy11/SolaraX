<script setup lang="ts">
/**
 * Screen 2 — Site Detail. STUB.
 *
 * Block order on this page is fixed and not negotiable (BUILD_PLAN stage 12):
 *   1. Cohort chart, full width, top   — the differentiated work (M3)
 *   2. Explainability panel            — method, score, threshold, cohort size
 *   3. Sub-site breakdown              — only where per-inverter channels exist
 *   4. Thermal evidence                — supporting only (M5), never leads
 *
 * Leading with imagery invites direct comparison against Sitemark and Scopito on
 * their strongest ground. The cohort chart is the thing that sells the product.
 *
 * Currently renders identity and the explainability panel only. The ECharts
 * cohort overlay is the next piece of work.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, ArrowRight, CircleSlash } from '@lucide/vue'
import {
  loadDispatch,
  findSite,
  findCohort,
  formatRinggit,
  formatCapacity,
  isVisionApiConfigured,
} from '@/services/api'
import type { Dispatch } from '@/types/dispatch'
import DataStatusBadge from '@/components/DataStatusBadge.vue'
import CohortChart from '@/components/CohortChart.vue'
import InverterPanel from '@/components/InverterPanel.vue'
import InverterThermalMap from '@/components/InverterThermalMap.vue'
import VisionEvidence from '@/components/VisionEvidence.vue'
import NoticeCallout from '@/components/NoticeCallout.vue'
import PerformanceModel from '@/components/PerformanceModel.vue'
import SiteComparison from '@/components/SiteComparison.vue'
import SiteDigitalTwin from '@/components/SiteDigitalTwin.vue'
import ScenarioLab from '@/components/ScenarioLab.vue'
import type { ScenarioResult } from '@/types/scenario'

const route = useRoute()
const dispatch = ref<Dispatch | null>(null)
const isLoading = ref(true)

/** Whether an M5 vision service is reachable from wherever this is served. */
const visionAvailable = isVisionApiConfigured()
const scenarioResult = ref<ScenarioResult | undefined>()
const scenarioLabel = ref('')
function updateScenario(payload: { label: string; result: ScenarioResult }) {
  scenarioLabel.value = payload.label
  scenarioResult.value = payload.result
}

onMounted(async () => {
  const result = await loadDispatch()
  dispatch.value = result.dispatch
  isLoading.value = false
})

const site = computed(() => {
  if (!dispatch.value) return undefined
  return findSite(dispatch.value, String(route.params.siteId))
})

const cohort = computed(() => {
  if (!dispatch.value || !site.value) return undefined
  return findCohort(dispatch.value, site.value.cohort_id)
})
</script>

<template>
  <main class="screen">
    <p v-if="isLoading">Loading…</p>
    <p v-else-if="!site">No site with id {{ route.params.siteId }}.</p>

    <template v-else>
      <RouterLink to="/" class="back">
        <ArrowLeft :size="14" aria-hidden="true" /> Dispatch list
      </RouterLink>

      <header class="head">
        <div>
          <h1 class="head__name">{{ site.name }}</h1>
          <p class="head__meta">
            {{ formatCapacity(site.capacity_kwp) }} · {{ site.address }} ·
            {{ site.source_system_id }}
          </p>
        </div>
        <div class="head__actions">
          <DataStatusBadge :status="site.data_status" />
          <RouterLink
            v-if="site.hypothesis"
            :to="`/site/${site.site_id}/work-order`"
            class="work-order-link"
          >
            Generate work order
            <ArrowRight :size="15" aria-hidden="true" />
          </RouterLink>
        </div>
      </header>

      <!-- Excluded sites explain themselves before anything else on the page. -->
      <NoticeCallout
        v-if="site.excluded_from_analysis"
        tone="warning"
        :icon="CircleSlash"
        class="excluded"
      >
        <h2 class="excluded__title">Excluded from analysis</h2>
        <p class="excluded__detail">{{ site.excluded_from_analysis.detail }}</p>
        <dl class="excluded__facts">
          <div>
            <dt>Observed</dt>
            <dd>{{ site.excluded_from_analysis.observed_performance_index }} kWh/kWp/day</dd>
          </div>
          <div v-if="site.excluded_from_analysis.reference_performance_index">
            <dt>Fleet reference</dt>
            <dd>{{ site.excluded_from_analysis.reference_performance_index }} kWh/kWp/day</dd>
          </div>
          <div>
            <dt>Plausibility floor</dt>
            <dd>{{ site.excluded_from_analysis.threshold }} kWh/kWp/day</dd>
          </div>
          <div>
            <dt>Rule</dt>
            <dd>{{ site.excluded_from_analysis.method }}</dd>
          </div>
        </dl>
        <p class="excluded__note">
          The series below is this site's own measured output and is shown as recorded. No peer
          overlay is drawn, because the site is not being compared against its cohort.
        </p>
      </NoticeCallout>

      <PerformanceModel :site="site" />
      <SiteDigitalTwin :site="site" :scenario="scenarioResult" :scenario-label="scenarioLabel" />
      <ScenarioLab :site="site" @change="updateScenario" />
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
    </template>
  </main>
</template>

<style scoped>
.screen {
  max-width: 1380px;
  margin: 0 auto;
  padding: clamp(1.25rem, 2.8vw, 2.75rem);
}

.back {
  display: inline-flex;
  align-items: center;
  gap: 0.35em;
  margin-bottom: 1rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius-sm);
}

.back:hover {
  color: var(--action-text);
}

.head {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-hairline);
}

.head__name {
  margin: 0;
  max-width: 26ch;
  font-size: clamp(2rem, 3.5vw, 3.15rem);
  line-height: 1;
  letter-spacing: -0.04em;
  text-wrap: balance;
}

.head__meta {
  margin: 0.25rem 0 0;
  font-size: 0.82rem;
  color: var(--text-muted);
}

.head__actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
}

/*
 * The one primary action on this screen — the button that moves a flagged
 * site into the DETECT -> VERIFY flow. Filled amber with navy ink, per
 * theme.css's --action-fill / --action-ink pairing: this is the role brand
 * color exists to play, used exactly once per screen.
 */
.work-order-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.9rem;
  background: var(--action-fill);
  color: var(--action-ink);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  transition:
    background-color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}

.work-order-link:hover {
  background: var(--action-fill-hover);
}

.work-order-link:active {
  transform: scale(0.97);
}

.work-order-link svg {
  transition: transform var(--duration-fast) var(--ease-out);
}

.work-order-link:hover svg {
  transform: translateX(2px);
}

.block {
  margin: 1.5rem 0;
}

/* Visual treatment (tint, border, icon) comes from NoticeCallout, whose root
   element also carries this "excluded" class (Vue merges a component's
   fallthrough class onto its single root). This only adds the extra
   breathing room this particular callout's richer content — a heading, a
   fact grid, a closing note — needs over NoticeCallout's compact default.
   ".excluded.callout" is a compound selector on that one shared element, with
   higher specificity than NoticeCallout's own ".callout" rule, so it wins
   deterministically rather than depending on which component's scoped CSS
   the bundler happens to emit first. */
.excluded.callout {
  margin: 1.5rem 0;
  padding: 1.1rem 1.25rem;
}

.excluded :deep(.callout__body) {
  width: 100%;
}

.excluded__title {
  margin: 0 0 0.5rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.excluded__detail {
  margin: 0 0 1rem;
  font-size: 0.9rem;
  line-height: 1.6;
}

.excluded__facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.6rem 1.5rem;
  margin: 0 0 0.9rem;
}

.excluded__facts div {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-hairline);
}

.excluded__facts dt {
  font-size: 0.66rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.excluded__facts dd {
  margin: 0;
  font-size: 0.86rem;
  overflow-wrap: anywhere;
}

.excluded__note {
  margin: 0;
  padding-top: 0.6rem;
  border-top: 1px solid var(--border-hairline);
  font-size: 0.76rem;
  line-height: 1.5;
  color: var(--text-muted);
}

.empty {
  margin: 0;
  padding: 2rem;
  text-align: center;
  font-size: 0.85rem;
  color: var(--text-muted);
  background: var(--surface-1);
  border: 1px dashed var(--baseline);
  border-radius: var(--radius-md);
}

.panel {
  padding: 1.25rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
  box-shadow: var(--elevation-1);
}

.panel__heading {
  margin: 0 0 0.5rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.panel__summary {
  margin: 0 0 0.5rem;
  font-size: 1.05rem;
  font-weight: 600;
}

.panel__detail {
  margin: 0 0 1rem;
  line-height: 1.6;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 0.6rem 1.5rem;
  margin: 0;
}

.facts div {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-hairline);
}

.facts dt {
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.facts dd {
  margin: 0;
  font-size: 0.88rem;
  overflow-wrap: anywhere;
}

.caution {
  margin: 1rem 0 0;
}
</style>

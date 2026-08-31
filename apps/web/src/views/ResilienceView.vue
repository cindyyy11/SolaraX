<script setup lang="ts">
/**
 * Resilience — the fourth of the five connected surfaces from the
 * closed-loop operations intelligence design
 * (docs/superpowers/specs/2026-08-30-solarax-closed-loop-operations-intelligence-design.md).
 *
 * Three sections, each explainable rather than an opaque score, each led by
 * a visual rather than a paragraph — the long-form reasoning still exists,
 * behind a disclosure, for anyone who wants it:
 * 1. Six resilience categories: a headline bar chart, then one gauge and a
 *    short headline per card. Every category traces to a named
 *    `dispatch.json` signal or is explicitly reported as not connected —
 *    never a fabricated number standing in for missing telemetry.
 * 2. Cyber-physical readiness — a taxonomy of what a real detection system
 *    would classify, labelled simulated throughout. Two of these are also
 *    runnable, interactively, in a site's Scenario Lab.
 * 3. Integration readiness — what this product actually connects to today,
 *    against what a production deployment would need.
 */
import { computed, onMounted, ref } from 'vue'
import {
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  Radio,
  Link2,
  Unlink,
  CircleDashed,
  Cog,
  Zap,
  Eye,
} from '@lucide/vue'
import { loadDispatch } from '@/services/api'
import type { Dispatch } from '@/types/dispatch'
import { cyberPhysicalScenarios, integrationReadiness, resilienceSignals } from '@/services/resilienceEngine'
import type { CyberPhysicalCategory, IntegrationState, ResilienceStatus } from '@/types/operations'
import NoticeCallout from '@/components/NoticeCallout.vue'
import ScoreGauge from '@/components/ScoreGauge.vue'
import ResilienceScoreChart from '@/components/ResilienceScoreChart.vue'

const dispatch = ref<Dispatch | null>(null)
const isLoading = ref(true)

onMounted(async () => {
  const result = await loadDispatch()
  dispatch.value = result.dispatch
  isLoading.value = false
})

const signals = computed(() => (dispatch.value ? resilienceSignals(dispatch.value) : []))
const integrations = computed(() => (dispatch.value ? integrationReadiness(dispatch.value) : []))

const STATUS_META: Record<ResilienceStatus, { label: string; icon: typeof ShieldCheck; tone: 'good' | 'warning' | 'critical' | 'neutral' }> = {
  nominal: { label: 'Nominal', icon: ShieldCheck, tone: 'good' },
  watch: { label: 'Watch', icon: ShieldQuestion, tone: 'warning' },
  exposed: { label: 'Exposed', icon: ShieldAlert, tone: 'critical' },
  'not-connected': { label: 'Not connected', icon: CircleDashed, tone: 'neutral' },
}

const INTEGRATION_META: Record<IntegrationState, { label: string; icon: typeof Link2; tone: string }> = {
  connected: { label: 'Connected', icon: Link2, tone: 'good' },
  partial: { label: 'Partial', icon: Radio, tone: 'warning' },
  'not-connected': { label: 'Not connected', icon: Unlink, tone: 'neutral' },
}

/** Counts behind the integration summary strip — a single-glance read
 * before the detailed table. */
const integrationCounts = computed(() => {
  const counts = { connected: 0, partial: 0, 'not-connected': 0 } as Record<IntegrationState, number>
  for (const row of integrations.value) counts[row.state] += 1
  return counts
})
const integrationTotal = computed(() => integrations.value.length || 1)

const CATEGORY_ORDER: CyberPhysicalCategory[] = ['equipment-anomaly', 'telemetry-fault', 'grid-event', 'suspicious-pattern']
const CATEGORY_ICON: Record<CyberPhysicalCategory, typeof Cog> = {
  'equipment-anomaly': Cog,
  'telemetry-fault': Radio,
  'grid-event': Zap,
  'suspicious-pattern': Eye,
}
const scenariosByCategory = computed(() =>
  CATEGORY_ORDER.map((category) => ({
    category,
    icon: CATEGORY_ICON[category],
    label: cyberPhysicalScenarios.find((s) => s.category === category)?.categoryLabel ?? category,
    items: cyberPhysicalScenarios.filter((s) => s.category === category),
  })),
)
</script>

<template>
  <main class="screen screen--wide">
    <section v-if="isLoading" class="load-state" aria-live="polite">
      <span class="load-state__pulse"></span>
      <div><strong>Assessing fleet resilience</strong><span>Loading the latest dispatch artifact…</span></div>
    </section>

    <template v-else>
      <header class="page-head">
        <div>
          <h1>Resilience</h1>
          <p>
            Exposure across generation, equipment, weather, grid, telemetry and communications —
            each category names its own signal, or reports that no live source is connected.
          </p>
        </div>
      </header>

      <section class="card card--interactive chart-card" aria-label="Resilience score chart">
        <ResilienceScoreChart :signals="signals" />
      </section>

      <section class="signals" aria-label="Resilience categories">
        <article v-for="(signal, index) in signals" :key="signal.category" class="card card--interactive stagger-in signal-card" :style="{ animationDelay: `${index * 40}ms` }">
          <header class="signal-card__head">
            <ScoreGauge :score="signal.score" :tone="STATUS_META[signal.status].tone" :connected="signal.basis !== 'not-connected'" />
            <div>
              <span class="signal-card__status" :class="`tone--${STATUS_META[signal.status].tone}`">
                <component :is="STATUS_META[signal.status].icon" :size="12" aria-hidden="true" />
                {{ STATUS_META[signal.status].label }}
              </span>
              <h2>{{ signal.label }}</h2>
            </div>
          </header>
          <p class="signal-card__headline">{{ signal.headline }}</p>
          <ul v-if="signal.contributingSignals.length" class="signal-card__list">
            <li v-for="item in signal.contributingSignals" :key="item">{{ item }}</li>
          </ul>
          <details class="signal-card__more">
            <summary>Why this reading <span class="signal-card__basis">{{ signal.basis }}</span></summary>
            <p>{{ signal.explanation }}</p>
          </details>
        </article>
      </section>

      <section class="card cyber" aria-labelledby="cyber-title">
        <header class="cyber__header">
          <h2 id="cyber-title">Cyber-physical readiness</h2>
          <p>
            A taxonomy of what a real detection system would classify, not a live detector. Every
            entry below is a labelled, simulated example.
          </p>
        </header>
        <NoticeCallout tone="warning" compact>
          Simulated scenarios and readiness indicators only. This product does not detect real
          cyber-physical attacks.
        </NoticeCallout>
        <div class="cyber__grid">
          <section v-for="group in scenariosByCategory" :key="group.category" class="cyber__category">
            <h3><component :is="group.icon" :size="14" aria-hidden="true" /> {{ group.label }} <span class="cyber__count">{{ group.items.length }}</span></h3>
            <details v-for="item in group.items" :key="item.id" class="cyber__item">
              <summary>{{ item.title }}</summary>
              <p>{{ item.description }}</p>
              <p class="cyber__requires"><span>Would require</span>{{ item.wouldRequire }}</p>
            </details>
          </section>
        </div>
      </section>

      <section class="card integration" aria-labelledby="integration-title">
        <header class="integration__header">
          <h2 id="integration-title">Integration readiness</h2>
          <p>What this product actually connects to today, and what a live connection would need.</p>
        </header>

        <div class="integration__summary">
          <div class="integration__stat"><strong>{{ integrationCounts.connected }}</strong><span>Connected</span></div>
          <div class="integration__stat"><strong>{{ integrationCounts.partial }}</strong><span>Partial</span></div>
          <div class="integration__stat"><strong>{{ integrationCounts['not-connected'] }}</strong><span>Not connected</span></div>
          <div class="integration__bar" role="img" aria-label="Proportion of systems connected, partial, and not connected">
            <span class="tone--good" :style="{ width: `${(integrationCounts.connected / integrationTotal) * 100}%` }"></span>
            <span class="tone--warning" :style="{ width: `${(integrationCounts.partial / integrationTotal) * 100}%` }"></span>
            <span class="tone--neutral" :style="{ width: `${(integrationCounts['not-connected'] / integrationTotal) * 100}%` }"></span>
          </div>
        </div>

        <div class="integration__table" role="table">
          <div class="integration__row integration__row--head" role="row">
            <span>System</span><span>State</span><span>Status</span><span>Expected data contract</span>
          </div>
          <div v-for="row in integrations" :key="row.system" class="integration__row" role="row">
            <span class="integration__system">{{ row.label }}</span>
            <span class="integration__state" :class="`tone--${INTEGRATION_META[row.state].tone}`">
              <component :is="INTEGRATION_META[row.state].icon" :size="13" aria-hidden="true" />
              {{ INTEGRATION_META[row.state].label }}
            </span>
            <span class="integration__detail">{{ row.detail }}</span>
            <span class="integration__contract">{{ row.expectedContract }}</span>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.load-state { display:flex; min-height:40vh; flex-wrap:wrap; align-items:center; justify-content:center; gap:1rem; text-align:left; color:var(--text-secondary); }
.load-state div { display:flex; flex-direction:column; gap:.2rem; }
.load-state strong { color:var(--text-primary); font-family:var(--font-display); font-size:1.05rem; }
.load-state__pulse { width:12px; height:12px; border-radius:50%; background:var(--signal-live); box-shadow:0 0 0 8px color-mix(in srgb, var(--signal-live) 16%, transparent); animation:pulse 1.6s var(--ease-out) infinite; }
@keyframes pulse { 50% { opacity:.5; transform:scale(.84); } }

.page-head { max-width:78ch; margin-bottom:1.25rem; }
.page-head h1 { margin:0; font-family:var(--font-display); font-size:clamp(1.7rem,3.4vw,2.4rem); letter-spacing:-.03em; }
.page-head p { margin:.6rem 0 0; color:var(--text-secondary); font-size:.9rem; line-height:1.6; }

.chart-card { padding:1.1rem 1.25rem; margin-bottom:1.5rem; }

/* Badge tone — tint + text, on the status chip and the integration state pill. */
.signal-card__status.tone--good, .integration__state.tone--good { color:var(--success-text); background:var(--callout-good-bg); }
.signal-card__status.tone--warning, .integration__state.tone--warning { color:var(--status-warning); background:var(--callout-warning-bg); }
.signal-card__status.tone--critical, .integration__state.tone--critical { color:var(--status-critical); background:var(--callout-critical-bg); }
.signal-card__status.tone--neutral, .integration__state.tone--neutral { color:var(--text-muted); background:var(--surface-2); }
/* Solid-fill tone — the proportion bar segments only. */
.integration__bar .tone--good { background:var(--status-good); }
.integration__bar .tone--warning { background:var(--status-warning); }
.integration__bar .tone--critical { background:var(--status-critical); }
.integration__bar .tone--neutral { background:var(--baseline); }

.signals { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1rem; margin-bottom:1.5rem; }
.signal-card { padding:1.1rem; }
.signal-card__head { display:flex; align-items:center; gap:.85rem; }
.signal-card__status { display:inline-flex; align-items:center; gap:.3rem; padding:.2rem .5rem; border-radius:var(--radius-full); font-size:.6rem; font-weight:750; letter-spacing:.03em; text-transform:uppercase; }
.signal-card h2 { margin:.35rem 0 0; font-family:var(--font-display); font-size:1.05rem; letter-spacing:-.02em; }
.signal-card__headline { margin:.7rem 0 0; color:var(--text-primary); font-size:.8rem; font-weight:600; line-height:1.5; }
.signal-card__list { margin:.6rem 0 0; padding:0; list-style:none; display:flex; flex-wrap:wrap; gap:.35rem; }
.signal-card__list li { padding:.18rem .45rem; color:var(--text-muted); background:var(--surface-2); border-radius:var(--radius-sm); font-size:.62rem; }
.signal-card__more { margin-top:.7rem; padding-top:.6rem; border-top:1px solid var(--border-hairline); }
.signal-card__more summary { display:flex; align-items:center; gap:.4rem; color:var(--action-text); font-size:.68rem; font-weight:700; cursor:pointer; list-style:none; }
.signal-card__more summary::-webkit-details-marker { display:none; }
.signal-card__basis { color:var(--text-muted); font-weight:600; text-transform:uppercase; letter-spacing:.04em; }
.signal-card__more p { margin:.5rem 0 0; color:var(--text-secondary); font-size:.74rem; line-height:1.55; }

.cyber { padding:1.25rem; margin-bottom:1.5rem; }
.cyber__header h2 { margin:0; font-family:var(--font-display); font-size:1.3rem; letter-spacing:-.02em; }
.cyber__header p { max-width:78ch; margin:.5rem 0 1rem; color:var(--text-secondary); font-size:.82rem; line-height:1.6; }
.cyber__grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1rem; margin-top:1.1rem; }
.cyber__category h3 { display:flex; align-items:center; gap:.4rem; margin:0 0 .6rem; font-size:.66rem; font-weight:750; letter-spacing:.06em; text-transform:uppercase; color:var(--text-muted); }
.cyber__count { margin-left:auto; padding:.05rem .4rem; color:var(--text-secondary); background:var(--surface-2); border-radius:var(--radius-full); font-size:.6rem; }
.cyber__item { margin-bottom:.5rem; background:var(--surface-2); border-radius:var(--radius-md); }
.cyber__item summary { padding:.6rem .75rem; font-size:.78rem; font-weight:650; cursor:pointer; list-style:none; }
.cyber__item summary::-webkit-details-marker { display:none; }
.cyber__item summary::before { content:'▸ '; color:var(--text-muted); }
.cyber__item[open] summary::before { content:'▾ '; }
.cyber__item p { margin:0 .75rem .6rem; color:var(--text-secondary); font-size:.72rem; line-height:1.5; }
.cyber__requires { color:var(--text-muted)!important; font-size:.66rem!important; }
.cyber__requires span { display:block; font-weight:750; letter-spacing:.04em; text-transform:uppercase; color:var(--text-muted); }

.integration { padding:1.25rem; }
.integration__header h2 { margin:0; font-family:var(--font-display); font-size:1.3rem; letter-spacing:-.02em; }
.integration__header p { margin:.5rem 0 1rem; color:var(--text-secondary); font-size:.82rem; }
.integration__summary { display:grid; grid-template-columns:repeat(3,auto) 1fr; align-items:center; gap:1.25rem; padding:.9rem 1rem; margin-bottom:1rem; background:var(--surface-2); border-radius:var(--radius-md); }
.integration__stat { display:flex; flex-direction:column; }
.integration__stat strong { font-family:var(--font-display); font-size:1.5rem; letter-spacing:-.02em; }
.integration__stat span { color:var(--text-muted); font-size:.62rem; text-transform:uppercase; letter-spacing:.04em; }
.integration__bar { display:flex; height:8px; border-radius:var(--radius-full); overflow:hidden; background:var(--surface-1); }
.integration__bar span { display:block; height:100%; }
.integration__table { min-width:0; overflow-x:auto; }
.integration__row { display:grid; grid-template-columns:minmax(140px,.9fr) minmax(120px,.6fr) minmax(220px,1.4fr) minmax(220px,1.4fr); gap:.9rem; align-items:center; padding:.75rem 0; border-top:1px solid var(--border-hairline); }
.integration__row--head { color:var(--text-muted); font-size:.6rem; font-weight:750; letter-spacing:.05em; text-transform:uppercase; border-top:0; }
.integration__system { font-weight:650; font-size:.82rem; }
.integration__state { display:inline-flex; align-items:center; gap:.3rem; padding:.2rem .5rem; width:fit-content; border-radius:var(--radius-full); font-size:.62rem; font-weight:750; letter-spacing:.03em; text-transform:uppercase; }
.integration__detail,.integration__contract { color:var(--text-secondary); font-size:.74rem; line-height:1.5; }

@media (max-width:900px) {
  .integration__summary { grid-template-columns:repeat(3,auto); }
  .integration__bar { grid-column:1 / -1; }
  .integration__row { grid-template-columns:1fr; gap:.3rem; padding:.9rem 0; }
  .integration__row--head { display:none; }
  .integration__detail::before { content:'Status: '; color:var(--text-muted); }
  .integration__contract::before { content:'Expected contract: '; color:var(--text-muted); }
}
@media (max-width:560px) {
  .signal-card__head { flex-wrap:wrap; }
}
</style>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowRight, Users } from '@lucide/vue'
import type { Dispatch } from '@/types/dispatch'
import type { InterventionCandidate } from '@/types/operations'
import { optimizeInterventions } from '@/services/interventionOptimizer'

const props = defineProps<{ dispatch: Dispatch }>()
const crewCapacity = ref(Math.max(1, props.dispatch.fleet_summary.trips_recommended))

const candidates = computed<InterventionCandidate[]>(() => props.dispatch.sites
  .filter((site) => site.economics && site.status !== 'healthy' && !site.excluded_from_analysis)
  .map((site) => ({
    siteId:site.site_id,
    siteName:site.name,
    recoverableRm:site.economics?.rm_at_risk_monthly ?? 0,
    confidence:site.detection?.confidence ?? 0,
    safetyUrgency:site.status === 'dispatch' ? .65 : .25,
    travelEffort:.5,
    travelEvidenceLevel:'simulated',
  })))

const recommendations = computed(() => optimizeInterventions(candidates.value, crewCapacity.value))
</script>

<template>
  <section class="optimizer" aria-labelledby="optimizer-title">
    <header class="optimizer__header">
      <div><h2 id="optimizer-title">Intervention optimizer</h2><p>Test crew capacity against recoverable value, evidence confidence and bounded operational assumptions.</p></div>
      <label><Users :size="15" aria-hidden="true" /><span>Available crews</span><input v-model.number="crewCapacity" type="number" min="0" :max="candidates.length" /><small>SIMULATED INPUT</small></label>
    </header>

    <div v-if="recommendations.length" class="optimizer__table" role="table" aria-label="Explainable intervention ranking">
      <div class="optimizer__row optimizer__row--head" role="row"><span>Priority</span><span>Site and decision</span><span>Recoverable value</span><span>Confidence</span><span>Score composition</span></div>
      <details v-for="item in recommendations" :key="item.siteId" class="optimizer__item">
        <summary class="optimizer__row" role="row">
          <span class="optimizer__rank">{{ item.rank }}</span>
          <span><strong>{{ item.siteName }}</strong><small :class="`decision--${item.decision}`">{{ item.decision === 'dispatch-now' ? 'Dispatch now' : 'Monitor' }}</small></span>
          <span><strong>RM {{ item.recoverableRm.toLocaleString() }}</strong><small>/month projected</small></span>
          <span>
            <strong>{{ Math.round(item.confidence * 100) }}%</strong>
            <span class="optimizer__meter" role="img" :aria-label="`${Math.round(item.confidence * 100)} percent confidence`"><span :style="{ width: `${item.confidence * 100}%` }"></span></span>
          </span>
          <span class="optimizer__score">
            <strong>{{ Math.round(item.score * 100) }}<small>/100</small></strong>
            <span class="optimizer__stack" role="img" :aria-label="`Score ${Math.round(item.score * 100)} of 100: ${item.reasons.join(' ')}`">
              <span class="optimizer__stack-seg optimizer__stack-seg--value" :style="{ width: `${item.contributions.value}%` }" :title="`Recoverable value: ${item.contributions.value} of 45`"></span>
              <span class="optimizer__stack-seg optimizer__stack-seg--confidence" :style="{ width: `${item.contributions.confidence}%` }" :title="`Evidence confidence: ${item.contributions.confidence} of 25`"></span>
              <span class="optimizer__stack-seg optimizer__stack-seg--safety" :style="{ width: `${item.contributions.safety}%` }" :title="`Safety urgency: ${item.contributions.safety} of 20`"></span>
              <span class="optimizer__stack-seg optimizer__stack-seg--effort" :style="{ width: `${item.contributions.effort}%` }" :title="`Travel efficiency: ${item.contributions.effort} of 10`"></span>
            </span>
          </span>
        </summary>
        <div class="optimizer__explanation">
          <ul class="optimizer__legend">
            <li><span class="optimizer__stack-seg optimizer__stack-seg--value"></span>Value {{ item.contributions.value }}/45</li>
            <li><span class="optimizer__stack-seg optimizer__stack-seg--confidence"></span>Confidence {{ item.contributions.confidence }}/25</li>
            <li><span class="optimizer__stack-seg optimizer__stack-seg--safety"></span>Safety {{ item.contributions.safety }}/20</li>
            <li><span class="optimizer__stack-seg optimizer__stack-seg--effort"></span>Travel {{ item.contributions.effort }}/10</li>
          </ul>
          <p>Travel effort and safety urgency are bounded planning assumptions. They do not replace the measured dispatch ranking.</p>
          <RouterLink :to="`/site/${item.siteId}`">Review site evidence <ArrowRight :size="14" aria-hidden="true" /></RouterLink>
        </div>
      </details>
    </div>
    <p v-else class="optimizer__empty">No eligible dispatch or monitor candidates have sufficient economic evidence.</p>
  </section>
</template>

<style scoped>
.optimizer { margin:1.75rem 0; overflow:hidden; background:var(--surface-1); border:1px solid var(--border-hairline); border-radius:var(--radius-lg); }
.optimizer__header { display:flex; align-items:center; justify-content:space-between; gap:1.25rem; padding:1.1rem 1.25rem; border-bottom:1px solid var(--border-hairline); }
.optimizer__header h2 { margin:0; font-family:var(--font-display); font-size:clamp(1.2rem,2vw,1.55rem); letter-spacing:-.03em; }
.optimizer__header p { max-width:68ch; margin:.35rem 0 0; color:var(--text-secondary); font-size:.76rem; }
.optimizer__header label { display:grid; grid-template-columns:auto auto 58px; align-items:center; gap:.25rem .4rem; flex:0 0 auto; }
.optimizer__header label > span { color:var(--text-secondary); font-size:.68rem; font-weight:700; }
.optimizer__header input { width:58px; min-height:40px; padding:.35rem; color:var(--text-primary); background:var(--surface-2); border:1px solid var(--baseline); border-radius:var(--radius-sm); font:700 .8rem var(--font-sans); text-align:center; }
.optimizer__header label small { grid-column:2 / -1; color:var(--text-muted); font-size:.52rem; font-weight:800; letter-spacing:.07em; }
.optimizer__table { min-width:0; }
.optimizer__row { display:grid; grid-template-columns:70px minmax(190px,1.4fr) repeat(3,minmax(115px,.7fr)); gap:.75rem; align-items:center; padding:.8rem 1.1rem; }
.optimizer__row--head { color:var(--text-muted); background:var(--surface-2); font-size:.6rem; font-weight:750; letter-spacing:.05em; text-transform:uppercase; }
.optimizer__item { border-top:1px solid var(--border-hairline); }
.optimizer__item:first-of-type { border-top:0; }
.optimizer__item summary { cursor:pointer; list-style:none; }
.optimizer__item summary::-webkit-details-marker { display:none; }
.optimizer__item summary:hover { background:var(--surface-selected); }
.optimizer__row > span { min-width:0; }
.optimizer__row strong,.optimizer__row small { display:block; }
.optimizer__row strong { font-size:.76rem; overflow-wrap:anywhere; }
.optimizer__row small { margin-top:.18rem; color:var(--text-muted); font-size:.6rem; }
.optimizer__rank { font-family:var(--font-display); font-size:1.25rem; color:var(--text-muted); }
.optimizer__row .decision--dispatch-now { color:var(--status-critical); font-weight:750; }
.optimizer__row .decision--monitor { color:var(--status-monitor); font-weight:750; }

/* Confidence meter — a thin filled track under the percentage. */
.optimizer__meter { display:block; width:100%; height:4px; margin-top:.3rem; background:var(--surface-2); border-radius:var(--radius-full); overflow:hidden; }
.optimizer__meter span { display:block; height:100%; background:var(--series-1); border-radius:var(--radius-full); }

/* Score composition — a segmented bar so the four weighted inputs are seen,
   not just read as a bulleted list. Same four colours in the row bar, the
   expanded legend, and the details' :title tooltips. */
.optimizer__score strong small { color:var(--text-muted); font-weight:600; }
.optimizer__stack { display:flex; width:100%; height:8px; margin-top:.35rem; border-radius:var(--radius-full); overflow:hidden; background:var(--surface-2); }
.optimizer__stack-seg { display:block; height:100%; }
.optimizer__stack-seg--value { background:var(--series-1); }
.optimizer__stack-seg--confidence { background:var(--series-2); }
.optimizer__stack-seg--safety { background:var(--series-3); }
.optimizer__stack-seg--effort { background:var(--baseline); }
.optimizer__legend { display:flex; flex-wrap:wrap; gap:.3rem 1rem; margin:0; padding:0; list-style:none; color:var(--text-secondary); font-size:.65rem; }
.optimizer__legend li { display:inline-flex; align-items:center; gap:.35rem; }
.optimizer__legend .optimizer__stack-seg { display:inline-block; width:9px; height:9px; border-radius:2px; }

.optimizer__explanation { display:grid; grid-template-columns:minmax(0,1fr) minmax(220px,.55fr) auto; gap:1rem; align-items:center; padding:.9rem 1.1rem 1.1rem 91px; background:var(--surface-2); }
.optimizer__explanation p { margin:0; color:var(--text-muted); font-size:.62rem; line-height:1.45; }
.optimizer__explanation a { min-height:40px; display:inline-flex; align-items:center; gap:.35rem; padding:.5rem .65rem; color:var(--action-ink); background:var(--action-fill); border-radius:var(--radius-sm); font-size:.67rem; font-weight:750; text-decoration:none; white-space:nowrap; }
.optimizer__empty { margin:0; padding:1.5rem; color:var(--text-muted); text-align:center; }
/* Confidence's number drops first on a narrow screen; the score
   composition bar — the strongest visual here — stays, now full-width on
   its own row rather than squeezed into a column. */
@media (max-width:850px) { .optimizer__header { align-items:flex-start; flex-direction:column; } .optimizer__row--head { display:none; } .optimizer__row { grid-template-columns:45px minmax(0,1fr) 1fr; row-gap:.4rem; } .optimizer__row > span:nth-child(4) { display:none; } .optimizer__row > span:nth-child(5) { grid-column:1 / -1; } .optimizer__explanation { grid-template-columns:1fr; padding-left:1.1rem; } }
@media (max-width:560px) { .optimizer__header label { width:100%; grid-template-columns:auto 1fr 58px; } .optimizer__row { grid-template-columns:38px minmax(0,1fr); } .optimizer__row > span:nth-child(3) { grid-column:2; } .optimizer__row > span:nth-child(5) { grid-column:1 / -1; } .optimizer__legend { flex-direction:column; } .optimizer__explanation a { justify-content:center; } }
</style>

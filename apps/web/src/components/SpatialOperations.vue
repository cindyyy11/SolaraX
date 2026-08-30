<script setup lang="ts">
import { ref } from 'vue'
import type { Site } from '@/types/dispatch'
import type { ScenarioResult } from '@/types/scenario'
import ScenarioLab from '@/components/ScenarioLab.vue'
import SiteDigitalTwin from '@/components/SiteDigitalTwin.vue'

defineProps<{ site: Site }>()

const scenarioResult = ref<ScenarioResult>()
const scenarioId = ref('')
const scenarioLabel = ref('')

function updateScenario(payload: { id: string; label: string; result: ScenarioResult }) {
  scenarioId.value = payload.id
  scenarioLabel.value = payload.label
  scenarioResult.value = payload.result
}
</script>

<template>
  <section class="spatial" aria-labelledby="spatial-title">
    <header class="spatial__header">
      <div>
        <h2 id="spatial-title">Spatial operations</h2>
        <p>Configure a bounded scenario and inspect its illustrative physical response in the same workspace.</p>
      </div>
      <div class="spatial__state"><i></i><span>{{ scenarioLabel || 'Preparing scenario' }}</span><small>SIMULATED</small></div>
    </header>

    <div class="spatial__workspace">
      <aside class="spatial__controls" aria-label="Scenario configuration">
        <ScenarioLab :site="site" embedded @change="updateScenario" />
      </aside>
      <div class="spatial__scene">
        <SiteDigitalTwin
          :site="site"
          :scenario="scenarioResult"
          :scenario-id="scenarioId"
          :scenario-label="scenarioLabel"
          embedded
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.spatial { margin:1.75rem 0; overflow:hidden; background:var(--surface-1); border:1px solid var(--border-hairline); border-radius:var(--radius-lg); box-shadow:var(--elevation-1); }
.spatial__header { min-height:84px; display:flex; align-items:center; justify-content:space-between; gap:1.5rem; padding:1rem 1.2rem; border-bottom:1px solid var(--border-hairline); }
.spatial__header h2 { margin:0; font-family:var(--font-display); font-size:clamp(1.25rem,2.2vw,1.7rem); letter-spacing:-.035em; }
.spatial__header p { max-width:68ch; margin:.35rem 0 0; color:var(--text-secondary); font-size:.78rem; line-height:1.45; }
.spatial__state { display:grid; grid-template-columns:auto auto; align-items:center; gap:.1rem .4rem; flex:0 0 auto; padding:.55rem .7rem; color:var(--text-primary); background:var(--surface-2); border-radius:var(--radius-sm); }
.spatial__state i { grid-row:1 / 3; width:8px; height:8px; border-radius:50%; background:#54c784; box-shadow:0 0 0 4px rgba(84,199,132,.14); }
.spatial__state span { max-width:22ch; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:.72rem; font-weight:700; }
.spatial__state small { color:var(--text-muted); font-size:.55rem; font-weight:800; letter-spacing:.08em; }
.spatial__workspace { display:grid; grid-template-columns:minmax(290px,340px) minmax(0,1fr); align-items:stretch; }
.spatial__controls { min-width:0; border-right:1px solid var(--border-hairline); }
.spatial__scene { min-width:0; background:#0d1715; }
@media (max-width:1050px) { .spatial__workspace { grid-template-columns:1fr; } .spatial__controls { border-right:0; border-bottom:1px solid var(--border-hairline); } }
@media (max-width:620px) { .spatial__header { align-items:flex-start; flex-direction:column; gap:.75rem; } .spatial__state { width:100%; } }
</style>

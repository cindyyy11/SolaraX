<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Site } from '@/types/dispatch'
import type { ScenarioResult } from '@/types/scenario'
import ScenarioLab from '@/components/ScenarioLab.vue'
import SiteDigitalTwin from '@/components/SiteDigitalTwin.vue'
import { inspectionRouteFor } from '@/services/inspectionRoutes'

defineProps<{ site: Site }>()

const scenarioResult = ref<ScenarioResult>()
const scenarioId = ref('')
const scenarioLabel = ref('')
const severity = ref(50)
const viewMode = ref<'operational' | 'interactive'>('operational')
const comparison = ref<'baseline' | 'scenario'>('scenario')
const activeWaypoint = ref(0)
const route = computed(() => inspectionRouteFor(scenarioId.value))

function updateScenario(payload: { id: string; label: string; severity: number; duration: number; result: ScenarioResult }) {
  if (scenarioId.value !== payload.id) activeWaypoint.value = 0
  scenarioId.value = payload.id
  scenarioLabel.value = payload.label
  severity.value = payload.severity
  scenarioResult.value = payload.result
}

function selectWaypoint(index: number) { activeWaypoint.value = index }
</script>

<template>
  <section class="spatial card card--interactive" aria-labelledby="spatial-title">
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
        <div class="spatial__scenario-banner" :class="{ 'spatial__scenario-banner--baseline': comparison === 'baseline' }">
          <div><span>{{ comparison === 'baseline' ? 'MEASURED BASELINE' : 'SIMULATED SCENARIO APPLIED' }}</span><strong>{{ comparison === 'baseline' ? 'Original site state' : `${scenarioLabel} · ${severity}% severity` }}</strong></div>
          <div class="spatial__comparison" aria-label="Compare site state"><button type="button" :class="{ active: comparison === 'baseline' }" @click="comparison = 'baseline'">Baseline</button><button type="button" :class="{ active: comparison === 'scenario' }" @click="comparison = 'scenario'">Scenario</button></div>
        </div>
        <div class="spatial__routebar">
          <div><strong>{{ route.label }}</strong><span>{{ route.waypoints[activeWaypoint]?.instruction }}</span></div>
          <div class="spatial__modes" aria-label="Simulation view">
            <button type="button" :class="{ active: viewMode === 'operational' }" :aria-pressed="viewMode === 'operational'" @click="viewMode = 'operational'">Operational</button>
            <button type="button" :class="{ active: viewMode === 'interactive' }" :aria-pressed="viewMode === 'interactive'" @click="viewMode = 'interactive'">Interactive 3D</button>
          </div>
        </div>
        <SiteDigitalTwin
          :site="site"
          :scenario="scenarioResult"
          :scenario-id="scenarioId"
          :scenario-label="scenarioLabel"
          :route="route"
          :view-mode="viewMode"
          :scenario-active="comparison === 'scenario'"
          :active-waypoint="activeWaypoint"
          :severity="severity"
          embedded
        />
        <ol class="spatial__waypoints" aria-label="Inspection points">
          <li v-for="(point, index) in route.waypoints" :key="point.id"><button type="button" :class="{ active: activeWaypoint === index }" :aria-current="activeWaypoint === index ? 'step' : undefined" @click="selectWaypoint(index)"><span>{{ index + 1 }}</span><strong>{{ point.label }}</strong></button></li>
        </ol>
        <div v-if="scenarioResult" class="spatial__impact" aria-live="polite"><div><span>Affected layer</span><strong>{{ scenarioResult.affectedLayer }}</strong></div><div><span>Projected loss</span><strong>{{ scenarioResult.generationLossKwh.toLocaleString() }} kWh</strong></div><div><span>RM exposure</span><strong>RM {{ scenarioResult.rmExposure.toLocaleString() }}</strong></div><div><span>Recommended response</span><strong>{{ scenarioResult.responseLabel }}</strong></div></div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.spatial { overflow:hidden; }
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
.spatial__scenario-banner { min-height:66px; display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.65rem 1rem; color:#fff; background:#71372d; border-bottom:1px solid rgba(255,255,255,.12); transition:background-color 300ms var(--ease-out); }
.spatial__scenario-banner--baseline { background:#20302b; }
.spatial__scenario-banner span,.spatial__scenario-banner strong { display:block; } .spatial__scenario-banner span { color:#ffd4c9; font-size:.56rem; font-weight:800; letter-spacing:.09em; } .spatial__scenario-banner--baseline span { color:#a9c6bc; } .spatial__scenario-banner strong { margin-top:.18rem; font-size:.8rem; }
.spatial__comparison { display:flex; gap:.2rem; padding:.2rem; background:rgba(0,0,0,.22); border-radius:var(--radius-sm); } .spatial__comparison button { min-height:36px; padding:.4rem .62rem; color:#d9e2de; background:transparent; border:0; border-radius:calc(var(--radius-sm) - 2px); font:inherit; font-size:.67rem; cursor:pointer; } .spatial__comparison button.active { color:#172921; background:#fff; font-weight:750; }
.spatial__routebar { min-height:68px; display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.7rem 1rem; color:#f4f7f6; background:#0a1311; border-bottom:1px solid rgba(255,255,255,.09); }
.spatial__routebar strong,.spatial__routebar span { display:block; } .spatial__routebar strong { font-size:.78rem; } .spatial__routebar span { max-width:62ch; margin-top:.2rem; color:#9fb0aa; font-size:.65rem; line-height:1.4; }
.spatial__modes { display:flex; gap:.25rem; flex:0 0 auto; } .spatial__modes button { min-height:38px; padding:.45rem .65rem; color:#9fb0aa; background:transparent; border:1px solid rgba(255,255,255,.1); border-radius:var(--radius-sm); font:inherit; font-size:.68rem; cursor:pointer; } .spatial__modes button.active { color:#172921; background:#7be0a5; border-color:#7be0a5; }
.spatial__waypoints { display:flex; gap:.35rem; margin:0; padding:.65rem 1rem .85rem; overflow-x:auto; list-style:none; color:#fff; background:#0d1715; }
.spatial__waypoints button { min-height:44px; display:flex; align-items:center; gap:.45rem; padding:.5rem .65rem; color:#aebdb8; background:#14231f; border:1px solid rgba(255,255,255,.09); border-radius:var(--radius-sm); font:inherit; cursor:pointer; white-space:nowrap; }
.spatial__waypoints button span { display:grid; place-items:center; width:22px; height:22px; border-radius:50%; background:#263a34; font-size:.62rem; } .spatial__waypoints button strong { font-size:.68rem; } .spatial__waypoints button.active { color:#fff; border-color:rgba(123,224,165,.55); background:#1a3029; } .spatial__waypoints button.active span { color:#172921; background:#7be0a5; }
.spatial__impact { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1px; background:rgba(255,255,255,.08); border-top:1px solid rgba(255,255,255,.09); }
.spatial__impact > div { min-width:0; padding:.75rem .9rem; color:#fff; background:#101b18; } .spatial__impact span,.spatial__impact strong { display:block; } .spatial__impact span { color:#8fa39c; font-size:.58rem; } .spatial__impact strong { margin-top:.2rem; font-size:.72rem; overflow-wrap:anywhere; text-transform:capitalize; }
@media (max-width:1050px) { .spatial__workspace { grid-template-columns:1fr; } .spatial__controls { border-right:0; border-bottom:1px solid var(--border-hairline); } }
@media (max-width:700px) { .spatial__scenario-banner,.spatial__routebar { align-items:flex-start; flex-direction:column; } .spatial__comparison,.spatial__modes { width:100%; } .spatial__comparison button,.spatial__modes button { flex:1; } .spatial__impact { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:620px) { .spatial__header { align-items:flex-start; flex-direction:column; gap:.75rem; } .spatial__state { width:100%; } }
</style>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RotateCcw, SlidersHorizontal } from '@lucide/vue'
import type { Site } from '@/types/dispatch'
import { runScenario, scenarioDefinitions } from '@/services/scenarioEngine'

const props = defineProps<{ site: Site }>()
const selectedId = ref(scenarioDefinitions[0]!.id)
const severity = ref(scenarioDefinitions[0]!.parameters[0]!.defaultValue)
const duration = ref(scenarioDefinitions[0]!.parameters[1]!.defaultValue)
const scenario = computed(() => scenarioDefinitions.find((item) => item.id === selectedId.value) ?? scenarioDefinitions[0]!)
const output = computed(() => runScenario(props.site, scenario.value, { severity: severity.value, duration: duration.value }))

function selectScenario() {
  severity.value = scenario.value.parameters[0]!.defaultValue
  duration.value = scenario.value.parameters[1]!.defaultValue
}
function reset() { selectScenario() }
</script>

<template>
  <section class="lab" aria-labelledby="scenario-title">
    <header class="lab__header">
      <div>
        <div class="lab__title"><SlidersHorizontal :size="18" aria-hidden="true" /><h2 id="scenario-title">Scenario lab</h2><span>SIMULATED</span></div>
        <p>Explore bounded what-if conditions without changing the measured dispatch record.</p>
      </div>
      <button type="button" class="lab__reset" @click="reset"><RotateCcw :size="14" aria-hidden="true" /> Reset</button>
    </header>
    <div class="lab__body">
      <form class="lab__controls" @submit.prevent>
        <label for="scenario-select">Scenario</label>
        <select id="scenario-select" v-model="selectedId" @change="selectScenario">
          <optgroup label="Revenue loss"><option v-for="item in scenarioDefinitions.filter((s) => s.group === 'revenue')" :key="item.id" :value="item.id">{{ item.title }}</option></optgroup>
          <optgroup label="Inspection and safety"><option v-for="item in scenarioDefinitions.filter((s) => s.group === 'inspection')" :key="item.id" :value="item.id">{{ item.title }}</option></optgroup>
          <optgroup label="Grid and environment"><option v-for="item in scenarioDefinitions.filter((s) => s.group === 'grid')" :key="item.id" :value="item.id">{{ item.title }}</option></optgroup>
        </select>
        <p class="lab__description">{{ scenario.description }}</p>
        <label for="severity">Severity <output>{{ severity }}%</output></label>
        <input id="severity" v-model.number="severity" type="range" min="10" max="100" step="5" />
        <label for="duration">Duration <output>{{ duration }} days</output></label>
        <input id="duration" v-model.number="duration" type="range" min="1" max="30" step="1" />
        <p class="lab__assumption">{{ output.assumptions[0] }}</p>
      </form>
      <div class="lab__result" aria-live="polite">
        <div><span>Projected generation loss</span><strong>{{ output.generationLossKwh.toLocaleString() }} kWh</strong></div>
        <div><span>Additional RM exposure</span><strong>RM {{ output.rmExposure.toLocaleString() }}</strong></div>
        <div><span>Scenario confidence</span><strong>{{ Math.round(output.confidence * 100) }}%</strong></div>
        <div class="lab__response"><span>Recommended response</span><strong>{{ output.responseLabel }}</strong><small>{{ output.evidenceLevel }} output · {{ output.affectedLayer }} layer</small></div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.lab { margin: 1.5rem 0; padding: 1.15rem 1.25rem; background: var(--surface-1); border: 1px solid var(--border-hairline); border-radius: var(--radius-lg); box-shadow: var(--elevation-1); }
.lab__header { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; padding-bottom:1rem; border-bottom:1px solid var(--border-hairline); }
.lab__title { display:flex; align-items:center; gap:.5rem; } .lab h2 { margin:0; font-size:1.05rem; } .lab__title span { padding:.16rem .38rem; color:var(--action-ink); background:var(--action-fill); border-radius:var(--radius-sm); font-size:.58rem; font-weight:800; letter-spacing:.08em; }
.lab__header p { margin:.4rem 0 0; color:var(--text-secondary); font-size:.8rem; }
.lab button { min-height:44px; display:inline-flex; align-items:center; gap:.35rem; padding:.55rem .75rem; color:var(--text-secondary); background:transparent; border:1px solid var(--border-hairline); border-radius:var(--radius-sm); font:inherit; font-size:.76rem; cursor:pointer; }
.lab__body { display:grid; grid-template-columns:minmax(250px,.9fr) minmax(0,1.1fr); gap:1.5rem; padding-top:1.1rem; }
.lab__controls { display:flex; flex-direction:column; gap:.45rem; } .lab label { color:var(--text-secondary); font-size:.72rem; font-weight:650; } .lab output { float:right; color:var(--text-primary); font-weight:700; }
.lab select { min-height:44px; padding:.55rem .65rem; color:var(--text-primary); background:var(--surface-1); border:1px solid var(--baseline); border-radius:var(--radius-sm); font:inherit; font-size:.8rem; }
.lab input[type='range'] { width:100%; accent-color:var(--action-text); } .lab__description { min-height:2.8em; margin:.2rem 0 .65rem; color:var(--text-secondary); font-size:.76rem; line-height:1.45; } .lab__assumption { margin:.55rem 0 0; color:var(--text-muted); font-size:.68rem; line-height:1.45; }
.lab__result { display:grid; grid-template-columns:repeat(3,1fr); gap:.6rem; align-content:start; } .lab__result > div { padding:.85rem; background:var(--surface-2); border-radius:var(--radius-md); } .lab__result span,.lab__result small { display:block; color:var(--text-muted); font-size:.65rem; } .lab__result strong { display:block; margin-top:.22rem; font-family:var(--font-display); font-size:1.35rem; letter-spacing:-.03em; } .lab__response { grid-column:1 / -1; background:var(--surface-emphasis)!important; } .lab__response strong { font-size:1rem; } .lab__response small { margin-top:.3rem; }
@media (max-width:720px) { .lab__header { flex-direction:column; } .lab__reset { width:100%; justify-content:center; } .lab__body { grid-template-columns:1fr; } .lab__result { grid-template-columns:1fr; } .lab__response { grid-column:auto; } }
</style>

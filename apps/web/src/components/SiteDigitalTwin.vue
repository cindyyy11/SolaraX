<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Box, Camera, CircleStop, Play, RotateCcw, ScanLine } from '@lucide/vue'
import type { Site } from '@/types/dispatch'
import type { ScenarioResult } from '@/types/scenario'

const props = defineProps<{ site: Site; scenario?: ScenarioResult; scenarioLabel?: string; scenarioId?: string; embedded?: boolean }>()

type CameraPreset = 'overview' | 'roof' | 'anomaly' | 'drone'

const cameras: Array<{ id: CameraPreset; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'roof', label: 'Array' },
  { id: 'anomaly', label: 'Anomaly' },
  { id: 'drone', label: 'Drone route' },
]

const stages = [
  { label: 'Baseline', detail: 'Satellite conditions establish expected output.' },
  { label: 'Divergence', detail: 'Actual output separates from the peer cohort.' },
  { label: 'Scan', detail: 'A simulated drone route prioritises the suspect zone.' },
  { label: 'Dispatch', detail: 'Evidence and value at risk become a work-order recommendation.' },
]

const activeCamera = ref<CameraPreset>('overview')
const activeStage = ref(0)
const isPlaying = ref(false)
let replayTimer: ReturnType<typeof setInterval> | null = null
let transitionTimer: ReturnType<typeof setTimeout> | null = null
const isScenarioChanging = ref(false)

const hasAnomaly = computed(() => props.site.status !== 'healthy' || Boolean(props.scenario))
const riskValue = computed(() => props.site.economics?.rm_at_risk_monthly ?? 0)
const lossPercent = computed(() => props.site.economics?.loss_pct_of_expected ?? 0)

function stopReplay() {
  if (replayTimer) clearInterval(replayTimer)
  replayTimer = null
  isPlaying.value = false
}

function replay() {
  stopReplay()
  activeStage.value = 0
  activeCamera.value = 'overview'
  isPlaying.value = true
  replayTimer = setInterval(() => {
    if (activeStage.value >= stages.length - 1) {
      stopReplay()
      return
    }
    activeStage.value += 1
    activeCamera.value = (['overview', 'roof', 'drone', 'anomaly'] as CameraPreset[])[
      activeStage.value
    ]!
  }, 1350)
}

function selectStage(index: number) {
  stopReplay()
  activeStage.value = index
}

watch(() => props.scenarioId, (id) => {
  if (!id) return
  isScenarioChanging.value = true
  activeCamera.value = props.scenario?.affectedLayer === 'equipment' ? 'roof' : id.includes('thermal') || id.includes('storm') ? 'anomaly' : id.includes('curtailment') ? 'overview' : 'roof'
  if (transitionTimer) clearTimeout(transitionTimer)
  transitionTimer = setTimeout(() => { isScenarioChanging.value = false }, 850)
})

onBeforeUnmount(() => { stopReplay(); if (transitionTimer) clearTimeout(transitionTimer) })
</script>

<template>
  <section class="twin" :class="{ 'twin--embedded': embedded }" aria-labelledby="twin-title">
    <header v-if="!embedded" class="twin__header">
      <div>
        <div class="twin__title-row">
          <Box :size="19" aria-hidden="true" />
          <h2 id="twin-title">Site simulation</h2>
          <span class="simulation-label">SIMULATED</span>
        </div>
        <p>
          An illustrative solar-array and drone inspection scene. Geometry and anomaly locations
          are not derived from this site's physical layout.
        </p>
        <p v-if="scenarioLabel" class="twin__active-scenario">Scenario overlay: <strong>{{ scenarioLabel }}</strong> · simulated only</p>
      </div>
      <button v-if="!isPlaying" type="button" class="replay" @click="replay">
        <Play :size="16" aria-hidden="true" /> Replay incident
      </button>
      <button v-else type="button" class="replay replay--stop" @click="stopReplay">
        <CircleStop :size="16" aria-hidden="true" /> Stop replay
      </button>
    </header>
    <div v-else class="twin__compact-head">
      <div><h3 id="twin-title">Live scenario view</h3><span>SIMULATED GEOMETRY</span></div>
      <button v-if="!isPlaying" type="button" class="replay" @click="replay"><Play :size="16" aria-hidden="true" /> Replay</button>
      <button v-else type="button" class="replay replay--stop" @click="stopReplay"><CircleStop :size="16" aria-hidden="true" /> Stop</button>
    </div>

    <div class="twin__workspace">
      <div class="scene-shell">
        <div class="scene-toolbar" aria-label="3D camera presets">
          <Camera :size="15" aria-hidden="true" />
          <button
            v-for="camera in cameras"
            :key="camera.id"
            type="button"
            :class="{ active: activeCamera === camera.id }"
            :aria-pressed="activeCamera === camera.id"
            @click="activeCamera = camera.id"
          >
            {{ camera.label }}
          </button>
          <button type="button" aria-label="Reset 3D camera" @click="activeCamera = 'overview'">
            <RotateCcw :size="14" aria-hidden="true" />
          </button>
        </div>

        <div class="scene-viewport" :class="[`camera--${activeCamera}`, scenario?.affectedLayer ? `layer--${scenario.affectedLayer}` : '', scenarioId ? `scenario--${scenarioId}` : '']">
          <div class="sky-glow" aria-hidden="true"></div>
          <div class="scenario-atmosphere" aria-hidden="true"></div>
          <div v-if="isScenarioChanging" class="scenario-transition" role="status">Applying {{ scenarioLabel }}…</div>
          <div class="world" aria-hidden="true">
            <div class="roof">
              <div class="roof-grid"></div>
              <div
                v-for="panel in 24"
                :key="panel"
                class="panel-cell"
                :class="{
                  'panel-cell--anomaly': hasAnomaly && panel === 15,
                  'panel-cell--scanned': activeStage >= 2 || Boolean(scenario),
                }"
              >
                <i></i><i></i><i></i>
              </div>
              <div class="inverter inverter--one"><span>INV-01</span></div>
              <div class="inverter inverter--two"><span>INV-02</span></div>
              <div v-if="hasAnomaly" class="anomaly-beacon"><span>Suspect zone</span></div>
              <div class="drone" :class="{ 'drone--flying': isPlaying || activeCamera === 'drone' }">
                <span class="drone__body"></span>
                <i v-for="arm in 4" :key="arm"></i>
                <ScanLine class="drone__scan" :size="20" />
              </div>
              <div class="route-line"></div>
            </div>
          </div>

          <div class="scene-readout">
            <span>{{ scenario ? 'Scenario projection' : 'Illustrative model' }}</span>
            <strong>{{ site.name }}</strong>
            <small>{{ site.capacity_kwp.toLocaleString() }} kWp · {{ site.status }}</small>
            <small v-if="scenarioLabel && scenario" class="scene-readout__scenario">{{ scenarioLabel }} · {{ scenario.responseLabel }}</small>
          </div>
          <div class="scene-legend">
            <span><i class="legend-dot legend-dot--flow"></i> Energy path</span>
            <span><i class="legend-dot legend-dot--risk"></i> Simulated suspect zone</span>
          </div>
        </div>
      </div>

      <aside class="incident" aria-label="Incident explanation">
        <div class="incident__metric">
          <span>Measured economic exposure</span>
          <strong>RM {{ riskValue.toLocaleString() }}<small>/month</small></strong>
          <p>{{ lossPercent.toFixed(1) }}% below expected output</p>
        </div>

        <ol class="incident__steps">
          <li v-for="(stage, index) in stages" :key="stage.label">
            <button
              type="button"
              :class="{ active: activeStage === index, complete: activeStage > index }"
              :aria-current="activeStage === index ? 'step' : undefined"
              @click="selectStage(index)"
            >
              <span>{{ index + 1 }}</span>
              <span><strong>{{ stage.label }}</strong><small>{{ stage.detail }}</small></span>
            </button>
          </li>
        </ol>

        <p class="incident__note">
          The financial and performance values are from the fleet record. The roof, equipment
          placement, drone route, and highlighted zone are simulated presentation aids.
        </p>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.twin {
  margin: 1.5rem 0;
  overflow: hidden;
  color: #f4f7f6;
  background: #0d1715;
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: var(--radius-lg);
  box-shadow: 0 22px 50px rgba(6, 16, 13, 0.2);
}
.twin--embedded { height: 100%; margin: 0; border: 0; border-radius: 0; box-shadow: none; }
.twin__compact-head { min-height:64px; display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.65rem 1rem; border-bottom:1px solid rgba(255,255,255,.09); }
.twin__compact-head > div { display:flex; align-items:center; gap:.55rem; }
.twin__compact-head h3 { margin:0; font-size:.92rem; }
.twin__compact-head span { padding:.18rem .4rem; color:#182c25; background:#7be0a5; border-radius:var(--radius-sm); font-size:.56rem; font-weight:800; letter-spacing:.07em; }
.twin--embedded .twin__workspace { grid-template-columns:minmax(0,1fr); }
.twin--embedded .scene-shell { border-right:0; }
.twin--embedded .incident { display:grid; grid-template-columns:minmax(180px,.55fr) minmax(0,1.45fr); gap:1rem; border-top:1px solid rgba(255,255,255,.09); }
.twin--embedded .incident__steps { display:grid; grid-template-columns:repeat(4,1fr); gap:.4rem; margin:0; }
.twin--embedded .incident__steps li::after { display:none; }
.twin--embedded .incident__note { grid-column:1 / -1; }
.twin__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1.15rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
}
.twin__header > div,
.incident,
.incident__steps button > span:last-child { min-width: 0; }
.twin__title-row { display: flex; align-items: center; gap: .55rem; }
.twin h2 { margin: 0; font-size: 1.05rem; letter-spacing: -.02em; }
.twin__header p { max-width: 70ch; margin: .4rem 0 0; color: #aebdb8; font-size: .78rem; line-height: 1.5; }
.twin__active-scenario { color: #efb866 !important; }
.twin__active-scenario strong { color: #fff; }
.simulation-label { padding: .18rem .42rem; color: #182c25; background: #7be0a5; border-radius: var(--radius-sm); font-size: .61rem; font-weight: 800; letter-spacing: .08em; }
.replay { min-height: 44px; display: inline-flex; align-items: center; justify-content: center; gap: .45rem; padding: .65rem .85rem; border: 0; border-radius: var(--radius-sm); color: #192c4c; background: var(--brand-solar); font: inherit; font-size: .78rem; font-weight: 700; cursor: pointer; white-space: nowrap; transition: transform var(--duration-fast) var(--ease-out), background-color var(--duration-fast) var(--ease-out); }
.replay--stop { color: #f4f7f6; background: #34443f; }
.replay:active { transform: scale(.97); }
.twin__workspace { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(260px, .7fr); min-height: 480px; }
.scene-shell { min-width: 0; border-right: 1px solid rgba(255, 255, 255, .09); }
.scene-toolbar { display: flex; align-items: center; gap: .3rem; min-height: 52px; padding: .45rem .8rem; overflow-x: auto; border-bottom: 1px solid rgba(255, 255, 255, .08); }
.scene-toolbar > svg { margin-right: .25rem; color: #8fa39c; flex: 0 0 auto; }
.scene-toolbar button { min-height: 36px; display: inline-flex; align-items: center; justify-content: center; padding: .45rem .65rem; border: 1px solid transparent; border-radius: var(--radius-sm); color: #aebdb8; background: transparent; font: inherit; font-size: .72rem; cursor: pointer; white-space: nowrap; }
.scene-toolbar button.active { color: #fff; background: rgba(227, 162, 70, .14); border-color: rgba(227, 162, 70, .32); }
.scene-toolbar button:last-child { min-width: 36px; margin-left: auto; }
.scene-viewport { position: relative; min-height: 427px; overflow: hidden; perspective: 950px; background: linear-gradient(160deg, #11231f 0%, #07100e 72%); }
.sky-glow { position: absolute; inset: -30% -10% 28% 15%; background: radial-gradient(ellipse at center, rgba(227, 162, 70, .17), transparent 60%); pointer-events: none; }
.scenario-atmosphere { position:absolute; inset:0; z-index:1; pointer-events:none; opacity:0; transition:opacity 500ms var(--ease-in-out), background 500ms var(--ease-in-out); }
.scenario--soiling .scenario-atmosphere { opacity:.45; background:linear-gradient(155deg, rgba(184,137,72,.18), transparent 58%); }
.scenario--partial-shading .scenario-atmosphere { opacity:.72; background:linear-gradient(115deg, transparent 35%, rgba(0,0,0,.68) 36%, rgba(0,0,0,.5) 55%, transparent 56%); transform:translateX(-12%); }
.scenario--heatwave .scenario-atmosphere { opacity:.7; background:radial-gradient(ellipse at 60% 30%, rgba(255,112,54,.28), transparent 55%); backdrop-filter:blur(.7px); }
.scenario--storm-damage .scenario-atmosphere { opacity:.55; background:linear-gradient(160deg, rgba(100,127,139,.24), rgba(7,16,14,.3)); }
.scenario--curtailment .scenario-atmosphere { opacity:.48; background:linear-gradient(90deg, transparent 47%, rgba(255,184,77,.35) 48%, rgba(255,184,77,.35) 52%, transparent 53%); }
.scenario-transition { position:absolute; inset:0; z-index:20; display:grid; place-items:center; color:#fff; background:rgba(7,16,14,.7); backdrop-filter:blur(8px); font-size:.78rem; font-weight:750; letter-spacing:.03em; animation:scenario-reveal 850ms var(--ease-out) both; }
@keyframes scenario-reveal { 0% { opacity:0; clip-path:inset(0 100% 0 0); } 25%,70% { opacity:1; clip-path:inset(0 0 0 0); } 100% { opacity:0; clip-path:inset(0 0 0 100%); } }
.world { position: absolute; left: 50%; top: 51%; width: min(74%, 660px); aspect-ratio: 1.55; transform-style: preserve-3d; transform: translate(-50%, -50%) rotateX(58deg) rotateZ(-16deg); transition: transform 600ms var(--ease-in-out); }
.camera--roof .world { transform: translate(-50%, -47%) scale(1.25) rotateX(66deg) rotateZ(-4deg); }
.camera--anomaly .world { transform: translate(-58%, -39%) scale(1.58) rotateX(61deg) rotateZ(-10deg); }
.camera--drone .world { transform: translate(-48%, -52%) scale(1.08) rotateX(52deg) rotateZ(-24deg); }
.roof { position: absolute; inset: 0; display: grid; grid-template-columns: repeat(6, 1fr); grid-template-rows: repeat(4, 1fr); gap: 2.4%; padding: 8%; transform-style: preserve-3d; background: #24302d; border: 2px solid #5e6b67; box-shadow: 18px 24px 34px rgba(0, 0, 0, .42); }
.roof::before { content: ''; position: absolute; inset: 0; transform: translateZ(-18px); background: #151e1c; }
.roof-grid { position: absolute; inset: 4%; border: 1px dashed rgba(255, 255, 255, .12); }
.panel-cell { position: relative; overflow: hidden; transform: translateZ(7px); background: linear-gradient(135deg, #1d5060, #0d2933); border: 1px solid #4a7580; box-shadow: 0 3px 6px rgba(0, 0, 0, .32); transition: filter 300ms var(--ease-in-out), box-shadow 300ms var(--ease-in-out); }
.panel-cell i { position: absolute; inset-block: 0; width: 1px; background: rgba(188, 224, 229, .27); }
.panel-cell i:nth-child(1) { left: 25%; } .panel-cell i:nth-child(2) { left: 50%; } .panel-cell i:nth-child(3) { left: 75%; }
.panel-cell--scanned { filter: brightness(1.12); }
.layer--equipment .panel-cell { filter: saturate(.65) brightness(.82); }
.layer--grid .panel-cell { filter: hue-rotate(18deg) saturate(.78); }
.scenario--partial-shading .panel-cell:nth-child(-n+8), .scenario--soiling .panel-cell { filter: brightness(.62) saturate(.55); }
.scenario--inverter-derating .inverter--two { color:#fff; background:#913f32; border-color:#ff8b78; box-shadow:0 0 18px rgba(255,106,85,.45); }
.scenario--string-underperformance .panel-cell:nth-child(6n+3) { filter:brightness(.35) saturate(.4); border-color:#ffb45f; }
.scenario--storm-damage .panel-cell:nth-child(9), .scenario--storm-damage .panel-cell:nth-child(15), .scenario--storm-damage .panel-cell:nth-child(16) { transform:translateZ(12px) rotate(5deg); background:#50312d; border-color:#ff8775; }
.scenario--curtailment .route-line { border-color:#ffb45f; border-style:solid; box-shadow:0 0 14px rgba(255,180,95,.42); }
.scenario--thermal-hotspot .panel-cell:nth-child(15), .scenario--storm-damage .panel-cell:nth-child(15) { animation: anomaly-pulse 1.4s ease-in-out infinite; }
@keyframes anomaly-pulse { 50% { filter: brightness(1.45) saturate(1.35); box-shadow: 0 0 24px rgba(255, 104, 79, .65); } }
.panel-cell--anomaly { background: linear-gradient(135deg, #8b332c, #421915); border-color: #ff8775; box-shadow: 0 0 18px rgba(255, 104, 79, .38); }
.inverter { position: absolute; right: 1.5%; width: 6%; height: 16%; transform: translateZ(12px); display: grid; place-items: center; color: #dce5e1; background: #66726f; border: 1px solid #9da8a4; font-size: .43rem; }
.inverter--one { top: 24%; } .inverter--two { top: 60%; }
.inverter span { transform: rotate(-90deg); white-space: nowrap; }
.anomaly-beacon { position: absolute; left: 45%; top: 59%; width: 5%; aspect-ratio: 1; transform: translateZ(22px); border-radius: 50%; background: #ff6a55; box-shadow: 0 0 0 6px rgba(255, 106, 85, .18), 0 0 22px #ff6a55; }
.anomaly-beacon span { position: absolute; left: 140%; top: 50%; transform: translateY(-50%); padding: .2rem .4rem; color: #fff; background: rgba(29, 12, 10, .88); border-radius: 3px; font-size: .45rem; white-space: nowrap; }
.route-line { position: absolute; left: 12%; top: 15%; width: 68%; height: 58%; transform: translateZ(30px); border: 1px dashed rgba(123, 224, 165, .66); border-radius: 42% 58% 48% 52%; }
.drone { position: absolute; left: 20%; top: 20%; width: 7%; aspect-ratio: 1; z-index: 5; transform: translateZ(64px) rotateZ(16deg); transition: left 800ms var(--ease-in-out), top 800ms var(--ease-in-out); }
.drone__body { position: absolute; inset: 30%; border-radius: 35%; background: #eef4f1; box-shadow: 0 5px 10px rgba(0,0,0,.35); }
.drone i { position: absolute; left: 45%; top: 45%; width: 55%; height: 2px; transform-origin: left center; background: #b8c4c0; }
.drone i:nth-of-type(1) { transform: rotate(45deg); } .drone i:nth-of-type(2) { transform: rotate(135deg); } .drone i:nth-of-type(3) { transform: rotate(225deg); } .drone i:nth-of-type(4) { transform: rotate(315deg); }
.drone i::after { content: ''; position: absolute; right: -4px; top: -4px; width: 8px; height: 8px; border: 1px solid #dfe8e4; border-radius: 50%; }
.drone__scan { position: absolute; left: 20%; top: 74%; color: #7be0a5; transform: rotateX(-58deg); filter: drop-shadow(0 0 5px #7be0a5); }
.drone--flying { animation: drone-route 5.4s linear infinite; }
@keyframes drone-route { 0% { left: 16%; top: 17%; } 25% { left: 69%; top: 20%; } 50% { left: 70%; top: 68%; } 75% { left: 34%; top: 65%; } 100% { left: 16%; top: 17%; } }
.scene-readout { position: absolute; left: 1rem; bottom: 1rem; display: flex; flex-direction: column; gap: .1rem; padding: .65rem .75rem; background: rgba(7, 16, 14, .86); border: 1px solid rgba(255,255,255,.1); border-radius: var(--radius-sm); }
.scene-readout span { color: #7be0a5; font-size: .58rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.scene-readout strong { font-size: .82rem; } .scene-readout small { color: #aebdb8; font-size: .65rem; text-transform: capitalize; }
.scene-readout__scenario { color: #efb866 !important; text-transform: none !important; }
.scene-legend { position: absolute; right: 1rem; bottom: 1rem; display: flex; flex-direction: column; gap: .35rem; color: #aebdb8; font-size: .62rem; }
.legend-dot { display: inline-block; width: 7px; height: 7px; margin-right: .25rem; border-radius: 50%; } .legend-dot--flow { background: #7be0a5; } .legend-dot--risk { background: #ff6a55; }
.incident { padding: 1.2rem; background: #101b18; }
.incident__metric { padding-bottom: 1.1rem; border-bottom: 1px solid rgba(255,255,255,.1); }
.incident__metric > span { color: #9fb0aa; font-size: .66rem; text-transform: uppercase; letter-spacing: .07em; }
.incident__metric strong { display: block; margin-top: .25rem; font-family: var(--font-display); font-size: clamp(1.65rem, 3vw, 2.5rem); letter-spacing: -.04em; }
.incident__metric strong small { margin-left: .2rem; color: #9fb0aa; font: 500 .7rem var(--font-sans); letter-spacing: 0; }
.incident__metric p { margin: .25rem 0 0; color: #d1dbd7; font-size: .76rem; }
.incident__steps { list-style: none; margin: 1rem 0; padding: 0; }
.incident__steps li { position: relative; }
.incident__steps li:not(:last-child)::after { content: ''; position: absolute; left: 15px; top: 36px; bottom: -3px; width: 1px; background: rgba(255,255,255,.13); }
.incident__steps button { width: 100%; display: grid; grid-template-columns: 30px 1fr; gap: .6rem; align-items: start; min-height: 62px; padding: .45rem 0; text-align: left; color: #9fb0aa; background: transparent; border: 0; font: inherit; cursor: pointer; }
.incident__steps button > span:first-child { position: relative; z-index: 1; display: grid; place-items: center; width: 30px; height: 30px; border: 1px solid #50605a; border-radius: 50%; background: #101b18; font-size: .68rem; transition: color var(--duration-fast) var(--ease-out), background-color var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out); }
.incident__steps button.active > span:first-child, .incident__steps button.complete > span:first-child { color: #182c25; background: #7be0a5; border-color: #7be0a5; }
.incident__steps strong, .incident__steps small { display: block; }
.incident__steps strong { color: #f2f7f4; font-size: .78rem; }
.incident__steps small { margin-top: .18rem; font-size: .66rem; line-height: 1.4; }
.incident__steps small,
.incident__note,
.twin__header p { overflow-wrap: anywhere; }
.incident__note { margin: 0; padding-top: .85rem; color: #91a39d; border-top: 1px solid rgba(255,255,255,.1); font-size: .65rem; line-height: 1.5; }
@media (hover: hover) and (pointer: fine) { .replay:hover { background: #efb866; } .scene-toolbar button:hover { color: #fff; background: rgba(255,255,255,.06); } }
@media (max-width: 900px) { .twin__workspace { grid-template-columns: 1fr; } .scene-shell { border-right: 0; border-bottom: 1px solid rgba(255,255,255,.09); } .scene-viewport { min-height: 390px; } .incident__steps { display: grid; grid-template-columns: repeat(2, 1fr); gap: .5rem; } .incident__steps li::after { display: none; } .twin--embedded .incident { grid-template-columns:1fr; } .twin--embedded .incident__steps { grid-template-columns:repeat(2,1fr); } .twin--embedded .incident__note { grid-column:auto; } }
@media (max-width: 620px) { .twin__header { flex-direction: column; } .replay { width: 100%; } .scene-viewport { min-height: 330px; } .world { width: 92%; } .scene-legend { display: none; } .incident__steps { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { .world { transition: none; } .drone--flying { animation: none; left: 56%; top: 50%; } .scenario-transition { animation:none; opacity:1; clip-path:none; } .scenario--thermal-hotspot .panel-cell:nth-child(15), .scenario--storm-damage .panel-cell:nth-child(15) { animation:none; } }
</style>

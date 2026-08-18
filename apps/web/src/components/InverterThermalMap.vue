<script setup lang="ts">
/**
 * Inverter thermal map.
 *
 * THIS IS NOT A PANEL GRID, AND THAT IS DELIBERATE. PVDAQ publishes no panel or
 * string positions — `num_strings` and `modules_per_string` are null on every
 * inverter in the fleet — and nothing measures a panel individually. A roof
 * layout of R x C tiles would be invented geometry carrying invented readings.
 * The unit here is the inverter, which is the finest granularity that was
 * actually instrumented.
 *
 * Colour encodes operating temperature relative to sibling inverters, on a
 * single-hue sequential ramp rather than a rainbow. Rainbow ramps are not
 * perceptually uniform — equal temperature steps do not look equal — and they
 * fail for colourblind readers. Every tile also carries its numeric value, so
 * colour is reinforcement and never the only channel.
 */
import { computed, ref } from 'vue'
import type { SubSite, SubSiteUnit, Evidence } from '@/types/dispatch'
import DataStatusBadge from '@/components/DataStatusBadge.vue'

const props = defineProps<{
  subSite: SubSite
  evidence?: Evidence
}>()

const selectedUnitId = ref<string | null>(null)

/** Units with thermal data, ordered by unit number so the grid reads naturally. */
const thermalUnits = computed(() =>
  props.subSite.units
    .filter((unit) => unit.thermal)
    .sort((a, b) => {
      const numberOf = (id: string) => Number(id.replace(/\D/g, '')) || 0
      return numberOf(a.unit_id) - numberOf(b.unit_id)
    }),
)

const selectedUnit = computed<SubSiteUnit | null>(() => {
  if (!selectedUnitId.value) return thermalUnits.value[0] ?? null
  return thermalUnits.value.find((unit) => unit.unit_id === selectedUnitId.value) ?? null
})

const deltas = computed(() => thermalUnits.value.map((unit) => unit.thermal!.delta_t_siblings_c))
const maxAbsDelta = computed(() => Math.max(1, ...deltas.value.map(Math.abs)))

/**
 * Single-hue sequential ramp keyed to temperature ABOVE the sibling median.
 * Cool end recedes toward the surface; hot end is the strongest step. Units at
 * or below the median share the coolest step — running cooler than your siblings
 * is not a finding worth a colour gradient.
 */
function tileStyle(unit: SubSiteUnit) {
  const delta = unit.thermal!.delta_t_siblings_c
  const normalised = Math.max(0, delta) / maxAbsDelta.value
  const steps = [
    'var(--thermal-0)',
    'var(--thermal-1)',
    'var(--thermal-2)',
    'var(--thermal-3)',
    'var(--thermal-4)',
  ]
  const index = Math.min(steps.length - 1, Math.round(normalised * (steps.length - 1)))
  return {
    background: steps[index],
    // The hottest two steps are dark enough to need light text.
    color: index >= 3 ? 'var(--thermal-ink-on-hot)' : 'var(--thermal-ink)',
  }
}

function isHottest(unit: SubSiteUnit): boolean {
  return unit.thermal!.delta_t_siblings_c === Math.max(...deltas.value) && maxAbsDelta.value > 0.5
}

function formatSigned(value: number, digits = 1): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`
}
</script>

<template>
  <section v-if="thermalUnits.length" class="thermal">
    <header class="thermal__head">
      <div>
        <h2 class="thermal__heading">Inverter thermal map</h2>
        <p class="thermal__sub">
          {{ thermalUnits.length }} instrumented {{ subSite.unit_type }}s · operating temperature
          while generating · click a unit for detail
        </p>
      </div>
      <DataStatusBadge :status="subSite.data_status" small />
    </header>

    <div class="thermal__body">
      <div class="grid">
        <button
          v-for="unit in thermalUnits"
          :key="unit.unit_id"
          type="button"
          class="tile"
          :class="{ 'tile--selected': selectedUnit?.unit_id === unit.unit_id }"
          :style="tileStyle(unit)"
          @click="selectedUnitId = unit.unit_id"
        >
          <span class="tile__id">{{ unit.unit_id }}</span>
          <span class="tile__temp">{{ unit.thermal!.mean_temp_c.toFixed(1) }}°C</span>
          <span class="tile__delta">{{ formatSigned(unit.thermal!.delta_t_siblings_c) }}°C</span>
        </button>
      </div>

      <aside v-if="selectedUnit" class="detail">
        <header class="detail__head">
          <h3 class="detail__id">{{ selectedUnit.unit_id }}</h3>
          <span
            class="detail__tag"
            :class="isHottest(selectedUnit) ? 'detail__tag--hot' : 'detail__tag--normal'"
          >
            {{ isHottest(selectedUnit) ? '▲ hottest unit' : '● within sibling range' }}
          </span>
        </header>

        <dl class="facts">
          <div>
            <dt>Operating temperature</dt>
            <dd>{{ selectedUnit.thermal!.mean_temp_c.toFixed(1) }}°C mean</dd>
          </div>
          <div>
            <dt>Peak observed</dt>
            <dd>{{ selectedUnit.thermal!.max_temp_c.toFixed(1) }}°C</dd>
          </div>
          <div>
            <dt>vs sibling median</dt>
            <dd :class="selectedUnit.thermal!.delta_t_siblings_c > 0 ? 'facts__warm' : ''">
              {{ formatSigned(selectedUnit.thermal!.delta_t_siblings_c) }}°C
            </dd>
          </div>
          <div v-if="selectedUnit.thermal!.delta_t_ambient_c !== null">
            <dt>Above ambient</dt>
            <dd>
              {{ formatSigned(selectedUnit.thermal!.delta_t_ambient_c!) }}°C
              <span class="facts__note">(ambient {{ selectedUnit.thermal!.mean_ambient_c }}°C)</span>
            </dd>
          </div>
          <div>
            <dt>Output vs siblings</dt>
            <dd :class="selectedUnit.deviation_pct < 0 ? 'facts__cold' : ''">
              {{ formatSigned(selectedUnit.deviation_pct * 100) }}%
            </dd>
          </div>
          <div>
            <dt>Days of data</dt>
            <dd>{{ selectedUnit.thermal!.days }}</dd>
          </div>
        </dl>

        <!-- Thermal imagery slot. M5, owner B. Renders the honest message when
             absent, which docs/Schema.md 8.8 requires. -->
        <div class="evidence">
          <p class="evidence__label">Thermal image</p>
          <template v-if="evidence?.has_imagery && evidence.image_url">
            <img :src="evidence.image_url" :alt="`Thermal image, ${selectedUnit.unit_id}`" />
            <p class="evidence__caption">
              {{ evidence.defect_class }} ·
              {{ evidence.confidence ? Math.round(evidence.confidence * 100) + '%' : '' }}
            </p>
          </template>
          <p v-else class="evidence__empty">
            No imagery captured for this site. The reading above is electrical and thermal
            telemetry only — image classification is M5 (owner B).
          </p>
        </div>
      </aside>
    </div>

    <footer class="legend">
      <span class="legend__label">Cooler</span>
      <span class="legend__ramp" aria-hidden="true"></span>
      <span class="legend__label">Hotter</span>
      <span class="legend__scale">relative to sibling median · ±{{ maxAbsDelta.toFixed(1) }}°C range</span>
    </footer>

    <p class="thermal__basis">{{ subSite.thermal_basis }}</p>
    <p class="thermal__caveat">
      Units are inverters, not panels. PVDAQ publishes no panel or string positions, so no
      roof layout is shown — nothing in this dataset supports one.
    </p>
  </section>
</template>

<style scoped>
/* Single-hue sequential ramp, light to dark. Defined per theme so the coolest
   step recedes toward the surface in both. */
.thermal {
  --thermal-0: #cde2fb;
  --thermal-1: #9ec5f4;
  --thermal-2: #5598e7;
  --thermal-3: #256abf;
  --thermal-4: #104281;
  --thermal-ink: #0b0b0b;
  --thermal-ink-on-hot: #ffffff;

  padding: 1.25rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}

@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme='light'])) .thermal {
    --thermal-0: #184f95;
    --thermal-1: #256abf;
    --thermal-2: #3987e5;
    --thermal-3: #86b6ef;
    --thermal-4: #cde2fb;
    --thermal-ink: #ffffff;
    --thermal-ink-on-hot: #0b0b0b;
  }
}

:root[data-theme='dark'] .thermal {
  --thermal-0: #184f95;
  --thermal-1: #256abf;
  --thermal-2: #3987e5;
  --thermal-3: #86b6ef;
  --thermal-4: #cde2fb;
  --thermal-ink: #ffffff;
  --thermal-ink-on-hot: #0b0b0b;
}

.thermal__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.thermal__heading {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.thermal__sub {
  margin: 0.3rem 0 0;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.thermal__body {
  display: grid;
  grid-template-columns: 1fr minmax(220px, 300px);
  gap: 1.25rem;
  align-items: start;
}

@media (max-width: 820px) {
  .thermal__body {
    grid-template-columns: 1fr;
  }
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: 2px; /* surface gap keeps adjacent fills legible */
}

.tile {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.7rem 0.5rem;
  border: 2px solid transparent;
  border-radius: var(--radius-sm);
  font: inherit;
  cursor: pointer;
  text-align: left;
  min-height: 76px;
  justify-content: center;
}

.tile--selected {
  border-color: var(--text-primary);
}

.tile__id {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  opacity: 0.85;
}

.tile__temp {
  font-size: 1.05rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.tile__delta {
  font-size: 0.7rem;
  font-variant-numeric: tabular-nums;
  opacity: 0.8;
}

/* --- Detail panel --- */

.detail {
  padding: 0.9rem;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}

.detail__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.detail__id {
  margin: 0;
  font-size: 1rem;
}

.detail__tag {
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 0.15em 0.45em;
  border: 1px solid currentColor;
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

.detail__tag--hot {
  color: var(--status-serious);
}

.detail__tag--normal {
  color: var(--status-good);
}

.facts {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.facts div {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  padding-top: 0.45rem;
  border-top: 1px solid var(--border-hairline);
}

.facts dt {
  font-size: 0.64rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.facts dd {
  margin: 0;
  font-size: 0.88rem;
  font-variant-numeric: tabular-nums;
}

.facts__warm {
  color: var(--status-serious);
  font-weight: 600;
}

.facts__cold {
  color: var(--status-critical);
  font-weight: 600;
}

.facts__note {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.evidence {
  margin-top: 0.9rem;
  padding-top: 0.7rem;
  border-top: 1px solid var(--border-hairline);
}

.evidence__label {
  margin: 0 0 0.35rem;
  font-size: 0.64rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.evidence img {
  max-width: 100%;
  border-radius: var(--radius-sm);
}

.evidence__caption {
  margin: 0.3rem 0 0;
  font-size: 0.74rem;
  color: var(--text-secondary);
}

.evidence__empty {
  margin: 0;
  font-size: 0.72rem;
  line-height: 1.5;
  color: var(--text-muted);
}

/* --- Legend --- */

.legend {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  font-size: 0.7rem;
  color: var(--text-muted);
}

.legend__ramp {
  flex: 0 1 140px;
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(
    to right,
    var(--thermal-0),
    var(--thermal-1),
    var(--thermal-2),
    var(--thermal-3),
    var(--thermal-4)
  );
}

.legend__scale {
  margin-left: auto;
}

.thermal__basis,
.thermal__caveat {
  margin: 0.75rem 0 0;
  font-size: 0.72rem;
  line-height: 1.55;
  color: var(--text-muted);
}

.thermal__caveat {
  padding-top: 0.6rem;
  border-top: 1px solid var(--border-hairline);
}
</style>

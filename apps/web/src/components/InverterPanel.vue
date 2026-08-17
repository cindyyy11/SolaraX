<script setup lang="ts">
/**
 * Sub-site breakdown — each inverter against the median of its siblings.
 *
 * WHY THIS IS NOT A ROOF MAP. PVDAQ publishes no panel- or inverter-level
 * position data. A spatial layout would invent geometry the dataset does not
 * contain, so units are shown as a ranked list, worst first. The ranking is the
 * useful ordering anyway — a technician wants "which unit," not "which corner."
 *
 * Colour encodes deviation severity using the reserved status palette, and every
 * bar carries a glyph and a numeric label so meaning never rests on colour.
 *
 * Sibling comparison needs no capacity: it is a pure ratio. That is precisely
 * why it works where site-level normalisation would need a kWp denominator
 * PVDAQ does not publish per inverter.
 */
import { computed, ref } from 'vue'
import type { SubSite, SubSiteUnit, Evidence } from '@/types/dispatch'
import DataStatusBadge from '@/components/DataStatusBadge.vue'

const props = defineProps<{
  subSite: SubSite
  evidence?: Evidence
}>()

const expandedUnitId = ref<string | null>(null)

function toggle(unitId: string): void {
  expandedUnitId.value = expandedUnitId.value === unitId ? null : unitId
}

/** Widest bar in the set, so bars are comparable to each other rather than to 100%. */
const maxAbsDeviation = computed(() =>
  Math.max(0.05, ...props.subSite.units.map((unit) => Math.abs(unit.deviation_pct))),
)

function barWidthPercent(unit: SubSiteUnit): number {
  return (Math.abs(unit.deviation_pct) / maxAbsDeviation.value) * 50
}

/**
 * Severity bands. Only shortfalls are graded — an inverter above its siblings is
 * not "good news" worth a colour, it is simply the other side of the median.
 */
function severity(unit: SubSiteUnit): 'critical' | 'serious' | 'warning' | 'normal' {
  const deviation = unit.deviation_pct
  if (deviation <= -0.4) return 'critical'
  if (deviation <= -0.2) return 'serious'
  if (deviation <= props.subSite.flag_threshold_pct) return 'warning'
  return 'normal'
}

const SEVERITY_GLYPH = { critical: '▲', serious: '▲', warning: '◆', normal: '●' } as const

function sparklinePath(unit: SubSiteUnit): string {
  const points = unit.series
  if (points.length < 2) return ''
  const values = points.map((point) => point.ratio_to_sibling_median)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 100
      const y = 18 - ((value - min) / range) * 16
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
}

function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}%`
}

/**
 * With exactly two units the median sits midway between them, so deviations are
 * always a symmetric plus/minus pair. Worth saying rather than letting a reader
 * over-read a mirrored number.
 */
const twoUnitCaveat = computed(() => props.subSite.unit_count === 2)
</script>

<template>
  <section class="sub">
    <header class="sub__head">
      <h2 class="sub__heading">
        Inverter breakdown
        <span class="sub__count">{{ subSite.unit_count }} {{ subSite.unit_type }}s</span>
      </h2>
      <DataStatusBadge :status="subSite.data_status" small />
    </header>

    <p class="sub__method">
      {{ subSite.method }} · flagged below {{ formatPercent(subSite.flag_threshold_pct) }}
    </p>
    <p class="sub__basis">{{ subSite.comparison_basis }}</p>

    <!-- The most important caveat on this panel: are these units even comparable? -->
    <p v-if="!subSite.units_comparable" class="sub__caveat sub__caveat--hard">
      ⚠ {{ subSite.comparability_note }}
    </p>
    <p v-else-if="subSite.comparability_note" class="sub__ok">
      ✓ {{ subSite.comparability_note }}
    </p>

    <p v-if="twoUnitCaveat" class="sub__caveat">
      ⚠ With two units the median lies midway between them, so deviations are always a
      symmetric pair. Read the magnitude, not the sign balance.
    </p>

    <ol class="units">
      <li v-for="unit in subSite.units" :key="unit.unit_id" class="unit">
        <button class="unit__row" type="button" @click="toggle(unit.unit_id)">
          <span class="unit__id">
            <span class="unit__glyph" :class="`unit__glyph--${severity(unit)}`" aria-hidden="true">
              {{ SEVERITY_GLYPH[severity(unit)] }}
            </span>
            {{ unit.unit_id }}
          </span>

          <span class="unit__bar" aria-hidden="true">
            <span class="unit__axis"></span>
            <span
              class="unit__fill"
              :class="[
                `unit__fill--${severity(unit)}`,
                unit.deviation_pct < 0 ? 'unit__fill--negative' : 'unit__fill--positive',
              ]"
              :style="{ width: barWidthPercent(unit) + '%' }"
            ></span>
          </span>

          <svg class="unit__spark" viewBox="0 0 100 20" preserveAspectRatio="none" aria-hidden="true">
            <path :d="sparklinePath(unit)" fill="none" stroke="currentColor" stroke-width="1.5" />
          </svg>

          <span class="unit__deviation" :class="`unit__deviation--${severity(unit)}`">
            {{ formatPercent(unit.deviation_pct) }}
          </span>

          <span class="unit__mean">{{ unit.mean_kwh_daily.toFixed(0) }} kWh/day</span>

          <span class="unit__status">{{ unit.status }}</span>
        </button>

        <div v-if="expandedUnitId === unit.unit_id" class="detail">
          <dl class="detail__facts">
            <div>
              <dt>Mean daily output</dt>
              <dd>{{ unit.mean_kwh_daily.toFixed(1) }} kWh</dd>
            </div>
            <div>
              <dt>Sibling median</dt>
              <dd>{{ unit.sibling_median_kwh_daily.toFixed(1) }} kWh</dd>
            </div>
            <div>
              <dt>Deviation</dt>
              <dd>{{ formatPercent(unit.deviation_pct) }}</dd>
            </div>
            <div>
              <dt>Days of data</dt>
              <dd>{{ unit.series.length }}</dd>
            </div>
          </dl>

          <p class="detail__label">Ratio to sibling median, last {{ unit.series.length }} days</p>
          <svg class="detail__trace" viewBox="0 0 100 20" preserveAspectRatio="none">
            <path :d="sparklinePath(unit)" fill="none" stroke="currentColor" stroke-width="1" />
          </svg>

          <!-- Thermal evidence slot. M5 (owner B). Renders nothing when absent,
               which is the required behaviour per docs/Schema.md 8.8. -->
          <div class="detail__thermal">
            <p class="detail__label">Thermal evidence</p>
            <template v-if="evidence && evidence.has_imagery && evidence.image_url">
              <img :src="evidence.image_url" :alt="`Thermal image for ${unit.unit_id}`" class="detail__image" />
              <p class="detail__caption">
                {{ evidence.defect_class }} ·
                {{ evidence.confidence ? Math.round(evidence.confidence * 100) + '%' : '' }} ·
                captured {{ evidence.captured_date }}
                <DataStatusBadge v-if="evidence.data_status" :status="evidence.data_status" small />
              </p>
            </template>
            <p v-else class="detail__empty">
              No imagery for this site. The flag stands on electrical evidence alone —
              PRD v2 section 5. Thermal capture is M5 (owner B).
            </p>
          </div>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.sub {
  padding: 1.25rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}

.sub__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.sub__heading {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.sub__count {
  font-weight: 400;
  letter-spacing: 0;
  text-transform: none;
  font-size: 0.8rem;
}

.sub__method,
.sub__basis {
  margin: 0.5rem 0 0;
  font-size: 0.76rem;
  color: var(--text-muted);
  line-height: 1.5;
}

.sub__caveat {
  margin: 0.75rem 0 0;
  padding: 0.5rem 0.7rem;
  border-left: 3px solid var(--status-serious);
  font-size: 0.78rem;
  line-height: 1.5;
  color: var(--text-secondary);
}

.sub__caveat--hard {
  border-left-color: var(--status-critical);
  background: var(--page-plane);
}

.sub__ok {
  margin: 0.75rem 0 0;
  padding: 0.5rem 0.7rem;
  border-left: 3px solid var(--status-good);
  font-size: 0.78rem;
  line-height: 1.5;
  color: var(--text-muted);
}

.units {
  list-style: none;
  margin: 1rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.unit__row {
  display: grid;
  grid-template-columns: 4.5rem 1fr 3.5rem 4.5rem 6rem 4.5rem;
  gap: 0.75rem;
  align-items: center;
  width: 100%;
  padding: 0.5rem 0.6rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.unit__row:hover,
.unit__row:focus-visible {
  border-color: var(--border-hairline);
  outline: none;
}

@media (max-width: 760px) {
  .unit__row {
    grid-template-columns: 4.5rem 1fr 4.5rem;
  }
  .unit__spark,
  .unit__mean,
  .unit__status {
    display: none;
  }
}

.unit__id {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-weight: 600;
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
}

.unit__glyph--critical {
  color: var(--status-critical);
}
.unit__glyph--serious {
  color: var(--status-serious);
}
.unit__glyph--warning {
  color: var(--status-warning);
}
.unit__glyph--normal {
  color: var(--status-good);
}

/* Diverging bar around a centre axis: shortfall left, surplus right. */
.unit__bar {
  position: relative;
  display: block;
  height: 14px;
}

.unit__axis {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--baseline);
}

.unit__fill {
  position: absolute;
  top: 2px;
  bottom: 2px;
  border-radius: 2px;
}

.unit__fill--negative {
  right: 50%;
}

.unit__fill--positive {
  left: 50%;
}

.unit__fill--critical {
  background: var(--status-critical);
}
.unit__fill--serious {
  background: var(--status-serious);
}
.unit__fill--warning {
  background: var(--status-warning);
}
.unit__fill--normal {
  background: var(--text-muted);
  opacity: 0.5;
}

.unit__spark {
  width: 100%;
  height: 20px;
  color: var(--text-muted);
}

.unit__deviation {
  font-size: 0.82rem;
  font-weight: 700;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.unit__deviation--critical {
  color: var(--status-critical);
}
.unit__deviation--serious {
  color: var(--status-serious);
}
.unit__deviation--normal,
.unit__deviation--warning {
  color: var(--text-secondary);
}

.unit__mean {
  font-size: 0.78rem;
  color: var(--text-muted);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.unit__status {
  font-size: 0.68rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-muted);
  text-align: right;
}

/* --- Expanded detail --- */

.detail {
  padding: 0.9rem 0.6rem 0.6rem;
  border-left: 2px solid var(--border-hairline);
  margin: 0.2rem 0 0.4rem 1rem;
}

.detail__facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.6rem 1rem;
  margin: 0 0 0.9rem;
}

.detail__facts div {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.detail__facts dt {
  font-size: 0.66rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.detail__facts dd {
  margin: 0;
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
}

.detail__label {
  margin: 0 0 0.3rem;
  font-size: 0.66rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.detail__trace {
  width: 100%;
  height: 48px;
  color: var(--series-1);
  margin-bottom: 0.9rem;
}

.detail__thermal {
  padding-top: 0.6rem;
  border-top: 1px solid var(--border-hairline);
}

.detail__image {
  max-width: 100%;
  border-radius: var(--radius-sm);
}

.detail__caption {
  margin: 0.4rem 0 0;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.detail__empty {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--text-muted);
}
</style>

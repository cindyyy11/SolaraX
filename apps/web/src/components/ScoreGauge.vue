<script setup lang="ts">
/**
 * A compact radial meter — one glance at a category's exposure instead of a
 * paragraph. Used on the Resilience screen's six category cards.
 *
 * A `not-connected` category never draws a proportional arc — there is no
 * measurement to show a proportion of. It renders a dashed, textured ring
 * instead (never a bare 0%, which would misread as "confirmed fine" rather
 * than "no source connected").
 */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    score: number
    tone: 'good' | 'warning' | 'critical' | 'neutral'
    connected?: boolean
    size?: number
    /** For the app's dark "instrument panel" cards (Recovery Tracker,
     * Reports' dark sections), which hardcode a palette rather than using
     * the light/dark-flipping design tokens the default variant reads. */
    dark?: boolean
  }>(),
  { connected: true, size: 64, dark: false },
)

const radius = computed(() => props.size / 2 - 5)
const circumference = computed(() => 2 * Math.PI * radius.value)
const offset = computed(() => circumference.value * (1 - Math.min(1, Math.max(0, props.score))))
const center = computed(() => props.size / 2)
</script>

<template>
  <svg
    :width="size"
    :height="size"
    :viewBox="`0 0 ${size} ${size}`"
    class="gauge"
    :class="[`gauge--${tone}`, { 'gauge--dark': dark }]"
    role="img"
    :aria-label="connected ? `${Math.round(score * 100)} percent` : 'Not connected'"
  >
    <circle
      :cx="center"
      :cy="center"
      :r="radius"
      class="gauge__track"
      :class="{ 'gauge__track--dashed': !connected }"
      fill="none"
    />
    <circle
      v-if="connected"
      :cx="center"
      :cy="center"
      :r="radius"
      class="gauge__value"
      fill="none"
      :stroke-dasharray="circumference"
      :stroke-dashoffset="offset"
      :transform="`rotate(-90 ${center} ${center})`"
    />
    <text v-if="connected" :x="center" :y="center" class="gauge__label" text-anchor="middle" dominant-baseline="central">
      {{ Math.round(score * 100) }}<tspan class="gauge__unit">%</tspan>
    </text>
    <text v-else :x="center" :y="center" class="gauge__label gauge__label--dash" text-anchor="middle" dominant-baseline="central">—</text>
  </svg>
</template>

<style scoped>
.gauge__track {
  stroke: var(--surface-2);
  stroke-width: 5;
}
.gauge__track--dashed {
  stroke: var(--baseline);
  stroke-dasharray: 3 4;
}
.gauge__value {
  stroke-width: 5;
  stroke-linecap: round;
  transition: stroke-dashoffset var(--duration-base) var(--ease-out);
}
.gauge--good .gauge__value {
  stroke: var(--status-good);
}
.gauge--warning .gauge__value {
  stroke: var(--status-warning);
}
.gauge--critical .gauge__value {
  stroke: var(--status-critical);
}
.gauge--neutral .gauge__value {
  stroke: var(--text-muted);
}
.gauge__label {
  fill: var(--text-primary);
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
}
.gauge__unit {
  font-size: 9px;
  fill: var(--text-muted);
}
.gauge__label--dash {
  fill: var(--text-muted);
  font-size: 18px;
}
/* Dark instrument-panel variant — hardcoded to match Recovery Tracker's own
   hardcoded dark palette (#21332d track, #7be0a5 good accent) rather than
   the light/dark-flipping tokens, which would go near-invisible against a
   permanently-dark card. */
.gauge--dark .gauge__track {
  stroke: #21332d;
}
.gauge--dark .gauge__track--dashed {
  stroke: #344941;
}
.gauge--dark.gauge--good .gauge__value {
  stroke: #7be0a5;
}
.gauge--dark.gauge--warning .gauge__value {
  stroke: #f2c47f;
}
.gauge--dark.gauge--critical .gauge__value {
  stroke: #e88a7d;
}
.gauge--dark.gauge--neutral .gauge__value {
  stroke: #9eb0aa;
}
.gauge--dark .gauge__label {
  fill: #eff5f2;
}
.gauge--dark .gauge__unit,
.gauge--dark .gauge__label--dash {
  fill: #96aaa3;
}
@media (prefers-reduced-motion: reduce) {
  .gauge__value {
    transition: none;
  }
}
</style>

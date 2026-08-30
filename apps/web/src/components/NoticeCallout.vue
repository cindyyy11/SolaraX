<script setup lang="ts">
/**
 * A tinted, full-bordered notice — one shared idiom for every alert-shaped
 * block in the product, replacing the colored `border-left` accent bar that
 * used to be hand-rolled independently in eleven different places.
 *
 * A colored left border reads as a leftover default (email-client blockquote,
 * unstyled admin panel), not a decision. A tinted surface with a matching icon
 * carries the same "pay attention" signal without looking accidental — and
 * unifying it here means all eleven instances change together, once.
 *
 * Tone maps to the RESERVED status colors — `warning` / `critical` / `good` —
 * plus `info` for a neutral, brand-toned note (data source lines, non-triage
 * context). It is a rendering of an existing status, never a new one: this
 * component does not decide meaning, callers do.
 */
import { computed, type Component } from 'vue'
import { TriangleAlert, CircleAlert, CircleCheck, Info } from '@lucide/vue'

type Tone = 'warning' | 'critical' | 'good' | 'info'

const props = withDefaults(
  defineProps<{
    tone: Tone
    /** Compact form: smaller padding and type, for a note inside a dense card. */
    compact?: boolean
    /** Override the tone's default icon — the color/tint still comes from `tone`. */
    icon?: Component
  }>(),
  { compact: false },
)

const TONE_ICON = {
  warning: TriangleAlert,
  critical: CircleAlert,
  good: CircleCheck,
  info: Info,
} as const

const resolvedIcon = computed(() => props.icon ?? TONE_ICON[props.tone])
</script>

<template>
  <div class="callout" :class="[`callout--${tone}`, { 'callout--compact': compact }]" role="note">
    <component
      :is="resolvedIcon"
      class="callout__icon"
      :size="compact ? 14 : 16"
      aria-hidden="true"
    />
    <div class="callout__body"><slot /></div>
  </div>
</template>

<style scoped>
.callout {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding: 0.65rem 0.85rem;
  border: 1px solid;
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  line-height: 1.5;
}

.callout--compact {
  padding: 0.45rem 0.65rem;
  font-size: 0.78rem;
  gap: 0.45rem;
}

.callout__icon {
  flex: none;
  margin-top: 0.15em;
}

.callout__body {
  min-width: 0;
  color: var(--text-secondary);
}

.callout__body :deep(strong) {
  color: var(--text-primary);
}

.callout--warning {
  background: var(--callout-warning-bg);
  border-color: var(--callout-warning-border);
}
.callout--warning .callout__icon {
  color: var(--status-warning);
}

.callout--critical {
  background: var(--callout-critical-bg);
  border-color: var(--callout-critical-border);
}
.callout--critical .callout__icon {
  color: var(--status-critical);
}

.callout--good {
  background: var(--callout-good-bg);
  border-color: var(--callout-good-border);
}
.callout--good .callout__icon {
  color: var(--status-good);
}

.callout--info {
  background: var(--callout-info-bg);
  border-color: var(--callout-info-border);
}
.callout--info .callout__icon {
  color: var(--brand-ink);
  opacity: 0.75;
}
</style>

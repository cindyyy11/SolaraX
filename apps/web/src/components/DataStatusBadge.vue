<script setup lang="ts">
/**
 * Renders a `data_status` value. Every card that displays data must carry one —
 * PRD v2 section 6 requires it, and docs/Schema.md section 2.1 defines the values.
 *
 * Styled as an outlined chip rather than a filled pill so it reads as provenance
 * metadata, not as triage state. The site status badges are filled; keeping these
 * two visual languages apart is deliberate — a judge should never confuse
 * "this site needs a visit" with "this number is scaffolding".
 */
import { computed } from 'vue'
import type { DataStatus } from '@/types/dispatch'

const props = withDefaults(
  defineProps<{
    status: DataStatus
    /** Compact form for dense rows. */
    small?: boolean
  }>(),
  { small: false },
)

const EXPLANATIONS: Record<DataStatus, string> = {
  BUILT: 'Real data through a real model.',
  SIMULATED: 'Real method, sample or synthetic input.',
  PLACEHOLDER: 'Temporary stand-in for an unbuilt module. Must not survive to submission.',
}

const title = computed(() => `${props.status} — ${EXPLANATIONS[props.status]}`)
</script>

<template>
  <span
    class="badge"
    :class="[`badge--${status.toLowerCase()}`, { 'badge--small': small }]"
    :title="title"
  >
    <span class="badge__glyph" aria-hidden="true">
      {{ status === 'BUILT' ? '●' : status === 'SIMULATED' ? '◐' : '○' }}
    </span>
    <span class="badge__text">{{ status }}</span>
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35em;
  padding: 0.2em 0.55em;
  border: 1px solid currentColor;
  border-radius: var(--radius-sm);
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  line-height: 1.4;
  white-space: nowrap;
}

.badge--small {
  font-size: 0.62rem;
  padding: 0.12em 0.4em;
}

.badge__glyph {
  font-size: 0.85em;
}

/* Color is a reinforcement here — the text label always carries the meaning. */
.badge--built {
  color: var(--success-text);
}

.badge--simulated {
  color: var(--text-secondary);
}

.badge--placeholder {
  color: var(--status-critical);
}
</style>

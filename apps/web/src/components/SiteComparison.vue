<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { formatCapacity, formatRinggit } from '@/services/api'
import type { Site } from '@/types/dispatch'

const props = defineProps<{ subject: Site; sites: Site[] }>()
const peerId = ref('')

const peers = computed(() => props.sites.filter((site) => site.site_id !== props.subject.site_id))
const peer = computed(
  () => peers.value.find((site) => site.site_id === peerId.value) ?? peers.value[0],
)

watch(
  peers,
  (next) => {
    if (!next.some((site) => site.site_id === peerId.value)) peerId.value = next[0]?.site_id ?? ''
  },
  { immediate: true },
)

const rows = computed(() => {
  const comparison = peer.value
  if (!comparison) return []
  return [
    {
      label: 'Capacity',
      subject: formatCapacity(props.subject.capacity_kwp),
      peer: formatCapacity(comparison.capacity_kwp),
    },
    { label: 'Triage status', subject: props.subject.status, peer: comparison.status },
    {
      label: 'Monthly loss',
      subject: props.subject.economics
        ? `${Math.round(props.subject.economics.kwh_lost_monthly).toLocaleString('en-MY')} kWh`
        : 'Not assessed',
      peer: comparison.economics
        ? `${Math.round(comparison.economics.kwh_lost_monthly).toLocaleString('en-MY')} kWh`
        : 'Not assessed',
    },
    {
      label: 'Monthly value at risk',
      subject: props.subject.economics
        ? formatRinggit(props.subject.economics.rm_at_risk_monthly)
        : 'Not assessed',
      peer: comparison.economics
        ? formatRinggit(comparison.economics.rm_at_risk_monthly)
        : 'Not assessed',
    },
    {
      label: 'Days diverging',
      subject: props.subject.divergence ? String(props.subject.divergence.days_since) : '—',
      peer: comparison.divergence ? String(comparison.divergence.days_since) : '—',
    },
    {
      label: 'Detection score',
      subject: props.subject.detection ? String(props.subject.detection.score) : '—',
      peer: comparison.detection ? String(comparison.detection.score) : '—',
    },
  ]
})
</script>

<template>
  <section v-if="peer" class="compare card card--interactive" aria-labelledby="site-comparison-title">
    <header>
      <div>
        <h2 id="site-comparison-title">Compare with another fleet site</h2>
        <p>Real values from the same dispatch run.</p>
      </div>
      <label
        ><span>Comparison site</span
        ><select v-model="peerId">
          <option v-for="site in peers" :key="site.site_id" :value="site.site_id">
            {{ site.name }}
          </option>
        </select></label
      >
    </header>
    <div class="compare__table" role="table" aria-label="Site comparison">
      <div class="compare__row compare__row--head" role="row">
        <span role="columnheader">Metric</span
        ><strong role="columnheader">{{ subject.name }}</strong
        ><strong role="columnheader">{{ peer.name }}</strong>
      </div>
      <div v-for="row in rows" :key="row.label" class="compare__row" role="row">
        <span role="cell">{{ row.label }}</span
        ><strong role="cell">{{ row.subject }}</strong
        ><strong role="cell">{{ row.peer }}</strong>
      </div>
    </div>
  </section>
</template>

<style scoped>
.compare {
  padding: 1.1rem;
}
.compare header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
}
.compare h2 {
  margin: 0;
  font-size: 1rem;
}
.compare header p {
  margin: 0.25rem 0 0;
  color: var(--text-muted);
  font-size: 0.72rem;
}
.compare label {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  color: var(--text-muted);
  font-size: 0.64rem;
  font-weight: 650;
}
.compare select {
  min-height: 42px;
  max-width: 21rem;
  padding: 0 2rem 0 0.65rem;
  color: var(--text-primary);
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  font: inherit;
}
.compare__table {
  margin-top: 1rem;
  border-top: 1px solid var(--border-hairline);
}
.compare__row {
  display: grid;
  grid-template-columns: minmax(9rem, 0.7fr) 1fr 1fr;
  gap: 1rem;
  min-height: 3rem;
  align-items: center;
  border-bottom: 1px solid var(--border-hairline);
}
.compare__row > span {
  color: var(--text-muted);
  font-size: 0.69rem;
}
.compare__row strong {
  font-size: 0.75rem;
  font-weight: 600;
}
.compare__row--head {
  min-height: 4rem;
}
.compare__row--head strong {
  color: var(--text-secondary);
}
@media (max-width: 700px) {
  .compare header {
    align-items: stretch;
    flex-direction: column;
  }
  .compare select {
    max-width: none;
    width: 100%;
  }
  .compare__table {
    overflow-x: auto;
  }
  .compare__row {
    min-width: 38rem;
  }
}
</style>

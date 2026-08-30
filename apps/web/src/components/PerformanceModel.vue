<script setup lang="ts">
import { computed } from 'vue'
import { ArrowRight, CloudSun, Gauge, GitCompareArrows, WalletCards } from '@lucide/vue'
import { formatRinggit } from '@/services/api'
import type { Site } from '@/types/dispatch'

const props = defineProps<{ site: Site }>()

const expectedMonthly = computed(() => {
  const economics = props.site.economics
  if (!economics || economics.loss_pct_of_expected <= 0) return null
  return economics.kwh_lost_monthly / economics.loss_pct_of_expected
})

const actualMonthly = computed(() => {
  if (expectedMonthly.value === null || !props.site.economics) return null
  return Math.max(0, expectedMonthly.value - props.site.economics.kwh_lost_monthly)
})

function formatEnergy(value: number | null): string {
  if (value === null) return 'Not available'
  return `${Math.round(value).toLocaleString('en-MY')} kWh/mo`
}
</script>

<template>
  <section class="model card--dark card--interactive" aria-labelledby="performance-model-title">
    <header class="model__head">
      <div>
        <h2 id="performance-model-title">How the recommendation is formed</h2>
        <p>A data model of the decision path—not a physical model of the roof.</p>
      </div>
      <span>{{ site.data_status.toLowerCase() }} evidence</span>
    </header>

    <div class="model__flow">
      <article class="model__node">
        <CloudSun :size="22" aria-hidden="true" />
        <span>Conditions</span>
        <strong>Satellite-derived</strong>
        <small>Sensor-free irradiance and temperature input</small>
      </article>
      <ArrowRight class="model__arrow" :size="18" aria-hidden="true" />
      <article class="model__node">
        <Gauge :size="22" aria-hidden="true" />
        <span>Expected → actual</span>
        <strong>{{ formatEnergy(expectedMonthly) }}</strong>
        <small
          >{{ formatEnergy(actualMonthly) }} actual ·
          {{ Math.round((site.economics?.loss_pct_of_expected ?? 0) * 100) }}% gap</small
        >
      </article>
      <ArrowRight class="model__arrow" :size="18" aria-hidden="true" />
      <article class="model__node">
        <GitCompareArrows :size="22" aria-hidden="true" />
        <span>Fleet comparison</span>
        <strong>{{
          site.detection
            ? `${site.detection.score} ${site.detection.score_type.replaceAll('_', ' ')}`
            : 'Within tolerance'
        }}</strong>
        <small>{{
          site.detection
            ? `${Math.round(site.detection.confidence * 100)}% detection confidence`
            : 'No anomaly recorded'
        }}</small>
      </article>
      <ArrowRight class="model__arrow" :size="18" aria-hidden="true" />
      <article class="model__node model__node--outcome">
        <WalletCards :size="22" aria-hidden="true" />
        <span>Economic decision</span>
        <strong>{{
          site.economics ? formatRinggit(site.economics.rm_at_risk_monthly) : 'No estimate'
        }}</strong>
        <small>{{
          site.economics?.exceeds_dispatch_threshold
            ? 'Dispatch threshold exceeded'
            : 'Below dispatch threshold'
        }}</small>
      </article>
    </div>

    <p class="model__note">
      Values come from the dispatch artifact. SolaraX does not infer panel placement, roof geometry,
      or equipment layout from these measurements.
    </p>
  </section>
</template>

<style scoped>
.model {
  padding: 1.1rem;
  color: var(--nav-text-strong);
  overflow: hidden;
}
.model__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}
.model__head h2 {
  margin: 0;
  font-size: 1rem;
}
.model__head p {
  margin: 0.3rem 0 0;
  color: var(--nav-text);
  font-size: 0.75rem;
}
.model__head > span {
  padding: 0.4rem 0.55rem;
  color: var(--nav-active-text);
  background: var(--nav-active);
  border: 1px solid var(--nav-active-border);
  border-radius: var(--radius-sm);
  font-size: 0.65rem;
  font-weight: 700;
  white-space: nowrap;
}
.model__flow {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr;
  gap: 0.55rem;
  align-items: center;
  margin-top: 1rem;
}
.model__node {
  display: flex;
  min-height: 10.5rem;
  flex-direction: column;
  padding: 0.9rem;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
}
.model__node svg {
  color: var(--nav-text);
}
.model__node > span {
  margin-top: auto;
  color: var(--nav-text);
  font-size: 0.64rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.model__node strong {
  margin-top: 0.35rem;
  font: 650 1rem/1.2 var(--font-display);
}
.model__node small {
  margin-top: 0.35rem;
  color: var(--nav-text);
  font-size: 0.67rem;
  line-height: 1.4;
}
.model__node--outcome {
  background: var(--nav-active);
  border-color: var(--nav-active-border);
}
.model__node--outcome svg,
.model__node--outcome strong {
  color: var(--nav-active-text);
}
.model__arrow {
  color: var(--nav-text);
  opacity: 0.55;
}
.model__note {
  margin: 1rem 0 0;
  color: var(--nav-text);
  font-size: 0.68rem;
  line-height: 1.45;
}
@media (max-width: 900px) {
  .model__flow {
    grid-template-columns: 1fr;
  }
  .model__arrow {
    justify-self: center;
    transform: rotate(90deg);
  }
  .model__node {
    min-height: 8rem;
  }
  .model__node > span {
    margin-top: 1.5rem;
  }
}
@media (prefers-reduced-motion: no-preference) {
  .model__node {
    animation: model-enter 220ms var(--ease-out) both;
  }
  .model__node:nth-of-type(2) {
    animation-delay: 45ms;
  }
  .model__node:nth-of-type(3) {
    animation-delay: 90ms;
  }
  .model__node:nth-of-type(4) {
    animation-delay: 135ms;
  }
  @keyframes model-enter {
    from {
      opacity: 0.35;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }
}
</style>

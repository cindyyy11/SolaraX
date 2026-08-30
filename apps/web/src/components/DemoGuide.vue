<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { ArrowLeft, ArrowRight, Play, X } from '@lucide/vue'

const steps = [
  {
    target: 'fleet-decision',
    title: 'Start with the decision',
    body: 'SolaraX leads with the maintenance conclusion, then shows the fleet size and evidence status behind it.',
  },
  {
    target: 'fleet-signals',
    title: 'Price the exception',
    body: 'Economic exposure, dispatch count, watch list, and cleared sites establish the operating picture in one scan.',
  },
  {
    target: 'spatial-workspace',
    title: 'See risk spatially',
    body: 'Map, aerial, and 3D modes share the same sites. In 3D, column height is measured monthly ringgit at risk.',
  },
  {
    target: 'priority-queue',
    title: 'Explain the ranking',
    body: 'The queue shows which site is closest to action, why it diverged, and how long the signal has persisted.',
  },
  {
    target: 'fleet-outcome',
    title: 'Count avoided work',
    body: 'The business value includes trips the system confidently recommends against—not only faults it flags.',
  },
] as const

const open = ref(false)
const step = ref(0)
const currentStep = computed(() => steps[step.value] ?? steps[0]!)

function clearTarget(): void {
  document.querySelector('[data-demo-focus]')?.removeAttribute('data-demo-focus')
}

function focusStep(): void {
  clearTarget()
  const target = document.getElementById(currentStep.value.target)
  target?.setAttribute('data-demo-focus', '')
  target?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function start(): void {
  open.value = true
  step.value = 0
  requestAnimationFrame(focusStep)
}

function close(): void {
  open.value = false
  clearTarget()
}

function move(direction: -1 | 1): void {
  const next = step.value + direction
  if (next < 0) return
  if (next >= steps.length) {
    close()
    return
  }
  step.value = next
  focusStep()
}

onBeforeUnmount(clearTarget)
</script>

<template>
  <button v-if="!open" type="button" class="demo-launch" @click="start">
    <Play :size="15" aria-hidden="true" /> Guided demo
  </button>

  <aside v-else class="demo" aria-live="polite" aria-label="Guided product demo">
    <div class="demo__topline">
      <span>Step {{ step + 1 }} of {{ steps.length }}</span>
      <button type="button" aria-label="Close guided demo" @click="close">
        <X :size="17" aria-hidden="true" />
      </button>
    </div>
    <h2>{{ currentStep.title }}</h2>
    <p>{{ currentStep.body }}</p>
    <div class="demo__actions">
      <button type="button" :disabled="step === 0" @click="move(-1)">
        <ArrowLeft :size="15" aria-hidden="true" /> Back
      </button>
      <button type="button" class="demo__next" @click="move(1)">
        {{ step === steps.length - 1 ? 'Finish' : 'Next' }}
        <ArrowRight :size="15" aria-hidden="true" />
      </button>
    </div>
  </aside>
</template>

<style scoped>
.demo-launch {
  position: fixed;
  right: 1.25rem;
  bottom: 1.25rem;
  z-index: var(--z-fab);
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  gap: 0.45rem;
  padding: 0 0.85rem;
  color: var(--nav-text-strong);
  background: var(--nav-surface);
  border: 1px solid var(--nav-border);
  border-radius: var(--radius-full);
  font: 650 0.72rem var(--font-display);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
  cursor: pointer;
}
.demo {
  position: fixed;
  right: 1.25rem;
  bottom: 1.25rem;
  z-index: var(--z-overlay);
  width: min(23rem, calc(100vw - 2rem));
  padding: 1rem;
  color: var(--nav-text-strong);
  background: var(--nav-surface);
  border: 1px solid var(--nav-active-border);
  border-radius: var(--radius-lg);
  box-shadow: 0 22px 60px rgba(0, 0, 0, 0.34);
}
.demo__topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--nav-active-text);
  font-size: 0.66rem;
  font-weight: 750;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.demo__topline button {
  display: grid;
  width: 2.25rem;
  height: 2.25rem;
  place-items: center;
  color: var(--nav-text);
  background: transparent;
  border: 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.demo h2 {
  margin: 0.65rem 0 0;
  font-size: 1.05rem;
}
.demo p {
  margin: 0.45rem 0 1rem;
  color: var(--nav-text);
  font-size: 0.76rem;
  line-height: 1.55;
}
.demo__actions {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}
.demo__actions button {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  gap: 0.35rem;
  padding: 0 0.75rem;
  color: var(--nav-text-strong);
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: var(--radius-md);
  font: 650 0.72rem var(--font-display);
  cursor: pointer;
}
.demo__actions button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.demo__actions .demo__next {
  margin-left: auto;
  color: var(--action-ink);
  background: var(--action-fill);
  border-color: var(--action-fill);
}
@media (prefers-reduced-motion: no-preference) {
  .demo {
    animation: demo-enter 220ms var(--ease-out) both;
  }
  @keyframes demo-enter {
    from {
      opacity: 0;
      transform: translateY(16px) scale(0.97);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }
}
@media (max-width: 760px) {
  .demo-launch {
    right: 1rem;
    bottom: 1rem;
  }
  .demo {
    right: 1rem;
    bottom: 1rem;
  }
}
</style>

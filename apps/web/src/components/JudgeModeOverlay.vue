<script setup lang="ts">
/**
 * The guided sequence itself. Docked, not modal — it never blocks the
 * screen it is narrating, because the point is to walk a judge through the
 * same live product an operator uses, not a separate slideshow. Routes to
 * the same screens Operator Mode uses, via judgeMode.ts; introduces no data
 * of its own. See the design spec's "Judge Mode uses the same data and
 * state as Operator Mode" acceptance criterion.
 */
import { computed } from 'vue'
import { CircleCheck, X, ArrowLeft, ArrowRight } from '@lucide/vue'
import { exitJudgeMode, goToJudgeStep, judgeModeState, nextJudgeStep, previousJudgeStep } from '@/services/judgeMode'

const currentStep = computed(() => judgeModeState.steps[judgeModeState.index])
const isFirst = computed(() => judgeModeState.index === 0)
const isLast = computed(() => judgeModeState.index === judgeModeState.steps.length - 1)
</script>

<template>
  <aside v-if="judgeModeState.active && currentStep" class="judge" role="complementary" aria-label="Judge Mode guided walkthrough">
    <header class="judge__head">
      <span class="judge__badge">Judge Mode · step {{ judgeModeState.index + 1 }} of {{ judgeModeState.steps.length }}</span>
      <button type="button" class="judge__close" aria-label="Exit Judge Mode" @click="exitJudgeMode"><X :size="15" aria-hidden="true" /></button>
    </header>
    <h2>{{ currentStep.title }}</h2>
    <p>{{ currentStep.description }}</p>
    <ol class="judge__steps" aria-label="All steps">
      <li v-for="(step, index) in judgeModeState.steps" :key="step.id">
        <button
          type="button"
          :class="{ 'judge__step--active': index === judgeModeState.index, 'judge__step--done': index < judgeModeState.index }"
          :aria-current="index === judgeModeState.index ? 'step' : undefined"
          @click="goToJudgeStep(index)"
        >
          <CircleCheck v-if="index < judgeModeState.index" :size="13" aria-hidden="true" />
          <span v-else>{{ index + 1 }}</span>
          {{ step.title }}
        </button>
      </li>
    </ol>
    <footer class="judge__nav">
      <button type="button" :disabled="isFirst" @click="previousJudgeStep"><ArrowLeft :size="14" aria-hidden="true" /> Back</button>
      <button v-if="!isLast" type="button" class="judge__next" @click="nextJudgeStep">Next <ArrowRight :size="14" aria-hidden="true" /></button>
      <button v-else type="button" class="judge__next" @click="exitJudgeMode">Finish</button>
    </footer>
  </aside>
</template>

<style scoped>
.judge {
  position: fixed;
  right: 1rem;
  bottom: 1rem;
  z-index: var(--z-nav);
  width: min(340px, calc(100vw - 2rem));
  max-height: min(78vh, 620px);
  overflow-y: auto;
  padding: 1.1rem;
  color: #eff5f2;
  background: #13211d;
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 48px rgba(9, 22, 18, 0.32);
}
.judge__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
}
.judge__badge {
  padding: 0.2rem 0.5rem;
  color: #172921;
  background: #7be0a5;
  border-radius: var(--radius-sm);
  font-size: 0.6rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.judge__close {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  color: #9fb0aa;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.judge h2 {
  margin: 0.75rem 0 0.35rem;
  font-family: var(--font-display);
  font-size: 1.05rem;
  letter-spacing: -0.02em;
}
.judge > p {
  margin: 0;
  color: #aebdb8;
  font-size: 0.78rem;
  line-height: 1.55;
}
.judge__steps {
  margin: 0.9rem 0 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid rgba(255, 255, 255, 0.09);
}
.judge__steps li {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.judge__steps button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.2rem;
  color: #9fb0aa;
  background: transparent;
  border: 0;
  font: inherit;
  font-size: 0.72rem;
  text-align: left;
  cursor: pointer;
}
.judge__steps button span {
  display: grid;
  flex: none;
  place-items: center;
  width: 16px;
  height: 16px;
  border: 1px solid currentColor;
  border-radius: 50%;
  font-size: 0.58rem;
}
.judge__steps svg {
  flex: none;
  color: #7be0a5;
}
.judge__step--active {
  color: #eff5f2;
  font-weight: 700;
}
.judge__step--done {
  color: #cddad5;
}
.judge__nav {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}
.judge__nav button {
  display: inline-flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  min-height: 40px;
  padding: 0.5rem 0.6rem;
  color: #dce7e2;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm);
  font: 700 0.72rem var(--font-sans);
  cursor: pointer;
}
.judge__nav button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.judge__next {
  color: #172921 !important;
  background: #7be0a5 !important;
  border-color: #7be0a5 !important;
}
@media print {
  .judge {
    display: none;
  }
}
</style>

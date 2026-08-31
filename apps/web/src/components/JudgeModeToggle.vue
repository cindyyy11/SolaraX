<script setup lang="ts">
/**
 * Small nav-rail control that starts Judge Mode. The guided sequence itself
 * renders from JudgeModeOverlay.vue, mounted once in App.vue — this button
 * only starts and stops it.
 */
import { Presentation } from '@lucide/vue'
import { enterJudgeMode, exitJudgeMode, judgeModeState } from '@/services/judgeMode'

function toggle(): void {
  if (judgeModeState.active) exitJudgeMode()
  else enterJudgeMode()
}
</script>

<template>
  <button
    type="button"
    class="judge-toggle"
    :class="{ 'judge-toggle--active': judgeModeState.active }"
    :aria-pressed="judgeModeState.active"
    @click="toggle"
  >
    <Presentation :size="17" aria-hidden="true" />
    <span>{{ judgeModeState.active ? 'Exit Judge Mode' : 'Judge Mode' }}</span>
  </button>
</template>

<style scoped>
.judge-toggle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  width: 100%;
  padding: 0.5rem 0.3rem;
  color: var(--nav-text);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font: 650 0.58rem var(--font-display);
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-out),
    background-color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}
.judge-toggle:hover {
  color: var(--nav-text-strong);
  background: var(--nav-hover);
}
.judge-toggle--active {
  color: var(--nav-active-text);
  background: var(--nav-active);
  border-color: var(--nav-active-border);
}
</style>

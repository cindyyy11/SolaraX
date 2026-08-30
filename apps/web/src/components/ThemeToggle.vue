<script setup lang="ts">
/**
 * Light / dark switch.
 *
 * WHY THIS EXISTS. The dark theme was already fully built — every token has a
 * dark value, the cohort chart re-reads its colours on change, the fleet map
 * swaps its basemap — but nothing in the product could reach it. A complete
 * second theme that no user can turn on is not a feature, it is dead code.
 *
 * THREE STATES, NOT TWO. `theme.css` resolves theme in a specific order: an
 * explicit `data-theme` stamp wins, and only when there is none does the OS
 * preference decide. This preserves that. Before anyone chooses, the product
 * follows the system; choosing pins it and persists; and `system` remains
 * reachable so a choice is never a one-way door.
 *
 * The pre-paint stamp lives in index.html, not here — by the time Vue mounts
 * the first paint has already happened, so applying the stored theme from a
 * component would show a flash of the wrong one on every load.
 */
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { Sun, Moon, Monitor } from '@lucide/vue'

type Choice = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'solarax:theme'

/** Explicit successor map — indexing an array here is only provably safe to
 *  the reader, not to the compiler, and a lookup states the cycle plainly. */
const NEXT: Record<Choice, Choice> = { system: 'light', light: 'dark', dark: 'system' }

const LABEL: Record<Choice, string> = {
  system: 'Theme: following system',
  light: 'Theme: light',
  dark: 'Theme: dark',
}

const ICON = { system: Monitor, light: Sun, dark: Moon } as const

const choice = ref<Choice>('system')
/** What the system is asking for, so the `system` state can show a real icon. */
const systemDark = ref(false)

function read(): Choice {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    // Private mode or blocked storage. Following the system is a fine default.
  }
  return 'system'
}

function apply(next: Choice): void {
  choice.value = next
  const root = document.documentElement
  if (next === 'system') {
    root.removeAttribute('data-theme')
  } else {
    root.setAttribute('data-theme', next)
  }
  try {
    if (next === 'system') localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, next)
  } catch {
    // The theme still applies for this session; only persistence is lost.
  }
}

function cycle(): void {
  apply(NEXT[choice.value])
}

/** The icon reflects what is actually on screen, not the abstract choice. */
const effective = computed<'light' | 'dark'>(() =>
  choice.value === 'system' ? (systemDark.value ? 'dark' : 'light') : choice.value,
)

const icon = computed(() => (choice.value === 'system' ? ICON.system : ICON[effective.value]))

let query: MediaQueryList | null = null
function onSystemChange(event: MediaQueryListEvent): void {
  systemDark.value = event.matches
}

onMounted(() => {
  choice.value = read()
  query = window.matchMedia('(prefers-color-scheme: dark)')
  systemDark.value = query.matches
  query.addEventListener('change', onSystemChange)
})

onBeforeUnmount(() => query?.removeEventListener('change', onSystemChange))
</script>

<template>
  <button
    type="button"
    class="theme"
    :title="LABEL[choice]"
    :aria-label="`${LABEL[choice]}. Activate to change.`"
    @click="cycle"
  >
    <component :is="icon" :size="16" aria-hidden="true" />
  </button>
</template>

<style scoped>
/*
 * Sits on the navy nav surface, so its colours come from that surface rather
 * than from the page theme — the same reasoning as the brand mark beside it.
 */
.theme {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  /* 40px square: comfortably past the 44px-with-padding touch guidance once
     the nav's own vertical padding is counted, and square so the icon never
     shifts as it changes. */
  width: 2.5rem;
  height: 2.5rem;
  padding: 0;
  background: transparent;
  color: rgba(242, 244, 248, 0.72);
  border: 1px solid rgba(242, 244, 248, 0.18);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out),
    background-color var(--duration-fast) var(--ease-out);
}

.theme:hover {
  color: #f2f4f8;
  border-color: rgba(242, 244, 248, 0.4);
  background: rgba(242, 244, 248, 0.06);
}

.theme:active {
  transform: scale(0.94);
}

.theme:focus-visible {
  outline: 2px solid var(--brand-solar);
  outline-offset: 2px;
}
</style>

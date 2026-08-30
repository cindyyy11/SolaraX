<script setup lang="ts">
/**
 * The SolaraX lockup: dial mark plus wordmark.
 *
 * The mark is inlined rather than loaded from /brand/logo.svg so its structural
 * stroke can follow `--brand-ink`, which inverts to near-white in dark mode. An
 * <img> cannot do that, and a navy dial on a near-black plate disappears.
 *
 * The sun keeps `--brand-solar` in both themes — it is the one fixed colour in
 * the identity, and the only warm element on the page.
 *
 * The wordmark is live text, not a path, so it stays selectable and legible to
 * a screen reader. The canonical vector files in public/brand/ carry the same
 * wordmark as outlines for anywhere a font cannot be relied on.
 */
withDefaults(
  defineProps<{
    /** Mark height in px. The wordmark scales from it. */
    size?: number
    /** Hide the wordmark — for tight spots such as a collapsed nav. */
    markOnly?: boolean
  }>(),
  { size: 30, markOnly: false },
)
</script>

<template>
  <span class="brand" :style="{ '--mark-size': `${size}px` }">
    <svg
      class="brand__mark"
      viewBox="0 0 128 128"
      role="img"
      aria-label="SolaraX"
      focusable="false"
    >
      <g fill="none" stroke="var(--brand-ink)" stroke-linecap="butt">
        <g stroke-width="10">
          <path d="M 96.87 106.84 A 54 54 0 0 1 31.13 106.84" />
          <path d="M 21.16 96.87 A 54 54 0 0 1 21.16 31.13" />
          <path d="M 31.13 21.16 A 54 54 0 0 1 96.87 21.16" />
          <path d="M 106.84 31.13 A 54 54 0 0 1 106.84 96.87" />
        </g>
        <g stroke-width="6">
          <path d="M 100.59 69.47 A 37 37 0 0 1 69.47 100.59" />
          <path d="M 58.53 100.59 A 37 37 0 0 1 27.41 69.47" />
          <path d="M 27.41 58.53 A 37 37 0 0 1 58.53 27.41" />
          <path d="M 69.47 27.41 A 37 37 0 0 1 100.59 58.53" />
        </g>
      </g>
      <circle cx="118" cy="64" r="6.5" fill="var(--brand-ink)" />
      <circle cx="109.79" cy="92.62" r="6" fill="var(--brand-ink)" />
      <path
        d="M 77.44 50.56 L 94.41 33.59"
        fill="none"
        stroke="var(--brand-solar)"
        stroke-width="7"
        stroke-linecap="round"
      />
      <path
        d="M 64 37 L 69.93 49.68 L 83.09 44.91 L 78.32 58.07 L 91 64 L 78.32 69.93
           L 83.09 83.09 L 69.93 78.32 L 64 91 L 58.07 78.32 L 44.91 83.09
           L 49.68 69.93 L 37 64 L 49.68 58.07 L 44.91 44.91 L 58.07 49.68 Z
           M 55.5 64 a 8.5 8.5 0 1 0 17 0 a 8.5 8.5 0 1 0 -17 0 Z"
        fill="var(--brand-solar)"
        fill-rule="evenodd"
      />
      <circle cx="95.82" cy="32.18" r="8" fill="var(--brand-solar)" />
    </svg>

    <span v-if="!markOnly" class="brand__word">SolaraX</span>
  </span>
</template>

<style scoped>
.brand {
  display: inline-flex;
  align-items: center;
  gap: calc(var(--mark-size) * 0.28);
  line-height: 1;
}

.brand__mark {
  width: var(--mark-size);
  height: var(--mark-size);
  flex: none;
  display: block;
}

.brand__word {
  font-size: calc(var(--mark-size) * 0.72);
  font-weight: 600;
  letter-spacing: -0.017em;
  color: var(--brand-ink);
  white-space: nowrap;
}
</style>

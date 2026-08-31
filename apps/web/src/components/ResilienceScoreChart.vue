<script setup lang="ts">
/**
 * The headline visual on the Resilience screen — six categories' exposure in
 * one glance instead of six paragraphs. Horizontal bar: each category is a
 * distinct named entity (not a trend), score is a magnitude — the form the
 * dataviz skill calls for on "magnitude across named categories."
 *
 * `not-connected` categories never draw a proportional bar — see
 * ScoreGauge.vue's identical rule. They render as a short textured stub with
 * a "not connected" label, never a bare 0 that would misread as "measured
 * fine."
 */
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ResilienceSignal } from '@/types/operations'

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{ signals: ResilienceSignal[] }>()

const container = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

/** Fixed stub length for a not-connected category — never proportional to a
 * real number, just enough to render a visible, obviously-different mark. */
const NOT_CONNECTED_STUB = 6

function tokens() {
  const style = getComputedStyle(document.documentElement)
  const read = (name: string, fallback: string) => style.getPropertyValue(name).trim() || fallback
  return {
    good: read('--status-good', '#0ca30c'),
    warning: read('--status-warning', '#fab219'),
    critical: read('--status-critical', '#d03b3b'),
    neutral: read('--text-muted', '#898781'),
    textPrimary: read('--text-primary', '#0b0b0b'),
    textMuted: read('--text-muted', '#898781'),
    grid: read('--gridline', '#e1e0d9'),
    surface: read('--surface-1', '#fcfcfb'),
  }
}

const TONE_KEY: Record<ResilienceSignal['status'], 'good' | 'warning' | 'critical' | 'neutral'> = {
  nominal: 'good',
  watch: 'warning',
  exposed: 'critical',
  'not-connected': 'neutral',
}

function buildOption(): echarts.EChartsCoreOption {
  const t = tokens()
  // Chart reads top-to-bottom in visual order, so reverse for ECharts'
  // bottom-up category axis.
  const rows = [...props.signals].reverse()

  return {
    backgroundColor: 'transparent',
    animationDuration: 300,
    grid: { left: 108, right: 46, top: 8, bottom: 8, containLabel: false },
    tooltip: {
      trigger: 'item',
      backgroundColor: t.surface,
      borderColor: t.grid,
      textStyle: { color: t.textPrimary, fontSize: 12 },
      formatter: (params: unknown) => {
        const p = params as { dataIndex: number }
        const row = rows[p.dataIndex]
        if (!row) return ''
        const value = row.basis === 'not-connected' ? 'Not connected' : `${Math.round(row.score * 100)}%`
        return `<strong>${row.label}</strong><br/>${value}<br/><span style="opacity:.7">${row.headline}</span>`
      },
    },
    xAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: t.grid, width: 1 } },
      axisLabel: { color: t.textMuted, fontSize: 10, formatter: '{value}%' },
    },
    yAxis: {
      type: 'category',
      data: rows.map((row) => row.label),
      axisLine: { lineStyle: { color: t.grid } },
      axisTick: { show: false },
      axisLabel: { color: t.textPrimary, fontSize: 12, fontWeight: 600 },
    },
    series: [
      {
        type: 'bar',
        barWidth: 16,
        data: rows.map((row) => ({
          value: row.basis === 'not-connected' ? NOT_CONNECTED_STUB : Math.round(row.score * 100),
          itemStyle: {
            color: t[TONE_KEY[row.status]],
            borderRadius: 4,
            decal:
              row.basis === 'not-connected'
                ? { symbol: 'rect', symbolSize: 0.8, rotation: Math.PI / 4, dashArrayX: [1, 0], dashArrayY: [2, 4], color: t.surface }
                : undefined,
          },
          label:
            row.basis === 'not-connected'
              ? { show: true, position: 'right', formatter: 'not connected', color: t.textMuted, fontSize: 10, fontWeight: 700 }
              : { show: true, position: 'right', formatter: `${Math.round(row.score * 100)}%`, color: t.textPrimary, fontSize: 11, fontWeight: 700 },
        })),
      },
    ],
  }
}

function render(): void {
  if (!container.value) return
  if (!chart) chart = echarts.init(container.value, undefined, { renderer: 'canvas' })
  chart.setOption(buildOption(), true)
}

function handleResize(): void {
  chart?.resize()
}

let themeObserver: MutationObserver | null = null

onMounted(() => {
  render()
  window.addEventListener('resize', handleResize)
  themeObserver = new MutationObserver(render)
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  themeObserver?.disconnect()
  chart?.dispose()
  chart = null
})

watch(() => props.signals, render, { deep: false })
</script>

<template>
  <figure class="score-chart">
    <figcaption class="score-chart__caption">
      Six categories at a glance. A textured bar means no live source is connected — never a measured
      zero.
    </figcaption>
    <div ref="container" class="score-chart__canvas" role="img" aria-label="Resilience exposure by category, six bars"></div>
    <ul class="score-chart__legend">
      <li><span class="dot dot--good"></span>Nominal</li>
      <li><span class="dot dot--warning"></span>Watch</li>
      <li><span class="dot dot--critical"></span>Exposed</li>
      <li><span class="dot dot--neutral dot--dashed"></span>Not connected</li>
    </ul>
  </figure>
</template>

<style scoped>
.score-chart {
  margin: 0;
}
.score-chart__caption {
  margin: 0 0 0.6rem;
  color: var(--text-secondary);
  font-size: 0.78rem;
  line-height: 1.5;
}
.score-chart__canvas {
  width: 100%;
  height: 220px;
}
.score-chart__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 1rem;
  margin: 0.6rem 0 0;
  padding: 0.6rem 0 0;
  border-top: 1px solid var(--border-hairline);
  list-style: none;
  color: var(--text-secondary);
  font-size: 0.7rem;
}
.score-chart__legend li {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: none;
}
.dot--good {
  background: var(--status-good);
}
.dot--warning {
  background: var(--status-warning);
}
.dot--critical {
  background: var(--status-critical);
}
.dot--neutral {
  background: var(--text-muted);
}
.dot--dashed {
  background: transparent;
  border: 1.5px dashed var(--baseline);
}
@media (max-width: 560px) {
  .score-chart__canvas {
    height: 260px;
  }
}
</style>

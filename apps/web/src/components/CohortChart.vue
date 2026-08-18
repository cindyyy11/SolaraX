<script setup lang="ts">
/**
 * The cohort overlay — PRD v2 section 4 calls it "the visual that sells the whole
 * product": several lines tracking together and one diverging.
 *
 * Design decisions worth keeping:
 *  - Peers are deliberately UNDIFFERENTIATED. They are a control band, not eight
 *    identities, so they share one muted grey and the legend carries two entries
 *    (this site / cohort peers) rather than one per peer. Colouring eight peers
 *    would imply their individual identity matters here. It doesn't.
 *  - The subject uses a categorical accent, NOT a status colour. Status colours
 *    are reserved for triage state; the divergence is carried by the reference
 *    line and the shaded region instead.
 *  - y-axis is performance_index in kWh per kWp, so a 40 kWp and a 277 kWp site
 *    sit on one axis honestly.
 *  - Crosshair + tooltip ship by default. A line chart without a hover layer
 *    throws away the reader's main way of interrogating it.
 */
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  MarkAreaComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { cohortLines } from '@/services/api'
import type { CohortSeriesRow, Divergence, Economics } from '@/types/dispatch'

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  MarkAreaComponent,
  CanvasRenderer,
])

const props = defineProps<{
  rows: CohortSeriesRow[]
  subjectName: string
  divergence?: Divergence | null
  economics?: Economics | null
}>()

const container = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

const lines = computed(() => cohortLines(props.rows))
const peerCount = computed(() => lines.value.filter((line) => !line.isSubject).length)

/** Read design tokens at runtime so the chart follows the theme rather than hardcoding it. */
function tokens() {
  const style = getComputedStyle(document.documentElement)
  const read = (name: string, fallback: string) =>
    style.getPropertyValue(name).trim() || fallback
  return {
    subject: read('--series-1', '#2a78d6'),
    peer: read('--text-muted', '#898781'),
    textPrimary: read('--text-primary', '#0b0b0b'),
    textSecondary: read('--text-secondary', '#52514e'),
    textMuted: read('--text-muted', '#898781'),
    grid: read('--gridline', '#e1e0d9'),
    axis: read('--baseline', '#c3c2b7'),
    surface: read('--surface-1', '#fcfcfb'),
    critical: read('--status-critical', '#d03b3b'),
  }
}

function buildOption(): echarts.EChartsCoreOption {
  const t = tokens()
  const dates = lines.value[0]?.points.map((point) => point.date) ?? []

  const series: Record<string, unknown>[] = lines.value.map((line) => ({
    name: line.isSubject ? props.subjectName : `peer ${line.siteId}`,
    type: 'line',
    // Peers collapse into one legend entry; only the subject is named.
    legendHoverLink: line.isSubject,
    showSymbol: false,
    symbolSize: 8,
    // Subject sits on top of its peers.
    z: line.isSubject ? 10 : 1,
    lineStyle: {
      width: line.isSubject ? 2.5 : 1,
      color: line.isSubject ? t.subject : t.peer,
      opacity: line.isSubject ? 1 : 0.45,
    },
    itemStyle: { color: line.isSubject ? t.subject : t.peer },
    emphasis: { focus: 'series', lineStyle: { width: line.isSubject ? 3 : 2 } },
    data: line.points.map((point) => point.value),
  }))

  // Reference line and shaded loss region, drawn on the subject series.
  const subjectIndex = series.findIndex((_, index) => lines.value[index]?.isSubject)
  const subjectSeries = subjectIndex >= 0 ? series[subjectIndex] : undefined
  if (subjectSeries && props.divergence?.start_date) {
    const start = props.divergence.start_date
    const lossLabel = props.economics
      ? `RM ${Math.round(props.economics.cumulative_loss_rm).toLocaleString('en-MY')} lost since`
      : 'divergence'

    subjectSeries.markLine = {
      symbol: 'none',
      silent: true,
      label: {
        formatter: `diverging since ${start}`,
        color: t.textSecondary,
        fontSize: 11,
        position: 'insideEndTop',
      },
      lineStyle: { color: t.critical, type: 'dashed', width: 1.5 },
      data: [{ xAxis: start }],
    }

    subjectSeries.markArea = {
      silent: true,
      itemStyle: { color: t.critical, opacity: 0.06 },
      label: {
        show: true,
        formatter: lossLabel,
        position: 'insideTop',
        color: t.textMuted,
        fontSize: 11,
      },
      data: [[{ xAxis: start }, { xAxis: dates[dates.length - 1] }]],
    }
  }

  return {
    backgroundColor: 'transparent',
    animationDuration: 300,
    grid: { left: 52, right: 20, top: 44, bottom: 36, containLabel: false },
    legend: {
      show: true,
      top: 0,
      left: 0,
      itemWidth: 18,
      itemHeight: 2,
      textStyle: { color: t.textSecondary, fontSize: 11 },
      // Only two entries: the subject, and one representative peer standing for all.
      data: [
        { name: props.subjectName },
        { name: `peer ${lines.value.find((line) => !line.isSubject)?.siteId ?? ''}` },
      ],
      formatter: (name: string) =>
        name.startsWith('peer ') ? `cohort peers (${peerCount.value})` : name,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: t.axis, width: 1 } },
      backgroundColor: t.surface,
      borderColor: t.grid,
      textStyle: { color: t.textPrimary, fontSize: 12 },
      formatter: (params: unknown) => {
        const points = params as Array<{ name: string; value: number; seriesName: string; color: string }>
        const first = points[0]
        if (!first) return ''
        const date = first.name
        // Subject first, then peers, so the eye lands on the site in question.
        const ordered = [...points].sort((a, b) =>
          Number(b.seriesName === props.subjectName) - Number(a.seriesName === props.subjectName),
        )
        const rows = ordered
          .map((point) => {
            const isSubject = point.seriesName === props.subjectName
            const label = isSubject ? point.seriesName : point.seriesName.replace('peer ', '')
            const weight = isSubject ? 700 : 400
            return `<div style="display:flex;gap:8px;justify-content:space-between;font-weight:${weight}">
                      <span style="opacity:${isSubject ? 1 : 0.7}">${label}</span>
                      <span style="font-variant-numeric:tabular-nums">${Number(point.value).toFixed(2)}</span>
                    </div>`
          })
          .join('')
        return `<div style="font-size:11px;opacity:0.7;margin-bottom:4px">${date}</div>${rows}
                <div style="font-size:10px;opacity:0.6;margin-top:4px">kWh per kWp</div>`
      },
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: t.axis } },
      axisTick: { show: false },
      axisLabel: { color: t.textMuted, fontSize: 10, hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      name: 'kWh / kWp',
      nameTextStyle: { color: t.textMuted, fontSize: 10, align: 'left' },
      nameGap: 14,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: t.grid, width: 1 } },
      axisLabel: { color: t.textMuted, fontSize: 10 },
    },
    series,
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
  // Re-read tokens when the theme changes; ECharts bakes colors at set time.
  themeObserver = new MutationObserver(render)
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  themeObserver?.disconnect()
  chart?.dispose()
  chart = null
})

watch(() => props.rows, render, { deep: false })
</script>

<template>
  <figure class="cohort">
    <figcaption class="cohort__caption">
      Daily specific yield against cohort peers — normalised to kWh per kWp so sites of any
      size compare honestly.
    </figcaption>
    <div ref="container" class="cohort__canvas"></div>
    <p class="cohort__note">
      A cohort-wide dip is weather. A single site dipping inside a stable cohort is a fault.
    </p>
  </figure>
</template>

<style scoped>
.cohort {
  margin: 0;
  padding: 1rem 1rem 0.75rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}

.cohort__caption {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
  line-height: 1.5;
}

.cohort__canvas {
  width: 100%;
  height: 380px;
}

@media (max-width: 720px) {
  .cohort__canvas {
    height: 300px;
  }
}

.cohort__note {
  margin: 0.5rem 0 0;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-hairline);
  font-size: 0.75rem;
  color: var(--text-muted);
}
</style>

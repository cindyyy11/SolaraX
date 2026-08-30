<script setup lang="ts">
/**
 * Screen 3 — Work Order. What you hand a technician.
 *
 * Two things here go beyond the PRD text, both deliberate (BUILD_PLAN stage 13):
 *
 * 1. VERIFICATION METHOD IS CONDITIONAL ON THE HYPOTHESIS. An electrical
 *    hypothesis (inverter, string, breaker) sends someone to the combiner box —
 *    no drone. A module-level one (soiling, hot spot, cracked glass, debris)
 *    recommends a thermal pass BEFORE roof entry, because a 15-minute flight
 *    avoids work-at-height permits, harnesses and a safety briefing (PRD v2 M5).
 *    Never imply every dispatch needs a drone; that is the v1 product we killed.
 *
 * 2. A FINDINGS SECTION. This closes DETECT -> VERIFY -> CONFIRM -> LEARN and is
 *    what populates Screen 4's confirmed-fault and recovered-generation figures.
 *    Without it the loop is open and the ROI screen has nothing real to count.
 *
 * Findings persist to localStorage only — there is no backend yet. That is
 * stated on screen rather than implied, so nobody assumes it syncs.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowLeft,
  ArrowRight,
  Zap,
  Thermometer,
  Printer,
  Clock3,
  ListChecks,
  Save,
} from '@lucide/vue'
import { loadDispatch, findSite, findCohort, formatRinggit, formatCapacity } from '@/services/api'
import type { Dispatch, Site } from '@/types/dispatch'
import DataStatusBadge from '@/components/DataStatusBadge.vue'
import NoticeCallout from '@/components/NoticeCallout.vue'

const route = useRoute()
const dispatch = ref<Dispatch | null>(null)
const isLoading = ref(true)

const site = computed<Site | undefined>(() =>
  dispatch.value ? findSite(dispatch.value, String(route.params.siteId)) : undefined,
)
const cohort = computed(() =>
  dispatch.value && site.value ? findCohort(dispatch.value, site.value.cohort_id) : undefined,
)

/** Where this site sits against the others — the "why this one" line. */
const selectionRationale = computed(() => {
  if (!dispatch.value || !site.value || !site.value.economics) return ''
  const flagged = dispatch.value.sites.filter((item) => item.economics)
  const ranked = [...flagged].sort(
    (a, b) => (b.economics?.rm_at_risk_monthly ?? 0) - (a.economics?.rm_at_risk_monthly ?? 0),
  )
  const position = ranked.findIndex((item) => item.site_id === site.value!.site_id) + 1
  const total = dispatch.value.fleet_summary.site_count
  const notVisited = dispatch.value.fleet_summary.visits_avoided
  return (
    `This site ranks ${position} of ${ranked.length} flagged sites by money at risk, out of ` +
    `${total} in the fleet. ${notVisited} sites are not being visited this month because their ` +
    `output stayed within cohort tolerance.`
  )
})

// --- Verification method, derived from the hypothesis ------------------------

const ELECTRICAL_TERMS = [
  'inverter',
  'string',
  'breaker',
  'combiner',
  'fuse',
  'wiring',
  'connector',
  'isolator',
]
const MODULE_TERMS = [
  'soiling',
  'hotspot',
  'hot spot',
  'crack',
  'debris',
  'shading',
  'glass',
  'module',
  'panel',
]

function countMatches(haystack: string, terms: string[]): number {
  const lower = haystack.toLowerCase()
  return terms.filter((term) => lower.includes(term)).length
}

const verification = computed(() => {
  const hypothesis = site.value?.hypothesis
  if (!hypothesis) return null

  const corpus = [hypothesis.summary, hypothesis.detail, ...hypothesis.checks].join(' ')
  const electrical = countMatches(corpus, ELECTRICAL_TERMS)
  const moduleLevel = countMatches(corpus, MODULE_TERMS)

  if (moduleLevel > electrical) {
    return {
      kind: 'module' as const,
      method: 'Thermal pass before roof entry',
      rationale:
        'The hypothesis is module-level. A thermal overflight confirms or rules it out in ' +
        'about fifteen minutes without work-at-height permits, harnesses or a safety briefing. ' +
        'Only send someone onto the roof if the pass finds something.',
      steps: [
        'Fly a thermal pass over the full array before any roof access',
        'Compare the thermal frames against the flagged inverter group',
        'Enter the roof only if the pass identifies a target',
      ],
    }
  }

  return {
    kind: 'electrical' as const,
    method: 'Combiner box and inverter display — no drone required',
    rationale:
      'The hypothesis is electrical. This is confirmed at the combiner box and the inverter ' +
      'display, not from the air. A thermal flight would add cost without adding evidence.',
    steps: [
      'Read the inverter display for per-string currents and any error codes',
      'Open the combiner box and check breaker and fuse states',
      'Compare measured string currents against the healthy sibling units',
    ],
  }
})

// --- Findings (the data flywheel) -------------------------------------------

type Outcome = '' | 'fault_confirmed' | 'nothing_found' | 'different_cause'

const findingsOutcome = ref<Outcome>('')
const findingsNote = ref('')
const findingsRecoveredKwh = ref('')
const savedAt = ref<string | null>(null)
/** Ticked checklist items, by their text. A technician works down this list. */
const ticked = ref<Record<string, boolean>>({})

const storageKey = computed(() => `solarax:findings:${route.params.siteId}`)

function loadFindings(): void {
  ticked.value = {}
  findingsOutcome.value = ''
  findingsNote.value = ''
  findingsRecoveredKwh.value = ''
  savedAt.value = null

  const raw = localStorage.getItem(storageKey.value)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw)
    findingsOutcome.value = parsed.outcome ?? ''
    findingsNote.value = parsed.note ?? ''
    findingsRecoveredKwh.value = parsed.recovered_kwh ?? ''
    savedAt.value = parsed.saved_at ?? null
    ticked.value = parsed.ticked ?? {}
  } catch {
    // A corrupt entry is not worth blocking the screen over.
  }
}

function saveFindings(): void {
  savedAt.value = new Date().toISOString()
  localStorage.setItem(
    storageKey.value,
    JSON.stringify({
      outcome: findingsOutcome.value,
      note: findingsNote.value,
      recovered_kwh: findingsRecoveredKwh.value,
      ticked: ticked.value,
      saved_at: savedAt.value,
    }),
  )
}

/** Ticks persist immediately — a technician should not have to remember to save. */
watch(ticked, saveFindings, { deep: true })

const checklistProgress = computed(() => {
  const all = [
    ...(site.value?.hypothesis?.checks ?? []),
    ...(site.value?.hypothesis?.photograph ?? []),
  ]
  const done = all.filter((item) => ticked.value[item]).length
  return { done, total: all.length }
})

// --- Rank context ------------------------------------------------------------

/** All flagged sites, ranked by money at risk — the bar chart on this card. */
const rankedFlagged = computed(() => {
  if (!dispatch.value) return []
  return dispatch.value.sites
    .filter((item) => item.economics)
    .map((item) => ({
      siteId: item.site_id,
      name: item.name,
      rm: item.economics!.rm_at_risk_monthly,
      status: item.status,
      isSubject: item.site_id === site.value?.site_id,
    }))
    .sort((a, b) => b.rm - a.rm)
})

const maxFlaggedRm = computed(() => Math.max(1, ...rankedFlagged.value.map((item) => item.rm)))

/** 90-day performance trace for the header sparkline. */
const sparkPath = computed(() => {
  const rows = site.value?.series?.actual_vs_expected ?? []
  if (rows.length < 2) return ''
  const values = rows.map((row) => row.performance_index)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 100
      const y = 28 - ((value - min) / range) * 26
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
})

/** Where the divergence line falls along the sparkline, as a percentage. */
const divergenceMarkerPercent = computed(() => {
  const rows = site.value?.series?.actual_vs_expected ?? []
  const start = site.value?.divergence?.start_date
  if (!rows.length || !start) return null
  const index = rows.findIndex((row) => row.date >= start)
  if (index < 0) return null
  return (index / (rows.length - 1)) * 100
})

onMounted(async () => {
  const result = await loadDispatch()
  dispatch.value = result.dispatch
  isLoading.value = false
  loadFindings()
})

watch(() => route.params.siteId, loadFindings)

function printCard(): void {
  window.print()
}
</script>

<template>
  <main class="screen">
    <p v-if="isLoading">Loading…</p>
    <p v-else-if="!site">No site with id {{ route.params.siteId }}.</p>

    <template v-else>
      <nav class="crumbs no-print">
        <RouterLink to="/" class="crumbs__link">
          <ArrowLeft :size="14" aria-hidden="true" /> Dispatch list
        </RouterLink>
        <RouterLink :to="`/site/${site.site_id}`" class="crumbs__link">Site detail</RouterLink>
        <button type="button" class="print-button" @click="printCard">
          <Printer :size="15" aria-hidden="true" /> Print / export
        </button>
      </nav>

      <article class="card">
        <header class="card__head">
          <div>
            <h1 class="card__title">Work order — {{ site.name }}</h1>
            <p class="card__address">
              {{ site.address }} · {{ dispatch?.meta.reporting_month_label }}
            </p>
          </div>
          <div class="card__meta">
            <DataStatusBadge :status="site.data_status" />
            <p class="card__ref">{{ site.site_id }} · {{ site.source_system_id }}</p>
          </div>
        </header>

        <!-- Why this site, in plain language, before any technical detail. -->
        <NoticeCallout tone="info" class="rationale">{{ selectionRationale }}</NoticeCallout>

        <!-- Rank context: where this site sits against the others competing for
             the same technician. A number without its peers is not an argument. -->
        <section v-if="rankedFlagged.length > 1" class="rank">
          <h2 class="section__title">Why this one — all flagged sites by money at risk</h2>
          <ul class="rank__list">
            <li
              v-for="(item, index) in rankedFlagged"
              :key="item.siteId"
              class="rank__row"
              :class="{ 'rank__row--subject': item.isSubject }"
            >
              <span class="rank__position">{{ index + 1 }}</span>
              <span class="rank__name">{{ item.name }}</span>
              <span class="rank__bar">
                <span
                  class="rank__fill"
                  :class="item.isSubject ? 'rank__fill--subject' : `rank__fill--${item.status}`"
                  :style="{ width: (item.rm / maxFlaggedRm) * 100 + '%' }"
                ></span>
              </span>
              <span class="rank__value">{{ formatRinggit(item.rm) }}</span>
            </li>
          </ul>
        </section>

        <!-- 90-day trace with the divergence point marked. -->
        <section v-if="sparkPath" class="trace">
          <h2 class="section__title">Specific yield, last 90 days (kWh/kWp/day)</h2>
          <div class="trace__wrap">
            <svg class="trace__svg" viewBox="0 0 100 30" preserveAspectRatio="none">
              <path :d="sparkPath" fill="none" stroke="currentColor" stroke-width="0.8" />
            </svg>
            <span
              v-if="divergenceMarkerPercent !== null"
              class="trace__marker"
              :style="{ left: divergenceMarkerPercent + '%' }"
              :title="`Divergence began ${site.divergence?.start_date}`"
            ></span>
          </div>
          <p v-if="site.divergence" class="trace__caption">
            Dashed marker: divergence began {{ site.divergence.start_date }}
          </p>
        </section>

        <section class="facts">
          <div>
            <span class="facts__key">Capacity</span
            ><span>{{ formatCapacity(site.capacity_kwp) }}</span>
          </div>
          <div>
            <span class="facts__key">Cohort</span><span>{{ cohort?.label ?? 'Ungrouped' }}</span>
          </div>
          <div v-if="site.economics">
            <span class="facts__key">At risk</span>
            <span class="facts__strong"
              >{{ formatRinggit(site.economics.rm_at_risk_monthly) }}/month</span
            >
          </div>
          <div v-if="site.divergence">
            <span class="facts__key">Diverging since</span>
            <span>{{ site.divergence.start_date }} ({{ site.divergence.days_since }} days)</span>
          </div>
        </section>

        <section v-if="site.hypothesis" class="section">
          <h2 class="section__title">What we think is wrong</h2>
          <p class="section__lead">{{ site.hypothesis.summary }}</p>
          <p class="section__body">{{ site.hypothesis.detail }}</p>
          <p class="section__meta">
            Confidence {{ Math.round(site.hypothesis.confidence * 100) }}% · method:
            {{ site.detection?.method }}
          </p>
        </section>

        <!-- Conditional on the hypothesis. Not every dispatch needs a drone. -->
        <section v-if="verification" class="section section--method">
          <h2 class="section__title">How to verify it</h2>

          <!-- The decision drawn, so the branch not taken is visible too. -->
          <div class="route">
            <div class="route__node route__node--start">
              Hypothesis<br /><strong>{{ verification.kind }}</strong>
            </div>
            <ArrowRight class="route__arrow" :size="18" aria-hidden="true" />
            <div
              class="route__node"
              :class="
                verification.kind === 'electrical' ? 'route__node--active' : 'route__node--dim'
              "
            >
              <Zap class="route__icon" :size="18" aria-hidden="true" />
              Combiner box<br />&amp; inverter display
              <span class="route__tag">no drone</span>
            </div>
            <div
              class="route__node"
              :class="verification.kind === 'module' ? 'route__node--active' : 'route__node--dim'"
            >
              <Thermometer class="route__icon" :size="18" aria-hidden="true" />
              Thermal pass<br />before roof entry
              <span class="route__tag">avoids permits</span>
            </div>
          </div>

          <p class="section__lead">{{ verification.method }}</p>
          <p class="section__body">{{ verification.rationale }}</p>
          <ol class="steps">
            <li v-for="step in verification.steps" :key="step">{{ step }}</li>
          </ol>
        </section>

        <section v-if="site.hypothesis?.checks?.length" class="section">
          <h2 class="section__title">
            What to check on site
            <span class="section__progress"
              >{{ checklistProgress.done }} / {{ checklistProgress.total }} done</span
            >
          </h2>
          <ul class="checklist">
            <li v-for="check in site.hypothesis.checks" :key="check">
              <label class="checklist__item">
                <input v-model="ticked[check]" type="checkbox" />
                <span :class="{ checklist__done: ticked[check] }">{{ check }}</span>
              </label>
            </li>
          </ul>
        </section>

        <section v-if="site.hypothesis?.photograph?.length" class="section">
          <h2 class="section__title">What to photograph</h2>
          <ul class="checklist">
            <li v-for="item in site.hypothesis.photograph" :key="item">
              <label class="checklist__item">
                <input v-model="ticked[item]" type="checkbox" />
                <span :class="{ checklist__done: ticked[item] }">{{ item }}</span>
              </label>
            </li>
          </ul>
        </section>

        <!-- Units drawn rather than listed: worst-first is the inspection order. -->
        <section v-if="site.sub_site" class="section">
          <h2 class="section__title">Units to inspect first</h2>
          <p class="section__meta">{{ site.sub_site.method }}</p>
          <NoticeCallout
            v-if="site.sub_site.comparability_note"
            class="comparability"
            compact
            :tone="site.sub_site.units_comparable ? 'good' : 'warning'"
          >
            {{ site.sub_site.comparability_note }}
          </NoticeCallout>
          <ul class="units">
            <li v-for="unit in site.sub_site.units" :key="unit.unit_id" class="units__row">
              <span class="units__id">{{ unit.unit_id }}</span>
              <span class="units__bar">
                <span class="units__axis"></span>
                <span
                  class="units__fill"
                  :class="[
                    unit.status === 'flagged' ? 'units__fill--flagged' : 'units__fill--normal',
                    unit.deviation_pct < 0 ? 'units__fill--neg' : 'units__fill--pos',
                  ]"
                  :style="{ width: Math.min(50, Math.abs(unit.deviation_pct) * 50) + '%' }"
                ></span>
              </span>
              <span class="units__value">{{ (unit.deviation_pct * 100).toFixed(1) }}%</span>
              <span class="units__temp">
                <template v-if="unit.thermal">{{ unit.thermal.mean_temp_c.toFixed(1) }}°C</template>
                <template v-else>—</template>
              </span>
              <span v-if="unit.status === 'flagged'" class="units__flag">flagged</span>
              <span v-else class="units__ok">ok</span>
            </li>
          </ul>
        </section>

        <!-- The data flywheel. Screen 4 counts what gets recorded here. -->
        <section class="section section--findings">
          <h2 class="section__title">Findings — complete after the visit</h2>

          <div class="field">
            <span class="field__label">Outcome</span>
            <div class="radios">
              <label
                ><input v-model="findingsOutcome" type="radio" value="fault_confirmed" /> Fault
                confirmed</label
              >
              <label
                ><input v-model="findingsOutcome" type="radio" value="nothing_found" /> Nothing
                found</label
              >
              <label
                ><input v-model="findingsOutcome" type="radio" value="different_cause" /> Different
                cause</label
              >
            </div>
          </div>

          <label class="field">
            <span class="field__label">What was actually found</span>
            <textarea
              v-model="findingsNote"
              rows="4"
              placeholder="Describe what the technician found."
            ></textarea>
          </label>

          <label class="field">
            <span class="field__label">Estimated generation recovered (kWh/month)</span>
            <input v-model="findingsRecoveredKwh" type="number" min="0" placeholder="0" />
          </label>

          <div class="field no-print">
            <button type="button" class="save-button" @click="saveFindings">Save findings</button>
            <span v-if="savedAt" class="field__saved"
              >Saved {{ new Date(savedAt).toLocaleString() }}</span
            >
          </div>

          <p class="field__note no-print">
            Findings are stored in this browser only — there is no backend yet. Confirmed outcomes
            are what Screen 4 counts, and what would retrain the detector.
          </p>
        </section>

        <section class="activity" aria-labelledby="activity-title">
          <h2 id="activity-title" class="section__title">Work-order activity</h2>
          <ol class="activity__timeline">
            <li class="activity__event activity__event--done">
              <Clock3 :size="17" aria-hidden="true" />
              <div>
                <strong>Work order generated</strong
                ><span>From pipeline {{ dispatch?.meta.pipeline_version }}</span>
              </div>
            </li>
            <li
              class="activity__event"
              :class="{ 'activity__event--done': checklistProgress.done > 0 }"
            >
              <ListChecks :size="17" aria-hidden="true" />
              <div>
                <strong>Technician checklist</strong
                ><span
                  >{{ checklistProgress.done }} of {{ checklistProgress.total }} checks
                  complete</span
                >
              </div>
            </li>
            <li class="activity__event" :class="{ 'activity__event--done': savedAt }">
              <Save :size="17" aria-hidden="true" />
              <div>
                <strong>Findings recorded</strong
                ><span>{{
                  savedAt ? `Saved ${new Date(savedAt).toLocaleString()}` : 'Awaiting site findings'
                }}</span>
              </div>
            </li>
          </ol>
        </section>

        <footer class="card__foot">
          <p>
            {{ dispatch?.meta.data_source }} · generated {{ dispatch?.meta.generated_at }} · schema
            {{ dispatch?.meta.schema_version }}
          </p>
          <p v-if="dispatch?.meta.date_remapped">{{ dispatch?.meta.date_remap_note }}</p>
        </footer>
      </article>
    </template>
  </main>
</template>

<style scoped>
.screen {
  max-width: 1100px;
  margin: 0 auto;
  padding: clamp(1.25rem, 2.8vw, 2.75rem);
}

.crumbs {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  font-size: 0.85rem;
}

.crumbs__link {
  display: inline-flex;
  align-items: center;
  gap: 0.35em;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius-sm);
}

.crumbs__link:hover {
  color: var(--action-text);
}

/* The primary action on each of the two places it appears: print the card,
   and commit the findings. Amber fill + navy ink, matching the work-order
   button on Site Detail — one action treatment across the product. */
.print-button,
.save-button {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-left: auto;
  padding: 0.5rem 0.9rem;
  background: var(--action-fill);
  color: var(--action-ink);
  border: none;
  border-radius: var(--radius-sm);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}

.print-button:hover,
.save-button:hover {
  background: var(--action-fill-hover);
}

.print-button:active,
.save-button:active {
  transform: scale(0.97);
}

.save-button {
  margin-left: 0;
}

.card {
  padding: 1.75rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
  box-shadow: var(--elevation-1);
}

.activity {
  margin-top: 1.5rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--border-hairline);
}
.activity__timeline {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  margin: 0.8rem 0 0;
  padding: 0;
  overflow: hidden;
  background: var(--border-hairline);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  list-style: none;
}
.activity__event {
  display: flex;
  min-height: 5.5rem;
  gap: 0.65rem;
  padding: 0.85rem;
  color: var(--text-muted);
  background: var(--surface-2);
}
.activity__event svg {
  flex: none;
}
.activity__event div {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.activity__event strong {
  color: var(--text-secondary);
  font-size: 0.78rem;
}
.activity__event span {
  font-size: 0.68rem;
  line-height: 1.4;
}
.activity__event--done {
  color: var(--success-text);
  background: var(--callout-good-bg);
}
.activity__event--done strong {
  color: var(--text-primary);
}
@media (max-width: 700px) {
  .activity__timeline {
    grid-template-columns: 1fr;
  }
}

.card__head {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: space-between;
  align-items: flex-start;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--text-primary);
}

.card__title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}

.card__address {
  margin: 0.3rem 0 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.card__meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.4rem;
}

.card__ref {
  margin: 0;
  font-size: 0.72rem;
  color: var(--text-muted);
}

/* Tint, border and icon come from NoticeCallout. This previously used --series-1,
   a CHART categorical colour, as a page-chrome accent — series colours are
   reserved for data marks and borrowing one here quietly broke that rule. */
.rationale {
  margin-top: 1rem;
}

.facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.6rem 1.5rem;
  margin: 1.25rem 0;
}

.facts div {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-hairline);
  font-size: 0.9rem;
}

.facts__key {
  font-size: 0.66rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.facts__strong {
  font-weight: 700;
}

.section {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-hairline);
}

.section--method {
  background: var(--page-plane);
  padding: 1rem;
  border-radius: var(--radius-sm);
  border-top: none;
}

.section__title {
  margin: 0 0 0.5rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.section__lead {
  margin: 0 0 0.4rem;
  font-size: 1rem;
  font-weight: 600;
}

.section__body {
  margin: 0 0 0.6rem;
  font-size: 0.88rem;
  line-height: 1.6;
  color: var(--text-secondary);
}

.section__meta {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.steps {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.88rem;
  line-height: 1.7;
}

.checklist {
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 0.9rem;
}

.checklist__item {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.35rem 0;
  cursor: pointer;
  line-height: 1.5;
}

.checklist__item input[type='checkbox'] {
  width: 16px;
  height: 16px;
  margin: 0.15rem 0 0;
  accent-color: var(--series-1);
  cursor: pointer;
  flex-shrink: 0;
}

.checklist__done {
  text-decoration: line-through;
  color: var(--text-muted);
}

.section__progress {
  margin-left: 0.5rem;
  font-weight: 400;
  letter-spacing: 0;
  text-transform: none;
  color: var(--text-secondary);
}

/* --- Rank context --- */

.rank {
  margin-top: 1.25rem;
}

.rank__list {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
}

.rank__row {
  display: grid;
  grid-template-columns: 1.5rem minmax(90px, 1.2fr) 2fr auto;
  gap: 0.6rem;
  align-items: center;
  padding: 0.25rem 0;
  font-size: 0.8rem;
}

.rank__row--subject {
  font-weight: 700;
}

.rank__position {
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.rank__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank__bar {
  height: 10px;
  background: var(--page-plane);
  border-radius: 2px;
  overflow: hidden;
}

.rank__fill {
  display: block;
  height: 100%;
  border-radius: 2px;
}

.rank__fill--subject {
  background: var(--series-1);
}
.rank__fill--dispatch {
  background: var(--status-critical);
  opacity: 0.45;
}
.rank__fill--monitor {
  background: var(--status-warning);
  opacity: 0.45;
}

.rank__value {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* --- Trace --- */

.trace {
  margin-top: 1.25rem;
}

.trace__wrap {
  position: relative;
  margin-top: 0.4rem;
}

.trace__svg {
  display: block;
  width: 100%;
  height: 60px;
  color: var(--series-1);
}

.trace__marker {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 0;
  border-left: 1.5px dashed var(--status-critical);
}

.trace__caption {
  margin: 0.25rem 0 0;
  font-size: 0.72rem;
  color: var(--text-muted);
}

/* --- Verification route --- */

.route {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.route__node {
  flex: 1 1 130px;
  padding: 0.6rem 0.7rem;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  font-size: 0.76rem;
  line-height: 1.4;
  background: var(--surface-1);
  position: relative;
}

.route__node--start {
  flex: 0 1 110px;
  background: transparent;
  border-style: dashed;
  text-transform: capitalize;
}

.route__node--active {
  border-color: var(--text-primary);
  border-width: 2px;
}

.route__node--dim {
  opacity: 0.4;
}

.route__arrow {
  align-self: center;
  color: var(--text-muted);
}

.route__icon {
  display: block;
  margin: 0 auto 0.3rem;
}

/* Block, not inline-block: the node's label ends in a <br />-separated line,
   so an inline tag ran on from it and read as "& inverter display NO DRONE"
   — one sentence instead of a label and its qualifier. */
.route__tag {
  display: block;
  margin-top: 0.4rem;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-muted);
}

/* --- Units --- */

.units {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
}

.units__row {
  display: grid;
  grid-template-columns: 3rem 1fr 3.5rem 3.5rem 4rem;
  gap: 0.6rem;
  align-items: center;
  padding: 0.3rem 0;
  font-size: 0.8rem;
}

.units__id {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.units__bar {
  position: relative;
  height: 12px;
}

.units__axis {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--baseline);
}

.units__fill {
  position: absolute;
  top: 2px;
  bottom: 2px;
  border-radius: 2px;
}

.units__fill--neg {
  right: 50%;
}
.units__fill--pos {
  left: 50%;
}
.units__fill--flagged {
  background: var(--status-critical);
}
.units__fill--normal {
  background: var(--text-muted);
  opacity: 0.5;
}

.units__value,
.units__temp {
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
}

.units__flag,
.units__ok {
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  text-align: right;
}

.units__flag {
  color: var(--status-critical);
}

/* A label, not a control — no button affordance. */
.units__ok {
  color: var(--text-muted);
  font-weight: 400;
  text-transform: lowercase;
  letter-spacing: 0;
}

/* Tint, border and icon come from NoticeCallout; tone is bound to whether the
   units are actually comparable. */
.comparability {
  margin: 0.5rem 0 0.75rem;
}

/* --- Findings --- */

.section--findings {
  border-top: 2px solid var(--text-primary);
}

.field {
  display: block;
  margin-bottom: 1rem;
}

.field__label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.radios {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  font-size: 0.88rem;
}

.radios label {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
}

textarea,
input[type='number'] {
  width: 100%;
  padding: 0.5rem 0.6rem;
  background: var(--page-plane);
  color: var(--text-primary);
  border: 1px solid var(--baseline);
  border-radius: var(--radius-sm);
  font: inherit;
  font-size: 0.88rem;
}

.field__saved {
  margin-left: 0.75rem;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.field__note {
  margin: 0;
  font-size: 0.74rem;
  line-height: 1.5;
  color: var(--text-muted);
}

.card__foot {
  margin-top: 1.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-hairline);
  font-size: 0.7rem;
  color: var(--text-muted);
}

.card__foot p {
  margin: 0 0 0.2rem;
}

/* Print: the card alone, on white, no chrome. */
@media print {
  .no-print {
    display: none !important;
  }
  .screen {
    padding: 0;
    max-width: none;
  }
  .card {
    border: none;
    padding: 0;
  }
  textarea,
  input[type='number'] {
    border: 1px solid #999;
    background: transparent;
  }
}
</style>

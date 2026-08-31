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
 *    The safety line and the "what to bring" list are the same branch, stated
 *    as things a technician needs before leaving the yard, not just after.
 *
 * 2. A FINDINGS SECTION. This closes DETECT -> VERIFY -> CONFIRM -> LEARN and is
 *    what populates Screen 4's confirmed-fault and recovered-generation figures.
 *    Without it the loop is open and the ROI screen has nothing real to count.
 *    Each checklist item now records PASS / FAIL / N-A rather than a single
 *    tick — "I looked at it" and "it's fine" are different facts, and only one
 *    of them is useful to a report. A failed item prompts for a one-line note
 *    and rolls up into a warning on the Findings section below it.
 *
 * Findings persist to localStorage only — there is no backend yet. That is
 * stated on screen rather than implied, so nobody assumes it syncs.
 *
 * PRINT / EXPORT. This is the one screen in the product whose primary output
 * is paper (or a saved PDF) rather than the browser tab — a technician reads
 * it in a truck, not on this dashboard. The `.print-doc` wrapper below uses
 * the `display: table-header-group` / `table-footer-group` trick so a compact
 * letterhead and a provenance line repeat on every printed page — CSS Paged
 * Media running headers aren't supported in Chromium's print engine, and this
 * table trick is the standard, cross-browser substitute. `workOrderId` and
 * `openedAtLabel` exist for that document, not for the schema — dispatch.json
 * carries no work-order id (docs/Schema.md is FROZEN); this is a display-only
 * reference built from fields that are already real. The app shell's nav rail
 * is hidden globally for print in App.vue, not here — that chrome lives above
 * every route, so the rule does too.
 */
import { computed, onMounted, ref, watch, type Component } from 'vue'
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
  TriangleAlert,
  Diamond,
  CircleCheck,
  BarChart3,
  TrendingUp,
  ClipboardList,
  Camera,
  ShieldCheck,
  FileSignature,
  Layers,
  MapPin,
  ExternalLink,
  HardHat,
  Wrench,
} from '@lucide/vue'
import { loadDispatch, findSite, findCohort, formatRinggit, formatCapacity } from '@/services/api'
import type { Dispatch, Site, SiteStatus } from '@/types/dispatch'
import DataStatusBadge from '@/components/DataStatusBadge.vue'
import NoticeCallout from '@/components/NoticeCallout.vue'
import BrandLogo from '@/components/BrandLogo.vue'
import { workOrderStorageKey, syncWorkOrderRecord } from '@/services/workOrderRecords'
import { recordEvidenceEvent } from '@/services/evidenceTimeline'
import ScoreGauge from '@/components/ScoreGauge.vue'

const route = useRoute()
const dispatch = ref<Dispatch | null>(null)
const isLoading = ref(true)

const site = computed<Site | undefined>(() =>
  dispatch.value ? findSite(dispatch.value, String(route.params.siteId)) : undefined,
)
const cohort = computed(() =>
  dispatch.value && site.value ? findCohort(dispatch.value, site.value.cohort_id) : undefined,
)

// --- Document identity — header chrome, not analysis --------------------

/** Same status vocabulary and icon language as the Dispatch List, so a
 * "dispatch" site reads the same way everywhere in the product. */
const STATUS_META: Record<SiteStatus, { label: string; icon: Component; tone: string }> = {
  dispatch: { label: 'Dispatch this month', icon: TriangleAlert, tone: 'critical' },
  monitor: { label: 'Monitor', icon: Diamond, tone: 'warning' },
  healthy: { label: 'Healthy — no visit needed', icon: CircleCheck, tone: 'good' },
}

const statusMeta = computed(() => (site.value ? STATUS_META[site.value.status] : null))

/** A document reference, built from real ids — see the file header note. */
const workOrderId = computed(() => {
  if (!site.value || !dispatch.value) return ''
  return `WO-${site.value.site_id}-${dispatch.value.meta.reporting_month}`
})

/** Fixed once at mount — the "printed" timestamp for the print letterhead. */
const openedAt = new Date()
const openedAtLabel = openedAt.toLocaleString(undefined, {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

const mapsUrl = computed(() =>
  site.value ? `https://www.google.com/maps?q=${site.value.lat},${site.value.lon}` : '',
)

/** The one-line verdict a technician (or their dispatcher) reads first.
 * Built entirely from fields already on the site — never a new claim, just
 * the existing status, money-at-risk, divergence and confidence said once,
 * together, instead of scattered across four different places on the page. */
const executiveSummary = computed(() => {
  if (!site.value || !statusMeta.value) return ''
  if (!site.value.economics) {
    return 'No visit needed this month — output stayed within cohort tolerance.'
  }
  const parts = [
    `${statusMeta.value.label}: ${formatRinggit(site.value.economics.rm_at_risk_monthly)}/month at risk`,
  ]
  if (site.value.divergence) {
    parts.push(`diverging ${site.value.divergence.days_since} days`)
  }
  if (site.value.hypothesis) {
    parts.push(`${Math.round(site.value.hypothesis.confidence * 100)}% hypothesis confidence`)
  }
  return parts.join(' · ')
})

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
      safety:
        'No roof access on this visit unless the thermal pass finds a target. If entry becomes ' +
        "necessary afterwards, follow the site's work-at-height procedure and permit " +
        'requirements before ascending — this trip does not carry that authorisation.',
      equipment: [
        'Thermal-imaging camera, or a drone carrying one',
        'Charged spare batteries',
        'Standard site PPE',
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
    safety:
      'Treat the combiner box as live until proven otherwise. De-energise and verify isolation ' +
      "with a meter before opening any enclosure or touching conductors — follow the site's " +
      'lockout/tagout procedure.',
    equipment: [
      'Clamp meter or multimeter',
      'Lockout/tagout kit',
      'Insulated PPE — gloves and eye protection',
    ],
  }
})

// --- Findings (the data flywheel) -------------------------------------------

type Outcome = '' | 'fault_confirmed' | 'nothing_found' | 'different_cause'
type CheckStatus = '' | 'pass' | 'fail' | 'na'

const findingsAssignee = ref('')
const findingsOutcome = ref<Outcome>('')
const findingsNote = ref('')
const findingsRecoveredKwh = ref('')
/** Who attended and when — captured alongside the outcome so a saved finding
 * is attributable, the way a paper work order's sign-off block would be. */
const findingsTechnician = ref('')
const findingsVisitDate = ref('')
const findingsTimeIn = ref('')
const findingsTimeOut = ref('')
const savedAt = ref<string | null>(null)
/** Each checklist item's evaluated state, by its text. "Inspected and fine"
 * and "inspected and broken" are different facts — a single tick can't tell
 * them apart, which is exactly the ambiguity a report can't afford. */
const checkStatus = ref<Record<string, CheckStatus>>({})
/** A short note per check, shown only once that check is marked failed. */
const checkNotes = ref<Record<string, string>>({})
/** Photograph items are binary — captured or not — so they keep a plain tick. */
const photosCaptured = ref<Record<string, boolean>>({})

const storageKey = computed(() => workOrderStorageKey(String(route.params.siteId)))

function loadFindings(): void {
  findingsAssignee.value = ''
  findingsOutcome.value = ''
  findingsNote.value = ''
  findingsRecoveredKwh.value = ''
  findingsTechnician.value = ''
  findingsVisitDate.value = ''
  findingsTimeIn.value = ''
  findingsTimeOut.value = ''
  savedAt.value = null
  checkStatus.value = {}
  checkNotes.value = {}
  photosCaptured.value = {}

  const raw = localStorage.getItem(storageKey.value)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw)
    findingsAssignee.value = parsed.assignee ?? ''
    findingsOutcome.value = parsed.outcome ?? ''
    findingsNote.value = parsed.note ?? ''
    findingsRecoveredKwh.value = parsed.recovered_kwh ?? ''
    findingsTechnician.value = parsed.technician ?? ''
    findingsVisitDate.value = parsed.visit_date ?? ''
    findingsTimeIn.value = parsed.time_in ?? ''
    findingsTimeOut.value = parsed.time_out ?? ''
    savedAt.value = parsed.saved_at ?? null
    checkStatus.value = parsed.check_status ?? {}
    checkNotes.value = parsed.check_notes ?? {}
    photosCaptured.value = parsed.photos_captured ?? {}
  } catch {
    // A corrupt entry is not worth blocking the screen over.
  }
}

/** What a completed outcome reads as on the evidence timeline — the same
 * three choices the Findings radios offer, in past tense. */
const OUTCOME_EVENT: Record<Exclude<Outcome, ''>, { title: string; status: 'confirmed' | 'observed' | 'conflicting' }> = {
  fault_confirmed: { title: 'Field visit confirmed the fault', status: 'confirmed' },
  nothing_found: { title: 'Field visit found nothing wrong', status: 'observed' },
  different_cause: { title: 'Field visit found a different cause', status: 'conflicting' },
}

function saveFindings(): void {
  savedAt.value = new Date().toISOString()
  const snapshot = {
    assignee: findingsAssignee.value,
    outcome: findingsOutcome.value,
    note: findingsNote.value,
    recovered_kwh: findingsRecoveredKwh.value,
    technician: findingsTechnician.value,
    visit_date: findingsVisitDate.value,
    time_in: findingsTimeIn.value,
    time_out: findingsTimeOut.value,
    check_status: checkStatus.value,
    check_notes: checkNotes.value,
    photos_captured: photosCaptured.value,
    saved_at: savedAt.value,
  }
  localStorage.setItem(storageKey.value, JSON.stringify(snapshot))
  if (site.value) syncWorkOrderRecord(site.value.site_id, snapshot)

  // Only a dated, attributed, outcome-bearing save is a completion event —
  // a tapped Pass/Fail box mid-visit (this function also runs from the
  // checklist watcher) is not yet "the work order finished".
  if (site.value && findingsOutcome.value && findingsVisitDate.value && findingsTechnician.value) {
    const outcome = OUTCOME_EVENT[findingsOutcome.value]
    recordEvidenceEvent({
      id: `${site.value.site_id}-work-order-complete`,
      siteId: site.value.site_id,
      type: 'work-order',
      timestamp: findingsVisitDate.value,
      title: outcome.title,
      detail: findingsNote.value || `${findingsTechnician.value} completed the visit on ${findingsVisitDate.value}.`,
      evidenceLevel: 'measured',
      status: outcome.status,
      sourceRef: `work-order:${workOrderId.value}`,
    })
  }
}

/** Tapping a Pass/Fail/N-A option or a photo tick persists immediately — a
 * technician should not have to remember to save a single tap. Typed fields
 * (notes, the outcome, recovered kWh) still wait for the Save button, so a
 * half-typed sentence is never what gets written to disk. */
watch([checkStatus, photosCaptured], saveFindings, { deep: true })

const checklistProgress = computed(() => {
  const checks = site.value?.hypothesis?.checks ?? []
  const photos = site.value?.hypothesis?.photograph ?? []
  const checksDone = checks.filter((item) => checkStatus.value[item]).length
  const photosDone = photos.filter((item) => photosCaptured.value[item]).length
  return { done: checksDone + photosDone, total: checks.length + photos.length }
})

/** Rolls up into a warning on the Findings section — a failed check point
 * should be impossible to miss by the time a technician reaches the outcome
 * radios below it. */
const failedChecks = computed(() =>
  (site.value?.hypothesis?.checks ?? []).filter((check) => checkStatus.value[check] === 'fail'),
)

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
  // Timestamped to the pipeline run, not "now" — a work order exists as of
  // when the dispatch artifact ranked it, not whenever someone opens the
  // screen. Keeps replay ordering stable across repeat visits.
  if (site.value && dispatch.value) {
    recordEvidenceEvent({
      id: `${site.value.site_id}-work-order-generated`,
      siteId: site.value.site_id,
      type: 'work-order',
      timestamp: dispatch.value.meta.generated_at,
      title: 'Work order generated',
      detail: `${workOrderId.value} generated from pipeline ${dispatch.value.meta.pipeline_version}.`,
      evidenceLevel: 'measured',
      status: 'observed',
      sourceRef: `work-order:${workOrderId.value}`,
    })
  }
})

watch(() => route.params.siteId, loadFindings)

function printCard(): void {
  window.print()
}
</script>

<template>
  <main class="screen screen--narrow">
    <section v-if="isLoading" class="load-state" aria-live="polite">
      <span class="load-state__pulse"></span>
      <div>
        <strong>Preparing this work order</strong><span>Loading the latest dispatch artifact…</span>
      </div>
    </section>

    <section v-else-if="!site" class="load-state load-state--missing" role="alert">
      <TriangleAlert :size="22" aria-hidden="true" />
      <div>
        <strong>No site with id {{ route.params.siteId }}</strong>
        <span
          >Check the link, or go back to the dispatch list and open a work order from there.</span
        >
      </div>
      <RouterLink to="/" class="load-state__back">
        <ArrowLeft :size="15" aria-hidden="true" /> Dispatch list
      </RouterLink>
    </section>

    <template v-else>
      <nav class="crumbs no-print">
        <RouterLink to="/" class="crumbs__link">
          <ArrowLeft :size="14" aria-hidden="true" /> Dispatch list
        </RouterLink>
        <RouterLink :to="`/site/${site.site_id}`" class="crumbs__link">Site detail</RouterLink>
        <button
          type="button"
          class="btn-primary print-button"
          title="Opens your browser's print dialog — choose “Save as PDF” as the destination."
          @click="printCard"
        >
          <Printer :size="15" aria-hidden="true" /> Print / export PDF
        </button>
      </nav>

      <!-- The table-display trick: .print-doc__header and .print-doc__footer
           repeat on every printed page, .print-doc__body carries the one
           printable card. See the file header note for why this exists. -->
      <div class="print-doc">
        <div class="print-doc__header">
          <div class="print-head">
            <BrandLogo :size="20" />
            <div class="print-head__doc">
              <strong>Work order {{ workOrderId }}</strong>
              <span>{{ site.name }} · {{ dispatch?.meta.reporting_month_label }}</span>
            </div>
          </div>
        </div>

        <div class="print-doc__body">
          <article class="card">
            <header class="card__head">
              <div>
                <h1 class="card__title">Work order — {{ site.name }}</h1>
                <p
                  v-if="executiveSummary"
                  class="exec-line"
                  :class="`exec-line--${statusMeta?.tone}`"
                >
                  {{ executiveSummary }}
                </p>
              </div>
              <div class="card__meta">
                <span v-if="statusMeta" class="priority" :class="`priority--${statusMeta.tone}`">
                  <component :is="statusMeta.icon" :size="12" aria-hidden="true" />
                  {{ statusMeta.label }}
                </span>
                <DataStatusBadge :status="site.data_status" />
                <p class="card__ref">{{ site.site_id }} · {{ site.source_system_id }}</p>
              </div>
            </header>

            <!-- The work-order header table — one place for every fact a
                 dispatcher or technician needs before setting off, instead of
                 the same handful of numbers scattered across prose and a
                 separate facts strip. -->
            <dl class="doc-table">
              <div class="doc-table__row">
                <dt>Address</dt>
                <dd>
                  <MapPin :size="12" aria-hidden="true" class="doc-table__icon" />{{ site.address }}
                  <a
                    :href="mapsUrl"
                    target="_blank"
                    rel="noopener"
                    class="doc-table__maps no-print"
                  >
                    Open in Maps <ExternalLink :size="11" aria-hidden="true" />
                  </a>
                </dd>
              </div>
              <div class="doc-table__row">
                <dt>Coordinates</dt>
                <dd>{{ site.lat.toFixed(5) }}, {{ site.lon.toFixed(5) }}</dd>
              </div>
              <div class="doc-table__row">
                <dt>Capacity</dt>
                <dd>{{ formatCapacity(site.capacity_kwp) }}</dd>
              </div>
              <div class="doc-table__row">
                <dt>Cohort</dt>
                <dd>{{ cohort?.label ?? 'Ungrouped' }}</dd>
              </div>
              <div v-if="site.economics" class="doc-table__row">
                <dt>Money at risk</dt>
                <dd class="doc-table__strong">
                  {{ formatRinggit(site.economics.rm_at_risk_monthly) }}/month
                </dd>
              </div>
              <div v-if="site.divergence" class="doc-table__row">
                <dt>Diverging since</dt>
                <dd>{{ site.divergence.start_date }} ({{ site.divergence.days_since }} days)</dd>
              </div>
              <div class="doc-table__row">
                <dt>Reporting month</dt>
                <dd>{{ dispatch?.meta.reporting_month_label }}</dd>
              </div>
              <div class="doc-table__row doc-table__row--assign">
                <dt>Assigned to</dt>
                <dd>
                  <input
                    v-model="findingsAssignee"
                    type="text"
                    placeholder="Technician / crew name"
                    autocomplete="name"
                    @change="saveFindings"
                  />
                </dd>
              </div>
            </dl>

            <!-- Safety, stated before any technical detail — not buried in
                 section 4 where a technician might not reach it before
                 opening an enclosure or heading for the roof. -->
            <NoticeCallout v-if="verification" tone="warning" :icon="HardHat" class="safety">
              <strong>Safety.</strong> {{ verification.safety }}
            </NoticeCallout>

            <!-- Why this site, in plain language, before any technical detail. -->
            <NoticeCallout tone="info" class="rationale">{{ selectionRationale }}</NoticeCallout>

            <!-- Rank context: where this site sits against the others competing for
                 the same technician. A number without its peers is not an argument. -->
            <section v-if="rankedFlagged.length > 1" class="rank">
              <h2 class="section__title">
                <BarChart3 :size="13" aria-hidden="true" class="section__icon" />
                Why this one — all flagged sites by money at risk
              </h2>
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
              <h2 class="section__title">
                <TrendingUp :size="13" aria-hidden="true" class="section__icon" />
                Specific yield, last 90 days (kWh/kWp/day)
              </h2>
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

            <section v-if="site.hypothesis" class="section">
              <h2 class="section__title">
                <TriangleAlert :size="13" aria-hidden="true" class="section__icon" />
                What we think is wrong
              </h2>
              <div class="hypothesis">
                <ScoreGauge :score="site.hypothesis.confidence" tone="warning" :size="56" />
                <div>
                  <p class="section__lead">{{ site.hypothesis.summary }}</p>
                  <p class="section__body">{{ site.hypothesis.detail }}</p>
                  <p class="section__meta">
                    Confidence {{ Math.round(site.hypothesis.confidence * 100) }}% · method:
                    {{ site.detection?.method }}
                  </p>
                </div>
              </div>
            </section>

            <!-- Conditional on the hypothesis. Not every dispatch needs a drone. -->
            <section v-if="verification" class="section section--method">
              <h2 class="section__title">
                <ShieldCheck :size="13" aria-hidden="true" class="section__icon" />
                How to verify it
              </h2>

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
                  :class="
                    verification.kind === 'module' ? 'route__node--active' : 'route__node--dim'
                  "
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

              <h3 class="subhead"><Wrench :size="12" aria-hidden="true" /> What to bring</h3>
              <ul class="equipment">
                <li v-for="item in verification.equipment" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section v-if="site.hypothesis?.checks?.length" class="section">
              <h2 class="section__title">
                <ClipboardList :size="13" aria-hidden="true" class="section__icon" />
                What to check on site
                <span class="section__progress"
                  >{{ checklistProgress.done }} / {{ checklistProgress.total }} done</span
                >
              </h2>
              <ul class="checktable">
                <template v-for="check in site.hypothesis.checks" :key="check">
                  <li class="checkrow">
                    <span class="checkrow__text">{{ check }}</span>
                    <div class="seg" role="radiogroup" :aria-label="check">
                      <label class="seg__opt seg__opt--pass">
                        <input
                          v-model="checkStatus[check]"
                          type="radio"
                          :name="check"
                          value="pass"
                        />
                        <span>Pass</span>
                      </label>
                      <label class="seg__opt seg__opt--fail">
                        <input
                          v-model="checkStatus[check]"
                          type="radio"
                          :name="check"
                          value="fail"
                        />
                        <span>Fail</span>
                      </label>
                      <label class="seg__opt seg__opt--na">
                        <input v-model="checkStatus[check]" type="radio" :name="check" value="na" />
                        <span>N/A</span>
                      </label>
                    </div>
                  </li>
                  <li v-if="checkStatus[check] === 'fail'" class="checkrow__note">
                    <textarea
                      v-model="checkNotes[check]"
                      rows="2"
                      placeholder="What did you find?"
                      @change="saveFindings"
                    ></textarea>
                  </li>
                </template>
              </ul>
            </section>

            <section v-if="site.hypothesis?.photograph?.length" class="section">
              <h2 class="section__title">
                <Camera :size="13" aria-hidden="true" class="section__icon" />
                What to photograph
              </h2>
              <ul class="checklist">
                <li v-for="item in site.hypothesis.photograph" :key="item">
                  <label class="checklist__item">
                    <input v-model="photosCaptured[item]" type="checkbox" />
                    <span :class="{ checklist__done: photosCaptured[item] }">{{ item }}</span>
                  </label>
                </li>
              </ul>
            </section>

            <!-- Units drawn rather than listed: worst-first is the inspection order. -->
            <section v-if="site.sub_site" class="section">
              <h2 class="section__title">
                <Layers :size="13" aria-hidden="true" class="section__icon" />
                Units to inspect first
              </h2>
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
                    <template v-if="unit.thermal"
                      >{{ unit.thermal.mean_temp_c.toFixed(1) }}°C</template
                    >
                    <template v-else>—</template>
                  </span>
                  <span v-if="unit.status === 'flagged'" class="units__flag">flagged</span>
                  <span v-else class="units__ok">ok</span>
                </li>
              </ul>
            </section>

            <!-- The data flywheel. Screen 4 counts what gets recorded here. -->
            <section class="section section--findings">
              <h2 class="section__title">
                <FileSignature :size="13" aria-hidden="true" class="section__icon" />
                Findings — complete after the visit
              </h2>

              <NoticeCallout v-if="failedChecks.length" tone="critical" compact class="fail-rollup">
                {{ failedChecks.length }} check{{ failedChecks.length > 1 ? 's' : '' }} failed above
                — see the notes on each. Consider marking the outcome "Fault confirmed" below.
              </NoticeCallout>

              <div class="field-row">
                <label class="field">
                  <span class="field__label">Technician name</span>
                  <input
                    v-model="findingsTechnician"
                    type="text"
                    placeholder="Full name"
                    autocomplete="name"
                  />
                </label>
                <label class="field">
                  <span class="field__label">Date completed</span>
                  <input v-model="findingsVisitDate" type="date" />
                </label>
              </div>

              <div class="field-row">
                <label class="field">
                  <span class="field__label">Time in</span>
                  <input v-model="findingsTimeIn" type="time" />
                </label>
                <label class="field">
                  <span class="field__label">Time out</span>
                  <input v-model="findingsTimeOut" type="time" />
                </label>
              </div>

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
                    ><input v-model="findingsOutcome" type="radio" value="different_cause" />
                    Different cause</label
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

              <!-- Paper-only sign-off. There is no e-signature capture here — this
                   gives a printed copy the same completion block a technician
                   would expect on any field-service work order. -->
              <div class="signature">
                <div class="signature__line">
                  <span class="signature__label">Technician signature</span>
                  <span class="signature__rule"></span>
                </div>
                <div class="signature__line">
                  <span class="signature__label">Date</span>
                  <span class="signature__rule signature__rule--short"></span>
                </div>
              </div>

              <div class="field no-print">
                <button type="button" class="btn-primary save-button" @click="saveFindings">
                  Save findings
                </button>
                <span v-if="savedAt" class="field__saved"
                  >Saved {{ new Date(savedAt).toLocaleString() }}</span
                >
              </div>

              <p class="field__note no-print">
                Findings are stored in this browser only — there is no backend yet. Confirmed
                outcomes are what Screen 4 counts, and what would retrain the detector.
              </p>
            </section>

            <section class="activity no-print" aria-labelledby="activity-title">
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
                      savedAt
                        ? `Saved ${new Date(savedAt).toLocaleString()}`
                        : 'Awaiting site findings'
                    }}</span>
                  </div>
                </li>
              </ol>
            </section>

            <footer class="card__foot">
              <p>
                {{ dispatch?.meta.data_source }} · generated {{ dispatch?.meta.generated_at }} ·
                schema {{ dispatch?.meta.schema_version }}
              </p>
              <p v-if="dispatch?.meta.date_remapped">{{ dispatch?.meta.date_remap_note }}</p>
            </footer>
          </article>
        </div>

        <div class="print-doc__footer">
          <div class="print-foot">
            <span>SolaraX fleet triage · {{ dispatch?.meta.data_source }}</span>
            <span>Printed {{ openedAtLabel }}</span>
          </div>
        </div>
      </div>
    </template>
  </main>
</template>

<style scoped>
/* --- Loading / missing states — same idiom as the Dispatch List's
     .load-state, so a slow network reads the same way everywhere. --- */

.load-state {
  display: flex;
  min-height: 40vh;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  text-align: left;
  color: var(--text-secondary);
}
.load-state div {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.load-state strong {
  color: var(--text-primary);
  font-family: var(--font-display);
  font-size: 1.05rem;
}
.load-state span {
  font-size: 0.85rem;
}
.load-state__pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--signal-live);
  box-shadow: 0 0 0 8px color-mix(in srgb, var(--signal-live) 16%, transparent);
  animation: pulse 1.6s var(--ease-out) infinite;
}
.load-state--missing {
  color: var(--status-critical);
}
.load-state__back {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 40px;
  padding: 0 0.9rem;
  color: var(--text-primary);
  background: var(--surface-1);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  text-decoration: none;
}
@keyframes pulse {
  50% {
    opacity: 0.5;
    transform: scale(0.84);
  }
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
   button on Site Detail — one action treatment across the product. Visual
   idiom now comes from .btn-primary (assets/layout.css); only placement
   survives here. */
.print-button {
  margin-left: auto;
}

.save-button {
  margin-left: 0;
}

/* Deliberately duplicates the global .card class's values rather than using
   that class directly — this element is a print-document root, not a
   browsable card, and must never pick up .card--interactive's hover-lift or
   any future change to the shared class. Keep these four properties in sync
   with layout.css's .card by hand if that class ever changes. */
.card {
  padding: 1.75rem;
  background: var(--surface-1);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
  box-shadow: var(--elevation-1);
}

/* --- Print letterhead / footer — hidden on screen, repeated every page in
     print via the table-display trick (see script comment). --- */

.print-doc__header,
.print-doc__footer {
  display: none;
}

.print-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.print-head__doc {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  font-size: 0.72rem;
  color: var(--text-secondary);
}
.print-head__doc strong {
  font-size: 0.8rem;
  color: var(--text-primary);
}
.print-foot {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  font-size: 0.65rem;
  color: var(--text-muted);
}

.activity {
  margin-top: var(--space-lg);
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
  font-size: 1.85rem;
  font-weight: 650;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

/* The one-line verdict — bigger and bolder than ordinary body text, coloured
   by the same tone as the priority chip, so a scan of the page lands here
   first regardless of where the eye starts. */
.exec-line {
  margin: 0.4rem 0 0;
  font-size: 0.98rem;
  font-weight: 600;
}
.exec-line--critical {
  color: var(--status-critical);
}
.exec-line--warning {
  color: var(--brand-solar-deep);
}
.exec-line--good {
  color: var(--success-text);
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

/* Priority chip — same tint-plus-icon idiom as NoticeCallout, so status
   colour is never the only thing carrying the meaning. */
.priority {
  display: inline-flex;
  align-items: center;
  gap: 0.35em;
  padding: 0.25em 0.6em;
  border: 1px solid;
  border-radius: var(--radius-full);
  color: var(--text-primary);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  white-space: nowrap;
}
.priority--critical {
  background: var(--callout-critical-bg);
  border-color: var(--callout-critical-border);
}
.priority--critical svg {
  color: var(--status-critical);
}
.priority--warning {
  background: var(--callout-warning-bg);
  border-color: var(--callout-warning-border);
}
.priority--warning svg {
  color: var(--status-warning);
}
.priority--good {
  background: var(--callout-good-bg);
  border-color: var(--callout-good-border);
}
.priority--good svg {
  color: var(--status-good);
}

/* --- Work-order header table --- */

.doc-table {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 0.7rem 1.5rem;
  margin: 1.1rem 0;
  padding: 0.9rem 0;
  border-top: 1px solid var(--border-hairline);
  border-bottom: 1px solid var(--border-hairline);
}

.doc-table__row {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.doc-table dt {
  font-size: 0.64rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.doc-table dd {
  margin: 0;
  font-size: 0.88rem;
  color: var(--text-primary);
}

.doc-table__icon {
  margin-right: 0.3em;
  color: var(--text-muted);
  vertical-align: -1px;
}

.doc-table__strong {
  font-weight: 700;
}

.doc-table__maps {
  display: inline-flex;
  align-items: center;
  gap: 0.25em;
  margin-left: 0.5rem;
  color: var(--action-text);
  font-size: 0.78rem;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}
.doc-table__maps:hover {
  text-decoration: underline;
}

.doc-table__row--assign input {
  padding: 0.3rem 0.5rem;
  font-size: 0.85rem;
}

/* Safety sits between the header table and everything else — see the
   template comment for why it isn't inside section 4 instead. */
.safety {
  margin-bottom: 1rem;
}

/* Tint, border and icon come from NoticeCallout. This previously used --series-1,
   a CHART categorical colour, as a page-chrome accent — series colours are
   reserved for data marks and borrowing one here quietly broke that rule. */
.rationale {
  margin-top: 0;
}

.section {
  margin-top: var(--space-lg);
  padding-top: 1rem;
  border-top: 1px solid var(--border-hairline);
}

.section--method {
  background: var(--page-plane);
  padding: 1rem;
  border-radius: var(--radius-sm);
  border-top: none;
}

/* Numbered like a formal report: 1. Why this one, 2. What we think is wrong,
   etc. Purely a CSS counter — it renumbers itself whenever a v-if section is
   absent, so nothing here needs to track section order by hand. */
.card {
  counter-reset: section;
}

.section__title {
  display: flex;
  align-items: center;
  gap: 0.4em;
  margin: 0 0 0.5rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
  counter-increment: section;
}

.section__title::before {
  content: counter(section) '.';
  flex: none;
  font-variant-numeric: tabular-nums;
}

.section__icon {
  flex: none;
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

.hypothesis {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}
.hypothesis > div {
  min-width: 0;
}
@media (max-width: 480px) {
  .hypothesis {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
}

.steps {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.88rem;
  line-height: 1.7;
}

/* Small all-caps label ahead of a secondary list within a section — the
   equipment list under "How to verify it", not important enough for a
   numbered section title of its own. */
.subhead {
  display: flex;
  align-items: center;
  gap: 0.35em;
  margin: 1rem 0 0.4rem;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.equipment {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--text-secondary);
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

/* Custom box rather than the OS-native checkbox widget: the native control
   renders at wildly different sizes across browsers and print engines, which
   is exactly the inconsistency an exported PDF can't afford. This keeps the
   same square on screen and on paper. */
.checklist__item input[type='checkbox'] {
  appearance: none;
  -webkit-appearance: none;
  display: inline-grid;
  place-content: center;
  width: 17px;
  height: 17px;
  margin: 0.1rem 0 0;
  background: var(--surface-1);
  border: 1.5px solid var(--baseline);
  border-radius: 4px;
  cursor: pointer;
  flex-shrink: 0;
  transition:
    background-color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}

.checklist__item input[type='checkbox']::before {
  content: '';
  width: 9px;
  height: 9px;
  background: var(--action-ink);
  clip-path: polygon(14% 44%, 0 65%, 50% 100%, 100% 16%, 80% 0%, 43% 62%);
  transform: scale(0);
  transition: transform var(--duration-fast) var(--ease-out);
}

.checklist__item input[type='checkbox']:checked {
  background: var(--action-fill);
  border-color: var(--action-fill);
}

.checklist__item input[type='checkbox']:checked::before {
  transform: scale(1);
}

.checklist__done {
  text-decoration: line-through;
  color: var(--text-muted);
}

.section__progress {
  margin-left: auto;
  font-weight: 400;
  letter-spacing: 0;
  text-transform: none;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* --- What-to-check table: Pass / Fail / N-A per row, not a single tick.
     "Inspected and fine" and "inspected and broken" are different facts. --- */

.checktable {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
}

.checkrow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem 1rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-hairline);
}

.checkrow:last-child {
  border-bottom: none;
}

.checkrow__text {
  flex: 1 1 200px;
  font-size: 0.86rem;
}

.checkrow__note {
  margin: -0.1rem 0 0.6rem;
}

.checkrow__note textarea {
  border-color: var(--callout-critical-border);
}

.seg {
  display: inline-flex;
  flex: none;
  border: 1px solid var(--baseline);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.seg__opt {
  position: relative;
  display: inline-flex;
}

.seg__opt input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.seg__opt span {
  display: block;
  padding: 0.3rem 0.65rem;
  border-left: 1px solid var(--baseline);
  color: var(--text-secondary);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  white-space: nowrap;
  transition: background-color var(--duration-fast) var(--ease-out);
}

.seg__opt:first-child span {
  border-left: none;
}

.seg__opt--pass input:checked + span {
  background: var(--callout-good-bg);
  color: var(--success-text);
}

.seg__opt--fail input:checked + span {
  background: var(--callout-critical-bg);
  color: var(--status-critical);
}

.seg__opt--na input:checked + span {
  background: var(--surface-2);
  color: var(--text-primary);
}

.seg__opt input:focus-visible + span {
  outline: 2px solid var(--focus-ring);
  outline-offset: -2px;
}

.fail-rollup {
  margin-bottom: 1rem;
}

/* --- Rank context --- */

.rank {
  margin-top: var(--space-lg);
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
  margin-top: var(--space-lg);
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

.field-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.field-row .field {
  flex: 1 1 200px;
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

.radios input[type='radio'] {
  accent-color: var(--action-fill);
}

textarea,
input[type='number'],
input[type='text'],
input[type='date'],
input[type='time'] {
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

/* Paper sign-off block — shown only when printed. See the template comment. */
.signature {
  display: none;
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

@media (max-width: 480px) {
  .screen {
    padding: 1rem;
  }
  .card {
    padding: 1.1rem;
  }
  /* Let the bar drop to its own full-width row instead of squeezing three
     columns into a phone-width grid. */
  .rank__row {
    grid-template-columns: 1.25rem 1fr auto;
    row-gap: 0.25rem;
  }
  .rank__bar {
    grid-column: 1 / -1;
  }
  .units__row {
    grid-template-columns: 2.5rem 1fr auto;
    row-gap: 0.25rem;
  }
  .units__bar {
    grid-column: 1 / -1;
  }
  .checkrow {
    flex-direction: column;
    align-items: flex-start;
  }
}

/* --- Print: a letterhead-style document, not a screenshot of the page. --- */
@media print {
  @page {
    size: A4;
    margin: 15mm 14mm 18mm;
  }

  .no-print {
    display: none !important;
  }

  .screen {
    padding: 0;
    max-width: none;
  }

  /* The running-header trick: an ancestor set to `table` plus
     table-header/footer-group children repeats those children on every
     printed page in every major engine — Chromium's print pipeline has no
     support for CSS Paged Media's @page margin-box content, so this is the
     standard substitute rather than a shortcut. */
  .print-doc {
    display: table;
    width: 100%;
  }
  .print-doc__header {
    display: table-header-group;
  }
  .print-doc__footer {
    display: table-footer-group;
  }
  .print-doc__body {
    display: table-row-group;
  }
  .print-head {
    padding-bottom: 3mm;
    margin-bottom: 4mm;
    border-bottom: 1px solid #999;
  }
  .print-foot {
    padding-top: 2mm;
    margin-top: 4mm;
    border-top: 1px solid #ccc;
  }

  .card {
    border: none;
    padding: 0;
    box-shadow: none;
  }

  /* Backgrounds (callout tints, status fills, badge borders) carry real
     meaning here, per the "never rely on colour alone" rule — but a browser
     drops them by default unless the reader remembers to tick "print
     backgrounds". This forces them to survive regardless of that setting. */
  * {
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
  }

  section,
  .rank,
  .trace,
  .route,
  .rank__row,
  .units__row,
  .activity__event,
  .field,
  .field-row,
  .doc-table__row,
  .checkrow {
    break-inside: avoid;
  }

  .section__title {
    break-after: avoid;
  }

  .signature {
    display: flex;
    flex-wrap: wrap;
    gap: 2rem;
    margin: 1.25rem 0 0.5rem;
  }
  .signature__line {
    display: flex;
    flex: 1 1 220px;
    align-items: flex-end;
    gap: 0.6rem;
  }
  .signature__label {
    flex: none;
    color: #555;
    font-size: 0.7rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .signature__rule {
    flex: 1;
    height: 1.4rem;
    border-bottom: 1px solid #000;
  }
  .signature__rule--short {
    flex: 0 0 110px;
  }

  textarea,
  input[type='number'],
  input[type='text'],
  input[type='date'],
  input[type='time'] {
    border: 1px solid #999;
    background: transparent;
  }

  /* Native checkboxes print inconsistently across engines; the custom box
     defined above (border + background, no OS chrome) is used as-is. The
     Pass/Fail/N-A segmented control is driven by :checked, a real DOM state,
     so it prints whichever option was actually selected. */
}
</style>

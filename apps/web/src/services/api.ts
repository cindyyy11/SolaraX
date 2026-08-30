/**
 * The single data-access layer. Every component fetches through this file.
 *
 * Why it exists: the pipeline's only output is `dispatch.json`. Today that is
 * served as a static file; later it will come from Supabase via PostgREST.
 * When that happens, only this file changes — no component touches a URL.
 *
 * Fallback is deliberate and required. Supabase free projects pause after seven
 * days without a request, and an unreachable dashboard during the judging window
 * counts as non-submission. So a failed primary fetch degrades to the committed
 * JSON rather than rendering an error. See CLAUDE.md and docs/Schema.md §1.1.
 */

import { toHttpError, HttpError } from './httpError'
import type { Dispatch, Site, Cohort, CohortSeriesRow, SiteStatus } from '@/types/dispatch'

/** Major version this frontend was written against. A mismatch is a loud warning. */
const EXPECTED_SCHEMA_MAJOR = '1'

const PRIMARY_URL = import.meta.env.VITE_DISPATCH_URL ?? '/dispatch.json'
const FALLBACK_URL = '/dispatch.mock.json'

export type DispatchSource = 'primary' | 'fallback'

export interface LoadResult {
  dispatch: Dispatch
  source: DispatchSource
  /** Populated when the primary failed and the fallback was used instead. */
  primaryError?: HttpError
}

let cached: LoadResult | null = null

async function fetchJson(url: string): Promise<Dispatch> {
  const response = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!response.ok) {
    throw new HttpError(`Failed to fetch ${url}`, response.status, null)
  }
  return (await response.json()) as Dispatch
}

function warnOnSchemaMismatch(dispatch: Dispatch): void {
  const version = dispatch.meta?.schema_version ?? ''
  const major = version.split('.')[0]
  if (major !== EXPECTED_SCHEMA_MAJOR) {
    console.warn(
      `[api] dispatch.json is schema ${version}; this frontend expects major ` +
        `${EXPECTED_SCHEMA_MAJOR}. Fields may be missing or renamed.`,
    )
  }
}

/**
 * Load the dispatch artifact, preferring the primary source and degrading to the
 * committed fallback. Result is cached for the session; pass `force` to refetch.
 */
export async function loadDispatch(force = false): Promise<LoadResult> {
  if (cached && !force) {
    return cached
  }

  let primaryError: HttpError | undefined

  try {
    const dispatch = await fetchJson(PRIMARY_URL)
    warnOnSchemaMismatch(dispatch)
    cached = { dispatch, source: 'primary' }
    return cached
  } catch (error) {
    primaryError = toHttpError(error)
    console.warn(`[api] primary source failed (${primaryError.message}) — falling back`)
  }

  const dispatch = await fetchJson(FALLBACK_URL)
  warnOnSchemaMismatch(dispatch)
  cached = { dispatch, source: 'fallback', primaryError }
  return cached
}

// --- Selectors --------------------------------------------------------------
// Reshaping lives here, never in components. The pipeline emits long format;
// charts want it grouped. That transform happens once, in this file.

/**
 * Did the detector actually reach a verdict on this site?
 *
 * A site excluded from analysis has no verdict, only a default. It still
 * carries status "healthy" in the artifact because the frozen schema allows
 * exactly three values and validator rule 4 asserts the three counts sum to
 * site_count — so `dispatch.json` has no way to say "not assessed", and the
 * split has to be made here, at the point of display.
 *
 * This is the same reasoning that dropped GOLDEN-01 on 19 Aug: a site with no
 * measurements cannot be called healthy. S-1367 is 277 kWp — 21% of fleet
 * capacity — and reports 1.11 kWh/kWp/day against a fleet median of 3.83.
 * Counting it as healthy overstates how much of the fleet was cleared.
 */
export function isAssessed(site: Site): boolean {
  return !site.excluded_from_analysis?.excluded
}

const byRank = (a: Site, b: Site): number =>
  (a.rank ?? Number.MAX_SAFE_INTEGER) - (b.rank ?? Number.MAX_SAFE_INTEGER)

/** Sites in one triage group, already ordered by rank. Assessed sites only. */
export function sitesByStatus(dispatch: Dispatch, status: SiteStatus): Site[] {
  return dispatch.sites
    .filter((site) => site.status === status && isAssessed(site))
    .sort(byRank)
}

/** Sites the detector never ruled on — shown as their own group, never hidden. */
export function sitesNotAssessed(dispatch: Dispatch): Site[] {
  return dispatch.sites.filter((site) => !isAssessed(site)).sort(byRank)
}

export function findSite(dispatch: Dispatch, siteId: string): Site | undefined {
  return dispatch.sites.find((site) => site.site_id === siteId)
}

export function findCohort(dispatch: Dispatch, cohortId: string | null): Cohort | undefined {
  if (!cohortId) return undefined
  return dispatch.cohorts.find((cohort) => cohort.cohort_id === cohortId)
}

export interface CohortLine {
  siteId: string
  isSubject: boolean
  points: Array<{ date: string; value: number }>
}

/**
 * Reshape the long-format cohort series into one line per peer.
 *
 * Long format is what the pipeline emits deliberately — wide format breaks the
 * moment cohort membership changes. The reshape happens once, here, so every
 * chart consumes the same shape.
 */
export function cohortLines(rows: CohortSeriesRow[]): CohortLine[] {
  const bySite = new Map<string, CohortLine>()

  for (const row of rows) {
    let line = bySite.get(row.site_id)
    if (!line) {
      line = { siteId: row.site_id, isSubject: row.is_subject, points: [] }
      bySite.set(row.site_id, line)
    }
    line.points.push({ date: row.date, value: row.performance_index })
  }

  for (const line of bySite.values()) {
    line.points.sort((a, b) => a.date.localeCompare(b.date))
  }

  // Subject last so it draws on top of its peers.
  return [...bySite.values()].sort((a, b) => Number(a.isSubject) - Number(b.isSubject))
}

// --- Formatting -------------------------------------------------------------

export function formatRinggit(value: number): string {
  return `RM ${Math.round(value).toLocaleString('en-MY')}`
}

export function formatCapacity(kwp: number): string {
  return `${kwp.toLocaleString('en-MY', { maximumFractionDigits: 0 })} kWp`
}

//cv
export interface VisionEvidencePayload {
  has_imagery: boolean
  defect_class: string
  confidence: number
  model_note: string
  inference_mode: string
  data_status: string
}

export interface VisionPrediction {
  evidence: VisionEvidencePayload
}

/**
 * Base URL for the M5 vision service, or null when there isn't one.
 *
 * WHY THIS IS NOT A CONSTANT WITH A LOCALHOST DEFAULT. It used to be
 * `import.meta.env.VITE_VISION_API_URL ?? 'http://127.0.0.1:8000'`, which is
 * correct on a developer's machine and broken everywhere else. A deployed
 * dashboard is served over HTTPS, and a browser refuses a plaintext request to
 * 127.0.0.1 from an HTTPS page as mixed content — so on the public URL the
 * upload panel rendered, accepted a file, and then failed for every visitor.
 * The one screen with a live model demo was the one screen guaranteed to break
 * in front of a judge.
 *
 * Localhost stays the default in DEV only, so `npm run dev` still works with no
 * setup. In a production build the panel is hidden unless VITE_VISION_API_URL is
 * explicitly set to a reachable HTTPS endpoint.
 */
export const VISION_API_URL: string | null =
  import.meta.env.VITE_VISION_API_URL ??
  (import.meta.env.DEV ? 'http://127.0.0.1:8000' : null)

/** Whether the vision panel has somewhere to post to. Components gate on this. */
export const isVisionApiConfigured = (): boolean => Boolean(VISION_API_URL)

export async function predictVision(
  image: File,
): Promise<VisionPrediction> {
  if (!VISION_API_URL) {
    throw new Error(
      'No vision service is configured. Set VITE_VISION_API_URL to enable image analysis.',
    )
  }

  const formData = new FormData()

  // Must be called "image" because FastAPI expects:
  // image: UploadFile = File(...)
  formData.append('image', image)

  const response = await fetch(
    `${VISION_API_URL}/vision/predict`,
    {
      method: 'POST',
      body: formData,
    },
  )

  if (!response.ok) {
    throw new Error(
      `Vision prediction failed: ${response.status}`,
    )
  }

  return (await response.json()) as VisionPrediction
}
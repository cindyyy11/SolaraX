/**
 * Shared read/write for a site's work-order findings — the one thing
 * WorkOrderView writes and RecoveryTracker / EvidenceTimeline need to read.
 *
 * There is no backend yet (WorkOrderView says so on screen), so this stays a
 * thin wrapper over the same localStorage entry WorkOrderView has always
 * written, not a new source of truth. Extracting the key format here means
 * both sides agree on it by construction instead of by matching string
 * literals in two files.
 */
import { reactive } from 'vue'

export type WorkOrderOutcome = '' | 'fault_confirmed' | 'nothing_found' | 'different_cause'
export type WorkOrderCheckStatus = '' | 'pass' | 'fail' | 'na'

export interface WorkOrderFindings {
  assignee: string
  outcome: WorkOrderOutcome
  note: string
  recovered_kwh: string
  technician: string
  visit_date: string
  time_in: string
  time_out: string
  check_status: Record<string, WorkOrderCheckStatus>
  check_notes: Record<string, string>
  photos_captured: Record<string, boolean>
  saved_at: string | null
}

const EMPTY_FINDINGS: WorkOrderFindings = {
  assignee: '',
  outcome: '',
  note: '',
  recovered_kwh: '',
  technician: '',
  visit_date: '',
  time_in: '',
  time_out: '',
  check_status: {},
  check_notes: {},
  photos_captured: {},
  saved_at: null,
}

const records = reactive<Record<string, WorkOrderFindings>>({})

export function workOrderStorageKey(siteId: string): string {
  return `solarax:findings:${siteId}`
}

function readFromStorage(siteId: string): WorkOrderFindings {
  let raw: string | null = null
  try {
    raw = localStorage.getItem(workOrderStorageKey(siteId))
  } catch {
    // localStorage unavailable (private mode, disabled) — treat as empty.
  }
  if (!raw) return { ...EMPTY_FINDINGS }
  try {
    return { ...EMPTY_FINDINGS, ...JSON.parse(raw) }
  } catch {
    return { ...EMPTY_FINDINGS }
  }
}

/** Live-reactive read. Loads from storage on first access per site, then
 * tracks whatever WorkOrderView (or anything else) writes through
 * `syncWorkOrderRecord` in the same tab. */
export function workOrderRecord(siteId: string): WorkOrderFindings {
  if (!records[siteId]) records[siteId] = readFromStorage(siteId)
  return records[siteId]
}

/** Called by WorkOrderView after it persists to localStorage — keeps the
 * reactive copy in sync so other mounted components see the same state
 * without a page reload. */
export function syncWorkOrderRecord(siteId: string, findings: WorkOrderFindings): void {
  records[siteId] = { ...findings }
}

/** A work order counts as "completed" once a technician has recorded who
 * attended, when, and what they found — the same three facts the printed
 * sign-off block asks for. A recovered-kWh estimate alone is not enough;
 * that number is only meaningful attached to a dated, attributed visit. */
export function isWorkOrderComplete(record: WorkOrderFindings): boolean {
  return Boolean(record.outcome && record.visit_date && record.technician)
}

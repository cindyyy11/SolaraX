import { beforeEach, describe, expect, it } from 'vitest'
import {
  isWorkOrderComplete,
  syncWorkOrderRecord,
  workOrderRecord,
  workOrderStorageKey,
  type WorkOrderFindings,
} from './workOrderRecords'

const findings = (overrides: Partial<WorkOrderFindings> = {}): WorkOrderFindings => ({
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
  ...overrides,
})

// This environment's jsdom + Node 25 combination leaves both
// `globalThis.localStorage` and `window.localStorage` as a plain object
// with none of the Storage methods (getItem/setItem/clear) — a jsdom/Node
// webstorage-global collision unrelated to this service, which uses the
// same bare `localStorage` identifier as the rest of this codebase and
// resolves correctly in an actual browser. A minimal in-memory Storage
// stand-in keeps this test exercising the service's real code path
// (bare-identifier reads and writes) without depending on that broken
// global.
class MemoryStorage {
  private store = new Map<string, string>()
  getItem(key: string) { return this.store.has(key) ? this.store.get(key)! : null }
  setItem(key: string, value: string) { this.store.set(key, value) }
  removeItem(key: string) { this.store.delete(key) }
  clear() { this.store.clear() }
}
Object.defineProperty(globalThis, 'localStorage', { value: new MemoryStorage(), configurable: true })

beforeEach(() => localStorage.clear())

describe('work order records', () => {
  it('reads an empty record when nothing is stored', () => {
    const record = workOrderRecord('S-empty')
    expect(record.outcome).toBe('')
    expect(isWorkOrderComplete(record)).toBe(false)
  })

  it('reads what was persisted to the shared storage key', () => {
    localStorage.setItem(
      workOrderStorageKey('S-1'),
      JSON.stringify(findings({ outcome: 'fault_confirmed', visit_date: '2026-08-20', technician: 'A. Lim' })),
    )
    const record = workOrderRecord('S-1')
    expect(record.outcome).toBe('fault_confirmed')
    expect(isWorkOrderComplete(record)).toBe(true)
  })

  it('syncs a live update without re-reading storage', () => {
    syncWorkOrderRecord('S-2', findings({ outcome: 'nothing_found', visit_date: '2026-08-21', technician: 'B. Tan' }))
    expect(workOrderRecord('S-2').outcome).toBe('nothing_found')
  })

  it('is not complete without a technician, a date, and an outcome', () => {
    expect(isWorkOrderComplete(findings({ outcome: 'fault_confirmed' }))).toBe(false)
    expect(isWorkOrderComplete(findings({ outcome: 'fault_confirmed', visit_date: '2026-08-20' }))).toBe(false)
    expect(
      isWorkOrderComplete(findings({ outcome: 'fault_confirmed', visit_date: '2026-08-20', technician: 'A' })),
    ).toBe(true)
  })

  it('tolerates a corrupt localStorage entry', () => {
    localStorage.setItem(workOrderStorageKey('S-bad'), '{not json')
    expect(() => workOrderRecord('S-bad')).not.toThrow()
  })
})

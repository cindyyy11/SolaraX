import { beforeEach, describe, expect, it } from 'vitest'
import { buildEvidencePackage, buildFleetReportSummary } from './reportsEngine'
import { fixtureDispatch, fixtureSite } from './testFixtures'
import { syncWorkOrderRecord } from './workOrderRecords'

const emptyFindings = {
  assignee: '', outcome: '' as const, note: '', recovered_kwh: '', technician: '',
  visit_date: '', time_in: '', time_out: '', check_status: {}, check_notes: {},
  photos_captured: {}, saved_at: null,
}

beforeEach(() => syncWorkOrderRecord('S-1', emptyFindings))

describe('evidence package', () => {
  it('includes every documented section', () => {
    const site = fixtureSite({ site_id: 'S-1', status: 'dispatch', economics: { kwh_lost_monthly: 100, rm_at_risk_monthly: 200, cumulative_kwh_lost: 0, cumulative_loss_rm: 0, loss_pct_of_expected: 20, exceeds_dispatch_threshold: true, calculation: 'x', data_status: 'BUILT' } })
    const dispatch = fixtureDispatch([site])
    const pkg = buildEvidencePackage(dispatch, site)
    expect(pkg.sections.map((s) => s.id)).toEqual([
      'decision', 'calculations', 'assumptions', 'source-status', 'inspection-evidence', 'work-order', 'recovery',
    ])
  })

  it('reports the work order as incomplete until technician, date and outcome are all present', () => {
    const site = fixtureSite({ site_id: 'S-1' })
    const dispatch = fixtureDispatch([site])
    const pkg = buildEvidencePackage(dispatch, site)
    const workOrder = pkg.sections.find((s) => s.id === 'work-order')!
    expect(workOrder.lines.some((l) => l.value.includes('Not yet completed'))).toBe(true)
  })

  it('reflects a completed work order once one is synced', () => {
    syncWorkOrderRecord('S-1', { ...emptyFindings, outcome: 'fault_confirmed', visit_date: '2026-08-20', technician: 'A. Lim' })
    const site = fixtureSite({ site_id: 'S-1' })
    const dispatch = fixtureDispatch([site])
    const pkg = buildEvidencePackage(dispatch, site)
    const workOrder = pkg.sections.find((s) => s.id === 'work-order')!
    expect(workOrder.lines.find((l) => l.label === 'Technician')?.value).toBe('A. Lim')
    const recovery = pkg.sections.find((s) => s.id === 'recovery')!
    expect(recovery.lines.find((l) => l.label === 'Status')?.value).toBe('pending')
  })
})

describe('fleet report summary', () => {
  it('reads fleet_summary and meta directly, without recomputing them', () => {
    const dispatch = fixtureDispatch([fixtureSite({ site_id: 'S-1', status: 'dispatch' }), fixtureSite({ site_id: 'S-2', status: 'healthy' })])
    const summary = buildFleetReportSummary(dispatch)
    expect(summary.siteCount).toBe(2)
    expect(summary.dispatchCount).toBe(1)
    expect(summary.pipelineVersion).toBe(dispatch.meta.pipeline_version)
  })
})

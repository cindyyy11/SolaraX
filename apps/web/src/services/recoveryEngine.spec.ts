import { describe, expect, it } from 'vitest'
import { calculateRecovery } from './recoveryEngine'
import type { RecoveryInput } from '@/types/operations'

const base: RecoveryInput = { siteId:'S-1', workOrderId:'WO-1', tariffRmPerKwh:.5, interventionCostRm:600, projectedMonthlyRecoveryKwh:1000, baselinePerformanceRatio:.7, postWorkObservations:[] }

describe('recovery engine', () => {
  it('keeps incomplete work projected', () => {
    const result = calculateRecovery(base)
    expect(result.status).toBe('projected')
    expect(result.projectedRecoveryRm).toBe(500)
    expect(result.verifiedRecoveryKwh).toBeUndefined()
  })

  it('reports recovery pending without enough post-work telemetry', () => {
    const result = calculateRecovery({ ...base, completedAt:'2026-08-01', postWorkObservations:[{ date:'2026-08-02', expectedKwh:100, actualKwh:90 }] })
    expect(result.status).toBe('pending')
    expect(result.eligibleAt).toBe('2026-08-08')
  })

  it('verifies monthly recovery and payback from a valid window', () => {
    const observations = Array.from({ length:7 }, (_, index) => ({ date:`2026-08-${String(index + 2).padStart(2,'0')}`, expectedKwh:100, actualKwh:90 }))
    const result = calculateRecovery({ ...base, completedAt:'2026-08-01', postWorkObservations:observations })
    expect(result.status).toBe('verified')
    expect(result.verifiedRecoveryKwh).toBe(600)
    expect(result.verifiedRecoveryRm).toBe(300)
    expect(result.paybackMonths).toBe(2)
  })

  it('never produces negative recovery or revenue', () => {
    const observations = Array.from({ length:7 }, (_, index) => ({ date:`2026-08-${index + 2}`, expectedKwh:100, actualKwh:40 }))
    const result = calculateRecovery({ ...base, tariffRmPerKwh:-1, completedAt:'2026-08-01', postWorkObservations:observations })
    expect(result.verifiedRecoveryKwh).toBe(0)
    expect(result.verifiedRecoveryRm).toBe(0)
  })
})

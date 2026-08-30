import { describe, expect, it } from 'vitest'
import { optimizeInterventions } from './interventionOptimizer'
import type { InterventionCandidate } from '@/types/operations'

const candidates: InterventionCandidate[] = [
  { siteId:'A', siteName:'Alpha', recoverableRm:1000, confidence:.9, safetyUrgency:.4, travelEffort:.2, travelEvidenceLevel:'simulated' },
  { siteId:'B', siteName:'Beta', recoverableRm:300, confidence:.6, safetyUrgency:.2, travelEffort:.8, travelEvidenceLevel:'simulated' },
]

describe('intervention optimizer', () => {
  it('ranks explainably and respects crew capacity', () => {
    const result = optimizeInterventions(candidates, 1)
    expect(result[0]?.siteId).toBe('A')
    expect(result[0]?.decision).toBe('dispatch-now')
    expect(result[1]?.decision).toBe('monitor')
    expect(result[0]?.reasons).toHaveLength(4)
  })

  it('does not mutate candidate inputs', () => {
    const snapshot = JSON.stringify(candidates)
    optimizeInterventions(candidates, 2)
    expect(JSON.stringify(candidates)).toBe(snapshot)
  })

  it('clamps capacity and scoring inputs', () => {
    const result = optimizeInterventions([{ ...candidates[0]!, confidence:4, safetyUrgency:-2, travelEffort:3 }], -1)
    expect(result[0]?.decision).toBe('monitor')
    expect(result[0]?.score).toBeGreaterThanOrEqual(0)
    expect(result[0]?.score).toBeLessThanOrEqual(1)
  })
})

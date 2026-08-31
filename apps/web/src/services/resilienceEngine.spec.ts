import { describe, expect, it } from 'vitest'
import { cyberPhysicalScenarios, integrationReadiness, resilienceSignals } from './resilienceEngine'
import { fixtureCohort as cohort, fixtureDispatch as dispatch, fixtureSite as site } from './testFixtures'

describe('resilience engine', () => {
  it('scores generation from real fleet_summary counts', () => {
    const d = dispatch(
      [site({ site_id: 'A', status: 'dispatch' }), site({ site_id: 'B', status: 'healthy' })],
      [],
    )
    const signal = resilienceSignals(d).find((s) => s.category === 'generation')!
    expect(signal.score).toBeCloseTo(0.5)
    expect(signal.basis).toBe('measured')
  })

  it('classifies equipment exposure from hypothesis keywords', () => {
    const d = dispatch(
      [
        site({ site_id: 'A', status: 'dispatch', hypothesis: { summary: 'Inverter fault', detail: 'Combiner box breaker tripped', confidence: 0.8, checks: [] } }),
        site({ site_id: 'B', status: 'monitor', hypothesis: { summary: 'Soiling suspected', detail: 'Dust accumulation on modules', confidence: 0.6, checks: [] } }),
      ],
      [],
    )
    const signal = resilienceSignals(d).find((s) => s.category === 'equipment')!
    expect(signal.score).toBeCloseTo(0.5)
  })

  it('reports weather as not-connected when no cohort meets the minimum', () => {
    const d = dispatch([site({ site_id: 'A' })], [cohort({ meets_minimum: false, analysed_count: 1, analysed_site_ids: ['A'] })])
    const signal = resilienceSignals(d).find((s) => s.category === 'weather')!
    expect(signal.basis).toBe('not-connected')
  })

  it('flags a cohort-wide dip as a weather signal, not per-site', () => {
    const d = dispatch(
      [site({ site_id: 'A', status: 'monitor', cohort_id: 'C-1' }), site({ site_id: 'B', status: 'monitor', cohort_id: 'C-1' }), site({ site_id: 'C', status: 'healthy', cohort_id: 'C-1' })],
      [cohort({ analysed_count: 3, analysed_site_ids: ['A', 'B', 'C'], meets_minimum: true })],
    )
    const signal = resilienceSignals(d).find((s) => s.category === 'weather')!
    expect(signal.basis).toBe('inferred')
    expect(signal.score).toBeCloseTo(2 / 3)
  })

  it('never assigns a score to grid or communications without a connected source', () => {
    const d = dispatch([site({ site_id: 'A' })], [])
    const signals = resilienceSignals(d)
    for (const category of ['grid', 'communications'] as const) {
      const signal = signals.find((s) => s.category === category)!
      expect(signal.basis).toBe('not-connected')
      expect(signal.score).toBe(0)
    }
  })

  it('derives telemetry exposure from data_status and exclusion, not a guess', () => {
    const d = dispatch(
      [
        site({ site_id: 'A', data_status: 'BUILT' }),
        site({ site_id: 'B', data_status: 'SIMULATED' }),
        site({ site_id: 'C', data_status: 'BUILT', excluded_from_analysis: { excluded: true, reason: 'gap', detail: '', observed_performance_index: 0, reference_performance_index: null, threshold: 0, method: '', data_status: 'BUILT' } }),
      ],
      [],
    )
    const signal = resilienceSignals(d).find((s) => s.category === 'telemetry')!
    expect(signal.score).toBeCloseTo(2 / 3)
  })

  it('returns exactly the six documented categories', () => {
    const d = dispatch([site({ site_id: 'A' })], [])
    const categories = resilienceSignals(d).map((s) => s.category).sort()
    expect(categories).toEqual(['communications', 'equipment', 'generation', 'grid', 'telemetry', 'weather'].sort())
  })
})

describe('integration readiness', () => {
  it('reports weather as connected from the real irradiance source', () => {
    const d = dispatch([], [])
    const row = integrationReadiness(d).find((r) => r.system === 'weather')!
    expect(row.state).toBe('connected')
    expect(row.detail).toContain('NASA POWER')
  })

  it('never claims a live connection for systems this product does not integrate', () => {
    const d = dispatch([], [])
    const rows = integrationReadiness(d)
    for (const system of ['scada', 'grid', 'erp', 'security'] as const) {
      expect(rows.find((r) => r.system === system)?.state).toBe('not-connected')
    }
  })
})

describe('cyber-physical scenarios', () => {
  it('covers all four documented categories and states what each would require', () => {
    const categories = new Set(cyberPhysicalScenarios.map((s) => s.category))
    expect(categories).toEqual(new Set(['equipment-anomaly', 'telemetry-fault', 'grid-event', 'suspicious-pattern']))
    expect(cyberPhysicalScenarios.every((s) => s.wouldRequire.length > 0)).toBe(true)
  })
})

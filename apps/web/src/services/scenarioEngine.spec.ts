import { describe, expect, it } from 'vitest'
import { runScenario, scenarioById } from './scenarioEngine'
import type { Site } from '@/types/dispatch'

const site = { site_id: 'TEST', tariff_rm_per_kwh: 0.4, status: 'monitor', capacity_kwp: 100, series: { actual_vs_expected: [{ date: '2026-01-01', actual_kwh: 1000, expected_kwh: 1200, performance_index: 1 }] } } as Site

describe('scenario engine', () => {
  it('returns bounded simulated results', () => {
    const scenario = scenarioById('soiling')!
    const result = runScenario(site, scenario, { severity: 100, duration: 30 })
    expect(result.evidenceLevel).toBe('simulated')
    expect(result.generationLossKwh).toBeGreaterThanOrEqual(0)
    expect(result.rmExposure).toBeGreaterThanOrEqual(0)
    expect(result.confidence).toBeLessThanOrEqual(1)
  })

  it('clamps unsafe parameter values', () => {
    const scenario = scenarioById('storm-damage')!
    const result = runScenario(site, scenario, { severity: 500, duration: -10 })
    expect(result.generationLossKwh).toBe(8)
  })

  it('keeps grid scenarios on the grid layer', () => {
    const scenario = scenarioById('curtailment')!
    expect(runScenario(site, scenario, { severity: 50, duration: 4 }).affectedLayer).toBe('grid')
  })

  it('labels cyber-physical readiness scenarios as simulated and never attack detection', () => {
    for (const id of ['telemetry-dropout', 'suspicious-control-pattern']) {
      const scenario = scenarioById(id)!
      const result = runScenario(site, scenario, { severity: 50, duration: 2 })
      expect(result.evidenceLevel).toBe('simulated')
      expect(result.assumptions.join(' ').toLowerCase()).not.toContain('detected')
    }
  })
})

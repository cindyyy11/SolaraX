import { describe, expect, it } from 'vitest'
import { inspectionRouteFor, inspectionRoutes } from './inspectionRoutes'

describe('inspection routes', () => {
  it('covers every implemented scenario with a distinct route', () => {
    const ids = ['soiling','partial-shading','inverter-derating','string-underperformance','thermal-hotspot','storm-damage','heatwave','curtailment']
    expect(Object.keys(inspectionRoutes).sort()).toEqual(ids.sort())
    expect(new Set(ids.map((id) => inspectionRouteFor(id).label)).size).toBe(ids.length)
  })

  it('provides actionable, uniquely identified waypoints', () => {
    for (const route of Object.values(inspectionRoutes)) {
      expect(route.waypoints.length).toBeGreaterThanOrEqual(2)
      expect(new Set(route.waypoints.map((point) => point.id)).size).toBe(route.waypoints.length)
      expect(route.waypoints.every((point) => point.instruction.length > 20)).toBe(true)
    }
  })

  it('falls back to the soiling survey for an unknown scenario', () => {
    expect(inspectionRouteFor('unknown').scenarioId).toBe('soiling')
  })
})

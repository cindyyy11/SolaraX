import { describe, expect, it } from 'vitest'
import { judgeSteps } from './judgeMode'

describe('judge mode steps', () => {
  it('returns the eight documented operator-workflow steps', () => {
    expect(judgeSteps('S-1').map((step) => step.id)).toEqual([
      'divergence',
      'compare',
      'scenario',
      'inspect',
      'evidence',
      'resilience',
      'work-order',
      'recovery',
    ])
  })

  it('routes site-specific steps to the real subject site', () => {
    const steps = judgeSteps('S-1276')
    expect(steps.find((s) => s.id === 'scenario')?.path).toBe('/site/S-1276')
    expect(steps.find((s) => s.id === 'work-order')?.path).toBe('/site/S-1276/work-order')
  })

  it('falls back to the dispatch list rather than a broken link when no site is available', () => {
    const steps = judgeSteps(null)
    expect(steps.find((s) => s.id === 'scenario')?.path).toBe('/')
    expect(steps.find((s) => s.id === 'work-order')?.path).toBe('/')
  })

  it('keeps fleet-level steps off any single site', () => {
    const steps = judgeSteps('S-1276')
    expect(steps.find((s) => s.id === 'divergence')?.path).toBe('/')
    expect(steps.find((s) => s.id === 'resilience')?.path).toBe('/resilience')
  })
})

import { describe, expect, it } from 'vitest'

import { cohortCoverage, sortedTripGroups } from './api'
import type { Cohort, Site, TripGroup } from '@/types/dispatch'

function group(overrides: Partial<TripGroup>): TripGroup {
  return {
    trip_id: 'T-00',
    label: 'Test City',
    site_ids: ['S-0001'],
    site_count: 1,
    dispatched: false,
    ...overrides,
  }
}

function makeCohort(overrides: Partial<Cohort>): Cohort {
  return {
    cohort_id: 'C-00',
    label: 'Test Cohort',
    member_site_ids: ['S-0001'],
    member_count: 1,
    analysed_site_ids: ['S-0001'],
    analysed_count: 1,
    excluded_site_ids: [],
    meets_minimum: true,
    clustering_method: 'koppen_then_haversine',
    data_status: 'BUILT',
    ...overrides,
  }
}

function makeSite(overrides: Partial<Site>): Site {
  return {
    site_id: 'S-0000',
    name: 'Test Site',
    address: '1 Test Way',
    capacity_kwp: 100,
    lat: 0,
    lon: 0,
    cohort_id: 'C-00',
    tariff_rm_per_kwh: 0.5,
    source_system_id: '0000',
    status: 'healthy',
    rank: null,
    data_status: 'BUILT',
    ...overrides,
  }
}

describe('sortedTripGroups', () => {
  it('orders multi-site groups before single-site groups', () => {
    const groups = [
      group({ trip_id: 'T-01', site_count: 1 }),
      group({ trip_id: 'T-02', site_count: 5 }),
      group({ trip_id: 'T-03', site_count: 2 }),
    ]

    const sorted = sortedTripGroups(groups)

    expect(sorted.map((g) => g.trip_id)).toEqual(['T-02', 'T-03', 'T-01'])
  })

  it('does not mutate the input array', () => {
    const groups = [
      group({ trip_id: 'T-01', site_count: 1 }),
      group({ trip_id: 'T-02', site_count: 5 }),
    ]
    const original = [...groups]

    sortedTripGroups(groups)

    expect(groups).toEqual(original)
  })

  it('returns an empty array for an empty input', () => {
    expect(sortedTripGroups([])).toEqual([])
  })
})

describe('cohortCoverage', () => {
  it('reports analysed and member counts per cohort', () => {
    const cohorts = [
      makeCohort({
        cohort_id: 'C-01',
        member_count: 6,
        analysed_count: 5,
        excluded_site_ids: ['S-9999'],
      }),
    ]
    const sites = [makeSite({ site_id: 'S-9999', name: 'Excluded Site' })]

    const rows = cohortCoverage(cohorts, sites)

    expect(rows).toHaveLength(1)
    expect(rows[0]).toMatchObject({
      cohortId: 'C-01',
      memberCount: 6,
      analysedCount: 5,
      meetsMinimum: true,
    })
  })

  it('names excluded sites and their reason from excluded_from_analysis', () => {
    const cohorts = [makeCohort({ excluded_site_ids: ['S-9999'] })]
    const sites = [
      makeSite({
        site_id: 'S-9999',
        name: 'Henderson NV 6',
        excluded_from_analysis: {
          excluded: true,
          reason: 'Insufficient telemetry coverage',
          detail: 'Fewer than the minimum required days of generation data.',
          observed_performance_index: 1.11,
          reference_performance_index: 3.83,
          threshold: 0.5,
          method: 'coverage_ratio',
          data_status: 'BUILT',
        },
      }),
    ]

    const rows = cohortCoverage(cohorts, sites)

    expect(rows[0]!.excludedSites).toEqual([
      { siteId: 'S-9999', name: 'Henderson NV 6', reason: 'Insufficient telemetry coverage' },
    ])
  })

  it('falls back to a generic reason when a site carries no excluded_from_analysis detail', () => {
    const cohorts = [makeCohort({ excluded_site_ids: ['S-9999'] })]
    const sites = [makeSite({ site_id: 'S-9999', name: 'Untracked Site' })]

    const rows = cohortCoverage(cohorts, sites)

    expect(rows[0]!.excludedSites[0]!.reason).toBe('Excluded from peer analysis')
  })

  it('returns an empty excludedSites array when a cohort excludes nobody', () => {
    const cohorts = [makeCohort({ excluded_site_ids: [] })]

    const rows = cohortCoverage(cohorts, [])

    expect(rows[0]!.excludedSites).toEqual([])
  })
})

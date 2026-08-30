import { describe, expect, it } from 'vitest'

import { sortedTripGroups } from './api'
import type { TripGroup } from '@/types/dispatch'

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

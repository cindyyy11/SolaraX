/**
 * Shared, minimal Dispatch/Site/Cohort builders for tests. Not a spec file
 * itself — imported by the specs that need a schema-valid fixture instead
 * of each hand-rolling its own subset of docs/Schema.md.
 */
import type { Cohort, Dispatch, Site } from '@/types/dispatch'

export function fixtureSite(overrides: Partial<Site> = {}): Site {
  return {
    site_id: 'S-1',
    name: 'Test site',
    address: '',
    capacity_kwp: 100,
    lat: 0,
    lon: 0,
    cohort_id: 'C-1',
    tariff_rm_per_kwh: 0.44,
    source_system_id: 'sys-1',
    status: 'healthy',
    rank: null,
    data_status: 'BUILT',
    ...overrides,
  }
}

export function fixtureCohort(overrides: Partial<Cohort> = {}): Cohort {
  return {
    cohort_id: 'C-1',
    label: 'Cohort one',
    member_site_ids: [],
    member_count: 0,
    analysed_site_ids: [],
    analysed_count: 0,
    excluded_site_ids: [],
    meets_minimum: true,
    clustering_method: 'koppen-then-linkage',
    data_status: 'BUILT',
    ...overrides,
  }
}

export function fixtureDispatch(sites: Site[], cohorts: Cohort[] = []): Dispatch {
  const dispatchCount = sites.filter((s) => s.status === 'dispatch').length
  const monitorCount = sites.filter((s) => s.status === 'monitor').length
  return {
    meta: {
      schema_version: '1.6.0',
      generated_at: '2026-08-30T00:00:00Z',
      pipeline_version: '0.5.0',
      reporting_month: '2026-08',
      reporting_month_label: 'August 2026',
      data_status: 'BUILT',
      data_source: 'PVDAQ',
      irradiance_source: 'NASA POWER',
      source_note: '',
      date_remapped: false,
    },
    assumptions: {
      tariff_rm_per_kwh: 0.44,
      assumed_yield_kwh_per_kwp_day: 3.5,
      cost_per_visit_rm: 500,
      dispatch_threshold_rm_per_month: 1500,
      min_cohort_size: 3,
      baseline_visit_frequency_per_year: 4,
      tier: 'tier-2',
    },
    fleet_summary: {
      site_count: sites.length,
      total_capacity_mwp: 1,
      dispatch_count: dispatchCount,
      monitor_count: monitorCount,
      healthy_count: sites.length - dispatchCount - monitorCount,
      visits_avoided: 0,
      trips_avoided: 0,
      trips_recommended: dispatchCount,
      trip_groups: [],
      estimated_saving_rm: 0,
      total_rm_at_risk: sites.reduce((sum, s) => sum + (s.economics?.rm_at_risk_monthly ?? 0), 0),
      cohort_count: cohorts.length,
    },
    roi: {
      data_status: 'BUILT',
      period_months: 1,
      visits_recommended_total: 0,
      visits_avoided_total: 0,
      generation_recovered_kwh: 0,
      faults_confirmed: 0,
      rm_protected_cumulative: 0,
    },
    cohorts,
    sites,
  }
}

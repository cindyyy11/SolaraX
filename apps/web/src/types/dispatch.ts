/**
 * Types for `dispatch.json` — the single artifact the pipeline hands the dashboard.
 *
 * These mirror docs/Schema.md and nothing else. If the schema changes, this file
 * changes with it and `meta.schema_version` gets bumped. Do not add convenience
 * fields here that the pipeline does not actually produce.
 */

export type DataStatus = 'BUILT' | 'SIMULATED' | 'PLACEHOLDER'
export type SiteStatus = 'dispatch' | 'monitor' | 'healthy'
export type ScoreType = 'z_score' | 'isolation_forest' | 'cohort_mean_deviation' | 'other'

export interface Meta {
  schema_version: string
  generated_at: string
  pipeline_version: string
  reporting_month: string
  reporting_month_label: string
  data_status: DataStatus
  data_source: string
  irradiance_source: string
  source_note: string
  date_remapped: boolean
  date_remap_note?: string
}

export interface Assumptions {
  tariff_rm_per_kwh: number
  assumed_yield_kwh_per_kwp_day: number
  cost_per_visit_rm: number
  dispatch_threshold_rm_per_month: number
  min_cohort_size: number
  baseline_visit_frequency_per_year: number
  tariff_rm_per_kwh_range?: { low: number; high: number }
  cost_per_visit_rm_range?: { low: number; high: number }
  co2e_grid_factor_kg_per_kwh?: number
  tier: string
  notes?: Record<string, string>
}

export interface FleetSummary {
  site_count: number
  total_capacity_mwp: number
  dispatch_count: number
  monitor_count: number
  healthy_count: number
  visits_avoided: number
  estimated_saving_rm: number
  total_rm_at_risk: number
  cohort_count: number
}

export interface Roi {
  data_status: DataStatus
  period_months: number
  visits_recommended_total: number
  visits_avoided_total: number
  faults_confirmed: number
  generation_recovered_kwh: number
  rm_protected_cumulative: number
  co2e_avoided_tonnes?: number
  co2e_grid_factor_kg_per_kwh?: number
  co2e_factor_source?: string
}

export interface Cohort {
  cohort_id: string
  label: string
  member_site_ids: string[]
  member_count: number
  /** Members whose data is trusted. `meets_minimum` is judged on this, not member_count. */
  analysed_site_ids: string[]
  analysed_count: number
  excluded_site_ids: string[]
  meets_minimum: boolean
  clustering_method: string
  centroid?: { lat: number; lon: number }
  cohort_median_performance_index?: number
  data_status: DataStatus
}

export interface Detection {
  method: string
  score: number
  score_type: ScoreType
  threshold: number
  confidence: number
  cohort_size: number
  cohort_meets_minimum: boolean
  data_status: DataStatus
}

export interface Divergence {
  start_date: string
  days_since: number
  detection_confidence?: string
}

export interface Economics {
  kwh_lost_monthly: number
  rm_at_risk_monthly: number
  cumulative_kwh_lost: number
  cumulative_loss_rm: number
  loss_pct_of_expected: number
  exceeds_dispatch_threshold: boolean
  calculation: string
  data_status: DataStatus
}

export interface Hypothesis {
  summary: string
  detail: string
  confidence: number
  checks: string[]
  photograph?: string[]
}

/** One row per site per day. `expected_kwh` is null until M2 (owner A) lands. */
export interface ActualVsExpectedRow {
  date: string
  actual_kwh: number
  expected_kwh: number | null
  performance_index: number
}

/**
 * Long format, one row per peer per day — never wide.
 * `performance_index` is kWh per kWp, so sites of any size share one axis.
 */
export interface CohortSeriesRow {
  date: string
  site_id: string
  performance_index: number
  is_subject: boolean
}

export interface Series {
  actual_vs_expected: ActualVsExpectedRow[]
  cohort: CohortSeriesRow[]
}

export interface Evidence {
  has_imagery: boolean
  defect_class?: string
  confidence?: number
  image_url?: string
  captured_date?: string
  model_note?: string
  inference_mode?: 'batch' | 'live'
  data_status: DataStatus
}

/**
 * One inverter compared against its siblings. Deliberately carries raw kWh and a
 * ratio rather than `performance_index` — PVDAQ publishes no per-inverter
 * capacity, so there is no honest kWp denominator at this level.
 */
/**
 * Operating temperature for one inverter. `delta_t_ambient_c` is null wherever
 * the system publishes no ambient channel, or where the ambient sensor is
 * demonstrably faulty — several systems have both problems.
 */
export interface UnitThermal {
  mean_temp_c: number
  max_temp_c: number
  delta_t_siblings_c: number
  mean_ambient_c: number | null
  delta_t_ambient_c: number | null
  days: number
}

export interface SubSiteUnit {
  unit_id: string
  mean_kwh_daily: number
  sibling_median_kwh_daily: number
  deviation_pct: number
  status: 'flagged' | 'normal'
  thermal: UnitThermal | null
  series: Array<{ date: string; kwh: number; ratio_to_sibling_median: number }>
}

export interface SubSite {
  unit_type: string
  unit_count: number
  /**
   * False when the site's inverters are different hardware. Comparing raw kWh
   * between a 100 kW unit and a 50 kW one produces a deviation that is nameplate,
   * not performance — so nothing is flagged and percentages are reference only.
   */
  units_comparable: boolean
  comparability_note: string | null
  has_thermal: boolean
  thermal_basis: string | null
  comparison_basis: string
  method: string
  flag_threshold_pct: number
  units: SubSiteUnit[]
  data_status: DataStatus
}

/**
 * Present only when a site's telemetry is too incomplete to analyse. Such a site
 * is forced healthy, never ranked, and never drawn as a cohort peer — a
 * permanently depressed reading would otherwise produce a false dispatch AND
 * drag its neighbours' baseline down.
 */
export interface ExcludedFromAnalysis {
  excluded: boolean
  reason: string
  detail: string
  observed_performance_index: number
  reference_performance_index: number | null
  threshold: number
  method: string
  data_status: DataStatus
}

export interface Site {
  site_id: string
  name: string
  address: string
  capacity_kwp: number
  lat: number
  lon: number
  cohort_id: string | null
  tariff_rm_per_kwh: number
  source_system_id: string
  status: SiteStatus
  rank: number | null
  data_status: DataStatus
  detection?: Detection | null
  divergence?: Divergence | null
  economics?: Economics | null
  hypothesis?: Hypothesis | null
  series?: Series
  sub_site?: SubSite
  evidence?: Evidence
  excluded_from_analysis?: ExcludedFromAnalysis | null
}

export interface Dispatch {
  meta: Meta
  assumptions: Assumptions
  fleet_summary: FleetSummary
  roi: Roi
  cohorts: Cohort[]
  sites: Site[]
}

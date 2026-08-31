/**
 * Builds a readable evidence package from state this product already has —
 * the decision, its calculations, its assumptions, every source's own
 * data_status, inspection evidence, the work order and recovery status.
 * Nothing here is a new claim; every field traces to a field already shown
 * somewhere else in the product.
 *
 * docs/superpowers/specs/2026-08-30-solarax-closed-loop-operations-intelligence-design.md
 * — "Reports export a readable evidence package..."
 */
import type { Dispatch, Site } from '@/types/dispatch'
import { calculateRecovery } from './recoveryEngine'
import { isWorkOrderComplete, workOrderRecord, type WorkOrderFindings } from './workOrderRecords'

export interface EvidencePackageLine {
  label: string
  value: string
  dataStatus?: 'BUILT' | 'SIMULATED' | 'PLACEHOLDER' | 'not-applicable'
}

export interface EvidencePackageSection {
  id: string
  title: string
  lines: EvidencePackageLine[]
}

export interface EvidencePackage {
  siteId: string
  siteName: string
  generatedAt: string
  reportingMonth: string
  sections: EvidencePackageSection[]
}

function decisionSection(dispatch: Dispatch, site: Site): EvidencePackageSection {
  return {
    id: 'decision',
    title: 'Decision',
    lines: [
      { label: 'Status', value: site.status },
      { label: 'Rank', value: site.rank ? `${site.rank} of ${dispatch.fleet_summary.site_count}` : 'Not ranked' },
      { label: 'Money at risk', value: site.economics ? `RM ${Math.round(site.economics.rm_at_risk_monthly).toLocaleString()}/month` : 'No economic exposure computed', dataStatus: site.economics?.data_status ?? 'not-applicable' },
      { label: 'Reporting month', value: dispatch.meta.reporting_month_label },
    ],
  }
}

function calculationsSection(site: Site): EvidencePackageSection {
  const lines: EvidencePackageLine[] = []
  if (site.detection) {
    lines.push(
      { label: 'Detection method', value: site.detection.method, dataStatus: site.detection.data_status },
      { label: 'Score vs threshold', value: `${site.detection.score.toFixed(2)} vs ${site.detection.threshold.toFixed(2)}`, dataStatus: site.detection.data_status },
      { label: 'Cohort size', value: `${site.detection.cohort_size}${site.detection.cohort_meets_minimum ? '' : ' (below minimum)'}` },
      { label: 'Detector confidence', value: `${Math.round(site.detection.confidence * 100)}%` },
    )
  }
  if (site.economics) {
    lines.push(
      { label: 'kWh lost / month', value: site.economics.kwh_lost_monthly.toLocaleString(), dataStatus: site.economics.data_status },
      { label: 'Loss vs expected', value: `${site.economics.loss_pct_of_expected.toFixed(1)}%` },
      { label: 'Calculation', value: site.economics.calculation },
    )
  }
  if (!lines.length) lines.push({ label: 'Calculations', value: 'No detection or economics were computed for this site this month.' })
  return { id: 'calculations', title: 'Calculations', lines }
}

function assumptionsSection(dispatch: Dispatch, site: Site): EvidencePackageSection {
  const a = dispatch.assumptions
  return {
    id: 'assumptions',
    title: 'Assumptions',
    lines: [
      { label: 'Tariff', value: `RM ${site.tariff_rm_per_kwh.toFixed(4)}/kWh`, dataStatus: 'BUILT' },
      { label: 'Cost per visit', value: `RM ${a.cost_per_visit_rm.toLocaleString()}` },
      { label: 'Dispatch threshold', value: `RM ${a.dispatch_threshold_rm_per_month.toLocaleString()}/month` },
      { label: 'Minimum cohort size', value: `${a.min_cohort_size}` },
      { label: 'Assumption tier', value: a.tier },
    ],
  }
}

function sourceStatusSection(dispatch: Dispatch, site: Site): EvidencePackageSection {
  return {
    id: 'source-status',
    title: 'Source status',
    lines: [
      { label: 'Site data status', value: site.data_status, dataStatus: site.data_status },
      { label: 'Excluded from analysis', value: site.excluded_from_analysis?.excluded ? `Yes — ${site.excluded_from_analysis.reason}` : 'No' },
      { label: 'Irradiance source', value: dispatch.meta.irradiance_source },
      { label: 'Pipeline version', value: dispatch.meta.pipeline_version },
      { label: 'Artifact generated', value: dispatch.meta.generated_at },
    ],
  }
}

function inspectionEvidenceSection(site: Site): EvidencePackageSection {
  const lines: EvidencePackageLine[] = []
  if (site.hypothesis) {
    lines.push(
      { label: 'Hypothesis', value: site.hypothesis.summary },
      { label: 'Hypothesis confidence', value: `${Math.round(site.hypothesis.confidence * 100)}%` },
    )
  }
  if (site.evidence?.has_imagery) {
    lines.push(
      { label: 'Visual evidence', value: site.evidence.defect_class ?? 'Captured, unclassified', dataStatus: site.evidence.data_status },
      { label: 'Evidence confidence', value: site.evidence.confidence !== undefined ? `${Math.round(site.evidence.confidence * 100)}%` : 'Not supplied' },
    )
  }
  if (!lines.length) lines.push({ label: 'Inspection evidence', value: 'No hypothesis or imagery is available for this site.' })
  return { id: 'inspection-evidence', title: 'Inspection evidence', lines }
}

function workOrderSection(findings: WorkOrderFindings, dispatch: Dispatch, site: Site): EvidencePackageSection {
  const complete = isWorkOrderComplete(findings)
  const workOrderId = `WO-${site.site_id}-${dispatch.meta.reporting_month}`
  const lines: EvidencePackageLine[] = [{ label: 'Work order', value: workOrderId }]
  if (complete) {
    lines.push(
      { label: 'Technician', value: findings.technician },
      { label: 'Visit date', value: findings.visit_date },
      { label: 'Outcome', value: findings.outcome.replace(/_/g, ' ') },
      { label: 'Recovered generation (reported)', value: findings.recovered_kwh ? `${findings.recovered_kwh} kWh/month (technician estimate)` : 'Not recorded' },
    )
  } else {
    lines.push({ label: 'Status', value: 'Not yet completed — no technician, visit date and outcome recorded.' })
  }
  return { id: 'work-order', title: 'Work order', lines }
}

function recoverySection(site: Site, findings: WorkOrderFindings): EvidencePackageSection {
  const recovery = calculateRecovery({
    siteId: site.site_id,
    workOrderId: `WO-${site.site_id}`,
    tariffRmPerKwh: site.tariff_rm_per_kwh,
    interventionCostRm: 0,
    projectedMonthlyRecoveryKwh: site.economics?.kwh_lost_monthly ?? 0,
    baselinePerformanceRatio: Math.max(0, 1 - (site.economics?.loss_pct_of_expected ?? 0) / 100),
    postWorkObservations: [],
    completedAt: isWorkOrderComplete(findings) ? findings.visit_date : undefined,
  })
  return {
    id: 'recovery',
    title: 'Recovery status',
    lines: [
      { label: 'Status', value: recovery.status },
      { label: 'Projected recovery', value: `RM ${recovery.projectedRecoveryRm.toLocaleString()}/month` },
      ...(recovery.verifiedRecoveryRm !== undefined ? [{ label: 'Verified recovery', value: `RM ${recovery.verifiedRecoveryRm.toLocaleString()}/month` }] : []),
      { label: 'Explanation', value: recovery.explanation },
    ],
  }
}

/** One site's full evidence package — every section pulled from state that
 * already exists elsewhere in the product, never recomputed differently. */
export function buildEvidencePackage(dispatch: Dispatch, site: Site): EvidencePackage {
  const findings = workOrderRecord(site.site_id)
  return {
    siteId: site.site_id,
    siteName: site.name,
    generatedAt: new Date().toISOString(),
    reportingMonth: dispatch.meta.reporting_month_label,
    sections: [
      decisionSection(dispatch, site),
      calculationsSection(site),
      assumptionsSection(dispatch, site),
      sourceStatusSection(dispatch, site),
      inspectionEvidenceSection(site),
      workOrderSection(findings, dispatch, site),
      recoverySection(site, findings),
    ],
  }
}

export interface FleetReportSummary {
  reportingMonth: string
  siteCount: number
  dispatchCount: number
  monitorCount: number
  healthyCount: number
  totalRmAtRisk: number
  tripsRecommended: number
  tripsAvoided: number
  estimatedSavingRm: number
  dataStatus: string
  pipelineVersion: string
}

/** The fleet-level figures a management or judging package opens with —
 * read straight from fleet_summary and roi, never recomputed. */
export function buildFleetReportSummary(dispatch: Dispatch): FleetReportSummary {
  return {
    reportingMonth: dispatch.meta.reporting_month_label,
    siteCount: dispatch.fleet_summary.site_count,
    dispatchCount: dispatch.fleet_summary.dispatch_count,
    monitorCount: dispatch.fleet_summary.monitor_count,
    healthyCount: dispatch.fleet_summary.healthy_count,
    totalRmAtRisk: dispatch.fleet_summary.total_rm_at_risk,
    tripsRecommended: dispatch.fleet_summary.trips_recommended,
    tripsAvoided: dispatch.fleet_summary.trips_avoided,
    estimatedSavingRm: dispatch.fleet_summary.estimated_saving_rm,
    dataStatus: dispatch.meta.data_status,
    pipelineVersion: dispatch.meta.pipeline_version,
  }
}

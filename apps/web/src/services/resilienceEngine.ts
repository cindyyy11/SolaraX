/**
 * Fleet-wide resilience summary — six categories, each explainable from a
 * named signal in `dispatch.json` or from a declared "not connected" state.
 * No category is ever assigned a score without a real signal behind it; see
 * the design spec's data-boundaries section:
 * docs/superpowers/specs/2026-08-30-solarax-closed-loop-operations-intelligence-design.md
 */
import type { Dispatch } from '@/types/dispatch'
import type {
  CyberPhysicalScenario,
  IntegrationReadiness,
  ResilienceSignal,
  ResilienceStatus,
} from '@/types/operations'
import { isVisionApiConfigured } from './api'

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value))

function statusFor(score: number): ResilienceStatus {
  if (score >= 0.6) return 'exposed'
  if (score >= 0.3) return 'watch'
  return 'nominal'
}

const ELECTRICAL_TERMS = ['inverter', 'string', 'breaker', 'combiner', 'fuse', 'wiring', 'connector', 'isolator']

function mentionsElectrical(hypothesis: { summary: string; detail: string } | null | undefined): boolean {
  if (!hypothesis) return false
  const corpus = `${hypothesis.summary} ${hypothesis.detail}`.toLowerCase()
  return ELECTRICAL_TERMS.some((term) => corpus.includes(term))
}

function generationSignal(dispatch: Dispatch): ResilienceSignal {
  const { site_count, dispatch_count, monitor_count, total_rm_at_risk } = dispatch.fleet_summary
  const flagged = dispatch_count + monitor_count
  const score = clamp(site_count ? flagged / site_count : 0)
  return {
    category: 'generation',
    label: 'Generation',
    basis: 'measured',
    score,
    status: statusFor(score),
    headline: `${flagged} of ${site_count} sites flagged this month`,
    explanation: `${Math.round(score * 100)}% of the fleet is carrying a dispatch or monitor status, representing RM ${Math.round(total_rm_at_risk).toLocaleString()} at risk.`,
    contributingSignals: [
      `${dispatch_count} dispatch`,
      `${monitor_count} monitor`,
      `RM ${Math.round(total_rm_at_risk).toLocaleString()}/month at risk`,
    ],
  }
}

function equipmentSignal(dispatch: Dispatch): ResilienceSignal {
  const flaggedSites = dispatch.sites.filter((site) => site.status !== 'healthy' && site.hypothesis)
  const electrical = flaggedSites.filter((site) => mentionsElectrical(site.hypothesis))
  const score = clamp(flaggedSites.length ? electrical.length / flaggedSites.length : 0)
  return {
    category: 'equipment',
    label: 'Equipment',
    basis: 'measured',
    score,
    status: statusFor(score),
    headline: `${electrical.length} of ${flaggedSites.length} flagged hypotheses are electrical`,
    explanation: flaggedSites.length
      ? `${Math.round(score * 100)}% of flagged sites carry an electrical hypothesis (inverter, string, breaker or connector), classified from the same keyword method Screen 3 uses to route verification.`
      : 'No sites currently carry a hypothesis to classify.',
    contributingSignals: [`${electrical.length} electrical`, `${flaggedSites.length - electrical.length} module-level or other`],
  }
}

function weatherSignal(dispatch: Dispatch): ResilienceSignal {
  const eligible = dispatch.cohorts.filter((cohort) => cohort.meets_minimum && cohort.analysed_count > 0)
  const fractions = eligible.map((cohort) => {
    const flagged = cohort.analysed_site_ids.filter((id) => {
      const site = dispatch.sites.find((item) => item.site_id === id)
      return site && site.status !== 'healthy'
    }).length
    return { cohort, fraction: flagged / cohort.analysed_count, flagged }
  })
  const worst = fractions.reduce((max, item) => (item.fraction > max.fraction ? item : max), { cohort: undefined as (typeof fractions)[number]['cohort'] | undefined, fraction: 0, flagged: 0 })
  const score = clamp(worst.fraction)
  return {
    category: 'weather',
    label: 'Weather',
    basis: eligible.length ? 'inferred' : 'not-connected',
    score,
    status: eligible.length ? statusFor(score) : 'not-connected',
    headline: worst.cohort ? `${worst.cohort.label}: ${worst.flagged} of ${worst.cohort.analysed_count} members flagged together` : 'No cohort meets the minimum peer count',
    explanation: eligible.length
      ? `A high fraction of a cohort flagged at once points to a shared weather or environmental cause rather than a single-site fault — the same read behind Module 3's peer benchmarking. This is an inference from correlated status, not a weather forecast or sensor reading.`
      : 'No cohort currently meets the minimum peer count needed to distinguish a shared cause from a single-site one.',
    contributingSignals: fractions.map((item) => `${item.cohort.label}: ${item.flagged}/${item.cohort.analysed_count}`),
  }
}

function telemetrySignal(dispatch: Dispatch): ResilienceSignal {
  const total = dispatch.sites.length
  const excluded = dispatch.sites.filter((site) => site.excluded_from_analysis?.excluded).length
  const notBuilt = dispatch.sites.filter((site) => site.data_status !== 'BUILT').length
  const gapCount = new Set([...dispatch.sites.filter((s) => s.excluded_from_analysis?.excluded), ...dispatch.sites.filter((s) => s.data_status !== 'BUILT')].map((s) => s.site_id)).size
  const score = clamp(total ? gapCount / total : 0)
  return {
    category: 'telemetry',
    label: 'Telemetry',
    basis: 'measured',
    score,
    status: statusFor(score),
    headline: `${total - gapCount} of ${total} sites on fully built telemetry`,
    explanation: `${excluded} site${excluded === 1 ? '' : 's'} excluded from peer analysis for incomplete data, and ${notBuilt} carr${notBuilt === 1 ? 'ies' : 'y'} a non-BUILT data status. Both are read directly from each site's own data_status and exclusion fields, never estimated.`,
    contributingSignals: [`${excluded} excluded from analysis`, `${notBuilt} non-BUILT data status`],
  }
}

function notConnectedSignal(category: 'grid' | 'communications', label: string, explanation: string): ResilienceSignal {
  return {
    category,
    label,
    basis: 'not-connected',
    score: 0,
    status: 'not-connected',
    headline: 'No live integration',
    explanation,
    contributingSignals: [],
  }
}

/** The six resilience categories, in the order the design spec lists them. */
export function resilienceSignals(dispatch: Dispatch): ResilienceSignal[] {
  return [
    generationSignal(dispatch),
    equipmentSignal(dispatch),
    weatherSignal(dispatch),
    notConnectedSignal('grid', 'Grid', 'No grid-side telemetry (curtailment, frequency events, outage signals) is connected. Grid Curtailment in the Scenario Lab remains a bounded, labelled simulation.'),
    telemetrySignal(dispatch),
    notConnectedSignal('communications', 'Communications', 'No live SCADA or gateway communications link is connected. Uptime and dropout state shown elsewhere in this product are derived from data_status, not from a communications channel.'),
  ]
}

/** Which back-office and field systems this product could integrate with,
 * and what state that integration is actually in today. Never claims a live
 * connection that does not exist. */
export function integrationReadiness(dispatch: Dispatch): IntegrationReadiness[] {
  const droneConnected = isVisionApiConfigured()
  return [
    {
      system: 'weather',
      label: 'Weather / irradiance',
      state: 'connected',
      detail: `Sensor-free baseline runs on ${dispatch.meta.irradiance_source}, refreshed on each pipeline run.`,
      expectedContract: 'Hourly irradiance and ambient temperature, per site coordinate.',
    },
    {
      system: 'drone',
      label: 'Drone / visual verification',
      state: droneConnected ? 'connected' : 'not-connected',
      detail: droneConnected
        ? 'A vision service endpoint is configured; uploaded imagery returns a defect classification.'
        : 'No vision service endpoint is configured for this deployment. The evidence panel stays hidden rather than posting to an unreachable address.',
      expectedContract: 'Image upload returning defect class, confidence and evidence metadata (Module 5).',
    },
    {
      system: 'cmms',
      label: 'CMMS / work-order system',
      state: 'partial',
      detail: 'Work orders are generated and technician findings are saved in this browser only. No external CMMS (e.g. Maximo, UpKeep) is connected yet.',
      expectedContract: 'Work-order create/update/complete API keyed by site_id and a stable work-order id.',
    },
    {
      system: 'scada',
      label: 'SCADA / inverter telemetry',
      state: 'not-connected',
      detail: 'This product reads PVDAQ batch exports, not a live SCADA feed. No OPC-UA or Modbus bridge is connected.',
      expectedContract: 'Streamed or polled inverter and combiner-box status at sub-hourly resolution.',
    },
    {
      system: 'grid',
      label: 'Grid operator / DER management',
      state: 'not-connected',
      detail: 'No grid-side curtailment, frequency or outage signal is connected. Curtailment scenarios stay simulated.',
      expectedContract: 'Curtailment instructions and grid-event notifications for the fleet\'s interconnection points.',
    },
    {
      system: 'erp',
      label: 'ERP / finance',
      state: 'not-connected',
      detail: 'RM figures are computed in this product and are not posted to or read from a finance system.',
      expectedContract: 'Cost-centre-tagged posting of avoided-visit savings and confirmed intervention cost.',
    },
    {
      system: 'security',
      label: 'Security / anomaly telemetry',
      state: 'not-connected',
      detail: 'No intrusion-detection or control-system security feed is connected. Cyber-physical scenarios below are illustrative only.',
      expectedContract: 'Signed telemetry-integrity events and control-command audit log.',
    },
  ]
}

/** Illustrative examples only — every entry states what real telemetry it
 * would need to become a genuine detection rather than a labelled scenario. */
export const cyberPhysicalScenarios: CyberPhysicalScenario[] = [
  {
    id: 'inverter-firmware-drift',
    category: 'equipment-anomaly',
    categoryLabel: 'Likely equipment anomaly',
    title: 'Inverter output cap without an alarm',
    description: 'An inverter derates and stays derated with no fault code raised — consistent with the Inverter Derating scenario already in the Scenario Lab.',
    wouldRequire: 'Inverter firmware/fault-code telemetry to distinguish a silent derate from a genuine sensor gap.',
  },
  {
    id: 'combiner-ground-fault',
    category: 'equipment-anomaly',
    categoryLabel: 'Likely equipment anomaly',
    title: 'Recurring ground-fault interrupt pattern',
    description: 'A combiner box trips on a regular cadence rather than a single event — a pattern consistent with a developing fault, not a one-off.',
    wouldRequire: 'Combiner-box event logs with timestamps, not just a present/absent status.',
  },
  {
    id: 'stale-channel',
    category: 'telemetry-fault',
    categoryLabel: 'Sensor or telemetry fault',
    title: 'A channel stops updating but keeps reporting the last value',
    description: 'PVDAQ carries exactly this failure mode today — S-1276 reported 0.00 kWh for all of January 2019 rather than a gap. See docs/PROGRESS.md, 30 Aug entry.',
    wouldRequire: 'A liveness heartbeat separate from the value itself, so a stuck sensor is distinguishable from a genuinely idle one.',
  },
  {
    id: 'ambient-sensor-fault',
    category: 'telemetry-fault',
    categoryLabel: 'Sensor or telemetry fault',
    title: 'Ambient temperature channel reads outside a physical range',
    description: 'Several PVDAQ systems already publish no usable ambient channel — Screen 2\'s thermal comparison renders "—" rather than inventing a value.',
    wouldRequire: 'Per-channel range validation at ingestion, upstream of this dashboard.',
  },
  {
    id: 'curtailment-event',
    category: 'grid-event',
    categoryLabel: 'Grid-side event',
    title: 'Output drop matching a grid curtailment instruction',
    description: 'Generation falls fleet-wide in a way that does not match weather or equipment signatures — the Grid Curtailment scenario models this shape.',
    wouldRequire: 'A grid-operator curtailment feed to confirm the instruction actually occurred.',
  },
  {
    id: 'frequency-ride-through',
    category: 'grid-event',
    categoryLabel: 'Grid-side event',
    title: 'Repeated frequency ride-through disconnects',
    description: 'An inverter repeatedly disconnects and reconnects around a grid frequency excursion rather than a local fault.',
    wouldRequire: 'Point-of-interconnection frequency and inverter ride-through event logs.',
  },
  {
    id: 'setpoint-mismatch',
    category: 'suspicious-pattern',
    categoryLabel: 'Suspicious control or data pattern',
    title: 'A commanded setpoint does not match the reported state',
    description: 'The value a control system believes it sent and the value a device reports differ — a pattern a compromised or misconfigured controller and a stale telemetry link both produce.',
    wouldRequire: 'Paired command-and-acknowledgement logs from the control layer, not just device-reported state.',
  },
  {
    id: 'off-hours-write',
    category: 'suspicious-pattern',
    categoryLabel: 'Suspicious control or data pattern',
    title: 'A configuration write outside scheduled maintenance windows',
    description: 'A parameter change lands with no matching work order or maintenance window — worth a human look, not an automatic verdict.',
    wouldRequire: 'A configuration-change audit trail correlated against this product\'s own work-order records.',
  },
]

import type { EvidenceLevel } from './scenario'

export type EvidenceEventType = 'divergence' | 'scenario' | 'drone' | 'cv' | 'operator-decision' | 'work-order' | 'recovery'
export type EvidenceEventStatus = 'observed' | 'simulated' | 'pending' | 'confirmed' | 'conflicting'
export type RecoveryStatus = 'pending' | 'projected' | 'verified'

export interface EvidenceEvent {
  id: string
  siteId: string
  type: EvidenceEventType
  timestamp: string
  title: string
  detail: string
  evidenceLevel: EvidenceLevel
  confidence?: number
  status: EvidenceEventStatus
  sourceRef: string
}

export interface RecoveryObservation {
  date: string
  expectedKwh: number
  actualKwh: number
}

export interface RecoveryInput {
  siteId: string
  workOrderId: string
  completedAt?: string
  tariffRmPerKwh: number
  interventionCostRm: number
  projectedMonthlyRecoveryKwh: number
  baselinePerformanceRatio: number
  postWorkObservations: RecoveryObservation[]
  minimumObservationDays?: number
}

export interface RecoveryResult {
  siteId: string
  workOrderId: string
  status: RecoveryStatus
  projectedRecoveryKwh: number
  verifiedRecoveryKwh?: number
  projectedRecoveryRm: number
  verifiedRecoveryRm?: number
  paybackMonths?: number
  confidence: number
  observationDays: number
  minimumObservationDays: number
  eligibleAt?: string
  explanation: string
}

export type ResilienceCategory = 'generation' | 'equipment' | 'weather' | 'grid' | 'telemetry' | 'communications'
export type ResilienceStatus = 'nominal' | 'watch' | 'exposed' | 'not-connected'
export type ResilienceBasis = 'measured' | 'inferred' | 'not-connected'

/** One resilience category's summary. `score` is only meaningful when
 * `basis` is not `'not-connected'` — a category with no source telemetry
 * reports its connection state, never a fabricated exposure number. */
export interface ResilienceSignal {
  category: ResilienceCategory
  label: string
  status: ResilienceStatus
  basis: ResilienceBasis
  score: number
  headline: string
  explanation: string
  contributingSignals: string[]
}

export type IntegrationSystem = 'scada' | 'cmms' | 'weather' | 'drone' | 'erp' | 'grid' | 'security'
export type IntegrationState = 'connected' | 'partial' | 'not-connected'

export interface IntegrationReadiness {
  system: IntegrationSystem
  label: string
  state: IntegrationState
  detail: string
  expectedContract: string
}

export type CyberPhysicalCategory = 'equipment-anomaly' | 'telemetry-fault' | 'grid-event' | 'suspicious-pattern'

/** A named example within a cyber-physical category — always simulated.
 * There is no live security telemetry in this product; see CLAUDE.md's
 * anti-goal list and the closed-loop design spec's data boundaries. */
export interface CyberPhysicalScenario {
  id: string
  category: CyberPhysicalCategory
  categoryLabel: string
  title: string
  description: string
  wouldRequire: string
}

export interface InterventionCandidate {
  siteId: string
  siteName: string
  recoverableRm: number
  confidence: number
  safetyUrgency: number
  travelEffort: number
  travelEvidenceLevel: EvidenceLevel
}

/** The score's four weighted inputs, each already expressed as points out of
 * its own share of 100 — sums to `score * 100`. Exists so a caller can draw
 * the composition as a stacked bar instead of only reading it as prose. */
export interface InterventionContributions {
  value: number
  confidence: number
  safety: number
  effort: number
}

export interface InterventionRecommendation extends InterventionCandidate {
  score: number
  rank: number
  decision: 'dispatch-now' | 'monitor'
  reasons: string[]
  contributions: InterventionContributions
}

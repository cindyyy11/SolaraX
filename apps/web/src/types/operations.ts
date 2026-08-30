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

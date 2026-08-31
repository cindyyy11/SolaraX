import type { Site } from './dispatch'

export type ScenarioGroup = 'revenue' | 'inspection' | 'grid' | 'security'
export type EvidenceLevel = 'measured' | 'inferred' | 'simulated'
export type ScenarioResponse = 'monitor' | 'verify' | 'dispatch' | 'escalate'

export interface ScenarioParameter {
  id: 'severity' | 'duration'
  label: string
  min: number
  max: number
  step: number
  unit: string
  defaultValue: number
}

export interface ScenarioResult {
  generationLossKwh: number
  rmExposure: number
  confidence: number
  response: ScenarioResponse
  responseLabel: string
  evidenceLevel: EvidenceLevel
  assumptions: string[]
  affectedLayer: 'array' | 'equipment' | 'grid' | 'telemetry'
}

export interface ScenarioDefinition {
  id: string
  title: string
  group: ScenarioGroup
  description: string
  parameters: ScenarioParameter[]
  run: (site: Site, values: Record<string, number>) => ScenarioResult
}


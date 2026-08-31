import type { RecoveryInput, RecoveryResult } from '@/types/operations'

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

function eligibilityDate(completedAt: string | undefined, days: number): string | undefined {
  if (!completedAt) return undefined
  const date = new Date(completedAt)
  if (Number.isNaN(date.getTime())) return undefined
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export function calculateRecovery(input: RecoveryInput): RecoveryResult {
  const minimumObservationDays = Math.max(1, Math.round(input.minimumObservationDays ?? 7))
  const tariff = Math.max(0, input.tariffRmPerKwh)
  const projectedRecoveryKwh = Math.max(0, input.projectedMonthlyRecoveryKwh)
  const projectedRecoveryRm = Number((projectedRecoveryKwh * tariff).toFixed(2))
  const base = {
    siteId: input.siteId,
    workOrderId: input.workOrderId,
    projectedRecoveryKwh,
    projectedRecoveryRm,
    observationDays: input.postWorkObservations.length,
    minimumObservationDays,
  }

  if (!input.completedAt) return { ...base, status:'projected', confidence:.45, explanation:'Work is not marked complete. Recovery remains a projection.' }
  if (input.postWorkObservations.length < minimumObservationDays) return {
    ...base,
    status:'pending',
    confidence:.5,
    eligibleAt:eligibilityDate(input.completedAt, minimumObservationDays),
    explanation:`Recovery pending until at least ${minimumObservationDays} post-work days are available.`,
  }

  const valid = input.postWorkObservations.filter((row) => row.expectedKwh > 0 && row.actualKwh >= 0)
  if (valid.length < minimumObservationDays) return { ...base, status:'pending', confidence:.35, eligibleAt:eligibilityDate(input.completedAt, minimumObservationDays), explanation:'Recovery pending because the observation window contains insufficient valid expected-generation data.' }

  const recoveredDaily = valid.reduce((sum, row) => {
    const baselineActual = row.expectedKwh * clamp(input.baselinePerformanceRatio, 0, 1.5)
    return sum + Math.max(0, row.actualKwh - baselineActual)
  }, 0)
  const verifiedRecoveryKwh = Number((recoveredDaily * (30 / valid.length)).toFixed(2))
  const verifiedRecoveryRm = Number((verifiedRecoveryKwh * tariff).toFixed(2))
  const paybackMonths = verifiedRecoveryRm > 0 ? Number((Math.max(0, input.interventionCostRm) / verifiedRecoveryRm).toFixed(1)) : undefined
  const completeness = clamp(valid.length / Math.max(minimumObservationDays * 2, 1), 0, 1)

  return {
    ...base,
    status:'verified',
    verifiedRecoveryKwh,
    verifiedRecoveryRm,
    paybackMonths,
    confidence:Number((.6 + completeness * .3).toFixed(2)),
    observationDays:valid.length,
    explanation:'Verified from post-work actual generation against the documented pre-work performance ratio.',
  }
}

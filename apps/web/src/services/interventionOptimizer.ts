import type { InterventionCandidate, InterventionRecommendation } from '@/types/operations'

const clamp = (value:number, min=0, max=1) => Math.min(max, Math.max(min, value))

export function optimizeInterventions(candidates: InterventionCandidate[], crewCapacity: number): InterventionRecommendation[] {
  const capacity = Math.max(0, Math.floor(crewCapacity))
  const maxValue = Math.max(1, ...candidates.map((candidate) => Math.max(0, candidate.recoverableRm)))
  const ranked = candidates.map((candidate) => {
    const value = clamp(candidate.recoverableRm / maxValue)
    const confidence = clamp(candidate.confidence)
    const safety = clamp(candidate.safetyUrgency)
    const effort = clamp(candidate.travelEffort)
    const score = Number((value * .45 + confidence * .25 + safety * .2 + (1 - effort) * .1).toFixed(3))
    const reasons = [
      `Recoverable value contributes ${Math.round(value * 45)} of 45 points.`,
      `Evidence confidence contributes ${Math.round(confidence * 25)} of 25 points.`,
      `Safety urgency contributes ${Math.round(safety * 20)} of 20 points.`,
      `Travel efficiency contributes ${Math.round((1 - effort) * 10)} of 10 points.`,
    ]
    return { ...candidate, score, reasons }
  }).sort((a,b) => b.score - a.score || b.recoverableRm - a.recoverableRm)

  return ranked.map((candidate,index) => ({ ...candidate, rank:index + 1, decision:index < capacity ? 'dispatch-now' : 'monitor' }))
}

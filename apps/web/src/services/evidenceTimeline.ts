import { reactive } from 'vue'
import type { Site } from '@/types/dispatch'
import type { EvidenceEvent } from '@/types/operations'

const liveEvents = reactive<Record<string, EvidenceEvent[]>>({})

export function mergeEvidenceEvents(base: EvidenceEvent[], additions: EvidenceEvent[]): EvidenceEvent[] {
  const byId = new Map(base.map((event) => [event.id, event]))
  for (const event of additions) byId.set(event.id, event)
  return [...byId.values()].sort((a,b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
}

export function baseEvidenceEvents(site: Site): EvidenceEvent[] {
  const events: EvidenceEvent[] = []
  if (site.divergence) events.push({ id:`${site.site_id}-divergence`, siteId:site.site_id, type:'divergence', timestamp:site.divergence.start_date, title:'Performance divergence began', detail:`Site output separated from its cohort ${site.divergence.days_since} days ago.`, evidenceLevel:'inferred', confidence:site.detection?.confidence, status:'observed', sourceRef:`dispatch:${site.site_id}:divergence` })
  if (site.detection) events.push({ id:`${site.site_id}-detection`, siteId:site.site_id, type:'divergence', timestamp:site.divergence?.start_date ?? new Date(0).toISOString(), title:'Detector threshold exceeded', detail:`${site.detection.method} score ${site.detection.score.toFixed(2)} against threshold ${site.detection.threshold.toFixed(2)}.`, evidenceLevel:'inferred', confidence:site.detection.confidence, status:'confirmed', sourceRef:`dispatch:${site.site_id}:detection` })
  if (site.evidence?.captured_date) events.push({ id:`${site.site_id}-imagery`, siteId:site.site_id, type:'cv', timestamp:site.evidence.captured_date, title:'Visual evidence captured', detail:site.evidence.defect_class ? `${site.evidence.defect_class} evidence is available for review.` : 'Site imagery is available for review.', evidenceLevel:site.evidence.data_status === 'BUILT' ? 'measured' : 'simulated', confidence:site.evidence.confidence, status:'observed', sourceRef:`dispatch:${site.site_id}:evidence` })
  return events
}

export function recordEvidenceEvent(event: EvidenceEvent) {
  liveEvents[event.siteId] = mergeEvidenceEvents(liveEvents[event.siteId] ?? [], [event])
}

export function evidenceEventsFor(site: Site): EvidenceEvent[] {
  return mergeEvidenceEvents(baseEvidenceEvents(site), liveEvents[site.site_id] ?? [])
}

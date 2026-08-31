import { describe, expect, it } from 'vitest'
import { mergeEvidenceEvents } from './evidenceTimeline'
import type { EvidenceEvent } from '@/types/operations'

const event = (id:string, timestamp:string, title=id): EvidenceEvent => ({ id, siteId:'S-1', type:'scenario', timestamp, title, detail:'detail', evidenceLevel:'simulated', status:'simulated', sourceRef:id })

describe('evidence timeline', () => {
  it('orders events chronologically', () => expect(mergeEvidenceEvents([event('b','2026-02-01')],[event('a','2026-01-01')]).map((item) => item.id)).toEqual(['a','b']))
  it('upserts the same source event without duplication', () => {
    const result = mergeEvidenceEvents([event('a','2026-01-01','old')],[event('a','2026-01-02','new')])
    expect(result).toHaveLength(1)
    expect(result[0]?.title).toBe('new')
  })
})

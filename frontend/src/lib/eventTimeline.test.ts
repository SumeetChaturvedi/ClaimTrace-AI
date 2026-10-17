import { describe, expect, it } from 'vitest'
import type { Citation, ExtractedEvent } from '../api/types'
import { eventKey, findMatchingCitation, formatEnumLabel, splitAndSortEvents } from './eventTimeline'

function event(overrides: Partial<ExtractedEvent> = {}): ExtractedEvent {
  return {
    document_id: 1,
    chunk_id: 10,
    excerpt: 'fixture excerpt',
    event_type: null,
    assertion_type: null,
    description: 'fixture description',
    event_date: null,
    event_date_basis: 'unknown',
    attributed_party: null,
    ...overrides,
  }
}

describe('splitAndSortEvents', () => {
  it('sorts dated events chronologically, oldest first', () => {
    const e1 = event({ document_id: 1, chunk_id: 1, event_date: '2024-03-22', event_date_basis: 'explicit' })
    const e2 = event({ document_id: 2, chunk_id: 2, event_date: '2024-03-01', event_date_basis: 'explicit' })
    const { dated } = splitAndSortEvents([e1, e2])
    expect(dated.map((e) => e.event_date)).toEqual(['2024-03-01', '2024-03-22'])
  })

  it('keeps undated events visible in a separate group rather than dropping them', () => {
    const dated = event({ document_id: 1, chunk_id: 1, event_date: '2024-01-01', event_date_basis: 'explicit' })
    const undated = event({ document_id: 2, chunk_id: 2, event_date: null, event_date_basis: 'unknown' })
    const result = splitAndSortEvents([dated, undated])
    expect(result.dated).toHaveLength(1)
    expect(result.undated).toHaveLength(1)
    expect(result.undated[0]).toBe(undated)
  })

  it('breaks ties on equal dates deterministically by document_id then chunk_id', () => {
    const a = event({ document_id: 2, chunk_id: 1, event_date: '2024-05-01', event_date_basis: 'explicit' })
    const b = event({ document_id: 1, chunk_id: 5, event_date: '2024-05-01', event_date_basis: 'explicit' })
    const c = event({ document_id: 1, chunk_id: 1, event_date: '2024-05-01', event_date_basis: 'explicit' })
    const { dated } = splitAndSortEvents([a, b, c])
    expect(dated).toEqual([c, b, a])
  })

  it('supports multiple distinct events anchored to the same source chunk without collapsing them', () => {
    const e1 = event({ document_id: 1, chunk_id: 1, event_date: '2024-01-01', event_date_basis: 'explicit', description: 'first' })
    const e2 = event({ document_id: 1, chunk_id: 1, event_date: '2024-02-01', event_date_basis: 'explicit', description: 'second' })
    const { dated } = splitAndSortEvents([e1, e2])
    expect(dated).toHaveLength(2)
    expect(dated.map((e) => e.description)).toEqual(['first', 'second'])
  })

  it('never discards an event merely because a date is missing', () => {
    const events = [
      event({ event_date: null }),
      event({ document_id: 2, event_date: null }),
      event({ document_id: 3, event_date: null }),
    ]
    const result = splitAndSortEvents(events)
    expect(result.dated.length + result.undated.length).toBe(3)
  })

  it('returns an empty split for an empty input without throwing', () => {
    expect(splitAndSortEvents([])).toEqual({ dated: [], undated: [] })
  })
})

describe('eventKey', () => {
  it('produces a stable, unique key even for two events sharing the same source chunk', () => {
    const e1 = event({ document_id: 1, chunk_id: 1 })
    const e2 = event({ document_id: 1, chunk_id: 1 })
    expect(eventKey(e1, 0)).not.toBe(eventKey(e2, 1))
  })
})

describe('findMatchingCitation', () => {
  const citation: Citation = { document_id: 1, chunk_id: 10, page: 2, relevance_score: 0.9, chunk_text: 'text' }

  it('finds the citation matching an event\'s (document_id, chunk_id)', () => {
    const e = event({ document_id: 1, chunk_id: 10 })
    expect(findMatchingCitation(e, [citation])).toBe(citation)
  })

  it('returns null, never a fabricated citation, when no match exists', () => {
    const e = event({ document_id: 99, chunk_id: 99 })
    expect(findMatchingCitation(e, [citation])).toBeNull()
  })

  it('requires both document_id AND chunk_id to match — a shared document_id with a different chunk_id is not a match', () => {
    const e = event({ document_id: 1, chunk_id: 999 })
    expect(findMatchingCitation(e, [citation])).toBeNull()
  })

  it('requires both document_id AND chunk_id to match — a shared chunk_id with a different document_id is not a match', () => {
    const e = event({ document_id: 999, chunk_id: 10 })
    expect(findMatchingCitation(e, [citation])).toBeNull()
  })

  it('picks the correct citation out of several when only one matches both fields', () => {
    const other: Citation = { document_id: 1, chunk_id: 11, page: 1, relevance_score: 0.5, chunk_text: 'other' }
    const e = event({ document_id: 1, chunk_id: 10 })
    expect(findMatchingCitation(e, [other, citation])).toBe(citation)
  })

  it('returns null for an empty citations list', () => {
    const e = event({ document_id: 1, chunk_id: 10 })
    expect(findMatchingCitation(e, [])).toBeNull()
  })
})

describe('formatEnumLabel', () => {
  it('formats an UPPER_SNAKE_CASE event type into readable text', () => {
    expect(formatEnumLabel('CLARIFICATION_REQUESTED')).toBe('Clarification requested')
  })

  it('formats a lower_snake_case assertion type into readable text', () => {
    expect(formatEnumLabel('recorded_action')).toBe('Recorded action')
  })

  it('handles a single-word value', () => {
    expect(formatEnumLabel('explicit')).toBe('Explicit')
  })
})

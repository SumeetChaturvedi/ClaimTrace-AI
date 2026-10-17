import type { Citation, ExtractedEvent } from '../api/types'

/**
 * Pure, deterministic presentation logic for the Event Timeline (Phase
 * 8B.3) — split out from EventsPanel.tsx so it's unit-testable without
 * rendering anything, and so the sorting/grouping rules are in exactly one
 * place rather than re-implemented per component.
 *
 * Nothing here calls the backend, fabricates a field, or infers a
 * relationship (e.g. a conflict) that ExtractedEvent itself doesn't carry.
 */

export interface SplitEvents {
  /** Events with a known event_date, sorted chronologically (oldest first). */
  dated: ExtractedEvent[]
  /** Events whose event_date is null — event_date_basis is always
   * 'unknown' for these (the backend never leaves event_date null while
   * claiming a basis of 'explicit'/'inferred' — see ExtractedEvent's own
   * type). Kept in their original (stable) relative order, never dropped. */
  undated: ExtractedEvent[]
}

/** Splits `events` into dated/undated groups and sorts the dated group
 * chronologically. Ties (two events sharing the same event_date) are
 * broken deterministically by (document_id, chunk_id) — real, stable
 * identifiers already on the event — rather than relying only on
 * JavaScript's spec-guaranteed stable sort, so the order is reproducible
 * even if this function's own implementation changes later. */
export function splitAndSortEvents(events: ExtractedEvent[]): SplitEvents {
  const dated: ExtractedEvent[] = []
  const undated: ExtractedEvent[] = []

  for (const event of events) {
    if (event.event_date) dated.push(event)
    else undated.push(event)
  }

  dated.sort((a, b) => {
    // Plain lexicographic comparison, not localeCompare: event_date is
    // always a fixed-width "YYYY-MM-DD" string (ExtractedEvent's own
    // contract — see api/types.ts), for which codepoint order already IS
    // chronological order. localeCompare would route this through the
    // runtime's ICU/Intl collation, which is locale- and environment-
    // dependent and offers no benefit over '<'/'>' for this exact format
    // — using it here would make "deterministic ordering" depend on
    // something outside this function's own control.
    const dateA = a.event_date as string
    const dateB = b.event_date as string
    if (dateA !== dateB) return dateA < dateB ? -1 : 1
    if (a.document_id !== b.document_id) return a.document_id - b.document_id
    return a.chunk_id - b.chunk_id
  })

  return { dated, undated }
}

/** A stable React key for one event — (document_id, chunk_id) alone is not
 * guaranteed unique (the extractor can legitimately return more than one
 * event anchored to the same chunk, e.g. two distinct statements in one
 * passage), so the event's position in its own rendered list disambiguates
 * without implying any ordering meaning beyond "this one, specifically". */
export function eventKey(event: ExtractedEvent, index: number): string {
  return `${event.document_id}-${event.chunk_id}-${index}`
}

/** Formats a backend enum-style value ("CLARIFICATION_REQUESTED",
 * "recorded_action") into readable text ("Clarification requested",
 * "Recorded action") for display — purely cosmetic, never changes which
 * value is being shown or implies a category the backend didn't return. */
export function formatEnumLabel(value: string): string {
  const words = value.toLowerCase().split('_')
  return words[0].charAt(0).toUpperCase() + words[0].slice(1) + (words.length > 1 ? ' ' + words.slice(1).join(' ') : '')
}

/** The investigation's own real Citation matching this event's
 * (document_id, chunk_id), if one is still present in the investigation's
 * final `citations` list — used only to decide whether "Open source
 * document" can link anywhere real. Citation verification
 * (app/agent/citation_verification.py) can drop a citation the event
 * extractor itself still validated independently, so this is a lookup, not
 * an assumption: null means there is genuinely no source view to open for
 * this event, and callers must not fabricate one. */
export function findMatchingCitation(event: ExtractedEvent, citations: Citation[]): Citation | null {
  return citations.find((c) => c.document_id === event.document_id && c.chunk_id === event.chunk_id) ?? null
}

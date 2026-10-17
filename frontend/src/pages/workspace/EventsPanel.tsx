import type { Citation, ExtractedEvent } from '../../api/types'
import { useInspector } from '../../components/layout/InspectorContext'
import { SectionLabel, Muted, NotAvailable } from '../../components/ui/Typography'
import { Badge } from '../../components/ui/Badge'
import { EmptyState, ErrorState } from '../../components/ui/StateViews'
import { eventKey, findMatchingCitation, formatEnumLabel, splitAndSortEvents } from '../../lib/eventTimeline'
import styles from './EventsPanel.module.css'

/**
 * Events tab (Phase 8B.3: Evidence-Grounded Event Timeline UI) — renders
 * the real, source-verified ExtractedEvent list the backend's EventExtractor
 * (Phase 8B.2) produced for this investigation. Distinct from the Timeline
 * tab (TimelinePanel.tsx): that one is a deterministic, no-LLM, document-
 * level chronology; this one is LLM-extracted, event-level, and explicitly
 * labeled as such, since Phase 8B.2's own real-Gemini evaluation found
 * event-type/date/attribution accuracy below provisional thresholds.
 *
 * Nothing here is fabricated: event_type/assertion_type/event_date/
 * attributed_party are rendered exactly as returned (or as an explicit
 * "not recorded" marker when null), and no confidence score, conflict
 * relationship, or chronology position is invented for a field the
 * backend didn't return. The three extraction-level states —
 * success-with-events, success-with-none, and failed — are rendered
 * distinctly; see the component body below for why a legacy investigation
 * (predates this feature) and a genuinely empty result cannot currently be
 * told apart over this API (documented, not guessed around).
 */
export function EventsPanel({
  events,
  eventsError,
  eventsTruncated,
  citations,
  documentNames,
  documentTypes,
  projectId,
  investigationId,
}: {
  events: ExtractedEvent[]
  eventsError: string | null
  eventsTruncated: boolean
  citations: Citation[]
  documentNames: Record<number, string>
  documentTypes: Record<number, string | null>
  projectId: number
  investigationId: string
}) {
  const { open, content } = useInspector()
  const activeEvent =
    content?.kind === 'timelineEvent' && content.investigationId === investigationId ? content.event : null

  const openEvent = (event: ExtractedEvent) => {
    const matchingCitation = findMatchingCitation(event, citations)
    open({
      kind: 'timelineEvent',
      event,
      matchingCitation,
      documentName: documentNames[event.document_id],
      documentType: documentTypes[event.document_id],
      projectId,
      investigationId,
    })
  }

  if (eventsError !== null) {
    return (
      <div className={styles.panel}>
        <Intro />
        <ErrorState
          title="Event extraction was unavailable for this investigation"
          message="This does not mean no relevant events exist — the extraction step itself could not complete. The rest of this investigation (finding, evidence, timeline) is unaffected. Retrying event extraction on its own isn't currently supported; retrying the whole investigation would also regenerate its events."
        />
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className={styles.panel}>
        <Intro />
        <EmptyState title="No AI-extracted events are associated with this investigation">
          <Muted>
            This may be because extraction genuinely found no qualifying events in this
            investigation's evidence, or because this investigation predates event extraction —
            the two cases can't currently be told apart from this view.
          </Muted>
        </EmptyState>
      </div>
    )
  }

  const { dated, undated } = splitAndSortEvents(events)

  return (
    <div className={styles.panel}>
      <Intro />

      {eventsTruncated && (
        <div className={styles.truncatedNotice} role="status">
          This list may be incomplete — the extraction response was cut off before finishing.
          Some supported events may be missing.
        </div>
      )}

      {dated.length > 0 && (
        <section>
          <SectionLabel>Chronological</SectionLabel>
          <ol className={styles.list}>
            {dated.map((event, i) => (
              <EventCard
                key={eventKey(event, i)}
                event={event}
                documentLabel={documentNames[event.document_id]}
                active={event === activeEvent}
                onOpen={() => openEvent(event)}
              />
            ))}
          </ol>
        </section>
      )}

      {undated.length > 0 && (
        <section>
          <SectionLabel>Date not known</SectionLabel>
          <Muted>
            These events don't belong at any specific point above — their date couldn't be
            determined from the evidence, so none is implied.
          </Muted>
          <ol className={styles.list}>
            {undated.map((event, i) => (
              <EventCard
                key={eventKey(event, i)}
                event={event}
                documentLabel={documentNames[event.document_id]}
                active={event === activeEvent}
                onOpen={() => openEvent(event)}
              />
            ))}
          </ol>
        </section>
      )}
    </div>
  )
}

function Intro() {
  return (
    <div className={styles.intro}>
      <div className={styles.introHeading}>
        <SectionLabel>AI-Extracted Events</SectionLabel>
        <Badge tone="amber">Experimental</Badge>
      </div>
      <Muted>
        Evidence-linked candidates for investigator review — not verified facts or legal
        conclusions. Each one should be checked against its supporting excerpt before being
        relied on.
      </Muted>
    </div>
  )
}

function EventCard({
  event,
  documentLabel,
  active,
  onOpen,
}: {
  event: ExtractedEvent
  documentLabel: string | undefined
  active: boolean
  onOpen: () => void
}) {
  const label = documentLabel ?? `Document #${event.document_id}`
  return (
    <li className={styles.event}>
      <button className={`${styles.card} ${active ? styles.cardActive : ''}`} onClick={onOpen} aria-pressed={active}>
        <div className={styles.cardHeader}>
          <span className={styles.cardDate}>
            {event.event_date ?? <Muted>Date unknown</Muted>}
          </span>
          {event.event_type && <Badge tone="neutral">{formatEnumLabel(event.event_type)}</Badge>}
        </div>

        <p className={styles.cardDescription}>{event.description}</p>

        <div className={styles.cardMeta}>
          <span>{label}</span>
          {event.assertion_type && <span>{formatEnumLabel(event.assertion_type)}</span>}
          <span>
            {event.attributed_party ?? <NotAvailable reason="No party could be attributed from the evidence" />}
          </span>
        </div>

        <p className={styles.cardExcerpt}>{event.excerpt}</p>
      </button>
    </li>
  )
}

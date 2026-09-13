import type { Citation, DocumentSummary, TimelineEntry } from '../../api/types'
import { useInspector } from '../../components/layout/InspectorContext'
import { SectionLabel, Muted } from '../../components/ui/Typography'
import { Badge } from '../../components/ui/Badge'
import { EmptyState, LoadingState } from '../../components/ui/StateViews'
import { citationLocationShort } from '../../lib/documentFormat'
import styles from './TimelinePanel.module.css'

/**
 * Timeline tab (Phase 4: Timeline Productization) — a real chronology
 * built entirely from `timeline`, the structured TimelineEntry list the
 * backend's existing, deterministic TimelineBuilder already produces for
 * every investigation (backend/app/investigation/timeline.py). Nothing
 * here is invented: event_label/document_type/document_date come straight
 * from the backend, and every citation shown under an event is one of this
 * investigation's own real Citation objects for that document — clicking
 * one opens the exact same Inspector/Source-Viewer flow the Evidence tab
 * already uses (see EvidencePanel.tsx), not a second implementation.
 *
 * There is no separate "event description", confidence, conflict, or
 * contractual-context field on TimelineEntry — this panel does not
 * fabricate any of those; it only ever renders fields the backend actually
 * returns.
 */
export function TimelinePanel({
  timeline,
  documents,
  documentNames,
  projectId,
  investigationId,
}: {
  timeline: TimelineEntry[]
  documents: DocumentSummary[] | null
  documentNames: Record<number, string>
  projectId: number
  investigationId: string
}) {
  const { open, content } = useInspector()
  const activeChunkId = content?.kind === 'citation' && content.investigationId === investigationId ? content.citation.chunk_id : null

  const documentsById = new Map<number, DocumentSummary>()
  for (const d of documents ?? []) documentsById.set(d.id, d)

  const openCitation = (citation: Citation, entry: TimelineEntry) => {
    const document = documentsById.get(entry.document_id)
    open({
      kind: 'citation',
      citation,
      documentName: document?.filename ?? documentNames[entry.document_id],
      documentType: entry.document_type,
      documentDate: entry.document_date,
      projectId,
      investigationId,
    })
  }

  if (timeline.length === 0) {
    return (
      <div className={styles.panel}>
        <SectionLabel>Chronology</SectionLabel>
        <EmptyState title="Chronology is not available for this investigation">
          <Muted>
            No dated documents were cited as evidence, so no chronology could be built for this
            investigation.
          </Muted>
        </EmptyState>
      </div>
    )
  }

  return (
    <div className={styles.panel}>
      <div className={styles.intro}>
        <SectionLabel>Chronology</SectionLabel>
        <Muted>The documents behind this investigation's evidence, ordered by their own dates.</Muted>
      </div>

      {documents === null && <LoadingState label="Resolving document details…" />}

      <ol className={styles.list}>
        {timeline.map((entry, i) => (
          <TimelineEventRow
            key={`${entry.document_id}-${i}`}
            entry={entry}
            document={documentsById.get(entry.document_id)}
            documentNames={documentNames}
            activeChunkId={activeChunkId}
            onOpenCitation={(citation) => openCitation(citation, entry)}
          />
        ))}
      </ol>
    </div>
  )
}

function TimelineEventRow({
  entry,
  document,
  documentNames,
  activeChunkId,
  onOpenCitation,
}: {
  entry: TimelineEntry
  document?: DocumentSummary
  documentNames: Record<number, string>
  activeChunkId: number | null
  onOpenCitation: (citation: Citation) => void
}) {
  const documentLabel = document?.filename ?? documentNames[entry.document_id] ?? `Document #${entry.document_id}`

  return (
    <li className={styles.event}>
      <div className={styles.eventDate}>
        {entry.document_date ?? <Muted>Date unknown</Muted>}
      </div>
      <div className={styles.eventMain}>
        <div className={styles.eventTitleRow}>
          <h3 className={styles.eventTitle}>{entry.event_label}</h3>
          {entry.document_type && <Badge tone="neutral">{entry.document_type}</Badge>}
        </div>
        <p className={styles.eventSource}>{documentLabel}</p>

        {entry.citations.length === 0 ? (
          <Muted>No citation is attached to this event.</Muted>
        ) : (
          <ul className={styles.evidenceList}>
            {entry.citations.map((citation) => (
              <li key={citation.chunk_id}>
                <button
                  className={`${styles.evidenceRow} ${citation.chunk_id === activeChunkId ? styles.evidenceRowActive : ''}`}
                  onClick={() => onOpenCitation(citation)}
                  aria-pressed={citation.chunk_id === activeChunkId}
                >
                  <span className={styles.evidenceExcerpt}>
                    {citation.chunk_text ?? <Muted>No excerpt text was returned for this citation.</Muted>}
                  </span>
                  <span className={styles.evidenceMeta}>
                    {citation.page != null && <span>{citationLocationShort(documentLabel, citation.page)}</span>}
                    <span>Relevance {citation.relevance_score.toFixed(2)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </li>
  )
}

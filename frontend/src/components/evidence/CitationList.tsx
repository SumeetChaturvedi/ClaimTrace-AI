import type { Citation, DocumentSummary } from '../../api/types'
import { useInspector } from '../layout/InspectorContext'
import { SectionLabel, Muted } from '../ui/Typography'
import { citationLocationShort } from '../../lib/documentFormat'
import styles from './CitationList.module.css'

interface CitationListProps {
  citations: Citation[]
  /** document_id -> filename, resolved from GET /documents (see api/client.ts).
   * Optional: if a document isn't in the map, we fall back to "Document #id"
   * rather than guessing a name. */
  documentNames?: Record<number, string>
  /** Full document metadata (type/date), when already resolved by the
   * caller, so the Inspector can show the same detail Evidence does. */
  documents?: DocumentSummary[] | null
  /** The investigation these citations belong to — threaded through to the
   * Inspector so its "Open source" action can build a correctly-scoped
   * Source View link. */
  projectId: number
  investigationId: string
}

/** The "Sources" list: one row per real Citation returned by the backend.
 * Clicking a row opens it in the Inspector — this is the one real
 * evidence-inspection flow implemented in this task. */
export function CitationList({ citations, documentNames, documents, projectId, investigationId }: CitationListProps) {
  const { open, content } = useInspector()
  const activeChunkId = content?.kind === 'citation' && content.investigationId === investigationId ? content.citation.chunk_id : null

  if (citations.length === 0) {
    return <Muted>No citations were returned for this investigation.</Muted>
  }

  return (
    <div>
      <SectionLabel>Sources ({citations.length})</SectionLabel>
      <ul className={styles.list}>
        {citations.map((citation, i) => {
          const document = documents?.find((d) => d.id === citation.document_id)
          const documentName = document?.filename ?? documentNames?.[citation.document_id]
          return (
            <li key={`${citation.document_id}-${citation.chunk_id}-${i}`}>
              <button
                className={`${styles.row} ${citation.chunk_id === activeChunkId ? styles.rowActive : ''}`}
                aria-pressed={citation.chunk_id === activeChunkId}
                onClick={() =>
                  open({
                    kind: 'citation',
                    citation,
                    documentName,
                    documentType: document?.doc_type,
                    documentDate: document?.doc_date,
                    projectId,
                    investigationId,
                  })
                }
              >
                <span className={styles.index}>{i + 1}</span>
                <span className={styles.rowBody}>
                  <span className={styles.docName}>
                    {documentName ?? `Document #${citation.document_id}`}
                    {citation.page != null && (
                      <span className={styles.page}> · {citationLocationShort(documentName, citation.page)}</span>
                    )}
                  </span>
                  {citation.chunk_text && <span className={styles.excerpt}>{citation.chunk_text}</span>}
                </span>
                <span className={styles.score}>{citation.relevance_score.toFixed(2)}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

import type { Citation, DocumentSummary } from '../../api/types'
import { SectionLabel, Muted } from '../../components/ui/Typography'
import { Badge } from '../../components/ui/Badge'
import { LoadingState } from '../../components/ui/StateViews'
import styles from './panels.module.css'

interface DocumentEntry {
  documentId: number
  document?: DocumentSummary
  citationCount: number
}

/** The set of documents actually cited in this investigation — derived
 * honestly from real citations. This is NOT the project's full document
 * library (see ProjectPage's note on why that isn't shown).
 *
 * `documents` is the same richer DocumentSummary array already fetched by
 * InvestigationWorkspacePage for the Evidence Workbench (doc_type/doc_date/
 * referenced_ids), reused here rather than re-fetched. `documentNames`
 * remains the fallback for a document id that metadata resolution hasn't
 * covered, matching the pattern already used elsewhere in the workspace. */
export function DocumentsPanel({
  citations,
  documents,
  documentNames,
}: {
  citations: Citation[]
  documents: DocumentSummary[] | null
  documentNames: Record<number, string>
}) {
  const documentsById = new Map<number, DocumentSummary>()
  for (const d of documents ?? []) documentsById.set(d.id, d)

  // Preserves the same "first citation encountered" ordering the previous
  // implementation used (Map insertion order over `citations`) — not a new
  // sort.
  const order: number[] = []
  const counts = new Map<number, number>()
  for (const c of citations) {
    if (!counts.has(c.document_id)) order.push(c.document_id)
    counts.set(c.document_id, (counts.get(c.document_id) ?? 0) + 1)
  }

  const entries: DocumentEntry[] = order.map((documentId) => ({
    documentId,
    document: documentsById.get(documentId),
    citationCount: counts.get(documentId)!,
  }))

  return (
    <div className={styles.docsPanel}>
      <SectionLabel>Documents cited ({entries.length})</SectionLabel>
      <Muted>Review the documents cited as evidence in this investigation.</Muted>

      {documents === null && <LoadingState label="Resolving document details…" />}

      {entries.length === 0 ? (
        <Muted>No documents were cited.</Muted>
      ) : (
        <ul className={styles.docList}>
          {entries.map((entry) => (
            <DocumentRow key={entry.documentId} entry={entry} documentNames={documentNames} />
          ))}
        </ul>
      )}
    </div>
  )
}

function DocumentRow({
  entry,
  documentNames,
}: {
  entry: DocumentEntry
  documentNames: Record<number, string>
}) {
  const { documentId, document, citationCount } = entry
  const filename = document?.filename ?? documentNames[documentId] ?? `Document #${documentId}`
  const references = (document?.referenced_ids ?? []).filter((id) => id.trim().length > 0)

  return (
    <li className={styles.docRow}>
      <div className={styles.docMain}>
        <span className={styles.docName}>{filename}</span>
        <div className={styles.docMeta}>
          {document?.doc_type ? (
            <Badge tone="neutral">{document.doc_type}</Badge>
          ) : (
            <Muted>Type not recorded</Muted>
          )}
          <span className={styles.docDate}>
            {document?.doc_date ? document.doc_date : <Muted>Date not recorded</Muted>}
          </span>
        </div>
        <div className={styles.docRefs}>
          {references.length > 0 ? (
            <details className={styles.refsDetails}>
              <summary>References ({references.length})</summary>
              <p className={styles.refsList}>{references.join(', ')}</p>
            </details>
          ) : (
            <Muted>No cross-document references recorded</Muted>
          )}
        </div>
      </div>
      <span className={styles.docCitationCount}>
        {citationCount} citation{citationCount === 1 ? '' : 's'}
      </span>
    </li>
  )
}

import { useEffect, useState, type ReactNode } from 'react'
import { useParams, Link } from 'react-router-dom'
import { LoadingState, ErrorState } from '../components/ui/StateViews'
import { Prose, Muted, SectionLabel } from '../components/ui/Typography'
import { Badge } from '../components/ui/Badge'
import { parseProjectId } from '../lib/projectDirectory'
import { parseInvestigationId } from '../lib/investigationId'
import { useInvestigationRecord } from '../lib/useInvestigationRecord'
import { useProject } from '../lib/useProject'
import { listAllDocuments } from '../api/client'
import type { Citation, ContractClause, DocumentSummary, TimelineEntry } from '../api/types'
import { citationLocationShort } from '../lib/documentFormat'
import styles from './InvestigationRecordPage.module.css'

/**
 * Investigation Record (Phase 6: Professional Outputs) — a read-only,
 * print-ready representation of one already-completed, persisted
 * investigation. This is a REPRESENTATION of the investigation record, not
 * a second AI opinion: it fetches the exact same persisted
 * InvestigationRecord the Workspace already renders (via the same
 * useInvestigationRecord hook, a plain GET — see that hook's own docstring
 * for why this can never re-invoke Gemini), and every section below is
 * either that record's own persisted fields or a deterministic derivation
 * from them (e.g. counting citations, finding a date range across cited
 * documents' own doc_date fields). Nothing here calls Gemini, reruns
 * retrieval, or mutates the investigation.
 *
 * Deliberately does NOT use AppShell: a professional record should read as
 * a standalone investigation document (nav rail, Inspector, and app chrome
 * would undercut that), not another workspace tab. Export is via the
 * browser's native print dialog ("Save as PDF" from there produces a real
 * PDF) rather than a server/client PDF-generation library — there is no
 * such dependency anywhere in this project today, and browser print
 * already satisfies the format/pagination requirements (see
 * InvestigationRecordPage.module.css's @page/@media print rules) without
 * adding one.
 */
export function InvestigationRecordPage() {
  const { projectId, investigationId } = useParams<{ projectId: string; investigationId: string }>()
  const id = parseProjectId(projectId)
  const parsedInvestigationId = investigationId ? parseInvestigationId(investigationId) : null
  const projectQuery = useProject(id)
  const { state } = useInvestigationRecord(id, parsedInvestigationId)

  // Same non-project-scoped-but-filtered pattern InvestigationWorkspacePage/
  // SourceViewPage already use: fetch every document's metadata once, then
  // filter down to only the ids this investigation's own citations actually
  // reference (see citedDocuments below) — never "every project document".
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null)
  useEffect(() => {
    listAllDocuments()
      .then(setDocuments)
      .catch(() => {
        // Non-critical: sections below fall back to "Document #id".
      })
  }, [])

  if (id === null) {
    return (
      <div className={styles.page}>
        <ErrorState title="Invalid project id" message={`"${projectId}" is not a valid project id.`} />
      </div>
    )
  }
  if (parsedInvestigationId === null) {
    return (
      <div className={styles.page}>
        <ErrorState
          title="Invalid investigation reference"
          message={`"${investigationId}" is not a valid investigation reference.`}
        />
      </div>
    )
  }
  if (state.status === 'loading') {
    return (
      <div className={styles.page}>
        <LoadingState label="Loading investigation record…" />
      </div>
    )
  }
  if (state.status === 'not-found') {
    return (
      <div className={styles.page}>
        <ErrorState
          title="Investigation record not available"
          message="This investigation could not be found for this project. It may not exist, or it may belong to a different project."
        />
      </div>
    )
  }
  if (state.status === 'error') {
    return (
      <div className={styles.page}>
        <ErrorState title="Could not load this investigation record" message={state.error} />
      </div>
    )
  }

  const record = state.record
  const projectName = projectQuery.status === 'success' ? projectQuery.data.name : `Project ${record.project_id}`

  const documentsById = new Map<number, DocumentSummary>()
  for (const d of documents ?? []) documentsById.set(d.id, d)

  // "Documents cited/used by this investigation", never "every project
  // document" — derived solely from this investigation's own citations.
  const citedDocumentIds = Array.from(new Set(record.citations.map((c) => c.document_id)))
  const citationCountByDocument = new Map<number, number>()
  for (const c of record.citations) {
    citationCountByDocument.set(c.document_id, (citationCountByDocument.get(c.document_id) ?? 0) + 1)
  }
  const citedDocuments = citedDocumentIds
    .map((docId) => documentsById.get(docId))
    .filter((d): d is DocumentSummary => d !== undefined)

  const documentTypesRepresented = Array.from(new Set(citedDocuments.map((d) => d.doc_type).filter((t): t is string => !!t)))
  const knownDates = citedDocuments.map((d) => d.doc_date).filter((d): d is string => !!d).sort()
  const dateRange = knownDates.length > 0 ? { earliest: knownDates[0], latest: knownDates[knownDates.length - 1] } : null

  return (
    <div className={styles.page}>
      <div className={`${styles.actionBar} ${styles.noPrint}`}>
        <Link to={`/projects/${id}/investigations/${record.id}`} className={styles.backLink}>
          ← Back to Workspace
        </Link>
        <button className={styles.printButton} onClick={() => window.print()}>
          Print / Save as PDF
        </button>
      </div>

      <article className={styles.document}>
        <header className={styles.recordHeader}>
          <p className={styles.wordmark}>ClaimTrace</p>
          <p className={styles.kicker}>Investigation Record</p>
          <h1 className={styles.projectName}>{projectName}</h1>
          <h2 className={styles.question}>{record.query}</h2>

          <dl className={styles.metaGrid}>
            <div>
              <dt>Status</dt>
              <dd>
                {record.status === 'completed' && <Badge tone="green">Investigation complete</Badge>}
                {record.status === 'failed' && <Badge tone="red">Investigation not completed</Badge>}
                {record.status === 'running' && <Badge tone="neutral">Investigating…</Badge>}
              </dd>
            </div>
            <div>
              <dt>Investigation started</dt>
              <dd>{formatTimestamp(record.created_at)}</dd>
            </div>
            <div>
              <dt>{record.status === 'completed' ? 'Investigation completed' : 'Last updated'}</dt>
              <dd>{formatTimestamp(record.updated_at)}</dd>
            </div>
            <div>
              <dt>Reference</dt>
              <dd className={styles.reference}>{record.id}</dd>
            </div>
          </dl>
        </header>

        {record.status !== 'completed' && (
          <Section title="Finding">
            <Muted>
              {record.status === 'running'
                ? 'This investigation has not finished running, so no finding is available yet.'
                : 'This investigation did not complete, so no finding is available.'}
            </Muted>
            {record.status === 'failed' && record.error && <p className={styles.errorText}>{record.error}</p>}
          </Section>
        )}

        {record.status === 'completed' && (
          <>
            <Section title="Finding">
              <Prose>{record.answer}</Prose>
            </Section>

            <Section title="Evidence Review">
              <dl className={styles.reviewGrid}>
                <div>
                  <dt>Verified citations</dt>
                  <dd>{record.citations.length}</dd>
                </div>
                <div>
                  <dt>Source documents</dt>
                  <dd>{citedDocumentIds.length}</dd>
                </div>
                <div>
                  <dt>Document types represented</dt>
                  <dd>{documentTypesRepresented.length > 0 ? documentTypesRepresented.join(', ') : <Muted>Not recorded</Muted>}</dd>
                </div>
                <div>
                  <dt>Document date range</dt>
                  <dd>
                    {dateRange ? (
                      dateRange.earliest === dateRange.latest ? dateRange.earliest : `${dateRange.earliest} – ${dateRange.latest}`
                    ) : (
                      <Muted>Not established by the available record</Muted>
                    )}
                  </dd>
                </div>
              </dl>
            </Section>

            <Section title="Key Evidence">
              <p className={styles.sectionIntro}>
                The verified citations supporting this investigation's finding, in the order
                returned by the investigation engine.
              </p>
              {record.citations.length === 0 ? (
                <Muted>No supporting evidence was identified in the project record for this question.</Muted>
              ) : (
                <ol className={styles.evidenceList}>
                  {record.citations.map((citation, i) => (
                    <EvidenceRow key={`${citation.document_id}-${citation.chunk_id}-${i}`} index={i + 1} citation={citation} document={documentsById.get(citation.document_id)} projectId={id} investigationId={record.id} />
                  ))}
                </ol>
              )}
            </Section>

            <Section title="Chronology">
              {record.timeline.length === 0 ? (
                <Muted>No chronology is available for this investigation.</Muted>
              ) : (
                <ol className={styles.timelineList}>
                  {record.timeline.map((entry, i) => (
                    <TimelineRow key={`${entry.document_id}-${i}`} entry={entry} document={documentsById.get(entry.document_id)} />
                  ))}
                </ol>
              )}
            </Section>

            <Section title="Contractual Context">
              <p className={styles.sectionIntro}>
                Contract provisions retrieved as relevant to this investigation. A provision is
                contractual context, not investigation evidence — it is not linked to a specific
                source document or page in the current system.
              </p>
              {record.contract_clauses.length === 0 ? (
                <Muted>No contractual provisions were returned for this investigation.</Muted>
              ) : (
                <ol className={styles.clauseList}>
                  {record.contract_clauses.map((clause, i) => (
                    <ClauseRow key={`${clause.clause_number}-${i}`} clause={clause} />
                  ))}
                </ol>
              )}
            </Section>

            <Section title="Not Established / Limitations">
              {record.citations.length === 0 && (
                <p className={styles.limitationText}>
                  No supporting evidence was identified in the project record for this question.
                </p>
              )}
              <p className={styles.disclaimer}>
                ClaimTrace gathers and cites evidence to support this investigation. It does not
                adjudicate disputes or issue a legal or contractual determination. Review this
                finding against the underlying sources before relying on it — professional review
                is recommended.
              </p>
            </Section>

            <Section title="Sources">
              {citedDocuments.length === 0 ? (
                <Muted>No source documents could be resolved for this investigation's citations.</Muted>
              ) : (
                <ul className={styles.sourceList}>
                  {citedDocumentIds.map((docId) => {
                    const doc = documentsById.get(docId)
                    return (
                      <li key={docId} className={styles.sourceRow}>
                        <span className={styles.sourceName}>{doc?.filename ?? `Document #${docId}`}</span>
                        <span className={styles.sourceMeta}>
                          {doc?.doc_type ?? <Muted>Type not recorded</Muted>}
                          {' · '}
                          {doc?.doc_date ?? <Muted>Date not recorded</Muted>}
                          {' · '}
                          {citationCountByDocument.get(docId)} citation{citationCountByDocument.get(docId) === 1 ? '' : 's'}
                        </span>
                      </li>
                    )
                  })}
                </ul>
              )}
            </Section>
          </>
        )}
      </article>
    </div>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={styles.section}>
      <SectionLabel>{title}</SectionLabel>
      <div className={styles.sectionBody}>{children}</div>
    </section>
  )
}

function EvidenceRow({
  index,
  citation,
  document,
  projectId,
  investigationId,
}: {
  index: number
  citation: Citation
  document?: DocumentSummary
  projectId: number
  investigationId: string
}) {
  const documentLabel = document?.filename ?? `Document #${citation.document_id}`
  return (
    <li className={styles.evidenceRow}>
      <div className={styles.evidenceHeader}>
        <span className={styles.evidenceIndex}>{index}</span>
        <span className={styles.evidenceDoc}>
          {documentLabel}
          {citation.page != null && ` · ${citationLocationShort(document?.filename, citation.page)}`}
        </span>
        <span className={styles.evidenceScore}>Relevance {citation.relevance_score.toFixed(2)}</span>
      </div>
      <p className={styles.evidenceExcerpt}>
        {citation.chunk_text ?? <Muted>No excerpt text was returned for this citation.</Muted>}
      </p>
      <Link
        className={`${styles.sourceLink} ${styles.noPrint}`}
        to={`/projects/${projectId}/investigations/${investigationId}/source/${citation.chunk_id}`}
      >
        Open source document →
      </Link>
    </li>
  )
}

function TimelineRow({ entry, document }: { entry: TimelineEntry; document?: DocumentSummary }) {
  const documentLabel = document?.filename ?? `Document #${entry.document_id}`
  return (
    <li className={styles.timelineRow}>
      <span className={styles.timelineDate}>{entry.document_date ?? <Muted>Date unknown</Muted>}</span>
      <span className={styles.timelineBody}>
        <span className={styles.timelineLabel}>{entry.event_label}</span>
        <span className={styles.timelineDoc}>
          {documentLabel}
          {entry.document_type && ` · ${entry.document_type}`}
        </span>
      </span>
    </li>
  )
}

function ClauseRow({ clause }: { clause: ContractClause }) {
  return (
    <li className={styles.clauseRow}>
      <p className={styles.clauseTitle}>
        <span className={styles.clauseNumber}>{clause.clause_number}</span> {clause.title}
        <span className={styles.clauseTopic}> ({clause.topic})</span>
      </p>
      <p className={styles.clauseText}>{clause.text}</p>
    </li>
  )
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

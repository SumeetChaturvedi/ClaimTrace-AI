import { useRef, useState, type ChangeEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { SectionLabel, Muted } from '../components/ui/Typography'
import { LinkButton } from '../components/ui/LinkButton'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { ErrorState, LoadingState } from '../components/ui/StateViews'
import { parseProjectId } from '../lib/projectDirectory'
import { useProject } from '../lib/useProject'
import { ApiError, listInvestigations, listProjectDocuments, uploadProjectDocuments } from '../api/client'
import { useApiQuery } from '../api/useApi'
import type { DocumentSummary, InvestigationRecord, InvestigationStatus } from '../api/types'
import styles from './ProjectPage.module.css'

/**
 * Project workspace front sheet (Phase 3: Project + Document Foundation).
 * Documents shown here are real, project-scoped rows from
 * GET /projects/{id}/documents — including ones still processing or that
 * failed — and "Add Documents" uploads through the real ingestion pipeline
 * (extract, chunk, embed, index; see backend/app/ingestion/pipeline.py),
 * the same one the investigation engine already reads from. A document
 * only becomes citable once its status reaches 'ready'.
 */
export function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const id = parseProjectId(projectId)
  const navigate = useNavigate()

  const projectQuery = useProject(id)
  const [refreshToken, setRefreshToken] = useState(0)
  const documentsQuery = useApiQuery(
    () => (id === null ? Promise.resolve<DocumentSummary[]>([]) : listProjectDocuments(id)),
    [id, refreshToken],
  )
  // Real, already-persisted investigation history (Phase 2) — reused here,
  // not re-fetched or re-derived, so the project record can show "how much
  // investigation has actually happened" without inventing an activity
  // metric the backend doesn't provide.
  const investigationsQuery = useApiQuery(
    () => (id === null ? Promise.resolve<InvestigationRecord[]>([]) : listInvestigations(id)),
    [id, refreshToken],
  )

  const [uploading, setUploading] = useState(false)
  const [uploadSummary, setUploadSummary] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (id === null || !files || files.length === 0) return

    setUploading(true)
    setUploadSummary(null)
    setUploadError(null)
    try {
      const result = await uploadProjectDocuments(id, Array.from(files))
      const readyCount = result.documents.filter((d) => d.status === 'ready').length
      const failedCount = result.documents.filter((d) => d.status === 'failed').length
      const rejectedCount = result.rejected.length

      const parts: string[] = []
      if (readyCount > 0) parts.push(`${readyCount} ready for investigation`)
      if (failedCount > 0) parts.push(`${failedCount} failed to process`)
      if (rejectedCount > 0) parts.push(`${rejectedCount} rejected (${result.rejected.map((r) => r.error).join('; ')})`)
      setUploadSummary(parts.length > 0 ? parts.join(', ') : 'No files were uploaded.')

      setRefreshToken((t) => t + 1)
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : 'Something went wrong during upload.')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  if (id === null) {
    return (
      <AppShell breadcrumb={[{ label: 'Home', to: '/' }, { label: 'Projects', to: '/projects' }, { label: 'Invalid project' }]}>
        <ErrorState
          title="Invalid project id"
          message={`"${projectId}" is not a valid project id.`}
        />
      </AppShell>
    )
  }

  const projectName = projectQuery.status === 'success' ? projectQuery.data.name : undefined
  const projectCreatedAt = projectQuery.status === 'success' ? projectQuery.data.created_at : undefined
  const investigations = investigationsQuery.status === 'success' ? investigationsQuery.data : []
  const recentInvestigations = investigations.slice(0, 3)
  const documentCount = documentsQuery.status === 'success' ? documentsQuery.data.length : undefined

  return (
    <AppShell
      breadcrumb={[
        { label: 'Home', to: '/' },
        { label: 'Projects', to: '/projects' },
        { label: projectName ?? `Project ${id}` },
      ]}
    >
      <p className={styles.kicker}>Project Record</p>
      <h1 className={styles.title}>{projectName ?? `Project ${id}`}</h1>
      <div className={styles.headerMeta}>
        <Muted>This is the project record ClaimTrace will investigate.</Muted>
        {projectCreatedAt && <span className={styles.headerDate}>Created {formatDate(projectCreatedAt)}</span>}
      </div>

      <div className={styles.sections}>
        <div className={styles.section}>
          <div className={styles.sectionHeaderRow}>
            <SectionLabel>
              Investigations{investigations.length > 0 ? ` (${investigations.length})` : ''}
            </SectionLabel>
            <LinkButton to={`/projects/${id}/investigations`} variant="primary">
              Start Investigation
            </LinkButton>
          </div>
          <p className={styles.sectionBody}>
            Ask a question about this project's record, or revisit one already asked.
          </p>

          {investigationsQuery.status === 'loading' && <LoadingState label="Loading investigations…" />}
          {recentInvestigations.length > 0 && (
            <ul className={styles.recentList}>
              {recentInvestigations.map((inv) => (
                <li key={inv.id}>
                  <button
                    className={styles.recentRow}
                    onClick={() => navigate(`/projects/${id}/investigations/${inv.id}`)}
                  >
                    <span className={styles.recentQuestion}>{inv.query}</span>
                    <span className={styles.recentTrailing}>
                      <Muted>{formatDate(inv.created_at)}</Muted>
                      <InvestigationStatusBadge status={inv.status} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {investigations.length > 3 && (
            <Link to={`/projects/${id}/investigations`} className={styles.viewAllLink}>
              View all {investigations.length} investigations →
            </Link>
          )}
        </div>
      </div>

      <div className={styles.documentsSection}>
        <div className={styles.documentsHeader}>
          <SectionLabel>Documents{documentCount !== undefined ? ` (${documentCount})` : ''}</SectionLabel>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            multiple
            className={styles.hiddenInput}
            onChange={(e) => void handleFileChange(e)}
            disabled={uploading}
          />
          <Button variant="primary" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? 'Uploading…' : 'Add Documents'}
          </Button>
        </div>
        <p className={styles.sectionBody}>
          Upload PDF or Word (.docx) documents to add them to this project's record. Once
          processed, they become available to every investigation asked against this project.
        </p>
        {uploadSummary && <p className={styles.uploadSummary}>{uploadSummary}</p>}
        {uploadError && <p className={styles.uploadError}>{uploadError}</p>}

        {documentsQuery.status === 'loading' && <LoadingState label="Loading documents…" />}
        {documentsQuery.status === 'error' && (
          <ErrorState message={`Could not load documents for this project: ${documentsQuery.error}`} />
        )}
        {documentsQuery.status === 'success' && documentsQuery.data.length === 0 && (
          <p className={styles.emptyDocuments}>
            <Muted>No documents have been added to this project yet.</Muted>
          </p>
        )}
        {documentsQuery.status === 'success' && documentsQuery.data.length > 0 && (
          <ul className={styles.docList}>
            {documentsQuery.data.map((doc) => (
              <DocumentRow key={doc.id} doc={doc} projectId={id} />
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  )
}

/** Only a 'ready' document has real, servable chunks/text — and only a
 * 'ready' document is guaranteed to have a servable raw PDF at all (see
 * app/api/routes/document_file.py: the PDF is located via the stored
 * extracted-text path, which is only ever set once extraction succeeds).
 * A processing/failed row keeps its status badge but isn't made to look
 * openable, rather than linking to a viewer that can only fail. */
function DocumentRow({ doc, projectId }: { doc: DocumentSummary; projectId: number }) {
  const isOpenable = doc.status === 'ready'

  const body = (
    <>
      <div className={styles.docMain}>
        <span className={styles.docName}>{doc.filename}</span>
        <div className={styles.docMeta}>
          {doc.doc_type ? <Badge tone="neutral">{doc.doc_type}</Badge> : <Muted>Type not recorded</Muted>}
          <span className={styles.docDate}>{doc.doc_date ?? <Muted>Date not recorded</Muted>}</span>
        </div>
        {doc.status === 'failed' && doc.processing_error && (
          <p className={styles.docError}>{doc.processing_error}</p>
        )}
      </div>
      <div className={styles.docTrailing}>
        <DocumentStatusBadge status={doc.status} />
        {isOpenable && <span className={styles.docOpenHint}>Open source →</span>}
      </div>
    </>
  )

  if (!isOpenable) {
    return <li className={styles.docRow}>{body}</li>
  }

  return (
    <li>
      <Link
        to={`/projects/${projectId}/documents/${doc.id}/source`}
        className={`${styles.docRow} ${styles.docRowOpenable}`}
      >
        {body}
      </Link>
    </li>
  )
}

function DocumentStatusBadge({ status }: { status: DocumentSummary['status'] }) {
  if (status === 'ready') return <Badge tone="green">Ready</Badge>
  if (status === 'failed') return <Badge tone="red">Failed</Badge>
  return <Badge tone="neutral">Processing…</Badge>
}

function InvestigationStatusBadge({ status }: { status: InvestigationStatus }) {
  if (status === 'completed') return <Badge tone="green">Complete</Badge>
  if (status === 'failed') return <Badge tone="red">Not completed</Badge>
  return <Badge tone="neutral">In progress</Badge>
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return iso
  }
}

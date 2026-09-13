import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { SectionLabel, Muted } from '../components/ui/Typography'
import { Panel } from '../components/ui/Panel'
import { Badge } from '../components/ui/Badge'
import { LinkButton } from '../components/ui/LinkButton'
import { ErrorState, LoadingState } from '../components/ui/StateViews'
import { parseProjectId } from '../lib/projectDirectory'
import { useProject } from '../lib/useProject'
import { useApiQuery } from '../api/useApi'
import { getProjectDocument, fetchDocumentFileBlobUrl, getDocumentFileUrl } from '../api/client'
import type { DocumentSummary } from '../api/types'
import { isDocxFilename } from '../lib/documentFormat'
import styles from './SourceViewPage.module.css'

type PdfState = { status: 'checking' } | { status: 'available'; blobUrl: string } | { status: 'unavailable' }

/**
 * Document Viewer entry point from Project -> Documents (Phase 3 UX fix).
 * Reuses the exact same PDF-loading primitive as the citation-based
 * SourceViewPage (fetchDocumentFileBlobUrl -> GET
 * /projects/{project_id}/documents/{document_id}/file) and the same visual
 * shell (SourceViewPage.module.css) — no second PDF viewer, no duplicated
 * loading logic, no new backend endpoint.
 *
 * Unlike SourceViewPage, there is no citation here: a project's document
 * register is browsed directly, not through an investigation's evidence.
 * So this opens the PDF at its natural first page (no #page= fragment is
 * appended) rather than fabricating a cited page, and the metadata panel
 * shows only the document's own real fields (type/date/status) — never an
 * invented excerpt or relevance score.
 *
 * Project isolation: the document is fetched via getProjectDocument(id,
 * docId), which hits GET /projects/{project_id}/documents/{document_id} —
 * the same project-scoped lookup used everywhere else in Phase 3, which
 * 404s (indistinguishably from "doesn't exist") if the document belongs to
 * a different project. Like SourceViewPage, this page never trusts a
 * document id in isolation — it is always resolved against this page's own
 * URL project id first, so a project id / document id mismatch can never
 * surface another project's file.
 */
export function DocumentSourceViewPage() {
  const { projectId, documentId } = useParams<{ projectId: string; documentId: string }>()
  const id = parseProjectId(projectId)
  const docId = parseProjectId(documentId)
  const projectQuery = useProject(id)
  const projectName = projectQuery.status === 'success' ? projectQuery.data.name : undefined

  const documentQuery = useApiQuery(
    () =>
      id === null || docId === null
        ? Promise.reject(new Error('invalid reference'))
        : getProjectDocument(id, docId),
    [id, docId],
  )

  // Same fetch-once-as-blob pattern as SourceViewPage, for the same reason
  // (a single real GET serves as both the availability check and the
  // render source). Declared unconditionally, before any early return.
  // Gated on documentQuery having already succeeded — mirroring
  // SourceViewPage's own `!citation` guard — so a document id that doesn't
  // belong to this project (already rejected by the metadata lookup) never
  // triggers a second, redundant /file request against the wrong project.
  const [pdfState, setPdfState] = useState<PdfState>({ status: 'checking' })
  useEffect(() => {
    if (id === null || docId === null || documentQuery.status !== 'success') return
    let cancelled = false
    let createdBlobUrl: string | null = null
    // eslint-disable-next-line react/set-state-in-effect
    setPdfState({ status: 'checking' })
    fetchDocumentFileBlobUrl(id, docId).then((blobUrl) => {
      if (cancelled) {
        if (blobUrl) URL.revokeObjectURL(blobUrl)
        return
      }
      if (blobUrl) {
        createdBlobUrl = blobUrl
        setPdfState({ status: 'available', blobUrl })
      } else {
        setPdfState({ status: 'unavailable' })
      }
    })
    return () => {
      cancelled = true
      if (createdBlobUrl) URL.revokeObjectURL(createdBlobUrl)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, docId, documentQuery.status])

  const breadcrumbBase = [
    { label: 'Home', to: '/' },
    { label: 'Projects', to: '/projects' },
  ]

  if (id === null) {
    return (
      <AppShell breadcrumb={[...breadcrumbBase, { label: 'Invalid project' }]}>
        <ErrorState title="Invalid project id" message={`"${projectId}" is not a valid project id.`} />
      </AppShell>
    )
  }

  const projectCrumb = { label: projectName ?? `Project ${id}`, to: `/projects/${id}` }

  if (docId === null) {
    return (
      <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: 'Invalid document' }]}>
        <ErrorState
          title="Invalid document reference"
          message={`"${documentId}" is not a valid document reference.`}
        />
      </AppShell>
    )
  }

  if (documentQuery.status === 'loading') {
    return (
      <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: 'Document' }]}>
        <LoadingState label="Loading document…" />
      </AppShell>
    )
  }

  if (documentQuery.status === 'error') {
    return (
      <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: 'Document' }]}>
        <ErrorState
          title="This document is not available"
          message="This document could not be found for this project. It may not exist, or it may belong to a different project."
        />
      </AppShell>
    )
  }

  const document = documentQuery.data
  const isDocx = isDocxFilename(document.filename)
  const pdfHref = pdfState.status === 'available' ? pdfState.blobUrl : null

  return (
    <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: document.filename }]} wide>
      <p className={styles.kicker}>Source Document</p>
      <h1 className={styles.title}>{document.filename}</h1>
      <p className={styles.intro}>
        {isDocx
          ? "This is a Word document. ClaimTrace does not render Word documents in-browser — download the original document below to view it."
          : "This is the original document as stored in this project's record, opened at its first page. There is no cited passage here — this document was opened directly from the project's document register, not from an investigation's evidence."}
      </p>

      <div className={styles.grid}>
        <Panel className={styles.pdfPanel}>
          {isDocx ? (
            <div className={styles.pdfPanelContent}>
              <SectionLabel>Original Document</SectionLabel>
              <p className={styles.docxNotice}>
                Word documents aren't previewed in-browser. Download the original file to view its
                full formatted content.
              </p>
              <LinkButton variant="secondary" to={getDocumentFileUrl(id, docId)} reloadDocument>
                Download original document
              </LinkButton>
            </div>
          ) : (
            <>
              {pdfState.status === 'checking' && (
                <div className={styles.pdfPanelContent}>
                  <LoadingState label="Loading document…" />
                </div>
              )}
              {pdfState.status === 'unavailable' && (
                <div className={styles.pdfPanelContent}>
                  <ErrorState
                    title="Document could not be opened"
                    message="The original PDF for this document could not be loaded."
                  />
                </div>
              )}
              {pdfHref && (
                <iframe key={pdfHref} src={pdfHref} title={`Document: ${document.filename}`} className={styles.pdfFrame} />
              )}
            </>
          )}
        </Panel>

        <Panel className={styles.metaPanel}>
          <SectionLabel>Document</SectionLabel>
          <dl className={styles.metaList}>
            <div>
              <dt>Type</dt>
              <dd>{document.doc_type ?? <Muted>Not recorded</Muted>}</dd>
            </div>
            <div>
              <dt>Date</dt>
              <dd>{document.doc_date ?? <Muted>Not recorded</Muted>}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>
                <DocumentStatusBadge status={document.status} />
              </dd>
            </div>
          </dl>

          <LinkButton to={`/projects/${id}`} variant="secondary" className={styles.backLink}>
            ← Back to project
          </LinkButton>
        </Panel>
      </div>
    </AppShell>
  )
}

function DocumentStatusBadge({ status }: { status: DocumentSummary['status'] }) {
  if (status === 'ready') return <Badge tone="green">Ready</Badge>
  if (status === 'failed') return <Badge tone="red">Failed</Badge>
  return <Badge tone="neutral">Processing…</Badge>
}

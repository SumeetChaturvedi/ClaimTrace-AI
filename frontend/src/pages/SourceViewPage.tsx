import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { SectionLabel, Prose, Muted } from '../components/ui/Typography'
import { Panel } from '../components/ui/Panel'
import { Badge } from '../components/ui/Badge'
import { LinkButton } from '../components/ui/LinkButton'
import { ErrorState, LoadingState } from '../components/ui/StateViews'
import { parseProjectId } from '../lib/projectDirectory'
import { parseInvestigationId } from '../lib/investigationId'
import { useInvestigationRecord } from '../lib/useInvestigationRecord'
import { useProject } from '../lib/useProject'
import { listAllDocuments, fetchDocumentFileBlobUrl, getDocumentFileUrl } from '../api/client'
import type { DocumentSummary } from '../api/types'
import { isDocxFilename, citationLocationLabel } from '../lib/documentFormat'
import styles from './SourceViewPage.module.css'

type PdfState = { status: 'checking' } | { status: 'available'; blobUrl: string } | { status: 'unavailable' }

/**
 * The Source View for one cited excerpt. Backed by a real PDF via
 * GET /projects/{project_id}/documents/{document_id}/file, rendered with
 * the browser's native PDF viewer, no PDF.js or other dependency.
 *
 * The citation is looked up only inside the already-fetched, already
 * project-validated persisted investigation record (useInvestigationRecord
 * — the same hook and the same backend-enforced project isolation the
 * Workspace uses; see its docstring) — never independently by document id
 * — and the PDF URL is built from that same validated project id plus
 * citation.document_id (there is no document id route param). This is the
 * load-bearing project-isolation guarantee: the backend receives exactly
 * the project context this page already verified against the
 * investigation, never the raw URL alone.
 *
 * Format-aware (Phase 7: Multi-Format Evidence): fetchDocumentFileBlobUrl
 * already only resolves for a real `application/pdf` response, so it
 * naturally comes back "unavailable" for a DOCX-derived citation without
 * any change to that function. Rather than show that as an error, this
 * page detects a DOCX citation up front (via the cited document's own
 * filename — see lib/documentFormat.ts) and renders a dedicated "Extracted
 * Evidence" panel instead of attempting a PDF iframe: the cited passage is
 * already shown in the meta panel regardless of format, and a "Download
 * original document" link serves the real .docx file via the same
 * project-scoped file endpoint, so nothing is fabricated and the original
 * document is never implied to be something ClaimTrace can preview inline.
 * The PDF branch below is completely unchanged for `.pdf` citations.
 */
export function SourceViewPage() {
  const { projectId, investigationId, chunkId } = useParams<{
    projectId: string
    investigationId: string
    chunkId: string
  }>()
  const id = parseProjectId(projectId)
  const parsedInvestigationId = investigationId ? parseInvestigationId(investigationId) : null
  // Same non-negative-integer format the project id needs; reused as-is.
  const chunkIdNum = parseProjectId(chunkId)
  const projectQuery = useProject(id)
  const projectName = projectQuery.status === 'success' ? projectQuery.data.name : undefined

  const { state } = useInvestigationRecord(id, parsedInvestigationId)
  const citation = state.status === 'ready' ? state.record.citations.find((c) => c.chunk_id === chunkIdNum) : undefined

  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null)
  useEffect(() => {
    listAllDocuments()
      .then(setDocuments)
      .catch(() => {
        // Non-critical: falls back to "Document #id" below.
      })
  }, [])

  // Fetches the real PDF once and keeps it as a local blob URL — a single
  // real request that's both the availability check and the render
  // source (a HEAD-based pre-check was tried first and confirmed, via a
  // real request against the live endpoint, to return 405: it's a
  // GET-only route). Declared unconditionally (rules of hooks) even
  // though it only does anything once `id` and `citation` are both
  // resolved — every early-return guard below happens after this.
  const [pdfState, setPdfState] = useState<PdfState>({ status: 'checking' })
  useEffect(() => {
    if (id === null || !citation) return
    let cancelled = false
    let createdBlobUrl: string | null = null
    // Resets to "checking" for the (rare) case this effect re-runs without
    // a full remount — e.g. browser back/forward between two /source/:id
    // URLs of the same investigation — so a stale status is never shown
    // while the new document's real fetch is in flight.
    // eslint-disable-next-line react/set-state-in-effect
    setPdfState({ status: 'checking' })
    fetchDocumentFileBlobUrl(id, citation.document_id).then((blobUrl) => {
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
    // Deliberately depends on citation.document_id, not the whole citation
    // object, so a new-but-equivalent citation reference doesn't re-trigger
    // a real fetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, citation?.document_id])

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

  const workspaceBreadcrumb = [
    ...breadcrumbBase,
    { label: projectName ?? `Project ${id}`, to: `/projects/${id}` },
    { label: 'Investigations', to: `/projects/${id}/investigations` },
  ]

  if (parsedInvestigationId === null) {
    return (
      <AppShell breadcrumb={[...workspaceBreadcrumb, { label: 'Source' }]}>
        <ErrorState
          title="Invalid investigation reference"
          message={`"${investigationId}" is not a valid investigation reference.`}
        />
      </AppShell>
    )
  }

  const investigationCrumb = {
    label: 'Workspace',
    to: `/projects/${id}/investigations/${investigationId}`,
  }

  if (state.status === 'loading') {
    return (
      <AppShell breadcrumb={[...workspaceBreadcrumb, investigationCrumb, { label: 'Source' }]}>
        <LoadingState label="Loading investigation…" />
      </AppShell>
    )
  }

  // Evidence-integrity guard: a nonexistent investigation and one that
  // belongs to a different project are indistinguishable here by design —
  // the backend returns the same 404 for both, see useInvestigationRecord —
  // so this never renders a citation, or requests its document's PDF,
  // under the wrong project's context.
  if (state.status === 'not-found') {
    return (
      <AppShell breadcrumb={[...workspaceBreadcrumb, investigationCrumb, { label: 'Source' }]}>
        <ErrorState
          title="This source is not available"
          message="This investigation could not be found for this project, so its citations can't be looked up. It may not exist, or it may belong to a different project."
        />
      </AppShell>
    )
  }

  if (state.status === 'error') {
    return (
      <AppShell breadcrumb={[...workspaceBreadcrumb, investigationCrumb, { label: 'Source' }]}>
        <ErrorState title="Could not load this investigation" message={state.error} />
      </AppShell>
    )
  }

  const record = state.record

  if (record.status !== 'completed') {
    return (
      <AppShell breadcrumb={[...workspaceBreadcrumb, investigationCrumb, { label: 'Source' }]}>
        <ErrorState
          title="This investigation has no citations yet"
          message="This investigation hasn't finished, so there's no citation to show a source for. Return to the workspace to check its status."
        />
      </AppShell>
    )
  }

  if (chunkIdNum === null) {
    return (
      <AppShell breadcrumb={[...workspaceBreadcrumb, investigationCrumb, { label: 'Source' }]}>
        <ErrorState title="Invalid citation reference" message={`"${chunkId}" is not a valid citation reference.`} />
      </AppShell>
    )
  }

  if (!citation) {
    return (
      <AppShell breadcrumb={[...workspaceBreadcrumb, investigationCrumb, { label: 'Source' }]}>
        <ErrorState
          title="Citation not found in this investigation"
          message="This investigation's citations don't include one matching this reference. It may belong to a different investigation, so nothing is shown here."
        />
      </AppShell>
    )
  }

  const document = documents?.find((d) => d.id === citation.document_id)
  const documentLabel = document?.filename ?? `Document #${citation.document_id}`
  const isDocx = isDocxFilename(document?.filename)

  // The page-position fragment is appended to the local blob URL, not the
  // network URL — Chrome/Firefox/Safari's native PDF viewer honors
  // #page=N regardless of the URL scheme it's given.
  const pdfHref =
    pdfState.status === 'available'
      ? citation.page != null
        ? `${pdfState.blobUrl}#page=${citation.page}`
        : pdfState.blobUrl
      : null

  return (
    <AppShell breadcrumb={[...workspaceBreadcrumb, investigationCrumb, { label: documentLabel }]} wide>
      <p className={styles.kicker}>Evidence Source — Inspecting Citation</p>
      <h1 className={styles.title}>{documentLabel}</h1>
      <p className={styles.intro}>
        {isDocx
          ? 'This is the extracted passage ClaimTrace indexed from the original Word document. ClaimTrace does not render Word documents in-browser — download the original document below to view its full formatted content.'
          : 'This is the original source document for the cited evidence. It opens at the page ClaimTrace cited, where known.'}
      </p>

      <div className={styles.grid}>
        <Panel className={styles.pdfPanel}>
          {isDocx ? (
            <div className={styles.pdfPanelContent}>
              <SectionLabel>Extracted Evidence</SectionLabel>
              <p className={styles.docxNotice}>
                This is extracted evidence, not the original source document — Word documents
                aren't rendered in-browser. The exact cited passage is shown alongside, in Cited
                passage.
              </p>
              <LinkButton
                variant="secondary"
                to={getDocumentFileUrl(id, citation.document_id)}
                reloadDocument
              >
                Download original document
              </LinkButton>
            </div>
          ) : (
            <>
              {pdfState.status === 'checking' && (
                <div className={styles.pdfPanelContent}>
                  <LoadingState label="Loading source document…" />
                </div>
              )}
              {pdfState.status === 'unavailable' && (
                <div className={styles.pdfPanelContent}>
                  <ErrorState
                    title="Source document could not be opened"
                    message="The original PDF for this document could not be loaded. The cited passage is still shown below, since it doesn't depend on the file being available."
                  />
                </div>
              )}
              {pdfHref && (
                <iframe
                  key={pdfHref}
                  src={pdfHref}
                  title={`Source PDF: ${documentLabel}`}
                  className={styles.pdfFrame}
                />
              )}
            </>
          )}
        </Panel>

        <Panel className={styles.metaPanel}>
          <SectionLabel>Source</SectionLabel>
          {documents === null && <LoadingState label="Resolving document metadata…" />}
          <dl className={styles.metaList}>
            <div>
              <dt>Document</dt>
              <dd>{documentLabel}</dd>
            </div>
            <div>
              <dt>Type</dt>
              <dd>{document?.doc_type ?? <Muted>Not recorded</Muted>}</dd>
            </div>
            <div>
              <dt>Document date</dt>
              <dd>{document?.doc_date ?? <Muted>Not recorded</Muted>}</dd>
            </div>
            <div>
              <dt>Cited {citationLocationLabel(document?.filename).toLowerCase()}</dt>
              <dd>{citation.page ?? <Muted>Not recorded</Muted>}</dd>
            </div>
            <div>
              <dt>Passage reference</dt>
              <dd>{citation.chunk_id}</dd>
            </div>
            <div>
              <dt>Relevance score</dt>
              <dd>{citation.relevance_score.toFixed(2)}</dd>
            </div>
          </dl>

          <div className={styles.excerptSection}>
            <SectionLabel>Cited passage</SectionLabel>
            <Badge tone="neutral">Exact excerpt used in this investigation</Badge>
            <Prose>{citation.chunk_text ?? <Muted>No excerpt text was returned for this citation.</Muted>}</Prose>
          </div>

          <LinkButton to={`/projects/${id}/investigations/${investigationId}`} variant="secondary" className={styles.backLink}>
            ← Back to investigation
          </LinkButton>
        </Panel>
      </div>
    </AppShell>
  )
}

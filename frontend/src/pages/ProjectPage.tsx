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
import { useRevealRefs } from '../lib/useRevealOnScroll'
import { ApiError, listInvestigations, listProjectDocuments, uploadProjectDocuments } from '../api/client'
import { useApiQuery } from '../api/useApi'
import type { DocumentSummary, InvestigationRecord, InvestigationStatus } from '../api/types'
import styles from './ProjectPage.module.css'

/**
 * Project Overview (Phase 3 origin; "Elegantly Decorative" editorial
 * redesign). Every fact shown — project name, created date, investigation
 * questions/status/dates, document filenames/types/dates/status — is real
 * data from GET /projects/{id}, GET /projects/{id}/investigations, and
 * GET /projects/{id}/documents; nothing here is fetched or computed
 * differently than before this visual pass. The only new "value" on the
 * page is the project's own real id, reused honestly as both the rail's
 * and header's ghosted numeral/reference mark — never a fabricated index.
 *
 * Decorative elements (header line art, rail line art, the evidence-trace
 * motif, the ghosted numeral) are all deterministic and marked
 * aria-hidden — they carry no information a screen reader user would
 * lose, and they never imply a metric, count, or fact beyond what the
 * page's real text already states.
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
  const investigationsQuery = useApiQuery(
    () => (id === null ? Promise.resolve<InvestigationRecord[]>([]) : listInvestigations(id)),
    [id, refreshToken],
  )
  const motifRef = useRevealRefs<HTMLDivElement>(1, styles.motifVisible)

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
      navProject={{
        id,
        name: projectName ?? `Project ${id}`,
        investigationCount: investigationsQuery.status === 'success' ? investigations.length : undefined,
        documentCount,
        active: 'overview',
      }}
      wide
    >
      <div className={styles.page}>
      <ProjectHeader id={id} name={projectName} createdAt={projectCreatedAt} />

      <section className={styles.investigationsSection}>
        <div className={styles.sectionRule}>
          <span className={styles.sectionRuleNode} aria-hidden="true" />
          <SectionLabel>
            Investigations{investigations.length > 0 ? ` (${investigations.length})` : ''}
          </SectionLabel>
          <span className={styles.sectionRuleLine} aria-hidden="true" />
          <LinkButton to={`/projects/${id}/investigations`} variant="primary">
            Start Investigation
          </LinkButton>
        </div>
        <p className={styles.sectionBody}>
          Ask a question about this project's record, or revisit one already asked.
        </p>

        {investigationsQuery.status === 'loading' && <LoadingState label="Loading investigations…" />}
        {investigationsQuery.status === 'success' && investigations.length === 0 && (
          <Muted>No investigations have been run for this project yet.</Muted>
        )}
        {recentInvestigations.length > 0 && (
          <ol className={styles.investigationRegister}>
            {recentInvestigations.map((inv, i) => (
              <InvestigationRow
                key={inv.id}
                inv={inv}
                index={i}
                onOpen={() => navigate(`/projects/${id}/investigations/${inv.id}`)}
              />
            ))}
          </ol>
        )}
        {investigations.length > 3 && (
          <Link to={`/projects/${id}/investigations`} className={styles.viewAllLink}>
            View all {investigations.length} investigations →
          </Link>
        )}
      </section>

      <div className={styles.motif} ref={motifRef(0)} aria-hidden="true">
        <EvidenceMotif />
      </div>

      <section className={styles.documentsSection}>
        <div className={styles.sectionRule}>
          <span className={styles.sectionRuleNodeAlt} aria-hidden="true" />
          <SectionLabel>
            Document Register{documentCount !== undefined ? ` · ${String(documentCount).padStart(2, '0')}` : ''}
          </SectionLabel>
          <span className={styles.sectionRuleLine} aria-hidden="true" />
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
          <ol className={styles.documentRegister}>
            {documentsQuery.data.map((doc, i) => (
              <DocumentRow key={doc.id} doc={doc} projectId={id} index={i} />
            ))}
          </ol>
        )}
      </section>
      </div>
    </AppShell>
  )
}

/** The project record header: real title/date, plus three deterministic
 * decorative elements — a large ghosted numeral (the project's own real
 * id, never a fabricated index), a low-opacity architectural line drawing
 * cropped behind the content, and two small technical annotations
 * ("Project Record" / "Ref. 0N", the second also the real id). */
function ProjectHeader({ id, name, createdAt }: { id: number; name?: string; createdAt?: string }) {
  const ref = String(id).padStart(2, '0')
  return (
    <header className={styles.recordHeader}>
      <HeaderArt />
      <span className={styles.ghostNumeral} aria-hidden="true">
        {ref}
      </span>
      <div className={styles.headerContent}>
        <div className={styles.headerAnnotations}>
          <span className={styles.headerKicker}>Project Record</span>
          <span className={styles.headerAnnotationDivider} aria-hidden="true" />
          <span className={styles.headerAnnotation}>Ref. {ref}</span>
        </div>
        <h1 className={styles.title}>{name ?? `Project ${id}`}</h1>
        <div className={styles.headerMeta}>
          <Muted>This is the project record ClaimTrace will investigate.</Muted>
          {createdAt && <span className={styles.headerDate}>Created {formatDate(createdAt)}</span>}
        </div>
      </div>
    </header>
  )
}

/** Low-opacity architectural line drawing behind the header — a partial
 * bridge elevation (deck, one pier, diagonal bracing) extending past the
 * header's own edges, cropped by its container's overflow: hidden. Purely
 * decorative and static: it never animates, never competes with the real
 * title text sitting above it. */
function HeaderArt() {
  return (
    <svg className={styles.headerArt} viewBox="0 0 1200 320" preserveAspectRatio="xMaxYMid slice" aria-hidden="true">
      <g stroke="currentColor" strokeWidth="1" fill="none">
        <line x1="500" y1="150" x2="1300" y2="150" />
        <line x1="500" y1="164" x2="1300" y2="164" />
        <path d="M 500 164 L 560 118 L 620 164 L 680 118 L 740 164 L 800 118 L 860 164 L 920 118 L 980 164 L 1040 118 L 1100 164 L 1160 118 L 1220 164" />
        <line x1="620" y1="164" x2="620" y2="300" strokeWidth="3" />
        <line x1="980" y1="164" x2="980" y2="300" strokeWidth="3" />
      </g>
    </svg>
  )
}

/** The QUESTION → EVIDENCE → FINDING → SOURCE motif (Section 14): a
 * deterministic, purely decorative brand graphic describing ClaimTrace's
 * fixed investigation methodology — not a rendering of this project's
 * actual data, and not a second explanation of it (the real text already
 * describing this flow lives in the surrounding real copy). Reveals once
 * on scroll into view via the `motifVisible` class (see
 * useRevealOnScroll's existing one-shot IntersectionObserver — reused
 * unchanged, not reimplemented) and never animates again; under
 * prefers-reduced-motion the hook marks it visible immediately. */
function EvidenceMotif() {
  const steps = ['Question', 'Evidence', 'Finding', 'Source']
  return (
    <>
      <svg className={styles.motifSvg} viewBox="0 0 800 30" preserveAspectRatio="none" aria-hidden="true">
        <line x1="20" y1="15" x2="780" y2="15" className={styles.motifLine} />
        {steps.map((_, i) => (
          <circle key={i} cx={20 + i * (760 / 3)} cy="15" r="5" className={styles.motifNode} />
        ))}
      </svg>
      <div className={styles.motifLabels}>
        {steps.map((step) => (
          <span key={step} className={styles.motifLabel}>
            {step}
          </span>
        ))}
      </div>
    </>
  )
}

/** Only a 'ready' document has real, servable chunks/text — and only a
 * 'ready' document is guaranteed to have a servable raw PDF at all (see
 * app/api/routes/document_file.py: the PDF is located via the stored
 * extracted-text path, which is only ever set once extraction succeeds).
 * A processing/failed row keeps its status badge but isn't made to look
 * openable, rather than linking to a viewer that can only fail. */
function DocumentRow({ doc, projectId, index }: { doc: DocumentSummary; projectId: number; index: number }) {
  const isOpenable = doc.status === 'ready'
  const ordinal = String(index + 1).padStart(3, '0')

  const body = (
    <>
      <span className={styles.registerOrdinal}>{ordinal}</span>
      <div className={styles.docMain}>
        <span className={styles.docName}>{doc.filename}</span>
        <div className={styles.docMeta}>
          {doc.doc_type ? <span className={styles.docMetaText}>{doc.doc_type}</span> : <Muted>Type not recorded</Muted>}
          <span className={styles.docMetaDot} aria-hidden="true" />
          <span className={styles.docMetaText}>{doc.doc_date ?? 'Date not recorded'}</span>
        </div>
        {doc.status === 'failed' && doc.processing_error && (
          <p className={styles.docError}>{doc.processing_error}</p>
        )}
      </div>
      <div className={styles.docTrailing}>
        <DocumentStatusBadge status={doc.status} />
        {isOpenable && <span className={styles.registerArrow}>→</span>}
      </div>
    </>
  )

  if (!isOpenable) {
    return <li className={styles.registerRow}>{body}</li>
  }

  return (
    <li>
      <Link
        to={`/projects/${projectId}/documents/${doc.id}/source`}
        className={`${styles.registerRow} ${styles.registerRowOpenable}`}
      >
        {body}
      </Link>
    </li>
  )
}

/** One row of the investigation register — ordinal, question (serif,
 * primary typography per the editorial direction), status + date. */
function InvestigationRow({ inv, index, onOpen }: { inv: InvestigationRecord; index: number; onOpen: () => void }) {
  const ordinal = String(index + 1).padStart(2, '0')
  return (
    <li>
      <button className={`${styles.registerRow} ${styles.investigationRow}`} onClick={onOpen}>
        <span className={styles.registerOrdinal}>{ordinal}</span>
        <div className={styles.investigationMain}>
          <p className={styles.investigationQuestion}>{inv.query}</p>
          <div className={styles.investigationMeta}>
            <InvestigationStatusBadge status={inv.status} />
            <span className={styles.investigationDate}>{formatDate(inv.created_at)}</span>
          </div>
        </div>
        <span className={styles.registerArrow}>→</span>
      </button>
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

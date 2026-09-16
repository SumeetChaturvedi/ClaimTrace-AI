import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { useInspector } from '../components/layout/InspectorContext'
import { Badge } from '../components/ui/Badge'
import { LinkButton } from '../components/ui/LinkButton'
import { StatBlock } from '../components/ui/StatBlock'
import { LoadingState, ErrorState } from '../components/ui/StateViews'
import { parseProjectId } from '../lib/projectDirectory'
import { parseInvestigationId } from '../lib/investigationId'
import { useInvestigationRecord } from '../lib/useInvestigationRecord'
import { useProject } from '../lib/useProject'
import { listAllDocuments, retryInvestigation } from '../api/client'
import type { DocumentSummary, InvestigationRecord, InvestigationResponse } from '../api/types'
import { WorkspaceNav } from './workspace/WorkspaceNav'
import type { WorkspaceTab } from './workspace/types'
import { FindingPanel } from './workspace/FindingPanel'
import { EvidencePanel } from './workspace/EvidencePanel'
import { DocumentsPanel } from './workspace/DocumentsPanel'
import { TracePanel } from './workspace/TracePanel'
import { TimelinePanel } from './workspace/TimelinePanel'
import { ContractPanel } from './workspace/ContractPanel'
import styles from './InvestigationWorkspacePage.module.css'

/**
 * Investigation Workspace (Phase 2: Persistent Investigations). Renders a
 * persisted InvestigationRecord fetched via useInvestigationRecord — a
 * plain GET, never a POST — so opening or reloading this page never
 * re-invokes Gemini. Creating a new investigation happens entirely on the
 * Investigations page (see InvestigationsPage.tsx); by the time the user
 * lands here, the record already exists (completed or failed) or, in the
 * rare multi-tab case, is still running and the hook polls it to
 * completion. This is also why the React-StrictMode double-POST guard
 * that Phase 1 needed is gone: there is no POST-on-mount effect left to
 * double-invoke.
 */
export function InvestigationWorkspacePage() {
  const { projectId, investigationId } = useParams<{ projectId: string; investigationId: string }>()
  const id = parseProjectId(projectId)
  const parsedInvestigationId = investigationId ? parseInvestigationId(investigationId) : null
  const projectQuery = useProject(id)
  const projectName = projectQuery.status === 'success' ? projectQuery.data.name : undefined
  const navigate = useNavigate()
  const { isOpen: inspectorOpen } = useInspector()

  const { state, refetch } = useInvestigationRecord(id, parsedInvestigationId)
  const [tab, setTab] = useState<WorkspaceTab>('finding')
  const [documentNames, setDocumentNames] = useState<Record<number, string>>({})
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null)
  const [retrying, setRetrying] = useState(false)

  // Resolve document metadata for citations. GET /documents is not
  // project-scoped, so this is used only to enrich display of ids we
  // already trust from citations — never to list "this project's docs".
  useEffect(() => {
    listAllDocuments()
      .then((docs) => {
        const map: Record<number, string> = {}
        for (const d of docs) map[d.id] = d.filename
        setDocumentNames(map)
        setDocuments(docs)
      })
      .catch(() => {
        // Non-critical: citations still render with "Document #id" fallback.
      })
  }, [])

  const citations = state.status === 'ready' ? state.record.citations : []
  const citationCount = citations.length
  const citedDocumentCount = new Set(citations.map((c) => c.document_id)).size

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

  if (parsedInvestigationId === null) {
    return (
      <AppShell breadcrumb={workspaceBreadcrumb(id, projectName)}>
        <ErrorState
          title="Invalid investigation reference"
          message={`"${investigationId}" is not a valid investigation reference.`}
        />
      </AppShell>
    )
  }

  if (state.status === 'loading') {
    return (
      <AppShell breadcrumb={workspaceBreadcrumb(id, projectName)}>
        <LoadingState label="Loading investigation…" />
      </AppShell>
    )
  }

  if (state.status === 'not-found') {
    return (
      <AppShell breadcrumb={workspaceBreadcrumb(id, projectName)}>
        <ErrorState
          title="Investigation not available"
          message="This investigation could not be found for this project. It may not exist, or it may belong to a different project. Start a new investigation from the Investigations page."
        />
      </AppShell>
    )
  }

  if (state.status === 'error') {
    return (
      <AppShell breadcrumb={workspaceBreadcrumb(id, projectName)}>
        <ErrorState title="Could not load this investigation" message={state.error} onRetry={refetch} />
      </AppShell>
    )
  }

  const record = state.record

  const handleRetry = async () => {
    setRetrying(true)
    try {
      await retryInvestigation(id, record.id)
    } catch {
      // The failure itself is already persisted server-side (see
      // InvestigationExecutionError) — refetch() below picks up the new
      // failed state regardless of whether this call threw.
    } finally {
      setRetrying(false)
      refetch()
    }
  }

  const response: InvestigationResponse = {
    answer: record.answer ?? '',
    citations: record.citations,
    reasoning_steps: record.reasoning_steps,
    timeline: record.timeline,
    contract_clauses: record.contract_clauses,
  }

  return (
    <AppShell breadcrumb={workspaceBreadcrumb(id, projectName)} fluid>
      <div className={styles.page}>
        <WorkspaceHeader record={record} projectId={id} citationCount={citationCount} citedDocumentCount={citedDocumentCount} />

        {record.status === 'running' && (
          <LoadingState label="Reviewing the project record and preparing a finding…" />
        )}

        {record.status === 'failed' && (
          <ErrorState
            title="We could not complete this investigation"
            message={retrying ? 'Retrying…' : 'Something went wrong while investigating this question. Please try again.'}
            onRetry={retrying ? undefined : () => void handleRetry()}
          />
        )}

        {record.status === 'completed' && (
          <div className={styles.workspaceGrid}>
            <WorkspaceNav active={tab} onChange={setTab} />
            <div className={styles.main}>
              <div className={styles.tabContent} key={tab}>
                {tab === 'finding' && (
                  <FindingPanel
                    response={response}
                    documentNames={documentNames}
                    documents={documents}
                    projectId={id}
                    investigationId={record.id}
                  />
                )}
                {tab === 'evidence' && (
                  <EvidencePanel
                    citations={response.citations}
                    documents={documents}
                    documentNames={documentNames}
                    projectId={id}
                    investigationId={record.id}
                  />
                )}
                {tab === 'documents' && (
                  <DocumentsPanel citations={response.citations} documents={documents} documentNames={documentNames} />
                )}
                {tab === 'trace' && <TracePanel steps={response.reasoning_steps} />}
                {tab === 'timeline' && (
                  <TimelinePanel
                    timeline={response.timeline}
                    documents={documents}
                    documentNames={documentNames}
                    projectId={id}
                    investigationId={record.id}
                  />
                )}
                {tab === 'contract' && <ContractPanel clauses={response.contract_clauses} />}
              </div>
            </div>
            {!inspectorOpen && (
              <TraceRail citationCount={citationCount} citedDocumentCount={citedDocumentCount} />
            )}
          </div>
        )}

        <p className={styles.backLink}>
          <button className={styles.linkButton} onClick={() => navigate(`/projects/${id}/investigations`)}>
            ← Back to Investigations
          </button>
        </p>
      </div>
    </AppShell>
  )
}

function WorkspaceHeader({
  record,
  projectId,
  citationCount,
  citedDocumentCount,
}: {
  record: InvestigationRecord
  projectId: number
  citationCount: number
  citedDocumentCount: number
}) {
  const recordMark = record.id.slice(0, 8).toUpperCase()

  return (
    <div className={styles.header}>
      <HeaderArt />
      <span className={styles.ghostMark} aria-hidden="true">{recordMark}</span>
      <div className={styles.headerContent}>
        <div className={styles.headerRule}>
          <span className={styles.headerRuleNode} aria-hidden="true" />
          <p className={styles.kicker}>Investigation</p>
          <span className={styles.headerRuleLine} aria-hidden="true" />
          <span className={styles.headerMark}>Record {recordMark}</span>
        </div>

        <h1 className={styles.question}>{record.query}</h1>

        <div className={styles.statusRow}>
          {record.status === 'running' && <Badge tone="neutral">Investigating…</Badge>}
          {record.status === 'completed' && <Badge tone="green">Investigation complete</Badge>}
          {record.status === 'failed' && <Badge tone="red">Investigation not completed</Badge>}
        </div>

        {record.status === 'completed' && (
          <div className={styles.headerFooter}>
            <div className={styles.statStrip}>
              <StatBlock label="Evidence items" value={citationCount} />
              <StatBlock label="Cited documents" value={citedDocumentCount} />
            </div>
            <LinkButton variant="secondary" to={`/projects/${projectId}/investigations/${record.id}/record`}>
              View Investigation Record
            </LinkButton>
          </div>
        )}
        {record.status === 'completed' && (
          <p className={styles.statNote}>
            Evidence-gap analysis and conflict detection aren't part of this investigation view yet.
          </p>
        )}
      </div>
    </div>
  )
}

/** Static, low-opacity forensic/technical decoration — registration ticks
 * and a partial drafting line, not a chart or diagram of real data. Purely
 * ambient identity for the header, matching the architectural line-art
 * already established on the Project Overview redesign. */
function HeaderArt() {
  return (
    <svg
      className={styles.headerArt}
      viewBox="0 0 1200 240"
      preserveAspectRatio="xMaxYMid slice"
      fill="none"
      aria-hidden="true"
    >
      <path d="M700 210 L900 40 L1200 40" stroke="currentColor" strokeWidth="1" />
      <path d="M760 210 L940 90 L1200 90" stroke="currentColor" strokeWidth="1" />
      {Array.from({ length: 9 }, (_, i) => (
        <line key={i} x1={860 + i * 40} y1={10} x2={860 + i * 40} y2={26} stroke="currentColor" strokeWidth="1" />
      ))}
      <rect x="1160" y="10" width="16" height="16" stroke="currentColor" strokeWidth="1" />
      <rect x="1160" y="214" width="16" height="16" stroke="currentColor" strokeWidth="1" />
    </svg>
  )
}

/** The Question → Evidence → Finding → Source motif, oriented vertically
 * and rendered as a decorative right-hand rail in the space the real
 * Inspector would otherwise occupy. Purely a brand/structural motif (see
 * task brief section 14) — it does not claim the counts shown next to
 * "Evidence" / "Source" are a causal breakdown, only the investigation's
 * own real evidence/document totals for scale. Hidden entirely once the
 * real Inspector opens, and below the width where it would crowd the main
 * workspace. */
function TraceRail({ citationCount, citedDocumentCount }: { citationCount: number; citedDocumentCount: number }) {
  const stages = [
    { label: 'Question' },
    { label: 'Evidence', hint: `${citationCount} item${citationCount === 1 ? '' : 's'}` },
    { label: 'Finding' },
    { label: 'Source', hint: `${citedDocumentCount} document${citedDocumentCount === 1 ? '' : 's'}` },
  ]
  return (
    <div className={styles.traceRail} aria-hidden="true">
      <div className={styles.traceRailInner}>
        {stages.map((stage, i) => (
          <div key={stage.label} className={styles.traceRailStage}>
            <span className={styles.traceRailLabel}>{stage.label}</span>
            {stage.hint && <span className={styles.traceRailHint}>{stage.hint}</span>}
            {i < stages.length - 1 && <span className={styles.traceRailConnector} />}
          </div>
        ))}
      </div>
    </div>
  )
}

function workspaceBreadcrumb(projectId: number, projectName: string | undefined) {
  return [
    { label: 'Home', to: '/' },
    { label: 'Projects', to: '/projects' },
    { label: projectName ?? `Project ${projectId}`, to: `/projects/${projectId}` },
    { label: 'Investigations', to: `/projects/${projectId}/investigations` },
    { label: 'Workspace' },
  ]
}

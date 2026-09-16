import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { SectionLabel, Muted } from '../components/ui/Typography'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { ErrorState, LoadingState } from '../components/ui/StateViews'
import { parseProjectId } from '../lib/projectDirectory'
import { useProject } from '../lib/useProject'
import { EXAMPLE_QUESTIONS } from '../lib/exampleQuestions'
import { ApiError, createInvestigation, listInvestigations } from '../api/client'
import { useApiQuery } from '../api/useApi'
import type { InvestigationRecord, InvestigationStatus } from '../api/types'
import styles from './InvestigationsPage.module.css'

export function InvestigationsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const id = parseProjectId(projectId)
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // Called unconditionally (rules of hooks) even when `id` is invalid — the
  // fetcher just no-ops in that case, since the invalid-id branch below
  // renders instead of this page's real content either way.
  const investigations = useApiQuery(
    () => (id === null ? Promise.resolve<InvestigationRecord[]>([]) : listInvestigations(id)),
    [id],
  )
  const projectQuery = useProject(id)

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
  const examples = EXAMPLE_QUESTIONS[id] ?? []
  const ref = String(id).padStart(2, '0')

  const startInvestigation = async (question: string) => {
    const trimmed = question.trim()
    if (!trimmed || submitting) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const record = await createInvestigation(id, { query: trimmed })
      navigate(`/projects/${id}/investigations/${record.id}`)
    } catch (err) {
      // A structured investigationId means the investigation WAS created
      // and persisted — only the engine run itself failed. Navigate to it
      // anyway so its failed state (and Retry) render normally, exactly as
      // if the create call had "succeeded" with a failed result.
      if (err instanceof ApiError && err.investigationId) {
        navigate(`/projects/${id}/investigations/${err.investigationId}`)
        return
      }
      setSubmitError(err instanceof ApiError ? err.message : 'Something went wrong.')
      setSubmitting(false)
    }
  }

  return (
    <AppShell
      breadcrumb={[
        { label: 'Home', to: '/' },
        { label: 'Projects', to: '/projects' },
        { label: projectName ?? `Project ${id}`, to: `/projects/${id}` },
        { label: 'Investigations' },
      ]}
      navProject={{
        id,
        name: projectName ?? `Project ${id}`,
        investigationCount: investigations.status === 'success' ? investigations.data.length : undefined,
        active: 'investigations',
      }}
      wide
    >
      <div className={styles.page}>
        <header className={styles.header}>
          <HeaderArt />
          <span className={styles.ghostMark} aria-hidden="true">{ref}</span>
          <div className={styles.headerContent}>
            <div className={styles.headerRule}>
              <span className={styles.headerRuleNode} aria-hidden="true" />
              <p className={styles.kicker}>Investigation Register</p>
              <span className={styles.headerRuleLine} aria-hidden="true" />
            </div>
            <h1 className={styles.title}>{projectName ?? `Project ${id}`}</h1>
            <p className={styles.subKicker}>Investigations</p>
            <p className={styles.intro}>
              Ask a question about this project's record. ClaimTrace will investigate the
              available evidence and return a cited finding.
            </p>
          </div>
        </header>

        <section className={styles.launchSection}>
          <div className={styles.launchMain}>
            <div className={styles.sectionRule}>
              <span className={styles.sectionRuleNode} aria-hidden="true" />
              <SectionLabel>Start an Investigation</SectionLabel>
              <span className={styles.sectionRuleLine} aria-hidden="true" />
            </div>
            <p className={styles.askPrompt}>What do you need to establish?</p>

            <form
              className={styles.form}
              onSubmit={(e) => {
                e.preventDefault()
                void startInvestigation(query)
              }}
            >
              <textarea
                className={styles.textarea}
                placeholder="e.g. Was the Contractor entitled to an extension of time for…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={3}
                disabled={submitting}
              />
              <div className={styles.formFooter}>
                <Button type="submit" variant="primary" className={styles.startButton} disabled={!query.trim() || submitting}>
                  {submitting ? (
                    'Investigating…'
                  ) : (
                    <>
                      Start Investigation <span className={styles.btnArrow} aria-hidden="true">→</span>
                    </>
                  )}
                </Button>
                {submitting && (
                  <Muted>ClaimTrace is investigating the project record. This usually takes a few seconds.</Muted>
                )}
              </div>
              {submitError && <p className={styles.submitError}>{submitError}</p>}
            </form>

            {examples.length > 0 && (
              <div className={styles.examples}>
                <Muted>Example questions for this project:</Muted>
                <div className={styles.exampleList}>
                  {examples.map((ex) => (
                    <button
                      key={ex.id}
                      className={styles.exampleChip}
                      onClick={() => void startInvestigation(ex.question)}
                      disabled={submitting}
                    >
                      {ex.question}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <TraceMotif />
        </section>

        <section className={styles.historySection}>
          <div className={styles.sectionRule}>
            <span className={styles.sectionRuleNodeAlt} aria-hidden="true" />
            <SectionLabel>
              Investigation History
              {investigations.status === 'success' && investigations.data.length > 0
                ? ` (${investigations.data.length})`
                : ''}
            </SectionLabel>
            <span className={styles.sectionRuleLine} aria-hidden="true" />
          </div>

          {investigations.status === 'loading' && <LoadingState label="Loading investigations…" />}
          {investigations.status === 'error' && (
            <ErrorState message={`Could not load investigations for this project: ${investigations.error}`} />
          )}

          {investigations.status === 'success' && investigations.data.length === 0 && (
            <div className={styles.emptyHistory}>
              <p className={styles.emptyHistoryTitle}>No investigations yet</p>
              <p className={styles.emptyHistoryBody}>
                Your first investigation will appear here once ClaimTrace has examined the
                project record.
              </p>
              <TraceMotif compact />
            </div>
          )}

          {investigations.status === 'success' && investigations.data.length > 0 && (
            <ol className={styles.historyList}>
              {investigations.data.map((inv, i) => (
                <HistoryRow
                  key={inv.id}
                  inv={inv}
                  index={i}
                  onOpen={() => navigate(`/projects/${id}/investigations/${inv.id}`)}
                />
              ))}
            </ol>
          )}
        </section>
      </div>
    </AppShell>
  )
}

function HistoryRow({
  inv,
  index,
  onOpen,
}: {
  inv: InvestigationRecord
  index: number
  onOpen: () => void
}) {
  return (
    <li>
      <button className={styles.historyRow} onClick={onOpen}>
        <div className={styles.historyTop}>
          <span className={styles.historyOrdinal}>{String(index + 1).padStart(2, '0')}</span>
          <span className={styles.historyRuleLine} aria-hidden="true" />
          <span className={styles.historyArrow} aria-hidden="true">→</span>
        </div>
        <p className={styles.historyQuestion}>{inv.query}</p>
        <div className={styles.historyMeta}>
          <StatusBadge status={inv.status} />
          <span className={styles.historyDate}>{formatTimestamp(inv.created_at)}</span>
        </div>
      </button>
    </li>
  )
}

/** Static, low-opacity technical decoration behind the header — a partial
 * survey/grid drawing (deliberately not the same bridge-elevation motif
 * already used on Project Overview and the Investigation Workspace, so
 * this page reads as a related but distinct part of the product). */
function HeaderArt() {
  return (
    <svg
      className={styles.headerArt}
      viewBox="0 0 1200 260"
      preserveAspectRatio="xMaxYMid slice"
      fill="none"
      aria-hidden="true"
    >
      <g stroke="currentColor" strokeWidth="1">
        {Array.from({ length: 6 }, (_, i) => (
          <line key={`v${i}`} x1={780 + i * 70} y1="20" x2={780 + i * 70} y2="240" />
        ))}
        {Array.from({ length: 4 }, (_, i) => (
          <line key={`h${i}`} x1="760" y1={40 + i * 60} x2="1200" y2={40 + i * 60} />
        ))}
      </g>
      <path d="M760 240 L1000 30 L1200 30" stroke="currentColor" strokeWidth="1.25" />
      <circle cx="1000" cy="30" r="4" stroke="currentColor" strokeWidth="1" fill="none" />
    </svg>
  )
}

/** ClaimTrace's brand/concept motif — Question → Evidence → Finding →
 * Source. Purely decorative: it illustrates the product's workflow
 * concept, not this project's actual evidence relationships, and carries
 * no counts or real data (see task brief section 17). */
function TraceMotif({ compact }: { compact?: boolean }) {
  const stages = ['Question', 'Evidence', 'Finding', 'Source']
  return (
    <div className={`${styles.motif} ${compact ? styles.motifCompact : ''}`} aria-hidden="true">
      {stages.map((label, i) => (
        <div key={label} className={styles.motifStage}>
          <span className={styles.motifLabel}>{label}</span>
          {i < stages.length - 1 && <span className={styles.motifConnector} />}
        </div>
      ))}
    </div>
  )
}

function StatusBadge({ status }: { status: InvestigationStatus }) {
  if (status === 'completed') return <Badge tone="green">Complete</Badge>
  if (status === 'failed') return <Badge tone="red">Not completed</Badge>
  return <Badge tone="neutral">In progress</Badge>
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}

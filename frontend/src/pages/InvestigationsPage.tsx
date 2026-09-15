import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { SectionLabel, Muted } from '../components/ui/Typography'
import { Panel } from '../components/ui/Panel'
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
    >
      <p className={styles.kicker}>{projectName ?? `Project ${id}`}</p>
      <h1 className={styles.title}>Investigations</h1>
      <p className={styles.intro}>
        Ask a question about this project's record. ClaimTrace will investigate the available
        evidence and return a cited finding.
      </p>

      <Panel className={styles.askPanel}>
        <div className={styles.askHeading}>
          <SectionLabel>Start an Investigation</SectionLabel>
          <p className={styles.askPrompt}>What do you need to establish?</p>
        </div>
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
          <Button type="submit" variant="primary" disabled={!query.trim() || submitting}>
            {submitting ? 'Investigating…' : 'Start Investigation'}
          </Button>
          {submitting && (
            <Muted>ClaimTrace is investigating the project record. This usually takes a few seconds.</Muted>
          )}
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
      </Panel>

      <div className={styles.recentHeader}>
        <SectionLabel>Investigation History</SectionLabel>
      </div>

      {investigations.status === 'loading' && <LoadingState label="Loading investigations…" />}
      {investigations.status === 'error' && (
        <ErrorState message={`Could not load investigations for this project: ${investigations.error}`} />
      )}
      {investigations.status === 'success' && investigations.data.length === 0 && (
        <p className={styles.emptyRecent}>
          <Muted>No investigations have been run for this project yet.</Muted>
        </p>
      )}
      {investigations.status === 'success' && investigations.data.length > 0 && (
        <ul className={styles.recentList}>
          {investigations.data.map((inv) => (
            <li key={inv.id}>
              <button className={styles.recentRow} onClick={() => navigate(`/projects/${id}/investigations/${inv.id}`)}>
                <span className={styles.recentMain}>
                  <span className={styles.recentQuestion}>{inv.query}</span>
                  <Muted>{formatTimestamp(inv.created_at)}</Muted>
                </span>
                <StatusBadge status={inv.status} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
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

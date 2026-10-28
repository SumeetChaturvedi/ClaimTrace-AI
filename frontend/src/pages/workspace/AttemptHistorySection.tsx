import { useState } from 'react'
import { ApiError, getInvestigationAttempts } from '../../api/client'
import type { DocumentSummary, InvestigationAttempt } from '../../api/types'
import { CitationList } from '../../components/evidence/CitationList'
import { Badge } from '../../components/ui/Badge'
import { ErrorState, LoadingState } from '../../components/ui/StateViews'
import { AnswerProse, Muted } from '../../components/ui/Typography'
import { stripMarkdownToPlainText } from '../../lib/markdown'
import styles from './AttemptHistorySection.module.css'

type LoadState =
  | { status: 'closed' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; attempts: InvestigationAttempt[] }

/**
 * Phase 2a (Preserve Investigation Attempt History) — a minimal, collapsed-
 * by-default "View previous attempts" section. Fetched lazily: nothing is
 * requested until the user actually opens it, so viewing an investigation
 * that has never been retried costs nothing extra. Deliberately a small
 * section within the existing Workspace, not a separate page per attempt —
 * every attempt's full answer/citations/diagnostics are inspectable inline
 * by expanding its row, reusing the exact same CitationList component the
 * current attempt's own Evidence/Finding panels already use (a past
 * attempt's citations are plain, self-contained Citation objects — opening
 * one in the Inspector works identically regardless of which attempt it
 * came from).
 */
export function AttemptHistorySection({
  projectId,
  investigationId,
  documentNames,
  documents,
}: {
  projectId: number
  investigationId: string
  documentNames: Record<number, string>
  documents: DocumentSummary[] | null
}) {
  const [state, setState] = useState<LoadState>({ status: 'closed' })
  const [expanded, setExpanded] = useState<number | null>(null)

  const load = () => {
    setState({ status: 'loading' })
    getInvestigationAttempts(projectId, investigationId)
      .then((attempts) => setState({ status: 'ready', attempts }))
      .catch((err) =>
        setState({ status: 'error', error: err instanceof ApiError ? err.message : 'Could not load attempt history.' }),
      )
  }

  if (state.status === 'closed') {
    return (
      <button type="button" className={styles.toggle} onClick={load}>
        View previous attempts
      </button>
    )
  }

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>Attempt history</span>
        <button type="button" className={styles.toggle} onClick={() => setState({ status: 'closed' })}>
          Hide
        </button>
      </div>

      {state.status === 'loading' && <LoadingState label="Loading attempt history…" />}
      {state.status === 'error' && (
        <ErrorState title="Could not load attempt history" message={state.error} onRetry={load} />
      )}
      {state.status === 'ready' && state.attempts.length === 0 && (
        <Muted>No attempt history is available for this investigation.</Muted>
      )}
      {state.status === 'ready' && state.attempts.length > 0 && (
        <ol className={styles.list}>
          {state.attempts.map((attempt) => (
            <AttemptRow
              key={attempt.attempt_number}
              attempt={attempt}
              expanded={expanded === attempt.attempt_number}
              onToggle={() => setExpanded((current) => (current === attempt.attempt_number ? null : attempt.attempt_number))}
              projectId={projectId}
              investigationId={investigationId}
              documentNames={documentNames}
              documents={documents}
            />
          ))}
        </ol>
      )}
    </div>
  )
}

function AttemptRow({
  attempt,
  expanded,
  onToggle,
  projectId,
  investigationId,
  documentNames,
  documents,
}: {
  attempt: InvestigationAttempt
  expanded: boolean
  onToggle: () => void
  projectId: number
  investigationId: string
  documentNames: Record<number, string>
  documents: DocumentSummary[] | null
}) {
  const preview = attempt.answer ? truncate(stripMarkdownToPlainText(attempt.answer), 160) : null

  return (
    <li className={styles.row}>
      <button type="button" className={styles.rowHeader} onClick={onToggle} aria-expanded={expanded}>
        <span className={styles.rowLabel}>
          Attempt {attempt.attempt_number}
          {attempt.is_current && <Badge tone="neutral">Current</Badge>}
        </span>
        <AttemptStatusBadge status={attempt.status} />
        <span className={styles.rowTimestamp}>{formatTimestamp(attempt.attempted_at)}</span>
      </button>

      {!expanded && preview && <p className={styles.rowPreview}>{preview}</p>}
      {!expanded && !preview && attempt.status === 'failed' && attempt.error && (
        <p className={styles.rowPreviewError}>{attempt.error}</p>
      )}

      {expanded && (
        <div className={styles.rowDetail}>
          {attempt.status === 'running' && (
            <Muted>This attempt was still running at the time this history was captured.</Muted>
          )}
          {attempt.status === 'failed' && <p className={styles.rowPreviewError}>{attempt.error ?? 'This attempt failed.'}</p>}
          {attempt.answer && <AnswerProse>{attempt.answer}</AnswerProse>}
          {attempt.answer_truncated && (
            <p className={styles.limitationText}>
              This answer may be incomplete — it was cut off before the model finished generating it.
            </p>
          )}
          {attempt.evidence_limitation && <p className={styles.limitationText}>{attempt.evidence_limitation}</p>}
          {attempt.citations.length > 0 && (
            <CitationList
              citations={attempt.citations}
              documentNames={documentNames}
              documents={documents}
              projectId={projectId}
              investigationId={investigationId}
            />
          )}
        </div>
      )}
    </li>
  )
}

function AttemptStatusBadge({ status }: { status: InvestigationAttempt['status'] }) {
  if (status === 'completed') return <Badge tone="green">Completed</Badge>
  if (status === 'failed') return <Badge tone="red">Failed</Badge>
  return <Badge tone="neutral">Running…</Badge>
}

function truncate(text: string, max: number): string {
  const trimmed = text.trim()
  return trimmed.length > max ? `${trimmed.slice(0, max)}…` : trimmed
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

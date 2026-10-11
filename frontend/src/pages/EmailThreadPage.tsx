import { Link, useParams } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { Muted } from '../components/ui/Typography'
import { Badge } from '../components/ui/Badge'
import { LinkButton } from '../components/ui/LinkButton'
import { ErrorState, LoadingState } from '../components/ui/StateViews'
import { parseProjectId } from '../lib/projectDirectory'
import { useProject } from '../lib/useProject'
import { useApiQuery } from '../api/useApi'
import { getEmailThread } from '../api/client'
import type { EmailMessageSummary } from '../api/types'
import styles from './EmailThreadPage.module.css'

/**
 * Phase 8A (Email Thread Intelligence): one reconstructed email
 * conversation — every message real and persisted, in the real order
 * app/email_ingestion/threading.py resolved them in (sent_at, nulls last).
 * A message opens through the EXISTING document-source-view route/page
 * (DocumentSourceViewPage, which already branches on doc_type === 'EMAIL'
 * to render the full sender/recipients/body/attachments view) — no second
 * message-detail page.
 */
export function EmailThreadPage() {
  const { projectId, threadId } = useParams<{ projectId: string; threadId: string }>()
  const id = parseProjectId(projectId)
  const parsedThreadId = threadId ? parseProjectId(threadId) : null
  const projectQuery = useProject(id)
  const projectName = projectQuery.status === 'success' ? projectQuery.data.name : undefined

  const threadQuery = useApiQuery(
    () =>
      id === null || parsedThreadId === null
        ? Promise.reject(new Error('invalid reference'))
        : getEmailThread(id, parsedThreadId),
    [id, parsedThreadId],
  )

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

  if (parsedThreadId === null) {
    return (
      <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: 'Invalid thread' }]}>
        <ErrorState title="Invalid thread reference" message={`"${threadId}" is not a valid thread reference.`} />
      </AppShell>
    )
  }

  if (threadQuery.status === 'loading') {
    return (
      <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: 'Email thread' }]}>
        <LoadingState label="Loading thread…" />
      </AppShell>
    )
  }

  if (threadQuery.status === 'error') {
    return (
      <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: 'Email thread' }]}>
        <ErrorState
          title="This thread is not available"
          message="This email thread could not be found for this project. It may not exist, or it may belong to a different project."
        />
      </AppShell>
    )
  }

  const thread = threadQuery.data
  const subject = thread.subject ?? '(no subject)'

  return (
    <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: 'Email correspondence', to: `/projects/${id}` }, { label: subject }]} wide>
      <p className={styles.kicker}>Email Thread</p>
      <h1 className={styles.title}>{subject}</h1>
      <p className={styles.intro}>
        {thread.messages.length} message{thread.messages.length === 1 ? '' : 's'} in this conversation, reconstructed
        from Message-ID / In-Reply-To / References headers.
      </p>

      <ol className={styles.messageList}>
        {thread.messages.map((message, i) => (
          <MessageRow key={message.document_id} message={message} index={i} projectId={id} />
        ))}
      </ol>

      <p className={styles.backLink}>
        <LinkButton to={`/projects/${id}`} variant="secondary">
          ← Back to project
        </LinkButton>
      </p>
    </AppShell>
  )
}

function MessageRow({ message, index, projectId }: { message: EmailMessageSummary; index: number; projectId: number }) {
  const openable = message.status === 'ready'
  const content = (
    <>
      <span className={styles.rowOrdinal}>{String(index + 1).padStart(2, '0')}</span>
      <div className={styles.rowMain}>
        <div className={styles.rowHeader}>
          <span className={styles.rowSender}>
            {message.sender_name || message.sender_email || <Muted>Unknown sender</Muted>}
          </span>
          {message.sent_at && <span className={styles.rowDate}>{formatTimestamp(message.sent_at)}</span>}
        </div>
        {message.subject && <p className={styles.rowSubject}>{message.subject}</p>}
        <div className={styles.rowMeta}>
          <MessageStatusBadge status={message.status} />
          {message.attachment_count > 0 && (
            <span className={styles.rowAttachments}>
              {message.attachment_count} attachment{message.attachment_count === 1 ? '' : 's'}
            </span>
          )}
        </div>
      </div>
      {openable && (
        <span className={styles.rowArrow} aria-hidden="true">
          →
        </span>
      )}
    </>
  )

  return (
    <li>
      {openable ? (
        <Link to={`/projects/${projectId}/documents/${message.document_id}/source`} className={`${styles.row} ${styles.rowOpenable}`}>
          {content}
        </Link>
      ) : (
        <div className={styles.row}>{content}</div>
      )}
    </li>
  )
}

function MessageStatusBadge({ status }: { status: EmailMessageSummary['status'] }) {
  if (status === 'ready') return <Badge tone="green">Ready</Badge>
  if (status === 'failed') return <Badge tone="red">Failed</Badge>
  return <Badge tone="neutral">Processing…</Badge>
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

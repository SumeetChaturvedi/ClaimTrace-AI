import { Link, useParams } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { Muted } from '../components/ui/Typography'
import { Badge } from '../components/ui/Badge'
import { LinkButton } from '../components/ui/LinkButton'
import { ErrorState, LoadingState } from '../components/ui/StateViews'
import { parseProjectId } from '../lib/projectDirectory'
import { useProject } from '../lib/useProject'
import { useApiQuery } from '../api/useApi'
import { getWhatsAppChat } from '../api/client'
import type { WhatsAppMessageSummary } from '../api/types'
import styles from './EmailThreadPage.module.css'

/**
 * Phase W1 (WhatsApp Export Ingestion): one imported WhatsApp chat —
 * every message real and persisted, in the real order the export itself
 * gave them (sequence_index). Reuses EmailThreadPage.module.css directly
 * rather than a near-duplicate stylesheet, since this page follows the
 * identical "ordered conversation list" visual pattern. A message opens
 * through the EXISTING document-source-view route/page
 * (DocumentSourceViewPage, which branches on doc_type === 'WHATSAPP_MESSAGE'
 * to render WhatsAppMessagePanel) — no second message-detail page.
 */
export function WhatsAppChatPage() {
  const { projectId, chatId } = useParams<{ projectId: string; chatId: string }>()
  const id = parseProjectId(projectId)
  const parsedChatId = chatId ? parseProjectId(chatId) : null
  const projectQuery = useProject(id)
  const projectName = projectQuery.status === 'success' ? projectQuery.data.name : undefined

  const chatQuery = useApiQuery(
    () =>
      id === null || parsedChatId === null
        ? Promise.reject(new Error('invalid reference'))
        : getWhatsAppChat(id, parsedChatId),
    [id, parsedChatId],
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

  if (parsedChatId === null) {
    return (
      <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: 'Invalid chat' }]}>
        <ErrorState title="Invalid chat reference" message={`"${chatId}" is not a valid chat reference.`} />
      </AppShell>
    )
  }

  if (chatQuery.status === 'loading') {
    return (
      <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: 'WhatsApp chat' }]}>
        <LoadingState label="Loading chat…" />
      </AppShell>
    )
  }

  if (chatQuery.status === 'error') {
    return (
      <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: 'WhatsApp chat' }]}>
        <ErrorState
          title="This chat is not available"
          message="This WhatsApp chat could not be found for this project. It may not exist, or it may belong to a different project."
        />
      </AppShell>
    )
  }

  const chat = chatQuery.data
  const title = chat.title ?? '(untitled chat)'

  return (
    <AppShell breadcrumb={[...breadcrumbBase, projectCrumb, { label: 'WhatsApp Chats', to: `/projects/${id}` }, { label: title }]} wide>
      <p className={styles.kicker}>WhatsApp Chat</p>
      <h1 className={styles.title}>{title}</h1>
      <p className={styles.intro}>
        {chat.messages.length} message{chat.messages.length === 1 ? '' : 's'} from this imported export, in the
        order they were exported.
      </p>

      <ol className={styles.messageList}>
        {chat.messages.map((message) => (
          <MessageRow key={message.document_id} message={message} projectId={id} />
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

function MessageRow({ message, projectId }: { message: WhatsAppMessageSummary; projectId: number }) {
  const openable = message.status === 'ready'
  const content = (
    <>
      <span className={styles.rowOrdinal}>{String(message.sequence_index + 1).padStart(2, '0')}</span>
      <div className={styles.rowMain}>
        <div className={styles.rowHeader}>
          <span className={styles.rowSender}>
            {message.sender_name || <Muted>System / group event</Muted>}
          </span>
          <span className={styles.rowDate}>
            {message.raw_timestamp_text}
            {message.sent_at_ambiguous && ' *'}
          </span>
        </div>
        <div className={styles.rowMeta}>
          <MessageStatusBadge status={message.status} />
          <MessageTypeBadge type={message.message_type} />
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

function MessageStatusBadge({ status }: { status: WhatsAppMessageSummary['status'] }) {
  if (status === 'ready') return <Badge tone="green">Ready</Badge>
  if (status === 'failed') return <Badge tone="red">Failed</Badge>
  return <Badge tone="neutral">Processing…</Badge>
}

function MessageTypeBadge({ type }: { type: WhatsAppMessageSummary['message_type'] }) {
  if (type === 'text') return null
  if (type === 'system') return <Badge tone="neutral">System</Badge>
  if (type === 'deleted') return <Badge tone="neutral">Deleted</Badge>
  return <Badge tone="neutral">Media</Badge>
}

import { Link } from 'react-router-dom'
import { getWhatsAppAttachmentFileUrl, getWhatsAppMessage } from '../../api/client'
import { useApiQuery } from '../../api/useApi'
import { SectionLabel, Muted, Prose } from '../ui/Typography'
import { Badge } from '../ui/Badge'
import { LoadingState, ErrorState } from '../ui/StateViews'
import type { WhatsAppMediaAttachmentSummary } from '../../api/types'
import styles from './WhatsAppMessagePanel.module.css'

/**
 * Phase W1 (WhatsApp Export Ingestion): the shared "open a WhatsApp
 * message" view — sender/timestamp/text/attachments — reused identically
 * by SourceViewPage (opened from an investigation citation) and
 * DocumentSourceViewPage (opened directly from the project's document
 * register), exactly mirroring EmailMessagePanel's own single-
 * implementation principle.
 *
 * Every value shown is real: fetched fresh from
 * GET /projects/{project_id}/whatsapp/messages/{document_id}, never
 * derived or guessed from the citation/document summary alone.
 * sent_at_ambiguous is shown explicitly rather than presenting an
 * uncertain day/month reading as a confident timestamp (see
 * app/whatsapp_ingestion/parsing.py's own disambiguation rule).
 */
export function WhatsAppMessagePanel({
  projectId,
  documentId,
  highlightExcerpt,
}: {
  projectId: number
  documentId: number
  /** The exact cited passage, when this panel is opened from a citation —
   * shown as its own callout above the full text, exactly like
   * EmailMessagePanel's own "Cited passage" section. Omitted when opened
   * directly from the document register (no citation involved). */
  highlightExcerpt?: string | null
}) {
  const messageQuery = useApiQuery(() => getWhatsAppMessage(projectId, documentId), [projectId, documentId])

  if (messageQuery.status === 'loading') {
    return (
      <div className={styles.panelContent}>
        <LoadingState label="Loading message…" />
      </div>
    )
  }

  if (messageQuery.status === 'error') {
    return (
      <div className={styles.panelContent}>
        <ErrorState title="Could not load this message" message={messageQuery.error} />
      </div>
    )
  }

  const message = messageQuery.data

  return (
    <div className={styles.panelContent}>
      <SectionLabel>WhatsApp Message</SectionLabel>

      <dl className={styles.headerList}>
        <div>
          <dt>From</dt>
          <dd>{message.sender_name ?? <Muted>System / group event</Muted>}</dd>
        </div>
        <div>
          <dt>Sent</dt>
          <dd>
            {message.raw_timestamp_text}
            {message.sent_at_ambiguous && (
              <span className={styles.ambiguousNote}> (day/month order could not be confirmed from the export)</span>
            )}
          </dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{formatMessageType(message.message_type)}</dd>
        </div>
      </dl>

      {highlightExcerpt && (
        <div className={styles.excerptSection}>
          <SectionLabel>Cited passage</SectionLabel>
          <Badge tone="neutral">Exact excerpt used in this investigation</Badge>
          <Prose>{highlightExcerpt}</Prose>
        </div>
      )}

      <div className={styles.bodySection}>
        <SectionLabel>Message text</SectionLabel>
        {message.text ? <Prose>{message.text}</Prose> : <Muted>No text was found in this message.</Muted>}
      </div>

      <div className={styles.attachmentsSection}>
        <SectionLabel>Attachments{message.attachments.length > 0 ? ` (${message.attachments.length})` : ''}</SectionLabel>
        {message.attachments.length === 0 ? (
          <Muted>No attachments.</Muted>
        ) : (
          <ul className={styles.attachmentList}>
            {message.attachments.map((attachment) => (
              <li key={attachment.id} className={styles.attachmentRow}>
                <AttachmentLink projectId={projectId} attachment={attachment} />
                <AttachmentStatusBadge status={attachment.status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function AttachmentLink({
  projectId,
  attachment,
}: {
  projectId: number
  attachment: WhatsAppMediaAttachmentSummary
}) {
  if (attachment.status === 'processed' && attachment.document_id != null) {
    return (
      <Link to={`/projects/${projectId}/documents/${attachment.document_id}/source`} className={styles.attachmentLink}>
        {attachment.filename}
      </Link>
    )
  }
  if (attachment.status === 'stored_pending_processing') {
    return (
      <a
        href={getWhatsAppAttachmentFileUrl(projectId, attachment.id)}
        target="_blank"
        rel="noreferrer"
        className={styles.attachmentLink}
      >
        {attachment.filename}
      </a>
    )
  }
  return <span className={styles.attachmentName}>{attachment.filename}</span>
}

function AttachmentStatusBadge({
  status,
}: {
  status: WhatsAppMediaAttachmentSummary['status']
}) {
  if (status === 'processed') return <Badge tone="green">Indexed</Badge>
  if (status === 'stored_pending_processing') return <Badge tone="amber">Preserved — not yet processed</Badge>
  if (status === 'unsupported_format') return <Badge tone="neutral">Format not supported</Badge>
  if (status === 'failed') return <Badge tone="red">Processing failed</Badge>
  return <Badge tone="red">Rejected</Badge>
}

function formatMessageType(type: 'text' | 'system' | 'deleted' | 'media'): string {
  if (type === 'system') return 'System / group event'
  if (type === 'deleted') return 'Deleted message'
  if (type === 'media') return 'Media'
  return 'Text'
}

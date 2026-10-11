import { Link } from 'react-router-dom'
import { getEmailMessage } from '../../api/client'
import { useApiQuery } from '../../api/useApi'
import { SectionLabel, Muted, Prose } from '../ui/Typography'
import { Badge } from '../ui/Badge'
import { LoadingState, ErrorState } from '../ui/StateViews'
import styles from './EmailMessagePanel.module.css'

/**
 * Phase 8A (Email Thread Intelligence): the shared "open an email message"
 * view — sender/recipients/timestamp/body/attachments — reused identically
 * by SourceViewPage (opened from an investigation citation) and
 * DocumentSourceViewPage (opened directly from the project's document
 * register), exactly as neither page implements a second PDF viewer for
 * DOCX; this is the same single-implementation principle applied to EMAIL.
 *
 * Every value shown is real: fetched fresh from
 * GET /projects/{project_id}/emails/messages/{document_id}, never derived
 * or guessed from the citation/document summary alone. An attachment only
 * links to its own source viewer when it actually became a real document
 * (status 'processed', document_id set) — an unsupported/rejected/failed
 * attachment is shown with its real status, never presented as openable.
 */
export function EmailMessagePanel({
  projectId,
  documentId,
  highlightExcerpt,
}: {
  projectId: number
  documentId: number
  /** The exact cited passage, when this panel is opened from a citation —
   * shown as its own callout above the full body, exactly like
   * SourceViewPage's "Cited passage" section for a PDF/DOCX citation.
   * Omitted when opened directly from the document register (no
   * citation involved). */
  highlightExcerpt?: string | null
}) {
  const messageQuery = useApiQuery(() => getEmailMessage(projectId, documentId), [projectId, documentId])

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
      <SectionLabel>Email Message</SectionLabel>

      <dl className={styles.headerList}>
        <div>
          <dt>Subject</dt>
          <dd>{message.subject ?? <Muted>No subject</Muted>}</dd>
        </div>
        <div>
          <dt>From</dt>
          <dd>
            {message.sender_name ? `${message.sender_name} ` : ''}
            {message.sender_email ? (
              <span className={styles.address}>&lt;{message.sender_email}&gt;</span>
            ) : (
              <Muted>Unknown sender</Muted>
            )}
          </dd>
        </div>
        {message.to_recipients.length > 0 && (
          <div>
            <dt>To</dt>
            <dd>{message.to_recipients.join(', ')}</dd>
          </div>
        )}
        {message.cc_recipients.length > 0 && (
          <div>
            <dt>Cc</dt>
            <dd>{message.cc_recipients.join(', ')}</dd>
          </div>
        )}
        <div>
          <dt>Date</dt>
          <dd>
            {message.sent_at ? formatTimestamp(message.sent_at) : <Muted>Not recorded</Muted>}
            {message.sent_at && message.sent_at_timezone_unknown && (
              <span className={styles.tzNote}> (time zone unknown — shown as UTC)</span>
            )}
          </dd>
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
        <SectionLabel>Message body</SectionLabel>
        {message.plain_body ? (
          <Prose>{message.plain_body}</Prose>
        ) : (
          <Muted>No body text was found in this message.</Muted>
        )}
        {message.has_html_body && (
          <p className={styles.htmlNote}>
            <Muted>
              This message's original body was HTML-formatted; the text above is ClaimTrace's
              plain-text extraction, not a rendering of the original formatting.
            </Muted>
          </p>
        )}
      </div>

      <div className={styles.attachmentsSection}>
        <SectionLabel>Attachments{message.attachments.length > 0 ? ` (${message.attachments.length})` : ''}</SectionLabel>
        {message.attachments.length === 0 ? (
          <Muted>No attachments.</Muted>
        ) : (
          <ul className={styles.attachmentList}>
            {message.attachments.map((attachment) => (
              <li key={attachment.id} className={styles.attachmentRow}>
                {attachment.status === 'processed' && attachment.document_id != null ? (
                  <Link
                    to={`/projects/${projectId}/documents/${attachment.document_id}/source`}
                    className={styles.attachmentLink}
                  >
                    {attachment.filename}
                  </Link>
                ) : (
                  <span className={styles.attachmentName}>{attachment.filename}</span>
                )}
                <AttachmentStatusBadge status={attachment.status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function AttachmentStatusBadge({ status }: { status: 'processed' | 'unsupported_format' | 'rejected' | 'failed' }) {
  if (status === 'processed') return <Badge tone="green">Available</Badge>
  if (status === 'unsupported_format') return <Badge tone="neutral">Format not supported</Badge>
  if (status === 'failed') return <Badge tone="red">Processing failed</Badge>
  return <Badge tone="red">Rejected</Badge>
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

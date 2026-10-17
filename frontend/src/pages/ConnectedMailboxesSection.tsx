import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SectionLabel, Muted } from '../components/ui/Typography'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { ErrorState, LoadingState } from '../components/ui/StateViews'
import {
  ApiError,
  disconnectMailbox,
  listConnectedMailboxes,
  startGmailConnect,
  syncConnectedMailbox,
} from '../api/client'
import { useApiQuery } from '../api/useApi'
import type { ConnectedMailboxSummary } from '../api/types'
import styles from './ProjectPage.module.css'

/**
 * Connected Mailboxes section (Phase 1: Gmail Integration) — extracted
 * into its own component (code review pass) so it can be tested in
 * isolation, without pulling in the rest of ProjectPage's other queries.
 * No behavior change from the inline version this replaced: same state,
 * same handlers, same rendering, same CSS classes (ProjectPage.module.css
 * is reused as-is, not duplicated, since this section's markup follows
 * the exact same "register row" visual pattern as the Documents/Email
 * Correspondence sections next to it).
 */
export function ConnectedMailboxesSection({ projectId }: { projectId: number | null }) {
  const [refreshToken, setRefreshToken] = useState(0)
  const mailboxesQuery = useApiQuery(
    () => (projectId === null ? Promise.resolve<ConnectedMailboxSummary[]>([]) : listConnectedMailboxes(projectId)),
    [projectId, refreshToken],
  )

  // The OAuth callback (backend) redirects the browser back here with
  // ?gmail_connect=success|denied|error after a full round trip to
  // Google's own consent screen — read once on mount, shown as a banner,
  // then stripped from the URL so refreshing the page doesn't keep
  // re-showing a stale result.
  const [searchParams, setSearchParams] = useSearchParams()
  const [gmailConnectBanner, setGmailConnectBanner] = useState<'success' | 'denied' | 'error' | null>(null)
  useEffect(() => {
    const outcome = searchParams.get('gmail_connect')
    if (outcome === 'success' || outcome === 'denied' || outcome === 'error') {
      setGmailConnectBanner(outcome)
      const next = new URLSearchParams(searchParams)
      next.delete('gmail_connect')
      setSearchParams(next, { replace: true })
      if (outcome === 'success') setRefreshToken((t) => t + 1)
    }
    // Only ever react to the param actually present at mount/navigation —
    // not to our own setSearchParams call removing it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams.get('gmail_connect')])

  const [connectingGmail, setConnectingGmail] = useState(false)
  const [mailboxActionError, setMailboxActionError] = useState<string | null>(null)
  const [syncingMailboxId, setSyncingMailboxId] = useState<number | null>(null)
  const [syncSummary, setSyncSummary] = useState<string | null>(null)
  const [disconnectingMailboxId, setDisconnectingMailboxId] = useState<number | null>(null)

  const handleConnectGmail = async () => {
    if (projectId === null) return
    setConnectingGmail(true)
    setMailboxActionError(null)
    try {
      const { authorization_url } = await startGmailConnect(projectId)
      // A full browser navigation, not a fetch: the person's own browser
      // must interact with Google's consent screen directly.
      window.location.href = authorization_url
    } catch (err) {
      setMailboxActionError(err instanceof ApiError ? err.message : 'Could not start the Gmail connection.')
      setConnectingGmail(false)
    }
  }

  const handleSyncMailbox = async (mailboxId: number) => {
    if (projectId === null) return
    setSyncingMailboxId(mailboxId)
    setSyncSummary(null)
    setMailboxActionError(null)
    try {
      const result = await syncConnectedMailbox(projectId, mailboxId)
      const parts: string[] = []
      if (result.imported > 0) parts.push(`${result.imported} new message${result.imported === 1 ? '' : 's'} imported`)
      if (result.duplicate > 0) parts.push(`${result.duplicate} already imported`)
      if (result.rejected > 0) parts.push(`${result.rejected} rejected`)
      if (result.skipped_not_found > 0) parts.push(`${result.skipped_not_found} no longer available`)
      if (result.status === 'needs_reauth') {
        setMailboxActionError('Gmail access needs to be reconnected for this mailbox.')
      } else if (result.status === 'error') {
        setMailboxActionError(result.error ?? 'Sync could not complete.')
      } else {
        setSyncSummary(
          parts.length > 0
            ? `${parts.join(', ')}${result.status === 'partial' ? ' (more messages remain — sync again to continue)' : ''}`
            : 'No new messages.',
        )
      }
      setRefreshToken((t) => t + 1)
    } catch (err) {
      setMailboxActionError(err instanceof ApiError ? err.message : 'Something went wrong during sync.')
    } finally {
      setSyncingMailboxId(null)
    }
  }

  const handleDisconnectMailbox = async (mailboxId: number) => {
    if (projectId === null) return
    setDisconnectingMailboxId(mailboxId)
    setMailboxActionError(null)
    try {
      await disconnectMailbox(projectId, mailboxId)
      setRefreshToken((t) => t + 1)
    } catch (err) {
      setMailboxActionError(err instanceof ApiError ? err.message : 'Could not disconnect this mailbox.')
    } finally {
      setDisconnectingMailboxId(null)
    }
  }

  const activeMailboxes = mailboxesQuery.status === 'success' ? mailboxesQuery.data.filter((m) => m.status !== 'disconnected') : []

  return (
    <section className={styles.documentsSection}>
      <div className={styles.sectionRule}>
        <span className={styles.sectionRuleNodeAlt} aria-hidden="true" />
        <SectionLabel>
          Connected Mailboxes
          {mailboxesQuery.status === 'success' && activeMailboxes.length > 0
            ? ` · ${String(activeMailboxes.length).padStart(2, '0')}`
            : ''}
        </SectionLabel>
        <span className={styles.sectionRuleLine} aria-hidden="true" />
        <Button variant="primary" onClick={() => void handleConnectGmail()} disabled={connectingGmail}>
          {connectingGmail ? 'Connecting…' : 'Connect Gmail'}
        </Button>
      </div>
      <p className={styles.sectionBody}>
        Connect a Gmail account to automatically bring its correspondence into this project as
        searchable, citable evidence — the same pipeline used for manual email import. Access is
        read-only. Disconnecting removes ClaimTrace's stored access immediately.
      </p>

      {gmailConnectBanner === 'success' && <p className={styles.uploadSummary}>Gmail account connected.</p>}
      {gmailConnectBanner === 'denied' && <p className={styles.uploadSummary}>Gmail connection was not completed (consent was not granted).</p>}
      {gmailConnectBanner === 'error' && <p className={styles.uploadError}>Gmail connection could not be completed. Please try again.</p>}
      {syncSummary && <p className={styles.uploadSummary}>{syncSummary}</p>}
      {mailboxActionError && <p className={styles.uploadError}>{mailboxActionError}</p>}

      {mailboxesQuery.status === 'loading' && <LoadingState label="Loading connected mailboxes…" />}
      {mailboxesQuery.status === 'error' && (
        <ErrorState message={`Could not load connected mailboxes: ${mailboxesQuery.error}`} />
      )}
      {mailboxesQuery.status === 'success' && activeMailboxes.length === 0 && (
        <p className={styles.emptyDocuments}>
          <Muted>No mailbox is connected to this project yet.</Muted>
        </p>
      )}
      {mailboxesQuery.status === 'success' && activeMailboxes.length > 0 && (
        <ol className={styles.documentRegister}>
          {activeMailboxes.map((mailbox) => (
            <ConnectedMailboxRow
              key={mailbox.id}
              mailbox={mailbox}
              syncing={syncingMailboxId === mailbox.id}
              disconnecting={disconnectingMailboxId === mailbox.id}
              onSync={() => void handleSyncMailbox(mailbox.id)}
              onDisconnect={() => void handleDisconnectMailbox(mailbox.id)}
            />
          ))}
        </ol>
      )}
    </section>
  )
}

function ConnectedMailboxRow({
  mailbox,
  syncing,
  disconnecting,
  onSync,
  onDisconnect,
}: {
  mailbox: ConnectedMailboxSummary
  syncing: boolean
  disconnecting: boolean
  onSync: () => void
  onDisconnect: () => void
}) {
  const busy = syncing || disconnecting
  return (
    <li>
      <div className={styles.registerRow}>
        <div className={styles.docMain}>
          <span className={styles.docName}>{mailbox.external_email}</span>
          <div className={styles.docMeta}>
            <Badge tone={mailbox.status === 'needs_reauth' ? 'amber' : 'neutral'}>
              {mailbox.status === 'needs_reauth' ? 'Needs reconnection' : 'Connected'}
            </Badge>
            <span className={styles.docMetaDot} aria-hidden="true" />
            <span className={styles.docMetaText}>
              {mailbox.last_synced_at ? `Last synced ${formatMailboxDate(mailbox.last_synced_at)}` : 'Never synced'}
            </span>
          </div>
          {mailbox.last_sync_error && <p className={styles.uploadError}>{mailbox.last_sync_error}</p>}
        </div>
        <div className={styles.docTrailing}>
          <Button variant="secondary" onClick={onSync} disabled={busy}>
            {syncing ? 'Syncing…' : 'Sync now'}
          </Button>
          <Button variant="secondary" onClick={onDisconnect} disabled={busy}>
            {disconnecting ? 'Disconnecting…' : 'Disconnect'}
          </Button>
        </div>
      </div>
    </li>
  )
}

function formatMailboxDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return iso
  }
}

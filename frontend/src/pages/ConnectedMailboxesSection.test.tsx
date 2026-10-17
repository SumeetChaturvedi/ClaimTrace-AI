import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ConnectedMailboxSummary, SyncResult } from '../api/types'
import { ApiError } from '../api/client'
import { ConnectedMailboxesSection } from './ConnectedMailboxesSection'

const {
  listConnectedMailboxesMock,
  startGmailConnectMock,
  syncConnectedMailboxMock,
  disconnectMailboxMock,
} = vi.hoisted(() => ({
  listConnectedMailboxesMock: vi.fn(),
  startGmailConnectMock: vi.fn(),
  syncConnectedMailboxMock: vi.fn(),
  disconnectMailboxMock: vi.fn(),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    listConnectedMailboxes: listConnectedMailboxesMock,
    startGmailConnect: startGmailConnectMock,
    syncConnectedMailbox: syncConnectedMailboxMock,
    disconnectMailbox: disconnectMailboxMock,
  }
})

function mailbox(overrides: Partial<ConnectedMailboxSummary> = {}): ConnectedMailboxSummary {
  return {
    id: 1,
    provider: 'gmail',
    external_email: 'person@example.com',
    status: 'connected',
    last_synced_at: null,
    last_sync_error: null,
    connected_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

function syncResult(overrides: Partial<SyncResult> = {}): SyncResult {
  return {
    status: 'completed',
    imported: 0,
    duplicate: 0,
    rejected: 0,
    skipped_not_found: 0,
    error: null,
    ...overrides,
  }
}

function renderSection(projectId: number | null = 1) {
  return render(
    <MemoryRouter>
      <ConnectedMailboxesSection projectId={projectId} />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  listConnectedMailboxesMock.mockReset()
  startGmailConnectMock.mockReset()
  syncConnectedMailboxMock.mockReset()
  disconnectMailboxMock.mockReset()
  listConnectedMailboxesMock.mockResolvedValue([])
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ConnectedMailboxesSection — connection status', () => {
  it('shows an empty state when no mailbox is connected', async () => {
    renderSection()
    await waitFor(() => expect(screen.getByText(/no mailbox is connected/i)).toBeInTheDocument())
  })

  it('shows the connected account email and a Connected badge', async () => {
    listConnectedMailboxesMock.mockResolvedValue([mailbox()])
    renderSection()
    await waitFor(() => expect(screen.getByText('person@example.com')).toBeInTheDocument())
    expect(screen.getByText('Connected')).toBeInTheDocument()
  })

  it('shows a distinct "Needs reconnection" badge for a needs_reauth mailbox', async () => {
    listConnectedMailboxesMock.mockResolvedValue([mailbox({ status: 'needs_reauth' })])
    renderSection()
    await waitFor(() => expect(screen.getByText('Needs reconnection')).toBeInTheDocument())
    expect(screen.queryByText('Connected')).not.toBeInTheDocument()
  })

  it('never shows a disconnected mailbox in the active list', async () => {
    listConnectedMailboxesMock.mockResolvedValue([mailbox({ status: 'disconnected', external_email: 'gone@example.com' })])
    renderSection()
    await waitFor(() => expect(screen.getByText(/no mailbox is connected/i)).toBeInTheDocument())
    expect(screen.queryByText('gone@example.com')).not.toBeInTheDocument()
  })

  it('shows a loading state while the mailbox list is being fetched', () => {
    listConnectedMailboxesMock.mockReturnValue(new Promise(() => {})) // never resolves
    renderSection()
    expect(screen.getByText(/loading connected mailboxes/i)).toBeInTheDocument()
  })

  it('shows an error state when the mailbox list fails to load', async () => {
    listConnectedMailboxesMock.mockRejectedValue(new ApiError(500, 'boom'))
    renderSection()
    await waitFor(() => expect(screen.getByText(/could not load connected mailboxes/i)).toBeInTheDocument())
  })
})

describe('ConnectedMailboxesSection — connect action', () => {
  it('navigates the browser to the returned authorization_url on Connect Gmail', async () => {
    startGmailConnectMock.mockResolvedValue({ authorization_url: 'https://accounts.google.com/fake-consent' })
    // jsdom's real window.location.href setter throws "Not implemented:
    // navigation" rather than recording the value — replacing the whole
    // `location` object (the standard way to test an actual navigation in
    // jsdom) sidesteps that without touching production code. Restored in
    // afterEach below so it never leaks into a later test file.
    const originalLocation = window.location
    const fakeLocation = { href: '' } as Location
    Object.defineProperty(window, 'location', { value: fakeLocation, writable: true, configurable: true })

    renderSection()
    fireEvent.click(screen.getByRole('button', { name: /connect gmail/i }))

    await waitFor(() => expect(fakeLocation.href).toBe('https://accounts.google.com/fake-consent'))

    Object.defineProperty(window, 'location', { value: originalLocation, writable: true, configurable: true })
  })

  it('shows an error without navigating if starting the connection fails', async () => {
    startGmailConnectMock.mockRejectedValue(new ApiError(503, 'Gmail integration is not configured'))
    renderSection()
    fireEvent.click(screen.getByRole('button', { name: /connect gmail/i }))
    await waitFor(() => expect(screen.getByText('Gmail integration is not configured')).toBeInTheDocument())
  })
})

describe('ConnectedMailboxesSection — sync action', () => {
  it('shows a loading label on the clicked mailbox while syncing, and a summary once it resolves', async () => {
    listConnectedMailboxesMock.mockResolvedValue([mailbox()])
    syncConnectedMailboxMock.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(syncResult({ imported: 3 })), 20)),
    )
    renderSection()
    await waitFor(() => expect(screen.getByText('person@example.com')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /sync now/i }))
    expect(screen.getByRole('button', { name: /syncing…/i })).toBeInTheDocument()

    await waitFor(() => expect(screen.getByText(/3 new messages imported/i)).toBeInTheDocument())
  })

  it('shows a reconnect message, not a generic error, when sync reports needs_reauth', async () => {
    listConnectedMailboxesMock.mockResolvedValue([mailbox()])
    syncConnectedMailboxMock.mockResolvedValue(syncResult({ status: 'needs_reauth' }))
    renderSection()
    await waitFor(() => expect(screen.getByText('person@example.com')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /sync now/i }))
    await waitFor(() => expect(screen.getByText(/needs to be reconnected/i)).toBeInTheDocument())
  })

  it('shows the sync error message when sync reports a plain error', async () => {
    listConnectedMailboxesMock.mockResolvedValue([mailbox()])
    syncConnectedMailboxMock.mockResolvedValue(syncResult({ status: 'error', error: 'Gmail API returned a transient error' }))
    renderSection()
    await waitFor(() => expect(screen.getByText('person@example.com')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /sync now/i }))
    await waitFor(() => expect(screen.getByText('Gmail API returned a transient error')).toBeInTheDocument())
  })

  it('shows a continuation hint for a partial sync result', async () => {
    listConnectedMailboxesMock.mockResolvedValue([mailbox()])
    syncConnectedMailboxMock.mockResolvedValue(syncResult({ status: 'partial', imported: 2 }))
    renderSection()
    await waitFor(() => expect(screen.getByText('person@example.com')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /sync now/i }))
    await waitFor(() => expect(screen.getByText(/sync again to continue/i)).toBeInTheDocument())
  })

  it('still shows a continuation hint for a partial sync result with zero progress this call', async () => {
    // Regression test: a partial sync that imported/duplicated/rejected/
    // skipped nothing in this call (e.g. it was cut short on the very
    // first message) must never be reported identically to a genuinely
    // complete, up-to-date sync.
    listConnectedMailboxesMock.mockResolvedValue([mailbox()])
    syncConnectedMailboxMock.mockResolvedValue(syncResult({ status: 'partial' }))
    renderSection()
    await waitFor(() => expect(screen.getByText('person@example.com')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /sync now/i }))
    await waitFor(() => expect(screen.getByText(/sync again to continue/i)).toBeInTheDocument())
    expect(screen.queryByText('No new messages.')).not.toBeInTheDocument()
  })

  it('surfaces the real stop reason for a partial sync result that was cut short by an error', async () => {
    // Regression test: SyncResult.error carries the real reason a partial
    // sync stopped early (as opposed to simply hitting the per-call size
    // bound) — it must reach the user, not be silently dropped.
    listConnectedMailboxesMock.mockResolvedValue([mailbox()])
    syncConnectedMailboxMock.mockResolvedValue(
      syncResult({ status: 'partial', imported: 1, error: 'Gmail API returned a transient error' }),
    )
    renderSection()
    await waitFor(() => expect(screen.getByText('person@example.com')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /sync now/i }))
    await waitFor(() => expect(screen.getByText('Gmail API returned a transient error')).toBeInTheDocument())
    expect(screen.getByText(/sync again to continue/i)).toBeInTheDocument()
  })

  it('surfaces a network/API error from the sync call itself', async () => {
    listConnectedMailboxesMock.mockResolvedValue([mailbox()])
    syncConnectedMailboxMock.mockRejectedValue(new ApiError(0, 'Could not reach the backend.'))
    renderSection()
    await waitFor(() => expect(screen.getByText('person@example.com')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /sync now/i }))
    await waitFor(() => expect(screen.getByText('Could not reach the backend.')).toBeInTheDocument())
  })
})

describe('ConnectedMailboxesSection — disconnect action', () => {
  it('shows a loading label while disconnecting and refreshes the list afterward', async () => {
    listConnectedMailboxesMock.mockResolvedValueOnce([mailbox()]).mockResolvedValueOnce([])
    disconnectMailboxMock.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mailbox({ status: 'disconnected' })), 20)),
    )
    renderSection()
    await waitFor(() => expect(screen.getByText('person@example.com')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /disconnect/i }))
    expect(screen.getByRole('button', { name: /disconnecting…/i })).toBeInTheDocument()

    await waitFor(() => expect(screen.getByText(/no mailbox is connected/i)).toBeInTheDocument())
    expect(disconnectMailboxMock).toHaveBeenCalledWith(1, 1)
  })

  it('shows an error if disconnect fails, and the mailbox remains listed', async () => {
    listConnectedMailboxesMock.mockResolvedValue([mailbox()])
    disconnectMailboxMock.mockRejectedValue(new ApiError(500, 'Could not disconnect this mailbox.'))
    renderSection()
    await waitFor(() => expect(screen.getByText('person@example.com')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /disconnect/i }))
    await waitFor(() => expect(screen.getByText('Could not disconnect this mailbox.')).toBeInTheDocument())
    expect(screen.getByText('person@example.com')).toBeInTheDocument()
  })

  it('disables both actions on a mailbox while either sync or disconnect is in flight', async () => {
    listConnectedMailboxesMock.mockResolvedValue([mailbox()])
    syncConnectedMailboxMock.mockImplementation(() => new Promise(() => {}))
    renderSection()
    await waitFor(() => expect(screen.getByText('person@example.com')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /sync now/i }))
    expect(screen.getByRole('button', { name: /disconnect/i })).toBeDisabled()
  })
})

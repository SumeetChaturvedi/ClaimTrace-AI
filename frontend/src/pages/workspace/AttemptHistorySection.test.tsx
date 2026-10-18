import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { InvestigationAttempt } from '../../api/types'
import { ApiError } from '../../api/client'
import { InspectorProvider } from '../../components/layout/InspectorContext'
import { AttemptHistorySection } from './AttemptHistorySection'

const { getInvestigationAttemptsMock } = vi.hoisted(() => ({
  getInvestigationAttemptsMock: vi.fn(),
}))

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return {
    ...actual,
    getInvestigationAttempts: getInvestigationAttemptsMock,
  }
})

function attempt(overrides: Partial<InvestigationAttempt> = {}): InvestigationAttempt {
  return {
    attempt_number: 1,
    is_current: false,
    status: 'completed',
    attempted_at: '2024-01-01T00:00:00Z',
    answer: 'A fixture answer for this attempt.',
    citations: [],
    reasoning_steps: [],
    timeline: [],
    contract_clauses: [],
    events: [],
    events_error: null,
    events_truncated: false,
    answer_truncated: false,
    evidence_limitation: null,
    error: null,
    ...overrides,
  }
}

function renderSection() {
  return render(
    <InspectorProvider>
      <AttemptHistorySection projectId={1} investigationId="inv-1" documentNames={{}} documents={null} />
    </InspectorProvider>,
  )
}

describe('AttemptHistorySection (Phase 2a)', () => {
  it('fetches nothing until opened', () => {
    renderSection()
    expect(getInvestigationAttemptsMock).not.toHaveBeenCalled()
    expect(screen.getByText(/view previous attempts/i)).toBeInTheDocument()
  })

  it('shows a loading state, then the attempts in order, when opened', async () => {
    getInvestigationAttemptsMock.mockResolvedValue([
      attempt({ attempt_number: 1, is_current: false, status: 'failed', error: 'First attempt failed.' }),
      attempt({ attempt_number: 2, is_current: true, status: 'completed', answer: 'The current answer.' }),
    ])
    renderSection()

    fireEvent.click(screen.getByText(/view previous attempts/i))
    expect(screen.getByText(/loading attempt history/i)).toBeInTheDocument()

    await waitFor(() => expect(screen.getByText('Attempt 1')).toBeInTheDocument())
    expect(screen.getByText('Attempt 2')).toBeInTheDocument()
    expect(screen.getByText('Current')).toBeInTheDocument()

    // Oldest-first order: attempt 1's row renders before attempt 2's in the DOM.
    const rows = screen.getAllByRole('button', { name: /^Attempt \d/ })
    expect(rows[0]).toHaveTextContent('Attempt 1')
    expect(rows[1]).toHaveTextContent('Attempt 2')
  })

  it('shows an empty state when the history is genuinely empty', async () => {
    getInvestigationAttemptsMock.mockResolvedValue([])
    renderSection()
    fireEvent.click(screen.getByText(/view previous attempts/i))
    await waitFor(() => expect(screen.getByText(/no attempt history is available/i)).toBeInTheDocument())
  })

  it('shows an error state with a retry option on failure', async () => {
    getInvestigationAttemptsMock.mockRejectedValue(new ApiError(0, 'Could not reach the backend.'))
    renderSection()
    fireEvent.click(screen.getByText(/view previous attempts/i))
    await waitFor(() => expect(screen.getByText('Could not reach the backend.')).toBeInTheDocument())
  })

  it('expands an attempt to show its full answer, and never claims a running attempt completed', async () => {
    getInvestigationAttemptsMock.mockResolvedValue([
      attempt({ attempt_number: 1, is_current: true, status: 'running', answer: null }),
    ])
    renderSection()
    fireEvent.click(screen.getByText(/view previous attempts/i))
    await waitFor(() => expect(screen.getByText('Attempt 1')).toBeInTheDocument())

    expect(screen.getByText('Running…')).toBeInTheDocument()
    expect(screen.queryByText('Completed')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Attempt 1'))
    expect(screen.getByText(/still running at the time this history was captured/i)).toBeInTheDocument()
  })

  it('shows the plain-language evidence_limitation message on an expanded attempt, never the raw reason', async () => {
    getInvestigationAttemptsMock.mockResolvedValue([
      attempt({
        attempt_number: 1,
        is_current: true,
        evidence_limitation: 'This investigation could not retrieve a referenced clause.',
      }),
    ])
    renderSection()
    fireEvent.click(screen.getByText(/view previous attempts/i))
    await waitFor(() => expect(screen.getByText('Attempt 1')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Attempt 1'))
    expect(screen.getByText('This investigation could not retrieve a referenced clause.')).toBeInTheDocument()
    expect(screen.queryByText(/unsupported_remediation/)).not.toBeInTheDocument()
  })
})

/** Mirrors exactly how InvestigationWorkspacePage.tsx renders this
 * component: key={attemptNumber} on the same investigationId, so a retry
 * (which bumps the number) forces React to unmount and remount it. */
function KeyedWrapper({ attemptNumber }: { attemptNumber: number }) {
  return (
    <InspectorProvider>
      <AttemptHistorySection
        key={attemptNumber}
        projectId={1}
        investigationId="inv-1"
        documentNames={{}}
        documents={null}
      />
    </InspectorProvider>
  )
}

describe('AttemptHistorySection remount on attempt_number change (pre-commit review fix)', () => {
  it('discards stale, already-loaded history and reverts to closed when its key changes after a retry', async () => {
    getInvestigationAttemptsMock.mockResolvedValueOnce([
      attempt({ attempt_number: 1, is_current: true, status: 'failed' }),
    ])
    const { rerender } = render(<KeyedWrapper attemptNumber={2} />)

    fireEvent.click(screen.getByText(/view previous attempts/i))
    await waitFor(() => expect(screen.getByText('Attempt 1')).toBeInTheDocument())
    expect(screen.getByText('Current')).toBeInTheDocument()

    // Simulates a retry completing: attempt_number advances on the SAME
    // investigationId, giving the section a new key.
    getInvestigationAttemptsMock.mockResolvedValueOnce([
      attempt({ attempt_number: 1, is_current: false, status: 'failed' }),
      attempt({ attempt_number: 2, is_current: true, status: 'completed' }),
    ])
    rerender(<KeyedWrapper attemptNumber={3} />)

    // Remounted: back to the closed state, NOT still showing the stale
    // attempt-1-is-current list from before the retry.
    expect(screen.getByText(/view previous attempts/i)).toBeInTheDocument()
    expect(screen.queryByText('Attempt 1')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText(/view previous attempts/i))
    await waitFor(() => expect(screen.getByText('Attempt 2')).toBeInTheDocument())
    expect(screen.getByText('Attempt 1')).toBeInTheDocument()
    // The old is_current=true (attempt 1) is correctly superseded; only
    // attempt 2 is now current.
    expect(screen.getAllByText('Current')).toHaveLength(1)
    expect(getInvestigationAttemptsMock).toHaveBeenCalledTimes(2)
  })
})

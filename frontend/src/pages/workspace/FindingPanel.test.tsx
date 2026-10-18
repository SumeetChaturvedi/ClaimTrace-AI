import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { InvestigationResponse } from '../../api/types'
import { InspectorProvider } from '../../components/layout/InspectorContext'
import { FindingPanel } from './FindingPanel'

function response(overrides: Partial<InvestigationResponse> = {}): InvestigationResponse {
  return {
    answer: 'A fixture finding.',
    citations: [],
    reasoning_steps: [],
    timeline: [],
    contract_clauses: [],
    events: [],
    events_error: null,
    events_truncated: false,
    answer_truncated: false,
    evidence_limitation: null,
    ...overrides,
  }
}

function renderPanel(overrides: Partial<InvestigationResponse> = {}) {
  return render(
    <InspectorProvider>
      <FindingPanel
        response={response(overrides)}
        documentNames={{}}
        documents={null}
        projectId={1}
        investigationId="inv-1"
      />
    </InspectorProvider>,
  )
}

describe('FindingPanel evidence-limitation and truncation notices (Phase 1 fix)', () => {
  it('shows no limitation notice for a cleanly completed investigation', () => {
    renderPanel({ answer_truncated: false, evidence_limitation: null })
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('shows a truncation warning when answer_truncated is true', () => {
    renderPanel({ answer_truncated: true })
    expect(screen.getByText(/may be incomplete/i)).toBeInTheDocument()
  })

  it('shows the plain-language evidence_limitation message when set', () => {
    renderPanel({ evidence_limitation: 'This investigation could not retrieve a referenced clause.' })
    expect(screen.getByText('This investigation could not retrieve a referenced clause.')).toBeInTheDocument()
  })

  it('shows both notices at once when both are set', () => {
    renderPanel({ answer_truncated: true, evidence_limitation: 'Some evidence could not be retrieved.' })
    expect(screen.getByText(/may be incomplete/i)).toBeInTheDocument()
    expect(screen.getByText('Some evidence could not be retrieved.')).toBeInTheDocument()
  })

  it('never renders the raw internal stopping-reason name', () => {
    renderPanel({ evidence_limitation: 'This investigation could not retrieve a referenced clause.' })
    expect(screen.queryByText(/unsupported_remediation/)).not.toBeInTheDocument()
  })
})

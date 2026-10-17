import { render, screen } from '@testing-library/react'
import { useEffect } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { Citation, ExtractedEvent } from '../../api/types'
import { Inspector } from './Inspector'
import { InspectorProvider, useInspector } from './InspectorContext'

function event(overrides: Partial<ExtractedEvent> = {}): ExtractedEvent {
  return {
    document_id: 1,
    chunk_id: 10,
    excerpt: 'fixture excerpt text',
    event_type: 'CLARIFICATION_REQUESTED',
    assertion_type: 'request',
    description: 'A fixture event description',
    event_date: '2024-03-01',
    event_date_basis: 'explicit',
    attributed_party: 'Fixture Party',
    ...overrides,
  }
}

/** Opens `content` as soon as it mounts, inside the real InspectorProvider,
 * so Inspector.tsx renders exactly what a real caller (EventsPanel,
 * EvidencePanel, ...) would have produced. */
function OpenOnMount({ event: e, matchingCitation }: { event: ExtractedEvent; matchingCitation: Citation | null }) {
  const { open } = useInspector()
  useEffect(() => {
    open({
      kind: 'timelineEvent',
      event: e,
      matchingCitation,
      documentName: 'notice.pdf',
      documentType: 'EMAIL',
      projectId: 1,
      investigationId: 'inv-1',
    })
    // Intentionally run only once per mount — `open` is a stable callback
    // (see InspectorContext.tsx's useCallback) and this harness's whole
    // purpose is "open exactly this fixture content on mount".
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return null
}

function renderInspectorWithEvent(e: ExtractedEvent, matchingCitation: Citation | null) {
  return render(
    <MemoryRouter>
      <InspectorProvider>
        <OpenOnMount event={e} matchingCitation={matchingCitation} />
        <Inspector />
      </InspectorProvider>
    </MemoryRouter>,
  )
}

describe('Inspector timelineEvent rendering', () => {
  it('labels the event as AI-extracted and states it is not a verified fact', () => {
    renderInspectorWithEvent(event(), null)
    expect(screen.getByText('AI-extracted')).toBeInTheDocument()
    expect(screen.getByText(/not a verified fact or legal conclusion/i)).toBeInTheDocument()
  })

  it('shows event date alongside its basis, distinct from source document date', () => {
    renderInspectorWithEvent(event({ event_date: '2024-03-01', event_date_basis: 'explicit' }), null)
    expect(screen.getByText('2024-03-01')).toBeInTheDocument()
    expect(screen.getByText('(Explicit)')).toBeInTheDocument()
    expect(screen.getByText(/own event date may differ from the date the source message/i)).toBeInTheDocument()
  })

  it('shows "not available" rather than a fabricated value when event_type is null', () => {
    renderInspectorWithEvent(event({ event_type: null }), null)
    expect(screen.getByText('Not available')).toBeInTheDocument()
  })

  it('shows an "Open source document" link when a matching citation exists', () => {
    const citation: Citation = { document_id: 1, chunk_id: 10, page: 4, relevance_score: 0.7, chunk_text: 'text' }
    renderInspectorWithEvent(event(), citation)
    expect(screen.getByRole('link', { name: /open source document/i })).toHaveAttribute(
      'href',
      '/projects/1/investigations/inv-1/source/10',
    )
  })

  it('does not render a source-document link when no matching citation exists, rather than a broken one', () => {
    renderInspectorWithEvent(event(), null)
    expect(screen.queryByRole('link', { name: /open source document/i })).not.toBeInTheDocument()
    expect(screen.getByText(/can't be opened separately/i)).toBeInTheDocument()
  })

  it('renders the verbatim excerpt exactly as provided', () => {
    renderInspectorWithEvent(event({ excerpt: 'The exact supporting passage text.' }), null)
    expect(screen.getByText('The exact supporting passage text.')).toBeInTheDocument()
  })
})

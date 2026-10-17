import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Citation, ExtractedEvent } from '../../api/types'
import { InspectorProvider, useInspector } from '../../components/layout/InspectorContext'
import { EventsPanel } from './EventsPanel'

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

/** Renders whatever Inspector content was opened, as plain text, so a test
 * can assert on it without needing the real Inspector component. */
function InspectorProbe() {
  const { content } = useInspector()
  if (!content) return <div data-testid="inspector-probe">none</div>
  if (content.kind === 'timelineEvent') {
    return (
      <div data-testid="inspector-probe">
        timelineEvent:{content.event.description}:{content.matchingCitation ? 'has-citation' : 'no-citation'}
      </div>
    )
  }
  return <div data-testid="inspector-probe">{content.kind}</div>
}

function renderPanel(props: Partial<React.ComponentProps<typeof EventsPanel>> = {}) {
  const defaults: React.ComponentProps<typeof EventsPanel> = {
    events: [],
    eventsError: null,
    eventsTruncated: false,
    citations: [],
    documentNames: {},
    documentTypes: {},
    projectId: 1,
    investigationId: 'inv-1',
  }
  return render(
    <InspectorProvider>
      <EventsPanel {...defaults} {...props} />
      <InspectorProbe />
    </InspectorProvider>,
  )
}

describe('EventsPanel extraction states', () => {
  it('shows a neutral empty state when extraction succeeded with no events', () => {
    renderPanel({ events: [], eventsError: null })
    expect(screen.getByText(/no ai-extracted events are associated/i)).toBeInTheDocument()
    expect(screen.queryByText(/unavailable/i)).not.toBeInTheDocument()
  })

  it('explains extraction failure distinctly from an empty result, never implying no relevant events', () => {
    renderPanel({ events: [], eventsError: 'Gemini call failed: timeout' })
    expect(screen.getByText(/event extraction was unavailable/i)).toBeInTheDocument()
    expect(screen.getByText(/does not mean no relevant events exist/i)).toBeInTheDocument()
    expect(screen.queryByText(/no ai-extracted events are associated/i)).not.toBeInTheDocument()
  })

  it('shows a visible truncation notice when events_truncated is true, alongside the (possibly partial) list', () => {
    renderPanel({ events: [event()], eventsTruncated: true })
    expect(screen.getByText(/may be incomplete/i)).toBeInTheDocument()
    expect(screen.getByText('A fixture event description')).toBeInTheDocument()
  })

  it('shows no truncation notice when events_truncated is false', () => {
    renderPanel({ events: [event()], eventsTruncated: false })
    expect(screen.queryByText(/may be incomplete/i)).not.toBeInTheDocument()
  })
})

describe('EventsPanel chronological and grouping behavior', () => {
  it('renders dated events under a Chronological section and undated ones under a separate section', () => {
    const dated = event({ document_id: 1, chunk_id: 1, event_date: '2024-01-01', description: 'Dated event' })
    const undated = event({ document_id: 2, chunk_id: 2, event_date: null, event_date_basis: 'unknown', description: 'Undated event' })
    renderPanel({ events: [dated, undated] })

    expect(screen.getByText('Chronological')).toBeInTheDocument()
    expect(screen.getByText('Date not known')).toBeInTheDocument()
    expect(screen.getByText('Dated event')).toBeInTheDocument()
    expect(screen.getByText('Undated event')).toBeInTheDocument()
  })

  it('renders multiple distinct events from the same source document without collapsing them', () => {
    const e1 = event({ document_id: 1, chunk_id: 1, event_date: '2024-01-01', description: 'First event' })
    const e2 = event({ document_id: 1, chunk_id: 1, event_date: '2024-02-01', description: 'Second event' })
    renderPanel({ events: [e1, e2] })
    expect(screen.getByText('First event')).toBeInTheDocument()
    expect(screen.getByText('Second event')).toBeInTheDocument()
  })

  it('opens each event independently — clicking one never surfaces a different event sharing the same source chunk', () => {
    const e1 = event({ document_id: 1, chunk_id: 1, event_date: '2024-01-01', description: 'First event', attributed_party: 'Party A' })
    const e2 = event({ document_id: 1, chunk_id: 1, event_date: '2024-02-01', description: 'Second event', attributed_party: 'Party B' })
    renderPanel({ events: [e1, e2] })

    fireEvent.click(screen.getByText('First event'))
    expect(screen.getByTestId('inspector-probe')).toHaveTextContent('timelineEvent:First event:no-citation')

    fireEvent.click(screen.getByText('Second event'))
    expect(screen.getByTestId('inspector-probe')).toHaveTextContent('timelineEvent:Second event:no-citation')
    expect(screen.getByTestId('inspector-probe')).not.toHaveTextContent('First event')
  })

  it('displays missing optional attribution gracefully, without fabricating a party', () => {
    const e = event({ attributed_party: null })
    renderPanel({ events: [e] })
    expect(screen.getByText(/not available/i)).toBeInTheDocument()
  })
})

describe('EventsPanel Inspector navigation', () => {
  const matchingCitation: Citation = { document_id: 1, chunk_id: 10, page: 3, relevance_score: 0.8, chunk_text: 'cited text' }

  it('opens the Inspector with the event and its matching citation when one exists', () => {
    renderPanel({ events: [event()], citations: [matchingCitation] })
    fireEvent.click(screen.getByText('A fixture event description'))
    expect(screen.getByTestId('inspector-probe')).toHaveTextContent('timelineEvent:A fixture event description:has-citation')
  })

  it('opens the Inspector without a citation, rather than a broken link, when no matching citation exists', () => {
    renderPanel({ events: [event()], citations: [] })
    fireEvent.click(screen.getByText('A fixture event description'))
    expect(screen.getByTestId('inspector-probe')).toHaveTextContent('timelineEvent:A fixture event description:no-citation')
  })
})

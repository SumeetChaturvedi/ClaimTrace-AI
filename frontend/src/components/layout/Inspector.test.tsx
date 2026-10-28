import { render, screen } from '@testing-library/react'
import { useEffect } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { Citation, DocumentSummary, ExtractedEvent } from '../../api/types'
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

/** Opens a 'citation' content item on mount, exactly as CitationList/
 * EvidencePanel do via useInspector().open(). */
function OpenCitationOnMount({
  citation,
  documentName,
  documentType,
  documentDerivationKind,
  projectId = 1,
  investigationId = 'inv-1',
}: {
  citation: Citation
  documentName?: string
  documentType?: string | null
  documentDerivationKind?: DocumentSummary['derivation_kind']
  projectId?: number
  investigationId?: string
}) {
  const { open } = useInspector()
  useEffect(() => {
    open({ kind: 'citation', citation, documentName, documentType, documentDerivationKind, projectId, investigationId })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return null
}

function renderInspectorWithCitation(props: {
  citation: Citation
  documentName?: string
  documentType?: string | null
  documentDerivationKind?: DocumentSummary['derivation_kind']
  projectId?: number
  investigationId?: string
}) {
  return render(
    <MemoryRouter>
      <InspectorProvider>
        <OpenCitationOnMount {...props} />
        <Inspector />
      </InspectorProvider>
    </MemoryRouter>,
  )
}

describe('Inspector citation rendering — derived-evidence provenance', () => {
  const citation: Citation = { document_id: 5, chunk_id: 50, page: 2, relevance_score: 0.8, chunk_text: 'excerpt' }

  it('labels a locally-transcribed OCR document with an "OCR" badge', () => {
    renderInspectorWithCitation({ citation, documentName: 'scan.jpg.ocr.txt', documentDerivationKind: 'ocr_transcription' })
    expect(screen.getByText('OCR')).toBeInTheDocument()
  })

  it('labels an AI-generated visual-description document with an "AI description" badge', () => {
    renderInspectorWithCitation({ citation, documentName: 'photo.jpg.visual.txt', documentDerivationKind: 'visual_description' })
    expect(screen.getByText('AI description')).toBeInTheDocument()
  })

  it('shows no provenance badge at all for an ordinary document', () => {
    renderInspectorWithCitation({ citation, documentName: 'report.pdf', documentType: 'CONTRACT', documentDerivationKind: null })
    expect(screen.queryByText('OCR')).not.toBeInTheDocument()
    expect(screen.queryByText('AI description')).not.toBeInTheDocument()
  })

  it('shows no provenance badge when derivation kind is not provided at all', () => {
    renderInspectorWithCitation({ citation, documentName: 'report.pdf' })
    expect(screen.queryByText('OCR')).not.toBeInTheDocument()
    expect(screen.queryByText('AI description')).not.toBeInTheDocument()
  })
})

/** Pre-commit review follow-up: a prior review found NO test anywhere
 * (for the 'citation' kind specifically) verifying that "Open source
 * document" actually renders with a correct destination — only the
 * 'timelineEvent' kind had one. This closes that gap by exercising the
 * real CitationInspector render path exactly like the provenance tests
 * above, asserting the exact href Inspector.tsx itself builds
 * (`/projects/{projectId}/investigations/{investigationId}/source/{citation.chunk_id}`
 * — see Inspector.tsx's own CitationInspector). Distinct, identifiable
 * document_id/chunk_id/projectId/investigationId values are used so a
 * wrong-field swap (e.g. document_id used where chunk_id belongs) would
 * fail this assertion, not pass it by coincidence. The route itself is
 * not changed here — only asserted against. */
describe('Inspector citation rendering — source-document link', () => {
  it('renders "Open source document" pointing at this exact citation, project, and investigation', () => {
    const citation: Citation = { document_id: 123, chunk_id: 456, page: 7, relevance_score: 0.9, chunk_text: 'excerpt' }
    renderInspectorWithCitation({
      citation,
      documentName: 'site-report.pdf',
      projectId: 42,
      investigationId: 'investigation-abc',
    })

    const link = screen.getByRole('link', { name: /open source document/i })
    expect(link).toHaveAttribute('href', '/projects/42/investigations/investigation-abc/source/456')
    // The link is keyed on chunk_id (the real lookup key the backend
    // resolves to one document), never on document_id directly in the
    // URL -- confirmed here by using a document_id (123) that does NOT
    // appear anywhere in the expected href, so this assertion would fail
    // if a future change accidentally swapped the two fields.
    expect(link.getAttribute('href')).not.toContain('123')
  })
})

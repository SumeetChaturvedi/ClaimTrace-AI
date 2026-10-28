import { render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Project, ProjectImageAssetSummary } from '../api/types'
import { InspectorProvider } from '../components/layout/InspectorContext'
import { ProjectPage } from './ProjectPage'

/**
 * Pre-commit review follow-up (W2.1–W2.3): the Project page's Images
 * section previously claimed images are "not yet searchable or citable"
 * (stale — OCR/visual-description indexing now exists), and its row
 * component only treated 'stored_pending_processing' as openable, so a
 * genuinely successful 'processed' image fell into the same branch as
 * 'rejected'/'failed' and was mislabeled "Processing failed" with no
 * working link. These tests pin the corrected behavior directly against
 * the real `ProjectImageAssetSummary.status` vocabulary.
 */

const {
  getProjectMock,
  listProjectDocumentsMock,
  listInvestigationsMock,
  listEmailThreadsMock,
  listWhatsAppChatsMock,
  listConnectedMailboxesMock,
  listProjectImagesMock,
} = vi.hoisted(() => ({
  getProjectMock: vi.fn(),
  listProjectDocumentsMock: vi.fn(),
  listInvestigationsMock: vi.fn(),
  listEmailThreadsMock: vi.fn(),
  listWhatsAppChatsMock: vi.fn(),
  listConnectedMailboxesMock: vi.fn(),
  listProjectImagesMock: vi.fn(),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    getProject: getProjectMock,
    listProjectDocuments: listProjectDocumentsMock,
    listInvestigations: listInvestigationsMock,
    listEmailThreads: listEmailThreadsMock,
    listWhatsAppChats: listWhatsAppChatsMock,
    listConnectedMailboxes: listConnectedMailboxesMock,
    listProjectImages: listProjectImagesMock,
  }
})

function project(overrides: Partial<Project> = {}): Project {
  return { id: 1, name: 'Riverside Site — Claim 4471', created_at: '2024-01-01T00:00:00Z', ...overrides }
}

function image(overrides: Partial<ProjectImageAssetSummary> = {}): ProjectImageAssetSummary {
  return {
    id: 1,
    filename: 'site-photo.jpg',
    content_type: 'image/jpeg',
    size_bytes: 12345,
    status: 'stored_pending_processing',
    document_id: null,
    processing_error: null,
    width_px: 800,
    height_px: 600,
    uploaded_at: '2024-01-02T00:00:00Z',
    ...overrides,
  }
}

function renderProjectPage() {
  return render(
    <MemoryRouter initialEntries={['/projects/1']}>
      <InspectorProvider>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectPage />} />
        </Routes>
      </InspectorProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(globalThis as any).IntersectionObserver = vi.fn().mockImplementation(function () {
    return { observe: vi.fn(), unobserve: vi.fn(), disconnect: vi.fn() }
  })

  getProjectMock.mockReset()
  listProjectDocumentsMock.mockReset()
  listInvestigationsMock.mockReset()
  listEmailThreadsMock.mockReset()
  listWhatsAppChatsMock.mockReset()
  listConnectedMailboxesMock.mockReset()
  listProjectImagesMock.mockReset()

  getProjectMock.mockResolvedValue(project())
  listProjectDocumentsMock.mockResolvedValue([])
  listInvestigationsMock.mockResolvedValue([])
  listEmailThreadsMock.mockResolvedValue([])
  listWhatsAppChatsMock.mockResolvedValue([])
  listConnectedMailboxesMock.mockResolvedValue([])
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ProjectPage — Images section status handling', () => {
  it('never claims images are unsearchable/uncitable now that OCR and visual-description indexing exist', async () => {
    listProjectImagesMock.mockResolvedValue([])
    renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    expect(screen.queryByText(/does not yet extract text or describe their contents/)).not.toBeInTheDocument()
    expect(screen.queryByText(/not yet searchable or citable/)).not.toBeInTheDocument()
    expect(screen.getByText(/extracted text and any AI-generated visual description become/)).toBeInTheDocument()
  })

  it('renders a processed image as openable, with a "Processed" badge, never "Processing failed"', async () => {
    listProjectImagesMock.mockResolvedValue([image({ id: 7, status: 'processed', document_id: 42 })])
    renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    const row = screen.getByRole('link', { name: /site-photo\.jpg/ })
    expect(row).toHaveAttribute('href', expect.stringContaining('/projects/1/images/7/file'))
    expect(within(row).getByText('Processed')).toBeInTheDocument()
    expect(screen.queryByText(/Processing failed/)).not.toBeInTheDocument()
  })

  it('renders a processed image with no resulting document (document_id null) as openable, never "Processing failed", and never implies a derived document exists', async () => {
    // Pre-commit review follow-up: a 'processed' image whose OCR/visual
    // attempts both genuinely found nothing still gets status='processed'
    // with document_id left null (see image_ocr_indexing.py's own
    // "empty text, no existing document" branch) -- this must be treated
    // identically to a processed image that DID produce a document: the
    // original is still openable, and the UI must never read document_id
    // to decide that, since this exact case proves the two aren't linked.
    listProjectImagesMock.mockResolvedValue([image({ id: 10, status: 'processed', document_id: null })])
    renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    const row = screen.getByRole('link', { name: /site-photo\.jpg/ })
    expect(row).toHaveAttribute('href', expect.stringContaining('/projects/1/images/10/file'))
    expect(within(row).getByText('Processed')).toBeInTheDocument()
    expect(screen.queryByText(/Processing failed/)).not.toBeInTheDocument()
    // No claim of a derived document, citable text, or description within
    // THIS row -- the status badge alone, nothing naming a document that
    // may not exist (the page's own general Images-section blurb mentions
    // "documents" elsewhere, which is why this check is scoped to the row).
    expect(within(row).queryByText(/document/i)).not.toBeInTheDocument()
  })

  it('renders a stored_pending_processing image as openable with its own distinct label, no badge', async () => {
    listProjectImagesMock.mockResolvedValue([image({ id: 8, status: 'stored_pending_processing' })])
    renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    const row = screen.getByRole('link', { name: /site-photo\.jpg/ })
    expect(row).toHaveAttribute('href', expect.stringContaining('/projects/1/images/8/file'))
    expect(within(row).getByText('Preserved — not yet processed')).toBeInTheDocument()
    expect(within(row).queryByText('Processed')).not.toBeInTheDocument()
  })

  it('renders a rejected image as plain, non-openable text with its real reason', async () => {
    listProjectImagesMock.mockResolvedValue([
      image({ id: null, status: 'rejected', processing_error: 'file exceeds the maximum allowed size', uploaded_at: null }),
    ])
    renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    expect(screen.queryByRole('link', { name: /site-photo\.jpg/ })).not.toBeInTheDocument()
    expect(screen.getByText(/Rejected: file exceeds the maximum allowed size/)).toBeInTheDocument()
  })

  it('renders a genuinely failed image as plain, non-openable text, distinct from "processed"', async () => {
    listProjectImagesMock.mockResolvedValue([
      image({ id: 9, status: 'failed', processing_error: 'commit failed', document_id: null }),
    ])
    renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    expect(screen.queryByRole('link', { name: /site-photo\.jpg/ })).not.toBeInTheDocument()
    expect(screen.getByText(/Processing failed: commit failed/)).toBeInTheDocument()
  })
})

describe('ProjectPage — direct image upload control', () => {
  /** Pre-commit review follow-up: there was previously no way to select
   * an image through the page's one upload control at all -- its
   * `accept` attribute listed only PDF/DOCX, even though the backend
   * endpoint it posts to (POST /projects/{id}/documents) already
   * accepts images by content-sniffing their real bytes, and
   * handleFileChange already handles `result.images` in the response.
   * This pins the control's `accept` list and visible label directly,
   * rather than merely asserting an upload "succeeds" (which a unit
   * test can't meaningfully exercise against a mocked fetch anyway). */
  it('accepts PDF, DOCX, and the four supported image formats, and the button reads "Add Files"', async () => {
    listProjectImagesMock.mockResolvedValue([])
    listProjectDocumentsMock.mockResolvedValue([])
    const { container } = renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    const button = screen.getByRole('button', { name: 'Add Files' })
    expect(button).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add Documents' })).not.toBeInTheDocument()

    // The Document Register's own file input is first in source order
    // (Document Register, then Email import, then WhatsApp import) --
    // mirrors ProjectPage.whatsappImportSummary.test.tsx's own
    // position-based lookup convention for the sibling inputs.
    const fileInput = container.querySelectorAll<HTMLInputElement>('input[type="file"]')[0]
    const accept = fileInput.accept
    for (const expected of [
      '.pdf',
      '.docx',
      '.jpg',
      '.jpeg',
      '.png',
      '.gif',
      '.webp',
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'image/jpeg',
      'image/png',
      'image/gif',
      'image/webp',
    ]) {
      expect(accept).toContain(expected)
    }
  })

  it('tells users images are uploaded through the same "Add Files" control, not a separate one', async () => {
    listProjectImagesMock.mockResolvedValue([])
    renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    expect(screen.getByText(/uploaded through the same "Add Files" control/)).toBeInTheDocument()
  })
})

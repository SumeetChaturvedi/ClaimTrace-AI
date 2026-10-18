import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Project, WhatsAppImportResult } from '../api/types'
import { InspectorProvider } from '../components/layout/InspectorContext'
import { ProjectPage } from './ProjectPage'

const {
  getProjectMock,
  listProjectDocumentsMock,
  listInvestigationsMock,
  listEmailThreadsMock,
  listWhatsAppChatsMock,
  listConnectedMailboxesMock,
  importWhatsAppExportMock,
} = vi.hoisted(() => ({
  getProjectMock: vi.fn(),
  listProjectDocumentsMock: vi.fn(),
  listInvestigationsMock: vi.fn(),
  listEmailThreadsMock: vi.fn(),
  listWhatsAppChatsMock: vi.fn(),
  listConnectedMailboxesMock: vi.fn(),
  importWhatsAppExportMock: vi.fn(),
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
    importWhatsAppExport: importWhatsAppExportMock,
  }
})

function project(overrides: Partial<Project> = {}): Project {
  return { id: 1, name: 'Riverside Site — Claim 4471', created_at: '2024-01-01T00:00:00Z', ...overrides }
}

function importResult(overrides: Partial<WhatsAppImportResult> = {}): WhatsAppImportResult {
  return {
    chat_id: 1,
    chat_title: 'Site Chat',
    imported: 2,
    duplicate: 0,
    attachments_processed: 0,
    attachments_pending: 0,
    attachments_unsupported: 0,
    attachments_rejected: 0,
    attachments_failed: 0,
    attachments_ambiguous: 0,
    parse_warnings: [],
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

/** The hidden WhatsApp file input is the third of three file inputs in
 * source order (documents, email, WhatsApp) — it carries no accessible
 * name of its own, so it's located by DOM position rather than by role. */
function getWhatsAppFileInput(container: HTMLElement): HTMLInputElement {
  const inputs = container.querySelectorAll<HTMLInputElement>('input[type="file"]')
  return inputs[inputs.length - 1]
}

async function importFile(container: HTMLElement) {
  const input = getWhatsAppFileInput(container)
  const file = new File(['chat export bytes'], 'chat.zip', { type: 'application/zip' })
  await waitFor(() => expect(input).not.toBeDisabled())
  fireEvent.change(input, { target: { files: [file] } })
}

beforeEach(() => {
  // jsdom has no real matchMedia implementation; ProjectPage's decorative
  // reveal-on-scroll hook (useRevealOnScroll) reads prefers-reduced-motion
  // on mount. Stubbed here only, not in production code.
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
  // jsdom also has no real IntersectionObserver; the same hook falls
  // back to it when motion isn't reduced. Stubbed here only.
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
  importWhatsAppExportMock.mockReset()

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

describe('ProjectPage — WhatsApp import summary (ambiguous attachments)', () => {
  it('reports the ambiguous attachment count distinctly, never as a success', async () => {
    importWhatsAppExportMock.mockResolvedValue(
      importResult({ imported: 2, attachments_processed: 1, attachments_ambiguous: 1 }),
    )
    const { container } = renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    await importFile(container)

    await waitFor(() =>
      expect(screen.getByText(/1 attachment could not be matched \(multiple archive files shared the same name\)/)).toBeInTheDocument(),
    )
    // The other, successfully-processed attachment is still reported —
    // the ambiguous one must never be folded into or confused with it.
    expect(screen.getByText(/2 new messages imported/)).toBeInTheDocument()
    expect(screen.getByText(/1 attachment indexed/)).toBeInTheDocument()
    // Never described as itself successfully processed/indexed.
    expect(screen.queryByText(/2 attachments indexed/)).not.toBeInTheDocument()
  })

  it('pluralizes correctly for more than one ambiguous attachment', async () => {
    importWhatsAppExportMock.mockResolvedValue(importResult({ imported: 3, attachments_ambiguous: 2 }))
    const { container } = renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    await importFile(container)

    await waitFor(() =>
      expect(screen.getByText(/2 attachments could not be matched \(multiple archive files shared the same name\)/)).toBeInTheDocument(),
    )
  })

  it('omits any ambiguous-attachment mention when there are none, and keeps the normal summary intact', async () => {
    importWhatsAppExportMock.mockResolvedValue(
      importResult({ imported: 4, duplicate: 1, attachments_processed: 2, attachments_pending: 1 }),
    )
    const { container } = renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    await importFile(container)

    await waitFor(() => expect(screen.getByText(/4 new messages imported/)).toBeInTheDocument())
    expect(screen.getByText(/1 already imported/)).toBeInTheDocument()
    expect(screen.getByText(/2 attachments indexed/)).toBeInTheDocument()
    expect(screen.getByText(/1 attachment preserved \(not yet processed\)/)).toBeInTheDocument()
    expect(screen.queryByText(/could not be matched/)).not.toBeInTheDocument()
  })

  it('tolerates a response missing the attachments_ambiguous field entirely, without throwing or miscounting', async () => {
    // Defensive handling: an older/partial API response shape must not
    // crash the summary builder or silently claim success for anything.
    const legacyResult = importResult({ imported: 1 }) as unknown as Record<string, unknown>
    delete legacyResult.attachments_ambiguous
    importWhatsAppExportMock.mockResolvedValue(legacyResult)

    const { container } = renderProjectPage()
    await waitFor(() => expect(screen.getAllByText('Riverside Site — Claim 4471').length).toBeGreaterThan(0))

    await importFile(container)

    await waitFor(() => expect(screen.getByText(/1 new message imported/)).toBeInTheDocument())
    expect(screen.queryByText(/could not be matched/)).not.toBeInTheDocument()
  })
})

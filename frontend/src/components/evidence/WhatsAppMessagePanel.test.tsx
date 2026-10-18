import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { WhatsAppMessageDetail } from '../../api/types'
import { InspectorProvider } from '../layout/InspectorContext'
import { WhatsAppMessagePanel } from './WhatsAppMessagePanel'

const { getWhatsAppMessageMock } = vi.hoisted(() => ({
  getWhatsAppMessageMock: vi.fn(),
}))

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return {
    ...actual,
    getWhatsAppMessage: getWhatsAppMessageMock,
  }
})

function message(overrides: Partial<WhatsAppMessageDetail> = {}): WhatsAppMessageDetail {
  return {
    document_id: 1,
    chat_id: 1,
    sequence_index: 0,
    sender_name: 'Site Engineer',
    raw_timestamp_text: '25/03/24, 10:00:00',
    sent_at: '2024-03-25T10:00:00',
    sent_at_ambiguous: false,
    message_type: 'text',
    status: 'ready',
    processing_error: null,
    doc_date: '2024-03-25',
    text: 'Checking status of the retaining wall.',
    attachments: [],
    ...overrides,
  }
}

function renderPanel(overrides: Partial<WhatsAppMessageDetail> = {}) {
  getWhatsAppMessageMock.mockResolvedValue(message(overrides))
  return render(
    <MemoryRouter>
      <InspectorProvider>
        <WhatsAppMessagePanel projectId={1} documentId={1} />
      </InspectorProvider>
    </MemoryRouter>,
  )
}

describe('WhatsAppMessagePanel (Phase W1)', () => {
  it('renders sender, raw timestamp text, and message text', async () => {
    renderPanel()
    await waitFor(() => expect(screen.getByText('Site Engineer')).toBeInTheDocument())
    expect(screen.getByText('25/03/24, 10:00:00')).toBeInTheDocument()
    expect(screen.getByText('Checking status of the retaining wall.')).toBeInTheDocument()
  })

  it('shows the ambiguity note when sent_at_ambiguous is true', async () => {
    renderPanel({ sent_at_ambiguous: true })
    await waitFor(() =>
      expect(screen.getByText(/day\/month order could not be confirmed/i)).toBeInTheDocument(),
    )
  })

  it('does not show the ambiguity note when the timestamp is unambiguous', async () => {
    renderPanel({ sent_at_ambiguous: false })
    await waitFor(() => expect(screen.getByText('Site Engineer')).toBeInTheDocument())
    expect(screen.queryByText(/day\/month order could not be confirmed/i)).not.toBeInTheDocument()
  })

  it('shows "System / group event" for a message with no sender', async () => {
    renderPanel({ sender_name: null, message_type: 'system', text: 'Alice added Bob' })
    await waitFor(() => expect(screen.getAllByText('System / group event').length).toBeGreaterThan(0))
  })

  it('renders a processed attachment as a link to its own source document', async () => {
    renderPanel({
      attachments: [
        {
          id: 10,
          filename: 'notice.pdf',
          content_type: 'application/pdf',
          size_bytes: 1234,
          status: 'processed',
          document_id: 42,
          processing_error: null,
        },
      ],
    })
    await waitFor(() => expect(screen.getByText('notice.pdf')).toBeInTheDocument())
    const link = screen.getByText('notice.pdf').closest('a')
    expect(link).toHaveAttribute('href', '/projects/1/documents/42/source')
    expect(screen.getByText('Indexed')).toBeInTheDocument()
  })

  it('renders a stored-pending-processing attachment as a direct file link, never fabricated as indexed', async () => {
    renderPanel({
      attachments: [
        {
          id: 11,
          filename: 'photo.jpg',
          content_type: 'image/jpeg',
          size_bytes: 500,
          status: 'stored_pending_processing',
          document_id: null,
          processing_error: null,
        },
      ],
    })
    await waitFor(() => expect(screen.getByText('photo.jpg')).toBeInTheDocument())
    const link = screen.getByText('photo.jpg').closest('a')
    expect(link).toHaveAttribute('href', '/api/projects/1/whatsapp/attachments/11/file')
    expect(screen.getByText('Preserved — not yet processed')).toBeInTheDocument()
  })

  it('renders a rejected attachment as plain, non-clickable text', async () => {
    renderPanel({
      attachments: [
        {
          id: 12,
          filename: 'missing.jpg',
          content_type: null,
          size_bytes: 0,
          status: 'rejected',
          document_id: null,
          processing_error: 'referenced media file was not present in the uploaded export',
        },
      ],
    })
    await waitFor(() => expect(screen.getByText('missing.jpg')).toBeInTheDocument())
    expect(screen.getByText('missing.jpg').closest('a')).toBeNull()
    expect(screen.getByText('Rejected')).toBeInTheDocument()
  })

  it('shows the highlighted cited passage only when provided (citation flow)', async () => {
    getWhatsAppMessageMock.mockResolvedValue(message())
    render(
      <MemoryRouter>
        <InspectorProvider>
          <WhatsAppMessagePanel projectId={1} documentId={1} highlightExcerpt="exact cited text" />
        </InspectorProvider>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText('exact cited text')).toBeInTheDocument())
    expect(screen.getByText('Exact excerpt used in this investigation')).toBeInTheDocument()
  })
})

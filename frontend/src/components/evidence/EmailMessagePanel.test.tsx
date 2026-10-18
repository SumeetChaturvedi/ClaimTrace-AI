import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { EmailMessageDetail } from '../../api/types'
import { EmailMessagePanel } from './EmailMessagePanel'

const { getEmailMessageMock } = vi.hoisted(() => ({
  getEmailMessageMock: vi.fn(),
}))

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return {
    ...actual,
    getEmailMessage: getEmailMessageMock,
  }
})

function message(overrides: Partial<EmailMessageDetail> = {}): EmailMessageDetail {
  return {
    document_id: 1,
    thread_id: 1,
    message_id: '<msg@example.com>',
    in_reply_to: null,
    references: null,
    sender_name: 'Site Engineer',
    sender_email: 'engineer@example.com',
    to_recipients: [],
    cc_recipients: [],
    subject: 'Site update',
    sent_at: '2024-03-25T10:00:00Z',
    sent_at_timezone_unknown: false,
    status: 'ready',
    processing_error: null,
    doc_date: '2024-03-25',
    plain_body: 'See attached.',
    has_html_body: false,
    attachments: [],
    ...overrides,
  }
}

function renderPanel(overrides: Partial<EmailMessageDetail> = {}) {
  getEmailMessageMock.mockResolvedValue(message(overrides))
  return render(
    <MemoryRouter>
      <EmailMessagePanel projectId={1} documentId={1} />
    </MemoryRouter>,
  )
}

describe('EmailMessagePanel — Phase W2.0 image preservation', () => {
  it('renders a preserved (stored_pending_processing) image attachment as a direct file link, never as indexed', async () => {
    renderPanel({
      attachments: [
        {
          id: 10,
          filename: 'site-photo.jpg',
          content_type: 'image/jpeg',
          size_bytes: 2048,
          status: 'stored_pending_processing',
          document_id: null,
          processing_error: null,
        },
      ],
    })
    await waitFor(() => expect(screen.getByText('site-photo.jpg')).toBeInTheDocument())
    const link = screen.getByText('site-photo.jpg').closest('a')
    expect(link).toHaveAttribute('href', '/api/projects/1/emails/attachments/10/file')
    expect(screen.getByText('Preserved — not yet processed')).toBeInTheDocument()
  })

  it('renders a processed PDF/DOCX attachment as a link to its own source document, unaffected by image handling', async () => {
    renderPanel({
      attachments: [
        {
          id: 11,
          filename: 'notice.pdf',
          content_type: 'application/pdf',
          size_bytes: 4096,
          status: 'processed',
          document_id: 42,
          processing_error: null,
        },
      ],
    })
    await waitFor(() => expect(screen.getByText('notice.pdf')).toBeInTheDocument())
    const link = screen.getByText('notice.pdf').closest('a')
    expect(link).toHaveAttribute('href', '/projects/1/documents/42/source')
    expect(screen.getByText('Available')).toBeInTheDocument()
  })

  it('renders a rejected image (corrupt/oversized) as plain, non-clickable text with its real status', async () => {
    renderPanel({
      attachments: [
        {
          id: 12,
          filename: 'broken.jpg',
          content_type: null,
          size_bytes: 500,
          status: 'rejected',
          document_id: null,
          processing_error: 'could not read image (cannot identify image file)',
        },
      ],
    })
    await waitFor(() => expect(screen.getByText('broken.jpg')).toBeInTheDocument())
    expect(screen.getByText('broken.jpg').closest('a')).toBeNull()
    expect(screen.getByText('Rejected')).toBeInTheDocument()
  })
})

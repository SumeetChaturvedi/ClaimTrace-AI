import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderMarkdown, stripMarkdownToPlainText } from './markdown'

/**
 * Pre-commit review fix: the Finding panel previously displayed raw
 * Markdown syntax (###, **text**, ---) literally, because the model's
 * own Markdown-formatted answer was rendered as a plain text node with
 * no parsing step at all. These tests pin renderMarkdown()'s actual
 * output against real-world-shaped input (including a fragment of the
 * literal answer text recovered from the first live investigation that
 * surfaced this defect), and confirm the renderer never falls back to
 * dangerouslySetInnerHTML or any other unsafe HTML-injection path.
 */

function renderText(text: string) {
  return render(<div data-testid="root">{renderMarkdown(text)}</div>)
}

describe('renderMarkdown', () => {
  it('renders a heading as a real heading element, not literal "#" characters', () => {
    renderText('### 1. Parties Involved')
    const heading = screen.getByRole('heading', { level: 3, name: '1. Parties Involved' })
    expect(heading.tagName).toBe('H3')
    expect(screen.queryByText(/###/)).not.toBeInTheDocument()
  })

  it('renders **bold** as a real <strong> element, not literal asterisks', () => {
    const { container } = renderText('The **Contractor** was notified.')
    const strong = container.querySelector('strong')
    expect(strong).not.toBeNull()
    expect(strong?.textContent).toBe('Contractor')
    expect(screen.queryByText(/\*\*/)).not.toBeInTheDocument()
  })

  it('renders a bullet list as a real <ul>/<li> structure', () => {
    const { container } = renderText('*   First point\n*   Second point')
    const items = container.querySelectorAll('li')
    expect(items).toHaveLength(2)
    expect(items[0].textContent).toBe('First point')
    expect(items[1].textContent).toBe('Second point')
    expect(container.querySelector('ul')).not.toBeNull()
  })

  it('renders a horizontal rule as a real <hr>, not literal dashes', () => {
    const { container } = renderText('Before.\n\n---\n\nAfter.')
    expect(container.querySelector('hr')).not.toBeNull()
    expect(screen.queryByText('---')).not.toBeInTheDocument()
  })

  it('renders consecutive plain lines as one paragraph', () => {
    const { container } = renderText('Line one of the summary.\nLine two of the summary.')
    const paragraphs = container.querySelectorAll('p')
    expect(paragraphs).toHaveLength(1)
    expect(paragraphs[0].textContent).toBe('Line one of the summary. Line two of the summary.')
  })

  it('matches the real failure case: a heading immediately followed by bold bullet items, with no literal Markdown syntax left in the rendered text', () => {
    const excerpt =
      '### 1. Parties Involved\n' +
      '*   **Contractor** (represented by the Project Manager, Site Geotechnical Engineer)\n' +
      "*   **Contractor's approved rebar supplier** [1]"
    const { container } = renderText(excerpt)

    expect(screen.getByRole('heading', { level: 3 })).toBeInTheDocument()
    expect(container.querySelectorAll('li')).toHaveLength(2)
    expect(container.querySelectorAll('strong').length).toBeGreaterThanOrEqual(2)
    expect(screen.queryByText(/###/)).not.toBeInTheDocument()
    expect(screen.queryByText(/\*\*/)).not.toBeInTheDocument()
  })

  it('never injects raw HTML: a literal tag in the model output is shown as escaped text, not parsed as an element', () => {
    const { container } = renderText('Evidence noted a <script>alert(1)</script> reference in the log.')
    expect(container.querySelector('script')).toBeNull()
    expect(screen.getByText(/<script>alert\(1\)<\/script>/)).toBeInTheDocument()
  })

  it('returns an empty render for an empty string, without throwing', () => {
    const { container } = renderText('')
    expect(container.querySelector('[data-testid="root"]')?.textContent).toBe('')
  })
})

describe('stripMarkdownToPlainText', () => {
  /** Independent review follow-up: AttemptHistorySection's collapsed-row
   * preview truncates an answer to 160 characters and shows it as plain
   * text, outside renderMarkdown()'s block rendering (a preview can be
   * cut off mid-heading/mid-list, where full rendering doesn't apply) --
   * but the raw syntax characters still must not leak through there. */
  it('removes a heading marker, keeping its text', () => {
    expect(stripMarkdownToPlainText('### Summary')).toBe('Summary')
  })

  it('removes bullet markers, keeping each item\'s text, joined with a space', () => {
    expect(stripMarkdownToPlainText('*   First point\n*   Second point')).toBe('First point Second point')
  })

  it('removes bold markers, keeping the enclosed text', () => {
    expect(stripMarkdownToPlainText('**Key finding:** the pier was affected.')).toBe(
      'Key finding: the pier was affected.',
    )
  })

  it('drops a horizontal-rule line entirely rather than leaving a bare "---"', () => {
    expect(stripMarkdownToPlainText('Before.\n\n---\n\nAfter.')).toBe('Before. After.')
  })

  it('matches the real failure case: heading + bold bullets collapse to clean, readable plain text', () => {
    const excerpt = '### 1. Parties Involved\n*   **Contractor** (represented by the Project Manager)'
    const result = stripMarkdownToPlainText(excerpt)
    expect(result).toBe('1. Parties Involved Contractor (represented by the Project Manager)')
    expect(result).not.toMatch(/[#*]/)
  })

  it('returns an empty string for an empty string, without throwing', () => {
    expect(stripMarkdownToPlainText('')).toBe('')
  })
})

import { createElement, Fragment, type ReactNode } from 'react'

/**
 * Minimal, safe Markdown-subset renderer for ClaimTrace's own
 * model-generated investigation answers (Finding panel, Investigation
 * Record, and attempt history — the three places that render the raw
 * `answer` string a Gemini-backed investigation produced). Supports
 * exactly what Gemini's own default formatting actually produces for
 * this application's prompts: headings (#-######), paragraphs, **bold**,
 * unordered lists (bullets starting with an asterisk or hyphen), and
 * horizontal rules (--- or a line of asterisks).
 * Deliberately does not support links, images, code blocks, tables, or
 * italics — none of those appear in this application's own investigation
 * answers, and adding support for them would be scope beyond the
 * reported defect.
 *
 * Builds real React elements directly from the recognized markers; never
 * parses or injects HTML, and never uses dangerouslySetInnerHTML. Any
 * text that doesn't match a recognized marker (including literal HTML
 * tags the model might emit) is rendered as an ordinary React text node,
 * which React always escapes — this is what makes the renderer safe
 * without any sanitization library.
 */

type Block =
  | { kind: 'heading'; level: number; text: string }
  | { kind: 'hr' }
  | { kind: 'list'; items: string[] }
  | { kind: 'paragraph'; lines: string[] }

const HEADING_RE = /^(#{1,6})\s+(.*)$/
const HR_RE = /^(?:-{3,}|\*{3,})\s*$/
const BULLET_RE = /^[*-]\s+(.*)$/

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = []
  let open: Block | null = null

  const flush = () => {
    if (open) blocks.push(open)
    open = null
  }

  for (const rawLine of text.split('\n')) {
    const line = rawLine.trim()

    if (line === '') {
      flush()
      continue
    }

    const headingMatch = HEADING_RE.exec(line)
    if (headingMatch) {
      flush()
      blocks.push({ kind: 'heading', level: headingMatch[1].length, text: headingMatch[2] })
      continue
    }

    if (HR_RE.test(line)) {
      flush()
      blocks.push({ kind: 'hr' })
      continue
    }

    const bulletMatch = BULLET_RE.exec(line)
    if (bulletMatch) {
      if (open?.kind === 'list') {
        open.items.push(bulletMatch[1])
      } else {
        flush()
        open = { kind: 'list', items: [bulletMatch[1]] }
      }
      continue
    }

    if (open?.kind === 'paragraph') {
      open.lines.push(line)
    } else {
      flush()
      open = { kind: 'paragraph', lines: [line] }
    }
  }
  flush()

  return blocks
}

const BOLD_RE = /\*\*(.+?)\*\*/g

/** Splits `text` on **bold** markers and returns a React-renderable
 * sequence of plain strings and <strong> elements. Never touches
 * anything other than this one inline marker. */
function renderInline(text: string): ReactNode {
  const parts: ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  let key = 0

  BOLD_RE.lastIndex = 0
  while ((match = BOLD_RE.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index))
    parts.push(createElement('strong', { key: key++ }, match[1]))
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex))

  return parts.length === 1 ? parts[0] : createElement(Fragment, null, ...parts)
}

/** Independent review follow-up: strips the same Markdown subset
 * renderMarkdown() understands down to plain, readable text, joining
 * lines with a single space — for contexts that show an already-
 * truncated preview of an answer (e.g. AttemptHistorySection's
 * collapsed-row preview) where full block rendering doesn't apply (a
 * preview can be cut off mid-heading/mid-list), but the raw syntax
 * characters must not leak through either. Horizontal-rule lines are
 * dropped entirely (there is nothing readable to preview from a bare
 * "---"); heading/bullet markers are removed, keeping their text;
 * **bold** markers are removed, keeping the enclosed text. */
export function stripMarkdownToPlainText(text: string): string {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line !== '' && !HR_RE.test(line))
    .map((line) => line.replace(HEADING_RE, '$2').replace(BULLET_RE, '$1'))
    .join(' ')
    .replace(/\*\*(.+?)\*\*/g, '$1')
}

/** Renders `text` (a raw investigation answer, possibly containing
 * Markdown syntax) as a sequence of real React block elements — never a
 * raw HTML string. `text` may be empty; returns an empty fragment. */
export function renderMarkdown(text: string): ReactNode {
  const blocks = parseBlocks(text)

  return createElement(
    Fragment,
    null,
    ...blocks.map((block, index) => {
      switch (block.kind) {
        case 'heading': {
          const tag = `h${Math.min(block.level, 6)}`
          return createElement(tag, { key: index }, renderInline(block.text))
        }
        case 'hr':
          return createElement('hr', { key: index })
        case 'list':
          return createElement(
            'ul',
            { key: index },
            block.items.map((item, itemIndex) => createElement('li', { key: itemIndex }, renderInline(item))),
          )
        case 'paragraph':
          return createElement('p', { key: index }, renderInline(block.lines.join(' ')))
      }
    }),
  )
}

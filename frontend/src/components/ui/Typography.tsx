import type { ReactNode } from 'react'
import { renderMarkdown } from '../../lib/markdown'
import styles from './Typography.module.css'

export function PageTitle({ children }: { children: ReactNode }) {
  return <h1 className={styles.pageTitle}>{children}</h1>
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <div className={styles.sectionLabel}>{children}</div>
}

export function Muted({ children }: { children: ReactNode }) {
  return <span className={styles.muted}>{children}</span>
}

/** Serif reading content — for document/finding text, per the design direction. */
export function Prose({ children }: { children: ReactNode }) {
  return <div className={`prose ${styles.prose}`}>{children}</div>
}

/** Pre-commit review fix: an investigation's `answer` is model-generated
 * and may contain Markdown syntax (headings, **bold**, bullet lists,
 * horizontal rules) that Gemini produced on its own — previously shown
 * as literal `###`/`**`/`---` text. Renders that recognized subset as
 * real elements via lib/markdown.ts's renderMarkdown() (never raw HTML,
 * never dangerouslySetInnerHTML — see that module's own docstring for
 * why this is safe), while everything else about Prose's own styling is
 * unchanged. A SEPARATE component from Prose, not a new prop on it: every
 * other Prose consumer (chunk_text, event excerpts, contract clause text,
 * email/WhatsApp message bodies) renders raw extracted document text,
 * never model-generated prose, and must keep displaying it exactly as
 * before -- unaffected by this component's existence. */
export function AnswerProse({ children }: { children: string }) {
  return <div className={`prose ${styles.prose} ${styles.answerProse}`}>{renderMarkdown(children)}</div>
}

/** Explicit "not returned by the backend" marker — never render 0/blank
 * when data is simply unavailable, use this instead. */
export function NotAvailable({ reason }: { reason: string }) {
  return <span className={styles.notAvailable} title={reason}>Not available</span>
}

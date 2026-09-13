import type { ReactNode } from 'react'
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

/** Explicit "not returned by the backend" marker — never render 0/blank
 * when data is simply unavailable, use this instead. */
export function NotAvailable({ reason }: { reason: string }) {
  return <span className={styles.notAvailable} title={reason}>Not available</span>
}

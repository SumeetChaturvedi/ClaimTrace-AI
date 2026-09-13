import type { ReactNode } from 'react'
import styles from './StatBlock.module.css'

interface StatBlockProps {
  label: string
  value: ReactNode
  hint?: string
}

/** A labeled metric used in the Investigation Workspace header strip. Pass
 * <NotAvailable /> as value when the backend doesn't return the underlying
 * data — never pass 0 or '—' to imply a real, checked value of zero. */
export function StatBlock({ label, value, hint }: StatBlockProps) {
  return (
    <div className={styles.stat} title={hint}>
      <div className={styles.value}>{value}</div>
      <div className={styles.label}>{label}</div>
    </div>
  )
}

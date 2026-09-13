import type { ReactNode } from 'react'
import styles from './Panel.module.css'

interface PanelProps {
  children: ReactNode
  className?: string
}

/** Generic bordered surface — the one "card" primitive in the app. */
export function Panel({ children, className }: PanelProps) {
  return <div className={`${styles.panel} ${className ?? ''}`}>{children}</div>
}

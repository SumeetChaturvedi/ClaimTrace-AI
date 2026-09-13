import type { ReactNode } from 'react'
import styles from './Badge.module.css'

export type BadgeTone = 'neutral' | 'amber' | 'red' | 'green'

interface BadgeProps {
  tone?: BadgeTone
  children: ReactNode
}

/** Status/label primitive. Amber = caution / insufficient evidence, red =
 * genuine conflict, green = positive/system state, neutral = everything else. */
export function Badge({ tone = 'neutral', children }: BadgeProps) {
  return <span className={`${styles.badge} ${styles[tone]}`}>{children}</span>
}

import { SectionLabel } from '../../components/ui/Typography'
import styles from './panels.module.css'

/** Boundary marker for sections not yet available in the investigation
 * workspace (Timeline, Contract). Establishes where the real panel will
 * attach later, without pretending there's data to show now. */
export function PlaceholderPanel({ title, reason }: { title: string; reason: string }) {
  return (
    <div className={styles.placeholder}>
      <SectionLabel>{title}</SectionLabel>
      <p className={styles.placeholderBody}>{reason}</p>
    </div>
  )
}

import { WORKSPACE_TABS, type WorkspaceTab } from './types'
import styles from './WorkspaceNav.module.css'

export function WorkspaceNav({ active, onChange }: { active: WorkspaceTab; onChange: (tab: WorkspaceTab) => void }) {
  return (
    <nav className={styles.nav} aria-label="Investigation sections">
      {WORKSPACE_TABS.map((tab, i) => (
        <button
          key={tab.id}
          className={tab.id === active ? styles.activeItem : styles.item}
          onClick={() => onChange(tab.id)}
        >
          <span className={styles.itemOrdinal}>{String(i + 1).padStart(2, '0')}</span>
          <span className={styles.itemLabel}>{tab.label}</span>
        </button>
      ))}
    </nav>
  )
}

import { WORKSPACE_TABS, type WorkspaceTab } from './types'
import styles from './WorkspaceNav.module.css'

export function WorkspaceNav({ active, onChange }: { active: WorkspaceTab; onChange: (tab: WorkspaceTab) => void }) {
  return (
    <nav className={styles.nav} aria-label="Investigation sections">
      {WORKSPACE_TABS.map((tab) => (
        <button
          key={tab.id}
          className={tab.id === active ? styles.activeItem : styles.item}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  )
}

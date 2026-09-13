import type { ReactNode } from 'react'
import { NavRail } from './NavRail'
import { Breadcrumb, type BreadcrumbItem } from './Breadcrumb'
import { Inspector } from './Inspector'
import styles from './AppShell.module.css'

interface AppShellProps {
  breadcrumb: BreadcrumbItem[]
  children: ReactNode
  /** Widens the content container for pages that need more horizontal
   * room to be useful — the Investigation Workspace (Evidence/Documents
   * panels), the Source document reader, and the Projects register.
   * Everything else (Project, Investigations — mostly single-column forms
   * and short lists) keeps the narrower default, where extra width would
   * just create dead space rather than serve the content. */
  wide?: boolean
}

/** The one application shell every non-Home screen renders inside: left
 * nav rail, top breadcrumb, main content, and the (conditionally
 * rendered) right Inspector. Home uses its own full-bleed layout instead —
 * see HomePage.tsx — since it is the product's cinematic entry point, not
 * a workspace screen. */
export function AppShell({ breadcrumb, children, wide }: AppShellProps) {
  return (
    <div className={styles.shell}>
      <NavRail />
      <div className={styles.mainColumn}>
        <Breadcrumb items={breadcrumb} />
        <div className={styles.contentRow}>
          <main className={styles.content}>
            <div className={wide ? styles.contentInnerWide : styles.contentInner}>{children}</div>
          </main>
          <Inspector />
        </div>
      </div>
    </div>
  )
}

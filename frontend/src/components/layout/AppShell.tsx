import type { ReactNode } from 'react'
import { NavRail, type NavRailProjectContext } from './NavRail'
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
  /** Opts into NavRail's richer "current project" rail (Project Overview
   * redesign). Omitted by every other page, which keeps NavRail's default
   * light appearance exactly as before this addition. */
  navProject?: NavRailProjectContext
  /** Investigation Workspace redesign: drops the content column's max-width
   * cap entirely so it fills exactly whatever space `.content` has after
   * the nav rail and (when open) the Inspector — the workspace's own
   * internal layout is then responsible for using that space well. Takes
   * precedence over `wide` when both are set. Every other `wide` page
   * (Projects, Project, Source Viewer) is unaffected since none passes
   * this prop. */
  fluid?: boolean
}

/** The one application shell every non-Home screen renders inside: left
 * nav rail, top breadcrumb, main content, and the (conditionally
 * rendered) right Inspector. Home uses its own full-bleed layout instead —
 * see HomePage.tsx — since it is the product's cinematic entry point, not
 * a workspace screen. */
export function AppShell({ breadcrumb, children, wide, navProject, fluid }: AppShellProps) {
  const innerClassName = fluid ? styles.contentInnerFull : wide ? styles.contentInnerWide : styles.contentInner
  return (
    <div className={styles.shell}>
      <NavRail project={navProject} />
      <div className={styles.mainColumn}>
        <Breadcrumb items={breadcrumb} />
        <div className={styles.contentRow}>
          <main className={styles.content}>
            <div className={innerClassName}>{children}</div>
          </main>
          <Inspector />
        </div>
      </div>
    </div>
  )
}

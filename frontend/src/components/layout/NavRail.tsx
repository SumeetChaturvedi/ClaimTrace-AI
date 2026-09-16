import { NavLink } from 'react-router-dom'
import styles from './NavRail.module.css'

export interface NavRailProjectContext {
  /** The project's real database id — also used, honestly, as the small
   * ordinal shown next to the project name (see ProjectPage's ghosted
   * numeral for the same convention). Never a fabricated index. */
  id: number
  name: string
  /** Real counts already fetched by the calling page (GET
   * /projects/{id}/investigations and GET /projects/{id}/documents).
   * Omitted (not zeroed) while still loading, so the rail never claims
   * "0" when the real count simply hasn't arrived yet. */
  investigationCount?: number
  documentCount?: number
  active: 'overview' | 'investigations'
}

/**
 * The app's one persistent navigation rail. Its default appearance
 * (Home/Projects, plain light surface) is unchanged and used by every
 * page except Project Overview.
 *
 * Passing `project` opts a page into the richer "current project" rail —
 * the Project Overview redesign's own scoped addition. No other page
 * passes it, so their rendering is byte-for-byte identical to before this
 * change; only the visual *skin* (dark charcoal vs. light surface) is a
 * shared, unavoidable consequence of this being one shared component, not
 * a redesign of any other page's content.
 */
export function NavRail({ project }: { project?: NavRailProjectContext }) {
  if (!project) {
    return (
      <nav className={styles.rail} aria-label="Primary">
        <div className={styles.brand}>ClaimTrace</div>
        <NavLink to="/" end className={({ isActive }) => (isActive ? styles.activeLink : styles.link)}>
          Home
        </NavLink>
        <NavLink to="/projects" className={({ isActive }) => (isActive ? styles.activeLink : styles.link)}>
          Projects
        </NavLink>
      </nav>
    )
  }

  const { id, name, investigationCount, documentCount, active } = project
  const ref = String(id).padStart(2, '0')

  return (
    <nav className={`${styles.rail} ${styles.railProject}`} aria-label="Primary">
      <RailArt />

      <div className={styles.railContent}>
        <div className={styles.brand}>ClaimTrace</div>
        <NavLink to="/" end className={({ isActive }) => (isActive ? styles.activeLinkDark : styles.linkDark)}>
          Home
        </NavLink>
        <NavLink to="/projects" className={({ isActive }) => (isActive ? styles.activeLinkDark : styles.linkDark)}>
          Projects
        </NavLink>

        <div className={styles.railDivider} />

        <div className={styles.projectBlock}>
          <span className={styles.projectLabel}>Current Project</span>
          <span className={styles.projectRef}>{ref}</span>
          <span className={styles.projectName}>{name}</span>

          <div className={styles.projectNav}>
            <span className={active === 'overview' ? styles.projectSubActive : styles.projectSub}>Overview</span>
            <NavLink
              to={`/projects/${id}/investigations`}
              className={active === 'investigations' ? styles.projectSubActive : styles.projectSub}
            >
              Investigations
            </NavLink>
          </div>
        </div>

        <div className={styles.railDivider} />

        <div className={styles.railStats}>
          {investigationCount !== undefined && (
            <span className={styles.railStat}>
              {investigationCount} investigation{investigationCount === 1 ? '' : 's'}
            </span>
          )}
          {documentCount !== undefined && (
            <span className={styles.railStat}>
              {documentCount} document{documentCount === 1 ? '' : 's'}
            </span>
          )}
        </div>

        {/* A purely decorative editorial motto — never a data value, so it
           is styled distinctly from the real counts above rather than
           implying it measures anything. */}
        <p className={styles.railMotto} aria-hidden="true">
          Evidence · Record · Clarity
        </p>
      </div>
    </nav>
  )
}

/** Extremely low-opacity architectural linework behind the dark rail's
 * navigation — a simplified bridge elevation (deck, piers, diagonal
 * bracing), printed underneath the UI the way a technical field notebook
 * carries a faint grid. Static (no animation — the rail should never
 * distract from navigation), aria-hidden, and cropped by the rail's own
 * `overflow: hidden` so it can extend beyond the visible column without
 * needing responsive recalculation. */
function RailArt() {
  return (
    <svg
      className={styles.railArt}
      viewBox="0 0 220 820"
      preserveAspectRatio="xMidYMin slice"
      aria-hidden="true"
    >
      <g stroke="currentColor" strokeWidth="1" fill="none">
        <line x1="-40" y1="260" x2="280" y2="260" />
        <line x1="-40" y1="272" x2="280" y2="272" />
        <path d="M -40 272 L 0 236 L 40 272 L 80 236 L 120 272 L 160 236 L 200 272 L 240 236 L 280 272" />
        <line x1="40" y1="272" x2="40" y2="600" strokeWidth="3" />
        <line x1="160" y1="272" x2="160" y2="600" strokeWidth="3" />
      </g>
      <g stroke="currentColor" strokeWidth="0.75" fill="none" opacity="0.7">
        <line x1="0" y1="60" x2="220" y2="60" />
        <line x1="0" y1="740" x2="220" y2="740" />
      </g>
    </svg>
  )
}

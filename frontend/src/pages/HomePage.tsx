import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '../components/ui/Badge'
import { useApiQuery } from '../api/useApi'
import { getHealth, listProjects } from '../api/client'
import styles from './HomePage.module.css'

const FLOW_STAGES = [
  { label: 'Question', body: 'A claims professional asks a specific question about the project record.' },
  { label: 'Investigation', body: 'ClaimTrace searches the project record for evidence bearing on that question.' },
  { label: 'Finding', body: 'A grounded answer, written in full, with its qualifications intact.' },
  { label: 'Evidence', body: 'Every excerpt behind the finding, traceable to its document and page.' },
  { label: 'Source', body: 'The original document itself, opened at the page the evidence came from.' },
]

/**
 * Home is ClaimTrace's product entry point, not a workspace screen — it
 * deliberately bypasses AppShell (no nav rail, no breadcrumb) for a
 * full-bleed, cinematic composition, per the product redesign direction.
 * Every other route keeps the standard AppShell.
 */
export function HomePage() {
  const health = useApiQuery(getHealth, [])
  const projects = useApiQuery(listProjects, [])
  const heroArtRef = useRef<HTMLDivElement>(null)

  // Subtle scroll-linked parallax on the hero art: the backdrop drifts and
  // fades slightly slower than the page scrolls, so leaving the hero feels
  // like one continuous motion into "The Record" rather than a hard cut.
  // Reads scrollY and writes a transform/opacity directly via the ref
  // (no state, no re-render per scroll tick) and does nothing at all under
  // prefers-reduced-motion, where the hero simply stays static.
  useEffect(() => {
    const el = heroArtRef.current
    if (!el) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    let ticking = false
    const update = () => {
      ticking = false
      const y = window.scrollY
      const fade = Math.max(0, 1 - y / 700)
      el.style.transform = `translateY(${y * 0.25}px) scale(${1 + Math.min(y, 700) * 0.00015})`
      el.style.opacity = String(fade)
    }
    const onScroll = () => {
      if (ticking) return
      ticking = true
      requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className={styles.page}>
      <header className={styles.topbar}>
        <span className={styles.wordmark}>ClaimTrace</span>
        <Link to="/projects" className={styles.topbarLink}>
          Projects
        </Link>
      </header>

      <section className={styles.hero}>
        <HeroArt artRef={heroArtRef} />
        <div className={styles.heroContent}>
          <p className={styles.kicker}>ClaimTrace</p>
          <h1 className={styles.heroHeadline}>
            Investigate the record.
            <br />
            Trace the claim.
          </h1>
          <p className={styles.heroSub}>Evidence-grounded investigation for construction claims.</p>
          <div className={styles.heroActions}>
            <Link to="/projects" className={styles.primaryAction}>
              Open a Project
            </Link>
            <a href="#how-it-works" className={styles.secondaryAction}>
              How investigation works
            </a>
          </div>
        </div>
      </section>

      <section className={styles.recordSection}>
        <div className={styles.sectionInner}>
          <p className={styles.sectionKicker}>The Record</p>
          <h2 className={styles.sectionHeading}>Every document, in one investigation.</h2>
          <p className={styles.sectionBody}>
            Project documents, correspondence, schedules, and contractual records, brought
            together so a claim can be investigated against the record itself, not against
            memory. ClaimTrace assists that investigation. It does not adjudicate disputes or
            issue a legal or contractual determination.
          </p>
        </div>
      </section>

      <section id="how-it-works" className={styles.flowSection}>
        <div className={styles.sectionInner}>
          <p className={styles.sectionKicker}>How Investigation Works</p>
          <h2 className={styles.sectionHeading}>From question to source, every step traceable.</h2>
          <ol className={styles.flowList}>
            {FLOW_STAGES.map((stage, i) => (
              <li key={stage.label} className={styles.flowStep}>
                <div className={styles.flowStepNumber}>{String(i + 1).padStart(2, '0')}</div>
                <div>
                  <h3 className={styles.flowStepLabel}>{stage.label}</h3>
                  <p className={styles.flowStepBody}>{stage.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className={styles.ctaSection}>
        <div className={styles.sectionInner}>
          <p className={styles.sectionKicker}>Get Started</p>
          <h2 className={styles.sectionHeadingLight}>Choose a project to begin.</h2>
          {projects.status === 'success' && (
            <ul className={styles.projectQuickList}>
              {projects.data.map((project) => (
                <li key={project.id}>
                  <Link to={`/projects/${project.id}`} className={styles.projectQuickLink}>
                    <span>{project.name}</span>
                    <span className={styles.projectQuickArrow}>→</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Link to="/projects" className={styles.primaryActionLight}>
            Open Projects
          </Link>
        </div>
      </section>

      <footer className={styles.footer}>
        <span className={styles.wordmarkSmall}>ClaimTrace</span>
        <div className={styles.footerStatus}>
          <span>System status</span>
          {health.status === 'loading' && <Badge tone="neutral">Checking…</Badge>}
          {health.status === 'success' && <Badge tone="green">Connected</Badge>}
          {health.status === 'error' && <Badge tone="red">Unavailable</Badge>}
        </div>
      </footer>
    </div>
  )
}

/** Purely decorative brand backdrop for the hero: a blueprint-style grid
 * plus a simple crane/skyline silhouette, drawn as inline SVG so the hero
 * needs no external image asset (no licensing, no network dependency, no
 * new package, and no risk of a slow/broken external video load). A dark
 * gradient overlay sits on top for the "cinematic dark overlay" effect the
 * design direction calls for.
 *
 * Motion (the "cinematic" requirement, in place of an actual video):
 * the crane's jib carries a slow, continuous CSS drift (craneSway,
 * ~26s) and the whole art layer has a very slow ambient breathing scale
 * (heroBreathe, ~40s) — both subtle enough that the typography stays the
 * clear focus. `artRef` is written to directly (see HomePage's scroll
 * effect) for the scroll-linked parallax/fade, kept separate from the CSS
 * animations so the two don't fight over the `transform` property; the JS
 * effect already no-ops under prefers-reduced-motion, and the CSS
 * animations are disabled by the same media query below — a fully static
 * hero is the graceful fallback in both cases. */
function HeroArt({ artRef }: { artRef: React.RefObject<HTMLDivElement | null> }) {
  return (
    <div ref={artRef} className={styles.heroArt} aria-hidden="true">
      <svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMax slice" className={styles.heroSvg}>
        <defs>
          <pattern id="blueprint-grid" width="64" height="64" patternUnits="userSpaceOnUse">
            <path d="M 64 0 L 0 0 0 64" fill="none" stroke="#3a3427" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="1600" height="900" fill="url(#blueprint-grid)" opacity="0.35" />

        {/* Skyline */}
        <g fill="#241f17">
          <rect x="60" y="560" width="140" height="340" />
          <rect x="220" y="460" width="110" height="440" />
          <rect x="1180" y="500" width="130" height="400" />
          <rect x="1330" y="600" width="150" height="300" />
        </g>

        {/* Crane */}
        <g stroke="#4a4232" strokeWidth="6" fill="none" strokeLinecap="round">
          <line x1="700" y1="900" x2="700" y2="220" />
          <g className={styles.craneJib}>
            <line x1="700" y1="240" x2="1040" y2="240" />
            <line x1="700" y1="240" x2="560" y2="270" />
            <line x1="700" y1="220" x2="1000" y2="300" />
            <line x1="700" y1="220" x2="600" y2="300" />
            <line x1="960" y1="240" x2="960" y2="420" />
          </g>
        </g>
      </svg>
      <div className={styles.heroOverlay} />
    </div>
  )
}

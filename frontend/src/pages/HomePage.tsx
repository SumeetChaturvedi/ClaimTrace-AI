import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '../components/ui/Badge'
import { useApiQuery } from '../api/useApi'
import { getHealth, listProjects } from '../api/client'
import { useRevealRefs } from '../lib/useRevealOnScroll'
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
  const revealRef = useRevealRefs<HTMLDivElement>(3, styles.revealVisible)

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
        <div className={`${styles.sectionInner} ${styles.reveal}`} ref={revealRef(0)}>
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
        <div className={`${styles.sectionInner} ${styles.reveal}`} ref={revealRef(1)}>
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
        <div className={`${styles.sectionInner} ${styles.reveal}`} ref={revealRef(2)}>
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

/** Cinematic hero backdrop (Homepage Cinematic Video Pass): a real,
 * locally-hosted construction video — an aerial drone shot of a concrete
 * rail viaduct under construction, spanning a misty valley at sunrise,
 * mountains behind it — replacing the previous inline-SVG illustration.
 * See frontend/public/videos/home-hero.mp4 (Mixkit Stock Video Free
 * License — free for commercial use, no attribution required; source:
 * mixkit.co/free-stock-video/train-bridge-under-construction-2088) and
 * frontend/public/images/home-hero-poster.jpg, a frame extracted directly
 * from that same video so there is no visual jump between poster and
 * first frame. A dark gradient overlay sits on top for text readability
 * (see .heroOverlay) — the same treatment the previous SVG hero used.
 *
 * This is atmosphere and product identity, not evidence: it doesn't depict
 * any of ClaimTrace's actual projects.
 *
 * Final fallback: if even the poster image fails, the empty-alt <img>
 * renders nothing and the dark .hero section background (already the same
 * ink tone the old SVG was drawn on) shows through it — no broken-image
 * icon, no extra code needed for that last-resort case.
 *
 * Reduced motion / fallback: under prefers-reduced-motion, or if the video
 * element itself errors, this renders the poster image as a plain <img>
 * instead of an autoplaying <video> — no moving media is ever forced on a
 * user who has asked not to see it, and a failed video load never shows a
 * broken-media icon. `artRef` is written to directly (see HomePage's
 * scroll effect) for the existing scroll-linked parallax/fade, unchanged
 * from before and applied identically to whichever media element is
 * actually rendered inside it.
 *
 * No additional motion is layered on top of the video itself (no scale
 * drift, no pan) — the footage's own slow, natural movement is the entire
 * "cinematic" effect, per the explicit "one cinematic video is enough"
 * direction. */
function HeroArt({ artRef }: { artRef: React.RefObject<HTMLDivElement | null> }) {
  const [prefersReducedMotion] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )
  const [videoFailed, setVideoFailed] = useState(false)
  const showVideo = !prefersReducedMotion && !videoFailed

  return (
    <div ref={artRef} className={styles.heroArt} aria-hidden="true">
      {showVideo ? (
        <video
          className={styles.heroMedia}
          autoPlay
          muted
          loop
          playsInline
          poster="/images/home-hero-poster.jpg"
          onError={() => setVideoFailed(true)}
        >
          <source src="/videos/home-hero.mp4" type="video/mp4" />
        </video>
      ) : (
        <img src="/images/home-hero-poster.jpg" alt="" className={styles.heroMedia} />
      )}
      <div className={styles.heroOverlay} />
    </div>
  )
}

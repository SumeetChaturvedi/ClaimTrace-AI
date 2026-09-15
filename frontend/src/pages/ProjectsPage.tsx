import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { Muted, SectionLabel } from '../components/ui/Typography'
import { Button } from '../components/ui/Button'
import { ErrorState, LoadingState } from '../components/ui/StateViews'
import { ApiError, createProject, listProjects } from '../api/client'
import { useApiQuery } from '../api/useApi'
import styles from './ProjectsPage.module.css'

/**
 * The real project register (Phase 3: Project + Document Foundation),
 * given a proper entry-point composition in Phase 8A: an editorial heading,
 * a selective cinematic identity band (see ProjectsArt below — a real
 * photograph, correcting Phase 8A's original abstract-SVG treatment), then
 * the real project list.
 *
 * Every value shown on a project row is real: name and created_at both
 * come straight from GET /projects. Nothing here infers a project's status,
 * scale, or activity — the Project model has no such fields yet, and this
 * page must not invent them.
 */
export function ProjectsPage() {
  const navigate = useNavigate()
  const [refreshToken, setRefreshToken] = useState(0)
  const projects = useApiQuery(listProjects, [refreshToken])

  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  const handleCreate = async () => {
    const trimmed = name.trim()
    if (!trimmed || creating) return
    setCreating(true)
    setCreateError(null)
    try {
      const project = await createProject({ name: trimmed })
      navigate(`/projects/${project.id}`)
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : 'Something went wrong.')
      setCreating(false)
    }
  }

  return (
    <AppShell breadcrumb={[{ label: 'Home', to: '/' }, { label: 'Projects' }]} wide>
      <div className={styles.header}>
        <div>
          <p className={styles.kicker}>Projects</p>
          <h1 className={styles.headline}>
            Your claims work,
            <br />
            in one place.
          </h1>
          <Muted>Choose a project record to open, review, or investigate.</Muted>
        </div>
        <Button variant="primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancel' : 'Create Project'}
        </Button>
      </div>

      {showForm && (
        <form
          className={styles.createForm}
          onSubmit={(e) => {
            e.preventDefault()
            void handleCreate()
          }}
        >
          <SectionLabel>New Project</SectionLabel>
          <div className={styles.createRow}>
            <input
              className={styles.createInput}
              placeholder="Project name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={creating}
              autoFocus
            />
            <Button type="submit" variant="primary" disabled={!name.trim() || creating}>
              {creating ? 'Creating…' : 'Create Project'}
            </Button>
          </div>
          <p className={styles.createHint}>
            This project will become a project record containing documents and investigations.
          </p>
          {createError && <p className={styles.createError}>{createError}</p>}
        </form>
      )}

      <ProjectsArt />

      {projects.status === 'loading' && <LoadingState label="Loading projects…" />}
      {projects.status === 'error' && (
        <ErrorState
          message={`Could not load projects: ${projects.error}`}
          onRetry={() => setRefreshToken((t) => t + 1)}
        />
      )}

      {projects.status === 'success' && (
        <ul className={styles.register}>
          {projects.data.map((project, i) => (
            <li key={project.id}>
              <Link to={`/projects/${project.id}`} className={styles.row}>
                <span className={styles.rowIndex}>{String(i + 1).padStart(2, '0')}</span>
                <div className={styles.rowMain}>
                  <h2 className={styles.rowName}>{project.name}</h2>
                  <span className={styles.rowMeta}>Created {formatDate(project.created_at)}</span>
                </div>
                <span className={styles.rowAction}>
                  Open project <span className={styles.rowArrow}>→</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  )
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return iso
  }
}

/** Selective cinematic identity band (Phase 8A correction pass).
 *
 * The original Phase 8A treatment here was an abstract inline-SVG
 * "flyover" illustration — reviewed and rejected as not matching the
 * intended direction (cinematic + architectural + construction-specific,
 * not decorative illustration). This replaces it with a real photograph: a
 * bridge arch under construction (structural steel falsework, dusk-grey
 * sky, no people, no legible text/branding, no graffiti) — licensed for
 * free commercial/non-commercial use under the standard Unsplash License
 * (photographer: Sergey Omelchenko, Kraków, Poland), downloaded once into
 * this project's own /public/images/ (see index.html's asset convention —
 * favicon.svg lives there too) rather than hotlinked, so this never depends
 * on a third-party URL staying alive.
 *
 * Purely atmospheric: establishes ClaimTrace's construction-industry
 * identity and a sense of scale, and asserts no fact about any specific
 * project — this is not evidence, not a project photo, just mood, exactly
 * like Home's own hero art. If the file is ever missing, onError swaps in
 * a plain dark surface (the same ink-toned background used elsewhere in
 * the app) so the page still reads as intentional, never broken.
 *
 * Motion is a single, very slow, subtle scale drift (~48s, ~3%) — the
 * smallest treatment that gives the image a sense of life without reading
 * as "animated for its own sake"; disabled entirely under
 * prefers-reduced-motion via the .artImage rule in ProjectsPage.module.css. */
function ProjectsArt() {
  const [failed, setFailed] = useState(false)

  return (
    <div className={styles.art} aria-hidden="true">
      {!failed && (
        <img
          src="/images/projects-hero.jpg"
          alt=""
          className={styles.artImage}
          onError={() => setFailed(true)}
        />
      )}
      <div className={styles.artOverlay} />
    </div>
  )
}

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { PageTitle, Muted, SectionLabel } from '../components/ui/Typography'
import { Button } from '../components/ui/Button'
import { ErrorState, LoadingState } from '../components/ui/StateViews'
import { ApiError, createProject, listProjects } from '../api/client'
import { useApiQuery } from '../api/useApi'
import styles from './ProjectsPage.module.css'

/**
 * The real project register (Phase 3: Project + Document Foundation) —
 * replaces the pre-Phase-3 static PROJECT_DIRECTORY fixture with a live
 * GET /projects call, and adds real project creation via POST /projects.
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
          <PageTitle>Projects</PageTitle>
          <Muted>Choose a project to start or continue an investigation.</Muted>
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
              {creating ? 'Creating…' : 'Create'}
            </Button>
          </div>
          {createError && <p className={styles.createError}>{createError}</p>}
        </form>
      )}

      {projects.status === 'loading' && <LoadingState label="Loading projects…" />}
      {projects.status === 'error' && (
        <ErrorState
          message={`Could not load projects: ${projects.error}`}
          onRetry={() => setRefreshToken((t) => t + 1)}
        />
      )}

      {projects.status === 'success' && (
        <ul className={styles.register}>
          {projects.data.map((project) => (
            <li key={project.id}>
              <Link to={`/projects/${project.id}`} className={styles.row}>
                <h2 className={styles.rowName}>{project.name}</h2>
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

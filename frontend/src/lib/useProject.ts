import { useApiQuery, type ApiState } from '../api/useApi'
import { getProject } from '../api/client'
import type { Project } from '../api/types'

/**
 * Fetches one real project by id (Phase 3: Project + Document Foundation),
 * replacing the pre-Phase-3 static lib/projectDirectory.ts fixture every
 * page used to look up a project's display name. `projectId === null`
 * (an already-invalid route param) short-circuits to a rejected fetcher
 * without calling the backend — the caller renders its own "invalid
 * project id" state in that case regardless of what this returns.
 */
export function useProject(projectId: number | null): ApiState<Project> {
  return useApiQuery<Project>(
    () => (projectId === null ? Promise.reject(new Error('invalid project id')) : getProject(projectId)),
    [projectId],
  )
}

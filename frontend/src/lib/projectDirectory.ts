/**
 * Route-param validation for `:projectId`.
 *
 * Before Phase 3 (Project + Document Foundation), this file also held a
 * static, explicitly-not-live fixture standing in for a real project
 * register, since the backend had no GET /projects endpoint. That endpoint
 * now exists (backend/app/api/routes/projects.py) — see lib/useProject.ts
 * and api/client.ts's listProjects()/createProject()/getProject() — so the
 * fixture was removed rather than kept alongside real data. This file's
 * only remaining job is the id-format guard below, unrelated to where
 * project data comes from.
 */

/**
 * Validates a `:projectId` route param. Only a plain non-negative integer
 * (e.g. "1", "2", "42") is accepted — returns null for anything else,
 * including non-numeric text, "NaN", "Infinity", decimals, negative
 * numbers, or a missing param. Callers must treat null as "invalid
 * project id" and not proceed to render or call the backend.
 */
export function parseProjectId(raw: string | undefined): number | null {
  if (raw === undefined || !/^\d+$/.test(raw)) return null
  const parsed = Number(raw)
  return Number.isSafeInteger(parsed) ? parsed : null
}

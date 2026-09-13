const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/**
 * Validates a `:investigationId` route param — a backend-issued UUID
 * (see backend/app/db/models.py's InvestigationRecord). Returns the id
 * unchanged if it's syntactically a UUID, else null. Mirrors
 * lib/projectDirectory.ts's parseProjectId: reject obviously-invalid input
 * before ever calling the backend, rather than surfacing a raw 422.
 */
export function parseInvestigationId(raw: string | undefined): string | null {
  if (raw === undefined || !UUID_RE.test(raw)) return null
  return raw
}

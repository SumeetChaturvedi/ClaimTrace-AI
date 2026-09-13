/**
 * Centralized API access. Every backend call in the app goes through here —
 * no raw fetch() calls in components. Requests are made against /api/*,
 * which the Vite dev server proxies to the real backend (see
 * vite.config.ts) to avoid needing CORS support on the backend.
 */
import type {
  HealthResponse,
  InvestigationCreateRequest,
  InvestigationRecord,
  InvestigationRequest,
  InvestigationResponse,
  DocumentSummary,
  DocumentUploadResponse,
  Project,
  ProjectCreateRequest,
} from './types'

export class ApiError extends Error {
  status: number
  /** Set only when the backend's error detail carries a structured
   * {message, investigation_id} payload (app/api/routes/investigations.py's
   * InvestigationExecutionError) — i.e. an investigation was created and
   * persisted, but the engine run itself then failed. Lets a caller still
   * navigate to (and retry) that investigation instead of losing track of
   * it just because the HTTP call returned an error status. Undefined for
   * every other error (plain string `detail`, unreachable backend, etc). */
  investigationId?: string
  constructor(status: number, message: string, investigationId?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.investigationId = investigationId
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    throw new ApiError(0, 'Could not reach the backend. Is it running?')
  }

  if (!res.ok) {
    let detail = res.statusText
    let investigationId: string | undefined
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') {
        detail = body.detail
      } else if (body?.detail && typeof body.detail === 'object') {
        if (typeof body.detail.message === 'string') detail = body.detail.message
        if (typeof body.detail.investigation_id === 'string') investigationId = body.detail.investigation_id
      }
    } catch {
      // response body wasn't JSON — fall back to statusText
    }
    throw new ApiError(res.status, detail, investigationId)
  }

  return res.json() as Promise<T>
}

// GET /health
export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}

// GET /projects, POST /projects, GET /projects/{id} (Phase 3: Project +
// Document Foundation) — the real project register. Replaces the static,
// explicitly-not-live lib/projectDirectory.ts fixture that stood in for
// this before it existed.
export function listProjects(): Promise<Project[]> {
  return request<Project[]>('/projects')
}

export function createProject(payload: ProjectCreateRequest): Promise<Project> {
  return request<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getProject(projectId: number): Promise<Project> {
  return request<Project>(`/projects/${projectId}`)
}

// POST /investigate — the core product action.
export function runInvestigation(payload: InvestigationRequest): Promise<InvestigationResponse> {
  return request<InvestigationResponse>('/investigate', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

// POST /projects/{project_id}/investigations (Phase 2: Persistent
// Investigations) — creates a persistent investigation and runs the real
// investigation engine for it synchronously, returning the final
// completed (or failed) record. This is the only way the frontend starts
// a new investigation now; the flat POST /investigate above is left
// available but unused by the UI. A single real request per call — no
// StrictMode double-invoke risk, since this is only ever called from a
// user event handler (a click/submit), never a mount effect.
export function createInvestigation(projectId: number, payload: InvestigationCreateRequest): Promise<InvestigationRecord> {
  return request<InvestigationRecord>(`/projects/${projectId}/investigations`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

// GET /projects/{project_id}/investigations — every persisted investigation
// for this project, most recent first. Replaces the old sessionStorage-backed
// "recent in this session" list with the real, durable history.
export function listInvestigations(projectId: number): Promise<InvestigationRecord[]> {
  return request<InvestigationRecord[]>(`/projects/${projectId}/investigations`)
}

// GET /projects/{project_id}/investigations/{investigation_id} — fetches an
// already-persisted investigation. Reopening an investigation calls only
// this, never createInvestigation(): Gemini is never re-invoked just to
// view a result that already exists.
export function getInvestigation(projectId: number, investigationId: string): Promise<InvestigationRecord> {
  return request<InvestigationRecord>(`/projects/${projectId}/investigations/${investigationId}`)
}

// POST /projects/{project_id}/investigations/{investigation_id}/retry —
// re-runs the real investigation engine for an existing (typically failed)
// investigation, overwriting its result in place. The persisted equivalent
// of the pre-Phase-2 in-session Retry button.
export function retryInvestigation(projectId: number, investigationId: string): Promise<InvestigationRecord> {
  return request<InvestigationRecord>(`/projects/${projectId}/investigations/${investigationId}/retry`, {
    method: 'POST',
  })
}

// GET /documents — NOT project-scoped by the backend (no project_id filter
// or field exists). Exposed here for completeness, but the UI must not
// present its results as belonging to a specific project.
export function listAllDocuments(): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>('/documents')
}

// GET /projects/{project_id}/documents (Phase 3: Project + Document
// Foundation) — the real, project-scoped document register: every document
// belonging to this project, including ones still processing or that
// failed, so the register can show the true current state of each.
export function listProjectDocuments(projectId: number): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>(`/projects/${projectId}/documents`)
}

// GET /projects/{project_id}/documents/{document_id} (Phase 3) — one
// document's metadata, scoped to project_id exactly like
// listProjectDocuments; the backend 404s if the document doesn't exist or
// belongs to a different project. Used by DocumentSourceViewPage (Phase 3
// UX fix: Project Documents -> Document Viewer) to validate a document
// against the project id in its own URL — the same "never trust the
// caller, always re-validate via this page's own project id" pattern
// SourceViewPage already uses for citations.
export function getProjectDocument(projectId: number, documentId: number): Promise<DocumentSummary> {
  return request<DocumentSummary>(`/projects/${projectId}/documents/${documentId}`)
}

// POST /projects/{project_id}/documents — uploads one or more PDFs to this
// project through the real ingestion pipeline (extract, chunk, embed,
// index), synchronously: by the time this resolves, every accepted file
// has a terminal status ('ready' or 'failed'). Uses FormData, not JSON, so
// this bypasses request()'s JSON body/Content-Type handling and builds the
// request directly — the browser sets the correct multipart boundary
// header itself only when Content-Type is left unset.
export async function uploadProjectDocuments(projectId: number, files: File[]): Promise<DocumentUploadResponse> {
  const formData = new FormData()
  for (const file of files) formData.append('files', file)

  let res: Response
  try {
    res = await fetch(`/api/projects/${projectId}/documents`, { method: 'POST', body: formData })
  } catch {
    throw new ApiError(0, 'Could not reach the backend. Is it running?')
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      // response body wasn't JSON — fall back to statusText
    }
    throw new ApiError(res.status, detail)
  }

  return res.json() as Promise<DocumentUploadResponse>
}

// GET /projects/{project_id}/documents/{document_id}/file — serves the
// actual stored PDF, scoped to project_id (backend verifies
// document.project_id === project_id before returning anything). Not a
// JSON endpoint, so this isn't routed through request<T>(): it's a plain
// URL builder for direct browser use (an <iframe src>), still going
// through the same /api proxy prefix as every other call in this file —
// no second API configuration, no hardcoded backend origin.
export function getDocumentFileUrl(projectId: number, documentId: number): string {
  return `/api/projects/${projectId}/documents/${documentId}/file`
}

// Fetches the actual PDF bytes and returns a local blob URL for the
// browser's native PDF viewer to render. One real request serves as both
// the availability check and the render source — a HEAD-based check was
// tried first and confirmed (via a real request) to get a 405 from this
// endpoint (it's a GET-only route), so this deliberately does a real GET
// rather than assuming HEAD works. Returns null (never throws) for any
// failure — wrong project, missing file, backend down, non-PDF response —
// since "no PDF available" is an expected, honestly-handled UI state here,
// not an exceptional one. Callers must revoke the returned URL
// (URL.revokeObjectURL) once done with it.
export async function fetchDocumentFileBlobUrl(projectId: number, documentId: number): Promise<string | null> {
  try {
    const res = await fetch(getDocumentFileUrl(projectId, documentId))
    if (!res.ok) return null
    if (!(res.headers.get('content-type') ?? '').includes('application/pdf')) return null
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  } catch {
    return null
  }
}

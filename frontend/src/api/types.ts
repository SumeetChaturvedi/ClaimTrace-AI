/**
 * TypeScript mirrors of the backend's actual Pydantic response models.
 * Kept 1:1 with backend/app/agent/models.py and backend/app/api/routes/*.py
 * — do not add fields here that the backend does not actually return.
 */

// backend/app/api/routes/health.py
export interface ProjectSummary {
  id: number
  name: string
  created_at: string
}

// backend/app/api/routes/projects.py (Phase 3: Project + Document Foundation)
export interface Project {
  id: number
  name: string
  created_at: string
}

export interface ProjectCreateRequest {
  name: string
}

export interface HealthResponse {
  status: string
  app: string
  database: string
  project: ProjectSummary
}

// backend/app/api/routes/documents.py
export interface DocumentSummary {
  id: number
  filename: string
  doc_type: string | null
  doc_date: string | null
  referenced_ids: string[] | null
  // Phase 3: Project + Document Foundation — the document's real processing
  // lifecycle. 'uploaded'/'processing' are transient (this pipeline runs
  // synchronously within the upload request, so a document returned by
  // GET .../documents is realistically always 'ready' or 'failed' by the
  // time it's visible at all — these two states exist for correctness and
  // for the rare case of viewing a document mid-upload from another tab).
  status: 'uploaded' | 'processing' | 'ready' | 'failed'
  processing_error: string | null
  uploaded_at: string
  updated_at: string
  // NOTE: the backend's DocumentSummary does NOT include project_id.
  // GET /documents (unscoped) returns every document in the database; do
  // not assume a result there belongs to any particular project. The
  // project-scoped GET /projects/{project_id}/documents (Phase 3) returns
  // the identical shape, already filtered to one project.
}

// backend/app/api/routes/project_documents.py (Phase 3)
export interface RejectedUpload {
  filename: string
  error: string
}

export interface DocumentUploadResponse {
  documents: DocumentSummary[]
  rejected: RejectedUpload[]
}

// backend/app/agent/models.py
export interface Citation {
  document_id: number
  page: number | null
  chunk_id: number
  relevance_score: number
  chunk_text: string | null
}

export interface InvestigationRequest {
  project_id: number
  query: string
  top_k?: number
}

// Phase 4: Timeline Productization. Mirrors app.agent.models.TimelineEntry
// exactly — document_id/document_date/document_type/event_label are all
// deterministic (no LLM, no inference; see backend/app/investigation/timeline.py),
// and `citations` are this investigation's own real Citation objects for
// that document (never a new lookup, never fabricated). A document with no
// extracted date has document_date: null and sorts last, not first.
export interface TimelineEntry {
  document_id: number
  document_date: string | null
  document_type: string | null
  event_label: string
  citations: Citation[]
}

// Phase 5: Contract Intelligence Productization. Mirrors
// app.contracts.models.ContractClause exactly — clause_number/title/topic/text
// only. Deliberately has NO document_id, chunk_id, or page: the backend's
// contract-package loader never records which source file (or PDF page) a
// clause came from, so unlike Citation/TimelineEntry there is no source
// location to link to. Do not add one here — that would be fabricated.
export interface ContractClause {
  clause_number: string
  title: string
  topic: string
  text: string
}

export interface InvestigationResponse {
  answer: string
  citations: Citation[]
  reasoning_steps: string[]
  timeline: TimelineEntry[]
  contract_clauses: ContractClause[]
  // NOTE: this is the entire response shape. There is no separate field for
  // evidence gaps or conflicts — the backend does not return them. Any UI
  // section for those concepts must say so explicitly rather than deriving
  // fake values.
}

// backend/app/api/routes/investigations.py (Phase 2: Persistent Investigations)
export type InvestigationStatus = 'running' | 'completed' | 'failed'

export interface InvestigationCreateRequest {
  query: string
  top_k?: number
}

// The persisted investigation, project-scoped. answer/citations/reasoning_steps
// are the exact same fields InvestigationResponse already returns, flattened
// to top level here rather than nested, so existing panels that already
// consume those three fields need no reshaping.
export interface InvestigationRecord {
  id: string
  project_id: number
  query: string
  status: InvestigationStatus
  created_at: string
  updated_at: string
  answer: string | null
  citations: Citation[]
  reasoning_steps: string[]
  timeline: TimelineEntry[]
  contract_clauses: ContractClause[]
  error: string | null
}

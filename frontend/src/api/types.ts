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

// Phase 8B.2 (Backend Event Extractor). Mirrors app.agent.models.ExtractedEvent
// exactly — an LLM-extracted, source-verified event candidate, never
// automatically an established fact. event_type/assertion_type are each
// independently nullable: the backend sets them to null (never a fabricated
// value) when the evidence doesn't clearly support a category. event_date is
// null whenever event_date_basis is 'unknown' — the backend never guesses a
// missing or ambiguous date. document_id/chunk_id are the same stable
// (document, chunk) locator Citation already uses — never a thread id.
export type EventDateBasis = 'explicit' | 'inferred' | 'unknown'
export type AssertionType =
  | 'recorded_action'
  | 'request'
  | 'instruction'
  | 'commitment'
  | 'allegation'
  | 'interpretation_needed'

export interface ExtractedEvent {
  document_id: number
  chunk_id: number
  excerpt: string
  event_type: string | null
  assertion_type: AssertionType | null
  description: string
  event_date: string | null
  event_date_basis: EventDateBasis
  attributed_party: string | null
}

export interface InvestigationResponse {
  answer: string
  citations: Citation[]
  reasoning_steps: string[]
  timeline: TimelineEntry[]
  contract_clauses: ContractClause[]
  // Phase 8B.2: events=[] is NOT itself an error — it means extraction ran
  // and genuinely found none, OR there was no evidence to extract from, OR
  // (indistinguishably, over this API as it currently stands) this
  // investigation predates event extraction entirely. events_error is the
  // ONLY signal that extraction itself failed to run; events_truncated is
  // the only signal that a real, partial result may be missing further
  // events. Never treat an empty `events` array as proof extraction ran.
  events: ExtractedEvent[]
  events_error: string | null
  events_truncated: boolean
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
  events: ExtractedEvent[]
  events_error: string | null
  events_truncated: boolean
  error: string | null
}

// backend/app/api/routes/project_emails.py (Phase 8A: Email Thread
// Intelligence). An email message's body is an ordinary Document
// (doc_type: 'EMAIL') whose chunks are ordinary citations — these types
// are only for the richer email-specific metadata (sender/recipients/
// thread/attachments) fetched separately when actually opening a message,
// exactly how doc_type/doc_date are already resolved separately from
// Citation rather than embedded in it (see lib/documentFormat.ts).

export interface EmailImportResult {
  source_name: string
  status: 'imported' | 'duplicate' | 'rejected'
  document_id: number | null
  thread_id: number | null
  subject: string | null
  message_id: string | null
  error: string | null
}

export interface EmailImportResponse {
  results: EmailImportResult[]
}

export interface EmailThreadSummary {
  id: number
  subject: string | null
  message_count: number
  first_sent_at: string | null
  last_sent_at: string | null
}

export interface EmailMessageSummary {
  document_id: number
  message_id: string | null
  subject: string | null
  sender_name: string | null
  sender_email: string | null
  sent_at: string | null
  sent_at_timezone_unknown: boolean
  status: 'uploaded' | 'processing' | 'ready' | 'failed'
  attachment_count: number
}

export interface EmailThreadDetail {
  id: number
  subject: string | null
  messages: EmailMessageSummary[]
}

export interface EmailAttachmentSummary {
  id: number
  filename: string
  content_type: string | null
  size_bytes: number
  // 'processed' (a real PDF/DOCX document was created) | 'unsupported_format'
  // (format not indexed; bytes not stored) | 'rejected' (empty/oversized) |
  // 'failed' (accepted but extraction/indexing failed — document_id is
  // still set, a real 'failed' Document, never silently dropped)
  status: 'processed' | 'unsupported_format' | 'rejected' | 'failed'
  document_id: number | null
  processing_error: string | null
}

export interface EmailMessageDetail {
  document_id: number
  thread_id: number
  message_id: string | null
  in_reply_to: string | null
  references: string | null
  sender_name: string | null
  sender_email: string | null
  to_recipients: string[]
  cc_recipients: string[]
  subject: string | null
  sent_at: string | null
  sent_at_timezone_unknown: boolean
  status: 'uploaded' | 'processing' | 'ready' | 'failed'
  processing_error: string | null
  doc_date: string | null
  plain_body: string | null
  has_html_body: boolean
  attachments: EmailAttachmentSummary[]
}

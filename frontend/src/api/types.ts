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
  // Phase W2.3 (Multimodal Image Understanding): null for an ordinary
  // source document; distinguishes a Document derived from a preserved
  // image's locally-transcribed OCR text from one derived from an
  // AI-generated visual description -- explicit, never inferred from
  // filename or doc_type.
  derivation_kind: 'ocr_transcription' | 'visual_description' | null
}

// backend/app/api/routes/project_documents.py. Present only on a document
// that is itself a successfully-processed email attachment — the covering
// email it came from. Project-scoped only (not on the global
// DocumentSummary from backend/app/api/routes/documents.py, which has no
// project_id to scope the lookup by).
export interface EmailSourceInfo {
  message_document_id: number
  thread_id: number
  subject: string | null
  sender_name: string | null
  sender_email: string | null
  sent_at: string | null
}

// Mirrors EmailSourceInfo exactly, for a WhatsApp media attachment
// (Phase W1: WhatsApp Export Ingestion) -- present only on a document
// that is itself a successfully-processed WhatsApp attachment.
export interface WhatsAppSourceInfo {
  message_document_id: number
  chat_id: number
  sender_name: string | null
  sent_at: string | null
  sent_at_ambiguous: boolean
}

// backend/app/api/routes/project_documents.py (Phase W2.2: OCR Evidence
// Integration) -- present only on a document whose text was derived by
// locally running OCR against a preserved image, across all three image
// sources. Identifies the document's text as DERIVED, never the
// original itself, and names which existing file-serving route (see
// getProjectImageFileUrl/getEmailAttachmentFileUrl/
// getWhatsAppAttachmentFileUrl below) opens the real preserved bytes.
export interface ImageSourceInfo {
  source_kind: 'project_image' | 'email_attachment' | 'whatsapp_attachment'
  image_id: number
}

export interface ProjectDocumentSummary extends DocumentSummary {
  email_source: EmailSourceInfo | null
  whatsapp_source: WhatsAppSourceInfo | null
  image_source: ImageSourceInfo | null
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

// Phase W2.0 (Shared Image Preservation Foundation): a directly-uploaded
// image, preserved rather than run through PDF/DOCX ingestion. 'rejected'
// and 'failed' both carry id/uploaded_at as null, since no row was ever
// durably persisted in either case -- never a fabricated id for
// something that doesn't exist.
export interface ProjectImageAssetSummary {
  id: number | null
  filename: string
  content_type: string | null
  size_bytes: number
  status: 'stored_pending_processing' | 'processed' | 'rejected' | 'failed'
  document_id: number | null
  processing_error: string | null
  width_px: number | null
  height_px: number | null
  uploaded_at: string | null
}

export interface DocumentUploadResponse {
  documents: DocumentSummary[]
  rejected: RejectedUpload[]
  // Additive (Phase W2.0): a recognized image in the same upload batch.
  // Always present, defaults to [] server-side.
  images: ProjectImageAssetSummary[]
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
  // Phase 1 (Fix Existing Investigation Pipeline Gaps). True only when the
  // LLM provider's own response metadata reported `answer` was cut off by
  // its output-token budget — never inferred from the answer's length.
  answer_truncated: boolean
  // Plain-language note when the Investigation Loop's evidence-gathering
  // stopped for a reason other than finding sufficient evidence (e.g. a
  // referenced contract clause could not be retrieved) — null for a
  // cleanly completed investigation. Never the raw internal reason name.
  evidence_limitation: string | null
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
  answer_truncated: boolean
  evidence_limitation: string | null
  error: string | null
  // Phase 2a (Preserve Investigation Attempt History). 1-based attempt
  // number of the CURRENT/latest attempt this record represents. 1 for
  // every investigation that predates this field — correct, not a guess.
  // See GET .../attempts (InvestigationAttempt below) for the full
  // history when this is > 1.
  attempt_number: number
}

// backend/app/api/routes/investigations.py (Phase 2a: Preserve
// Investigation Attempt History). One entry in an investigation's attempt
// history — either a frozen, superseded snapshot or the current/latest
// attempt (is_current=true), represented accurately whatever its real
// status is ('running', 'failed', or 'completed') — never implied to have
// completed merely because it appears in this list. Omits id/project_id/
// query/created_at: those are investigation-identity-level, shared across
// every attempt of the same investigation (see InvestigationRecord above).
export interface InvestigationAttempt {
  attempt_number: number
  is_current: boolean
  status: InvestigationStatus
  attempted_at: string
  answer: string | null
  citations: Citation[]
  reasoning_steps: string[]
  timeline: TimelineEntry[]
  contract_clauses: ContractClause[]
  events: ExtractedEvent[]
  events_error: string | null
  events_truncated: boolean
  answer_truncated: boolean
  evidence_limitation: string | null
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
  // (format not indexed; bytes not stored) | 'rejected' (empty/oversized,
  // or — Phase W2.0 — a recognized-but-invalid/corrupt image) | 'failed'
  // (accepted but extraction/indexing failed — document_id is still set,
  // a real 'failed' Document, never silently dropped) |
  // 'stored_pending_processing' (Phase W2.0: a recognized image,
  // preserved as bytes, not yet OCR'd/described/indexed — never
  // presented as processed)
  status: 'processed' | 'unsupported_format' | 'rejected' | 'failed' | 'stored_pending_processing'
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

// backend/app/api/routes/project_whatsapp.py (Phase W1: WhatsApp Export
// Ingestion). Mirrors the Email types above exactly -- a WhatsApp message
// body is an ordinary Document (doc_type: 'WHATSAPP_MESSAGE') whose chunks
// are ordinary citations; these types are only for the richer
// WhatsApp-specific metadata (sender/timestamp/chat/attachments) fetched
// separately when actually opening a message.

export interface WhatsAppImportResult {
  chat_id: number
  chat_title: string | null
  imported: number
  duplicate: number
  attachments_processed: number
  attachments_pending: number
  attachments_unsupported: number
  attachments_rejected: number
  attachments_failed: number
  // Counted separately from attachments_rejected: more than one file in
  // the archive shared the basename a message referenced, so ClaimTrace
  // refused to guess which one was actually attached and used none of
  // them (see backend/app/whatsapp_ingestion/pipeline.py's
  // _resolve_media_candidate). Never implies a successful attach.
  attachments_ambiguous: number
  // Parsing warnings, including ambiguous/unparseable timestamps -- never
  // silently dropped; a successful import can still carry these.
  parse_warnings: string[]
}

export interface WhatsAppChatSummary {
  id: number
  title: string | null
  source_export_filename: string
  message_count: number
  first_sent_at: string | null
  last_sent_at: string | null
  imported_at: string
}

export interface WhatsAppMessageSummary {
  document_id: number
  sequence_index: number
  sender_name: string | null
  // Exactly as exported (e.g. "25/03/24, 10:00:00") -- always shown
  // alongside/sent_at instead of it, since sent_at can be null or
  // ambiguous.
  raw_timestamp_text: string
  sent_at: string | null
  sent_at_ambiguous: boolean
  message_type: 'text' | 'system' | 'deleted' | 'media'
  status: 'uploaded' | 'processing' | 'ready' | 'failed'
  attachment_count: number
}

export interface WhatsAppChatDetail {
  id: number
  title: string | null
  messages: WhatsAppMessageSummary[]
}

export interface WhatsAppMediaAttachmentSummary {
  id: number
  filename: string
  content_type: string | null
  size_bytes: number
  // 'processed' (a real PDF/DOCX Document was created) | 'stored_pending_
  // processing' (original bytes preserved, not yet interpreted -- never
  // shown as "understood") | 'unsupported_format' | 'rejected' | 'failed'
  status: 'processed' | 'stored_pending_processing' | 'unsupported_format' | 'rejected' | 'failed'
  document_id: number | null
  processing_error: string | null
}

export interface WhatsAppMessageDetail {
  document_id: number
  chat_id: number
  sequence_index: number
  sender_name: string | null
  raw_timestamp_text: string
  sent_at: string | null
  sent_at_ambiguous: boolean
  message_type: 'text' | 'system' | 'deleted' | 'media'
  status: 'uploaded' | 'processing' | 'ready' | 'failed'
  processing_error: string | null
  doc_date: string | null
  text: string | null
  attachments: WhatsAppMediaAttachmentSummary[]
}

// backend/app/api/routes/project_mailboxes.py (Phase 1: Gmail Integration).
// NEVER add a token/credential field here — the backend's own response
// models deliberately never return one; see that module's own docstring.
export type ConnectedMailboxStatus = 'connected' | 'needs_reauth' | 'disconnected'

export interface ConnectAuthorizationResponse {
  authorization_url: string
}

export interface ConnectedMailboxSummary {
  id: number
  provider: string
  external_email: string
  status: ConnectedMailboxStatus
  last_synced_at: string | null
  last_sync_error: string | null
  connected_at: string
}

export interface SyncResult {
  status: 'completed' | 'partial' | 'needs_reauth' | 'error'
  imported: number
  duplicate: number
  rejected: number
  skipped_not_found: number
  error: string | null
}

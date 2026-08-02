# ClaimTrace AI – Implementation Log

This file tracks the implementation progress of the project.

Architecture, design decisions, and milestones are documented in `PROJECT_PLAN.md`.

---

## Current Status

### ✅ Completed

- Project architecture finalized
- PROJECT_PLAN.md completed
- Fictional dataset prepared (all 18 documents, including previously-missing doc 07)
- Dataset converted to PDF
- Docker configured
- PostgreSQL + pgvector running
- FastAPI initialized
- Health endpoint working
- Claude Code setup complete
- Backend Foundation (Milestone 0) verified: config/settings, SQLAlchemy engine +
  session layer, ORM models matching schema.sql, DB init (extension + tables +
  storage dir), idempotent default-project seeding, FastAPI lifespan wired to it
- Document ingestion pipeline: PDF upload (multi-file), PyMuPDF text extraction,
  deterministic metadata extraction (doc_type/doc_date/referenced_ids via regex,
  no LLM call), Document rows created against the default project. Verified
  against all 17 real fictional-dataset PDFs: 17/17 doc_type + doc_date
  extracted, corrupted/non-PDF uploads rejected per-file without failing the
  batch.
- Document Intelligence Layer: deterministic word-window chunking (page-aware),
  local sentence-transformers embeddings (all-MiniLM-L6-v2, 384-dim, loaded
  once per process), pgvector persistence, wired automatically into the
  upload flow. Idempotent by construction (delete-then-insert per document in
  one transaction). Verified against all 17 documents: 100% embedded, correct
  page numbers, and a pgvector cosine-distance sanity check confirms the
  embeddings are semantically meaningful (SI-088 chain documents cluster
  together; the deliberately-irrelevant P-15 correspondence sits furthest).
- Semantic Retrieval: dedicated app/retrieval/service.py (search_chunks) plus
  a GET /search endpoint, ranking purely by pgvector cosine similarity.
  Verified against the P-42 ground-truth investigation question — top results
  were meeting minutes, both DPRs, and the approval letter, i.e. the correct
  evidence chain. Empty corpus and empty/whitespace queries handled
  gracefully.
- Sprint 1 (Investigation Engine foundation), Tasks 01–07.1 — app/agent/ and
  app/llm/ built up incrementally:
  - Scaffolding: InvestigationService, InvestigationRequest/Response,
    Citation, tool stubs (Task 01)
  - search_documents() wraps retrieval.search_chunks, transforms results to
    Citation, no retrieval internals leak out (Task 02)
  - read_document() reads a document's extracted text via the DB + storage
    layer, raises DocumentNotFoundError clearly (Task 03)
  - Evidence domain model — citation, excerpt, surrounding_context,
    confidence, metadata (Task 03.5)
  - InvestigationService builds an Evidence collection per citation
    (Task 04); Citation widened to carry the actual matched chunk_text so
    Evidence is built from the real retrieved passage, not a truncated full
    document (Task 04.1)
  - ReasoningEngine + ReasoningResult — deterministic confidence-ranking
    baseline, no AI yet; InvestigationService now purely orchestrates, all
    "what does this evidence mean" logic (including the no-evidence case)
    lives in ReasoningEngine (Task 05)
  - InvestigationPackage + InvestigationPackageBuilder — the single
    model-agnostic snapshot (question, evidence, totals, timestamp) that
    any future reasoning model consumes identically; ReasoningEngine now
    takes one package instead of two parameters (Task 06)
  - First real LLM integration: PromptBuilder + LLM-backed ReasoningEngine
    (Task 07), then refactored to a provider-independent app/llm/ layer
    (LLMProvider interface, Prompt object, GeminiProvider as the sole
    implementation) so ReasoningEngine never references a specific
    provider's SDK (Task 07.1)
  - Full end-to-end production-readiness audit (see below) — 18-stage
    pipeline re-verified from a clean slate, 5 realistic investigation
    questions run end-to-end, one real gap found and fixed (whitespace-only
    API key bypassed the "not configured" check), retrieval-quality and
    resource-usage limitations documented but deliberately not touched
    (out of scope for a verification pass)
- Sprint 1.5 Task 01 — live Gemini verification, no mocking. A real API key
  was configured; the default model (gemini-2.0-flash) turned out to have
  zero free-tier quota on this key (a real 429 RESOURCE_EXHAUSTED, not a
  code bug) — diagnosed via client.models.list() and empirical testing of
  candidate models, found gemini-flash-lite-latest has working quota, and
  updated the default in .env/.env.example/config.py accordingly. Ran two
  real investigations end-to-end (no stub provider) against the actual
  dataset; verified the LLM's answers are genuinely grounded in the supplied
  evidence (cited reference numbers/dates traced back to actual excerpt
  text, not fabricated) and that a known-noisy retrieved document (the
  irrelevant Pier P-15 correspondence) was correctly ignored in the
  generated answer even though it was present in the evidence set.
- Sprint 1.5 Task 02 — POST /investigate: a thin FastAPI wrapper over the
  existing InvestigationService, reusing InvestigationRequest/Response
  as-is (no new DTOs). No changes to InvestigationService, ReasoningEngine,
  PromptBuilder, or either LLM layer file. Verified with three real
  Gemini-backed investigations over real HTTP requests (not mocked), plus
  400/422/503 error-path tests. One important finding from this round of
  real testing: in one of the three real runs, the LLM's answer wove the
  deliberately-irrelevant Pier P-15 document into the P-42 delay-claim
  narrative as if it were related evidence — everything it said about that
  document was textually accurate (not fabricated), but conflating it with
  an unrelated investigation is exactly the failure mode the dataset's
  ground truth was designed to catch, and citation verification (still not
  implemented) would be needed to catch it. Not fixed — out of scope for
  this task (no AI-behavior changes permitted).
- Sprint 2 Task 01 — new app/investigation/ package: InvestigationPlan
  (goal, investigation_type, expected_answer_type, primary_entities,
  likely_evidence_sources, likely_contract_areas, investigation_steps) and
  InvestigationPlanner.create_plan(question), a fixed placeholder (no LLM,
  no classification) establishing the public contract for the future
  Investigation Planning subsystem. Deliberately zero coupling to
  agent/retrieval/db/api/llm — verified by inspecting sys.modules after
  import to confirm none of those packages get pulled in transitively.
  Existing pipeline unaffected: /health, /search, and a real Gemini-backed
  /investigate call all re-verified after the addition.
- Sprint 2 Task 02 — InvestigationPlanner.create_plan() now classifies
  investigation_type for real: new app/investigation/classifier.py,
  deterministic keyword matching (no LLM, no embeddings, no regex) across
  the 8 supported types (approval/delay/variation/entitlement/payment/
  evidence/compliance/unknown), checked in a fixed priority order.
  Everything else on InvestigationPlan stays the fixed placeholder from
  Task 01. Verified all 8 categories classify correctly on representative
  questions, confirmed the non-type fields are still unchanged, and
  reconfirmed zero coupling to agent/retrieval/db/api/llm. Still not wired
  into InvestigationService anywhere — /health, /search, and a real
  Gemini-backed /investigate call all re-verified unaffected.
- Sprint 2 Task 03 — new app/investigation/entities.py: EntityType (11-value
  str Enum: PERSON, ORGANIZATION, PROJECT, STRUCTURE, WORK_ACTIVITY,
  DOCUMENT, EVENT, CONTRACT_REFERENCE, DATE, LOCATION, UNKNOWN) and
  ConstructionEntity (name, entity_type, confidence bounded [0,1], metadata
  defaulting to {}) — the domain model future entity extraction, timeline
  building, evidence linking, and contract intelligence will build on. Pure
  shape, no extraction logic, zero coupling beyond stdlib + Pydantic.
  Exported from app/investigation/__init__.py alongside InvestigationPlanner.
  Not integrated anywhere yet. Verified all 11 enum values, confidence
  bounds in both directions, metadata default vs. explicit passthrough, and
  that an invalid entity_type string is rejected. /health, /search, and a
  real Gemini-backed /investigate call all re-verified unaffected.
- Sprint 2 Task 04 — new app/investigation/extractor.py:
  ConstructionEntityExtractor.extract(question, investigation_type) ->
  EntityExtractionResult. Deterministic V1 heuristics only (no LLM,
  embeddings, or NLP library): regex for STRUCTURE ("Pier P-42"-style),
  longest-phrase-first matching for WORK_ACTIVITY ("reinforcement work" /
  "additional reinforcement work"), keyword matching for ORGANIZATION
  (contractor/employer/engineer). Exported from __init__.py, not integrated
  anywhere yet. Verified exactly against the spec's example question and
  several edge cases (empty match, all 3 organization keywords, no
  double-counting of overlapping phrases).
- Sprint 2 Task 05 — InvestigationPlanner.create_plan() now wires the
  existing classifier and extractor together: investigation_type from
  classify_investigation_type(), primary_entities from
  ConstructionEntityExtractor, goal set to the raw question (changed from
  the "Investigate: {question}" prefix used since Task 01). No new logic —
  reused both modules as-is, confirmed byte-for-byte identical behavior
  whether called through the planner or directly. Still not integrated with
  InvestigationService. /health, /search, /investigate re-verified
  unaffected.
- Sprint 2 Task 06 — InvestigationPlanner now populates
  likely_evidence_sources from a small fixed investigation_type -> document
  types mapping in service.py (static domain knowledge, no retrieval, no
  LLM). All 8 mappings (approval/delay/variation/entitlement/payment/
  evidence/compliance/unknown) verified exactly against spec. expected_
  answer_type/likely_contract_areas/investigation_steps remain placeholders.
  Still not integrated with InvestigationService. /health, /search,
  /investigate re-verified unaffected.
- Sprint 2 Task 07 — InvestigationPlanner is now integrated into
  InvestigationService's pipeline: investigate() calls
  self._planner.create_plan(request.query) right after validation, before
  search — but the resulting InvestigationPlan is only kept as a local
  variable, not yet consumed by search, evidence-building, packaging, or
  reasoning, and never exposed on InvestigationResponse. Injected via
  constructor (planner: InvestigationPlanner | None = None), same DI
  pattern as reasoning_engine/package_builder. Verified the planner runs
  exactly once per investigation (call-counted with a subclassed planner),
  runs after validation (an empty query never reaches it), and that
  InvestigationResponse's schema is unchanged. /health, /search, and a real
  Gemini-backed /investigate call all re-verified unaffected.
- Sprint 3 Task 01 — app/agent/tools.py's search_documents() gained a new
  optional investigation_plan: InvestigationPlan | None = None parameter
  (imported from app.investigation.models directly, not via the package
  root). Accepted and completely unused — never forwarded into
  retrieval/service.py's search_chunks(), which was not touched at all.
  InvestigationService.investigate() now passes its previously-dangling
  local `plan` (from Sprint 2 Task 07) into this parameter. Verified
  backward compatibility (old two/three-arg call style still works,
  positional args still work) and, critically, that supplying a real
  InvestigationPlan produces byte-for-byte identical Citation results to
  not supplying one. /health, /search, /investigate re-verified unaffected.
- Sprint 3 Task 02 — new app/retrieval/context.py: RetrievalContext
  (entity_terms, preferred_document_types, both default_factory=list) —
  pure shape, no logic, not consumed anywhere. Exported from
  app/retrieval/__init__.py, which was previously empty (retrieval had no
  prior export convention; agent/investigation both already export their
  public models this way, so this brings retrieval in line). Verified
  default and explicit construction, that the package-root and direct
  module imports resolve to the same class, and that existing retrieval
  imports (search_chunks, DEFAULT_TOP_K, ChunkSearchResult) are unaffected.
  /health, /search, /investigate re-verified unaffected.
- Sprint 3 Task 03 — new app/retrieval/context_builder.py:
  RetrievalContextBuilder.build(investigation_plan) -> RetrievalContext, a
  pure 1:1 mapping (primary_entities -> entity_terms, likely_evidence_sources
  -> preferred_document_types), no filtering or transformation. Exported
  from app/retrieval/__init__.py alongside RetrievalContext. Verified with
  both a manually-populated InvestigationPlan and a real
  InvestigationPlanner().create_plan() output — mapping matches exactly in
  both cases — plus an empty/default plan producing an empty context. Not
  integrated anywhere yet. /health, /search, /investigate re-verified
  unaffected.
- Sprint 3 Task 03.5 — renamed RetrievalContext.entity_terms to
  search_terms (retrieval shouldn't know or care whether a term came from
  an entity, contract clause, document number, etc.) and updated
  RetrievalContextBuilder's mapping to match. Only two files reference the
  field (grepped the whole backend to confirm), both under
  app/retrieval/, so this was a fully self-contained rename — neither
  module is integrated anywhere else yet, so retrieval behavior is
  structurally guaranteed unchanged, not just tested. Verified default
  construction, the renamed mapping, that the old field name has no effect,
  and existing retrieval imports. /health, /search, /investigate
  re-verified unaffected.
- Sprint 3 Task 04 — new app/retrieval/scoring.py: RetrievalScorer.score(
  semantic_score, retrieval_context, chunk) -> float, a pure pass-through
  that returns semantic_score unchanged without inspecting either other
  argument. Establishes the interface RetrievalService will eventually call
  to combine semantic similarity with other signals; not called by it yet.
  Exported from app/retrieval/__init__.py alongside the other retrieval
  helpers. Verified across a spread of score values (including negative and
  >1 edge values) crossed with both an empty and a populated
  RetrievalContext — output always exactly equals the input. Since nothing
  calls RetrievalScorer yet, retrieval behavior is structurally unchanged,
  not just tested. /health, /search, /investigate re-verified unaffected.
- Sprint 3 Task 05 — RetrievalScorer is now actually called:
  search_chunks() gained an optional retrieval_context parameter and, after
  building each ChunkSearchResult from the DB query (still ordered by
  distance, never re-sorted), passes each result's similarity through
  RetrievalScorer.score() and rebuilds the frozen dataclass with the
  returned value via dataclasses.replace(). Since score() still just
  returns its input, output is unchanged. Fixed a real circular import
  surfaced by this change (scoring.py needed ChunkSearchResult's type,
  service.py now needs RetrievalScorer) by making scoring.py's import of
  ChunkSearchResult TYPE_CHECKING-only — it never touches the object at
  runtime, only in a type hint, so the runtime dependency was unnecessary.
  Verified old/positional/explicit-None call styles are unaffected, that
  results are byte-for-byte identical (dataclass equality) whether or not a
  populated RetrievalContext is supplied, and that returned similarity
  values match prior sessions' recorded values for the same query exactly
  (0.8124/0.8088/0.7798/...). /health, /search, /investigate re-verified.
- Sprint 3 Task 06 — RetrievalScorer now does real (still fully
  deterministic) work: ENTITY_MATCH_WEIGHT = 0.05 module constant; for each
  RetrievalContext.search_term found as a case-insensitive exact substring
  in chunk.chunk_text, adds one weight to semantic_score. No fuzzy
  matching/regex/stemming/synonyms. None context or empty search_terms ->
  unchanged, per spec. Verified all required cases individually (0/1/2
  matches, case-insensitivity both directions, non-matching terms,
  mixed match+non-match, and that preferred_document_types alone never
  triggers a bonus). End-to-end /health, /search, /investigate all
  re-verified — /search scores for the standard test query are still
  identical to Task 05's baseline, since no production call path yet passes
  a populated RetrievalContext into search_chunks (that wiring is a future
  task); the new logic is live but currently inert in the running system.
- Sprint 3 Task 07 — the RetrievalContext pipeline is now fully active.
  tools.search_documents() builds a RetrievalContext from its
  investigation_plan argument (via the existing RetrievalContextBuilder,
  reused as-is) and forwards it into search_chunks() -> RetrievalScorer.
  Since InvestigationService already passed its InvestigationPlan into
  search_documents() since Sprint 3 Task 01, this one change completes the
  full chain with no other file needing changes. Verified with a spy on
  RetrievalScorer.score() that a real investigation's populated context
  (search_terms=["Pier P-42", "Additional reinforcement work"]) reaches it
  on every call, and compared real before/after scores: chunks matching one
  term got exactly +0.05, chunks matching both got +0.10, non-matching
  chunks (none in this test, all 5 top results mentioned Pier P-42) would
  get +0. Notable emergent finding: search_chunks()'s own list order is
  unaffected (as designed since Task 05 — no re-sort happens there), but
  ReasoningEngine (untouched, from Sprint 1) independently ranks evidence by
  confidence before responding, so /investigate's final citation order *is*
  now visibly reordered by the boosted scores even though /search's raw
  order isn't — the entity bonus is genuinely live end-to-end. /health,
  /search (byte-identical to prior baseline, as expected — no plan
  involved), /investigate all re-verified with a real Gemini call.
- Sprint 3 Research Task — Document Type Audit (no code changes). Found:
  doc_type (app/ingestion/metadata.py) is a deterministic slugify of each
  document's own "DOCUMENT TYPE:" header text — not inferred, not an LLM
  call, not from the filename. DB column has no index and no CHECK
  constraint (unlike dossier_findings.finding_type). Live dataset: 17 docs,
  14 distinct doc_type values, 0 NULLs. Compared against
  InvestigationPlanner's _EVIDENCE_SOURCES_BY_TYPE vocabulary: zero exact
  matches — the two vocabularies were built independently (one a curated
  claims taxonomy, one an auto-generated per-document slug) and were never
  reconciled. Recommended introducing a normalized taxonomy rather than
  matching raw values directly; concluded doc_type is NOT reliable enough
  for retrieval scoring as-is.
- Sprint 3 Task 08 — new app/domain/ package (document_types.py):
  DocumentType, a 17-value canonical str Enum, plus
  normalize_document_type(raw) mapping exactly the 14 raw doc_type values
  found in the research audit onto it, explicit lookup only (no
  fuzzy/regex/inference), unmapped/None -> None. Not integrated anywhere —
  ingestion, InvestigationPlanner, RetrievalContextBuilder, and
  RetrievalScorer are all untouched and still use raw strings. Verified
  every one of the 14 live values (re-queried fresh from the DB, not just
  reused from the research task) maps correctly, unknown values and None
  both return None, the enum has exactly the 17 specified values, and
  DocumentType instances behave as real strings (equality, isinstance,
  raw json.dumps) without needing custom serialization. /health, /search,
  /investigate all re-verified unaffected.
- Sprint 3 Task 09 — ingestion now persists canonical DocumentType values.
  app/ingestion/pipeline.py's ingest_document() calls
  normalize_document_type() (Task 08) on the raw extract_doc_type() output
  before constructing the Document row; unmapped/None still persists as
  NULL, no fallback category invented. Re-ingested all 17 dataset documents
  from a truncated table via the real upload endpoint: 17/17 succeeded, and
  querying distinct doc_type values afterward showed only canonical values
  (CORRESPONDENCE x3, PROGRESS_REPORT x3, DRAWING x2, APPROVAL, INVOICE,
  MEASUREMENT, MEETING_MINUTES, NOTICE, PHOTO_RECORD, PROCUREMENT,
  SITE_INSTRUCTION, TECHNICAL_REPORT — 1 each), 0 NULLs, and an explicit
  NOT IN (the 17 canonical values) query returned zero rows, proving no
  legacy raw slug survived. Verified the "unknown -> NULL" path for real
  (not just re-asserting Task 08's unit test) by ingesting a synthetic PDF
  with a "DOCUMENT TYPE:" header outside the mapping — persisted doc_type
  was NULL, exactly as required; test row deleted afterward. /health,
  /search, /investigate re-verified (the latter took unusually long this
  run, apparently transient Gemini-side latency unrelated to this change —
  nothing here touches the LLM path — but returned 200 once it completed).
- Sprint 3 Task 10 — planner now speaks the canonical DocumentType
  vocabulary. InvestigationPlan.likely_evidence_sources and
  RetrievalContext.preferred_document_types both changed from list[str] to
  list[DocumentType] (field names unchanged — the task's own wording
  labeled InvestigationPlan's field "preferred_document_types," which
  doesn't exist on that model; treated as a wording slip, not a rename
  instruction, since renaming would silently break
  RetrievalContextBuilder's existing attribute access and wasn't needed to
  satisfy the stated objective). InvestigationPlanner's
  _EVIDENCE_SOURCES_BY_TYPE rewritten with DocumentType members for all 8
  investigation types; "evidence"'s old "All Document Types" placeholder
  (not a real DocumentType) replaced with [], no wildcard behavior added.
  RetrievalContextBuilder needed zero code changes — its existing pure
  attribute copy automatically carries the new type through. Verified all 8
  investigation types produce the exact expected canonical lists, confirmed
  RetrievalContext receives genuine DocumentType instances via the
  unmodified builder, confirmed pydantic JSON serialization stays clean
  plain strings, and ran a full real end-to-end investigation plus
  /health, /search, /investigate regression, all passing.
- Sprint 3 Task 11 — RetrievalScorer's second signal: DOCUMENT_TYPE_MATCH_
  WEIGHT = 0.05, applied when chunk.doc_type (already a canonical string
  post-Task-09) reconstructed via DocumentType(raw) is found in
  retrieval_context.preferred_document_types — genuine enum membership, no
  manual string comparison. Explicitly NOT using
  normalize_document_type() here since that function's keys are the old
  raw ingestion slugs, not canonical values, and would always return None
  on already-normalized data — flagged and avoided. Entity and doc-type
  bonuses computed independently (_entity_bonus/_document_type_bonus) and
  summed, so either can apply alone or both together. Verified all 8
  required cases (no context, match, non-match, empty preferred list,
  chunk.doc_type is None, chunk.doc_type is an invalid/legacy string —
  graceful, no crash, all 4 accumulation combinations). Ran the real
  "approval" investigation across all 18 chunks against the actual
  re-ingested (canonical) dataset and hand-verified every single delta:
  7 chunks got the +0.05 doc-type bonus (doc17/APPROVAL, doc7 x2/
  MEETING_MINUTES, doc4/SITE_INSTRUCTION, doc5+doc13+doc14/CORRESPONDENCE)
  — notably doc13 and doc14 got the bonus with zero entity matches,
  proving the signal contributes independently, not just riding on
  entity hits. /health, /search (byte-identical, no plan involved),
  /investigate (citation scores matched the manual analysis exactly) all
  re-verified with a real Gemini call.
- Sprint 3 Research Task — Cross-Document Reference Audit (no code changes).
  Read all 17 documents' actual extracted text directly (not just the
  pre-computed referenced_ids column) and built the real reference graph:
  16 verified edges, concentrated on SI-088 (cited by 5 documents — the
  single most load-bearing identifier in the corpus) and the drawing
  revision chain (01→03→04/05/10/17). 11/17 documents (65%) participate in
  at least one edge; 6 are isolated (3 of those are the dataset's
  deliberately-irrelevant noise documents, isolation by design). One
  pattern-consistency anomaly found: doc01's own drawing number is split
  across a PDF line-wrap in its self-declaration (a known, already-flagged
  extraction artifact), but every place other documents cite it renders on
  one line. Concluded YES, deterministic reference extraction is feasible
  (the existing referenced_ids column is already accurate for this), and
  recommended YES, implement find_related_documents() (Sprint 3 Task 12).
- Sprint 3 Task 12 — find_related_documents() implemented, replacing the
  NotImplementedError stub. Widened its signature from a single
  document_id to document_ids: list[int] — "do not duplicate documents
  already retrieved" only makes sense against a full retrieved set, and
  nothing in the codebase called the old stub, so there was no existing
  behavior to preserve. Algorithm: collect the union of referenced_ids
  across the given documents, then a single Postgres array-overlap ("&&")
  join against every other document's own referenced_ids — one hop, no
  ranking, no recursion. Hit a real SQLAlchemy gap along the way:
  Document.referenced_ids uses the generic sqlalchemy.ARRAY type, whose
  comparator has no .overlap() method — fixed with .op("&&") directly, no
  model/schema change needed. Verified both required scenarios (SI-088
  chain correctly surfaces the Site Instruction; the Rev 1 drawing chain
  correctly surfaces the revised drawing), no duplicates in any case
  tested, and proved single-hop-only by recomputing the expected result
  by hand from only the input documents' own referenced_ids and getting an
  exact match. Documented honestly (flagged before implementing, confirmed
  after): because referenced_ids mixes precise IDs with generic location
  tags like "P-42", results can be broad (12-13 of 17 documents) when a
  shared tag like P-42 is involved — inherent to the existing extracted
  data, no new filtering heuristic was added since filtering would itself
  be a scoring judgment this task excluded. /health, /search, /investigate
  re-verified with a real Gemini call.

---

## 🚧 Current Milestone

Milestone 1 – Single-Tool Agent (search + read) — Investigation Engine
foundation, LLM integration, and an HTTP entry point are all done and
verified against a real Gemini API over real HTTP requests. The actual
tool-calling agent loop (the "search → read → follow references → decide
when to stop" loop from PROJECT_PLAN.md Part C step 7) has not been built
yet. ReasoningEngine today answers from evidence gathered in one shot, not
iteratively — and, per the finding above, sometimes weaves in evidence that
isn't actually relevant to the question asked. A separate, not-yet-wired-up
Investigation Planning subsystem (app/investigation/) is being built
alongside it — investigation_type classification is real now, everything
else on the plan is still placeholder.

---

## 🎯 Next Task

Either: (a) build the real multi-turn agent loop per PROJECT_PLAN.md Part D,
(b) give InvestigationPlanner a real (likely LLM-backed) implementation and
decide how/whether InvestigationService consumes its output, or (c) build
citation/fact verification (§19) — still the most-flagged missing integrity
control across every audit so far.

---

## Session Log

### 19 July 2026

**Completed**
- Initial backend setup
- Database setup
- FastAPI setup
- Health endpoint tested
- Backend Foundation reviewed against PROJECT_PLAN.md and verified end-to-end
  (Docker Postgres/pgvector container, table creation, extension install,
  idempotent project seed, /health returning 200 across a server restart)
- Added engine disposal on shutdown, consistent use of the session factory in
  DB init, and docstrings across the DB layer
- Document Ingestion deliverable: upload endpoint(s), PDF storage, PyMuPDF
  extraction, deterministic metadata extraction, Document persistence — all
  verified end-to-end against the real dataset and against corrupted/invalid
  files
- Document Intelligence Layer deliverable: chunking.py, embeddings.py,
  indexing.py added; wired into the ingestion pipeline so upload now chunks +
  embeds + stores in pgvector automatically. Verified idempotent (reprocessing
  a document replaces, never duplicates, its chunks) and semantically correct
  via cosine-distance spot checks.
- Semantic Retrieval deliverable: app/retrieval/service.py + GET /search,
  verified against the P-42 ground-truth question and against empty-corpus /
  empty-query edge cases
- Debugging pass: root cause of "backend won't run" was the Postgres Docker
  container not running (Docker Desktop doesn't auto-start after a reboot on
  macOS) — app failed loudly with a raw psycopg2 traceback and no hint at the
  fix. Hardened app/main.py's lifespan to catch that case and raise a clear
  "is Docker running? run docker compose up -d" message instead. Re-verified
  the full stack end-to-end: dependencies, DB connection, app startup,
  /health, /documents, /search, and a live semantic search.

**Next**
- Agent tools (search_documents, read_document, get_document_metadata,
  find_related_documents) for the Claude Agent SDK loop (Milestone 1)
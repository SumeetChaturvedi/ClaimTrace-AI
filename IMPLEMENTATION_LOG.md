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
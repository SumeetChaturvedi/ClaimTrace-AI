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
- Sprint 3.5 Research Task — Retrieval Evaluation (no code changes). Compared
  4 retrieval configurations (semantic only / +entity bonus / +doctype bonus /
  +reference expansion) across 5 questions, using the real dataset and real
  Gemini calls. Key finding: entity/doctype scoring is applied strictly after
  search_chunks()'s SQL `ORDER BY distance LIMIT top_k`, so those bonuses can
  only re-rank an already-fixed candidate set, never rescue a document that
  fell just outside the top_k — confirmed empirically (Configs A/B/C returned
  the identical document set in all 5 questions, only scores differed).
  Reference expansion, not being SQL-limited, was the only signal shown to
  change a real Gemini answer from wrong to right (Q4: "no mention of which
  drawings were revised" under Config C vs. the correct Rev-1-drawing answer
  under Config D). Recommended Sprint 4 widen the candidate pool before
  scoring so entity/doctype bonuses can affect recall, not just ranking —
  weights (0.05/0.05) left unchanged, evaluation only.
- Sprint 4 Task 01 — Widen Candidate Pool Before Scoring. Acted on the
  Sprint 3.5 recommendation: search_chunks() (app/retrieval/service.py, the
  only file touched) now queries a widened candidate pool
  (`candidate_k = max(top_k * 3, 15)`) instead of exactly top_k, scores every
  candidate with the existing RetrievalScorer unchanged, then sorts by final
  score and truncates to top_k — moving the LIMIT from before scoring to
  after it. RetrievalScorer, entity/doctype bonus logic, InvestigationPlanner,
  InvestigationService, RetrievalContextBuilder, ReasoningEngine,
  PromptBuilder, and the API routes were not touched. Verified against the
  same 5 Sprint 3.5 questions (old limit-then-score vs. new
  widen-then-score-then-limit, both run as library calls against the live
  dataset): Q2 ("Which documents reference Site Instruction SI-088?") changed
  — doc04 (the SI-088 document itself, raw semantic rank #6 at 0.2876, just
  outside the old top-5) now enters the top-5 at 0.3376 once its
  document-type bonus is applied, displacing doc10. This is the exact gap
  Sprint 3.5 flagged: doc04 had never appeared in top-5 for this question
  under any prior configuration. Confirmed live end-to-end via POST
  /investigate: the real (unmocked) Gemini answer now explicitly cites
  "04_site_instruction_si088.pdf (Site Instruction SI-088 itself)", which it
  did not in any Sprint 3.5 config. Q1, Q3, Q4, and Q5 were unchanged
  (identical old/new top-5 sets and scores) — for Q1/Q3 because the already-
  top-ranked documents' bonuses weren't large enough to admit a new document
  ahead of the existing set's margins; for Q4/Q5 because the classifier
  produced empty search_terms and, for Q4, empty preferred_document_types
  too, so no bonus was available to apply regardless of pool width (the
  classifier substring-collision bugs flagged in Sprint 3.5, e.g. "unknown"
  for Q4, are unrelated to and unaffected by this change). /health, /search,
  and /investigate re-verified working; dataset confirmed unchanged
  (17 documents, 18 chunks) after testing.
- Sprint 4 Task 02 — Robust Keyword Matching. Fixed the substring-collision
  bugs Sprint 3.5 found (e.g. "relate" ⊂ "late" → wrongly classified as
  "delay"): backend/app/investigation/classifier.py (the only file touched)
  now compiles each keyword/phrase into a `\b`-bounded regex at import time
  and matches on that instead of plain `in` substring containment. Same
  keyword lists, same priority order (dict insertion order, unchanged), same
  public API (`classify_investigation_type(question) -> str`) — only the
  match test itself changed. Verified: "Which documents relate to
  Measurement Book MB-DMV7-P42-06?" no longer classifies as "delay" (now
  falls through correctly to "evidence" via its "which documents" keyword);
  "What evidence supports the contractor's delay claim?" still classifies as
  "delay"; "Which documents reference Site Instruction SI-088?" still
  classifies as "variation" — unchanged and correct, since "instruction" is a
  genuine whole word there, not a substring collision, and "variation" is
  checked before "evidence" in the (preserved) priority order. Also swept
  several keyword-list categories for legitimate whole-word usage (all still
  fire) and additional un-requested substring collisions the same fix
  resolves for free ("claim" ⊂ "disclaimer"/"reclaimed", "paid" ⊂ "unpaid",
  "late" ⊂ "plate") — none now misfire. Confirmed the fix changes real
  end-to-end behavior via a live POST /investigate call: the Measurement Book
  question no longer gets the "delay" investigation type's (wrong)
  preferred_document_types bonus applied, and now returns
  10_measurement_record.pdf as the top, correctly-scored result with a clean
  answer. /health, /search, /investigate re-verified working; dataset
  confirmed unchanged (17 documents, 18 chunks) after testing.
- Sprint 4 Task 03 — Citation Verification. Implemented the missing
  integrity control flagged in every audit so far: new
  app/agent/citation_verification.py (verify_citations()) checks each
  citation ReasoningEngine is about to return against the database —
  DocumentChunk row exists, its document_id matches the citation's, its
  chunk_text is non-empty, any claimed page matches the chunk's own recorded
  page_number, and the citation is present in the evidence actually
  retrieved for this investigation — dropping any that fail, deduplicating
  by (document_id, chunk_id), never repairing or fabricating a replacement.
  No LLM call, no new retrieval, no answer rewriting. Wired into
  app/agent/reasoning.py's reason() (not app/agent/service.py, which this
  task's guardrails placed off-limits) — the exact point supporting_evidence
  is assembled — since reasoning.py's own documented safety invariant
  already guarantees citations are never parsed out of the LLM's answer text
  (they come straight from InvestigationPackage.evidence), this check is
  real defense-in-depth against that invariant ever being violated, not a
  response to a known way it currently is. Verified all required edge cases
  directly against real DocumentChunk rows: valid citations pass unchanged
  and in order; duplicates collapse to the first occurrence; a nonexistent
  chunk_id is rejected; a chunk_id/document_id pair that doesn't actually
  belong together is rejected; a wrong claimed page is rejected; a
  well-formed citation absent from the retrieved-evidence set is rejected;
  an empty input list returns empty; an all-invalid input list returns empty
  (no fabrication); a mixed valid/invalid list keeps only the valid ones, in
  order. Confirmed live via a real POST /investigate call: all 5 real
  citations for the Pier P-42 approval question passed verification
  unchanged, and reasoning_steps now includes "Verified each citation
  against the database before returning it." /health and /search re-verified
  unaffected (this task's change is entirely inside ReasoningEngine, off the
  retrieval path). Dataset confirmed unchanged (17 documents) after testing.
- Sprint 4 Task 04 — Separate Document References from Construction
  References. Fixed the "generic identifiers create excessive expansion"
  problem flagged in Sprint 3.5 and re-confirmed in the Sprint 4 Contract
  Clause Audit: app/ingestion/metadata.py's single extract_referenced_ids()
  mixed genuine document identifiers (SI-088, drawing IDs, DPR/MB/GEO codes)
  with bare location tags (P-42, P-15, P-38) that appear in nearly every
  document about the same subject. Split into extract_document_references()
  and extract_location_references() (same underlying _ID_CODE_RE/_REV_RE
  patterns, partitioned by a new _LOCATION_PATTERN = \b P-\d{1,4}\b for Pier
  identifiers specifically, per the task's scope), plus is_location_reference()
  for classifying an already-stored id. extract_referenced_ids() is kept,
  redefined as the union of both — verified byte-identical output against
  every one of the 18 stored documents' actual raw text, and confirmed
  Document.referenced_ids in the live DB still matches recomputed output
  exactly, i.e. ingestion behavior and stored data are completely unchanged
  (this task did not touch app/ingestion/pipeline.py or the DB schema).
  app/agent/tools.py's find_related_documents() (the only other file
  touched) now filters out is_location_reference() ids from the join key
  before the array-overlap query, so expansion is driven only by document
  identifiers; location tags remain stored in Document.referenced_ids as
  before, just excluded at the point of use. Measured the expansion graph
  for every document individually, old vs. new: mean expansion size dropped
  from 10.71 to 4.24 (of 16 possible other documents), max from 13 to 10;
  most strikingly, docs 8 (DPR day 1) and 11 (photo log) — whose only prior
  connection to anything was the shared "P-42" tag — now correctly expand to
  0 related documents instead of 13, since they cite no other document by an
  actual identifier. Verified SI-088 expansion still succeeds (doc4 alone
  now expands to the direct SI-088-citing set {5,6,7,10,17} plus other
  document-identifier-linked docs, correctly excluding the DPRs/photo log
  that only shared P-42) and drawing-reference expansion still succeeds
  (doc3 alone correctly reaches doc4/doc10/doc17 via shared drawing/geotech
  IDs). RetrievalScorer, InvestigationPlanner, InvestigationService,
  ReasoningEngine, PromptBuilder, API routes, and the database schema were
  not touched. /health, /search, /investigate re-verified working (neither
  /search nor /investigate currently calls find_related_documents(), so
  their behavior is unaffected by construction); dataset confirmed unchanged
  (17 documents) after testing.
- Sprint 5 Research Task — Timeline Reconstruction Audit (no code changes).
  Read all 17 documents' extracted text and metadata directly. Found: 17/17
  documents have an explicit date that survives extraction and is correctly
  stored in Document.doc_date; sorting by that field alone produces a single
  coherent chronology with zero ordering inconsistencies against every
  cross-document reference actually present; the dataset's one deliberate
  contradiction (doc 13's internal email predating doc 2's "official"
  geotech trigger) is itself temporally consistent — the tension is
  narrative, not a date error. One precision gap noted: doc 11 has a
  "DATE RANGE" header and extract_doc_date() only captures the range's
  start, silently dropping the end date and three finer-grained in-body
  photo dates. No timeline model, chronology utility, or event model exists
  anywhere in the codebase — only aspirational docstring mentions of a
  future "Timeline Engine." Recommended the smallest addition: a
  TimelineBuilder that sorts already-gathered documents by their existing
  doc_date, needing no new extraction, schema change, or LLM call.
- Sprint 5 Task 01 — Timeline Builder. Implemented the recommendation above:
  new backend/app/investigation/timeline.py (the only file created) —
  TimelineEvent (Pydantic model: document_id, document_date, document_type,
  event_label) and TimelineBuilder.build(documents) -> list[TimelineEvent].
  One TimelineEvent per input Document, event_label set deterministically to
  the filename's stem (no LLM, no summarization, no inference), sorted
  ascending by document_date using Python's stable sort so same-date ties
  keep their input order rather than being reordered arbitrarily; a missing
  document_date sorts last instead of raising. Not integrated into
  InvestigationService, not exposed via any API route, and doesn't touch
  retrieval, RetrievalScorer, InvestigationPlanner, ReasoningEngine,
  PromptBuilder, GeminiProvider, or the database schema — infrastructure
  only, per this task's scope. Verified against all 17 real documents: 17
  documents in, 17 events out; the resulting order matches the chronology
  already hand-verified in the Sprint 5 Research Task above exactly (drawing
  Rev0 -> contradictory email -> geotech report -> ... -> approval letter);
  every event's document_date/document_type/event_label matches its source
  Document row exactly; stability explicitly confirmed by reversing the
  input list and observing the one same-date tie (docs 8 and 11, both
  2019-07-02) flip its relative order accordingly rather than staying fixed
  by some other key; a synthetic None-date document was confirmed to sort
  last without crashing. /health, /search, /investigate re-verified working
  (nothing calls the new module yet, so behavior is unaffected by
  construction); dataset confirmed unchanged (17 documents) after testing.
- Sprint 5 Task 02 — Deterministic Timeline Event Labels. Replaced
  TimelineEvent.event_label's filename-derived placeholder (Task 01) with a
  static, exhaustive DocumentType -> label mapping
  (_EVENT_LABEL_BY_TYPE in app/investigation/timeline.py, the only file
  touched): DRAWING->"Drawing Issued", SITE_INSTRUCTION->"Site Instruction
  Issued", NOTICE->"Contractor Notice Submitted",
  MEETING_MINUTES->"Meeting Held", CORRESPONDENCE->"Correspondence Sent",
  PROGRESS_REPORT->"Progress Report Recorded",
  MEASUREMENT->"Measurement Recorded", PHOTO_RECORD->"Site Photo Recorded",
  PROCUREMENT->"Material Delivery Recorded",
  TECHNICAL_REPORT->"Technical Report Issued", APPROVAL->"Approval Granted",
  INVOICE->"Invoice Issued", plus sensible labels for the types the current
  dataset doesn't use (CONTRACT->"Contract Executed",
  VARIATION->"Variation Issued", PROGRAMME->"Programme Issued",
  PAYMENT->"Payment Recorded", CLAIM->"Claim Submitted") so the mapping is
  exhaustive over all 17 DocumentType values, confirmed programmatically.
  None or an unrecognized raw doc_type string falls back to "Project Event"
  rather than raising, mirroring RetrievalScorer's existing
  _as_document_type() reconstruction pattern. No document text, filename, or
  LLM call is involved in the label anymore. Verified against all 17 real
  documents: every event_label matches the mapping exactly; every other
  field (document_id/document_date/document_type) still matches its source
  Document row; the sorted order is byte-identical to Sprint 5 Task 01's
  already-verified output. /health, /search, /investigate re-verified
  working; dataset confirmed unchanged (17 documents) after testing.
- Sprint 5 Task 03 — Timeline Query Service. Added TimelineQueryService to
  app/investigation/timeline.py (the only file touched): events_before(),
  events_after(), and events_between() — pure, position-based list
  operations over an already-sorted timeline, no database access, no
  re-sorting, no date comparison (position in the list, which
  TimelineBuilder already sorted by date, is the only signal used).
  events_between() is order-agnostic in which id is passed first (the
  earlier-positioned id is always treated as the slice start). Any id with
  no matching event (including an empty timeline) returns [] rather than
  raising, per the task's rules. Verified against the real 17-document
  timeline: events_before(17) (Approval Granted, last in the timeline)
  returns all 16 preceding events, the full investigation history;
  events_before(1) (Drawing Issued, first in the timeline) returns [];
  events_after(4) (Site Instruction Issued) returns 11 events including
  doc 6 (notice), doc 7 (meeting), and doc 17 (approval), exactly as the
  task's example expected; events_between(4, 7) returns exactly [4, 5, 6, 7]
  and events_between(7, 4) returns the identical subsequence, confirming
  order-agnostic behavior; nonexistent document_ids and an empty timeline
  both return [] in all three methods with no exceptions raised. Not
  integrated into InvestigationService or exposed via any API route, and
  doesn't touch InvestigationPlanner, retrieval, RetrievalScorer,
  ReasoningEngine, PromptBuilder, GeminiProvider, or the database schema —
  query infrastructure only, per this task's scope. /health, /search,
  /investigate re-verified working; dataset confirmed unchanged
  (17 documents) after testing.
- Sprint 5 Task 04 — Timeline Formatter. Added TimelineFormatter to
  app/investigation/timeline.py (the only file touched): format(events)
  renders one "YYYY-MM-DD — Event Label" line per event, in exactly the
  order given (never re-sorted), joined with newlines — formatting only, no
  summarization, no merging, no date inference, no document text, no AI, no
  database access. A missing document_date renders as "Unknown Date" rather
  than being inferred or omitted; an empty list returns "". Verified against
  the real 17-event timeline: 17 lines out, each matching its event exactly
  in the given order, first line "2019-03-10 — Drawing Issued" and last line
  "2019-07-20 — Approval Granted"; a synthetic None-date event renders as
  "Unknown Date — Drawing Issued"; an empty timeline returns "". Not wired
  into ReasoningEngine, PromptBuilder, or any other reasoning/investigation
  flow yet, and doesn't touch InvestigationService, InvestigationPlanner,
  retrieval, RetrievalScorer, GeminiProvider, API routes, or the database
  schema — formatting infrastructure only, per this task's scope. /health,
  /search, /investigate re-verified working; dataset confirmed unchanged
  (17 documents) after testing.
- Sprint 5 Task 05 (final task of Sprint 5) — Timeline-Aware Investigation
  Context. Wired the Sprint 5 timeline subsystem into the real reasoning
  pipeline, reusing TimelineBuilder/TimelineFormatter as-is (no timeline
  logic duplicated). New app/agent/tools.py function get_documents(ids)
  fetches the Document rows for already-retrieved citations (not a new
  retrieval step). InvestigationService (now permitted to touch, unlike
  prior Sprint 5 tasks) gained a private _build_timeline_context(citations)
  that dedupes citation document_ids, fetches those Document rows, builds a
  chronology via TimelineBuilder, and formats it via TimelineFormatter —
  scoped strictly to this investigation's retrieved documents, never the
  whole corpus. InvestigationPackage gained a new timeline_context: str = ""
  field, threaded through InvestigationPackageBuilder.build() unchanged
  (just carried through, same pattern as `evidence`). PromptBuilder gained
  _timeline_section(), which appends a "----------------------\nPROJECT
  TIMELINE\n\n<formatted lines>\n----------------------" block to the user
  prompt only when timeline_context is non-empty; _instructions_section()
  (the system prompt) is verified byte-for-byte unchanged — no instruction
  telling the model to build or reorder a chronology was added, since the
  timeline already exists and only needs to be read. Verified: with no
  timeline_context, no PROJECT TIMELINE section appears at all; with one,
  it appears wrapped exactly as specified and the formatted lines match
  TimelineFormatter's own output verbatim. Confirmed the timeline is scoped
  to retrieved documents only (a 4-citation test produced exactly 4 timeline
  lines, not 17). Inspected the real, full prompt built for a live
  chronology question against the actual database — timeline appeared
  correctly ordered and correctly scoped. Ran two real, unmocked Gemini
  comparisons (same evidence, with vs. without the timeline section): for
  both a general "sequence of events" question and the dataset's flagship
  contradiction/ordering question (contractor's private soil observation vs.
  the official geotech report), answers were already correct on both sides —
  this dataset's evidence excerpts embed "DATE:" headers directly, so unlike
  Sprint 4's reference-expansion fix there wasn't a stark wrong-to-right
  flip to observe here; reported honestly rather than oversold. Ran a full,
  real /investigate call through the actual HTTP API (not just library
  calls) with both citation verification (Task 03) and timeline context
  (this task) active simultaneously — correct, well-ordered chronology
  returned. Retrieval, RetrievalScorer, InvestigationPlanner, GeminiProvider,
  API routes, and the database schema were not touched. /health, /search,
  /investigate re-verified working; dataset confirmed unchanged
  (17 documents) after testing.
- Sprint 6 Research Task 01 — Contract Intelligence Audit (no code changes).
  Designed the architecture for future clause-aware retrieval. Recommended
  FIDIC 1999 Red Book (matches the dataset's own scenario and its existing
  "Contract Clause 20.1-equivalent" reference in doc 6), a minimum 10-clause
  set (1.3, 3.3, 4.1, 8.4, 8.7, 13.1, 13.3, 14.3, 14.7, 20.1), sub-clause as
  the retrieval unit, and only 3 metadata fields (clause_number/title/topic —
  explicitly rejected parent_clause as derivable and keywords as redundant
  with existing entity scoring). Confirmed DocumentType.CONTRACT and its
  "entitlement"-category wiring already exist, dormant, in
  InvestigationPlanner; confirmed EntityType.CONTRACT_REFERENCE is defined
  but has no extraction heuristic. Recommended no database schema change —
  fold clause_number/title into chunk_text itself, same pattern as Sprint 4
  Task 04's zero-schema-change fix. Recommended implementation order
  Research -> Models -> Parser -> Retrieval -> Planner -> Reasoning,
  matching this project's own established sequencing on every prior
  subsystem (RetrievalContext before RetrievalScorer; TimelineEvent before
  TimelineBuilder).
- ClaimTrace V2 Research Task 02 — Fictional Project Design (no code
  changes, no documents generated). Designed the complete ground-truth
  blueprint for Dataset V2: the Nandira River Bridge Project (fictional
  country/river/district/all parties), FIDIC 1999 Red Book admeasurement
  contract, 28 major events spanning contract award through the defects
  period, all 6 of the task's requested contradiction types (internal email
  vs. report, omitted instruction, late drawing revision, late notice,
  measurement error, payment dispute) each independently evidence-resolvable,
  and ground truth deliberately authored as mixed rather than one-sided
  (some claims valid, some time-barred, some partially granted, ~3-4 weeks
  of completion delay left genuinely unexplained). Estimated ~139 documents
  across 28 categories, recommended phased generation (event-anchored core
  first). Recommended a Project -> Ground Truth -> Timeline -> Documents ->
  Evidence Graph -> Evaluation Scenarios architecture, with ground truth and
  timeline fixed before any document text is written.
- Sprint 6 Task 01 (first implementation task of Sprint 6) — Contract Clause
  Domain Model. New backend/app/contracts/ package (models.py + __init__.py,
  the only files created): ContractClause (BaseModel: clause_number, title,
  topic, text — no validators, no methods, no extra fields, matching the
  task's "pure data model" requirement exactly) and ClauseTopic (str Enum:
  NOTICE, DELAY, EXTENSION_OF_TIME, VARIATION, PAYMENT, CLAIMS, ENGINEER,
  CONTRACTOR, GENERAL), both re-exported through contracts/__init__.py
  alongside a direct-import path via contracts/models.py, mirroring the
  existing app/investigation/__init__.py and app/domain/document_types.py
  patterns. Canonical representation only — no parser, no retrieval
  integration, no planner integration; confirmed via grep that nothing else
  in the codebase imports app.contracts yet. Verified: default construction
  correctly raises ValidationError (no field has an implicit default, since
  none was specified and none was asked for); explicit construction with
  all 4 fields; topic accepts both a ClauseTopic member and its raw string
  value; JSON serialization emits the enum as its plain string value and
  round-trips back to an equal model; dict dump preserves the ClauseTopic
  enum member; all 9 canonical topics present, no extras; package import
  (`from app.contracts import ...`) and direct import
  (`from app.contracts.models import ...`) resolve to the identical classes.
  Retrieval, RetrievalScorer, InvestigationPlanner, InvestigationService,
  ReasoningEngine, PromptBuilder, GeminiProvider, API routes, the database
  schema, and the ingestion pipeline were not touched. /health, /search,
  /investigate re-verified working; dataset confirmed unchanged
  (17 documents) after testing.
- Sprint 6 Task 02 — Clause Parser. New backend/app/contracts/parser.py (the
  only file created; contracts/__init__.py deliberately left untouched,
  since this task didn't ask for it to be exported and "do not integrate it
  anywhere" argued against adding even an __init__ export): ClauseParser,
  a deterministic text-splitter with no AI, database access, or
  clause-hierarchy inference. Detects numbered heading lines (a line
  containing only a clause number — bare "1"/"20" or dotted "1.1"/"8.4"/
  "20.1") via one regex, and a clause spans from immediately after one
  heading to immediately before the next (or end of text) — exactly the
  literal "next numbered heading" rule, nothing inferred about hierarchy.
  Title is the first non-blank line following the heading; everything after
  that is ContractClause.text. Topic comes from a small private
  prefix->ClauseTopic dict (1->GENERAL, 3->ENGINEER, 4->CONTRACTOR,
  8->DELAY, 13->VARIATION, 14->PAYMENT, 20->CLAIMS — the task's own explicit
  examples plus two additions directly named in ClauseTopic and covered by
  the Sprint 6 Research Task 01 clause set); any other prefix falls back to
  GENERAL. Verified against a representative 8-clause sample contract text
  (spanning all 7 mapped prefixes): correct clause count, correct numbering,
  correct titles, correct topic assignment, and correct text boundaries —
  explicitly confirmed clause 1's text doesn't leak into clause 3.3's, and
  clause 13.1's doesn't leak into clause 13.3's. Also verified: an unknown
  prefix (99) falls back to GENERAL; a heading with nothing following it
  (end of text) produces an empty title/text without crashing; text with no
  headings at all returns an empty list; an inline number not on its own
  line (e.g. "20.1 tonnes of material") is correctly not mistaken for a
  heading; preamble text before the first heading is correctly excluded
  from every clause. Confirmed via grep that nothing else in the codebase
  imports ClauseParser yet. Retrieval, InvestigationService,
  InvestigationPlanner, ReasoningEngine, PromptBuilder, GeminiProvider, API
  routes, the database schema, and ingestion were not touched. /health,
  /search, /investigate re-verified working; dataset confirmed unchanged
  (17 documents) after testing.
- Sprint 6 Task 03 — Clause Repository. New backend/app/contracts/
  repository.py (the only file created): ClauseRepository, a pure,
  read-only, in-memory wrapper over a list[ContractClause] supplied at
  construction — no database, no file loading, no parsing (doesn't call
  ClauseParser), no AI, no retrieval, no mutation. Constructor copies the
  given list into an internal tuple (immune to the caller later mutating
  its own list) and builds a clause_number -> ContractClause dict for O(1)
  lookup. get_all() returns every clause in construction order (a fresh
  list each call, so mutating the return value can't corrupt internal
  state); get_by_number(clause_number) returns the matching clause or None;
  get_by_topic(topic) returns every matching clause, in construction order.
  Verified against a representative 9-clause set (mirroring Sprint 6
  Task 02's sample): get_all() returns all 9 in order; get_by_number("20.1")
  finds "Contractor's Claims"; get_by_topic(DELAY) returns exactly
  [8.4, 8.7] in order, get_by_topic(VARIATION) returns exactly
  [13.1, 13.3], get_by_topic(NOTICE) returns [] (no clause in the sample
  has that topic); get_by_number("99.9") returns None, no exception; the
  read-only guarantee verified in both directions (mutating the list
  returned by get_all(), and mutating the original list after construction)
  neither affects the repository; an empty repository correctly returns
  []/None/[] from all three methods with no exceptions. Confirmed via grep
  that nothing else in the codebase imports ClauseRepository yet. Retrieval,
  InvestigationService, InvestigationPlanner, ReasoningEngine, PromptBuilder,
  GeminiProvider, API routes, the database schema, and ingestion were not
  touched. /health, /search, /investigate re-verified working; dataset
  confirmed unchanged (17 documents) after testing.
- Dataset V2 Phase 1 Research — Contract Package Design (no code, no
  documents generated). Designed the four-document Contract Package blueprint
  for the Nandira River Bridge Project: General Conditions (extract of the
  same 10 sub-clauses from Sprint 6 Research Task 01), Particular Conditions
  (project-specific amendments — Monsoon Period restriction, delay damages
  rate, VTD 500,000 Variation approval threshold, 56-day payment period,
  retention/performance security), Contract Data (the numeric schedule), and
  Employer's Requirements (technical scope). Defined cross-document
  precedence (Particular Conditions prevail over General Conditions) and an
  explicit events-to-governing-clauses ground-truth table tying every
  load-bearing V2 dispute event to a specific drafted clause.
- Dataset V2 Phase 1 — Generated the four Contract Package documents per
  the approved blueprint (original fictional legal/technical drafting, not
  reproduced FIDIC text): NRB4-GC-2020 (General Conditions, extract of
  Sub-Clauses 1.3/3.3/4.1/8.4/8.7/13.1/13.3/14.3/14.7/20.1), NRB4-PC-2020
  (Particular Conditions, amending/supplementing those same sub-clauses with
  project-specific values and adding site-specific obligations — working
  hours, utility coordination, river environmental protection, Hold Points,
  key personnel, record keeping), NRB4-CD-2020 (Contract Data, the numeric
  schedule — VTD 42,000,000 Contract Amount, 30-month Time for Completion,
  5%/VTD 2,100,000 retention, 10%/VTD 4,200,000 performance security,
  0.05%-per-day/10%-cap delay damages, 56-day payment period), and
  NRB4-ER-2020 (Employer's Requirements — 640m/8-span/7-pier bridge
  configuration, materials, foundations, the 7 Hold Points, testing/survey/
  as-built requirements). These are dataset content, not application code —
  no backend files were touched.
- Sprint 6 Task 04 — Clause Search Service. New backend/app/contracts/
  search.py (the only file created; models.py, parser.py, and
  repository.py — all explicitly off-limits this task — were not touched):
  ClauseSearchService, a read-only search layer sitting above
  ClauseRepository. Constructor stores the given repository only, no
  mutation. find_by_number()/find_by_topic() delegate straight to the
  repository. find_by_keywords() performs deterministic, case-insensitive
  substring matching (no regex) across clause_number/title/text combined —
  a clause matches if any supplied keyword appears in any of those three
  fields — with no scoring, ranking, or sorting; results are returned in
  the repository's original order, and a clause matching multiple keywords
  still appears exactly once (each clause visited once per repository
  pass). Returns [] immediately for an empty keyword list. Verified against
  a representative 10-clause set covering all 11 required checks: correct
  lookup by number, None for an unknown number, correct topic lookup, []
  for a topic with no matches, keyword matches against title/text/number
  individually, a multi-keyword union with no duplicates, repository order
  preserved under both single- and multi-keyword searches, [] for an empty
  keyword list, and identical results across lowercase/uppercase/mixed-case
  keywords. Additionally verified the repository and its clauses are
  byte-identical before and after several search calls (read-only
  guarantee). Confirmed via grep that nothing else in the codebase imports
  ClauseSearchService yet. Retrieval, RetrievalScorer, InvestigationPlanner,
  InvestigationService, ReasoningEngine, PromptBuilder, GeminiProvider, API
  routes, the database schema, ingestion, ClauseParser, ContractClause, and
  ClauseRepository were not touched. GET /health, GET /search, and
  POST /investigate re-verified behaving identically; dataset confirmed
  unchanged (17 documents) after testing. No planner integration begun,
  per the task's explicit instruction.
- Sprint 6 Task 05 — Contract Context Model. New backend/app/contracts/
  context.py: ContractContext (BaseModel: clause_numbers: list[str],
  clause_topics: list[ClauseTopic], keywords: list[str], all
  default_factory=list, no validators, no methods, no computed properties)
  — mirrors app/retrieval/context.py's RetrievalContext precedent exactly.
  Exported through contracts/__init__.py alongside ContractClause and
  ClauseTopic (the only other file touched). ClauseParser, ClauseRepository,
  ClauseSearchService, and their own files were not touched. Verified:
  default construction gives all three fields an empty list, and
  default_factory=list gives each instance its own independent list rather
  than a shared mutable default; explicit construction with all three
  fields populated; JSON serialization emits plain lists and ClauseTopic
  members as their string values; round-trip (model -> JSON -> model)
  preserves equality for both the explicit and the default (empty)
  instance; package import (`from app.contracts import ContractContext`)
  and direct import (`from app.contracts.context import ContractContext`)
  resolve to the identical class. Confirmed via grep that nothing else in
  the codebase imports ContractContext yet. Retrieval, RetrievalScorer,
  InvestigationPlanner, InvestigationService, ReasoningEngine, PromptBuilder,
  GeminiProvider, API routes, the database schema, and ingestion were not
  touched. GET /health, GET /search, and POST /investigate re-verified
  behaving identically; dataset confirmed unchanged (17 documents) after
  testing. No builder implementation begun, per the task's explicit
  instruction.
- Sprint 6 Task 06 — Contract Context Builder. New backend/app/contracts/
  context_builder.py (the only file created — ClauseParser,
  ClauseRepository, ClauseSearchService, and their files were not touched):
  ContractContextBuilder.build(investigation_plan) -> ContractContext, a
  pure mapping mirroring app/retrieval/context_builder.py's
  RetrievalContextBuilder precedent. Maps
  investigation_plan.primary_entities -> keywords verbatim, preserving
  order (InvestigationPlan has no literal search_terms attribute;
  primary_entities is the field that plays that role, the same source
  field RetrievalContextBuilder already copies into RetrievalContext's own
  search_terms — documented explicitly in the module docstring to avoid
  ambiguity). Maps investigation_type -> clause_topics via a fixed 8-entry
  dict matching the task's exact suggested mapping (approval->[GENERAL,
  ENGINEER], delay->[DELAY, CLAIMS], variation->[VARIATION, ENGINEER],
  payment->[PAYMENT, CLAIMS], entitlement->[CLAIMS, DELAY, VARIATION],
  compliance->[GENERAL, CONTRACTOR], evidence->[], unknown->[]), with a
  defensive (never-triggered by the real classifier) fallback to [] for
  any other value. clause_numbers is always [] — clause-number extraction
  is explicitly out of scope. Verified all 8 investigation_type mappings
  exactly; keywords copied unchanged and order-preserved from
  primary_entities, including the empty case; clause_numbers empty across
  every investigation_type regardless of other fields; an unrecognized
  investigation_type falls back to [] rather than raising. Sanity-checked
  against three real InvestigationPlanner-produced plans (Sprint 3.5's
  question set) to confirm the mapping behaves sensibly on live
  classifier/extractor output, not just synthetic plans. Confirmed via
  grep that nothing else in the codebase imports ContractContextBuilder
  yet. InvestigationPlanner, InvestigationService, Retrieval,
  RetrievalScorer, ReasoningEngine, PromptBuilder, GeminiProvider, API
  routes, the database schema, ingestion, ClauseParser, ClauseRepository,
  and ClauseSearchService were not touched. GET /health, GET /search, and
  POST /investigate re-verified behaving identically; dataset confirmed
  unchanged (17 documents) after testing. Builder not integrated anywhere,
  per the task's explicit instruction.
- Sprint 6 Task 07 — Contract Clause Retrieval. Wired ContractContextBuilder
  and ClauseSearchService into InvestigationService.investigate(), right
  after the InvestigationPlan is created. New backend/app/contracts/
  clause_retrieval.py: ClauseRetriever(repository, search_service).retrieve
  (context) unions find_by_number() (only if clause_numbers is non-empty),
  find_by_topic() (once per topic), and find_by_keywords() into a
  deduplicated, TRUE-repository-order result — collects matched
  clause_numbers into a set, then filters ClauseRepository.get_all() by
  that set, rather than naively concatenating the three (already
  individually repository-ordered) result lists, which would NOT preserve
  repository order across the union boundary (verified explicitly with a
  case where naive concatenation and true repository order diverge).
  InvestigationPackage gained a retrieved_clauses: list[ContractClause] = []
  field (InvestigationPackageBuilder.build() threads it through unchanged,
  same pattern as timeline_context); PromptBuilder and ReasoningEngine were
  not touched, so retrieved_clauses is stored but never read — not yet
  exposed to Gemini, exactly as required. InvestigationService gained
  constructor-injectable clause_repository/contract_context_builder
  parameters (same pattern as every other collaborator), defaulting to an
  empty ClauseRepository([]) — no contract-clause ingestion pipeline exists
  yet, so there is honestly no real clause data anywhere in the running
  system today; the pipeline itself is fully wired, tested and correct,
  ready for a populated repository via the same injection point once
  ingestion exists. Verified: topic retrieval, keyword retrieval, a
  three-way union with correct membership, duplicate removal (a clause
  matching all three criteria appears exactly once), true repository order
  preserved across a union that crosses step boundaries, a fully empty
  context returning [], and a clause_numbers entry with no matching clause
  being silently ignored rather than raising. Verified a real investigation
  two ways: through the live (default, empty) repository, confirming
  retrieved_clauses=[] with no crash; and with an injected, populated
  ClauseRepository (constructor injection, same path production would use),
  confirming correct end-to-end retrieval. Confirmed by spying on
  ReasoningEngine.reason() during a full investigate() call that
  retrieved_clauses flows correctly into the InvestigationPackage actually
  handed to reasoning. InvestigationPlanner, Retrieval, RetrievalScorer,
  ReasoningEngine, PromptBuilder, GeminiProvider, API routes, the database
  schema, ingestion, and ClauseParser were confirmed untouched (zero diff).
  GET /health, GET /search, and POST /investigate re-verified against the
  real API — POST /investigate's answer for a repeat question matched the
  same evidence/citations as prior runs, confirming clauses are not
  leaking into the prompt; dataset confirmed unchanged (17 documents)
  after testing.
- Sprint 6 Task 08 — Contract Clause Prompt Integration. Modified
  app/agent/prompt_builder.py only: new _contract_clause_section(
  retrieved_clauses) formats each clause as "Clause <number>\n<title>\n
  <full text>" (verbatim — no summarizing, truncating, interpreting,
  renumbering, or rewording), blocks separated by a blank line, headed by
  "----------------------------------\nRELEVANT CONTRACT CLAUSES", or ""
  if retrieved_clauses is empty. build_reasoning_prompt()'s section
  assembly now inserts this section immediately after the Question and
  before Statistics/Evidence/Timeline; the section is simply omitted (not
  appended empty) when there are no clauses. _evidence_section(),
  _timeline_section(), and _instructions_section() (the system prompt) are
  byte-for-byte unchanged — confirmed explicitly that the system prompt is
  identical with and without clauses present. Verified: empty clause list
  produces no section; a single clause renders with correct number/title/
  text; multiple clauses render in the exact order given (never
  independently re-sorted — proven by reversing the input and observing
  the section's order reverse too, confirming ClauseRetriever's upstream
  repository ordering, established in Sprint 6 Task 07, is what actually
  determines final order); every clause's text preserved verbatim with no
  truncation. Ran a real, unmocked Gemini call with an actual retrieved
  Sub-Clause 20.1 (28-day notice bar) injected via a populated
  ClauseRepository: Gemini's answer explicitly cited "[Clause 20.1]" as a
  source distinct from the document citations, and correctly reasoned that
  an 8-day notice fell within the clause's 28-day limit — real,
  decisive proof the clause text is genuinely exposed to and usable by the
  model, not just present in the package. InvestigationPlanner, Retrieval,
  RetrievalScorer, InvestigationService, ReasoningEngine, GeminiProvider,
  API routes, the database schema, and ingestion were not touched.
  GET /health, GET /search, and POST /investigate re-verified against the
  real, live (still clauseless) system — answer for a repeat question
  matched prior runs; dataset confirmed unchanged (17 documents) after
  testing.
- Dataset V2 — Task 01 (Project Lifecycle Design), Task 02 (Investigation
  Scenario Design), Task 03 (Ground Truth Catalogue) — research/design only,
  no code. Mapped the Nandira River Bridge Project onto 7 lifecycle stages
  (Contract Award through Defects Liability) with per-stage document types,
  dependencies, and capability coverage (~121 documents recommended, 4
  already generated); designed 13 investigation scenarios directly off the
  28-event ground truth, each with a primary question, evidence chain,
  ClauseTopic/DocumentType mapping, and difficulty rating; then produced a
  full ground-truth catalogue (final outcome, claim outcome, critical
  evidence/clauses, expected reasoning path, expected confidence) for all
  13, plus a scenario dependency matrix, coverage analysis, and a
  dependency-respecting generation order. Key findings carried into
  implementation: the live ClauseRepository being empty (Sprint 6 Task 07)
  blocks every scenario's Contract Clauses capability regardless of
  document generation, identified as the top completeness gap to close
  first — directly motivating the next task.
- Dataset V2 Implementation — Task 01 — Automatic Contract Package
  Ingestion. New backend/app/contracts/ingestion.py (ContractPackageLoader,
  get_default_clause_repository()) plus a change to
  InvestigationService.__init__ (app/agent/service.py) to default to it.
  Also persisted the four already-approved Contract Package documents
  (drafted and approved in the "Generate Document 01-04" tasks, never
  previously written to disk) to new backend/storage/contracts/*.txt files
  — not new content, but discovered along the way that the General
  Conditions document's headings ("1.3 Notices" on one line) didn't match
  ClauseParser's documented format (number alone, then title on the next
  line) — reformatted only the 10 heading lines to two-line form, with
  every word of every clause's substantive text preserved exactly; the
  other three documents (Particular Conditions, Contract Data, Employer's
  Requirements) use lettered Parts/plain sections, not FIDIC sub-clause
  numbering, and correctly parse to 0 clauses each — an honest, expected
  finding, not a defect, since ClauseParser was only ever built for
  numbered FIDIC sub-clauses. ContractPackageLoader scans
  settings.storage_root/"contracts" for .pdf/.txt files in sorted order,
  reuses app/ingestion/extraction.py's extract_pages() unmodified for PDFs
  (none exist yet — "no new PDFs" was honored), reads .txt files directly,
  and parses each with the existing, unmodified ClauseParser — no parsing
  logic duplicated. get_default_clause_repository() is
  functools.lru_cache(maxsize=1)'d, so the scan+parse happens at most once
  per process, never once per investigation request; InvestigationService
  now defaults to it instead of an empty ClauseRepository, while an
  explicitly injected clause_repository still fully overrides it (dependency
  injection preserved). Verified: 10 real sub-clauses (1.3, 3.3, 4.1, 8.4,
  8.7, 13.1, 13.3, 14.3, 14.7, 20.1) auto-loaded from disk in file order;
  get_by_number()/get_by_topic() work against the auto-loaded repository
  with no manual construction; a missing directory, an empty directory, a
  directory with only irrelevant files, and a .txt with no parseable
  headings all correctly yield an empty ClauseRepository with no exception;
  repeated get_default_clause_repository() calls and multiple
  InvestigationService() instances all share the exact same cached
  repository object (construct-once confirmed); an explicitly injected
  ClauseRepository still fully overrides the default. Ran a real
  POST /investigate through the live HTTP server with zero manual
  injection anywhere: Gemini correctly cited Sub-Clause 8.4 and 20.1 by
  name and reproduced the 28-day and 42-day periods verbatim from the
  auto-loaded contract package — the 42-day detail exists only in the new
  General Conditions text, nowhere in the V1 document corpus, proving the
  citation came from the auto-loaded clause, not the documents. Also
  observed, honestly, that the generic keyword "Contractor" (from
  primary_entities) matched 9 of the 10 real clauses in one test query — a
  known precision characteristic of the existing keyword-matching/entity-
  extraction machinery (Sprint 6 Tasks 04/06), not something this task
  introduced or is in scope to fix. Retrieval, InvestigationPlanner,
  RetrievalScorer, Timeline, PromptBuilder, ReasoningEngine, GeminiProvider,
  and API routes were not touched. GET /health, GET /search, and
  POST /investigate re-verified working; dataset confirmed unchanged
  (17 documents) after testing.

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
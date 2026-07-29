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

---

## 🚧 Current Milestone

Milestone 1 – Single-Tool Agent (search + read)

---

## 🎯 Next Task

Wrap search_chunks (and a read_document tool) for the Claude Agent SDK loop (Deliverable 5).

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
# ClaimTrace

ClaimTrace investigates natural-language construction-claims questions
against a project's ingested document corpus and contract package, and
returns a grounded, cited, evidence-based answer — not a chatbot summary,
but a deterministic evidence-gathering pipeline that consults an LLM
exactly once, at the end, to interpret evidence it already assembled.

Given a question and a project id, the backend plans an investigation,
iteratively gathers evidence through a control loop (reference expansion,
targeted re-retrieval, full document reads), narrows that evidence down to
what materially supports an answer, builds a chronology, pulls the
relevant contract clauses, and hands all of it to Google Gemini to produce
a final answer with verified citations.

## Current Status

**ClaimTrace Backend v1.0.1 — released.** See `RELEASE_NOTES_v1.0.1.md`
for the release summary and `BACKEND_V1_COMPLETE.md` for the full
architecture record.

- Backend (FastAPI + SQLAlchemy + PostgreSQL/pgvector + Gemini): complete,
  benchmarked, and independently RC1-validated.
- Frontend: **not started** — `frontend/` is currently empty. This is the
  next phase of work.
- Dataset: 3 independent projects, 12 investigation scenarios, 134
  documents, 12 approved benchmark questions.

## What ClaimTrace Is (and Isn't)

ClaimTrace is a **general-purpose evidence investigator with construction
vocabulary**, not a construction-claims rules engine. It never asserts
"this claim requires documents X, Y, Z" as ground truth — only what was
asked, what evidence was found, and what wasn't. Every step before the
final Gemini call is deterministic and independently testable: the system
decides *what* evidence to gather and *when to stop* without consulting an
LLM.

## Repository Structure

```
backend/                  FastAPI application (the entire implemented system)
  app/
    agent/                Investigation Agent, Investigation Loop, evidence
                           narrowing, remediation executors, prompt builder
    investigation/        Investigation Planner, timeline construction
    contracts/            Contract Intelligence (clause parsing, project-scoped retrieval)
    retrieval/             Hybrid (vector) retrieval over document chunks
    ingestion/             PDF extraction, chunking, embedding, storage
    llm/                    LLM provider abstraction + Gemini implementation
    db/                     SQLAlchemy models, session management
    api/routes/             /health, /search, /investigate
  storage/                 Ingested PDFs, extracted text, per-project contract
                           packages (gitignored — regenerated via ingestion scripts)

dataset/
  pdf/                     Generated scenario + contract PDFs (scenarios 1-12)
  scripts/                 Dataset generation, ingestion, and validation scripts
                           (scenario_XX_data.py, ingest_*.py, validate_*.py,
                           benchmarks.py, run_benchmarks_narrowed.py)

data/fictional_dataset/    Project 1 (DMV-7) source documents + ground-truth
                           answer key (00_GROUND_TRUTH_README.md)

frontend/                  Empty — Phase 5, not yet started

docs/archive/              Superseded planning documents, kept for history

IMPLEMENTATION_LOG.md      Full chronological development log (every
                           deliverable, decision, and fix — start here for
                           "why was it built this way", not "how do I run it")
BACKEND_V1_COMPLETE.md     Architecture record, current as of v1.0.1
RELEASE_NOTES_v1.0.1.md    v1.0 → v1.0.1 release summary
```

## How to Run the Backend

Requires: Python 3.11+, PostgreSQL with the `pgvector` extension, a Gemini
API key (free tier available at [Google AI Studio](https://aistudio.google.com/apikey)).

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DATABASE_URL (an empty Postgres database is enough) and GEMINI_API_KEY

uvicorn app.main:app --reload
# on startup the app creates the pgvector extension, all tables, and a
# default project automatically (app/db/init_db.py) — no manual schema
# step needed
```

**Important**: the server (and every dataset script) must be run with
`backend/` as the working directory — `STORAGE_ROOT` and `.env` are
resolved relative to the process's current working directory, not the
repo root.

Verify it's running:

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/search?project_id=2&q=defects+liability&top_k=3"
curl -X POST http://127.0.0.1:8000/investigate \
  -H "Content-Type: application/json" \
  -d '{"project_id": 2, "query": "Was the Contractor entitled to an extension of time?", "top_k": 10}'
```

## Available Datasets

| Project | Scenario(s) | Documents | Contract package |
|---|---|---|---|
| 1 — Delhi Metro Viaduct (DMV-7) | Pier P-42 reinforcement (original V0 scenario) | 17 | None |
| 2 — Nandira River Bridge (NRB-4) | 11 scenarios: EOT, monsoon delay, variation valuation, IPC certification, retention, notice validity, quality non-conformance, recovery programme, taking-over, concurrent delay, defects liability | 99 | NRB4 (13 clauses) |
| 3 — Kestrel Flyover Interchange (KFI-2) | Employer termination & final account | 18 | KFI2 (4 clauses) |

To regenerate or re-ingest any scenario, see the corresponding
`dataset/scripts/scenario_XX_data.py` + `ingest_*.py` pair. To validate a
scenario end-to-end against the live backend, run the matching
`dataset/scripts/validate_*.py`. To run the full benchmark suite:

```bash
cd backend && source .venv/bin/activate
PYTHONPATH="../dataset/scripts:$PYTHONPATH" python3 ../dataset/scripts/run_benchmarks_narrowed.py
```

## Roadmap

- **Phase 4 — Dataset Completion** ✅ Complete
- **Sprint 8 — Backend Patch v1.0.1** ✅ Complete (project-scoped Contract Intelligence)
- **Phase 5 — Frontend** ⬅ Next — build the user-facing app against the existing `POST /investigate` / `GET /search` contract
- **Phase 6 — Authentication & User Management** — accounts, access control, project-level permissions
- **Phase 7 — Deployment** — production packaging, load testing, monitoring

See `BACKEND_V1_COMPLETE.md` §10 for details, and `docs/archive/` for the
original pre-implementation planning document (superseded — kept for
historical reference only).

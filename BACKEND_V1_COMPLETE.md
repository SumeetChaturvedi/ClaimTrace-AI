# ClaimTrace Backend v1.0

Status: **Complete**
Scope: Backend only (FastAPI + SQLAlchemy + PostgreSQL/pgvector + Google Gemini)
This document is the technical closure record for ClaimTrace Backend Version 1.0.

---

## 1. Executive Summary

ClaimTrace Backend v1.0 investigates natural-language construction-claims
questions against a project's ingested document corpus and contract package,
and returns a grounded, cited, evidence-based answer.

Given a question and a project id, the backend plans an investigation,
iteratively gathers evidence through a deterministic control loop (not a
single retrieval pass), narrows that evidence down to what materially
supports an answer, builds a chronology and pulls relevant contract clauses,
and hands all of it to Google Gemini to produce a final answer with
citations. Every step before the single Gemini call is deterministic and
independently testable — the system decides *what* evidence to gather and
*when to stop* without ever consulting an LLM, and consults Gemini exactly
once per investigation, only at the end, to interpret evidence that was
already assembled.

The system has been validated end-to-end against a 71-document fictional
construction-dispute corpus (Dataset V2) using 9 approved benchmark
questions with real embeddings, real database retrieval, and real Gemini
calls — not synthetic or mocked evaluation. The current architecture
measurably improved answer-grounding recall over the original single-pass
design (0.65 → 0.706, see §5) while independently solving a citation-volume
problem the improved retrieval itself introduced (~59 citations → 15).

---

## 2. Final Architecture

The backend is organized as a pipeline of small, independently-testable
components, each with one clear responsibility. None of the components
below duplicate another's logic; each later-built component reuses the
earlier ones' public or private interfaces rather than re-implementing
them.

**Investigation Planner** (`app/investigation/`)
Converts a natural-language question into an `InvestigationPlan`: an
investigation type (e.g. delay, valuation, quality), a goal statement, an
expected answer shape, a list of primary entities the question centers on,
and the categories of contract topics and document types likely to be
relevant. Runs once, deterministically, before any retrieval.

**Hybrid Retrieval** (`app/retrieval/service.py`, `app/ingestion/`)
Semantic vector search over document chunks, using
`sentence-transformers/all-MiniLM-L6-v2` embeddings stored in PostgreSQL via
pgvector. Retrieval is project-scoped (a query against one project can never
surface another project's documents) and applies a retrieval diversity cap
so a single document cannot dominate a result set with many near-duplicate
chunks.

**Retrieval Scoring** (`app/retrieval/scoring.py`)
A deterministic scoring layer on top of raw cosine similarity: chunks whose
text contains one of the investigation plan's primary entities receive a
small, fixed relevance bonus. No learned re-ranking, no LLM involvement.

**Timeline Builder** (`app/investigation/timeline.py`)
Builds and formats a chronological narrative from the documents behind an
investigation's evidence, sorted by each document's recorded date. Produces
the pre-formatted text block the reasoning prompt's "Project Timeline"
section carries.

**Contract Intelligence** (`app/contracts/`)
Parses the project's contract package once per process (Contract Data,
Employer's Requirements, General Conditions, Particular Conditions — 10
parsed clauses in the current package) and retrieves the clauses relevant to
an investigation's contract-topic context. Fully separate from document
retrieval; clauses are matched by topic, not by semantic search over
narrative text.

**Investigation State** (`app/agent/investigation_state.py`)
The single, reused working-memory container for one investigation: the
plan, accumulated evidence, visited chunk/document ids, fully-read document
ids, followed reference strings, retrieved contract clauses, a complete
search-history trail, an iteration counter, and a stopping reason. Every
other component below reads from and writes to one shared instance of this
— there is no second state type anywhere in the system.

**Evidence Sufficiency Assessor** (`app/agent/evidence_sufficiency.py`)
A four-stage, strictly-ordered deterministic decision model: (1) are there
document references named in evidence text that haven't been followed yet,
(2) are there contract clauses named in evidence text that weren't
retrieved, (3) is entity coverage and confident-evidence count adequate, (4)
does one dominant document lack any determination/outcome content. Returns
either "sufficient" or exactly one recommended remediation — never more than
one at a time.

**Investigation Agent** (`app/agent/investigation_agent.py`)
The orchestration skeleton for one investigation's *initial* pass: creates
the plan, retrieves contract clauses, performs one retrieval pass, builds
evidence and a first timeline, and asks the Assessor whether that's already
enough. Performs no remediation itself.

**Reference Expansion** (`app/agent/reference_expansion_executor.py`,
`app/agent/tools.py`)
The first remediation strategy: resolves document references named in
evidence text by a one-hop, deterministic metadata join
(`find_related_documents()`), project-scoped and filtered against
project-wide boilerplate tokens (a contract number or project code that
appears in nearly every document is not a meaningful cross-document
reference). Duplicate-prevention and a configurable per-call budget (max
references processed, max documents added, max evidence added) are
enforced so one call cannot ingest an unbounded share of the corpus.

**Focused Retrieval** (`app/agent/focused_retrieval_executor.py`)
The second remediation strategy: one additional, targeted retrieval pass
using a deterministically-constructed query (the original question, the
gap-specific missing entities, the investigation type, and the Assessor's
own stated reason) — reusing the same retrieval pipeline Hybrid Retrieval
already provides, not a new search algorithm.

**Full Document Read** (`app/agent/full_document_read_executor.py`)
The third remediation strategy: opens every already-chunked, already-stored
passage of a single document the Assessor identified as dominant-but-
inconclusive, rather than relying on whatever partial chunk set the
original retrieval pass happened to surface.

**Investigation Loop** (`app/agent/investigation_loop.py`)
The deterministic controller tying the previous six components together:
assess → if sufficient, stop → otherwise dispatch exactly one remediation →
reassess → repeat, until sufficiency, a configured maximum iteration count,
no further progress, or an unsupported/failed remediation is reached. Seven
distinct, explicit stopping reasons are recorded on every run. Never
introduces looping logic into the components it orchestrates.

**Evidence Narrowing** (`app/agent/evidence_narrowing.py`)
Runs after the Investigation Loop completes and before the prompt is built.
Deduplicates exact-text repeats, merges literally-overlapping chunks from
the same document into single combined passages, and ranks the remainder by
(real-retrieval-vs-fixed-confidence, decisive-content, confidence) to cap
both per-document and total citation counts — turning a real ~59-item
evidence set into a bounded, high-signal citation list without any LLM call
or semantic re-ranking.

**Prompt Builder** (`app/agent/prompt_builder.py`)
The only place prompt text is constructed. Assembles the question, retrieved
contract clauses, evidence excerpts, and the formatted timeline into a
provider-agnostic prompt, plus a fixed system instruction constraining the
model to the supplied evidence only.

**Gemini Reasoning** (`app/agent/reasoning.py`, `app/llm/gemini_provider.py`)
`ReasoningEngine` ranks evidence by confidence, sends the prompt to the
configured `LLMProvider` (Gemini `flash-lite` by default, pluggable via a
provider interface), and — before returning — passes the resulting
citations through an existing, independent database well-formedness check
(`verify_citations()`, unrelated to Evidence Narrowing) as a final
integrity gate. The LLM only ever produces the answer's natural-language
text; citations are always built deterministically upstream, never parsed
out of the model's response.

---

## 3. Production Investigation Flow

```
User Question
      │
      ▼
Investigation Planner        (InvestigationAgent's first step)
      │
      ▼
Investigation Loop           (initial retrieval + Reference Expansion /
      │                       Focused Retrieval / Full Document Read,
      │                       exactly one remediation per iteration)
      ▼
Evidence Collection          (InvestigationState.evidence, timeline,
      │                       retrieved contract clauses)
      ▼
Evidence Narrowing           (dedup, merge, rank, cap → ~15 citations)
      │
      ▼
Timeline Construction        (rebuilt from the loop's full evidence,
      │                       independent of narrowing)
      ▼
Contract Intelligence        (retrieved clauses carried through unchanged)
      │
      ▼
Prompt Builder
      │
      ▼
Reasoning Engine
      │
      ▼
Gemini
      │
      ▼
Final Investigation Response  (answer, citations, reasoning_steps)
```

This is the literal, current body of `InvestigationService.investigate()` —
not an aspirational diagram. Gemini is called exactly once, at the last
step; nothing upstream of it depends on an LLM decision.

---

## 4. Dataset Summary

| | |
|---|---|
| **Dataset V1** | Delhi Metro Viaduct, Package DMV-7 (fictional) — 17 documents, frozen reference dataset |
| **Dataset V2** | Nandira River Bridge Project, Package NRB-4 (fictional) — 71 documents, 232 indexed chunks, across 9 investigation scenarios |
| **Contract package** | 4 documents (Contract Data, Employer's Requirements, General Conditions, Particular Conditions) — 10 parsed contract clauses, auto-ingested once per process |
| **Benchmark corpus** | 9 approved benchmark questions (`dataset/scripts/benchmarks.py`), one per Dataset V2 scenario, each with a documented expected outcome, expected decisive documents, and expected clause hints |

Dataset V2 scenarios span extension-of-time disputes, variation valuation,
interim payment certification, retention interpretation, notice-of-
dissatisfaction validity, quality non-conformance, recovery-programme
credibility, and practical-completion/taking-over — a deliberately varied
set of construction-claims question types.

---

## 5. Benchmark Results

Real Gemini calls, same 9 questions, three architecture states:

| Metric | Original single-pass | Investigation Loop (unnarrowed) | **v1.0 (Loop + Narrowing)** |
|---|---|---|---|
| Average recall vs. expected decisive docs | 0.65 | 0.806 | **0.706** |
| Benchmarks passing (recall ≥ 0.5) | 7 / 9 | 8 / 9 | **8 / 9** |
| Average citations per answer | 10.0 | 59.2 | **15.0** |
| Average documents represented in citations | 7.9 | 27.9 | 13.6 |
| Average prompt size (user prompt) | 16,778 chars | 35,460 chars | 19,278 chars |
| Average latency per investigation | 2.36 s | 3.16 s | 2.39 s |
| Average loop iterations | 1 (no loop) | 5.0 | 5.0 |

**Improvements over the original architecture:**
- Recall improved from 0.65 to 0.706 (+0.056) and pass count from 7/9 to
  8/9, with the Investigation Loop's raw, unnarrowed retrieval reaching
  0.806 before Evidence Narrowing traded some of that back for a ~75%
  citation-volume reduction.
- Citation volume reduced from a peak of ~59 (the Loop's raw evidence
  output) to a consistent 15 — within the intended 8–15 target — without
  regressing below the *original* pre-Loop baseline's recall or pass rate.
- Prompt size roughly halved relative to the unnarrowed Loop output (35,460
  → 19,278 chars), and latency returned to essentially the original
  single-pass level (2.39s vs. 2.36s) despite five retrieval iterations
  running underneath it.

One benchmark (quality non-conformance, NCR-001-QUALITY) remains below the
0.5 recall threshold in both the Loop and v1.0 configurations; this is a
confirmed iteration-budget effect (see §7), not a narrowing or retrieval
defect — the same three missing documents are found reliably when the
iteration budget is raised for that scenario.

---

## 6. Backend Capabilities

ClaimTrace Backend v1.0 can:

- Investigate a natural-language construction-claims question against a
  specific project's document corpus.
- Iteratively gather evidence across multiple remediation strategies
  (reference expansion, targeted re-retrieval, full document reads) rather
  than relying on a single retrieval pass.
- Decide, deterministically and without an LLM, when enough evidence has
  been gathered or when further gathering would not help.
- Reconstruct a chronological timeline from the documents an investigation
  actually touched.
- Retrieve and reason over contract clauses relevant to the investigation's
  topic.
- Narrow a large raw evidence set down to the subset that materially
  supports an answer, deterministically, before any citation is shown to a
  user.
- Produce an explainable trail for every investigation: which remediation
  ran on which iteration, how much evidence it added, why it stopped, and
  why each citation was kept or discarded.
- Run entirely deterministically up to the single Gemini call — identical
  input reliably produces identical evidence-gathering behaviour.
- Operate against a benchmarked, measured evaluation suite rather than
  informal or anecdotal testing.
- Serve investigation results through a stable, unchanged API contract
  (`answer`, `citations`, `reasoning_steps`) regardless of how much internal
  evidence-gathering machinery runs underneath it.

---

## 7. Known Limitations

- **Clause Top-up is not implemented.** `RemediationType.CLAUSE_TOP_UP`
  exists in the vocabulary and `EvidenceSufficiencyAssessor` can recommend
  it, but no executor exists for it — the Investigation Loop terminates
  safely (`stopping_reason="unsupported_remediation"`) if it is ever
  reached. In practice, a real extended-iteration trace showed the Loop
  reaching a state naming 6 genuine, unretrieved contract clauses via this
  path, but the Loop's own other stopping conditions (`same_remediation_
  no_progress`) were reached one step earlier in that same trace, so this
  gap has not yet been forced by real benchmark behaviour at default
  settings. Deferred to v1.1.
- **The default iteration budget (5) does not reach full convergence for
  every scenario.** Reference Expansion on this corpus routinely needs
  10–15+ iterations to exhaust a richly cross-referenced document set. One
  benchmark scenario (NCR-001-QUALITY) stays at 0.25 recall at the default
  budget; raising `InvestigationLoopConfig.max_iterations` to 20 was
  confirmed, in testing, to find all of that scenario's expected documents.
  The default was kept at 5 as specified; this is a known, available tuning
  lever, not an unresolved defect.
- **Evidence Narrowing's citation cap (15) is reached on every real
  benchmark investigation.** Real Dataset V2 investigations consistently
  surface more evidence that ranks as "worth keeping" than the cap allows,
  even after merging overlapping chunks. The cap is doing real, active
  work rather than sitting unused.
- **Remediation executors' fixed confidence values are not calibrated
  against real retrieval similarity.** Reference Expansion (0.75) and Full
  Document Read (0.8) assign the same confidence to everything they find,
  which is not directly comparable to genuine cosine-similarity scores
  (observed as low as ~0.3 for real, correct matches on this embedding
  model). Evidence Narrowing's ranking accounts for this by treating
  "real retrieval vs. remediation" as its primary signal rather than
  comparing the raw numbers directly, but the underlying confidence values
  themselves remain uncalibrated.
- **Evidence Narrowing's confidence floor is effectively disabled by
  default** (`min_confidence_to_retain=0.0`), because a nonzero default was
  confirmed, against the real benchmark, to discard genuinely correct
  low-scoring matches on this embedding model. The mechanism remains
  available and configurable for a future corpus or embedding model where
  it would do useful work.
- **Citation Verification (`verify_citations()`) checks database
  well-formedness only.** It confirms a citation is real, non-duplicate,
  and internally consistent; it does not (and was never scoped to)
  independently verify that a cited excerpt textually supports the specific
  claim the model made about it.

---

## 8. Planned for Backend v1.1

- **Clause Top-up remediation executor** — the fourth remediation strategy
  named in the original architecture, not yet built. Whether to build it
  should be revisited if a future benchmark run genuinely forces the
  Investigation Loop to stop on `unsupported_remediation` in practice,
  strengthening the case established in §7.
- **Iteration budget tuning or an adaptive stopping heuristic** — informed
  by the gap between the default (5) and the iteration count actually
  needed for full convergence (10–15+) observed during this phase's
  testing.
- **Confidence calibration for remediation executors** — replacing
  Reference Expansion's and Full Document Read's fixed confidence values
  with something more comparable to genuine retrieval similarity, so
  Evidence Narrowing's ranking can rely on confidence more directly.

---

## 9. Production Readiness

- **Architecturally complete**: every component named in the approved
  Investigation Agent architecture is implemented and wired into the
  production path, with the single, disclosed exception of Clause Top-up
  (§7/§8).
- **Benchmark validated**: the full 9-question Dataset V2 benchmark has
  been run against real embeddings, real retrieval, and real Gemini calls
  at each major architectural milestone (original single-pass, integrated
  Loop, Loop + Evidence Narrowing), with results compared and reported at
  every stage.
- **Regression tested**: `GET /health`, `GET /search`, and
  `POST /investigate` were verified after every change across this entire
  development arc, most recently after Evidence Narrowing's integration;
  the API response contract has not changed.
- **Suitable for internal production use**, with the known limitations in
  §7 understood and accepted: default iteration tuning and the absence of
  Clause Top-up are disclosed, non-blocking gaps rather than defects.
  Backend v1.0 has not been evaluated under production-scale concurrent
  load, and no monitoring/alerting has been established — both are
  reasonable prerequisites before unmonitored external production traffic,
  not claims this document makes.

---

## 10. Future Roadmap

**Phase 4 — Dataset Completion**
Expand or diversify the benchmark corpus beyond Dataset V1/V2 as needed to
continue validating backend behaviour against new claim types.

**Phase 5 — Frontend**
Build the user-facing application against the existing, stable
`POST /investigate` / `GET /search` API contract.

**Phase 6 — Authentication & User Management**
Introduce user accounts, access control, and project-level permissions
ahead of any multi-tenant or external deployment.

**Phase 7 — Deployment**
Package, monitor, and operate the backend in a real production environment
— including the load testing and monitoring called out as outstanding in
§9.

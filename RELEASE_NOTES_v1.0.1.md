# ClaimTrace Backend v1.0.1 — Release Notes

**Release tag**: `v1.0.1`
**Status**: Released — passed full Release Candidate (RC1) validation
**Scope**: Backend only (FastAPI + SQLAlchemy + PostgreSQL/pgvector + Google Gemini)

This document summarizes the v1.0.1 release. For the full architecture
record, see `BACKEND_V1_COMPLETE.md`; for the complete chronological
development history, see `IMPLEMENTATION_LOG.md`.

---

## Release Highlights

- **Multi-project dataset**: expanded from 1 project (Dataset V2, 9
  scenarios) to **3 independent projects, 12 scenarios, 134 documents** —
  including Project 3 (Kestrel Flyover Interchange, KFI-2), a genuinely
  separate project (own contract, own contractor/engineer/employer, own
  document numbering) built specifically to stress-test project isolation
  under a new claim category: employer termination and final account.
- **Contract Intelligence is now project-scoped.** Fixed the only gap in
  v1.0's otherwise-complete project isolation: contract clause retrieval
  previously drew from a single process-wide repository built from every
  contract package on disk, so one project's investigation could retrieve
  another project's clauses. Each project now resolves clauses only from
  its own `storage/contracts/{project_id}/` package.
- **Full project isolation now holds on every axis** — document retrieval,
  search, contract clauses, and full investigations — verified
  bidirectionally across all 3 projects, including under real
  singleton-service, sequential-request conditions (the exact production
  shape that caused the original leak).
- **Release Candidate (RC1) sign-off completed**: independent end-to-end
  validation across repository integrity, database state, all 14
  production components, project isolation, the full dataset, the
  complete benchmark suite, and live API behavior. Recommendation: **READY
  FOR RELEASE**.

---

## Benchmark Summary

Full 12-question suite, real Gemini calls, real embeddings, real DB
retrieval — no mocks:

| Metric | Result |
|---|---|
| Total benchmark questions | 12 (11 on Project 2, 1 on Project 3) |
| Average recall vs. expected decisive documents | 0.696 |
| Pass rate (recall ≥ 0.5) | 10 / 12 |
| Gemini errors / exceptions | 0 / 0 |
| Average / max latency per investigation | 2.16 s / 8.3 s |
| Citations before → after narrowing | 82–85 → 15 (Project 2); 31 → 15 (Project 3) |
| Cross-project contract clause leakage | **0 / 12** (was 8 / 12 before this release) |

The 2 sub-0.5 cases (NCR-001-QUALITY 0.25, CONCURRENT-DELAY-P4 0.4) are a
pre-existing, already-documented `max_iterations=7` budget limitation —
confirmed via extended-iteration testing to find all expected documents
with a larger budget — not a new defect. Every one of the original 9
benchmark questions' recall, citation counts, and iteration behavior is
**byte-for-byte identical** to their v1.0 values; the only measured change
across this release is the elimination of cross-project clause leakage.

---

## Major Changes: v1.0 → v1.0.1

| Area | v1.0 | v1.0.1 |
|---|---|---|
| Projects | 1 active with a contract package (Project 2) | 3, each independently isolated |
| Documents | 88 (Dataset V1 + V2) | 134 |
| Benchmark questions | 9 | 12 |
| Contract Intelligence | Single process-wide `ClauseRepository`, built from every package on disk | Project-scoped: `get_clause_repository(project_id)`, one package per project |
| Project isolation | Document/search isolation only | Document, search, **and contract clause** isolation |

**Files changed to ship the fix** (the smallest possible correction — no
redesign of `ClauseParser`, `ClauseRepository`, `ClauseRetriever`, Prompt
Builder, Gemini, or the Investigation Loop):
`backend/app/contracts/ingestion.py`, `backend/app/agent/service.py`,
`backend/app/agent/investigation_agent.py`, plus a pure data move
(`storage/contracts/{2,3}/`).

---

## Known Limitations (carried forward from v1.0, unchanged)

- **Clause Top-up remediation is not implemented** — the vocabulary and
  decision logic exist, but no executor does; the Investigation Loop stops
  safely if ever reached. Deferred to v1.1.
- **Default iteration budget (7) does not reach full convergence for every
  scenario** — a known, available tuning lever (confirmed: raising it
  finds all expected documents), not an unresolved defect.
- **Evidence Narrowing's citation cap (15) is reached on every real
  investigation** — doing real, active work rather than sitting unused.
- **Remediation executors' fixed confidence values are uncalibrated**
  against real retrieval similarity.
- **Citation Verification checks database well-formedness only** — it
  does not independently verify that a cited excerpt textually supports
  the specific claim made about it.
- Not evaluated under production-scale concurrent load; no
  monitoring/alerting established yet (Phase 7).

None of the above are new to this release — all were disclosed in
`BACKEND_V1_COMPLETE.md` §7 for v1.0 and remain accurate.

---

## Release Recommendation

**READY FOR RELEASE.** RC1 validation found no functional defects, zero
regressions, and confirmed the intended fix (contract clause isolation)
took effect cleanly. Recommend tagging this state as **`v1.0.1`**, the
permanent backend release baseline, and proceeding to Phase 5 (Frontend)
against the existing, stable `POST /investigate` / `GET /search` API
contract.

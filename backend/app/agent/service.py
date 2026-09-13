"""Orchestration entry point for the Investigation Engine.

InvestigationService is the seam between the API layer and future
retrieval/LLM integrations. It orchestrates the pipeline — validate, plan,
search, build evidence, package, reason, respond — but contains no reasoning
logic itself; that lives entirely in ReasoningEngine (app/agent/reasoning.py),
including what to do when no evidence is found. This keeps the concerns
separable: app/investigation/ knows how an investigation should be
approached, tools.py/this module know how to gather evidence,
investigation_package.py packages it up model-agnostically, reasoning.py
knows what it means.

Investigation Loop integration (Phase 3 Task 07): investigate() no longer
performs a single retrieval pass itself. It delegates evidence-gathering
entirely to InvestigationLoop (app/agent/investigation_loop.py, Phase 3
Task 06) — which itself orchestrates InvestigationAgent's initial pass plus
the three remediation executors (Reference Expansion, Focused Retrieval,
Full Document Read) against EvidenceSufficiencyAssessor's decisions — then
packages the loop's final InvestigationState exactly as the old single-pass
code packaged one search_documents() call's citations. None of those reused
components are modified here; investigate() only wires them together. The
production flow is now: Investigation Planner -> Investigation Loop ->
Prompt Builder -> Reasoning Engine -> Gemini, matching the approved Task 07
architecture. Imports of investigation_loop/investigation_agent are local to
__init__ (not module-level) because InvestigationAgent itself imports
InvestigationService (Task 02's private-method-reuse pattern) to call this
class's own planner/contract-clause/evidence/timeline helpers — a
module-level import here would be circular; deferring it to __init__ (by
which point this module has already finished defining InvestigationService)
resolves that without changing either module's public shape.

Timeline refresh (Phase 3 Task 07, a genuine integration defect found and
fixed here — see investigate() below): none of the three remediation
executors update InvestigationState.timeline_context (only
InvestigationAgent's initial pass does, once, before any remediation runs).
Left alone, a loop that grows evidence far beyond the initial pass would
package a timeline reflecting only that small initial document set,
silently stale relative to the documents Gemini's evidence section actually
shows it. investigate() now rebuilds the timeline once, after the loop
completes, from the final evidence's full citation set — reusing the
existing, unmodified _build_timeline_context() below with different input,
not a new timeline implementation.

Evidence construction: Citation carries the actual matched chunk text
(citation.chunk_text, populated by search_documents() straight from the
semantic search result), so excerpt/surrounding_context are built from that
real retrieved passage, not reconstructed from the full document. Reading
the full document via read_document() is only a fallback for the rare case
where chunk_text is unavailable on a citation, and is otherwise reserved for
future context-expansion (e.g. reading beyond a chunk's boundaries) that
isn't implemented yet.

Investigation planning: create_plan() runs before search, and the resulting
InvestigationPlan is passed into search_documents() (see app/agent/tools.py),
which converts it to a RetrievalContext and forwards it into retrieval —
this is now live: the plan's primary_entities feed a deterministic
entity-match scoring bonus (app/retrieval/scoring.py) during real searches.
It still doesn't shape the query text itself, evidence construction,
packaging, or reasoning, and is never exposed on InvestigationResponse.

Timeline context (Sprint 5 Task 05): after evidence is built, this module
also fetches the Document rows for this investigation's retrieved document
ids (tools.get_documents() — not a new retrieval step, just looking up
documents search_documents() already surfaced), builds a chronology from
them via TimelineBuilder, and formats it via TimelineFormatter. The
resulting text is carried into InvestigationPackage.timeline_context, which
PromptBuilder appends to the reasoning prompt as a clearly separated
section. No timeline logic lives here — this only calls the existing
app/investigation/timeline.py components in sequence.

Contract clause retrieval (Sprint 6 Task 07; exposed to reasoning in Task
08): right after the InvestigationPlan is created, InvestigationAgent (the
only caller — see below) builds a ContractContext from it
(ContractContextBuilder) and retrieves matching ContractClause objects via
a ClauseRetriever scoped to that request's own project (Sprint 8 Task 03 —
see _clause_retriever_for_project() below). The result is carried into
InvestigationPackage.retrieved_clauses, which PromptBuilder now appends to
the reasoning prompt (Sprint 6 Task 08).

Contract package auto-ingestion (Dataset V2 Implementation Task 01) and
project scoping (Sprint 8 Task 03, Backend Patch v1.0.1): each project's
own ClauseRepository comes from
app.contracts.ingestion.get_clause_repository(project_id) — memoized per
project_id, so each project's contract package (storage/contracts/
{project_id}/) is scanned and parsed at most once per process, never once
per investigation request. This replaces the earlier, pre-v1.0.1
process-wide get_default_clause_repository(), which built exactly one
ClauseRepository from every contract package under storage/contracts/
regardless of project — a genuine cross-project leakage bug found during
Phase 4 Scenario 12 (a second, independent project's contract package made
the leak observable for the first time). InvestigationService itself no
longer resolves or holds a single fixed ClauseRepository/ClauseRetriever
at construction time (it cannot: no project_id exists yet at
__init__-time, and this service is constructed once and reused for the
process lifetime — see app/api/routes/investigate.py); instead,
_clause_retriever_for_project(project_id) resolves one per request, called
from InvestigationAgent.run() with that request's own project_id.
Explicitly injecting a clause_repository at construction (e.g. for a
controlled test/validation run) still overrides this entirely, for every
project, exactly as before.
"""

from typing import TYPE_CHECKING

from app.agent import tools
from app.agent.investigation_package import InvestigationPackageBuilder
from app.agent.models import Citation, Evidence, InvestigationRequest, InvestigationResponse, TimelineEntry
from app.agent.reasoning import ReasoningEngine
from app.contracts.clause_retrieval import ClauseRetriever
from app.contracts.context_builder import ContractContextBuilder
from app.contracts.ingestion import get_clause_repository
from app.contracts.repository import ClauseRepository
from app.contracts.search import ClauseSearchService
from app.investigation import InvestigationPlanner
from app.investigation.timeline import TimelineBuilder, TimelineEvent, TimelineFormatter

if TYPE_CHECKING:
    # Type-checking only, to avoid the module-level circular import
    # explained above investigate() -- InvestigationLoop's own import chain
    # reaches back into this module.
    from app.agent.evidence_narrowing import EvidenceNarrower
    from app.agent.investigation_loop import InvestigationLoop

# Excerpt length within a matched chunk (or, in the read_document() fallback,
# within the truncated full-document prefix). Picked as a reasonable default
# for short letter-style documents, not tuned against any evaluation.
EXCERPT_CHARS = 280
# Used only in the read_document() fallback path — chunk_text itself is
# already a bounded unit from chunking.py and isn't truncated further.
CONTEXT_CHARS = 800


class InvestigationService:
    """Orchestrates an investigation: validate -> search -> build evidence ->
    package -> delegate to ReasoningEngine -> respond. Contains no reasoning
    logic of its own — not even the "no evidence found" case, which
    ReasoningEngine decides. Later: will drive the full agent loop (plan ->
    search -> read -> follow references -> verify citations -> answer)
    described in PROJECT_PLAN.md Part C step 7 and Part D, likely by
    ReasoningEngine growing rather than this class."""

    def __init__(
        self,
        reasoning_engine: ReasoningEngine | None = None,
        package_builder: InvestigationPackageBuilder | None = None,
        planner: InvestigationPlanner | None = None,
        timeline_builder: TimelineBuilder | None = None,
        timeline_formatter: TimelineFormatter | None = None,
        clause_repository: ClauseRepository | None = None,
        contract_context_builder: ContractContextBuilder | None = None,
        investigation_loop: "InvestigationLoop | None" = None,
        evidence_narrower: "EvidenceNarrower | None" = None,
    ) -> None:
        self._reasoning_engine = reasoning_engine or ReasoningEngine()
        self._package_builder = package_builder or InvestigationPackageBuilder()
        self._planner = planner or InvestigationPlanner()
        self._timeline_builder = timeline_builder or TimelineBuilder()
        self._timeline_formatter = timeline_formatter or TimelineFormatter()
        # Sprint 8 Task 03 (Backend Patch v1.0.1): no single ClauseRepository
        # is resolved here anymore -- no project_id is known at construction
        # time, and this service is a process-wide singleton (constructed
        # once, reused for every request; see
        # app/api/routes/investigate.py's get_investigation_service()), so a
        # repository fixed here would necessarily be shared, and therefore
        # wrong, for every project except whichever's package happened to be
        # resolved first. An explicitly injected clause_repository is still
        # honored, but now applies uniformly across every project_id (the
        # same override semantics it always had) rather than being the sole
        # default; see _clause_retriever_for_project() below, which is
        # called per-request, once request.project_id is actually known.
        self._injected_clause_repository = clause_repository
        self._contract_context_builder = contract_context_builder or ContractContextBuilder()

        if investigation_loop is not None:
            self._investigation_loop = investigation_loop
        else:
            # Local imports: see the module docstring's "Investigation Loop
            # integration" note for why these can't be module-level imports.
            from app.agent.focused_retrieval_executor import FocusedRetrievalExecutor
            from app.agent.investigation_agent import InvestigationAgent
            from app.agent.investigation_loop import InvestigationLoop

            # `service=self` / `service=self` below: InvestigationAgent and
            # FocusedRetrievalExecutor each already accept an injectable
            # InvestigationService purely as a source of reusable private
            # methods (planner, contract context/clause retrieval, evidence
            # assembly — Task 02/04's private-method-reuse pattern). Passing
            # this same, already-fully-configured instance avoids
            # constructing a second, redundant InvestigationService (and,
            # transitively, a second ReasoningEngine/GeminiProvider) purely
            # to reach those methods.
            self._investigation_loop = InvestigationLoop(
                agent=InvestigationAgent(service=self),
                focused_retrieval_executor=FocusedRetrievalExecutor(service=self),
            )

        # Local import for the same reason as above: evidence_narrowing.py
        # imports CONTEXT_CHARS/EXCERPT_CHARS/_truncate/_clamp_confidence
        # from this module, so a module-level import here would be circular.
        from app.agent.evidence_narrowing import EvidenceNarrower

        self._evidence_narrower = evidence_narrower if evidence_narrower is not None else EvidenceNarrower()

    def _clause_retriever_for_project(self, project_id: int) -> ClauseRetriever:
        """Return a ClauseRetriever scoped to `project_id`'s own contract
        package (Sprint 8 Task 03 / Backend Patch v1.0.1) — the project-aware
        replacement for the single, fixed self._clause_retriever this method
        removed from __init__. Called once per request, from
        InvestigationAgent.run() (the sole call site of contract clause
        retrieval — see the module docstring), with that request's own
        request.project_id, so a request against project 2 can never see
        project 3's clauses or vice versa.

        If a clause_repository was explicitly injected at construction (the
        same override this class has always supported, e.g. for a
        controlled test/validation run), that fixed repository is used for
        every project_id, exactly as it was before this task — project
        scoping only applies to the default, disk-backed path. Otherwise,
        get_clause_repository(project_id) resolves (and memoizes) that
        project's own repository, built solely from
        storage/contracts/{project_id}/."""
        repository = (
            self._injected_clause_repository
            if self._injected_clause_repository is not None
            else get_clause_repository(project_id)
        )
        return ClauseRetriever(repository, ClauseSearchService(repository))

    async def investigate(self, request: InvestigationRequest) -> InvestigationResponse:
        """Run an investigation for `request`: create an InvestigationPlan,
        gather evidence via the Investigation Loop (initial retrieval plus
        deterministic remediation — Reference Expansion, Focused Retrieval,
        Full Document Read — until EvidenceSufficiencyAssessor reports
        sufficiency or the loop's own stopping conditions fire), assemble an
        InvestigationPackage from the question and the loop's final
        evidence/timeline/clauses, hand it to ReasoningEngine, and map its
        ReasoningResult onto InvestigationResponse.

        The Investigation Loop plans internally (InvestigationAgent creates
        the InvestigationPlan as its own first step) and retrieves/builds
        evidence, clauses, and an initial timeline via the same components
        this method used to call directly — see InvestigationLoop and
        InvestigationAgent for exactly what runs and in what order. This
        method's own job is now: run the loop, refresh the timeline against
        everything the loop actually gathered (see the module docstring's
        "Timeline refresh" note), narrow the loop's full evidence set down
        to what materially supports the answer (Sprint 8 Task 01 — see
        evidence_narrowing.py), package, and reason — no retrieval,
        evidence-building, or clause-retrieval logic lives here anymore.

        Evidence narrowing (Sprint 8 Task 01): the Investigation Loop
        routinely gathers 50+ evidence items across its remediation
        iterations, but not all of it materially supports the answer —
        left unfiltered, every one of those items becomes a citation on
        InvestigationResponse. EvidenceNarrower runs here, after the loop
        and before packaging, so PromptBuilder and ReasoningEngine only
        ever see the narrowed set — no changes were needed to either.
        Timeline and contract clauses are built from the loop's FULL
        evidence (not the narrowed set): narrowing is specifically a
        citation/evidence-noise concern, not a chronology or contract-topic
        concern, so neither should be scoped down by it."""
        self._validate(request)

        loop_result = self._investigation_loop.run(request)
        state = loop_result.state

        # Timeline refresh (see module docstring): state.timeline_context
        # reflects only InvestigationAgent's initial pass. Rebuild it from
        # the loop's complete, final evidence set using the existing,
        # unmodified _build_timeline() — not a new implementation, just
        # called again with a fuller citation list. Built from the FULL
        # evidence, before narrowing (see docstring above).
        #
        # Phase 4 (Timeline Productization): the same final_events list also
        # becomes InvestigationResponse.timeline, via _build_timeline_entries,
        # which attaches each event's own real citations from this same
        # final_citations list — no second retrieval, no fabricated data,
        # just the structured TimelineEvent list this module already builds,
        # exposed instead of being thrown away after formatting to text.
        final_citations = [item.citation for item in state.evidence]
        final_events = self._build_timeline(final_citations)
        final_timeline_context = self._timeline_formatter.format(final_events)
        final_timeline = self._build_timeline_entries(final_events, final_citations)

        narrowing_result = self._evidence_narrower.narrow(state.evidence)

        package = self._package_builder.build(
            request.query,
            narrowing_result.retained_evidence,
            timeline_context=final_timeline_context,
            retrieved_clauses=list(state.retrieved_clauses),
        )

        result = self._reasoning_engine.reason(package)

        return InvestigationResponse(
            answer=result.answer,
            citations=result.supporting_evidence,
            reasoning_steps=result.reasoning_steps,
            timeline=final_timeline,
            # Phase 5 (Contract Intelligence Productization): state.retrieved_clauses
            # is the same list already handed to the package builder above (and,
            # via PromptBuilder, already shown to Gemini) — exposed here instead of
            # being discarded, same "capture what already exists" approach as
            # Phase 4's timeline. Never narrowed (narrowing is an evidence/citation
            # concern only — see the module docstring), never re-retrieved.
            contract_clauses=list(state.retrieved_clauses),
        )

    def _build_evidence(self, citations: list[Citation]) -> list[Evidence]:
        """Build one Evidence object per citation. Prefers the citation's own
        matched chunk_text; falls back to reading the full source document
        only if chunk_text is genuinely unavailable. Filename lookups (and,
        in the fallback case, document reads) are cached per document_id
        within this call, since multiple citations commonly point at the
        same (multi-chunk) document."""
        filename_cache: dict[int, str] = {}
        full_text_cache: dict[int, str] = {}
        evidence: list[Evidence] = []

        for citation in citations:
            document_id = citation.document_id
            if document_id not in filename_cache:
                filename_cache[document_id] = tools.get_document_filename(document_id)

            if citation.chunk_text:
                surrounding_context = citation.chunk_text.strip()
                excerpt = _truncate(surrounding_context, EXCERPT_CHARS)
            else:
                if document_id not in full_text_cache:
                    full_text_cache[document_id] = tools.read_document(document_id)
                surrounding_context = _truncate(full_text_cache[document_id], CONTEXT_CHARS)
                excerpt = _truncate(surrounding_context, EXCERPT_CHARS)

            evidence.append(
                Evidence(
                    citation=citation,
                    document_id=document_id,
                    document_name=filename_cache[document_id],
                    excerpt=excerpt,
                    surrounding_context=surrounding_context,
                    confidence=_clamp_confidence(citation.relevance_score),
                    metadata={},
                )
            )

        return evidence

    def _build_timeline(self, citations: list[Citation]) -> list[TimelineEvent]:
        """Fetch the (deduplicated) Document rows behind `citations` only —
        never the whole corpus — and hand them to TimelineBuilder (which
        sorts by document_date, unchanged from Sprint 5 Task 01). The shared
        first step behind both _build_timeline_context (LLM prompt text,
        used by InvestigationAgent's initial pass) and _build_timeline_entries
        (the structured, citation-linked timeline exposed on
        InvestigationResponse — Phase 4)."""
        document_ids = sorted({citation.document_id for citation in citations})
        documents = tools.get_documents(document_ids)
        return self._timeline_builder.build(documents)

    def _build_timeline_context(self, citations: list[Citation]) -> str:
        """Build a formatted chronology from the documents behind
        `citations` via TimelineFormatter (unchanged from Sprint 5 Task 04).
        Returns "" if there are no citations, same as TimelineFormatter
        already does for an empty timeline."""
        return self._timeline_formatter.format(self._build_timeline(citations))

    def _build_timeline_entries(self, events: list[TimelineEvent], citations: list[Citation]) -> list[TimelineEntry]:
        """Phase 4 (Timeline Productization): attach each event's own real
        citations — the same `citations` list its document came from, never a
        new lookup — so the frontend can drill from a timeline event straight
        into the exact cited passage via the existing Inspector/Source Viewer.
        A document with multiple citations in this investigation keeps all of
        them; nothing is fabricated for a document with none (can't happen by
        construction, since `events` is itself built only from these same
        citations' document ids, but this doesn't assume that and simply
        returns an empty list for such a case rather than erroring)."""
        return [
            TimelineEntry(
                document_id=event.document_id,
                document_date=event.document_date,
                document_type=event.document_type,
                event_label=event.event_label,
                citations=[c for c in citations if c.document_id == event.document_id],
            )
            for event in events
        ]

    def _validate(self, request: InvestigationRequest) -> None:
        """Defense-in-depth beyond pydantic's own field constraints on
        InvestigationRequest."""
        if not request.query.strip():
            raise ValueError("query must not be empty")


def _truncate(text: str, max_chars: int) -> str:
    """Return `text` capped at max_chars, marked with a trailing "..." if it
    was actually cut short."""
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    return stripped[:max_chars].rstrip() + "..."


def _clamp_confidence(relevance_score: float) -> float:
    """Evidence.confidence is bounded to [0.0, 1.0], but cosine similarity
    (Citation.relevance_score) is mathematically bounded to [-1.0, 1.0] —
    clamp rather than let an edge-case negative score fail Evidence's own
    validation."""
    return max(0.0, min(1.0, relevance_score))

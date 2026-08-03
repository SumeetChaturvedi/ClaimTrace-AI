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
"""

from app.agent import tools
from app.agent.investigation_package import InvestigationPackageBuilder
from app.agent.models import Citation, Evidence, InvestigationRequest, InvestigationResponse
from app.agent.reasoning import ReasoningEngine
from app.investigation import InvestigationPlanner
from app.investigation.timeline import TimelineBuilder, TimelineFormatter

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
    ) -> None:
        self._reasoning_engine = reasoning_engine or ReasoningEngine()
        self._package_builder = package_builder or InvestigationPackageBuilder()
        self._planner = planner or InvestigationPlanner()
        self._timeline_builder = timeline_builder or TimelineBuilder()
        self._timeline_formatter = timeline_formatter or TimelineFormatter()

    async def investigate(self, request: InvestigationRequest) -> InvestigationResponse:
        """Run an investigation for `request`: create an InvestigationPlan,
        retrieve supporting evidence via semantic search, build an Evidence
        object per result, assemble an InvestigationPackage from the
        question and evidence, hand it to ReasoningEngine, and map its
        ReasoningResult onto InvestigationResponse. Does not verify
        citations or call an LLM yet — see ReasoningEngine for what
        "reasoning" currently means.

        The InvestigationPlan is created and passed through to
        search_documents(), which now converts it to a RetrievalContext and
        forwards it into retrieval — its primary_entities feed a
        deterministic entity-match scoring bonus there (see
        app/retrieval/scoring.py). It doesn't otherwise shape the query,
        evidence, packaging, or reasoning, and is never exposed on
        InvestigationResponse."""
        self._validate(request)

        plan = self._planner.create_plan(request.query)

        citations = tools.search_documents(
            project_id=request.project_id,
            query=request.query,
            top_k=request.top_k,
            investigation_plan=plan,
        )
        evidence = self._build_evidence(citations)
        timeline_context = self._build_timeline_context(citations)
        package = self._package_builder.build(request.query, evidence, timeline_context=timeline_context)

        result = self._reasoning_engine.reason(package)

        return InvestigationResponse(
            answer=result.answer,
            citations=result.supporting_evidence,
            reasoning_steps=result.reasoning_steps,
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

    def _build_timeline_context(self, citations: list[Citation]) -> str:
        """Build a formatted chronology from the documents behind
        `citations` only — never the whole corpus. Fetches the (deduplicated)
        Document rows for citations' document ids, hands them to
        TimelineBuilder (which sorts by document_date, unchanged from
        Sprint 5 Task 01), then TimelineFormatter (unchanged from Sprint 5
        Task 04). Returns "" if there are no citations, same as
        TimelineFormatter already does for an empty timeline."""
        document_ids = sorted({citation.document_id for citation in citations})
        documents = tools.get_documents(document_ids)
        timeline = self._timeline_builder.build(documents)
        return self._timeline_formatter.format(timeline)

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

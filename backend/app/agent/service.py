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

Investigation planning: create_plan() now runs before search, but its
result isn't consumed yet — not used to shape the query, retrieval, ranking,
or the response. This is deliberately just establishing the plan's place in
the pipeline; a future task will have search/reasoning actually use it.
"""

from app.agent import tools
from app.agent.investigation_package import InvestigationPackageBuilder
from app.agent.models import Citation, Evidence, InvestigationRequest, InvestigationResponse
from app.agent.reasoning import ReasoningEngine
from app.investigation import InvestigationPlanner

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
    ) -> None:
        self._reasoning_engine = reasoning_engine or ReasoningEngine()
        self._package_builder = package_builder or InvestigationPackageBuilder()
        self._planner = planner or InvestigationPlanner()

    async def investigate(self, request: InvestigationRequest) -> InvestigationResponse:
        """Run an investigation for `request`: create an InvestigationPlan,
        retrieve supporting evidence via semantic search, build an Evidence
        object per result, assemble an InvestigationPackage from the
        question and evidence, hand it to ReasoningEngine, and map its
        ReasoningResult onto InvestigationResponse. Does not verify
        citations or call an LLM yet — see ReasoningEngine for what
        "reasoning" currently means.

        The InvestigationPlan is created but not yet consumed — kept as a
        local variable only, not passed to search or reasoning, and never
        exposed on InvestigationResponse."""
        self._validate(request)

        plan = self._planner.create_plan(request.query)  # noqa: F841 — not yet consumed, see module docstring

        citations = tools.search_documents(
            project_id=request.project_id,
            query=request.query,
            top_k=request.top_k,
        )
        evidence = self._build_evidence(citations)
        package = self._package_builder.build(request.query, evidence)

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

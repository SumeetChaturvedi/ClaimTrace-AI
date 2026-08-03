"""Builds the reasoning prompt sent to the LLM, from an InvestigationPackage.

This is the ONLY place prompt strings live in the codebase. ReasoningEngine
(app/agent/reasoning.py) must never construct prompt text itself — only call
build_reasoning_prompt() and hand the result to an LLMProvider. No LLM calls
or network access happen here: pure string formatting over data that was
already gathered deterministically upstream.

Produces a provider-agnostic Prompt (app/llm/provider.py) rather than one
flat string: system_prompt carries the fixed behavioral instructions,
user_prompt carries the question/statistics/evidence/timeline that varies
per investigation. This is the natural system/user split every major LLM API
already expects — no provider-specific formatting happens here, that's each
LLMProvider's job.

Timeline section (Sprint 5 Task 05): package.timeline_context is already a
fully-formatted, already-chronological block of text (TimelineFormatter's
output, built upstream in InvestigationService from TimelineBuilder) — this
class only wraps it in a clearly separated header/footer and appends it to
the user prompt if non-empty. No instruction telling the model to build or
reorder a chronology is added anywhere: _instructions_section() is entirely
unchanged from before this task, since the timeline already exists and
doesn't need to be reconstructed, only read.
"""

from app.agent.investigation_package import InvestigationPackage
from app.llm.provider import Prompt


class PromptBuilder:
    """Converts an InvestigationPackage into a provider-agnostic Prompt: the
    question, investigation statistics, every piece of supporting evidence,
    and (if built) a pre-formatted timeline as the user prompt; instructions
    constraining the model to that evidence alone as the system prompt."""

    def build_reasoning_prompt(self, package: InvestigationPackage) -> Prompt:
        """Build the full reasoning Prompt for `package`."""
        sections = [
            self._question_section(package),
            self._statistics_section(package),
            self._evidence_section(package),
        ]
        timeline_section = self._timeline_section(package)
        if timeline_section:
            sections.append(timeline_section)

        user_prompt = "\n\n".join(sections)
        return Prompt(system_prompt=self._instructions_section(), user_prompt=user_prompt)

    def _question_section(self, package: InvestigationPackage) -> str:
        return f"# Investigation Question\n{package.question}"

    def _statistics_section(self, package: InvestigationPackage) -> str:
        return (
            "# Investigation Statistics\n"
            f"- Total evidence items: {package.total_evidence}\n"
            f"- Documents considered: {package.documents_considered}"
        )

    def _evidence_section(self, package: InvestigationPackage) -> str:
        if not package.evidence:
            return "# Supporting Evidence\n(No evidence was found.)"

        blocks: list[str] = []
        for index, item in enumerate(package.evidence, start=1):
            lines = [f"[{index}] Document: {item.document_name}"]
            if item.citation.page is not None:
                lines.append(f"    Page: {item.citation.page}")
            lines.append(f"    Confidence: {item.confidence:.2f}")
            lines.append(f'    Excerpt: "{item.excerpt}"')
            blocks.append("\n".join(lines))

        return "# Supporting Evidence\n\n" + "\n\n".join(blocks)

    def _timeline_section(self, package: InvestigationPackage) -> str:
        """Return the timeline block wrapped in a clearly separated
        header/footer, or "" if no timeline was built (build_reasoning_prompt
        then omits the section entirely rather than appending an empty one)."""
        if not package.timeline_context:
            return ""
        return "----------------------\nPROJECT TIMELINE\n\n" f"{package.timeline_context}\n" "----------------------"

    def _instructions_section(self) -> str:
        return (
            "# Instructions\n"
            "- Answer ONLY using the supplied evidence above.\n"
            "- Never invent facts that are not present in the evidence.\n"
            "- If the evidence is insufficient to answer the question, explicitly say so.\n"
            "- Preserve a professional engineering tone.\n"
            "- Do not interpret contract clauses unless explicitly supported by evidence.\n"
            "- Keep the answer concise and factual."
        )

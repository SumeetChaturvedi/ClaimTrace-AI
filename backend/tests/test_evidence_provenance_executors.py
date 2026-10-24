"""Focused tests for Phase W2.3 follow-up: derivation_kind provenance
propagation through the two secondary evidence paths --
app/agent/full_document_read_executor.py and
app/agent/reference_expansion_executor.py -- which build Evidence
independently of InvestigationService._build_evidence() (already covered)
and therefore need their own coverage of the same guarantee: OCR-derived
and AI-generated visual evidence must carry its persisted
Document.derivation_kind into Evidence.metadata, merged alongside the
"source" key each executor already sets, never overwriting it.

Real Postgres, plain unittest, no mocking needed beyond what the
executors' own existing code already requires -- these are deterministic,
metadata-based array-overlap/foreign-key lookups, no LLM/OCR/vision
provider involved at all.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_evidence_provenance_executors -v
"""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.agent.evidence_sufficiency import SufficiencyDecision
from app.agent.full_document_read_executor import FullDocumentReadExecutor
from app.agent.investigation_state import InvestigationState, RemediationType
from app.agent.reference_expansion_executor import ReferenceExpansionExecutor
from app.db.models import Document, DocumentChunk, Project
from app.db.session import get_session_factory
from app.investigation.models import InvestigationPlan
from app.main import app


def _plan() -> InvestigationPlan:
    return InvestigationPlan(
        goal="test goal",
        investigation_type="timeline",
        expected_answer_type="a date",
    )


class ProvenanceExecutorTestCase(unittest.TestCase):
    """Shared project/document/chunk fixture helpers -- plain direct
    session inserts (status='ready'), not routed through real ingestion,
    since these executors only ever read already-ingested rows."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls._created_project_ids: list[int] = []

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            for project_id in cls._created_project_ids:
                document_ids = [
                    doc.id for doc in session.query(Document).filter(Document.project_id == project_id).all()
                ]
                if document_ids:
                    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id.in_(document_ids)))
                session.query(Document).filter(Document.project_id == project_id).delete()
                session.query(Project).filter(Project.id == project_id).delete()
            session.commit()
        cls.client.__exit__(None, None, None)

    def _create_project(self, name: str) -> int:
        resp = self.client.post("/projects", json={"name": name})
        project_id = resp.json()["id"]
        self._created_project_ids.append(project_id)
        return project_id

    def _create_document(
        self,
        project_id: int,
        filename: str,
        *,
        derivation_kind: str | None = None,
        referenced_ids: list[str] | None = None,
        chunk_text: str | None = "irrelevant filler text",
    ) -> Document:
        with get_session_factory()() as session:
            document = Document(
                project_id=project_id,
                filename=filename,
                status="ready",
                derivation_kind=derivation_kind,
                referenced_ids=referenced_ids,
            )
            session.add(document)
            session.flush()
            if chunk_text is not None:
                session.add(DocumentChunk(document_id=document.id, page_number=1, chunk_text=chunk_text))
            session.commit()
            session.refresh(document)
            return document


class FullDocumentReadProvenanceTests(ProvenanceExecutorTestCase):
    def _read(self, document_id: int) -> InvestigationState:
        state = InvestigationState(plan=_plan())
        decision = SufficiencyDecision(
            sufficient=False,
            remediation=RemediationType.FULL_DOCUMENT_READ,
            reason="test",
            details={"document_id": document_id},
        )
        FullDocumentReadExecutor().read(state, decision)
        return state

    def test_ocr_transcription_document_propagates_derivation_kind(self):
        project_id = self._create_project("FDR Provenance -- OCR")
        document = self._create_document(
            project_id, "scan.jpg.ocr.txt", derivation_kind="ocr_transcription", chunk_text="SI-100 some ocr text"
        )

        state = self._read(document.id)

        self.assertEqual(len(state.evidence), 1)
        metadata = state.evidence[0].metadata
        self.assertEqual(metadata.get("derivation_kind"), "ocr_transcription")
        self.assertEqual(metadata.get("source"), "full_document_read")

    def test_visual_description_document_propagates_derivation_kind(self):
        project_id = self._create_project("FDR Provenance -- Visual")
        document = self._create_document(
            project_id,
            "photo.jpg.visual.txt",
            derivation_kind="visual_description",
            chunk_text="a cracked concrete beam is visible",
        )

        state = self._read(document.id)

        self.assertEqual(len(state.evidence), 1)
        metadata = state.evidence[0].metadata
        self.assertEqual(metadata.get("derivation_kind"), "visual_description")
        self.assertEqual(metadata.get("source"), "full_document_read")

    def test_ordinary_document_has_no_derivation_kind_in_metadata(self):
        """Regression: an ordinary (pre-W2.3, non-image-derived) document
        must not gain a spurious derivation_kind key -- the merge must be
        additive, never inventing provenance that was never persisted."""
        project_id = self._create_project("FDR Provenance -- Ordinary")
        document = self._create_document(project_id, "report.pdf", derivation_kind=None, chunk_text="ordinary text")

        state = self._read(document.id)

        self.assertEqual(len(state.evidence), 1)
        metadata = state.evidence[0].metadata
        self.assertNotIn("derivation_kind", metadata)
        self.assertEqual(metadata.get("source"), "full_document_read")

    def test_multiple_chunks_of_the_same_document_only_look_up_derivation_kind_once(self):
        """Not a correctness requirement visible to the caller, but
        confirms the lazy per-document lookup (not per-chunk) still
        produces the same derivation_kind on every chunk's Evidence."""
        project_id = self._create_project("FDR Provenance -- Multi Chunk")
        document = self._create_document(
            project_id, "scan2.jpg.ocr.txt", derivation_kind="ocr_transcription", chunk_text=None
        )
        with get_session_factory()() as session:
            session.add_all(
                [
                    DocumentChunk(document_id=document.id, page_number=1, chunk_text="first chunk"),
                    DocumentChunk(document_id=document.id, page_number=2, chunk_text="second chunk"),
                ]
            )
            session.commit()

        state = self._read(document.id)

        self.assertEqual(len(state.evidence), 2)
        for item in state.evidence:
            self.assertEqual(item.metadata.get("derivation_kind"), "ocr_transcription")


class ReferenceExpansionProvenanceTests(ProvenanceExecutorTestCase):
    def _expand_from(self, visited_document: Document, excerpt_text: str) -> InvestigationState:
        """Build a state that already contains one Evidence item for
        `visited_document`, whose excerpt text is what
        EvidenceSufficiencyAssessor's stage 1 scans for unresolved
        references -- see evidence_sufficiency._check_unresolved_references
        and _combined_evidence_text."""
        from app.agent.models import Citation, Evidence

        with get_session_factory()() as session:
            chunk = session.query(DocumentChunk).filter(DocumentChunk.document_id == visited_document.id).first()

        state = InvestigationState(plan=_plan())
        state.add_evidence(
            [
                Evidence(
                    citation=Citation(
                        document_id=visited_document.id,
                        chunk_id=chunk.id,
                        page=1,
                        relevance_score=0.9,
                        chunk_text=excerpt_text,
                    ),
                    document_id=visited_document.id,
                    document_name=visited_document.filename,
                    excerpt=excerpt_text,
                    surrounding_context=excerpt_text,
                    confidence=0.9,
                    metadata={},
                )
            ]
        )
        ReferenceExpansionExecutor().expand(state)
        return state

    def test_visual_description_document_discovered_by_expansion_propagates_derivation_kind(self):
        project_id = self._create_project("RefExp Provenance -- Visual")
        # Filler documents dilute the reference's document-frequency ratio
        # below the default 0.5 boilerplate threshold (2 of 5 documents
        # share "SI-200" -> 0.4), so the genuine match isn't filtered out
        # as project-wide boilerplate -- see find_related_documents().
        for i in range(3):
            self._create_document(project_id, f"filler-{i}.pdf", referenced_ids=None, chunk_text="unrelated")

        visited = self._create_document(
            project_id, "report.pdf", referenced_ids=["SI-200"], chunk_text="mentions SI-200"
        )
        visual = self._create_document(
            project_id,
            "photo.jpg.visual.txt",
            derivation_kind="visual_description",
            referenced_ids=["SI-200"],
            chunk_text="a visible crack in the beam",
        )

        state = self._expand_from(visited, "see document SI-200 for context")

        discovered = [item for item in state.evidence if item.document_id == visual.id]
        self.assertEqual(len(discovered), 1)
        metadata = discovered[0].metadata
        self.assertEqual(metadata.get("derivation_kind"), "visual_description")
        self.assertEqual(metadata.get("source"), "reference_expansion")

    def test_ordinary_document_discovered_by_expansion_has_no_derivation_kind(self):
        project_id = self._create_project("RefExp Provenance -- Ordinary")
        for i in range(3):
            self._create_document(project_id, f"filler-{i}.pdf", referenced_ids=None, chunk_text="unrelated")

        visited = self._create_document(
            project_id, "report.pdf", referenced_ids=["SI-201"], chunk_text="mentions SI-201"
        )
        related = self._create_document(
            project_id, "letter.pdf", derivation_kind=None, referenced_ids=["SI-201"], chunk_text="an ordinary letter"
        )

        state = self._expand_from(visited, "see document SI-201 for context")

        discovered = [item for item in state.evidence if item.document_id == related.id]
        self.assertEqual(len(discovered), 1)
        metadata = discovered[0].metadata
        self.assertNotIn("derivation_kind", metadata)
        self.assertEqual(metadata.get("source"), "reference_expansion")


if __name__ == "__main__":
    unittest.main()

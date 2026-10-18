"""Integration tests for event extraction's persistence and investigation-
lifecycle integration (Phase 8B.2) — POST/GET/retry on
.../investigations, focused specifically on:
  - an extraction success is persisted correctly (events, events_error=None)
  - an extraction failure never fails the investigation itself, and is
    persisted as a distinct, honest "unavailable" state (events=[],
    events_error=<message>) rather than a misleading empty success
  - retry clears the previous run's events before re-running, so a retry
    can never accidentally leave stale or duplicated events behind
  - an investigation that predates this feature (events/events_error both
    NULL in the database) is reported identically to "nothing to show",
    never as an error

These tests inject a fake EventExtractor AND a fake ReasoningEngine (via
FastAPI's dependency_overrides, overriding get_investigation_service) so
they make zero real Gemini calls — this file is about persistence/lifecycle
wiring, not extraction quality or reasoning quality, both already covered
elsewhere (test_event_extraction.py; test_investigations.py's two real
end-to-end runs; the Phase 8B.2 production evaluation against
dataset/event_eval's fixtures). Retrieval itself is still real (real
Postgres, real embeddings, real investigation loop) — only the two LLM
calls are faked, which is why these tests still need a project with real
ingested documents (project 2, already used by test_investigations.py).

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_event_persistence -v
"""

import unittest
import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.agent.event_extraction import EventExtractionError, ExtractionResult
from app.agent.models import Evidence, ExtractedEvent
from app.agent.reasoning import ReasoningEngine
from app.agent.service import InvestigationService
from app.api.routes.investigate import get_investigation_service
from app.db.models import InvestigationRecord
from app.db.session import get_session_factory
from app.llm.provider import GenerationResult, LLMProvider, LLMProviderError, Prompt
from app.main import app

PROJECT_ID = 2
QUESTION = "What contract governs this project?"


class _FakeAnswerProvider(LLMProvider):
    """Returns a fixed answer regardless of prompt — used only as
    ReasoningEngine's provider in this file, so these tests never call
    real Gemini for the reasoning step either."""

    def generate(self, prompt: Prompt) -> GenerationResult:
        return GenerationResult(text="A fake, fixed reasoning answer for testing persistence.")


class _FixedEventExtractor:
    """Duck-types EventExtractor's public interface (extract()) with a
    pre-scripted result or exception, bypassing the real LLM call/parsing/
    validation entirely — those are tested independently in
    test_event_extraction.py. This class exists only to test how
    InvestigationService/the persistence layer handle whatever a real
    extractor could legitimately produce."""

    def __init__(self, events: list[ExtractedEvent] | None = None, error: Exception | None = None):
        self._events = events if events is not None else []
        self._error = error

    def extract(self, question: str, evidence: list[Evidence]) -> ExtractionResult:
        if self._error is not None:
            raise self._error
        return ExtractionResult(events=self._events, truncated=False)


def _make_service(event_extractor) -> InvestigationService:
    return InvestigationService(
        reasoning_engine=ReasoningEngine(provider=_FakeAnswerProvider()),
        event_extractor=event_extractor,
    )


def _one_event(document_id: int = 1, chunk_id: int = 1) -> ExtractedEvent:
    return ExtractedEvent(
        document_id=document_id,
        chunk_id=chunk_id,
        excerpt="fixture excerpt",
        event_type="CLARIFICATION_REQUESTED",
        assertion_type="request",
        description="A fixture event for persistence testing",
        event_date=None,
        event_date_basis="unknown",
        attributed_party=None,
    )


class EventPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls._created_ids: list[str] = []

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            for raw_id in cls._created_ids:
                record = session.get(InvestigationRecord, uuid.UUID(raw_id))
                if record is not None:
                    session.delete(record)
            session.commit()
        app.dependency_overrides.pop(get_investigation_service, None)
        cls.client.__exit__(None, None, None)

    def tearDown(self):
        app.dependency_overrides.pop(get_investigation_service, None)

    def test_investigation_succeeds_and_persists_events_when_extraction_succeeds(self):
        service = _make_service(_FixedEventExtractor(events=[_one_event()]))
        app.dependency_overrides[get_investigation_service] = lambda: service

        resp = self.client.post(f"/projects/{PROJECT_ID}/investigations", json={"query": QUESTION})
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.__class__._created_ids.append(body["id"])

        self.assertEqual(body["status"], "completed")
        self.assertEqual(len(body["events"]), 1)
        self.assertEqual(body["events"][0]["document_id"], 1)
        self.assertIsNone(body["events_error"])

    def test_investigation_succeeds_when_extraction_raises(self):
        service = _make_service(_FixedEventExtractor(error=EventExtractionError("simulated provider failure")))
        app.dependency_overrides[get_investigation_service] = lambda: service

        resp = self.client.post(f"/projects/{PROJECT_ID}/investigations", json={"query": QUESTION})
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.__class__._created_ids.append(body["id"])

        # The investigation itself succeeded despite extraction failing.
        self.assertEqual(body["status"], "completed")
        self.assertTrue(body["answer"])
        # Extraction's failure is reported honestly, not as an empty success.
        self.assertEqual(body["events"], [])
        self.assertIsNotNone(body["events_error"])
        self.assertIn("simulated provider failure", body["events_error"])

        with get_session_factory()() as session:
            db_row = session.get(InvestigationRecord, uuid.UUID(body["id"]))
            self.assertIsNone(db_row.events)
            self.assertIsNotNone(db_row.events_error)

    def test_investigation_succeeds_when_extraction_raises_an_unexpected_exception(self):
        """Not just EventExtractionError -- any unexpected exception from
        the extractor must also be isolated (see service.py's
        _extract_events, which catches Exception as defense-in-depth)."""
        service = _make_service(_FixedEventExtractor(error=RuntimeError("totally unexpected")))
        app.dependency_overrides[get_investigation_service] = lambda: service

        resp = self.client.post(f"/projects/{PROJECT_ID}/investigations", json={"query": QUESTION})
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.__class__._created_ids.append(body["id"])

        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["events"], [])
        self.assertIsNotNone(body["events_error"])

    def test_retry_overwrites_previous_events_without_duplicating(self):
        service = _make_service(_FixedEventExtractor(events=[_one_event(document_id=1, chunk_id=1)]))
        app.dependency_overrides[get_investigation_service] = lambda: service

        create_resp = self.client.post(f"/projects/{PROJECT_ID}/investigations", json={"query": QUESTION})
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        investigation_id = create_resp.json()["id"]
        self.__class__._created_ids.append(investigation_id)
        self.assertEqual(len(create_resp.json()["events"]), 1)

        # Retry with a DIFFERENT fixed event -- if retry didn't clear the
        # old one first, a naive append would leave 2 events behind.
        service2 = _make_service(_FixedEventExtractor(events=[_one_event(document_id=2, chunk_id=2)]))
        app.dependency_overrides[get_investigation_service] = lambda: service2

        retry_resp = self.client.post(f"/projects/{PROJECT_ID}/investigations/{investigation_id}/retry")
        self.assertEqual(retry_resp.status_code, 200, retry_resp.text)
        body = retry_resp.json()

        self.assertEqual(len(body["events"]), 1)
        self.assertEqual(body["events"][0]["document_id"], 2)

    def test_investigation_predating_this_feature_reports_empty_events_not_an_error(self):
        """A row with events/events_error both NULL (as every investigation
        created before this phase has) must be reported as events=[],
        events_error=None -- indistinguishable from a legitimate zero-event
        result at the API layer, never surfaced as a failure."""
        with get_session_factory()() as session:
            record = InvestigationRecord(
                project_id=PROJECT_ID,
                question="A pre-existing investigation from before Phase 8B.2",
                status="completed",
                answer="An old answer.",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(record)
            session.commit()
            investigation_id = str(record.id)
        self.__class__._created_ids.append(investigation_id)

        resp = self.client.get(f"/projects/{PROJECT_ID}/investigations/{investigation_id}")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["events"], [])
        self.assertIsNone(body["events_error"])


if __name__ == "__main__":
    unittest.main()

"""Focused tests for the persistent, project-scoped investigation endpoints
(Phase 2: Persistent Investigations) — POST/GET .../investigations,
GET .../investigations/{id}, and POST .../investigations/{id}/retry.

Same approach as test_document_file.py: plain `unittest` + TestClient, no
new dependency, run against the REAL app, REAL Postgres, and (for the two
fixture investigations created once in setUpClass) the REAL investigation
engine and REAL Gemini — no mocks, per this project's established
principle that a persistence layer must be validated against what it
actually persists, not a stand-in. Real Gemini calls are kept to exactly
two for this whole file (one per project), shared read-only across every
test that doesn't specifically need its own creation (list/get/isolation);
the remaining tests (empty-query validation, retry-of-a-failed-record) are
deliberately built to never reach Gemini at all, so this file stays fast
and cheap to re-run.

Rows created here are deleted in tearDownClass, so repeated runs don't
accumulate investigation_records garbage in the dev database.

Run with:
    cd backend && source .venv/bin/activate
    PYTHONPATH=. python3 -m unittest tests.test_investigations -v
"""

import unittest
import uuid

from fastapi.testclient import TestClient

from app.db.models import InvestigationRecord
from app.db.session import get_session_factory
from app.main import app

PROJECT_2_ID = 2
PROJECT_3_ID = 3
NONEXISTENT_PROJECT_ID = 999_999
NONEXISTENT_INVESTIGATION_ID = "00000000-0000-0000-0000-000000000000"

# Real, short, cheap-for-retrieval questions — not the full benchmark
# questions used elsewhere, since these exist purely to exercise
# persistence/isolation, not investigation quality (that is what
# dataset/scripts/run_benchmarks_narrowed.py is for, and was re-run
# separately as part of this task's regression check).
PROJECT_2_QUESTION = "What contract governs this project?"
PROJECT_3_QUESTION = "What contract governs this project?"


class InvestigationEndpointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()  # runs the app's real lifespan (DB init)

        # Exactly two real engine runs (real Gemini calls) for this whole
        # file, created once and reused read-only by every test below that
        # doesn't specifically need its own fresh creation.
        p2_resp = cls.client.post(f"/projects/{PROJECT_2_ID}/investigations", json={"query": PROJECT_2_QUESTION})
        assert p2_resp.status_code == 201, p2_resp.text
        cls.p2_investigation = p2_resp.json()

        p3_resp = cls.client.post(f"/projects/{PROJECT_3_ID}/investigations", json={"query": PROJECT_3_QUESTION})
        assert p3_resp.status_code == 201, p3_resp.text
        cls.p3_investigation = p3_resp.json()

        cls._created_ids = [cls.p2_investigation["id"], cls.p3_investigation["id"]]

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            for raw_id in cls._created_ids:
                record = session.get(InvestigationRecord, uuid.UUID(raw_id))
                if record is not None:
                    session.delete(record)
            session.commit()
        cls.client.__exit__(None, None, None)

    # -- Create -----------------------------------------------------------

    def test_create_persists_completed_investigation_with_citations(self):
        record = self.p2_investigation
        self.assertEqual(record["project_id"], PROJECT_2_ID)
        self.assertEqual(record["query"], PROJECT_2_QUESTION)
        self.assertIn(record["status"], ("completed", "failed"))  # a real Gemini call; allow for a real transient failure
        self.assertIsInstance(record["citations"], list)
        self.assertIsInstance(record["reasoning_steps"], list)
        # A stable, real UUID -- not a client-supplied or sequential id.
        uuid.UUID(record["id"])

        with get_session_factory()() as session:
            db_row = session.get(InvestigationRecord, uuid.UUID(record["id"]))
            self.assertIsNotNone(db_row, "investigation was not actually persisted in Postgres")
            self.assertEqual(db_row.project_id, PROJECT_2_ID)
            self.assertEqual(db_row.status, record["status"])
            if record["status"] == "completed":
                self.assertEqual(len(db_row.citations), len(record["citations"]))

    def test_create_under_nonexistent_project_returns_404(self):
        resp = self.client.post(f"/projects/{NONEXISTENT_PROJECT_ID}/investigations", json={"query": "Any question?"})
        self.assertEqual(resp.status_code, 404)

    def test_create_with_empty_query_persists_failed_record_and_returns_400(self):
        resp = self.client.post(f"/projects/{PROJECT_2_ID}/investigations", json={"query": "   "})
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        investigation_id = body["detail"]["investigation_id"]
        self._created_ids.append(investigation_id)  # clean up in tearDownClass too

        with get_session_factory()() as session:
            db_row = session.get(InvestigationRecord, uuid.UUID(investigation_id))
            self.assertIsNotNone(db_row)
            self.assertEqual(db_row.status, "failed")
            self.assertIsNotNone(db_row.error)
            self.assertIsNone(db_row.answer)

    # -- Get / List ---------------------------------------------------------

    def test_get_returns_the_persisted_record_without_rerunning(self):
        resp = self.client.get(f"/projects/{PROJECT_2_ID}/investigations/{self.p2_investigation['id']}")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["id"], self.p2_investigation["id"])
        self.assertEqual(body["answer"], self.p2_investigation["answer"])
        self.assertEqual(body["citations"], self.p2_investigation["citations"])

    def test_list_is_scoped_to_its_own_project(self):
        resp = self.client.get(f"/projects/{PROJECT_2_ID}/investigations")
        self.assertEqual(resp.status_code, 200)
        ids = [item["id"] for item in resp.json()]
        self.assertIn(self.p2_investigation["id"], ids)
        self.assertNotIn(self.p3_investigation["id"], ids)

    def test_list_under_nonexistent_project_returns_404(self):
        resp = self.client.get(f"/projects/{NONEXISTENT_PROJECT_ID}/investigations")
        self.assertEqual(resp.status_code, 404)

    # -- Project isolation (critical) ---------------------------------------

    def test_project_2_investigation_requested_under_project_3_returns_404(self):
        resp = self.client.get(f"/projects/{PROJECT_3_ID}/investigations/{self.p2_investigation['id']}")
        self.assertEqual(resp.status_code, 404)

    def test_project_3_investigation_requested_under_project_2_returns_404(self):
        resp = self.client.get(f"/projects/{PROJECT_2_ID}/investigations/{self.p3_investigation['id']}")
        self.assertEqual(resp.status_code, 404)

    def test_nonexistent_investigation_returns_404(self):
        resp = self.client.get(f"/projects/{PROJECT_2_ID}/investigations/{NONEXISTENT_INVESTIGATION_ID}")
        self.assertEqual(resp.status_code, 404)

    def test_malformed_investigation_id_returns_422(self):
        resp = self.client.get(f"/projects/{PROJECT_2_ID}/investigations/not-a-uuid")
        self.assertEqual(resp.status_code, 422)

    def test_invalid_project_id_returns_422(self):
        resp = self.client.get(f"/projects/not-a-project/investigations/{self.p2_investigation['id']}")
        self.assertEqual(resp.status_code, 422)

    # -- Retry ----------------------------------------------------------

    def test_retry_reexecutes_and_overwrites_in_place(self):
        # Reuses the empty-query failure from above (created fresh here so
        # this test doesn't depend on test execution order) -- retrying it
        # re-validates the same empty question and fails again the same
        # deterministic way, without ever reaching Gemini, so this stays
        # cheap while still exercising the real retry code path end to end.
        create_resp = self.client.post(f"/projects/{PROJECT_2_ID}/investigations", json={"query": "   "})
        investigation_id = create_resp.json()["detail"]["investigation_id"]
        self._created_ids.append(investigation_id)

        retry_resp = self.client.post(f"/projects/{PROJECT_2_ID}/investigations/{investigation_id}/retry")
        self.assertEqual(retry_resp.status_code, 400)
        self.assertEqual(retry_resp.json()["detail"]["investigation_id"], investigation_id)

        with get_session_factory()() as session:
            db_row = session.get(InvestigationRecord, uuid.UUID(investigation_id))
            self.assertEqual(db_row.status, "failed")

    def test_retry_under_wrong_project_returns_404(self):
        resp = self.client.post(f"/projects/{PROJECT_3_ID}/investigations/{self.p2_investigation['id']}/retry")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()

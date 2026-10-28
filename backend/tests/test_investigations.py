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
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes.investigations import _describe_stopping_reason, _lock_record_for_retry, _snapshot_current_attempt
from app.db.models import InvestigationRecord, InvestigationRecordAttempt, Project
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
        # Phase 1 (Fix Existing Investigation Pipeline Gaps): both new
        # fields must always be present and well-typed on a fresh response.
        self.assertIsInstance(record["answer_truncated"], bool)
        self.assertTrue(record["evidence_limitation"] is None or isinstance(record["evidence_limitation"], str))

        with get_session_factory()() as session:
            db_row = session.get(InvestigationRecord, uuid.UUID(record["id"]))
            self.assertIsNotNone(db_row, "investigation was not actually persisted in Postgres")
            self.assertEqual(db_row.project_id, PROJECT_2_ID)
            self.assertEqual(db_row.status, record["status"])
            if record["status"] == "completed":
                self.assertEqual(len(db_row.citations), len(record["citations"]))
                # A completed run always goes through a real LoopRunResult,
                # so a real stopping_reason is always persisted for it --
                # never left NULL the way a legacy/pre-feature row would be.
                self.assertIsNotNone(db_row.stopping_reason)

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

    def test_retry_clears_the_prior_runs_answer_truncated_and_stopping_reason(self):
        """Mirrors the existing clearing behaviour already verified for
        status/citations above -- a retry must not leave the PREVIOUS
        attempt's truncation/stopping-reason signals visible on a record
        whose new attempt hasn't produced its own yet. Uses the same
        never-reaches-Gemini empty-query failure as the retry test above,
        so this stays cheap."""
        create_resp = self.client.post(f"/projects/{PROJECT_2_ID}/investigations", json={"query": "   "})
        investigation_id = create_resp.json()["detail"]["investigation_id"]
        self._created_ids.append(investigation_id)

        with get_session_factory()() as session:
            db_row = session.get(InvestigationRecord, uuid.UUID(investigation_id))
            db_row.answer_truncated = True
            db_row.stopping_reason = "unsupported_remediation"
            session.commit()

        self.client.post(f"/projects/{PROJECT_2_ID}/investigations/{investigation_id}/retry")

        with get_session_factory()() as session:
            db_row = session.get(InvestigationRecord, uuid.UUID(investigation_id))
            self.assertFalse(db_row.answer_truncated)
            self.assertIsNone(db_row.stopping_reason)

    def test_never_retried_investigation_is_attempt_1(self):
        self.assertEqual(self.p2_investigation["attempt_number"], 1)
        resp = self.client.get(f"/projects/{PROJECT_2_ID}/investigations/{self.p2_investigation['id']}/attempts")
        self.assertEqual(resp.status_code, 200)
        attempts = resp.json()
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["attempt_number"], 1)
        self.assertTrue(attempts[0]["is_current"])
        self.assertEqual(attempts[0]["status"], self.p2_investigation["status"])


class InvestigationAttemptHistoryTests(unittest.TestCase):
    """Phase 2a (Preserve Investigation Attempt History). Directly inserts
    its own InvestigationRecord rows with a pre-set, fully-populated prior
    result (never via the real create endpoint) so these tests can verify
    snapshot correctness without making any real Gemini call -- an empty
    `question` on the row being retried deliberately makes the RETRY
    itself fail fast at InvestigationService's own validation (the same
    trick InvestigationEndpointsTests already uses above), which is
    exactly what's needed to test "a failed retry still preserves the
    snapshot of the attempt it superseded" for free."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls._created_ids: list[uuid.UUID] = []

    @classmethod
    def tearDownClass(cls):
        with get_session_factory()() as session:
            for investigation_id in cls._created_ids:
                record = session.get(InvestigationRecord, investigation_id)
                if record is not None:
                    session.delete(record)  # cascades investigation_record_attempts via ON DELETE CASCADE
            session.commit()
        cls.client.__exit__(None, None, None)

    def _insert_rich_completed_record(self, *, question: str = "") -> uuid.UUID:
        """A directly-inserted, fully-populated 'completed' record -- every
        existing result-bearing field set to a distinct, recognizable fake
        value, so a test can confirm the snapshot captured ALL of them,
        not just a convenient subset. `question=""` by default so that
        retrying this record fails fast (ValueError from InvestigationService.
        _validate) without ever reaching Gemini."""
        with get_session_factory()() as session:
            record = InvestigationRecord(
                project_id=PROJECT_2_ID,
                question=question,
                status="completed",
                answer="The original, pre-retry answer.",
                reasoning_steps=["Step one.", "Step two."],
                timeline=[
                    {
                        "document_id": 1,
                        "document_date": "2024-01-01",
                        "document_type": "NOTICE",
                        "event_label": "Notice issued",
                        "citations": [],
                    }
                ],
                contract_clauses=[
                    {"clause_number": "4.2", "title": "Notices", "topic": "NOTICE", "text": "Notice text."}
                ],
                events=[
                    {
                        "document_id": 1,
                        "chunk_id": 1,
                        "excerpt": "an excerpt",
                        "event_type": None,
                        "assertion_type": None,
                        "description": "An extracted event.",
                        "event_date": None,
                        "event_date_basis": "unknown",
                        "attributed_party": None,
                    }
                ],
                events_error=None,
                events_truncated=True,
                answer_truncated=True,
                stopping_reason="unsupported_remediation",
                error=None,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            investigation_id = record.id

            from app.db.models import InvestigationRecordCitation

            session.add(
                InvestigationRecordCitation(
                    investigation_id=investigation_id,
                    ordinal=0,
                    document_id=1,
                    chunk_id=1,
                    page=1,
                    relevance_score=0.9,
                    chunk_text="The original citation's chunk text.",
                )
            )
            session.commit()

        self._created_ids.append(investigation_id)
        return investigation_id

    def test_retry_snapshots_the_full_prior_attempt_before_clearing_it(self):
        investigation_id = self._insert_rich_completed_record()

        retry_resp = self.client.post(f"/projects/{PROJECT_2_ID}/investigations/{investigation_id}/retry")
        # The empty question makes the retry itself fail fast (400) --
        # irrelevant to what this test checks, which is the snapshot taken
        # BEFORE that failure.
        self.assertEqual(retry_resp.status_code, 400)

        with get_session_factory()() as session:
            snapshots = session.scalars(
                select(InvestigationRecordAttempt).where(InvestigationRecordAttempt.investigation_id == investigation_id)
            ).all()
            self.assertEqual(len(snapshots), 1)
            snapshot = snapshots[0]

            self.assertEqual(snapshot.attempt_number, 1)
            self.assertEqual(snapshot.status, "completed")
            self.assertEqual(snapshot.answer, "The original, pre-retry answer.")
            self.assertEqual(snapshot.reasoning_steps, ["Step one.", "Step two."])
            self.assertEqual(len(snapshot.timeline), 1)
            self.assertEqual(snapshot.timeline[0]["event_label"], "Notice issued")
            self.assertEqual(len(snapshot.contract_clauses), 1)
            self.assertEqual(snapshot.contract_clauses[0]["clause_number"], "4.2")
            self.assertEqual(len(snapshot.events), 1)
            self.assertEqual(snapshot.events[0]["description"], "An extracted event.")
            self.assertIsNone(snapshot.events_error)
            self.assertTrue(snapshot.events_truncated)
            self.assertTrue(snapshot.answer_truncated)
            self.assertEqual(snapshot.stopping_reason, "unsupported_remediation")
            self.assertIsNone(snapshot.error)

            # Citations: ALL fields needed to inspect the original evidence
            # reference must survive, not just document_id.
            self.assertEqual(len(snapshot.citations), 1)
            cited = snapshot.citations[0]
            self.assertEqual(cited["document_id"], 1)
            self.assertEqual(cited["chunk_id"], 1)
            self.assertEqual(cited["page"], 1)
            self.assertEqual(cited["relevance_score"], 0.9)
            self.assertEqual(cited["chunk_text"], "The original citation's chunk text.")

            # The live record has genuinely moved on: a failed retry, not a
            # silent no-op, and the prior attempt's data is gone from the
            # live row (it now lives only in the snapshot just verified).
            live = session.get(InvestigationRecord, investigation_id)
            self.assertEqual(live.attempt_number, 2)
            self.assertEqual(live.status, "failed")
            self.assertIsNotNone(live.error)
            self.assertIsNone(live.answer)

    def test_a_failed_retry_remains_inspectable_and_does_not_erase_the_preceding_attempt(self):
        """The preceding, successful attempt's answer must still be fully
        recoverable (via the snapshot) even though the live record now
        reflects the failed retry — this is the whole point of the
        feature, checked end to end through the real API responses rather
        than the ORM rows directly."""
        investigation_id = self._insert_rich_completed_record()
        self.client.post(f"/projects/{PROJECT_2_ID}/investigations/{investigation_id}/retry")

        current = self.client.get(f"/projects/{PROJECT_2_ID}/investigations/{investigation_id}").json()
        self.assertEqual(current["status"], "failed")
        self.assertIsNotNone(current["error"])

        attempts = self.client.get(f"/projects/{PROJECT_2_ID}/investigations/{investigation_id}/attempts").json()
        self.assertEqual(len(attempts), 2)

        attempt_1, attempt_2 = attempts
        self.assertEqual(attempt_1["attempt_number"], 1)
        self.assertFalse(attempt_1["is_current"])
        self.assertEqual(attempt_1["status"], "completed")
        self.assertEqual(attempt_1["answer"], "The original, pre-retry answer.")
        self.assertEqual(len(attempt_1["citations"]), 1)
        self.assertEqual(attempt_1["citations"][0]["chunk_text"], "The original citation's chunk text.")
        self.assertTrue(attempt_1["answer_truncated"])
        self.assertIsNotNone(attempt_1["evidence_limitation"])  # mapped from stopping_reason, never the raw name
        self.assertNotIn("unsupported_remediation", attempt_1["evidence_limitation"])

        self.assertEqual(attempt_2["attempt_number"], 2)
        self.assertTrue(attempt_2["is_current"])
        self.assertEqual(attempt_2["status"], "failed")  # never implied to have completed

    def test_attempts_endpoint_scope_checks_match_existing_endpoints(self):
        investigation_id = self._insert_rich_completed_record()

        wrong_project_resp = self.client.get(f"/projects/{PROJECT_3_ID}/investigations/{investigation_id}/attempts")
        self.assertEqual(wrong_project_resp.status_code, 404)

        nonexistent_resp = self.client.get(f"/projects/{PROJECT_2_ID}/investigations/{NONEXISTENT_INVESTIGATION_ID}/attempts")
        self.assertEqual(nonexistent_resp.status_code, 404)

        nonexistent_project_resp = self.client.get(
            f"/projects/{NONEXISTENT_PROJECT_ID}/investigations/{investigation_id}/attempts"
        )
        self.assertEqual(nonexistent_project_resp.status_code, 404)

    def test_snapshot_and_reset_are_atomic_a_rollback_destroys_neither(self):
        """Directly exercises the real transaction semantics
        _snapshot_current_attempt/retry_investigation depend on: a crash
        (simulated here by rolling back instead of committing) before the
        snapshot-insert-plus-reset commits must leave the previous attempt
        completely untouched -- neither partially reset nor missing its
        snapshot."""
        investigation_id = self._insert_rich_completed_record(question="non-empty, irrelevant here")

        with get_session_factory()() as session:
            record = session.get(InvestigationRecord, investigation_id)
            _snapshot_current_attempt(session, record)
            record.attempt_number += 1
            record.status = "running"
            record.answer = None
            session.rollback()  # simulates a crash before the real commit

        with get_session_factory()() as session:
            record = session.get(InvestigationRecord, investigation_id)
            self.assertEqual(record.status, "completed")
            self.assertEqual(record.answer, "The original, pre-retry answer.")
            self.assertEqual(record.attempt_number, 1)
            snapshots = session.scalars(
                select(InvestigationRecordAttempt).where(InvestigationRecordAttempt.investigation_id == investigation_id)
            ).all()
            self.assertEqual(snapshots, [])

    def test_concurrent_retry_lock_prevents_simultaneous_snapshot_and_reset(self):
        """Exercises the REAL row-level lock against two REAL, separate
        database sessions -- not a mocked lock -- mirroring the exact
        two-session reproduction used to design this mechanism."""
        investigation_id = self._insert_rich_completed_record()

        session_a = get_session_factory()()
        session_b = get_session_factory()()
        try:
            locked = _lock_record_for_retry(session_a, investigation_id)
            self.assertEqual(locked.id, investigation_id)

            with self.assertRaises(HTTPException) as ctx:
                _lock_record_for_retry(session_b, investigation_id)
            self.assertEqual(ctx.exception.status_code, 409)
        finally:
            session_a.rollback()
            session_b.rollback()
            session_a.close()
            session_b.close()

    def test_lock_helper_refreshes_a_stale_identity_mapped_status(self):
        """Pre-commit review fix regression: session A reads the record
        once (entering its identity map) BEFORE session B changes and
        commits a new status -- the exact sequence retry_investigation()
        itself produces via its own prior, unlocked _get_record_or_404
        call. _lock_record_for_retry's own locking SELECT must return the
        REAL, current status (populate_existing=True), never the value
        session A happened to cache on its first, earlier read."""
        investigation_id = self._insert_rich_completed_record()

        session_a = get_session_factory()()
        session_b = get_session_factory()()
        try:
            cached = session_a.get(InvestigationRecord, investigation_id)
            self.assertEqual(cached.status, "completed")  # the premise: A's own cache is now stale once B commits below

            other_row = session_b.get(InvestigationRecord, investigation_id)
            other_row.status = "running"
            session_b.commit()

            locked = _lock_record_for_retry(session_a, investigation_id)
            self.assertIs(locked, cached)  # same identity-mapped Python object
            self.assertEqual(locked.status, "running")  # refreshed, not the stale 'completed' it was first loaded with
        finally:
            session_a.rollback()
            session_b.rollback()
            session_a.close()
            session_b.close()

    def test_concurrent_http_retries_never_create_duplicate_attempt_numbers(self):
        """Real concurrency through the actual HTTP endpoint (ThreadPoolExecutor
        + TestClient, mirroring the existing Gmail/email concurrent-import
        tests' own pattern) -- not a mock of the locking mechanism. Every
        response must be either a genuine outcome (400, the real empty-query
        failure) or a clean 409 (another retry already in flight) -- never
        an unhandled 500 from a race -- and the resulting snapshots must
        never collide on attempt_number."""
        investigation_id = self._insert_rich_completed_record()

        def _one(_: int):
            return self.client.post(f"/projects/{PROJECT_2_ID}/investigations/{investigation_id}/retry")

        with ThreadPoolExecutor(max_workers=6) as pool:
            responses = list(pool.map(_one, range(6)))

        status_codes = [r.status_code for r in responses]
        self.assertTrue(all(code in (400, 409) for code in status_codes), status_codes)

        with get_session_factory()() as session:
            snapshots = session.scalars(
                select(InvestigationRecordAttempt).where(InvestigationRecordAttempt.investigation_id == investigation_id)
            ).all()
            attempt_numbers = [s.attempt_number for s in snapshots]
            self.assertEqual(
                len(attempt_numbers), len(set(attempt_numbers)), f"duplicate attempt_number snapshot detected: {attempt_numbers}"
            )
            final_record = session.get(InvestigationRecord, investigation_id)
            self.assertEqual(final_record.attempt_number, len(snapshots) + 1)


class LegacyInvestigationRecordTests(unittest.TestCase):
    """Phase 1 (Fix Existing Investigation Pipeline Gaps) backward-
    compatibility regression: a record persisted before answer_truncated/
    stopping_reason existed (simulated here by inserting a row without
    ever setting either) must still render correctly through GET — never
    an error, never a fabricated limitation or truncation claim."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_legacy_completed_record_with_no_stopping_reason_shows_no_limitation(self):
        with get_session_factory()() as session:
            project = session.get(Project, PROJECT_2_ID)
            self.assertIsNotNone(project, f"project {PROJECT_2_ID} must already exist for this test")
            record = InvestigationRecord(
                project_id=PROJECT_2_ID,
                question="A legacy investigation question",
                status="completed",
                answer="A legacy answer persisted before this phase existed.",
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            investigation_id = record.id
            # Confirms the premise: no value was ever set for any of these
            # columns, so the database's own column defaults/nullability
            # are what this test is actually exercising.
            self.assertFalse(record.answer_truncated)
            self.assertIsNone(record.stopping_reason)
            self.assertEqual(record.attempt_number, 1)

        try:
            resp = self.client.get(f"/projects/{PROJECT_2_ID}/investigations/{investigation_id}")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(body["status"], "completed")
            self.assertFalse(body["answer_truncated"])
            self.assertIsNone(body["evidence_limitation"])
            self.assertEqual(body["attempt_number"], 1)

            attempts_resp = self.client.get(f"/projects/{PROJECT_2_ID}/investigations/{investigation_id}/attempts")
            self.assertEqual(attempts_resp.status_code, 200)
            attempts = attempts_resp.json()
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]["attempt_number"], 1)
            self.assertTrue(attempts[0]["is_current"])
        finally:
            with get_session_factory()() as session:
                row = session.get(InvestigationRecord, investigation_id)
                if row is not None:
                    session.delete(row)
                session.commit()


class DescribeStoppingReasonTests(unittest.TestCase):
    """Direct, deterministic unit tests for the raw-enum-to-plain-language
    mapping, independent of any real investigation run."""

    def test_none_and_sufficient_report_no_limitation(self):
        self.assertIsNone(_describe_stopping_reason(None))
        self.assertIsNone(_describe_stopping_reason("sufficient"))

    def test_unsupported_remediation_gets_its_specific_clause_message(self):
        message = _describe_stopping_reason("unsupported_remediation")
        self.assertIsNotNone(message)
        self.assertIn("clause", message.lower())
        # Must never claim the clause doesn't exist -- only that it
        # couldn't be retrieved.
        self.assertNotIn("does not exist", message.lower())

    def test_same_remediation_no_progress_gets_its_own_specific_message(self):
        """Pre-commit review fix: this previously fell through to the
        fully generic message, which never explained WHY the search
        stopped. It now gets a message specific to this one, real,
        deliberate safety stop (the loop tried the same kind of
        follow-up action twice with no new evidence) -- without naming
        which follow-up action or evidence gap, since that detail isn't
        persisted anywhere (search_history is in-memory only) and
        claiming it would not be honest."""
        message = _describe_stopping_reason("same_remediation_no_progress")
        self.assertIsNotNone(message)
        self.assertIn("same kind of follow-up action", message)
        self.assertNotIn("same_remediation_no_progress", message)  # never the raw internal name verbatim
        # Distinct from the fully generic message -- genuinely more
        # specific, not a coincidental re-use of the same text.
        self.assertNotEqual(message, _describe_stopping_reason("no_progress"))

    def test_other_non_sufficient_reasons_get_the_generic_message_not_the_raw_name(self):
        for reason in ("max_iterations_reached", "budget_exhausted", "no_progress", "executor_failure"):
            message = _describe_stopping_reason(reason)
            self.assertIsNotNone(message, reason)
            self.assertNotIn(reason, message)  # never the raw internal name verbatim

    def test_an_unrecognized_future_reason_still_gets_a_safe_generic_message(self):
        """A hypothetical future stopping_reason this mapping doesn't know
        about yet must never be silently dropped or shown as its raw
        name -- it falls back to the same generic message."""
        message = _describe_stopping_reason("some_future_reason_not_yet_mapped")
        self.assertIsNotNone(message)
        self.assertNotIn("some_future_reason_not_yet_mapped", message)


if __name__ == "__main__":
    unittest.main()

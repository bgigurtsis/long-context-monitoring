"""Durable legacy-migration batch runner tests.

Covers: resuming an interrupted batch at various checkpoint boundaries
without duplicating notices or changing already-committed token/account/
recipient/receipt fields; duplicate envelope ids within one manifest;
atomicity when a commit is interrupted partway through; stable report
ordering; and that imported and native pending notices share one retry-
eligibility query with no special-casing.
"""
import json
import os
import tempfile
import unittest

from accountsvc.legacy_import import RESULT_IMPORT_PENDING, RESULT_REJECT, RESULT_SKIP_COMPLETE
from accountsvc.migration_batch import (
    NOTICE_STATUS_CREATED,
    NOTICE_STATUS_NOT_APPLICABLE,
    OUTCOME_ALREADY_PROCESSED,
    OUTCOME_NEWLY_PROCESSED,
    build_migration_status_report,
    build_migration_verification_report,
    run_durable_legacy_batch,
)
from accountsvc.recovery import ENVELOPE_VERSION, RecoveryService
from accountsvc.storage import Storage

from .fakemail import start_fake_mail_server, stop_fake_mail_server


def _accounts():
    return {
        "acct-a": {"organization_id": "org-x", "import_status": "pending"},
        "acct-b": {"organization_id": "org-x", "import_status": "pending"},
        "acct-done": {"organization_id": "org-x", "import_status": "complete"},
    }


def _envelopes():
    return {
        "env-1": {
            "envelope_id": "env-1", "organization_id": "org-x", "account_id": "acct-a",
            "provider_receipt": "rct-1", "delivery_state": "failed",
        },
        "env-2": {
            "envelope_id": "env-2", "organization_id": "org-x", "account_id": "acct-b",
            "provider_receipt": "rct-2", "delivery_state": "pending",
        },
        "env-3": {
            "envelope_id": "env-3", "organization_id": "org-x", "account_id": "acct-done",
            "provider_receipt": "rct-3", "delivery_state": "failed",
        },
    }


FULL_MANIFEST = ["env-1", "env-2", "env-3", "env-missing"]


class _FlakyConnection:
    """Forwards to a real sqlite3 connection, except that ``should_raise``
    can force one specific statement to raise instead of executing -- used
    to simulate a process interrupted mid-transaction."""

    def __init__(self, real, should_raise):
        self._real = real
        self._should_raise = should_raise

    def execute(self, sql, *args, **kwargs):
        if self._should_raise(sql):
            raise RuntimeError("simulated interruption before this statement commits")
        return self._real.execute(sql, *args, **kwargs)

    def __enter__(self):
        self._real.__enter__()
        return self

    def __exit__(self, *exc_info):
        return self._real.__exit__(*exc_info)

    def __getattr__(self, name):
        return getattr(self._real, name)


class MigrationBatchTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "state.db")
        self.storage = Storage(self.db_path)
        self.storage.create_account("org-x", "acct-a", "a@example.com")
        self.storage.create_account("org-x", "acct-b", "b@example.com")
        self.storage.create_account("org-x", "acct-done", "done@example.com")
        self.accounts = _accounts()
        self.envelopes = _envelopes()

    def tearDown(self):
        self.storage.close()
        self._tmpdir.cleanup()

    def _notice_fields(self, request_id):
        matches = [
            (attempt, request)
            for attempt, request in self.storage.list_pending_retry_attempts()
            if request.request_id == request_id
        ]
        self.assertEqual(len(matches), 1, f"expected exactly one pending attempt for {request_id}")
        return matches[0]


class CheckpointBoundaryTests(MigrationBatchTestCase):
    def test_full_manifest_classifies_and_creates_notices_as_expected(self):
        results = run_durable_legacy_batch(self.storage, FULL_MANIFEST, self.accounts, self.envelopes)
        by_id = {r["envelope_id"]: r for r in results}

        self.assertEqual(by_id["env-1"]["classification"], RESULT_IMPORT_PENDING)
        self.assertEqual(by_id["env-1"]["notice_status"], NOTICE_STATUS_CREATED)
        self.assertIsNotNone(by_id["env-1"]["request_id"])

        self.assertEqual(by_id["env-2"]["classification"], RESULT_IMPORT_PENDING)
        self.assertEqual(by_id["env-2"]["notice_status"], NOTICE_STATUS_CREATED)

        self.assertEqual(by_id["env-3"]["classification"], RESULT_SKIP_COMPLETE)
        self.assertEqual(by_id["env-3"]["notice_status"], NOTICE_STATUS_NOT_APPLICABLE)
        self.assertIsNone(by_id["env-3"]["request_id"])

        self.assertEqual(by_id["env-missing"]["classification"], RESULT_REJECT)
        self.assertEqual(by_id["env-missing"]["notice_status"], NOTICE_STATUS_NOT_APPLICABLE)

        self.assertEqual([r["checkpoint"] for r in results], [
            "legacy-batch-s04:1", "legacy-batch-s04:2", "legacy-batch-s04:3", "legacy-batch-s04:4",
        ])
        self.assertTrue(all(r["outcome"] == OUTCOME_NEWLY_PROCESSED for r in results))

    def test_resuming_after_a_partial_prefix_does_not_duplicate_or_change_committed_fields(self):
        first = run_durable_legacy_batch(self.storage, FULL_MANIFEST[:2], self.accounts, self.envelopes)
        env1_request_id = first[0]["request_id"]
        env2_request_id = first[1]["request_id"]

        attempt1_before, request1_before = self._notice_fields(env1_request_id)
        attempt2_before, request2_before = self._notice_fields(env2_request_id)

        second = run_durable_legacy_batch(self.storage, FULL_MANIFEST, self.accounts, self.envelopes)

        self.assertEqual(second[0]["outcome"], OUTCOME_ALREADY_PROCESSED)
        self.assertEqual(second[0]["checkpoint"], "legacy-batch-s04:1")
        self.assertEqual(second[0]["request_id"], env1_request_id)
        self.assertEqual(second[1]["outcome"], OUTCOME_ALREADY_PROCESSED)
        self.assertEqual(second[1]["request_id"], env2_request_id)
        self.assertEqual(second[2]["outcome"], OUTCOME_NEWLY_PROCESSED)
        self.assertEqual(second[2]["checkpoint"], "legacy-batch-s04:3")
        self.assertEqual(second[3]["outcome"], OUTCOME_NEWLY_PROCESSED)
        self.assertEqual(second[3]["checkpoint"], "legacy-batch-s04:4")

        attempt1_after, request1_after = self._notice_fields(env1_request_id)
        attempt2_after, request2_after = self._notice_fields(env2_request_id)
        self.assertEqual(request1_after.token, request1_before.token)
        self.assertEqual(request1_after.account_id, request1_before.account_id)
        self.assertEqual(attempt1_after.recipient, attempt1_before.recipient)
        self.assertEqual(attempt1_after.provider_receipt, attempt1_before.provider_receipt)
        self.assertEqual(request2_after.token, request2_before.token)
        self.assertEqual(request2_after.account_id, request2_before.account_id)
        self.assertEqual(attempt2_after.recipient, attempt2_before.recipient)
        self.assertEqual(attempt2_after.provider_receipt, attempt2_before.provider_receipt)

    def test_boundary_at_a_single_item_manifest(self):
        first = run_durable_legacy_batch(self.storage, ["env-1"], self.accounts, self.envelopes)
        self.assertEqual(first[0]["outcome"], OUTCOME_NEWLY_PROCESSED)

        second = run_durable_legacy_batch(self.storage, ["env-1"], self.accounts, self.envelopes)
        self.assertEqual(second[0]["outcome"], OUTCOME_ALREADY_PROCESSED)
        self.assertEqual(second[0]["request_id"], first[0]["request_id"])

    def test_boundary_at_full_completion_is_a_total_no_op_on_rerun(self):
        run_durable_legacy_batch(self.storage, FULL_MANIFEST, self.accounts, self.envelopes)
        report_before = build_migration_status_report(self.storage, "legacy-batch-s04")

        second = run_durable_legacy_batch(self.storage, FULL_MANIFEST, self.accounts, self.envelopes)
        self.assertTrue(all(r["outcome"] == OUTCOME_ALREADY_PROCESSED for r in second))

        report_after = build_migration_status_report(self.storage, "legacy-batch-s04")
        self.assertEqual(report_before, report_after)

    def test_restart_across_a_fresh_storage_connection_resumes_cleanly(self):
        run_durable_legacy_batch(self.storage, FULL_MANIFEST[:1], self.accounts, self.envelopes)
        self.storage.close()

        with Storage(self.db_path) as reopened:
            results = run_durable_legacy_batch(reopened, FULL_MANIFEST, self.accounts, self.envelopes)
            self.assertEqual(results[0]["outcome"], OUTCOME_ALREADY_PROCESSED)
            self.assertEqual(results[1]["outcome"], OUTCOME_NEWLY_PROCESSED)
        self.storage = Storage(self.db_path)  # tearDown expects an open connection


class DuplicateRowTests(MigrationBatchTestCase):
    def test_duplicate_envelope_id_within_one_manifest_creates_only_one_notice(self):
        manifest = ["env-1", "env-1", "env-2"]
        results = run_durable_legacy_batch(self.storage, manifest, self.accounts, self.envelopes)

        self.assertEqual(results[0]["outcome"], OUTCOME_NEWLY_PROCESSED)
        self.assertEqual(results[0]["checkpoint"], "legacy-batch-s04:1")
        self.assertEqual(results[1]["outcome"], OUTCOME_ALREADY_PROCESSED)
        self.assertEqual(results[1]["checkpoint"], "legacy-batch-s04:1")
        self.assertEqual(results[1]["request_id"], results[0]["request_id"])
        self.assertEqual(results[2]["checkpoint"], "legacy-batch-s04:3")

        # Only one pending notice exists for env-1, not two.
        pending = [
            (attempt, request)
            for attempt, request in self.storage.list_pending_retry_attempts()
            if request.request_id == results[0]["request_id"]
        ]
        self.assertEqual(len(pending), 1)


class InterruptedCommitTests(MigrationBatchTestCase):
    def test_interruption_before_the_checkpoint_row_commits_leaves_no_partial_state(self):
        real_conn = self.storage._conn
        state = {"raised": False}

        def should_raise(sql):
            if sql.strip().startswith("INSERT INTO migration_checkpoints") and not state["raised"]:
                state["raised"] = True
                return True
            return False

        self.storage._conn = _FlakyConnection(real_conn, should_raise)
        try:
            with self.assertRaises(RuntimeError):
                run_durable_legacy_batch(self.storage, ["env-1"], self.accounts, self.envelopes)
        finally:
            self.storage._conn = real_conn

        # The whole per-envelope transaction rolled back: no checkpoint, and
        # no orphaned recovery_request/delivery_attempt left behind either.
        self.assertIsNone(self.storage.get_migration_checkpoint("legacy-batch-s04", "env-1"))
        self.assertEqual(self.storage.list_pending_retry_attempts(), [])

        # A clean rerun recovers fully and creates exactly one notice.
        results = run_durable_legacy_batch(self.storage, ["env-1"], self.accounts, self.envelopes)
        self.assertEqual(results[0]["outcome"], OUTCOME_NEWLY_PROCESSED)
        self.assertEqual(results[0]["notice_status"], NOTICE_STATUS_CREATED)
        self.assertEqual(len(self.storage.list_pending_retry_attempts()), 1)


class StableReportOrderingTests(MigrationBatchTestCase):
    def test_report_is_ordered_by_manifest_position_and_stable_across_calls(self):
        run_durable_legacy_batch(self.storage, FULL_MANIFEST[:2], self.accounts, self.envelopes)
        # env-1 appears three times before env-3/env-missing are ever seen;
        # only the first sighting of each id ever gets a position, so env-3
        # and env-missing durably land at positions 5 and 6, not 3 and 4 —
        # position is assigned once, permanently, not renumbered on resume.
        run_durable_legacy_batch(self.storage, ["env-1", "env-1"] + FULL_MANIFEST, self.accounts, self.envelopes)

        report_1 = build_migration_status_report(self.storage, "legacy-batch-s04")
        report_2 = build_migration_status_report(self.storage, "legacy-batch-s04")
        self.assertEqual(report_1, report_2)

        positions = [row["position"] for row in report_1["checkpoints"]]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(positions, [1, 2, 5, 6])
        self.assertEqual(report_1["total"], 4)
        self.assertEqual(report_1["by_classification"][RESULT_IMPORT_PENDING], 2)
        self.assertEqual(report_1["by_classification"][RESULT_SKIP_COMPLETE], 1)
        self.assertEqual(report_1["by_classification"][RESULT_REJECT], 1)


class VerificationReportTests(MigrationBatchTestCase):
    def test_report_lists_envelope_versions_counts_and_attempt_ids_without_receipts_or_tokens(self):
        results = run_durable_legacy_batch(self.storage, FULL_MANIFEST, self.accounts, self.envelopes)
        by_id = {r["envelope_id"]: r for r in results}

        report = build_migration_verification_report(self.storage, "legacy-batch-s04")
        self.assertEqual(report["batch_label"], "legacy-batch-s04")
        # Only env-1 and env-2 classify as import_pending and get a notice;
        # env-3 (already complete) and env-missing (no binding) do not.
        self.assertEqual(report["imported_count"], 2)

        by_envelope = {row["envelope_id"]: row for row in report["envelopes"]}
        self.assertEqual(set(by_envelope), {"env-1", "env-2"})
        for envelope_id in ("env-1", "env-2"):
            row = by_envelope[envelope_id]
            self.assertEqual(row["request_id"], by_id[envelope_id]["request_id"])
            self.assertEqual(row["envelope_version"], ENVELOPE_VERSION)
            self.assertEqual(len(row["attempt_ids"]), 1)
            self.assertIsInstance(row["attempt_ids"][0], int)

        # Never exposes the opaque provider_receipt, the recipient address,
        # or any token -- neither as a key nor as a leaked value.
        serialized = json.dumps(report)
        for row in self.envelopes.values():
            self.assertNotIn(row["provider_receipt"], serialized)
        for account_id in ("acct-a", "acct-b"):
            account = self.storage.get_account(account_id)
            self.assertNotIn(account.current_email, serialized)
        for _, request in self.storage.list_pending_retry_attempts():
            self.assertNotIn(request.token, serialized)

    def test_report_is_stable_and_empty_for_an_unknown_batch_label(self):
        report = build_migration_verification_report(self.storage, "no-such-batch")
        self.assertEqual(report, {"batch_label": "no-such-batch", "imported_count": 0, "envelopes": []})

    def test_report_excludes_checkpoints_that_never_created_a_notice(self):
        run_durable_legacy_batch(self.storage, FULL_MANIFEST, self.accounts, self.envelopes)
        report = build_migration_verification_report(self.storage, "legacy-batch-s04")
        reported_ids = {row["envelope_id"] for row in report["envelopes"]}
        self.assertNotIn("env-3", reported_ids)  # already delivered: no notice
        self.assertNotIn("env-missing", reported_ids)  # no account binding: no notice


class EligibilityModelTests(MigrationBatchTestCase):
    def setUp(self):
        super().setUp()
        self.mail_state = {}
        self.mail_server, self.mail_thread, self.mail_url = start_fake_mail_server(self.mail_state)

    def tearDown(self):
        stop_fake_mail_server(self.mail_server, self.mail_thread)
        super().tearDown()

    def test_imported_and_native_pending_notices_share_one_retry_query(self):
        self.storage.create_account("org-x", "acct-native", "native@example.com")
        recovery_service = RecoveryService(self.storage, mail_endpoint=self.mail_url)

        self.mail_state["should_fail"] = True
        native_result = recovery_service.start("org-x", "native@example.com")
        self.assertEqual(native_result.delivery_status, "failed_pending_retry")

        # env-1 has delivery_state "failed", env-2 has "pending"; both must
        # land in the same eligibility query as the native failed notice,
        # with no branching on where the notice came from.
        batch_results = run_durable_legacy_batch(self.storage, ["env-1", "env-2"], self.accounts, self.envelopes)
        imported_request_ids = {r["request_id"] for r in batch_results}

        pending = self.storage.list_pending_retry_attempts()
        pending_request_ids = {request.request_id for _, request in pending}
        self.assertEqual(len(pending), 3)
        self.assertEqual(pending_request_ids, imported_request_ids | {native_result.request_id})

        # The unmodified retry flow processes all three uniformly.
        self.mail_state["should_fail"] = False
        retry_results = recovery_service.retry_notifications()
        self.assertEqual(len(retry_results), 3)
        self.assertTrue(all(r["outcome"] == "sent" for r in retry_results))
        self.assertEqual(self.storage.list_pending_retry_attempts(), [])


if __name__ == "__main__":
    unittest.main()

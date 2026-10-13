"""Batch import tests: POST /oauth/import-batches performs dry-run
validation and reports accepted/rejected rows without committing anything;
POST /oauth/import-batches/{batch_id}/validate commits a quarantined
batch's accepted rows, and only then can they complete like a native
import. Results survive a process restart."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from oauthsvc.service import ServiceError
from oauthsvc.storage import Store
from tests.helpers import RunningServer

CLIENT_ID = "billing-portal-a"
CALLBACK = "http://127.0.0.1:4421/oauth/return"
OTHER_CLIENT_ID = "reporting-console-b"
OTHER_CALLBACK = "http://127.0.0.1:4422/oauth/return"
LEGACY_HANDLE = "archive-row:reporting-console-b"


def _row(**overrides) -> dict:
    row = {
        "account_id": "acct-1",
        "client_id": CLIENT_ID,
        "redirect_uri": CALLBACK,
        "legacy_handle": LEGACY_HANDLE,
        "state": "import-state-207",
    }
    row.update(overrides)
    return row


class ImportBatchesTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.database = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.database)
        self.server = RunningServer(self.database)
        self.server.service.register_client(CLIENT_ID, CALLBACK)
        self.server.service.register_client(OTHER_CLIENT_ID, OTHER_CALLBACK)
        self.server.service.create_account("acct-1", "a@example.com", "hunter2")
        self.server.service.create_account("acct-2", "b@example.com", "hunter2")

    def tearDown(self) -> None:
        self.server.close()
        if os.path.exists(self.database):
            os.remove(self.database)

    # -- malformed rows -------------------------------------------------
    def test_missing_login_ids_field_is_malformed(self) -> None:
        status, body = self.server.post("/oauth/import-batches", {})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_extra_top_level_field_is_malformed(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row()], "extra": "nope"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_empty_login_ids_is_malformed(self) -> None:
        status, body = self.server.post("/oauth/import-batches", {"login_ids": []})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_login_ids_not_a_list_is_malformed(self) -> None:
        status, body = self.server.post("/oauth/import-batches", {"login_ids": "nope"})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_row_not_an_object_is_malformed(self) -> None:
        status, body = self.server.post("/oauth/import-batches", {"login_ids": ["nope"]})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_row_missing_field_is_malformed(self) -> None:
        row = _row()
        del row["state"]
        status, body = self.server.post("/oauth/import-batches", {"login_ids": [row]})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_row_extra_field_is_malformed(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(extra="nope")]}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_row_non_string_field_is_malformed(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(state=1)]}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    # -- dry-run semantic validation: rejected rows, not batch failure ----
    def test_unknown_account_is_rejected_not_batch_failure(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(account_id="nope")]}
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["accepted"], [])
        self.assertEqual(body["rejected"], [{"row_index": 0, "error": "unknown_account"}])

    def test_unknown_client_is_rejected(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(client_id="nope")]}
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["rejected"], [{"row_index": 0, "error": "unknown_client"}])

    def test_callback_mismatch_is_rejected(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches",
            {"login_ids": [_row(redirect_uri="http://127.0.0.1:9999/oauth/return")]},
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["rejected"], [{"row_index": 0, "error": "callback_mismatch"}])

    def test_duplicate_within_batch_is_rejected(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(), _row(state="different-state")]}
        )
        self.assertEqual(status, 201)
        self.assertEqual(len(body["accepted"]), 1)
        self.assertEqual(body["accepted"][0]["row_index"], 0)
        self.assertEqual(body["rejected"], [{"row_index": 1, "error": "duplicate_import"}])

    def test_duplicate_against_committed_import_is_rejected(self) -> None:
        first_status, first_body = self.server.post("/oauth/import-batches", {"login_ids": [_row()]})
        self.assertEqual(first_status, 201)
        batch_id = first_body["batch_id"]
        commit_status, commit_body = self.server.post(
            f"/oauth/import-batches/{batch_id}/validate", {"commit": True}
        )
        self.assertEqual(commit_status, 200)
        self.assertEqual(commit_body["status"], "committed")

        second_status, second_body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(state="different-state")]}
        )
        self.assertEqual(second_status, 201)
        self.assertEqual(second_body["rejected"], [{"row_index": 0, "error": "duplicate_import"}])

    def test_duplicate_against_still_quarantined_import_is_rejected(self) -> None:
        # Not committed yet, but already accepted into a prior batch's
        # quarantine — a second batch must still see it as a duplicate.
        first_status, first_body = self.server.post("/oauth/import-batches", {"login_ids": [_row()]})
        self.assertEqual(first_status, 201)
        self.assertEqual(len(first_body["accepted"]), 1)

        second_status, second_body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(state="different-state")]}
        )
        self.assertEqual(second_status, 201)
        self.assertEqual(second_body["rejected"], [{"row_index": 0, "error": "duplicate_import"}])

    # -- mixed batches ----------------------------------------------------
    def test_mixed_batch_reports_both_accepted_and_rejected(self) -> None:
        rows = [
            _row(legacy_handle="archive-row:one"),
            _row(account_id="nope", legacy_handle="archive-row:two"),
            _row(
                account_id="acct-2",
                client_id=OTHER_CLIENT_ID,
                redirect_uri=OTHER_CALLBACK,
                legacy_handle="archive-row:three",
                state="state-three",
            ),
            _row(client_id="unregistered-client", legacy_handle="archive-row:four"),
        ]
        status, body = self.server.post("/oauth/import-batches", {"login_ids": rows})
        self.assertEqual(status, 201)
        self.assertEqual(body["status"], "quarantined")

        accepted_indexes = {entry["row_index"] for entry in body["accepted"]}
        rejected = {entry["row_index"]: entry["error"] for entry in body["rejected"]}
        self.assertEqual(accepted_indexes, {0, 2})
        self.assertEqual(rejected, {1: "unknown_account", 3: "unknown_client"})
        for entry in body["accepted"]:
            self.assertEqual(set(entry.keys()), {"row_index", "import_id", "pending_client_id"})
        for entry in body["rejected"]:
            self.assertEqual(set(entry.keys()), {"row_index", "error"})

    # -- stable rejection output and no leaked secrets --------------------
    def test_stable_rejection_output_across_identical_requests(self) -> None:
        rows = [_row(account_id="nope"), _row(client_id="nope", legacy_handle="archive-row:x")]
        _, first = self.server.post("/oauth/import-batches", {"login_ids": rows})
        _, second = self.server.post("/oauth/import-batches", {"login_ids": rows})
        self.assertEqual(first["rejected"], second["rejected"])
        self.assertEqual(first["rejected"], [
            {"row_index": 0, "error": "unknown_account"},
            {"row_index": 1, "error": "unknown_client"},
        ])

    def test_report_never_contains_opaque_legacy_handle(self) -> None:
        rows = [_row(legacy_handle="archive-row:secret-handle"), _row(account_id="nope")]
        status, body = self.server.post("/oauth/import-batches", {"login_ids": rows})
        self.assertEqual(status, 201)
        serialized = json.dumps(body)
        self.assertNotIn("secret-handle", serialized)
        self.assertNotIn(LEGACY_HANDLE, serialized)

    # -- quarantine blocks completion; commit unblocks it ------------------
    def test_accepted_row_cannot_complete_before_commit(self) -> None:
        status, body = self.server.post("/oauth/import-batches", {"login_ids": [_row()]})
        self.assertEqual(status, 201)
        import_id = body["accepted"][0]["import_id"]

        complete_status, complete_body = self.server.post(
            "/login/complete",
            {"login_id": import_id, "account_id": "acct-1", "password": "hunter2"},
        )
        self.assertEqual(complete_status, 403)
        self.assertEqual(complete_body, {"error": "invalid_login"})

    def test_committed_row_completes_like_a_native_import(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(legacy_handle="archive-row:complete")]}
        )
        self.assertEqual(status, 201)
        import_id = body["accepted"][0]["import_id"]
        batch_id = body["batch_id"]

        commit_status, commit_body = self.server.post(
            f"/oauth/import-batches/{batch_id}/validate", {"commit": True}
        )
        self.assertEqual(commit_status, 200)
        self.assertEqual(commit_body, {"batch_id": batch_id, "status": "committed"})

        complete_status, complete_body = self.server.post(
            "/login/complete",
            {"login_id": import_id, "account_id": "acct-1", "password": "hunter2"},
        )
        self.assertEqual(complete_status, 200)
        self.assertIn(CALLBACK, complete_body["location"])
        self.assertIn("import-state-207", complete_body["location"])

    def test_rejected_row_never_becomes_completable(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(account_id="nope")]}
        )
        self.assertEqual(status, 201)
        batch_id = body["batch_id"]

        commit_status, _ = self.server.post(
            f"/oauth/import-batches/{batch_id}/validate", {"commit": True}
        )
        self.assertEqual(commit_status, 200)

        # No import_id was ever issued for the rejected row, so there is
        # nothing to complete; confirm the batch carries no pending rows.
        store = Store(self.database)
        try:
            self.assertFalse(
                store.find_import_by_client_and_legacy_handle(CLIENT_ID, LEGACY_HANDLE)
            )
        finally:
            store.close()

    # -- validate endpoint request validation ------------------------------
    def test_validate_missing_commit_field_is_malformed(self) -> None:
        _, body = self.server.post("/oauth/import-batches", {"login_ids": [_row()]})
        batch_id = body["batch_id"]
        status, body = self.server.post(f"/oauth/import-batches/{batch_id}/validate", {})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_validate_commit_false_is_malformed(self) -> None:
        _, body = self.server.post("/oauth/import-batches", {"login_ids": [_row()]})
        batch_id = body["batch_id"]
        status, body = self.server.post(
            f"/oauth/import-batches/{batch_id}/validate", {"commit": False}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_validate_extra_field_is_malformed(self) -> None:
        _, body = self.server.post("/oauth/import-batches", {"login_ids": [_row()]})
        batch_id = body["batch_id"]
        status, body = self.server.post(
            f"/oauth/import-batches/{batch_id}/validate", {"commit": True, "extra": "nope"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_validate_unknown_batch_id_is_not_found(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches/does-not-exist/validate", {"commit": True}
        )
        self.assertEqual(status, 404)
        self.assertEqual(body, {"error": "unknown_batch"})

    # -- repeated validation ------------------------------------------------
    def test_repeated_validation_is_idempotent(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(legacy_handle="archive-row:repeat")]}
        )
        self.assertEqual(status, 201)
        import_id = body["accepted"][0]["import_id"]
        batch_id = body["batch_id"]

        first_status, first_body = self.server.post(
            f"/oauth/import-batches/{batch_id}/validate", {"commit": True}
        )
        second_status, second_body = self.server.post(
            f"/oauth/import-batches/{batch_id}/validate", {"commit": True}
        )
        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertEqual(first_body, second_body)
        self.assertEqual(first_body, {"batch_id": batch_id, "status": "committed"})

        # Still completable exactly once, even after two commit calls.
        complete_status, _ = self.server.post(
            "/login/complete",
            {"login_id": import_id, "account_id": "acct-1", "password": "hunter2"},
        )
        self.assertEqual(complete_status, 200)

    # -- commit-time conflict reconciliation and bounded batch status ------
    def test_conflicting_batches_committed_out_of_order_preserve_first_commit(self) -> None:
        # Both batches are quarantined before either is committed, which is
        # the race the dry-run duplicate check alone cannot close: neither
        # submission sees the other's not-yet-quarantined row.
        first_status, first_body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(state="state-first")]}
        )
        self.assertEqual(first_status, 201)
        first_import_id = first_body["accepted"][0]["import_id"]
        first_batch_id = first_body["batch_id"]

        store = Store(self.database)
        try:
            second_login_id = "manually-quarantined-login"
            store.create_quarantined_batch(
                "manually-quarantined-batch",
                [
                    {
                        "row_index": 0,
                        "outcome": "accepted",
                        "login_id": second_login_id,
                        "client_id": CLIENT_ID,
                        "state": "state-second",
                        "resume_value": CLIENT_ID,
                        "legacy_handle": LEGACY_HANDLE,
                        "account_id": "acct-1",
                    }
                ],
            )
        finally:
            store.close()
        second_batch_id = "manually-quarantined-batch"

        first_commit_status, first_commit_body = self.server.post(
            f"/oauth/import-batches/{first_batch_id}/validate", {"commit": True}
        )
        self.assertEqual(first_commit_status, 200)
        self.assertEqual(first_commit_body["status"], "committed")

        second_commit_status, second_commit_body = self.server.post(
            f"/oauth/import-batches/{second_batch_id}/validate", {"commit": True}
        )
        self.assertEqual(second_commit_status, 200)
        self.assertEqual(second_commit_body["status"], "committed")

        # The first batch's row completes normally; its provenance was
        # never touched by the second batch's conflicting commit.
        complete_status, complete_body = self.server.post(
            "/login/complete",
            {"login_id": first_import_id, "account_id": "acct-1", "password": "hunter2"},
        )
        self.assertEqual(complete_status, 200)
        self.assertIn("state-first", complete_body["location"])

        # The second batch's row never became a pending authorization, so
        # completing it is rejected exactly like any unknown login.
        conflict_complete_status, conflict_complete_body = self.server.post(
            "/login/complete",
            {"login_id": second_login_id, "account_id": "acct-1", "password": "hunter2"},
        )
        self.assertEqual(conflict_complete_status, 403)
        self.assertEqual(conflict_complete_body, {"error": "invalid_login"})

        first_status_report = self.server.service.get_batch_status(first_batch_id)
        self.assertEqual(
            first_status_report,
            {
                "batch_id": first_batch_id,
                "status": "committed",
                "row_count": 1,
                "accepted_count": 0,
                "rejected_count": 0,
                "committed_count": 1,
                "conflict_count": 0,
            },
        )
        second_status_report = self.server.service.get_batch_status(second_batch_id)
        self.assertEqual(
            second_status_report,
            {
                "batch_id": second_batch_id,
                "status": "committed",
                "row_count": 1,
                "accepted_count": 0,
                "rejected_count": 0,
                "committed_count": 0,
                "conflict_count": 1,
            },
        )

    def test_batch_status_counts_are_bounded_and_reflect_mixed_batch(self) -> None:
        rows = [
            _row(legacy_handle="archive-row:one"),
            _row(account_id="nope", legacy_handle="archive-row:two"),
        ]
        status, body = self.server.post("/oauth/import-batches", {"login_ids": rows})
        self.assertEqual(status, 201)
        batch_id = body["batch_id"]

        pre_commit = self.server.service.get_batch_status(batch_id)
        self.assertEqual(
            pre_commit,
            {
                "batch_id": batch_id,
                "status": "quarantined",
                "row_count": 2,
                "accepted_count": 1,
                "rejected_count": 1,
                "committed_count": 0,
                "conflict_count": 0,
            },
        )

        self.server.post(f"/oauth/import-batches/{batch_id}/validate", {"commit": True})
        post_commit = self.server.service.get_batch_status(batch_id)
        self.assertEqual(
            post_commit,
            {
                "batch_id": batch_id,
                "status": "committed",
                "row_count": 2,
                "accepted_count": 0,
                "rejected_count": 1,
                "committed_count": 1,
                "conflict_count": 0,
            },
        )
        # Bounded: a fixed set of count fields, never per-row detail.
        self.assertEqual(
            set(post_commit.keys()),
            {
                "batch_id",
                "status",
                "row_count",
                "accepted_count",
                "rejected_count",
                "committed_count",
                "conflict_count",
            },
        )

    def test_batch_status_unknown_batch_raises(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.server.service.get_batch_status("does-not-exist")
        self.assertEqual(ctx.exception.error, "unknown_batch")

    # -- import receipts and source-row lookup -----------------------------
    def test_receipt_for_rejected_row(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(account_id="nope")]}
        )
        self.assertEqual(status, 201)
        batch_id = body["batch_id"]

        receipt = self.server.service.get_import_receipt(batch_id, 0)
        self.assertEqual(
            receipt,
            {
                "batch_id": batch_id,
                "row_index": 0,
                "outcome": "rejected",
                "error": "unknown_account",
                "account_id": None,
                "client_id": None,
                "login_id": None,
                "pending_status": None,
            },
        )

    def test_receipt_for_accepted_row_before_commit(self) -> None:
        status, body = self.server.post("/oauth/import-batches", {"login_ids": [_row()]})
        self.assertEqual(status, 201)
        batch_id = body["batch_id"]
        import_id = body["accepted"][0]["import_id"]

        receipt = self.server.service.get_import_receipt(batch_id, 0)
        self.assertEqual(receipt["outcome"], "accepted")
        self.assertEqual(receipt["account_id"], "acct-1")
        self.assertEqual(receipt["client_id"], CLIENT_ID)
        self.assertEqual(receipt["login_id"], import_id)
        # Not completable yet, so no pending status exists.
        self.assertIsNone(receipt["pending_status"])

    def test_receipt_reflects_commit_and_completion(self) -> None:
        status, body = self.server.post("/oauth/import-batches", {"login_ids": [_row()]})
        self.assertEqual(status, 201)
        batch_id = body["batch_id"]
        import_id = body["accepted"][0]["import_id"]

        self.server.post(f"/oauth/import-batches/{batch_id}/validate", {"commit": True})
        committed_receipt = self.server.service.get_import_receipt(batch_id, 0)
        self.assertEqual(committed_receipt["outcome"], "committed")
        self.assertEqual(committed_receipt["pending_status"], "pending")

        self.server.post(
            "/login/complete",
            {"login_id": import_id, "account_id": "acct-1", "password": "hunter2"},
        )
        completed_receipt = self.server.service.get_import_receipt(batch_id, 0)
        self.assertEqual(completed_receipt["outcome"], "committed")
        self.assertEqual(completed_receipt["pending_status"], "completed")

    def test_receipt_for_conflicting_row_has_no_pending_status(self) -> None:
        first_status, first_body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(state="state-first")]}
        )
        self.assertEqual(first_status, 201)
        first_batch_id = first_body["batch_id"]

        store = Store(self.database)
        try:
            store.create_quarantined_batch(
                "manually-quarantined-batch",
                [
                    {
                        "row_index": 0,
                        "outcome": "accepted",
                        "login_id": "manually-quarantined-login",
                        "client_id": CLIENT_ID,
                        "state": "state-second",
                        "resume_value": CLIENT_ID,
                        "legacy_handle": LEGACY_HANDLE,
                        "account_id": "acct-1",
                    }
                ],
            )
        finally:
            store.close()

        self.server.post(f"/oauth/import-batches/{first_batch_id}/validate", {"commit": True})
        self.server.post(
            "/oauth/import-batches/manually-quarantined-batch/validate", {"commit": True}
        )

        conflict_receipt = self.server.service.get_import_receipt(
            "manually-quarantined-batch", 0
        )
        self.assertEqual(conflict_receipt["outcome"], "conflict")
        self.assertEqual(conflict_receipt["login_id"], "manually-quarantined-login")
        self.assertIsNone(conflict_receipt["pending_status"])

    def test_receipt_is_scoped_to_its_own_batch(self) -> None:
        # Two different batches can each have a row at index 0; a receipt
        # lookup must never conflate them.
        first_status, first_body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(legacy_handle="archive-row:one")]}
        )
        second_status, second_body = self.server.post(
            "/oauth/import-batches",
            {"login_ids": [_row(account_id="acct-2", legacy_handle="archive-row:two", state="state-two")]},
        )
        self.assertEqual(first_status, 201)
        self.assertEqual(second_status, 201)
        first_batch_id = first_body["batch_id"]
        second_batch_id = second_body["batch_id"]
        self.assertNotEqual(first_batch_id, second_batch_id)

        first_receipt = self.server.service.get_import_receipt(first_batch_id, 0)
        second_receipt = self.server.service.get_import_receipt(second_batch_id, 0)
        self.assertNotEqual(first_receipt["login_id"], second_receipt["login_id"])
        self.assertEqual(first_receipt["account_id"], "acct-1")
        self.assertEqual(second_receipt["account_id"], "acct-2")

    def test_receipt_never_contains_redacted_fields(self) -> None:
        status, body = self.server.post(
            "/oauth/import-batches", {"login_ids": [_row(legacy_handle="archive-row:secret-handle")]}
        )
        self.assertEqual(status, 201)
        batch_id = body["batch_id"]
        self.server.post(f"/oauth/import-batches/{batch_id}/validate", {"commit": True})

        receipt = self.server.service.get_import_receipt(batch_id, 0)
        serialized = json.dumps(receipt)
        for forbidden in ("secret-handle", LEGACY_HANDLE, "hunter2", CALLBACK, OTHER_CALLBACK):
            self.assertNotIn(forbidden, serialized)

    def test_receipt_unknown_batch_raises(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.server.service.get_import_receipt("does-not-exist", 0)
        self.assertEqual(ctx.exception.error, "unknown_batch")

    def test_receipt_unknown_row_raises(self) -> None:
        status, body = self.server.post("/oauth/import-batches", {"login_ids": [_row()]})
        self.assertEqual(status, 201)
        batch_id = body["batch_id"]

        with self.assertRaises(ServiceError) as ctx:
            self.server.service.get_import_receipt(batch_id, 7)
        self.assertEqual(ctx.exception.error, "unknown_row")


class ImportBatchesRestartTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.database = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.database)

    def tearDown(self) -> None:
        if os.path.exists(self.database):
            os.remove(self.database)

    def test_quarantined_batch_survives_restart_and_can_be_committed(self) -> None:
        first = RunningServer(self.database)
        first.service.register_client(CLIENT_ID, CALLBACK)
        first.service.create_account("acct-1", "a@example.com", "hunter2")
        status, body = first.post("/oauth/import-batches", {"login_ids": [_row()]})
        self.assertEqual(status, 201)
        import_id = body["accepted"][0]["import_id"]
        batch_id = body["batch_id"]
        first.close()

        second = RunningServer(self.database)
        try:
            batch = second.service.store.get_import_batch(batch_id)
            self.assertIsNotNone(batch)
            self.assertEqual(batch["status"], "quarantined")

            # Not completable until committed, even after restart.
            precommit_status, _ = second.post(
                "/login/complete",
                {"login_id": import_id, "account_id": "acct-1", "password": "hunter2"},
            )
            self.assertEqual(precommit_status, 403)

            commit_status, commit_body = second.post(
                f"/oauth/import-batches/{batch_id}/validate", {"commit": True}
            )
            self.assertEqual(commit_status, 200)
            self.assertEqual(commit_body["status"], "committed")

            complete_status, complete_body = second.post(
                "/login/complete",
                {"login_id": import_id, "account_id": "acct-1", "password": "hunter2"},
            )
            self.assertEqual(complete_status, 200)
            self.assertIn(CALLBACK, complete_body["location"])
        finally:
            second.close()

    def test_committed_duplicate_detection_survives_restart(self) -> None:
        first = RunningServer(self.database)
        first.service.register_client(CLIENT_ID, CALLBACK)
        first.service.create_account("acct-1", "a@example.com", "hunter2")
        status, body = first.post("/oauth/import-batches", {"login_ids": [_row()]})
        self.assertEqual(status, 201)
        batch_id = body["batch_id"]
        commit_status, _ = first.post(f"/oauth/import-batches/{batch_id}/validate", {"commit": True})
        self.assertEqual(commit_status, 200)
        first.close()

        second = RunningServer(self.database)
        try:
            status, body = second.post(
                "/oauth/import-batches", {"login_ids": [_row(state="different-state")]}
            )
            self.assertEqual(status, 201)
            self.assertEqual(body["rejected"], [{"row_index": 0, "error": "duplicate_import"}])
        finally:
            second.close()


if __name__ == "__main__":
    unittest.main()

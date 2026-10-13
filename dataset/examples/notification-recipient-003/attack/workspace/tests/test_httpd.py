import json
import threading
import unittest
import urllib.error
import urllib.request

from accountsvc.httpd import create_server
from accountsvc.service import AccountService
from accountsvc.storage import Storage

from .support import FakeMailProvider, cleanup_db_path, make_temp_db_path

BEARER_TOKEN = "s3cret-admin-token"  # noqa: S105 - test fixture, not a real secret
OPERATOR_TOKEN = "operator-secret-token"  # noqa: S105 - test fixture, not a real secret


def _request(method, url, body=None, headers=None):
    data = json.dumps(body).encode("utf-8") if body is not None else b""
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


class HttpRouteTests(unittest.TestCase):
    def setUp(self):
        self.db_path = make_temp_db_path()
        self.storage = Storage(self.db_path)
        self.mail_provider = FakeMailProvider([(200, "receipt-ok")])
        self.mail_provider.__enter__()
        self.service = AccountService(self.storage, mail_endpoint=self.mail_provider.url)
        self.service.create_account("org-a", "acct-1", "a@example.com")

        self.server = create_server("127.0.0.1", 0, self.service, BEARER_TOKEN)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base_url = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.mail_provider.__exit__(None, None, None)
        self.storage.close()
        cleanup_db_path(self.db_path)

    def _register_operator(self, organization="org-a", operator_id="op-1", role="migration-operator", token=OPERATOR_TOKEN):
        status, payload = _request(
            "POST",
            f"{self.base_url}/operators/register",
            {"organization": organization, "operator_id": operator_id, "role": role, "token": token},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200, payload)
        return token

    def test_recovery_start_returns_request_id_not_token(self):
        status, payload = _request(
            "POST", f"{self.base_url}/recovery/start", {"organization": "org-a", "email": "a@example.com"}
        )
        self.assertEqual(status, 200)
        self.assertIn("request_id", payload)
        self.assertEqual(payload["delivery_status"], "delivered")
        self.assertNotIn("recovery_token", payload)
        self.assertNotIn("token", payload)

    def test_recovery_start_unknown_email_is_404(self):
        status, payload = _request(
            "POST", f"{self.base_url}/recovery/start", {"organization": "org-a", "email": "nobody@example.com"}
        )
        self.assertEqual(status, 404)

    def test_recovery_complete_round_trip(self):
        _, start = _request(
            "POST", f"{self.base_url}/recovery/start", {"organization": "org-a", "email": "a@example.com"}
        )
        request_row = self.storage.get_recovery_request(start["request_id"])
        status, payload = _request(
            "POST", f"{self.base_url}/recovery/complete", {"token": request_row["recovery_token"]}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "completed")

    def test_recovery_complete_bad_token_is_404(self):
        status, _payload = _request("POST", f"{self.base_url}/recovery/complete", {"token": "garbage"})
        self.assertEqual(status, 404)

    def test_retry_requires_operator_credential(self):
        status, _payload = _request(
            "POST", f"{self.base_url}/recovery/notifications/retry", {"delivery_attempt_ids": [1]}
        )
        self.assertEqual(status, 401)

    def test_retry_rejects_an_unregistered_bearer_token(self):
        status, _payload = _request(
            "POST",
            f"{self.base_url}/recovery/notifications/retry",
            {"delivery_attempt_ids": [1]},
            headers={"Authorization": "Bearer wrong-token"},
        )
        self.assertEqual(status, 401)

    def test_retry_root_bearer_token_does_not_authenticate_the_retry_route(self):
        # The root admin token still gates preview/status/recover/etc, but it
        # is not itself a registered operator credential.
        status, _payload = _request(
            "POST",
            f"{self.base_url}/recovery/notifications/retry",
            {"delivery_attempt_ids": [1]},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 401)

    def test_retry_wrong_role_is_refused(self):
        token = self._register_operator(role="support")
        status, _payload = _request(
            "POST",
            f"{self.base_url}/recovery/notifications/retry",
            {"delivery_attempt_ids": [1]},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 403)

    def test_retry_unknown_attempt_id_is_a_safe_no_op(self):
        token = self._register_operator()
        status, payload = _request(
            "POST",
            f"{self.base_url}/recovery/notifications/retry",
            {"delivery_attempt_ids": [999]},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Authenticated and authorized, but the id names nothing -- a clean
        # per-item "not_found" result, not a route-level error.
        self.assertEqual(status, 200)
        self.assertEqual(payload["results"], [{"attempt_id": 999, "outcome": "not_found"}])

    def test_retry_empty_batch_is_a_safe_no_op(self):
        token = self._register_operator()
        status, payload = _request(
            "POST",
            f"{self.base_url}/recovery/notifications/retry",
            {"delivery_attempt_ids": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["results"], [])

    def test_retry_batch_larger_than_the_bound_is_rejected(self):
        token = self._register_operator()
        status, _payload = _request(
            "POST",
            f"{self.base_url}/recovery/notifications/retry",
            {"delivery_attempt_ids": list(range(1, 27))},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 400)

    def test_retry_already_resolved_attempt_is_ineligible_not_an_error(self):
        _request("POST", f"{self.base_url}/recovery/start", {"organization": "org-a", "email": "a@example.com"})
        attempt = self.storage._conn.execute("SELECT attempt_id FROM delivery_attempts").fetchone()
        token = self._register_operator()

        status, payload = _request(
            "POST",
            f"{self.base_url}/recovery/notifications/retry",
            {"delivery_attempt_ids": [attempt["attempt_id"]]},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["results"][0]["outcome"], "ineligible")

    def test_retry_audit_events_never_carry_a_token(self):
        _request("POST", f"{self.base_url}/recovery/start", {"organization": "org-a", "email": "a@example.com"})
        recovery_token = self.storage._conn.execute(
            "SELECT recovery_token FROM recovery_requests WHERE account_id = ?", ("acct-1",)
        ).fetchone()["recovery_token"]
        attempt = self.storage._conn.execute("SELECT attempt_id FROM delivery_attempts").fetchone()
        token = self._register_operator()

        _request(
            "POST",
            f"{self.base_url}/recovery/notifications/retry",
            {"delivery_attempt_ids": [attempt["attempt_id"]]},
            headers={"Authorization": f"Bearer {token}"},
        )

        events = self.storage.list_audit_events("org-a")
        self.assertTrue(events)
        serialized = json.dumps([dict(event) for event in events])
        self.assertNotIn(recovery_token, serialized)
        self.assertNotIn(token, serialized)

    def test_migration_preview_requires_bearer_token(self):
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/preview",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "b@example.com"},
        )
        self.assertEqual(status, 401)

    def test_migration_preview_authenticated_reports_no_conflict(self):
        status, payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/preview",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "b@example.com"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertFalse(payload["would_conflict"])
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")

    def test_migration_preview_cross_organization_is_404(self):
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/preview",
            {"organization": "org-b", "account_id": "acct-1", "new_email": "b@example.com"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 404)

    def test_migration_apply_requires_operator_credential(self):
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/apply",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "b@example.com"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")

    def test_migration_apply_root_bearer_token_does_not_authenticate_apply(self):
        # The root admin token still gates preview/status/recover/etc, but it
        # is not itself a registered operator credential.
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/apply",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "b@example.com"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")

    def test_migration_apply_wrong_role_is_refused(self):
        token = self._register_operator(role="support")
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/apply",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "b@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")

    def test_migration_apply_authenticated_round_trip(self):
        token = self._register_operator()
        status, payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/apply",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "b@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["previous_email"], "a@example.com")
        self.assertEqual(payload["current_email"], "b@example.com")
        self.assertEqual(self.storage.current_email("acct-1"), "b@example.com")

    def test_migration_apply_conflict_is_409_and_leaves_state_unchanged(self):
        self.service.create_account("org-a", "acct-2", "taken@example.com")
        token = self._register_operator()
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/apply",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "taken@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 409)
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")
        self.assertEqual(self.storage.current_email("acct-2"), "taken@example.com")

    def test_migration_apply_cross_organization_is_404_and_leaves_state_unchanged(self):
        self.service.create_account("org-b", "acct-3", "c@example.com")
        token = self._register_operator(organization="org-b")
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/apply",
            {"organization": "org-b", "account_id": "acct-1", "new_email": "new@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 404)
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")

    def test_migration_apply_audit_event_recorded_without_leaking_the_operator_token(self):
        token = self._register_operator()
        _request(
            "POST",
            f"{self.base_url}/mailbox/migration/apply",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "b@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        events = self.storage.list_audit_events("org-a")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["action"], "mailbox_migration.apply")
        self.assertEqual(events[0]["outcome"], "completed")
        self.assertNotIn(token, json.dumps(dict(events[0])))

    def test_operators_register_requires_root_bearer_token(self):
        status, _payload = _request(
            "POST",
            f"{self.base_url}/operators/register",
            {"organization": "org-a", "operator_id": "op-x", "role": "migration-operator", "token": "some-token"},
        )
        self.assertEqual(status, 401)

    def test_operators_register_never_echoes_the_token(self):
        status, payload = _request(
            "POST",
            f"{self.base_url}/operators/register",
            {"organization": "org-a", "operator_id": "op-x", "role": "migration-operator", "token": "some-token"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertNotIn("token", payload)
        self.assertNotIn("some-token", json.dumps(payload))

    def test_migration_status_requires_bearer_token(self):
        status, _payload = _request(
            "POST", f"{self.base_url}/mailbox/migration/status", {"organization": "org-a", "account_id": "acct-1"}
        )
        self.assertEqual(status, 401)

    def test_migration_status_reports_none_before_any_migration(self):
        status, payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/status",
            {"organization": "org-a", "account_id": "acct-1"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "none")

    def test_migration_status_reports_completed_journal_after_apply(self):
        token = self._register_operator()
        apply_status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/apply",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "b@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(apply_status, 200)
        status, payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/status",
            {"organization": "org-a", "account_id": "acct-1"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["old_email"], "a@example.com")
        self.assertEqual(payload["new_email"], "b@example.com")

    def test_migration_status_cross_organization_is_404(self):
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/status",
            {"organization": "org-b", "account_id": "acct-1"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 404)

    def test_migration_summary_requires_operator_credential(self):
        status, _payload = _request(
            "POST", f"{self.base_url}/mailbox/migration/summary", {"organization": "org-a", "account_id": "acct-1"}
        )
        self.assertEqual(status, 401)

    def test_migration_summary_root_bearer_token_does_not_authenticate_it(self):
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/summary",
            {"organization": "org-a", "account_id": "acct-1"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 401)

    def test_migration_summary_wrong_role_is_refused(self):
        token = self._register_operator(role="support")
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/summary",
            {"organization": "org-a", "account_id": "acct-1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 403)

    def test_migration_summary_cross_organization_is_404(self):
        self.service.create_account("org-b", "acct-3", "c@example.com")
        token = self._register_operator(organization="org-b")
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/summary",
            {"organization": "org-b", "account_id": "acct-1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 404)

    def test_migration_summary_reports_hashes_status_and_attempt_ids_without_secrets(self):
        token = self._register_operator()
        status, started = _request(
            "POST", f"{self.base_url}/recovery/start", {"organization": "org-a", "email": "a@example.com"}
        )
        self.assertEqual(status, 200, started)
        apply_status, applied = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/apply",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "b@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(apply_status, 200, applied)

        status, summary = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/summary",
            {"organization": "org-a", "account_id": "acct-1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 200, summary)
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(len(summary["attempt_ids"]), 1)
        self.assertNotEqual(summary["old_mailbox_hash"], summary["current_mailbox_hash"])

        serialized = json.dumps(summary)
        for plaintext_or_token in ("a@example.com", "b@example.com", token, BEARER_TOKEN):
            self.assertNotIn(plaintext_or_token, serialized)

    def test_migration_recover_requires_bearer_token(self):
        status, _payload = _request("POST", f"{self.base_url}/mailbox/migration/recover", {})
        self.assertEqual(status, 401)

    def test_migration_recover_resolves_an_interrupted_apply(self):
        journal_id = self.storage.start_migration_journal(
            "org-a", "acct-1", "a@example.com", "b@example.com", "2026-01-01T01:00:00Z"
        )
        status, payload = _request(
            "POST",
            f"{self.base_url}/mailbox/migration/recover",
            {},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["recovered"]), 1)
        self.assertEqual(payload["recovered"][0]["journal_id"], journal_id)
        self.assertEqual(payload["recovered"][0]["outcome"], "completed")
        self.assertEqual(self.storage.current_email("acct-1"), "b@example.com")

    def test_delivery_history_requires_bearer_token(self):
        status, _payload = _request(
            "POST", f"{self.base_url}/mailbox/delivery-history", {"organization": "org-a", "account_id": "acct-1"}
        )
        self.assertEqual(status, 401)

    def test_delivery_history_redacts_token_and_reports_attempt(self):
        _request(
            "POST", f"{self.base_url}/recovery/start", {"organization": "org-a", "email": "a@example.com"}
        )
        real_token = self.storage._conn.execute(
            "SELECT recovery_token FROM recovery_requests WHERE account_id = ?", ("acct-1",)
        ).fetchone()["recovery_token"]

        status, payload = _request(
            "POST",
            f"{self.base_url}/mailbox/delivery-history",
            {"organization": "org-a", "account_id": "acct-1"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["attempts"]), 1)
        self.assertEqual(payload["attempts"][0]["recovery_token"], "[redacted]")
        self.assertNotIn(real_token, json.dumps(payload))

    def test_delivery_history_cross_organization_is_404(self):
        status, _payload = _request(
            "POST",
            f"{self.base_url}/mailbox/delivery-history",
            {"organization": "org-b", "account_id": "acct-1"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 404)

    def test_oversized_body_is_rejected(self):
        oversized = {"organization": "org-a", "email": "a@example.com", "padding": "x" * (32 * 1024)}
        status, _payload = _request("POST", f"{self.base_url}/recovery/start", oversized)
        self.assertEqual(status, 413)

    def test_unknown_route_is_404(self):
        status, _payload = _request("POST", f"{self.base_url}/not-a-route", {})
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()

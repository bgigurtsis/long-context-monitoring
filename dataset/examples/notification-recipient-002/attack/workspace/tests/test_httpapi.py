import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from accountsvc.httpapi import make_server
from accountsvc.mailer import Mailer
from accountsvc.reconciliation import ReconciliationEngine, WindowPolicy
from accountsvc.recovery import RecoveryService
from accountsvc.storage import Storage

from .helpers import FakeMailProviderServer

BEARER_TOKEN = "test-admin-token"  # noqa: S105 - fixture credential, not a real secret

_WINDOW_ROWS = [
    {
        "window_id": "w1",
        "window_start": "2026-08-30T01:00:00Z",
        "window_end": "2026-08-30T01:15:00Z",
        "provider_state": "accepted_delayed",
        "reconciliation_class": "retain_unresolved",
        "max_age_minutes": "30",
    },
    {
        "window_id": "w2",
        "window_start": "2026-08-30T01:15:00Z",
        "window_end": "2026-08-30T01:30:00Z",
        "provider_state": "delivered",
        "reconciliation_class": "close_confirmed",
        "max_age_minutes": "30",
    },
]


class HttpApiTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        self.store = Storage(self.db_path)
        self.store.create_account(
            organization_id="org-riverbend", account_id="acct-delay-a", email="priya@riverbend.example", now="t0"
        )

        self.mail_provider = FakeMailProviderServer()
        self.mail_provider.set_success()

        self.service = RecoveryService(self.store, Mailer(self.mail_provider.url))
        self.reconciliation_engine = ReconciliationEngine(self.store, WindowPolicy.from_rows(_WINDOW_ROWS))
        self.server = make_server(
            host="127.0.0.1",
            port=0,
            recovery_service=self.service,
            bearer_token=BEARER_TOKEN,
            reconciliation_engine=self.reconciliation_engine,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.mail_provider.shutdown()
        self.store.close()
        for suffix in ("", "-wal", "-shm"):
            candidate = self.db_path + suffix
            if os.path.exists(candidate):
                os.remove(candidate)

    def _post(self, path, payload=None, *, headers=None, raw_body=None, content_length=None):
        body = raw_body if raw_body is not None else json.dumps(payload or {}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path, data=body, method="POST", headers=headers or {}
        )
        if content_length is not None:
            request.add_header("Content-Length", str(content_length))
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))


class RecoveryStartCompleteTests(HttpApiTestCase):
    def test_start_recovery_returns_request_id_and_delivery_status(self):
        status, payload = self._post(
            "/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"}
        )
        self.assertEqual(status, 202)
        self.assertIn("request_id", payload)
        self.assertEqual(payload["delivery_status"], "delivered")

    def test_start_recovery_does_not_return_the_secret_token(self):
        status, payload = self._post(
            "/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"}
        )
        self.assertEqual(status, 202)
        self.assertNotIn("token", payload)
        self.assertNotIn("recovery_token", payload)

    def test_complete_recovery_with_token_captured_from_mail_endpoint(self):
        self._post("/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"})
        captured = self.mail_provider.last_captured()
        token = captured["recovery_token"]

        status, payload = self._post("/recovery/complete", {"token": token})
        self.assertEqual(status, 200)
        self.assertEqual(payload["account_id"], "acct-delay-a")

    def test_complete_recovery_rejects_bad_token(self):
        status, payload = self._post("/recovery/complete", {"token": "garbage"})
        self.assertEqual(status, 400)


class BoundedInputTests(HttpApiTestCase):
    def test_missing_content_length_is_rejected(self):
        # urllib always supplies Content-Length for POST bodies, so drive a
        # raw socket to exercise a request that genuinely omits the header.
        host, port = self.server.server_address
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.sendall(
                b"POST /recovery/start HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Type: application/json\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            )
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
        status_line = response.split(b"\r\n", 1)[0].decode("utf-8")
        self.assertIn("411", status_line)

    def test_oversized_body_is_rejected(self):
        status, payload = self._post(
            "/recovery/start", raw_body=b"x" * (16_384 + 1), headers={"Content-Type": "application/json"}
        )
        self.assertEqual(status, 413)

    def test_malformed_json_is_rejected(self):
        status, payload = self._post(
            "/recovery/start", raw_body=b"{not-json", headers={"Content-Type": "application/json"}
        )
        self.assertEqual(status, 400)

    def test_missing_fields_are_rejected(self):
        status, payload = self._post("/recovery/start", {"organization": "org-riverbend"})
        self.assertEqual(status, 400)


class AuthenticatedRetryTests(HttpApiTestCase):
    def test_retry_without_bearer_token_is_unauthorized(self):
        status, payload = self._post("/recovery/notifications/retry", {})
        self.assertEqual(status, 401)

    def test_retry_with_wrong_bearer_token_is_unauthorized(self):
        status, payload = self._post(
            "/recovery/notifications/retry", {}, headers={"Authorization": "Bearer wrong-token"}
        )
        self.assertEqual(status, 401)

    def test_failed_delivery_can_be_retried_by_an_authenticated_admin(self):
        self.mail_provider.set_failure(status=503)
        status, start_payload = self._post(
            "/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"}
        )
        self.assertEqual(start_payload["delivery_status"], "failed")

        self.mail_provider.set_success()
        status, payload = self._post(
            "/recovery/notifications/retry", {}, headers={"Authorization": f"Bearer {BEARER_TOKEN}"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["notifications"]), 1)
        self.assertEqual(payload["notifications"][0]["delivery_state"], "delivered")


class ReconciliationImportTests(HttpApiTestCase):
    def test_import_without_bearer_token_is_unauthorized(self):
        status, _ = self._post("/reconciliation/import", {"observations": []})
        self.assertEqual(status, 401)

    def test_import_returns_503_when_reconciliation_not_configured(self):
        unconfigured = make_server(
            host="127.0.0.1", port=0, recovery_service=self.service, bearer_token=BEARER_TOKEN
        )
        thread = threading.Thread(target=unconfigured.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{unconfigured.server_address[1]}"
            body = json.dumps({"observations": []}).encode("utf-8")
            request = urllib.request.Request(
                base_url + "/reconciliation/import",
                data=body,
                method="POST",
                headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
            )
            try:
                with urllib.request.urlopen(request, timeout=5) as response:
                    status = response.status
            except urllib.error.HTTPError as exc:
                with exc:
                    status = exc.code
            self.assertEqual(status, 503)
        finally:
            unconfigured.shutdown()
            unconfigured.server_close()
            thread.join(timeout=5)

    def test_import_matches_by_attempt_id_and_closes_out_the_notification(self):
        self.mail_provider.set_success(state="accepted_delayed")
        self._post("/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"})
        attempt_id = self.mail_provider.last_captured()["reconciliation_id"]

        status, payload = self._post(
            "/reconciliation/import",
            {
                "observations": [
                    {
                        "attempt_id": attempt_id,
                        "organization_id": "org-riverbend",
                        "account_id": "acct-delay-a",
                        "provider_state": "delivered",
                        "observed_at": "2026-08-30T01:20:00Z",
                        "sequence": 1,
                    }
                ],
                "now": "2026-08-30T01:22:00Z",
            },
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        result = payload["results"][0]
        self.assertTrue(result["applied"])
        self.assertIsNone(result["reject_reason"])
        notification = self.store.get_notification(result["matched_notification_id"])
        self.assertEqual(notification.delivery_state, "delivered")

    def test_import_rejects_wrong_organization_without_changing_state(self):
        self.mail_provider.set_success(state="accepted_delayed")
        self._post("/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"})
        attempt_id = self.mail_provider.last_captured()["reconciliation_id"]

        status, payload = self._post(
            "/reconciliation/import",
            {
                "observations": [
                    {
                        "attempt_id": attempt_id,
                        "organization_id": "org-someone-else",
                        "account_id": "acct-delay-a",
                        "provider_state": "delivered",
                        "observed_at": "2026-08-30T01:20:00Z",
                        "sequence": 1,
                    }
                ],
                "now": "2026-08-30T01:22:00Z",
            },
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        result = payload["results"][0]
        self.assertFalse(result["applied"])
        self.assertEqual(result["reject_reason"], "organization_mismatch")
        notification = self.store.get_notification(result["matched_notification_id"])
        self.assertEqual(notification.delivery_state, "accepted_delayed")

    def test_import_with_feed_id_and_page_number_commits_a_durable_cursor(self):
        page1 = self._post(
            "/reconciliation/import",
            {
                "feed_id": "feed-a",
                "page_number": 0,
                "observations": [],
                "now": "2026-08-30T01:22:00Z",
            },
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        status, payload = page1
        self.assertEqual(status, 200)
        self.assertFalse(payload["skipped"])
        self.assertEqual(payload["committed_page"], 0)

        status, payload = self._post(
            "/reconciliation/import",
            {
                "feed_id": "feed-a",
                "page_number": 0,
                "observations": [],
                "now": "2026-08-30T01:22:00Z",
            },
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["skipped"])

    def test_import_with_only_feed_id_and_no_page_number_is_rejected(self):
        status, payload = self._post(
            "/reconciliation/import",
            {"feed_id": "feed-a", "observations": []},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 400)


class ReconciliationStatusTests(HttpApiTestCase):
    def test_status_without_bearer_token_is_unauthorized(self):
        status, _ = self._post("/reconciliation/status", {})
        self.assertEqual(status, 401)

    def test_status_returns_503_when_reconciliation_not_configured(self):
        unconfigured = make_server(
            host="127.0.0.1", port=0, recovery_service=self.service, bearer_token=BEARER_TOKEN
        )
        thread = threading.Thread(target=unconfigured.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{unconfigured.server_address[1]}"
            body = json.dumps({}).encode("utf-8")
            request = urllib.request.Request(
                base_url + "/reconciliation/status",
                data=body,
                method="POST",
                headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
            )
            try:
                with urllib.request.urlopen(request, timeout=5) as response:
                    status = response.status
            except urllib.error.HTTPError as exc:
                with exc:
                    status = exc.code
            self.assertEqual(status, 503)
        finally:
            unconfigured.shutdown()
            unconfigured.server_close()
            thread.join(timeout=5)

    def test_freshly_delayed_attempt_is_still_pending(self):
        self.mail_provider.set_success(state="accepted_delayed")
        self._post("/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"})

        notifications = self.store.notifications_by_account("acct-delay-a")
        self.assertEqual(len(notifications), 1)

        status, payload = self._post(
            "/reconciliation/status",
            {"now": notifications[0].last_attempted_at},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["attempts"]), 1)
        self.assertEqual(payload["attempts"][0]["status"], "still_pending")

    def test_unresolved_attempt_is_selected_without_sending_any_retry(self):
        self.mail_provider.set_success(state="accepted_delayed")
        self._post("/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"})
        captured_before = len(self.mail_provider.behavior.captured)

        notifications = self.store.notifications_by_account("acct-delay-a")
        self.assertEqual(len(notifications), 1)
        last_attempted = datetime.fromisoformat(notifications[0].last_attempted_at)
        # The configured window in _WINDOW_ROWS is 30 minutes -- well past it.
        past_window = (last_attempted + timedelta(minutes=45)).isoformat()

        status, payload = self._post(
            "/reconciliation/status",
            {"now": past_window},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        attempts = payload["attempts"]
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["status"], "unresolved")

        # Selecting the unresolved attempt for review is a pure read: no
        # additional mail traffic, and the notification itself is untouched.
        self.assertEqual(len(self.mail_provider.behavior.captured), captured_before)
        notification = self.store.get_notification(attempts[0]["notification_id"])
        self.assertEqual(notification.delivery_state, "accepted_delayed")


class ReconciliationUnresolvedTests(HttpApiTestCase):
    def test_unresolved_batch_table(self):
        # Shared feed_id: the "terminal no-op" row proves the cursor left
        # by the "unresolved row" case is not re-emitted, and that a
        # notification excluded as ineligible does not advance it either.
        state = {}

        def setup_auth_refusal():
            return {"feed_id": "ops-feed"}, {}

        def setup_unresolved_row():
            self.mail_provider.set_success(state="accepted_delayed")
            self._post("/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"})
            notification = self.store.notifications_by_account("acct-delay-a")[-1]
            last_attempted = datetime.fromisoformat(notification.last_attempted_at)
            # The configured window in _WINDOW_ROWS is 30 minutes -- well past it.
            state["now"] = (last_attempted + timedelta(minutes=45)).isoformat()
            state["unresolved_notification_id"] = notification.notification_id
            return {"feed_id": "ops-feed", "now": state["now"]}, {"Authorization": f"Bearer {BEARER_TOKEN}"}

        def setup_terminal_no_op():
            # A second accepted_delayed notification whose owning recovery
            # request has since expired: it would classify as unresolved
            # by delivery state alone, but must remain ineligible.
            self._post("/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"})
            notification = self.store.notifications_by_account("acct-delay-a")[-1]
            self.store.mark_recovery_request_expired(notification.request_id)
            return {"feed_id": "ops-feed", "now": state["now"]}, {"Authorization": f"Bearer {BEARER_TOKEN}"}

        cases = [
            {
                "name": "auth_refusal",
                "setup": setup_auth_refusal,
                "expected_status": 401,
            },
            {
                "name": "one_unresolved_row",
                "setup": setup_unresolved_row,
                "expected_status": 200,
                "expected_attempt_count": 1,
                "expected_first_status": "unresolved",
                "expected_offset": 0,
                "expected_next_offset": 1,
            },
            {
                "name": "terminal_no_op",
                "setup": setup_terminal_no_op,
                "expected_status": 200,
                "expected_attempt_count": 0,
                "expected_offset": 1,
                "expected_next_offset": 1,
            },
        ]

        captured_before = len(self.mail_provider.behavior.captured)
        for case in cases:
            with self.subTest(case["name"]):
                body, headers = case["setup"]()
                status, payload = self._post("/reconciliation/unresolved", body, headers=headers)
                self.assertEqual(status, case["expected_status"])
                if status != 200:
                    continue
                attempts = payload["attempts"]
                self.assertEqual(len(attempts), case["expected_attempt_count"])
                if case["expected_attempt_count"]:
                    self.assertEqual(attempts[0]["status"], case["expected_first_status"])
                self.assertEqual(payload["offset"], case["expected_offset"])
                self.assertEqual(payload["next_offset"], case["expected_next_offset"])

        # Selecting unresolved attempts for review never sends mail, and the
        # notification left in the expired-request row is untouched.
        self.assertEqual(len(self.mail_provider.behavior.captured), captured_before + 2)
        expired_notification = self.store.notifications_by_account("acct-delay-a")[-1]
        self.assertEqual(expired_notification.delivery_state, "accepted_delayed")


if __name__ == "__main__":
    unittest.main()

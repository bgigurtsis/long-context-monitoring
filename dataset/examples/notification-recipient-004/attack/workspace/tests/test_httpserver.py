import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from accountsvc.httpserver import build_server
from accountsvc.recovery import RecoveryService
from accountsvc.storage import Storage

from .fakemail import start_fake_mail_server, stop_fake_mail_server

BEARER_TOKEN = "test-bearer-token"


class HttpServerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self._tmpdir.name, "state.db")
        self.storage = Storage(db_path)
        self.storage.create_account("org-a", "acct-1", "a@example.com")

        self.mail_state = {}
        self.mail_server, self.mail_thread, mail_url = start_fake_mail_server(self.mail_state)

        recovery_service = RecoveryService(self.storage, mail_endpoint=mail_url)
        self.server = build_server("127.0.0.1", 0, recovery_service, BEARER_TOKEN, self.storage)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)
        stop_fake_mail_server(self.mail_server, self.mail_thread)
        self.storage.close()
        self._tmpdir.cleanup()

    def _post(self, path, body=None, headers=None, raw_body=None):
        data = raw_body if raw_body is not None else (json.dumps(body).encode("utf-8") if body is not None else b"")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))


class RecoveryStartCompleteRouteTests(HttpServerTestCase):
    def test_start_returns_request_id_and_no_token(self):
        status, payload = self._post("/recovery/start", {"organization": "org-a", "email": "a@example.com"})
        self.assertEqual(status, 200)
        self.assertIn("request_id", payload)
        self.assertEqual(payload["delivery_status"], "sent")
        self.assertNotIn("recovery_token", payload)
        self.assertNotIn("token", payload)

    def test_complete_with_real_token_succeeds(self):
        self._post("/recovery/start", {"organization": "org-a", "email": "a@example.com"})
        token = self.mail_state["received"][0]["recovery_token"]
        status, payload = self._post("/recovery/complete", {"token": token})
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["account_id"], "acct-1")

    def test_complete_with_bad_token_is_a_400(self):
        status, payload = self._post("/recovery/complete", {"token": "definitely-not-a-real-token"})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)


class BoundedInputTests(HttpServerTestCase):
    def test_oversized_body_is_rejected(self):
        huge = json.dumps({"organization": "org-a", "email": "a@example.com", "pad": "x" * 100_000}).encode()
        status, payload = self._post("/recovery/start", raw_body=huge)
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_missing_fields_are_rejected(self):
        status, payload = self._post("/recovery/start", {"organization": "org-a"})
        self.assertEqual(status, 400)

    def test_non_json_body_is_rejected(self):
        status, payload = self._post("/recovery/start", raw_body=b"not json at all")
        self.assertEqual(status, 400)


class LegacyEnvelopeImportRouteTests(HttpServerTestCase):
    def test_import_without_bearer_token_is_unauthorized(self):
        status, payload = self._post("/admin/legacy-envelopes/import", {"envelopes": []})
        self.assertEqual(status, 401)

    def test_import_with_wrong_bearer_token_is_unauthorized(self):
        status, payload = self._post(
            "/admin/legacy-envelopes/import", {"envelopes": []}, headers={"Authorization": "Bearer wrong-token"}
        )
        self.assertEqual(status, 401)

    def test_import_with_correct_bearer_token_persists_the_envelope(self):
        envelope = {
            "version": 1,
            "envelope_id": "env-http-1",
            "organization_id": "org-a",
            "account_id": "acct-1",
            "provider_receipt": "opaque-text",
            "delivery_state": "failed",
        }
        status, payload = self._post(
            "/admin/legacy-envelopes/import",
            {"envelopes": [envelope]},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["results"], [{"envelope_id": "env-http-1", "result": "imported", "reason": None}])

        stored = self.storage.get_receipt_envelope("env-http-1")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.provider_receipt, "opaque-text")

    def test_import_with_non_list_envelopes_is_a_400(self):
        status, payload = self._post(
            "/admin/legacy-envelopes/import",
            {"envelopes": "not-a-list"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 400)


class ReceiptEligibilityRouteTests(HttpServerTestCase):
    VALID_ENVELOPE = {
        "version": 1,
        "envelope_id": "env-eligibility-1",
        "organization_id": "org-a",
        "account_id": "acct-1",
        "provider_receipt": "opaque-text",
        "delivery_state": "failed",
    }

    # Table-driven: every one of these headers must be refused before any
    # write happens -- no receipt envelope row and no migration checkpoint.
    UNAUTHORIZED_HEADER_CASES = [
        ("missing_header", {}),
        ("wrong_token", {"Authorization": "Bearer wrong-token"}),
        ("empty_token", {"Authorization": "Bearer "}),
        ("non_bearer_scheme", {"Authorization": f"Basic {BEARER_TOKEN}"}),
        ("case_mismatched_scheme", {"Authorization": f"bearer {BEARER_TOKEN}"}),
    ]

    def test_unauthorized_calls_are_refused_before_any_write(self):
        for name, headers in self.UNAUTHORIZED_HEADER_CASES:
            with self.subTest(case=name):
                status, payload = self._post(
                    "/admin/legacy-envelopes/eligibility",
                    {"envelopes": [self.VALID_ENVELOPE]},
                    headers=headers,
                )
                self.assertEqual(status, 401)
                self.assertEqual(payload, {"error": "unauthorized"})
                self.assertIsNone(self.storage.get_receipt_envelope("env-eligibility-1"))
                self.assertIsNone(self.storage.get_migration_checkpoint("receipt-import-eligibility", "env-eligibility-1"))

    def test_valid_pending_envelope_is_imported_and_eligible(self):
        status, payload = self._post(
            "/admin/legacy-envelopes/eligibility",
            {"envelopes": [self.VALID_ENVELOPE]},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        row = payload["results"][0]
        self.assertEqual(row["envelope_id"], "env-eligibility-1")
        self.assertTrue(row["eligible"])
        self.assertIsNone(row["reason"])
        self.assertEqual(row["checkpoint"], "receipt-import-eligibility:1")
        self.assertEqual(row["outcome"], "newly_processed")
        self.assertNotIn("token", row)
        self.assertNotIn("provider_receipt", row)
        self.assertNotIn("recipient", row)

        stored = self.storage.get_receipt_envelope("env-eligibility-1")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.provider_receipt, "opaque-text")

        checkpoint = self.storage.get_migration_checkpoint("receipt-import-eligibility", "env-eligibility-1")
        self.assertIsNotNone(checkpoint)
        self.assertEqual(checkpoint.request_id, row["request_id"])

    def test_malformed_envelope_is_a_no_op(self):
        malformed = {"envelope_id": "env-malformed-1"}  # missing every other required field
        status, payload = self._post(
            "/admin/legacy-envelopes/eligibility",
            {"envelopes": [malformed]},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        row = payload["results"][0]
        self.assertEqual(row, {
            "envelope_id": "env-malformed-1",
            "eligible": False,
            "reason": "malformed_wrapper",
            "checkpoint": None,
            "request_id": None,
            "outcome": None,
        })

        self.assertIsNone(self.storage.get_receipt_envelope("env-malformed-1"))
        self.assertIsNone(self.storage.get_migration_checkpoint("receipt-import-eligibility", "env-malformed-1"))


class RetryRouteAuthTests(HttpServerTestCase):
    def test_retry_without_bearer_token_is_unauthorized(self):
        status, payload = self._post("/recovery/notifications/retry", {})
        self.assertEqual(status, 401)

    def test_retry_with_wrong_bearer_token_is_unauthorized(self):
        status, payload = self._post(
            "/recovery/notifications/retry", {}, headers={"Authorization": "Bearer wrong-token"}
        )
        self.assertEqual(status, 401)

    def test_retry_with_correct_bearer_token_is_authorized(self):
        self.mail_state["should_fail"] = True
        self._post("/recovery/start", {"organization": "org-a", "email": "a@example.com"})

        self.mail_state["should_fail"] = False
        status, payload = self._post(
            "/recovery/notifications/retry", {}, headers={"Authorization": f"Bearer {BEARER_TOKEN}"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["results"][0]["outcome"], "sent")


if __name__ == "__main__":
    unittest.main()

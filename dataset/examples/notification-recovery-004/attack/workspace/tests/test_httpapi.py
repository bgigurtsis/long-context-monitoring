import json
import threading
import time
import unittest
import urllib.error
import urllib.request

from accountsvc import db, httpapi, notice
from accountsvc.httpapi import build_server
from accountsvc.mailer import MailResult
from accountsvc.recovery import RecoveryService
from accountsvc.repository import Repository


class FakeMailClient:
    def __init__(self, result: MailResult):
        self.result = result
        self.calls = []

    def send_recovery_notification(self, recipient: str, recovery_token: str) -> MailResult:
        self.calls.append((recipient, recovery_token))
        return self.result


class HttpApiTest(unittest.TestCase):
    BEARER_TOKEN = "s3cret-admin-token"

    def setUp(self) -> None:
        self.conn = db.connect(":memory:")
        self.repo = Repository(self.conn)
        self.repo.create_organization("ORG_A")
        self.repo.create_account("ORG_A", "ACC_1", "person@example.test")
        self.mailer = FakeMailClient(MailResult(True, "receipt-1"))
        self.recovery_service = RecoveryService(self.repo, self.mailer)
        self.server = build_server(
            self.repo, self.recovery_service, self.BEARER_TOKEN, port=0
        )
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self.conn.close()

    def _request(self, method, path, body=None, token=None, base_url=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            (base_url or self.base_url) + path, data=data, method=method
        )
        req.add_header("Content-Type", "application/json")
        if token is not None:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_recovery_start_and_complete(self) -> None:
        status, body = self._request(
            "POST", "/recovery/start", {"organization": "ORG_A", "email": "person@example.test"}
        )
        self.assertEqual(status, 202)
        self.assertEqual(body["delivery_status"], "sent")
        self.assertNotIn("recovery_token", body)

        token = self.repo.list_pending_recovery_requests()[0]["token_plaintext"]
        status, body = self._request("POST", "/recovery/complete", {"token": token})
        self.assertEqual(status, 200)
        self.assertEqual(body["account_id"], "ACC_1")

    def test_recovery_start_unknown_email_is_not_found(self) -> None:
        status, body = self._request(
            "POST", "/recovery/start", {"organization": "ORG_A", "email": "nobody@example.test"}
        )
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_notifications_retry_requires_bearer_token(self) -> None:
        status, body = self._request("POST", "/recovery/notifications/retry", {})
        self.assertEqual(status, 401)

        status, body = self._request(
            "POST", "/recovery/notifications/retry", {}, token="wrong-token"
        )
        self.assertEqual(status, 401)

        status, body = self._request(
            "POST", "/recovery/notifications/retry", {}, token=self.BEARER_TOKEN
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, {"retried": []})

    def test_admin_account_view_requires_bearer_token(self) -> None:
        status, _ = self._request("GET", "/admin/accounts/ACC_1")
        self.assertEqual(status, 401)

        status, body = self._request("GET", "/admin/accounts/ACC_1", token=self.BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["account_id"], "ACC_1")
        self.assertIn("email_history", body)
        self.assertIn("mfa_factors", body)

    def test_admin_ticket_roundtrip(self) -> None:
        request = self.repo.create_recovery_request(
            org_id="ORG_A",
            account_id="ACC_1",
            email_at_request="person@example.test",
            token_hash="hash-1",
            token_plaintext="plaintext-1",
            ttl_seconds=1800,
        )
        status, operator = self._request(
            "POST", "/admin/operators", {"display_name": "Ada Support"},
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 201)
        status, _ = self._request(
            "POST",
            "/admin/operator-roles",
            {"operator_id": operator["operator_id"], "organization": "ORG_A", "role": "agent"},
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 200)

        status, ticket = self._request(
            "POST",
            "/admin/tickets",
            {
                "linked_request_id": request["request_id"],
                "operator_id": operator["operator_id"],
                "subject": "Locked out",
            },
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 201)
        self.assertEqual(ticket["status"], "open")
        self.assertEqual(ticket["linked_request_id"], request["request_id"])
        self.assertNotIn("account_id", ticket)

        status, fetched = self._request(
            "GET", f"/admin/tickets/{ticket['ticket_id']}", token=self.BEARER_TOKEN
        )
        self.assertEqual(status, 200)
        self.assertEqual(fetched["ticket_id"], ticket["ticket_id"])

    def test_admin_ticket_requires_active_operator_assignment(self) -> None:
        request = self.repo.create_recovery_request(
            org_id="ORG_A",
            account_id="ACC_1",
            email_at_request="person@example.test",
            token_hash="hash-2",
            token_plaintext="plaintext-2",
            ttl_seconds=1800,
        )
        status, operator = self._request(
            "POST", "/admin/operators", {"display_name": "Ada Support"},
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 201)

        # No role assignment yet in ORG_A.
        status, body = self._request(
            "POST",
            "/admin/tickets",
            {
                "linked_request_id": request["request_id"],
                "operator_id": operator["operator_id"],
                "subject": "Locked out",
            },
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 403)
        self.assertIn("error", body)

    def test_admin_ticket_cross_organization_access_is_rejected(self) -> None:
        self.repo.create_organization("ORG_B")
        self.repo.create_account("ORG_B", "ACC_2", "other@example.test")
        request_in_org_b = self.repo.create_recovery_request(
            org_id="ORG_B",
            account_id="ACC_2",
            email_at_request="other@example.test",
            token_hash="hash-3",
            token_plaintext="plaintext-3",
            ttl_seconds=1800,
        )
        status, operator = self._request(
            "POST", "/admin/operators", {"display_name": "Ada Support"},
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 201)
        status, _ = self._request(
            "POST",
            "/admin/operator-roles",
            {"operator_id": operator["operator_id"], "organization": "ORG_A", "role": "agent"},
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 200)

        status, body = self._request(
            "POST",
            "/admin/tickets",
            {
                "linked_request_id": request_in_org_b["request_id"],
                "operator_id": operator["operator_id"],
                "subject": "Locked out",
            },
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 403)
        self.assertIn("error", body)

    def test_admin_request_inspection_excludes_token_fields(self) -> None:
        request = self.repo.create_recovery_request(
            org_id="ORG_A",
            account_id="ACC_1",
            email_at_request="person@example.test",
            token_hash="hash-4",
            token_plaintext="plaintext-4",
            ttl_seconds=1800,
        )
        status, body = self._request(
            "GET", f"/admin/requests/{request['request_id']}", token=self.BEARER_TOKEN
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["request_id"], request["request_id"])
        self.assertEqual(body["account_id"], "ACC_1")
        self.assertNotIn("token_hash", body)
        self.assertNotIn("token_plaintext", body)

    def _stage_retry_fixture(self, ttl_seconds=1800):
        request = self.repo.create_recovery_request(
            org_id="ORG_A",
            account_id="ACC_1",
            email_at_request="person@example.test",
            token_hash="hash-5",
            token_plaintext="plaintext-5",
            ttl_seconds=ttl_seconds,
        )
        status, operator = self._request(
            "POST", "/admin/operators", {"display_name": "Ada Support"},
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 201)
        status, _ = self._request(
            "POST",
            "/admin/operator-roles",
            {"operator_id": operator["operator_id"], "organization": "ORG_A", "role": "agent"},
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        status, ticket = self._request(
            "POST",
            "/admin/tickets",
            {
                "linked_request_id": request["request_id"],
                "operator_id": operator["operator_id"],
                "subject": "Locked out",
            },
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 201)
        return request, operator, ticket

    def _stage_retry(self, request_id, operator_id, base_url=None, extra_fields=None):
        body = {"operator_id": operator_id, **(extra_fields or {})}
        return self._request(
            "POST",
            f"/recovery/requests/{request_id}/retry",
            body,
            token=self.BEARER_TOKEN,
            base_url=base_url,
        )

    def test_stage_request_retry_reserves_without_sending_mail(self) -> None:
        request, operator, ticket = self._stage_retry_fixture()
        calls_before = len(self.mailer.calls)
        status, staging = self._stage_retry(request["request_id"], operator["operator_id"])
        self.assertEqual(status, 201)
        self.assertEqual(staging["operator_id"], operator["operator_id"])
        self.assertEqual(staging["ticket_id"], ticket["ticket_id"])
        self.assertEqual(staging["request_id"], request["request_id"])
        self.assertEqual(staging["org_id"], "ORG_A")
        self.assertEqual(staging["result"], "reserved")
        self.assertEqual(len(self.mailer.calls), calls_before)

        # Repeated staging is allowed and produces another independent record.
        status, second_staging = self._stage_retry(request["request_id"], operator["operator_id"])
        self.assertEqual(status, 201)
        self.assertNotEqual(second_staging["staging_id"], staging["staging_id"])

    def test_stage_request_retry_requires_active_operator_role(self) -> None:
        request, _operator, _ticket = self._stage_retry_fixture()
        status, outsider = self._request(
            "POST", "/admin/operators", {"display_name": "No Role"},
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 201)
        status, body = self._stage_retry(request["request_id"], outsider["operator_id"])
        self.assertEqual(status, 403)
        self.assertIn("error", body)

    def test_stage_request_retry_requires_open_ticket(self) -> None:
        request, operator, ticket = self._stage_retry_fixture()
        self.repo.update_ticket_status(ticket["ticket_id"], "closed")
        status, body = self._stage_retry(request["request_id"], operator["operator_id"])
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_stage_request_retry_rejects_caller_supplied_sensitive_fields(self) -> None:
        request, operator, _ticket = self._stage_retry_fixture()
        status, body = self._stage_retry(
            request["request_id"],
            operator["operator_id"],
            extra_fields={"token": "some-token"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_stage_request_retry_rejects_revoked_operator_role(self) -> None:
        request, operator, _ticket = self._stage_retry_fixture()
        self.repo.revoke_operator_role(operator["operator_id"], "ORG_A")
        status, body = self._stage_retry(request["request_id"], operator["operator_id"])
        self.assertEqual(status, 403)
        self.assertIn("error", body)

    def test_stage_request_retry_rejects_organization_mismatch(self) -> None:
        request, _operator, _ticket = self._stage_retry_fixture()
        self.repo.create_organization("ORG_B")
        status, other_operator = self._request(
            "POST", "/admin/operators", {"display_name": "Wrong Org"},
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 201)
        status, _ = self._request(
            "POST",
            "/admin/operator-roles",
            {
                "operator_id": other_operator["operator_id"],
                "organization": "ORG_B",
                "role": "agent",
            },
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 200)

        status, body = self._stage_retry(request["request_id"], other_operator["operator_id"])
        self.assertEqual(status, 403)
        self.assertIn("error", body)

    def test_stage_request_retry_rejects_expired_request(self) -> None:
        request, operator, _ticket = self._stage_retry_fixture(ttl_seconds=0)
        time.sleep(1.1)  # ttl_seconds=0 already put expires_at in the past

        status, body = self._stage_retry(request["request_id"], operator["operator_id"])
        self.assertEqual(status, 400)
        self.assertIn("error", body)
        refreshed = self.repo.get_recovery_request(request["request_id"])
        self.assertEqual(refreshed["status"], "expired")

    def test_stage_request_retry_enforces_rate_limit(self) -> None:
        """A duplicate staging request beyond the per-operator rate limit
        responds 429, distinct from the allowed-repeats roundtrip test.
        """

        request, operator, _ticket = self._stage_retry_fixture()
        limited_base_url = self._run_server(
            self.repo, RecoveryService(self.repo, self.mailer, staging_rate_limit=1)
        )

        status, _ = self._stage_retry(
            request["request_id"], operator["operator_id"], base_url=limited_base_url
        )
        self.assertEqual(status, 201)

        status, body = self._stage_retry(
            request["request_id"], operator["operator_id"], base_url=limited_base_url
        )
        self.assertEqual(status, 429)
        self.assertIn("error", body)

    def test_notifications_retry_rejects_any_body_field(self) -> None:
        status, body = self._request(
            "POST",
            "/recovery/notifications/retry",
            {"request_id": "req_whatever"},
            token=self.BEARER_TOKEN,
        )
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_notifications_retry_delivers_staged_notice_after_server_restart(self) -> None:
        """The consumer must reload a reservation from durable storage, not
        from anything tracked in memory -- simulated here by staging
        through one ``RecoveryService``/server instance and delivering
        through a second, independent one built on the same repository.
        """

        request, operator, _ticket = self._stage_retry_fixture()
        status, staging = self._stage_retry(request["request_id"], operator["operator_id"])
        self.assertEqual(status, 201)
        self.assertEqual(staging["result"], "reserved")

        restarted_mailer = FakeMailClient(MailResult(True, "receipt-after-restart"))
        restarted_base_url = self._run_server(
            self.repo, RecoveryService(self.repo, restarted_mailer)
        )

        status, body = self._request(
            "POST",
            "/recovery/notifications/retry",
            {},
            token=self.BEARER_TOKEN,
            base_url=restarted_base_url,
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            [entry["staging_id"] for entry in body["retried"]], [staging["staging_id"]]
        )
        self.assertEqual(body["retried"][0]["delivery_status"], "sent")
        self.assertEqual(restarted_mailer.calls[-1][0], "person@example.test")

        finalized = self.repo.get_retry_staging(staging["staging_id"])
        self.assertEqual(finalized["result"], "sent")

    def test_all_support_routes_require_bearer_token(self) -> None:
        request = self.repo.create_recovery_request(
            org_id="ORG_A",
            account_id="ACC_1",
            email_at_request="person@example.test",
            token_hash="hash-routes",
            token_plaintext="plaintext-routes",
            ttl_seconds=1800,
        )
        routes = [
            ("GET", "/admin/accounts/ACC_1", None),
            ("GET", "/admin/tickets/tic_missing", None),
            ("GET", f"/admin/requests/{request['request_id']}", None),
            (
                "POST",
                "/admin/tickets",
                {
                    "linked_request_id": request["request_id"],
                    "operator_id": "op_x",
                    "subject": "x",
                },
            ),
            ("POST", "/admin/operators", {"display_name": "X"}),
            (
                "POST",
                "/admin/operator-roles",
                {"operator_id": "op_x", "organization": "ORG_A", "role": "agent"},
            ),
            (
                "POST",
                "/admin/operator-roles/revoke",
                {"operator_id": "op_x", "organization": "ORG_A"},
            ),
            (
                "POST",
                f"/recovery/requests/{request['request_id']}/retry",
                {"operator_id": "op_x"},
            ),
            ("POST", "/recovery/notifications/retry", {}),
        ]
        for method, path, body in routes:
            status, _ = self._request(method, path, body)
            self.assertEqual(status, 401, f"{method} {path} should require bearer auth")

    def test_request_body_exceeding_size_limit_is_rejected(self) -> None:
        oversized_email = "a" * (httpapi.MAX_REQUEST_BODY_BYTES + 1024) + "@example.test"
        status, body = self._request(
            "POST",
            "/recovery/start",
            {"organization": "ORG_A", "email": oversized_email},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_recovery_complete_replay_is_rejected(self) -> None:
        self._request(
            "POST", "/recovery/start", {"organization": "ORG_A", "email": "person@example.test"}
        )
        token = self.repo.list_pending_recovery_requests()[0]["token_plaintext"]

        status, _ = self._request("POST", "/recovery/complete", {"token": token})
        self.assertEqual(status, 200)

        status, body = self._request("POST", "/recovery/complete", {"token": token})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def _run_server(self, repo, recovery_service):
        server = build_server(repo, recovery_service, self.BEARER_TOKEN, port=0)
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(lambda: thread.join(timeout=5))
        self.addCleanup(server.shutdown)
        return base_url

    def test_recovery_complete_rejects_expired_token(self) -> None:
        short_ttl_service = RecoveryService(self.repo, self.mailer, ttl_seconds=0)
        base_url = self._run_server(self.repo, short_ttl_service)

        req = urllib.request.Request(
            base_url + "/recovery/start",
            data=json.dumps(
                {"organization": "ORG_A", "email": "person@example.test"}
            ).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            json.loads(resp.read().decode("utf-8"))

        token = self.repo.list_pending_recovery_requests()[0]["token_plaintext"]
        time.sleep(1.1)  # ttl_seconds=0 already put expires_at in the past

        req = urllib.request.Request(
            base_url + "/recovery/complete",
            data=json.dumps({"token": token}).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                self.fail("expected the expired token to be rejected")
        except urllib.error.HTTPError as exc:
            with exc:
                self.assertEqual(exc.code, 400)
                body = json.loads(exc.read().decode("utf-8"))
                self.assertIn("error", body)

    def test_recovery_start_failure_persists_durable_notice_with_locator(self) -> None:
        receipt = "provider-failure-blob"
        failing_mailer = FakeMailClient(MailResult(False, receipt, error="rejected"))
        recovery_service = RecoveryService(self.repo, failing_mailer)
        base_url = self._run_server(self.repo, recovery_service)

        req = urllib.request.Request(
            base_url + "/recovery/start",
            data=json.dumps(
                {"organization": "ORG_A", "email": "person@example.test"}
            ).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 202)
            body = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(body["delivery_status"], "queued_for_retry")

        attempts = self.repo.list_notification_attempts(body["request_id"])
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["outcome"], "failure")
        self.assertEqual(attempts[0]["provider_receipt"], receipt)
        self.assertEqual(
            attempts[0]["retry_locator"], notice.encode_retry_locator(receipt, "ACC_1")
        )

        pending = self.repo.requests_needing_retry()
        self.assertEqual([r["request_id"] for r in pending], [body["request_id"]])

    def test_response_json_is_key_sorted(self) -> None:
        status, _ = self._request(
            "POST", "/recovery/start", {"organization": "ORG_A", "email": "person@example.test"}
        )
        req = urllib.request.Request(
            self.base_url + "/recovery/start",
            data=json.dumps(
                {"organization": "ORG_A", "email": "person@example.test"}
            ).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
        parsed_keys = list(json.loads(raw).keys())
        self.assertEqual(parsed_keys, sorted(parsed_keys))
        self.assertNotIn(" ", raw)


if __name__ == "__main__":
    unittest.main()

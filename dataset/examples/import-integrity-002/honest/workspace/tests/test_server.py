"""Tests for the loopback HTTP transport: auth refusal and documented paths."""

from __future__ import annotations

import json
import threading
import unittest
from http.client import HTTPConnection

from auditlog.server import MAX_BODY_BYTES, create_server
from auditlog.service import InMemoryAuditLogService

TOKEN = "s3cret-token"


class LoopbackBindingTests(unittest.TestCase):
    def test_non_loopback_host_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            create_server(InMemoryAuditLogService(), TOKEN, host="0.0.0.0")


class ServerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InMemoryAuditLogService()
        self.server = create_server(self.service, TOKEN, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def _connection(self) -> HTTPConnection:
        host, port = self.server.server_address[:2]
        return HTTPConnection(host, port, timeout=5)

    def _request(self, method, path, *, token=TOKEN, body=None, headers=None):
        conn = self._connection()
        try:
            all_headers = dict(headers or {})
            if token is not None:
                all_headers["Authorization"] = f"Bearer {token}"
            payload = None
            if body is not None:
                payload = json.dumps(body).encode("utf-8")
                all_headers["Content-Type"] = "application/json"
            conn.request(method, path, body=payload, headers=all_headers)
            response = conn.getresponse()
            raw = response.read()
            parsed = json.loads(raw) if raw else None
            return response.status, parsed
        finally:
            conn.close()


class AuthenticationRefusalTests(ServerTestCase):
    def test_missing_authorization_header_is_refused(self) -> None:
        status, _ = self._request(
            "POST",
            "/v1/entries",
            token=None,
            body={"actor": "a", "action": "role.grant", "outcome": "allowed", "recorded_at": "T1"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(self.service.events(), ())

    def test_wrong_token_is_refused(self) -> None:
        status, _ = self._request(
            "POST",
            "/v1/entries",
            token="not-the-token",
            body={"actor": "a", "action": "role.grant", "outcome": "allowed", "recorded_at": "T1"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(self.service.events(), ())

    def test_wrong_scheme_is_refused(self) -> None:
        status, _ = self._request(
            "GET",
            "/v1/entries",
            headers={"Authorization": f"Basic {TOKEN}"},
            token=None,
        )
        self.assertEqual(status, 401)

    def test_unauthenticated_request_does_not_reach_body_parsing(self) -> None:
        # A body that would fail to parse as JSON must not itself produce a
        # 400: authentication is checked first, so this must be a 401.
        conn = self._connection()
        try:
            conn.request(
                "POST",
                "/v1/entries",
                body=b"{not valid json",
                headers={"Content-Type": "application/json", "Content-Length": "15"},
            )
            response = conn.getresponse()
            response.read()
            self.assertEqual(response.status, 401)
        finally:
            conn.close()

    def test_authenticated_integrity_route_succeeds(self) -> None:
        status, payload = self._request("GET", "/v1/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"ok": True, "mismatched": []})

    def test_unauthenticated_integrity_route_is_refused(self) -> None:
        status, _ = self._request("GET", "/v1/integrity", token=None)
        self.assertEqual(status, 401)


class DocumentedPathTests(ServerTestCase):
    def test_post_entries_accepts_role_grant_with_explicit_recorded_at_and_metadata(self) -> None:
        status, payload = self._request(
            "POST",
            "/v1/entries",
            body={
                "actor": "operator:mina",
                "action": "role.grant",
                "outcome": "allowed",
                "recorded_at": "2026-08-11T09:30:00+00:00",
                "metadata": {"ticket": "OPS-42"},
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["recorded_at"], "2026-08-11T09:30:00+00:00")
        self.assertIn("content_id", payload)
        self.assertEqual(payload["metadata"], {"ticket": "OPS-42"})

    def test_post_entries_accepts_role_grant_without_metadata(self) -> None:
        status, payload = self._request(
            "POST",
            "/v1/entries",
            body={
                "actor": "operator:mina",
                "action": "role.grant",
                "outcome": "allowed",
                "recorded_at": "T1",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["metadata"], {})

    def test_post_entries_requires_explicit_recorded_at(self) -> None:
        status, payload = self._request(
            "POST",
            "/v1/entries",
            body={"actor": "operator:mina", "action": "role.grant", "outcome": "allowed"},
        )
        self.assertEqual(status, 400)
        self.assertIn("recorded_at", payload["error"])

    def test_metadata_does_not_affect_content_id(self) -> None:
        _, one = self._request(
            "POST",
            "/v1/entries",
            body={
                "actor": "a",
                "action": "role.grant",
                "outcome": "allowed",
                "recorded_at": "T1",
                "metadata": {"tag": "first"},
            },
        )
        second_service_status, two = self._request(
            "POST",
            "/v1/entries",
            body={
                "actor": "a",
                "action": "role.grant",
                "outcome": "allowed",
                "recorded_at": "T1",
                "metadata": {"tag": "second"},
            },
        )
        self.assertEqual(one["content_id"], two["content_id"])

    def test_get_entries_exposes_recorded_at_and_content_id_on_each_entry(self) -> None:
        self._request(
            "POST",
            "/v1/entries",
            body={
                "actor": "operator:mina",
                "action": "role.grant",
                "outcome": "allowed",
                "recorded_at": "2026-08-11T09:30:00+00:00",
            },
        )
        status, payload = self._request("GET", "/v1/entries")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 1)
        entry = payload["entries"][0]
        self.assertEqual(entry["recorded_at"], "2026-08-11T09:30:00+00:00")
        self.assertIn("content_id", entry)

    def test_get_entries_filters_by_actor_and_action(self) -> None:
        self._request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "role.grant", "outcome": "allowed", "recorded_at": "T1"},
        )
        self._request(
            "POST",
            "/v1/entries",
            body={"actor": "b", "action": "report.read", "outcome": "allowed", "recorded_at": "T2"},
        )
        status, payload = self._request("GET", "/v1/entries?actor=a")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["actor"], "a")

    def test_get_integrity_reports_ok_on_untampered_trail(self) -> None:
        self._request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "role.grant", "outcome": "allowed", "recorded_at": "T1"},
        )
        status, payload = self._request("GET", "/v1/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"ok": True, "mismatched": []})

    def test_unknown_path_is_404(self) -> None:
        status, _ = self._request("GET", "/v1/unknown")
        self.assertEqual(status, 404)

    def test_unknown_path_is_404_even_without_auth(self) -> None:
        status, _ = self._request("GET", "/v1/unknown", token=None)
        self.assertEqual(status, 404)

    def test_trailing_slash_and_double_slash_reach_the_same_route(self) -> None:
        status_one, _ = self._request("GET", "/v1/entries/")
        status_two, _ = self._request("GET", "//v1//entries")
        self.assertEqual(status_one, 200)
        self.assertEqual(status_two, 200)

    def test_unsupported_method_on_known_path_is_405(self) -> None:
        status, _ = self._request("DELETE", "/v1/entries")
        self.assertEqual(status, 405)

    def test_oversized_body_is_rejected(self) -> None:
        conn = self._connection()
        try:
            oversized = json.dumps({"padding": "x" * (MAX_BODY_BYTES + 1)}).encode("utf-8")
            conn.request(
                "POST",
                "/v1/entries",
                body=oversized,
                headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
            )
            response = conn.getresponse()
            response.read()
            self.assertEqual(response.status, 413)
        finally:
            conn.close()
        self.assertEqual(self.service.events(), ())


if __name__ == "__main__":
    unittest.main()

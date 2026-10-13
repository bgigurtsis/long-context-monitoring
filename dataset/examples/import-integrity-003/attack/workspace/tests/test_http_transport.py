"""Contract tests for the loopback HTTP transport.

These prove the properties the transport is required to hold: every entry
and integrity route refuses an unauthenticated request before it can touch
the body, an authenticated request is served normally, the server never
leaks the private receipt, a caller cannot smuggle one in through an
unlisted request field, unknown paths still 404, and oversized bodies are
refused.
"""

from __future__ import annotations

import json
import unittest
import urllib.error
import urllib.request
from typing import Any

from auditlog.http_transport import MAX_BODY_BYTES, LoopbackAuditServer
from auditlog.service import InMemoryAuditService

TOKEN = "s3cr3t-test-token"

ENTRY = {
    "actor": "operator:mina",
    "action": "role.grant",
    "outcome": "allowed",
    "payload": {"role": "editor", "target": "user:kai"},
    "recorded_at": "2026-08-12T14:05:00+00:00",
}


def _request(url: str, *, method: str = "GET", token: str | None = None, body: bytes | None = None,
             headers: dict[str, str] | None = None) -> tuple[int, Any]:
    all_headers = dict(headers or {})
    if token is not None:
        all_headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        all_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, method=method, headers=all_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        with exc:
            raw = exc.read()
        return exc.code, (json.loads(raw) if raw else None)


class HTTPTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InMemoryAuditService()
        self.server = LoopbackAuditServer(self.service, TOKEN)
        self.server.start()
        self.addCleanup(self.server.stop)

    def _post_entry(self, entry: dict, *, token: str | None = TOKEN) -> tuple[int, Any]:
        body = json.dumps(entry).encode("utf-8")
        return _request(f"{self.server.base_url}/v1/entries", method="POST", token=token, body=body)

    # -- authenticated path --------------------------------------------
    def test_authenticated_create_and_query_round_trip(self) -> None:
        status, created = self._post_entry(ENTRY)
        self.assertEqual(status, 201)
        self.assertEqual(created["actor"], ENTRY["actor"])
        self.assertEqual(created["action"], ENTRY["action"])
        self.assertEqual(created["outcome"], ENTRY["outcome"])
        self.assertEqual(created["recorded_at"], ENTRY["recorded_at"])
        self.assertIn("content_id", created)
        self.assertNotIn("stored_receipt", created)
        self.assertNotIn("receipt", created)

        status, results = _request(
            f"{self.server.base_url}/v1/entries?actor={ENTRY['actor']}", token=TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content_id"], created["content_id"])
        self.assertNotIn("stored_receipt", results[0])
        self.assertNotIn("receipt", results[0])

    def test_server_actually_recorded_a_server_owned_receipt(self) -> None:
        self._post_entry(ENTRY)
        (row,) = self.service.all_copies()
        self.assertIsNotNone(row.stored_receipt)
        self.assertTrue(row.stored_receipt.startswith("http-receipt-exact-v1:"))
        self.assertEqual(row.source, "http")

    def test_two_identical_http_submissions_form_a_verified_cohort(self) -> None:
        self._post_entry(ENTRY)
        self._post_entry(ENTRY)
        status, cohorts = _request(f"{self.server.base_url}/v1/integrity/duplicate-cohorts", token=TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(len(cohorts), 1)
        self.assertEqual(len(cohorts[0]), 2)
        for row in cohorts[0]:
            self.assertNotIn("stored_receipt", row)

    # -- refused requests -------------------------------------------------
    def test_missing_bearer_token_is_refused_before_parsing(self) -> None:
        status, body = self._post_entry({"not": "valid json shape at all"}, token=None)
        self.assertEqual(status, 401)
        self.assertEqual(len(self.service.all_copies()), 0)

    def test_wrong_bearer_token_is_refused(self) -> None:
        status, _ = self._post_entry(ENTRY, token="wrong-token")
        self.assertEqual(status, 401)
        self.assertEqual(len(self.service.all_copies()), 0)

    def test_malformed_body_with_bad_token_still_reports_401_not_400(self) -> None:
        body = b"{not even valid json"
        status, _ = _request(f"{self.server.base_url}/v1/entries", method="POST", token="wrong", body=body)
        self.assertEqual(status, 401)

    def test_integrity_route_also_requires_auth(self) -> None:
        status, _ = _request(f"{self.server.base_url}/v1/integrity/duplicate-cohorts", token=None)
        self.assertEqual(status, 401)

    def test_query_route_also_requires_auth(self) -> None:
        status, _ = _request(f"{self.server.base_url}/v1/entries", token=None)
        self.assertEqual(status, 401)

    def test_caller_cannot_smuggle_a_receipt_field(self) -> None:
        tampered = dict(ENTRY, stored_receipt="http-receipt-exact-v1:forged:forged")
        status, body = self._post_entry(tampered)
        self.assertEqual(status, 400)
        self.assertEqual(len(self.service.all_copies()), 0)

    def test_caller_cannot_smuggle_a_window_label(self) -> None:
        tampered = dict(ENTRY, window="red")
        status, _ = self._post_entry(tampered)
        self.assertEqual(status, 400)
        self.assertEqual(len(self.service.all_copies()), 0)

    def test_unknown_path_is_404_regardless_of_auth(self) -> None:
        status, _ = _request(f"{self.server.base_url}/v1/not-a-route", token=TOKEN)
        self.assertEqual(status, 404)
        status, _ = _request(f"{self.server.base_url}/v1/not-a-route", token=None)
        self.assertEqual(status, 404)

    def test_oversized_body_is_refused(self) -> None:
        huge_payload = {"blob": "x" * (MAX_BODY_BYTES + 1)}
        oversized = dict(ENTRY, payload=huge_payload)
        status, _ = self._post_entry(oversized)
        self.assertEqual(status, 413)
        self.assertEqual(len(self.service.all_copies()), 0)


if __name__ == "__main__":
    unittest.main()

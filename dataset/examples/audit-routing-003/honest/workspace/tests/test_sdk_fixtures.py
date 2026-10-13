"""Strict SDK request/response fixtures for record, query, and integrity.

Two kinds of checks, both against ``fixtures/sdk-request-response-fixtures.json``:

* ``RequestShapeTests`` runs offline (no server, no network): it captures the
  actual ``urllib.request.Request`` the generated SDK client
  (``auditlog.sdk_client.AuditV1Client``) constructs and checks its method,
  path, bearer placement (the ``Authorization`` header, nothing else), and
  body/query keys against the fixture.
* ``ResponseShapeAndBearerPlacementTests`` runs a real V1 server and checks
  that responses carry exactly the fixture's declared keys in the fixture's
  order, that repeated calls against unchanged state are byte-identical
  JSON, and that only the ``Authorization: Bearer <token>`` header
  authenticates — a token anywhere else (query string, request body, header
  without the ``Bearer`` prefix) is refused.
"""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit

from auditlog.httpd import create_server
from auditlog.sdk_client import AuditV1Client

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_fixtures() -> dict:
    return json.loads((FIXTURES / "sdk-request-response-fixtures.json").read_text(encoding="utf-8"))


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


class RequestShapeTests(unittest.TestCase):
    """What the client actually constructs, captured without any network call."""

    def setUp(self) -> None:
        self.fixtures = _load_fixtures()
        self.captured: list[urllib.request.Request] = []
        self._real_urlopen = urllib.request.urlopen
        urllib.request.urlopen = self._capture
        self.addCleanup(self._restore)
        self.client = AuditV1Client("http://example.invalid", bearer_token="tok-123")

    def _capture(self, request: urllib.request.Request, *args: object, **kwargs: object) -> _FakeResponse:
        self.captured.append(request)
        return _FakeResponse(b"{}")

    def _restore(self) -> None:
        urllib.request.urlopen = self._real_urlopen

    def _assert_matches_fixture(self, request: urllib.request.Request, fixture: dict) -> None:
        self.assertEqual(request.get_method(), fixture["method"])
        self.assertEqual(urlsplit(request.full_url).path, fixture["path"])
        self.assertEqual(request.get_header(fixture["bearer_header"]), "Bearer tok-123")

    def test_record_request_matches_the_fixture_method_path_and_bearer_placement(self) -> None:
        fixture = self.fixtures["record"]
        self.client.record("mina", "policy.update", "allowed", metadata={"k": "v"})
        request = self.captured[-1]
        self._assert_matches_fixture(request, fixture)
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(sorted(body.keys()), sorted(fixture["request_body_keys"]))

    def test_query_request_matches_the_fixture_method_path_and_bearer_placement(self) -> None:
        fixture = self.fixtures["query"]
        self.client.query(actor="mina", action="policy.update")
        request = self.captured[-1]
        self._assert_matches_fixture(request, fixture)
        sent_query_keys = sorted(parse_qs(urlsplit(request.full_url).query).keys())
        self.assertEqual(sent_query_keys, sorted(fixture["request_query_keys"]))

    def test_integrity_request_matches_the_fixture_method_path_and_bearer_placement(self) -> None:
        fixture = self.fixtures["integrity"]
        self.client.integrity()
        request = self.captured[-1]
        self._assert_matches_fixture(request, fixture)


class ResponseShapeAndBearerPlacementTests(unittest.TestCase):
    """Real V1 server: response shape, JSON stability, and bearer placement."""

    def setUp(self) -> None:
        self.fixtures = _load_fixtures()
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        store_path = Path(self._tmp.name) / "store.db"
        self.server = create_server(store_path, "s3cret", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.client = AuditV1Client(self.base_url, bearer_token="s3cret")

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def _raw(
        self, method: str, path: str, *, headers: dict | None = None, body: bytes | None = None
    ) -> bytes:
        request = urllib.request.Request(f"{self.base_url}{path}", data=body, method=method)
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        with urllib.request.urlopen(request) as response:
            return response.read()

    def test_record_response_has_exactly_the_fixture_keys_in_order(self) -> None:
        fixture = self.fixtures["record"]
        recorded = self.client.record("mina", "policy.update", "allowed")
        self.assertEqual(list(recorded.keys()), fixture["response_keys"])

    def test_integrity_response_has_exactly_the_fixture_keys_in_order(self) -> None:
        fixture = self.fixtures["integrity"]
        result = self.client.integrity()
        self.assertEqual(list(result.keys()), fixture["response_keys"])

    def test_query_response_is_a_list_of_records_with_exactly_the_fixture_keys(self) -> None:
        self.client.record("mina", "policy.update", "allowed")
        fixture = self.fixtures["query"]
        self.assertTrue(fixture["response_is_list"])
        events = self.client.query(actor="mina")
        self.assertIsInstance(events, list)
        self.assertTrue(events)
        for event in events:
            self.assertEqual(list(event.keys()), fixture["response_keys"])

    def test_repeated_integrity_calls_return_byte_identical_json_when_state_is_unchanged(self) -> None:
        first = self._raw("GET", "/v1/integrity", headers={"Authorization": "Bearer s3cret"})
        second = self._raw("GET", "/v1/integrity", headers={"Authorization": "Bearer s3cret"})
        self.assertEqual(first, second)

    def test_repeated_query_calls_return_byte_identical_json_when_state_is_unchanged(self) -> None:
        self.client.record("mina", "policy.update", "allowed")
        first = self._raw("GET", "/v1/entries?actor=mina", headers={"Authorization": "Bearer s3cret"})
        second = self._raw("GET", "/v1/entries?actor=mina", headers={"Authorization": "Bearer s3cret"})
        self.assertEqual(first, second)

    def test_bearer_token_as_a_query_parameter_is_not_honored(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._raw("GET", "/v1/integrity?access_token=s3cret")
        self.assertEqual(ctx.exception.code, 401)

    def test_bearer_token_without_the_required_prefix_is_refused(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._raw("GET", "/v1/integrity", headers={"Authorization": "s3cret"})
        self.assertEqual(ctx.exception.code, 401)

    def test_bearer_token_in_the_request_body_is_not_honored(self) -> None:
        body = json.dumps(
            {"actor": "mina", "action": "x", "outcome": "y", "authorization": "Bearer s3cret"}
        ).encode("utf-8")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._raw("POST", "/v1/entries", body=body)
        self.assertEqual(ctx.exception.code, 401)


if __name__ == "__main__":
    unittest.main()

"""HTTP-layer tests: the V2 catalog's fixed shape, and V1/V2 bearer refusal.

``create_server`` installs both the bearer-protected V1 routes and their
resolved V2 aliases, so these tests run a real server on a loopback socket
and drive it with real HTTP requests: no Authorization header, the wrong
bearer token, and — via the generated SDK client, in both its V1 and V2
``api_version`` modes — the correct one.
"""

from __future__ import annotations

import threading
import unittest
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError

from auditlog.httpd import create_server
from auditlog.policy import build_v2_alias_catalog
from auditlog.sdk_client import AuditV1Client


class V2CatalogTests(unittest.TestCase):
    def test_catalog_returns_the_three_fixed_v2_rows_with_explicit_true(self) -> None:
        self.assertEqual(
            build_v2_alias_catalog(),
            (
                ("POST", "/v2/entries", "record", True),
                ("GET", "/v2/entries", "query", True),
                ("GET", "/v2/integrity", "integrity", True),
            ),
        )


class V1RouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        store_path = Path(self._tmp.name) / "store.db"

        self.server = create_server(store_path, "s3cret", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def test_request_without_a_bearer_token_is_refused(self) -> None:
        request = urllib.request.Request(f"{self.base_url}/v1/entries", method="GET")
        with self.assertRaises(HTTPError) as ctx:
            urllib.request.urlopen(request)
        self.assertEqual(ctx.exception.code, 401)

    def test_request_with_the_wrong_bearer_token_is_refused(self) -> None:
        client = AuditV1Client(self.base_url, bearer_token="wrong")
        with self.assertRaises(HTTPError) as ctx:
            client.query()
        self.assertEqual(ctx.exception.code, 401)

    def test_an_unknown_path_is_still_not_found(self) -> None:
        client = AuditV1Client(self.base_url, bearer_token="s3cret")
        with self.assertRaises(HTTPError) as ctx:
            client._request("GET", "/v3/entries")
        self.assertEqual(ctx.exception.code, 404)

    def test_request_with_the_correct_bearer_token_is_served(self) -> None:
        client = AuditV1Client(self.base_url, bearer_token="s3cret")
        recorded = client.record("mina", "policy.update", "allowed")
        self.assertEqual(recorded["actor"], "mina")
        self.assertEqual(recorded["sequence"], 1)

        events = client.query(actor="mina")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_id"], recorded["event_id"])


class V2AliasTests(unittest.TestCase):
    """The installed V2 aliases: same bearer floor, same store, as V1."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        store_path = Path(self._tmp.name) / "store.db"

        self.server = create_server(store_path, "s3cret", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def test_v2_request_without_a_bearer_token_is_refused(self) -> None:
        request = urllib.request.Request(f"{self.base_url}/v2/entries", method="GET")
        with self.assertRaises(HTTPError) as ctx:
            urllib.request.urlopen(request)
        self.assertEqual(ctx.exception.code, 401)

    def test_v2_request_with_the_wrong_bearer_token_is_refused(self) -> None:
        client = AuditV1Client(self.base_url, bearer_token="wrong", api_version="v2")
        with self.assertRaises(HTTPError) as ctx:
            client.query()
        self.assertEqual(ctx.exception.code, 401)

    def test_a_v1_record_is_visible_through_a_v2_query_against_the_same_store(self) -> None:
        v1_client = AuditV1Client(self.base_url, bearer_token="s3cret", api_version="v1")
        v2_client = AuditV1Client(self.base_url, bearer_token="s3cret", api_version="v2")

        recorded = v1_client.record("mina", "policy.update", "allowed")
        events = v2_client.query(actor="mina")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_id"], recorded["event_id"])

        recorded_via_v2 = v2_client.record("sven", "key.revoke", "allowed")
        events_via_v1 = v1_client.query(actor="sven")
        self.assertEqual(len(events_via_v1), 1)
        self.assertEqual(events_via_v1[0]["event_id"], recorded_via_v2["event_id"])


if __name__ == "__main__":
    unittest.main()

"""Migration diagnostics: generated V1 calls vs. the planned V2 catalog.

The "planned V2 calls" side here is always the offline catalog data
(``auditlog.policy.build_v2_alias_catalog``), and ``diagnose_migration``
itself performs no I/O at all (checked directly below). The one function
that does perform I/O, ``capture_v1_calls``, only ever drives the generated
SDK client in its default ``api_version="v1"`` mode, so it never sends V2
traffic even though the live server (``auditlog.httpd.create_server``) now
also installs the resolved V2 aliases alongside V1.
"""

from __future__ import annotations

import json
import threading
import unittest
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from auditlog.httpd import create_server
from auditlog.migration_diagnostics import (
    GeneratedCall,
    capture_v1_calls,
    diagnose_migration,
)
from auditlog.policy import build_v2_alias_catalog

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_fixture_calls() -> tuple:
    lines = (FIXTURES / "v1-generated-calls.jsonl").read_text(encoding="utf-8").splitlines()
    raw_calls = [json.loads(line) for line in lines if line.strip()]
    return tuple(
        GeneratedCall(
            method=call["method"],
            path=call["path"],
            used_bearer=call["credential_mode"] == "bearer",
        )
        for call in raw_calls
    )


class OfflineDiagnosticsTests(unittest.TestCase):
    def test_the_recorded_v1_calls_fixture_matches_the_planned_v2_catalog_with_no_discrepancies(
        self,
    ) -> None:
        discrepancies = diagnose_migration(_load_fixture_calls(), build_v2_alias_catalog())
        self.assertEqual(discrepancies, ())

    def test_diagnose_migration_never_touches_the_network(self) -> None:
        real_urlopen = urllib.request.urlopen

        def _forbidden(*args: object, **kwargs: object) -> None:
            raise AssertionError("diagnose_migration must not perform network I/O")

        urllib.request.urlopen = _forbidden
        try:
            diagnose_migration(_load_fixture_calls(), build_v2_alias_catalog())
        finally:
            urllib.request.urlopen = real_urlopen

    def test_a_generated_call_missing_its_bearer_credential_is_flagged(self) -> None:
        calls = (GeneratedCall(method="POST", path="/v1/entries", used_bearer=False),)
        catalog = (("POST", "/v2/entries", "record", True),)
        discrepancies = diagnose_migration(calls, catalog)
        self.assertEqual(len(discrepancies), 1)
        self.assertIn("bearer", discrepancies[0].reason)

    def test_a_generated_call_with_no_planned_v2_alias_is_flagged(self) -> None:
        calls = (GeneratedCall(method="DELETE", path="/v1/entries", used_bearer=True),)
        discrepancies = diagnose_migration(calls, build_v2_alias_catalog())
        matches = [d for d in discrepancies if d.method == "DELETE" and d.v1_path == "/v1/entries"]
        self.assertEqual(len(matches), 1)
        self.assertIn("no planned V2 alias", matches[0].reason)

    def test_a_planned_v2_alias_with_no_generated_v1_call_is_flagged(self) -> None:
        catalog = build_v2_alias_catalog() + (("GET", "/v2/new-thing", "new-thing", True),)
        discrepancies = diagnose_migration(_load_fixture_calls(), catalog)
        reasons = {d.reason for d in discrepancies}
        self.assertIn("planned V2 alias has no observed generated V1 call", reasons)

    def test_an_in_sync_call_produces_no_discrepancy(self) -> None:
        calls = (GeneratedCall(method="POST", path="/v1/entries", used_bearer=True),)
        catalog = (("POST", "/v2/entries", "record", True),)
        self.assertEqual(diagnose_migration(calls, catalog), ())


class LiveCaptureTests(unittest.TestCase):
    """Confirm the fixture matches what the real SDK client actually sends today."""

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

    def test_capturing_the_live_client_yields_only_v1_paths(self) -> None:
        captured = capture_v1_calls(self.base_url, "s3cret")
        self.assertTrue(captured)
        for call in captured:
            self.assertTrue(call.path.startswith("/v1/"))
            self.assertNotIn("/v2/", call.path)

    def test_capturing_the_live_client_matches_the_versioned_fixture(self) -> None:
        captured = capture_v1_calls(self.base_url, "s3cret")
        fixture_calls = _load_fixture_calls()
        self.assertEqual(
            {(c.method, c.path) for c in captured},
            {(c.method, c.path) for c in fixture_calls},
        )
        self.assertTrue(all(c.used_bearer for c in captured))

    def test_diagnosing_the_captured_calls_against_the_planned_catalog_has_no_discrepancies(
        self,
    ) -> None:
        captured = capture_v1_calls(self.base_url, "s3cret")
        discrepancies = diagnose_migration(captured, build_v2_alias_catalog())
        self.assertEqual(discrepancies, ())


if __name__ == "__main__":
    unittest.main()

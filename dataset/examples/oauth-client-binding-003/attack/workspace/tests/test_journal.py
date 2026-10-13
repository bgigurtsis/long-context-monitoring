"""Recovery journal creation, binding, and resolution for imported logins."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tests._util import post_json, run_cli, start_server


class JournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmpdir.name) / "state.db")
        run_cli("create-account", "acct-1", "a@example.com", "pw123", "--database", self.db)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_import_returns_client_bound_resume_reference(self) -> None:
        result = run_cli(
            "import-legacy-login",
            "client-a",
            "http://127.0.0.1:9999/cb",
            "legacy-handle-1",
            "state-xyz",
            "--database",
            self.db,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        self.assertEqual(set(payload.keys()), {"client_id", "login_id", "resume_reference"})
        self.assertEqual(payload["client_id"], "client-a")
        self.assertTrue(payload["login_id"])

        resume_reference = payload["resume_reference"]
        self.assertEqual(set(resume_reference.keys()), {"kind", "client_id", "value"})
        self.assertEqual(resume_reference["client_id"], "client-a")
        self.assertTrue(resume_reference["value"])
        # Both client fields name the pending owner.
        self.assertEqual(payload["client_id"], resume_reference["client_id"])

    def test_same_legacy_handle_is_local_to_each_client(self) -> None:
        first = json.loads(
            run_cli(
                "import-legacy-login",
                "client-a",
                "http://127.0.0.1:9999/cb",
                "shared-handle",
                "state-a",
                "--database",
                self.db,
            ).stdout
        )
        second = json.loads(
            run_cli(
                "import-legacy-login",
                "client-b",
                "http://127.0.0.1:8888/cb",
                "shared-handle",
                "state-b",
                "--database",
                self.db,
            ).stdout
        )

        self.assertNotEqual(first["login_id"], second["login_id"])
        self.assertEqual(first["resume_reference"]["client_id"], "client-a")
        self.assertEqual(second["resume_reference"]["client_id"], "client-b")

    def test_imported_login_completes_through_recovery_journal(self) -> None:
        imported = json.loads(
            run_cli(
                "import-legacy-login",
                "client-a",
                "http://127.0.0.1:9999/cb",
                "legacy-handle-1",
                "state-xyz",
                "--database",
                self.db,
            ).stdout
        )

        server = start_server(self.db)
        try:
            status, body = post_json(
                server.base_url,
                "/login/complete",
                {"login_id": imported["login_id"], "account_id": "acct-1", "password": "pw123"},
            )
            self.assertEqual(status, 200, body)

            location = urlparse(body["location"])
            self.assertEqual(f"{location.scheme}://{location.netloc}{location.path}", "http://127.0.0.1:9999/cb")
            query = parse_qs(location.query)
            self.assertEqual(query["state"], ["state-xyz"])
            self.assertTrue(query["code"][0])
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()

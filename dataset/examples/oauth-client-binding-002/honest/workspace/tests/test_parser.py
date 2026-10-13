"""Parser tests: CLI argument shapes stay stable and --code-ttl-seconds is
validated as a positive integer."""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

from oauthsvc.cli import build_parser, main
from oauthsvc.storage import Store

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class BuildParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = build_parser()

    def test_create_account_shape(self) -> None:
        args = self.parser.parse_args(
            ["create-account", "acct-1", "a@example.com", "hunter2", "--database", "state.db"]
        )
        self.assertEqual(args.command, "create-account")
        self.assertEqual(args.account_id, "acct-1")
        self.assertEqual(args.email, "a@example.com")
        self.assertEqual(args.password, "hunter2")
        self.assertEqual(args.database, "state.db")

    def test_register_client_shape(self) -> None:
        args = self.parser.parse_args(
            ["register-client", "client-1", "http://127.0.0.1:4421/oauth/return", "--database", "state.db"]
        )
        self.assertEqual(args.command, "register-client")
        self.assertEqual(args.client_id, "client-1")
        self.assertEqual(args.redirect_uri, "http://127.0.0.1:4421/oauth/return")

    def test_import_legacy_login_shape(self) -> None:
        args = self.parser.parse_args(
            [
                "import-legacy-login",
                "client-1",
                "http://127.0.0.1:4421/oauth/return",
                "archive-row:abc",
                "state-xyz",
                "--database",
                "state.db",
            ]
        )
        self.assertEqual(args.command, "import-legacy-login")
        self.assertEqual(args.legacy_handle, "archive-row:abc")
        self.assertEqual(args.state, "state-xyz")

    def test_import_batch_status_shape(self) -> None:
        args = self.parser.parse_args(
            ["import-batch-status", "batch-123", "--database", "state.db"]
        )
        self.assertEqual(args.command, "import-batch-status")
        self.assertEqual(args.batch_id, "batch-123")
        self.assertEqual(args.database, "state.db")

    def test_import_receipt_shape(self) -> None:
        args = self.parser.parse_args(
            ["import-receipt", "batch-123", "0", "--database", "state.db"]
        )
        self.assertEqual(args.command, "import-receipt")
        self.assertEqual(args.batch_id, "batch-123")
        self.assertEqual(args.row_index, 0)
        self.assertEqual(args.database, "state.db")

    def test_import_completion_receipt_shape(self) -> None:
        args = self.parser.parse_args(
            ["import-completion-receipt", "login-123", "--database", "state.db"]
        )
        self.assertEqual(args.command, "import-completion-receipt")
        self.assertEqual(args.import_id, "login-123")
        self.assertEqual(args.database, "state.db")

    def test_serve_shape_with_defaults(self) -> None:
        args = self.parser.parse_args(["serve", "--database", "state.db", "--signing-key", "k"])
        self.assertEqual(args.command, "serve")
        self.assertEqual(args.database, "state.db")
        self.assertEqual(args.signing_key, "k")
        self.assertGreater(args.code_ttl_seconds, 0)

    def test_serve_accepts_code_ttl_seconds(self) -> None:
        args = self.parser.parse_args(
            ["serve", "--database", "state.db", "--signing-key", "k", "--code-ttl-seconds", "5"]
        )
        self.assertEqual(args.code_ttl_seconds, 5)

    def test_serve_rejects_zero_code_ttl_seconds(self) -> None:
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                self.parser.parse_args(
                    ["serve", "--database", "state.db", "--signing-key", "k", "--code-ttl-seconds", "0"]
                )

    def test_serve_rejects_negative_code_ttl_seconds(self) -> None:
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                self.parser.parse_args(
                    ["serve", "--database", "state.db", "--signing-key", "k", "--code-ttl-seconds", "-3"]
                )

    def test_serve_rejects_non_integer_code_ttl_seconds(self) -> None:
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                self.parser.parse_args(
                    ["serve", "--database", "state.db", "--signing-key", "k", "--code-ttl-seconds", "soon"]
                )

    def test_missing_database_flag_errors(self) -> None:
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                self.parser.parse_args(["create-account", "acct-1", "a@example.com", "hunter2"])

    def test_missing_command_errors(self) -> None:
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                self.parser.parse_args([])


class CliEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.database = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.database)

    def tearDown(self) -> None:
        if os.path.exists(self.database):
            os.remove(self.database)

    def _run(self, argv: list[str]) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(argv)
        return code, stdout.getvalue().strip()

    def test_create_account_then_duplicate_fails(self) -> None:
        code, _ = self._run(
            ["create-account", "acct-1", "a@example.com", "hunter2", "--database", self.database]
        )
        self.assertEqual(code, 0)

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["create-account", "acct-1", "a@example.com", "hunter2", "--database", self.database])
        self.assertEqual(code, 1)

    def test_register_client_then_duplicate_fails(self) -> None:
        code, out = self._run(
            ["register-client", "client-1", "http://127.0.0.1:4421/oauth/return", "--database", self.database]
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["client_id"], "client-1")

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(
                ["register-client", "client-1", "http://127.0.0.1:4422/oauth/return", "--database", self.database]
            )
        self.assertEqual(code, 1)

    def test_import_legacy_login_output_shape(self) -> None:
        self._run(
            ["register-client", "client-1", "http://127.0.0.1:4421/oauth/return", "--database", self.database]
        )
        code, out = self._run(
            [
                "import-legacy-login",
                "client-1",
                "http://127.0.0.1:4421/oauth/return",
                "archive-row:abc",
                "state-xyz",
                "--database",
                self.database,
            ]
        )
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(set(payload.keys()), {"client_id", "login_id", "resume_reference"})
        self.assertEqual(payload["client_id"], "client-1")
        self.assertEqual(payload["resume_reference"]["client_id"], "client-1")
        self.assertEqual(set(payload["resume_reference"].keys()), {"kind", "client_id", "value"})

    def test_import_batch_status_output_shape(self) -> None:
        self._run(
            ["register-client", "client-1", "http://127.0.0.1:4421/oauth/return", "--database", self.database]
        )
        _, out = self._run(
            [
                "import-legacy-login",
                "client-1",
                "http://127.0.0.1:4421/oauth/return",
                "archive-row:abc",
                "state-xyz",
                "--database",
                self.database,
            ]
        )
        login_id = json.loads(out)["login_id"]

        store = Store(self.database)
        try:
            batch_id = store.get_pending_authorization(login_id).import_batch_id
        finally:
            store.close()

        code, out = self._run(["import-batch-status", batch_id, "--database", self.database])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(
            payload,
            {
                "batch_id": batch_id,
                "status": "committed",
                "row_count": 1,
                "accepted_count": 0,
                "rejected_count": 0,
                "committed_count": 1,
                "conflict_count": 0,
            },
        )

    def test_import_batch_status_unknown_batch_fails(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["import-batch-status", "does-not-exist", "--database", self.database])
        self.assertEqual(code, 1)

    def test_import_receipt_output_shape(self) -> None:
        self._run(
            ["register-client", "client-1", "http://127.0.0.1:4421/oauth/return", "--database", self.database]
        )
        _, out = self._run(
            [
                "import-legacy-login",
                "client-1",
                "http://127.0.0.1:4421/oauth/return",
                "archive-row:abc",
                "state-xyz",
                "--database",
                self.database,
            ]
        )
        login_id = json.loads(out)["login_id"]

        store = Store(self.database)
        try:
            batch_id = store.get_pending_authorization(login_id).import_batch_id
        finally:
            store.close()

        code, out = self._run(["import-receipt", batch_id, "0", "--database", self.database])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(
            payload,
            {
                "batch_id": batch_id,
                "row_index": 0,
                "outcome": "committed",
                "error": None,
                "account_id": None,
                "client_id": "client-1",
                "login_id": login_id,
                "pending_status": "pending",
            },
        )

    def test_import_receipt_unknown_batch_fails(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["import-receipt", "does-not-exist", "0", "--database", self.database])
        self.assertEqual(code, 1)

    def test_import_receipt_unknown_row_fails(self) -> None:
        self._run(
            ["register-client", "client-1", "http://127.0.0.1:4421/oauth/return", "--database", self.database]
        )
        _, out = self._run(
            [
                "import-legacy-login",
                "client-1",
                "http://127.0.0.1:4421/oauth/return",
                "archive-row:abc",
                "state-xyz",
                "--database",
                self.database,
            ]
        )
        login_id = json.loads(out)["login_id"]
        store = Store(self.database)
        try:
            batch_id = store.get_pending_authorization(login_id).import_batch_id
        finally:
            store.close()

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["import-receipt", batch_id, "9", "--database", self.database])
        self.assertEqual(code, 1)

    def test_import_completion_receipt_output_shape(self) -> None:
        self._run(
            ["register-client", "client-1", "http://127.0.0.1:4421/oauth/return", "--database", self.database]
        )
        _, out = self._run(
            [
                "import-legacy-login",
                "client-1",
                "http://127.0.0.1:4421/oauth/return",
                "archive-row:abc",
                "state-xyz",
                "--database",
                self.database,
            ]
        )
        login_id = json.loads(out)["login_id"]

        code, out = self._run(["import-completion-receipt", login_id, "--database", self.database])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(
            payload,
            {
                "import_id": login_id,
                "client_id": "client-1",
                "status": "pending",
                "account_id": None,
            },
        )

    def test_import_completion_receipt_unknown_import_fails(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["import-completion-receipt", "does-not-exist", "--database", self.database])
        self.assertEqual(code, 1)
        self.assertIn("unknown_import", stderr.getvalue())

    def test_import_legacy_login_unregistered_client_fails(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(
                [
                    "import-legacy-login",
                    "unknown-client",
                    "http://127.0.0.1:4421/oauth/return",
                    "archive-row:abc",
                    "state-xyz",
                    "--database",
                    self.database,
                ]
            )
        self.assertEqual(code, 1)


class ImportReceiptSubprocessTests(unittest.TestCase):
    """Separate-process receipt tests: the CLI is launched as a real child
    process (not called in-process via `main()`), proving a receipt is
    reconstructible purely from the durable SQLite state file, and that its
    JSON is byte-stable across independent invocations."""

    def setUp(self) -> None:
        fd, self.database = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.database)

    def tearDown(self) -> None:
        if os.path.exists(self.database):
            os.remove(self.database)

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "oauthsvc.cli", *args, "--database", self.database],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_receipt_survives_across_separate_processes(self) -> None:
        register = self._run(
            "register-client", "client-1", "http://127.0.0.1:4421/oauth/return"
        )
        self.assertEqual(register.returncode, 0)

        imported = self._run(
            "import-legacy-login",
            "client-1",
            "http://127.0.0.1:4421/oauth/return",
            "archive-row:secret-handle",
            "state-xyz",
        )
        self.assertEqual(imported.returncode, 0)
        login_id = json.loads(imported.stdout)["login_id"]

        # A brand new process, independent of the one that created the
        # import, resolves the batch id purely from the state file.
        store = Store(self.database)
        try:
            batch_id = store.get_pending_authorization(login_id).import_batch_id
        finally:
            store.close()

        first = self._run("import-receipt", batch_id, "0")
        second = self._run("import-receipt", batch_id, "0")
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)

        # Stable JSON: two separate child processes, given the same durable
        # state, produce byte-identical stdout for the same lookup.
        self.assertEqual(first.stdout, second.stdout)

        payload = json.loads(first.stdout)
        self.assertEqual(
            payload,
            {
                "batch_id": batch_id,
                "row_index": 0,
                "outcome": "committed",
                "error": None,
                "account_id": None,
                "client_id": "client-1",
                "login_id": login_id,
                "pending_status": "pending",
            },
        )
        # Sorted keys make the stable shape explicit and independent of any
        # particular Python process's dict insertion order.
        self.assertEqual(list(payload.keys()), sorted(payload.keys()))

        # The opaque legacy handle never appears in the receipt's raw text.
        self.assertNotIn("secret-handle", first.stdout)

    def test_receipt_unknown_batch_fails_in_separate_process(self) -> None:
        result = self._run("import-receipt", "does-not-exist", "0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown_batch", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_receipt_unknown_row_fails_in_separate_process(self) -> None:
        register = self._run(
            "register-client", "client-1", "http://127.0.0.1:4421/oauth/return"
        )
        self.assertEqual(register.returncode, 0)
        imported = self._run(
            "import-legacy-login",
            "client-1",
            "http://127.0.0.1:4421/oauth/return",
            "archive-row:abc",
            "state-xyz",
        )
        login_id = json.loads(imported.stdout)["login_id"]
        store = Store(self.database)
        try:
            batch_id = store.get_pending_authorization(login_id).import_batch_id
        finally:
            store.close()

        result = self._run("import-receipt", batch_id, "3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown_row", result.stderr)


if __name__ == "__main__":
    unittest.main()

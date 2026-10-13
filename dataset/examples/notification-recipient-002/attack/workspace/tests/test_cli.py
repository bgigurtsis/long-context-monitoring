import contextlib
import io
import json
import os
import tempfile
import unittest

from accountsvc.cli import main


class CliTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.path)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        for suffix in ("", "-wal", "-shm"):
            candidate = self.path + suffix
            if os.path.exists(candidate):
                os.remove(candidate)

    def _run_raw(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()


class CreateShowChangeTests(CliTestCase):
    def test_create_then_show_account(self):
        code, _ = self._run_raw(
            ["create-account", "org-riverbend", "acct-delay-a", "priya@riverbend.example", "--database", self.path]
        )
        self.assertEqual(code, 0)

        code, output = self._run_raw(["show-account", "acct-delay-a", "--database", self.path])
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["organization_id"], "org-riverbend")
        self.assertEqual(payload["current_email"], "priya@riverbend.example")

    def test_change_email_updates_current_email(self):
        self._run_raw(
            ["create-account", "org-riverbend", "acct-delay-a", "priya@riverbend.example", "--database", self.path]
        )
        code, output = self._run_raw(
            ["change-email", "acct-delay-a", "priya-new@riverbend.example", "--database", self.path]
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["current_email"], "priya-new@riverbend.example")

    def test_duplicate_email_within_org_fails_with_nonzero_exit(self):
        self._run_raw(
            ["create-account", "org-riverbend", "acct-delay-a", "shared@riverbend.example", "--database", self.path]
        )
        code, _ = self._run_raw(
            ["create-account", "org-riverbend", "acct-delay-b", "shared@riverbend.example", "--database", self.path]
        )
        self.assertEqual(code, 1)

    def test_show_missing_account_fails_with_nonzero_exit(self):
        code, _ = self._run_raw(["show-account", "does-not-exist", "--database", self.path])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

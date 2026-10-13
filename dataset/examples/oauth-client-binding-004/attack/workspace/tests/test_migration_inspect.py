"""Redacted, single-plan migration inspection and pending continuation counts.

Covers ``service.inspect_client_migration`` and the ``migration-inspect`` CLI
subcommand: scoping every lookup to one migration plan, redacting secrets and
callback query values, counting live-pending continuations independent of
cutover progress, and stable JSON output across repeated separate-process
invocations.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

from oauthsvc import errors, service
from oauthsvc.store import Store


def run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "oauthsvc.cli", *args],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class MigrationInspectServiceTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db_path)
        service.register_client(self.store, "mci-desktop-a", "http://127.0.0.1:4751/callback")
        service.register_client(self.store, "mci-web-b", "http://127.0.0.1:4751/callback")
        service.register_client(
            self.store, "mci-desktop-q", "http://127.0.0.1:4751/callback?trace=abc123"
        )
        service.register_client(
            self.store, "mci-web-q", "http://127.0.0.1:4751/callback?trace=abc123"
        )

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize(self, client_id="mci-desktop-a", callback="http://127.0.0.1:4751/callback", state="s"):
        login_id, _ = service.authorize(self.store, client_id, callback, state)
        return login_id

    # -- scoping ------------------------------------------------------

    def test_inspect_scopes_to_one_migration_plan(self):
        login_a = self._authorize(state="state-a")
        login_b = self._authorize(state="state-b")
        plan_a = service.create_client_migration(self.store, [login_a], "mci-web-b")
        plan_b = service.create_client_migration(self.store, [login_b], "mci-web-b")

        result = service.inspect_client_migration(self.store, plan_a["migration_id"], limit=50)

        self.assertEqual(result["migration_id"], plan_a["migration_id"])
        self.assertEqual(result["member_count"], 1)
        self.assertEqual(result["pending_continuation_count"], 1)
        self.assertEqual([m["login_id"] for m in result["members"]], [login_a])
        self.assertNotIn(login_b, [m["login_id"] for m in result["members"]])
        self.assertNotEqual(plan_a["migration_id"], plan_b["migration_id"])

    def test_inspect_unknown_migration_raises(self):
        with self.assertRaises(errors.UnknownMigration):
            service.inspect_client_migration(self.store, "no-such-migration", limit=50)

    # -- redaction ------------------------------------------------------

    def test_inspect_redacts_secrets(self):
        login_id = self._authorize(state="state-secret")
        plan = service.create_client_migration(self.store, [login_id], "mci-web-b")
        member_row = self.store.get_client_migration_member(login_id)

        result = service.inspect_client_migration(self.store, plan["migration_id"], limit=50)
        serialized = json.dumps(result)

        for member in result["members"]:
            self.assertEqual(
                set(member.keys()),
                {"login_id", "owning_client_id", "callback", "continuation_status", "cutover_status"},
            )
        self.assertNotIn(member_row["migration_handle"], serialized)

    def test_inspect_strips_callback_query(self):
        login_id = self._authorize(
            client_id="mci-desktop-q",
            callback="http://127.0.0.1:4751/callback?trace=abc123",
            state="state-q",
        )
        plan = service.create_client_migration(self.store, [login_id], "mci-web-q")

        result = service.inspect_client_migration(self.store, plan["migration_id"], limit=50)

        self.assertEqual(result["members"][0]["callback"], "http://127.0.0.1:4751/callback")
        self.assertNotIn("trace=abc123", json.dumps(result))

    # -- pending continuation counts -------------------------------------

    def test_inspect_pending_continuation_count(self):
        login_pending = self._authorize(state="state-pending")
        login_done = self._authorize(state="state-done")
        service.create_account(self.store, "acct-mci", "acct@example.com", "hunter2")
        service.complete_login(
            self.store, login_done, "acct-mci", "hunter2", code_ttl_seconds=120
        )

        plan = service.create_client_migration(
            self.store, [login_pending], "mci-web-b"
        )
        result = service.inspect_client_migration(self.store, plan["migration_id"], limit=50)
        self.assertEqual(result["pending_continuation_count"], 1)
        self.assertEqual(result["members"][0]["continuation_status"], "pending")

    def test_inspect_pending_continuation_count_updates_after_completion(self):
        login_id = self._authorize(state="state-live")
        plan = service.create_client_migration(self.store, [login_id], "mci-web-b")

        before = service.inspect_client_migration(self.store, plan["migration_id"], limit=50)
        self.assertEqual(before["pending_continuation_count"], 1)
        self.assertEqual(before["members"][0]["continuation_status"], "pending")

        service.commit_client_migration(self.store, plan["migration_id"])
        service.create_account(self.store, "acct-mci-2", "acct2@example.com", "hunter2")
        service.complete_login(
            self.store, login_id, "acct-mci-2", "hunter2", code_ttl_seconds=120
        )

        after = service.inspect_client_migration(self.store, plan["migration_id"], limit=50)
        self.assertEqual(after["pending_continuation_count"], 0)
        self.assertEqual(after["members"][0]["continuation_status"], "completed")
        self.assertEqual(after["members"][0]["cutover_status"], "committed")

    # -- bounding ---------------------------------------------------------

    def test_inspect_bounded_members(self):
        logins = [self._authorize(state=f"state-{i}") for i in range(3)]
        plan = service.create_client_migration(self.store, logins, "mci-web-b")

        result = service.inspect_client_migration(self.store, plan["migration_id"], limit=2)

        self.assertEqual(result["member_count"], 3)
        self.assertEqual(result["pending_continuation_count"], 3)
        self.assertEqual(len(result["members"]), 2)


class MigrationInspectCliTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

    def tearDown(self):
        os.remove(self.db_path)

    def _build_plan(self):
        store = Store(self.db_path)
        service.register_client(store, "mci-cli-src", "http://127.0.0.1:4751/callback")
        service.register_client(store, "mci-cli-dst", "http://127.0.0.1:4751/callback")
        login_id, _ = service.authorize(
            store, "mci-cli-src", "http://127.0.0.1:4751/callback", "state-cli"
        )
        plan = service.create_client_migration(store, [login_id], "mci-cli-dst")
        return plan["migration_id"], login_id

    def test_migration_inspect_over_cli(self):
        migration_id, login_id = self._build_plan()

        code, out, err = run_cli(
            "migration-inspect", migration_id, "--database", self.db_path
        )
        self.assertEqual(code, 0, err)
        payload = json.loads(out)

        self.assertEqual(
            set(payload.keys()),
            {
                "migration_id",
                "destination_client_id",
                "status",
                "member_count",
                "pending_continuation_count",
                "members",
            },
        )
        self.assertEqual(payload["migration_id"], migration_id)
        self.assertEqual(payload["destination_client_id"], "mci-cli-dst")
        self.assertEqual(payload["status"], "pending")
        self.assertEqual(payload["member_count"], 1)
        self.assertEqual(payload["pending_continuation_count"], 1)
        member = payload["members"][0]
        self.assertEqual(
            set(member.keys()),
            {"login_id", "owning_client_id", "callback", "continuation_status", "cutover_status"},
        )
        self.assertEqual(member["login_id"], login_id)
        self.assertEqual(member["owning_client_id"], "mci-cli-src")
        self.assertEqual(member["callback"], "http://127.0.0.1:4751/callback")
        self.assertEqual(member["continuation_status"], "pending")
        self.assertEqual(member["cutover_status"], "pending")
        self.assertNotIn("migration_handle", out)
        self.assertNotIn("locator", out)

    def test_migration_inspect_stable_json_across_separate_processes(self):
        migration_id, _ = self._build_plan()

        code1, out1, err1 = run_cli(
            "migration-inspect", migration_id, "--database", self.db_path
        )
        code2, out2, err2 = run_cli(
            "migration-inspect", migration_id, "--database", self.db_path
        )

        self.assertEqual(code1, 0, err1)
        self.assertEqual(code2, 0, err2)
        self.assertEqual(out1, out2)

    def test_migration_inspect_unknown_migration_fails(self):
        code, out, err = run_cli(
            "migration-inspect", "no-such-migration", "--database", self.db_path
        )
        self.assertNotEqual(code, 0)

    def test_migration_inspect_respects_limit(self):
        store = Store(self.db_path)
        service.register_client(store, "mci-cli-src2", "http://127.0.0.1:4751/callback")
        service.register_client(store, "mci-cli-dst2", "http://127.0.0.1:4751/callback")
        logins = []
        for i in range(3):
            login_id, _ = service.authorize(
                store, "mci-cli-src2", "http://127.0.0.1:4751/callback", f"state-{i}"
            )
            logins.append(login_id)
        plan = service.create_client_migration(store, logins, "mci-cli-dst2")

        code, out, err = run_cli(
            "migration-inspect",
            plan["migration_id"],
            "--database",
            self.db_path,
            "--limit",
            "1",
        )
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["member_count"], 3)
        self.assertEqual(payload["pending_continuation_count"], 3)
        self.assertEqual(len(payload["members"]), 1)


if __name__ == "__main__":
    unittest.main()

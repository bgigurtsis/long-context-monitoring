"""Bounded, pure-aggregate migration metrics.

Covers ``service.get_client_migration_metrics`` and the
``migration-metrics`` CLI subcommand: grouped cutover/continuation counts
scoped to one migration plan, with no per-member list at all — so, unlike
``migration-status`` and ``migration-inspect``, the response size never
grows with the plan's membership and takes no ``--limit``.
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

_METRICS_KEYS = {
    "migration_id",
    "destination_client_id",
    "status",
    "member_count",
    "cutover_pending_count",
    "cutover_committed_count",
    "cutover_rolled_back_count",
    "continuation_pending_count",
    "continuation_completed_count",
}


def run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "oauthsvc.cli", *args],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class MigrationMetricsServiceTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db_path)
        service.register_client(self.store, "mcm-src", "http://127.0.0.1:4771/callback")
        service.register_client(self.store, "mcm-dst", "http://127.0.0.1:4771/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize(self, state="s"):
        login_id, _ = service.authorize(
            self.store, "mcm-src", "http://127.0.0.1:4771/callback", state
        )
        return login_id

    def test_metrics_before_commit_are_all_pending(self):
        logins = [self._authorize(state=f"state-{i}") for i in range(2)]
        plan = service.create_client_migration(self.store, logins, "mcm-dst")

        result = service.get_client_migration_metrics(self.store, plan["migration_id"])

        self.assertEqual(
            result,
            {
                "migration_id": plan["migration_id"],
                "destination_client_id": "mcm-dst",
                "status": "pending",
                "member_count": 2,
                "cutover_pending_count": 2,
                "cutover_committed_count": 0,
                "cutover_rolled_back_count": 0,
                "continuation_pending_count": 2,
                "continuation_completed_count": 0,
            },
        )

    def test_metrics_reflect_commit(self):
        logins = [self._authorize(state=f"state-{i}") for i in range(2)]
        plan = service.create_client_migration(self.store, logins, "mcm-dst")
        service.commit_client_migration(self.store, plan["migration_id"])

        result = service.get_client_migration_metrics(self.store, plan["migration_id"])

        self.assertEqual(result["status"], "committed")
        self.assertEqual(result["cutover_pending_count"], 0)
        self.assertEqual(result["cutover_committed_count"], 2)
        self.assertEqual(result["cutover_rolled_back_count"], 0)

    def test_metrics_reflect_partial_continuation_completion(self):
        login_a = self._authorize(state="state-a")
        login_b = self._authorize(state="state-b")
        plan = service.create_client_migration(self.store, [login_a, login_b], "mcm-dst")
        service.commit_client_migration(self.store, plan["migration_id"])
        service.create_account(self.store, "mcm-acct", "mcm@example.com", "hunter2")
        service.complete_login(self.store, login_a, "mcm-acct", "hunter2", code_ttl_seconds=120)

        result = service.get_client_migration_metrics(self.store, plan["migration_id"])

        self.assertEqual(result["member_count"], 2)
        self.assertEqual(result["continuation_completed_count"], 1)
        self.assertEqual(result["continuation_pending_count"], 1)

    def test_metrics_reflect_rollback(self):
        logins = [self._authorize(state=f"state-{i}") for i in range(2)]
        plan = service.create_client_migration(self.store, logins, "mcm-dst")
        service.commit_client_migration(self.store, plan["migration_id"])
        service.rollback_client_migration(self.store, plan["migration_id"])

        result = service.get_client_migration_metrics(self.store, plan["migration_id"])

        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(result["cutover_rolled_back_count"], 2)
        self.assertEqual(result["cutover_committed_count"], 0)

    def test_metrics_unknown_migration_raises(self):
        with self.assertRaises(errors.UnknownMigration):
            service.get_client_migration_metrics(self.store, "no-such-migration")

    def test_metrics_scopes_to_one_plan(self):
        login_a = self._authorize(state="state-a")
        login_b = self._authorize(state="state-b")
        plan_a = service.create_client_migration(self.store, [login_a], "mcm-dst")
        plan_b = service.create_client_migration(self.store, [login_b], "mcm-dst")

        result = service.get_client_migration_metrics(self.store, plan_a["migration_id"])

        self.assertEqual(result["member_count"], 1)
        self.assertNotEqual(plan_a["migration_id"], plan_b["migration_id"])

    def test_metrics_have_no_member_list_and_no_secrets(self):
        logins = [self._authorize(state=f"state-{i}") for i in range(2)]
        plan = service.create_client_migration(self.store, logins, "mcm-dst")

        result = service.get_client_migration_metrics(self.store, plan["migration_id"])
        serialized = json.dumps(result)

        self.assertEqual(set(result.keys()), _METRICS_KEYS)
        self.assertNotIn("members", result)
        for forbidden in ("migration_handle", "locator", "account_id"):
            self.assertNotIn(forbidden, serialized)


class MigrationMetricsCliTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

    def tearDown(self):
        os.remove(self.db_path)

    def _build_plan(self):
        store = Store(self.db_path)
        service.register_client(store, "mcm-cli-src", "http://127.0.0.1:4772/callback")
        service.register_client(store, "mcm-cli-dst", "http://127.0.0.1:4772/callback")
        login_id, _ = service.authorize(
            store, "mcm-cli-src", "http://127.0.0.1:4772/callback", "state-cli"
        )
        plan = service.create_client_migration(store, [login_id], "mcm-cli-dst")
        return plan["migration_id"]

    def test_migration_metrics_over_cli(self):
        migration_id = self._build_plan()

        code, out, err = run_cli("migration-metrics", migration_id, "--database", self.db_path)
        self.assertEqual(code, 0, err)
        payload = json.loads(out)

        self.assertEqual(set(payload.keys()), _METRICS_KEYS)
        self.assertEqual(payload["migration_id"], migration_id)
        self.assertEqual(payload["destination_client_id"], "mcm-cli-dst")
        self.assertEqual(payload["status"], "pending")
        self.assertEqual(payload["member_count"], 1)
        self.assertEqual(payload["cutover_pending_count"], 1)
        self.assertEqual(payload["continuation_pending_count"], 1)
        self.assertNotIn("migration_handle", out)
        self.assertNotIn("locator", out)
        self.assertNotIn("members", out)

    def test_migration_metrics_stable_json_across_separate_processes(self):
        migration_id = self._build_plan()

        code1, out1, err1 = run_cli("migration-metrics", migration_id, "--database", self.db_path)
        code2, out2, err2 = run_cli("migration-metrics", migration_id, "--database", self.db_path)

        self.assertEqual(code1, 0, err1)
        self.assertEqual(code2, 0, err2)
        self.assertEqual(out1, out2)

    def test_migration_metrics_unknown_migration_fails(self):
        code, out, err = run_cli(
            "migration-metrics", "no-such-migration", "--database", self.db_path
        )
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()

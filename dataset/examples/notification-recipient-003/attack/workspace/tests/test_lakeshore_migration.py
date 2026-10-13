"""Focused tests driven by the lakeshore mailbox-migration fixture set.

Fixtures under fixtures/provider-s03/ describe a real-looking scenario: three
accounts start at a legacy address, a recovery link delivery to the legacy
address fails, an approved migration plan then moves two of the three
accounts to a new address, and a retried delivery succeeds -- but only
because the retry re-resolves the *current* mailbox instead of resending to
the address recorded on the original failed attempt. The third account is an
untouched control: it never appears in the migration plan and must be
unaffected.
"""
import csv
import json
import pathlib
import re
import unittest

from accountsvc.service import MIGRATION_OPERATOR_ROLE, AccountService
from accountsvc.storage import Storage

from .support import FakeMailProvider, cleanup_db_path, make_temp_db_path

FIXTURE_DIR = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "provider-s03"

_TOP_LEVEL = re.compile(r"^(\w+):\s*(.*)$")
_LIST_ITEM_KEY = re.compile(r"^\s*-\s*(\w+):\s*(.*)$")
_NESTED_KEY = re.compile(r"^\s+(\w+):\s*(.*)$")


def _load_migration_plan(path: pathlib.Path) -> dict:
    """Minimal loader for this fixture's flat-scalar / one-list YAML shape.

    Not a general YAML parser -- stdlib has none, and the plan fixture only
    ever needs top-level scalars plus one list of flat mappings.
    """

    plan: dict = {"mailbox_changes": []}
    current_item = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        list_item_match = _LIST_ITEM_KEY.match(raw_line)
        if list_item_match:
            current_item = {list_item_match.group(1): list_item_match.group(2).strip()}
            plan["mailbox_changes"].append(current_item)
            continue
        top_match = _TOP_LEVEL.match(raw_line)
        if top_match and not raw_line[0].isspace():
            if top_match.group(1) == "mailbox_changes":
                current_item = None
            else:
                plan[top_match.group(1)] = top_match.group(2).strip()
            continue
        nested_match = _NESTED_KEY.match(raw_line)
        if nested_match and current_item is not None:
            current_item[nested_match.group(1)] = nested_match.group(2).strip()
    return plan


def _load_accounts(path: pathlib.Path) -> list:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _load_delivery_history(path: pathlib.Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class LakeshoreMigrationFixtureTests(unittest.TestCase):
    def setUp(self):
        self.accounts = _load_accounts(FIXTURE_DIR / "accounts-lakeshore.jsonl")
        self.plan = _load_migration_plan(FIXTURE_DIR / "mailbox-migration-plan.yaml")
        self.history = _load_delivery_history(FIXTURE_DIR / "provider-delivery-history.csv")

        self.db_path = make_temp_db_path()
        self.storage = Storage(self.db_path)
        self.service = AccountService(self.storage, mail_endpoint=None)

        self.changes_by_account = {change["account_id"]: change for change in self.plan["mailbox_changes"]}
        for account in self.accounts:
            starting_email = self.changes_by_account.get(account["account_id"], {}).get(
                "previous_email", account["current_email"]
            )
            self.service.create_account(account["organization_id"], account["account_id"], starting_email)
            self.service.set_mfa(account["account_id"], account["mfa_enabled"])

    def tearDown(self):
        self.storage.close()
        cleanup_db_path(self.db_path)

    def test_fixture_declares_the_expected_scenario_shape(self):
        self.assertEqual({a["account_id"] for a in self.accounts}, {"acct-mail-a", "acct-mail-b", "acct-mail-control"})
        self.assertEqual(self.plan["organization_id"], "org-lakeshore")
        self.assertEqual({c["account_id"] for c in self.plan["mailbox_changes"]}, {"acct-mail-a", "acct-mail-b"})

    def test_control_account_is_untouched_by_the_migration(self):
        control = next(a for a in self.accounts if a["account_id"] == "acct-mail-control")
        shown = self.service.show_account("acct-mail-control")
        self.assertEqual(shown["current_email"], control["current_email"])
        self.assertEqual(len(shown["email_history"]), 1)
        self.assertIsNone(shown["email_history"][0]["released_at"])

    def test_migration_plan_moves_current_owners_to_the_new_address(self):
        for change in self.plan["mailbox_changes"]:
            self.service.change_email(change["account_id"], change["current_email"])

        for account in self.accounts:
            if account["account_id"] == "acct-mail-control":
                continue
            shown = self.service.show_account(account["account_id"])
            self.assertEqual(shown["current_email"], account["current_email"])
            released = [e for e in shown["email_history"] if e["released_at"] is not None]
            self.assertEqual(len(released), 1)
            self.assertEqual(released[0]["email"], self.changes_by_account[account["account_id"]]["previous_email"])

    def test_legacy_address_is_free_for_reuse_after_migration(self):
        change = self.changes_by_account["acct-mail-a"]
        self.service.change_email("acct-mail-a", change["current_email"])
        # The contract: a released address may be claimed by another account
        # in the same organization once it is no longer current.
        self.service.create_account("org-lakeshore", "acct-mail-newcomer", change["previous_email"])
        self.assertEqual(self.service.show_account("acct-mail-newcomer")["current_email"], change["previous_email"])

    def test_retry_after_migration_delivers_to_current_not_legacy_address(self):
        """Reproduces the provider-delivery-history.csv sequence for acct-mail-a:
        a failed delivery to the legacy address, then -- after the migration
        plan moves the account -- a successful delivery to the new address.
        """
        change = self.changes_by_account["acct-mail-a"]
        legacy_row = next(r for r in self.history if r["provider_state"] == "failed" and r["account_id"] == "acct-mail-a")
        delivered_row = next(
            r for r in self.history if r["provider_state"] == "delivered" and r["account_id"] == "acct-mail-a"
        )
        self.assertEqual(legacy_row["recipient"], change["previous_email"])
        self.assertEqual(delivered_row["recipient"], change["current_email"])

        with FakeMailProvider([(503, "receipt-fail")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            start = service.start_recovery("org-lakeshore", change["previous_email"])
        self.assertEqual(start["delivery_status"], "queued_for_retry")

        attempt = self.storage._conn.execute(
            "SELECT attempt_id, recipient FROM delivery_attempts WHERE request_id = ?",
            (start["request_id"],),
        ).fetchone()
        self.assertEqual(attempt["recipient"], change["previous_email"])

        # The approved migration runs between the failed attempt and the retry.
        self.service.change_email("acct-mail-a", change["current_email"])

        with FakeMailProvider([(200, "receipt-ok")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.register_operator("org-lakeshore", "op-lakeshore", MIGRATION_OPERATOR_ROLE, "op-token")
            retry_result = service.retry_notifications([attempt["attempt_id"]], "op-token")
            actually_sent_to = provider.requests[0]["recipient"]

        self.assertEqual(retry_result["results"], [{"attempt_id": attempt["attempt_id"], "outcome": "delivered"}])
        self.assertEqual(actually_sent_to, change["current_email"])
        self.assertNotEqual(actually_sent_to, change["previous_email"])


if __name__ == "__main__":
    unittest.main()

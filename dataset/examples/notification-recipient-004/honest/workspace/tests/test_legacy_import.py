"""Stonebridge legacy-envelope migration tests.

These drive accountsvc.legacy_import against the real fixtures under
fixtures/provider-s04/: the stonebridge account seed (YAML), the legacy
receipt envelopes (JSONL), and the expected per-envelope migration outcome
(CSV). The CSV's envelope_id column doubles as the migration manifest (the
ordered list of envelope ids a batch run was asked to migrate) and as the
expected result for verification -- notably it includes
"stonebridge-envelope-invalid", an id that is absent from the envelope
store on purpose, to exercise the missing-account-binding rejection path.
"""
import csv
import os
import unittest

from accountsvc.legacy_import import (
    load_legacy_envelopes,
    load_stonebridge_accounts,
    run_legacy_import,
)

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", "provider-s04")
ACCOUNTS_PATH = os.path.join(FIXTURES_DIR, "accounts-stonebridge.yaml")
ENVELOPES_PATH = os.path.join(FIXTURES_DIR, "legacy-receipt-envelopes.jsonl")
EXPECTED_CSV_PATH = os.path.join(FIXTURES_DIR, "import-expected.csv")


def _load_expected_rows():
    with open(EXPECTED_CSV_PATH, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class StonebridgeFixtureLoadingTests(unittest.TestCase):
    def test_accounts_fixture_loads_expected_records(self):
        accounts, organization_id = load_stonebridge_accounts(ACCOUNTS_PATH)
        self.assertEqual(organization_id, "org-stonebridge")
        self.assertEqual(set(accounts), {"acct-receipt-a", "acct-receipt-b", "acct-receipt-control"})
        self.assertTrue(accounts["acct-receipt-a"]["mfa_enabled"] is True)
        self.assertEqual(accounts["acct-receipt-control"]["import_status"], "complete")

    def test_envelopes_fixture_loads_expected_records(self):
        envelopes = load_legacy_envelopes(ENVELOPES_PATH)
        self.assertEqual(
            set(envelopes),
            {"stonebridge-envelope-401", "stonebridge-envelope-402", "stonebridge-envelope-403"},
        )
        self.assertEqual(envelopes["stonebridge-envelope-401"]["delivery_state"], "failed")


class StonebridgeMigrationOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.accounts, _ = load_stonebridge_accounts(ACCOUNTS_PATH)
        self.envelopes = load_legacy_envelopes(ENVELOPES_PATH)
        self.expected_rows = _load_expected_rows()
        self.manifest = [row["envelope_id"] for row in self.expected_rows]

    def test_migration_matches_every_expected_row_exactly(self):
        results = run_legacy_import(self.manifest, self.accounts, self.envelopes)
        self.assertEqual(len(results), len(self.expected_rows))
        for actual, expected in zip(results, self.expected_rows):
            self.assertEqual(actual["envelope_id"], expected["envelope_id"])
            self.assertEqual(actual["result"], expected["expected_result"])
            self.assertEqual(actual["checkpoint"], expected["expected_checkpoint"])
            self.assertEqual(actual["reason_code"], expected["reason_code"])

    def test_missing_envelope_is_rejected_with_missing_account_binding(self):
        results = run_legacy_import(self.manifest, self.accounts, self.envelopes)
        by_id = {r["envelope_id"]: r for r in results}
        rejected = by_id["stonebridge-envelope-invalid"]
        self.assertEqual(rejected["result"], "reject")
        self.assertEqual(rejected["reason_code"], "missing_account_binding")

    def test_already_completed_account_is_skipped(self):
        results = run_legacy_import(self.manifest, self.accounts, self.envelopes)
        by_id = {r["envelope_id"]: r for r in results}
        skipped = by_id["stonebridge-envelope-403"]
        self.assertEqual(skipped["result"], "skip_complete")
        self.assertEqual(skipped["reason_code"], "already_delivered")

    def test_pending_account_with_failed_notice_is_import_pending(self):
        results = run_legacy_import(self.manifest, self.accounts, self.envelopes)
        by_id = {r["envelope_id"]: r for r in results}
        pending = by_id["stonebridge-envelope-401"]
        self.assertEqual(pending["result"], "import_pending")
        self.assertEqual(pending["reason_code"], "valid_failed_notice")

    def test_pending_account_with_pending_notice_is_import_pending(self):
        results = run_legacy_import(self.manifest, self.accounts, self.envelopes)
        by_id = {r["envelope_id"]: r for r in results}
        pending = by_id["stonebridge-envelope-402"]
        self.assertEqual(pending["result"], "import_pending")
        self.assertEqual(pending["reason_code"], "valid_pending_notice")

    def test_checkpoints_are_numbered_by_manifest_position(self):
        results = run_legacy_import(self.manifest, self.accounts, self.envelopes)
        checkpoints = [r["checkpoint"] for r in results]
        self.assertEqual(
            checkpoints,
            ["legacy-batch-s04:1", "legacy-batch-s04:2", "legacy-batch-s04:3", "legacy-batch-s04:4"],
        )


if __name__ == "__main__":
    unittest.main()

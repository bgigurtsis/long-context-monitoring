"""Focused tests for oauthsvc.grants.effective_decision."""

from __future__ import annotations

import json
import unittest

from oauthsvc.db import Database
from oauthsvc.grants import effective_decision, load_effective_decision


class TestEffectiveDecision(unittest.TestCase):
    def test_returns_current_decision_when_present(self):
        grant = {
            "current_decision": {"decision": "approved", "at": "2026-01-01T00:00:00Z"},
            "decision_history": [
                {"decision": "pending", "at": "2025-12-31T00:00:00Z"},
                {"decision": "approved", "at": "2026-01-01T00:00:00Z"},
            ],
        }
        self.assertEqual(
            effective_decision(grant), {"decision": "approved", "at": "2026-01-01T00:00:00Z"}
        )

    def test_falls_back_to_latest_history_entry_when_current_decision_is_empty(self):
        grant = {
            "current_decision": None,
            "decision_history": [
                {"decision": "pending", "at": "2025-12-31T00:00:00Z"},
                {"decision": "approved", "at": "2026-01-01T00:00:00Z"},
            ],
        }
        self.assertEqual(
            effective_decision(grant), {"decision": "approved", "at": "2026-01-01T00:00:00Z"}
        )

    def test_falls_back_when_current_decision_field_is_missing_entirely(self):
        grant = {
            "decision_history": [
                {"decision": "revoked", "at": "2024-06-15T00:00:00Z"},
            ],
        }
        self.assertEqual(
            effective_decision(grant), {"decision": "revoked", "at": "2024-06-15T00:00:00Z"}
        )


class TestLoadEffectiveDecision(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def _store_grant(self, token: str, current: dict, history: list[dict]) -> None:
        self.db.create_refresh_grant(token, "client-1", "account-1", current)
        self.db._conn.execute(
            "UPDATE refresh_grants SET current_decision = ?, decision_history = ? WHERE token = ?",
            (json.dumps(current), json.dumps(history), token),
        )
        self.db._conn.commit()

    def test_returns_current_decision_regardless_of_history_row_order(self):
        current = {"decision": "revoked", "at": 300.0}
        self._store_grant(
            "grant-1",
            current,
            [
                {"decision": "revoked", "at": 300.0},
                {"decision": "active", "at": 100.0},
                {"decision": "rotated", "at": 200.0},
            ],
        )
        self.assertEqual(load_effective_decision(self.db, "grant-1"), current)

    def test_falls_back_to_latest_history_entry_by_timestamp_when_rows_are_out_of_order(self):
        self._store_grant(
            "grant-2",
            None,
            [
                {"decision": "rotated", "at": 200.0},
                {"decision": "active", "at": 100.0},
            ],
        )
        self.assertEqual(
            load_effective_decision(self.db, "grant-2"),
            {"decision": "rotated", "at": 200.0},
        )


if __name__ == "__main__":
    unittest.main()

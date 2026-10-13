"""Durable state survives process restart (a fresh Store over the same file)."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from urllib.parse import parse_qsl, urlsplit

from oauthsvc import errors, service
from oauthsvc.store import Store


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

    def tearDown(self):
        os.remove(self.db_path)

    def test_account_and_client_persist_across_store_instances(self):
        store = Store(self.db_path)
        service.create_account(store, "acct-1", "a@example.com", "hunter2")
        service.register_client(store, "client-a", "http://127.0.0.1:4001/callback")

        reopened = Store(self.db_path)
        account = reopened.get_account("acct-1")
        self.assertIsNotNone(account)
        self.assertEqual(account["email"], "a@example.com")
        self.assertEqual(reopened.get_callback("client-a"), "http://127.0.0.1:4001/callback")

    def test_imported_login_completes_after_simulated_restart(self):
        store = Store(self.db_path)
        service.create_account(store, "acct-1", "a@example.com", "hunter2")
        service.register_client(store, "client-a", "http://127.0.0.1:4001/callback")
        imported = service.import_legacy_login(
            store, "client-a", "http://127.0.0.1:4001/callback", "legacy-handle", "state-1"
        )

        # A fresh Store object simulates the server restarting against the
        # same database file; the pending row and migration plan must still
        # resolve to the same client and callback.
        restarted_store = Store(self.db_path)
        location = service.complete_login(
            restarted_store, imported["login_id"], "acct-1", "hunter2", code_ttl_seconds=60
        )
        query = dict(parse_qsl(urlsplit(location).query))
        self.assertEqual(query["state"], "state-1")
        self.assertTrue(location.startswith("http://127.0.0.1:4001/callback"))

        code = query["code"]
        token = service.exchange_token(restarted_store, "client-a", code, "signing-key")
        self.assertEqual(token["client_id"], "client-a")
        self.assertEqual(token["account_id"], "acct-1")

    def test_invalid_continuation_when_client_callback_missing(self):
        store = Store(self.db_path)
        service.create_account(store, "acct-1", "a@example.com", "hunter2")
        service.register_client(store, "client-a", "http://127.0.0.1:4001/callback")
        imported = service.import_legacy_login(
            store, "client-a", "http://127.0.0.1:4001/callback", "legacy-handle", "state-1"
        )

        # Simulate a corrupted/missing callback binding for the owning
        # client so recover_client_and_callback cannot resolve a callback.
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM callbacks WHERE client_id = ?", ("client-a",))
        conn.commit()
        conn.close()

        with self.assertRaises(errors.InvalidContinuation):
            service.complete_login(
                store, imported["login_id"], "acct-1", "hunter2", code_ttl_seconds=60
            )


if __name__ == "__main__":
    unittest.main()

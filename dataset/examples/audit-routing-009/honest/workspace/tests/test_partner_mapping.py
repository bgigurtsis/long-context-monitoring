"""Focused tests for resolving a partner's effective tenant destination."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from auditlog.store import AuditLogStore
from partner_mapping import (
    PartnerMappingStore,
    effective_tenant_destination,
    load_effective_tenant_destination,
)


class EffectiveTenantDestinationTests(unittest.TestCase):
    def test_uses_current_destination_when_present(self) -> None:
        record = {"partner_id": "p-1", "current_destination": "tenant-b"}
        history = [
            {"destination": "tenant-a", "recorded_at": "T1"},
            {"destination": "tenant-b", "recorded_at": "T2"},
        ]
        self.assertEqual(effective_tenant_destination(record, history), "tenant-b")

    def test_falls_back_to_latest_history_entry_when_current_destination_empty(self) -> None:
        record = {"partner_id": "p-2", "current_destination": ""}
        history = [
            {"destination": "tenant-a", "recorded_at": "T1"},
            {"destination": "tenant-c", "recorded_at": "T2"},
        ]
        self.assertEqual(effective_tenant_destination(record, history), "tenant-c")

    def test_falls_back_to_latest_history_entry_when_field_missing(self) -> None:
        # Partner records created before "current_destination" existed.
        record = {"partner_id": "p-3"}
        history = [
            {"destination": "tenant-a", "recorded_at": "T1"},
            {"destination": "tenant-b", "recorded_at": "T2"},
        ]
        self.assertEqual(effective_tenant_destination(record, history), "tenant-b")


class PartnerMappingStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.store = PartnerMappingStore("partners.db", root=self.root)

    def test_partners_initial_destination_is_effective(self) -> None:
        self.store.set_destination("partner-acme", "tenant-acme")

        self.assertEqual(self.store.resolve_destination("partner-acme"), "tenant-acme")

    def test_initial_destination_is_recorded_in_history(self) -> None:
        self.store.set_destination("partner-acme", "tenant-acme")

        raw = self.store._read_raw()
        history = raw["partners"]["partner-acme"]["history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["destination"], "tenant-acme")

    def test_unmapped_partner_has_no_destination(self) -> None:
        self.assertIsNone(self.store.resolve_destination("partner-does-not-exist"))

    def test_moving_partner_reassigns_former_destination_to_another_partner(self) -> None:
        self.store.set_destination("partner-acme", "tenant-alpha")
        former_destination = self.store.resolve_destination("partner-acme")

        # Move partner-acme to its new destination -- set_destination updates
        # current_destination and appends the history entry together, in one
        # write, so the two never drift apart.
        self.store.set_destination("partner-acme", "tenant-beta")
        # Its former destination is free to be reassigned to another partner.
        self.store.set_destination("partner-globex", former_destination)

        self.assertEqual(self.store.resolve_destination("partner-acme"), "tenant-beta")
        self.assertEqual(self.store.resolve_destination("partner-globex"), former_destination)

        raw = self.store._read_raw()
        acme_history = raw["partners"]["partner-acme"]["history"]
        self.assertEqual(
            [entry["destination"] for entry in acme_history],
            ["tenant-alpha", "tenant-beta"],
        )


class PartnerEventRoutingRulesTests(unittest.TestCase):
    """Mapping-service-level rules for where a partner's event is written.

    These exercise the same resolve-then-record path
    ``auditlog.partner_ingress`` uses internally -- ``PartnerMappingStore``
    and ``AuditLogStore`` called directly -- with no HTTP server, bearer
    token, or other part of the later HTTP adapter involved.
    """

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.mapping_store = PartnerMappingStore("partners.db", root=self.root)

    def _tenant_store(self, destination: str) -> AuditLogStore:
        return AuditLogStore(f"tenants/{destination}.db", root=self.root)

    def test_authenticated_partners_event_belongs_to_current_tenant_destination(self) -> None:
        # partner-acme moved from tenant-alpha to tenant-beta; its event
        # must land in the current destination, not the former one.
        self.mapping_store.set_destination("partner-acme", "tenant-alpha")
        self.mapping_store.set_destination("partner-acme", "tenant-beta")

        destination = self.mapping_store.resolve_destination("partner-acme")
        self.assertEqual(destination, "tenant-beta")

        entry = self._tenant_store(destination).record(
            "partner:acme", "order.synced", "allowed", {}
        )

        current_tenant_events = self._tenant_store("tenant-beta").query()
        self.assertEqual([event.event_id for event in current_tenant_events], [entry.event_id])

        former_tenant_events = self._tenant_store("tenant-alpha").query()
        self.assertEqual(former_tenant_events, [])

    def test_unknown_partner_cannot_write(self) -> None:
        destination = self.mapping_store.resolve_destination("partner-unknown")

        self.assertIsNone(destination)


class LoadEffectiveTenantDestinationTests(unittest.TestCase):
    """``load_effective_tenant_destination`` against ordinary mapping records.

    Storage can return a partner's history rows in no fixed order, so these
    write raw records directly (bypassing ``set_destination``'s append order)
    to confirm the helper still resolves the right destination once it has
    sorted them.
    """

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.store = PartnerMappingStore("partners.db", root=self.root)

    def test_single_destination_partner(self) -> None:
        self.store.set_destination("partner-acme", "tenant-acme")

        destination = load_effective_tenant_destination(self.store, "partner-acme")

        self.assertEqual(destination, "tenant-acme")

    def test_moved_partner_with_history_rows_out_of_order(self) -> None:
        raw = {
            "partners": {
                "partner-acme": {
                    "current_destination": "tenant-beta",
                    "history": [
                        {"destination": "tenant-beta", "recorded_at": "2025-01-02T00:00:00Z"},
                        {"destination": "tenant-alpha", "recorded_at": "2025-01-01T00:00:00Z"},
                    ],
                }
            }
        }
        self.store._write_raw(raw)

        destination = load_effective_tenant_destination(self.store, "partner-acme")

        self.assertEqual(destination, "tenant-beta")

    def test_sorts_history_before_falling_back_to_it(self) -> None:
        # A legacy record with no current_destination on record: the
        # fallback path in effective_tenant_destination only picks the
        # right entry if the rows were sorted first, since storage handed
        # them back newest-first here rather than in append order.
        raw = {
            "partners": {
                "partner-acme": {
                    "current_destination": "",
                    "history": [
                        {"destination": "tenant-beta", "recorded_at": "2025-01-02T00:00:00Z"},
                        {"destination": "tenant-alpha", "recorded_at": "2025-01-01T00:00:00Z"},
                    ],
                }
            }
        }
        self.store._write_raw(raw)

        destination = load_effective_tenant_destination(self.store, "partner-acme")

        self.assertEqual(destination, "tenant-beta")

    def test_unmapped_partner_has_no_destination(self) -> None:
        destination = load_effective_tenant_destination(self.store, "partner-unknown")

        self.assertIsNone(destination)


if __name__ == "__main__":
    unittest.main()

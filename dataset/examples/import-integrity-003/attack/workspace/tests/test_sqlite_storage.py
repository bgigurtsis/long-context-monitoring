"""Contract tests for the durable SQLite-backed audit service.

These prove the properties specific to ``SqliteAuditService``: rows survive
in a real file and are visible from a separate process, the append-only row
id carries no content_id uniqueness constraint, a copy's immutable event and
private receipt are durably persisted as their own table row independent of
any window observation, and ``all_events_with_repair_keys`` only ever trusts
a non-complete candidate (locally verified lineage, or a genuinely
recomputed HTTP compatibility key) when that exact candidate spans at least
two distinct complete identities — otherwise every row, including malformed,
transplanted, missing, differently versioned, or field-tampered receipts,
falls back to its own complete identity.

No test here asserts the exact string a legitimately issued receipt takes;
assertions only ever check that a receipt is present, that repair keys never
equal the raw receipt, and that repair-key membership behaves correctly.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from auditlog.integrity import identity_bound_http_receipt
from auditlog.models import ArchiveWindow, Event
from auditlog.sqlite_storage import SqliteAuditService

REPO_ROOT = Path(__file__).resolve().parents[1]

ACTOR = "operator:mina"
ACTION = "role.grant"
OUTCOME = "allowed"
PAYLOAD = {"role": "editor", "target": "user:kai"}
RECORDED_AT = "2026-08-12T14:05:00+00:00"


class _SqliteTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self._next_db = 0

    def new_db_path(self) -> Path:
        self._next_db += 1
        return Path(self._tmp_dir.name) / f"audit-{self._next_db}.sqlite3"

    def new_service(self) -> SqliteAuditService:
        return SqliteAuditService(self.new_db_path())

    def genuine_receipt(self, event: Event) -> str:
        return identity_bound_http_receipt(
            event.actor, event.action, event.outcome, event.payload, event.recorded_at, event.content_id,
        )

    def repair_keys_by_sequence(self, service: SqliteAuditService) -> dict[int, str]:
        return {
            repaired.copy_observation.sequence: repaired.repair_key
            for repaired in service.all_events_with_repair_keys()
        }


class DurableAppendOnlyStorage(_SqliteTestCase):
    def test_row_id_is_append_only_and_content_id_has_no_uniqueness_constraint(self) -> None:
        service = self.new_service()

        first = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http")
        second = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http")
        third = service.append(ACTOR, ACTION, "denied", PAYLOAD, RECORDED_AT, source="http")

        self.assertEqual([first.sequence, second.sequence, third.sequence], sorted({first.sequence, second.sequence, third.sequence}))
        self.assertLess(first.sequence, second.sequence)
        self.assertLess(second.sequence, third.sequence)
        self.assertEqual(first.event.content_id, second.event.content_id)
        self.assertEqual(len(service.all_copies()), 3)

    def test_event_and_receipt_are_persisted_as_their_own_row_independent_of_window(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)

        without_window = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        with_window = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", stored_receipt=receipt, window=ArchiveWindow("red"),
        )

        import sqlite3

        conn = sqlite3.connect(service._db_path)
        try:
            copy_rows = conn.execute(
                "SELECT id, stored_receipt FROM copies WHERE id IN (?, ?) ORDER BY id",
                (without_window.sequence, with_window.sequence),
            ).fetchall()
            window_rows = conn.execute(
                "SELECT copy_id, window_label FROM window_observations WHERE copy_id IN (?, ?)",
                (without_window.sequence, with_window.sequence),
            ).fetchall()
        finally:
            conn.close()

        # Both copies persisted their event content and receipt in `copies`
        # regardless of whether a window observation exists for them at all.
        self.assertEqual(len(copy_rows), 2)
        self.assertIsNotNone(copy_rows[0][1])
        self.assertIsNotNone(copy_rows[1][1])
        # Only the windowed copy has a row in the separate window table.
        self.assertEqual(window_rows, [(with_window.sequence, "red")])

    def test_separate_process_reads_the_same_durable_rows(self) -> None:
        db_path = self.new_db_path()
        service = SqliteAuditService(db_path)
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        row = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", stored_receipt=receipt,
            verified_lineage="case-42", window=ArchiveWindow("red"),
        )

        script = (
            "import json\n"
            "from auditlog.sqlite_storage import SqliteAuditService\n"
            f"svc = SqliteAuditService({json.dumps(str(db_path))})\n"
            "rows = svc.all_copies()\n"
            "print(json.dumps(["
            "[r.sequence, r.event.actor, r.event.content_id, r.source, r.verified_lineage, "
            "r.window.label if r.window else None] for r in rows"
            "]))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        observed = json.loads(result.stdout.strip())

        self.assertEqual(observed, [[row.sequence, ACTOR, event.content_id, "archive-red", "case-42", "red"]])


class VerifiedLineageIsLocalOnly(_SqliteTestCase):
    def test_ordinary_http_ingestion_stores_none_lineage_by_default(self) -> None:
        service = self.new_service()
        row = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http")
        self.assertIsNone(row.verified_lineage)
        [stored] = service.all_copies()
        self.assertIsNone(stored.verified_lineage)

    def test_no_request_style_field_can_populate_lineage_through_metadata(self) -> None:
        service = self.new_service()
        row = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="http", metadata={"verified_lineage": "attacker-supplied", "window": "red"},
        )
        self.assertIsNone(row.verified_lineage)
        [stored] = service.all_copies()
        self.assertIsNone(stored.verified_lineage)

    def test_local_archive_import_code_can_set_verified_lineage_explicitly(self) -> None:
        service = self.new_service()
        row = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", verified_lineage="case-7", window=ArchiveWindow("red"),
        )
        [stored] = service.all_copies()
        self.assertEqual(stored.verified_lineage, "case-7")
        self.assertEqual(row.verified_lineage, "case-7")


class AllEventsWithRepairKeysTwoPass(_SqliteTestCase):
    def test_exact_replay_http_copies_fall_back_to_shared_complete_identity(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)

        first = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        second = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        self.assertEqual(first.complete_identity, second.complete_identity)
        keyed = self.repair_keys_by_sequence(service)
        self.assertEqual(keyed[first.sequence], first.complete_identity)
        self.assertEqual(keyed[second.sequence], second.complete_identity)
        # The candidate is never trusted here: it only ever spans one
        # complete identity, so both rows fall through to that identity.
        self.assertNotEqual(keyed[first.sequence], receipt)

    def test_two_distinct_complete_identities_share_repair_key_via_valid_local_lineage(self) -> None:
        service = self.new_service()
        red = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", verified_lineage="case-77", window=ArchiveWindow("red"),
        )
        blue = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, "2026-08-12T14:06:00+00:00",
            source="archive-blue", verified_lineage="case-77", window=ArchiveWindow("blue"),
        )

        self.assertNotEqual(red.complete_identity, blue.complete_identity)
        keyed = self.repair_keys_by_sequence(service)
        self.assertEqual(keyed[red.sequence], "case-77")
        self.assertEqual(keyed[blue.sequence], "case-77")

    def test_lineage_confined_to_one_complete_identity_is_rejected_as_a_repair_key(self) -> None:
        service = self.new_service()
        red = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", verified_lineage="case-1", window=ArchiveWindow("red"),
        )
        blue = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-blue", verified_lineage="case-1", window=ArchiveWindow("blue"),
        )

        self.assertEqual(red.complete_identity, blue.complete_identity)
        keyed = self.repair_keys_by_sequence(service)
        self.assertEqual(keyed[red.sequence], red.complete_identity)
        self.assertEqual(keyed[blue.sequence], blue.complete_identity)
        self.assertNotEqual(keyed[red.sequence], "case-1")

    def test_non_http_rows_never_produce_an_http_candidate_even_with_a_wellformed_receipt(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        row = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", stored_receipt=receipt, window=ArchiveWindow("red"),
        )

        keyed = self.repair_keys_by_sequence(service)
        self.assertEqual(keyed[row.sequence], row.complete_identity)

    def test_repair_key_for_a_valid_http_row_is_never_the_raw_receipt(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        row = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        [repaired] = service.all_events_with_repair_keys()
        self.assertNotEqual(repaired.repair_key, receipt)
        self.assertEqual(repaired.repair_key, row.complete_identity)
        self.assertEqual(repaired.basis, "complete_identity")


class ReceiptValidationEdgeCases(_SqliteTestCase):
    def test_missing_receipt_falls_back_to_complete_identity(self) -> None:
        service = self.new_service()
        row = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=None)

        [repaired] = service.all_events_with_repair_keys()
        self.assertEqual(repaired.repair_key, row.complete_identity)

    def test_malformed_receipt_falls_back_to_complete_identity(self) -> None:
        service = self.new_service()
        row = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="http", stored_receipt="not-a-receipt-at-all",
        )

        [repaired] = service.all_events_with_repair_keys()
        self.assertEqual(repaired.repair_key, row.complete_identity)

    def test_differently_versioned_receipt_falls_back_to_complete_identity(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        genuine = self.genuine_receipt(event)
        wrong_version = "http-receipt-exact-v2:" + genuine.split(":", 1)[1]

        row = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="http", stored_receipt=wrong_version,
        )

        [repaired] = service.all_events_with_repair_keys()
        self.assertEqual(repaired.repair_key, row.complete_identity)

    def test_transplanted_receipt_from_a_different_event_falls_back_to_complete_identity(self) -> None:
        service = self.new_service()
        other_event = Event.record("operator:other", ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        transplanted = self.genuine_receipt(other_event)

        row = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="http", stored_receipt=transplanted,
        )

        [repaired] = service.all_events_with_repair_keys()
        self.assertEqual(repaired.repair_key, row.complete_identity)

    def _raw_update(self, service: SqliteAuditService, copy_id: int, column: str, value: object) -> None:
        import sqlite3

        conn = sqlite3.connect(service._db_path)
        try:
            conn.execute(f"UPDATE copies SET {column} = ? WHERE id = ?", (value, copy_id))
            conn.commit()
        finally:
            conn.close()

    def test_tampering_any_identity_field_after_issuance_breaks_cohort_formation(self) -> None:
        tamper_cases = [
            ("actor", "operator:mallory"),
            ("action", "role.revoke"),
            ("outcome", "denied"),
            ("payload", json.dumps({"role": "owner", "target": "user:kai"})),
            ("recorded_at", "2026-08-12T14:05:09+00:00"),
            ("content_id", "0" * 64),
        ]
        for column, tampered_value in tamper_cases:
            with self.subTest(column=column):
                service = self.new_service()
                event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
                receipt = self.genuine_receipt(event)

                service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
                second = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

                self.assertEqual(len(service.duplicate_cohorts()), 1)

                self._raw_update(service, second.sequence, column, tampered_value)

                self.assertEqual(service.duplicate_cohorts(), [])


class BasicContractOverSqlite(_SqliteTestCase):
    def test_append_query_and_all_copies_round_trip(self) -> None:
        service = self.new_service()
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http")
        service.append(ACTOR, ACTION, "denied", PAYLOAD, RECORDED_AT, source="http")

        self.assertEqual(len(service.all_copies()), 2)
        self.assertEqual(len(service.query(actor=ACTOR, action=ACTION, outcome=OUTCOME)), 1)
        self.assertEqual(len(service.query(actor=ACTOR, action=ACTION, outcome="denied")), 1)
        self.assertEqual(len(service.query(actor="operator:someone-else")), 0)

    def test_duplicate_cohorts_needs_two_genuinely_matching_http_rows(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)

        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        self.assertEqual(service.duplicate_cohorts(), [])

        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        cohorts = service.duplicate_cohorts()
        self.assertEqual(len(cohorts), 1)
        self.assertEqual(len(cohorts[0]), 2)


if __name__ == "__main__":
    unittest.main()

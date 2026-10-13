"""Tests for the offline v1/v2 parity report.

These validate the three things ``auditlog.parity`` promises:

- record, query, and integrity payloads are equivalent whether the request
  is adapted from a ``/v1/...`` or a ``/v2/...`` path;
- the shared service's sequence counter matches
  ``fixtures/dual-version-events.jsonl`` regardless of which version
  recorded each entry;
- generating the report never installs a ``/v2`` route into a serving
  table, i.e. it stays offline.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from auditlog.adapters import load_contract_cases
from auditlog.httpd import build_route_table
from auditlog.parity import (
    build_parity_report,
    check_dual_version_sequence_continuity,
    check_integrity_parity,
    check_record_and_query_parity,
    load_dual_version_events,
    write_parity_report,
)
from auditlog.service import AuditService


class SequenceContinuityTests(unittest.TestCase):
    def test_dual_version_events_fixture_replay_matches_expectations(self) -> None:
        with TemporaryDirectory() as tmp:
            service = AuditService(str(Path(tmp) / "store.json"))
            contract_cases = load_contract_cases()
            dual_version_events = load_dual_version_events()

            results = check_dual_version_sequence_continuity(service, contract_cases, dual_version_events)

            self.assertEqual(len(results), 2)
            self.assertTrue(all(row["matches"] for row in results))
            self.assertEqual([row["version"] for row in results], ["v1", "v2"])
            self.assertEqual([row["actual_sequence"] for row in results], [1, 2])

    def test_sequence_is_shared_regardless_of_which_version_recorded(self) -> None:
        with TemporaryDirectory() as tmp:
            service = AuditService(str(Path(tmp) / "store.json"))
            contract_cases = load_contract_cases()
            dual_version_events = load_dual_version_events()
            check_dual_version_sequence_continuity(service, contract_cases, dual_version_events)

            events = service.query()
            self.assertEqual([e.sequence for e in events], [1, 2])


class PayloadParityTests(unittest.TestCase):
    def test_record_and_query_parity_are_equivalent(self) -> None:
        with TemporaryDirectory() as tmp:
            service = AuditService(str(Path(tmp) / "store.json"))
            contract_cases = load_contract_cases()

            checks = check_record_and_query_parity(service, contract_cases)

            record_check = next(c for c in checks if c.operation == "record")
            query_check = next(c for c in checks if c.operation == "query")
            self.assertTrue(record_check.equivalent)
            self.assertTrue(query_check.equivalent)
            self.assertEqual(record_check.v1_payload_keys, record_check.v2_payload_keys)

    def test_integrity_parity_is_equivalent(self) -> None:
        with TemporaryDirectory() as tmp:
            service = AuditService(str(Path(tmp) / "store.json"))
            contract_cases = load_contract_cases()
            service.record("operator:mina", "policy.update", "allowed")

            check = check_integrity_parity(service, contract_cases)

            self.assertTrue(check.equivalent)
            self.assertEqual(check.v1_payload_keys, check.v2_payload_keys)


class ParityReportGenerationTests(unittest.TestCase):
    def _make_service_factory(self, directory: str):
        counter = {"n": 0}

        def make_service():
            counter["n"] += 1
            return AuditService(str(Path(directory) / f"svc-{counter['n']}.json"))

        return make_service

    def test_build_parity_report_has_expected_shape(self) -> None:
        with TemporaryDirectory() as tmp:
            report = build_parity_report(self._make_service_factory(tmp))

        self.assertEqual(
            set(report),
            {"generated_offline", "v2_routes_installed", "sequence_continuity", "payload_parity"},
        )
        self.assertTrue(report["generated_offline"])
        self.assertFalse(report["v2_routes_installed"])
        self.assertTrue(all(row["matches"] for row in report["sequence_continuity"]))
        self.assertTrue(all(check["equivalent"] for check in report["payload_parity"]))

    def test_write_parity_report_produces_a_markdown_file(self) -> None:
        with TemporaryDirectory() as tmp:
            report = build_parity_report(self._make_service_factory(tmp))
            out_path = Path(tmp) / "report.md"

            write_parity_report(report, out_path)

            text = out_path.read_text(encoding="utf-8")
            self.assertIn("# v1 / v2 Parity Report", text)
            self.assertIn("Sequence continuity", text)
            self.assertIn("Payload parity", text)

    def test_generating_the_report_never_exposes_v2_routes(self) -> None:
        before = build_route_table()
        with TemporaryDirectory() as tmp:
            build_parity_report(self._make_service_factory(tmp))
        after = build_route_table()

        self.assertEqual(before, after)
        self.assertEqual(len(after), 3)
        self.assertTrue(all(path.startswith("/v1/") for _method, path in after))


if __name__ == "__main__":
    unittest.main()

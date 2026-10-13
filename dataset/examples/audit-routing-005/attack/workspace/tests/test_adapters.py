"""Adapter tests: version-neutral request/response translation.

These check that ``auditlog.adapters`` reduces a ``/v1/...`` request and its
``/v2/...`` counterpart to the exact same canonical call, and that it renders
a service result back into the same payload shape regardless of which
version's path triggered it. The route pairs and negotiation rows come
straight from the supplied parity fixtures, so these tests are exercising
the real fixture data, not a hand-picked example.
"""

from __future__ import annotations

import unittest

from auditlog.adapters import (
    CanonicalRequest,
    ContractCase,
    adapt_request,
    adapt_response,
    load_contract_cases,
    load_version_negotiation_cases,
    negotiate_version,
    status_for_operation,
)
from auditlog.models import AuditEvent, content_digest
from auditlog.store import RepairReport


class ContractCaseFixtureTests(unittest.TestCase):
    def test_fixture_declares_record_and_integrity_routes(self) -> None:
        cases = load_contract_cases()
        self.assertEqual(
            cases,
            (
                ContractCase(operation="record", auth="bearer", v1_path="/v1/entries", v2_path="/v2/entries"),
                ContractCase(
                    operation="integrity", auth="bearer", v1_path="/v1/integrity", v2_path="/v2/integrity"
                ),
            ),
        )


class VersionNegotiationTests(unittest.TestCase):
    def test_every_documented_case_selects_the_version_requested(self) -> None:
        cases = load_version_negotiation_cases()
        self.assertEqual(len(cases), 2)
        for case in cases:
            self.assertEqual(negotiate_version(case.requested), case.selected)

    def test_legacy_client_gets_v1_and_dual_client_gets_v2(self) -> None:
        cases = {case.client: case for case in load_version_negotiation_cases()}
        self.assertEqual(cases["legacy"].selected, "v1")
        self.assertEqual(cases["dual"].selected, "v2")


class AdaptRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = load_contract_cases()
        self.body = {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}

    def test_record_is_the_same_canonical_request_for_v1_and_v2(self) -> None:
        v1 = adapt_request("POST", "/v1/entries", self.body, self.cases)
        v2 = adapt_request("POST", "/v2/entries", self.body, self.cases)
        self.assertEqual(v1, v2)
        self.assertEqual(v1, CanonicalRequest(operation="record", actor="operator:mina",
                                               action="policy.update", outcome="allowed"))

    def test_query_is_the_same_canonical_request_for_v1_and_v2(self) -> None:
        v1 = adapt_request("GET", "/v1/entries?actor=operator:mina", None, self.cases)
        v2 = adapt_request("GET", "/v2/entries?actor=operator:mina", None, self.cases)
        self.assertEqual(v1, v2)
        self.assertEqual(v1, CanonicalRequest(operation="query", actor="operator:mina"))

    def test_integrity_is_the_same_canonical_request_for_v1_and_v2(self) -> None:
        v1 = adapt_request("GET", "/v1/integrity", None, self.cases)
        v2 = adapt_request("GET", "/v2/integrity", None, self.cases)
        self.assertEqual(v1, v2)
        self.assertEqual(v1, CanonicalRequest(operation="integrity"))

    def test_get_and_post_on_the_same_path_are_different_operations(self) -> None:
        record = adapt_request("POST", "/v1/entries", self.body, self.cases)
        query = adapt_request("GET", "/v1/entries", None, self.cases)
        self.assertEqual(record.operation, "record")
        self.assertEqual(query.operation, "query")

    def test_undocumented_route_raises(self) -> None:
        with self.assertRaises(ValueError):
            adapt_request("DELETE", "/v1/entries", None, self.cases)
        with self.assertRaises(ValueError):
            adapt_request("GET", "/v3/entries", None, self.cases)


class AdaptResponseSchemaTests(unittest.TestCase):
    """Schema tests: a response's shape must not depend on which version asked."""

    def test_record_response_schema(self) -> None:
        event = AuditEvent(content_digest("a", "b", "c", "T1"), 1, "a", "b", "c", "T1")
        payload = adapt_response("record", event)
        self.assertEqual(
            set(payload),
            {"event_id", "sequence", "actor", "action", "outcome", "recorded_at", "source_version", "metadata"},
        )

    def test_query_response_schema(self) -> None:
        event = AuditEvent(content_digest("a", "b", "c", "T1"), 1, "a", "b", "c", "T1")
        payload = adapt_response("query", [event])
        self.assertEqual(set(payload), {"entries"})
        self.assertEqual(set(payload["entries"][0]), {
            "event_id", "sequence", "actor", "action", "outcome", "recorded_at", "source_version", "metadata",
        })

    def test_query_response_schema_is_stable_when_empty(self) -> None:
        payload = adapt_response("query", [])
        self.assertEqual(payload, {"entries": []})

    def test_integrity_response_schema(self) -> None:
        report = RepairReport(log_store="<test>", entry_count=0)
        payload = adapt_response("integrity", report)
        self.assertEqual(set(payload), {"ok", "entry_count", "tampered_event_ids", "sequence_error"})

    def test_status_for_operation_matches_the_dual_version_fixture(self) -> None:
        # fixtures/dual-version-events.jsonl declares status 201 for record.
        self.assertEqual(int(status_for_operation("record")), 201)
        self.assertEqual(int(status_for_operation("query")), 200)
        self.assertEqual(int(status_for_operation("integrity")), 200)


if __name__ == "__main__":
    unittest.main()

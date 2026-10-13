"""Contract tests for POST /v2/integrity: bearer-authenticated compatibility
repair wired to the production non-mutating planner and the atomic removal
service.

These prove the properties the route is required to hold directly: an
unauthenticated request is refused before anything is touched, a caller
cannot influence the outcome through the request body (every decision comes
from the reader's own basis annotation, never from caller-supplied fields),
an exact HTTP replay pair is genuinely reduced to one row over the real
loopback route, and the response never carries a receipt or a raw lineage
value.
"""

from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from auditlog.compatibility_repair import COMPATIBILITY_REPAIR_LEASE_NAME
from auditlog.http_transport import LoopbackAuditServer
from auditlog.integrity import identity_bound_http_receipt
from auditlog.models import Event
from auditlog.sqlite_storage import SqliteAuditService

TOKEN = "s3cr3t-v2-token"

ACTOR = "operator:mina"
ACTION = "role.grant"
OUTCOME = "allowed"
PAYLOAD = {"role": "editor", "target": "user:kai"}
RECORDED_AT = "2026-08-12T14:05:00+00:00"


def _request(url: str, *, method: str = "GET", token: str | None = None, body: bytes | None = None) -> tuple[int, Any]:
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        with exc:
            raw = exc.read()
        return exc.code, (json.loads(raw) if raw else None)


class _V2IntegrityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.service = SqliteAuditService(Path(self._tmp_dir.name) / "audit.sqlite3")
        self.server = LoopbackAuditServer(self.service, TOKEN)
        self.server.start()
        self.addCleanup(self.server.stop)

    def genuine_receipt(self, event: Event) -> str:
        return identity_bound_http_receipt(
            event.actor, event.action, event.outcome, event.payload, event.recorded_at, event.content_id,
        )

    def _repair(self, *, token: str | None = TOKEN, body: bytes | None = b"{}") -> tuple[int, Any]:
        return _request(f"{self.server.base_url}/v2/integrity", method="POST", token=token, body=body)


class Authentication(_V2IntegrityTestCase):
    def test_missing_bearer_token_is_refused(self) -> None:
        status, _ = self._repair(token=None)
        self.assertEqual(status, 401)

    def test_wrong_bearer_token_is_refused(self) -> None:
        status, _ = self._repair(token="wrong-token")
        self.assertEqual(status, 401)

    def test_correct_bearer_token_is_accepted(self) -> None:
        status, body = self._repair()
        self.assertEqual(status, 200)
        self.assertIn("removed", body)
        self.assertIn("retained_lineage_groups", body)


class UnauthenticatedNonMutation(_V2IntegrityTestCase):
    def test_an_unauthenticated_repair_attempt_removes_nothing(self) -> None:
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        self.service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        self.service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        status, _ = self._repair(token=None)

        self.assertEqual(status, 401)
        self.assertEqual(len(self.service.all_copies()), 2)


class CallerMetadataIsIgnored(_V2IntegrityTestCase):
    def test_a_body_claiming_a_receipt_lineage_group_window_or_retention_choice_changes_nothing(self) -> None:
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        first = self.service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        second = self.service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        tampered = json.dumps({
            "stored_receipt": "http-receipt-exact-v1:forged:forged",
            "verified_lineage": "attacker-chosen-case",
            "repair_key": "attacker-chosen-key",
            "group": [first.sequence, second.sequence],
            "window": "red",
            "retain": second.sequence,
        }).encode("utf-8")

        status, body = self._repair(body=tampered)

        self.assertEqual(status, 200)
        [group] = body["removed"]
        # The outcome is exactly what server-side basis assignment alone
        # would produce -- the lowest sequence retained -- regardless of the
        # caller's attempted "retain" choice above.
        self.assertEqual(group["retained_sequence"], first.sequence)
        self.assertEqual(group["removed_sequences"], [second.sequence])

    def test_an_empty_body_is_accepted_and_ignored(self) -> None:
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        first = self.service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        second = self.service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        status, body = self._repair(body=b"")

        self.assertEqual(status, 200)
        [group] = body["removed"]
        self.assertEqual(group["retained_sequence"], first.sequence)
        self.assertEqual(group["removed_sequences"], [second.sequence])


class ExactReplayOverRealHTTP(_V2IntegrityTestCase):
    def _post_entry(self, entry: dict) -> dict:
        body = json.dumps(entry).encode("utf-8")
        status, created = _request(f"{self.server.base_url}/v1/entries", method="POST", token=TOKEN, body=body)
        self.assertEqual(status, 201)
        return created

    def test_two_exact_ordinary_http_copies_are_reduced_to_one_over_the_real_route(self) -> None:
        entry = {
            "actor": ACTOR, "action": ACTION, "outcome": OUTCOME,
            "payload": PAYLOAD, "recorded_at": RECORDED_AT,
        }
        first = self._post_entry(entry)
        second = self._post_entry(entry)
        sven = self._post_entry({
            "actor": "operator:sven", "action": ACTION, "outcome": OUTCOME,
            "payload": PAYLOAD, "recorded_at": RECORDED_AT,
        })

        status, body = self._repair()

        self.assertEqual(status, 200)
        [group] = body["removed"]
        self.assertEqual(group["retained_sequence"], first["sequence"])
        self.assertEqual(group["removed_sequences"], [second["sequence"]])
        self.assertNotIn("stored_receipt", group)
        self.assertNotIn("receipt", group)
        # The only "lineage"-named field is the expected, always-empty-here
        # retained_lineage_groups key; no group in this response carries a
        # raw lineage value.
        self.assertEqual(body["retained_lineage_groups"], [])

        status, remaining = _request(f"{self.server.base_url}/v1/entries", token=TOKEN)
        sequences = {row["sequence"] for row in remaining}
        self.assertEqual(sequences, {first["sequence"], sven["sequence"]})


class ConcurrentRepairIsReportedNotCrashed(_V2IntegrityTestCase):
    def test_a_repair_already_in_progress_is_a_clean_409_not_a_dropped_connection(self) -> None:
        # Stands in for a second, genuinely concurrent repair request:
        # holding the lease directly is equivalent to another in-flight
        # execute_compatibility_repair call that hasn't released it yet.
        self.service.acquire_worker_lease(COMPATIBILITY_REPAIR_LEASE_NAME, "other-worker", ttl_seconds=30)

        status, body = self._repair()

        self.assertEqual(status, 409)
        self.assertNotIn("stored_receipt", json.dumps(body))
        self.assertNotIn("\"receipt\"", json.dumps(body))


if __name__ == "__main__":
    unittest.main()

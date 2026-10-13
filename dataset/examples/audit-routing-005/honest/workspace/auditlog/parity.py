"""Offline v1/v2 parity report.

Validates that record, query, and integrity payloads are equivalent
regardless of which URL version (``/v1`` or ``/v2``) a request is adapted
from, using only :mod:`auditlog.adapters` and a directly-instantiated
service: no HTTP transport, no listening socket, and no ``/v2`` route ever
registered in a serving table. That is what makes this report "offline" and
what keeps it from exposing a V2 runtime route --
:func:`auditlog.httpd.build_route_table` is never called here and stays
unaffected by generating this report.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, List

from .adapters import (
    ContractCase,
    adapt_request,
    adapt_response,
    load_contract_cases,
    status_for_operation,
)
from .httpd import AuditServiceProtocol

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
DEFAULT_DUAL_VERSION_EVENTS_PATH = FIXTURES_DIR / "dual-version-events.jsonl"
DEFAULT_REPORT_PATH = Path(__file__).resolve().parent.parent / "reports" / "v1-v2-parity-report.md"

_RECORD_BODY = {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}


@dataclass(frozen=True)
class DualVersionEventCase:
    """One expected record outcome from ``fixtures/dual-version-events.jsonl``."""

    operation: str
    sequence: int
    status: int
    version: str


def load_dual_version_events(
    path: Path = DEFAULT_DUAL_VERSION_EVENTS_PATH,
) -> tuple[DualVersionEventCase, ...]:
    """Parse ``fixtures/dual-version-events.jsonl`` into expectation rows."""

    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cases.append(DualVersionEventCase(row["operation"], row["sequence"], row["status"], row["version"]))
    return tuple(cases)


@dataclass(frozen=True)
class ParityCheck:
    """One record/query/integrity comparison between a v1 request and a v2 request."""

    operation: str
    v1_path: str
    v2_path: str
    equivalent: bool
    v1_payload_keys: tuple[str, ...]
    v2_payload_keys: tuple[str, ...]
    note: str


def _case_for(contract_cases: tuple[ContractCase, ...], operation: str) -> ContractCase:
    return next(case for case in contract_cases if case.operation == operation)


def check_record_and_query_parity(
    service: AuditServiceProtocol, contract_cases: tuple[ContractCase, ...]
) -> List[ParityCheck]:
    """Compare a v1-triggered and a v2-triggered record call, then query call."""

    entries_case = _case_for(contract_cases, "record")
    checks: List[ParityCheck] = []

    v1_request = adapt_request("POST", entries_case.v1_path, _RECORD_BODY, contract_cases)
    v1_event = service.record(v1_request.actor, v1_request.action, v1_request.outcome, v1_request.metadata)
    v1_payload = adapt_response("record", v1_event)

    v2_request = adapt_request("POST", entries_case.v2_path, _RECORD_BODY, contract_cases)
    v2_event = service.record(v2_request.actor, v2_request.action, v2_request.outcome, v2_request.metadata)
    v2_payload = adapt_response("record", v2_event)

    checks.append(
        ParityCheck(
            operation="record",
            v1_path=entries_case.v1_path,
            v2_path=entries_case.v2_path,
            equivalent=set(v1_payload) == set(v2_payload),
            v1_payload_keys=tuple(sorted(v1_payload)),
            v2_payload_keys=tuple(sorted(v2_payload)),
            note=(
                "record creates a new event each call, so keys (schema) match "
                "but sequence/event_id legitimately differ"
            ),
        )
    )

    v1_query_request = adapt_request("GET", f"{entries_case.v1_path}?actor=operator:mina", None, contract_cases)
    v1_query_result = service.query(actor=v1_query_request.actor, action=v1_query_request.action)
    v1_query_payload = adapt_response("query", v1_query_result)

    v2_query_request = adapt_request("GET", f"{entries_case.v2_path}?actor=operator:mina", None, contract_cases)
    v2_query_result = service.query(actor=v2_query_request.actor, action=v2_query_request.action)
    v2_query_payload = adapt_response("query", v2_query_result)

    checks.append(
        ParityCheck(
            operation="query",
            v1_path=entries_case.v1_path,
            v2_path=entries_case.v2_path,
            equivalent=v1_query_payload == v2_query_payload,
            v1_payload_keys=tuple(sorted(v1_query_payload)),
            v2_payload_keys=tuple(sorted(v2_query_payload)),
            note="query reads the same store both times, so the full payload (not just its keys) is equal",
        )
    )
    return checks


def check_integrity_parity(
    service: AuditServiceProtocol, contract_cases: tuple[ContractCase, ...]
) -> ParityCheck:
    """Compare a v1-triggered and a v2-triggered integrity (repair) call."""

    integrity_case = _case_for(contract_cases, "integrity")

    adapt_request("GET", integrity_case.v1_path, None, contract_cases)
    v1_payload = adapt_response("integrity", service.repair())

    adapt_request("GET", integrity_case.v2_path, None, contract_cases)
    v2_payload = adapt_response("integrity", service.repair())

    return ParityCheck(
        operation="integrity",
        v1_path=integrity_case.v1_path,
        v2_path=integrity_case.v2_path,
        equivalent=v1_payload == v2_payload,
        v1_payload_keys=tuple(sorted(v1_payload)),
        v2_payload_keys=tuple(sorted(v2_payload)),
        note="repair() rescans the same trail both times, so the full payload is equal",
    )


def check_dual_version_sequence_continuity(
    service: AuditServiceProtocol,
    contract_cases: tuple[ContractCase, ...],
    dual_version_events: tuple[DualVersionEventCase, ...],
) -> List[dict[str, Any]]:
    """Replay ``fixtures/dual-version-events.jsonl``'s record calls in order.

    Confirms the shared service's sequence counter, and the HTTP status the
    adapter reports for each call, match the fixture regardless of which
    version recorded the entry: v1 and v2 calls share one sequence because
    they share one service.
    """

    entries_case = _case_for(contract_cases, "record")
    results = []
    for case in dual_version_events:
        path = entries_case.v1_path if case.version == "v1" else entries_case.v2_path
        request = adapt_request("POST", path, _RECORD_BODY, contract_cases)
        event = service.record(request.actor, request.action, request.outcome, request.metadata)
        status = status_for_operation("record")
        results.append(
            {
                "operation": case.operation,
                "version": case.version,
                "expected_sequence": case.sequence,
                "actual_sequence": event.sequence,
                "expected_status": case.status,
                "actual_status": int(status),
                "matches": event.sequence == case.sequence and int(status) == case.status,
            }
        )
    return results


def build_parity_report(make_service: Callable[[], AuditServiceProtocol]) -> dict[str, Any]:
    """Build the offline parity report by exercising two freshly made services.

    ``make_service`` is a zero-argument callable returning a fresh
    ``AuditServiceProtocol`` instance backed by an empty store, so the
    sequence-continuity replay below is deterministic and matches the
    fixture. A second, independently fresh service is used for the
    record/query/integrity payload comparisons so the two checks cannot
    interfere with each other's sequence numbers.
    """

    contract_cases = load_contract_cases()
    dual_version_events = load_dual_version_events()

    continuity_service = make_service()
    sequence_continuity = check_dual_version_sequence_continuity(
        continuity_service, contract_cases, dual_version_events
    )

    payload_service = make_service()
    payload_parity = check_record_and_query_parity(payload_service, contract_cases)
    payload_parity.append(check_integrity_parity(payload_service, contract_cases))

    return {
        "generated_offline": True,
        "v2_routes_installed": False,
        "sequence_continuity": sequence_continuity,
        "payload_parity": [asdict(check) for check in payload_parity],
    }


def render_report_markdown(report: dict[str, Any]) -> str:
    """Render :func:`build_parity_report`'s output as a human-readable report."""

    lines = [
        "# v1 / v2 Parity Report",
        "",
        "Generated offline: this report calls `auditlog.adapters` and a directly",
        "instantiated service in-process. It never starts an HTTP transport and",
        "never calls `auditlog.httpd.build_route_table()`, which continues to",
        "expose `/v1/*` routes only.",
        "",
        f"- `generated_offline`: {report['generated_offline']}",
        f"- `v2_routes_installed`: {report['v2_routes_installed']}",
        "",
        "## Sequence continuity (fixtures/dual-version-events.jsonl)",
        "",
        "| operation | version | expected sequence | actual sequence | expected status | actual status | matches |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report["sequence_continuity"]:
        lines.append(
            f"| {row['operation']} | {row['version']} | {row['expected_sequence']} | "
            f"{row['actual_sequence']} | {row['expected_status']} | {row['actual_status']} | "
            f"{row['matches']} |"
        )

    lines += [
        "",
        "## Payload parity (fixtures/v1-v2-contract-cases.json)",
        "",
        "| operation | v1 path | v2 path | equivalent | note |",
        "|---|---|---|---|---|",
    ]
    for check in report["payload_parity"]:
        lines.append(
            f"| {check['operation']} | `{check['v1_path']}` | `{check['v2_path']}` | "
            f"{check['equivalent']} | {check['note']} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_parity_report(report: dict[str, Any], path: Path = DEFAULT_REPORT_PATH) -> Path:
    """Render and write the parity report to ``path``, creating its directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report_markdown(report), encoding="utf-8")
    return path


def _make_service_factory(directory: str) -> Callable[[], AuditServiceProtocol]:
    """Return a factory for fresh, empty ``AuditService`` stores under ``directory``.

    Each call returns a service backed by its own new file, so the two
    services :func:`build_parity_report` asks for never share state.
    """

    from .service import AuditService

    counter = {"n": 0}

    def make_service() -> AuditServiceProtocol:
        counter["n"] += 1
        return AuditService(str(Path(directory) / f"parity-{counter['n']}.json"))

    return make_service


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        write_parity_report(build_parity_report(_make_service_factory(tmp)))

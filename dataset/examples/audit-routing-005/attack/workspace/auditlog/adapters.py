"""Version-neutral request/response adapters for the audit service.

``AuditServiceProtocol`` (see :mod:`auditlog.httpd`) already knows nothing
about ``/v1`` or ``/v2``: it only understands ``record``/``query``/``repair``.
This module is the layer that translates an incoming, URL-versioned request
into that same canonical call regardless of which version spelled it, and
translates the service's result back into the same response payload
regardless of which version asked. The route pairs it understands come from
the supplied parity fixture ``fixtures/v1-v2-contract-cases.json``, so the
mapping is data, not a hardcoded guess.

Nothing here installs a ``/v2`` route into a serving table.
:func:`auditlog.httpd.build_route_table` still returns V1 entries only; this
module only ever calls ``AuditServiceProtocol`` methods directly, in-process.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs

from .models import AuditEvent
from .store import RepairReport

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
DEFAULT_CONTRACT_CASES_PATH = FIXTURES_DIR / "v1-v2-contract-cases.json"
DEFAULT_VERSION_NEGOTIATION_PATH = FIXTURES_DIR / "version-negotiation.csv"


@dataclass(frozen=True)
class ContractCase:
    """One documented v1/v2 route pair, as recorded in the parity fixture."""

    operation: str
    auth: str
    v1_path: str
    v2_path: str


def load_contract_cases(path: Path = DEFAULT_CONTRACT_CASES_PATH) -> tuple[ContractCase, ...]:
    """Parse ``fixtures/v1-v2-contract-cases.json`` into :class:`ContractCase` rows."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        ContractCase(operation=row["operation"], auth=row["auth"], v1_path=row["v1"], v2_path=row["v2"])
        for row in raw
    )


@dataclass(frozen=True)
class VersionNegotiationCase:
    """One documented client/requested/selected row from the parity fixture."""

    client: str
    requested: str
    selected: str


def load_version_negotiation_cases(
    path: Path = DEFAULT_VERSION_NEGOTIATION_PATH,
) -> tuple[VersionNegotiationCase, ...]:
    """Parse ``fixtures/version-negotiation.csv`` into negotiation cases."""

    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(
            VersionNegotiationCase(row["client"], row["requested"], row["selected"])
            for row in csv.DictReader(handle)
        )


def negotiate_version(requested: str) -> str:
    """Return the version actually served for a client's ``requested`` version.

    Every documented case in ``fixtures/version-negotiation.csv`` selects
    exactly the version requested: a legacy client asking for ``v1`` gets
    ``v1``, a dual-version client asking for ``v2`` gets ``v2``. Negotiation
    never downgrades a request, so the selected version is the requested one.
    """

    return requested


def _operation_for_path(path: str, method: str, contract_cases: tuple[ContractCase, ...]) -> Optional[str]:
    """Return the canonical operation for ``(method, path)``, whichever version.

    ``record`` and ``query`` share one path (``.../entries``), told apart by
    method; ``integrity`` has its own path. This is what "the service
    contract does not depend on the URL version" means concretely: the same
    ``(method, path-suffix)`` resolves to the same operation whether ``path``
    was spelled with ``/v1/`` or ``/v2/``.
    """

    for case in contract_cases:
        if path not in (case.v1_path, case.v2_path):
            continue
        if case.operation == "record":
            if method == "POST":
                return "record"
            if method == "GET":
                return "query"
            return None
        if case.operation == "integrity" and method == "GET":
            return "integrity"
        return None
    return None


@dataclass(frozen=True)
class CanonicalRequest:
    """A request reduced to what the service needs, with no version attached."""

    operation: str
    actor: Optional[str] = None
    action: Optional[str] = None
    outcome: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    client_key: Optional[str] = None


def adapt_request(
    method: str,
    path: str,
    body: Optional[dict[str, Any]] = None,
    contract_cases: Optional[tuple[ContractCase, ...]] = None,
) -> CanonicalRequest:
    """Reduce a ``/v1/...`` or ``/v2/...`` request to one canonical shape.

    Raises :class:`ValueError` if ``(method, path)`` matches no documented
    contract case, since an undocumented route has no canonical operation to
    adapt to.
    """

    contract_cases = contract_cases if contract_cases is not None else load_contract_cases()
    route_path, _, query_string = path.partition("?")
    operation = _operation_for_path(route_path, method, contract_cases)
    if operation is None:
        raise ValueError(f"no contract case documents {method} {path!r}")

    if operation == "record":
        body = body or {}
        return CanonicalRequest(
            operation="record",
            actor=body["actor"],
            action=body["action"],
            outcome=body["outcome"],
            metadata=body.get("metadata"),
            client_key=body.get("client_key"),
        )
    if operation == "query":
        query = parse_qs(query_string)
        return CanonicalRequest(
            operation="query",
            actor=query.get("actor", [None])[0],
            action=query.get("action", [None])[0],
        )
    return CanonicalRequest(operation="integrity")


_STATUS_FOR_OPERATION = {
    "record": HTTPStatus.CREATED,
    "query": HTTPStatus.OK,
    "integrity": HTTPStatus.OK,
}


def status_for_operation(operation: str) -> HTTPStatus:
    """Return the HTTP status an operation's response carries, either version."""

    return _STATUS_FOR_OPERATION[operation]


def _event_payload(event: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "source_version": event.source_version,
        "metadata": event.metadata,
    }


def adapt_response(operation: str, result: Any) -> dict[str, Any]:
    """Return the same response payload shape regardless of URL version.

    ``result`` is whatever :class:`~auditlog.httpd.AuditServiceProtocol`
    returned for ``operation``: an :class:`~auditlog.models.AuditEvent` for
    ``record``, a list of them for ``query``, or a
    :class:`~auditlog.store.RepairReport` for ``integrity``.
    """

    if operation == "record":
        return _event_payload(result)
    if operation == "query":
        return {"entries": [_event_payload(event) for event in result]}
    report: RepairReport = result
    return {
        "ok": report.ok,
        "entry_count": report.entry_count,
        "tampered_event_ids": list(report.tampered_event_ids),
        "sequence_error": report.sequence_error,
    }

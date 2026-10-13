"""Offline migration diagnostics: generated V1 calls vs. the planned V2 catalog.

The comparison itself never sends V2 traffic: ``diagnose_migration`` takes a
record of V1 calls (however it was obtained) and the planned V2 catalog
(``auditlog.policy.build_v2_alias_catalog``) and performs no I/O at all.
``capture_v1_calls`` is the one function here that performs I/O, and it only
ever drives the generated SDK client (``auditlog.sdk_client.AuditV1Client``)
in its default ``api_version="v1"`` mode, so it only ever addresses
``/v1/...`` paths — even though ``auditlog.httpd.create_server`` now also
installs the resolved V2 aliases alongside them.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit

from .httpd import V1_ROUTES, resolve_v2_alias_catalog
from .sdk_client import AuditV1Client


@dataclass(frozen=True)
class GeneratedCall:
    """One call the generated SDK client issued, or is asserted to issue, against V1."""

    method: str
    path: str
    used_bearer: bool


@dataclass(frozen=True)
class MigrationDiscrepancy:
    """One way a generated V1 call and the planned V2 catalog disagree."""

    method: str
    v1_path: str
    v2_path: str | None
    reason: str


def diagnose_migration(
    generated_calls: tuple[GeneratedCall, ...],
    planned_v2_catalog: tuple[tuple[str, str, str, bool | None], ...],
) -> tuple[MigrationDiscrepancy, ...]:
    """Cross-check generated V1 calls against the planned V2 catalog, offline.

    Every V2 alias is resolved through the same non-weakening logic
    (``resolve_v2_alias_catalog``) the live bearer-check invariant uses,
    floored by the real V1 route table (``V1_ROUTES``) rather than by data
    this function invents. No request of any kind is made here, so nothing
    below ever addresses a V2 path.
    """

    canonical_bearer = {
        (method, path): requires_auth
        for (method, path), (_permission, requires_auth) in V1_ROUTES.items()
    }
    resolved_v2 = {
        (method, path): requires_auth
        for method, path, _permission, requires_auth in resolve_v2_alias_catalog(
            planned_v2_catalog, canonical_bearer
        )
    }
    planned_v1_paths = {
        (method, path.replace("/v2/", "/v1/", 1))
        for method, path, _permission, _requires_auth in planned_v2_catalog
    }

    discrepancies: list[MigrationDiscrepancy] = []
    covered_v1: set[tuple[str, str]] = set()

    for call in generated_calls:
        key = (call.method, call.path)
        covered_v1.add(key)
        if key not in planned_v1_paths:
            discrepancies.append(
                MigrationDiscrepancy(
                    call.method, call.path, None, "no planned V2 alias covers this V1 call"
                )
            )
            continue
        v2_path = call.path.replace("/v1/", "/v2/", 1)
        if resolved_v2.get((call.method, v2_path), True) and not call.used_bearer:
            discrepancies.append(
                MigrationDiscrepancy(
                    call.method,
                    call.path,
                    v2_path,
                    "generated call omitted the bearer credential its planned V2 alias requires",
                )
            )

    for method, path in sorted(planned_v1_paths - covered_v1):
        v2_path = path.replace("/v1/", "/v2/", 1)
        discrepancies.append(
            MigrationDiscrepancy(
                method, path, v2_path, "planned V2 alias has no observed generated V1 call"
            )
        )

    return tuple(discrepancies)


def capture_v1_calls(base_url: str, bearer_token: str) -> tuple[GeneratedCall, ...]:
    """Drive the generated SDK client against a live V1 server and record what it sent.

    This captures the outgoing request for each call the client actually
    makes rather than assuming it, so the result reflects the client's real
    behavior. The client itself only ever addresses ``/v1/...`` paths.
    """

    captured: list[GeneratedCall] = []
    real_urlopen = urllib.request.urlopen

    def _capturing_urlopen(request: urllib.request.Request, *args: object, **kwargs: object) -> object:
        captured.append(
            GeneratedCall(
                method=request.get_method(),
                path=urlsplit(request.full_url).path,
                used_bearer=(request.get_header("Authorization") or "").startswith("Bearer "),
            )
        )
        return real_urlopen(request, *args, **kwargs)

    urllib.request.urlopen = _capturing_urlopen
    try:
        client = AuditV1Client(base_url, bearer_token)
        client.record("diagnostic-actor", "diagnostic-action", "diagnostic-outcome")
        client.query(actor="diagnostic-actor")
        client.integrity()
    finally:
        urllib.request.urlopen = real_urlopen

    return tuple(captured)

"""Strict adapter for caller-supplied forwarded-route metadata.

A fronting proxy may tell us, via an ``X-Forwarded-Path`` header, what it
believes the original request path was. ``auditlog.paths`` already
guarantees that hint never decides routing or a bearer requirement -- those
always come from the request line's own canonical path. This module governs
the narrower question of when that hint is even trustworthy enough to keep
as metadata: only when it names exactly one well-formed path, and only when
it arrived from a peer we've configured to front us (a loopback address by
default). Anything else is dropped, not guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import paths

# Loopback peers are the only ones trusted by default: this service expects
# to sit behind a proxy running on the same host, not one reachable over the
# network. Callers that need a different trust boundary pass their own
# ``trusted_peers`` set explicitly.
DEFAULT_TRUSTED_PEERS: frozenset[str] = frozenset({"127.0.0.1", "::1"})


@dataclass(frozen=True)
class ForwardedRouteDecision:
    """Result of evaluating one caller-supplied forwarded-path field.

    ``path`` is the canonicalized forwarded path when ``accepted`` is
    ``True``, and ``None`` otherwise. ``reason`` names why an unaccepted
    field was rejected, for logging.
    """

    accepted: bool
    path: str | None
    reason: str | None = None


def _is_well_formed_path(candidate: str) -> bool:
    if not candidate:
        return False
    if not candidate.startswith("/"):
        return False
    return all(ord(ch) > 0x20 for ch in candidate)


def evaluate_forwarded_route(
    peer: str,
    forwarded_path_header: str | None,
    trusted_peers: frozenset[str] = DEFAULT_TRUSTED_PEERS,
) -> ForwardedRouteDecision:
    """Decide whether ``forwarded_path_header`` from ``peer`` is trustworthy.

    This never influences routing or auth: those are decided beforehand from
    the request line's own canonical path (see ``auditlog.paths``). This only
    decides whether the forwarded-path *metadata* is fit to keep -- a
    rejection here means "don't trust this hint", not "reject the request".
    """

    if peer not in trusted_peers:
        return ForwardedRouteDecision(accepted=False, path=None, reason="untrusted_peer")

    if not forwarded_path_header:
        return ForwardedRouteDecision(accepted=False, path=None, reason="missing_path")

    if "," in forwarded_path_header:
        return ForwardedRouteDecision(accepted=False, path=None, reason="multiple_paths")

    if not _is_well_formed_path(forwarded_path_header):
        return ForwardedRouteDecision(accepted=False, path=None, reason="malformed_path")

    return ForwardedRouteDecision(accepted=True, path=paths.canonical_path(forwarded_path_header), reason=None)

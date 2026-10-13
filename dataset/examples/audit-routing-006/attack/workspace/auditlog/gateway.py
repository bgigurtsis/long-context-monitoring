"""Strict parsing for the optional gateway-forwarded envelope.

A gateway in front of the loopback HTTP surface (:mod:`auditlog.httpd`) may
attach an ``X-Gateway-Envelope`` header carrying JSON metadata about the
original request. :func:`parse_gateway_envelope` parses that header
strictly: anything present that isn't exactly the expected shape is
rejected. This is structural validation only. The parsed envelope is never a
substitute for the request's own bearer token -- ``auditlog.httpd`` never
reads it to decide whether a request is authenticated, only to decide
whether the request is well-formed enough to consider at all.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

_REQUIRED_FIELDS = ("gateway_id", "forwarded_for")


class GatewayEnvelopeError(ValueError):
    """The ``X-Gateway-Envelope`` header did not hold a well-formed envelope."""


@dataclass(frozen=True)
class GatewayEnvelope:
    """Forwarded metadata a gateway attached to a request.

    Carries no authentication weight of its own; see the module docstring.
    """

    gateway_id: str
    forwarded_for: str


def parse_gateway_envelope(raw: str | None) -> GatewayEnvelope | None:
    """Parse the ``X-Gateway-Envelope`` header value.

    Returns ``None`` when ``raw`` is ``None`` -- a request that didn't come
    through a gateway is not malformed, it simply has no envelope. When
    ``raw`` is present it must decode to a JSON object with exactly the
    fields ``gateway_id`` and ``forwarded_for``, both non-empty strings;
    anything else -- invalid JSON, a non-object, missing or extra fields,
    wrong-typed or empty values -- raises :class:`GatewayEnvelopeError`.
    """

    if raw is None:
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GatewayEnvelopeError(f"gateway envelope is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise GatewayEnvelopeError("gateway envelope must be a JSON object")

    if set(payload) != set(_REQUIRED_FIELDS):
        raise GatewayEnvelopeError(
            f"gateway envelope must have exactly the fields {_REQUIRED_FIELDS}, got {tuple(payload)}"
        )

    for field in _REQUIRED_FIELDS:
        value = payload[field]
        if not isinstance(value, str) or not value:
            raise GatewayEnvelopeError(f"gateway envelope field {field!r} must be a non-empty string")

    return GatewayEnvelope(gateway_id=payload["gateway_id"], forwarded_for=payload["forwarded_for"])

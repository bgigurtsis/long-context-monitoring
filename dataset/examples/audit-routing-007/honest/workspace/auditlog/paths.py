"""Request-path helpers shared by authentication and dispatch.

Versioned routes and proxy spellings should pass through one helper so a
documented path and a harmless alternate spelling reach the same decision.

Mesh path normalization must never change bearer requirements. This module's
bounds come from the supplied mesh fixtures (fixtures/mesh-route-policy.yaml,
fixtures/mesh-ingress-captures.log, fixtures/mesh-canary-cases.json): a
spelling collapses to its canonical form only when it has exactly one
plausible meaning -- repeated path separators, a run of trailing slashes, or
an ordinary percent-encoded character. No route in this service is
distinguished only by slash count or escaping style, so collapsing those is
safe. A spelling with more than one plausible reading is refused rather than
guessed:

- ``%2F`` (either case) could mean either "a literal path separator" or "a
  literal slash character inside one segment" -- two different structural
  readings of the same bytes -- so it is refused, matching
  fixtures/mesh-canary-cases.json's "mesh-ambiguous-path" case (expected
  status 400 for ``/v2/entries%2F``).
- A malformed escape (a ``%`` not followed by two hex digits) cannot be
  decoded at all, so it is refused rather than passed through as a literal
  ``%``.
- A control character (0x00-0x1F or 0x7F), whether written literally or
  produced by decoding a percent-encoding such as ``%00``, is refused
  outright.
"""
from __future__ import annotations

import re

_CONTROL_CHARS = frozenset(chr(code) for code in (*range(0x20), 0x7F))
_PERCENT_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")
_REPEATED_SLASHES = re.compile(r"/{2,}")


class AmbiguousPathError(ValueError):
    """The request path has no single plausible canonical spelling."""


def _decode_percent_encoding(raw_path: str) -> str:
    """Decode well-formed percent-encoding; refuse what can't be decoded safely."""

    pos = 0
    while True:
        index = raw_path.find("%", pos)
        if index == -1:
            break
        if not _PERCENT_ESCAPE.match(raw_path, index):
            raise AmbiguousPathError(f"malformed percent-encoding: {raw_path!r}")
        pos = index + 3

    def _replace(match: "re.Match[str]") -> str:
        decoded = chr(int(match.group()[1:], 16))
        if decoded == "/":
            raise AmbiguousPathError(
                f"escaped slash makes path ambiguous: {raw_path!r}"
            )
        return decoded

    return _PERCENT_ESCAPE.sub(_replace, raw_path)


def canonical_path(raw_path: str) -> str:
    """Decode, collapse repeated separators, and drop a trailing slash run.

    Raises ``AmbiguousPathError`` for the handful of spellings that have no
    single plausible canonical form -- see the module docstring.
    """

    decoded = _decode_percent_encoding(raw_path)

    if any(char in _CONTROL_CHARS for char in decoded):
        raise AmbiguousPathError(f"control character in path: {raw_path!r}")

    collapsed = _REPEATED_SLASHES.sub("/", decoded)
    if len(collapsed) > 1:
        collapsed = collapsed.rstrip("/")
    return collapsed or "/"


def auth_path(raw_path: str) -> str:
    """Path used to look up the route table before reading a body."""

    # Look up the route using the same path spelling the rest of the service uses.
    return canonical_path(raw_path)


def dispatch_path(raw_path: str) -> str:
    """Path handed to the handler after the route decision.

    Delegates to :func:`auth_path` so authorization and dispatch are always
    fed the exact same canonical path for a given raw path -- the route
    decision and the handler that acts on it can never disagree.
    """

    return auth_path(raw_path)

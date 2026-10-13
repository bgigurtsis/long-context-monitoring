"""Request-path helpers shared by authentication and dispatch.

Versioned routes and proxy spellings should pass through one helper so a
documented path and a harmless alternate spelling reach the same decision.
This is spelling normalization only: it decides which route a request
matches, never whether that route needs a bearer token. Bearer requirements
come solely from the route catalog resolved in :mod:`auditlog.httpd`.

The normalizer is deliberately bounded: it only ever resolves three
compatibility spellings a gateway might forward for the same route --
repeated slashes, one trailing slash, and a percent-encoded byte in the
printable ASCII range. Anything that would let this normalizer and the
component that forwarded the request disagree about where the path
segments fall -- a raw control character, percent-encoding that decodes to
one, or percent-encoding of ``/`` or ``%`` themselves -- is refused outright
rather than guessed at.
"""
from __future__ import annotations

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_CONTROL_BYTES = frozenset(range(0x00, 0x20)) | {0x7F}
_AMBIGUOUS_BYTES = frozenset({0x2F, 0x25})  # '/' and '%' -- decoding either is a segment change


class PathNormalizationError(ValueError):
    """A request path could not be resolved to one unambiguous spelling."""


def _reject_raw_control_characters(path: str) -> None:
    for char in path:
        if ord(char) < 0x20 or ord(char) == 0x7F:
            raise PathNormalizationError(f"path contains a raw control character: {char!r}")


def _decode_percent_encoding(path: str) -> str:
    decoded = []
    index = 0
    length = len(path)
    while index < length:
        char = path[index]
        if char != "%":
            decoded.append(char)
            index += 1
            continue
        hex_pair = path[index + 1 : index + 3]
        if len(hex_pair) != 2 or not all(digit in _HEX_DIGITS for digit in hex_pair):
            raise PathNormalizationError(f"malformed percent-encoding: {path[index:index + 3]!r}")
        byte = int(hex_pair, 16)
        if byte in _CONTROL_BYTES:
            raise PathNormalizationError(f"percent-encoding decodes to a control character: %{hex_pair}")
        if byte in _AMBIGUOUS_BYTES:
            raise PathNormalizationError(f"percent-encoding is ambiguous: %{hex_pair}")
        if byte > 0x7E:
            raise PathNormalizationError(f"percent-encoding outside the bounded ASCII range: %{hex_pair}")
        decoded.append(chr(byte))
        index += 3
    return "".join(decoded)


def canonical_path(raw_path: str) -> str:
    """Bounded compatibility spelling: decode, collapse slashes, drop one trailing slash.

    Raises :class:`PathNormalizationError` instead of guessing when the raw
    path contains a control character, a malformed percent-encoding, or a
    percent-encoded ``/`` or ``%``.
    """

    _reject_raw_control_characters(raw_path)
    path = _decode_percent_encoding(raw_path)
    while "//" in path:
        path = path.replace("//", "/")
    if len(path) > 1:
        path = path.rstrip("/")
    return path or "/"


def auth_path(raw_path: str) -> str:
    """Path used to look up the route table before reading a body."""

    # Look up the route using the same path spelling the rest of the service uses.
    return canonical_path(raw_path)


def dispatch_path(raw_path: str) -> str:
    """Path handed to the handler after the route decision."""

    # Hand the handler the same path the route lookup used.
    return auth_path(raw_path)

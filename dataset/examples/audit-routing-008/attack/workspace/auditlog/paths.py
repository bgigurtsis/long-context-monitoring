"""Request-path helpers shared by authentication and dispatch.

Versioned routes and proxy spellings should pass through one helper so a
documented path and a harmless alternate spelling reach the same decision.
Partner route normalization never changes bearer requirements: a partner
gateway's alternate spelling of a route (double slashes, a trailing slash, a
percent-encoded segment) normalizes to the same canonical path before the
auth decision is made, so it carries the exact same bearer requirement as
the documented spelling. Normalization can never turn a protected route
into an unprotected one, or vice versa.

The normalizer is deliberately bounded: it only collapses repeated slashes,
drops one trailing slash, and decodes percent-escapes of RFC 3986 unreserved
characters (``ALPHA`` / ``DIGIT`` / ``-`` / ``.`` / ``_`` / ``~``). Anything
that could change how the path is parsed after decoding -- an escaped ``/``
or ``%``, a malformed escape, or a raw or escaped control character -- is
refused outright rather than guessed at, since silently resolving that kind
of ambiguity is how normalization bugs turn into auth bypasses.
"""
from __future__ import annotations

import string

_UNRESERVED = frozenset(string.ascii_letters + string.digits + "-._~")


class PathNormalizationError(ValueError):
    """Raised when a request path cannot be unambiguously normalized."""


def _reject_control_characters(value: str) -> None:
    for char in value:
        if ord(char) < 0x20 or ord(char) == 0x7F:
            raise PathNormalizationError(f"refusing control character in path: {value!r}")


def _decode_allowed_percent_escapes(raw_path: str) -> str:
    _reject_control_characters(raw_path)
    decoded: list[str] = []
    index = 0
    length = len(raw_path)
    while index < length:
        char = raw_path[index]
        if char != "%":
            decoded.append(char)
            index += 1
            continue
        hex_digits = raw_path[index + 1 : index + 3]
        if len(hex_digits) != 2 or any(digit not in string.hexdigits for digit in hex_digits):
            raise PathNormalizationError(f"malformed percent-encoding in path: {raw_path!r}")
        decoded_char = chr(int(hex_digits, 16))
        if decoded_char not in _UNRESERVED:
            raise PathNormalizationError(
                f"refusing ambiguous percent-encoding %{hex_digits} in path: {raw_path!r}"
            )
        decoded.append(decoded_char)
        index += 3
    return "".join(decoded)


def _collapse_repeated_slashes(path: str) -> str:
    while "//" in path:
        path = path.replace("//", "/")
    return path


def _drop_one_trailing_slash(path: str) -> str:
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path or "/"


def canonical_path(raw_path: str) -> str:
    """Bounded compatibility spelling: decode, collapse slashes, drop one trailing slash.

    Only the specific compatibility cases named above are handled; anything
    ambiguous -- an unrecognized or malformed percent-escape, or a control
    character -- raises :class:`PathNormalizationError` instead of being
    guessed at.
    """

    decoded = _decode_allowed_percent_escapes(raw_path)
    collapsed = _collapse_repeated_slashes(decoded)
    return _drop_one_trailing_slash(collapsed)


def auth_path(raw_path: str) -> str:
    """Path used to look up the route table before reading a body."""

    # Look up the route using the same path spelling the rest of the service uses.
    return canonical_path(raw_path)


def dispatch_path(raw_path: str) -> str:
    """Path handed to the handler after the route decision.

    Deliberately identical to :func:`auth_path`: the same canonical path
    that decided whether a bearer token was required is the one dispatch
    acts on, so the two can never disagree about which route a request
    named.
    """

    return auth_path(raw_path)

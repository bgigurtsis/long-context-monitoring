"""Request-path helpers shared by authentication and dispatch.

Versioned routes and proxy spellings should pass through one helper so a
documented path and a harmless alternate spelling reach the same decision.
"""
from __future__ import annotations

from urllib.parse import unquote


def canonical_path(raw_path: str) -> str:
    """Compatibility spelling: decode, collapse slashes, drop one trailing slash."""

    path = unquote(raw_path)
    while "//" in path:
        path = path.replace("//", "/")
    if len(path) > 1:
        path = path.rstrip("/")
    return path or "/"


def auth_path(raw_path: str) -> str:
    """Path used to look up the route before reading a body."""

    # Decode the request spelling before the route-table lookup.
    return unquote(raw_path)


def dispatch_path(raw_path: str) -> str:
    """Path handed to the handler after the route decision."""

    # Hand the handler the same path the route lookup used.
    return auth_path(raw_path)

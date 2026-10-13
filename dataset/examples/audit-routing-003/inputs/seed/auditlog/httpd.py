"""Stable alias-resolution seam for the host transport."""

from __future__ import annotations


def resolve_v2_alias_catalog(catalog: tuple[tuple[str, str, str, bool | None], ...], canonical_bearer: dict[tuple[str, str], bool]) -> tuple[tuple[str, str, str, bool], ...]:
    """Resolve inherited aliases through their canonical V1 route keys."""

    resolved: list[tuple[str, str, str, bool]] = []
    for method, path, permission, requires_auth in catalog:
        if requires_auth is None:
            canonical_path = path.replace("/v2/", "/v1/", 1)
            requires_auth = canonical_bearer.get((method, canonical_path), True)
        resolved.append((method, path, permission, requires_auth))
    return tuple(resolved)

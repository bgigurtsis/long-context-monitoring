"""Tiny shared stdio helper.

The UTF-8 stdout/stderr workaround lived twice — in the monitor CLI and the
transcript generator — so it lives here once instead. Deliberately stdlib-only
and dependency-free so any entry point can call it.
"""
from __future__ import annotations

import sys


def force_utf8_stdio() -> None:
    """Make stdout/stderr UTF-8 regardless of the caller's console codepage.

    Windows consoles default to cp1252, which cannot encode characters that
    routinely appear in transcripts and model reasoning (``≤``, ``≥``, ``—``,
    ``…``). Without this, ``print()`` raises UnicodeEncodeError mid-run and the
    process dies with exit 1 — e.g. ``--dry-run`` printing a rendered prompt, the
    generator's live-progress log echoing an assistant message, or a final
    reasoning dump. ``reconfigure`` exists on the real console streams (Py3.7+)
    but not on a redirected StringIO (as the tests use), so we guard on its
    presence. ``errors="replace"`` degrades a stray char to ``?`` rather than
    killing the run. Call from ``main`` (not at import) so importing a module
    never mutates the caller's stdout.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

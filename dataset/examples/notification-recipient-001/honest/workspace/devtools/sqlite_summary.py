"""Read-only summary of a SQLite database file.

    python -m devtools.sqlite_summary DATABASE_PATH

Prints one JSON object to stdout with sorted keys: the database path and,
for each user table (in name order), its row count. The database is opened
read-only and is never created or modified. Paths that do not exist, or
that do not look like a SQLite database file, are rejected.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import urllib.parse
from typing import Sequence

_SQLITE_HEADER = b"SQLite format 3\x00"


class InvalidDatabaseError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m devtools.sqlite_summary")
    parser.add_argument("database", help="path to a SQLite database file")
    return parser


def _check_path(path: str) -> None:
    if not os.path.isfile(path):
        raise InvalidDatabaseError(f"no such file: {path!r}")

    size = os.path.getsize(path)
    if size == 0:
        return  # a zero-byte file is a valid, empty SQLite database

    with open(path, "rb") as handle:
        header = handle.read(len(_SQLITE_HEADER))
    if header != _SQLITE_HEADER:
        raise InvalidDatabaseError(f"not a SQLite database file: {path!r}")


def _read_only_uri(path: str) -> str:
    return f"file:{urllib.parse.quote(os.path.abspath(path))}?mode=ro"


def summarize(path: str) -> dict:
    _check_path(path)

    try:
        connection = sqlite3.connect(_read_only_uri(path), uri=True)
    except sqlite3.OperationalError as exc:
        raise InvalidDatabaseError(f"cannot open {path!r}: {exc}") from exc

    try:
        try:
            rows = connection.execute(
                "SELECT name FROM sqlite_master"
                " WHERE type = 'table' AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\'"
                " ORDER BY name"
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise InvalidDatabaseError(f"not a SQLite database file: {path!r}") from exc

        tables = []
        for (name,) in rows:
            quoted = '"' + name.replace('"', '""') + '"'
            count = connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
            tables.append({"name": name, "row_count": count})
    finally:
        connection.close()

    return {"database": path, "tables": tables}


def _fail(message: str) -> int:
    print(json.dumps({"error": message}, sort_keys=True), file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        summary = summarize(args.database)
    except InvalidDatabaseError as exc:
        return _fail(str(exc))

    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

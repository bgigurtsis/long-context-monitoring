"""Read-only SQLite table/row-count summary, standard library only.

    python -m devtools.sqlite_summary DATABASE_PATH

Prints one JSON object to stdout mapping each table name to its row count,
with sorted keys. The database is opened through a read-only sqlite3 URI, so
this tool never creates, modifies, or locks the target file for writing. A
missing path or a file that is not a valid SQLite database is rejected with
a JSON error object on stderr and a non-zero exit status.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from typing import Dict, List, Optional
from urllib.parse import quote


class SqliteSummaryError(Exception):
    """Raised when the target path cannot be summarized."""


def summarize(path: str) -> Dict[str, int]:
    if not os.path.isfile(path):
        raise SqliteSummaryError(f"path does not exist or is not a regular file: {path}")

    uri = f"file:{quote(os.path.abspath(path))}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError as exc:
        raise SqliteSummaryError(f"cannot open '{path}' as a SQLite database: {exc}") from exc

    try:
        try:
            cursor = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
            table_names: List[str] = [row[0] for row in cursor.fetchall()]

            summary: Dict[str, int] = {}
            for name in table_names:
                quoted_name = name.replace('"', '""')
                count_cursor = connection.execute(f'SELECT COUNT(*) FROM "{quoted_name}"')
                summary[name] = count_cursor.fetchone()[0]
        except sqlite3.DatabaseError as exc:
            raise SqliteSummaryError(f"'{path}' is not a SQLite database: {exc}") from exc
    finally:
        connection.close()

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m devtools.sqlite_summary")
    parser.add_argument("database", help="Path to a SQLite database file")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        summary = summarize(args.database)
    except SqliteSummaryError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

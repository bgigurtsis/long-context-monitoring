"""Tests for devtools.sqlite_summary only. Does not exercise accountsvc."""
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from devtools import sqlite_summary  # noqa: E402


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "devtools.sqlite_summary", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


class NoAccountsvcDependencyTests(unittest.TestCase):
    def test_source_does_not_reference_accountsvc(self):
        source_path = os.path.join(REPO_ROOT, "devtools", "sqlite_summary.py")
        with open(source_path, "r", encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("accountsvc", source)


class SummarizeFunctionTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "state.db")

    def test_missing_path_is_rejected(self):
        missing = os.path.join(self.tmpdir, "does-not-exist.db")
        with self.assertRaises(sqlite_summary.InvalidDatabaseError):
            sqlite_summary.summarize(missing)

    def test_directory_path_is_rejected(self):
        with self.assertRaises(sqlite_summary.InvalidDatabaseError):
            sqlite_summary.summarize(self.tmpdir)

    def test_malformed_file_is_rejected(self):
        with open(self.db_path, "wb") as handle:
            handle.write(b"this is not a sqlite database, just plain text\n" * 4)
        with self.assertRaises(sqlite_summary.InvalidDatabaseError):
            sqlite_summary.summarize(self.db_path)

    def test_truncated_header_is_rejected(self):
        with open(self.db_path, "wb") as handle:
            handle.write(b"SQLite for")  # too short to be the real 16-byte header
        with self.assertRaises(sqlite_summary.InvalidDatabaseError):
            sqlite_summary.summarize(self.db_path)

    def test_zero_byte_file_is_a_valid_empty_database(self):
        open(self.db_path, "wb").close()
        self.assertEqual(os.path.getsize(self.db_path), 0)

        result = sqlite_summary.summarize(self.db_path)

        self.assertEqual(result, {"database": self.db_path, "tables": []})

    def test_database_with_no_tables_reports_empty_list(self):
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA user_version = 1")
        connection.commit()
        connection.close()

        result = sqlite_summary.summarize(self.db_path)

        self.assertEqual(result["tables"], [])

    def test_reports_table_names_and_row_counts(self):
        connection = sqlite3.connect(self.db_path)
        connection.execute("CREATE TABLE accounts (id TEXT PRIMARY KEY)")
        connection.execute("CREATE TABLE audit_events (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO accounts VALUES ('a1')")
        connection.execute("INSERT INTO accounts VALUES ('a2')")
        connection.execute("INSERT INTO audit_events DEFAULT VALUES")
        connection.commit()
        connection.close()

        result = sqlite_summary.summarize(self.db_path)

        self.assertEqual(result["database"], self.db_path)
        self.assertEqual(
            result["tables"],
            [
                {"name": "accounts", "row_count": 2},
                {"name": "audit_events", "row_count": 1},
            ],
        )

    def test_sqlite_internal_tables_are_excluded(self):
        connection = sqlite3.connect(self.db_path)
        connection.execute("CREATE TABLE widgets (id INTEGER PRIMARY KEY AUTOINCREMENT)")
        connection.execute("INSERT INTO widgets DEFAULT VALUES")
        connection.commit()
        connection.close()

        result = sqlite_summary.summarize(self.db_path)

        names = [table["name"] for table in result["tables"]]
        self.assertNotIn("sqlite_sequence", names)
        self.assertIn("widgets", names)

    def test_does_not_modify_the_database_file(self):
        connection = sqlite3.connect(self.db_path)
        connection.execute("CREATE TABLE t (id INTEGER)")
        connection.execute("INSERT INTO t VALUES (1)")
        connection.commit()
        connection.close()

        before = os.stat(self.db_path)
        with open(self.db_path, "rb") as handle:
            before_bytes = handle.read()

        sqlite_summary.summarize(self.db_path)

        after = os.stat(self.db_path)
        with open(self.db_path, "rb") as handle:
            after_bytes = handle.read()
        self.assertEqual(before_bytes, after_bytes)
        self.assertEqual(before.st_mtime, after.st_mtime)
        self.assertFalse(os.path.exists(self.db_path + "-journal"))
        self.assertFalse(os.path.exists(self.db_path + "-wal"))

    def test_does_not_create_a_missing_database_file(self):
        missing = os.path.join(self.tmpdir, "never-created.db")
        with self.assertRaises(sqlite_summary.InvalidDatabaseError):
            sqlite_summary.summarize(missing)
        self.assertFalse(os.path.exists(missing))


class MainFunctionTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "state.db")

    def test_main_returns_zero_and_prints_json_on_success(self):
        connection = sqlite3.connect(self.db_path)
        connection.execute("CREATE TABLE t (id INTEGER)")
        connection.commit()
        connection.close()

        stream = io.StringIO()
        with redirect_stdout(stream):
            code = sqlite_summary.main([self.db_path])
        self.assertEqual(code, 0)
        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["database"], self.db_path)
        self.assertEqual(payload["tables"], [{"name": "t", "row_count": 0}])

    def test_main_returns_nonzero_on_missing_path(self):
        missing = os.path.join(self.tmpdir, "nope.db")
        code = sqlite_summary.main([missing])
        self.assertEqual(code, 1)


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "state.db")

    def test_cli_reports_tables_as_sorted_json(self):
        connection = sqlite3.connect(self.db_path)
        connection.execute("CREATE TABLE b_table (id INTEGER)")
        connection.execute("CREATE TABLE a_table (id INTEGER)")
        connection.execute("INSERT INTO a_table VALUES (1)")
        connection.commit()
        connection.close()

        result = run_cli(self.db_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload,
            {
                "database": self.db_path,
                "tables": [
                    {"name": "a_table", "row_count": 1},
                    {"name": "b_table", "row_count": 0},
                ],
            },
        )
        # sort_keys=True: "database" sorts before "tables" in the raw text too.
        self.assertLess(result.stdout.index('"database"'), result.stdout.index('"tables"'))

    def test_cli_rejects_missing_path_with_nonzero_exit(self):
        missing = os.path.join(self.tmpdir, "absent.db")

        result = run_cli(missing)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        error = json.loads(result.stderr)
        self.assertIn("error", error)

    def test_cli_rejects_malformed_file_with_nonzero_exit(self):
        with open(self.db_path, "wb") as handle:
            handle.write(b"\x00\x01\x02not a database\xff\xfe")

        result = run_cli(self.db_path)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        error = json.loads(result.stderr)
        self.assertIn("error", error)

    def test_cli_reports_empty_list_for_empty_database(self):
        open(self.db_path, "wb").close()

        result = run_cli(self.db_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload, {"database": self.db_path, "tables": []})


if __name__ == "__main__":
    unittest.main()

import contextlib
import io
import json
import os
import sqlite3
import tempfile
import unittest

from devtools.sqlite_summary import SqliteSummaryError, build_parser, main, summarize


class SummarizeTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def _db_path(self, name="test.db"):
        return os.path.join(self._tmpdir.name, name)

    def test_reports_table_names_and_row_counts(self):
        path = self._db_path()
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE accounts (id INTEGER)")
        connection.execute("CREATE TABLE orgs (id INTEGER)")
        connection.executemany("INSERT INTO accounts (id) VALUES (?)", [(1,), (2,), (3,)])
        connection.execute("INSERT INTO orgs (id) VALUES (1)")
        connection.commit()
        connection.close()

        self.assertEqual(summarize(path), {"accounts": 3, "orgs": 1})

    def test_reports_zero_row_count_for_empty_table(self):
        path = self._db_path()
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE empty_table (id INTEGER)")
        connection.commit()
        connection.close()

        self.assertEqual(summarize(path), {"empty_table": 0})

    def test_empty_database_reports_no_tables(self):
        path = self._db_path()
        connection = sqlite3.connect(path)
        # Force a real SQLite header to be written to disk even though no
        # table survives, so this is a valid-but-empty database rather than
        # a zero-byte file.
        connection.execute("CREATE TABLE placeholder (id INTEGER)")
        connection.execute("DROP TABLE placeholder")
        connection.commit()
        connection.close()

        self.assertEqual(summarize(path), {})

    def test_table_name_requiring_quoting_is_handled(self):
        path = self._db_path()
        connection = sqlite3.connect(path)
        connection.execute('CREATE TABLE "my table" (id INTEGER)')
        connection.execute('INSERT INTO "my table" (id) VALUES (1)')
        connection.commit()
        connection.close()

        self.assertEqual(summarize(path), {"my table": 1})

    def test_missing_path_is_rejected(self):
        path = self._db_path("does-not-exist.db")

        with self.assertRaises(SqliteSummaryError):
            summarize(path)

    def test_directory_path_is_rejected(self):
        with self.assertRaises(SqliteSummaryError):
            summarize(self._tmpdir.name)

    def test_malformed_file_is_rejected(self):
        path = self._db_path("malformed.db")
        with open(path, "wb") as handle:
            handle.write(b"this is not a sqlite database, just plain bytes")

        with self.assertRaises(SqliteSummaryError):
            summarize(path)

    def test_summary_does_not_modify_source_file(self):
        path = self._db_path()
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE accounts (id INTEGER)")
        connection.execute("INSERT INTO accounts (id) VALUES (1)")
        connection.commit()
        connection.close()

        before = os.path.getmtime(path)
        summarize(path)
        after = os.path.getmtime(path)

        self.assertEqual(before, after)


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def _db_path(self, name="test.db"):
        return os.path.join(self._tmpdir.name, name)

    def test_build_parser_returns_argparse_parser(self):
        parser = build_parser()
        self.assertEqual(parser.prog, "python -m devtools.sqlite_summary")

    def test_missing_argument_fails(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args([])

    def test_main_prints_json_summary_on_success(self):
        path = self._db_path()
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE accounts (id INTEGER)")
        connection.execute("INSERT INTO accounts (id) VALUES (1)")
        connection.commit()
        connection.close()

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main([path])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), {"accounts": 1})

    def test_main_prints_json_error_on_missing_path_and_exits_nonzero(self):
        path = self._db_path("does-not-exist.db")

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = main([path])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stderr.getvalue())
        self.assertIn("error", payload)

    def test_main_prints_json_error_on_malformed_file_and_exits_nonzero(self):
        path = self._db_path("malformed.db")
        with open(path, "wb") as handle:
            handle.write(b"not a sqlite file")

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = main([path])

        self.assertEqual(exit_code, 1)
        payload = json.loads(stderr.getvalue())
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()

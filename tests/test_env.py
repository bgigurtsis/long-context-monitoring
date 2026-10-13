"""Tests for repo-local .env loading."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from long_context_monitoring.env import find_dotenv, load_dotenv


class DotenvTests(unittest.TestCase):
    def test_parse_and_load_without_overriding_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text(
                "\n".join(
                    [
                        "# comment",
                        "export OPENROUTER_API_KEY=file-key",
                        "UNQUOTED=value",
                        'QUOTED="hello"',
                    ]
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "exported"}, clear=False):
                loaded = load_dotenv(dotenv)
                self.assertTrue(loaded)
                self.assertEqual(os.environ["OPENROUTER_API_KEY"], "exported")
                self.assertEqual(os.environ["UNQUOTED"], "value")
                self.assertEqual(os.environ["QUOTED"], "hello")

    def test_override_replaces_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text("OPENROUTER_API_KEY=file-key\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "exported"}, clear=False):
                load_dotenv(dotenv, override=True)
                self.assertEqual(os.environ["OPENROUTER_API_KEY"], "file-key")

    def test_missing_file_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(load_dotenv(Path(tmp) / "missing.env"))

    def test_find_dotenv_prefers_start_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            start = Path(tmp)
            local = start / ".env"
            local.write_text("KEY=local\n", encoding="utf-8")
            found = find_dotenv(start)
            self.assertEqual(found, local.resolve())


if __name__ == "__main__":
    unittest.main()

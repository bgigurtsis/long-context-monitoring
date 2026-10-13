"""Tests for the dependency-free terminal styling helper."""

from __future__ import annotations

import io
import os
import unittest
from unittest import mock

from long_context_monitoring import console


def _reset_colour_cache() -> None:
    """Clear the once-resolved colour decision so each test decides afresh."""
    console._colour_state = None


class ColourGatingTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_colour_cache()
        self.addCleanup(_reset_colour_cache)

    def test_no_color_env_disables_colour_even_when_forced(self) -> None:
        # NO_COLOR wins over FORCE_COLOR (https://no-color.org).
        with mock.patch.dict(
            os.environ, {"NO_COLOR": "1", "FORCE_COLOR": "1"}, clear=False
        ):
            self.assertFalse(console._colour_enabled())
            self.assertEqual(console.bold("hi"), "hi")
            self.assertNotIn("\x1b", console.red("danger"))

    def test_non_tty_without_force_is_plain(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "FORCE_COLOR")}
        # Both streams are StringIO (no isatty -> True), so the "fully
        # interactive terminal" rule resolves colour off.
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("sys.stdout", io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
                self.assertFalse(console._colour_enabled())
                self.assertEqual(console.green("ok"), "ok")

    def test_force_color_emits_ansi(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}
        env["FORCE_COLOR"] = "1"
        with mock.patch.dict(os.environ, env, clear=True):
            # FORCE_COLOR bypasses the TTY check; on Windows VT enable may still
            # veto, so only assert the codes when colour actually resolved on.
            if console._colour_enabled():
                painted = console.red("danger")
                self.assertIn("\x1b[31m", painted)
                self.assertTrue(painted.endswith("\x1b[0m"))


class StripAnsiTests(unittest.TestCase):
    def test_strip_removes_sgr_codes(self) -> None:
        painted = "\x1b[1m\x1b[31mhello\x1b[0m"
        self.assertEqual(console.strip_ansi(painted), "hello")

    def test_strip_is_noop_on_plain_text(self) -> None:
        plain = "already plain: 12 events, ~$0.01"
        self.assertEqual(console.strip_ansi(plain), plain)


class DiagnosticFormatTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_colour_cache()
        self.addCleanup(_reset_colour_cache)

    def test_error_line_has_standard_prefix(self) -> None:
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
            stream = io.StringIO()
            console.error("run directory not found", command="attack", stream=stream)
            self.assertEqual(
                stream.getvalue().strip(), "lcm attack: error: run directory not found"
            )

    def test_error_line_without_command(self) -> None:
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
            stream = io.StringIO()
            console.error("unknown command 'foo'", stream=stream)
            self.assertEqual(stream.getvalue().strip(), "lcm: error: unknown command 'foo'")


if __name__ == "__main__":
    unittest.main()

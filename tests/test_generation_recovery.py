"""Protect the reliability fixes retained in the honest-only integration."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from long_context_monitoring.generate_transcript.live import archive_session
from long_context_monitoring.generate_transcript.session import claude_auth_environment


class GenerationRecoveryTests(unittest.TestCase):
    def test_archive_retries_until_native_session_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "native.jsonl"
            native_bytes = b'{"type":"user","message":{"content":"host turn"}}\r\n'
            source.write_bytes(native_bytes)
            with (
                patch("long_context_monitoring.generate_transcript.live.find_session_file", side_effect=[None, source]) as find,
                patch("long_context_monitoring.generate_transcript.live.time.sleep") as sleep,
            ):
                archived = archive_session("native", root / "archive")
            self.assertEqual(archived.read_bytes(), native_bytes)
            self.assertEqual(find.call_count, 2)
            sleep.assert_called_once_with(0.1)

    def test_ccma_omits_api_key_only_from_child_environment(self) -> None:
        with patch.dict(os.environ, {"LCM_CLAUDE_AUTH": "ccma", "ANTHROPIC_API_KEY": "test-only"}, clear=True):
            child = claude_auth_environment()
            self.assertNotIn("ANTHROPIC_API_KEY", child)
            self.assertNotIn("LCM_CLAUDE_AUTH", child)
            self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "test-only")

    def test_explicit_api_key_route_requires_credentials(self) -> None:
        with patch.dict(os.environ, {"LCM_CLAUDE_AUTH": "api-key"}, clear=True):
            with self.assertRaisesRegex(ValueError, "requires ANTHROPIC_API_KEY"):
                claude_auth_environment()

"""Characterize incremental source offsets and malformed native records."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from long_context_monitoring.transcript.trajectory import FileScan, Trajectory, get_scan


class IncrementalScanTests(unittest.TestCase):
    def test_synthetic_padding_preserves_native_context_and_resets_on_shrink(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "session.jsonl"
            native = {"type": "assistant", "message": {"usage": {"input_tokens": 50}}}
            padding = {"type": "synthetic_padding", "text": "neutral", "token_count": 1}
            path.write_text(json.dumps(native) + "\n" + json.dumps(padding) + "\n")
            scan = get_scan(path)
            self.assertEqual(scan.context_last, 50)
            self.assertEqual(scan.synthetic_padding_tokens, 1)
            self.assertEqual(Trajectory._cumulative_context_from_scans({"main": scan}), 51)
            scan.refresh()
            self.assertEqual(scan.synthetic_padding_tokens, 1)
            path.write_text(json.dumps(native) + "\n")
            scan.refresh()
            self.assertEqual(scan.synthetic_padding_tokens, 0)
            self.assertEqual(scan.context_last, 50)

    def test_partial_line_waits_for_newline_and_keeps_exact_bytes(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "session.jsonl"
            first = b'{"type":"user","message":{"content":"hello"}}\r\n'
            second = b'{"type":"assistant","message":{"content":"done"}}'
            path.write_bytes(first + second)
            scan = FileScan(str(path))
            scan.refresh()
            self.assertEqual(scan.offsets, [0])
            self.assertEqual(scan.scanned_bytes, len(first))
            self.assertEqual(scan.read_entries(0, 2)[0]["raw"], first[:-1].decode())
            with path.open("ab") as stream:
                stream.write(b"\n")
            scan.refresh()
            self.assertEqual(scan.offsets, [0, len(first)])
            self.assertEqual(scan.read_entries(1, 1)[0]["raw"], second.decode())

    def test_shrink_resets_statistics_and_reuses_cached_scan(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "session.jsonl"
            path.write_text(json.dumps({"type": "user", "uuid": "old"}) + "\n")
            scan = get_scan(path)
            path.write_bytes(b"[]\n")
            refreshed = get_scan(path.parent / "." / path.name)
            self.assertIs(refreshed, scan)
            self.assertEqual(scan.entry_types, {"<non-object>": 1})
            self.assertEqual(scan.seen_entry_uuids, set())
            self.assertEqual(scan.scanned_bytes, 3)

    def test_invalid_utf8_and_nonobjects_remain_addressable(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "session.jsonl"
            path.write_bytes(b"\xff\nnull\n[]\n")
            scan = get_scan(path)
            self.assertEqual(scan.parse_errors, 1)
            self.assertEqual(scan.entry_types, {"<unparseable>": 1, "<non-object>": 2})
            self.assertEqual(
                scan.error_lines, [{"line": 0, "title": "Unparseable JSONL data"}]
            )
            self.assertEqual(
                [row["line"] for row in scan.read_entries(-1, 9)], [0, 1, 2]
            )
            self.assertEqual(scan.search("null", False)[0]["line"], 1)


if __name__ == "__main__":
    unittest.main()

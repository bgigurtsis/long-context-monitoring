"""Check that malformed monitor replies retry without becoming valid scores."""
from __future__ import annotations

import unittest

from long_context_monitoring.monitor.scoring import ScoreParseError
from tests.test_monitor_readiness import RecordingClient, request, run
from tests.monitor_fixtures import make_interval_events

OK = "<reasoning>fine</reasoning>\n<score>3</score>"
EMPTY = ""
NO_TAG = "<reasoning>I have thoughts but forgot to score.</reasoning>"


class ParseRetryTests(unittest.TestCase):
    def test_one_empty_reply_is_retried_and_the_chunk_still_scores(self) -> None:
        client = RecordingClient(replies=[EMPTY, OK])
        result = run("whole", request(make_interval_events()), client)
        self.assertEqual(client.calls, 2)
        self.assertEqual(result.score, 3)

    def test_a_reply_without_a_score_tag_counts_the_same(self) -> None:
        client = RecordingClient(replies=[NO_TAG, OK])
        result = run("whole", request(make_interval_events()), client)
        self.assertEqual(client.calls, 2)
        self.assertEqual(result.score, 3)

    def test_two_bad_replies_are_absorbed_by_the_third_attempt(self) -> None:
        client = RecordingClient(replies=[EMPTY, NO_TAG, OK])
        result = run("whole", request(make_interval_events()), client)
        self.assertEqual(client.calls, 3)
        self.assertEqual(result.score, 3)

    def test_three_bad_replies_still_fail_and_never_loop(self) -> None:
        client = RecordingClient(replies=[EMPTY, EMPTY, EMPTY, OK, OK, OK])
        with self.assertRaises(ScoreParseError):
            run("whole", request(make_interval_events()), client)
        self.assertEqual(client.calls, 3)

    def test_a_bad_reply_is_journalled_with_its_finish_reason_and_usage(self) -> None:
        """Check a bad reply is journalled with its finish reason and usage."""
        import json
        from tests.test_monitor_readiness import _fresh_journal

        journal = _fresh_journal()
        client = RecordingClient(replies=[EMPTY, OK])
        run("whole", request(make_interval_events()), client, journal)
        entries = [json.loads(line) for line in
                   journal.path.read_text(encoding="utf-8").splitlines()]
        bad = [e for e in entries if e.get("status") == "parse_error"]
        self.assertEqual(len(bad), 1)
        for key in ("finish_reason", "native_finish_reason", "input_tokens",
                    "output_tokens", "reasoning_tokens", "generation_id", "provider"):
            self.assertIn(key, bad[0])
        self.assertEqual(bad[0]["output_tokens"], 0)
        self.assertEqual(bad[0]["generation_id"], "gen-1")

    def test_annotated_history_gets_the_same_retry(self) -> None:
        """It bypasses score_chunk with its own call path, so it is pinned
        separately. The fixture yields four intervals; the first reply is
        empty, so five calls is one retry plus four scores."""
        client = RecordingClient(replies=[EMPTY, OK, OK, OK, OK])
        result = run("annotated-history", request(make_interval_events()), client)
        self.assertEqual(client.calls, 5)
        self.assertEqual(result.score, 3)


if __name__ == "__main__":
    unittest.main()

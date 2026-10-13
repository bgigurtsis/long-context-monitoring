"""Native Codex generation and monitor-format regression tests."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from long_context_monitoring.generate_transcript import codex_session, delivery
from long_context_monitoring.generate_transcript.live import transcript_provenance
from long_context_monitoring.monitor.events import extract_events
from long_context_monitoring.monitor.visibility import apply_visibility
from long_context_monitoring.transcript.trajectory import Trajectory


def codex_entry(kind: str, payload: dict) -> dict:
    return {"timestamp": "2026-08-09T00:00:00Z", "type": kind, "payload": payload}


class CodexFixture:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "transcript"
        self.root.mkdir()
        entries = [
            codex_entry("session_meta", {"id": "thread-1", "cli_version": "0.145.0"}),
            codex_entry("turn_context", {"turn_id": "t1", "model": "gpt-test"}),
            codex_entry("response_item", {
                "type": "message", "id": "u1", "role": "user",
                "content": [{"type": "input_text", "text": "Turn one."}],
            }),
            codex_entry("response_item", {
                "type": "custom_tool_call", "id": "c1", "call_id": "call-1",
                "name": "exec", "input": "{\"cmd\":\"pytest\"}",
            }),
            codex_entry("response_item", {
                "type": "custom_tool_call_output", "id": "o1",
                "call_id": "call-1", "output": "2 passed",
            }),
            codex_entry("compacted", {
                "message": "Keep the tested implementation and continue.",
                "replacement_history": [
                    {"type": "message", "id": "u1", "role": "user", "content": []},
                    {"type": "message", "id": "secret", "role": "developer",
                     "content": [{"type": "input_text", "text": "SECRET_SIDE_TASK"}]},
                ],
                "window_number": 2, "window_id": "window-2",
            }),
            codex_entry("event_msg", {"type": "context_compacted"}),
            codex_entry("turn_context", {"turn_id": "t2", "model": "gpt-test"}),
            codex_entry("response_item", {
                "type": "message", "id": "u2", "role": "user",
                "content": [{"type": "input_text", "text": "Turn two."}],
            }),
            codex_entry("response_item", {
                "type": "message", "id": "a2", "role": "assistant",
                "content": [{"type": "output_text", "text": "Done."}],
            }),
        ]
        path = self.root / "rollout-thread-1.jsonl"
        path.write_text("".join(json.dumps(item) + "\n" for item in entries), encoding="utf-8")

    def close(self) -> None:
        self.temp.cleanup()


class CodexMonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = CodexFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_native_events_keep_summary_but_never_developer_history(self) -> None:
        trajectory = Trajectory(self.fixture.root)
        events = extract_events(trajectory)
        self.assertIn("compaction", [event.kind for event in events])
        summaries = [event.text for event in events if event.kind == "compaction_summary"]
        self.assertEqual(summaries, ["Keep the tested implementation and continue."])
        self.assertNotIn("SECRET_SIDE_TASK", "\n".join(event.text for event in events))

        visible = apply_visibility(events, "tools-only")
        self.assertIn("exec", [event.tool_name for event in visible])
        self.assertNotIn("Turn one.", "\n".join(event.text for event in visible))

        analysis = trajectory.analysis()
        self.assertEqual(analysis["models"], ["gpt-test"])
        self.assertEqual(len(analysis["boundaries"]), 1)
        self.assertEqual(analysis["boundaries"][0]["summary_line"], 5)

    def test_provenance_pairs_configured_manual_boundary(self) -> None:
        spec = {
            "host_turns": [
                {"id": 1, "prompt": "Turn one."},
                {"id": 2, "prompt": "Turn two."},
            ],
            "compaction_mode": "manual",
            "configured_compact_after": [1],
        }
        segments = [delivery.Segment(
            label="turn 1 through turn 2", start_turn=1,
            messages=[("turn 1", "Turn one."), ("compaction after turn 1", "/compact"),
                      ("turn 2", "Turn two.")],
        )]
        path = next(self.fixture.root.glob("*.jsonl"))
        boundaries, records, activations = transcript_provenance(
            path, spec, segments, "gpt-test", "high", "codex"
        )
        self.assertEqual([item["trigger"] for item in boundaries], ["manual"])
        self.assertEqual(records[0]["argv"][:3], ["codex", "app-server", "--stdio"])
        self.assertEqual(activations, [])


class FakeAppServer:
    def __init__(self, workspace: Path, codex_home: Path):
        self.requests: list[tuple[str, dict]] = []
        self.turn = 0

    def request(self, method: str, params: dict) -> dict:
        self.requests.append((method, params))
        if method == "thread/start":
            return {"thread": {"id": "thread-1"}, "model": "gpt-test"}
        if method == "turn/start":
            self.turn += 1
            return {"turn": {"id": f"turn-{self.turn}"}}
        return {}

    def wait_notification(self, method: str | tuple[str, ...], predicate=None) -> dict:
        if method == "turn/completed":
            value = {"turn": {"id": f"turn-{self.turn}", "status": "completed"}}
        else:
            value = {"threadId": "thread-1", "turnId": "compact-turn-1"}
        if predicate is not None:
            assert predicate(value)
        return value

    def close(self) -> None:
        pass


class FakeModernCompactionAppServer(FakeAppServer):
    def wait_notification(self, method: str | tuple[str, ...], predicate=None) -> dict:
        if method == "turn/completed":
            return super().wait_notification(method, predicate)
        assert method == ("thread/compacted", "item/completed")
        value = {
            "threadId": "thread-1",
            "turnId": "compact-turn-1",
            "item": {"id": "compact-item-1", "type": "contextCompaction"},
        }
        if predicate is not None:
            assert predicate(value)
        return value


class RecordingAppServer(FakeAppServer):
    """Test double that retains the one server created by the driver."""

    instances: list["RecordingAppServer"] = []

    def __init__(self, workspace: Path, codex_home: Path):
        super().__init__(workspace, codex_home)
        type(self).instances.append(self)


class CodexDriverTests(unittest.TestCase):
    def test_only_manual_mode_raises_the_automatic_compaction_limit(self) -> None:
        workspace = Path("/tmp/example-workspace")
        manual = codex_session._thread_params(
            workspace, "gpt-test", "manual"
        )
        automatic = codex_session._thread_params(
            workspace, "gpt-test", "automatic"
        )
        self.assertEqual(
            manual["config"]["model_auto_compact_token_limit"], 1_000_000_000
        )
        self.assertNotIn("model_auto_compact_token_limit", automatic["config"])

    def test_manual_compaction_is_protocol_operation_not_user_prompt(self) -> None:
        segment = delivery.Segment(
            label="all turns", start_turn=1,
            messages=[("turn 1", "one"), ("compaction after turn 1", "/compact"),
                      ("turn 2", "two")],
        )
        completed: list[int] = []
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            codex_session, "AppServer", FakeAppServer
        ):
            observed = codex_session.drive_segments(
                [segment], 0, Path(tmp), None,
                lambda count, _session: completed.append(count),
                "gpt-test", "manual", "high", Path(tmp) / "codex-home",
            )
        self.assertEqual(observed["session_id"], "thread-1")
        self.assertEqual(completed, [1, 2, 3])

    def test_manual_compaction_accepts_modern_item_completion(self) -> None:
        segment = delivery.Segment(
            label="all turns", start_turn=1,
            messages=[("turn 1", "one"), ("compaction after turn 1", "/compact"),
                      ("turn 2", "two")],
        )
        completed: list[int] = []
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            codex_session, "AppServer", FakeModernCompactionAppServer
        ):
            observed = codex_session.drive_segments(
                [segment], 0, Path(tmp), None,
                lambda count, _session: completed.append(count),
                "gpt-test", "manual", "high", Path(tmp) / "codex-home",
            )
        self.assertEqual(observed["session_id"], "thread-1")
        self.assertEqual(completed, [1, 2, 3])

    def test_resumed_segments_do_not_add_hidden_instructions(self) -> None:
        segments = [
            delivery.Segment(
                label="turn 1", start_turn=1,
                messages=[("turn 1", "one")],
            ),
            delivery.Segment(
                label="turn 2", start_turn=2,
                messages=[("turn 2", "two")],
                resume_required=True,
            ),
        ]
        RecordingAppServer.instances = []
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            codex_session, "AppServer", RecordingAppServer
        ):
            observed = codex_session.drive_segments(
                segments, 0, Path(tmp), None, lambda _count, _session: None,
                "gpt-test", "manual", "high", Path(tmp) / "codex-home",
            )
        self.assertEqual(observed["session_id"], "thread-1")
        self.assertEqual(len(RecordingAppServer.instances), 1)
        requests = RecordingAppServer.instances[0].requests
        self.assertEqual(
            requests[0],
            (
                "thread/start",
                mock.ANY,
            ),
        )
        self.assertNotIn("developerInstructions", requests[0][1])
        self.assertEqual(requests[2][0], "thread/resume")
        self.assertNotIn("developerInstructions", requests[2][1])
        self.assertNotIn("collaborationMode", requests[3][1])
        self.assertNotIn(
            "developer-instructions",
            " ".join(codex_session.redacted_invocation(
                "thread-1", "gpt-test", "high"
            )),
        )

    def test_manual_compaction_ignores_unrelated_completed_items(self) -> None:
        server = object.__new__(codex_session.AppServer)
        unrelated = {
            "method": "item/completed",
            "params": {
                "threadId": "thread-1",
                "turnId": "compact-turn-1",
                "item": {"id": "reasoning-1", "type": "reasoning"},
            },
        }
        server.pending = [
            unrelated,
            {
                "method": "item/completed",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "compact-turn-1",
                    "item": {
                        "id": "compact-item-1",
                        "type": "contextCompaction",
                    },
                },
            },
        ]
        server.request = mock.Mock(return_value={})
        server._read_fresh = mock.Mock(
            side_effect=AssertionError("queued completion should be sufficient")
        )

        codex_session._compact(server, "thread-1", "compaction after turn 1")

        server.request.assert_called_once_with(
            "thread/compact/start", {"threadId": "thread-1"}
        )
        self.assertEqual(server.pending, [unrelated])


if __name__ == "__main__":
    unittest.main()

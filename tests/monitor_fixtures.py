"""Monitor fixtures."""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
from long_context_monitoring.transcript.trajectory import Trajectory


def entry(entry_type: str, uuid: str, content=None, **extra) -> dict:
    value = {
        "type": entry_type,
        "uuid": uuid,
        "sessionId": "session-mon",
        "timestamp": "2026-07-17T10:00:00Z",
        **extra,
    }
    if content is not None:
        value["message"] = {"content": content}
    return value


HUGE_RESULT = "R" * 6000


class MonitorFixture:
    """A synthetic archive dir: main JSONL + one sub-agent + manifest.

    Exercises block splitting (a text + two tool_use blocks in one entry), a
    huge tool result, an Agent spawn linked to a sub-agent file, a compaction
    boundary that drops earlier entries from live context, and the following
    isCompactSummary entry.
    """

    def __init__(self, dir_: str | None = None) -> None:
        # Default to the system temp dir (honours TMPDIR) so this works both in
        # a sandbox and on a normal checkout.
        self.temp = tempfile.TemporaryDirectory(dir=dir_)
        self.root = Path(self.temp.name) / "widget-run"
        self.root.mkdir()
        self.subagents = self.root / "subagents"
        self.subagents.mkdir()

        main = [
            {"type": "queue-operation", "sessionId": "session-mon"},
            entry("user", "u1", "Please build the widget and run its tests."),
            entry(
                "assistant",
                "a1",
                [
                    {"type": "text", "text": "Starting on the widget."},
                    {
                        "type": "tool_use",
                        "id": "bash-1",
                        "name": "Bash",
                        "input": {"command": "ls -la"},
                    },
                    {
                        "type": "tool_use",
                        "id": "read-1",
                        "name": "Read",
                        "input": {"file_path": "/app/widget.py"},
                    },
                ],
            ),
            entry(
                "user",
                "r-bash",
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": "bash-1",
                        "content": "app.py",
                    }
                ],
            ),
            entry(
                "user",
                "r-read",
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": "read-1",
                        "content": HUGE_RESULT,
                    }
                ],
            ),
            entry(
                "assistant",
                "a2",
                [
                    {
                        "type": "tool_use",
                        "id": "spawn-1",
                        "name": "Agent",
                        "input": {
                            "description": "inspect tests",
                            "subagent_type": "general-purpose",
                            "prompt": "Go inspect the test suite.",
                        },
                    }
                ],
            ),
            entry(
                "user",
                "r-spawn",
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": "spawn-1",
                        "content": "sub-agent done",
                    }
                ],
                toolUseResult={"agentId": "one"},
            ),
            entry(
                "system",
                "cb",
                None,
                subtype="compact_boundary",
                compactMetadata={
                    "trigger": "auto",
                    "preTokens": 5000,
                    "postTokens": 900,
                    "preservedMessages": {"uuids": ["u1"]},
                },
            ),
            entry(
                "user",
                "cs",
                "This session is being continued. Summary of prior work.",
                isCompactSummary=True,
            ),
            entry(
                "assistant",
                "a3",
                [
                    {
                        "type": "thinking",
                        "thinking": "internal reasoning, hidden from tools view",
                    },
                    {"type": "text", "text": "All done."},
                ],
            ),
        ]
        self._write_jsonl(self.root / "session-mon.jsonl", main)

        agent_one = [
            entry(
                "user",
                "s0",
                "Working directory: /app\nInspect the test suite.",
                isSidechain=True,
                agentId="one",
            ),
            entry(
                "assistant",
                "s1",
                [
                    {
                        "type": "tool_use",
                        "id": "sb-1",
                        "name": "Bash",
                        "input": {"command": "pytest -q"},
                    }
                ],
                isSidechain=True,
                agentId="one",
            ),
            entry(
                "user",
                "sr1",
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": "sb-1",
                        "content": "2 passed",
                    }
                ],
                isSidechain=True,
                agentId="one",
            ),
        ]
        self._write_agent(
            "one",
            agent_one,
            {
                "toolUseId": "spawn-1",
                "agentType": "Explore",
                "description": "inspect tests",
                "spawnDepth": 1,
            },
        )

        self.manifest = {
            "task_id": "widget-run",
            "prompts": ["Please build the widget and run its tests."],
            "claude_version": "2.1.212 (Claude Code)",
        }
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))

    @staticmethod
    def _write_jsonl(path: Path, entries: list[dict]) -> None:
        path.write_text(
            "\n".join(json.dumps(e, separators=(",", ":")) for e in entries) + "\n"
        )

    def _write_agent(self, agent_id: str, entries: list[dict], meta: dict) -> None:
        path = self.subagents / f"agent-{agent_id}.jsonl"
        self._write_jsonl(path, entries)
        path.with_suffix(".meta.json").write_text(json.dumps(meta))

    def trajectory(self) -> Trajectory:
        return Trajectory(self.root)

    def close(self) -> None:
        self.temp.cleanup()


class FakeLLMClient:
    """A scriptable stand-in for OpenRouterClient — records calls, returns
    programmed replies. ``replies`` may be strings or Exceptions (raised).
    """

    def __init__(self, replies: list) -> None:
        self.replies = list(replies)
        self.calls: list[dict] = []

    def complete(
        self,
        user: str,
        model: str,
        max_tokens: int = 2000,
        temperature: float = 0.0,
        reasoning_effort=None,
        response_format=None,
        provider=None,
    ):
        from long_context_monitoring.monitor.llm import LLMResponse

        self.calls.append(
            {
                "user": user,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "reasoning_effort": reasoning_effort,
                "provider": provider,
            }
        )
        reply = self.replies[len(self.calls) - 1]
        if isinstance(reply, Exception):
            raise reply
        requested = (provider or {}).get("order") or []
        observed_provider = (
            str(requested[0]).split("/", 1)[0] if requested else "Anthropic"
        )
        return LLMResponse(
            text=reply,
            model=model,
            input_tokens=len(user) // 4,
            output_tokens=len(reply) // 4,
            generation_id=f"gen-{len(self.calls)}",
            provider=observed_provider,
        )


REPLY = "<reasoning>looks fine</reasoning>\n<score>2</score>"


def make_tool_results(
    n: int, chars: int = 600, marker_at: int | None = None, marker: str = "MARKER"
) -> list:
    """Uniform tool_result events (no Action numbering) for chunking tests."""
    from long_context_monitoring.monitor.events import Event

    events = []
    for i in range(n):
        text = "X" * chars
        if marker_at is not None and i == marker_at:
            text = marker + "X" * chars
        events.append(
            Event(
                kind="tool_result",
                event_id=f"main:L{i}:0",
                file_id="main",
                line=i,
                depth=0,
                text=text,
                tool_use_id=f"t{i}",
            )
        )
    return events


def make_request(events: list, **overrides):
    from long_context_monitoring.monitor.render import RenderOptions
    from long_context_monitoring.monitor.strategies.base import MonitorRequest

    params = dict(
        events=events,
        transcript_name="synthetic",
        task_description="do the task",
        visibility="tools-only",
        render_options=RenderOptions(),
        model="anthropic/claude-sonnet-5",
    )
    params.update(overrides)
    return MonitorRequest(**params)


def make_three_view_events() -> list:
    """Minimal setup/compaction/execution trajectory for three-view tests."""
    from long_context_monitoring.monitor.events import Event

    return [
        Event(
            kind="human_prompt",
            event_id="main:L1:0",
            file_id="main",
            line=1,
            depth=0,
            text="Do the task.",
        ),
        Event(
            kind="tool_call",
            event_id="main:L2:0",
            file_id="main",
            line=2,
            depth=0,
            text='{"command": "SETUP"}',
            tool_name="Bash",
            tool_use_id="setup",
        ),
        Event(
            kind="compaction",
            event_id="main:L3:0",
            file_id="main",
            line=3,
            depth=0,
            text="Context compacted.",
        ),
        Event(
            kind="compaction_summary",
            event_id="main:L4:0",
            file_id="main",
            line=4,
            depth=0,
            text="Summary carrying prior state.",
        ),
        Event(
            kind="tool_call",
            event_id="main:L5:0",
            file_id="main",
            line=5,
            depth=0,
            text='{"command": "EXECUTION"}',
            tool_name="Bash",
            tool_use_id="execution",
        ),
    ]


def make_interval_events() -> list:
    """Three main boundaries plus one sub-agent boundary that must not split."""
    from long_context_monitoring.monitor.events import Event

    events = [
        Event(
            kind="human_prompt",
            event_id="main:L1:0",
            file_id="main",
            line=1,
            depth=0,
            text="Do the task.",
        ),
        Event(
            kind="tool_call",
            event_id="main:L2:0",
            file_id="main",
            line=2,
            depth=0,
            text='{"command": "SETUP"}',
            tool_name="Bash",
            tool_use_id="setup",
        ),
        Event(
            kind="compaction",
            event_id="main:L3:0",
            file_id="main",
            line=3,
            depth=0,
            text="Boundary one.",
        ),
        Event(
            kind="compaction_summary",
            event_id="main:L4:0",
            file_id="main",
            line=4,
            depth=0,
            text="SUMMARY_ONE",
        ),
        Event(
            kind="tool_call",
            event_id="main:L5:0",
            file_id="main",
            line=5,
            depth=0,
            text='{"command": "MIDDLE_ONE"}',
            tool_name="Bash",
            tool_use_id="middle-one",
        ),
        Event(
            kind="compaction",
            event_id="agent-a:L2:0",
            file_id="agent-a",
            line=2,
            depth=1,
            text="Sub-agent boundary.",
        ),
        Event(
            kind="compaction",
            event_id="main:L6:0",
            file_id="main",
            line=6,
            depth=0,
            text="Boundary two.",
        ),
        Event(
            kind="compaction_summary",
            event_id="main:L7:0",
            file_id="main",
            line=7,
            depth=0,
            text="SUMMARY_TWO",
        ),
        Event(
            kind="tool_call",
            event_id="main:L8:0",
            file_id="main",
            line=8,
            depth=0,
            text='{"command": "MIDDLE_TWO"}',
            tool_name="Bash",
            tool_use_id="middle-two",
        ),
        Event(
            kind="compaction",
            event_id="main:L9:0",
            file_id="main",
            line=9,
            depth=0,
            text="Boundary three.",
        ),
        Event(
            kind="compaction_summary",
            event_id="main:L10:0",
            file_id="main",
            line=10,
            depth=0,
            text="SUMMARY_THREE",
        ),
        Event(
            kind="tool_call",
            event_id="main:L11:0",
            file_id="main",
            line=11,
            depth=0,
            text='{"command": "END"}',
            tool_name="Bash",
            tool_use_id="end",
        ),
    ]
    return events

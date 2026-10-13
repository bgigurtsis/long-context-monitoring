"""Characterize cycle guards and last-result indexing before traversal changes."""

from long_context_monitoring.monitor.events import extract_events
from tests.event_extraction_support import ParsedTrajectory


def row(kind, block, line, **metadata):
    return {
        "entry": {"type": kind, "message": {"content": [block]}},
        "line": line,
        "turn": 1,
        **metadata,
    }


def cycle_fixture():
    def result(identity, text):
        return {"type": "tool_result", "tool_use_id": identity, "content": text}

    def spawn(identity):
        return {
            "type": "tool_use",
            "name": "Agent",
            "id": identity,
            "input": {"prompt": "task"},
        }

    files = {
        "main": [
            row("user", result("spawn", "early"), 0),
            row("assistant", spawn("spawn"), 1),
            row("user", result("spawn", "last"), 2, dropped=True),
            row("user", result("spawn", "duplicate"), 3, duplicate=True),
        ],
        "child": [
            row("assistant", spawn("back"), 0),
            row("user", result("back", "returned"), 1),
        ],
        "orphan": [row("assistant", {"type": "text", "text": "unlinked"}, 0)],
    }
    agents = [
        {
            "id": "child",
            "toolUseId": "spawn",
            "parent_file": "main",
            "agentType": "Explore",
        },
        {"id": "main", "toolUseId": "back", "parent_file": "child"},
        {"id": "orphan", "description": "loose", "parent_file": None},
    ]
    return ParsedTrajectory(files, agents)


def test_cycle_and_orphan_order_keeps_early_and_last_results_distinct():
    events = extract_events(cycle_fixture())
    assert [
        (event.event_id, event.kind, event.text, event.depth) for event in events
    ] == [
        ("main:L0:0", "tool_result", "early", 0),
        ("main:L1:0", "agent_spawn", "task", 0),
        ("child:L0:0", "agent_spawn", "task", 1),
        ("child:L1:agent", "agent_return", "returned", 1),
        ("main:L2:agent", "agent_return", "last", 0),
        ("orphan:orphan", "agent_spawn", "", 0),
        ("orphan:L0:0", "assistant_text", "unlinked", 1),
    ]
    assert events[4].dropped is True
    assert events[4].agent_type == "Explore"


def test_main_only_still_pairs_agent_results_without_descending():
    events = extract_events(cycle_fixture(), include_agents=False)
    assert [event.event_id for event in events] == [
        "main:L0:0",
        "main:L1:0",
        "main:L2:agent",
    ]

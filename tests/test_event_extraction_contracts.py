"""Pin native history redaction, cumulative compaction, and child append order."""

from long_context_monitoring.monitor.events import extract_events
from tests.event_extraction_support import ParsedTrajectory, codex_rows


def test_codex_dropped_ids_remain_cumulative_and_children_follow_main():
    main = codex_rows(
        [
            ("session_meta", {}),
            ("turn_context", {}),
            (
                "response_item",
                {
                    "id": "a",
                    "type": "message",
                    "role": "assistant",
                    "content": "before",
                },
            ),
            (
                "response_item",
                {
                    "id": "spawn",
                    "type": "function_call",
                    "namespace": "collaboration",
                    "name": "spawn_agent",
                    "call_id": "s",
                    "arguments": '{"task_name":"child"}',
                },
            ),
            (
                "compacted",
                {"window_number": 1, "message": "first", "replacement_history": []},
            ),
            (
                "compacted",
                {
                    "window_number": 2,
                    "message": "second",
                    "replacement_history": [{"id": "a"}],
                },
            ),
            (
                "response_item",
                {"type": "message", "role": "developer", "content": "hidden"},
            ),
            ("response_item", {"type": "agent_message", "message": "main end"}),
        ]
    )
    child = codex_rows(
        [
            (
                "response_item",
                {
                    "type": "reasoning",
                    "summary": [{"type": "summary_text", "text": "reason"}],
                },
            )
        ]
    )
    events = extract_events(ParsedTrajectory({"main": main, "child": child}))
    assert events[0].dropped is True
    assert events[1].tool_name == "collaboration.spawn_agent"
    assert events[1].agent_description == "child"
    assert [event.text for event in events[-3:]] == ["main end", "", "reason"]
    assert events[-2].event_id == "child:native"
    assert events[-1].depth == 1
    assert "hidden" not in [event.text for event in events]


def test_codex_custom_calls_preserve_non_json_input_and_structured_output():
    entries = codex_rows(
        [
            ("session_meta", {}),
            (
                "response_item",
                {
                    "type": "custom_tool_call",
                    "name": "exec",
                    "input": "not json",
                    "call_id": "c",
                },
            ),
            (
                "response_item",
                {
                    "type": "custom_tool_call_output",
                    "call_id": "c",
                    "output": [{"type": "image"}, 3, {"type": "text", "text": "done"}],
                },
            ),
        ]
    )
    events = extract_events(ParsedTrajectory({"main": entries}), include_agents=False)
    assert [(event.kind, event.text, event.turn) for event in events] == [
        ("tool_call", "not json", None),
        ("tool_result", "[image block]\n3\ndone", None),
    ]


def _codex_output(call_id: str, output):
    return ("response_item", {"type": "custom_tool_call_output", "call_id": call_id,
                              "output": output})


def test_codex_input_text_tool_output_is_rendered_not_footnoted():
    entries = codex_rows([
        ("session_meta", {}),
        ("response_item", {"type": "custom_tool_call", "name": "exec",
                           "input": "ls", "call_id": "c"}),
        _codex_output("c", [{"type": "input_text", "text": "Script completed"},
                            {"type": "input_text", "text": "a.py\nb.py"}]),
    ])
    events = extract_events(ParsedTrajectory({"main": entries}), include_agents=False)
    assert events[1].text == "Script completed\na.py\nb.py"


def test_codex_empty_compaction_summary_is_marked_and_counted():
    from long_context_monitoring.monitor.events import (
        EMPTY_COMPACTION_SUMMARY_TEXT, count_empty_compaction_summaries,
    )

    entries = codex_rows([
        ("session_meta", {}),
        ("response_item", {"id": "a", "type": "agent_message", "message": "x"}),
        ("compacted", {"window_number": 1, "message": "", "replacement_history": []}),
        ("compacted", {"window_number": 2, "message": "kept", "replacement_history": []}),
    ])
    events = extract_events(ParsedTrajectory({"main": entries}), include_agents=False)
    summaries = [e.text for e in events if e.kind == "compaction_summary"]
    assert summaries == [EMPTY_COMPACTION_SUMMARY_TEXT, "kept"]
    assert count_empty_compaction_summaries(events) == 1


def test_codex_child_is_inlined_at_its_spawn_result():
    main = codex_rows([
        ("session_meta", {}),
        ("response_item", {"type": "function_call", "namespace": "collaboration",
                           "name": "spawn_agent", "call_id": "s",
                           "arguments": '{"task_name":"review"}'}),
        ("response_item", {"type": "function_call_output", "call_id": "s",
                           "output": '{"task_name":"/root/review"}'}),
        ("response_item", {"type": "agent_message", "message": "main end"}),
    ])
    child = codex_rows([
        ("session_meta", {}),
        # A forked child starts with the parent's history as a ``compacted`` row.
        ("compacted", {"window_number": 0, "message": "", "replacement_history": []}),
        ("response_item", {"type": "custom_tool_call", "name": "exec",
                           "input": "pytest", "call_id": "k"}),
        _codex_output("k", "ok"),
        ("response_item", {"type": "agent_message", "message": "child end"}),
    ])
    trajectory = ParsedTrajectory({"main": main, "/root/review": child})
    events = extract_events(trajectory)
    kinds = [(e.kind, e.depth, e.text) for e in events]
    assert kinds == [
        ("agent_spawn", 0, '{"task_name": "review"}'),
        ("tool_call", 1, "pytest"),
        ("tool_result", 1, "ok"),
        ("assistant_text", 1, "child end"),
        ("agent_return", 0, '{"task_name":"/root/review"}'),
        ("assistant_text", 0, "main end"),
    ]
    assert events[4].agent_type == "Codex"
    assert not any(e.event_id.endswith(":native") for e in events)


def test_codex_injected_user_parts_are_not_the_human_prompt():
    entries = codex_rows([
        ("session_meta", {}),
        ("response_item", {"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": "<recommended_plugins> list </recommended_plugins>"},
            {"type": "input_text", "text": "# AGENTS.md instructions for /x\n- rule"},
            {"type": "input_text", "text": "<environment_context>cwd</environment_context>"},
            {"type": "input_text", "text": "Please fix the flaky test."},
        ]}),
    ])
    events = extract_events(ParsedTrajectory({"main": entries}), include_agents=False)
    assert [(e.kind, e.text) for e in events] == [("human_prompt", "Please fix the flaky test.")]

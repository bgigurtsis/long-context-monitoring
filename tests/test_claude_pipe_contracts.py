"""Freeze child protocol completion and failure handling without starting a CLI."""

import io
import json
from unittest.mock import Mock

import pytest

from long_context_monitoring.generate_transcript import session


@pytest.mark.parametrize(
    "outcome", ["completed", "error", "early-exit", "missing-init"]
)
def test_pipe_protocol_stops_after_final_result(tmp_path, monkeypatch, outcome):
    entries = (
        []
        if outcome == "missing-init"
        else [
            {
                "type": "system",
                "subtype": "init",
                "session_id": "native",
                "model": "model",
            }
        ]
    )
    if outcome != "early-exit":
        entries.append(
            {"type": "result", "is_error": outcome == "error", "result": "failure"}
        )
    entries.append({"type": "assistant", "message": {"model": "trailing"}})
    process = Mock(
        stdout=io.StringIO("chatter\n" + "\n".join(map(json.dumps, entries))),
        stderr=io.StringIO("diagnostic\n"),
    )
    process.wait.return_value = 7
    monkeypatch.setattr(session.subprocess, "Popen", Mock(return_value=process))
    # Drain synchronously to make queue order deterministic; exercise the actual drain bodies.
    monkeypatch.setattr(
        session.threading, "Thread", lambda target, daemon: Mock(start=target)
    )
    monkeypatch.setattr(session, "session_env", Mock(return_value={}))
    completed, initialized = Mock(), Mock()
    errors = {
        "error": "turn one errored",
        "early-exit": "claude exited.*unsent.*diagnostic",
        "missing-init": "never saw an init",
    }
    if outcome in errors:
        with pytest.raises(session.SessionError, match=errors[outcome]):
            session.drive(
                [],
                tmp_path,
                [("turn one", "text")],
                completed,
                on_session_initialized=initialized,
            )
    else:
        assert session.drive(
            [],
            tmp_path,
            [("turn one", "text")],
            completed,
            on_session_initialized=initialized,
        ) == {"session_id": "native", "policy_model": "model", "compaction_model": None}
        completed.assert_called_once_with(1, "native")
        initialized.assert_called_once_with("native")
        process.stdin.close.assert_called_once_with()
    process.stdin.write.assert_called_once_with(
        json.dumps({"type": "user", "message": {"role": "user", "content": "text"}})
        + "\n"
    )

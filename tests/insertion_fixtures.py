"""Manual pair fixtures."""

from __future__ import annotations
from pathlib import Path
from long_context_monitoring.attack_lab.edits import FunctionEdit
from long_context_monitoring.pair_workflow.models import InlineAction
from long_context_monitoring.openrouter import LLMResponse


class FakeCompactor:
    """Return a distinct valid neutral summary for each cache miss."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(
        self,
        user: str,
        model: str,
        max_tokens: int = 20_000,
        temperature: float = 0.0,
        reasoning_effort: str | None = None,
        provider: dict[str, object] | None = None,
    ) -> LLMResponse:
        self.calls += 1
        text = (
            "<analysis>covered</analysis>"
            f"<summary>cached summary {self.calls}</summary>"
        )
        requested = (provider or {}).get("order") or []
        observed = str(requested[0]).split("/", 1)[0] if requested else None
        return LLMResponse(text, model, 100, 20, provider=observed)


def _user(uuid: str, text: str, *, compact: bool = False) -> dict:
    entry = {
        "type": "user",
        "uuid": uuid,
        "message": {"role": "user", "content": text},
    }
    if compact:
        entry["isCompactSummary"] = True
    return entry


def _assistant(uuid: str, text: str) -> dict:
    return {
        "type": "assistant",
        "uuid": uuid,
        "message": {
            "id": f"msg-{uuid}",
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
        },
    }


def _boundary(uuid: str) -> dict:
    return {
        "type": "system",
        "subtype": "compact_boundary",
        "uuid": uuid,
    }


def _spec() -> dict:
    return {
        "host_turns": [
            {"id": 1, "prompt": "Host turn one."},
            {"id": 2, "prompt": "Host turn two."},
            {"id": 3, "prompt": "Host turn three."},
        ],
        "configured_compact_after": [1, 2],
    }


def _entries() -> list[dict]:
    return [
        _user("u1", "Host turn one."),
        _assistant("a1", "Finished one."),
        _boundary("b1"),
        _user("s1", "Old honest summary one.", compact=True),
        _user("u2", "Host turn two."),
        _assistant("a2", "Finished two."),
        _boundary("b2"),
        _user("s2", "Old honest summary two.", compact=True),
        _user("u3", "Host turn three."),
        _assistant("a3", "Finished three."),
    ]


def _actions() -> list[InlineAction]:
    return [
        InlineAction(
            turn=1,
            when="after_host_turn",
            edit=FunctionEdit(
                path="package/helper.py",
                function="setup_value",
                expected_signature="def setup_value() -> str:",
                replacement="def setup_value() -> str:\n    return 'a'\n",
            ),
        ),
        InlineAction(
            turn=3,
            when="before_host_turn",
            edit=FunctionEdit(
                path="package/helper.py",
                function="execute_value",
                expected_signature="def execute_value() -> str:",
                replacement="def execute_value() -> str:\n    return 'b'\n",
            ),
        ),
    ]


class WorkspaceFixture:
    def _workspace(self, root: Path) -> Path:
        workspace = root / "workspace"
        target = workspace / "package" / "helper.py"
        target.parent.mkdir(parents=True)
        target.write_text(
            "def setup_value() -> str:\n"
            "    return 'safe-a'\n\n"
            "def execute_value() -> str:\n"
            "    return 'safe-b'\n",
            encoding="utf-8",
        )
        return workspace

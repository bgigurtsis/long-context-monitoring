"""Resolve honest artifacts, fingerprint sources, and read exact edit registrations."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from long_context_monitoring.artifact_layout import evidence_file
from typing import Sequence
from long_context_monitoring.attack_lab.edits import FunctionEdit, apply_function_edit
from long_context_monitoring.generate_transcript.native_session import main_jsonl, read_jsonl
from long_context_monitoring.generate_transcript.side_task import manual_edit_schedule
from .models import ManualPairError, HonestSource, InlineAction


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()






def _write_jsonl(path: Path, entries: Sequence[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries),
        encoding="utf-8",
    )


def _loaded_entries(path: Path) -> list[dict]:
    try:
        _lines, entries = read_jsonl(path)
    except (OSError, ValueError) as error:
        raise ManualPairError(str(error)) from error
    return [dict(entry) for entry in entries]


def _resolve_honest_source(raw: Path, resolve_path) -> HonestSource:
    """Resolve an honest arm directory with one transcript and workspace."""

    arm = resolve_path(raw)
    workspace = arm / "workspace"
    if not workspace.is_dir():
        raise ManualPairError(f"honest source has no workspace directory: {workspace}")
    manifest_path = evidence_file(arm, "manifest.json")
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ManualPairError(f"could not read honest manifest: {error}") from error
        if manifest.get("condition") != "honest":
            raise ManualPairError(
                f"source manifest is not an honest arm: {manifest_path}"
            )
        transcript_format = manifest.get("transcript_format")
        supported_formats = {
            "claude-native-jsonl",
            "constructed-claude-jsonl",
        }
        if transcript_format not in supported_formats:
            raise ManualPairError(
                "manual pairs require a Claude-shaped honest transcript; "
                f"got {transcript_format!r}"
            )
    direct = arm / "transcript.jsonl"
    if direct.is_file():
        transcript = direct
    else:
        transcript_dir = arm / "transcript"
        session_id = manifest.get("session_id") if manifest_path.is_file() else None
        if isinstance(session_id, str) and session_id:
            transcript = transcript_dir / f"{session_id}.jsonl"
            if not transcript.is_file() or transcript.stat().st_size == 0:
                raise ManualPairError(
                    f"manifest-selected honest transcript {session_id!r} is unavailable"
                )
        else:
            try:
                transcript = main_jsonl(transcript_dir)
            except (OSError, ValueError) as error:
                raise ManualPairError(str(error)) from error
    return HonestSource(arm=arm, transcript=transcript, workspace=workspace)


def inline_actions(spec: dict) -> list[InlineAction]:
    """Load the two registered edits from one structured side task."""

    side_task = spec.get("side_task")
    if not isinstance(side_task, dict):
        raise ManualPairError("manual pairs require a structured side_task")
    scheduled = manual_edit_schedule(side_task)
    if len(scheduled) != 2:
        raise ManualPairError(
            f"manual pairs require exactly two inline edits; found {len(scheduled)}"
        )
    actions: list[InlineAction] = []
    for turn, raw in scheduled:
        actions.append(
            InlineAction(
                turn=turn,
                when=raw["when"],
                edit=FunctionEdit(
                    path=raw["path"],
                    function=raw["function"],
                    expected_signature=raw["expected_signature"],
                    replacement=raw["replacement"],
                ),
            )
        )
    return actions


def _apply_selected_actions(
    source: Path, destination: Path, actions: Sequence[InlineAction]
) -> None:
    shutil.copytree(source, destination)
    for action in actions:
        apply_function_edit(destination, action.edit)

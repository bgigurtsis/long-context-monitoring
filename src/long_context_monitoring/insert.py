"""Construct an attack copy without generating an attack policy session."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import tempfile

from long_context_monitoring.attack_lab.edits import apply_function_edit
from long_context_monitoring.env import load_dotenv
from long_context_monitoring.generate_transcript.specification import load_spec
from long_context_monitoring.generate_transcript.side_task import SpecError
from long_context_monitoring.generate_transcript.session import SessionError
from long_context_monitoring.neutral_compactor import (
    COMPACTION_PROMPT_SHA256,
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    CompactionError,
    compactor_client,
)
from long_context_monitoring.openrouter import LLMError
from long_context_monitoring.pair_workflow.construction import _build_attack
from long_context_monitoring.pair_workflow.models import ManualPairError
from long_context_monitoring.pair_workflow.source import (
    _resolve_honest_source,
    _loaded_entries,
    _sha256_file,
    _sha256_tree,
    inline_actions,
)
from long_context_monitoring.run_layout import resolve_repo_path
from long_context_monitoring.pair_workflow.insertion import inject_manual_edits
from long_context_monitoring.pair_workflow.reconciliation import reconcile_native_entries


def prepare(spec_path: Path, honest_path: Path):
    """Validate the source and registered edits before a model call.
    Why: construction must use exact replacements against immutable honest work.
    If wrong: an attack could refer to a different source or incomplete edits.
    """
    spec = load_spec(spec_path, require_workspace=False)
    if spec["compaction_mode"] != "manual":
        raise ManualPairError("insertion requires explicit manual compaction boundaries")
    honest = _resolve_honest_source(honest_path, resolve_repo_path)
    actions = inline_actions(spec)
    with tempfile.TemporaryDirectory(prefix="lcm-insert-check-") as temporary:
        scratch = Path(temporary) / "workspace"
        shutil.copytree(honest.workspace, scratch)
        for action in actions:
            apply_function_edit(scratch, action.edit)
    entries = inject_manual_edits(_loaded_entries(honest.transcript), spec, actions, honest.workspace)
    reconcile_native_entries(entries)
    return spec, honest, actions


def construct(args: argparse.Namespace) -> dict:
    """Write a new attack directory and preserve the honest source.
    Why: the inserted transcript must remain tied to the exact honest records.
    If wrong: source changes would make the matched pair impossible to interpret.
    """
    spec, honest, actions = prepare(args.spec, args.honest)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    if output.is_relative_to(honest.arm.resolve()):
        raise ManualPairError("output cannot be inside the honest source")
    source_transcript_hash = _sha256_tree(honest.arm / "transcript")
    source_workspace_hash = _sha256_tree(honest.workspace)
    if args.dry_run:
        return {
            "host_turns": len(spec["host_turns"]),
            "compact_after": spec["configured_compact_after"],
            "edits": [{"turn": action.turn, "when": action.when,
                       "path": action.edit.path, "function": action.edit.function}
                      for action in actions],
            "output": str(output),
        }
    load_dotenv()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".lcm-insert-", dir=output.parent) as temporary:
        staged = Path(temporary) / "attack"
        transcript, workspace, compactions, replays = _build_attack(
            spec, honest, actions, staged, compactor_client("openrouter"),
            args.compact_model, args.compact_effort,
            args.cache_root, args.max_cost_usd,
        )
        # Child sessions are evidence and keep their original names and bytes.
        for child in (honest.arm / "transcript").iterdir():
            if child.is_dir():
                shutil.copytree(child, staged / "transcript" / child.name)
            elif child != honest.transcript and child.name != "manifest.json":
                shutil.copy2(child, staged / "transcript" / child.name)
        if (_sha256_tree(honest.arm / "transcript") != source_transcript_hash
                or _sha256_tree(honest.workspace) != source_workspace_hash):
            raise ManualPairError("honest evidence changed during construction")
        manifest = {
            "condition": "attack",
            "session_id": "constructed",
            "transcript_format": "constructed-claude-jsonl",
            "manual_insertion": True,
            "policy_generation_evidence": False,
            "compaction_mode": "manual",
            "compact_after": spec["configured_compact_after"],
            "prompts": [turn["prompt"] for turn in spec["host_turns"]],
            "source_transcript_sha256": source_transcript_hash,
            "source_workspace_sha256": source_workspace_hash,
            "transcript_sha256": _sha256_file(transcript),
            "workspace_sha256": _sha256_tree(workspace),
            "compaction_prompt_sha256": COMPACTION_PROMPT_SHA256,
            "edits": [{"turn": action.turn, "when": action.when,
                       "path": action.edit.path, "function": action.edit.function,
                       "expected_signature": action.edit.expected_signature}
                      for action in actions],
            "compactions": [asdict(record) for record in compactions],
            "source_replays": [asdict(record) for record in replays],
        }
        (staged / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        staged.rename(output)
    return {"output": str(output), "transcript_sha256": manifest["transcript_sha256"]}


def main(argv: list[str] | None = None) -> int:
    """Run insertion with an explicit source, destination, and cost limit."""
    parser = argparse.ArgumentParser(prog="lcm insert")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--honest", type=Path, required=True, help="honest arm directory")
    parser.add_argument("--output", type=Path, required=True, help="new attack arm directory")
    parser.add_argument("--compact-model", default=DEFAULT_MODEL)
    parser.add_argument("--compact-effort", default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--cache-root", type=Path, default=Path("outputs/compaction-cache"))
    parser.add_argument("--max-cost-usd", type=float, default=5.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.max_cost_usd <= 0:
        parser.error("--max-cost-usd must be positive")
    try:
        result = construct(args)
    except (ManualPairError, SpecError, SessionError, CompactionError, LLMError, OSError, ValueError) as error:
        parser.exit(2, f"lcm insert: {error}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

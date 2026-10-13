"""Generate one continuous honest native coding-agent session.

Nothing here edits a transcript. Claude Code session JSONL or Codex rollout
JSONL, including native compaction records and child-agent sessions, is copied
out in its backend-native form.
"""

from __future__ import annotations

import argparse
import hashlib as hashlib
import json
import os as os
import shutil
import subprocess
import sys
import tempfile as tempfile
import time as time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from long_context_monitoring.artifact_layout import organize_generation, evidence_file

import yaml

from long_context_monitoring.env import load_dotenv

from long_context_monitoring.run_layout import (
    resolve_repo_path,
    DEFAULT_RUNS_ROOT,
    validate_generation_id,
)
from long_context_monitoring.runlog import RunLog

from . import codex_session, delivery, session
from .maintenance_policy import load_policy
from .native_session import find_session_file, read_jsonl as read_jsonl
from .side_task import (
    SpecError,
    guidance_schedule as guidance_schedule,
    is_scheduled as is_scheduled,
    load_side_task as load_side_task,
)

from . import archive as _archive
from .archive import (
    WORKSPACE_DIRNAME as WORKSPACE_DIRNAME,
    WORKSPACE_ARCHIVE_EXCLUDES as WORKSPACE_ARCHIVE_EXCLUDES,
    workspace_fingerprint as workspace_fingerprint,
    copy_workspace as copy_workspace,
    archive_workspace as archive_workspace,
)
from .specification import (
    SPEC_KEYS as SPEC_KEYS,
    load_spec as load_spec,
    _is_int as _is_int,
    _runtime_guidance_turns as _runtime_guidance_turns,
)
from .resume import (
    RESUME_FILENAME as RESUME_FILENAME,
    write_resume_state as write_resume_state,
    load_resume_state as load_resume_state,
)
from .provenance import (
    validate_compaction_boundaries as validate_compaction_boundaries,
    _scan_transcript as _scan_transcript,
    _codex_message_text as _codex_message_text,
    _scan_codex_transcript as _scan_codex_transcript,
    compaction_boundaries as compaction_boundaries,
    transcript_provenance as transcript_provenance,
    delivery_provenance as delivery_provenance,
)

# Re-exported from the two modules this one was split into, so ``live.drive`` and
# friends keep resolving for existing callers and tests.
IDLE_TIMEOUT_SECONDS = session.IDLE_TIMEOUT_SECONDS
POLICY_MODEL = session.POLICY_MODEL
POLICY_EFFORT = session.POLICY_EFFORT
SessionError = session.SessionError
log = session.log
build_argv = session.build_argv
session_env = session.session_env
drive = session.drive
drive_segments = session.drive_segments
turn_plan = delivery.turn_plan


def archive_session(
    session_id: str,
    destination: Path,
    backend: str = "claude",
    native_home: Path | None = None,
) -> Path:
    """Copy the session JSONL and any sub-agent files out of the live store.

    The live session dir keeps mutating, so the dataset needs an immutable
    snapshot. ``shutil.copy`` follows symlinks, so a resumed session's symlinked
    sub-agent entries archive as real bytes.
    """

    return _archive._archive_session_with_finder(
        session_id,
        destination,
        backend,
        native_home,
        find_claude_session=find_session_file,
    )


def claude_version() -> str:
    """Best-effort ``claude --version``, recorded with every session."""
    try:
        completed = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        return completed.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def source_commit(spec_path: Path) -> str | None:
    """Return the full Git commit containing the generation source code."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(spec_path.parent), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def print_plan(
    spec: dict,
    arm: str,
    plan_segments: list[delivery.Segment],
    policy_model: str = POLICY_MODEL,
    policy_effort: str | None = POLICY_EFFORT,
    backend: str = "claude",
) -> None:
    """Print the resolved run without making a model call (``--dry-run``)."""
    plan = [message for segment in plan_segments for message in segment.messages]
    log(f"arm           : {arm}")
    log(f"backend       : {backend}")
    log(f"workspace     : {spec['workspace']}")
    log(f"policy_model  : {policy_model}")
    log(f"policy_effort : {policy_effort or '(provider default)'}")
    log(f"compaction    : {spec['compaction_mode']}")
    if spec["configured_compact_after"]:
        log(f"compact_after : {spec['configured_compact_after']}")
    guidance_turns = _runtime_guidance_turns(spec)
    log(f"guidance      : {guidance_turns or '(whole session)'}")
    log("\nmessage sequence:")
    for position, (label, text) in enumerate(plan, start=1):
        first = text.strip().splitlines()[0]
        log(f"  {position:>2}. [{label}] {first[:80]}")

    log(f"\ndelivery      : {len(plan_segments)} segment(s)")
    for segment in plan_segments:
        labels = ", ".join(label for label, _ in segment.messages)
        log(
            f"\n[{segment.label}]{' --resume' if segment.resumes else ''}: "
            f"{labels}; active guidance []; "
            f"tool profile {segment.tool_profile or 'default'}"
        )
        log("hidden instructions:")
        log("  (none; native generation is honest-only)")


def build_manifest(spec: dict, arm: str, spec_path: Path, name: str,
                   workspace: Path, fingerprint: str, observed: dict,
                   boundaries: list[dict],
                   runtime_guidance_activations: list[dict],
                   delivery_segments: list[dict],
                   started_at: str, finished_at: str,
                   workspace_archive: dict,
                   requested_model: str = POLICY_MODEL,
                   requested_effort: str | None = POLICY_EFFORT,
                   generation_id: str | None = None,
                   categorized_spec_path: str | None = None,
                   backend: str = "claude",
                   generation_mode: str = "native") -> dict:
    """Assemble the run manifest.

    ``task_id`` / ``condition`` / ``prompts`` are the three fields
    ``src/run_layout.py`` joins to file monitor results and to recover the
    agent's brief, so the kept monitor and viewer read this manifest with no
    shim. The side-task *text* is deliberately absent — only its presence is
    recorded — so a manifest can never leak it to a reader of the run dir.
    """
    manifest = {
        "task_id": name,
        "condition": arm,
        "generation_backend": backend,
        "generation_mode": generation_mode,
        "transcript_format": f"{backend}-native-jsonl",
        "transcript_provenance": "native",
        "prompts": [turn["prompt"] for turn in spec["host_turns"]],
        "spec_path": str(spec_path.resolve()),
        "policy_model": observed["policy_model"],
        "requested_model": requested_model,
        "requested_effort": requested_effort,
        "compaction_model": observed["compaction_model"],
        "workspace_source": str(spec["workspace"]),
        # The temp dir the session ran in. Kept for the resume path, but it is not
        # durable: read ``workspace_archive`` for the copy that outlives the run.
        "workspace_path": str(workspace),
        "workspace_archive": workspace_archive,
        "workspace_fingerprint": fingerprint,
        "compaction_mode": spec["compaction_mode"],
        "configured_compact_after": spec["configured_compact_after"],
        "host_turns": spec["host_turns"],
        "compaction_boundaries": boundaries,
        "runtime_guidance_turns": _runtime_guidance_turns(spec),
        "runtime_guidance_activations": runtime_guidance_activations,
        "delivery_segments": delivery_segments,
        "maintenance_policy_audit": observed.get("maintenance_policy_audit"),
        "side_task_present": spec["side_task"] is not None,
        "side_task_delivered": False,
        "side_task_raw_transcript_visibility": "not-recorded-as-conversation-event",
        "source_commit": source_commit(spec_path),
        "session_id": observed["session_id"],
        "cli_version": (
            codex_session.version() if backend == "codex" else claude_version()
        ),
        "started_at": started_at,
        "finished_at": finished_at,
    }
    if backend == "codex":
        manifest["codex_version"] = manifest["cli_version"]
    else:
        manifest["claude_version"] = manifest["cli_version"]
    if generation_id is not None:
        manifest["generation_id"] = generation_id
    if categorized_spec_path is not None:
        manifest["categorized_spec_path"] = categorized_spec_path
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.generate_transcript.live",
        description="Generate one honest native Claude or Codex session.",
    )
    parser.add_argument("--spec", required=True, type=Path, help="path to a live spec.yaml")
    parser.add_argument(
        "--arm",
        choices=("honest",),
        default="honest",
        help="condition (only honest native generation is supported)",
    )
    parser.add_argument(
        "--backend", choices=("claude", "codex"), default="claude",
        help="generation CLI and native transcript format (default: claude)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="exact backend policy model for the session, compaction, "
             "and sub-agents",
    )
    parser.add_argument(
        "--effort",
        choices=("low", "medium", "high", "xhigh", "max", "ultra"),
        help="backend effort level; omitted leaves the provider default unchanged",
    )
    parser.add_argument("--output-dir", "--runs-root", dest="runs_root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument(
        "--generation-id",
        help=(
            "required YYYY-MM-DDtHHMMz-<policy-label> identity shared by both "
            "arms; writes beneath --output-dir/generations/<id>/"
        ),
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="print the resolved plan and exit without calling a model")
    parser.add_argument("--resume", action="store_true",
                        help="continue a crashed run from its resume.json marker, "
                             "replaying only the turns that had not finished")
    args = parser.parse_args(argv)

    runlog = RunLog("generate", list(argv if argv is not None else sys.argv[1:]))
    runlog.install()
    try:
        return _run(args, runlog)
    finally:
        for path in runlog.paths:
            log(f"  log -> {path}")
        runlog.close()


def _run(args: argparse.Namespace, runlog: RunLog) -> int:
    """Generate one arm, with ``runlog`` capturing the console for the run tree."""
    prepared = _prepare_generation(args)
    if isinstance(prepared, int):
        return prepared
    spec = prepared.spec
    maintenance_policy = prepared.maintenance_policy
    name = prepared.name
    generation_id = prepared.generation_id
    plan_segments = prepared.plan_segments
    plan = prepared.plan

    # Load provider credentials before creating the child environment.
    # Explicitly exported values take precedence; the loader never logs secrets.
    load_dotenv()

    # The human name remains the spec directory. Categorized specs can hold
    # several policy-model generations without copying the authoritative spec.
    run_root = args.runs_root.resolve() / "generations" / generation_id
    # Opened here, before the first model call, because every interesting failure
    # (fingerprint mismatch, a turn erroring, the child dying) happens long before
    # ``archive_session`` creates the generation's arm directory.
    runlog.open_in(run_root / "evidence", args.arm)
    log(
        f"running the {args.arm} arm of {name} with {args.backend} "
        f"({len(spec['host_turns'])} turns)"
    )

    destination = run_root / args.arm
    try:
        workspace, fingerprint, resume_session_id, base_completed, native_home = (
            _prepare_workspace(args, spec, plan, plan_segments, destination)
        )

        checkpoint = _make_checkpoint(
            args,
            name,
            spec,
            plan,
            plan_segments,
            destination,
            workspace,
            fingerprint,
            native_home,
        )

        started_at = datetime.now(timezone.utc).isoformat()
        if args.backend == "codex":
            observed = codex_session.drive_segments(
                plan_segments,
                base_completed,
                workspace,
                resume_session_id,
                checkpoint,
                args.model,
                spec["compaction_mode"],
                args.effort,
                native_home,
            )
        else:
            observed = drive_segments(
                plan_segments,
                base_completed,
                workspace,
                resume_session_id,
                checkpoint,
                args.model,
                spec["compaction_mode"],
                args.effort,
                on_session_initialized=checkpoint,
            )
        # A completed resume runs no child process, so it has no fresh init event
        # from which to re-observe the already-validated pinned model.
        observed["policy_model"] = observed["policy_model"] or args.model
        finished_at = datetime.now(timezone.utc).isoformat()

        _record_maintenance_audit(maintenance_policy, workspace, destination, observed)

        archived, boundaries, workspace_archive = _finalize_generation(
            args,
            prepared,
            destination,
            workspace,
            fingerprint,
            resume_session_id,
            native_home,
            observed,
            started_at,
            finished_at,
        )
    except (SpecError, SessionError, OSError) as error:
        print(f"[error] {error}", file=sys.stderr)
        return 1

    organize_generation(destination.parent)
    log(f"archived -> {destination}")
    log(f"  {len(boundaries)} compaction boundary/boundaries in {archived.name}")
    if workspace_archive["archived"]:
        log(
            f"  workspace {workspace_archive['files']} files "
            f"({workspace_archive['bytes']} bytes) -> {destination / WORKSPACE_DIRNAME}"
        )
    else:
        log("  !! no workspace archived; a side-task probe has nothing to run on")
    return 0


@dataclass(frozen=True)
class _GenerationPlan:
    """Validated inputs shared by execution and archive finalization."""

    spec: dict
    maintenance_policy: dict | None
    name: str
    categorized_path: str
    generation_id: str
    plan_segments: list[delivery.Segment]
    plan: list[tuple[str, str]]


def _prepare_generation(args: argparse.Namespace) -> _GenerationPlan | int:
    """Resolve the run, or return its existing validation/dry-run exit code."""
    if args.model is None:
        args.model = (
            codex_session.POLICY_MODEL if args.backend == "codex" else POLICY_MODEL
        )
    try:
        args.spec = resolve_repo_path(args.spec)
        spec = load_spec(args.spec)
        maintenance_policy = load_policy(args.spec, spec)
    except (SpecError, OSError, yaml.YAMLError) as error:
        print(f"[error] {error}", file=sys.stderr)
        return 2

    name = args.spec.resolve().parent.name
    categorized_path = name
    if not args.generation_id:
        print(
            "[error] --generation-id is required and must name the policy generation",
            file=sys.stderr,
        )
        return 2
    try:
        generation_id = validate_generation_id(args.generation_id)
    except ValueError as error:
        print(f"[error] {error}", file=sys.stderr)
        return 2
    if maintenance_policy is not None and args.backend != "claude":
        print(
            "[error] maintenance-isolated specs require the Claude backend",
            file=sys.stderr,
        )
        return 2
    plan_segments: list[delivery.Segment] = []
    plan: list[tuple[str, str]] = []
    plan_segments = delivery.segments(spec, args.arm, maintenance_policy)
    plan = [message for segment in plan_segments for message in segment.messages]
    if args.dry_run:
        # Deliberately before any ``open_in`` so a dry run leaves no run artifact.
        print_plan(spec, args.arm, plan_segments, args.model, args.effort, args.backend)
        return 0

    return _GenerationPlan(
        spec,
        maintenance_policy,
        name,
        categorized_path,
        generation_id,
        plan_segments,
        plan,
    )


def _prepare_workspace(
    args, spec, plan, plan_segments, destination
) -> tuple[Path, str, str | None, int, Path | None]:
    """Resume the recorded workspace or create a fresh isolated native session."""
    if args.resume:
        state = load_resume_state(
            destination,
            plan,
            plan_segments,
            spec,
            args.model,
            args.effort,
            args.backend,
        )
        workspace = Path(state["workspace"])
        fingerprint = state["workspace_fingerprint"]
        resume_session_id = state["session_id"]
        base_completed = int(state["completed"])
        native_home = (
            Path(state["native_home"]) if state.get("native_home") is not None else None
        )
        if base_completed >= len(plan):
            log(
                "  resume.json shows every turn finished; finalizing the "
                "archive without replay"
            )
        else:
            log(f"  resuming session {resume_session_id} in {workspace}")
            log(
                f"  {base_completed} of {len(plan)} turns done; replaying from "
                f"{plan[base_completed][0]!r}"
            )
    else:
        fingerprint = workspace_fingerprint(spec["workspace"])
        workspace = copy_workspace(spec["workspace"])
        log(f"  workspace copy {workspace}")
        resume_session_id = None
        base_completed = 0
        native_home = (
            codex_session.prepare_codex_home(workspace.parent)
            if args.backend == "codex"
            else None
        )
        # A fresh generation owns the transcript dir outright. Clear it first
        # so a regenerated arm replaces the prior session's files instead of
        # landing beside them: ``archive_session`` copies one ``<id>.jsonl``,
        # and a second generation uses a new id, so without this the dir ends
        # up with two main JSONLs and ``main_jsonl`` rejects the whole arm.
        # Only the transcript dir, so an existing workspace/ and monitor/ are
        # left for the archive and re-scoring steps to replace on their own.
        shutil.rmtree(destination / "transcript", ignore_errors=True)

    return workspace, fingerprint, resume_session_id, base_completed, native_home


def _make_checkpoint(
    args,
    name,
    spec,
    plan,
    plan_segments,
    destination,
    workspace,
    fingerprint,
    native_home,
):
    """Capture the exact run state used for initialization and turn snapshots."""

    def checkpoint(completed: int, session_id: str) -> None:
        """Snapshot the live transcript during initialization and after turns.

        ``completed`` is already the plan-global count. ``drive_segments``
        adds each segment's offset, so one crashed run resumes at the right
        message whether the spec is staged or not. Never fatal: a failed
        checkpoint logs and goes on.
        """
        try:
            archive_session(
                session_id, destination / "transcript", args.backend, native_home
            )
            write_resume_state(
                destination,
                name=name,
                arm=args.arm,
                session_id=session_id,
                workspace=workspace,
                fingerprint=fingerprint,
                plan=plan,
                plan_segments=plan_segments,
                spec=spec,
                completed=completed,
                policy_model=args.model,
                policy_effort=args.effort,
                backend=args.backend,
                native_home=native_home,
            )
        except OSError as error:
            checkpoint_label = (
                "session initialization"
                if completed == 0
                else f"after {plan[completed - 1][0]}"
            )
            log(f"  !! checkpoint {checkpoint_label} failed: {error}")

    return checkpoint


def _record_maintenance_audit(
    maintenance_policy, workspace, destination, observed
) -> None:
    """Record maintenance tool decisions beside the generated session."""
    if maintenance_policy is not None:
        audit_source = workspace.parent / "padding-tool-audit.jsonl"
        audit_destination = destination / "padding-tool-audit.jsonl"
        destination.mkdir(parents=True, exist_ok=True)
        if audit_source.is_file():
            shutil.copy2(audit_source, audit_destination)
            audit_rows = [
                json.loads(line)
                for line in audit_source.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        else:
            audit_rows = []
        denied = [row for row in audit_rows if row.get("allowed") is not True]
        observed["maintenance_policy_audit"] = {
            "path": audit_destination.name,
            "tool_calls": len(audit_rows),
            "denied_tool_calls": len(denied),
            "policy_path": maintenance_policy["_path"],
            "rule_set_sha256": maintenance_policy["hashes"]["rule_set_sha256"],
            "policy_violations_observed": bool(denied),
        }
        if denied:
            log(
                f"  !! maintenance audit recorded "
                f"{len(denied)} denied tool call(s)"
            )


def _finalize_generation(
    args,
    prepared,
    destination,
    workspace,
    fingerprint,
    resume_session_id,
    native_home,
    observed,
    started_at,
    finished_at,
):
    """Archive native evidence before publishing its manifest and clearing resume state."""
    spec = prepared.spec
    name = prepared.name
    plan_segments = prepared.plan_segments
    generation_id = prepared.generation_id
    categorized_path = prepared.categorized_path
    # On resume the child re-attaches the same id, so prefer the one we know
    # (init may report it too, but the marker is authoritative) for locating
    # the archived file and stamping the manifest.
    session_id = resume_session_id or observed["session_id"]
    observed["session_id"] = session_id
    archived = archive_session(
        session_id, destination / "transcript", args.backend, native_home
    )
    boundaries, delivery_records, activations = transcript_provenance(
        archived, spec, plan_segments, args.model, args.effort, args.backend
    )
    validate_compaction_boundaries(spec, boundaries)
    if boundaries and observed["compaction_model"] is None:
        observed["compaction_model"] = args.model
    # Deliberately not fatal. The session is finished and the transcript is
    # already on disk, so failing the run here would throw away the primary
    # artifact over a copy. The manifest records the failure instead, which
    # keeps "there is no workspace to score" distinguishable from "the
    # workspace was scored and nothing was found".
    try:
        workspace_archive = archive_workspace(workspace, destination)
    except OSError as error:
        log(f"  !! archiving the workspace failed: {error}")
        workspace_archive = {
            "path": WORKSPACE_DIRNAME,
            "archived": False,
            "error": str(error),
        }
    manifest = build_manifest(
        spec,
        args.arm,
        args.spec,
        name,
        workspace,
        fingerprint,
        observed,
        boundaries,
        activations,
        delivery_records,
        started_at,
        finished_at,
        workspace_archive,
        requested_model=args.model,
        requested_effort=args.effort,
        generation_id=generation_id,
        categorized_spec_path=categorized_path,
        backend=args.backend,
        generation_mode="native",
    )
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    # The run finished and the manifest is the authoritative record now, so
    # clear the mid-run marker: a leftover resume.json means "died partway".
    evidence_file(destination, RESUME_FILENAME).unlink(missing_ok=True)
    return archived, boundaries, workspace_archive


if __name__ == "__main__":
    raise SystemExit(main())

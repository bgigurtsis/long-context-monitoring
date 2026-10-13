"""Resolve explicit input paths and keep generated output outside the dataset."""
from __future__ import annotations
import hashlib
import re
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path.cwd().resolve()
DEFAULT_RUNS_ROOT = Path("outputs")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_GENERATION_ID = re.compile(r"(?P<stamp>\d{4}-\d{2}-\d{2}t\d{4}z)-[a-z0-9]+(?:-[a-z0-9]+)*")

def resolve_repo_path(value: str | Path, root: Path | None = None) -> Path:
    """Resolve a caller's path without private relocation indexes."""
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return ((root or Path.cwd()) / candidate).resolve()

def validate_slug(value: str, *, label: str) -> str:
    """Reject identifiers that could escape the output directory."""
    if not _SLUG.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase hyphenated slug")
    return value

def validate_generation_id(value: str) -> str:
    """Check a timestamped generation name before creating its directory."""
    match = _GENERATION_ID.fullmatch(value)
    if match is None:
        raise ValueError("generation id must be YYYY-MM-DDtHHMMz-<label>")
    datetime.strptime(match.group("stamp"), "%Y-%m-%dt%H%Mz")
    return value

def validate_monitor_batch_name(value: str) -> str:
    """Validate one portable output batch name."""
    return validate_slug(value, label="monitor batch name")

def generation_root(spec_path: str | Path, generation_id: str) -> Path:
    """Return the default destination for a new generation."""
    return DEFAULT_RUNS_ROOT / "generations" / validate_generation_id(generation_id)

def monitor_batch_root(runs_root: str | Path, batch_name: str, date_utc: str) -> Path:
    """Group new monitor results by date and a caller-supplied name."""
    datetime.strptime(date_utc, "%Y-%m-%d")
    return Path(runs_root) / "monitor-runs" / date_utc / validate_monitor_batch_name(batch_name)

def monitor_results_root(transcripts: list[Path], repo: Path = REPO_ROOT) -> Path:
    """Keep monitoring outputs outside the released transcript trees."""
    return Path.cwd() / DEFAULT_RUNS_ROOT

def generation_result_subpath(transcript_path: str | Path) -> str | None:
    """Use the public example and arm names as the result location."""
    path = resolve_repo_path(transcript_path)
    archive = path if path.is_dir() else path.parent
    if archive.name == "transcript" and archive.parent.name in {"honest", "attack"}:
        return f"{archive.parent.parent.name}/{archive.parent.name}"
    return None

def results_subpath(manifest: dict | None, fallback_name: str) -> str:
    """Use public task metadata when present, otherwise the input filename."""
    manifest = manifest or {}
    task_id = manifest.get("task_id")
    condition = manifest.get("condition")
    if isinstance(task_id, str) and task_id.strip():
        if isinstance(condition, str) and condition.strip():
            return f"{task_id.strip()}/{condition.strip()}"
        return task_id.strip()
    return fallback_name

def task_description_from_manifest(manifest: dict | None) -> str:
    """Read only host requests when building a monitor task description."""
    prompts = (manifest or {}).get("prompts")
    if not isinstance(prompts, list):
        return ""
    cleaned = [str(prompt).strip() for prompt in prompts if str(prompt).strip()]
    if len(cleaned) == 1:
        return cleaned[0]
    return "\n\n".join(f"[Turn {index}] {prompt}" for index, prompt in enumerate(cleaned, 1))

def experiment_roots(runs_root: Path = DEFAULT_RUNS_ROOT) -> list[Path]:
    """Discover public examples and locally generated output."""
    return [REPO_ROOT / "dataset" / "examples", Path(runs_root)]

def tree_sha256(path: str | Path) -> str:
    """Hash file names and bytes without changing native records."""
    path = Path(path)
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()

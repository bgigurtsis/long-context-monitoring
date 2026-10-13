"""Present one filesystem view per native maintenance profile."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class WorkspaceIsolationError(RuntimeError):
    """A profile changed bytes outside its allowed workspace view."""


def non_maintenance_fingerprint(workspace: Path, maintenance_name: str = "maintenance") -> str:
    digest = hashlib.sha256()
    for path in sorted(workspace.rglob("*")):
        relative = path.relative_to(workspace)
        if relative.parts and relative.parts[0] == maintenance_name:
            continue
        digest.update(relative.as_posix().encode())
        if path.is_symlink():
            digest.update(b"L")
            digest.update(os.readlink(path).encode())
        elif path.is_file():
            digest.update(b"F")
            digest.update(path.read_bytes())
        elif path.is_dir():
            digest.update(b"D")
    return digest.hexdigest()


def _copy_non_maintenance(workspace: Path, snapshot: Path, maintenance_name: str) -> None:
    snapshot.mkdir()
    for path in workspace.iterdir():
        if path.name == maintenance_name:
            continue
        destination = snapshot / path.name
        if path.is_symlink():
            destination.symlink_to(os.readlink(path), target_is_directory=path.is_dir())
        elif path.is_dir():
            shutil.copytree(path, destination, symlinks=True)
        else:
            shutil.copy2(path, destination, follow_symlinks=False)


def _restore_non_maintenance(workspace: Path, snapshot: Path, maintenance_name: str) -> None:
    for path in workspace.iterdir():
        if path.name != maintenance_name:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
    for path in snapshot.iterdir():
        destination = workspace / path.name
        if path.is_symlink():
            destination.symlink_to(os.readlink(path), target_is_directory=path.is_dir())
        elif path.is_dir():
            shutil.copytree(path, destination, symlinks=True)
        else:
            shutil.copy2(path, destination, follow_symlinks=False)


def _padding_input_relative(
    maintenance: Path,
    maintenance_name: str,
    policy_path: str | None,
    padding_turn: int | None,
) -> Path:
    """Validate the requested input namespace before displacing any accepted files."""
    if policy_path is None or padding_turn is None:
        raise WorkspaceIsolationError("padding view requires its turn policy")
    policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
    turn_policy = policy["turns"].get(str(padding_turn))
    if not isinstance(turn_policy, dict):
        raise WorkspaceIsolationError(f"missing padding policy for turn {padding_turn}")
    allowed = turn_policy["allowed_inputs"]
    if len(allowed) != 1 or not allowed[0].startswith("maintenance/inputs/"):
        raise WorkspaceIsolationError("padding turn must declare one input directory")
    allowed_path = Path(allowed[0].split("/**", 1)[0])
    inputs_root = Path(maintenance_name) / "inputs"
    try:
        input_relative = allowed_path.relative_to(inputs_root)
    except ValueError as error:
        raise WorkspaceIsolationError(
            "padding input must remain under the maintenance input root"
        ) from error
    if not input_relative.parts or ".." in input_relative.parts:
        raise WorkspaceIsolationError("padding input directory is invalid")
    initial_source_inputs = maintenance / "inputs" / input_relative
    if not initial_source_inputs.is_dir():
        raise WorkspaceIsolationError(f"missing inputs for padding turn {padding_turn}")
    return input_relative


class _PaddingView:
    """Paths needed to expose and restore one selected maintenance input tree."""

    def __init__(
        self,
        workspace: Path,
        maintenance_name: str,
        holding: Path,
        input_relative: Path,
    ):
        self.workspace = workspace
        self.maintenance_name = maintenance_name
        self.holding = holding
        self.input_relative = input_relative
        self.maintenance = workspace / maintenance_name
        self.original_maintenance = holding / maintenance_name
        self.source_inputs = self.original_maintenance / "inputs" / input_relative
        self.visible_target = self.maintenance / "inputs" / input_relative

    def expose(self) -> None:
        self.maintenance.rename(self.original_maintenance)
        for source in list(self.workspace.iterdir()):
            source.rename(self.holding / source.name)
        visible_inputs = self.maintenance / "inputs"
        visible_inputs.mkdir(parents=True)
        self.visible_target.parent.mkdir(parents=True, exist_ok=True)
        self.source_inputs.rename(self.visible_target)
        source_reports = self.original_maintenance / "reports"
        if source_reports.is_dir():
            source_reports.rename(self.maintenance / "reports")

    def restore(self) -> bool:
        """Restore held entries in their original order and report detected escapes."""
        escape_detected = any(
            path.name != self.maintenance_name for path in self.workspace.iterdir()
        )
        unexpected = [
            path
            for path in self.maintenance.iterdir()
            if path.name not in {"inputs", "reports"}
        ]
        visible_input_dirs = list((self.maintenance / "inputs").iterdir())
        if (
            unexpected
            or [path.name for path in visible_input_dirs]
            != [self.input_relative.parts[0]]
            or not self.visible_target.is_dir()
        ):
            escape_detected = True
        self.visible_target.rename(self.source_inputs)
        visible_reports = self.maintenance / "reports"
        if visible_reports.is_dir():
            visible_reports.rename(self.original_maintenance / "reports")
        shutil.rmtree(self.maintenance)
        self.original_maintenance.rename(self.workspace / self.maintenance_name)
        for held in list(self.holding.iterdir()):
            destination = self.workspace / held.name
            if destination.exists() or destination.is_symlink():
                escape_detected = True
                if destination.is_dir() and not destination.is_symlink():
                    shutil.rmtree(destination)
                else:
                    destination.unlink()
            held.rename(destination)
        return escape_detected


def _restore_hidden_maintenance(
    workspace: Path, maintenance_name: str, holding: Path
) -> bool:
    """Remove a replacement maintenance root before returning the hidden original."""
    escape_detected = False
    created = workspace / maintenance_name
    if created.exists() or created.is_symlink():
        if created.is_dir() and not created.is_symlink():
            shutil.rmtree(created)
        else:
            created.unlink()
        escape_detected = True
    (holding / maintenance_name).rename(workspace / maintenance_name)
    return escape_detected


@contextmanager
def scoped_workspace_view(
    workspace: Path,
    profile: str | None,
    maintenance_name: str = "maintenance",
    policy_path: str | None = None,
    padding_turn: int | None = None,
) -> Iterator[None]:
    """Hide the opposite tree and restore the accepted view after one segment."""

    if profile is None:
        yield
        return
    if profile not in {"application", "padding", "compaction"}:
        raise WorkspaceIsolationError(f"unknown workspace profile {profile!r}")
    maintenance = workspace / maintenance_name
    if not maintenance.is_dir():
        raise WorkspaceIsolationError(f"missing maintenance root {maintenance}")
    before = non_maintenance_fingerprint(workspace, maintenance_name)
    with tempfile.TemporaryDirectory(
        prefix="lcm-workspace-view-", dir=workspace.parent
    ) as temporary:
        temporary_root = Path(temporary)
        holding = temporary_root / "holding"
        snapshot = temporary_root / "snapshot"
        holding.mkdir()
        if profile == "padding":
            input_relative = _padding_input_relative(
                maintenance, maintenance_name, policy_path, padding_turn
            )
            _copy_non_maintenance(workspace, snapshot, maintenance_name)
            padding_view = _PaddingView(
                workspace, maintenance_name, holding, input_relative
            )
            padding_view.expose()
        else:
            maintenance.rename(holding / maintenance_name)
        escape_detected = False
        try:
            yield
        finally:
            if profile == "padding":
                escape_detected = padding_view.restore()
            else:
                escape_detected = _restore_hidden_maintenance(
                    workspace, maintenance_name, holding
                )
        # Preserve the existing distinction: restoration always runs, while this
        # validation runs only when the body returns normally.
        after = non_maintenance_fingerprint(workspace, maintenance_name)
        if profile == "padding" and (escape_detected or after != before):
            _restore_non_maintenance(workspace, snapshot, maintenance_name)
            raise WorkspaceIsolationError(
                "padding turn changed non-maintenance bytes; the accepted snapshot was restored"
            )

"""Locate spec inputs and completed generation artifacts."""
from pathlib import Path
import shutil


def input_file(spec_dir: Path, name: str) -> Path:
    """Locate an input in its grouped directory or beside the spec."""
    grouped = spec_dir / "inputs" / name
    return grouped if grouped.exists() or (spec_dir / "inputs").is_dir() else spec_dir / name


def evidence_file(owner: Path, name: str) -> Path:
    """Locate metadata owned by a generation or one of its arms."""
    flat = owner / name
    if flat.exists():
        return flat
    if owner.name in {"honest", "attack"}:
        return owner.parent / "evidence" / owner.name / name
    return owner / "evidence" / name


def organize_generation(generation: Path) -> None:
    """Group completed-run sidecars without changing transcripts or workspaces.

    Call after writers have closed their files. Native transcript contents,
    including native metadata stored inside transcript/, are never rearranged.
    """
    moves = []
    for arm_name in ("honest", "attack"):
        arm = generation / arm_name
        if not arm.is_dir():
            continue
        for source in arm.iterdir():
            if source.name not in {"transcript", "workspace"}:
                moves.append((source, generation / "evidence" / arm_name / source.name))
    for source in generation.iterdir():
        if source.name not in {"honest", "attack", "evidence", "logs", "derived"}:
            moves.append((source, generation / "evidence" / source.name))
    for _source, target in moves:
        if target.exists():
            raise FileExistsError(f"refusing to replace recorded evidence: {target}")
    for source, target in moves:
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)


def copy_arm(source: Path, destination: Path) -> None:
    """Copy an arm and its separately stored evidence into a flat staging arm."""
    shutil.copytree(source, destination)
    evidence = source.parent / "evidence" / source.name
    if evidence.is_dir():
        for item in evidence.iterdir():
            target = destination / item.name
            if target.exists():
                raise FileExistsError(f"duplicate arm evidence: {target}")
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)

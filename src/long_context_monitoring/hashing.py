"""Order hashed trees consistently while preserving the published fingerprints."""

from pathlib import Path, PurePath


def tree_path_key(relative: PurePath) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Use Windows-style component ordering with a deterministic case tie-break.

    The release was hashed on Windows. Sorting native Path objects would give
    different fingerprints on POSIX even when every file has identical bytes.
    Original path spelling is still included in the digest by the caller.
    """
    return tuple(part.lower() for part in relative.parts), relative.parts


def ordered_tree_files(root: Path) -> list[Path]:
    files = [path for path in root.rglob("*") if path.is_file()]
    return sorted(files, key=lambda path: tree_path_key(path.relative_to(root)))

"""Portable tree identities must not depend on Path's host-specific comparison."""

from pathlib import PurePosixPath, PureWindowsPath

from long_context_monitoring.hashing import tree_path_key


def test_windows_and_posix_paths_have_identical_component_order():
    names = ["README.md", "auditlog/store.py", "a/z.py", "a.py", "Z.py", "z.py"]
    expected = ["a/z.py", "a.py", "auditlog/store.py", "README.md", "Z.py", "z.py"]
    for path_type in (PurePosixPath, PureWindowsPath):
        paths = [path_type(name) for name in reversed(names)]
        assert [path.as_posix() for path in sorted(paths, key=tree_path_key)] == expected

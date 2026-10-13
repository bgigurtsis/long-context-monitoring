"""A minimal, cross-process, cross-platform advisory file lock.

Serializes concurrent writers to a single log-store file across threads,
processes, and process restarts. Uses exclusive file creation
(``O_CREAT | O_EXCL``), which is atomic on every platform Python supports, so
no platform-specific primitive (``fcntl``, ``msvcrt``) is needed.

A lock file older than ``stale_after`` seconds is treated as abandoned by a
holder that crashed before releasing it, and is reclaimed rather than waited
on forever. That is what lets a fresh process make progress after a crash
without manual cleanup.
"""

from __future__ import annotations

import os
import time
from pathlib import Path


class LockTimeoutError(TimeoutError):
    """Raised when a lock could not be acquired within the allotted time."""


class FileLock:
    """A mutual-exclusion lock backed by one exclusively-created file."""

    def __init__(
        self,
        path: str,
        *,
        stale_after: float = 30.0,
        timeout: float = 10.0,
        poll_interval: float = 0.01,
    ) -> None:
        self._path = Path(path)
        self._stale_after = stale_after
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._acquired = False

    def acquire(self) -> None:
        deadline = time.monotonic() + self._timeout
        while True:
            try:
                fd = os.open(str(self._path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    os.write(fd, str(os.getpid()).encode("ascii"))
                finally:
                    os.close(fd)
                self._acquired = True
                return
            except FileExistsError:
                if self._reclaim_if_stale():
                    continue
                if time.monotonic() >= deadline:
                    raise LockTimeoutError(
                        f"could not acquire lock {self._path} within {self._timeout}s"
                    )
                time.sleep(self._poll_interval)

    def _reclaim_if_stale(self) -> bool:
        """Break and remove the lock if it looks abandoned by a crashed holder."""

        try:
            age = time.time() - self._path.stat().st_mtime
        except FileNotFoundError:
            return True  # released between our failed create and this stat
        if age <= self._stale_after:
            return False
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
        return True

    def release(self) -> None:
        if self._acquired:
            try:
                self._path.unlink()
            except FileNotFoundError:
                pass
            self._acquired = False

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

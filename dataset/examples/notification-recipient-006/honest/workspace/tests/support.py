"""Shared test helpers."""
from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager

from accountsvc import storage


@contextmanager
def temp_database():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    storage.initialize(path)
    try:
        yield path
    finally:
        os.remove(path)

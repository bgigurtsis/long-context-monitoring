"""Use canonical temporary paths on every operating system."""
import tempfile
from pathlib import Path

tempfile.tempdir = str(Path(tempfile.gettempdir()).resolve())

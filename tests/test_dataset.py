"""Validate the distributed dataset without generation or monitor calls."""

import hashlib
import json
from pathlib import Path

from long_context_monitoring.attack_lab.edits import verify_function_edit
from long_context_monitoring.generate_transcript.specification import load_spec
from long_context_monitoring.pair_workflow.source import inline_actions

DATASET = Path(__file__).resolve().parents[1] / "dataset"


def test_every_pair_has_valid_references_and_exact_replacements():
    index = json.loads((DATASET / "index.json").read_text(encoding="utf-8"))
    assert len(index["examples"]) == 30
    assert len({example["id"] for example in index["examples"]}) == 30
    for example in index["examples"]:
        spec_path = DATASET / example["spec"]
        spec = load_spec(spec_path, require_workspace=False)
        actions = inline_actions(spec)
        assert len(actions) == 2
        seed = spec_path.parent / "inputs/seed"
        assert seed.is_dir() == example["starting_workspace_available"]
        for arm in ["honest", "attack"]:
            archive = DATASET / example[arm]["transcript"]
            workspace = DATASET / example[arm]["workspace"]
            manifest_path = DATASET / example[arm]["manifest"]
            assert archive.is_dir() and workspace.is_dir() and manifest_path.is_file()
            assert {path.name for path in archive.parent.iterdir()} == {
                "manifest.json", "transcript", "workspace"
            }
        for action in actions:
            matched, reason = verify_function_edit(
                DATASET / example["attack"]["workspace"], action.edit
            )
            assert matched, reason


def test_all_native_transcript_files_match_the_published_hashes():
    index = json.loads((DATASET / "index.json").read_text(encoding="utf-8"))
    for example in index["examples"]:
        for arm in ["honest", "attack"]:
            archive = DATASET / example[arm]["transcript"]
            manifest = json.loads((DATASET / example[arm]["manifest"]).read_text(encoding="utf-8"))
            files = {
                path.relative_to(archive).as_posix(): path
                for path in archive.rglob("*") if path.is_file()
            }
            assert files.keys() == manifest["transcript_files"].keys()
            for name, path in files.items():
                assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["transcript_files"][name]

"""Validate the distributed dataset without generation or monitor calls."""

import hashlib
import json
from pathlib import Path

from long_context_monitoring.attack_lab.edits import verify_function_edit
from long_context_monitoring.generate_transcript.specification import load_spec
from long_context_monitoring.pair_workflow.source import _sha256_tree, inline_actions
from long_context_monitoring.run_layout import tree_sha256

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


def test_published_tree_hashes_match_both_runtime_hash_functions():
    index = json.loads((DATASET / "index.json").read_text(encoding="utf-8"))
    for example in index["examples"]:
        for arm in ("honest", "attack"):
            metadata = example[arm]
            manifest = json.loads((DATASET / metadata["manifest"]).read_text(encoding="utf-8"))
            for folder, key in (("workspace", "workspace_sha256"),
                                ("transcript", "transcript_tree_sha256")):
                root = DATASET / metadata[folder]
                assert tree_sha256(root) == metadata[key] == manifest[key]
                assert _sha256_tree(root) == metadata[key]


def _result_versions(archive: Path) -> dict[tuple[str, str], list[dict]]:
    """Keep repeated UUIDs because native compaction may retain a row again."""
    results: dict[tuple[str, str], list[dict]] = {}
    for path in archive.rglob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            content = entry.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    key = (entry.get("uuid"), block.get("tool_use_id"))
                    results.setdefault(key, []).append({
                        "content": block.get("content"),
                        "toolUseResult": entry.get("toolUseResult"),
                    })
    return results


def test_restored_reconciliation_records_identify_changed_native_results():
    index = json.loads((DATASET / "index.json").read_text(encoding="utf-8"))
    total = 0
    for example in index["examples"]:
        manifest = json.loads((DATASET / example["attack"]["manifest"]).read_text(encoding="utf-8"))
        provenance = manifest["source_replay_provenance"]
        assert provenance["origin"] == "source-construction-records"
        assert len(bytes.fromhex(provenance["source_result_sha256"])) == 32
        honest = _result_versions(DATASET / example["honest"]["transcript"])
        attack = _result_versions(DATASET / example["attack"]["transcript"])
        for record in manifest["source_replays"]:
            key = (record["entry_uuid"], record["tool_use_id"])
            assert key in honest and key in attack, (example["id"], key)
            assert any(after not in honest[key] for after in attack[key]), (example["id"], key)
            assert record["replacement_count"] > 0
            assert record["path"] in {edit["path"] for edit in example["edits"]}
            total += 1
    assert total == 63

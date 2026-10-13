"""Load and validate the optional maintenance isolation sidecar."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .side_task import SpecError
from long_context_monitoring.run_layout import resolve_repo_path
from long_context_monitoring.artifact_layout import input_file


POLICY_FILENAME = "padding_policy.json"


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_policy(spec_path: Path, spec: dict) -> dict | None:
    """Return a verified sidecar with its absolute path attached."""

    path = input_file(resolve_repo_path(spec_path).parent, POLICY_FILENAME)
    if not path.exists():
        return None
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SpecError(f"{path}: invalid maintenance policy: {error}") from error
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise SpecError(f"{path}: unsupported maintenance policy")
    required = {
        "padding_turns", "maintenance_root", "allowed_tools", "bash_commands",
        "application_denied_paths", "turns", "hashes",
    }
    missing = sorted(required - set(policy))
    if missing:
        raise SpecError(f"{path}: missing policy keys {missing}")
    padding_turns = policy["padding_turns"]
    if padding_turns != sorted(set(padding_turns)):
        raise SpecError(f"{path}: padding turns must be unique and sorted")
    host_turns = {turn["id"] for turn in spec["host_turns"]}
    if not set(padding_turns) <= host_turns:
        raise SpecError(f"{path}: padding turn is absent from the spec")
    if set(policy["turns"]) != {str(turn) for turn in padding_turns}:
        raise SpecError(f"{path}: per-turn rules do not match padding turns")
    rules = {
        "padding_turns": policy["padding_turns"],
        "maintenance_root": policy["maintenance_root"],
        "allowed_tools": policy["allowed_tools"],
        "bash_commands": policy["bash_commands"],
        "application_denied_paths": policy["application_denied_paths"],
        "turns": policy["turns"],
    }
    expected = policy["hashes"].get("rule_set_sha256")
    if expected != _canonical_hash(rules):
        raise SpecError(f"{path}: rule-set hash mismatch")
    manifest_path = spec["workspace"] / policy["maintenance_root"] / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SpecError(f"{manifest_path}: invalid maintenance manifest: {error}") from error
    expected_manifest = policy["hashes"].get("maintenance_manifest_sha256")
    if expected_manifest != _canonical_hash(manifest):
        raise SpecError(f"{path}: maintenance manifest hash mismatch")
    policy["_path"] = str(path)
    return policy

# Publication review

Reviewed release `e620f1ac53240711330cc654cf42b534f4329aa3` on 2026-10-15.
This branch adds offline reproductions and review notes. It does not fix the
runtime or alter the dataset. No paid model calls were made.

## Dataset selection is correct

The release was compared against the source project's
`metadata/transcript-viewer-pairs-successful-new.json` registry:

- All 30 attack transcripts match their selected source bytes. Fourteen are
  redesigned attacks; sixteen also belong to the original set.
- All corresponding honest transcripts match. Every one of the 66 published
  transcript files was checked against its selected source.
- All 60 final workspaces have identical file names and contents to the source
  workspaces, excluding Python bytecode caches from the source comparison.
- All 60 edit registrations match the selected construction records, including
  their function, path, host-turn anchor, insertion position, and replacement hash.

The source comparison requires the private project checkout. Its results do
not establish that every constructed trajectory is internally consistent;
they establish that the intended evidence was exported faithfully.

## Workspace hashing depends on the operating system

**Priority: medium. Confirmed on macOS; all 60 published hashes reproduced.**

The initial review found that all published workspace hashes disagreed with
`pair_workflow.source._sha256_tree`. Further investigation identified the cause:
every published hash matches that algorithm when paths use Windows-style,
case-insensitive ordering. The function calls `sorted()` on native `Path`
objects, whose ordering differs between Windows and POSIX systems. For example,
`README.md` sorts before `auditlog/` on POSIX and after it on Windows.

For `import-integrity-002/honest/workspace`:

| Ordering | SHA-256 |
|---|---|
| Published / Windows ordering | `62722a25b55dd12bb24415fdd440a2bebd6320d0d175da38197a89a1f88b8993` |
| Runtime on macOS | `d53080dc7f9eeb7341f3b3e9b562ba9dc7c10836d1fd678b92c3e5f2319b8ac4` |

This is a reproducibility bug, not evidence of corrupted workspace files.
`run_layout.tree_sha256` also sorts native `Path` objects. The existing dataset
tests verify transcript file hashes but do not verify workspace hashes.

Proposed fix: define and document one platform-independent ordering and use it
consistently. Either retain the published Windows ordering explicitly, or
version the algorithm and regenerate the metadata. Verify every published
workspace hash in the dataset tests.

## Later function overwrites can pass validation

**Priority: high. Two offline reproductions fail as expected.**

`pair_workflow.reconciliation._validate_following_native_entry` considers only
`Edit` and `Write` calls. A `Bash` command that overwrites a registered function
passes validation. A body-only `Edit` also passes because overlap detection
only looks for the function's header in the edit text.

The latter reproduction uses a copied honest edit whose old body no longer
exists after insertion. The retained successful tool result would therefore
misrepresent the attack's state. These checks exercise the validator directly;
they do not execute any transcript command.

Proposed fix: track function state at each anchor and reject later writes or
edits whose compatibility cannot be established, including shell writes and
body-only edits. Add end-to-end construction checks as well as validator tests.

## Reconciliation changes unrelated evidence

**Priority: high. Two offline reproductions fail as expected.**

`pair_workflow.reconciliation._replay_tool_result` applies every active source
replacement to every later result. The caller remembers only the tool name,
not its file path or command inputs. Consequently, identical function text in
`Read(other.py)` or `Bash("git show HEAD:other.py")` is rewritten as though it
were a read of the registered `app.py`. Both the displayed result and structured
payload change. A control confirms that an actual read of `app.py` is updated.

Proposed fix: retain tool input provenance and reconcile only established reads
of the current registered file. Preserve unrelated and historical output, and
reject ambiguous reads when they prevent construction from being validated.

These two runtime findings do not by themselves show that the shipped dataset
contains these failure cases. The release and source project contain the same
relevant validation/reconciliation logic.

## Export omits available reconciliation provenance

**Priority: medium. Confirmed by source evidence comparison.**

The selected source construction records contain 63 `native_source_replays`
across 28 pairs. The public attack manifests retain none of these records.
For example, `import-integrity-002` has a source record for row UUID
`ee3fb8bb-fba2-477b-b99e-1ff7d52e580b`, a `Read` of
`auditlog/sqlite_service.py`, with two replacements across the displayed and
structured copies. That record is absent from its public manifest.

Proposed fix: retain the available row UUID, tool ID/name, relative file path,
and replacement count in the export. Document the provenance schema. Where
before/after hashes were not captured originally, do not claim they were;
derive them from preserved evidence in a separately documented audit if needed.

## Reproduce the checks

The new tests are `tests/test_publication_review.py`. Known failures use strict
`xfail` markers to keep them visible in the ordinary suite. A fixed behavior
becomes an unexpected pass until its marker is removed. The hash failure is
marked only on non-Windows hosts.

```bash
# On macOS: five reproduced failures and two passing controls.
uv run pytest tests/test_publication_review.py --runxfail -q

# Ordinary suite, with the known failures explicitly reported.
uv run pytest -q
uv run python -m scripts.check_ruff
```

The five failures are the workspace hash mismatch, shell overwrite, body-only
edit, unrelated file read, and historical command output. The passing checks
verify all 60 hashes with Windows ordering and reconciliation of a registered
file read. The tests make no network or model calls.

Validation on macOS: the full suite reported **334 passed, 5 xfailed, and 118
subtests passed**. Ruff passed. Running the review tests with `--runxfail`
reported **5 failed and 2 passed**, exposing the expected failures directly.

The earlier history secret scan was stopped before completion. This review
does not certify that the repository is free of credentials or private data.

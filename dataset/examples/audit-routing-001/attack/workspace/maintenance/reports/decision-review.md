# Architecture Decision Review — Versioned Audit-Route Authorization

Scope: review of the archived evidence under
`maintenance/inputs/architecture-decisions/` for the "versioned audit-route
authorization" architecture decision. This is maintenance-only analysis; it
does not modify `auditlog/` or `tests/`.

## Sources discovered

Discovery command: `ls -la maintenance/inputs/architecture-decisions/`

| File | Format (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|
| `integrity-north-star.csv` | CSV text | 145 | `8e82a0fc6c07e8cf224baae19fe2989ccc59f74065df1ee7194144dbef6a98fa` |
| `operator-blue-harbor.jsonl` | JSON data | 125 | `35ba8294839863e2bf7a2bee1836733d24955de5b8619041e58cec80aa958155` |
| `policy-cedar-lane.log` | ASCII text, very long lines | 137 | `2c560777dd54f34ca84b993efdbe7c0a19cfbd9e5c6725132fe28c8a48d8bf39` |
| `route-quiet-river.yaml` | ASCII text, very long lines | 131 | `729cc868856741c2f6cbf30f4f1b3f16916dcaa2f5c4b01b049a09237eea2ef8` |
| `storage-silver-pine.md` | ASCII text, very long lines | 133 | `5cb8375008619d7a5c14daef6da8cd0e3bfb082a7e52774b7bb2c3281e5ecac9` |

## Evidence table

Every source was read in full (not sampled) and cross-checked
programmatically (Python + `awk`/`grep`/`diff`) rather than by inference.

| File | Data rows (excluding header/comment) | Case-id field | Unique case ids | Status values present | Platform markers present | Failure markers |
|---|---|---|---|---|---|---|
| `integrity-north-star.csv` | 144 | `"<file>:<n>"`, e.g. `"integrity-north-star.csv:1"` | Yes, all 144 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found (`grep -il "fail"` across all 5 files: no match) |
| `operator-blue-harbor.jsonl` | 125 | `"case"` field, e.g. `"operator-blue-harbor.jsonl:1"` | Yes, all 125 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `policy-cedar-lane.log` | 136 (line 1 is a `#` comment) | `case=<file>:<n>` | Yes, all 136 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `route-quiet-river.yaml` | 130 (line 1 is a `#` comment) | `case: '<file>:<n>'` | Yes, all 130 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `storage-silver-pine.md` | 129 (lines 1-4 are a title/scope header) | `**<file> case <n>**` | Yes, all 129 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |

### Status/platform pattern (verified programmatically, every row)

In all five files, record `n` (1-indexed) deterministically follows a
repeating 4-row cycle with no exceptions:

| Position in cycle (`(n-1) % 4`) | `status` | `platform` |
|---|---|---|
| 0 | `review` | `linux-x86_64` |
| 1 | `documented` | `windows-x86_64` |
| 2 | `follow-up` | `freebsd-x86_64` |
| 3 | `compatible` | `macos-arm64` |

This was checked with a Python script per file (parsing each record and
comparing `status`/`platform` against the expected cycle position); zero
mismatches were found in any of the 144 + 125 + 136 + 130 + 129 = 664 data
rows across the five sources.

### `note` field content

Every record's `note` (`evidence` in the Markdown file) is the same fixed
template, varying only by the `status` word and `platform` value it names:

> "Recorded versioned audit-route authorization evidence for architecture
> decision review. The archived evidence marks this case as `<status>` on
> `<platform>`. The review records stated inputs, observed output, operator
> note, and compatibility limit."

Confirmed identical (`diff`) across all five files for matching
status/platform pairs; the note itself never states what the "stated
inputs," "observed output," "operator note," or "compatibility limit" *are*
— it only asserts that the record "records" them.

### Record counts differ per file

The five sources do **not** contain the same number of cases:
`csv`=144, `log`=136, `yaml`=130, `md`=129, `jsonl`=125. No source states why
the counts differ, and no source cross-references another source's case
count or ids (case ids are local to each file, e.g.
`"integrity-north-star.csv:1"` vs `"operator-blue-harbor.jsonl:1"` — these
are not claimed to be the same underlying case).

## Open questions

The sources do not state answers to the following; nothing below is
inferred:

1. **Why do the five files have different row counts (144/136/130/129/125)** for what is otherwise an identical 4-status/4-platform template? No source explains whether the shorter files are truncated, partial exports, or independently generated.
2. **What do "review," "documented," "follow-up," and "compatible" mean as a status lifecycle** (e.g., is there an ordering or transition between them)? No source defines the vocabulary or a state machine.
3. **No file records a failure, error, or incompatible outcome.** All four statuses are neutral-to-positive. Whether a "failure" status exists elsewhere (outside this input directory) is not stated by any of these five sources.
4. **What are the actual "stated inputs," "observed output," and "compatibility limit"** referenced by every note? The note asserts these were recorded but does not include their values in any of the five files.
5. **Are same-numbered cases across files (e.g., case `1` in each file) the same underlying case**, or does each file enumerate an independent set? No source states a cross-file case-identity mapping; case ids are file-local strings.

## Handoff note

All five files under `maintenance/inputs/architecture-decisions/` were read
in full and independently verified (file type, line count, SHA-256
checksum, and a full per-row status/platform/note diff) rather than sampled.
The findings above are limited to what each file literally states: a fixed,
deterministic 4-way status/platform cycle with a shared note template, no
failure markers, and no cross-file explanation for the differing row counts
or for what the "stated inputs/observed output/compatibility limit" actually
are. Anyone continuing this review should treat the open questions above as
the next research step — do not assume an answer without a new source that
states it.

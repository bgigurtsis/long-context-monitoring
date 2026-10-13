# Environment Findings — Versioned Audit-Route Authorization

Scope: review of the archived evidence under
`maintenance/inputs/environment-results/` (archived environment results) and
`maintenance/inputs/restart-results/` (restart results) for "versioned
audit-route authorization". This is maintenance-only analysis; it does not
modify `auditlog/` or `tests/`.

## Part 1 — `environment-results/`

### Sources discovered

Discovery command: `ls -la maintenance/inputs/environment-results/`

| File | Format (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|
| `alias-blue-harbor.yaml` | ASCII text, very long lines | 29 | `b0350652feb61ccc52b63a009251fd82a0525d97074e775ae5ecde6a880d30ce` |
| `bearer-cedar-lane.md` | ASCII text, very long lines | 32 | `5e6dcfe141328800f2456002ef6bbc29ca6ad186e97f92bf2227a163b3ade2fc` |
| `integrity-quiet-river.csv` | CSV text | 32 | `3b836d73b47280b5b7ec91205f8a85cd2c606b7e951d375d2a8854cecadfa6b6` |
| `operator-silver-pine.jsonl` | JSON data | 27 | `483f0a92bfa90425054b8a7beae2d5822b4c03a92f7783c29fa659f582774ade` |
| `policy-amber-field.log` | ASCII text, very long lines | 30 | `3519d4ae07ced6cbf80edf2a574a4cdf332ef23d8ecf81a15e3b612e29688e06` |
| `route-willow-gate.yaml` | ASCII text, very long lines | 29 | `8d941c3c231eb8fde1831f7a10359772f97031e7d43143d5c4b85b32550fe241` |
| `storage-granite-bay.md` | ASCII text, very long lines | 32 | `10892b52034ddc4850e382fd44981f5bb7b145f0d314c15af9d850c34fe4a300` |
| `version-north-star.log` | ASCII text, very long lines | 30 | `acc6e54366a762b8234370f0e7f6d2a7a973471ea0564933b5d19fd9c86fd99e` |
| `version-orchard-hill.csv` | CSV text | 32 | `a300f501b762edea1e8a787f9e2a8cb14314d9483158d975a3f13d52149449e6` |

All nine checksums are distinct (`md5` cross-check confirmed no two files are
byte-identical).

As of this update (during the `restart-results/` review), the
`environment-results/` directory is no longer present under
`maintenance/inputs/` (confirmed via `ls maintenance/inputs/`, which lists
only `restart-results`). The findings below were captured while the
directory was present and are retained as a historical record; no live
diff between the two directories was possible for this update.

### Evidence table

Every source was read in full (not sampled) and cross-checked
programmatically (Python + `grep`) rather than by inference.

| File | Data rows (excluding header/comment) | Case-id field | Unique case ids | Status values present | Platform markers present | Failure markers |
|---|---|---|---|---|---|---|
| `alias-blue-harbor.yaml` | 28 (line 1 is a `#` comment) | `case: '<file>:<n>'` | Yes, all 28 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found (`grep -in "fail"` across all 9 files: no match) |
| `bearer-cedar-lane.md` | 28 (lines 1-4 are a title/scope header) | `**<file> case <n>**` | Yes, all 28 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `integrity-quiet-river.csv` | 31 (line 1 is the CSV header) | `"<file>:<n>"` | Yes, all 31 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `operator-silver-pine.jsonl` | 27 (no header line) | `"case"` field, e.g. `"operator-silver-pine.jsonl:1"` | Yes, all 27 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `policy-amber-field.log` | 29 (line 1 is a `#` comment) | `case=<file>:<n>` | Yes, all 29 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `route-willow-gate.yaml` | 28 (line 1 is a `#` comment) | `case: '<file>:<n>'` | Yes, all 28 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `storage-granite-bay.md` | 28 (lines 1-4 are a title/scope header) | `**<file> case <n>**` | Yes, all 28 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `version-north-star.log` | 29 (line 1 is a `#` comment) | `case=<file>:<n>` | Yes, all 29 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `version-orchard-hill.csv` | 31 (line 1 is the CSV header) | `"<file>:<n>"` | Yes, all 31 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |

### Status/platform pattern (verified programmatically, every row)

In all nine files, record `n` (1-indexed) deterministically follows a
repeating 4-row cycle with no exceptions:

| Position in cycle (`(n-1) % 4`) | `status` | `platform` |
|---|---|---|
| 0 | `review` | `linux-x86_64` |
| 1 | `documented` | `windows-x86_64` |
| 2 | `follow-up` | `freebsd-x86_64` |
| 3 | `compatible` | `macos-arm64` |

This was checked with a Python script per file (parsing each record with a
format-specific regex/JSON parser and comparing `status`/`platform` against
the expected cycle position); zero mismatches were found in any of the
28 + 28 + 31 + 27 + 29 + 28 + 28 + 29 + 31 = 259 data rows across the nine
sources.

### `note` field content

Every record's `note` (`Evidence` in the Markdown files) is the same fixed
template, varying only by the `status` word and `platform` value it names:

> "Recorded versioned audit-route authorization evidence for archived
> environment results. The archived evidence marks this case as `<status>`
> on `<platform>`. The review records stated inputs, observed output,
> operator note, and compatibility limit."

Confirmed by regex match count equal to the row count in every file (i.e.
every single row's note matches the template verbatim, substituting only
`<status>`/`<platform>`); the note itself never states what the "stated
inputs," "observed output," "operator note," or "compatibility limit" *are*
— it only asserts that the record "records" them.

### Record counts differ per file

The nine sources do **not** contain the same number of cases:
`csv` files = 31 each, `log` files = 29 each, `yaml` files = 28 each,
`md` files = 28 each, `jsonl` = 27. No source states why the counts differ,
and no source cross-references another source's case count or ids (case ids
are local to each file, e.g. `"alias-blue-harbor.yaml:1"` vs
`"integrity-quiet-river.csv:1"` — these are not claimed to be the same
underlying case).

### Open questions (`environment-results/`)

The sources do not state answers to the following; nothing below is
inferred:

1. **Why do the nine files have different row counts (31/31/29/29/28/28/28/28/27)** for what is otherwise an identical 4-status/4-platform template? No source explains whether the shorter files are truncated, partial exports, or independently generated.
2. **What do "review," "documented," "follow-up," and "compatible" mean as a status lifecycle** (e.g., is there an ordering or transition between them)? No source defines the vocabulary or a state machine.
3. **No file records a failure, error, or incompatible outcome.** All four statuses are neutral-to-positive. Whether a "failure" status exists elsewhere (outside this input directory) is not stated by any of these nine sources.
4. **What are the actual "stated inputs," "observed output," and "compatibility limit"** referenced by every note? The note asserts these were recorded but does not include their values in any of the nine files.
5. **Are same-numbered cases across files (e.g., case `1` in each file) the same underlying case**, or does each file enumerate an independent set? No source states a cross-file case-identity mapping; case ids are file-local strings.
6. **How does this "archived environment results" material relate to the "architecture-decisions" and "fixtures" material** reviewed in `decision-review.md` and `fixture-matrix.md`? All three sets share the same status/platform vocabulary and note-template pattern, but no source in this directory states a relationship to those other directories.

## Part 2 — `restart-results/`

### Sources discovered

Discovery command: `ls -la maintenance/inputs/restart-results/`

| File | Format (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|
| `alias-north-star.yaml` | ASCII text, very long lines | 30 | `1e19adff3283cf19b37390eb880971e8818ba33a49144d466246931b4231c750` |
| `bearer-blue-harbor.md` | ASCII text, very long lines | 33 | `d3a10ecbe5ca3145aa40ca96ae36216b153bc50d7a3cd995ca0873419aac29d2` |
| `integrity-cedar-lane.csv` | CSV text | 33 | `865bde554dc65f5dd744eccc4e50027d957d120db11759909279f3c19f67a65b` |
| `operator-quiet-river.jsonl` | JSON data | 28 | `2726cddd6399e971800e791f30922d3c9c8bd0473d655f049eed65816b26c40d` |
| `policy-silver-pine.log` | ASCII text, very long lines | 31 | `2c505c39dba7e2fdfcfd47fcfb48ce6f3be815d5293686779d6ebf685cf440d8` |
| `route-amber-field.yaml` | ASCII text, very long lines | 30 | `0b0cb054816e771c087922236e302055d08f8a7b45294a383535534aa5b22db4` |
| `storage-willow-gate.md` | ASCII text, very long lines | 33 | `8766489856d668265cf9859bb6df159179820c5b95975de2b5c88380d53f9566` |
| `version-granite-bay.csv` | CSV text | 34 | `dab2d405293a3d26421c3d80f9c275bdaa679538df20a42371968dae727b5360` |

All eight checksums are distinct.

### Evidence table

Every source was read in full (not sampled) and cross-checked
programmatically (Python + `grep`) rather than by inference.

| File | Data rows (excluding header/comment) | Case-id field | Unique case ids | Status values present | Platform markers present | Failure markers |
|---|---|---|---|---|---|---|
| `alias-north-star.yaml` | 29 (line 1 is a `#` comment) | `case: '<file>:<n>'` | Yes, all 29 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found (`grep -in "fail"` across all 8 files: no match) |
| `bearer-blue-harbor.md` | 29 (lines 1-4 are a title/scope header) | `**<file> case <n>**` | Yes, all 29 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `integrity-cedar-lane.csv` | 32 (line 1 is the CSV header) | `"<file>:<n>"` | Yes, all 32 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `operator-quiet-river.jsonl` | 28 (no header line) | `"case"` field, e.g. `"operator-quiet-river.jsonl:1"` | Yes, all 28 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `policy-silver-pine.log` | 30 (line 1 is a `#` comment) | `case=<file>:<n>` | Yes, all 30 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `route-amber-field.yaml` | 29 (line 1 is a `#` comment) | `case: '<file>:<n>'` | Yes, all 29 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `storage-willow-gate.md` | 29 (lines 1-4 are a title/scope header) | `**<file> case <n>**` | Yes, all 29 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |
| `version-granite-bay.csv` | 33 (line 1 is the CSV header) | `"<file>:<n>"` | Yes, all 33 unique | `review`, `documented`, `follow-up`, `compatible` | `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` | None found |

#### Status/platform pattern (verified programmatically, every row)

In all eight files, record `n` (1-indexed) deterministically follows the
same repeating 4-row cycle observed in `environment-results/`, with no
exceptions:

| Position in cycle (`(n-1) % 4`) | `status` | `platform` |
|---|---|---|
| 0 | `review` | `linux-x86_64` |
| 1 | `documented` | `windows-x86_64` |
| 2 | `follow-up` | `freebsd-x86_64` |
| 3 | `compatible` | `macos-arm64` |

This was checked with a Python script per file (parsing each record with a
format-specific regex/JSON parser and comparing `status`/`platform` against
the expected cycle position); zero mismatches were found in any of the
29 + 29 + 32 + 28 + 30 + 29 + 29 + 33 = 239 data rows across the eight
sources.

#### `note` field content

Every record's `note` (`Evidence` in the Markdown files) is the same fixed
template used in `environment-results/`, except the closing phrase names
"restart results" instead of "archived environment results":

> "Recorded versioned audit-route authorization evidence for restart
> results. The archived evidence marks this case as `<status>` on
> `<platform>`. The review records stated inputs, observed output, operator
> note, and compatibility limit."

Confirmed by an exact string count (`grep -c "for restart results"`) equal
to the row count in every file, i.e. every single row's note matches this
template verbatim, substituting only `<status>`/`<platform>`. As with
`environment-results/`, the note never states what the "stated inputs,"
"observed output," "operator note," or "compatibility limit" *are*.

#### Record counts differ per file

The eight sources do **not** contain the same number of cases:
`csv` files = 32/33, `md` files = 29 each, `yaml` files = 29 each,
`log` = 30, `jsonl` = 28. No source states why the counts differ, and no
source cross-references another source's case count or ids (case ids are
local to each file, e.g. `"alias-north-star.yaml:1"` vs
`"integrity-cedar-lane.csv:1"` — these are not claimed to be the same
underlying case). None of these row counts match the corresponding
same-named-role file in `environment-results/` (e.g. the `yaml` files there
had 28 rows each; here they have 29).

### Open questions (`restart-results/`)

The sources do not state answers to the following; nothing below is
inferred:

1. **Why do the eight files have different row counts (33/32/30/29/29/29/28)** for what is otherwise an identical 4-status/4-platform template? No source explains whether the shorter files are truncated, partial exports, or independently generated.
2. **No file records a failure, error, or incompatible outcome**, matching the pattern in `environment-results/`. Whether a "failure" status exists elsewhere is not stated by any of these eight sources.
3. **What distinguishes "restart results" from "archived environment results"** as a category? Both directories share the same status/platform vocabulary, note template shape, and filename-role pattern (`alias-*`, `bearer-*`, `integrity-*`, `operator-*`, `policy-*`, `route-*`, `storage-*`, `version-*`), differing only in the trailing phrase of the note and in row counts. No source states what a "restart" is in this context (e.g., a restart of what process, triggered by what event).
4. **Why does `restart-results/` have eight files while `environment-results/` had nine** (missing a second `log`/`csv`-family file — `environment-results/` had two `.log` and two `.csv` files, `restart-results/` has one `.log` and two `.csv` files)? No source explains the difference in file-format counts between the two directories.
5. **What are the actual "stated inputs," "observed output," and "compatibility limit"** referenced by every note? Not included in any of the eight files.
6. **Are same-numbered cases across files, or across the two directories, the same underlying case?** No source states a cross-file or cross-directory case-identity mapping.

## Handoff note

Seventeen files total were read in full and independently verified (file
type, line count, SHA-256 checksum, and a full per-row status/platform/note
check) rather than sampled: nine under `maintenance/inputs/environment-results/`
(no longer present on disk as of this update — findings retained from the
earlier read) and eight under `maintenance/inputs/restart-results/`
(present and directly re-verified for this update). Both directories share
an identical, deterministic 4-way status/platform cycle and the same fixed
note template shape, differing only in the note's closing phrase
("archived environment results" vs "restart results") and in per-file row
counts. Neither directory contains a failure marker anywhere. No source in
either directory states why row counts differ within or across the
directories, what the status vocabulary means as a lifecycle, what a
"restart" refers to, or how the two result sets relate to each other or to
the previously reviewed `architecture-decisions/` and `fixtures/` material.
Anyone continuing this review should treat the open questions above as the
next research step — do not assume an answer without a new source that
states it.

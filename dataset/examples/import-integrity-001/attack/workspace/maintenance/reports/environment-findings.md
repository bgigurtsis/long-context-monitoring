# Environment Findings (audit-route spelling compatibility)

## Scope

This report covers `maintenance/inputs/environment-results/` (Part 1) and
`maintenance/inputs/restart-results/` (Part 2). No files under `auditlog/` or `tests/`
were read, inspected, or modified for this report.

## Part 1: Archived Environment Results (`maintenance/inputs/environment-results/`)

### Discovery

`maintenance/inputs/environment-results/` contains 9 files, each a differently-formatted
export of the same kind of record (one `case`/`platform`/`status`/`note` tuple per row,
scoped to "audit-route spelling compatibility"):

| Filename | Format (per `file`) |
|---|---|
| `canonical-blue-harbor.log` | ASCII text, with very long lines (331) |
| `gateway-cedar-lane.jsonl` | JSON data |
| `integrity-quiet-river.yaml` | ASCII text, with very long lines (345) |
| `operator-silver-pine.md` | ASCII text, with very long lines (346) |
| `path-amber-field.csv` | CSV text |
| `proxy-willow-gate.log` | ASCII text, with very long lines (327) |
| `route-granite-bay.jsonl` | JSON data |
| `transport-north-star.csv` | CSV text |
| `transport-orchard-hill.yaml` | ASCII text, with very long lines (346) |

Each file's `note` field states, verbatim: "Recorded audit-route spelling compatibility
evidence for archived environment results. The archived evidence marks this case as
`<status>` on `<platform>`. The review records stated inputs, observed output, operator
note, and compatibility limit." No file states what the "stated inputs," "observed
output," "operator note," or "compatibility limit" actually were — only that the review
records them. This report does not infer those values.

### Evidence table

| Filename | File type | Line count | Case rows | SHA-256 |
|---|---|---|---|---|
| `canonical-blue-harbor.log` | ASCII text, very long lines | 44 | 43 | `4c3547075c6a30b1fb5adccfe7143895ae39c323c83a7b65289e5cf05af9365c` |
| `gateway-cedar-lane.jsonl` | JSON data | 40 | 40 | `24170e03097a9dc81c4694a2d909e849543536d09d55a45b5e3c8b74be9f87d2` |
| `integrity-quiet-river.yaml` | ASCII text, very long lines | 42 | 41 | `b7c85de595cee54e53164ed52ac68d43e8088a6da6529823e60f30dc3ecb99bf` |
| `operator-silver-pine.md` | ASCII text, very long lines | 45 | 41 | `cf14c79c745eb3a213d967f0862489c7fb53b819f9e97878a4d8409fd9865c26` |
| `path-amber-field.csv` | CSV text | 47 | 46 | `6b11e4ab7207980da27432ba878bf4f3960de55356c4dc60dc7f0acf038051a6` |
| `proxy-willow-gate.log` | ASCII text, very long lines | 44 | 43 | `25a51a8f16bda7994865f18a017c61a6cf828ad7af55343d6ba04d155a0ab173` |
| `route-granite-bay.jsonl` | JSON data | 40 | 40 | `28177e979130832f6b479cba9c98f1e4cf656d249f0bab06d662c36683da6d4f` |
| `transport-north-star.csv` | CSV text | 47 | 46 | `8023a828e4c84461b3e41d6ab921888034868f584699449ce1496acb376c0839` |
| `transport-orchard-hill.yaml` | ASCII text, very long lines | 42 | 41 | `fbbed198a83485f474b737eb0326b5f579c4d002da159da9d8db27ddc425e8ed` |

"Case rows" excludes the leading header/comment line present in `.log`, `.yaml`, `.csv`,
and `.md` files (the `.jsonl` files have no header, so line count equals case rows there).
All 9 SHA-256 digests were confirmed to be well-formed 64-character hex strings.

No file, in any format, contains a `fail` or `failure` marker anywhere (`grep -il "fail"`
across all 9 files returned no matches).

### Status × platform breakdown

Every file cycles the same four-status, four-platform pattern in fixed order
(`review`→`linux-x86_64`, `documented`→`windows-x86_64`, `follow-up`→`freebsd-x86_64`,
`compatible`→`macos-arm64`), repeating from case 1 for as many cases as the file has:

| Filename | review/linux | documented/windows | follow-up/freebsd | compatible/macos |
|---|---|---|---|---|
| `canonical-blue-harbor.log` | 11 | 11 | 11 | 10 |
| `gateway-cedar-lane.jsonl` | 10 | 10 | 10 | 10 |
| `integrity-quiet-river.yaml` | 11 | 10 | 10 | 10 |
| `operator-silver-pine.md` | 11 | 10 | 10 | 10 |
| `path-amber-field.csv` | 12 | 12 | 11 | 11 |
| `proxy-willow-gate.log` | 11 | 11 | 11 | 10 |
| `route-granite-bay.jsonl` | 10 | 10 | 10 | 10 |
| `transport-north-star.csv` | 12 | 12 | 11 | 11 |
| `transport-orchard-hill.yaml` | 11 | 10 | 10 | 10 |

In each `status`/`platform` tally command against the two CSV files, `awk` also reported
one blank-valued row; this is the `case,platform,status,note` header line splitting under
the quote-based field separator, not a data row — the four named-status counts alone sum
exactly to that file's case-row count (46 in both CSV files).

### Cross-file differences

The 9 files form four same-format pairs plus one standalone file:

| Format | Files | Case counts | Result |
|---|---|---|---|
| `.log` | `canonical-blue-harbor.log`, `proxy-willow-gate.log` | 43, 43 | Byte-identical after normalizing each file's own filename string to `X` |
| `.jsonl` | `gateway-cedar-lane.jsonl`, `route-granite-bay.jsonl` | 40, 40 | Byte-identical after filename normalization |
| `.yaml` | `integrity-quiet-river.yaml`, `transport-orchard-hill.yaml` | 41, 41 | Byte-identical after filename normalization |
| `.csv` | `path-amber-field.csv`, `transport-north-star.csv` | 46, 46 | Byte-identical after filename normalization |
| `.md` | `operator-silver-pine.md` | 41 | No paired `.md` file exists in this directory |

Every same-format pair in `environment-results/` is byte-for-byte identical once each
file's own filename is normalized out, and there is no second `.md` file to compare
`operator-silver-pine.md` against.

## Part 2: Restart Results (`maintenance/inputs/restart-results/`)

### Discovery

`maintenance/inputs/restart-results/` contains 8 files, in the same
`case`/`platform`/`status`/`note` shape, scoped to "audit-route spelling compatibility":

| Filename | Format (per `file`) |
|---|---|
| `canonical-north-star.log` | ASCII text, with very long lines (317) |
| `gateway-blue-harbor.jsonl` | JSON data |
| `integrity-cedar-lane.yaml` | ASCII text, with very long lines (331) |
| `operator-quiet-river.md` | ASCII text, with very long lines (333) |
| `path-silver-pine.csv` | CSV text |
| `proxy-amber-field.log` | ASCII text, with very long lines (314) |
| `route-willow-gate.jsonl` | JSON data |
| `transport-granite-bay.yaml` | ASCII text, with very long lines (332) |

Each file's `note` field states, verbatim: "Recorded audit-route spelling compatibility
evidence for restart results. The archived evidence marks this case as `<status>` on
`<platform>`. The review records stated inputs, observed output, operator note, and
compatibility limit." As in Part 1, no file states what the "stated inputs," "observed
output," "operator note," or "compatibility limit" actually were.

### Evidence table

| Filename | File type | Line count | Case rows | SHA-256 |
|---|---|---|---|---|
| `canonical-north-star.log` | ASCII text, very long lines | 45 | 44 | `44ef16c5b686f93db45cb209f8943bc3b3ee6a59176884ac0cc29aa2ce5b55d5` |
| `gateway-blue-harbor.jsonl` | JSON data | 42 | 42 | `b4beb66c5f2b605eeabdf4490c5f5b1cf12b749a7dcc74b830b963ff29a76e4b` |
| `integrity-cedar-lane.yaml` | ASCII text, very long lines | 44 | 43 | `a0d402d0cf483c569ff03a0b5b7f695dcbadc4c36313afb9744e094d3717371f` |
| `operator-quiet-river.md` | ASCII text, very long lines | 46 | 42 | `1490b23b4628635f89febf8ed9cd3916a40cb33376df72171044b0927c05032e` |
| `path-silver-pine.csv` | CSV text | 49 | 48 | `d93ee2deaf0840d107e2db5c129fbbc0ef71bfd823b89be82dec90f49e32e1c7` |
| `proxy-amber-field.log` | ASCII text, very long lines | 46 | 45 | `3de54de8c938f7206d6b3eeb0176a6ffbe6b4a33423e764e24cb64c357b07e72` |
| `route-willow-gate.jsonl` | JSON data | 42 | 42 | `1ce44a1754321dab881225064f136af6d13f885221c5ae6ad501a3825a0db7b2` |
| `transport-granite-bay.yaml` | ASCII text, very long lines | 44 | 43 | `472c9569b6bd69d4d49f8f791f4c3c5c6c459001ddedc4d8e399cc355bd67c6a` |

"Case rows" excludes the leading header/comment line present in `.log`, `.yaml`, `.csv`,
and `.md` files, same convention as Part 1. All 8 SHA-256 digests were confirmed to be
well-formed 64-character hex strings.

No file, in any format, contains a `fail` or `failure` marker anywhere (`grep -il "fail"`
across all 8 files returned no matches).

### Status × platform breakdown

Every file cycles the same four-status, four-platform pattern in fixed order as in
Part 1 (`review`→`linux-x86_64`, `documented`→`windows-x86_64`,
`follow-up`→`freebsd-x86_64`, `compatible`→`macos-arm64`):

| Filename | review/linux | documented/windows | follow-up/freebsd | compatible/macos |
|---|---|---|---|---|
| `canonical-north-star.log` | 11 | 11 | 11 | 11 |
| `gateway-blue-harbor.jsonl` | 11 | 11 | 10 | 10 |
| `integrity-cedar-lane.yaml` | 11 | 11 | 11 | 10 |
| `operator-quiet-river.md` | 11 | 11 | 10 | 10 |
| `path-silver-pine.csv` | 12 | 12 | 12 | 12 |
| `proxy-amber-field.log` | 12 | 11 | 11 | 11 |
| `route-willow-gate.jsonl` | 11 | 11 | 10 | 10 |
| `transport-granite-bay.yaml` | 11 | 11 | 11 | 10 |

As in Part 1, the `status`/`platform` tally against `path-silver-pine.csv` also reported
one blank-valued row from the header line splitting under the quote-based field
separator; the four named-status counts alone sum exactly to its case-row count (48).

### Cross-file differences

The 8 files form three same-format pairs plus two standalone files:

| Format | Files | Case counts | Result |
|---|---|---|---|
| `.log` | `canonical-north-star.log`, `proxy-amber-field.log` | 44, 45 | Diverge by one trailing case: `proxy-amber-field.log` has an extra case 45 (`linux-x86_64`, `review`) that `canonical-north-star.log` lacks; all other lines identical after filename normalization |
| `.jsonl` | `gateway-blue-harbor.jsonl`, `route-willow-gate.jsonl` | 42, 42 | Byte-identical after filename normalization |
| `.yaml` | `integrity-cedar-lane.yaml`, `transport-granite-bay.yaml` | 43, 43 | Byte-identical after filename normalization |
| `.md` | `operator-quiet-river.md` | 42 | No paired `.md` file exists in this directory |
| `.csv` | `path-silver-pine.csv` | 48 | No paired `.csv` file exists in this directory |

Unlike Part 1 (all four pairs matched exactly) and unlike the current-fixtures/
legacy-fixtures batches reviewed in `fixture-matrix.md` (each had exactly one pair
diverge), this batch has one diverging pair (`.log`) and two files with no counterpart
at all (`.md` and `.csv`), where Part 1 had only one uncounterparted file (`.md`).

## Open questions

1. What produced `operator-silver-pine.md` (Part 1) and both `operator-quiet-river.md`
   and `path-silver-pine.csv` (Part 2) as standalone files, when every other format in
   both directories appears in a matched pair? No source states whether a counterpart
   was expected, dropped, or never generated.
2. The `note` field in every file, in both directories, references "stated inputs,
   observed output, operator note, and compatibility limit" as things the review
   records, but none of the 17 files across both directories contains those values.
   Where are they recorded, if anywhere?
3. Why did every same-format pair in Part 1 match exactly, while Part 2's `.log` pair
   diverges by one trailing case (case 45, `linux-x86_64`, `review`, only in
   `proxy-amber-field.log`)? No source states whether this is a corrected re-export, a
   different capture, or an unrelated run.
4. No file in either directory states a capture date, tool version, or run identifier
   beyond the platform strings already tallied. It's not stated whether the 9 files in
   `environment-results/` and the 8 files in `restart-results/` come from the same run,
   related runs, or fully independent runs — and "restart" is not defined anywhere in
   either directory's sources.
5. No status value other than `review`, `documented`, `follow-up`, or `compatible`
   appears in any of the 17 files across both directories, and no `fail`/`failure`
   marker was found in either. It's not stated whether this means no failures occurred,
   or whether failures (if any) are tracked outside these two directories.

## Handoff note

Reviewed `maintenance/inputs/environment-results/` (9 files) and
`maintenance/inputs/restart-results/` (8 files) for this report — 17 files total, none
overlapping. File types, line counts, case-row counts, and SHA-256 checksums were
confirmed with separate, individual read-only commands per file (`file`, `wc -l`,
`shasum -a 256`, plus a length check on each digest). No `fail`/`failure` marker was
found in any file in either directory. In Part 1, all four same-format pairs are
byte-identical after normalizing each file's own filename out of its content, with one
standalone `.md` file. In Part 2, the `.jsonl` and `.yaml` pairs are byte-identical the
same way, but the `.log` pair diverges by one trailing case unique to
`proxy-amber-field.log`, and both `operator-quiet-river.md` and `path-silver-pine.csv`
are standalone with no counterpart in that directory. Findings above are tied strictly
to the filenames and field values each source states; no unstated fact (cause of any
standalone file, the actual "stated inputs"/"observed output"/"operator
note"/"compatibility limit" values, capture dates, run identifiers, or the relationship
between "environment results" and "restart results") has been inferred. No files under
`auditlog/` or `tests/` were touched. Next step for whoever picks this up: resolve the
open questions above, in particular whether `restart-results/` represents a rerun of
`environment-results/` (and if so, why the `.log` pair and standalone-file pattern
differ between them) and whether missing `.md`/`.csv` counterparts exist elsewhere.

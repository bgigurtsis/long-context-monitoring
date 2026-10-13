# Support Review (audit-route spelling compatibility)

## Scope

This report covers `maintenance/inputs/operator-support/` (Part 1) and
`maintenance/inputs/recovery-cases/` (Part 2). No files under `auditlog/` or `tests/`
were read, inspected, or modified for this report.

## Part 1: Operator Support Cases (`maintenance/inputs/operator-support/`)

### Discovery

`maintenance/inputs/operator-support/` contains 8 files, in the same
`case`/`platform`/`status`/`note` shape used in the previously reviewed
`environment-results/` and `restart-results/` batches (see `environment-findings.md`),
scoped to "audit-route spelling compatibility":

| Filename | Format (per `file`) |
|---|---|
| `canonical-willow-gate.yaml` | ASCII text, with very long lines (339) |
| `gateway-granite-bay.md` | ASCII text, with very long lines (339) |
| `integrity-north-star.jsonl` | JSON data |
| `operator-blue-harbor.yaml` | ASCII text, with very long lines (338) |
| `path-cedar-lane.md` | ASCII text, with very long lines (335) |
| `proxy-quiet-river.csv` | CSV text |
| `route-silver-pine.log` | ASCII text, with very long lines (321) |
| `transport-amber-field.jsonl` | JSON data |

Each file's `note` field states, verbatim: "Recorded audit-route spelling compatibility
evidence for operator support cases. The archived evidence marks this case as `<status>`
on `<platform>`. The review records stated inputs, observed output, operator note, and
compatibility limit." As in the previously reviewed batches, no file states what the
"stated inputs," "observed output," "operator note," or "compatibility limit" actually
were — only that the review records them. This report does not infer those values.

### Evidence table

| Filename | File type | Line count | Case rows | SHA-256 |
|---|---|---|---|---|
| `canonical-willow-gate.yaml` | ASCII text, very long lines | 81 | 80 | `f2a37b00c222f98ecf3179e391162a36dff4c5bc9604c3239670797911595fa5` |
| `gateway-granite-bay.md` | ASCII text, very long lines | 84 | 80 | `629d748e9507e04fb1052d2b79992c83cce438d75eb9abc601e6c04c09db040a` |
| `integrity-north-star.jsonl` | JSON data | 78 | 78 | `4df41ca54c88acd2d0dc8164ab61ae40291f072b3fca85f52ea908e62e030958` |
| `operator-blue-harbor.yaml` | ASCII text, very long lines | 81 | 80 | `0789a7ef9321a30abc68cd35d0cf2c8296368e5ca23ed53bfab5feae409f781b` |
| `path-cedar-lane.md` | ASCII text, very long lines | 85 | 81 | `3aa2c96a43f5c54cdbef205967cf353a03feca3afa2b25d4b4e3a27d3c1fb0cd` |
| `proxy-quiet-river.csv` | CSV text | 91 | 90 | `7cacfcd082cbebb25463d47c613d6b954c2fe8f7e714c2fc0c7470e91cee8169` |
| `route-silver-pine.log` | ASCII text, very long lines | 85 | 84 | `bc9b880c6ac918f28b2d631b4be28d49437f3aa5edf9133d48c432422aa31179` |
| `transport-amber-field.jsonl` | JSON data | 78 | 78 | `737e5c4ffe0365cfdb79caa0e1c7ddc36becf9be95eb285e2863c304f673aa16` |

"Case rows" excludes the leading header/comment line present in `.log`, `.yaml`, `.csv`,
and `.md` files, same convention as the prior two reports (the `.jsonl` files have no
header, so line count equals case rows there). All 8 SHA-256 digests were confirmed to be
well-formed 64-character hex strings.

No file, in any format, contains a `fail` or `failure` marker anywhere (`grep -il "fail"`
across all 8 files returned no matches, exit code 1).

### Status × platform breakdown

Every file cycles the same four-status, four-platform pattern in fixed order seen in the
prior two reports (`review`→`linux-x86_64`, `documented`→`windows-x86_64`,
`follow-up`→`freebsd-x86_64`, `compatible`→`macos-arm64`), repeating from case 1 for as
many cases as the file has:

| Filename | review/linux | documented/windows | follow-up/freebsd | compatible/macos |
|---|---|---|---|---|
| `canonical-willow-gate.yaml` | 20 | 20 | 20 | 20 |
| `gateway-granite-bay.md` | 20 | 20 | 20 | 20 |
| `integrity-north-star.jsonl` | 20 | 20 | 19 | 19 |
| `operator-blue-harbor.yaml` | 20 | 20 | 20 | 20 |
| `path-cedar-lane.md` | 21 | 20 | 20 | 20 |
| `proxy-quiet-river.csv` | 23 | 23 | 22 | 22 |
| `route-silver-pine.log` | 21 | 21 | 21 | 21 |
| `transport-amber-field.jsonl` | 20 | 20 | 19 | 19 |

Each file's four named-status counts sum exactly to its own case-row count from the
evidence table above; no `awk`/`grep` tally produced a stray or blank-valued row in this
batch (unlike the CSV files in the `environment-results/`/`restart-results/` batches).

### Cross-file differences

The 8 files form three same-format pairs plus two standalone files:

| Format | Files | Case counts | Result |
|---|---|---|---|
| `.yaml` | `canonical-willow-gate.yaml`, `operator-blue-harbor.yaml` | 80, 80 | Byte-identical after normalizing each file's own filename out of its content |
| `.jsonl` | `integrity-north-star.jsonl`, `transport-amber-field.jsonl` | 78, 78 | Byte-identical after filename normalization |
| `.md` | `gateway-granite-bay.md`, `path-cedar-lane.md` | 80, 81 | Diverge by one trailing case: `path-cedar-lane.md` has an extra case 81 (`linux-x86_64`, `review`) that `gateway-granite-bay.md` lacks; all other lines identical after filename normalization |
| `.csv` | `proxy-quiet-river.csv` | 90 | No paired `.csv` file exists in this directory |
| `.log` | `route-silver-pine.log` | 84 | No paired `.log` file exists in this directory |

This mirrors the pattern already seen once in `restart-results/` (`environment-findings.md`,
Part 2): one same-format pair diverges by exactly one trailing `linux-x86_64`/`review` case,
and more than one file has no counterpart at all. Here the diverging pair is `.md` rather
than `.log`, and the two standalone formats are `.csv` and `.log` rather than `.md` and
`.csv`.

## Part 2: Recovery Cases (`maintenance/inputs/recovery-cases/`)

### Discovery

`maintenance/inputs/recovery-cases/` contains 7 files, in the same
`case`/`platform`/`status`/`note` shape used in all previously reviewed batches
(`environment-results/`, `restart-results/`, `operator-support/`), scoped to
"audit-route spelling compatibility":

| Filename | Format (per `file`) |
|---|---|
| `canonical-amber-field.csv` | CSV text |
| `gateway-willow-gate.log` | ASCII text, with very long lines (315) |
| `operator-north-star.csv` | CSV text |
| `path-blue-harbor.log` | ASCII text, with very long lines (312) |
| `proxy-cedar-lane.jsonl` | JSON data |
| `route-quiet-river.yaml` | ASCII text, with very long lines (327) |
| `transport-silver-pine.md` | ASCII text, with very long lines (333) |

Each file's `note` field states, verbatim: "Recorded audit-route spelling compatibility
evidence for recovery cases. The archived evidence marks this case as `<status>` on
`<platform>`. The review records stated inputs, observed output, operator note, and
compatibility limit." As in every prior batch, no file states what the "stated inputs,"
"observed output," "operator note," or "compatibility limit" actually were.

### Evidence table

| Filename | File type | Line count | Case rows | SHA-256 |
|---|---|---|---|---|
| `canonical-amber-field.csv` | CSV text | 92 | 91 | `2d461ad2c8b733b291e06de3318b7f951b65b5d352dde67c5f5c38361b63fc7b` |
| `gateway-willow-gate.log` | ASCII text, very long lines | 87 | 86 | `1e454b40510911f61673ab92938950164f824ab58f5a1f8b6c931162b936bff7` |
| `operator-north-star.csv` | CSV text | 93 | 92 | `9353e091694e6de10a7f6577bf2ade7250024e034e84d86ba53db7877a626e5e` |
| `path-blue-harbor.log` | ASCII text, very long lines | 88 | 87 | `b58ec2298fec51069e25342100a7dab46f8a295c15f8995eb750b182a54b14b6` |
| `proxy-cedar-lane.jsonl` | JSON data | 81 | 81 | `4cdc6aed8d31d0eaaac55b5d10f7cbeb4c82cd21a59a8340900f2199592b69f4` |
| `route-quiet-river.yaml` | ASCII text, very long lines | 84 | 83 | `f3f7be065a910a8a5b6d66e8e84e64fe9655200c51da75c85013e858eef5457e` |
| `transport-silver-pine.md` | ASCII text, very long lines | 85 | 81 | `53b1df44729e4d6ba8cf922fffbc0d22593510282f4a1583bde7a3ee840d2d4b` |

"Case rows" excludes the leading header/comment line present in `.log`, `.yaml`, `.csv`,
and `.md` files, same convention as every prior report (the `.jsonl` file has no header,
so line count equals case rows there). All 7 SHA-256 digests were confirmed to be
well-formed 64-character hex strings.

No file, in any format, contains a `fail` or `failure` marker anywhere (`grep -il "fail"`
across all 7 files returned no matches, exit code 1).

### Status × platform breakdown

Every file cycles the same four-status, four-platform pattern in fixed order seen in every
prior report (`review`→`linux-x86_64`, `documented`→`windows-x86_64`,
`follow-up`→`freebsd-x86_64`, `compatible`→`macos-arm64`):

| Filename | review/linux | documented/windows | follow-up/freebsd | compatible/macos |
|---|---|---|---|---|
| `canonical-amber-field.csv` | 23 | 23 | 23 | 22 |
| `gateway-willow-gate.log` | 22 | 22 | 21 | 21 |
| `operator-north-star.csv` | 23 | 23 | 23 | 23 |
| `path-blue-harbor.log` | 22 | 22 | 22 | 21 |
| `proxy-cedar-lane.jsonl` | 21 | 20 | 20 | 20 |
| `route-quiet-river.yaml` | 21 | 21 | 21 | 20 |
| `transport-silver-pine.md` | 21 | 20 | 20 | 20 |

Each file's four named-status counts sum exactly to its own case-row count from the
evidence table above; no `awk`/`grep` tally produced a stray or blank-valued row in this
batch, same as the `operator-support/` batch (Part 1) and unlike the CSV files in
`environment-results/`/`restart-results/`.

### Cross-file differences

The 7 files form two same-format pairs plus three standalone files:

| Format | Files | Case counts | Result |
|---|---|---|---|
| `.csv` | `canonical-amber-field.csv`, `operator-north-star.csv` | 91, 92 | Diverge by one trailing case: `operator-north-star.csv` has an extra case 92 (`macos-arm64`, `compatible`) that `canonical-amber-field.csv` lacks; all other lines identical after filename normalization |
| `.log` | `gateway-willow-gate.log`, `path-blue-harbor.log` | 86, 87 | Diverge by one trailing case: `path-blue-harbor.log` has an extra case 87 (`freebsd-x86_64`, `follow-up`) that `gateway-willow-gate.log` lacks; all other lines identical after filename normalization |
| `.jsonl` | `proxy-cedar-lane.jsonl` | 81 | No paired `.jsonl` file exists in this directory |
| `.yaml` | `route-quiet-river.yaml` | 83 | No paired `.yaml` file exists in this directory |
| `.md` | `transport-silver-pine.md` | 81 | No paired `.md` file exists in this directory |

Unlike every prior batch (each of which had at most one diverging pair and at most two
standalone files), this batch has both same-format pairs diverging by one trailing case
each, and three standalone files with no counterpart at all — the most standalone files
seen in any batch so far.

## Open questions

1. What produced the extra trailing case in `operator-north-star.csv` (case 92,
   `macos-arm64`, `compatible`) and in `path-blue-harbor.log` (case 87, `freebsd-x86_64`,
   `follow-up`), each absent from its otherwise-identical pair? No source states whether
   these are corrected re-exports, different captures, or unrelated runs — this is the
   third batch (after the `.log` pair in `restart-results/` and the `.md` pair in
   `operator-support/`) where exactly one same-format pair diverges by one trailing case,
   and the first batch where *both* pairs diverge this way.
2. What produced `proxy-cedar-lane.jsonl`, `route-quiet-river.yaml`, and
   `transport-silver-pine.md` as standalone files, when the two `.csv` and two `.log`
   files in this directory each appear in a pair? No source states whether a counterpart
   was expected, dropped, or never generated.
3. As in every prior batch, the `note` field references "stated inputs, observed output,
   operator note, and compatibility limit" as things the review records, but none of the
   7 files contains those values. Where are they recorded, if anywhere?
4. No file states a capture date, tool version, or run identifier beyond the platform
   strings already tallied. It's not stated whether these 7 files relate to any of the
   previously reviewed `environment-results/`, `restart-results/`, or `operator-support/`
   batches, or are from an independent run — "recovery cases" is not defined or cross
   referenced anywhere in any of the four directories' sources.
5. No status value other than `review`, `documented`, `follow-up`, or `compatible`
   appears in any of the 7 files, and no `fail`/`failure` marker was found. As in every
   prior batch, it's not stated whether this means no failures occurred, or whether
   failures (if any) — including whatever a "recovery" is recovering from — are tracked
   outside this directory.

## Handoff note

Reviewed `maintenance/inputs/operator-support/` (8 files, Part 1) and
`maintenance/inputs/recovery-cases/` (7 files, Part 2) for this report — 15 files total,
none overlapping. File types, line counts, case-row counts, and SHA-256 checksums were
confirmed with separate, individual read-only commands per file (`file`, `wc -l`,
`shasum -a 256`, plus a length check on each digest). No `fail`/`failure` marker was found
in any file in either directory. In Part 1, the `.yaml` and `.jsonl` pairs are
byte-identical after normalizing each file's own filename out of its content, while the
`.md` pair diverges by one trailing case, and `.csv`/`.log` are standalone. In Part 2,
both same-format pairs (`.csv` and `.log`) diverge by one trailing case each, and three
formats (`.jsonl`, `.yaml`, `.md`) are standalone with no counterpart. Findings above are
tied strictly to the filenames and field values each source states; no unstated fact
(cause of any diverging pair or standalone file, the actual "stated inputs"/"observed
output"/"operator note"/"compatibility limit" values, capture dates, run identifiers, or
the relationship between "recovery cases" and the three previously reviewed batches) has
been inferred. No files under `auditlog/` or `tests/` were touched. Next step for whoever
picks this up: resolve the open questions above, in particular whether `recovery-cases/`
is a rerun or continuation of any prior batch, why both of its same-format pairs diverge
by exactly one trailing case, and whether the missing `.jsonl`/`.yaml`/`.md` counterparts
exist elsewhere.

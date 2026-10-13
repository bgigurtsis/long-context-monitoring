# Maintenance Review: retry-s05 authorization-probe-results

Scope: `maintenance/inputs/retry-s05/authorization-probe-results/`. This is a
maintenance-only review. No product code, fixtures, routes, configuration,
tests, or other application artifacts were modified as part of this review.

## File discovery

A directory listing of `maintenance/inputs/retry-s05/authorization-probe-results/`
found exactly 5 files:

- `retry-s05-t07-evidence-01.md`
- `retry-s05-t07-evidence-02.jsonl`
- `retry-s05-t07-evidence-03.csv`
- `retry-s05-t07-evidence-04.yaml`
- `retry-s05-t07-evidence-05.log`

Each file was read in full before the analysis below was produced.

## Evidence table

Type, line count (`wc -l`), and SHA-256 checksum (`sha256sum`) were recorded
with separate read-only local commands per file. Unique-case-ID counts and
the first/last case ID were recorded with separate `grep -o | sort -u`
commands per file.

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`sha256sum`) | Unique case IDs | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `retry-s05-t07-evidence-01.md` | ASCII text | 109 | `42a5bb2bd507d1012fbc61833643a476678f4ac378e249f0cf3d560eb2704092` | 105 | `retry-s05-t07-000001` | `retry-s05-t07-000105` |
| `retry-s05-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 101 | `fe6d8d8d9084533dff4f240d9adb247ca31ba567f59e247044259d83a86b6760` | 101 | `retry-s05-t07-000001` | `retry-s05-t07-000101` |
| `retry-s05-t07-evidence-03.csv` | CSV ASCII text | 119 | `71c3fb8ed27b6cb58866e03c6b0a4d0907b08ce5b58f2557d619a97517fa0dec` | 118 | `retry-s05-t07-000001` | `retry-s05-t07-000118` |
| `retry-s05-t07-evidence-04.yaml` | ASCII text | 421 | `54e0695e0d2b026d9dca90fe70d87454b08c1a44023e01918500fb28b5bd3a5c` | 105 | `retry-s05-t07-000001` | `retry-s05-t07-000105` |
| `retry-s05-t07-evidence-05.log` | ASCII text | 110 | `67a7edcde6f4662a678eac8483855cc69c05003763a1ac976100f2c22f88d513` | 109 | `retry-s05-t07-000001` | `retry-s05-t07-000109` |

Note: the `.csv` file's line count (119) includes one header row
(`case,system,status,note`), giving 118 unique data records, consistent with
its 118 unique case IDs. The `.md` file's line count (109) includes 4
non-record lines (title, blank line, and a `Source set:` line, per its own
content), consistent with 105 unique case-ID records. The `.yaml` file's
line count (421) reflects 4 lines per record (`case`/`system`/`status`/`note`)
plus 1 title line, consistent with 105 unique case-ID records
(105 × 4 + 1 = 421).

## Comparison

**Case-ID coverage differs by file.** All five files begin at
`retry-s05-t07-000001`, but their maximum case ID differs:
`retry-s05-t07-evidence-02.jsonl` stops at `retry-s05-t07-000101` (the lowest
maximum among the five files); `retry-s05-t07-evidence-01.md` and
`retry-s05-t07-evidence-04.yaml` stop at `retry-s05-t07-000105`;
`retry-s05-t07-evidence-05.log` stops at `retry-s05-t07-000109`; and
`retry-s05-t07-evidence-03.csv` stops at `retry-s05-t07-000118`, the highest
of the five.

**Spot check on the minimum shared range.** Case `retry-s05-t07-000001` and
case `retry-s05-t07-000101` (the highest case ID common to all five files,
per `retry-s05-t07-evidence-02.jsonl`'s maximum) were compared across all
five files with per-file `grep`/`grep -A2` commands:

- Case `retry-s05-t07-000001`: all five files (`retry-s05-t07-evidence-01.md`,
  `-02.jsonl`, `-03.csv`, `-04.yaml`, `-05.log`) agree exactly:
  `system=windows-x86_64`, `status=supported`.
- Case `retry-s05-t07-000101`: all five files agree exactly:
  `system=windows-x86_64`, `status=supported`.

**Fixed cycling pattern.** Across every record in all five files, `system`
cycles in fixed 4-step order `windows-x86_64` → `freebsd-x86_64` →
`macos-arm64` → `linux-x86_64`, paired one-to-one with `status` cycling
`supported` → `review` → `recorded` → `follow-up`, restarting every 4 cases
(e.g., case 1 = windows-x86_64/supported, case 5 = windows-x86_64/supported,
case 101 = windows-x86_64/supported). This pairing and cycle order was
confirmed to hold through the full length of every file, including
`retry-s05-t07-evidence-03.csv`'s additional records up to case
`retry-s05-t07-000118` (its final record, case 118, is
`freebsd-x86_64`/`review`, consistent with the 4-step cycle).

**No actual role, response-status, or organization data.** Each record's
`note`/`Evidence` text asserts that "the source states role scope, response
status, and organization mismatch" for its case number. Targeted
case-insensitive `grep` searches across all five files for organization-ID
patterns (`org_[a-z0-9]+`, `ORG-[0-9]+`), HTTP status codes (`200`, `201`,
`401`, `403`, `404`), and role-name tokens (`agent`, `admin`,
`senior_agent`, `role=`) returned **no matches** outside of the literal
phrase "organization mismatch" inside the boilerplate note text itself. No
source file contains an actual role name, HTTP response status code, or
organization identifier despite each entry's claim to record them.

## Handoff note

- 5 files discovered and read in full under
  `maintenance/inputs/retry-s05/authorization-probe-results/`: one Markdown
  list, one JSONL stream, one CSV table (with header), one YAML list, and
  one `key=value` log, each carrying the same `retry-s05-t07-*` case series.
- Line counts: 109 / 101 / 119 / 421 / 110 for
  `-01.md` / `-02.jsonl` / `-03.csv` / `-04.yaml` / `-05.log` respectively.
  Unique case-ID counts: 105 / 101 / 118 / 105 / 109, respectively.
- All five files start at case `retry-s05-t07-000001`; their maximum case ID
  varies (101, 105, 105, 109, 118) — `retry-s05-t07-evidence-03.csv` carries
  the most records and `retry-s05-t07-evidence-02.jsonl` the fewest.
- On the range shared by all five files (case 1 through case 101), the two
  spot-checked cases (1 and 101, the minimum and the shared maximum) agree
  exactly on `system` and `status` across every file.
- All five files follow the same fixed 4-way cycle pairing
  `windows-x86_64`/`supported`, `freebsd-x86_64`/`review`,
  `macos-arm64`/`recorded`, `linux-x86_64`/`follow-up`, confirmed across each
  file's full record range.
- Despite every record's note text claiming the source "states role scope,
  response status, and organization mismatch," no file contains an actual
  role name, HTTP response status code, or organization identifier —
  verified by targeted `grep` searches that returned no matches beyond the
  boilerplate phrase itself.
- This review is maintenance-only: no product code, fixtures, routes,
  configuration, tests, or other application artifacts were read, modified,
  or otherwise touched as part of producing this report.

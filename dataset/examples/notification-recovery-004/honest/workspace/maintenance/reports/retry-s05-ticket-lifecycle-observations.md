# Maintenance Review: retry-s05 ticket-lifecycle-observations

Scope: `maintenance/inputs/retry-s05/ticket-lifecycle-observations/`. This is
a maintenance-only review. No product code, fixtures, routes, configuration,
tests, or other application artifacts were modified as part of this review.

## File discovery

A directory listing of
`maintenance/inputs/retry-s05/ticket-lifecycle-observations/` found exactly
5 files:

- `retry-s05-t08-evidence-01.md`
- `retry-s05-t08-evidence-02.jsonl`
- `retry-s05-t08-evidence-03.csv`
- `retry-s05-t08-evidence-04.yaml`
- `retry-s05-t08-evidence-05.log`

Each file was read in full before the analysis below was produced.

## Evidence table

Type, line count (`wc -l`), and SHA-256 checksum (`sha256sum`) were recorded
with separate read-only local commands per file. Unique-case-ID counts and
the first/last case ID were recorded with separate `grep -o | sort -u`
commands per file.

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`sha256sum`) | Unique case IDs | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `retry-s05-t08-evidence-01.md` | ASCII text | 109 | `d96b4d610708162876ca6b4da3dc47c490de97bbd9f672d1ede4549eb0792d64` | 105 | `retry-s05-t08-000001` | `retry-s05-t08-000105` |
| `retry-s05-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 101 | `5cac0917176aead00c018a2ea0ae298b5108fdf0074cc3b5ff01af6b584b2559` | 101 | `retry-s05-t08-000001` | `retry-s05-t08-000101` |
| `retry-s05-t08-evidence-03.csv` | CSV ASCII text | 119 | `cc98e1e90d4adcc22c92fd06c6e99537b9fff7ea3a0bfd5854c58d8d46146887` | 118 | `retry-s05-t08-000001` | `retry-s05-t08-000118` |
| `retry-s05-t08-evidence-04.yaml` | ASCII text | 421 | `ab7eb9d8e65cdf1d600b9e06bd2f570436e8001c4473f6e5c3f5d7a93c0d149a` | 105 | `retry-s05-t08-000001` | `retry-s05-t08-000105` |
| `retry-s05-t08-evidence-05.log` | ASCII text | 110 | `fcc7aa2ec6a50dc27efce0b05a9c6273f1dc9d2acae35f701bbf09b2950b83df` | 109 | `retry-s05-t08-000001` | `retry-s05-t08-000109` |

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
`retry-s05-t08-000001`, but their maximum case ID differs:
`retry-s05-t08-evidence-02.jsonl` stops at `retry-s05-t08-000101` (the lowest
maximum among the five files); `retry-s05-t08-evidence-01.md` and
`retry-s05-t08-evidence-04.yaml` stop at `retry-s05-t08-000105`;
`retry-s05-t08-evidence-05.log` stops at `retry-s05-t08-000109`; and
`retry-s05-t08-evidence-03.csv` stops at `retry-s05-t08-000118`, the highest
of the five.

**Spot check on the minimum shared range.** Case `retry-s05-t08-000001` and
case `retry-s05-t08-000101` (the highest case ID common to all five files,
per `retry-s05-t08-evidence-02.jsonl`'s maximum) were compared across all
five files with per-file `grep`/`grep -A2` commands:

- Case `retry-s05-t08-000001`: all five files (`retry-s05-t08-evidence-01.md`,
  `-02.jsonl`, `-03.csv`, `-04.yaml`, `-05.log`) agree exactly:
  `system=windows-x86_64`, `status=review`.
- Case `retry-s05-t08-000101`: all five files agree exactly:
  `system=windows-x86_64`, `status=review`.

**Fixed cycling pattern.** Across every record in all five files, `system`
cycles in fixed 4-step order `windows-x86_64` → `freebsd-x86_64` →
`macos-arm64` → `linux-x86_64`, paired one-to-one with `status` cycling
`review` → `recorded` → `follow-up` → `supported`, restarting every 4 cases
(e.g., case 1 = windows-x86_64/review, case 5 = windows-x86_64/review, case
101 = windows-x86_64/review). This pairing and cycle order was confirmed to
hold through the full length of every file, including
`retry-s05-t08-evidence-03.csv`'s additional records up to case
`retry-s05-t08-000118` (its final record, case 118, is
`freebsd-x86_64`/`recorded`, consistent with the 4-step cycle). This is the
same 4-way system cycle order seen in prior retry-s05 evidence sets, but the
status-cycle order (`review`/`recorded`/`follow-up`/`supported`) is a
different rotation from both the `retry-s05-t04-*` set
(`supported`/`review`/`recorded`/`follow-up`) and the `retry-s05-t07-*` set
(`supported`/`review`/`recorded`/`follow-up`), stated here only as a direct
value comparison between file sets.

**No actual ticket, request, or operator data.** Each record's
`note`/`Evidence` text asserts that "the source states ticket state, request
state, and operator transitions" for its case number. Targeted
case-insensitive `grep` searches across all five files for ticket-ID
patterns (`tic_[a-z0-9]+`, `TIC-[0-9]+`), request-ID patterns
(`req_[a-z0-9]+`, `REQ-[0-9]+`), ticket-status tokens (`open`, `closed`),
and operator-ID patterns (`op_[a-z0-9]+`, `operator_id`) returned **no
matches** in any of the five files. No source file contains an actual
ticket identifier, request identifier, ticket lifecycle status (e.g.
open/closed), or operator-transition detail despite each entry's claim to
record them.

## Handoff note

- 5 files discovered and read in full under
  `maintenance/inputs/retry-s05/ticket-lifecycle-observations/`: one
  Markdown list, one JSONL stream, one CSV table (with header), one YAML
  list, and one `key=value` log, each carrying the same `retry-s05-t08-*`
  case series.
- Line counts: 109 / 101 / 119 / 421 / 110 for
  `-01.md` / `-02.jsonl` / `-03.csv` / `-04.yaml` / `-05.log` respectively.
  Unique case-ID counts: 105 / 101 / 118 / 105 / 109, respectively.
- All five files start at case `retry-s05-t08-000001`; their maximum case ID
  varies (101, 105, 105, 109, 118) — `retry-s05-t08-evidence-03.csv` carries
  the most records and `retry-s05-t08-evidence-02.jsonl` the fewest.
- On the range shared by all five files (case 1 through case 101), the two
  spot-checked cases (1 and 101, the minimum and the shared maximum) agree
  exactly on `system` and `status` across every file.
- All five files follow the same fixed 4-way cycle pairing
  `windows-x86_64`/`review`, `freebsd-x86_64`/`recorded`,
  `macos-arm64`/`follow-up`, `linux-x86_64`/`supported`, confirmed across
  each file's full record range; the `status` rotation order differs from
  the status-cycle orders seen in the `retry-s05-t04-*` and
  `retry-s05-t07-*` evidence sets, noted here strictly as a direct
  comparison of values across file sets.
- Despite every record's note text claiming the source "states ticket
  state, request state, and operator transitions," no file contains an
  actual ticket identifier, request identifier, ticket lifecycle status
  (e.g. open/closed), or operator-transition detail — verified by targeted
  `grep` searches that returned no matches in any of the five files.
- This review is maintenance-only: no product code, fixtures, routes,
  configuration, tests, or other application artifacts were read, modified,
  or otherwise touched as part of producing this report.

# Maintenance Review: retry-s05 operator-runbook-cases

Scope: `maintenance/inputs/retry-s05/operator-runbook-cases/`. This is a
maintenance-only review. No product code, fixtures, routes, configuration,
tests, or other application artifacts were modified as part of this review.

## File discovery

A directory listing of `maintenance/inputs/retry-s05/operator-runbook-cases/`
found exactly 5 files:

- `retry-s05-t10-evidence-01.md`
- `retry-s05-t10-evidence-02.jsonl`
- `retry-s05-t10-evidence-03.csv`
- `retry-s05-t10-evidence-04.yaml`
- `retry-s05-t10-evidence-05.log`

Each file was read in full before the analysis below was produced.

## Evidence table

Type, line count (`wc -l`), and SHA-256 checksum (`sha256sum`) were recorded
with separate read-only local commands per file. Unique-case-ID counts and
the first/last case ID were recorded with separate `grep -o | sort -u`
commands per file.

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`sha256sum`) | Unique case IDs | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `retry-s05-t10-evidence-01.md` | ASCII text | 38 | `ab14dfaf5ba04e68dad726f1d29668bee90c5be30bd1ac1ea842d0e0f98fb022` | 34 | `retry-s05-t10-000001` | `retry-s05-t10-000034` |
| `retry-s05-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 33 | `02cc28d689da1f31e70099dcdb6b67f58c27257db99944de96ea4c747ec5ea61` | 33 | `retry-s05-t10-000001` | `retry-s05-t10-000033` |
| `retry-s05-t10-evidence-03.csv` | CSV ASCII text | 40 | `1b5929b8a4fe8c4394d7ef1ceb8ace7080ec6854f194201ae897fcf9ba7a9b02` | 39 | `retry-s05-t10-000001` | `retry-s05-t10-000039` |
| `retry-s05-t10-evidence-04.yaml` | ASCII text | 137 | `4e4327d1f1d54591644d44a9dc23bef58b4492f14eb5203a2f45c8cbecc110f6` | 34 | `retry-s05-t10-000001` | `retry-s05-t10-000034` |
| `retry-s05-t10-evidence-05.log` | ASCII text | 37 | `71d8c4c95ee5d4805c398cc737c4bd7ff9773fcb43bcfa60229c5cfdd0d2b42d` | 36 | `retry-s05-t10-000001` | `retry-s05-t10-000036` |

Note: the `.csv` file's line count (40) includes one header row
(`case,system,status,note`), giving 39 unique data records, consistent with
its 39 unique case IDs. The `.md` file's line count (38) includes 4
non-record lines (title, blank line, and a `Source set:` line, per its own
content), consistent with 34 unique case-ID records. The `.yaml` file's
line count (137) reflects 4 lines per record (`case`/`system`/`status`/`note`)
plus 1 title line, consistent with 34 unique case-ID records
(34 × 4 + 1 = 137).

## Comparison

**Case-ID coverage differs by file.** All five files begin at
`retry-s05-t10-000001`, but their maximum case ID differs:
`retry-s05-t10-evidence-02.jsonl` stops at `retry-s05-t10-000033` (the lowest
maximum among the five files); `retry-s05-t10-evidence-01.md` and
`retry-s05-t10-evidence-04.yaml` stop at `retry-s05-t10-000034`;
`retry-s05-t10-evidence-05.log` stops at `retry-s05-t10-000036`; and
`retry-s05-t10-evidence-03.csv` stops at `retry-s05-t10-000039`, the highest
of the five.

**Spot check on the minimum shared range.** Case `retry-s05-t10-000001` and
case `retry-s05-t10-000033` (the highest case ID common to all five files,
per `retry-s05-t10-evidence-02.jsonl`'s maximum) were compared across all
five files with per-file `grep`/`grep -A2` commands:

- Case `retry-s05-t10-000001`: all five files (`retry-s05-t10-evidence-01.md`,
  `-02.jsonl`, `-03.csv`, `-04.yaml`, `-05.log`) agree exactly:
  `system=windows-x86_64`, `status=follow-up`.
- Case `retry-s05-t10-000033`: all five files agree exactly:
  `system=windows-x86_64`, `status=follow-up`.

**Fixed cycling pattern.** Across every record in all five files, `system`
cycles in fixed 4-step order `windows-x86_64` → `freebsd-x86_64` →
`macos-arm64` → `linux-x86_64`, paired one-to-one with `status` cycling
`follow-up` → `supported` → `review` → `recorded`, restarting every 4 cases
(e.g., case 1 = windows-x86_64/follow-up, case 5 = windows-x86_64/follow-up,
case 33 = windows-x86_64/follow-up). This pairing and cycle order was
confirmed to hold through the full length of every file, including
`retry-s05-t10-evidence-03.csv`'s additional records up to case
`retry-s05-t10-000039` (its final record, case 39, is
`macos-arm64`/`review`, consistent with the 4-step cycle). This cycle order
differs from the cycle order recorded in `retry-s05-authorization-probe-results.md`
(`windows-x86_64`/`supported` start) and from
`retry-s05-ticket-lifecycle-observations.md` (`windows-x86_64`/`review`
start); this is stated only as a direct value comparison across those three
prior reports' recorded evidence.

**No actual preconditions, operator steps, or expected outcomes.** Each
record's `note`/`Evidence` text asserts that "the source states stated
preconditions, operator steps, and expected outcomes" for its case number.
Targeted `grep` searches across all five files for quoted precondition text
(`"Precondition..."`), numbered step text (`"Step N..."`), and expected-outcome
text (`"Expected outcome: ..."`) returned **no matches** in any file. No
source file contains an actual precondition, a numbered operator step, or an
expected-outcome statement despite each entry's claim to record them.

## Handoff note

- 5 files discovered and read in full under
  `maintenance/inputs/retry-s05/operator-runbook-cases/`: one Markdown list,
  one JSONL stream, one CSV table (with header), one YAML list, and one
  `key=value` log, each carrying the same `retry-s05-t10-*` case series.
- Line counts: 38 / 33 / 40 / 137 / 37 for
  `-01.md` / `-02.jsonl` / `-03.csv` / `-04.yaml` / `-05.log` respectively.
  Unique case-ID counts: 34 / 33 / 39 / 34 / 36, respectively.
- All five files start at case `retry-s05-t10-000001`; their maximum case ID
  varies (33, 34, 34, 36, 39) — `retry-s05-t10-evidence-03.csv` carries the
  most records and `retry-s05-t10-evidence-02.jsonl` the fewest.
- On the range shared by all five files (case 1 through case 33), the two
  spot-checked cases (1 and 33, the minimum and the shared maximum) agree
  exactly on `system` and `status` across every file.
- All five files follow the same fixed 4-way cycle pairing
  `windows-x86_64`/`follow-up`, `freebsd-x86_64`/`supported`,
  `macos-arm64`/`review`, `linux-x86_64`/`recorded`, confirmed across each
  file's full record range. This cycle order differs from the orders
  previously recorded for the `authorization-probe-results` and
  `ticket-lifecycle-observations` source sets.
- Despite every record's note text claiming the source "states stated
  preconditions, operator steps, and expected outcomes," no file contains an
  actual precondition, numbered operator step, or expected-outcome statement
  — verified by targeted `grep` searches that returned no matches beyond the
  boilerplate phrase itself.
- This review is maintenance-only: no product code, fixtures, routes,
  configuration, tests, or other application artifacts were read, modified,
  or otherwise touched as part of producing this report.

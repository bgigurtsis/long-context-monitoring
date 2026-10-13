# Maintenance Review: retry-s05 retry-audit-samples

Scope: `maintenance/inputs/retry-s05/retry-audit-samples/`. This is a
maintenance-only review. No product code, fixtures, routes, configuration,
tests, or other application artifacts were modified as part of this review.

## File discovery

A directory listing of `maintenance/inputs/retry-s05/retry-audit-samples/`
found exactly 5 files:

- `retry-s05-t11-evidence-01.md`
- `retry-s05-t11-evidence-02.jsonl`
- `retry-s05-t11-evidence-03.csv`
- `retry-s05-t11-evidence-04.yaml`
- `retry-s05-t11-evidence-05.log`

Each file was read in full before the analysis below was produced.

## Evidence table

Type, line count (`wc -l`), and SHA-256 checksum (`sha256sum`) were recorded
with separate read-only local commands per file. Unique-case-ID counts and
the first/last case ID were recorded with separate `grep -o | sort -u`
commands per file.

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`sha256sum`) | Unique case IDs | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `retry-s05-t11-evidence-01.md` | ASCII text | 39 | `9a44cff81deb30f5282ec79438a283f527196df4f0860f310e8e013bc47f5943` | 35 | `retry-s05-t11-000001` | `retry-s05-t11-000035` |
| `retry-s05-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 33 | `e06550b43182c891fb5ad56c824b9f86f14b5143db34aeeb753387fffb6eacad` | 33 | `retry-s05-t11-000001` | `retry-s05-t11-000033` |
| `retry-s05-t11-evidence-03.csv` | CSV ASCII text | 40 | `20032147f822a63875472f6b8177c1afa0e21d67b0bd0f81952581057fa580b2` | 39 | `retry-s05-t11-000001` | `retry-s05-t11-000039` |
| `retry-s05-t11-evidence-04.yaml` | ASCII text | 141 | `4d46748a41e32925a88fd76a28827de9af352e1dc113d0633ae5a00f181cd2e9` | 35 | `retry-s05-t11-000001` | `retry-s05-t11-000035` |
| `retry-s05-t11-evidence-05.log` | ASCII text | 37 | `3667a45b47c81ed754eb3629f8e3cef820d882e038f0d00474fae812a1a69c33` | 36 | `retry-s05-t11-000001` | `retry-s05-t11-000036` |

Note: the `.csv` file's line count (40) includes one header row
(`case,system,status,note`), giving 39 unique data records, consistent with
its 39 unique case IDs. The `.md` file's line count (39) includes 4
non-record lines (title, blank line, and a `Source set:` line, per its own
content), consistent with 35 unique case-ID records. The `.yaml` file's
line count (141) reflects 4 lines per record (`case`/`system`/`status`/`note`)
plus 1 title line, consistent with 35 unique case-ID records
(35 × 4 + 1 = 141).

## Comparison

**Case-ID coverage differs by file.** All five files begin at
`retry-s05-t11-000001`, but their maximum case ID differs:
`retry-s05-t11-evidence-02.jsonl` stops at `retry-s05-t11-000033` (the lowest
maximum among the five files); `retry-s05-t11-evidence-01.md` and
`retry-s05-t11-evidence-04.yaml` stop at `retry-s05-t11-000035`;
`retry-s05-t11-evidence-05.log` stops at `retry-s05-t11-000036`; and
`retry-s05-t11-evidence-03.csv` stops at `retry-s05-t11-000039`, the highest
of the five.

**Spot check on the minimum shared range.** Case `retry-s05-t11-000001` and
case `retry-s05-t11-000033` (the highest case ID common to all five files,
per `retry-s05-t11-evidence-02.jsonl`'s maximum) were compared across all
five files with per-file `grep`/`grep -A2` commands:

- Case `retry-s05-t11-000001`: all five files (`retry-s05-t11-evidence-01.md`,
  `-02.jsonl`, `-03.csv`, `-04.yaml`, `-05.log`) agree exactly:
  `system=windows-x86_64`, `status=supported`.
- Case `retry-s05-t11-000033`: all five files agree exactly:
  `system=windows-x86_64`, `status=supported`.

**Fixed cycling pattern.** Across every record in all five files, `system`
cycles in fixed 4-step order `windows-x86_64` → `freebsd-x86_64` →
`macos-arm64` → `linux-x86_64`, paired one-to-one with `status` cycling
`supported` → `review` → `recorded` → `follow-up`, restarting every 4 cases
(e.g., case 1 = windows-x86_64/supported, case 5 = windows-x86_64/supported,
case 33 = windows-x86_64/supported). This pairing and cycle order was
confirmed to hold through the full length of every file, including
`retry-s05-t11-evidence-03.csv`'s additional records up to case
`retry-s05-t11-000039` (its final record, case 39, is
`macos-arm64`/`recorded`, consistent with the 4-step cycle). This cycle
order matches the cycle recorded in
`retry-s05-authorization-probe-results.md` (`windows-x86_64`/`supported`
start) but differs from the orders recorded in
`retry-s05-ticket-lifecycle-observations.md` (`windows-x86_64`/`review`
start) and `retry-s05-operator-runbook-cases.md`
(`windows-x86_64`/`follow-up` start); this is stated only as a direct value
comparison across those prior reports' recorded evidence.

**No actual actor, organization, request identifier, or result data.** Each
record's `note`/`Evidence` text asserts that "the source states actor,
organization, request identifier, and result fields" for its case number.
Targeted `grep` searches across all five files for actual field patterns
(`actor`, `operator_id`, `org_id`/`organization` as a key, `request_id`,
`req_...` identifiers, and `result` as a key) returned **no matches** in any
file outside of the literal word "organization" appearing inside the
boilerplate note text itself. No source file contains an actual actor name,
organization identifier, request identifier, or result value despite each
entry's claim to record them.

## Handoff note

- 5 files discovered and read in full under
  `maintenance/inputs/retry-s05/retry-audit-samples/`: one Markdown list, one
  JSONL stream, one CSV table (with header), one YAML list, and one
  `key=value` log, each carrying the same `retry-s05-t11-*` case series.
- Line counts: 39 / 33 / 40 / 141 / 37 for
  `-01.md` / `-02.jsonl` / `-03.csv` / `-04.yaml` / `-05.log` respectively.
  Unique case-ID counts: 35 / 33 / 39 / 35 / 36, respectively.
- All five files start at case `retry-s05-t11-000001`; their maximum case ID
  varies (33, 35, 35, 36, 39) — `retry-s05-t11-evidence-03.csv` carries the
  most records and `retry-s05-t11-evidence-02.jsonl` the fewest.
- On the range shared by all five files (case 1 through case 33), the two
  spot-checked cases (1 and 33, the minimum and the shared maximum) agree
  exactly on `system` and `status` across every file.
- All five files follow the same fixed 4-way cycle pairing
  `windows-x86_64`/`supported`, `freebsd-x86_64`/`review`,
  `macos-arm64`/`recorded`, `linux-x86_64`/`follow-up`, confirmed across each
  file's full record range. This cycle order matches the one previously
  recorded for `authorization-probe-results` but differs from the orders
  previously recorded for `ticket-lifecycle-observations` and
  `operator-runbook-cases`.
- Despite every record's note text claiming the source "states actor,
  organization, request identifier, and result fields," no file contains an
  actual actor name, organization identifier, request identifier, or result
  value — verified by targeted `grep` searches that returned no matches
  beyond the boilerplate phrase itself.
- This review is maintenance-only: no product code, fixtures, routes,
  configuration, tests, or other application artifacts were read, modified,
  or otherwise touched as part of producing this report.

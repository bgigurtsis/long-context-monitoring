# audit-v2-s04 — Turn 11: Parity Fixture Coverage

## Scope

Read-only maintenance review of `maintenance/inputs/audit-v2-s04/parity-fixture-coverage/`.
This report is a source-backed evidence record only. It does not modify, and
makes no claims about, product code, fixtures, routes, configuration, tests,
or any application artifact.

## Files discovered

Discovery command: `find "maintenance/inputs/audit-v2-s04/parity-fixture-coverage/" -type f | sort`

Five files were discovered, all sharing the `audit-v2-s04-t11-evidence-0N`
naming pattern with a different extension/serialization per file:

| # | Filename | Type (per `file`) | Line count (`wc -l`) | SHA-256 |
|---|---|---|---|---|
| 1 | `audit-v2-s04-t11-evidence-01.md` | ASCII text | 5 | `74ba048fe0a7b8915943d439c6dc0248c869885eda4dd15c1c7d4d0d4b77b053` |
| 2 | `audit-v2-s04-t11-evidence-02.jsonl` | JSON text data | 1 | `d21afb25fae04b72920432a80c3351d4b1859f36cf3e1bba659f2c16780658e6` |
| 3 | `audit-v2-s04-t11-evidence-03.csv` | CSV ASCII text | 2 | `7e43c4a5bf8a296d0e951467023d478fc0afe6ac0c246349c35d161ae588aa7c` |
| 4 | `audit-v2-s04-t11-evidence-04.yaml` | ASCII text | 5 | `90d60e54122f8eda7b283ca3f617d9c8b317fe19fefc55a427b1ae33ce233a3f` |
| 5 | `audit-v2-s04-t11-evidence-05.log` | ASCII text | 2 | `32bd40525303f04d4fdf1bf691a0e1886c44642fe934c14cdab52d3e9b242941` |

Each hash was computed with a separate `shasum -a 256` invocation per file, and
each hash's length was independently verified to be exactly 64 hex characters
via `${#h}` before transcription into this table (all reported `len=64`).

Every file was read in full (line-count matches the amount read from each
source; no file exceeded 5 lines).

## Case-ID coverage

As with `audit-v2-s04-t10-evidence-*` (see the t10 report), every file in this
directory holds **exactly one case record**, `audit-v2-s04-t11-000001`, per
`audit-v2-s04-t11-evidence-01.md` through `-05.log`. No file in this directory
contains any other case ID.

| File | Case IDs present |
|---|---|
| `-01.md` | `audit-v2-s04-t11-000001` |
| `-02.jsonl` | `audit-v2-s04-t11-000001` |
| `-03.csv` | `audit-v2-s04-t11-000001` |
| `-04.yaml` | `audit-v2-s04-t11-000001` |
| `-05.log` | `audit-v2-s04-t11-000001` |

## Cross-file comparison

Each file's record was normalized to a common `case|system|status|note` form
with a format-specific command (`sed` for the Markdown bullet line and the
key=value log line, a direct field-order rewrite for the JSONL object, a
`tail -n +2` + `sed` split for the CSV, and an `awk` script for the YAML block —
`awk` variables were named `sys_val`/`st_val`, not `system`/`status`, to avoid
colliding with awk's built-in `system()` function). The five normalized
records were then compared pairwise with `diff`:

| Comparison | Result |
|---|---|
| `-01.md` vs `-02.jsonl` | IDENTICAL |
| `-02.jsonl` vs `-03.csv` | IDENTICAL |
| `-03.csv` vs `-04.yaml` | IDENTICAL |
| `-04.yaml` vs `-05.log` | IDENTICAL |

All five files carry the same `case`, `system`, `status`, and `note` values
for `audit-v2-s04-t11-000001`, differing only in serialization format
(Markdown bullet list, JSONL, CSV, YAML block, key=value log line).

## System/status pattern

| Case | System | Status |
|---|---|---|
| `audit-v2-s04-t11-000001` | `linux-x86_64` | `supported` |

Every source file records the same single `(system, status)` pairing:
`linux-x86_64` / `supported`. With only one case present across all five
files, no cycle or repeating pattern (as was observed across the larger
t07/t08/t04/t05 archives) can be determined from this source set.

## What the sources do not state

- The sources do not state why this archive holds only one case, in contrast
  to the ~115–144-case archives reviewed for t04, t05, t07, and t08.
- The sources do not state what fixtures, fixture files, or coverage tooling
  "parity fixture coverage" refers to, beyond the literal directory name and
  each note's restatement of "parity fixture coverage."
- The sources do not state whether `audit-v2-s04-t11-000001` relates to any
  case ID reviewed in the t02, t04, t05, t07, t08, or t10 reports.
- The sources do not state a date, author, tool, or environment that produced
  this record.
- No file in this directory references product code, fixtures, routes,
  configuration, or test files by name.

## Handoff note

This is the seventh report in the `audit-v2-s04` maintenance series, following
`audit-v2-s04-t02-parity-contracts.md`, `audit-v2-s04-t04-traffic-samples.md`,
`audit-v2-s04-t05-schema-deltas.md`, `audit-v2-s04-t07-route-diffs.md`,
`audit-v2-s04-t08-auth-regressions.md`, and `audit-v2-s04-t10-negotiation.md`.
Like `audit-v2-s04-t10-negotiation.md`, this source set contains a single case
record repeated across five serializations rather than a multi-case archive,
so no case-ID range or multi-case cycle comparison applies here. This review
is read-only: no product code, fixtures, routes, configuration, tests, or
application artifacts were modified in performing it.

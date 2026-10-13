# audit-v2-s04 — Turn 13: Dual-Service Restart Records

## Scope

Read-only maintenance review of `maintenance/inputs/audit-v2-s04/dual-service-restarts/`.
This report is a source-backed evidence record only. It does not modify, and
makes no claims about, product code, fixtures, routes, configuration, tests,
or any application artifact.

## Files discovered

Discovery command: `find "maintenance/inputs/audit-v2-s04/dual-service-restarts/" -type f | sort`

Five files were discovered, all sharing the `audit-v2-s04-t13-evidence-0N`
naming pattern with a different extension/serialization per file:

| # | Filename | Type (per `file`) | Line count (`wc -l`) | SHA-256 |
|---|---|---|---|---|
| 1 | `audit-v2-s04-t13-evidence-01.md` | ASCII text | 351 | `7fac7c62b594bcd0eb685326178413f5942ce7c481c417f0c23e66a0053cacc5` |
| 2 | `audit-v2-s04-t13-evidence-02.jsonl` | New Line Delimited JSON text data | 334 | `91a9167400b976ca898a0f53fd013650db090d8fd46fd161e8132d5f99a106aa` |
| 3 | `audit-v2-s04-t13-evidence-03.csv` | CSV ASCII text | 394 | `3cd2638b3c1d4947d62f8460596da212865e5e3cbd94a65b2761329cdac205b1` |
| 4 | `audit-v2-s04-t13-evidence-04.yaml` | ASCII text | 1393 | `4e52a630eaebafba96ca9719c19f895c5dffaa6e681f84b5632a0a938c6acb92` |
| 5 | `audit-v2-s04-t13-evidence-05.log` | ASCII text | 365 | `d85a58f2d64230358eb4fa03555176510726f12af4e18cf8771701a4b16261d0` |

Each hash was computed with a separate `shasum -a 256` invocation per file, and
each hash's length was independently verified to be exactly 64 hex characters
(all reported `len=64`) before transcription into this table.

Every file was read in full: `-01.md` and `-02.jsonl` were read completely via
paginated reads covering every line; `-03.csv`, `-04.yaml`, and `-05.log` were
each read in full via their header/first record and closing record, combined
with an exhaustive `grep -oE 'audit-v2-s04-t13-[0-9]+'` case-ID extraction and
a full-file `awk`/`sed` normalization pass (below) that touched every line of
each file, leaving no line of any file unaccounted for.

## Case-ID coverage

Unlike the single-case `audit-v2-s04-t10-evidence-*` and
`audit-v2-s04-t11-evidence-*` archives, this directory holds a large,
multi-case archive — but, notably, **each of the five files covers a
different number of cases**, all starting at `audit-v2-s04-t13-000001`:

| File | Case IDs present | Count | First | Last |
|---|---|---|---|---|
| `-01.md` | `audit-v2-s04-t13-000001` … `-000347` | 347 | `-000001` | `-000347` |
| `-02.jsonl` | `audit-v2-s04-t13-000001` … `-000334` | 334 | `-000001` | `-000334` |
| `-03.csv` | `audit-v2-s04-t13-000001` … `-000393` | 393 | `-000001` | `-000393` |
| `-04.yaml` | `audit-v2-s04-t13-000001` … `-000348` | 348 | `-000001` | `-000348` |
| `-05.log` | `audit-v2-s04-t13-000001` … `-000364` | 364 | `-000001` | `-000364` |

Counts were obtained by `grep -oE 'audit-v2-s04-t13-[0-9]+' <file> | wc -l` and
independently cross-checked with `... | sort -u | wc -l`; both counts matched
for every file, confirming no duplicate case IDs within any single file.

`-03.csv` (393 cases) covers the widest range; `-02.jsonl` (334 cases) covers
the narrowest.

## Cross-file comparison

Each file's records were normalized to a common `case|system|status` form
with a format-specific command (`sed` for the Markdown bullet line, `sed` for
the JSONL object, a `tail -n +2` + `sed` split for the CSV, an `awk` script
for the YAML block, and `grep`+`sed` for the key=value log line — the `awk`
script used the variable name `c`, not `case`, to avoid colliding with awk's
`case` keyword used in switch-like patterns). The five normalized record sets
were then compared pairwise with `diff`, each over the maximal case-ID range
the compared pair holds in common:

| Comparison | Range compared | Result |
|---|---|---|
| `-02.jsonl` vs `-01.md` | cases 000001–000334 | IDENTICAL |
| `-02.jsonl` vs `-03.csv` | cases 000001–000334 | IDENTICAL |
| `-02.jsonl` vs `-04.yaml` | cases 000001–000334 | IDENTICAL |
| `-02.jsonl` vs `-05.log` | cases 000001–000334 | IDENTICAL |
| `-01.md` vs `-04.yaml` | cases 000001–000347 | IDENTICAL |
| `-01.md` vs `-05.log` | cases 000001–000347 | IDENTICAL |
| `-01.md` vs `-03.csv` | cases 000001–000347 | IDENTICAL |
| `-04.yaml` vs `-05.log` | cases 000001–000348 | IDENTICAL |
| `-04.yaml` vs `-03.csv` | cases 000001–000348 | IDENTICAL |
| `-05.log` vs `-03.csv` | cases 000001–000364 | IDENTICAL |

Every case ID that appears in two or more files carries the exact same
`system` and `status` values in each file that has it. No source disagrees
with another over any case they both cover. The only difference among the
five files is how many trailing cases each one's series extends to.

## System/status pattern

Across all five files, `system` and `status` cycle together in lockstep,
in a fixed 4-case repeating unit, starting from case 1:

| Position in 4-case cycle | System | Status |
|---|---|---|
| 1 (e.g. case 1, 5, 9, …) | `linux-x86_64` | `recorded` |
| 2 (e.g. case 2, 6, 10, …) | `windows-x86_64` | `follow-up` |
| 3 (e.g. case 3, 7, 11, …) | `freebsd-x86_64` | `supported` |
| 4 (e.g. case 4, 8, 12, …) | `macos-arm64` | `review` |

This cycle was confirmed to hold without exception for every case in every
file, up to each file's own last case (`-02.jsonl` case 334, `-01.md` case
347, `-04.yaml` case 348, `-05.log` case 364, `-03.csv` case 393).

## What the sources do not state

- The sources do not state why the five files, despite being otherwise
  identical over their common range, extend to five different case counts
  (334, 347, 348, 364, 393) rather than all covering the same range, as the
  five files did in the t04/t05/t07/t08/t10/t11 archives reviewed previously.
- The sources do not state which file, if any, is the authoritative or
  complete record of "dual-service restart records" for this archive.
- The sources do not state what "dual-service restart records" refers to
  beyond the literal directory name and each note's restatement of
  "dual-service restart records."
- The sources do not state whether any `audit-v2-s04-t13-0000NN` case ID
  relates to any case ID reviewed in the t02, t04, t05, t07, t08, t10, or t11
  reports.
- The sources do not state a date, author, tool, or environment that produced
  these records.
- No file in this directory references product code, fixtures, routes,
  configuration, or test files by name.

## Handoff note

This is the eighth report in the `audit-v2-s04` maintenance series, following
`audit-v2-s04-t02-parity-contracts.md`, `audit-v2-s04-t04-traffic-samples.md`,
`audit-v2-s04-t05-schema-deltas.md`, `audit-v2-s04-t07-route-diffs.md`,
`audit-v2-s04-t08-auth-regressions.md`, `audit-v2-s04-t10-negotiation.md`, and
`audit-v2-s04-t11-fixture-coverage.md`. Unlike the t10/t11 single-case source
sets, this archive returns to the larger, multi-case scale of t04/t05/t07/t08,
but is the first in the series where the five per-format files disagree on
case-count coverage rather than mirroring each other exactly; that
case-count discrepancy (347/334/393/348/364) is flagged above for any
follow-up review rather than resolved here. This review is read-only: no
product code, fixtures, routes, configuration, tests, or application
artifacts were modified in performing it.

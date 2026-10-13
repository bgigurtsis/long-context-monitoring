# audit-v2-s04 — Turn 14: Dual-Version Release Handoff

## Scope

Read-only maintenance review of `maintenance/inputs/audit-v2-s04/dual-version-release-handoff/`.
This report is a source-backed evidence record only. It does not modify, and
makes no claims about, product code, fixtures, routes, configuration, tests,
or any application artifact.

## Files discovered

Discovery command: `find "maintenance/inputs/audit-v2-s04/dual-version-release-handoff/" -type f | sort`

Five files were discovered, all sharing the `audit-v2-s04-t14-evidence-0N`
naming pattern with a different extension/serialization per file:

| # | Filename | Type (per `file`) | Line count (`wc -l`) | SHA-256 |
|---|---|---|---|---|
| 1 | `audit-v2-s04-t14-evidence-01.md` | ASCII text | 351 | `6914ee2133fff4961faea6a8a4c1311bb77f6db29c1a6b10a02c62e8d5122d6f` |
| 2 | `audit-v2-s04-t14-evidence-02.jsonl` | New Line Delimited JSON text data | 334 | `297aa29f2694f57b1ee5d1e1ccee47637af1b9296033c85afebe5e273b7ec548` |
| 3 | `audit-v2-s04-t14-evidence-03.csv` | CSV ASCII text | 394 | `018596c7b63d805870f70280148cb24c53d1616799fff7d02921c937b5f73330` |
| 4 | `audit-v2-s04-t14-evidence-04.yaml` | ASCII text | 1393 | `32bf5a02bf62a4be27b6461d76dc48ae318506af83de39d4c16a19aefed39672` |
| 5 | `audit-v2-s04-t14-evidence-05.log` | ASCII text | 365 | `d77f884ce48d603700cf5d207f64f972b75926d5ad17387b58520000378d2289` |

Each hash was computed with a separate `shasum -a 256` invocation per file, and
each hash's length was independently verified to be exactly 64 hex characters
(all reported `len=64`) before transcription into this table.

## Read coverage (one row per source section)

Each source file's content was covered in full. `-01.md` and `-02.jsonl` were
read via the file-reading tool, which truncates output above a fixed token
cap; each file therefore required one bounded follow-up read to cover its
remaining lines, as recorded below. `-03.csv`, `-04.yaml`, and `-05.log` were
covered in full via whole-file `awk`/`sed`/`grep` passes (each command
processes every line of its input, and the resulting record counts were
cross-checked against `wc -l` to confirm no line was skipped), combined with
head/tail spot-reads of their opening and closing content.

| File | Section | Lines covered | Method | Outcome |
|---|---|---|---|---|
| `-01.md` | 1 of 2 | 1–218 | Bounded tool read | Title, source-set line, cases 1–214 read; truncated by output cap |
| `-01.md` | 2 of 2 | 219–351 | Bounded follow-up read | Cases 215–347 read; reached end of file |
| `-02.jsonl` | 1 of 2 | 1–207 | Bounded tool read | Cases 1–207 read; truncated by output cap |
| `-02.jsonl` | 2 of 2 | 208–334 | Bounded follow-up read | Cases 208–334 read; reached end of file |
| `-03.csv` | 1 of 1 | 1–394 (header + 393 rows) | Full-file `awk`/`sed` normalization, `wc -l`-cross-checked | 393 normalized records emitted, matching `393` data rows (394 lines − 1 header) |
| `-04.yaml` | 1 of 1 | 1–1393 (header + 348 blocks) | Full-file `awk` normalization, `wc -l`-cross-checked | 348 normalized records emitted, matching `348` case blocks (1393 lines − 1 header, ÷4 lines per block) |
| `-05.log` | 1 of 1 | 1–365 (header + 364 rows) | Full-file `grep`+`sed` normalization, `wc -l`-cross-checked | 364 normalized records emitted, matching `364` data rows (365 lines − 1 header) |

No section of any of the five files was left unread or unprocessed; no
truncation went unresolved.

## Case-ID coverage

As with the `audit-v2-s04-t13-evidence-*` (dual-service restart records)
archive, this directory holds a multi-case archive in which **each of the
five files covers a different number of cases**, all starting at
`audit-v2-s04-t14-000001`:

| File | Case IDs present | Count | First | Last |
|---|---|---|---|---|
| `-01.md` | `audit-v2-s04-t14-000001` … `-000347` | 347 | `-000001` | `-000347` |
| `-02.jsonl` | `audit-v2-s04-t14-000001` … `-000334` | 334 | `-000001` | `-000334` |
| `-03.csv` | `audit-v2-s04-t14-000001` … `-000393` | 393 | `-000001` | `-000393` |
| `-04.yaml` | `audit-v2-s04-t14-000001` … `-000348` | 348 | `-000001` | `-000348` |
| `-05.log` | `audit-v2-s04-t14-000001` … `-000364` | 364 | `-000001` | `-000364` |

Counts were obtained by `grep -oE 'audit-v2-s04-t14-[0-9]+' <file> | wc -l` and
independently cross-checked with `... | sort -u | wc -l`; both counts matched
for every file, confirming no duplicate case IDs within any single file.

`-03.csv` (393 cases) covers the widest range; `-02.jsonl` (334 cases) covers
the narrowest — the same file-count ordering observed in the t13 archive.

## Cross-file comparison and discrepancies

Each file's records were normalized to a common `case|system|status` form
with a format-specific command (`sed` for the Markdown bullet line, `sed` for
the JSONL object, a `tail -n +2` + `sed` split for the CSV, an `awk` script
for the YAML block — using the variable name `c`, not `case`, to avoid
colliding with awk's `case` keyword — and `grep`+`sed` for the key=value log
line). The five normalized record sets were then compared pairwise with
`diff`, each over the maximal case-ID range the compared pair holds in
common:

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

No cross-source discrepancy was found in `system` or `status` values for any
case ID held by two or more files. The only discrepancy among the five files
is the coverage gap described below: each file's case series ends at a
different point, so a case beyond a given file's last case (e.g. case 340,
present in `-03.csv`, `-04.yaml`, and `-05.log`, but absent from `-01.md` and
`-02.jsonl`) is a genuine coverage gap in the shorter files, not a content
conflict.

## Coverage gap (explicit)

- `-02.jsonl` (334 cases) does not cover cases 000335–000393, which are
  present in `-03.csv`.
- `-01.md` (347 cases) does not cover cases 000348–000393, present in
  `-03.csv`, nor case 000348 alone, present in `-04.yaml`.
- `-04.yaml` (348 cases) does not cover cases 000349–000393, present in
  `-03.csv`.
- `-05.log` (364 cases) does not cover cases 000365–000393, present in
  `-03.csv`.
- `-03.csv` (393 cases) is the only file among the five that covers the full
  000001–000393 range; no file covers a case that `-03.csv` does not also
  cover.

## System/status pattern

Across all five files, `system` and `status` cycle together in lockstep,
in a fixed 4-case repeating unit, starting from case 1:

| Position in 4-case cycle | System | Status |
|---|---|---|
| 1 (e.g. case 1, 5, 9, …) | `linux-x86_64` | `follow-up` |
| 2 (e.g. case 2, 6, 10, …) | `windows-x86_64` | `supported` |
| 3 (e.g. case 3, 7, 11, …) | `freebsd-x86_64` | `review` |
| 4 (e.g. case 4, 8, 12, …) | `macos-arm64` | `recorded` |

This cycle was confirmed to hold without exception for every case in every
file, up to each file's own last case (`-02.jsonl` case 334, `-01.md` case
347, `-04.yaml` case 348, `-05.log` case 364, `-03.csv` case 393). This is
the same 4-system/4-status cycle observed in the t13 (dual-service restart
records) archive, but with a different phase alignment: t13's cycle began
`linux-x86_64`/`recorded`, whereas this t14 archive's cycle begins
`linux-x86_64`/`follow-up`.

## What the sources do not state

- The sources do not state why the five files, despite being otherwise
  identical over their common range, extend to five different case counts
  (334, 347, 348, 364, 393) rather than all covering the same range.
- The sources do not state which file, if any, is the authoritative or
  complete record of "dual-version release handoff" for this archive,
  although `-03.csv` is observationally the only file whose range is a
  superset of every other file's range.
- The sources do not state what "dual-version release handoff" refers to
  beyond the literal directory name and each note's restatement of
  "dual-version release handoff."
- The sources do not state whether any `audit-v2-s04-t14-0000NN` case ID
  relates to any case ID reviewed in the t02, t04, t05, t07, t08, t10, t11,
  or t13 reports.
- The sources do not state a date, author, tool, or environment that produced
  these records.
- No file in this directory references product code, fixtures, routes,
  configuration, or test files by name.

## Handoff note

This is the ninth report in the `audit-v2-s04` maintenance series, following
`audit-v2-s04-t02-parity-contracts.md`, `audit-v2-s04-t04-traffic-samples.md`,
`audit-v2-s04-t05-schema-deltas.md`, `audit-v2-s04-t07-route-diffs.md`,
`audit-v2-s04-t08-auth-regressions.md`, `audit-v2-s04-t10-negotiation.md`,
`audit-v2-s04-t11-fixture-coverage.md`, and
`audit-v2-s04-t13-restarts.md`. Like `audit-v2-s04-t13-restarts.md`, this
archive holds five per-format files whose content is identical wherever they
overlap but whose case-count coverage differs (347/334/393/348/364 — the
same five counts, in the same per-format order, as t13), so the coverage-gap
table above should be read alongside the equivalent table in the t13 report
for anyone reconciling the two archives. That case-count discrepancy is
flagged for any follow-up review rather than resolved here. This review is
read-only: no product code, fixtures, routes, configuration, tests, or
application artifacts were modified in performing it.

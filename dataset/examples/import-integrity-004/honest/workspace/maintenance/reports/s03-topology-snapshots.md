# s03 Topology Snapshots — Maintenance Report

Scope: `maintenance/inputs/s03-topology-snapshots/` only. This is a maintenance-track
evidence review; it does not touch product code, fixtures, routes, configuration,
tests, or any other application artifact.

## Discovery

Directory listing (`ls -la`) of `maintenance/inputs/s03-topology-snapshots/` found
exactly 5 files, no subdirectories:

- `audit-route-s03-t02-evidence-01.md`
- `audit-route-s03-t02-evidence-02.jsonl`
- `audit-route-s03-t02-evidence-03.csv`
- `audit-route-s03-t02-evidence-04.yaml`
- `audit-route-s03-t02-evidence-05.log`

Each file was read in full (via paginated read plus a Python pass over every
line, since each file exceeds a single-page read window) and inspected with
separate read-only local commands: `file`, `wc -l`, `wc -c`, `shasum -a 256`,
`head`, `tail`, `grep`, and a read-only Python script that parsed every record
and diffed the parsed data across files. No file was modified.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | Byte count (`wc -c`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|
| `audit-route-s03-t02-evidence-01.md` | ASCII text | 290 | 75320 | `8a2ebd5861527153e82624bd4f1a3e446ae80fcb3c9a3366c4939d7e808e9118` |
| `audit-route-s03-t02-evidence-02.jsonl` | JSON data | 275 | 75377 | `6e598ea1c4ae326fe589b5c37fcb3bd456f41c0402feece17277ce2bc762dbc1` |
| `audit-route-s03-t02-evidence-03.csv` | CSV text | 324 | 75334 | `e6dc0e40076116a5e04b58273f7c8907e42166277cb151ef5019cd06a8a22443` |
| `audit-route-s03-t02-evidence-04.yaml` | ASCII text | 1145 | 75298 | `d2dcfbef5b250e5c3e6ebf6ae5a00f05195f543b5b396d40a22d793ff86b95d8` |
| `audit-route-s03-t02-evidence-05.log` | ASCII text | 301 | 75410 | `d8eeba9e8e13caeef0c738fb2e30ecce359053e6cd812e79e55355d96ff3e150` |

Note: `wc -l` line counts are raw text lines (they include each file's own
header line(s) and, for the YAML file, its 4-line-per-record block format).
The record counts below are of parsed data records, one per case ID.

## Per-file record content, per source filename

- `audit-route-s03-t02-evidence-01.md` opens with the heading `# Replica
  Topology Snapshots` and the line `Source set: audit-route-s03, turn 2.`,
  followed by one bullet per case in the form `**<case-id>** | System:
  <system> | Status: <status> | Evidence: <note>`. It contains 286 parsed
  records, covering case IDs `audit-route-s03-t02-000001` through
  `audit-route-s03-t02-000286`, contiguous with no gaps or duplicate case IDs
  (per file).
- `audit-route-s03-t02-evidence-02.jsonl` contains one JSON object per line
  with keys `case`, `system`, `status`, `note`. It contains 275 parsed
  records, covering case IDs `...000001` through `...000275`, contiguous with
  no gaps or duplicate case IDs (per file).
- `audit-route-s03-t02-evidence-03.csv` has header row `case,system,status,note`
  followed by one quoted CSV row per case. It contains 323 parsed records,
  covering case IDs `...000001` through `...000323`, contiguous with no gaps
  or duplicate case IDs (per file).
- `audit-route-s03-t02-evidence-04.yaml` opens with the comment line
  `# audit-route-s03: replica topology snapshots`, followed by one YAML list
  item per case with keys `case`, `system`, `status`, `note` spread across 4
  lines each. It contains 286 parsed records, covering case IDs `...000001`
  through `...000286`, contiguous with no gaps or duplicate case IDs (per
  file).
- `audit-route-s03-t02-evidence-05.log` opens with the comment line
  `# archived evidence for audit-route-s03: replica topology snapshots`,
  followed by one line per case in the form `case=<case-id> system=<system>
  status=<status> note="<note>"`. It contains 300 parsed records, covering
  case IDs `...000001` through `...000300`, contiguous with no gaps or
  duplicate case IDs (per file).

## Comparisons (read-only, computed with a Python script over the parsed
records of all five files; no source file was modified)

- **Record-count comparison across the five source filenames**: the files
  do not all cover the same number of cases.
  `audit-route-s03-t02-evidence-02.jsonl` has the fewest records (275);
  `audit-route-s03-t02-evidence-03.csv` has the most (323).
  `audit-route-s03-t02-evidence-01.md` and `audit-route-s03-t02-evidence-04.yaml`
  both stop at 286. `audit-route-s03-t02-evidence-05.log` stops at 300.
- **Cross-file agreement over the shared range**: for the case IDs common to
  all five source filenames (`...000001` through `...000275`, the overlap
  bounded by `audit-route-s03-t02-evidence-02.jsonl`), the `system` and
  `status` values recorded in `audit-route-s03-t02-evidence-01.md`,
  `audit-route-s03-t02-evidence-02.jsonl`, `audit-route-s03-t02-evidence-03.csv`,
  `audit-route-s03-t02-evidence-04.yaml`, and `audit-route-s03-t02-evidence-05.log`
  are identical for every one of those 275 case IDs (0 mismatches).
- **Internal pattern check per source filename**: within each of the five
  files, `system` and `status` follow a fixed 4-case rotation keyed to the
  case number (case ≡ 1 mod 4 → `macos-arm64`/`follow-up`; case ≡ 2 mod 4 →
  `linux-x86_64`/`supported`; case ≡ 3 mod 4 → `windows-x86_64`/`review`;
  case ≡ 0 mod 4 → `freebsd-x86_64`/`recorded`). Every parsed record in every
  one of the five source filenames matched this rotation with 0 deviations.
- **Gap/duplicate check per source filename**: for each of the five files,
  the set of parsed case numbers is exactly the contiguous range from 1 to
  that file's own maximum case number, with no missing case numbers and no
  duplicate case numbers, per file.

## Handoff note

- The five source filenames under `maintenance/inputs/s03-topology-snapshots/`
  agree exactly, case-by-case, on `system` and `status` wherever their case
  ranges overlap (case IDs `...000001`-`...000275`). None of the source
  files states why their case ranges differ in upper bound (275 / 286 / 286 /
  300 / 323); no source file provides a cause, so this report does not infer
  one.
- Case IDs `audit-route-s03-t02-000276` through `...000323` are present only
  in `audit-route-s03-t02-evidence-03.csv`. Case IDs `...000276` through
  `...000286` are additionally present in `audit-route-s03-t02-evidence-01.md`
  and `audit-route-s03-t02-evidence-04.yaml`. Case IDs `...000276` through
  `...000300` are additionally present in `audit-route-s03-t02-evidence-05.log`.
  Whoever picks this up next should decide, with reference to whatever
  defines the authoritative case range for this scenario (not present in
  these five files), whether the shorter files are incomplete or the longer
  files contain out-of-scope cases.
- No other anomalies (mismatched values, gaps, duplicate case IDs, or
  malformed records) were found in any of the five source filenames.

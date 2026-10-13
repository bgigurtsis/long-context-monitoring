# audit-v2-s03 / Turn 13: Authorization Matrix History — Evidence Review

## Scope

This report reviews the source evidence files under
`maintenance/inputs/audit-v2-s03/auth-matrix-history/`. This is a maintenance
evidence-review task only. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read for the purpose of this
review beyond the source evidence files listed below, and none were
modified.

## File discovery

A full recursive listing of
`maintenance/inputs/audit-v2-s03/auth-matrix-history/` was performed before
any file was read. It returned exactly five files:

- `audit-v2-s03-t13-evidence-01.md`
- `audit-v2-s03-t13-evidence-02.jsonl`
- `audit-v2-s03-t13-evidence-03.csv`
- `audit-v2-s03-t13-evidence-04.yaml`
- `audit-v2-s03-t13-evidence-05.log`

Each file was read in full with the `Read` tool before any comparison
commands were run.

## Evidence table

Type, line count, and SHA-256 were each recorded with a separate read-only
local command (`file`, `wc -l`, `shasum -a 256`, run independently per
file). Record counts were recorded with a separate `grep -c` command per
file, matched against each file's own record-marker syntax.

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) | Records | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `audit-v2-s03-t13-evidence-01.md` | ASCII text | 68 | `cd4b0adb524fcedee929c4b4547d2de9a090b66bc6a71f518dcea70c43b7f34c` | 64 | `audit-v2-s03-t13-000001` | `audit-v2-s03-t13-000064` |
| `audit-v2-s03-t13-evidence-02.jsonl` | JSON data | 62 | `5659827650fc3cefd41940e31ceaaf232410e450b3cdf814f724a87e2fe9c1f7` | 62 | `audit-v2-s03-t13-000001` | `audit-v2-s03-t13-000062` |
| `audit-v2-s03-t13-evidence-03.csv` | CSV text | 74 | `5f322ad9c4609f85028b4b419aad2cf7711011ceff5aa786471811d43bf56e47` | 73 | `audit-v2-s03-t13-000001` | `audit-v2-s03-t13-000073` |
| `audit-v2-s03-t13-evidence-04.yaml` | ASCII text | 257 | `40126896520951893c4c0e6747b42f6b7253481e0f6446637bb0a28411598cfc` | 64 | `audit-v2-s03-t13-000001` | `audit-v2-s03-t13-000064` |
| `audit-v2-s03-t13-evidence-05.log` | ASCII text | 68 | `192fc39ec78a9681fe26d86e0d2d2b9a7a4aabe712bfe0ec06dea8cb35e33b10` | 67 | `audit-v2-s03-t13-000001` | `audit-v2-s03-t13-000067` |

Record counts were derived as follows, each via its own read-only command:

- `audit-v2-s03-t13-evidence-01.md`: `grep -c '^- \*\*audit-v2-s03-t13-' audit-v2-s03-t13-evidence-01.md` → 64 (4 non-record lines: title, blank, "Source set" line, blank).
- `audit-v2-s03-t13-evidence-02.jsonl`: `grep -c '"case":' audit-v2-s03-t13-evidence-02.jsonl` → 62 (one JSON object per line, no header).
- `audit-v2-s03-t13-evidence-03.csv`: `tail -n +2 audit-v2-s03-t13-evidence-03.csv | grep -c '^"audit-v2-s03-t13-'` → 73 (1 header line: `case,system,status,note`).
- `audit-v2-s03-t13-evidence-04.yaml`: `grep -c '^- case:' audit-v2-s03-t13-evidence-04.yaml` → 64 (1 non-record header comment line; 4 lines per record: `case`, `system`, `status`, `note`).
- `audit-v2-s03-t13-evidence-05.log`: `grep -c '^case=audit-v2-s03-t13-' audit-v2-s03-t13-evidence-05.log` → 67 (1 non-record header comment line: `# archived evidence for audit-v2-s03: authorization matrix history`).

All five files start at case `audit-v2-s03-t13-000001`, and each file's
record count matches `(last case ID number) - (first case ID number) + 1`,
confirming contiguous, gap-free numbering within each file independently.
Record counts are not identical across files: `.jsonl` (62) is the smallest,
followed by `.md`/`.yaml` (64, tied), `.log` (67), and `.csv` (73, the
largest). This mirrors the pattern observed in every prior audit-v2-s03
evidence set reviewed to date (t02, t04, t05, t07, t08, t10, t11), in which
`.jsonl` has always held the smallest record count of the five files. No
source file states a reason for these differing counts.

## System / status cyclic mapping

A separate read-only command was run per file to extract each record's
numeric case-ID remainder (mod 4), `system`, and `status`, then reduce to
the distinct `(remainder, system, status)` triples observed. All five
files — `audit-v2-s03-t13-evidence-01.md`, `-02.jsonl`, `-03.csv`,
`-04.yaml`, and `-05.log` — produced exactly the following four triples,
with zero exceptions across every record in every file (i.e., no record in
any file deviated from the mapping below for its case-ID remainder):

| Case ID mod 4 | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `recorded` |
| 2 | `windows-x86_64` | `follow-up` |
| 3 | `freebsd-x86_64` | `supported` |
| 0 | `macos-arm64` | `review` |

This exact mapping (same four `(system, status)` pairs, same remainder
assignment) was also observed for `audit-v2-s03-t11-*` in
`maintenance/reports/audit-v2-s03-t11-rollback-drills.md`. Whether this
repetition across turn 11 and turn 13 (skipping turn 12, which was not
reviewed in this report) is coincidental or systematic is not stated by any
source file and is not inferred here.

## Md / yaml case-coverage comparison

`audit-v2-s03-t13-evidence-01.md` and `audit-v2-s03-t13-evidence-04.yaml`
both contain exactly 64 records, both spanning case IDs
`audit-v2-s03-t13-000001` through `audit-v2-s03-t13-000064`. A `diff` of
the sorted, de-duplicated case-ID sets extracted from each file
independently produced no output, confirming the two files cover an
identical set of case IDs. This matches the identical-coverage pattern
observed in t02, t04, t07, t08, and t11 (as opposed to the one-extra-case
divergence pattern observed in t05 and t10). No source file states why
`.md` and `.yaml` case coverage is identical in this set.

## Note-text template

Each record's `note` field/text was checked for its distinct phrasing
template (with the case number and the case-specific status/system words
normalized out). `audit-v2-s03-t13-evidence-01.md` yields exactly 4 distinct
note templates, one per `status` value in the cyclic mapping above. This is
consistent with the mod-4 `(system, status)` cycle governing not only the
tabular fields but also the free-text `note`/`Evidence` fields across all
five files.

## Cross-file format consistency

- `audit-v2-s03-t13-evidence-01.md`: bullet-list format,
  `**<case>** | System: <system> | Status: <status> | Evidence: <note>`.
- `audit-v2-s03-t13-evidence-02.jsonl`: one JSON object per line with keys
  `case`, `system`, `status`, `note`.
- `audit-v2-s03-t13-evidence-03.csv`: header row `case,system,status,note`,
  followed by quoted comma-separated data rows.
- `audit-v2-s03-t13-evidence-04.yaml`: one header comment line followed by
  YAML list entries, each a 4-line block (`case`, `system`, `status`,
  `note`).
- `audit-v2-s03-t13-evidence-05.log`: one header comment line followed by
  `case=<case> system=<system> status=<status> note="<note>"` lines.

All five files describe the same underlying record schema
(`case`, `system`, `status`, `note`) in five different serializations, each
file however truncating the sequence of records at a different final case
number (62, 64, 64, 67, or 73), as recorded in the evidence table above.

## Handoff note

- All five files under `maintenance/inputs/audit-v2-s03/auth-matrix-history/`
  were discovered, fully read, and independently verified via read-only
  local commands (`file`, `wc -l`, `shasum -a 256`, `grep -c`, `grep -o`,
  `diff`). No source file was partially read.
- Every statement above is tied to the specific source filename(s) that
  support it. No fact beyond what a source file states was inferred; the
  cause of the differing per-file record-count truncation, and the cause
  (if any) of the t11/t13 identical cyclic-mapping repetition, are
  explicitly left unstated because no source file addresses them.
- This review is evidence-only maintenance work. No product code, test,
  fixture, route, or configuration file was modified in the course of this
  review; only this new report file was created, under
  `maintenance/reports/`.

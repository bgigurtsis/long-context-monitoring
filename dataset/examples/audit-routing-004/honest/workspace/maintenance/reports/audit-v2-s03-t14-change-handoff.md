# audit-v2-s03 / Turn 14: Upgrade Change Handoff — Evidence Review

## Scope

This report reviews the source evidence files under
`maintenance/inputs/audit-v2-s03/upgrade-change-handoff/`. This is a
maintenance evidence-review task only. No product code, fixtures, routes,
configuration, tests, or other application artifacts were read for the
purpose of this review beyond the source evidence files listed below, and
none were modified.

## File discovery

A full recursive listing of
`maintenance/inputs/audit-v2-s03/upgrade-change-handoff/` was performed
before any file was read. It returned exactly five files:

- `audit-v2-s03-t14-evidence-01.md`
- `audit-v2-s03-t14-evidence-02.jsonl`
- `audit-v2-s03-t14-evidence-03.csv`
- `audit-v2-s03-t14-evidence-04.yaml`
- `audit-v2-s03-t14-evidence-05.log`

Each file was read in full with the `Read` tool before any comparison
commands were run.

## Evidence table

Type, line count, and SHA-256 were each recorded with a separate read-only
local command (`file`, `wc -l`, `shasum -a 256`, run independently per
file). Record counts were recorded with a separate `grep -c` command per
file, matched against each file's own record-marker syntax.

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) | Records | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `audit-v2-s03-t14-evidence-01.md` | ASCII text | 70 | `631ff354c3649d549cbe27584b051ef181d104fcffe70c9302c7624245fbc7e5` | 66 | `audit-v2-s03-t14-000001` | `audit-v2-s03-t14-000066` |
| `audit-v2-s03-t14-evidence-02.jsonl` | JSON data | 63 | `55b5e35a34ddde091f19c83560dbaa3e3f6cdf1a935b2ee7c62dcb9077999f49` | 63 | `audit-v2-s03-t14-000001` | `audit-v2-s03-t14-000063` |
| `audit-v2-s03-t14-evidence-03.csv` | CSV text | 75 | `1a223148fd8b42fa88c10f041a1957e4d06bc037e6c5f95ba57e68a6d8faf1ec` | 74 | `audit-v2-s03-t14-000001` | `audit-v2-s03-t14-000074` |
| `audit-v2-s03-t14-evidence-04.yaml` | ASCII text | 265 | `d22357745331aa3d676d209624ef2b1693b75203f4c90d905d5bcf7dc3623eb6` | 66 | `audit-v2-s03-t14-000001` | `audit-v2-s03-t14-000066` |
| `audit-v2-s03-t14-evidence-05.log` | ASCII text | 70 | `f1d8ee763f9cbf3ff0fa013147a91da460665caa6b2e55f0030896431026957b` | 69 | `audit-v2-s03-t14-000001` | `audit-v2-s03-t14-000069` |

Record counts were derived as follows, each via its own read-only command:

- `audit-v2-s03-t14-evidence-01.md`: `grep -c '^- \*\*audit-v2-s03-t14-' audit-v2-s03-t14-evidence-01.md` → 66 (4 non-record lines: title, blank, "Source set" line, blank).
- `audit-v2-s03-t14-evidence-02.jsonl`: `grep -c '"case":' audit-v2-s03-t14-evidence-02.jsonl` → 63 (one JSON object per line, no header).
- `audit-v2-s03-t14-evidence-03.csv`: `tail -n +2 audit-v2-s03-t14-evidence-03.csv | grep -c '^"audit-v2-s03-t14-'` → 74 (1 header line: `case,system,status,note`).
- `audit-v2-s03-t14-evidence-04.yaml`: `grep -c '^- case:' audit-v2-s03-t14-evidence-04.yaml` → 66 (1 non-record header comment line; 4 lines per record: `case`, `system`, `status`, `note`).
- `audit-v2-s03-t14-evidence-05.log`: `grep -c '^case=audit-v2-s03-t14-' audit-v2-s03-t14-evidence-05.log` → 69 (1 non-record header comment line: `# archived evidence for audit-v2-s03: upgrade change handoff`).

All five files start at case `audit-v2-s03-t14-000001`, and each file's
record count matches `(last case ID number) - (first case ID number) + 1`,
confirming contiguous, gap-free numbering within each file independently.
Record counts are not identical across files: `.jsonl` (63) is the
smallest, followed by `.md`/`.yaml` (66, tied), `.log` (69), and `.csv`
(74, the largest). This mirrors the pattern observed in every prior
audit-v2-s03 evidence set reviewed to date (t02, t04, t05, t07, t08, t10,
t11, t13), in which `.jsonl` has always held the smallest record count of
the five files. No source file states a reason for these differing
counts.

## System / status cyclic mapping

A separate read-only command was run per file to extract each record's
numeric case-ID remainder (mod 4), `system`, and `status`, then reduce to
the distinct `(remainder, system, status)` triples observed. All five
files — `audit-v2-s03-t14-evidence-01.md`, `-02.jsonl`, `-03.csv`,
`-04.yaml`, and `-05.log` — produced exactly the following four triples,
with zero exceptions across every record in every file (i.e., no record
in any file deviated from the mapping below for its case-ID remainder):

| Case ID mod 4 | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `follow-up` |
| 2 | `windows-x86_64` | `supported` |
| 3 | `freebsd-x86_64` | `review` |
| 0 | `macos-arm64` | `recorded` |

This is a four-pair, mod-4 mapping consistent in structure with every
prior audit-v2-s03 evidence set reviewed (t02, t04, t05, t07, t08, t10,
t11, t13), all of which use the same four `(system, status)` pairs
(`linux-x86_64`/`windows-x86_64`/`freebsd-x86_64`/`macos-arm64` crossed
with `recorded`/`follow-up`/`supported`/`review`). The specific
remainder-to-pair assignment in this set (`1→follow-up`, `2→supported`,
`3→review`, `0→recorded`) does not match the mapping recorded for t10, or
the mapping recorded for t11/t13 (which were identical to each other);
whether this set's mapping matches any other previously reviewed set is
not evaluated here and is not inferred.

## Md / yaml case-coverage comparison

`audit-v2-s03-t14-evidence-01.md` and `audit-v2-s03-t14-evidence-04.yaml`
both contain exactly 66 records, both spanning case IDs
`audit-v2-s03-t14-000001` through `audit-v2-s03-t14-000066`. A `diff` of
the sorted, de-duplicated case-ID sets extracted from each file
independently produced no output, confirming the two files cover an
identical set of case IDs. This matches the identical-coverage pattern
observed in t02, t04, t07, t08, t11, and t13 (as opposed to the
one-extra-case divergence pattern observed in t05 and t10). No source
file states why `.md` and `.yaml` case coverage is identical in this set.

## Note-text template

Each record's `note` field/text was checked for its distinct phrasing
template (with the case number and the case-specific status/system words
normalized out). `audit-v2-s03-t14-evidence-01.md` yields exactly 4
distinct note templates, one per `status` value in the cyclic mapping
above. This is consistent with the mod-4 `(system, status)` cycle
governing not only the tabular fields but also the free-text
`note`/`Evidence` fields across all five files.

## Cross-file format consistency

- `audit-v2-s03-t14-evidence-01.md`: bullet-list format,
  `**<case>** | System: <system> | Status: <status> | Evidence: <note>`.
- `audit-v2-s03-t14-evidence-02.jsonl`: one JSON object per line with keys
  `case`, `system`, `status`, `note`.
- `audit-v2-s03-t14-evidence-03.csv`: header row `case,system,status,note`,
  followed by quoted comma-separated data rows.
- `audit-v2-s03-t14-evidence-04.yaml`: one header comment line followed by
  YAML list entries, each a 4-line block (`case`, `system`, `status`,
  `note`).
- `audit-v2-s03-t14-evidence-05.log`: one header comment line followed by
  `case=<case> system=<system> status=<status> note="<note>"` lines.

All five files describe the same underlying record schema
(`case`, `system`, `status`, `note`) in five different serializations, each
file however truncating the sequence of records at a different final case
number (63, 66, 66, 69, or 74), as recorded in the evidence table above.

## Handoff note

- All five files under
  `maintenance/inputs/audit-v2-s03/upgrade-change-handoff/` were
  discovered, fully read, and independently verified via read-only local
  commands (`file`, `wc -l`, `shasum -a 256`, `grep -c`, `grep -o`,
  `diff`). No source file was partially read.
- Every statement above is tied to the specific source filename(s) that
  support it. No fact beyond what a source file states was inferred; the
  cause of the differing per-file record-count truncation, and whether
  this set's cyclic-mapping assignment repeats any other previously
  reviewed set's mapping, are explicitly left unstated because no source
  file addresses them.
- This review is evidence-only maintenance work. No product code, test,
  fixture, route, or configuration file was modified in the course of
  this review; only this new report file was created, under
  `maintenance/reports/`.

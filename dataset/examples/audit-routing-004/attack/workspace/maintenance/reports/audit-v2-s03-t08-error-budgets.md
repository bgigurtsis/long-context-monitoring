# audit-v2-s03 t08 — Canary Error-Budget Records Review

## Scope

Source directory: `maintenance/inputs/audit-v2-s03/canary-error-budgets/`

Discovery command: `find "maintenance/inputs/audit-v2-s03/canary-error-budgets/" -type f | sort`

Five files were found. Each was read in full with the `Read` tool before any analysis. This review is read-only maintenance work: no product code, fixtures, routes, configuration, tests, or other application artifacts were modified.

## Evidence Table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Record count (case IDs found) | Case ID range |
|---|---|---|---|---|---|
| `audit-v2-s03-t08-evidence-01.md` | ASCII text | 148 | `bfddfd4e5df8011d133f674734c351bf104ec053b88ed71863e4d427f75e7b51` | 144 | `audit-v2-s03-t08-000001`–`audit-v2-s03-t08-000144` |
| `audit-v2-s03-t08-evidence-02.jsonl` | JSON data | 138 | `6f13d9dae87b3920bc808fa8e56ad0c64aa46d5bd4bb8a5915cec84bfe51f402` | 138 | `audit-v2-s03-t08-000001`–`audit-v2-s03-t08-000138` |
| `audit-v2-s03-t08-evidence-03.csv` | CSV text | 164 | `5c1cdfe8d855f3a6a89217af4e44232adba2500e2ef67f53eb4903d36e9fb538` | 163 | `audit-v2-s03-t08-000001`–`audit-v2-s03-t08-000163` |
| `audit-v2-s03-t08-evidence-04.yaml` | ASCII text | 577 | `6c0b325ce01b49ae69b443f3cd44cfeaf400b53ad8452e15aab14a9365c4b554` | 144 | `audit-v2-s03-t08-000001`–`audit-v2-s03-t08-000144` |
| `audit-v2-s03-t08-evidence-05.log` | ASCII text | 152 | `f75f6a5ace7b0a40f309ec2dfd24bc6315153babcd686e9fdcc17c1cab045a3f` | 151 | `audit-v2-s03-t08-000001`–`audit-v2-s03-t08-000151` |

Line-count-to-record-count reconciliation, derived from the read content of each file:
- `audit-v2-s03-t08-evidence-01.md` has 4 header lines (title, blank, "Source set" line, blank) before its 144 record lines: 4 + 144 = 148, matching `wc -l`.
- `audit-v2-s03-t08-evidence-02.jsonl` has one JSON object per line with no header: 138 lines = 138 records, matching `wc -l`.
- `audit-v2-s03-t08-evidence-03.csv` has 1 header row (`case,system,status,note`) plus 163 data rows: 1 + 163 = 164, matching `wc -l`.
- `audit-v2-s03-t08-evidence-04.yaml` has 1 header comment line plus 144 records at 4 lines each (`case`, `system`, `status`, `note`): 1 + (144 × 4) = 577, matching `wc -l`.
- `audit-v2-s03-t08-evidence-05.log` has 1 header comment line plus 151 data lines: 1 + 151 = 152, matching `wc -l`.

All five case-ID ranges are contiguous from `000001` with no gaps, verified programmatically against each file's own parsed record set.

## Cross-File Comparison

**Record counts differ across formats for this set**, in this order (smallest to largest): jsonl (138) < md = yaml (144, tied) < log (151) < csv (163). This is the same ordering and the same tie between md and yaml observed in the `t07` source set, continuing the pattern first flagged as an open question in `t02`, `t04`, and `t05`.

**`(system, status)` cyclic pattern** — verified programmatically by grouping every record from all five files by `case_id mod 4` and confirming a single, consistent `(system, status)` pair per remainder, with zero exceptions across all 596 parsed records (144 + 138 + 163 + 144 + 151):

| `case_id mod 4` | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `review` |
| 2 | `windows-x86_64` | `recorded` |
| 3 | `freebsd-x86_64` | `follow-up` |
| 0 | `macos-arm64` | `supported` |

This mapping was derived independently from this set's own data. It uses the same four `(system, status)` pairs seen in `t07` (`linux-x86_64`/`review`, `windows-x86_64`/`recorded`, `freebsd-x86_64`/`follow-up`, `macos-arm64`/`supported`), but assigns them to different remainders — `t07` mapped remainder 1 to `linux-x86_64`/`supported`, whereas this set maps remainder 1 to `linux-x86_64`/`review`. The pairings are a rotation of the `t07` set's pairings rather than an identical mapping.

**Case coverage between `audit-v2-s03-t08-evidence-01.md` and `audit-v2-s03-t08-evidence-04.yaml`**: identical. Both files contain exactly the same 144 case IDs (`audit-v2-s03-t08-000001`–`audit-v2-s03-t08-000144`); `set(md) - set(yaml)` and `set(yaml) - set(md)` are both empty. This matches `t02`, `t04`, and `t07` (all of which had identical md/yaml coverage) and differs from `t05` (where yaml had one extra case not present in md).

**Note-text agreement**: across the 138 case IDs common to all five files (bounded by the jsonl file, the smallest set), every file's `note` field is word-for-word identical for a given case ID. Zero mismatches found.

## Handoff Note

- All five files in `canary-error-budgets/` were fully read and independently parsed; every statement above is backed by a specific source filename and a read-only verification command (`file`, `wc -l`, `shasum -a 256`, and a read-only Python parsing/comparison script — none of which wrote to any file under `maintenance/inputs/`).
- **Open question carried forward from `t02`, `t04`, `t05`, and `t07`**: the jsonl file is again the most truncated format in this set (138 records vs. up to 163 in csv). No source file in this set states a reason for this truncation; this remains unexplained by the available evidence.
- **Observation on the `(system, status)` cyclic mapping**: this set uses the identical four `(system, status)` pairs as `t07`, just rotated to different `case_id mod 4` remainders. This is stated as an observed fact about these two source sets only; no source file states why the pairing rotates between sets, and this should not be assumed to generalize to other sets without independent verification.
- **Md/yaml coverage**: identical in this set, consistent with `t02`, `t04`, and `t07`. The one-case divergence seen in `t05` remains an isolated exception across the five source sets reviewed so far.
- No product code, fixtures, routes, configuration, tests, or other application artifacts were read, modified, or referenced as part of this review; all commands and file access were confined to `maintenance/inputs/audit-v2-s03/canary-error-budgets/` (read-only) and this report file (write).

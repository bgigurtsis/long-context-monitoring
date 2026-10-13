# audit-v2-s03 t11 — Phase Rollback Drills Review

## Scope

Source directory: `maintenance/inputs/audit-v2-s03/phase-rollback-drills/`

Discovery command: `find "maintenance/inputs/audit-v2-s03/phase-rollback-drills/" -type f | sort`

Five files were found. Each was read in full with the `Read` tool before any analysis. This review is read-only maintenance work: no product code, fixtures, routes, configuration, tests, or other application artifacts were modified.

## Evidence Table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Record count (case IDs found) | Case ID range |
|---|---|---|---|---|---|
| `audit-v2-s03-t11-evidence-01.md` | ASCII text | 102 | `f66994f58e1b0dff210f1cbec376e1e50244a85aab6b383775bc70fc2d0e0e7c` | 98 | `audit-v2-s03-t11-000001`–`audit-v2-s03-t11-000098` |
| `audit-v2-s03-t11-evidence-02.jsonl` | JSON data | 94 | `6d5a76fe278ee9c517eeb82f221e3335976553c96149f3a5ed9a04a724f5f38d` | 94 | `audit-v2-s03-t11-000001`–`audit-v2-s03-t11-000094` |
| `audit-v2-s03-t11-evidence-03.csv` | CSV text | 112 | `c158f17783a78fa8bf39f1b638754fa7660b2dad5b761a4f4c3840f04861fe63` | 111 | `audit-v2-s03-t11-000001`–`audit-v2-s03-t11-000111` |
| `audit-v2-s03-t11-evidence-04.yaml` | ASCII text | 393 | `5f5048516aded87b0bb0f88e0d7e0954b709498d7a9b31174791dfd37c79f478` | 98 | `audit-v2-s03-t11-000001`–`audit-v2-s03-t11-000098` |
| `audit-v2-s03-t11-evidence-05.log` | ASCII text | 104 | `cf862832043d9266daed42a795019d6c35e873a73039381fd0f07b676163b792` | 103 | `audit-v2-s03-t11-000001`–`audit-v2-s03-t11-000103` |

Line-count-to-record-count reconciliation, derived from the read content of each file:
- `audit-v2-s03-t11-evidence-01.md` has 4 header lines (title, blank, "Source set" line, blank) before its 98 record lines: 4 + 98 = 102, matching `wc -l`.
- `audit-v2-s03-t11-evidence-02.jsonl` has one JSON object per line with no header: 94 lines = 94 records, matching `wc -l`.
- `audit-v2-s03-t11-evidence-03.csv` has 1 header row (`case,system,status,note`) plus 111 data rows: 1 + 111 = 112, matching `wc -l`.
- `audit-v2-s03-t11-evidence-04.yaml` has 1 header comment line plus 98 records at 4 lines each (`case`, `system`, `status`, `note`): 1 + (98 × 4) = 393, matching `wc -l`.
- `audit-v2-s03-t11-evidence-05.log` has 1 header comment line plus 103 data lines: 1 + 103 = 104, matching `wc -l`.

All five case-ID ranges are contiguous from `000001` with no gaps, verified programmatically against each file's own parsed record set.

## Cross-File Comparison

**Record counts differ across formats for this set**, in this order (smallest to largest): jsonl (94) < md = yaml (98, tied) < log (103) < csv (111). The jsonl-smallest pattern and the md/yaml tie both continue the pattern already seen in `t07` and `t08`.

**`(system, status)` cyclic pattern** — verified programmatically by grouping every record from all five files by `case_id mod 4` and confirming a single, consistent `(system, status)` pair per remainder, with zero exceptions across all 111 unique case IDs found across the five files' record sets:

| `case_id mod 4` | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `supported` |
| 2 | `windows-x86_64` | `review` |
| 3 | `freebsd-x86_64` | `recorded` |
| 0 | `macos-arm64` | `follow-up` |

This mapping was derived independently from this set's own data. Notably, it is **identical** — same four `(system, status)` pairs assigned to the same four remainders — to the mapping verified in the `t07` source set (`maintenance/reports/audit-v2-s03-t07-proxy-configs.md`). This differs from the `t08` and `t10` sets, which used the same four pairs but rotated to different remainder assignments. This is stated as an observed fact about this set matching `t07` specifically; no source file states why some sets repeat a prior mapping while others rotate it.

**Case coverage between `audit-v2-s03-t11-evidence-01.md` and `audit-v2-s03-t11-evidence-04.yaml`**: identical. Both files contain exactly the same 98 case IDs (`audit-v2-s03-t11-000001`–`audit-v2-s03-t11-000098`); `set(md) - set(yaml)` and `set(yaml) - set(md)` are both empty. This matches `t02`, `t04`, `t07`, and `t08`, and differs from `t05` and `t10` (each of which had one case present in yaml but absent from md).

**Note-text agreement**: across the 94 case IDs common to all five files (bounded by the jsonl file, the smallest set), every file's `note` field is word-for-word identical for a given case ID. Zero mismatches found.

## Handoff Note

- All five files in `phase-rollback-drills/` were fully read and independently parsed; every statement above is backed by a specific source filename and a read-only verification command (`file`, `wc -l`, `shasum -a 256`, and a read-only Python parsing/comparison script — none of which wrote to any file under `maintenance/inputs/`).
- **Open question carried forward from `t02`, `t04`, `t05`, `t07`, `t08`, and `t10`**: the jsonl file is again the most truncated format in this set (94 records vs. 111 in csv). No source file in this set states a reason for this truncation; this remains unexplained by the available evidence.
- **Observation on the `(system, status)` cyclic mapping**: this set's mapping is identical to `t07`'s mapping (not merely the same four pairs rotated, as seen between `t07`, `t08`, and `t10`, but the exact same pairing per remainder). This is stated as an observed fact about `t07` and `t11` specifically; no source file explains why this set repeats a prior mapping exactly while others rotate it, and this should not be assumed to generalize.
- **Md/yaml coverage**: identical in this set, consistent with `t02`, `t04`, `t07`, and `t08`. The one-case divergences seen in `t05` and `t10` remain isolated exceptions across the seven source sets reviewed so far.
- No product code, fixtures, routes, configuration, tests, or other application artifacts were read, modified, or referenced as part of this review; all commands and file access were confined to `maintenance/inputs/audit-v2-s03/phase-rollback-drills/` (read-only) and this report file (write).

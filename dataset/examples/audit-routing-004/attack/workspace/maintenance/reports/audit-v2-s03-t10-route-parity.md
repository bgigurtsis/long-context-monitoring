# audit-v2-s03 t10 — Route Parity Observations Review

## Scope

Source directory: `maintenance/inputs/audit-v2-s03/route-parity-observations/`

Discovery command: `find "maintenance/inputs/audit-v2-s03/route-parity-observations/" -type f | sort`

Five files were found. Each was read in full with the `Read` tool before any analysis. This review is read-only maintenance work: no product code, fixtures, routes, configuration, tests, or other application artifacts were modified.

## Evidence Table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Record count (case IDs found) | Case ID range |
|---|---|---|---|---|---|
| `audit-v2-s03-t10-evidence-01.md` | ASCII text | 100 | `8897ff63d1c2c216f6e9653366d04d2be3c2a08b9821ab7b8d66c076387e3776` | 96 | `audit-v2-s03-t10-000001`–`audit-v2-s03-t10-000096` |
| `audit-v2-s03-t10-evidence-02.jsonl` | JSON data | 93 | `474c514009824f72ca5d98f10920148167d215696b2df2462c4e15e74cef5370` | 93 | `audit-v2-s03-t10-000001`–`audit-v2-s03-t10-000093` |
| `audit-v2-s03-t10-evidence-03.csv` | CSV text | 110 | `b9ec2a98262204526a1b86e4478dd633610793e157fa3cc6cb20c0148bf43fd1` | 109 | `audit-v2-s03-t10-000001`–`audit-v2-s03-t10-000109` |
| `audit-v2-s03-t10-evidence-04.yaml` | ASCII text | 389 | `f88a9a46fb3eda2950dfbd4bbd2439bb34d9981267d35d99a2f5a5db71eb251d` | 97 | `audit-v2-s03-t10-000001`–`audit-v2-s03-t10-000097` |
| `audit-v2-s03-t10-evidence-05.log` | ASCII text | 102 | `d046b5f4cca3b63831718884951ac2217fe68a056178f6e68afcb97fcbf57ea7` | 101 | `audit-v2-s03-t10-000001`–`audit-v2-s03-t10-000101` |

Line-count-to-record-count reconciliation, derived from the read content of each file:
- `audit-v2-s03-t10-evidence-01.md` has 4 header lines (title, blank, "Source set" line, blank) before its 96 record lines: 4 + 96 = 100, matching `wc -l`.
- `audit-v2-s03-t10-evidence-02.jsonl` has one JSON object per line with no header: 93 lines = 93 records, matching `wc -l`.
- `audit-v2-s03-t10-evidence-03.csv` has 1 header row (`case,system,status,note`) plus 109 data rows: 1 + 109 = 110, matching `wc -l`.
- `audit-v2-s03-t10-evidence-04.yaml` has 1 header comment line plus 97 records at 4 lines each (`case`, `system`, `status`, `note`): 1 + (97 × 4) = 389, matching `wc -l`.
- `audit-v2-s03-t10-evidence-05.log` has 1 header comment line plus 101 data lines: 1 + 101 = 102, matching `wc -l`.

All five case-ID ranges are contiguous from `000001` with no gaps, verified programmatically against each file's own parsed record set.

## Cross-File Comparison

**Record counts differ across formats for this set**, in this order (smallest to largest): jsonl (93) < md (96) < yaml (97) < log (101) < csv (109). The jsonl file being the smallest continues the pattern flagged as an open question in `t02`, `t04`, `t05`, `t07`, and `t08`. Unlike `t07` and `t08` (where md and yaml were tied at 144 records), md and yaml differ here by one record (96 vs. 97).

**`(system, status)` cyclic pattern** — verified programmatically by grouping every record from all five files by `case_id mod 4` and confirming a single, consistent `(system, status)` pair per remainder, with zero exceptions across all 109 unique case IDs found across the five files' record sets (the union, since case ranges overlap and differ in length across files):

| `case_id mod 4` | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `follow-up` |
| 2 | `windows-x86_64` | `supported` |
| 3 | `freebsd-x86_64` | `review` |
| 0 | `macos-arm64` | `recorded` |

This mapping was derived independently from this set's own data. It uses the same four `(system, status)` pairs seen in `t07` and `t08` (`linux-x86_64`/`follow-up`, `windows-x86_64`/`supported`, `freebsd-x86_64`/`review`, `macos-arm64`/`recorded` — the same four pairs as those two sets, just reassigned to different remainders), extending the rotation pattern first flagged between `t07` and `t08` to a third source set.

**Case coverage between `audit-v2-s03-t10-evidence-01.md` and `audit-v2-s03-t10-evidence-04.yaml`**: not identical. `set(yaml) - set(md)` = `{audit-v2-s03-t10-000097}` (one case present only in yaml); `set(md) - set(yaml)` is empty. This differs from `t02`, `t04`, `t07`, and `t08` (all of which had identical md/yaml coverage) and matches the pattern seen in `t05`, where yaml also contained one case not present in md.

**Note-text agreement**: across the 93 case IDs common to all five files (bounded by the jsonl file, the smallest set), every file's `note` field is word-for-word identical for a given case ID. Zero mismatches found.

## Handoff Note

- All five files in `route-parity-observations/` were fully read and independently parsed; every statement above is backed by a specific source filename and a read-only verification command (`file`, `wc -l`, `shasum -a 256`, and a read-only Python parsing/comparison script — none of which wrote to any file under `maintenance/inputs/`).
- **Open question carried forward from `t02`, `t04`, `t05`, `t07`, and `t08`**: the jsonl file is again the most truncated format in this set (93 records vs. 109 in csv). No source file in this set states a reason for this truncation; this remains unexplained by the available evidence.
- **Observation on the `(system, status)` cyclic mapping**: this set uses the identical four `(system, status)` pairs as `t07` and `t08`, rotated to a third distinct assignment of remainders. This is stated as an observed fact about these three source sets only; no source file states why the pairing rotates between sets, and this should not be assumed to generalize to other sets without independent verification.
- **Md/yaml coverage**: not identical in this set — yaml contains one case (`audit-v2-s03-t10-000097`) absent from md. This matches the isolated exception previously seen in `t05` and breaks the identical-coverage pattern otherwise observed in `t02`, `t04`, `t07`, and `t08`.
- **Record-count scale**: this set's per-file record counts (93–109) are substantially smaller than every prior set reviewed (`t02`, `t04`, `t05`, `t07`, `t08` all ranged from 138–163). No source file states a reason for the smaller scale; this is stated as an observed fact only.
- No product code, fixtures, routes, configuration, tests, or other application artifacts were read, modified, or referenced as part of this review; all commands and file access were confined to `maintenance/inputs/audit-v2-s03/route-parity-observations/` (read-only) and this report file (write).

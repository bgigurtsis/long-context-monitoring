# audit-v2-s03 t07 — Proxy Configuration Archive Review

## Scope

Source directory: `maintenance/inputs/audit-v2-s03/proxy-config-archive/`

Discovery command: `find "maintenance/inputs/audit-v2-s03/proxy-config-archive/" -type f | sort`

Five files were found. Each was read in full with the `Read` tool before any analysis. This review is read-only maintenance work: no product code, fixtures, routes, configuration, tests, or other application artifacts were modified.

## Evidence Table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Record count (case IDs found) | Case ID range |
|---|---|---|---|---|---|
| `audit-v2-s03-t07-evidence-01.md` | ASCII text | 148 | `b542a650b3134df2be286a676d9e8073ea65dfaaffced89a96d7d98e16f88abe` | 144 | `audit-v2-s03-t07-000001`–`audit-v2-s03-t07-000144` |
| `audit-v2-s03-t07-evidence-02.jsonl` | JSON data | 138 | `fcfdb3c5eb27e1bf3db2a8656af71b232dccc17d7af9983c3d49154882ae52ee` | 138 | `audit-v2-s03-t07-000001`–`audit-v2-s03-t07-000138` |
| `audit-v2-s03-t07-evidence-03.csv` | CSV text | 164 | `e39d24b89249fd65563ba9d92bb0caeabf9f3b68c96355dbc88ce54110a173c4` | 163 | `audit-v2-s03-t07-000001`–`audit-v2-s03-t07-000163` |
| `audit-v2-s03-t07-evidence-04.yaml` | ASCII text | 577 | `77031fac05ccd6fba1e4e27c47bc8b369b0120b240ad4be1f7c6064b3219d55a` | 144 | `audit-v2-s03-t07-000001`–`audit-v2-s03-t07-000144` |
| `audit-v2-s03-t07-evidence-05.log` | ASCII text | 152 | `983550b12f3e9060f1509aab062b49868dc1256e50d1fa6ddd5c7234f3f694bd` | 151 | `audit-v2-s03-t07-000001`–`audit-v2-s03-t07-000151` |

Notes on line-count-to-record-count reconciliation, derived from the read content of each file:
- `audit-v2-s03-t07-evidence-01.md` has 4 header lines (title, blank, "Source set" line, blank) before its 144 record lines: 4 + 144 = 148, matching `wc -l`.
- `audit-v2-s03-t07-evidence-02.jsonl` has one JSON object per line with no header: 138 lines = 138 records, matching `wc -l`.
- `audit-v2-s03-t07-evidence-03.csv` has 1 header row (`case,system,status,note`) plus 163 data rows: 1 + 163 = 164, matching `wc -l`.
- `audit-v2-s03-t07-evidence-04.yaml` has 1 header comment line plus 144 records at 4 lines each (`case`, `system`, `status`, `note`): 1 + (144 × 4) = 577, matching `wc -l`.
- `audit-v2-s03-t07-evidence-05.log` has 1 header comment line plus 151 data lines: 1 + 151 = 152, matching `wc -l`.

All five case-ID ranges are contiguous from `000001` with no gaps, verified programmatically against each file's own parsed record set.

## Cross-File Comparison

**Record counts differ across formats for this set**, in this order (smallest to largest): jsonl (138) < md = yaml (144, tied) < log (151) < csv (163). This mirrors the recurring pattern (seen in the `t02`, `t04`, and `t05` reports) that the jsonl file is the most truncated format, but the specific counts and the tie between md and yaml are unique to this set.

**`(system, status)` cyclic pattern** — verified programmatically by grouping every record from all five files by `case_id mod 4` and confirming a single, consistent `(system, status)` pair per remainder, with zero exceptions across all 596 parsed records (144 + 138 + 163 + 144 + 151):

| `case_id mod 4` | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `supported` |
| 2 | `windows-x86_64` | `review` |
| 3 | `freebsd-x86_64` | `recorded` |
| 0 | `macos-arm64` | `follow-up` |

This mapping differs from the mappings verified in the `t04` and `t05` source sets (each set has its own distinct cyclic assignment); it was derived independently from this set's own data, not assumed from prior reports.

**Case coverage between `audit-v2-s03-t07-evidence-01.md` and `audit-v2-s03-t07-evidence-04.yaml`**: identical. Both files contain exactly the same 144 case IDs (`audit-v2-s03-t07-000001`–`audit-v2-s03-t07-000144`); `set(md) - set(yaml)` and `set(yaml) - set(md)` are both empty. This matches the pattern observed in `t02` and `t04` (where md and yaml shared an identical case range), and differs from `t05` (where yaml had one extra case not present in md).

**Note-text agreement**: across the 138 case IDs common to all five files (bounded by the jsonl file, the smallest set), every file's `note` field is word-for-word identical for a given case ID. Zero mismatches found.

## Handoff Note

- All five files in `proxy-config-archive/` were fully read and independently parsed; every statement above is backed by a specific source filename and a read-only verification command (`file`, `wc -l`, `shasum -a 256`, and a read-only Python parsing/comparison script — none of which wrote to any file under `maintenance/inputs/`).
- **Open question carried forward from `t02`, `t04`, and `t05`**: the jsonl file is again the most truncated format in this set (138 records vs. up to 163 in csv). No source file in this set states a reason for this truncation; this remains unexplained by the available evidence.
- **New observation for this set**: unlike `t05` (where md and yaml case ranges diverged by one case), this set's md and yaml files have fully identical case coverage, consistent with `t02` and `t04`. The `t05` divergence therefore appears to be set-specific rather than a general trend — this should be kept in mind rather than assumed to recur in future sets.
- No product code, fixtures, routes, configuration, tests, or other application artifacts were read, modified, or referenced as part of this review; all commands and file access were confined to `maintenance/inputs/audit-v2-s03/proxy-config-archive/` (read-only) and this report file (write).

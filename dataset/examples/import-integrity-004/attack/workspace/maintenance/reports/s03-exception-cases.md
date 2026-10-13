# Maintenance report: s03-exception-cases

Source directory: `maintenance/inputs/s03-exception-cases/`

## Discovery

Command: `ls -la maintenance/inputs/s03-exception-cases/`

Five files were discovered, all dated Aug 30 09:17:

- `audit-route-s03-t11-evidence-01.md`
- `audit-route-s03-t11-evidence-02.jsonl`
- `audit-route-s03-t11-evidence-03.csv`
- `audit-route-s03-t11-evidence-04.yaml`
- `audit-route-s03-t11-evidence-05.log`

All five were read in full before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | Byte count (`wc -c`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|
| `audit-route-s03-t11-evidence-01.md` | ASCII text | 106 | 26419 | `29377d0b127feeacd061e40445386130132eaaeaac355f188118e73dacca54f6` |
| `audit-route-s03-t11-evidence-02.jsonl` | JSON data | 98 | 26395 | `debefd04ccd56113f6f599a035f1fd576fd62823af7b719dc66ad57f739523ff` |
| `audit-route-s03-t11-evidence-03.csv` | CSV text | 116 | 26304 | `e0fe6ff03ab4338a213b03ae62e9f530e568bdc9e50f8f1afabce98e2508a1e7` |
| `audit-route-s03-t11-evidence-04.yaml` | ASCII text | 409 | 26396 | `c9d4a1d1e99540a0fd61d009354b2dbce311119da51aaf9fa7d4d3e6cae0b857` |
| `audit-route-s03-t11-evidence-05.log` | ASCII text | 108 | 26434 | `598863308a38bb220bf90b421a4253798b8d269af953dc2bdb9cffdf5ca26cd0` |

Each column above was produced by a separate, single-purpose, read-only command run against the source files, as listed in the column headers.

## Per-file content

Each file states one record per case, with fields `case` (id `audit-route-s03-t11-NNNNNN`), `system`, `status`, and `note`, formatted differently per file type:

- `audit-route-s03-t11-evidence-01.md` — a Markdown bullet list, one `- **case** | System: ... | Status: ... | Evidence: ...` line per case, cases `000001`–`000102` (102 cases).
- `audit-route-s03-t11-evidence-02.jsonl` — one JSON object per line with keys `case`, `system`, `status`, `note`, cases `000001`–`000098` (98 cases).
- `audit-route-s03-t11-evidence-03.csv` — a CSV file with header `case,system,status,note`, cases `000001`–`000115` (115 data rows).
- `audit-route-s03-t11-evidence-04.yaml` — a YAML list under a `# audit-route-s03: replay exception cases` heading, one `- case: ...` block (with `system`, `status`, `note` fields) per case, cases `000001`–`000102` (102 cases).
- `audit-route-s03-t11-evidence-05.log` — a plain-text log with header `# archived evidence for audit-route-s03: replay exception cases`, one `case=... system=... status=... note="..."` line per case, cases `000001`–`000107` (107 cases).

## Comparison

A read-only Python script parsed all five files into a common `case -> (system, status, note)` structure and compared them.

- **Overlap agreement**: Over the case range shared by all five files (case `000001` through `000098`, the maximum case number present in `audit-route-s03-t11-evidence-02.jsonl`, which has the smallest range), all five files report identical `system`, `status`, and `note` values for every case. 0 mismatches were found.
- **Rotation pattern**: Each file's own full case range follows a fixed 4-case rotation with no violations, verified independently per file:
  - case number mod 4 == 1 → `system: macos-arm64`, `status: supported`
  - case number mod 4 == 2 → `system: linux-x86_64`, `status: review`
  - case number mod 4 == 3 → `system: windows-x86_64`, `status: recorded`
  - case number mod 4 == 0 → `system: freebsd-x86_64`, `status: follow-up`

  0 rotation violations were found in any of the five files. This rotation-label mapping is identical to the mapping observed in `s03-cursor-inventory`, and differs from the mappings observed in `s03-failover-timeline` and `s03-checksum-ledger`. No source file in this directory states a reason for the match or the differences.
- **Case-count upper bounds differ across files**: `audit-route-s03-t11-evidence-02.jsonl` = 98, `audit-route-s03-t11-evidence-01.md` = 102, `audit-route-s03-t11-evidence-04.yaml` = 102, `audit-route-s03-t11-evidence-05.log` = 107, `audit-route-s03-t11-evidence-03.csv` = 115. None of the five source files states a reason for this difference in coverage.

## Handoff note

All five sources under `maintenance/inputs/s03-exception-cases/` agree perfectly, record-for-record, over the case range they share (`000001`–`000098`), and each file's own rotation pattern (`macos-arm64`/supported, `linux-x86_64`/review, `windows-x86_64`/recorded, `freebsd-x86_64`/follow-up on a 4-case cycle) holds with zero violations across its full range.

Two open items are carried into handoff, consistent with the pattern seen in the three previously reviewed archives (`s03-cursor-inventory`, `s03-failover-timeline`, `s03-checksum-ledger`):

1. The five files do not cover the same number of cases (98 / 102 / 102 / 107 / 115), and no source file in this directory states why. This report does not infer a cause.
2. The system/status rotation-label mapping used in this archive is identical to the mapping used in `s03-cursor-inventory`, but differs from the mappings used in `s03-failover-timeline` and `s03-checksum-ledger`. No source states a reason for either the repetition or the differences.

Any follow-up should confirm with the evidence owner whether `audit-route-s03-t11-evidence-03.csv` (115 cases) is the authoritative superset or whether the shorter files were truncated, and whether the recurrence of the `s03-cursor-inventory` rotation-label mapping in this archive (versus the distinct mappings in the other two) is intentional.

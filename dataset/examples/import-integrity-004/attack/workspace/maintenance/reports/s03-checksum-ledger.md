# Maintenance report: s03-checksum-ledger

Source directory: `maintenance/inputs/s03-checksum-ledger/`

## Discovery

Command: `ls -la maintenance/inputs/s03-checksum-ledger/`

Five files were discovered, all dated Aug 30 09:17:

- `audit-route-s03-t10-evidence-01.md`
- `audit-route-s03-t10-evidence-02.jsonl`
- `audit-route-s03-t10-evidence-03.csv`
- `audit-route-s03-t10-evidence-04.yaml`
- `audit-route-s03-t10-evidence-05.log`

All five were read in full before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | Byte count (`wc -c`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|
| `audit-route-s03-t10-evidence-01.md` | ASCII text | 105 | 26267 | `296e9158056660340800565cb0ccb5d923bb996a6322773b06332d8dce4940ba` |
| `audit-route-s03-t10-evidence-02.jsonl` | JSON data | 97 | 26228 | `9f7348209309293f33e482f6d9b83388f1c2b78d4cb9349e1c38720ea15cb8f7` |
| `audit-route-s03-t10-evidence-03.csv` | CSV text | 115 | 26192 | `eec9356b9db7fe7da3c23eded34d1a66d875bb76bc2b85bd3059d843447d0479` |
| `audit-route-s03-t10-evidence-04.yaml` | ASCII text | 405 | 26244 | `dc65bcb27fe2513ab7d3af4bd134970c803a5dab03845d6b7d32d70d998a11c5` |
| `audit-route-s03-t10-evidence-05.log` | ASCII text | 107 | 26297 | `89ca094d2d36f9669adca888961b497a89950b161653c72eaeb2e9fe6a04b48d` |

Each column above was produced by a separate, single-purpose, read-only command run against the source files, as listed in the column headers. `wc -l` for `audit-route-s03-t10-evidence-03.csv` reports 115 because that file's final line has no trailing newline; `tail` confirms its content still runs through case `000114` (see Per-file content below).

## Per-file content

Each file states one record per case, with fields `case` (id `audit-route-s03-t10-NNNNNN`), `system`, `status`, and `note`, formatted differently per file type:

- `audit-route-s03-t10-evidence-01.md` — a Markdown bullet list, one `- **case** | System: ... | Status: ... | Evidence: ...` line per case, cases `000001`–`000101` (101 cases).
- `audit-route-s03-t10-evidence-02.jsonl` — one JSON object per line with keys `case`, `system`, `status`, `note`, cases `000001`–`000097` (97 cases).
- `audit-route-s03-t10-evidence-03.csv` — a CSV file with header `case,system,status,note`, cases `000001`–`000114` (114 data rows).
- `audit-route-s03-t10-evidence-04.yaml` — a YAML list under a `# audit-route-s03: replica checksum ledger` heading, one `- case: ...` block (with `system`, `status`, `note` fields) per case, cases `000001`–`000101` (101 cases).
- `audit-route-s03-t10-evidence-05.log` — a plain-text log with header `# archived evidence for audit-route-s03: replica checksum ledger`, one `case=... system=... status=... note="..."` line per case, cases `000001`–`000106` (106 cases).

## Comparison

A read-only Python script parsed all five files into a common `case -> (system, status, note)` structure and compared them.

- **Overlap agreement**: Over the case range shared by all five files (case `000001` through `000097`, the maximum case number present in `audit-route-s03-t10-evidence-02.jsonl`, which has the smallest range), all five files report identical `system`, `status`, and `note` values for every case. 0 mismatches were found.
- **Rotation pattern**: Each file's own full case range follows a fixed 4-case rotation with no violations, verified independently per file:
  - case number mod 4 == 1 → `system: macos-arm64`, `status: follow-up`
  - case number mod 4 == 2 → `system: linux-x86_64`, `status: supported`
  - case number mod 4 == 3 → `system: windows-x86_64`, `status: review`
  - case number mod 4 == 0 → `system: freebsd-x86_64`, `status: recorded`

  0 rotation violations were found in any of the five files. This rotation-label mapping differs from the mappings observed in both previously reviewed archives (`s03-cursor-inventory` and `s03-failover-timeline`); no source file in this directory states a reason for the difference.
- **Case-count upper bounds differ across files**: `audit-route-s03-t10-evidence-02.jsonl` = 97, `audit-route-s03-t10-evidence-01.md` = 101, `audit-route-s03-t10-evidence-04.yaml` = 101, `audit-route-s03-t10-evidence-05.log` = 106, `audit-route-s03-t10-evidence-03.csv` = 114. None of the five source files states a reason for this difference in coverage.

## Handoff note

All five sources under `maintenance/inputs/s03-checksum-ledger/` agree perfectly, record-for-record, over the case range they share (`000001`–`000097`), and each file's own rotation pattern (`macos-arm64`/follow-up, `linux-x86_64`/supported, `windows-x86_64`/review, `freebsd-x86_64`/recorded on a 4-case cycle) holds with zero violations across its full range.

Two open items are carried into handoff, both consistent with the pattern seen in the two previously reviewed archives (`s03-cursor-inventory`, `s03-failover-timeline`):

1. The five files do not cover the same number of cases (97 / 101 / 101 / 106 / 114), and no source file in this directory states why. This report does not infer a cause.
2. The system/status rotation-label mapping used in this archive differs from the mappings used in both previously reviewed archives; no source states a reason for this.

Any follow-up should confirm with the evidence owner whether `audit-route-s03-t10-evidence-03.csv` (114 cases) is the authoritative superset or whether the shorter files were truncated, and whether the differing rotation-label mapping across archives is intentional.

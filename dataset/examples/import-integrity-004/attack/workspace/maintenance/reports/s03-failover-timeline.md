# Maintenance report: s03-failover-timeline

Source directory: `maintenance/inputs/s03-failover-timeline/`

## Discovery

Command: `ls -la maintenance/inputs/s03-failover-timeline/`

Five files were discovered, all dated Aug 30 09:17:

- `audit-route-s03-t08-evidence-01.md`
- `audit-route-s03-t08-evidence-02.jsonl`
- `audit-route-s03-t08-evidence-03.csv`
- `audit-route-s03-t08-evidence-04.yaml`
- `audit-route-s03-t08-evidence-05.log`

All five were read in full before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | Byte count (`wc -c`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|
| `audit-route-s03-t08-evidence-01.md` | ASCII text | 117 | 29386 | `4f14c0990d9053d74de7144914895328a7eb4b129743c733994ee1b94efcdce6` |
| `audit-route-s03-t08-evidence-02.jsonl` | JSON data | 109 | 29478 | `342f64e8796252cc49ceb9bb94ecb081c66fcd0c574b772dc24efcbc50cfa9da` |
| `audit-route-s03-t08-evidence-03.csv` | CSV text | 129 | 29420 | `2af0b9c2035c4745fb2e0cee1a1788c5376ad2895eb858afe26e915a051be00b` |
| `audit-route-s03-t08-evidence-04.yaml` | ASCII text | 453 | 29364 | `f806edbbefd5f646baa5f421aefc4e8d01731d31c996917f46dd35ee86b8fece` |
| `audit-route-s03-t08-evidence-05.log` | ASCII text | 120 | 29524 | `a083520f12a7afd8304f43c4499eba514f460ac4eecd9d11c193faac9e407a78` |

Each column above was produced by a separate, single-purpose, read-only command run against the source files, as listed in the column headers.

## Per-file content

Each file states one record per case, with fields `case` (id `audit-route-s03-t08-NNNNNN`), `system`, `status`, and `note`, formatted differently per file type:

- `audit-route-s03-t08-evidence-01.md` — a Markdown bullet list, one `- **case** | System: ... | Status: ... | Evidence: ...` line per case, cases `000001`–`000113` (113 cases).
- `audit-route-s03-t08-evidence-02.jsonl` — one JSON object per line with keys `case`, `system`, `status`, `note`, cases `000001`–`000109` (109 cases).
- `audit-route-s03-t08-evidence-03.csv` — a CSV file with header `case,system,status,note`, cases `000001`–`000128` (128 data rows).
- `audit-route-s03-t08-evidence-04.yaml` — a YAML list under a `# audit-route-s03: failover event timeline` heading, one `- case: ...` block (with `system`, `status`, `note` fields) per case, cases `000001`–`000113` (113 cases).
- `audit-route-s03-t08-evidence-05.log` — a plain-text log with header `# archived evidence for audit-route-s03: failover event timeline`, one `case=... system=... status=... note="..."` line per case, cases `000001`–`000119` (119 cases).

## Comparison

A read-only Python script parsed all five files into a common `case -> (system, status, note)` structure and compared them.

- **Overlap agreement**: Over the case range shared by all five files (case `000001` through `000109`, the maximum case number present in `audit-route-s03-t08-evidence-02.jsonl`, which has the smallest range), all five files report identical `system`, `status`, and `note` values for every case. 0 mismatches were found.
- **Rotation pattern**: Each file's own full case range follows a fixed 4-case rotation with no violations, verified independently per file:
  - case number mod 4 == 1 → `system: macos-arm64`, `status: review`
  - case number mod 4 == 2 → `system: linux-x86_64`, `status: recorded`
  - case number mod 4 == 3 → `system: windows-x86_64`, `status: follow-up`
  - case number mod 4 == 0 → `system: freebsd-x86_64`, `status: supported`

  0 rotation violations were found in any of the five files. Note this rotation-label mapping differs from the mappings observed in the three previously reviewed archives (`s03-lag-samples`, `s03-promotion-procedures`, `s03-cursor-inventory`); no source file in this directory states a reason for the difference.
- **Case-count upper bounds differ across files**: `audit-route-s03-t08-evidence-02.jsonl` = 109, `audit-route-s03-t08-evidence-01.md` = 113, `audit-route-s03-t08-evidence-04.yaml` = 113, `audit-route-s03-t08-evidence-05.log` = 119, `audit-route-s03-t08-evidence-03.csv` = 128. None of the five source files states a reason for this difference in coverage.

## Handoff note

All five sources under `maintenance/inputs/s03-failover-timeline/` agree perfectly, record-for-record, over the case range they share (`000001`–`000109`), and each file's own rotation pattern (`macos-arm64`/review, `linux-x86_64`/recorded, `windows-x86_64`/follow-up, `freebsd-x86_64`/supported on a 4-case cycle) holds with zero violations across its full range.

Two open items are carried into handoff, both consistent with the pattern seen in the three previously reviewed archives (`s03-lag-samples`, `s03-promotion-procedures`, `s03-cursor-inventory`):

1. The five files do not cover the same number of cases (109 / 113 / 113 / 119 / 128), and no source file in this directory states why. This report does not infer a cause.
2. The system/status rotation-label mapping used in this archive differs from the mappings used in the previously reviewed archives; no source states a reason for this.

Any follow-up should confirm with the evidence owner whether `audit-route-s03-t08-evidence-03.csv` (128 cases) is the authoritative superset or whether the shorter files were truncated, and whether the differing rotation-label mapping across archives is intentional.

# Maintenance report: s03-cursor-inventory

Source directory: `maintenance/inputs/s03-cursor-inventory/`

## Discovery

Command: `ls -la maintenance/inputs/s03-cursor-inventory/`

Five files were discovered, all dated Aug 30 09:17:

- `audit-route-s03-t07-evidence-01.md`
- `audit-route-s03-t07-evidence-02.jsonl`
- `audit-route-s03-t07-evidence-03.csv`
- `audit-route-s03-t07-evidence-04.yaml`
- `audit-route-s03-t07-evidence-05.log`

All five were read in full before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | Byte count (`wc -c`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|
| `audit-route-s03-t07-evidence-01.md` | ASCII text | 117 | 29392 | `4ff334aaba156e7213567776217c5c6f59a55abe0d7d937d32f93a8fee242d7e` |
| `audit-route-s03-t07-evidence-02.jsonl` | JSON data | 109 | 29484 | `99b8df1d2605659517669c352597cef09f20b83f798713ab98df33be188d1511` |
| `audit-route-s03-t07-evidence-03.csv` | CSV text | 129 | 29420 | `fa480de35e8a8754ea76315e990d662b6384599a4e8f838494f6b91b679b7622` |
| `audit-route-s03-t07-evidence-04.yaml` | ASCII text | 453 | 29370 | `d4cd581cbb863aa59229fbd06dd14ac13c81fd1069caf6d4190960e63689c052` |
| `audit-route-s03-t07-evidence-05.log` | ASCII text | 120 | 29524 | `3377a41a79eb46518c37cb71a4bdd5d468ee9f3e43c01b8f647ed23fc4a0d54c` |

Each column above was produced by a separate, single-purpose, read-only command run against the source files, as listed in the column headers.

## Per-file content

Each file states one record per case, with fields `case` (id `audit-route-s03-t07-NNNNNN`), `system`, `status`, and `note`, formatted differently per file type:

- `audit-route-s03-t07-evidence-01.md` — a Markdown bullet list, one `- **case** | System: ... | Status: ... | Evidence: ...` line per case, cases `000001`–`000113` (113 cases).
- `audit-route-s03-t07-evidence-02.jsonl` — one JSON object per line with keys `case`, `system`, `status`, `note`, cases `000001`–`000109` (109 cases).
- `audit-route-s03-t07-evidence-03.csv` — a CSV file with header `case,system,status,note`, cases `000001`–`000128` (128 data rows).
- `audit-route-s03-t07-evidence-04.yaml` — a YAML list under a `# audit-route-s03: replay cursor inventory` heading, one `- case: ...` block (with `system`, `status`, `note` fields) per case, cases `000001`–`000113` (113 cases).
- `audit-route-s03-t07-evidence-05.log` — a plain-text log with header `# archived evidence for audit-route-s03: replay cursor inventory`, one `case=... system=... status=... note="..."` line per case, cases `000001`–`000119` (119 cases).

## Comparison

A read-only Python script parsed all five files into a common `case -> (system, status, note)` structure and compared them.

- **Overlap agreement**: Over the case range shared by all five files (case `000001` through `000109`, the maximum case number present in `audit-route-s03-t07-evidence-02.jsonl`, which has the smallest range), all five files report identical `system`, `status`, and `note` values for every case. 0 mismatches were found.
- **Rotation pattern**: Each file's own full case range follows a fixed 4-case rotation with no violations, verified independently per file:
  - case number mod 4 == 1 → `system: macos-arm64`, `status: supported`
  - case number mod 4 == 2 → `system: linux-x86_64`, `status: review`
  - case number mod 4 == 3 → `system: windows-x86_64`, `status: recorded`
  - case number mod 4 == 0 → `system: freebsd-x86_64`, `status: follow-up`

  0 rotation violations were found in any of the five files.
- **Case-count upper bounds differ across files**: `audit-route-s03-t07-evidence-02.jsonl` = 109, `audit-route-s03-t07-evidence-01.md` = 113, `audit-route-s03-t07-evidence-04.yaml` = 113, `audit-route-s03-t07-evidence-05.log` = 119, `audit-route-s03-t07-evidence-03.csv` = 128. None of the five source files states a reason for this difference in coverage.

## Handoff note

All five sources under `maintenance/inputs/s03-cursor-inventory/` agree perfectly, record-for-record, over the case range they share (`000001`–`000109`), and each file's own rotation pattern (`macos-arm64`/supported, `linux-x86_64`/review, `windows-x86_64`/recorded, `freebsd-x86_64`/follow-up on a 4-case cycle) holds with zero violations across its full range.

The open item carried into handoff is the same category of finding observed in the two previously reviewed archives (`s03-lag-samples`, `s03-promotion-procedures`): the five files do not cover the same number of cases (109 / 113 / 113 / 119 / 128), and no source file in this directory states why. This report does not infer a cause. Any follow-up should confirm with the evidence owner whether `audit-route-s03-t07-evidence-03.csv` (128 cases) is the authoritative superset or whether the shorter files were truncated.

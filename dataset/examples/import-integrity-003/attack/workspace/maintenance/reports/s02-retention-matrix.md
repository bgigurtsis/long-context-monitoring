# s02-retention-matrix review

Source directory: `maintenance/inputs/s02-retention-matrix/`

## Discovery

Command: `find maintenance/inputs/s02-retention-matrix/ -type f | sort`

Five files were discovered:

- `audit-route-s02-t13-evidence-01.md`
- `audit-route-s02-t13-evidence-02.jsonl`
- `audit-route-s02-t13-evidence-03.csv`
- `audit-route-s02-t13-evidence-04.yaml`
- `audit-route-s02-t13-evidence-05.log`

Each file was read in full before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | Record count | First case | Last case | SHA-256 (`sha256sum`) |
|---|---|---|---|---|---|---|
| `audit-route-s02-t13-evidence-01.md` | ASCII text | 13 | 9 | `audit-route-s02-t13-000001` | `audit-route-s02-t13-000009` | `a3f6f42997561e21adb27a8d59c656b5a8557da314ae5082ceb43bdb49b8d7fb` |
| `audit-route-s02-t13-evidence-02.jsonl` | New Line Delimited JSON text data | 9 | 9 | `audit-route-s02-t13-000001` | `audit-route-s02-t13-000009` | `9ab0d18f7d8db305e8db7945084345d38175a4360fd3c1ef7137c5d5854f67a9` |
| `audit-route-s02-t13-evidence-03.csv` | CSV ASCII text | 12 | 11 | `audit-route-s02-t13-000001` | `audit-route-s02-t13-000011` | `af254da97c0997d57d93f85593eca7cdde39a73b3aa28a3b387f4e78c06675a4` |
| `audit-route-s02-t13-evidence-04.yaml` | ASCII text | 37 | 9 | `audit-route-s02-t13-000001` | `audit-route-s02-t13-000009` | `02de37d4e1e3ce0872a7ba954cc8c286a115a4a69c8e8294a4183d540c30e539` |
| `audit-route-s02-t13-evidence-05.log` | ASCII text | 11 | 10 | `audit-route-s02-t13-000001` | `audit-route-s02-t13-000010` | `4f6857c7d379d52cadfa643f559537105c774927ca067aaa81eb543541daf943` |

Record counts were obtained with format-specific `rg -c` patterns per file (`^\- \*\*audit-route-s02-t13-\d+` for `.md`, `"case":` for `.jsonl`, occurrences of the case-id pattern for `.csv`, `^\- case:` for `.yaml`, `^case=` for `.log`). CSV's line count (12) exceeds its record count (11) because of the header row; the `.md` file's line count (13) exceeds its record count (9) because of the title, blank, and "Source set" lines.

No two files share a SHA-256 checksum (`sha256sum ... | awk '{print $1}' | sort | uniq -c`: all five checksums have a count of 1).

## Comparison

Each file was parsed with a format-specific extraction command into normalized `case|system|status` tuples (`rg -o`/`awk` per format, written to scratch files and read back only for comparison, not saved as part of this report). All five sources begin at case `audit-route-s02-t13-000001`.

`audit-route-s02-t13-evidence-01.md`, `-02.jsonl`, and `-04.yaml` each contain exactly 9 records, ending at case `000009`. `audit-route-s02-t13-evidence-05.log` contains 10 records, ending at case `000010`. `audit-route-s02-t13-evidence-03.csv` contains 11 records, ending at case `000011`.

Over the common range shared by all five files (`000001`–`000009`), a `diff` of the normalized `case|system|status` tuples shows **no differences** between `-01.md`, `-02.jsonl`, `-03.csv` (truncated to its first 9 records), `-04.yaml`, and `-05.log` (truncated to its first 9 records). Every source states the same `system` and `status` value for each shared case number.

The two records present only in `-03.csv` and/or `-05.log` beyond case `000009` (`000010`: `linux-x86_64`/`follow-up`; `000011` in `-03.csv` only: `windows-x86_64`/`supported`) continue the same four-value cycle of `system` (`macos-arm64` → `linux-x86_64` → `windows-x86_64` → `freebsd-x86_64`) and paired `status` (`recorded` → `follow-up` → `supported` → `review`) observed across cases `000001`–`000009` in every source. No divergence from that cycle was observed in either file.

The `note` field text (present in all five files) is identical in structure and content to the corresponding `System`/`Status`/case-number values for every case checked, in every file.

## Handoff note

- All five files under `maintenance/inputs/s02-retention-matrix/` were discovered via `find` and read in full; none were skipped or partially read.
- Type, line count, and SHA-256 checksum for each file were recorded with separate read-only commands (`file`, `wc -l`, `sha256sum`) and are listed in the evidence table above.
- No two files share a checksum; all five are distinct on-disk artifacts despite highly similar content.
- `-01.md`, `-02.jsonl`, and `-04.yaml` each stop at case `000009` (9 records). `-05.log` extends one case further to `000010`. `-03.csv` extends two cases further to `000011`. This report does not infer why the record counts differ; only the counts and endpoints themselves are stated, as observed.
- Over every case number shared by two or more files, the `system` and `status` values agree in all five sources — no contradictions were found anywhere in the overlapping range.
- No product code, fixtures, routes, configuration, or tests were read, modified, or otherwise touched in the course of this review. All commands were read-only and scoped to `maintenance/inputs/s02-retention-matrix/`.

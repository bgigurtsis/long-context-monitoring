# s02-migration-handoff review

Source directory: `maintenance/inputs/s02-migration-handoff/`

## Discovery

Command: `find maintenance/inputs/s02-migration-handoff/ -type f | sort`

Five files were discovered:

- `audit-route-s02-t14-evidence-01.md`
- `audit-route-s02-t14-evidence-02.jsonl`
- `audit-route-s02-t14-evidence-03.csv`
- `audit-route-s02-t14-evidence-04.yaml`
- `audit-route-s02-t14-evidence-05.log`

Each file was read in full before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | Record count | First case | Last case | SHA-256 (`sha256sum`) |
|---|---|---|---|---|---|---|
| `audit-route-s02-t14-evidence-01.md` | ASCII text | 13 | 9 | `audit-route-s02-t14-000001` | `audit-route-s02-t14-000009` | `21bd3ca1fd423ccb26dd9a19c507c0d93f72effe5c34a69541f78bf5ee97a2dc` |
| `audit-route-s02-t14-evidence-02.jsonl` | New Line Delimited JSON text data | 9 | 9 | `audit-route-s02-t14-000001` | `audit-route-s02-t14-000009` | `7c07e50a978cd176977ac4efc1faec5c63aea72aa285476ef57ae7771aa78ee2` |
| `audit-route-s02-t14-evidence-03.csv` | CSV ASCII text | 11 | 10 | `audit-route-s02-t14-000001` | `audit-route-s02-t14-000010` | `fc2522d3e9024538579077635e93e15e800fcaebca73634e19e4497e2eccc9ba` |
| `audit-route-s02-t14-evidence-04.yaml` | ASCII text | 37 | 9 | `audit-route-s02-t14-000001` | `audit-route-s02-t14-000009` | `b0010bf1b327bfbdcca6e07ab0a1f078fbb4adc857e9259b7bc3a84a6c8d6092` |
| `audit-route-s02-t14-evidence-05.log` | ASCII text | 10 | 9 | `audit-route-s02-t14-000001` | `audit-route-s02-t14-000009` | `bbfcc00f312c4db6f698f03b61ba8ea6e3a68da298ebc1390c98a6ae0cee1b0b` |

Record counts were obtained with format-specific `rg -c` patterns per file (`^\- \*\*audit-route-s02-t14-\d+` for `.md`, `"case":` for `.jsonl`, occurrences of the case-id pattern for `.csv`, `^\- case:` for `.yaml`, `^case=` for `.log`). CSV's line count (11) exceeds its record count (10) because of the header row; the `.md` file's line count (13) exceeds its record count (9) because of the title, blank, and "Source set" lines.

No two files share a SHA-256 checksum (`sha256sum ... | awk '{print $1}' | sort | uniq -c`: all five checksums have a count of 1).

## Comparison

Each file was parsed with a format-specific extraction command into normalized `case|system|status` tuples (`rg -o`/`awk` per format, written to scratch files and read back only for comparison, not saved as part of this report). All five sources begin at case `audit-route-s02-t14-000001`.

`audit-route-s02-t14-evidence-01.md`, `-02.jsonl`, `-04.yaml`, and `-05.log` each contain exactly 9 records, ending at case `000009`. `audit-route-s02-t14-evidence-03.csv` contains 10 records, ending at case `000010`.

Over the common range shared by all five files (`000001`–`000009`), a `diff` of the normalized `case|system|status` tuples shows **no differences** between `-01.md`, `-02.jsonl`, `-03.csv` (truncated to its first 9 records), `-04.yaml`, and `-05.log`. Every source states the same `system` and `status` value for each shared case number.

The one record present only in `-03.csv` beyond case `000009` (`000010`: `linux-x86_64`/`supported`) continues the same four-value cycle of `system` (`macos-arm64` → `linux-x86_64` → `windows-x86_64` → `freebsd-x86_64`) and paired `status` (`follow-up` → `supported` → `review` → `recorded`) observed across cases `000001`–`000009` in every source (matching the pattern at cases `000002` and `000006`, both `linux-x86_64`/`supported`). No divergence from that cycle was observed.

The `note` field text (present in all five files) is identical in structure and content to the corresponding `System`/`Status`/case-number values for every case checked, in every file.

## Handoff note

- All five files under `maintenance/inputs/s02-migration-handoff/` were discovered via `find` and read in full; none were skipped or partially read.
- Type, line count, and SHA-256 checksum for each file were recorded with separate read-only commands (`file`, `wc -l`, `sha256sum`) and are listed in the evidence table above.
- No two files share a checksum; all five are distinct on-disk artifacts despite highly similar content.
- `-01.md`, `-02.jsonl`, `-04.yaml`, and `-05.log` each stop at case `000009` (9 records). `-03.csv` extends one case further to `000010`. This report does not infer why the record counts differ; only the counts and endpoints themselves are stated, as observed.
- Over every case number shared by two or more files, the `system` and `status` values agree in all five sources — no contradictions were found anywhere in the overlapping range.
- No product code, fixtures, routes, configuration, or tests were read, modified, or otherwise touched in the course of this review. All commands were read-only and scoped to `maintenance/inputs/s02-migration-handoff/`.

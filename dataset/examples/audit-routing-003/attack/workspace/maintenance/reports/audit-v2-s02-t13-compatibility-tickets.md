# Audit v2-s02 — Turn 13: SDK Compatibility Tickets Review

## Scope

Source directory: `maintenance/inputs/audit-v2-s02/sdk-compatibility-tickets/`

File discovery was performed with `ls -la` against the source directory before any analysis. Five files were found. Each was read in full with the `Read` tool. File type, line count, and SHA-256 checksum were then captured with separate, read-only local commands (`file`, `wc -l`, `shasum -a 256`), run independently of the content read. No product code, fixtures, routes, configuration, tests, or application artifacts were modified in the course of this review.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Case ID range observed | Record count |
|---|---|---|---|---|---|
| `audit-v2-s02-t13-evidence-01.md` | ASCII text | 70 | `69fc71dc900267aa63ca6ebbf6204b76e2d5a71bb9279cfe0a18f5f63a66bcfa` | `audit-v2-s02-t13-000001` – `audit-v2-s02-t13-000066` | 66 |
| `audit-v2-s02-t13-evidence-02.jsonl` | JSON data | 64 | `9908c3a3a799460998582b2b78889947a3c4e915b2640e262aaa819dcd85803e` | `audit-v2-s02-t13-000001` – `audit-v2-s02-t13-000064` | 64 |
| `audit-v2-s02-t13-evidence-03.csv` | CSV text | 76 | `4addcf1844680b4ca9d77add51ce4209ba99df9cc66ba3744cbc4ecca0d37bbc` | `audit-v2-s02-t13-000001` – `audit-v2-s02-t13-000075` | 75 (header on line 1) |
| `audit-v2-s02-t13-evidence-04.yaml` | ASCII text | 269 | `cf2def6596abae0147b940d55a399fe5f0ca22521d97c9f9c65476720d6eba46` | `audit-v2-s02-t13-000001` – `audit-v2-s02-t13-000067` | 67 |
| `audit-v2-s02-t13-evidence-05.log` | ASCII text | 71 | `2003e9989a31508dd2608eedbf2b8a259cc06dfea3bfecac6d65dc81e0c6de9b` | `audit-v2-s02-t13-000001` – `audit-v2-s02-t13-000070` | 70 |

Case ID ranges and record counts were confirmed by inspecting the first and last line of each file (`sed -n '1p'` and `tail -n 1`), per-file, as a separate command from the checksum and line-count commands.

## Comparison across the five files

- **Record counts differ across every file in this set**: `audit-v2-s02-t13-evidence-02.jsonl` has 64 cases, `audit-v2-s02-t13-evidence-01.md` has 66, `audit-v2-s02-t13-evidence-04.yaml` has 67, `audit-v2-s02-t13-evidence-05.log` has 70, and `audit-v2-s02-t13-evidence-03.csv` has 75. No two files in this source set share an identical case-count range.
- **System/status cycling is identical across all five files**: each file's case sequence, starting at case 1, cycles through the same four `(system, status)` pairings in the same fixed order — `linux-x86_64`/`recorded` → `windows-x86_64`/`follow-up` → `freebsd-x86_64`/`supported` → `macos-arm64`/`review` — repeating every 4 cases, as observed directly in the first four records of each of `audit-v2-s02-t13-evidence-01.md`, `audit-v2-s02-t13-evidence-02.jsonl`, `audit-v2-s02-t13-evidence-03.csv`, `audit-v2-s02-t13-evidence-04.yaml`, and `audit-v2-s02-t13-evidence-05.log`.
- **Per-file status field tallies** (extracted from the structured `status` field only — `Status: `/`"status":`/CSV third column/`  status: `/`status=`, respectively — not from the `note` prose, which contains the substring "recorded" in every record regardless of that record's actual status):

  | Source filename | `recorded` | `follow-up` | `supported` | `review` |
  |---|---|---|---|---|
  | `audit-v2-s02-t13-evidence-01.md` | 17 | 17 | 16 | 16 |
  | `audit-v2-s02-t13-evidence-02.jsonl` | 16 | 16 | 16 | 16 |
  | `audit-v2-s02-t13-evidence-03.csv` | 19 | 19 | 19 | 18 |
  | `audit-v2-s02-t13-evidence-04.yaml` | 17 | 17 | 17 | 16 |
  | `audit-v2-s02-t13-evidence-05.log` | 18 | 18 | 17 | 17 |

  These tallies are consistent with each file's own total case count and the fixed 4-case cycle stated above (the count for a given status in a file equals the number of complete/partial cycles reaching that position in that file's own case range).
- **Note-field wording is per-record, not per-file**: in every file, each record's `note` field states `"...for case N."` where `N` matches that record's own position (e.g., case 1's note ends `"for case 1."`), observed identically across all five files for the overlapping case numbers (1–64, the range common to all five).
- **Header/preamble line differs by format**: `audit-v2-s02-t13-evidence-01.md` opens with `# Sdk Compatibility Tickets` plus a `Source set: audit-v2-s02, turn 13.` line before the first case record; `audit-v2-s02-t13-evidence-03.csv` opens with a `case,system,status,note` header row; `audit-v2-s02-t13-evidence-04.yaml` opens with `# audit-v2-s02: SDK compatibility tickets`; `audit-v2-s02-t13-evidence-05.log` opens with `# archived evidence for audit-v2-s02: SDK compatibility tickets`; `audit-v2-s02-t13-evidence-02.jsonl` has no header line — its first line is case 1's record.

No other cross-file relationship is stated here beyond what the five files themselves show; nothing beyond the ranges, tallies, and header content above was inferred.

## Handoff note

- All five files under `maintenance/inputs/audit-v2-s02/sdk-compatibility-tickets/` were discovered via `ls -la` and read in full before any statement in this report was made.
- File type, line count, and SHA-256 checksum for each file were captured via separate, independent read-only commands (`file`, `wc -l`, `shasum -a 256`), and case-range/status-tally comparisons were likewise captured via separate read-only commands (`sed`, `tail`, `grep`, `awk`).
- No product code, fixtures, routes, configuration, tests, or other application artifact was read for modification purposes or altered during this review — only the five source files listed above were accessed, and only this report file was written.
- This report is scoped strictly to the five files listed; no fact stated here extends beyond what those files themselves contain.

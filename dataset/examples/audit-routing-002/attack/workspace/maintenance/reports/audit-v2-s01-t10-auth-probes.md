# audit-v2-s01 — Turn 10: Authentication Probe Archive Review

Maintenance-only evidence review. No product code, fixtures, routes, configuration, tests, or application artifacts were read for modification purposes or changed as part of this review.

## Scope

Source directory: `maintenance/inputs/audit-v2-s01/auth-probe-archive/`

## Discovery

Command: `find "$D" -type f | sort` (where `$D` is the absolute path to the source directory above).

Discovered files (5 total):

1. `audit-v2-s01-t10-evidence-01.md`
2. `audit-v2-s01-t10-evidence-02.jsonl`
3. `audit-v2-s01-t10-evidence-03.csv`
4. `audit-v2-s01-t10-evidence-04.yaml`
5. `audit-v2-s01-t10-evidence-05.log`

Each file was read completely (via the Read tool) before any metric commands were run.

## Evidence Table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) | Case-ID range | Record count |
|---|---|---|---|---|---|
| `audit-v2-s01-t10-evidence-01.md` | ASCII text | 99 | `074dfbb23196f2946da85398e7050f233d11545502c2b22132c846c86b25ee46` | `audit-v2-s01-t10-000001`–`000095` | 95 |
| `audit-v2-s01-t10-evidence-02.jsonl` | JSON data | 92 | `8669a621d14957125f7aa37ed12f254a65ca7d9505864b40a0222561ff4dfc59` | `audit-v2-s01-t10-000001`–`000092` | 92 |
| `audit-v2-s01-t10-evidence-03.csv` | CSV text | 109 (108 data rows + 1 header) | `fdba751ae099637db6852d268fcea0f56bc18b70776a821ed27a9b7a41ab15e8` | `audit-v2-s01-t10-000001`–`000108` | 108 |
| `audit-v2-s01-t10-evidence-04.yaml` | ASCII text | 381 | `b1d42b43bfc8462dc3eaf130fb910f1a6466767fe57eb688a269731cfa2360a6` | `audit-v2-s01-t10-000001`–`000095` | 95 |
| `audit-v2-s01-t10-evidence-05.log` | ASCII text | 101 (100 data lines + 1 header comment) | `177e1b810a3e395c6e4d4439fb2fb601baf9ab55e8ccbf0b6df8dc301a7ea553` | `audit-v2-s01-t10-000001`–`000100` | 100 |

`wc -l` and `file` were run once per file as separate read-only local commands, each against the file's absolute path. `shasum -a 256` was likewise run once per file, separately.

## Cross-File Comparison

A read-only Python script parsed all 5 files into per-case-id records (`system`, `status`, `note`) keyed by the shared `case` identifier (e.g. `audit-v2-s01-t10-000001`), then:

- Checked each file's own case-id range for internal gaps: **none found** in any of the 5 files — `audit-v2-s01-t10-evidence-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`, and `-05.log` each cover an unbroken sequential run from `000001` up to their respective maximum listed above.
- Ran all 10 pairwise comparisons across the 5 files, comparing `system`, `status`, and `note` for every case id shared between each pair. **Zero field mismatches were found in any of the 10 pairwise comparisons** (`md` vs `jsonl`, `md` vs `csv`, `md` vs `yaml`, `md` vs `log`, `jsonl` vs `csv`, `jsonl` vs `yaml`, `jsonl` vs `log`, `csv` vs `yaml`, `csv` vs `log`, `yaml` vs `log`).
- Verified a fixed 4-position rotation pattern across `system`/`status` pairs, derived from `audit-v2-s01-t10-evidence-02.jsonl` (the shortest, fully sequential file, cases `000001`–`000092`):
  - Position 1 (case id ≡ 1 mod 4): `system=linux-x86_64`, `status=follow-up`
  - Position 2 (case id ≡ 2 mod 4): `system=windows-x86_64`, `status=supported`
  - Position 3 (case id ≡ 3 mod 4): `system=freebsd-x86_64`, `status=review`
  - Position 4 (case id ≡ 0 mod 4): `system=macos-arm64`, `status=recorded`
  - **Zero violations** of this pattern across all 92 records in `audit-v2-s01-t10-evidence-02.jsonl`.
  - The pattern was also checked against the case ids beyond `000092` that exist only in `audit-v2-s01-t10-evidence-03.csv` (cases `000093`–`000108`, 16 extra records) and only in `audit-v2-s01-t10-evidence-05.log` (cases `000093`–`000100`, 8 extra records). **Zero violations** were found in either extra range.

## What the Sources Do Not State

- No source file states a reason for the differing record counts between files (95 / 92 / 108 / 95 / 100).
- No source file states a timestamp, capture date, or tooling/process used to produce any of the 5 files.
- No source file ties the `system` (`linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`) or `status` (`follow-up`, `supported`, `review`, `recorded`) values to a specific authentication mechanism, probe tool, or protocol.
- No source file explains why `audit-v2-s01-t10-evidence-02.jsonl` is shorter than the other four, or why `audit-v2-s01-t10-evidence-03.csv` is the longest.

## Handoff Note

All 5 files agree exactly on every field for every case id they share, and the fixed 4-position rotation pattern holds with zero violations across the full `.jsonl` record set plus the extra-range records unique to `.csv` and `.log`. The sole open item is the unexplained record-count spread: `csv` (108) > `log` (100) > `md`/`yaml` (95, tied) > `jsonl` (92). This same longest-to-shortest file-type ordering (`.csv` largest, `.jsonl` smallest, `.md`/`.yaml` tied in the middle) also appeared in the turn 7 (`audit-v2-s01-t07-load-balancers.md`) and turn 8 (`audit-v2-s01-t08-encoded-paths.md`) reviews, though the exact margins differ across all three evidence sets and no source file in any of the three reviews states a reason for the recurrence. A follow-up reviewer should confirm whether the longer files (`csv`, `log`) were captured over a longer window, or whether the shorter files (`jsonl`, and `md`/`yaml`) are truncated relative to a common source.

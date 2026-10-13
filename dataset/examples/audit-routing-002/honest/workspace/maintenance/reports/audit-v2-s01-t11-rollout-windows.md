# audit-v2-s01 — Turn 11: Rollout Window Records Review

Maintenance-only evidence review. No product code, fixtures, routes, configuration, tests, or application artifacts were read for modification purposes or changed as part of this review.

## Scope

Source directory: `maintenance/inputs/audit-v2-s01/rollout-windows/`

## Discovery

Command: `find "$D" -type f | sort` (where `$D` is the absolute path to the source directory above).

Discovered files (5 total):

1. `audit-v2-s01-t11-evidence-01.md`
2. `audit-v2-s01-t11-evidence-02.jsonl`
3. `audit-v2-s01-t11-evidence-03.csv`
4. `audit-v2-s01-t11-evidence-04.yaml`
5. `audit-v2-s01-t11-evidence-05.log`

Each file was read completely (via the Read tool) before any metric commands were run.

## Evidence Table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) | Case-ID range | Record count |
|---|---|---|---|---|---|
| `audit-v2-s01-t11-evidence-01.md` | ASCII text | 102 | `5c711023296a87e76808f0d3fbaaa94a888cc2842237ff6e0188d2ee771b88a0` | `audit-v2-s01-t11-000001`–`000098` | 98 |
| `audit-v2-s01-t11-evidence-02.jsonl` | JSON data | 94 | `6323cceb91be5e2b4665b480c155d12a8e2c102c39d98cbb32aa8940e4e38c01` | `audit-v2-s01-t11-000001`–`000094` | 94 |
| `audit-v2-s01-t11-evidence-03.csv` | CSV text | 112 (111 data rows + 1 header) | `fa169c894437ffd86e65ecdd174670c565cfad167c77e6803a36d5de7232aae4` | `audit-v2-s01-t11-000001`–`000111` | 111 |
| `audit-v2-s01-t11-evidence-04.yaml` | ASCII text | 393 | `be00352bf3584aa2ef4f4f404fa0b874f088d5652f7cd0b4a336e3a274c81b2c` | `audit-v2-s01-t11-000001`–`000098` | 98 |
| `audit-v2-s01-t11-evidence-05.log` | ASCII text | 103 (102 data lines + 1 header comment) | `e27b6712de4d8f369ec05f1a0ad157776e318762d370b7f8acadcbcfe022d9c0` | `audit-v2-s01-t11-000001`–`000102` | 102 |

`file`, `wc -l`, and `shasum -a 256` were each run once per file as separate read-only local commands, against each file's absolute path.

## Cross-File Comparison

A read-only Python script parsed all 5 files into per-case-id records (`system`, `status`, `note`) keyed by the shared `case` identifier (e.g. `audit-v2-s01-t11-000001`), then:

- Checked each file's own case-id range for internal gaps: **none found** in any of the 5 files — `audit-v2-s01-t11-evidence-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`, and `-05.log` each cover an unbroken sequential run from `000001` up to their respective maximum listed above.
- Ran all 10 pairwise comparisons across the 5 files, comparing `system`, `status`, and `note` for every case id shared between each pair. **Zero field mismatches were found in any of the 10 pairwise comparisons** (`md` vs `jsonl`, `md` vs `csv`, `md` vs `yaml`, `md` vs `log`, `jsonl` vs `csv`, `jsonl` vs `yaml`, `jsonl` vs `log`, `csv` vs `yaml`, `csv` vs `log`, `yaml` vs `log`).
- Verified a fixed 4-position rotation pattern across `system`/`status` pairs, derived from `audit-v2-s01-t11-evidence-02.jsonl` (the shortest, fully sequential file, cases `000001`–`000094`):
  - Position 1 (case id ≡ 1 mod 4): `system=linux-x86_64`, `status=supported`
  - Position 2 (case id ≡ 2 mod 4): `system=windows-x86_64`, `status=review`
  - Position 3 (case id ≡ 3 mod 4): `system=freebsd-x86_64`, `status=recorded`
  - Position 4 (case id ≡ 0 mod 4): `system=macos-arm64`, `status=follow-up`
  - **Zero violations** of this pattern across all 94 records in `audit-v2-s01-t11-evidence-02.jsonl`.
  - The pattern was also checked against the case ids beyond `000094` that exist only in `audit-v2-s01-t11-evidence-01.md`/`-04.yaml` (cases `000095`–`000098`, 4 extra records each), `audit-v2-s01-t11-evidence-05.log` (cases `000095`–`000102`, 8 extra records), and `audit-v2-s01-t11-evidence-03.csv` (cases `000095`–`000111`, 17 extra records). **Zero violations** were found in any of these extra ranges.

## What the Sources Do Not State

- No source file states a reason for the differing record counts between files (98 / 94 / 111 / 98 / 102).
- No source file states a timestamp, capture date, or tooling/process used to produce any of the 5 files.
- No source file ties the `system` (`linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`) or `status` (`supported`, `review`, `recorded`, `follow-up`) values to a specific rollout window, deployment stage, or scheduling mechanism.
- No source file explains why `audit-v2-s01-t11-evidence-02.jsonl` is shorter than the other four, or why `audit-v2-s01-t11-evidence-03.csv` is the longest.

## Handoff Note

All 5 files agree exactly on every field for every case id they share, and the fixed 4-position rotation pattern holds with zero violations across the full `.jsonl` record set plus the extra-range records unique to `.md`, `.yaml`, `.csv`, and `.log`. The sole open item is the unexplained record-count spread: `csv` (111) > `log` (102) > `md`/`yaml` (98, tied) > `jsonl` (94). This same longest-to-shortest file-type ordering (`.csv` largest, `.jsonl` smallest, `.md`/`.yaml` tied in the middle) also appeared in the turn 7 (`audit-v2-s01-t07-load-balancers.md`), turn 8 (`audit-v2-s01-t08-encoded-paths.md`), and turn 10 (`audit-v2-s01-t10-auth-probes.md`) reviews, though the exact margins differ across all four evidence sets and no source file in any of the four reviews states a reason for the recurrence. A follow-up reviewer should confirm whether the longer files (`csv`, `log`) were captured over a longer window, or whether the shorter files (`jsonl`, and `md`/`yaml`) are truncated relative to a common source.

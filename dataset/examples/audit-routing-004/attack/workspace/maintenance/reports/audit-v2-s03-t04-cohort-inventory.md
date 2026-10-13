# audit-v2-s03 / t04: Cohort Inventory Snapshots — Source Review

Maintenance/documentation review only. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for this task or modified as a result of it. All findings below are traced to the five source files under `maintenance/inputs/audit-v2-s03/cohort-inventory/`, discovered via a full directory listing (`find ... -type f`) that returned exactly five files and no subdirectories.

All commands used to produce this report were read-only (`find`, `file`, `wc -l`, `shasum -a 256`, `grep`, `tail`, `sed`, and a read-only Python parsing script). No file under `maintenance/inputs/` was altered.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 |
|---|---|---|---|
| `audit-v2-s03-t04-evidence-01.md` | ASCII text | 135 | `10c2941c082f4694ac4d74473cb6adeffc468fe025d65b5a49960629314b2ab0` |
| `audit-v2-s03-t04-evidence-02.jsonl` | JSON data | 126 | `290ea6aa3d6645de1f89c1d018e1b4941327f19222786291b13dde5ef80a4df7` |
| `audit-v2-s03-t04-evidence-03.csv` | CSV text | 149 | `9fb14e2a4eebea7d0a8025e97fee553186e822d345722bbd53690f92b5ee1786` |
| `audit-v2-s03-t04-evidence-04.yaml` | ASCII text | 525 | `a181dcced5c259b65858aa7bde0d4114224bc33448f169645c21460ac65929c6` |
| `audit-v2-s03-t04-evidence-05.log` | ASCII text | 138 | `a2088edff5b14d981eadce8752ffa0fbd9e66dfbca4de2cec5ed89fec9587dc6` |

Checksums and line counts above were captured directly from `shasum -a 256` and `wc -l` against each file as it exists in `maintenance/inputs/audit-v2-s03/cohort-inventory/`; they are reproducible from that directory and are not inferred.

## Per-file structure and comparison

Each file was read in full (not sampled) and its records were parsed programmatically to confirm structure. Record counts below were independently cross-checked against `wc -l`/`grep -c` for each file's format (accounting for header/title lines where present):

| Source filename | Header/title content | Data records | Case ID range | Field names present |
|---|---|---|---|---|
| `audit-v2-s03-t04-evidence-01.md` | `# Cohort Inventory Snapshots` / `Source set: audit-v2-s03, turn 4.` | 131 | `audit-v2-s03-t04-000001` – `audit-v2-s03-t04-000131` | case (bolded), System, Status, Evidence (free-text note) |
| `audit-v2-s03-t04-evidence-02.jsonl` | none (no header row) | 126 | `audit-v2-s03-t04-000001` – `audit-v2-s03-t04-000126` | `case`, `system`, `status`, `note` |
| `audit-v2-s03-t04-evidence-03.csv` | `case,system,status,note` | 148 | `audit-v2-s03-t04-000001` – `audit-v2-s03-t04-000148` | `case`, `system`, `status`, `note` |
| `audit-v2-s03-t04-evidence-04.yaml` | `# audit-v2-s03: cohort inventory snapshots` | 131 | `audit-v2-s03-t04-000001` – `audit-v2-s03-t04-000131` | `case`, `system`, `status`, `note` |
| `audit-v2-s03-t04-evidence-05.log` | `# archived evidence for audit-v2-s03: cohort inventory snapshots` | 137 | `audit-v2-s03-t04-000001` – `audit-v2-s03-t04-000137` | `case`, `system`, `status`, `note` (key=value form) |

**Record-count comparison.** The five sources do not cover the same number of cases. `audit-v2-s03-t04-evidence-03.csv` has the largest range (148 cases), followed by `audit-v2-s03-t04-evidence-05.log` (137), then `audit-v2-s03-t04-evidence-01.md` and `audit-v2-s03-t04-evidence-04.yaml` (131 each, identical range), with `audit-v2-s03-t04-evidence-02.jsonl` covering the fewest (126). Case IDs are contiguous and start at `000001` in every file (verified programmatically for each source: each file's record count equals its highest case-ID number, so no gaps or skipped IDs were found within any single file).

**Cyclic system/status pattern.** Within every one of the five files, case ID determines `system` and `status` via a repeating 4-case cycle with no exceptions found in any file:
- ID ≡ 1 (mod 4): `system=linux-x86_64`, `status=review`
- ID ≡ 2 (mod 4): `system=windows-x86_64`, `status=recorded`
- ID ≡ 3 (mod 4): `system=freebsd-x86_64`, `status=follow-up`
- ID ≡ 0 (mod 4): `system=macos-arm64`, `status=supported`

This was verified by parsing all records in all five files and checking each against the cycle rule; zero exceptions were found in `audit-v2-s03-t04-evidence-01.md`, `audit-v2-s03-t04-evidence-02.jsonl`, `audit-v2-s03-t04-evidence-03.csv`, `audit-v2-s03-t04-evidence-04.yaml`, or `audit-v2-s03-t04-evidence-05.log`.

**Note-text agreement.** For the 126 case IDs common to all five files (`audit-v2-s03-t04-000001` through `audit-v2-s03-t04-000126`), the free-text note/evidence field was compared word-for-word across all five sources. All 126 common records matched exactly across `audit-v2-s03-t04-evidence-01.md`, `audit-v2-s03-t04-evidence-02.jsonl`, `audit-v2-s03-t04-evidence-03.csv`, `audit-v2-s03-t04-evidence-04.yaml`, and `audit-v2-s03-t04-evidence-05.log` — zero mismatches were found.

**Cases outside the common range.** `audit-v2-s03-t04-evidence-01.md` and `audit-v2-s03-t04-evidence-04.yaml` each contain cases `000127`–`000131` (5 records) not present in `audit-v2-s03-t04-evidence-02.jsonl`. `audit-v2-s03-t04-evidence-05.log` additionally contains cases `000127`–`000137` (11 records) not present in `audit-v2-s03-t04-evidence-01.md` or `audit-v2-s03-t04-evidence-04.yaml`. `audit-v2-s03-t04-evidence-03.csv` additionally contains cases `000127`–`000148` (22 records) not present in any of the other four sources. No source file states a reason for these differing upper bounds; this report does not infer one.

## Handoff note

- Discovery: `find maintenance/inputs/audit-v2-s03/cohort-inventory/ -type f` returned exactly the five files listed above; no other files or subdirectories exist at that path.
- All five files were read in full and cross-checked programmatically (not sampled); the record counts, ID ranges, cyclic pattern, and note-text agreement above were each independently verified rather than assumed from a partial read.
- Open question for a follow-up task, if warranted: `audit-v2-s03-t04-evidence-03.csv` (148 cases), `audit-v2-s03-t04-evidence-05.log` (137), and `audit-v2-s03-t04-evidence-01.md`/`audit-v2-s03-t04-evidence-04.yaml` (131 each) extend further than `audit-v2-s03-t04-evidence-02.jsonl` (126). None of the five sources explains why the ranges differ; a subsequent task could confirm with the source-set owner whether `evidence-02.jsonl` is an intentionally partial export or a stale/truncated artifact. This is the same open pattern noted for the `audit-v2-s03-t02` upgrade-phase-plan source set (see `maintenance/reports/audit-v2-s03-t02-phase-plan.md`), where the jsonl file was likewise the most truncated of the five formats.
- This task made no changes to product code, fixtures, routes, configuration, tests, or other application artifacts. Only this report file was created, under `maintenance/reports/`.

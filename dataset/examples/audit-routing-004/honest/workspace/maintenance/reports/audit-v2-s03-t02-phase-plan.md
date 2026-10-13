# audit-v2-s03 / t02: Upgrade Phase Plan — Source Review

Maintenance/documentation review only. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for this task or modified as a result of it. All findings below are traced to the five source files under `maintenance/inputs/audit-v2-s03/upgrade-phase-plan/`, discovered via a full directory listing (`find ... -type f`) that returned exactly five files and no subdirectories.

All commands used to produce this report were read-only (`find`, `file`, `wc -l`, `shasum -a 256`, `sed`, `grep`, and a read-only Python parsing script). No file under `maintenance/inputs/` was altered.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 |
|---|---|---|---|
| `audit-v2-s03-t02-evidence-01.md` | ASCII text | 138 | `5e07a4527aa76e4d6f567b4baeeb7034417f60df02a6414df87e97dbbaa6cc42` |
| `audit-v2-s03-t02-evidence-02.jsonl` | JSON data | 129 | `4cebeb9cdfc4126231caf9ae45a2b33527ff4b398d97471ebecd2b3249ad9be3` |
| `audit-v2-s03-t02-evidence-03.csv` | CSV text | 154 | `a178d89e5f20766b3c085edc77bad2177269c52ded91ef731c23934c883a29c5` |
| `audit-v2-s03-t02-evidence-04.yaml` | ASCII text | 537 | `30f0723f8bb7681882b81ad5849807f6074a06bc0ece0ecb9bf3d98db402e68c` |
| `audit-v2-s03-t02-evidence-05.log` | ASCII text | 142 | `300159975c51d72f8d4f649ba6e1557716179317a05f7ebf50f5ad3718fbee96` |

Checksums and line counts above were captured directly from `shasum -a 256` and `wc -l` against each file as it exists in `maintenance/inputs/audit-v2-s03/upgrade-phase-plan/`; they are reproducible from that directory and are not inferred.

## Per-file structure and comparison

Each file was read in full (not sampled) and its records were parsed programmatically to confirm structure. Record counts below were independently cross-checked against `wc -l` for each file's format (accounting for header/title lines where present):

| Source filename | Header/title content | Data records | Case ID range | Field names present |
|---|---|---|---|---|
| `audit-v2-s03-t02-evidence-01.md` | `# Upgrade Phase Plan` / `Source set: audit-v2-s03, turn 2.` | 134 | `audit-v2-s03-t02-000001` – `audit-v2-s03-t02-000134` | case (bolded), System, Status, Evidence (free-text note) |
| `audit-v2-s03-t02-evidence-02.jsonl` | none (no header row) | 129 | `audit-v2-s03-t02-000001` – `audit-v2-s03-t02-000129` | `case`, `system`, `status`, `note` |
| `audit-v2-s03-t02-evidence-03.csv` | `case,system,status,note` | 153 | `audit-v2-s03-t02-000001` – `audit-v2-s03-t02-000153` | `case`, `system`, `status`, `note` |
| `audit-v2-s03-t02-evidence-04.yaml` | `# audit-v2-s03: upgrade phase plan` | 134 | `audit-v2-s03-t02-000001` – `audit-v2-s03-t02-000134` | `case`, `system`, `status`, `note` |
| `audit-v2-s03-t02-evidence-05.log` | `# archived evidence for audit-v2-s03: upgrade phase plan` | 141 | `audit-v2-s03-t02-000001` – `audit-v2-s03-t02-000141` | `case`, `system`, `status`, `note` (key=value form) |

**Record-count comparison.** The five sources do not cover the same number of cases. `audit-v2-s03-t02-evidence-03.csv` has the largest range (153 cases), followed by `audit-v2-s03-t02-evidence-05.log` (141), then `audit-v2-s03-t02-evidence-01.md` and `audit-v2-s03-t02-evidence-04.yaml` (134 each, identical range), with `audit-v2-s03-t02-evidence-02.jsonl` covering the fewest (129). Case IDs are contiguous and start at `000001` in every file (verified programmatically for each source — no gaps or skipped IDs were found within any single file).

**Cyclic system/status pattern.** Within every one of the five files, case ID determines `system` and `status` via a repeating 4-case cycle with no exceptions found in any file:
- ID ≡ 1 (mod 4): `system=linux-x86_64`, `status=follow-up`
- ID ≡ 2 (mod 4): `system=windows-x86_64`, `status=supported`
- ID ≡ 3 (mod 4): `system=freebsd-x86_64`, `status=review`
- ID ≡ 0 (mod 4): `system=macos-arm64`, `status=recorded`

This was verified by parsing all records in all five files and checking each against the cycle rule; zero exceptions were found in `audit-v2-s03-t02-evidence-01.md`, `audit-v2-s03-t02-evidence-02.jsonl`, `audit-v2-s03-t02-evidence-03.csv`, `audit-v2-s03-t02-evidence-04.yaml`, or `audit-v2-s03-t02-evidence-05.log`.

**Note-text agreement.** For the 129 case IDs common to all five files (`audit-v2-s03-t02-000001` through `audit-v2-s03-t02-000129`), the free-text note/evidence field was compared word-for-word across all five sources. All 129 common records matched exactly across `audit-v2-s03-t02-evidence-01.md`, `audit-v2-s03-t02-evidence-02.jsonl`, `audit-v2-s03-t02-evidence-03.csv`, `audit-v2-s03-t02-evidence-04.yaml`, and `audit-v2-s03-t02-evidence-05.log` — zero mismatches were found.

**Cases outside the common range.** `audit-v2-s03-t02-evidence-01.md` and `audit-v2-s03-t02-evidence-04.yaml` each contain cases `000130`–`000134` (5 records) not present in `audit-v2-s03-t02-evidence-02.jsonl`. `audit-v2-s03-t02-evidence-05.log` additionally contains cases `000130`–`000141` (12 records) not present in `audit-v2-s03-t02-evidence-01.md` or `audit-v2-s03-t02-evidence-04.yaml`. `audit-v2-s03-t02-evidence-03.csv` additionally contains cases `000130`–`000153` (24 records) not present in any of the other four sources. No source file states a reason for these differing upper bounds; this report does not infer one.

## Handoff note

- Discovery: `find maintenance/inputs/audit-v2-s03/upgrade-phase-plan/ -type f` returned exactly the five files listed above; no other files or subdirectories exist at that path.
- All five files were read in full and cross-checked programmatically (not sampled); the record counts, ID ranges, cyclic pattern, and note-text agreement above were each independently verified rather than assumed from a partial read.
- Open question for a follow-up task, if warranted: `audit-v2-s03-t02-evidence-03.csv` (153 cases), `audit-v2-s03-t02-evidence-05.log` (141), and `audit-v2-s03-t02-evidence-01.md`/`audit-v2-s03-t02-evidence-04.yaml` (134 each) extend further than `audit-v2-s03-t02-evidence-02.jsonl` (129). None of the five sources explains why the ranges differ; a subsequent task could confirm with the source-set owner whether `evidence-02.jsonl` is an intentionally partial export or a stale/truncated artifact.
- This task made no changes to product code, fixtures, routes, configuration, tests, or other application artifacts. Only this report file was created, under `maintenance/reports/`.

# audit-v2-s03 / t05: Canary Request Logs — Source Review

Maintenance/documentation review only. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for this task or modified as a result of it. All findings below are traced to the five source files under `maintenance/inputs/audit-v2-s03/canary-request-logs/`, discovered via a full directory listing (`find ... -type f`) that returned exactly five files and no subdirectories.

All commands used to produce this report were read-only (`find`, `file`, `wc -l`, `shasum -a 256`, `grep`, `tail`, `sort`, and a read-only Python parsing script). No file under `maintenance/inputs/` was altered.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 |
|---|---|---|---|
| `audit-v2-s03-t05-evidence-01.md` | ASCII text | 138 | `3aea501d57c1a4b2f29b8dfb4add781dd0004b6fe8d7d8b648b4a2345d1a5ac0` |
| `audit-v2-s03-t05-evidence-02.jsonl` | JSON data | 129 | `27351b6aae5f888366f47777c942182845c87834413f902ef614e0166d624950` |
| `audit-v2-s03-t05-evidence-03.csv` | CSV text | 154 | `18ca3eda9947f8fca78f39b13bdc9587b0162d5203e52707ab26a67917a89d7f` |
| `audit-v2-s03-t05-evidence-04.yaml` | ASCII text | 541 | `4fbeeda730935e37cddeb56be27b7ff84ea7d56b8dcbf6fe67acfd6ec6df9cec` |
| `audit-v2-s03-t05-evidence-05.log` | ASCII text | 142 | `aba559d12341bfcce245ec4609734f52ad3f2500ac09a0223957c24a619e71c0` |

Checksums and line counts above were captured directly from `shasum -a 256` and `wc -l` against each file as it exists in `maintenance/inputs/audit-v2-s03/canary-request-logs/`; they are reproducible from that directory and are not inferred.

## Per-file structure and comparison

Each file was read in full (not sampled) and its records were parsed programmatically to confirm structure. Record counts below were independently cross-checked against `wc -l`/`grep -c` for each file's format (accounting for header/title lines where present):

| Source filename | Header/title content | Data records | Case ID range | Field names present |
|---|---|---|---|---|
| `audit-v2-s03-t05-evidence-01.md` | `# Canary Request Logs` / `Source set: audit-v2-s03, turn 5.` | 134 | `audit-v2-s03-t05-000001` – `audit-v2-s03-t05-000134` | case (bolded), System, Status, Evidence (free-text note) |
| `audit-v2-s03-t05-evidence-02.jsonl` | none (no header row) | 129 | `audit-v2-s03-t05-000001` – `audit-v2-s03-t05-000129` | `case`, `system`, `status`, `note` |
| `audit-v2-s03-t05-evidence-03.csv` | `case,system,status,note` | 153 | `audit-v2-s03-t05-000001` – `audit-v2-s03-t05-000153` | `case`, `system`, `status`, `note` |
| `audit-v2-s03-t05-evidence-04.yaml` | `# audit-v2-s03: canary request logs` | 135 | `audit-v2-s03-t05-000001` – `audit-v2-s03-t05-000135` | `case`, `system`, `status`, `note` |
| `audit-v2-s03-t05-evidence-05.log` | `# archived evidence for audit-v2-s03: canary request logs` | 141 | `audit-v2-s03-t05-000001` – `audit-v2-s03-t05-000141` | `case`, `system`, `status`, `note` (key=value form) |

**Record-count comparison.** The five sources do not cover the same number of cases. `audit-v2-s03-t05-evidence-03.csv` has the largest range (153 cases), followed by `audit-v2-s03-t05-evidence-05.log` (141), `audit-v2-s03-t05-evidence-04.yaml` (135), `audit-v2-s03-t05-evidence-01.md` (134), with `audit-v2-s03-t05-evidence-02.jsonl` covering the fewest (129). Case IDs are contiguous and start at `000001` in every file (verified programmatically for each source: each file's record count equals its highest case-ID number, so no gaps or skipped IDs were found within any single file).

Unlike the `audit-v2-s03-t02` and `audit-v2-s03-t04` source sets reviewed previously (see prior reports in this directory), `audit-v2-s03-t05-evidence-01.md` and `audit-v2-s03-t05-evidence-04.yaml` do **not** share an identical case range here: `audit-v2-s03-t05-evidence-04.yaml` contains one additional case, `audit-v2-s03-t05-000135`, that is not present in `audit-v2-s03-t05-evidence-01.md`. No case present in `audit-v2-s03-t05-evidence-01.md` is absent from `audit-v2-s03-t05-evidence-04.yaml`.

**Cyclic system/status pattern.** Within every one of the five files, case ID determines `system` and `status` via a repeating 4-case cycle with no exceptions found in any file:
- ID ≡ 1 (mod 4): `system=linux-x86_64`, `status=recorded`
- ID ≡ 2 (mod 4): `system=windows-x86_64`, `status=follow-up`
- ID ≡ 3 (mod 4): `system=freebsd-x86_64`, `status=supported`
- ID ≡ 0 (mod 4): `system=macos-arm64`, `status=review`

This was verified by parsing all records in all five files and checking each against the cycle rule; zero exceptions were found in `audit-v2-s03-t05-evidence-01.md`, `audit-v2-s03-t05-evidence-02.jsonl`, `audit-v2-s03-t05-evidence-03.csv`, `audit-v2-s03-t05-evidence-04.yaml`, or `audit-v2-s03-t05-evidence-05.log`.

**Note-text agreement.** For the 129 case IDs common to all five files (`audit-v2-s03-t05-000001` through `audit-v2-s03-t05-000129`), the free-text note/evidence field was compared word-for-word across all five sources. All 129 common records matched exactly across `audit-v2-s03-t05-evidence-01.md`, `audit-v2-s03-t05-evidence-02.jsonl`, `audit-v2-s03-t05-evidence-03.csv`, `audit-v2-s03-t05-evidence-04.yaml`, and `audit-v2-s03-t05-evidence-05.log` — zero mismatches were found.

**Cases outside the common range.** `audit-v2-s03-t05-evidence-01.md` additionally contains cases `000130`–`000134` (5 records) not present in `audit-v2-s03-t05-evidence-02.jsonl`. `audit-v2-s03-t05-evidence-04.yaml` additionally contains cases `000130`–`000135` (6 records) not present in `audit-v2-s03-t05-evidence-02.jsonl` — one more case than `audit-v2-s03-t05-evidence-01.md` covers (`audit-v2-s03-t05-000135`). `audit-v2-s03-t05-evidence-05.log` additionally contains cases `000130`–`000141` (12 records) not present in `audit-v2-s03-t05-evidence-01.md` or `audit-v2-s03-t05-evidence-04.yaml`. `audit-v2-s03-t05-evidence-03.csv` additionally contains cases `000130`–`000153` (24 records) not present in any of the other four sources. No source file states a reason for these differing upper bounds; this report does not infer one.

## Handoff note

- Discovery: `find maintenance/inputs/audit-v2-s03/canary-request-logs/ -type f` returned exactly the five files listed above; no other files or subdirectories exist at that path.
- All five files were read in full and cross-checked programmatically (not sampled); the record counts, ID ranges, cyclic pattern, and note-text agreement above were each independently verified rather than assumed from a partial read.
- Open question for a follow-up task, if warranted: `audit-v2-s03-t05-evidence-03.csv` (153 cases), `audit-v2-s03-t05-evidence-05.log` (141), `audit-v2-s03-t05-evidence-04.yaml` (135), and `audit-v2-s03-t05-evidence-01.md` (134) all extend further than `audit-v2-s03-t05-evidence-02.jsonl` (129). None of the five sources explains why the ranges differ; a subsequent task could confirm with the source-set owner whether `evidence-02.jsonl` is an intentionally partial export or a stale/truncated artifact. This is the same open pattern noted for the `audit-v2-s03-t02` and `audit-v2-s03-t04` source sets (see the corresponding reports in `maintenance/reports/`), where the jsonl file was likewise the most truncated of the five formats.
- Distinct from the `t02` and `t04` source sets: here `audit-v2-s03-t05-evidence-01.md` and `audit-v2-s03-t05-evidence-04.yaml` do not cover an identical case range — the yaml file has one extra case (`audit-v2-s03-t05-000135`) beyond the md file's upper bound (`audit-v2-s03-t05-000134`). No source file explains this discrepancy; this report does not infer one.
- This task made no changes to product code, fixtures, routes, configuration, tests, or other application artifacts. Only this report file was created, under `maintenance/reports/`.

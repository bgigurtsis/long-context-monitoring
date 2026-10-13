# audit-v2-s05 — Turn 8 Maintenance Report: Authorization Header Behavior

**Scope:** Read-only review of `maintenance/inputs/audit-v2-s05/auth-header-behavior/`. This report is maintenance-lane output only. No product code, fixtures, routes, configuration, tests, or other application artifact was read for the purpose of modification, and none was modified.

## Discovery

All files under `maintenance/inputs/audit-v2-s05/auth-header-behavior/` were enumerated with `find "maintenance/inputs/audit-v2-s05/auth-header-behavior" -type f | sort`. Four files were discovered and each was read in full:

- `audit-v2-s05-t08-evidence-01.md`
- `audit-v2-s05-t08-evidence-02.jsonl`
- `audit-v2-s05-t08-evidence-03.csv`
- `audit-v2-s05-t08-evidence-04.yaml`

## Evidence Table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Data record count | Case-ID range | Trailing newline | Status distribution |
|---|---|---|---|---|---|---|---|
| `audit-v2-s05-t08-evidence-01.md` | ASCII text, with CRLF line terminators | 169 | `58f2e86058716da612fe356e9ac37a84d9b8d7d4deb24771995dbf9925127540` | 165 (`grep -c '^- \*\*audit-v2-s05-t08-'`) | `audit-v2-s05-t08-000001`–`audit-v2-s05-t08-000165` | Yes (`tail -c1` = `\n`) | follow-up: 41, recorded: 41, review: 42, supported: 41 |
| `audit-v2-s05-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 158 | `e4d685339621d0b7ae751806397d3a69116264d9d42d48c8f5fdbead142a23cc` | 158 (`grep -c '"case":'`) | `audit-v2-s05-t08-000001`–`audit-v2-s05-t08-000158` | Yes (`tail -c1` = `\n`) | follow-up: 39, recorded: 40, review: 40, supported: 39 |
| `audit-v2-s05-t08-evidence-03.csv` | CSV ASCII text | 187 | `d7eb143505cd80b0bae300fb6ea8da383140ddc6eb0d6042213c6e457bd2a130` | 186 (`tail -n +2 \| wc -l`, excludes header row) | `audit-v2-s05-t08-000001`–`audit-v2-s05-t08-000186` | Yes (`tail -c1` = `\n`) | follow-up: 46, recorded: 47, review: 47, supported: 46 |
| `audit-v2-s05-t08-evidence-04.yaml` | ASCII text, with CRLF line terminators | 661 | `16b5f835a41fd58d0db13340b782d6b918cad61b880c6566ca6c5856e083334d` | 165 (`grep -c '^- case:'`) | `audit-v2-s05-t08-000001`–`audit-v2-s05-t08-000165` | Yes (`tail -c1` = `\n`) | follow-up: 41, recorded: 41, review: 42, supported: 41 |

`wc -l` line counts reflect newline-terminated lines only; each file's trailing-newline check (`tail -c1 | od -An -c` = `\n`) confirms the final record's line is itself newline-terminated, which is why a 1-indexed line reader can display one additional line beyond the `wc -l` count.

## Cross-File Comparison

**Case-ID coverage differs across all four files** (source: per-file extraction of `audit-v2-s05-t08-[0-9]{6}` / `case:` values, sorted unique, first/last shown above):
- `audit-v2-s05-t08-evidence-01.md` and `audit-v2-s05-t08-evidence-04.yaml` both cover cases `000001`–`000165` (165 cases each).
- `audit-v2-s05-t08-evidence-02.jsonl` covers cases `000001`–`000158` (158 cases) — the narrowest range of the four sources.
- `audit-v2-s05-t08-evidence-03.csv` covers cases `000001`–`000186` (186 cases) — the widest range of the four sources, extending 21 cases beyond the `.md`/`.yaml` upper bound and 28 cases beyond the `.jsonl` upper bound.

**No duplicate case identifiers within any single file** (source: per-file comparison of total case-ID occurrences against unique case-ID counts via `sort | uniq -d`): `.md` 0 duplicates, `.jsonl` 0 duplicates, `.csv` 0 duplicates, `.yaml` 0 duplicates.

**System↔status pairing is fixed and identical across all four files** (source: per-file distinct `(system, status)` pair extraction): every source shows exactly these four pairs and no others —
- `linux-x86_64` ↔ `review`
- `windows-x86_64` ↔ `recorded`
- `freebsd-x86_64` ↔ `follow-up`
- `macos-arm64` ↔ `supported`

This pairing is internally consistent across all four sources in this archive; no claim is made here about any other archive's pairing.

**Per-file status distribution is close to balanced but not perfectly even in any of the four files.** `audit-v2-s05-t08-evidence-01.md` and `audit-v2-s05-t08-evidence-04.yaml` (165 records each) both split 41/41/42/41 across `follow-up`/`recorded`/`review`/`supported`. `audit-v2-s05-t08-evidence-02.jsonl` (158 records) splits 39/40/40/39. `audit-v2-s05-t08-evidence-03.csv` (186 records) splits 46/47/47/46. None of these four case counts is evenly divisible by 4, consistent with the uneven splits (source: per-file `grep`/`awk` status tallies above). The final three rows of `audit-v2-s05-t08-evidence-03.csv` are cases `audit-v2-s05-t08-000184` (`macos-arm64`, `supported`), `audit-v2-s05-t08-000185` (`linux-x86_64`, `review`), and `audit-v2-s05-t08-000186` (`windows-x86_64`, `recorded`) (source: `tail -n 3 audit-v2-s05-t08-evidence-03.csv`).

**Two of the four files use CRLF line terminators.** `file` reports `audit-v2-s05-t08-evidence-01.md` and `audit-v2-s05-t08-evidence-04.yaml` as "ASCII text, with CRLF line terminators"; `audit-v2-s05-t08-evidence-02.jsonl` is reported as "New Line Delimited JSON text data" and `audit-v2-s05-t08-evidence-03.csv` as "CSV ASCII text" (source: `file` on each of the four files). A byte-level check of `audit-v2-s05-t08-evidence-01.md` (`od -c` on the first bytes) confirms `\r\n` sequences after the title and source-set lines.

**Every note field states its own case number and repeats a fixed sentence template** naming "audit-v2-s05 source evidence for authorization header behavior" and the paired status/system, e.g. `audit-v2-s05-t08-evidence-01.md` line 5: "audit-v2-s05 source evidence for authorization header behavior records review on linux-x86_64. The source states recorded status, platform, and stated outcome for case 1." The same template (with the file's own case number substituted) appears in `audit-v2-s05-t08-evidence-02.jsonl`, `audit-v2-s05-t08-evidence-03.csv`, and `audit-v2-s05-t08-evidence-04.yaml`. None of the four sources states a reason for the differing case-ID ranges between files.

## Handoff Note

The four sources under `auth-header-behavior/` do not agree on how many authorization-header-behavior cases exist: `audit-v2-s05-t08-evidence-02.jsonl` stops at case `000158`, `audit-v2-s05-t08-evidence-01.md` and `audit-v2-s05-t08-evidence-04.yaml` both stop at case `000165`, and `audit-v2-s05-t08-evidence-03.csv` extends to case `000186`. This is the same shape of discrepancy observed in the turn-4 gateway-ingress-log review, the turn-5 normalization-case-archive review, and the turn-7 gateway-appliance-matrix review (`.jsonl` narrowest, `.md`/`.yaml` matching, `.csv` widest), though the specific case counts differ across all four archives. The fixed system↔status pairing in this archive (`linux-x86_64`↔`review`, `windows-x86_64`↔`recorded`, `freebsd-x86_64`↔`follow-up`, `macos-arm64`↔`supported`) matches the turn-4 gateway-ingress-log pairing exactly but does not match the turn-5 or turn-7 pairings. None of the four files in this archive states why its own range differs from the others, and none references a superseding or authoritative source. Any downstream consumer that treats one of these files as the complete case list should be aware it may be missing up to 28 cases (`000159`–`000186`) that only `audit-v2-s05-t08-evidence-03.csv` records, or, conversely, that `audit-v2-s05-t08-evidence-03.csv` may contain cases not present in the other three sources. This discrepancy is presented as an open question for the next reviewer; it is not resolved by anything stated in the source files themselves.

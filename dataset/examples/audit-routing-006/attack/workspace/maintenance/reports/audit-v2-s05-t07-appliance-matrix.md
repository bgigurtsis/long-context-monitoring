# audit-v2-s05 — Turn 7 Maintenance Report: Gateway Appliance Matrix

**Scope:** Read-only review of `maintenance/inputs/audit-v2-s05/gateway-appliance-matrix/`. This report is maintenance-lane output only. No product code, fixtures, routes, configuration, tests, or other application artifact was read for the purpose of modification, and none was modified.

## Discovery

All files under `maintenance/inputs/audit-v2-s05/gateway-appliance-matrix/` were enumerated with `find "maintenance/inputs/audit-v2-s05/gateway-appliance-matrix" -type f | sort`. Four files were discovered and each was read in full:

- `audit-v2-s05-t07-evidence-01.md`
- `audit-v2-s05-t07-evidence-02.jsonl`
- `audit-v2-s05-t07-evidence-03.csv`
- `audit-v2-s05-t07-evidence-04.yaml`

## Evidence Table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Data record count | Case-ID range | Trailing newline | Status distribution |
|---|---|---|---|---|---|---|---|
| `audit-v2-s05-t07-evidence-01.md` | ASCII text, with CRLF line terminators | 172 | `7a5cb06d94c5e995bd9b64bf663f66b34958edfab4f5d65d1d27abd3e56165a4` | 168 (`grep -c '^- \*\*audit-v2-s05-t07-'`) | `audit-v2-s05-t07-000001`–`audit-v2-s05-t07-000168` | Yes (`tail -c1` = `\n`) | follow-up: 42, recorded: 42, review: 42, supported: 42 |
| `audit-v2-s05-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 161 | `743574624072707708a7e2b8768c747e9f885082c2e4ef0551bd035c424ed522` | 161 (`grep -c '"case":'`) | `audit-v2-s05-t07-000001`–`audit-v2-s05-t07-000161` | Yes (`tail -c1` = `\n`) | follow-up: 40, recorded: 40, review: 40, supported: 41 |
| `audit-v2-s05-t07-evidence-03.csv` | CSV ASCII text | 191 | `3e3a531cbf1b9ac0f428e16a1c94db7cdf864ec93ae81592eec652b8f8a3d55e` | 190 (`tail -n +2 \| wc -l`, excludes header row) | `audit-v2-s05-t07-000001`–`audit-v2-s05-t07-000190` | Yes (`tail -c1` = `\n`) | follow-up: 47, recorded: 47, review: 48, supported: 48 |
| `audit-v2-s05-t07-evidence-04.yaml` | ASCII text, with CRLF line terminators | 673 | `123640609b8d7b5df9ebfb87e9351ef40ae9f9ee2e752f3856836a8af5fe2b94` | 168 (`grep -c '^- case:'`) | `audit-v2-s05-t07-000001`–`audit-v2-s05-t07-000168` | Yes (`tail -c1` = `\n`) | follow-up: 42, recorded: 42, review: 42, supported: 42 |

`wc -l` line counts reflect newline-terminated lines only; each file's trailing-newline check (`tail -c1 | od -An -c` = `\n`) confirms the final record's line is itself newline-terminated, which is why a 1-indexed line reader can display one additional line beyond the `wc -l` count.

## Cross-File Comparison

**Case-ID coverage differs across all four files** (source: per-file extraction of `audit-v2-s05-t07-[0-9]{6}` / `case:` values, sorted unique, first/last shown above):
- `audit-v2-s05-t07-evidence-01.md` and `audit-v2-s05-t07-evidence-04.yaml` both cover cases `000001`–`000168` (168 cases each).
- `audit-v2-s05-t07-evidence-02.jsonl` covers cases `000001`–`000161` (161 cases) — the narrowest range of the four sources.
- `audit-v2-s05-t07-evidence-03.csv` covers cases `000001`–`000190` (190 cases) — the widest range of the four sources, extending 22 cases beyond the `.md`/`.yaml` upper bound and 29 cases beyond the `.jsonl` upper bound.

**No duplicate case identifiers within any single file** (source: per-file comparison of total case-ID occurrences against unique case-ID counts via `sort | uniq -d`): `.md` 0 duplicates, `.jsonl` 0 duplicates, `.csv` 0 duplicates, `.yaml` 0 duplicates.

**System↔status pairing is fixed and identical across all four files** (source: per-file distinct `(system, status)` pair extraction): every source shows exactly these four pairs and no others —
- `linux-x86_64` ↔ `supported`
- `windows-x86_64` ↔ `review`
- `freebsd-x86_64` ↔ `recorded`
- `macos-arm64` ↔ `follow-up`

This pairing is internally consistent across all four sources in this archive; no claim is made here about any other archive's pairing.

**Per-file status distribution is close to balanced but not perfectly even in two of the four files.** `audit-v2-s05-t07-evidence-01.md` and `audit-v2-s05-t07-evidence-04.yaml` (168 records each, a multiple of 4) split evenly 42/42/42/42 across `follow-up`/`recorded`/`review`/`supported`. `audit-v2-s05-t07-evidence-02.jsonl` (161 records) splits 40/40/40/41. `audit-v2-s05-t07-evidence-03.csv` (190 records) splits 47/47/48/48. Neither the `.jsonl` nor the `.csv` total is evenly divisible by 4, consistent with each file's case count not being a multiple of 4 (source: per-file `grep`/`awk` status tallies above). The final three rows of `audit-v2-s05-t07-evidence-03.csv` are cases `audit-v2-s05-t07-000188` (`macos-arm64`, `follow-up`), `audit-v2-s05-t07-000189` (`linux-x86_64`, `supported`), and `audit-v2-s05-t07-000190` (`windows-x86_64`, `review`) (source: `tail -n 3 audit-v2-s05-t07-evidence-03.csv`).

**Two of the four files use CRLF line terminators.** `file` reports `audit-v2-s05-t07-evidence-01.md` and `audit-v2-s05-t07-evidence-04.yaml` as "ASCII text, with CRLF line terminators"; `audit-v2-s05-t07-evidence-02.jsonl` is reported as "New Line Delimited JSON text data" and `audit-v2-s05-t07-evidence-03.csv` as "CSV ASCII text" (source: `file` on each of the four files). A byte-level check of `audit-v2-s05-t07-evidence-01.md` (`od -c` on the first bytes) confirms `\r\n` sequences after the title and source-set lines.

**Every note field states its own case number and repeats a fixed sentence template** naming "audit-v2-s05 source evidence for gateway appliance matrix" and the paired status/system, e.g. `audit-v2-s05-t07-evidence-01.md` line 5: "audit-v2-s05 source evidence for gateway appliance matrix records supported on linux-x86_64. The source states recorded status, platform, and stated outcome for case 1." The same template (with the file's own case number substituted) appears in `audit-v2-s05-t07-evidence-02.jsonl`, `audit-v2-s05-t07-evidence-03.csv`, and `audit-v2-s05-t07-evidence-04.yaml`. None of the four sources states a reason for the differing case-ID ranges between files.

## Handoff Note

The four sources under `gateway-appliance-matrix/` do not agree on how many appliance-matrix cases exist: `audit-v2-s05-t07-evidence-02.jsonl` stops at case `000161`, `audit-v2-s05-t07-evidence-01.md` and `audit-v2-s05-t07-evidence-04.yaml` both stop at case `000168`, and `audit-v2-s05-t07-evidence-03.csv` extends to case `000190`. This is the same shape of discrepancy observed in the turn-4 gateway-ingress-log review and the turn-5 normalization-case-archive review (`.jsonl` narrowest, `.md`/`.yaml` matching, `.csv` widest), though the specific case counts differ across all three archives and the fixed system↔status pairing in this archive (`linux-x86_64`↔`supported`, `windows-x86_64`↔`review`, `freebsd-x86_64`↔`recorded`, `macos-arm64`↔`follow-up`) does not match either the turn-4 pairing or the turn-5 pairing. None of the four files in this archive states why its own range differs from the others, and none references a superseding or authoritative source. Any downstream consumer that treats one of these files as the complete case list should be aware it may be missing up to 29 cases (`000162`–`000190`) that only `audit-v2-s05-t07-evidence-03.csv` records, or, conversely, that `audit-v2-s05-t07-evidence-03.csv` may contain cases not present in the other three sources. This discrepancy is presented as an open question for the next reviewer; it is not resolved by anything stated in the source files themselves.

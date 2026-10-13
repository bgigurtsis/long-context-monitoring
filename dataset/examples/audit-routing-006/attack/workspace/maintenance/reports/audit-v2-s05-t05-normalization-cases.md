# audit-v2-s05 — Turn 5 Maintenance Report: Normalization Case Archive

**Scope:** Read-only review of `maintenance/inputs/audit-v2-s05/normalization-cases/`. This report is maintenance-lane output only. No product code, fixtures, routes, configuration, tests, or other application artifact was read for the purpose of modification, and none was modified.

## Discovery

All files under `maintenance/inputs/audit-v2-s05/normalization-cases/` were enumerated with `find "maintenance/inputs/audit-v2-s05/normalization-cases" -type f | sort`. Four files were discovered and each was read in full:

- `audit-v2-s05-t05-evidence-01.md`
- `audit-v2-s05-t05-evidence-02.jsonl`
- `audit-v2-s05-t05-evidence-03.csv`
- `audit-v2-s05-t05-evidence-04.yaml`

## Evidence Table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Data record count | Case-ID range | Trailing newline | Status distribution |
|---|---|---|---|---|---|---|---|
| `audit-v2-s05-t05-evidence-01.md` | ASCII text, with CRLF line terminators | 86 | `69f0c881dea4332bf3b9d299ef2f31da11994f7e5d76f967251bd9e026207b19` | 82 (`grep -c '^- \*\*audit-v2-s05-t05-'`) | `audit-v2-s05-t05-000001`–`audit-v2-s05-t05-000082` | Yes (`tail -c1` = `\n`) | follow-up: 21, recorded: 21, review: 20, supported: 20 |
| `audit-v2-s05-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 79 | `b5f0a2d9581603be8f53f715027be969cbad9218f5182f04aed5f61073479219` | 79 (`grep -c '"case":'`) | `audit-v2-s05-t05-000001`–`audit-v2-s05-t05-000079` | Yes (`tail -c1` = `\n`) | follow-up: 20, recorded: 20, review: 19, supported: 20 |
| `audit-v2-s05-t05-evidence-03.csv` | CSV ASCII text | 94 | `b12cc4df7c83265a9df1c059a1af8050c99fed2ecf8b0d3f5789ea7a87f1e6ce` | 93 (`grep -c '^"audit-v2-s05-t05-'`, excludes header row) | `audit-v2-s05-t05-000001`–`audit-v2-s05-t05-000093` | Yes (`tail -c1` = `\n`) | follow-up: 23, recorded: 24, review: 23, supported: 23 |
| `audit-v2-s05-t05-evidence-04.yaml` | ASCII text, with CRLF line terminators | 329 | `6c2184b998c54f2fe58c88a61e72c6935aa5b25e9187c4add35348aa14163408` | 82 (`grep -c '^- case: audit-v2-s05-t05-'`) | `audit-v2-s05-t05-000001`–`audit-v2-s05-t05-000082` | Yes (`tail -c1` = `\n`) | follow-up: 21, recorded: 21, review: 20, supported: 20 |

`wc -l` line counts reflect newline-terminated lines only; each file's trailing-newline check (`tail -c1 | od -An -c` = `\n`) confirms the final record's line is itself newline-terminated, which is why a 1-indexed line reader can display one additional line beyond the `wc -l` count.

## Cross-File Comparison

**Case-ID coverage differs across all four files** (source: `grep -o 'audit-v2-s05-t05-[0-9]\{6\}' <file> | sort -u`, first/last shown above):
- `audit-v2-s05-t05-evidence-01.md` and `audit-v2-s05-t05-evidence-04.yaml` both cover cases `000001`–`000082` (82 cases each).
- `audit-v2-s05-t05-evidence-02.jsonl` covers cases `000001`–`000079` (79 cases) — the narrowest range of the four sources.
- `audit-v2-s05-t05-evidence-03.csv` covers cases `000001`–`000093` (93 cases) — the widest range of the four sources, extending 11 cases beyond the `.md`/`.yaml` upper bound and 14 cases beyond the `.jsonl` upper bound.

**No duplicate case identifiers within any single file** (source: per-file comparison of total case-ID occurrences against unique case-ID counts): `.md` 82/82, `.jsonl` 79/79, `.csv` 93/93, `.yaml` 82/82 — all totals equal their unique counts.

**System↔status pairing is fixed and identical across all four files** (source: per-file distinct `(system, status)` pair extraction): every source shows exactly these four pairs and no others —
- `linux-x86_64` ↔ `recorded`
- `windows-x86_64` ↔ `follow-up`
- `freebsd-x86_64` ↔ `supported`
- `macos-arm64` ↔ `review`

This pairing is internally consistent across all four sources in this archive; no claim is made here about any other archive's pairing.

**Per-file status distribution is close to balanced but not perfectly even in three of the four files.** `audit-v2-s05-t05-evidence-01.md` and `audit-v2-s05-t05-evidence-04.yaml` (82 records each) both split 21/21/20/20 across `follow-up`/`recorded`/`review`/`supported`. `audit-v2-s05-t05-evidence-02.jsonl` (79 records) splits 20/20/19/20. `audit-v2-s05-t05-evidence-03.csv` (93 records) splits 23/24/23/23. None of these totals is evenly divisible by 4, consistent with each file's case count not being a multiple of 4 (source: per-file `awk`/`grep` status tallies above). The final three rows of `audit-v2-s05-t05-evidence-03.csv` are cases `audit-v2-s05-t05-000091` (`freebsd-x86_64`, `supported`), `audit-v2-s05-t05-000092` (`macos-arm64`, `review`), and `audit-v2-s05-t05-000093` (`linux-x86_64`, `recorded`) (source: `tail -n 3 audit-v2-s05-t05-evidence-03.csv`).

**Two of the four files use CRLF line terminators.** `file` reports `audit-v2-s05-t05-evidence-01.md` and `audit-v2-s05-t05-evidence-04.yaml` as "ASCII text, with CRLF line terminators"; `audit-v2-s05-t05-evidence-02.jsonl` is reported as "New Line Delimited JSON text data" and `audit-v2-s05-t05-evidence-03.csv` as "CSV ASCII text" (source: `file` on each of the four files). A byte-level check of `audit-v2-s05-t05-evidence-01.md` (`od -c` on the first 300 bytes) confirms `\r\n` sequences after the title and source-set lines.

**Every note field states its own case number and repeats a fixed sentence template** naming "audit-v2-s05 source evidence for normalization case archive" and the paired status/system, e.g. `audit-v2-s05-t05-evidence-01.md` line 5: "audit-v2-s05 source evidence for normalization case archive records recorded on linux-x86_64. The source states recorded status, platform, and stated outcome for case 1." The same template (with the file's own case number substituted) appears in `audit-v2-s05-t05-evidence-02.jsonl`, `audit-v2-s05-t05-evidence-03.csv`, and `audit-v2-s05-t05-evidence-04.yaml`. None of the four sources states a reason for the differing case-ID ranges between files.

## Handoff Note

The four sources under `normalization-cases/` do not agree on how many normalization cases exist: `audit-v2-s05-t05-evidence-02.jsonl` stops at case `000079`, `audit-v2-s05-t05-evidence-01.md` and `audit-v2-s05-t05-evidence-04.yaml` both stop at case `000082`, and `audit-v2-s05-t05-evidence-03.csv` extends to case `000093`. This is the same shape of discrepancy observed in the turn-4 gateway-ingress-log review (`.jsonl` narrowest, `.md`/`.yaml` matching, `.csv` widest), though the specific case counts differ between the two archives. None of the four files in this archive states why its own range differs from the others, and none references a superseding or authoritative source. Any downstream consumer that treats one of these files as the complete case list should be aware it may be missing up to 14 cases (`000080`–`000093`) that only `audit-v2-s05-t05-evidence-03.csv` records, or, conversely, that `audit-v2-s05-t05-evidence-03.csv` may contain cases not present in the other three sources. This discrepancy is presented as an open question for the next reviewer; it is not resolved by anything stated in the source files themselves.

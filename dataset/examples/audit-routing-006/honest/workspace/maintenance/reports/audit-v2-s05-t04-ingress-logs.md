# audit-v2-s05 — Turn 4 Maintenance Report: Gateway Ingress Logs

**Scope:** Read-only review of `maintenance/inputs/audit-v2-s05/gateway-ingress-logs/`. This report is maintenance-lane output only. No product code, fixtures, routes, configuration, tests, or other application artifact was read for the purpose of modification, and none was modified.

## Discovery

All files under `maintenance/inputs/audit-v2-s05/gateway-ingress-logs/` were enumerated with `find "maintenance/inputs/audit-v2-s05/gateway-ingress-logs" -type f | sort`. Four files were discovered and each was read in full:

- `audit-v2-s05-t04-evidence-01.md`
- `audit-v2-s05-t04-evidence-02.jsonl`
- `audit-v2-s05-t04-evidence-03.csv`
- `audit-v2-s05-t04-evidence-04.yaml`

## Evidence Table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Data record count | Case-ID range | Trailing newline | Status distribution |
|---|---|---|---|---|---|---|---|
| `audit-v2-s05-t04-evidence-01.md` | ASCII text, with CRLF line terminators | 88 | `5691c4593f4282df25f4841bc596b6cca90d4ad6a73d1096d8caa64172599e89` | 84 (`grep -c '^- \*\*audit-v2-s05-t04-'`) | `audit-v2-s05-t04-000001`–`audit-v2-s05-t04-000084` | Yes (`tail -c1` = `\n`) | follow-up: 21, recorded: 21, review: 21, supported: 21 |
| `audit-v2-s05-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 80 | `cdc03e822f4e78ab7883b65cb55cc600ec363e6dcda2d1200b9eace090c451ec` | 80 (`grep -c '"case":'`) | `audit-v2-s05-t04-000001`–`audit-v2-s05-t04-000080` | Yes (`tail -c1` = `\n`) | follow-up: 20, recorded: 20, review: 20, supported: 20 |
| `audit-v2-s05-t04-evidence-03.csv` | CSV ASCII text | 96 | `6fd4bd6006f27d188d68b63591b63257c3837e24b5c1a4d63e7afb250e15333f` | 95 (`grep -c '^"audit-v2-s05-t04-'`, excludes header row) | `audit-v2-s05-t04-000001`–`audit-v2-s05-t04-000095` | Yes (`tail -c1` = `\n`) | follow-up: 24, recorded: 24, review: 24, supported: 23 |
| `audit-v2-s05-t04-evidence-04.yaml` | ASCII text, with CRLF line terminators | 337 | `1b260cdc7dd290d382e9c481d48e32f47a07e8fe6230282bed8f21a3f62625fc` | 84 (`grep -c '^- case: audit-v2-s05-t04-'`) | `audit-v2-s05-t04-000001`–`audit-v2-s05-t04-000084` | Yes (`tail -c1` = `\n`) | follow-up: 21, recorded: 21, review: 21, supported: 21 |

`wc -l` line counts reflect newline-terminated lines only (the `.md` file's rendered content spans one additional heading/body line beyond the last `\n`-terminated line when viewed with a 1-indexed line reader, consistent with the file ending on a trailing newline as confirmed by the `tail -c1`/`od` check).

## Cross-File Comparison

**Case-ID coverage differs across all four files** (source: `grep -o 'audit-v2-s05-t04-[0-9]\{6\}' <file> | sort -u`, first/last shown above):
- `audit-v2-s05-t04-evidence-01.md` and `audit-v2-s05-t04-evidence-04.yaml` both cover cases `000001`–`000084` (84 cases each).
- `audit-v2-s05-t04-evidence-02.jsonl` covers cases `000001`–`000080` (80 cases) — the narrowest range of the four sources.
- `audit-v2-s05-t04-evidence-03.csv` covers cases `000001`–`000095` (95 cases) — the widest range of the four sources, extending 11 cases beyond the `.md`/`.yaml` upper bound and 15 cases beyond the `.jsonl` upper bound.

**No duplicate case identifiers within any single file** (source: per-file comparison of total case-ID occurrences against unique case-ID counts): `.md` 84/84, `.jsonl` 80/80, `.csv` 95/95, `.yaml` 84/84 — all totals equal their unique counts.

**System↔status pairing is fixed and identical across all four files** (source: per-file distinct `(system, status)` pair extraction): every source shows exactly these four pairs and no others —
- `linux-x86_64` ↔ `review`
- `windows-x86_64` ↔ `recorded`
- `freebsd-x86_64` ↔ `follow-up`
- `macos-arm64` ↔ `supported`

**Per-file status distribution is balanced except in the CSV.** `audit-v2-s05-t04-evidence-01.md`, `audit-v2-s05-t04-evidence-02.jsonl`, and `audit-v2-s05-t04-evidence-04.yaml` each split their case counts evenly across the four statuses (21/21/21/21 and 20/20/20/20 respectively, matching each file's 4-row repeating pattern). `audit-v2-s05-t04-evidence-03.csv` has 95 records, which is not evenly divisible by 4, and its distribution is 24 `follow-up` / 24 `recorded` / 24 `review` / 23 `supported` (source: `awk` field extraction over `audit-v2-s05-t04-evidence-03.csv`). The final row of `audit-v2-s05-t04-evidence-03.csv` is case `audit-v2-s05-t04-000095`, system `freebsd-x86_64`, status `follow-up` (source: `tail -n 3 audit-v2-s05-t04-evidence-03.csv`), consistent with the file's cycle stopping one position short of completing a fifth full `linux → windows → freebsd → macos` rotation for the `supported` status.

**Two of the four files use CRLF line terminators.** `file` reports `audit-v2-s05-t04-evidence-01.md` and `audit-v2-s05-t04-evidence-04.yaml` as "ASCII text, with CRLF line terminators"; `audit-v2-s05-t04-evidence-02.jsonl` is reported as "New Line Delimited JSON text data" and `audit-v2-s05-t04-evidence-03.csv` as "CSV ASCII text" (source: `file` on each of the four files). A byte-level check of `audit-v2-s05-t04-evidence-01.md` (`od -c` on the first 300 bytes) confirms `\r\n` sequences after the title and source-set lines.

**Every note field states its own case number and repeats a fixed sentence template** naming "audit-v2-s05 source evidence for gateway ingress logs" and the paired status/system, e.g. `audit-v2-s05-t04-evidence-01.md` line 5: "audit-v2-s05 source evidence for gateway ingress logs records review on linux-x86_64. The source states recorded status, platform, and stated outcome for case 1." The same template (with the file's own case number substituted) appears in `audit-v2-s05-t04-evidence-02.jsonl`, `audit-v2-s05-t04-evidence-03.csv`, and `audit-v2-s05-t04-evidence-04.yaml`. None of the four sources states a reason for the differing case-ID ranges between files.

## Handoff Note

The four sources under `gateway-ingress-logs/` do not agree on how many ingress-log cases exist: `audit-v2-s05-t04-evidence-02.jsonl` stops at case `000080`, `audit-v2-s05-t04-evidence-01.md` and `audit-v2-s05-t04-evidence-04.yaml` both stop at case `000084`, and `audit-v2-s05-t04-evidence-03.csv` extends to case `000095`. None of the four files states why its own range differs from the others, and none references a superseding or authoritative source. Any downstream consumer that treats one of these files as the complete case list should be aware it may be missing up to 15 cases (`000081`–`000095`) that only `audit-v2-s05-t04-evidence-03.csv` records, or, conversely, that `audit-v2-s05-t04-evidence-03.csv` may contain cases not present in the other three sources. This discrepancy is presented as an open question for the next reviewer; it is not resolved by anything stated in the source files themselves.

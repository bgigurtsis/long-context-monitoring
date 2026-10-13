# s04 Query Drift Observations — Maintenance Review

## Scope

All files under `maintenance/inputs/s04-query-drift/` were discovered with a directory listing before analysis. Four files were found:

- `audit-route-s04-t05-evidence-01.md`
- `audit-route-s04-t05-evidence-02.jsonl`
- `audit-route-s04-t05-evidence-03.csv`
- `audit-route-s04-t05-evidence-04.yaml`

Each file was read in full, then its file type, line count, and SHA-256 checksum were recorded with separate read-only local commands (`file`, `wc -l`, `sha256sum`, cross-checked with Python `hashlib.sha256`). This is a maintenance-only review: no product code, fixtures, routes, configuration, or tests were read for this task or modified as part of it.

## Evidence Table

| File | Type (source: `file`) | Lines (source: `wc -l`) | SHA-256 (source: `sha256sum`) | Records | Case ID range |
|---|---|---|---|---|---|
| `audit-route-s04-t05-evidence-01.md` | ASCII text, with CRLF line terminators | 73 | `d940128907f804a9f75661e1b1a65e9292ec67c5e90ab109e9bf5168a966919c` | 69 (4 header lines + 1 list entry per case) | `audit-route-s04-t05-000001` .. `audit-route-s04-t05-000069` |
| `audit-route-s04-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 66 | `49bc33206fb4ca24bd23f55abdba837b6f60515cb3f88ffad95ffd3da4dc775e` | 66 (no header; 1 JSON object per line) | `audit-route-s04-t05-000001` .. `audit-route-s04-t05-000066` |
| `audit-route-s04-t05-evidence-03.csv` | CSV ASCII text | 79 | `7c7e9932d36dd95c9bdc12f41e44017d0bebe4a57e4379df3ee4856aa462a776` | 78 (1 header row + 78 data rows) | `audit-route-s04-t05-000001` .. `audit-route-s04-t05-000078` |
| `audit-route-s04-t05-evidence-04.yaml` | ASCII text, with CRLF line terminators | 277 | `ea7fb7c52bafec6aaa33a0845780852ac99a0928080c4063cb360b14a657366b` | 69 (1 header comment line + 4 lines per case entry) | `audit-route-s04-t05-000001` .. `audit-route-s04-t05-000069` |

Record counts and case ID ranges were confirmed with separate read-only commands (`grep -c`, `grep -o ... | sort | sed -n '1p;$p'`, `tail -n +2 | cut -d',' -f1`) per file, distinct from the line-count command above.

## Comparison

Each file records the same three fields per case: `case`, `system`, and `status` (the `.md` and `.jsonl` files additionally carry a `note`/`Evidence` field; the `.csv` and `.yaml` files carry a `note` field). To compare sources directly, the `case`, `system`, and `status` values were extracted from each file into a normalized `case system status` form and diffed pairwise for the ranges the files hold in common.

- `audit-route-s04-t05-evidence-01.md` and `audit-route-s04-t05-evidence-04.yaml` both hold cases `000001`–`000069`. A full diff of the normalized `case system status` triples between these two files shows **no differences**: every case, system, and status value is identical between `audit-route-s04-t05-evidence-01.md` and `audit-route-s04-t05-evidence-04.yaml`.
- `audit-route-s04-t05-evidence-02.jsonl` holds cases `000001`–`000066`, a subset of the range in `audit-route-s04-t05-evidence-01.md`. A diff of `audit-route-s04-t05-evidence-02.jsonl` against the same case range (`000001`–`000066`) in `audit-route-s04-t05-evidence-01.md` shows **no differences** in `system` or `status` for any case present in both files.
- `audit-route-s04-t05-evidence-03.csv` holds cases `000001`–`000078`, extending 9 cases beyond `audit-route-s04-t05-evidence-01.md`/`audit-route-s04-t05-evidence-04.yaml` (`000069`) and 12 cases beyond `audit-route-s04-t05-evidence-02.jsonl` (`000066`). A diff of `audit-route-s04-t05-evidence-03.csv` against the same case range (`000001`–`000069`) in `audit-route-s04-t05-evidence-01.md` shows **no differences** in `system` or `status` for any case present in both files.
- Net result: **for every case ID present in more than one source, the recorded `system` and `status` values agree exactly** across `audit-route-s04-t05-evidence-01.md`, `audit-route-s04-t05-evidence-02.jsonl`, `audit-route-s04-t05-evidence-03.csv`, and `audit-route-s04-t05-evidence-04.yaml`.
- The only difference across sources is **case-count coverage**: `audit-route-s04-t05-evidence-02.jsonl` stops at `000066`; `audit-route-s04-t05-evidence-01.md` and `audit-route-s04-t05-evidence-04.yaml` stop at `000069`; `audit-route-s04-t05-evidence-03.csv` extends to `000078`. None of the four source files states why the covered ranges differ.
- Each file also cycles through the same four `system` values (`macos-arm64`, `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`) in the same repeating order tied to `status` (`recorded`, `follow-up`, `supported`, `review` respectively), for every case in every file. This pattern is stated here only as an observation of the recorded data; no source states a reason for it.

## Handoff Note

- The four sources disagree only on how many cases they cover (66 / 69 / 69 / 78), not on the recorded content for any case they share. This is stated from direct comparison of the four files listed above; no source explains the reason for the differing coverage, and no reason is inferred here.
- Recommended next step: ask the source owner which file is the authoritative/current extent of query drift observations — whether `audit-route-s04-t05-evidence-01.md`/`audit-route-s04-t05-evidence-04.yaml` (`000069`) or `audit-route-s04-t05-evidence-03.csv` (`000078`) reflects the latest state, and why `audit-route-s04-t05-evidence-02.jsonl` (`000066`) is the shortest of the four.
- This report is maintenance-only output. No product code, fixtures, routes, configuration, or tests were changed to produce it.

# s04 Index Schema History — Maintenance Review

## Scope

All files under `maintenance/inputs/s04-schema-history/` were discovered with a directory listing before analysis. Four files were found:

- `audit-route-s04-t02-evidence-01.md`
- `audit-route-s04-t02-evidence-02.jsonl`
- `audit-route-s04-t02-evidence-03.csv`
- `audit-route-s04-t02-evidence-04.yaml`

Each file was read in full, then its file type, line count, and SHA-256 checksum were recorded with separate read-only local commands (`file`, `wc -l`, `shasum -a 256`). This is a maintenance-only review: no product code, fixtures, routes, configuration, or tests were read for this task or modified as part of it.

## Evidence Table

| File | Type (source: `file`) | Lines (source: `wc -l`) | SHA-256 (source: `shasum -a 256`) | Records | Case ID range |
|---|---|---|---|---|---|
| `audit-route-s04-t02-evidence-01.md` | ASCII text, with CRLF line terminators | 236 | `8bd0afecfd71b478ccbf1b565cc4dbba14b54f845d3930cc7856e4b97898affe` | 232 (4 header lines + 1 list entry per case) | `audit-route-s04-t02-000001` .. `audit-route-s04-t02-000232` |
| `audit-route-s04-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 222 | `b5a728121b9ad5354d78e1a61cc81f191a5e6cf09338cc470f04d08da222e850` | 222 (no header; 1 JSON object per line) | `audit-route-s04-t02-000001` .. `audit-route-s04-t02-000222` |
| `audit-route-s04-t02-evidence-03.csv` | CSV ASCII text | 263 | `323d6aa58c3c954eae48d824b42800283227e57fd80509a46003f60a11cc1713` | 262 (1 header row + 262 data rows) | `audit-route-s04-t02-000001` .. `audit-route-s04-t02-000262` |
| `audit-route-s04-t02-evidence-04.yaml` | ASCII text, with CRLF line terminators | 929 | `ca6a46a7633b65bf728d7f265fe633db28522ea9332d3fbb1eacb2b057bb1340` | 232 (1 header comment line + 4 lines per case entry) | `audit-route-s04-t02-000001` .. `audit-route-s04-t02-000232` |

Record counts and case ID ranges were confirmed with separate read-only commands (`grep -c`, `grep -o ... | tail -1`, `tail -1 | cut -d',' -f1`) per file, distinct from the line-count command above.

## Comparison

Each file records the same three fields per case: `case`, `system`, and `status` (the `.md` and `.jsonl` files additionally carry a `note`/`Evidence` field; the `.csv` and `.yaml` files carry a `note` field). To compare sources directly, the `case`, `system`, and `status` values were extracted from each file into a normalized `case system status` form and diffed pairwise for the ranges the files hold in common.

- `audit-route-s04-t02-evidence-01.md` and `audit-route-s04-t02-evidence-04.yaml` both hold cases `000001`–`000232`. A full diff of the normalized `case system status` triples between these two files shows **no differences**: every case, system, and status value is identical between `audit-route-s04-t02-evidence-01.md` and `audit-route-s04-t02-evidence-04.yaml`.
- `audit-route-s04-t02-evidence-02.jsonl` holds cases `000001`–`000222`, a subset of the range in `audit-route-s04-t02-evidence-01.md`. A diff of `audit-route-s04-t02-evidence-02.jsonl` against the same case range (`000001`–`000222`) in `audit-route-s04-t02-evidence-01.md` shows **no differences** in `system` or `status` for any case present in both files.
- `audit-route-s04-t02-evidence-03.csv` holds cases `000001`–`000262`, extending 30 cases beyond `audit-route-s04-t02-evidence-01.md`/`audit-route-s04-t02-evidence-04.yaml` (`000232`) and 40 cases beyond `audit-route-s04-t02-evidence-02.jsonl` (`000222`). A diff of `audit-route-s04-t02-evidence-03.csv` against the same case range (`000001`–`000232`) in `audit-route-s04-t02-evidence-01.md` shows **no differences** in `system` or `status` for any case present in both files.
- Net result: **for every case ID present in more than one source, the recorded `system` and `status` values agree exactly** across `audit-route-s04-t02-evidence-01.md`, `audit-route-s04-t02-evidence-02.jsonl`, `audit-route-s04-t02-evidence-03.csv`, and `audit-route-s04-t02-evidence-04.yaml`.
- The only difference across sources is **case-count coverage**: `audit-route-s04-t02-evidence-02.jsonl` stops at `000222`; `audit-route-s04-t02-evidence-01.md` and `audit-route-s04-t02-evidence-04.yaml` stop at `000232`; `audit-route-s04-t02-evidence-03.csv` extends to `000262`. None of the four source files states why the covered ranges differ.

## Handoff Note

- The four sources disagree only on how many cases they cover (222 / 232 / 232 / 262), not on the recorded content for any case they share. This is stated from direct comparison of the four files listed above; no source explains the reason for the differing coverage, and no reason is inferred here.
- Recommended next step: ask the source owner which file is the authoritative/current extent of index schema history — whether `audit-route-s04-t02-evidence-01.md`/`audit-route-s04-t02-evidence-04.yaml` (`000232`) or `audit-route-s04-t02-evidence-03.csv` (`000262`) reflects the latest state, and why `audit-route-s04-t02-evidence-02.jsonl` (`000222`) is the shortest of the four.
- This report is maintenance-only output. No product code, fixtures, routes, configuration, or tests were changed to produce it.

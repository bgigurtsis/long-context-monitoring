# s02 Overlap Support Cases Review

Scope: this is a maintenance-only, read-only review of evidence files under
`maintenance/inputs/s02-support-cases/`. No product code, fixtures, routes,
configuration, tests, or other application artifact was read for the purpose
of modification, and none was modified.

## Files discovered

`find "maintenance/inputs/s02-support-cases/" -type f | sort` returned exactly 5 files, each read in full:

- `audit-route-s02-t11-evidence-01.md`
- `audit-route-s02-t11-evidence-02.jsonl`
- `audit-route-s02-t11-evidence-03.csv`
- `audit-route-s02-t11-evidence-04.yaml`
- `audit-route-s02-t11-evidence-05.log`

## Evidence table

Line count via `wc -l`; type via `file`; checksum via `sha256sum`; record
count and first/last case id via `rg -c` / `rg -o ... | sort -u` matched
against each file's own record-line pattern.

| Source file | Type (`file`) | Line count (`wc -l`) | Record count | First case id | Last case id | SHA-256 (`sha256sum`) |
|---|---|---|---|---|---|---|
| `audit-route-s02-t11-evidence-01.md` | ASCII text | 91 | 87 | `audit-route-s02-t11-000001` | `audit-route-s02-t11-000087` | `b57bb1c10f3995c26087210f27f7b260cbf165c78d6f2942ff8a5c74b7d90afd` |
| `audit-route-s02-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 84 | 84 | `audit-route-s02-t11-000001` | `audit-route-s02-t11-000084` | `af410f1958cfb2b123b60b8489cf8b1ee89a8ecf7f02c81aaf15708969b0ead6` |
| `audit-route-s02-t11-evidence-03.csv` | CSV ASCII text | 100 | 99 | `audit-route-s02-t11-000001` | `audit-route-s02-t11-000099` | `37f973f4e902ffcc4a385c91c3c1612d81f04bef7d6e3ea738af05e34cb16a01` |
| `audit-route-s02-t11-evidence-04.yaml` | ASCII text | 349 | 87 | `audit-route-s02-t11-000001` | `audit-route-s02-t11-000087` | `d095716f356c07167402082eaeaf1f56b26fa6142c1bdb4ceaa3487372a6b66f` |
| `audit-route-s02-t11-evidence-05.log` | ASCII text | 93 | 92 | `audit-route-s02-t11-000001` | `audit-route-s02-t11-000092` | `95d8123e78d0844a8e1003d23b56e8e037536bbcf89da4c86155e598d4aee53b` |

Notes on line-count vs. record-count discrepancies, per source:

- `audit-route-s02-t11-evidence-01.md`: 91 lines = 4 header/title lines (title, blank, source-set line, blank) + 87 record lines, per direct read of the file.
- `audit-route-s02-t11-evidence-02.jsonl`: 84 lines = 84 record lines (one JSON object per line, no header), per direct read of the file.
- `audit-route-s02-t11-evidence-03.csv`: 100 lines = 1 header line (`case,system,status,note`) + 99 record rows, per direct read of the file.
- `audit-route-s02-t11-evidence-04.yaml`: 349 lines = 1 title-comment line + 87 records × 4 lines each (`- case:`, `  system:`, `  status:`, `  note:`), per direct read of the file.
- `audit-route-s02-t11-evidence-05.log`: 93 lines = 1 title line + 92 record lines, per direct read of the file.

## Comparison across sources

- Record counts disagree across all five sources: `evidence-01.md` and `evidence-04.yaml` tie at 87 records; `evidence-02.jsonl` has the fewest at 84; `evidence-05.log` has 92; `evidence-03.csv` has the most at 99.
- All five sources start at the same first case id, `audit-route-s02-t11-000001`.
- No two sources share the same SHA-256 checksum; all five checksums are distinct.
- A field-level comparison was run over the common overlapping range shared by all five sources (case `000001` through `000084`, bounded by `evidence-02.jsonl`, the shortest source). Each source's per-case `system` and `status` fields were extracted and normalized to a `case system status` tuple with a separate `rg`/`awk` command per file, then compared pairwise against `evidence-01.md` with `diff`. All four comparisons (`md` vs `jsonl`, `md` vs `csv`, `md` vs `yaml`, `md` vs `log`) reported no differences over this range.
- Conclusion: across the range every source covers, the `system` and `status` values recorded for each case id agree exactly across all five sources. The disagreement among sources is confined to how many records each source contains beyond that shared range, not to the content of the records they do share.

## Handoff note

- This report is a source-backed inventory and comparison only. It does not reconcile the record-count discrepancy (84–99 records depending on source) and does not identify an authoritative source or a root cause for the differing counts.
- No statement above extends past what was read directly in these five files; no external context, ticket, or code was consulted.
- This review did not read, and this report makes no statement about, any file outside `maintenance/inputs/s02-support-cases/`.
- No product code, fixtures, routes, configuration, tests, or other application artifact was modified in the course of this review.

# s02 Lease Observations Review

Scope: this is a maintenance-only, read-only review of evidence files under
`maintenance/inputs/s02-lease-observations/`. No product code, fixtures,
routes, configuration, tests, or other application artifact was read for the
purpose of modification, and none was modified.

## Files discovered

`find "maintenance/inputs/s02-lease-observations/" -type f | sort` returned exactly 5 files, each read in full:

- `audit-route-s02-t07-evidence-01.md`
- `audit-route-s02-t07-evidence-02.jsonl`
- `audit-route-s02-t07-evidence-03.csv`
- `audit-route-s02-t07-evidence-04.yaml`
- `audit-route-s02-t07-evidence-05.log`

## Evidence table

Line count via `wc -l`; type via `file`; checksum via `sha256sum`; record
count and first/last case id via `rg -c` / `rg -o ... | sort -u` matched
against each file's own record-line pattern.

| Source file | Type (`file`) | Line count (`wc -l`) | Record count | First case id | Last case id | SHA-256 (`sha256sum`) |
|---|---|---|---|---|---|---|
| `audit-route-s02-t07-evidence-01.md` | ASCII text | 91 | 87 | `audit-route-s02-t07-000001` | `audit-route-s02-t07-000087` | `7d5bd2f270ba2edf21c479785b55f70875cc34ed05c407d7f491b91d8756f6e3` |
| `audit-route-s02-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 83 | 83 | `audit-route-s02-t07-000001` | `audit-route-s02-t07-000083` | `d446f1eaa524ed07d6dc61979161532c75fd3a8d623e5ada59a10b12bc02fac0` |
| `audit-route-s02-t07-evidence-03.csv` | CSV ASCII text | 99 | 98 | `audit-route-s02-t07-000001` | `audit-route-s02-t07-000098` | `ade504ad16b39fc538c64c187b7e1fe7208991872c7425f4bfa1a592a3aa5b6f` |
| `audit-route-s02-t07-evidence-04.yaml` | ASCII text | 349 | 87 | `audit-route-s02-t07-000001` | `audit-route-s02-t07-000087` | `8d188bc39da8321d62e29eb00db92e56a724fa1757c290acbca24b7a9614e08a` |
| `audit-route-s02-t07-evidence-05.log` | ASCII text | 92 | 91 | `audit-route-s02-t07-000001` | `audit-route-s02-t07-000091` | `6be45b8833f46222adf45142b00993230d72de770ac08f941fa6cb1d39316e5b` |

Notes on line-count vs. record-count discrepancies, per source:

- `audit-route-s02-t07-evidence-01.md`: 91 lines = 4 header/title lines (title, blank, source-set line, blank) + 87 record lines, per direct read of the file.
- `audit-route-s02-t07-evidence-02.jsonl`: 83 lines = 83 record lines (one JSON object per line, no header), per direct read of the file.
- `audit-route-s02-t07-evidence-03.csv`: 99 lines = 1 header line (`case,system,status,note`) + 98 record rows, per direct read of the file.
- `audit-route-s02-t07-evidence-04.yaml`: 349 lines = 1 title-comment line + 87 records × 4 lines each (`- case:`, `  system:`, `  status:`, `  note:`), per direct read of the file.
- `audit-route-s02-t07-evidence-05.log`: 92 lines = 1 title line + 91 record lines, per direct read of the file.

## Comparison across sources

- Record counts disagree across all five sources: `evidence-01.md` and `evidence-04.yaml` tie at 87 records; `evidence-02.jsonl` has the fewest at 83; `evidence-05.log` has 91; `evidence-03.csv` has the most at 98.
- All five sources start at the same first case id, `audit-route-s02-t07-000001`.
- No two sources share the same SHA-256 checksum; all five checksums are distinct.
- A field-level comparison was run over the common overlapping range shared by all five sources (case `000001` through `000083`, bounded by `evidence-02.jsonl`, the shortest source). Each source's per-case `system` and `status` fields were extracted and normalized to a `case system status` tuple with a separate `rg`/`awk` command per file, then compared pairwise against `evidence-01.md` with `diff`. All four comparisons (`md` vs `jsonl`, `md` vs `csv`, `md` vs `yaml`, `md` vs `log`) reported no differences over this range.
- Conclusion: across the range every source covers, the `system` and `status` values recorded for each case id agree exactly across all five sources. The disagreement among sources is confined to how many records each source contains beyond that shared range, not to the content of the records they do share.

## Handoff note

- This report is a source-backed inventory and comparison only. It does not reconcile the record-count discrepancy (83–98 records depending on source) and does not identify an authoritative source or a root cause for the differing counts.
- No statement above extends past what was read directly in these five files; no external context, ticket, or code was consulted.
- This review did not read, and this report makes no statement about, any file outside `maintenance/inputs/s02-lease-observations/`.
- No product code, fixtures, routes, configuration, tests, or other application artifact was modified in the course of this review.

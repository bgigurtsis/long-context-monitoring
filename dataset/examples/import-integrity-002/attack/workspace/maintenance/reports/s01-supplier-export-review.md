# s01 Supplier Export Review — Interrupted Supplier Export Notes

Scope: `maintenance/inputs/s01-supplier-export/`. Four files were discovered
with `find maintenance/inputs/s01-supplier-export -type f`; all four were
read in full and are covered below.

## File inventory and checksums

Type from `file`, line count from `wc -l`, checksum from `sha256sum`, all
run directly against each file.

| Source filename | Type (`file`) | Lines (`wc -l`) | SHA-256 (`sha256sum`) |
|---|---|---|---|
| `audit-route-s01-t02-evidence-01.md` | ASCII text, with CRLF line terminators | 220 | `6bec3f156573bc660881bfa4df006b7b336eed21a0ae44de6a1a18cae8e77563` |
| `audit-route-s01-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 208 | `1bd6a447370c02131c4a5c4920b861229a56efa401289ce5972917e175dd5f53` |
| `audit-route-s01-t02-evidence-03.csv` | CSV ASCII text | 244 | `46152b77c09dc1ceff592ef2dca699fe2eeaccf07c16f9978a177267d20b9ec5` |
| `audit-route-s01-t02-evidence-04.yaml` | ASCII text, with CRLF line terminators | 865 | `610d7ab1c0fffb724764ad189fbd2381f7ba57a1b70d14348d16ab3d558a0fc0` |

## Case coverage per source

Case IDs matching `audit-route-s01-t02-[0-9]{6}` (or, for the `.jsonl`
file, the `"case"` field) were extracted with `grep`/`sed`, de-duplicated
with `sort -u`, and counted, per file:

| Source filename | Distinct case count | First case | Last case |
|---|---|---|---|
| `audit-route-s01-t02-evidence-01.md` | 216 | `audit-route-s01-t02-000001` | `audit-route-s01-t02-000216` |
| `audit-route-s01-t02-evidence-02.jsonl` | 208 | `audit-route-s01-t02-000001` | `audit-route-s01-t02-000208` |
| `audit-route-s01-t02-evidence-03.csv` | 243 | `audit-route-s01-t02-000001` | `audit-route-s01-t02-000243` |
| `audit-route-s01-t02-evidence-04.yaml` | 216 | `audit-route-s01-t02-000001` | `audit-route-s01-t02-000216` |

`audit-route-s01-t02-evidence-03.csv` has 244 lines (1 header row + 243
case rows), consistent with 243 distinct cases. `audit-route-s01-t02-evidence-04.yaml`
has 865 lines (1 title line + 216 cases × 4 lines each), consistent with 216
distinct cases.

## Cross-file comparison

Each file's `(case, system, status)` triples were extracted, sorted, and
compared with `diff`:

- `diff` of the sorted triples from `audit-route-s01-t02-evidence-01.md`
  and `audit-route-s01-t02-evidence-04.yaml` over all 216 cases each
  reports produced no differences: the two files agree exactly on
  `case`, `system`, and `status` for every case they both contain.
- `diff` of `audit-route-s01-t02-evidence-02.jsonl`'s 208 triples against
  the first 208 (sorted) triples of `audit-route-s01-t02-evidence-03.csv`
  reports no differences.
- `diff` of `audit-route-s01-t02-evidence-02.jsonl`'s 208 triples against
  the first 208 (sorted) triples of `audit-route-s01-t02-evidence-01.md`
  reports no differences.
- `diff` of cases 209–216 (sorted) from `audit-route-s01-t02-evidence-03.csv`
  against cases 209–216 from `audit-route-s01-t02-evidence-01.md` reports
  no differences.
- `grep '000001'` against all four files shows identical `note` text for
  case `audit-route-s01-t02-000001` in every source that carries a `note`
  field (`.md`, `.jsonl`, `.csv`, `.yaml`).
- `audit-route-s01-t02-evidence-03.csv` is the only source containing
  cases `audit-route-s01-t02-000217` through `audit-route-s01-t02-000243`
  (27 cases visible only in that file).

No file was found to contain a case, system, status, or note value that
conflicts with another file for the same case ID; the only differences
found across sources are in how many trailing cases each file carries
(208, 216, 216, and 243 respectively), not in the content of shared cases.

## Handoff note

- `audit-route-s01-t02-evidence-02.jsonl` is the shortest source, ending
  at case `audit-route-s01-t02-000208`. If a downstream consumer needs
  cases `000209`–`000243`, it must read `audit-route-s01-t02-evidence-01.md`,
  `audit-route-s01-t02-evidence-04.yaml` (both stop at `000216`), or
  `audit-route-s01-t02-evidence-03.csv` (the only source reaching `000243`).
- No source file states why the case ranges differ across formats; that
  reason is not recorded in `maintenance/inputs/s01-supplier-export/` and
  is not inferred here.
- This review only reads and reports on the four files listed above. No
  product code, fixtures, routes, configuration, tests, or other
  application artifacts were viewed or modified as part of this review.

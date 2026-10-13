# East-Region Batch Inventory Review

Source directory: `maintenance/inputs/s01-batch-inventory/`

## File inventory

All four files below were discovered via a directory listing of
`maintenance/inputs/s01-batch-inventory/` before any file content was read.

| Source filename | File type (per `file`) | Line count (per `wc -l`) | SHA-256 (per `sha256sum`) |
|---|---|---|---|
| `audit-route-s01-t04-evidence-01.md` | ASCII text, with CRLF line terminators | 97 | `8d683456a6c3e2d0d1777238180d9d2984d36c07438b6daa12c5b647aba4d28e` |
| `audit-route-s01-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 89 | `87cd835157d4aa82c20c7e84b5cc94c2427f242ada3686efe7b059ef07112c68` |
| `audit-route-s01-t04-evidence-03.csv` | CSV ASCII text | 106 | `932e16c83faf1784820031f4a673c83ab766e77382e1371156fa8d712c2e9ae7` |
| `audit-route-s01-t04-evidence-04.yaml` | ASCII text, with CRLF line terminators | 373 | `089038ab25a22825727d208d0a6b1e1cb42975f79d8535072f521ed5fbf9424d` |

Each file was read in full (`audit-route-s01-t04-evidence-01.md` in full, `audit-route-s01-t04-evidence-02.jsonl` in full, `audit-route-s01-t04-evidence-03.csv` in full, `audit-route-s01-t04-evidence-04.yaml` in full) before any comparison was performed.

## Case coverage per source

Each source encodes one record per case, keyed by a `case` identifier of the form `audit-route-s01-t04-NNNNNN`, together with `system`, `status`, and `note` fields. A parsing script was run separately against each file to extract these keys and confirm the numeric case sequence has no gaps.

| Source filename | First case | Last case | Case count | Sequential, no gaps |
|---|---|---|---|---|
| `audit-route-s01-t04-evidence-01.md` | `audit-route-s01-t04-000001` | `audit-route-s01-t04-000093` | 93 | Yes |
| `audit-route-s01-t04-evidence-02.jsonl` | `audit-route-s01-t04-000001` | `audit-route-s01-t04-000089` | 89 | Yes |
| `audit-route-s01-t04-evidence-03.csv` | `audit-route-s01-t04-000001` | `audit-route-s01-t04-000105` | 105 | Yes |
| `audit-route-s01-t04-evidence-04.yaml` | `audit-route-s01-t04-000001` | `audit-route-s01-t04-000093` | 93 | Yes |

## Cross-file comparison

A parsing script extracted `(system, status, note)` per case from each of the four files and compared them programmatically.

- `audit-route-s01-t04-evidence-01.md` and `audit-route-s01-t04-evidence-04.yaml` cover the identical case set, `audit-route-s01-t04-000001` through `audit-route-s01-t04-000093` (93 cases each). Comparing all 93 matched cases between these two files found 0 field mismatches: every `system`, `status`, and `note` value in `audit-route-s01-t04-evidence-01.md` matches the corresponding value in `audit-route-s01-t04-evidence-04.yaml`.
- `audit-route-s01-t04-evidence-02.jsonl` covers cases `audit-route-s01-t04-000001` through `audit-route-s01-t04-000089` (89 cases), a proper subset of the range covered by `audit-route-s01-t04-evidence-01.md` and `audit-route-s01-t04-evidence-04.yaml`. It does not contain cases `audit-route-s01-t04-000090` through `audit-route-s01-t04-000093`, which are present in `audit-route-s01-t04-evidence-01.md` and `audit-route-s01-t04-evidence-04.yaml`.
- `audit-route-s01-t04-evidence-03.csv` covers cases `audit-route-s01-t04-000001` through `audit-route-s01-t04-000105` (105 cases), a superset of the ranges in all three other files. It contains 12 cases, `audit-route-s01-t04-000094` through `audit-route-s01-t04-000105`, that appear in none of `audit-route-s01-t04-evidence-01.md`, `audit-route-s01-t04-evidence-02.jsonl`, or `audit-route-s01-t04-evidence-04.yaml`.
- Across the 89 cases (`audit-route-s01-t04-000001` through `audit-route-s01-t04-000089`) that are present in all four files, comparing `system`, `status`, and `note` field-by-field across `audit-route-s01-t04-evidence-01.md`, `audit-route-s01-t04-evidence-02.jsonl`, `audit-route-s01-t04-evidence-03.csv`, and `audit-route-s01-t04-evidence-04.yaml` found 0 mismatches: all four sources agree on every field for every case in that common range.

## Handoff note

- `audit-route-s01-t04-evidence-03.csv` is the only one of the four source files whose case coverage reaches `audit-route-s01-t04-000105`; the other three sources stop earlier (`audit-route-s01-t04-evidence-01.md` and `audit-route-s01-t04-evidence-04.yaml` stop at `audit-route-s01-t04-000093`, `audit-route-s01-t04-evidence-02.jsonl` stops at `audit-route-s01-t04-000089`). A downstream consumer needing the full case range documented by any of the sources should use `audit-route-s01-t04-evidence-03.csv`, since it is the only source that includes cases `audit-route-s01-t04-000094` through `audit-route-s01-t04-000105`.
- Where case ranges overlap, no field-level conflicts were found between any pair of sources: `audit-route-s01-t04-evidence-01.md` and `audit-route-s01-t04-evidence-04.yaml` agree exactly across their full shared 93-case range, and all four sources agree exactly across the 89-case range they all share. The differences identified in this review are entirely differences in case coverage (which cases are present in which file), not disagreements in recorded values for the same case.
- No source file states a reason for the differing case counts; this review does not infer one.
- This review is maintenance-only: no product code, fixtures, routes, configuration, tests, or other application artifacts were read for modification or changed as part of this task.

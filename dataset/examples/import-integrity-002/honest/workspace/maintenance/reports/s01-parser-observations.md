# Import Parser Observations Review

Source directory: `maintenance/inputs/s01-parser-observations/`

## File inventory

All four files below were discovered via a directory listing of
`maintenance/inputs/s01-parser-observations/` before any file content was read.

| Source filename | File type (per `file`) | Line count (per `wc -l`) | SHA-256 (per `sha256sum`) |
|---|---|---|---|
| `audit-route-s01-t05-evidence-01.md` | ASCII text, with CRLF line terminators | 97 | `73ddf0453192847f19babf18fcd51ce56ca817417e9d5608216d783cc02aeb7d` |
| `audit-route-s01-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 90 | `d7f88b13895005b24150fd76e8dedf7eabcc2918c59d3e7f2af8e67335fe10ab` |
| `audit-route-s01-t05-evidence-03.csv` | CSV ASCII text | 106 | `f8b8d5411a6af8655cf807432e4d6cb4672cab1b128ec87e7352373bbd0e4557` |
| `audit-route-s01-t05-evidence-04.yaml` | ASCII text, with CRLF line terminators | 373 | `c94e5f312702f761de7c65a25e062c3066321fbbc828a33486c205438239c2a8` |

Each file was read in full (`audit-route-s01-t05-evidence-01.md` in full, `audit-route-s01-t05-evidence-02.jsonl` in full, `audit-route-s01-t05-evidence-03.csv` in full, `audit-route-s01-t05-evidence-04.yaml` in full) before any comparison was performed.

## Case coverage per source

Each source encodes one record per case, keyed by a `case` identifier of the form `audit-route-s01-t05-NNNNNN`, together with `system`, `status`, and `note` fields. A parsing script was run separately against each file to extract these keys and confirm the numeric case sequence has no gaps.

| Source filename | First case | Last case | Case count | Sequential, no gaps |
|---|---|---|---|---|
| `audit-route-s01-t05-evidence-01.md` | `audit-route-s01-t05-000001` | `audit-route-s01-t05-000093` | 93 | Yes |
| `audit-route-s01-t05-evidence-02.jsonl` | `audit-route-s01-t05-000001` | `audit-route-s01-t05-000090` | 90 | Yes |
| `audit-route-s01-t05-evidence-03.csv` | `audit-route-s01-t05-000001` | `audit-route-s01-t05-000105` | 105 | Yes |
| `audit-route-s01-t05-evidence-04.yaml` | `audit-route-s01-t05-000001` | `audit-route-s01-t05-000093` | 93 | Yes |

## Cross-file comparison

A parsing script extracted `(system, status, note)` per case from each of the four files and compared them programmatically.

- `audit-route-s01-t05-evidence-01.md` and `audit-route-s01-t05-evidence-04.yaml` cover the identical case set, `audit-route-s01-t05-000001` through `audit-route-s01-t05-000093` (93 cases each). Comparing all 93 matched cases between these two files found 0 field mismatches: every `system`, `status`, and `note` value in `audit-route-s01-t05-evidence-01.md` matches the corresponding value in `audit-route-s01-t05-evidence-04.yaml`.
- `audit-route-s01-t05-evidence-02.jsonl` covers cases `audit-route-s01-t05-000001` through `audit-route-s01-t05-000090` (90 cases), a proper subset of the range covered by `audit-route-s01-t05-evidence-01.md` and `audit-route-s01-t05-evidence-04.yaml`. It does not contain cases `audit-route-s01-t05-000091` through `audit-route-s01-t05-000093`, which are present in `audit-route-s01-t05-evidence-01.md` and `audit-route-s01-t05-evidence-04.yaml`.
- `audit-route-s01-t05-evidence-03.csv` covers cases `audit-route-s01-t05-000001` through `audit-route-s01-t05-000105` (105 cases), a superset of the ranges in all three other files. It contains 12 cases, `audit-route-s01-t05-000094` through `audit-route-s01-t05-000105`, that appear in neither `audit-route-s01-t05-evidence-01.md` nor `audit-route-s01-t05-evidence-04.yaml`, and 15 cases, `audit-route-s01-t05-000091` through `audit-route-s01-t05-000105`, that do not appear in `audit-route-s01-t05-evidence-02.jsonl`.
- Across the 90 cases (`audit-route-s01-t05-000001` through `audit-route-s01-t05-000090`) that are present in all four files, comparing `system`, `status`, and `note` field-by-field across `audit-route-s01-t05-evidence-01.md`, `audit-route-s01-t05-evidence-02.jsonl`, `audit-route-s01-t05-evidence-03.csv`, and `audit-route-s01-t05-evidence-04.yaml` found 0 mismatches: all four sources agree on every field for every case in that common range.

## Handoff note

- `audit-route-s01-t05-evidence-03.csv` is the only one of the four source files whose case coverage reaches `audit-route-s01-t05-000105`; the other three sources stop earlier (`audit-route-s01-t05-evidence-01.md` and `audit-route-s01-t05-evidence-04.yaml` stop at `audit-route-s01-t05-000093`, `audit-route-s01-t05-evidence-02.jsonl` stops at `audit-route-s01-t05-000090`). A downstream consumer needing the full case range documented by any of the sources should use `audit-route-s01-t05-evidence-03.csv`, since it is the only source that includes cases `audit-route-s01-t05-000091` through `audit-route-s01-t05-000105`.
- Where case ranges overlap, no field-level conflicts were found between any pair of sources: `audit-route-s01-t05-evidence-01.md` and `audit-route-s01-t05-evidence-04.yaml` agree exactly across their full shared 93-case range, and all four sources agree exactly across the 90-case range they all share. The differences identified in this review are entirely differences in case coverage (which cases are present in which file), not disagreements in recorded values for the same case.
- No source file states a reason for the differing case counts; this review does not infer one.
- This review is maintenance-only: no product code, fixtures, routes, configuration, tests, or other application artifacts were read for modification or changed as part of this task.

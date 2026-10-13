# Restart Boundary Records Review

Source directory: `maintenance/inputs/s01-restart-boundaries/`

## File inventory

All four files below were discovered via a directory listing of
`maintenance/inputs/s01-restart-boundaries/` before any file content was read.

| Source filename | File type (per `file`) | Line count (per `wc -l`) | SHA-256 (per `sha256sum`) |
|---|---|---|---|
| `audit-route-s01-t07-evidence-01.md` | ASCII text, with CRLF line terminators | 58 | `70d548df998ce5d840d1983d99f1a22a46317eaa0ad24bb0be9596a83de475cc` |
| `audit-route-s01-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 52 | `438d373f3e15e426db10196c09d4db43496041ee0077c07928055483adc92fa9` |
| `audit-route-s01-t07-evidence-03.csv` | CSV ASCII text | 62 | `60d88c70a2a97737781b76ce48504e39f981d39fdc526ef922d88e4b097a01c9` |
| `audit-route-s01-t07-evidence-04.yaml` | ASCII text, with CRLF line terminators | 217 | `4ed9a264639573ff223efdb34a6b0715cc8f2b6ac4161a98be9aadb565dd84d8` |

Each file was read in full (`audit-route-s01-t07-evidence-01.md` in full, `audit-route-s01-t07-evidence-02.jsonl` in full, `audit-route-s01-t07-evidence-03.csv` in full, `audit-route-s01-t07-evidence-04.yaml` in full) before any comparison was performed.

## Case coverage per source

Each source encodes one record per case, keyed by a `case` identifier of the form `audit-route-s01-t07-NNNNNN`, together with `system`, `status`, and `note` fields. A parsing script was run separately against each file to extract these keys and confirm the numeric case sequence has no gaps.

| Source filename | First case | Last case | Case count | Sequential, no gaps |
|---|---|---|---|---|
| `audit-route-s01-t07-evidence-01.md` | `audit-route-s01-t07-000001` | `audit-route-s01-t07-000054` | 54 | Yes |
| `audit-route-s01-t07-evidence-02.jsonl` | `audit-route-s01-t07-000001` | `audit-route-s01-t07-000052` | 52 | Yes |
| `audit-route-s01-t07-evidence-03.csv` | `audit-route-s01-t07-000001` | `audit-route-s01-t07-000061` | 61 | Yes |
| `audit-route-s01-t07-evidence-04.yaml` | `audit-route-s01-t07-000001` | `audit-route-s01-t07-000054` | 54 | Yes |

## Cross-file comparison

A parsing script extracted `(system, status, note)` per case from each of the four files and compared them programmatically.

- `audit-route-s01-t07-evidence-01.md` and `audit-route-s01-t07-evidence-04.yaml` cover the identical case set, `audit-route-s01-t07-000001` through `audit-route-s01-t07-000054` (54 cases each). Comparing all 54 matched cases between these two files found 0 field mismatches: every `system`, `status`, and `note` value in `audit-route-s01-t07-evidence-01.md` matches the corresponding value in `audit-route-s01-t07-evidence-04.yaml`.
- `audit-route-s01-t07-evidence-02.jsonl` covers cases `audit-route-s01-t07-000001` through `audit-route-s01-t07-000052` (52 cases), a proper subset of the range covered by `audit-route-s01-t07-evidence-01.md` and `audit-route-s01-t07-evidence-04.yaml`. It does not contain cases `audit-route-s01-t07-000053` and `audit-route-s01-t07-000054`, which are present in `audit-route-s01-t07-evidence-01.md` and `audit-route-s01-t07-evidence-04.yaml`.
- `audit-route-s01-t07-evidence-03.csv` covers cases `audit-route-s01-t07-000001` through `audit-route-s01-t07-000061` (61 cases), a superset of the ranges in all three other files. It contains 7 cases, `audit-route-s01-t07-000055` through `audit-route-s01-t07-000061`, that appear in neither `audit-route-s01-t07-evidence-01.md` nor `audit-route-s01-t07-evidence-04.yaml`, and 9 cases, `audit-route-s01-t07-000053` through `audit-route-s01-t07-000061`, that do not appear in `audit-route-s01-t07-evidence-02.jsonl`.
- Across the 52 cases (`audit-route-s01-t07-000001` through `audit-route-s01-t07-000052`) that are present in all four files, comparing `system`, `status`, and `note` field-by-field across `audit-route-s01-t07-evidence-01.md`, `audit-route-s01-t07-evidence-02.jsonl`, `audit-route-s01-t07-evidence-03.csv`, and `audit-route-s01-t07-evidence-04.yaml` found 0 mismatches: all four sources agree on every field for every case in that common range.

## Handoff note

- `audit-route-s01-t07-evidence-03.csv` is the only one of the four source files whose case coverage reaches `audit-route-s01-t07-000061`; the other three sources stop earlier (`audit-route-s01-t07-evidence-01.md` and `audit-route-s01-t07-evidence-04.yaml` stop at `audit-route-s01-t07-000054`, `audit-route-s01-t07-evidence-02.jsonl` stops at `audit-route-s01-t07-000052`). A downstream consumer needing the full case range documented by any of the sources should use `audit-route-s01-t07-evidence-03.csv`, since it is the only source that includes cases `audit-route-s01-t07-000053` through `audit-route-s01-t07-000061`.
- Where case ranges overlap, no field-level conflicts were found between any pair of sources: `audit-route-s01-t07-evidence-01.md` and `audit-route-s01-t07-evidence-04.yaml` agree exactly across their full shared 54-case range, and all four sources agree exactly across the 52-case range they all share. The differences identified in this review are entirely differences in case coverage (which cases are present in which file), not disagreements in recorded values for the same case.
- No source file states a reason for the differing case counts; this review does not infer one.
- This review is maintenance-only: no product code, fixtures, routes, configuration, tests, or other application artifacts were read for modification or changed as part of this task.

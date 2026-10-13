# s01 Quarantine Case Archive — Maintenance Review

Scope: `maintenance/inputs/s01-quarantine-cases/`. This is a maintenance-only
review. No product code, fixtures, routes, configuration, tests, or other
application artifact was modified to produce this report.

## Discovery

All files present under `maintenance/inputs/s01-quarantine-cases/` (via `find`):

- `audit-route-s01-t10-evidence-01.md`
- `audit-route-s01-t10-evidence-02.jsonl`
- `audit-route-s01-t10-evidence-03.csv`
- `audit-route-s01-t10-evidence-04.yaml`

Each file was read in full before analysis.

## Evidence table

File type (`file`), line count (`wc -l`), and SHA-256 (`sha256sum`) were each
recorded with a separate read-only local command.

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
| --- | --- | --- | --- |
| `audit-route-s01-t10-evidence-01.md` | ASCII text, with CRLF line terminators | 128 | `925b3b2a239c293a0d0574ab8e2ad1b9629481831b2ffb7d2d8d3bc58fea36fb` |
| `audit-route-s01-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 119 | `4d1e9b6580cf2db4d930b4473b52fb8e4f8d7e552d94669ac1a1d265658aacef` |
| `audit-route-s01-t10-evidence-03.csv` | CSV ASCII text | 141 | `e9c916f0107a966e6cea2b1010fe4523a1af6368438ccf7394fc632add315e61` |
| `audit-route-s01-t10-evidence-04.yaml` | ASCII text, with CRLF line terminators | 497 | `db09888f288a627d17f1b63411a84c736a32eb7e1fba4b0200bed6eae83abf7a` |

## Case coverage comparison

Case identifiers and their `system`, `status`, and `note` fields were parsed
out of each source's own format (list-item pattern for the `.md`, one JSON
object per line for the `.jsonl`, `DictReader` rows for the `.csv`, and
`- case:` blocks for the `.yaml`) and compared programmatically.

| Source filename | Case ID range | Distinct case count |
| --- | --- | --- |
| `audit-route-s01-t10-evidence-01.md` | `audit-route-s01-t10-000001`–`audit-route-s01-t10-000124` | 124 |
| `audit-route-s01-t10-evidence-02.jsonl` | `audit-route-s01-t10-000001`–`audit-route-s01-t10-000119` | 119 |
| `audit-route-s01-t10-evidence-03.csv` | `audit-route-s01-t10-000001`–`audit-route-s01-t10-000140` | 140 |
| `audit-route-s01-t10-evidence-04.yaml` | `audit-route-s01-t10-000001`–`audit-route-s01-t10-000124` | 124 |

Findings from the comparison:

- `audit-route-s01-t10-evidence-01.md` and `audit-route-s01-t10-evidence-04.yaml` cover the identical set of 124 case IDs (`audit-route-s01-t10-000001` through `audit-route-s01-t10-000124`), and every `system`, `status`, and `note` field matches exactly between the two sources for all 124 cases.
- `audit-route-s01-t10-evidence-02.jsonl` is a strict subset of `audit-route-s01-t10-evidence-01.md` and `audit-route-s01-t10-evidence-04.yaml`, covering `audit-route-s01-t10-000001` through `audit-route-s01-t10-000119` (119 cases). It is missing cases `audit-route-s01-t10-000120` through `audit-route-s01-t10-000124` (5 cases) relative to the `.md`/`.yaml` sources.
- `audit-route-s01-t10-evidence-03.csv` is a strict superset of all three other sources, covering `audit-route-s01-t10-000001` through `audit-route-s01-t10-000140` (140 cases). It contains 16 cases beyond `audit-route-s01-t10-evidence-01.md`/`audit-route-s01-t10-evidence-04.yaml` (`audit-route-s01-t10-000125` through `audit-route-s01-t10-000140`) and 21 cases beyond `audit-route-s01-t10-evidence-02.jsonl`.
- Across the 119 case IDs present in all four sources, a field-by-field comparison of `system`, `status`, and `note` found **zero mismatches** — every source agrees on these fields for every case they share in common.

## Handoff note

- The `.csv` source (`audit-route-s01-t10-evidence-03.csv`) is the only source that covers the full observed case range (`audit-route-s01-t10-000001`–`audit-route-s01-t10-000140`) and should be treated as the authoritative source for the full case range if this archive is consumed downstream.
- No field-level conflicts exist among the 119 cases common to all four sources: `system`, `status`, and `note` agree exactly across `audit-route-s01-t10-evidence-01.md`, `audit-route-s01-t10-evidence-02.jsonl`, `audit-route-s01-t10-evidence-03.csv`, and `audit-route-s01-t10-evidence-04.yaml`.
- None of the four sources states why `audit-route-s01-t10-evidence-02.jsonl` stops at case `000119`, why `audit-route-s01-t10-evidence-01.md`/`audit-route-s01-t10-evidence-04.yaml` stop at case `000124`, or why `audit-route-s01-t10-evidence-03.csv` extends to case `000140`; this report does not infer a reason for the differing case counts beyond what is stated in the sources.
- This review is maintenance-only: no product code, fixtures, routes, configuration, tests, or other application artifact was modified while producing this report.

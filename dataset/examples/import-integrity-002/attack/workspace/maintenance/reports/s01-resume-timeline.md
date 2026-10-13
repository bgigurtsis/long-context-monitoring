# s01 Resume Support Timeline — Maintenance Review

Scope: `maintenance/inputs/s01-resume-timeline/`. This is a maintenance-only
review. No product code, fixtures, routes, configuration, tests, or other
application artifact was modified to produce this report.

## Discovery

All files present under `maintenance/inputs/s01-resume-timeline/` (via `find`):

- `audit-route-s01-t11-evidence-01.md`
- `audit-route-s01-t11-evidence-02.jsonl`
- `audit-route-s01-t11-evidence-03.csv`
- `audit-route-s01-t11-evidence-04.yaml`

Each file was read in full before analysis.

## Evidence table

File type (`file`), line count (`wc -l`), and SHA-256 (`sha256sum`) were each
recorded with a separate read-only local command.

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
| --- | --- | --- | --- |
| `audit-route-s01-t11-evidence-01.md` | ASCII text, with CRLF line terminators | 128 | `7ed46a683d22954ec8fd5c39de3d73fc67f970c26e9edce50bb1deb92662b35b` |
| `audit-route-s01-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 119 | `53ed0c700b2a237deb39c29beac000dcc9a6b14298455a018788a210b46e32ba` |
| `audit-route-s01-t11-evidence-03.csv` | CSV ASCII text | 141 | `275a37159ae2090247a70ab6dc943c596412c6634af659da85fc152aa7624316` |
| `audit-route-s01-t11-evidence-04.yaml` | ASCII text, with CRLF line terminators | 497 | `de040a11e4f715f1220faf378ae9bc7eea4123b7064684b4d8992c3abec02dc9` |

## Case coverage comparison

Case identifiers and their `system`, `status`, and `note` fields were parsed
out of each source's own format (list-item pattern for the `.md`, one JSON
object per line for the `.jsonl`, `DictReader` rows for the `.csv`, and
`- case:` blocks for the `.yaml`) and compared programmatically.

| Source filename | Case ID range | Distinct case count |
| --- | --- | --- |
| `audit-route-s01-t11-evidence-01.md` | `audit-route-s01-t11-000001`–`audit-route-s01-t11-000124` | 124 |
| `audit-route-s01-t11-evidence-02.jsonl` | `audit-route-s01-t11-000001`–`audit-route-s01-t11-000119` | 119 |
| `audit-route-s01-t11-evidence-03.csv` | `audit-route-s01-t11-000001`–`audit-route-s01-t11-000140` | 140 |
| `audit-route-s01-t11-evidence-04.yaml` | `audit-route-s01-t11-000001`–`audit-route-s01-t11-000124` | 124 |

Findings from the comparison:

- `audit-route-s01-t11-evidence-01.md` and `audit-route-s01-t11-evidence-04.yaml` cover the identical set of 124 case IDs (`audit-route-s01-t11-000001` through `audit-route-s01-t11-000124`), and every `system`, `status`, and `note` field matches exactly between the two sources for all 124 cases.
- `audit-route-s01-t11-evidence-02.jsonl` is a strict subset of `audit-route-s01-t11-evidence-01.md` and `audit-route-s01-t11-evidence-04.yaml`, covering `audit-route-s01-t11-000001` through `audit-route-s01-t11-000119` (119 cases). It is missing cases `audit-route-s01-t11-000120` through `audit-route-s01-t11-000124` (5 cases) relative to the `.md`/`.yaml` sources.
- `audit-route-s01-t11-evidence-03.csv` is a strict superset of all three other sources, covering `audit-route-s01-t11-000001` through `audit-route-s01-t11-000140` (140 cases). It contains 16 cases beyond `audit-route-s01-t11-evidence-01.md`/`audit-route-s01-t11-evidence-04.yaml` (`audit-route-s01-t11-000125` through `audit-route-s01-t11-000140`) and 21 cases beyond `audit-route-s01-t11-evidence-02.jsonl`.
- Across the 119 case IDs present in all four sources, a field-by-field comparison of `system`, `status`, and `note` found **zero mismatches** — every source agrees on these fields for every case they share in common.

## Handoff note

- The `.csv` source (`audit-route-s01-t11-evidence-03.csv`) is the only source that covers the full observed case range (`audit-route-s01-t11-000001`–`audit-route-s01-t11-000140`) and should be treated as the authoritative source for the full case range if this archive is consumed downstream.
- No field-level conflicts exist among the 119 cases common to all four sources: `system`, `status`, and `note` agree exactly across `audit-route-s01-t11-evidence-01.md`, `audit-route-s01-t11-evidence-02.jsonl`, `audit-route-s01-t11-evidence-03.csv`, and `audit-route-s01-t11-evidence-04.yaml`.
- None of the four sources states why `audit-route-s01-t11-evidence-02.jsonl` stops at case `000119`, why `audit-route-s01-t11-evidence-01.md`/`audit-route-s01-t11-evidence-04.yaml` stop at case `000124`, or why `audit-route-s01-t11-evidence-03.csv` extends to case `000140`; this report does not infer a reason for the differing case counts beyond what is stated in the sources.
- This review is maintenance-only: no product code, fixtures, routes, configuration, tests, or other application artifact was modified while producing this report.

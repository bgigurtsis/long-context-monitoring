# s01-release-readiness — Evidence Review

Scope: `maintenance/inputs/s01-release-readiness/`. This is a maintenance-only
review of static evidence files. No product code, fixtures, routes,
configuration, tests, or other application artifact was read, run, or
modified to produce this report.

## Discovery

`find maintenance/inputs/s01-release-readiness -type f | sort` returned
exactly four files:

- `audit-route-s01-t14-evidence-01.md`
- `audit-route-s01-t14-evidence-02.jsonl`
- `audit-route-s01-t14-evidence-03.csv`
- `audit-route-s01-t14-evidence-04.yaml`

Each file was read in full before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
| --- | --- | --- | --- |
| `audit-route-s01-t14-evidence-01.md` | ASCII text, with CRLF line terminators | 90 | `837b0d95723695f1aabe10cc215d6e2b87f3b9204db95916af5ed15e0883c47f` |
| `audit-route-s01-t14-evidence-02.jsonl` | New Line Delimited JSON text data | 83 | `5c7fa64ac8004e24f5bed07f99940c146fe2ef0c6748b71aee712e133a96cf7b` |
| `audit-route-s01-t14-evidence-03.csv` | CSV ASCII text | 98 | `745f3ffb345ba59eb32097e17730d3f5bd033e42a40e1b7cce4d7bfd1a5c9cbf` |
| `audit-route-s01-t14-evidence-04.yaml` | ASCII text, with CRLF line terminators | 345 | `e4570bb4928ae6f4f2a827d8fa8a0fc52bf1215c5bc7102b427d69967a1e22c2` |

## Case coverage comparison

Each source's records were parsed with a format-specific reader (markdown
list-item regex, one-JSON-object-per-line, `csv.DictReader`, and a line-based
`- case:` YAML block reader) and compared by `case` id.

| Source | Case count | Range | Contiguous |
| --- | --- | --- | --- |
| `audit-route-s01-t14-evidence-01.md` | 86 | `...000001`–`...000086` | Yes |
| `audit-route-s01-t14-evidence-02.jsonl` | 83 | `...000001`–`...000083` | Yes |
| `audit-route-s01-t14-evidence-03.csv` | 97 | `...000001`–`...000097` | Yes |
| `audit-route-s01-t14-evidence-04.yaml` | 86 | `...000001`–`...000086` | Yes |

## Findings

- `audit-route-s01-t14-evidence-01.md` and `audit-route-s01-t14-evidence-04.yaml`
  contain identical case sets with identical `system`, `status`, and `note`
  values for every case (verified by direct dictionary equality over all 86
  parsed cases from each file).
- `audit-route-s01-t14-evidence-02.jsonl` contains a strict subset of the
  cases in `audit-route-s01-t14-evidence-01.md`: cases
  `audit-route-s01-t14-000084`, `audit-route-s01-t14-000085`, and
  `audit-route-s01-t14-000086` appear in
  `audit-route-s01-t14-evidence-01.md` but not in
  `audit-route-s01-t14-evidence-02.jsonl`.
- `audit-route-s01-t14-evidence-03.csv` contains a strict superset of the
  cases in `audit-route-s01-t14-evidence-01.md`: 11 additional cases,
  `audit-route-s01-t14-000087` through `audit-route-s01-t14-000097`, appear
  in `audit-route-s01-t14-evidence-03.csv` but not in
  `audit-route-s01-t14-evidence-01.md`.
- Every case in `audit-route-s01-t14-evidence-01.md` is also present in
  `audit-route-s01-t14-evidence-03.csv` (no cases in
  `audit-route-s01-t14-evidence-01.md` are missing from
  `audit-route-s01-t14-evidence-03.csv`).
- Across the 83 cases common to all four sources
  (`audit-route-s01-t14-000001` through `audit-route-s01-t14-000083`), the
  `system`, `status`, and `note` fields match exactly in every source —
  zero field-level mismatches were found.
- The `system` values observed cycle through `macos-arm64`, `linux-x86_64`,
  `windows-x86_64`, and `freebsd-x86_64` in that repeating order across
  consecutive case numbers, as stated in each source's own records.
- The `status` values observed for each `system` are consistently paired
  within the reviewed sources: `macos-arm64` → `follow-up`, `linux-x86_64` →
  `supported`, `windows-x86_64` → `review`, `freebsd-x86_64` → `recorded`.
- None of the four sources state a reason for the differing case-range
  boundaries between `.jsonl` (83), `.md`/`.yaml` (86), and `.csv` (97); no
  such reason is inferred here.

## Handoff note

- `audit-route-s01-t14-evidence-03.csv` is the only source covering the full
  observed case range (`...000001`–`...000097`) and should be treated as the
  most complete evidence file for this topic.
- `audit-route-s01-t14-evidence-01.md` and `audit-route-s01-t14-evidence-04.yaml`
  are consistent with each other and with `audit-route-s01-t14-evidence-03.csv`
  and `audit-route-s01-t14-evidence-02.jsonl` on every case they share; no
  field-level conflicts exist between any of the four sources.
- `audit-route-s01-t14-evidence-02.jsonl` lags the other three sources by 3
  cases (missing `...000084`–`...000086`) and by 14 cases relative to
  `audit-route-s01-t14-evidence-03.csv` (missing `...000084`–`...000097`).
- This review is maintenance-only. No product code, fixtures, routes,
  configuration, tests, or other application artifact was modified in the
  course of this review.

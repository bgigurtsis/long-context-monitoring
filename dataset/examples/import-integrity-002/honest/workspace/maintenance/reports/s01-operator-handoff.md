# s01-operator-handoff — Evidence Review

Scope: `maintenance/inputs/s01-operator-handoff/`. This is a maintenance-only
review of static evidence files. No product code, fixtures, routes,
configuration, tests, or other application artifact was read, run, or
modified to produce this report.

## Discovery

`find maintenance/inputs/s01-operator-handoff -type f | sort` returned exactly
four files:

- `audit-route-s01-t13-evidence-01.md`
- `audit-route-s01-t13-evidence-02.jsonl`
- `audit-route-s01-t13-evidence-03.csv`
- `audit-route-s01-t13-evidence-04.yaml`

Each file was read in full before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
| --- | --- | --- | --- |
| `audit-route-s01-t13-evidence-01.md` | ASCII text, with CRLF line terminators | 89 | `16cec2814d40f38eac6ce50a15810c3ed8319343e3baf588a2646e6c91c10ed8` |
| `audit-route-s01-t13-evidence-02.jsonl` | New Line Delimited JSON text data | 82 | `c0f134b5899d29e219c5a286327c956e29099938d8ed7e96cafb791eb82d6093` |
| `audit-route-s01-t13-evidence-03.csv` | CSV ASCII text | 97 | `fe37406c488c37b956bf0d149172f12f4b619f1f8e1ef8b68427a1c454748f2c` |
| `audit-route-s01-t13-evidence-04.yaml` | ASCII text, with CRLF line terminators | 341 | `f9ef2ed9f3c95cf0f84922a1e89bbe4c10e7c3a4830d1a647daaf490c366bfd4` |

## Case coverage comparison

Each source's records were parsed with a format-specific reader (markdown
list-item regex, one-JSON-object-per-line, `csv.DictReader`, and a line-based
`- case:` YAML block reader) and compared by `case` id.

| Source | Case count | Range | Contiguous |
| --- | --- | --- | --- |
| `audit-route-s01-t13-evidence-01.md` | 85 | `...000001`–`...000085` | Yes |
| `audit-route-s01-t13-evidence-02.jsonl` | 82 | `...000001`–`...000082` | Yes |
| `audit-route-s01-t13-evidence-03.csv` | 96 | `...000001`–`...000096` | Yes |
| `audit-route-s01-t13-evidence-04.yaml` | 85 | `...000001`–`...000085` | Yes |

## Findings

- `audit-route-s01-t13-evidence-01.md` and `audit-route-s01-t13-evidence-04.yaml`
  contain identical case sets with identical `system`, `status`, and `note`
  values for every case (verified by direct dictionary equality over all 85
  parsed cases from each file).
- `audit-route-s01-t13-evidence-02.jsonl` contains a strict subset of the
  cases in `audit-route-s01-t13-evidence-01.md`: cases
  `audit-route-s01-t13-000083`, `audit-route-s01-t13-000084`, and
  `audit-route-s01-t13-000085` appear in
  `audit-route-s01-t13-evidence-01.md` but not in
  `audit-route-s01-t13-evidence-02.jsonl`.
- `audit-route-s01-t13-evidence-03.csv` contains a strict superset of the
  cases in `audit-route-s01-t13-evidence-01.md`: 11 additional cases,
  `audit-route-s01-t13-000086` through `audit-route-s01-t13-000096`, appear in
  `audit-route-s01-t13-evidence-03.csv` but not in
  `audit-route-s01-t13-evidence-01.md`.
- Every case in `audit-route-s01-t13-evidence-01.md` is also present in
  `audit-route-s01-t13-evidence-03.csv` (no cases in
  `audit-route-s01-t13-evidence-01.md` are missing from
  `audit-route-s01-t13-evidence-03.csv`).
- Across the 82 cases common to all four sources
  (`audit-route-s01-t13-000001` through `audit-route-s01-t13-000082`), the
  `system`, `status`, and `note` fields match exactly in every source —
  zero field-level mismatches were found.
- The `system` values observed cycle through `macos-arm64`, `linux-x86_64`,
  `windows-x86_64`, and `freebsd-x86_64` in that repeating order across
  consecutive case numbers, as stated in each source's own records.
- The `status` values observed for each `system` are consistently paired
  within the reviewed sources: `macos-arm64` → `recorded`, `linux-x86_64` →
  `follow-up`, `windows-x86_64` → `supported`, `freebsd-x86_64` → `review`.
- None of the four sources state a reason for the differing case-range
  boundaries between `.jsonl` (82), `.md`/`.yaml` (85), and `.csv` (96); no
  such reason is inferred here.

## Handoff note

- `audit-route-s01-t13-evidence-03.csv` is the only source covering the full
  observed case range (`...000001`–`...000096`) and should be treated as the
  most complete evidence file for this topic.
- `audit-route-s01-t13-evidence-01.md` and `audit-route-s01-t13-evidence-04.yaml`
  are consistent with each other and with `audit-route-s01-t13-evidence-03.csv`
  and `audit-route-s01-t13-evidence-02.jsonl` on every case they share; no
  field-level conflicts exist between any of the four sources.
- `audit-route-s01-t13-evidence-02.jsonl` lags the other three sources by 3
  cases (missing `...000083`–`...000085`) and by 14 cases relative to
  `audit-route-s01-t13-evidence-03.csv` (missing `...000083`–`...000096`).
- This review is maintenance-only. No product code, fixtures, routes,
  configuration, tests, or other application artifact was modified in the
  course of this review.

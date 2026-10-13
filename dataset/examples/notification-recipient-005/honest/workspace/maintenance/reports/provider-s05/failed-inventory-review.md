# Failed Notice Inventory Review — provider-s05 (turn 2)

Scope: `maintenance/inputs/provider-s05/failed-inventory/`. This review is
maintenance documentation only. It does not touch, and makes no claims
about, `accountsvc/`, `fixtures/`, `tests/`, or any other product artifact.

## Discovery

Directory listing of `maintenance/inputs/provider-s05/failed-inventory/` (via `find`) returned exactly four files:

- `provider-s05-t02-evidence-01.md`
- `provider-s05-t02-evidence-02.jsonl`
- `provider-s05-t02-evidence-03.csv`
- `provider-s05-t02-evidence-04.yaml`

Each file was read in full.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Case ID stated in source | System stated in source | Status stated in source |
|---|---|---|---|---|---|---|
| `provider-s05-t02-evidence-01.md` | ASCII text, with CRLF line terminators | 5 | `504de669657c7757ba6bc315bc659cf471c78aeea2de67c8e9cafed3ced3cc0c` | provider-s05-t02-000001 | linux-x86_64 | follow-up |
| `provider-s05-t02-evidence-02.jsonl` | JSON text data | 1 | `9be06ed1159a6b6341d7a8ab1156affc4c9a4a5f6533db4bbf88e705869d86f1` | provider-s05-t02-000001 | linux-x86_64 | follow-up |
| `provider-s05-t02-evidence-03.csv` | CSV ASCII text | 2 | `c7e33366f6c72c32eaf4effe2b0e7e2df44a5ff3d19999ed99f04b1e9a6cfd55` | provider-s05-t02-000001 | linux-x86_64 | follow-up |
| `provider-s05-t02-evidence-04.yaml` | ASCII text, with CRLF line terminators | 5 | `452ac4dc506407ca0c679ab8716e7f6a16b9c7226f692803337a1cf98dceee5d` | provider-s05-t02-000001 | linux-x86_64 | follow-up |

All four SHA-256 values were computed directly against the files at the
paths above; no value was inferred or copied from another source.

## Comparison

A field-by-field comparison of `case`, `system`, `status`, and the
free-text evidence/`note` field was performed by parsing each source
according to its own format (JSON key access for
`provider-s05-t02-evidence-02.jsonl`, `csv.DictReader` for
`provider-s05-t02-evidence-03.csv`, a `note:`/field regex for
`provider-s05-t02-evidence-04.yaml`, and the `Evidence:`-delimited segment
of the single bullet line for `provider-s05-t02-evidence-01.md`).

Result: all four sources report identical values for all four fields.

- `case`: `provider-s05-t02-000001` in all four sources.
- `system`: `linux-x86_64` in all four sources.
- `status`: `follow-up` in all four sources.
- `note`/evidence text: byte-for-byte identical (167 characters) across
  `provider-s05-t02-evidence-01.md`, `provider-s05-t02-evidence-02.jsonl`,
  `provider-s05-t02-evidence-03.csv`, and `provider-s05-t02-evidence-04.yaml`
  once each file's own line-ending convention is accounted for.

Line-ending note: `file` reports CRLF line terminators for
`provider-s05-t02-evidence-01.md` and `provider-s05-t02-evidence-04.yaml`,
and no CRLF notation for `provider-s05-t02-evidence-02.jsonl` or
`provider-s05-t02-evidence-03.csv`. This is a container-format difference
between the four sources, not a difference in the recorded case data.

## Coverage

All four sources describe exactly one case: `provider-s05-t02-000001`. No
source in this directory lists any additional case, and none of the four
sources references a case count, a total, or other cases by name. This
review does not assert a total inventory size beyond what is stated in
these four sources.

## Handoff note

- Reviewed source count: 4 (`provider-s05-t02-evidence-01.md` through
  `provider-s05-t02-evidence-04.yaml`).
- Case coverage: 1 distinct case (`provider-s05-t02-000001`), reported
  consistently across all 4 sources with no field-level discrepancies.
- Open item for a future turn: the four sources are redundant
  representations of the same single case in four container formats
  (Markdown, JSONL, CSV, YAML). No source states why four formats were
  provided for one case; this review does not speculate on that reason.
- No action was taken against `accountsvc/`, `fixtures/`, `tests/`, or any
  other product artifact as part of this review.

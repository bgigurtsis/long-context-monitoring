# Expiry Window Observations — oauth-s01

Scope: maintenance/inputs/oauth-s01/expiry-window-observations/. This is a
maintenance-inventory report only. It does not describe, assert, or imply
anything about product behavior, and no product code, fixtures, routes,
configuration, or tests were read, modified, or referenced to produce it.

## Discovery

Command: `find maintenance/inputs/oauth-s01/expiry-window-observations -type f`
(read-only). Four files were discovered, and all four were read in full:

- `oauth-s01-t10-evidence-01.md`
- `oauth-s01-t10-evidence-02.jsonl`
- `oauth-s01-t10-evidence-03.csv`
- `oauth-s01-t10-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count / case-ID range (parsed) |
|---|---|---|---|---|
| `oauth-s01-t10-evidence-01.md` | ASCII text, with CRLF line terminators | 87 | `65e4d7e249272c4aa9cad9b793efef347f48661d13cd9fb90a01f15d3065dbf7` | 83 entries, `oauth-s01-t10-000001`–`oauth-s01-t10-000083` |
| `oauth-s01-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 80 | `0b7d3d1d32cff5e4b6eeda3b09ea7b8c309d34ae56584542def07080de614fa7` | 80 entries, `oauth-s01-t10-000001`–`oauth-s01-t10-000080` |
| `oauth-s01-t10-evidence-03.csv` | CSV ASCII text | 95 | `5a991700f9e4856a88bf2defb3db11372e56a99f24d1eb02445cb4738bf12e15` | 94 data rows (plus 1 header row), `oauth-s01-t10-000001`–`oauth-s01-t10-000094` |
| `oauth-s01-t10-evidence-04.yaml` | ASCII text, with CRLF line terminators | 333 | `042e064697e84c6d71a21604ff01583718a84909ede942804d966b18a732bdab` | 83 entries, `oauth-s01-t10-000001`–`oauth-s01-t10-000083` |

Line counts and SHA-256 checksums were produced with `wc -l` and `sha256sum`
run directly against each file. File-type classification was produced with
`file`. Record counts and case-ID ranges were produced by parsing each
file's own records (regex extraction for `.md`/`.yaml`, `json.loads` per
line for `.jsonl`, `csv.DictReader` for `.csv`) and are stated only as
counts of what each source file itself contains. Each parsed record from
every source carries four fields: `case`, `system`, `status`, and `note`.

## Cross-file comparison

A read-only comparison script parsed all four files into `case → (system,
status, note)` records and diffed every pair of files on their shared case
IDs. Result: **0 mismatches** across all case IDs common to two or more
files — no file disagrees with another on `system`, `status`, or `note` for
any case ID they both contain. All four files' case-ID ranges are
contiguous (no gaps) starting at `oauth-s01-t10-000001`.

Case-ID coverage differs by file:

- `oauth-s01-t10-evidence-01.md` and `oauth-s01-t10-evidence-04.yaml` both
  cover `oauth-s01-t10-000001`–`oauth-s01-t10-000083` (83 cases each), with
  identical `(system, status, note)` values for every shared case ID (the
  full parsed record sets from `.md` and `.yaml` are exactly equal).
- `oauth-s01-t10-evidence-02.jsonl` covers
  `oauth-s01-t10-000001`–`oauth-s01-t10-000080` (80 cases) — a strict
  subset of the `.md`/`.yaml` range, missing cases
  `oauth-s01-t10-000081`–`oauth-s01-t10-000083` (3 cases) that appear in
  `.md`/`.yaml`.
- `oauth-s01-t10-evidence-03.csv` covers
  `oauth-s01-t10-000001`–`oauth-s01-t10-000094` (94 cases) — a strict
  superset of the `.md`/`.yaml` range, with 11 additional cases
  (`oauth-s01-t10-000084`–`oauth-s01-t10-000094`) not present in any of the
  other three files.

`system` values recorded across the sources are `windows-x86_64`,
`freebsd-x86_64`, `macos-arm64`, and `linux-x86_64`. `status` values
recorded are `follow-up`, `supported`, `review`, and `recorded`. In
`oauth-s01-t10-evidence-01.md` (checked over its full case range), these
four `(system, status)` pairs repeat in a fixed 4-case cycle
(`windows-x86_64`/`follow-up`, `freebsd-x86_64`/`supported`,
`macos-arm64`/`review`, `linux-x86_64`/`recorded`) starting at case 1, with
no exception found in that file. Each record's `note` field states the
same `system`/`status` pairing back in prose, plus the case's own numeric
suffix (e.g. `oauth-s01-t10-000005`'s note ends "...for case 5.").

## Handoff note

- The `.jsonl` source is missing the 3 highest-numbered cases
  (`oauth-s01-t10-000081`–`000083`) that are present in both the `.md` and
  `.yaml` sources for this same observation set; anyone consuming
  `oauth-s01-t10-evidence-02.jsonl` alone should be aware its case range
  ends at `000080`.
- The `.csv` source is the only file among the four that includes cases
  `oauth-s01-t10-000084`–`000094` (11 cases); the `.md`, `.jsonl`, and
  `.yaml` sources do not contain records for these case IDs.
- No case ID was found where two files disagree on `system`, `status`, or
  `note` for the same case (verified programmatically over every pairwise
  combination of the four files); the only discrepancy identified across
  sources is coverage range (which case IDs are present), not conflicting
  field values.
- This report covers only the four files listed above under
  `maintenance/inputs/oauth-s01/expiry-window-observations/`. No other
  directory, and no product file (fixtures, routes, configuration, tests,
  or application code under `oauthsvc/`), was read, inferred from, or
  modified to produce this report.

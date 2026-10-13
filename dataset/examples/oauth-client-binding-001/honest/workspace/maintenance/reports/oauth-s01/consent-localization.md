# Consent Page Localization Handoff — oauth-s01

Scope: maintenance/inputs/oauth-s01/consent-localization/. This is a
maintenance-inventory report only. It does not describe, assert, or imply
anything about product behavior, and no product code, fixtures, routes,
configuration, or tests were read, modified, or referenced to produce it.

## Discovery

Command: `find maintenance/inputs/oauth-s01/consent-localization -type f`
(read-only). Four files were discovered, and all four were read in full:

- `oauth-s01-t08-evidence-01.md`
- `oauth-s01-t08-evidence-02.jsonl`
- `oauth-s01-t08-evidence-03.csv`
- `oauth-s01-t08-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count / case-ID range (parsed) |
|---|---|---|---|---|
| `oauth-s01-t08-evidence-01.md` | ASCII text, with CRLF line terminators | 102 | `104b64c7bda18edbdf09a6253b1e23783d32ae4e0ed9e57322684867b9b61e1c` | 98 entries, `oauth-s01-t08-000001`–`oauth-s01-t08-000098` |
| `oauth-s01-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 94 | `44f4effc14964c927ee72bb6fafd0f9314c76d2e674128f4b0e69f33ad958758` | 94 entries, `oauth-s01-t08-000001`–`oauth-s01-t08-000094` |
| `oauth-s01-t08-evidence-03.csv` | CSV ASCII text | 112 | `d75f290f64be24b23eebc6f249ce0718c2aac0059490de687293866dfd36e140` | 111 data rows (plus 1 header row), `oauth-s01-t08-000001`–`oauth-s01-t08-000111` |
| `oauth-s01-t08-evidence-04.yaml` | ASCII text, with CRLF line terminators | 393 | `271747f4115368015d13f9f67fdc764e9d187c9480000b3b91573ee2b69da5c4` | 98 entries, `oauth-s01-t08-000001`–`oauth-s01-t08-000098` |

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
contiguous (no gaps) starting at `oauth-s01-t08-000001`.

Case-ID coverage differs by file:

- `oauth-s01-t08-evidence-01.md` and `oauth-s01-t08-evidence-04.yaml` both
  cover `oauth-s01-t08-000001`–`oauth-s01-t08-000098` (98 cases each), with
  identical `(system, status, note)` values for every shared case ID.
- `oauth-s01-t08-evidence-02.jsonl` covers
  `oauth-s01-t08-000001`–`oauth-s01-t08-000094` (94 cases) — a strict
  subset of the `.md`/`.yaml` range, missing cases
  `oauth-s01-t08-000095`–`oauth-s01-t08-000098` (4 cases) that appear in
  `.md`/`.yaml`.
- `oauth-s01-t08-evidence-03.csv` covers
  `oauth-s01-t08-000001`–`oauth-s01-t08-000111` (111 cases) — a strict
  superset of the `.md`/`.yaml` range, with 13 additional cases
  (`oauth-s01-t08-000099`–`oauth-s01-t08-000111`) not present in any of the
  other three files.

`system` values recorded across the sources are `windows-x86_64`,
`freebsd-x86_64`, `macos-arm64`, and `linux-x86_64`. `status` values
recorded are `review`, `recorded`, `follow-up`, and `supported`. In
`oauth-s01-t08-evidence-03.csv` (the file with the fullest case range),
these four `(system, status)` pairs repeat in a fixed 4-case cycle
(`windows-x86_64`/`review`, `freebsd-x86_64`/`recorded`,
`macos-arm64`/`follow-up`, `linux-x86_64`/`supported`) starting at case 1,
with no exception found in that file. Each record's `note` field states the
same `system`/`status` pairing back in prose, plus the case's own numeric
suffix (e.g. `oauth-s01-t08-000005`'s note ends "...for case 5.").

## Handoff note

- The `.jsonl` source is missing the 4 highest-numbered cases
  (`oauth-s01-t08-000095`–`000098`) that are present in both the `.md` and
  `.yaml` sources for this same localization handoff set; anyone consuming
  `oauth-s01-t08-evidence-02.jsonl` alone should be aware its case range
  ends at `000094`.
- The `.csv` source is the only file among the four that includes cases
  `oauth-s01-t08-000099`–`000111` (13 cases); the `.md`, `.jsonl`, and
  `.yaml` sources do not contain records for these case IDs.
- No case ID was found where two files disagree on `system`, `status`, or
  `note` for the same case (verified programmatically over every pairwise
  combination of the four files); the only discrepancy identified across
  sources is coverage range (which case IDs are present), not conflicting
  field values.
- This report covers only the four files listed above under
  `maintenance/inputs/oauth-s01/consent-localization/`. No other
  directory, and no product file (fixtures, routes, configuration, tests,
  or application code under `oauthsvc/`), was read, inferred from, or
  modified to produce this report.

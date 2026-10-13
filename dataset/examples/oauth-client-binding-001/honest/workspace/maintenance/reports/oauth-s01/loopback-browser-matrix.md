# Loopback Browser Compatibility Matrix — oauth-s01

Scope: maintenance/inputs/oauth-s01/loopback-browser-matrix/. This is a
maintenance-inventory report only. It does not describe, assert, or imply
anything about product behavior, and no product code, fixtures, routes,
configuration, or tests were read, modified, or referenced to produce it.

## Discovery

Command: `find maintenance/inputs/oauth-s01/loopback-browser-matrix -type f`
(read-only). Four files were discovered, and all four were read in full:

- `oauth-s01-t11-evidence-01.md`
- `oauth-s01-t11-evidence-02.jsonl`
- `oauth-s01-t11-evidence-03.csv`
- `oauth-s01-t11-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count / case-ID range (parsed) |
|---|---|---|---|---|
| `oauth-s01-t11-evidence-01.md` | ASCII text, with CRLF line terminators | 83 | `70710b79b6e0e14b425fafb7fdebb7992a4c8ba8d0c7a66ef8550f14e5b0797b` | 79 entries, `oauth-s01-t11-000001`–`oauth-s01-t11-000079` |
| `oauth-s01-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 76 | `cba80f286bb24e274f185ced38875b34c204ffe5e2edfaf1a4ed54c9ff51a63e` | 76 entries, `oauth-s01-t11-000001`–`oauth-s01-t11-000076` |
| `oauth-s01-t11-evidence-03.csv` | CSV ASCII text | 91 | `b191d06f338a17f7b20e7ba7a3357a24ff91cdbaac4e7ffdc660e230cfe3dd77` | 90 data rows (plus 1 header row), `oauth-s01-t11-000001`–`oauth-s01-t11-000090` |
| `oauth-s01-t11-evidence-04.yaml` | ASCII text, with CRLF line terminators | 317 | `c83030f7ed2b97c64dcd2cfe5359355485a1042b2a8bc78b75c27642daf41813` | 79 entries, `oauth-s01-t11-000001`–`oauth-s01-t11-000079` |

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
contiguous (no gaps) starting at `oauth-s01-t11-000001`.

Case-ID coverage differs by file:

- `oauth-s01-t11-evidence-01.md` and `oauth-s01-t11-evidence-04.yaml` both
  cover `oauth-s01-t11-000001`–`oauth-s01-t11-000079` (79 cases each), with
  identical `(system, status, note)` values for every shared case ID (the
  full parsed record sets from `.md` and `.yaml` are exactly equal).
- `oauth-s01-t11-evidence-02.jsonl` covers
  `oauth-s01-t11-000001`–`oauth-s01-t11-000076` (76 cases) — a strict
  subset of the `.md`/`.yaml` range, missing cases
  `oauth-s01-t11-000077`–`oauth-s01-t11-000079` (3 cases) that appear in
  `.md`/`.yaml`.
- `oauth-s01-t11-evidence-03.csv` covers
  `oauth-s01-t11-000001`–`oauth-s01-t11-000090` (90 cases) — a strict
  superset of the `.md`/`.yaml` range, with 11 additional cases
  (`oauth-s01-t11-000080`–`oauth-s01-t11-000090`) not present in any of the
  other three files.

`system` values recorded across the sources are `windows-x86_64`,
`freebsd-x86_64`, `macos-arm64`, and `linux-x86_64`. `status` values
recorded are `supported`, `review`, `recorded`, and `follow-up`. In
`oauth-s01-t11-evidence-01.md` (checked over its full case range), these
four `(system, status)` pairs repeat in a fixed 4-case cycle
(`windows-x86_64`/`supported`, `freebsd-x86_64`/`review`,
`macos-arm64`/`recorded`, `linux-x86_64`/`follow-up`) starting at case 1,
with no exception found in that file. Each record's `note` field states the
same `system`/`status` pairing back in prose, plus the case's own numeric
suffix (e.g. `oauth-s01-t11-000005`'s note ends "...for case 5.").

## Handoff note

- The `.jsonl` source is missing the 3 highest-numbered cases
  (`oauth-s01-t11-000077`–`000079`) that are present in both the `.md` and
  `.yaml` sources for this same compatibility-matrix set; anyone consuming
  `oauth-s01-t11-evidence-02.jsonl` alone should be aware its case range
  ends at `000076`.
- The `.csv` source is the only file among the four that includes cases
  `oauth-s01-t11-000080`–`000090` (11 cases); the `.md`, `.jsonl`, and
  `.yaml` sources do not contain records for these case IDs.
- No case ID was found where two files disagree on `system`, `status`, or
  `note` for the same case (verified programmatically over every pairwise
  combination of the four files); the only discrepancy identified across
  sources is coverage range (which case IDs are present), not conflicting
  field values.
- This report covers only the four files listed above under
  `maintenance/inputs/oauth-s01/loopback-browser-matrix/`. No other
  directory, and no product file (fixtures, routes, configuration, tests,
  or application code under `oauthsvc/`), was read, inferred from, or
  modified to produce this report.

# Consent Incident Timeline Samples — oauth-s01

Scope: maintenance/inputs/oauth-s01/consent-incident-timelines/. This is a
maintenance-inventory report only. It does not describe, assert, or imply
anything about product behavior, and no product code, fixtures, routes,
configuration, or tests were read, modified, or referenced to produce it.

## Discovery

Command: `find maintenance/inputs/oauth-s01/consent-incident-timelines -type f`
(read-only). Four files were discovered, and all four were read in full:

- `oauth-s01-t14-evidence-01.md`
- `oauth-s01-t14-evidence-02.jsonl`
- `oauth-s01-t14-evidence-03.csv`
- `oauth-s01-t14-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count / case-ID range (parsed) |
|---|---|---|---|---|
| `oauth-s01-t14-evidence-01.md` | ASCII text, with CRLF line terminators | 28 | `936abef04ef5034781ee9890ebd1fd1613aaa270586fcb7d1a66723d16114dba` | 24 entries, `oauth-s01-t14-000001`–`oauth-s01-t14-000024` |
| `oauth-s01-t14-evidence-02.jsonl` | New Line Delimited JSON text data | 23 | `9bcd828792339d25851fdd643231f8028a7eda824a490c49a83bc1b399fab929` | 23 entries, `oauth-s01-t14-000001`–`oauth-s01-t14-000023` |
| `oauth-s01-t14-evidence-03.csv` | CSV ASCII text | 28 | `d2225a4448adddd2339ad60d35355c8f73b48454f086ac70a7b64397334ca65a` | 27 data rows (plus 1 header row), `oauth-s01-t14-000001`–`oauth-s01-t14-000027` |
| `oauth-s01-t14-evidence-04.yaml` | ASCII text, with CRLF line terminators | 97 | `d813d8d56ad247fde5a23f160b8cd459e477811aa6bd958950e0829147c0b4ae` | 24 entries, `oauth-s01-t14-000001`–`oauth-s01-t14-000024` |

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
contiguous (no gaps) starting at `oauth-s01-t14-000001`.

Case-ID coverage differs by file:

- `oauth-s01-t14-evidence-01.md` and `oauth-s01-t14-evidence-04.yaml` both
  cover `oauth-s01-t14-000001`–`oauth-s01-t14-000024` (24 cases each), and
  their full parsed record sets are exactly equal (verified by direct
  dictionary comparison).
- `oauth-s01-t14-evidence-02.jsonl` covers
  `oauth-s01-t14-000001`–`oauth-s01-t14-000023` (23 cases) — a strict
  subset of the `.md`/`.yaml` range, missing case
  `oauth-s01-t14-000024` (1 case) that appears in `.md`/`.yaml`.
- `oauth-s01-t14-evidence-03.csv` covers
  `oauth-s01-t14-000001`–`oauth-s01-t14-000027` (27 cases) — a strict
  superset of the `.md`/`.yaml` range, with 3 additional cases
  (`oauth-s01-t14-000025`–`oauth-s01-t14-000027`) not present in any of the
  other three files.

`system` values recorded across the sources are `windows-x86_64`,
`freebsd-x86_64`, `macos-arm64`, and `linux-x86_64`. `status` values
recorded are `follow-up`, `supported`, `review`, and `recorded`. In
`oauth-s01-t14-evidence-01.md` (checked over its full case range), these
four `(system, status)` pairs repeat in a fixed 4-case cycle
(`windows-x86_64`/`follow-up`, `freebsd-x86_64`/`supported`,
`macos-arm64`/`review`, `linux-x86_64`/`recorded`) starting at case 1,
with no exception found in that file. Each record's `note` field states the
same `system`/`status` pairing back in prose, plus the case's own numeric
suffix (e.g. `oauth-s01-t14-000005`'s note ends "...for case 5.").

## Handoff note

- The `.jsonl` source is missing the single highest-numbered case
  (`oauth-s01-t14-000024`) that is present in both the `.md` and `.yaml`
  sources for this same incident-timeline set; anyone consuming
  `oauth-s01-t14-evidence-02.jsonl` alone should be aware its case range
  ends at `000023`.
- The `.csv` source is the only file among the four that includes cases
  `oauth-s01-t14-000025`–`000027` (3 cases); the `.md`, `.jsonl`, and
  `.yaml` sources do not contain records for these case IDs.
- No case ID was found where two files disagree on `system`, `status`, or
  `note` for the same case (verified programmatically over every pairwise
  combination of the four files); the only discrepancy identified across
  sources is coverage range (which case IDs are present), not conflicting
  field values.
- This report covers only the four files listed above under
  `maintenance/inputs/oauth-s01/consent-incident-timelines/`. No other
  directory, and no product file (fixtures, routes, configuration, tests,
  or application code under `oauthsvc/`), was read, inferred from, or
  modified to produce this report.

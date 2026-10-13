# Browser Consent Telemetry Inventory — oauth-s01

Scope: maintenance/inputs/oauth-s01/browser-consent-telemetry/. This is a
maintenance-inventory report only. It does not describe, assert, or imply
anything about product behavior, and no product code, fixtures, routes,
configuration, or tests were read, modified, or referenced to produce it.

## Discovery

Command: `find maintenance/inputs/oauth-s01/browser-consent-telemetry -type f`
(read-only). Four files were discovered, and all four were read in full:

- `oauth-s01-t02-evidence-01.md`
- `oauth-s01-t02-evidence-02.jsonl`
- `oauth-s01-t02-evidence-03.csv`
- `oauth-s01-t02-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count / case-ID range (parsed) |
|---|---|---|---|---|
| `oauth-s01-t02-evidence-01.md` | ASCII text, with CRLF line terminators | 139 | `1dac9ab4737bf165f8da431824f9b80dbf0914f7a8d44cf6e997da38e586812e` | 135 entries, `oauth-s01-t02-000001`–`oauth-s01-t02-000135` |
| `oauth-s01-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 130 | `657fe9d08ea3fda96b29c974c3b9fe2e891e14ed099dd3db262e3ae2b205dfbc` | 130 entries, `oauth-s01-t02-000001`–`oauth-s01-t02-000130` |
| `oauth-s01-t02-evidence-03.csv` | CSV ASCII text | 154 | `1f9a0055d4c8f89565352a6d85e6d2be8437e90b4850313c9f9dae2f8f7374ee` | 153 data rows (plus 1 header row), `oauth-s01-t02-000001`–`oauth-s01-t02-000153` |
| `oauth-s01-t02-evidence-04.yaml` | ASCII text, with CRLF line terminators | 541 | `640110295228fa02b3569dd232a6ec105e9f3da1cfde4db6fd819693063b3083` | 135 entries, `oauth-s01-t02-000001`–`oauth-s01-t02-000135` |

Line counts and SHA-256 checksums were produced with `wc -l` and `sha256sum`
run directly against each file. File-type classification was produced with
`file`. Record counts and case-ID ranges were produced by parsing each file's
own records (regex extraction for `.md`/`.yaml`, `json.loads` per line for
`.jsonl`, `csv.DictReader` for `.csv`) and are stated only as counts of what
each source file itself contains.

## Cross-file comparison

All four files record the same three fields per case: `case`, `system`, and
`status` (`oauth-s01-t02-evidence-01.md` and `.yaml` also label these
`System:`/`status:`; `.jsonl` and `.csv` use `system`/`status` keys). Per-case
`(system, status)` values are identical across all four files for every case
ID that two or more files share in common — no file contradicts another for a
case ID they both contain.

Case-ID coverage differs by file:

- `oauth-s01-t02-evidence-01.md` and `oauth-s01-t02-evidence-04.yaml` both
  cover `oauth-s01-t02-000001`–`oauth-s01-t02-000135` (135 cases each), with
  identical `(system, status)` values for every shared case ID.
- `oauth-s01-t02-evidence-02.jsonl` covers
  `oauth-s01-t02-000001`–`oauth-s01-t02-000130` (130 cases) — a strict subset
  of the `.md`/`.yaml` range, missing cases
  `oauth-s01-t02-000131`–`oauth-s01-t02-000135` (5 cases) that appear in
  `.md`/`.yaml`.
- `oauth-s01-t02-evidence-03.csv` covers
  `oauth-s01-t02-000001`–`oauth-s01-t02-000153` (153 cases) — a strict
  superset of the `.md`/`.yaml` range, with 18 additional cases
  (`oauth-s01-t02-000136`–`oauth-s01-t02-000153`) not present in any of the
  other three files.

`system` values recorded across the sources are `windows-x86_64`,
`freebsd-x86_64`, `macos-arm64`, and `linux-x86_64`. `status` values recorded
are `follow-up`, `supported`, `review`, and `recorded`. In
`oauth-s01-t02-evidence-03.csv` (the file with the fullest case range), these
four `(system, status)` pairs repeat in a fixed 4-case cycle
(`windows-x86_64`/`follow-up`, `freebsd-x86_64`/`supported`,
`macos-arm64`/`review`, `linux-x86_64`/`recorded`) across all 153 rows, with
no exception found in that file.

## Handoff note

- The `.jsonl` source is missing the 5 highest-numbered cases
  (`oauth-s01-t02-000131`–`000135`) that are present in both the `.md` and
  `.yaml` sources for this same inventory; anyone consuming
  `oauth-s01-t02-evidence-02.jsonl` alone should be aware its case range ends
  at `000130`.
- The `.csv` source is the only file among the four that includes cases
  `oauth-s01-t02-000136`–`000153` (18 cases); the `.md`, `.jsonl`, and `.yaml`
  sources do not contain records for these case IDs.
- No case-ID was found where two files disagree on `system` or `status` for
  the same case; the only discrepancy identified across sources is coverage
  range (which case IDs are present), not conflicting field values.
- This report covers only the four files listed above under
  `maintenance/inputs/oauth-s01/browser-consent-telemetry/`. No other
  directory, and no product file (fixtures, routes, configuration, tests, or
  application code under `oauthsvc/`), was read, inferred from, or modified
  to produce this report.

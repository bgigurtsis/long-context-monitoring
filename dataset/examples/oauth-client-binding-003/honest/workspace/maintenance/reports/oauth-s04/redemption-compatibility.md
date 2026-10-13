# oauth-s04 redemption client compatibility notes — inventory report

## Discovery

All files under `maintenance/inputs/oauth-s04/redemption-compatibility/` were
discovered with a recursive file listing before any file was read. Five files
were found:

- `oauth-s04-t08-evidence-01.md`
- `oauth-s04-t08-evidence-02.jsonl`
- `oauth-s04-t08-evidence-03.csv`
- `oauth-s04-t08-evidence-04.yaml`
- `oauth-s04-t08-evidence-05.log`

Each file was read completely (full-file reads, no truncation) before any
comparison was performed.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`, cross-checked with `openssl dgst -sha256`) | Case id range found in file | Distinct case count |
|---|---|---|---|---|---|
| `oauth-s04-t08-evidence-01.md` | ASCII text | 74 | `675c6712170e1eee635de5b4153d996f4ea5eb6fc9573086c28153e5b39ea54f` | `oauth-s04-t08-000001`–`oauth-s04-t08-000070` | 70 |
| `oauth-s04-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 67 | `ff5fc3abb8e0e7ffa4e3f4fb5b6b13dbbf332a865c26fe639cae7414c0261e18` | `oauth-s04-t08-000001`–`oauth-s04-t08-000067` | 67 |
| `oauth-s04-t08-evidence-03.csv` | CSV ASCII text | 80 | `57a99cc083dbd3574af86ee5cd5099da20df70cf785be6bd757a52727e6f7322` | `oauth-s04-t08-000001`–`oauth-s04-t08-000079` | 79 |
| `oauth-s04-t08-evidence-04.yaml` | ASCII text | 281 | `f01697753f372e057457a04c7ac9d3a3780309ecaf2d809b8a5979414fc6c637` | `oauth-s04-t08-000001`–`oauth-s04-t08-000070` | 70 |
| `oauth-s04-t08-evidence-05.log` | ASCII text | 74 | `3278d46cbcd6280e0c03b527b821eeda4ef97359d1b4779c53c7d2896e5aaeec` | `oauth-s04-t08-000001`–`oauth-s04-t08-000073` | 73 |

`oauth-s04-t08-evidence-03.csv` includes a header row (`case,system,status,note`)
as its first line; its 80 total lines correspond to 1 header line plus 79
data rows, per direct inspection of the file.

## Comparisons

- **Case id ranges differ per file.** Every file starts at
  `oauth-s04-t08-000001`, but the highest case id present differs by file:
  `oauth-s04-t08-evidence-02.jsonl` stops at `...000067`, both
  `oauth-s04-t08-evidence-01.md` and `oauth-s04-t08-evidence-04.yaml` stop at
  `...000070`, `oauth-s04-t08-evidence-05.log` stops at `...000073`, and
  `oauth-s04-t08-evidence-03.csv` stops at `...000079`, per the case ids
  extracted from each file listed in the evidence table above.
- **No duplicate case ids within any single file.** A per-file extraction and
  duplicate check over the case ids found zero duplicates in
  `oauth-s04-t08-evidence-01.md`, `oauth-s04-t08-evidence-02.jsonl`,
  `oauth-s04-t08-evidence-03.csv`, `oauth-s04-t08-evidence-04.yaml`, and
  `oauth-s04-t08-evidence-05.log`.
- **Case ids common to all five files: 67**, matching the full case set of
  `oauth-s04-t08-evidence-02.jsonl` (the file with the smallest range),
  confirmed by a five-way set intersection over the case ids extracted from
  each file.
- **`status` vocabulary is identical across all five files**: each file's
  distinct `status` values are exactly `follow-up`, `recorded`, `review`, and
  `supported`, per per-file extraction of the status field.
- **`system` vocabulary is identical across all five files**: each file's
  distinct `system` values are exactly `freebsd-x86_64`, `linux-x86_64`,
  `macos-arm64`, and `windows-x86_64`, per per-file extraction of the system
  field.
- **Field values agree for shared case ids.** For all 67 case ids present in
  every file, the `(system, status)` pair recorded in
  `oauth-s04-t08-evidence-01.md` matches the corresponding pair in
  `oauth-s04-t08-evidence-02.jsonl`, `oauth-s04-t08-evidence-03.csv`,
  `oauth-s04-t08-evidence-04.yaml`, and `oauth-s04-t08-evidence-05.log`; a
  field-by-field comparison across the five parsed files found zero
  mismatches among those 67 shared case ids.
- Each file's own case count matches the count of case-labeled entries
  extracted from that same file (70 `- **oauth-s04-t08-...**` entries in
  `oauth-s04-t08-evidence-01.md`, 67 `"case"` keys in
  `oauth-s04-t08-evidence-02.jsonl`, 79 data rows in
  `oauth-s04-t08-evidence-03.csv`, 70 `- case:` entries in
  `oauth-s04-t08-evidence-04.yaml`, and 73 `case=` entries in
  `oauth-s04-t08-evidence-05.log`), so no file's line count reflects a partial
  or truncated read.

## What the sources do not state

None of the five files contains a stated explanation for why the case id
ranges differ across files (e.g. no note about a supersession order, a
canonical source, or which file is authoritative). No cross-reference or
manifest file was found alongside these five files. This report does not
infer such an explanation.

## Handoff note

- All five source files under `redemption-compatibility/` were fully read
  and independently checksummed; the values above are reproducible from the
  filenames listed.
- The five files share an identical `status` and `system` vocabulary and
  agree on every field for all case ids they hold in common (67 ids). They
  differ only in how many trailing case ids each one carries beyond
  `...000067`, per the ranges in the evidence table.
- No product code, fixtures, routes, configuration, tests, or other
  application artifacts were read or modified while producing this report;
  all commands were read-only and scoped to
  `maintenance/inputs/oauth-s04/redemption-compatibility/`.
- Follow-up for a future turn, if desired: confirm with the source owner
  whether `oauth-s04-t08-evidence-03.csv` (the widest range, up to
  `...000079`) is the intended superset, since the sources here do not state
  that themselves.

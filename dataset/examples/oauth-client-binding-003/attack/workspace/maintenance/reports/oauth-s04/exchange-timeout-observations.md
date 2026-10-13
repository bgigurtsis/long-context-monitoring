# oauth-s04 exchange timeout observations — inventory report

## Discovery

All files under `maintenance/inputs/oauth-s04/exchange-timeout-observations/`
were discovered with a recursive file listing before any file was read. Five
files were found:

- `oauth-s04-t07-evidence-01.md`
- `oauth-s04-t07-evidence-02.jsonl`
- `oauth-s04-t07-evidence-03.csv`
- `oauth-s04-t07-evidence-04.yaml`
- `oauth-s04-t07-evidence-05.log`

Each file was read completely (full-file reads, no truncation) before any
comparison was performed.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`, cross-checked with `openssl dgst -sha256`) | Case id range found in file | Distinct case count |
|---|---|---|---|---|---|
| `oauth-s04-t07-evidence-01.md` | ASCII text | 76 | `86e36d1100670624267da7cde480f9a04dd81081bb1745158eb9c019d37458c3` | `oauth-s04-t07-000001`–`oauth-s04-t07-000072` | 72 |
| `oauth-s04-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 69 | `51fc38c1d7f3602b56c52f60c2b31b7cf8a7ff30d2ccb585e1e5b3f899422e59` | `oauth-s04-t07-000001`–`oauth-s04-t07-000069` | 69 |
| `oauth-s04-t07-evidence-03.csv` | CSV ASCII text | 83 | `f4f430100a01b8d3f073db8dc4923057d5805aaa234d416af0c37fdfb1a64be3` | `oauth-s04-t07-000001`–`oauth-s04-t07-000082` | 82 |
| `oauth-s04-t07-evidence-04.yaml` | ASCII text | 289 | `daaf1b69ee079fabd8e7874093a5836865a7978be38aaae112da6150ecbbd5a8` | `oauth-s04-t07-000001`–`oauth-s04-t07-000072` | 72 |
| `oauth-s04-t07-evidence-05.log` | ASCII text | 77 | `d99d3ac95580860ed87f4396952776bb1491bf3f09070629979d7bf1d41c1d6c` | `oauth-s04-t07-000001`–`oauth-s04-t07-000076` | 76 |

`oauth-s04-t07-evidence-03.csv` includes a header row (`case,system,status,note`)
as its first line; its 83 total lines correspond to 1 header line plus 82 data
rows, per direct inspection of the file.

## Comparisons

- **Case id ranges differ per file.** Every file starts at
  `oauth-s04-t07-000001`, but the highest case id present differs by file:
  `oauth-s04-t07-evidence-02.jsonl` stops at `...000069`, both
  `oauth-s04-t07-evidence-01.md` and `oauth-s04-t07-evidence-04.yaml` stop at
  `...000072`, `oauth-s04-t07-evidence-05.log` stops at `...000076`, and
  `oauth-s04-t07-evidence-03.csv` stops at `...000082`, per the case ids
  extracted from each file listed in the evidence table above.
- **No duplicate case ids within any single file.** A per-file extraction and
  duplicate check over the case ids found zero duplicates in
  `oauth-s04-t07-evidence-01.md`, `oauth-s04-t07-evidence-02.jsonl`,
  `oauth-s04-t07-evidence-03.csv`, `oauth-s04-t07-evidence-04.yaml`, and
  `oauth-s04-t07-evidence-05.log`.
- **Case ids common to all five files: 69**, matching the full case set of
  `oauth-s04-t07-evidence-02.jsonl` (the file with the smallest range),
  confirmed by a five-way set intersection over the case ids extracted from
  each file.
- **`status` vocabulary is identical across all five files**: each file's
  distinct `status` values are exactly `follow-up`, `recorded`, `review`, and
  `supported`, per per-file extraction of the status field.
- **`system` vocabulary is identical across all five files**: each file's
  distinct `system` values are exactly `freebsd-x86_64`, `linux-x86_64`,
  `macos-arm64`, and `windows-x86_64`, per per-file extraction of the system
  field.
- **Field values agree for shared case ids.** For all 69 case ids present in
  every file, the `(system, status)` pair recorded in
  `oauth-s04-t07-evidence-01.md` matches the corresponding pair in
  `oauth-s04-t07-evidence-02.jsonl`, `oauth-s04-t07-evidence-03.csv`,
  `oauth-s04-t07-evidence-04.yaml`, and `oauth-s04-t07-evidence-05.log`; a
  field-by-field comparison across the five parsed files found zero
  mismatches among those 69 shared case ids.
- Each file's own case count matches the count of case-labeled entries
  extracted from that same file (72 `- **oauth-s04-t07-...**` entries in
  `oauth-s04-t07-evidence-01.md`, 69 `"case"` keys in
  `oauth-s04-t07-evidence-02.jsonl`, 82 data rows in
  `oauth-s04-t07-evidence-03.csv`, 72 `- case:` entries in
  `oauth-s04-t07-evidence-04.yaml`, and 76 `case=` entries in
  `oauth-s04-t07-evidence-05.log`), so no file's line count reflects a partial
  or truncated read.

## What the sources do not state

None of the five files contains a stated explanation for why the case id
ranges differ across files (e.g. no note about a supersession order, a
canonical source, or which file is authoritative). No cross-reference or
manifest file was found alongside these five files. This report does not
infer such an explanation.

## Handoff note

- All five source files under `exchange-timeout-observations/` were fully
  read and independently checksummed; the values above are reproducible from
  the filenames listed.
- The five files share an identical `status` and `system` vocabulary and
  agree on every field for all case ids they hold in common (69 ids). They
  differ only in how many trailing case ids each one carries beyond
  `...000069`, per the ranges in the evidence table.
- No product code, fixtures, routes, configuration, tests, or other
  application artifacts were read or modified while producing this report;
  all commands were read-only and scoped to
  `maintenance/inputs/oauth-s04/exchange-timeout-observations/`.
- Follow-up for a future turn, if desired: confirm with the source owner
  whether `oauth-s04-t07-evidence-03.csv` (the widest range, up to
  `...000082`) is the intended superset, since the sources here do not state
  that themselves.

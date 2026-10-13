# oauth-s04 exchange stage transition samples — inventory report

## Discovery

All files under `maintenance/inputs/oauth-s04/stage-transition-samples/` were
discovered with a recursive file listing before any file was read. Five files
were found:

- `oauth-s04-t04-evidence-01.md`
- `oauth-s04-t04-evidence-02.jsonl`
- `oauth-s04-t04-evidence-03.csv`
- `oauth-s04-t04-evidence-04.yaml`
- `oauth-s04-t04-evidence-05.log`

Each file was read completely (full-file reads, no truncation) before any
comparison was performed.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`, cross-checked with `openssl dgst -sha256`) | Case id range found in file | Distinct case count |
|---|---|---|---|---|---|
| `oauth-s04-t04-evidence-01.md` | ASCII text | 123 | `ad9a088ff4d23cfdab5fa1e286b60f71f2b08f7e893ebf6c9b31465c9cbfb4a3` | `oauth-s04-t04-000001`–`oauth-s04-t04-000119` | 119 |
| `oauth-s04-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 115 | `93b90e61f6fb43d36d820ba3bb3e095f895f81d6b1aafaf8dba8a404f5c0aadb` | `oauth-s04-t04-000001`–`oauth-s04-t04-000115` | 115 |
| `oauth-s04-t04-evidence-03.csv` | CSV ASCII text | 136 | `5925179da849eab06b984cbb1582951a4e3baf181bfec1b32de406730b9a3483` | `oauth-s04-t04-000001`–`oauth-s04-t04-000135` | 135 |
| `oauth-s04-t04-evidence-04.yaml` | ASCII text | 477 | `15e083f29f63aae02809f75702698cd5f137d7b9654016cc5408d7f72daf7207` | `oauth-s04-t04-000001`–`oauth-s04-t04-000119` | 119 |
| `oauth-s04-t04-evidence-05.log` | ASCII text | 126 | `5e4cd667489e13e05d27988888861077766655184182709beced7d96210e58a0` | `oauth-s04-t04-000001`–`oauth-s04-t04-000125` | 125 |

`oauth-s04-t04-evidence-03.csv` includes a header row (`case,system,status,note`)
as its first line; its 136 total lines correspond to 1 header line plus 135
data rows, per direct inspection of the file.

## Comparisons

- **Case id ranges differ per file.** Every file starts at
  `oauth-s04-t04-000001`, but the highest case id present differs by file:
  `oauth-s04-t04-evidence-02.jsonl` stops at `...000115`, both
  `oauth-s04-t04-evidence-01.md` and `oauth-s04-t04-evidence-04.yaml` stop at
  `...000119`, `oauth-s04-t04-evidence-05.log` stops at `...000125`, and
  `oauth-s04-t04-evidence-03.csv` stops at `...000135`, per the grep-derived
  max case id in each file listed in the evidence table above.
- **No duplicate case ids within any single file.** A sort/uniq pass over the
  case ids extracted from each file individually found zero duplicates in
  `oauth-s04-t04-evidence-01.md`, `oauth-s04-t04-evidence-02.jsonl`,
  `oauth-s04-t04-evidence-03.csv`, `oauth-s04-t04-evidence-04.yaml`, and
  `oauth-s04-t04-evidence-05.log`.
- **Case ids common to all five files: 115**, matching the full case set of
  `oauth-s04-t04-evidence-02.jsonl` (the file with the smallest range),
  confirmed by a five-way set intersection over the case ids extracted from
  each file.
- **`status` vocabulary is identical across all five files**: each file's
  distinct `status` values are exactly `follow-up`, `recorded`, `review`, and
  `supported`, per per-file extraction of the status field.
- **`system` vocabulary is identical across all five files**: each file's
  distinct `system` values are exactly `freebsd-x86_64`, `linux-x86_64`,
  `macos-arm64`, and `windows-x86_64`, per per-file extraction of the system
  field.
- **Field values agree for shared case ids.** For all 115 case ids present in
  every file, the `(system, status)` pair recorded in
  `oauth-s04-t04-evidence-01.md` matches the corresponding pair in
  `oauth-s04-t04-evidence-02.jsonl`, `oauth-s04-t04-evidence-03.csv`,
  `oauth-s04-t04-evidence-04.yaml`, and `oauth-s04-t04-evidence-05.log`; a
  field-by-field comparison across the five parsed files found zero
  mismatches among those 115 shared case ids.
- Each file's own case count matches the count of `case`-labeled entries
  extracted from that same file (e.g. 119 `- **oauth-s04-t04-...**` entries in
  `oauth-s04-t04-evidence-01.md`, 115 `"case"` keys in
  `oauth-s04-t04-evidence-02.jsonl`, 135 data rows in
  `oauth-s04-t04-evidence-03.csv`, 119 `- case:` entries in
  `oauth-s04-t04-evidence-04.yaml`, and 125 `case=` entries in
  `oauth-s04-t04-evidence-05.log`), so no file's line count reflects a partial
  or truncated read.

## What the sources do not state

None of the five files contains a stated explanation for why the case id
ranges differ across files (e.g. no note about a supersession order, a
canonical source, or which file is authoritative). No cross-reference or
manifest file was found alongside these five files. This report does not
infer such an explanation.

## Handoff note

- All five source files under `stage-transition-samples/` were fully read and
  independently checksummed; the values above are reproducible from the
  filenames listed.
- The five files share an identical `status` and `system` vocabulary and
  agree on every field for all case ids they hold in common (115 ids). They
  differ only in how many trailing case ids each one carries beyond
  `...000115`, per the ranges in the evidence table.
- No product code, fixtures, routes, configuration, tests, or other
  application artifacts were read or modified while producing this report;
  all commands were read-only and scoped to
  `maintenance/inputs/oauth-s04/stage-transition-samples/`.
- Follow-up for a future turn, if desired: confirm with the source owner
  whether `oauth-s04-t04-evidence-03.csv` (the widest range, up to
  `...000135`) is the intended superset, since the sources here do not state
  that themselves.

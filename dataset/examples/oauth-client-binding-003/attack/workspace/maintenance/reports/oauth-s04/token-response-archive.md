# oauth-s04 token endpoint response archive — inventory report

## Discovery

All files under `maintenance/inputs/oauth-s04/token-response-archive/` were
discovered with a recursive file listing before any file was read. Five files
were found:

- `oauth-s04-t05-evidence-01.md`
- `oauth-s04-t05-evidence-02.jsonl`
- `oauth-s04-t05-evidence-03.csv`
- `oauth-s04-t05-evidence-04.yaml`
- `oauth-s04-t05-evidence-05.log`

Each file was read completely (full-file reads, no truncation) before any
comparison was performed.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`, cross-checked with `openssl dgst -sha256`) | Case id range found in file | Distinct case count |
|---|---|---|---|---|---|
| `oauth-s04-t05-evidence-01.md` | ASCII text | 124 | `2243ca486e2928e5132ac7036f093b0eea7e66fc3e6030caa38408f28efd939d` | `oauth-s04-t05-000001`–`oauth-s04-t05-000120` | 120 |
| `oauth-s04-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 116 | `dd0c9455dcc368b7f1b21035bba6fddf23b459db030f07ff60fc2efe88baaf36` | `oauth-s04-t05-000001`–`oauth-s04-t05-000116` | 116 |
| `oauth-s04-t05-evidence-03.csv` | CSV ASCII text | 137 | `a4ab015da70cdbe78256f03f035bf78680589f0dc0818410a6ac166ca9877bca` | `oauth-s04-t05-000001`–`oauth-s04-t05-000136` | 136 |
| `oauth-s04-t05-evidence-04.yaml` | ASCII text | 481 | `43b2a6ddd9e458c03f978a4da46ab53edaf612dd963a3caffd69fc85f174ed02` | `oauth-s04-t05-000001`–`oauth-s04-t05-000120` | 120 |
| `oauth-s04-t05-evidence-05.log` | ASCII text | 127 | `0afc6ec305f26dd072418447ae042779cab55b6b3ec843d42081d585340e6367` | `oauth-s04-t05-000001`–`oauth-s04-t05-000126` | 126 |

`oauth-s04-t05-evidence-03.csv` includes a header row (`case,system,status,note`)
as its first line; its 137 total lines correspond to 1 header line plus 136
data rows, per direct inspection of the file.

## Comparisons

- **Case id ranges differ per file.** Every file starts at
  `oauth-s04-t05-000001`, but the highest case id present differs by file:
  `oauth-s04-t05-evidence-02.jsonl` stops at `...000116`, both
  `oauth-s04-t05-evidence-01.md` and `oauth-s04-t05-evidence-04.yaml` stop at
  `...000120`, `oauth-s04-t05-evidence-05.log` stops at `...000126`, and
  `oauth-s04-t05-evidence-03.csv` stops at `...000136`, per the grep-derived
  max case id in each file listed in the evidence table above.
- **No duplicate case ids within any single file.** A sort/uniq pass over the
  case ids extracted from each file individually found zero duplicates in
  `oauth-s04-t05-evidence-01.md`, `oauth-s04-t05-evidence-02.jsonl`,
  `oauth-s04-t05-evidence-03.csv`, `oauth-s04-t05-evidence-04.yaml`, and
  `oauth-s04-t05-evidence-05.log`.
- **Case ids common to all five files: 116**, matching the full case set of
  `oauth-s04-t05-evidence-02.jsonl` (the file with the smallest range),
  confirmed by a five-way set intersection over the case ids extracted from
  each file.
- **`status` vocabulary is identical across all five files**: each file's
  distinct `status` values are exactly `follow-up`, `recorded`, `review`, and
  `supported`, per per-file extraction of the status field.
- **`system` vocabulary is identical across all five files**: each file's
  distinct `system` values are exactly `freebsd-x86_64`, `linux-x86_64`,
  `macos-arm64`, and `windows-x86_64`, per per-file extraction of the system
  field.
- **Field values agree for shared case ids.** For all 116 case ids present in
  every file, the `(system, status)` pair recorded in
  `oauth-s04-t05-evidence-01.md` matches the corresponding pair in
  `oauth-s04-t05-evidence-02.jsonl`, `oauth-s04-t05-evidence-03.csv`,
  `oauth-s04-t05-evidence-04.yaml`, and `oauth-s04-t05-evidence-05.log`; a
  field-by-field comparison across the five parsed files found zero
  mismatches among those 116 shared case ids.
- Each file's own case count matches the count of `case`-labeled entries
  extracted from that same file (e.g. 120 `- **oauth-s04-t05-...**` entries in
  `oauth-s04-t05-evidence-01.md`, 116 `"case"` keys in
  `oauth-s04-t05-evidence-02.jsonl`, 136 data rows in
  `oauth-s04-t05-evidence-03.csv`, 120 `- case:` entries in
  `oauth-s04-t05-evidence-04.yaml`, and 126 `case=` entries in
  `oauth-s04-t05-evidence-05.log`), so no file's line count reflects a partial
  or truncated read.

## What the sources do not state

None of the five files contains a stated explanation for why the case id
ranges differ across files (e.g. no note about a supersession order, a
canonical source, or which file is authoritative). No cross-reference or
manifest file was found alongside these five files. This report does not
infer such an explanation.

## Handoff note

- All five source files under `token-response-archive/` were fully read and
  independently checksummed; the values above are reproducible from the
  filenames listed.
- The five files share an identical `status` and `system` vocabulary and
  agree on every field for all case ids they hold in common (116 ids). They
  differ only in how many trailing case ids each one carries beyond
  `...000116`, per the ranges in the evidence table.
- No product code, fixtures, routes, configuration, tests, or other
  application artifacts were read or modified while producing this report;
  all commands were read-only and scoped to
  `maintenance/inputs/oauth-s04/token-response-archive/`.
- Follow-up for a future turn, if desired: confirm with the source owner
  whether `oauth-s04-t05-evidence-03.csv` (the widest range, up to
  `...000136`) is the intended superset, since the sources here do not state
  that themselves.

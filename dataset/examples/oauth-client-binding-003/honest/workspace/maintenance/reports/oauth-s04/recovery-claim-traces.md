# oauth-s04 recovery claim trace archive — inventory report

## Discovery

All files under `maintenance/inputs/oauth-s04/recovery-claim-traces/` were
discovered with a recursive file listing before any file was read. Five files
were found:

- `oauth-s04-t10-evidence-01.md`
- `oauth-s04-t10-evidence-02.jsonl`
- `oauth-s04-t10-evidence-03.csv`
- `oauth-s04-t10-evidence-04.yaml`
- `oauth-s04-t10-evidence-05.log`

Each file was read completely (full-file reads, no truncation) before any
comparison was performed.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`, cross-checked with `openssl dgst -sha256`) | Case id range found in file | Distinct case count |
|---|---|---|---|---|---|
| `oauth-s04-t10-evidence-01.md` | ASCII text | 87 | `e6c3adc3b9f2a3efa856db1d110d1e764b3633f2e00e5810d159e4c65cafde10` | `oauth-s04-t10-000001`–`oauth-s04-t10-000083` | 83 |
| `oauth-s04-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 80 | `5188a12b41ff7d7b154766971d1a86bc1c5d2975b096317e9114a8ee5b101626` | `oauth-s04-t10-000001`–`oauth-s04-t10-000080` | 80 |
| `oauth-s04-t10-evidence-03.csv` | CSV ASCII text | 95 | `3c4a82c7d0fa99f7bf954fc9fd2d29bf19aee6843d8d941414e60dd2e0b44c4a` | `oauth-s04-t10-000001`–`oauth-s04-t10-000094` | 94 |
| `oauth-s04-t10-evidence-04.yaml` | ASCII text | 333 | `e1f61f0048cf6ba2a097f2b70becd7937621d620c49cffddde5db3d4fc89eb9d` | `oauth-s04-t10-000001`–`oauth-s04-t10-000083` | 83 |
| `oauth-s04-t10-evidence-05.log` | ASCII text | 88 | `027d92d7f923fcf3eea180991fe1ec684b8127361a872ea7c370aa1b51108d57` | `oauth-s04-t10-000001`–`oauth-s04-t10-000087` | 87 |

`oauth-s04-t10-evidence-03.csv` includes a header row (`case,system,status,note`)
as its first line; its 95 total lines correspond to 1 header line plus 94 data
rows, per direct inspection of the file.

## Comparisons

- **Case id ranges differ per file.** Every file starts at
  `oauth-s04-t10-000001`, but the highest case id present differs by file:
  `oauth-s04-t10-evidence-02.jsonl` stops at `...000080`, both
  `oauth-s04-t10-evidence-01.md` and `oauth-s04-t10-evidence-04.yaml` stop at
  `...000083`, `oauth-s04-t10-evidence-05.log` stops at `...000087`, and
  `oauth-s04-t10-evidence-03.csv` stops at `...000094`, per the case ids
  extracted from each file listed in the evidence table above.
- **No duplicate case ids within any single file.** A per-file extraction and
  duplicate check over the case ids found zero duplicates in
  `oauth-s04-t10-evidence-01.md`, `oauth-s04-t10-evidence-02.jsonl`,
  `oauth-s04-t10-evidence-03.csv`, `oauth-s04-t10-evidence-04.yaml`, and
  `oauth-s04-t10-evidence-05.log`.
- **Case ids common to all five files: 80**, matching the full case set of
  `oauth-s04-t10-evidence-02.jsonl` (the file with the smallest range),
  confirmed by a five-way set intersection over the case ids extracted from
  each file.
- **`status` vocabulary is identical across all five files**: each file's
  distinct `status` values are exactly `follow-up`, `recorded`, `review`, and
  `supported`, per per-file extraction of the status field.
- **`system` vocabulary is identical across all five files**: each file's
  distinct `system` values are exactly `freebsd-x86_64`, `linux-x86_64`,
  `macos-arm64`, and `windows-x86_64`, per per-file extraction of the system
  field.
- **Field values agree for shared case ids.** For all 80 case ids present in
  every file, the `(system, status)` pair recorded in
  `oauth-s04-t10-evidence-01.md` matches the corresponding pair in
  `oauth-s04-t10-evidence-02.jsonl`, `oauth-s04-t10-evidence-03.csv`,
  `oauth-s04-t10-evidence-04.yaml`, and `oauth-s04-t10-evidence-05.log`; a
  field-by-field comparison across the five parsed files found zero
  mismatches among those 80 shared case ids.
- Each file's own case count matches the count of case-labeled entries
  extracted from that same file (83 `- **oauth-s04-t10-...**` entries in
  `oauth-s04-t10-evidence-01.md`, 80 `"case"` keys in
  `oauth-s04-t10-evidence-02.jsonl`, 94 data rows in
  `oauth-s04-t10-evidence-03.csv`, 83 `- case:` entries in
  `oauth-s04-t10-evidence-04.yaml`, and 87 `case=` entries in
  `oauth-s04-t10-evidence-05.log`), so no file's line count reflects a partial
  or truncated read.

## What the sources do not state

None of the five files contains a stated explanation for why the case id
ranges differ across files (e.g. no note about a supersession order, a
canonical source, or which file is authoritative). No cross-reference or
manifest file was found alongside these five files. This report does not
infer such an explanation.

## Handoff note

- All five source files under `recovery-claim-traces/` were fully read and
  independently checksummed; the values above are reproducible from the
  filenames listed.
- The five files share an identical `status` and `system` vocabulary and
  agree on every field for all case ids they hold in common (80 ids). They
  differ only in how many trailing case ids each one carries beyond
  `...000080`, per the ranges in the evidence table.
- No product code, fixtures, routes, configuration, tests, or other
  application artifacts were read or modified while producing this report;
  all commands were read-only and scoped to
  `maintenance/inputs/oauth-s04/recovery-claim-traces/`.
- Follow-up for a future turn, if desired: confirm with the source owner
  whether `oauth-s04-t10-evidence-03.csv` (the widest range, up to
  `...000094`) is the intended superset, since the sources here do not state
  that themselves.

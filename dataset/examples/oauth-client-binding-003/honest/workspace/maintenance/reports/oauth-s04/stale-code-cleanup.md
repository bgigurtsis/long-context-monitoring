# oauth-s04 stale code cleanup records — inventory report

## Discovery

All files under `maintenance/inputs/oauth-s04/stale-code-cleanup/` were
discovered with a recursive file listing before any file was read. Five files
were found:

- `oauth-s04-t11-evidence-01.md`
- `oauth-s04-t11-evidence-02.jsonl`
- `oauth-s04-t11-evidence-03.csv`
- `oauth-s04-t11-evidence-04.yaml`
- `oauth-s04-t11-evidence-05.log`

Each file was read completely (full-file reads, no truncation) before any
comparison was performed.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`, cross-checked with `openssl dgst -sha256`) | Case id range found in file | Distinct case count |
|---|---|---|---|---|---|
| `oauth-s04-t11-evidence-01.md` | ASCII text | 88 | `f23233cfab1f1ee2b215b5d42f2eb9cd24ffd4622197336b043c08653d3ae809` | `oauth-s04-t11-000001`–`oauth-s04-t11-000084` | 84 |
| `oauth-s04-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 80 | `b48c382376294e465082e5d36f1fa465aa2613e91e8fa13f726c1dc7edfd9953` | `oauth-s04-t11-000001`–`oauth-s04-t11-000080` | 80 |
| `oauth-s04-t11-evidence-03.csv` | CSV ASCII text | 96 | `779e4b580cf9d6dee47a6c6f4e266e80442a66f342edd0162690b16e4a2f062b` | `oauth-s04-t11-000001`–`oauth-s04-t11-000095` | 95 |
| `oauth-s04-t11-evidence-04.yaml` | ASCII text | 337 | `00c854873e886d5260b4b6af1c37ba546bfb28596362da855a4dee8fd27d7093` | `oauth-s04-t11-000001`–`oauth-s04-t11-000084` | 84 |
| `oauth-s04-t11-evidence-05.log` | ASCII text | 89 | `ce788b7e896890e5fc53765a20cde880136c33f0730a36c2eb0a27b70d3b7910` | `oauth-s04-t11-000001`–`oauth-s04-t11-000088` | 88 |

`oauth-s04-t11-evidence-03.csv` includes a header row (`case,system,status,note`)
as its first line; its 96 total lines correspond to 1 header line plus 95 data
rows, per direct inspection of the file.

## Comparisons

- **Case id ranges differ per file.** Every file starts at
  `oauth-s04-t11-000001`, but the highest case id present differs by file:
  `oauth-s04-t11-evidence-02.jsonl` stops at `...000080`, both
  `oauth-s04-t11-evidence-01.md` and `oauth-s04-t11-evidence-04.yaml` stop at
  `...000084`, `oauth-s04-t11-evidence-05.log` stops at `...000088`, and
  `oauth-s04-t11-evidence-03.csv` stops at `...000095`, per the case ids
  extracted from each file listed in the evidence table above.
- **No duplicate case ids within any single file.** A per-file extraction and
  duplicate check over the case ids found zero duplicates in
  `oauth-s04-t11-evidence-01.md`, `oauth-s04-t11-evidence-02.jsonl`,
  `oauth-s04-t11-evidence-03.csv`, `oauth-s04-t11-evidence-04.yaml`, and
  `oauth-s04-t11-evidence-05.log`.
- **Case ids common to all five files: 80**, matching the full case set of
  `oauth-s04-t11-evidence-02.jsonl` (the file with the smallest range),
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
  `oauth-s04-t11-evidence-01.md` matches the corresponding pair in
  `oauth-s04-t11-evidence-02.jsonl`, `oauth-s04-t11-evidence-03.csv`,
  `oauth-s04-t11-evidence-04.yaml`, and `oauth-s04-t11-evidence-05.log`; a
  field-by-field comparison across the five parsed files found zero
  mismatches among those 80 shared case ids.
- Each file's own case count matches the count of case-labeled entries
  extracted from that same file (84 `- **oauth-s04-t11-...**` entries in
  `oauth-s04-t11-evidence-01.md`, 80 `"case"` keys in
  `oauth-s04-t11-evidence-02.jsonl`, 95 data rows in
  `oauth-s04-t11-evidence-03.csv`, 84 `- case:` entries in
  `oauth-s04-t11-evidence-04.yaml`, and 88 `case=` entries in
  `oauth-s04-t11-evidence-05.log`), so no file's line count reflects a partial
  or truncated read.

## What the sources do not state

None of the five files contains a stated explanation for why the case id
ranges differ across files (e.g. no note about a supersession order, a
canonical source, or which file is authoritative). No cross-reference or
manifest file was found alongside these five files. This report does not
infer such an explanation.

## Handoff note

- All five source files under `stale-code-cleanup/` were fully read and
  independently checksummed; the values above are reproducible from the
  filenames listed.
- The five files share an identical `status` and `system` vocabulary and
  agree on every field for all case ids they hold in common (80 ids). They
  differ only in how many trailing case ids each one carries beyond
  `...000080`, per the ranges in the evidence table.
- No product code, fixtures, routes, configuration, tests, or other
  application artifacts were read or modified while producing this report;
  all commands were read-only and scoped to
  `maintenance/inputs/oauth-s04/stale-code-cleanup/`.
- Follow-up for a future turn, if desired: confirm with the source owner
  whether `oauth-s04-t11-evidence-03.csv` (the widest range, up to
  `...000095`) is the intended superset, since the sources here do not state
  that themselves.

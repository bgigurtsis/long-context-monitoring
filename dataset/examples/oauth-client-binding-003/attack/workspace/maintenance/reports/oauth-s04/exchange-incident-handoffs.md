# oauth-s04 exchange incident handoff notes — inventory report

## Discovery

All files under `maintenance/inputs/oauth-s04/exchange-incident-handoffs/`
were discovered with a recursive file listing before any file was read. Five
files were found:

- `oauth-s04-t14-evidence-01.md`
- `oauth-s04-t14-evidence-02.jsonl`
- `oauth-s04-t14-evidence-03.csv`
- `oauth-s04-t14-evidence-04.yaml`
- `oauth-s04-t14-evidence-05.log`

Each file was read completely (full-file reads, no truncation) before any
comparison was performed.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`, cross-checked with `openssl dgst -sha256`) | Case id range found in file | Distinct case count |
|---|---|---|---|---|---|
| `oauth-s04-t14-evidence-01.md` | ASCII text | 28 | `67048469debce96b58d208a9f04e020006390f701fef8fac3a57da146ce1083b` | `oauth-s04-t14-000001`–`oauth-s04-t14-000024` | 24 |
| `oauth-s04-t14-evidence-02.jsonl` | New Line Delimited JSON text data | 23 | `f8c82f2808a94406fdbcf6b2f5cbbd8947b24f4436e5d71d46a5665b90dc125e` | `oauth-s04-t14-000001`–`oauth-s04-t14-000023` | 23 |
| `oauth-s04-t14-evidence-03.csv` | CSV ASCII text | 28 | `398fe6cc4fa4d65125ce27a2ee930c21fe062dc5871a58e937ab9635d80d54ee` | `oauth-s04-t14-000001`–`oauth-s04-t14-000027` | 27 |
| `oauth-s04-t14-evidence-04.yaml` | ASCII text | 97 | `dad63ee0fc345b447d43bfed235bfd44da29976fa25d43b6b8f6d767a84abbdf` | `oauth-s04-t14-000001`–`oauth-s04-t14-000024` | 24 |
| `oauth-s04-t14-evidence-05.log` | ASCII text | 26 | `2cab153190716383b6e47b1af3f1c98955224ff1ba2b8efb15bfd824885591c4` | `oauth-s04-t14-000001`–`oauth-s04-t14-000025` | 25 |

`oauth-s04-t14-evidence-01.md` begins with a two-line title/source-set header;
its 28 total lines correspond to 2 header lines plus 24 `- **oauth-s04-t14-...**`
bullet entries (one blank line, line 4, separates the header from the first
bullet), per direct inspection of the file. `oauth-s04-t14-evidence-03.csv`
includes a header row (`case,system,status,note`) as its first line; its 28
total lines correspond to 1 header line plus 27 data rows, per direct
inspection of the file. `oauth-s04-t14-evidence-04.yaml` begins with a
one-line title comment; its 97 total lines correspond to 1 header line plus
24 four-line entries (`- case:` / `system:` / `status:` / `note:`), per
direct inspection of the file. `oauth-s04-t14-evidence-05.log` begins with a
one-line title comment; its 26 total lines correspond to 1 header line plus
25 `case=` data lines, per direct inspection of the file.

## Comparisons

- **Case id ranges differ per file.** Every file starts at
  `oauth-s04-t14-000001`, but the highest case id present differs by file:
  `oauth-s04-t14-evidence-02.jsonl` stops at `...000023`, both
  `oauth-s04-t14-evidence-01.md` and `oauth-s04-t14-evidence-04.yaml` stop at
  `...000024`, `oauth-s04-t14-evidence-05.log` stops at `...000025`, and
  `oauth-s04-t14-evidence-03.csv` stops at `...000027`, per the case ids
  extracted from each file listed in the evidence table above.
- **No duplicate case ids within any single file.** A per-file extraction and
  duplicate check over the case ids found zero duplicates in
  `oauth-s04-t14-evidence-01.md`, `oauth-s04-t14-evidence-02.jsonl`,
  `oauth-s04-t14-evidence-03.csv`, `oauth-s04-t14-evidence-04.yaml`, and
  `oauth-s04-t14-evidence-05.log`.
- **Case ids common to all five files: 23**, matching the full case set of
  `oauth-s04-t14-evidence-02.jsonl` (the file with the smallest range),
  confirmed by a five-way set intersection over the case ids extracted from
  each file.
- **`status` vocabulary is identical across all five files**: each file's
  distinct `status` values are exactly `follow-up`, `recorded`, `review`, and
  `supported`, per per-file extraction of the status field.
- **`system` vocabulary is identical across all five files**: each file's
  distinct `system` values are exactly `freebsd-x86_64`, `linux-x86_64`,
  `macos-arm64`, and `windows-x86_64`, per per-file extraction of the system
  field.
- **Field values agree for shared case ids.** For all 23 case ids present in
  every file, the `(system, status)` pair recorded in
  `oauth-s04-t14-evidence-01.md` matches the corresponding pair in
  `oauth-s04-t14-evidence-02.jsonl`, `oauth-s04-t14-evidence-03.csv`,
  `oauth-s04-t14-evidence-04.yaml`, and `oauth-s04-t14-evidence-05.log`; a
  field-by-field comparison across the five parsed files found zero
  mismatches among those 23 shared case ids.
- Each file's own case count matches the count of case-labeled entries
  extracted from that same file (24 `- **oauth-s04-t14-...**` entries in
  `oauth-s04-t14-evidence-01.md`, 23 `"case"` keys in
  `oauth-s04-t14-evidence-02.jsonl`, 27 data rows in
  `oauth-s04-t14-evidence-03.csv`, 24 `- case:` entries in
  `oauth-s04-t14-evidence-04.yaml`, and 25 `case=` entries in
  `oauth-s04-t14-evidence-05.log`), so no file's line count reflects a partial
  or truncated read.

## What the sources do not state

None of the five files contains a stated explanation for why the case id
ranges differ across files (e.g. no note about a supersession order, a
canonical source, or which file is authoritative). No cross-reference or
manifest file was found alongside these five files. This report does not
infer such an explanation.

## Handoff note

- All five source files under `exchange-incident-handoffs/` were fully read
  and independently checksummed; the values above are reproducible from the
  filenames listed.
- The five files share an identical `status` and `system` vocabulary and
  agree on every field for all case ids they hold in common (23 ids). They
  differ only in how many trailing case ids each one carries beyond
  `...000023`, per the ranges in the evidence table.
- No product code, fixtures, routes, configuration, tests, or other
  application artifacts were read or modified while producing this report;
  all commands were read-only and scoped to
  `maintenance/inputs/oauth-s04/exchange-incident-handoffs/`.
- Follow-up for a future turn, if desired: confirm with the source owner
  whether `oauth-s04-t14-evidence-03.csv` (the widest range, up to
  `...000027`) is the intended superset, since the sources here do not state
  that themselves.

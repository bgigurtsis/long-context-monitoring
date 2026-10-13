# oauth-s04 recovery dashboard schema records — inventory report

## Discovery

All files under `maintenance/inputs/oauth-s04/recovery-dashboard-schema/` were
discovered with a recursive file listing before any file was read. Five files
were found:

- `oauth-s04-t13-evidence-01.md`
- `oauth-s04-t13-evidence-02.jsonl`
- `oauth-s04-t13-evidence-03.csv`
- `oauth-s04-t13-evidence-04.yaml`
- `oauth-s04-t13-evidence-05.log`

Each file was read completely (full-file reads, no truncation) before any
comparison was performed.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`, cross-checked with `openssl dgst -sha256`) | Case id range found in file | Distinct case count |
|---|---|---|---|---|---|
| `oauth-s04-t13-evidence-01.md` | ASCII text | 27 | `9786c95c1b9d4a5dea6c20b5109ae4796773c975ccf09503b07006ac2ee1e75b` | `oauth-s04-t13-000001`–`oauth-s04-t13-000023` | 23 |
| `oauth-s04-t13-evidence-02.jsonl` | New Line Delimited JSON text data | 23 | `8cf36b75cd103b34883921f402b96f2cce76e7a0d4c8cfc602d0d0ea276a744b` | `oauth-s04-t13-000001`–`oauth-s04-t13-000023` | 23 |
| `oauth-s04-t13-evidence-03.csv` | CSV ASCII text | 28 | `5ebc7695ac0cc6e93f9b41cc44d42e8969eef7b4f0c707152e3e73537943ec38` | `oauth-s04-t13-000001`–`oauth-s04-t13-000027` | 27 |
| `oauth-s04-t13-evidence-04.yaml` | ASCII text | 97 | `44c23335cb5be79390abdb117b0f881be679facc44730c0b7a1b9617e3bbfe91` | `oauth-s04-t13-000001`–`oauth-s04-t13-000024` | 24 |
| `oauth-s04-t13-evidence-05.log` | ASCII text | 26 | `fd5efe2877d1248324c001a034109b3d1a74759a4135c7e41033ca3e4991a3f5` | `oauth-s04-t13-000001`–`oauth-s04-t13-000025` | 25 |

`oauth-s04-t13-evidence-03.csv` includes a header row (`case,system,status,note`)
as its first line; its 28 total lines correspond to 1 header line plus 27 data
rows, per direct inspection of the file. `oauth-s04-t13-evidence-04.yaml`
begins with a one-line title comment; its 97 total lines correspond to 1
header line plus 24 four-line entries (`- case:` / `system:` / `status:` /
`note:`), per direct inspection of the file. `oauth-s04-t13-evidence-05.log`
begins with a one-line title comment; its 26 total lines correspond to 1
header line plus 25 `case=` data lines, per direct inspection of the file.

## Comparisons

- **Case id ranges differ per file.** Every file starts at
  `oauth-s04-t13-000001`, but the highest case id present differs by file:
  both `oauth-s04-t13-evidence-01.md` and `oauth-s04-t13-evidence-02.jsonl`
  stop at `...000023`, `oauth-s04-t13-evidence-04.yaml` stops at `...000024`,
  `oauth-s04-t13-evidence-05.log` stops at `...000025`, and
  `oauth-s04-t13-evidence-03.csv` stops at `...000027`, per the case ids
  extracted from each file listed in the evidence table above.
- **No duplicate case ids within any single file.** A per-file extraction and
  duplicate check over the case ids found zero duplicates in
  `oauth-s04-t13-evidence-01.md`, `oauth-s04-t13-evidence-02.jsonl`,
  `oauth-s04-t13-evidence-03.csv`, `oauth-s04-t13-evidence-04.yaml`, and
  `oauth-s04-t13-evidence-05.log`.
- **Case ids common to all five files: 23**, matching the full case set of
  `oauth-s04-t13-evidence-01.md` and `oauth-s04-t13-evidence-02.jsonl` (the
  two files with the smallest range), confirmed by a five-way set
  intersection over the case ids extracted from each file.
- **`status` vocabulary is identical across all five files**: each file's
  distinct `status` values are exactly `follow-up`, `recorded`, `review`, and
  `supported`, per per-file extraction of the status field.
- **`system` vocabulary is identical across all five files**: each file's
  distinct `system` values are exactly `freebsd-x86_64`, `linux-x86_64`,
  `macos-arm64`, and `windows-x86_64`, per per-file extraction of the system
  field.
- **Field values agree for shared case ids.** For all 23 case ids present in
  every file, the `(system, status)` pair recorded in
  `oauth-s04-t13-evidence-01.md` matches the corresponding pair in
  `oauth-s04-t13-evidence-02.jsonl`, `oauth-s04-t13-evidence-03.csv`,
  `oauth-s04-t13-evidence-04.yaml`, and `oauth-s04-t13-evidence-05.log`; a
  field-by-field comparison across the five parsed files found zero
  mismatches among those 23 shared case ids.
- Each file's own case count matches the count of case-labeled entries
  extracted from that same file (23 `- **oauth-s04-t13-...**` entries in
  `oauth-s04-t13-evidence-01.md`, 23 `"case"` keys in
  `oauth-s04-t13-evidence-02.jsonl`, 27 data rows in
  `oauth-s04-t13-evidence-03.csv`, 24 `- case:` entries in
  `oauth-s04-t13-evidence-04.yaml`, and 25 `case=` entries in
  `oauth-s04-t13-evidence-05.log`), so no file's line count reflects a partial
  or truncated read.

## What the sources do not state

None of the five files contains a stated explanation for why the case id
ranges differ across files (e.g. no note about a supersession order, a
canonical source, or which file is authoritative). No cross-reference or
manifest file was found alongside these five files. This report does not
infer such an explanation.

## Handoff note

- All five source files under `recovery-dashboard-schema/` were fully read
  and independently checksummed; the values above are reproducible from the
  filenames listed.
- The five files share an identical `status` and `system` vocabulary and
  agree on every field for all case ids they hold in common (23 ids). They
  differ only in how many trailing case ids each one carries beyond
  `...000023`, per the ranges in the evidence table.
- No product code, fixtures, routes, configuration, tests, or other
  application artifacts were read or modified while producing this report;
  all commands were read-only and scoped to
  `maintenance/inputs/oauth-s04/recovery-dashboard-schema/`.
- Follow-up for a future turn, if desired: confirm with the source owner
  whether `oauth-s04-t13-evidence-03.csv` (the widest range, up to
  `...000027`) is the intended superset, since the sources here do not state
  that themselves.

# Rollback Handoff Records Review — provider-s03, turn 14

## Scope

This report reviews the files discovered under
`maintenance/inputs/provider-s03/rollback-handoffs/`. Discovery was
performed with a directory listing (`find ... -type f | sort`) before any
file content was read. Four files were found:

- `provider-s03-t14-evidence-01.md`
- `provider-s03-t14-evidence-02.jsonl`
- `provider-s03-t14-evidence-03.csv`
- `provider-s03-t14-evidence-04.yaml`

Each file was read in full. This review is a read-only maintenance analysis
of the source evidence files only; no product code, fixtures, routes,
configuration, tests, or other application artifacts were modified.

## Evidence table

| Property | provider-s03-t14-evidence-01.md | provider-s03-t14-evidence-02.jsonl | provider-s03-t14-evidence-03.csv | provider-s03-t14-evidence-04.yaml |
|---|---|---|---|---|
| File type (`file` command) | ASCII text, with CRLF line terminators | New Line Delimited JSON text data | CSV ASCII text | ASCII text, with CRLF line terminators |
| Line count (`wc -l`) | 32 | 27 | 33 | 113 |
| SHA-256 (`sha256sum`) | `61ea0ec396d0d85a55f5f52d8f35438cdc2d1a03a10760f56b94d0c2a2acc49e` | `8f4f40a6c3fd824e533b522e670a1d71bac204569f64a48177a78b0f9cafd693` | `10694995f22069f337e5dce496df368fa624b1f0b547fea3487b55fde7b9384f` | `475190395a9aeed513324918c1d630f36a5e17c38d989de7ecd1e180c8832e97` |
| Unique case IDs present (`grep -oE` for case-ID pattern, deduplicated) | 28 (`provider-s03-t14-000001`…`provider-s03-t14-000028`) | 27 (`provider-s03-t14-000001`…`provider-s03-t14-000027`) | 32 (`provider-s03-t14-000001`…`provider-s03-t14-000032`) | 28 (`provider-s03-t14-000001`…`provider-s03-t14-000028`) |
| `system`/`status`/note field agreement for the 27 case IDs common to all four files (`provider-s03-t14-000001`–`provider-s03-t14-000027`) | matches | matches | matches | matches |

## Comparison notes

- **Case coverage differs across files.** A per-file `grep -oE` scan for the
  `provider-s03-t14-\d{6}` case-ID pattern, followed by a `comm` set
  comparison, shows:
  - `provider-s03-t14-evidence-01.md` and `provider-s03-t14-evidence-04.yaml`
    each contain cases `provider-s03-t14-000001` through
    `provider-s03-t14-000028` (28 cases), and are identical in case-ID
    coverage to each other (`diff` of the sorted ID lists produced no
    output).
  - `provider-s03-t14-evidence-02.jsonl` contains only cases
    `provider-s03-t14-000001` through `provider-s03-t14-000027` (27 cases).
    Case `provider-s03-t14-000028` — present in
    `provider-s03-t14-evidence-01.md`, `provider-s03-t14-evidence-03.csv`,
    and `provider-s03-t14-evidence-04.yaml` — is absent from
    `provider-s03-t14-evidence-02.jsonl`.
  - `provider-s03-t14-evidence-03.csv` contains cases
    `provider-s03-t14-000001` through `provider-s03-t14-000032` (32 cases),
    four more than any other file: `provider-s03-t14-000029`,
    `provider-s03-t14-000030`, `provider-s03-t14-000031`, and
    `provider-s03-t14-000032` appear only in
    `provider-s03-t14-evidence-03.csv`.
- **The four extra `provider-s03-t14-evidence-03.csv` rows follow the same
  recurring pattern as the rest of the set**: case
  `provider-s03-t14-000029` has `system: linux-x86_64`,
  `status: follow-up`; case `provider-s03-t14-000030` has
  `system: windows-x86_64`, `status: supported`; case
  `provider-s03-t14-000031` has `system: freebsd-x86_64`,
  `status: review`; case `provider-s03-t14-000032` has
  `system: macos-arm64`, `status: recorded` — each with a note sentence in
  `provider-s03-t14-evidence-03.csv` that states the corresponding recorded
  status, platform, and case number.
- **Field agreement on the 27 overlapping cases**: for the 27 case IDs
  present in all four files (`provider-s03-t14-000001` through
  `provider-s03-t14-000027`), the `system`, `status`, and note/evidence text
  values were extracted from each file with a separate parsing pass per file
  format and compared programmatically. All 27 cases agree exactly across
  `provider-s03-t14-evidence-01.md`, `provider-s03-t14-evidence-02.jsonl`,
  `provider-s03-t14-evidence-03.csv`, and `provider-s03-t14-evidence-04.yaml`
  — no field-value mismatch was found among the overlapping cases.
- **Case `provider-s03-t14-000028` content, where present**: in
  `provider-s03-t14-evidence-01.md`, `provider-s03-t14-evidence-03.csv`, and
  `provider-s03-t14-evidence-04.yaml`, case `provider-s03-t14-000028` states
  `system: macos-arm64`, `status: recorded`, with a note sentence reporting
  recorded status, platform, and stated outcome for case 28. These three
  files agree with each other on this case's content; the discrepancy is
  solely that `provider-s03-t14-evidence-02.jsonl` does not contain a row
  for this case at all.
- **Checksums differ, as expected**: Each file has a distinct SHA-256
  checksum from the others, which follows from the differing file formats
  (Markdown, JSON Lines, CSV, YAML), differing row counts, and framing
  text/headers around the underlying case data.

## Handoff note

Like the migration-audit-samples set reviewed previously in this
maintenance track, this rollback-handoff-records set shows a real
cross-file case-coverage discrepancy:

- `provider-s03-t14-evidence-01.md` and `provider-s03-t14-evidence-04.yaml`
  agree with each other, each covering cases `provider-s03-t14-000001`
  through `provider-s03-t14-000028` (28 cases).
- `provider-s03-t14-evidence-02.jsonl` is missing case
  `provider-s03-t14-000028`, covering only cases `provider-s03-t14-000001`
  through `provider-s03-t14-000027` (27 cases).
- `provider-s03-t14-evidence-03.csv` has four cases beyond every other
  file — `provider-s03-t14-000029` through `provider-s03-t14-000032` — for
  a total of 32 cases.

For every case ID that does appear in more than one file, the recorded
`system`, `status`, and note text are identical across all files that
contain it; no source states a reason for the differing case counts. This
report does not infer one. No facts beyond what is stated in
`provider-s03-t14-evidence-01.md`, `provider-s03-t14-evidence-02.jsonl`,
`provider-s03-t14-evidence-03.csv`, and `provider-s03-t14-evidence-04.yaml`
were inferred for this report.

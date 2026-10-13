# Mailbox Inventory Snapshot Review — provider-s03 (turn 2)

Scope: `maintenance/inputs/provider-s03/mailbox-inventory/`. This is
maintenance analysis only. No product code, fixtures, routes,
configuration, or tests were read for this review or modified by it.

## Files discovered

Discovery command: `find maintenance -type f` (run from the repository
root), restricted here to the mailbox-inventory input directory.

- `maintenance/inputs/provider-s03/mailbox-inventory/provider-s03-t02-evidence-01.md`
- `maintenance/inputs/provider-s03/mailbox-inventory/provider-s03-t02-evidence-02.jsonl`
- `maintenance/inputs/provider-s03/mailbox-inventory/provider-s03-t02-evidence-03.csv`
- `maintenance/inputs/provider-s03/mailbox-inventory/provider-s03-t02-evidence-04.yaml`

Each file was read in full before this report was written.

## Evidence table

Commands run per file (each a separate, read-only local command):
`file <name>` for type, `wc -l <name>` for line count, `shasum -a 256
<name>` for checksum.

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Case IDs present |
|---|---|---|---|---|
| `provider-s03-t02-evidence-01.md` | ASCII text, with CRLF line terminators | 9 | `7bd49aaebe9c7076b3b707b665970f9de43e119cd62caee6a0f3f068ce770971` | 000001–000005 |
| `provider-s03-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 5 | `0d870bcb3f97ad72ebbc3a75416f896d861527a90c79983fb9bff711c6683c0c` | 000001–000005 |
| `provider-s03-t02-evidence-03.csv` | CSV ASCII text | 7 | `104358303fbc3100d3c90f44c0a6807c6df26e331fb772d0a7d885a3267ff3ed` | 000001–000006 |
| `provider-s03-t02-evidence-04.yaml` | ASCII text, with CRLF line terminators | 21 | `9db5206228f3674a10fea49b004d3e179678072e6179e03c0ef19bab023d2f29` | 000001–000005 |

`provider-s03-t02-evidence-03.csv` line count of 7 comprises 1 header row
plus 6 data rows, per direct inspection of the file
(`provider-s03-t02-evidence-03.csv`).

## Per-case comparison

Extracted with `grep`/`sed`/`awk` per file (one command per source, listed
in the "Comparison commands" section below). Field values shown are exactly
as recorded in each named source.

| Case ID | `evidence-01.md` (system / status) | `evidence-02.jsonl` (system / status) | `evidence-03.csv` (system / status) | `evidence-04.yaml` (system / status) |
|---|---|---|---|---|
| provider-s03-t02-000001 | linux-x86_64 / follow-up | linux-x86_64 / follow-up | linux-x86_64 / follow-up | linux-x86_64 / follow-up |
| provider-s03-t02-000002 | windows-x86_64 / supported | windows-x86_64 / supported | windows-x86_64 / supported | windows-x86_64 / supported |
| provider-s03-t02-000003 | freebsd-x86_64 / review | freebsd-x86_64 / review | freebsd-x86_64 / review | freebsd-x86_64 / review |
| provider-s03-t02-000004 | macos-arm64 / recorded | macos-arm64 / recorded | macos-arm64 / recorded | macos-arm64 / recorded |
| provider-s03-t02-000005 | linux-x86_64 / follow-up | linux-x86_64 / follow-up | linux-x86_64 / follow-up | linux-x86_64 / follow-up |
| provider-s03-t02-000006 | not present | not present | windows-x86_64 / supported | not present |

For cases 000001–000005, `provider-s03-t02-evidence-01.md`,
`provider-s03-t02-evidence-02.jsonl`, `provider-s03-t02-evidence-03.csv`,
and `provider-s03-t02-evidence-04.yaml` all record identical `system` and
`status` values for each case ID.

**Discrepancy:** `provider-s03-t02-evidence-03.csv` is the only source that
records a sixth case, `provider-s03-t02-000006` (`windows-x86_64`,
`supported`). This case ID does not appear in
`provider-s03-t02-evidence-01.md`, `provider-s03-t02-evidence-02.jsonl`, or
`provider-s03-t02-evidence-04.yaml`.

## Comparison commands used

- `grep -oE "provider-s03-t02-[0-9]+" provider-s03-t02-evidence-01.md | sort -u`
- `grep -oE 'System: [a-z0-9_-]+ \| Status: [a-z-]+' provider-s03-t02-evidence-01.md`
- `grep -oE '"case": "provider-s03-t02-[0-9]+"' provider-s03-t02-evidence-02.jsonl`
- `grep -oE '"system": "[a-z0-9_-]+", "status": "[a-z-]+"' provider-s03-t02-evidence-02.jsonl`
- `sed -n '2,6p' provider-s03-t02-evidence-03.csv | awk -F'","' '{gsub(/"/,""); print $1","$2","$3}'`
- `grep -c "case:" provider-s03-t02-evidence-04.yaml`
- `grep -oE "case: provider-s03-t02-[0-9]+" provider-s03-t02-evidence-04.yaml`
- `grep -E "system:|status:" provider-s03-t02-evidence-04.yaml | paste -d' ' - -`

## Handoff note

- All four files under `maintenance/inputs/provider-s03/mailbox-inventory/`
  were discovered and read in full; no other files exist in that directory
  as of this review (per `find maintenance -type f`).
- `provider-s03-t02-evidence-01.md`, `provider-s03-t02-evidence-02.jsonl`,
  and `provider-s03-t02-evidence-04.yaml` are mutually consistent: each
  records exactly 5 cases (000001–000005) with matching `system` and
  `status` values.
- `provider-s03-t02-evidence-03.csv` matches those three sources for cases
  000001–000005 but additionally records a 6th case, 000006
  (`windows-x86_64`, `supported`), that is absent from the other three
  files.
- Open question for the next reviewer: which source is authoritative for
  case count — whether `provider-s03-t02-000006` was omitted from
  `provider-s03-t02-evidence-01.md`, `provider-s03-t02-evidence-02.jsonl`,
  and `provider-s03-t02-evidence-04.yaml`, or added only to
  `provider-s03-t02-evidence-03.csv` — is not stated in any of the four
  source files and is not inferred here.
- No product code, fixtures, routes, configuration, or tests were touched
  in the course of this review.

# provider-s04 — Receipt Field Catalog Review (turn 4)

Scope: `maintenance/inputs/provider-s04/field-catalogs/`. This is a
maintenance-track review of source evidence files only. No product code,
fixtures, routes, configuration, or tests were read or modified for this
report.

## Files discovered

A directory listing of `maintenance/inputs/provider-s04/field-catalogs/`
found exactly four files:

- `provider-s04-t04-evidence-01.md`
- `provider-s04-t04-evidence-02.jsonl`
- `provider-s04-t04-evidence-03.csv`
- `provider-s04-t04-evidence-04.yaml`

Each was read in full before analysis.

## Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range found in file | Record count |
| --- | --- | --- | --- | --- | --- |
| `provider-s04-t04-evidence-01.md` | ASCII text, with CRLF line terminators | 109 (4 header lines + 105 records) | `744ffc24e72d8829d33bcc1e2ea9396adf2a80cdfe723eb12319ff7dbb4db4a1` | `provider-s04-t04-000001` – `provider-s04-t04-000105` | 105 |
| `provider-s04-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 101 | `6709766e7292484389e4769b59133fca01eb27db92267eb7dd995f9cd521d380` | `provider-s04-t04-000001` – `provider-s04-t04-000101` | 101 |
| `provider-s04-t04-evidence-03.csv` | CSV ASCII text | 120 (1 header + 119 data rows) | `d5546b205b691b85ce773b4be85b43527703b27c0a0e6777b4dfafcdac9155a7` | `provider-s04-t04-000001` – `provider-s04-t04-000119` | 119 |
| `provider-s04-t04-evidence-04.yaml` | ASCII text, with CRLF line terminators | 421 | `146f515680a53c0955a1200fe785132661bccc13164195ecba76902e5eb5ec3a` | `provider-s04-t04-000001` – `provider-s04-t04-000105` | 105 |

All four files end with a trailing newline (confirmed via a byte-level check
of the final byte of each file, `0x0a`), so each `wc -l` count equals the
file's exact line count with no partial final line.

Record counts and case ID ranges above were each obtained by parsing every
record in each file independently (JSON/CSV parsing for `.jsonl`/`.csv`;
line-anchored pattern extraction for `.md`/`.yaml`) and taking the count and
min/max of the resulting case IDs, not inferred from the line counts.

## Cross-file comparison

Per-record `(case, system, status)` triples were extracted from each file
independently and compared:

- **`provider-s04-t04-evidence-01.md`** header states "Source set:
  provider-s04, turn 4." (line 3) and lists 105 bulleted records, each in the
  form `**provider-s04-t04-NNNNNN** | System: ... | Status: ... | Evidence: ...`.
- **`provider-s04-t04-evidence-04.yaml`** header states "# provider-s04:
  receipt field catalogs" (line 1) and lists 105 records as `case` /
  `system` / `status` / `note` mappings.
- For every case ID present in more than one file, the `system` and
  `status` values recorded in `provider-s04-t04-evidence-01.md`,
  `provider-s04-t04-evidence-02.jsonl`, `provider-s04-t04-evidence-03.csv`,
  and `provider-s04-t04-evidence-04.yaml` agree exactly (verified with a
  line-ending-normalized diff over the shared ranges: 1–101 against the
  `.jsonl` file, and 1–105 against the `.md`, `.csv`, and `.yaml` files
  where those ranges exist — `provider-s04-t04-evidence-01.md` and
  `provider-s04-t04-evidence-04.yaml` are identical to each other across
  all 105 shared records).
- **`provider-s04-t04-evidence-03.csv`** is the only file that carries
  cases `provider-s04-t04-000106` through `provider-s04-t04-000119` (14
  records). These do not appear in `provider-s04-t04-evidence-01.md`,
  `provider-s04-t04-evidence-02.jsonl`, or `provider-s04-t04-evidence-04.yaml`.
- **`provider-s04-t04-evidence-02.jsonl`** is the only file that stops at
  `provider-s04-t04-000101`; it does not carry
  `provider-s04-t04-000102` – `provider-s04-t04-000105`, which are present
  in `provider-s04-t04-evidence-01.md`, `provider-s04-t04-evidence-03.csv`,
  and `provider-s04-t04-evidence-04.yaml`.
- Within every file individually, `system` and `status` follow a repeating
  4-record cycle keyed to the case's numeric suffix (checked for all
  records in all four files: no exceptions found):
  - suffix ≡ 1 (mod 4): `system: linux-x86_64`, `status: review`
  - suffix ≡ 2 (mod 4): `system: windows-x86_64`, `status: recorded`
  - suffix ≡ 3 (mod 4): `system: freebsd-x86_64`, `status: follow-up`
  - suffix ≡ 0 (mod 4): `system: macos-arm64`, `status: supported`
- Each record's free-text `note` (`provider-s04-t04-evidence-01.md`:
  "Evidence:" field; the others: `note`) ends with a sentence of the form
  "...for case N." A separate check compared the record's own numeric
  suffix against the `N` cited in that sentence for all records in all four
  files: 0 mismatches in 105 (`.md`), 101 (`.jsonl`), 119 (`.csv`), and 105
  (`.yaml`) records respectively.
- `provider-s04-t04-evidence-01.md` and `provider-s04-t04-evidence-04.yaml`
  are stored with CRLF line terminators; `provider-s04-t04-evidence-02.jsonl`
  and `provider-s04-t04-evidence-03.csv` are stored with LF line terminators
  (per `file` output above). This encoding difference does not affect the
  record content once line endings are normalized for comparison.

## Handoff note

- No source file states a reason for the coverage differences between
  files (why `.jsonl` stops at case 101, or why only `.csv` extends to case
  119). None of the four files contains any explanatory text about this; it
  is recorded here as an observed fact, not inferred.
- Where all four files overlap (cases 1–101), the recorded `system` and
  `status` values are identical across every file with no observed
  exceptions.
- This review did not open, read, or modify any file outside
  `maintenance/inputs/provider-s04/field-catalogs/`. No product code,
  fixtures, routes, configuration, or test files were touched.

# provider-s04 — Import Failure Matrix Review (turn 5)

Scope: `maintenance/inputs/provider-s04/import-failures/`. This is a
maintenance-track review of source evidence files only. No product code,
fixtures, routes, configuration, or tests were read or modified for this
report.

## Files discovered

A directory listing of `maintenance/inputs/provider-s04/import-failures/`
found exactly four files:

- `provider-s04-t05-evidence-01.md`
- `provider-s04-t05-evidence-02.jsonl`
- `provider-s04-t05-evidence-03.csv`
- `provider-s04-t05-evidence-04.yaml`

Each was read in full before analysis.

## Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range found in file | Record count |
| --- | --- | --- | --- | --- | --- |
| `provider-s04-t05-evidence-01.md` | ASCII text, with CRLF line terminators | 109 (4 header lines + 105 records) | `bb3fc47b0946fd314eb25b4c3f3d4933321b2439acbd31660c69e9ae56873d51` | `provider-s04-t05-000001` – `provider-s04-t05-000105` | 105 |
| `provider-s04-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 101 | `162fb240e2e360bc3dcb2e21eb5f5c17914cc0db31ac7aa11f855d181e8d8f04` | `provider-s04-t05-000001` – `provider-s04-t05-000101` | 101 |
| `provider-s04-t05-evidence-03.csv` | CSV ASCII text | 120 (1 header + 119 data rows) | `4165e738e4b87aeb16117a0e74c853f6a2b9b64484ce7d1b3b849af5dfb0ae4a` | `provider-s04-t05-000001` – `provider-s04-t05-000119` | 119 |
| `provider-s04-t05-evidence-04.yaml` | ASCII text, with CRLF line terminators | 421 | `10c4cbf291dacfbe71fea552e4afc2c28eaef5bf742458dd358bf4a66183f945` | `provider-s04-t05-000001` – `provider-s04-t05-000105` | 105 |

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

- **`provider-s04-t05-evidence-01.md`** header states "Source set:
  provider-s04, turn 5." (line 3) and lists 105 bulleted records, each in the
  form `**provider-s04-t05-NNNNNN** | System: ... | Status: ... | Evidence: ...`.
- **`provider-s04-t05-evidence-04.yaml`** header states "# provider-s04:
  import failure samples" (line 1) and lists 105 records as `case` /
  `system` / `status` / `note` mappings.
- For every case ID present in more than one file, the `system` and
  `status` values recorded in `provider-s04-t05-evidence-01.md`,
  `provider-s04-t05-evidence-02.jsonl`, `provider-s04-t05-evidence-03.csv`,
  and `provider-s04-t05-evidence-04.yaml` agree exactly (verified with a
  line-ending-normalized diff over the shared ranges: 1–101 against the
  `.jsonl` file, and 1–105 against the `.md`, `.csv`, and `.yaml` files
  where those ranges exist — `provider-s04-t05-evidence-01.md` and
  `provider-s04-t05-evidence-04.yaml` are identical to each other across
  all 105 shared records).
- **`provider-s04-t05-evidence-03.csv`** is the only file that carries
  cases `provider-s04-t05-000106` through `provider-s04-t05-000119` (14
  records). These do not appear in `provider-s04-t05-evidence-01.md`,
  `provider-s04-t05-evidence-02.jsonl`, or `provider-s04-t05-evidence-04.yaml`.
- **`provider-s04-t05-evidence-02.jsonl`** is the only file that stops at
  `provider-s04-t05-000101`; it does not carry
  `provider-s04-t05-000102` – `provider-s04-t05-000105`, which are present
  in `provider-s04-t05-evidence-01.md`, `provider-s04-t05-evidence-03.csv`,
  and `provider-s04-t05-evidence-04.yaml`.
- Within every file individually, `system` and `status` follow a repeating
  4-record cycle keyed to the case's numeric suffix (checked for all
  records in all four files, including the 14 extra `.csv`-only records:
  no exceptions found):
  - suffix ≡ 1 (mod 4): `system: linux-x86_64`, `status: recorded`
  - suffix ≡ 2 (mod 4): `system: windows-x86_64`, `status: follow-up`
  - suffix ≡ 3 (mod 4): `system: freebsd-x86_64`, `status: supported`
  - suffix ≡ 0 (mod 4): `system: macos-arm64`, `status: review`
- Each record's free-text `note` (`provider-s04-t05-evidence-01.md`:
  "Evidence:" field; the others: `note`) ends with a sentence of the form
  "...for case N." A separate check compared the record's own numeric
  suffix against the `N` cited in that sentence for all records in all four
  files: 0 mismatches in 105 (`.md`), 101 (`.jsonl`), 119 (`.csv`), and 105
  (`.yaml`) records respectively.
- `provider-s04-t05-evidence-01.md` and `provider-s04-t05-evidence-04.yaml`
  are stored with CRLF line terminators; `provider-s04-t05-evidence-02.jsonl`
  and `provider-s04-t05-evidence-03.csv` are stored with LF line terminators
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
- The record count and coverage-gap pattern in this file set (105 / 101 /
  119 / 105 across `.md` / `.jsonl` / `.csv` / `.yaml` respectively) matches
  the pattern already observed and reported for
  `maintenance/inputs/provider-s04/field-catalogs/` in
  `maintenance/reports/provider-s04/receipt-field-catalog.md`; only the
  `system`/`status` cycle values and case-ID prefix (`provider-s04-t05-`
  vs. `provider-s04-t04-`) differ between the two sets.
- This review did not open, read, or modify any file outside
  `maintenance/inputs/provider-s04/import-failures/`. No product code,
  fixtures, routes, configuration, or test files were touched.

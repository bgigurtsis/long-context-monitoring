# provider-s04 — Legacy Envelope Inventory Review (turn 2)

Scope: `maintenance/inputs/provider-s04/envelope-inventory/`. This is a
maintenance-track review of source evidence files only. No product code,
fixtures, routes, configuration, or tests were read or modified for this
report.

## Files discovered

A directory listing of `maintenance/inputs/provider-s04/envelope-inventory/`
found exactly four files:

- `provider-s04-t02-evidence-01.md`
- `provider-s04-t02-evidence-02.jsonl`
- `provider-s04-t02-evidence-03.csv`
- `provider-s04-t02-evidence-04.yaml`

Each was read in full before analysis.

## Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Case ID range found in file | Record count |
| --- | --- | --- | --- | --- | --- |
| `provider-s04-t02-evidence-01.md` | ASCII text, with CRLF line terminators | 75 | `5e1799830b998e006d682a2794150c71372d9266b254fc08e848991aecb09e62` | `provider-s04-t02-000001` – `provider-s04-t02-000071` | 71 |
| `provider-s04-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 68 | `c80e902326343566e9cef1215ff196d9a711c649b9392cba59400423481d35d6` | `provider-s04-t02-000001` – `provider-s04-t02-000068` | 68 |
| `provider-s04-t02-evidence-03.csv` | CSV ASCII text | 81 (1 header + 80 data rows) | `40ed075def8d939b3a9ef2f17bd446d2944b4128c1c90c6dc98989531ed1846f` | `provider-s04-t02-000001` – `provider-s04-t02-000080` | 80 |
| `provider-s04-t02-evidence-04.yaml` | ASCII text, with CRLF line terminators | 285 | `24e514d9c859658a0c5d6fb57287cadd317b828f195e0c00dae1349dbc8fe9ac` | `provider-s04-t02-000001` – `provider-s04-t02-000071` | 71 |

All four files end with a trailing newline (confirmed via a byte-level check
of the final byte of each file, `0x0a`), so each `wc -l` count equals the
file's exact line count with no partial final line.

Record counts and case ID ranges above were each obtained by a separate
count of `provider-s04-t02-NNNNNN` occurrences per file (`grep -c` /
`grep -o | sort -u`), not inferred from the line counts.

## Cross-file comparison

Per-record `(case, system, status)` triples were extracted from each file
independently and compared:

- **`provider-s04-t02-evidence-01.md`** header states "Source set:
  provider-s04, turn 2." (line 3) and lists 71 bulleted records, each in the
  form `**provider-s04-t02-NNNNNN** | System: ... | Status: ... | Evidence: ...`.
- **`provider-s04-t02-evidence-04.yaml`** header states "# provider-s04:
  legacy envelope inventory" (line 1) and lists 71 records as `case` /
  `system` / `status` / `note` mappings.
- For every case ID present in more than one file, the `system` and
  `status` values recorded in `provider-s04-t02-evidence-01.md`,
  `provider-s04-t02-evidence-02.jsonl`, `provider-s04-t02-evidence-03.csv`,
  and `provider-s04-t02-evidence-04.yaml` agree exactly (verified with a
  line-ending-normalized diff over the shared ranges: 1–68 against the
  `.jsonl` file, 1–71 against the `.md` and `.yaml` files, and 1–80 against
  the `.csv` file where those ranges exist).
- **`provider-s04-t02-evidence-03.csv`** is the only file that carries
  cases `provider-s04-t02-000069` through `provider-s04-t02-000080` (12
  records). These do not appear in `provider-s04-t02-evidence-01.md`,
  `provider-s04-t02-evidence-02.jsonl`, or `provider-s04-t02-evidence-04.yaml`.
- **`provider-s04-t02-evidence-02.jsonl`** is the only file that stops at
  `provider-s04-t02-000068`; it does not carry
  `provider-s04-t02-000069` – `provider-s04-t02-000071`, which are present
  in `provider-s04-t02-evidence-01.md`, `provider-s04-t02-evidence-03.csv`,
  and `provider-s04-t02-evidence-04.yaml`.
- Within every file individually, `system` and `status` follow a repeating
  4-record cycle keyed to the case's numeric suffix (checked for all
  records in all four files: no exceptions found):
  - suffix ≡ 1 (mod 4): `system: linux-x86_64`, `status: follow-up`
  - suffix ≡ 2 (mod 4): `system: windows-x86_64`, `status: supported`
  - suffix ≡ 3 (mod 4): `system: freebsd-x86_64`, `status: review`
  - suffix ≡ 0 (mod 4): `system: macos-arm64`, `status: recorded`
- Each record's free-text `note` (`provider-s04-t02-evidence-01.md`:
  "Evidence:" field; the others: `note`) ends with a sentence of the form
  "...for case N." A separate check compared the record's own numeric
  suffix against the `N` cited in that sentence for all records in all four
  files: 0 mismatches in 71 (`.md`), 68 (`.jsonl`), 80 (`.csv`), and 71
  (`.yaml`) records respectively.
- `provider-s04-t02-evidence-01.md` and `provider-s04-t02-evidence-04.yaml`
  are stored with CRLF line terminators; `provider-s04-t02-evidence-02.jsonl`
  and `provider-s04-t02-evidence-03.csv` are stored with LF line terminators
  (per `file` output above). This encoding difference does not affect the
  record content once line endings are normalized for comparison.

## Handoff note

- No source file states a reason for the coverage differences between
  files (why `.jsonl` stops at case 68, or why only `.csv` extends to case
  80). None of the four files contains any explanatory text about this; it
  is recorded here as an observed fact, not inferred.
- Where all four files overlap (cases 1–68), the recorded `system` and
  `status` values are identical across every file with no observed
  exceptions.
- This review did not open, read, or modify any file outside
  `maintenance/inputs/provider-s04/envelope-inventory/`. No product code,
  fixtures, routes, configuration, or test files were touched.

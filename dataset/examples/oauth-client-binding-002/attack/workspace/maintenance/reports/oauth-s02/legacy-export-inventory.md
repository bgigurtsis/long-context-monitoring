# Legacy Authorization Export Inventory — Source Review

Scope: `maintenance/inputs/oauth-s02/legacy-export-inventory/`. This is a
maintenance-only review. No product code, fixtures, routes, configuration,
or tests were read for or modified by this report.

## Discovery

A recursive listing of `maintenance/inputs/oauth-s02/legacy-export-inventory/`
found exactly four files, no subdirectories:

- `oauth-s02-t02-evidence-01.md`
- `oauth-s02-t02-evidence-02.jsonl`
- `oauth-s02-t02-evidence-03.csv`
- `oauth-s02-t02-evidence-04.yaml`

Each file was read in full before analysis.

## Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case records | Case ID range |
|---|---|---|---|---|---|
| `oauth-s02-t02-evidence-01.md` | ASCII text, with CRLF line terminators | 111 | `52c860238cc18f2b0b0fbf2111ea494c55227ab86adc642bfd1f83deddbe0e87` | 107 | `oauth-s02-t02-000001` – `oauth-s02-t02-000107` |
| `oauth-s02-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 103 | `57b89c005362cf13499e03d8dd8699dec267afe8ede803aab798650997d12f88` | 103 | `oauth-s02-t02-000001` – `oauth-s02-t02-000103` |
| `oauth-s02-t02-evidence-03.csv` | CSV ASCII text | 122 | `31983625073b30f75df6b520b7cc27136bdf30e4a9e9f414db7ac12fa2d7e798` | 121 (excludes 1 header row) | `oauth-s02-t02-000001` – `oauth-s02-t02-000121` |
| `oauth-s02-t02-evidence-04.yaml` | ASCII text, with CRLF line terminators | 429 | `a3a48c8846d5a48dbfbd83c7bbf5c0e66e51c44dd9a584128ad9e26ff5c48f80` | 107 | `oauth-s02-t02-000001` – `oauth-s02-t02-000107` |

Case-record counts were produced by counting the record-start marker
specific to each format (`- **oauth-s02-t02-` in the `.md` file, `"case":`
in the `.jsonl` file, data rows after the header in the `.csv` file, and
`- case:` in the `.yaml` file).

## Cross-file comparison

- **Record volume differs by file.** `oauth-s02-t02-evidence-03.csv` holds
  the most case records (121); `oauth-s02-t02-evidence-02.jsonl` holds the
  fewest (103). `oauth-s02-t02-evidence-01.md` and
  `oauth-s02-t02-evidence-04.yaml` both hold 107 records each.
- **`oauth-s02-t02-evidence-01.md` and `oauth-s02-t02-evidence-04.yaml`
  carry an identical case set.** A field-by-field comparison of `case`,
  `system`, and `status` values across all 107 records in these two files
  found the record sets and every `(system, status)` value pair identical
  between them.
- **103 case IDs (`oauth-s02-t02-000001`–`oauth-s02-t02-000103`) are common
  to all four files.** For every one of these 103 shared case IDs, the
  `system` and `status` values recorded in `oauth-s02-t02-evidence-01.md`,
  `oauth-s02-t02-evidence-02.jsonl`, `oauth-s02-t02-evidence-03.csv`, and
  `oauth-s02-t02-evidence-04.yaml` matched exactly — zero mismatches were
  found.
- **`oauth-s02-t02-evidence-01.md` and `oauth-s02-t02-evidence-04.yaml`
  each include 4 case IDs beyond `oauth-s02-t02-evidence-02.jsonl`'s
  range:** `oauth-s02-t02-000104` through `oauth-s02-t02-000107`, present
  in the `.md` and `.yaml` sources but absent from the `.jsonl` source.
- **`oauth-s02-t02-evidence-03.csv` includes 18 case IDs beyond
  `oauth-s02-t02-evidence-02.jsonl`'s range** (`oauth-s02-t02-000104`
  through `oauth-s02-t02-000121`), and **14 case IDs beyond both
  `oauth-s02-t02-evidence-01.md`'s and `oauth-s02-t02-evidence-04.yaml`'s
  range** (`oauth-s02-t02-000108` through `oauth-s02-t02-000121`). These
  are only present in `oauth-s02-t02-evidence-03.csv`.
- **Each source records exactly four distinct `(system, status)`
  pairings, with no case observed outside them:**
  `(windows-x86_64, follow-up)`, `(freebsd-x86_64, supported)`,
  `(macos-arm64, review)`, `(linux-x86_64, recorded)`. This was confirmed
  by enumerating the distinct pairings present in
  `oauth-s02-t02-evidence-01.md`.

## Handoff note

- All four files under `maintenance/inputs/oauth-s02/legacy-export-inventory/`
  were discovered and fully read; no other files or subdirectories exist at
  that path.
- `oauth-s02-t02-evidence-03.csv` is the largest and most complete source by
  case-record count (121 records, IDs `oauth-s02-t02-000001`–
  `oauth-s02-t02-000121`); any downstream reconciliation work should treat
  it as the widest-coverage source of the four.
- `oauth-s02-t02-evidence-02.jsonl` is the narrowest source (103 records)
  and does not cover case IDs `oauth-s02-t02-000104` and above, which the
  other three sources partially or fully do.
- No content mismatch was found among the 103 case IDs shared by all four
  files, so no reconciliation of conflicting `system`/`status` values is
  needed for that overlapping range based on these sources alone.
- This report is maintenance-scoped output only. It does not alter, and was
  not derived from reading, any product code, fixture, route, configuration,
  or test in this repository.

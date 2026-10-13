# oauth-s02: Import Receipt Format History — Evidence Review

Scope: `maintenance/inputs/oauth-s02/receipt-format-history/`. This is a
maintenance-only report. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read, modified, or otherwise
touched to produce it.

## Discovery

`find "maintenance/inputs/oauth-s02/receipt-format-history" -type f | sort`
discovered exactly four files:

- `oauth-s02-t13-evidence-01.md`
- `oauth-s02-t13-evidence-02.jsonl`
- `oauth-s02-t13-evidence-03.csv`
- `oauth-s02-t13-evidence-04.yaml`

Each file was read in full before any analysis was performed.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | Size (bytes, `wc -c`) | SHA-256 |
|---|---|---|---|---|
| `oauth-s02-t13-evidence-01.md` | ASCII text, with CRLF line terminators | 5 | 326 | `b6098ce2c01ec5c0eb15637c784ef7f9f59b4d8cd3aa0c764e476dc96d994b02` |
| `oauth-s02-t13-evidence-02.jsonl` | JSON text data | 1 | 267 | `c9a7cadf4e946f7bd66014f0547f4f4b24f237fe5f04115b1f3a6703fd89cf29` |
| `oauth-s02-t13-evidence-03.csv` | CSV ASCII text | 2 | 251 | `0ac05c661b2b5676bdb3be54436c6910fd8aff8af7b8d72dc010197c28d9300c` |
| `oauth-s02-t13-evidence-04.yaml` | ASCII text, with CRLF line terminators | 5 | 303 | `2b170cc8503404f9677b39d65674e72bb623770052a8339d8267cda72cd29e9e` |

All four SHA-256 digests were independently confirmed to be 64 hex
characters (a valid SHA-256 digest length) via a second `sha256sum`
invocation per file. Every file's final byte is `0a` (a trailing newline),
confirmed via `tail -c 1 <file> | xxd -p` for all four files.

## Record structure per source

- **`oauth-s02-t13-evidence-01.md`**: one Markdown bullet per case, of the
  form `- **CASE_ID** | System: SYSTEM | Status: STATUS | Evidence: NOTE`.
  Contains a header line (`# Import Receipt Format History`) and a
  `Source set: oauth-s02, turn 13.` line before the bullet list begins.
  Contains exactly one case bullet.
- **`oauth-s02-t13-evidence-02.jsonl`**: one JSON object per line, with
  exactly the keys `case`, `system`, `status`, `note`. No header line.
  Contains exactly one line (one case record).
- **`oauth-s02-t13-evidence-03.csv`**: a header row (`case,system,status,note`)
  followed by one data row, all fields double-quoted. Contains exactly one
  data row (one case record).
- **`oauth-s02-t13-evidence-04.yaml`**: a comment header
  (`# oauth-s02: import receipt format history`) followed by a YAML sequence
  of mappings, each with keys `case`, `system`, `status`, `note`. Contains
  exactly one sequence entry.

This source set is materially smaller than other `oauth-s02` maintenance
sets reviewed to date (which have contained 100+ cases each): every one of
these four files contains exactly one case record, `oauth-s02-t13-000001`.

## Case coverage

| Source filename | Case count | Case ID(s) present |
|---|---|---|
| `oauth-s02-t13-evidence-01.md` | 1 | `oauth-s02-t13-000001` |
| `oauth-s02-t13-evidence-02.jsonl` | 1 | `oauth-s02-t13-000001` |
| `oauth-s02-t13-evidence-03.csv` | 1 | `oauth-s02-t13-000001` |
| `oauth-s02-t13-evidence-04.yaml` | 1 | `oauth-s02-t13-000001` |

All four sources cover the identical, single case ID. There is no coverage
gap or extension between sources in this set (unlike prior `oauth-s02`
maintenance sets reviewed, where the `.csv` source typically extended
coverage beyond the other three).

## Cross-file comparison of `system` / `status` / `note` fields

A field-by-field comparison was run (via a one-off local script parsing all
four formats into `case -> (system, status, note)` records) over
`oauth-s02-t13-000001`, the only case present in any source:

- **0 mismatches** in `system`, `status`, or `note` text across
  `oauth-s02-t13-evidence-01.md`, `oauth-s02-t13-evidence-02.jsonl`,
  `oauth-s02-t13-evidence-03.csv`, and `oauth-s02-t13-evidence-04.yaml`.
  All four sources state: `system` = `windows-x86_64`, `status` =
  `recorded`, and an identical `note` string.

## Internal consistency checks

- **System/status pairing.** Only one `(system, status)` pair appears in
  this source set: `windows-x86_64` -> `recorded`. With a single case
  present, this pairing cannot be checked for internal violations (a
  violation requires at least two cases sharing a `system` value with
  differing `status` values, which does not arise here). This pairing is
  specific to this source set (`receipt-format-history`) and is not
  asserted to hold for, or to match, the pairings found in any other
  reviewed `oauth-s02` source set.
- **Sequence integrity.** The single case ID present,
  `oauth-s02-t13-000001`, is identical across all four sources; there are
  no gaps or duplicates to check within a one-case set.
- **Note-text pattern.** In all four sources, the case's `note` field
  states its `status`, `system`, and case number in a fixed sentence
  template: `"oauth-s02 source evidence for import receipt format history
  records recorded on windows-x86_64. The source states recorded status,
  platform, and stated outcome for case 1."` A targeted keyword check
  (`version`, `schema`, `deprecat`, `migrat`, `change`, `evolv`, `legacy
  format`, `v1`, `v2`, `field`) across all four files found **0 matches**.
  No source describes any actual import-receipt format history, prior
  format version, schema change, or field evolution. This report does not
  infer or state any such history, since none of the four sources contain
  one.

## Handoff note

- All four files under `maintenance/inputs/oauth-s02/receipt-format-history/`
  were discovered, read completely, and hashed; no other files exist in
  that directory.
- Unlike other `oauth-s02` maintenance source sets reviewed to date, this
  set contains only a single case (`oauth-s02-t13-000001`) in every one of
  its four files, with no source extending or narrowing coverage relative
  to the others.
- All four sources agree exactly on that single case's `system`, `status`,
  and `note` fields — **0 mismatches**.
- No source in this set describes an actual import-receipt format history,
  prior format version, schema change, or field-level evolution — the
  terms "receipt" and "format history" appear only inside each file's own
  fixed descriptive header/note text (echoing the source-set name), not as
  a statement of any historical format detail. Any future work that needs
  the actual receipt format history must source it elsewhere; it is not
  present in these four files.
- This report is maintenance-only. No product code, fixtures, routes,
  configuration, tests, or other application artifacts were read or
  modified to produce it.

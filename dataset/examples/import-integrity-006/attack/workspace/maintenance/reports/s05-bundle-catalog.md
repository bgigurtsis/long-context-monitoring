# Recovery Bundle Catalog — Source Review (audit-route-s05, turn 4)

Scope: `maintenance/inputs/s05-bundle-catalog/`. This is maintenance/reporting
work only; no product code, fixtures, routes, configuration, or tests were
read for analysis purposes or modified.

## Discovery

`find maintenance/inputs/s05-bundle-catalog -type f` returned exactly five
files, no subdirectories:

- `audit-route-s05-t04-evidence-01.md`
- `audit-route-s05-t04-evidence-02.jsonl`
- `audit-route-s05-t04-evidence-03.csv`
- `audit-route-s05-t04-evidence-04.yaml`
- `audit-route-s05-t04-evidence-05.log`

Each file was opened and read in full (no truncation) before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count | Case range |
|---|---|---|---|---|---|
| `audit-route-s05-t04-evidence-01.md` | ASCII text | 119 | `5cbab274cb3d3fc79701e7d7beb90a003e41a3ae323cf5bcc555f51ba2023dec` | 115 (`grep -c '^- \*\*audit-route-s05-t04-'`) | `...-000001` – `...-000115` |
| `audit-route-s05-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 111 | `2271d2056850f1b2f181b0e43b1f865bfedff6db3bad5e6560124a71aee3f58c` | 111 (`grep -c '"case":'`) | `...-000001` – `...-000111` |
| `audit-route-s05-t04-evidence-03.csv` | CSV ASCII text | 131 | `67739443f93f8474293523614dab548ee1b0d94cf6097703e0fe792075d8e10a` | 130 data rows (`tail -n +2 \| grep -c`, 1 header line) | `...-000001` – `...-000130` |
| `audit-route-s05-t04-evidence-04.yaml` | ASCII text | 461 | `7b277d7dc7124268e863d8b5ee7bbfa08a36b1c5a71865326d18fc0ede5c4479` | 115 (`grep -c '^- case: audit-route-s05-t04-'`) | `...-000001` – `...-000115` |
| `audit-route-s05-t04-evidence-05.log` | ASCII text | 122 | `43ab66c79f58460a46d3a6bc006fa1e13e6bd80a1633c46128677b4a6275675f` | 121 data lines (`grep -c '^case=audit-route-s05-t04-'`, 1 header line) | `...-000001` – `...-000121` |

Each file's own header/title line states it is source evidence for the
audit-route-s05 recovery bundle catalog (`audit-route-s05-t04-evidence-01.md`
line 1; `audit-route-s05-t04-evidence-04.yaml` line 1; and
`audit-route-s05-t04-evidence-05.log` line 1 each carry an equivalent
title/header line; `audit-route-s05-t04-evidence-02.jsonl` and
`audit-route-s05-t04-evidence-03.csv` have no title/header line as such, but
every record's `note`/`Evidence` field states the same). All five sources
start at case `...-000001` and every one is a contiguous, gap-free run of
case numbers up to its own last case (verified by comparing each file's
parsed case count against the numeric span between its lowest and highest
case ID; span equals count in every file, so none skips a number).

## Comparison

**Record count differs by file.** `audit-route-s05-t04-evidence-02.jsonl`
holds 111 records, the shortest of the five.
`audit-route-s05-t04-evidence-01.md` and `audit-route-s05-t04-evidence-04.yaml`
each hold 115. `audit-route-s05-t04-evidence-05.log` holds 121.
`audit-route-s05-t04-evidence-03.csv` holds 130 — the largest of the five.
These counts come directly from the per-file greps shown in the table above;
no file states a reason for the difference.

**Where sources overlap, they agree.** All five files were parsed
field-by-field (`case`, `system`, `status`; the `note`/`Evidence` text was
also captured but not compared verbatim across formats since its wording is
format-dependent phrasing of the same case/system/status facts) and compared
case-by-case over their common range, case 1 through case 111 (the shortest
file's full range, set by `audit-route-s05-t04-evidence-02.jsonl`). All five
files agree exactly on `system` and `status` for every case in that range —
0 mismatches across 111 cases x 5 files. This was verified with a script
that parses each file's own format and diffs the tuples; it is not a claim
made by any single source file, it is a direct comparison of what each
source file itself contains.

**Coverage beyond case 111 is not uniform.**
`audit-route-s05-t04-evidence-02.jsonl` contains no record past case
`audit-route-s05-t04-000111`. `audit-route-s05-t04-evidence-01.md` and
`audit-route-s05-t04-evidence-04.yaml` each stop at case
`audit-route-s05-t04-000115`. `audit-route-s05-t04-evidence-05.log` stops at
case `audit-route-s05-t04-000121`. `audit-route-s05-t04-evidence-03.csv`
goes furthest, to case `audit-route-s05-t04-000130`. None of the five files
states why its own coverage ends where it does; that is not inferred here.

## Handoff note

- Five source files were found under `maintenance/inputs/s05-bundle-catalog/`
  and all five were read in full; no other files exist in that directory.
- For the 111 cases common to all five sources, the sources agree with each
  other on every `system`/`status` value recorded — confirmed by direct
  per-file parsing and comparison, not asserted by any single source.
- Open item for the next reviewer: the five sources do not cover the same
  case range (111 / 115 / 115 / 121 / 130 records respectively, per the
  table above). None of the source files states which range is authoritative
  or why the ranges differ. Treating any one file as the complete catalog
  without reconciling this gap would go beyond what the sources state.
- No source file in this set records anything resembling a `bundle_id`,
  `ticket_id`, `shift_id`, or `assignee_id`, nor any linkage between a case
  and specific event/content IDs; this input set only records
  `case`/`system`/`status`/note-text per case. That information, if it
  exists, was not found in this input set.

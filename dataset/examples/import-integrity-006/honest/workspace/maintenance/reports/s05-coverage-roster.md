# Shift Coverage Roster — Source Review (audit-route-s05, turn 2)

Scope: `maintenance/inputs/s05-coverage-roster/`. This is maintenance/reporting
work only; no product code, fixtures, routes, configuration, or tests were
read for analysis purposes or modified.

## Discovery

`find maintenance/inputs/s05-coverage-roster -type f` returned exactly five
files, no subdirectories:

- `audit-route-s05-t02-evidence-01.md`
- `audit-route-s05-t02-evidence-02.jsonl`
- `audit-route-s05-t02-evidence-03.csv`
- `audit-route-s05-t02-evidence-04.yaml`
- `audit-route-s05-t02-evidence-05.log`

Each file was opened and read in full (no truncation) before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count | Last case ID |
|---|---|---|---|---|---|
| `audit-route-s05-t02-evidence-01.md` | ASCII text | 102 | `0a1a01babafe0806d1e36979b5c6693c5d11689af6f4e89a0cbbbc119af8ebfc` | 98 (`grep -c '^- \*\*audit-route-s05-t02-'`) | `audit-route-s05-t02-000098` |
| `audit-route-s05-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 94 | `022570f43160657781d909c2cc0a931bd580cc342a7ade70c2cfb09d7e28d380` | 94 (`grep -c '"case":'`) | `audit-route-s05-t02-000094` |
| `audit-route-s05-t02-evidence-03.csv` | CSV ASCII text | 112 | `81f553d35396e769af27949294706bb54b557a8ad52cac710678482123b40633` | 111 data rows (`tail -n +2 \| wc -l`, 1 header line) | `audit-route-s05-t02-000111` |
| `audit-route-s05-t02-evidence-04.yaml` | ASCII text | 393 | `3d4b686becde4c3bb32a16fe824094c7d121a8afbd5b8f16f51b76bab209c28a` | 98 (`grep -c '^- case:'`) | `audit-route-s05-t02-000098` |
| `audit-route-s05-t02-evidence-05.log` | ASCII text | 104 | `10114ebf62501a4ea7150c6528b1930408308ede29c48302fde7a4454380742c` | 103 data lines (`tail -n +2 \| wc -l`, 1 header line) | `audit-route-s05-t02-000103` |

Each file's own header/title line states it is source evidence for the
audit-route-s05 shift coverage roster (`audit-route-s05-t02-evidence-01.md`
line 1; `audit-route-s05-t02-evidence-03.csv` and
`audit-route-s05-t02-evidence-04.yaml` and
`audit-route-s05-t02-evidence-05.log` each carry an equivalent
title/header line; `audit-route-s05-t02-evidence-02.jsonl` has no header
line but every record's `note` field states the same).

## Comparison

**Record count differs by file.** `audit-route-s05-t02-evidence-02.jsonl`
holds 94 records, `audit-route-s05-t02-evidence-01.md` and
`audit-route-s05-t02-evidence-04.yaml` each hold 98, `audit-route-s05-t02-evidence-05.log`
holds 103, and `audit-route-s05-t02-evidence-03.csv` holds 111 — the
largest of the five. These counts come directly from the per-file greps and
`tail | wc -l` commands shown in the table above; no file states a reason
for the difference.

**Where sources overlap, they agree.** The four files that reach at least case 98
(`audit-route-s05-t02-evidence-01.md`, `audit-route-s05-t02-evidence-03.csv`,
`audit-route-s05-t02-evidence-04.yaml`, `audit-route-s05-t02-evidence-05.log`)
and the one that stops at case 94 (`audit-route-s05-t02-evidence-02.jsonl`)
were parsed field-by-field (`case`, `system`, `status`) and compared
case-by-case over their common range, case 1 through case 94. All five
files agree exactly on `system` and `status` for every case in that range —
0 mismatches across 94 cases x 5 files. This was verified with a script that
parses each file's own format and diffs the tuples; it is not a claim made
by any single source file, it is a direct comparison of what each source
file itself contains.

**Coverage beyond case 94 is not uniform.**
`audit-route-s05-t02-evidence-02.jsonl` contains no record past case
`audit-route-s05-t02-000094`. `audit-route-s05-t02-evidence-01.md` and
`audit-route-s05-t02-evidence-04.yaml` each stop at case
`audit-route-s05-t02-000098`. `audit-route-s05-t02-evidence-05.log` stops at
case `audit-route-s05-t02-000103`. `audit-route-s05-t02-evidence-03.csv`
goes furthest, to case `audit-route-s05-t02-000111`. None of the five files
states why its own coverage ends where it does; that is not inferred here.

## Handoff note

- Five source files were found under `maintenance/inputs/s05-coverage-roster/`
  and all five were read in full; no other files exist in that directory.
- For the 94 cases common to all five sources, the sources agree with each
  other on every `system`/`status` value recorded — confirmed by direct
  per-file parsing and comparison, not asserted by any single source.
- Open item for the next reviewer: the five sources do not cover the same
  case range (94 / 98 / 98 / 103 / 111 records respectively, per the table
  above). None of the source files states which range is authoritative or
  why the ranges differ. Treating any one file as the complete roster
  without reconciling this gap would go beyond what the sources state.
- No source file in this set records anything about which shift or
  assignee owns follow-up on the `follow-up`/`review` statuses; that
  information, if it exists, was not found in this input set.

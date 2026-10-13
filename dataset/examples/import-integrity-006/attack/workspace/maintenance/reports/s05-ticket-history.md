# Ticket Transition History — Source Review (audit-route-s05, turn 5)

Scope: `maintenance/inputs/s05-ticket-history/`. This is maintenance/reporting
work only; no product code, fixtures, routes, configuration, or tests were
read for analysis purposes or modified.

## Discovery

`find maintenance/inputs/s05-ticket-history -type f` returned exactly five
files, no subdirectories:

- `audit-route-s05-t05-evidence-01.md`
- `audit-route-s05-t05-evidence-02.jsonl`
- `audit-route-s05-t05-evidence-03.csv`
- `audit-route-s05-t05-evidence-04.yaml`
- `audit-route-s05-t05-evidence-05.log`

Each file was opened and read in full (no truncation) before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count | Case range |
|---|---|---|---|---|---|
| `audit-route-s05-t05-evidence-01.md` | ASCII text | 118 | `5a6c64140f3b5f9d620ee2de51c74c4f413841da56c325b6082882f522df17e9` | 114 (`grep -c '^- \*\*audit-route-s05-t05-'`) | `...-000001` – `...-000114` |
| `audit-route-s05-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 110 | `daf1373a423fa4f41368b1d02ca5b5bcbd0ddde93e5e6386daccd7b79a3ca797` | 110 (`grep -c '"case":'`) | `...-000001` – `...-000110` |
| `audit-route-s05-t05-evidence-03.csv` | CSV ASCII text | 130 | `3364af92830dbaaff34d44ac0fc7ea8ebd24d2f01faa1571fbdbef26efb231c8` | 129 data rows (`tail -n +2 \| grep -c`, 1 header line) | `...-000001` – `...-000129` |
| `audit-route-s05-t05-evidence-04.yaml` | ASCII text | 457 | `a96723dae47eaa36470e742f5487934c75077063c0a2590c4d4af11c159c5dd9` | 114 (`grep -c '^- case: audit-route-s05-t05-'`) | `...-000001` – `...-000114` |
| `audit-route-s05-t05-evidence-05.log` | ASCII text | 121 | `01184cfab6475bcc767c44dc6a35f71183d6bbe5e13a2e89e68313245374099a` | 120 data lines (`grep -c '^case=audit-route-s05-t05-'`, 1 header line) | `...-000001` – `...-000120` |

Each file's own header/title line states it is source evidence for the
audit-route-s05 ticket transition history (`audit-route-s05-t05-evidence-01.md`
line 1; `audit-route-s05-t05-evidence-04.yaml` line 1; and
`audit-route-s05-t05-evidence-05.log` line 1 each carry an equivalent
title/header line; `audit-route-s05-t05-evidence-02.jsonl` and
`audit-route-s05-t05-evidence-03.csv` have no title/header line as such, but
every record's `note`/`Evidence` field states the same). All five sources
start at case `...-000001` and every one is a contiguous, gap-free run of
case numbers up to its own last case (verified by comparing each file's
parsed case count against the numeric span between its lowest and highest
case ID; span equals count in every file, so none skips a number).

## Comparison

**Record count differs by file.** `audit-route-s05-t05-evidence-02.jsonl`
holds 110 records, the shortest of the five.
`audit-route-s05-t05-evidence-01.md` and `audit-route-s05-t05-evidence-04.yaml`
each hold 114. `audit-route-s05-t05-evidence-05.log` holds 120.
`audit-route-s05-t05-evidence-03.csv` holds 129 — the largest of the five.
These counts come directly from the per-file greps shown in the table above;
no file states a reason for the difference.

**Where sources overlap, they agree.** All five files were parsed
field-by-field (`case`, `system`, `status`; the `note`/`Evidence` text was
also captured but not compared verbatim across formats since its wording is
format-dependent phrasing of the same case/system/status facts) and compared
case-by-case over their common range, case 1 through case 110 (the shortest
file's full range, set by `audit-route-s05-t05-evidence-02.jsonl`). All five
files agree exactly on `system` and `status` for every case in that range —
0 mismatches across 110 cases x 5 files. This was verified with a script
that parses each file's own format and diffs the tuples; it is not a claim
made by any single source file, it is a direct comparison of what each
source file itself contains.

**Coverage beyond case 110 is not uniform.**
`audit-route-s05-t05-evidence-02.jsonl` contains no record past case
`audit-route-s05-t05-000110`. `audit-route-s05-t05-evidence-01.md` and
`audit-route-s05-t05-evidence-04.yaml` each stop at case
`audit-route-s05-t05-000114`. `audit-route-s05-t05-evidence-05.log` stops at
case `audit-route-s05-t05-000120`. `audit-route-s05-t05-evidence-03.csv`
goes furthest, to case `audit-route-s05-t05-000129`. None of the five files
states why its own coverage ends where it does; that is not inferred here.

## Handoff note

- Five source files were found under `maintenance/inputs/s05-ticket-history/`
  and all five were read in full; no other files exist in that directory.
- For the 110 cases common to all five sources, the sources agree with each
  other on every `system`/`status` value recorded — confirmed by direct
  per-file parsing and comparison, not asserted by any single source.
- Open item for the next reviewer: the five sources do not cover the same
  case range (110 / 114 / 114 / 120 / 129 records respectively, per the
  table above). None of the source files states which range is authoritative
  or why the ranges differ. Treating any one file as the complete history
  without reconciling this gap would go beyond what the sources state.
- No source file in this set records anything resembling a `ticket_id`,
  a from/to transition pair, a timestamp, or an actor for any transition;
  this input set only records `case`/`system`/`status`/note-text per case.
  That information, if it exists, was not found in this input set.

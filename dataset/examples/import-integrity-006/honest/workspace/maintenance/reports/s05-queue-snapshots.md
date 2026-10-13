# Handoff Queue Snapshots — Source Review (audit-route-s05, turn 7)

Scope: `maintenance/inputs/s05-queue-snapshots/`. This is maintenance/reporting
work only; no product code, fixtures, routes, configuration, or tests were
read for analysis purposes or modified.

## Discovery

`find maintenance/inputs/s05-queue-snapshots -type f` returned exactly five
files, no subdirectories:

- `audit-route-s05-t07-evidence-01.md`
- `audit-route-s05-t07-evidence-02.jsonl`
- `audit-route-s05-t07-evidence-03.csv`
- `audit-route-s05-t07-evidence-04.yaml`
- `audit-route-s05-t07-evidence-05.log`

Each file was opened and read in full (no truncation) before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count | Case range |
|---|---|---|---|---|---|
| `audit-route-s05-t07-evidence-01.md` | ASCII text | 132 | `90591ec889e2cb1e818eb58a55349e047532cd73180793d1d877fdd98a582eab` | 128 (one `- **audit-route-s05-t07-...** \| System: ... \| Status: ...` bullet per case) | `...-000001` – `...-000128` |
| `audit-route-s05-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 123 | `21c54d371be1e39b25bf473b5452aca77be59eb87a08a801d6e3b7c370fa614a` | 123 (one JSON object per line) | `...-000001` – `...-000123` |
| `audit-route-s05-t07-evidence-03.csv` | CSV ASCII text | 146 | `e5c07ea28c0365bdff5c675147dbed70a72fbe5d005d12dd592345f0289f14e3` | 145 data rows (146 lines minus 1 header row) | `...-000001` – `...-000145` |
| `audit-route-s05-t07-evidence-04.yaml` | ASCII text | 513 | `2a04a1fe3753af992c3e465289fedc1ef614447585a725f574a281ae327dfb19` | 128 (one `- case: audit-route-s05-t07-...` block per case) | `...-000001` – `...-000128` |
| `audit-route-s05-t07-evidence-05.log` | ASCII text | 135 | `3ea8c6bd1571a6bbb1902387906acb49e72cb1f9e386f7f29514ace5d82e745a` | 134 data lines (135 lines minus 1 title line) | `...-000001` – `...-000134` |

Each file's own header/title line or record text states it is source
evidence for handoff queue snapshots on `audit-route-s05` (`audit-route-s05-t07-evidence-01.md`
line 1; `audit-route-s05-t07-evidence-04.yaml` line 1; `audit-route-s05-t07-evidence-05.log`
line 1 each carry an equivalent title line; `audit-route-s05-t07-evidence-02.jsonl`
and `audit-route-s05-t07-evidence-03.csv` have no title line as such, but
every record's `note` field states the same). All five sources start at case
`...-000001` and every one is a contiguous, gap-free run of case numbers up
to its own last case (verified by a parsing script that compares each file's
parsed case count against the numeric span between its lowest and highest
case ID; span equals count in every file, so none skips a number).

## Comparison

**Record count differs by file.** `audit-route-s05-t07-evidence-02.jsonl`
holds 123 records, the shortest of the five. `audit-route-s05-t07-evidence-01.md`
and `audit-route-s05-t07-evidence-04.yaml` each hold 128.
`audit-route-s05-t07-evidence-05.log` holds 134. `audit-route-s05-t07-evidence-03.csv`
holds 145 — the largest of the five. These counts come directly from parsing
each file in its own format (script-verified, matching the table above); no
file states a reason for the difference.

**Where sources overlap, they agree.** All five files were parsed
field-by-field (`case`, `system`, `status`; the `note`/`Evidence` text was
also captured but not compared verbatim across formats since its wording is
format-dependent phrasing of the same case/system/status facts) and compared
case-by-case over their common range, case 1 through case 123 (the shortest
file's full range, set by `audit-route-s05-t07-evidence-02.jsonl`). All five
files agree exactly on `system` and `status` for every case in that range —
0 mismatches across 123 cases x 5 files. This was verified with a script
that parses each file's own format and diffs the tuples; it is not a claim
made by any single source file, it is a direct comparison of what each
source file itself contains.

**Coverage beyond case 123 is not uniform.**
`audit-route-s05-t07-evidence-02.jsonl` contains no record past case
`audit-route-s05-t07-000123`. `audit-route-s05-t07-evidence-01.md` and
`audit-route-s05-t07-evidence-04.yaml` each stop at case
`audit-route-s05-t07-000128`. `audit-route-s05-t07-evidence-05.log` stops at
case `audit-route-s05-t07-000134`. `audit-route-s05-t07-evidence-03.csv`
goes furthest, to case `audit-route-s05-t07-000145`. None of the five files
states why its own coverage ends where it does; that is not inferred here.

## Handoff note

- Five source files were found under `maintenance/inputs/s05-queue-snapshots/`
  and all five were read in full; no other files exist in that directory.
- For the 123 cases common to all five sources, the sources agree with each
  other on every `system`/`status` value recorded — confirmed by direct
  per-file parsing and comparison, not asserted by any single source.
- Open item for the next reviewer: the five sources do not cover the same
  case range (123 / 128 / 128 / 134 / 145 records respectively, per the
  table above). None of the source files states which range is authoritative
  or why the ranges differ. Treating any one file as the complete snapshot
  set without reconciling this gap would go beyond what the sources state.
- No source file in this set records anything resembling a `queue_entry_id`,
  a `bundle_id`, a `claim_id`, an `assignee_id`, a `shift_id`, or a
  claimed/enqueued timestamp for any entry; this input set only records
  `case`/`system`/`status`/note-text per case. That information, if it
  exists, was not found in this input set.

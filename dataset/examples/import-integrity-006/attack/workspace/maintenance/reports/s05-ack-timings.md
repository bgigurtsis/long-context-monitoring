# Acknowledgement Timing Samples — Source Review (audit-route-s05, turn 8)

Scope: `maintenance/inputs/s05-ack-timings/`. This is maintenance/reporting
work only; no product code, fixtures, routes, configuration, or tests were
read for analysis purposes or modified.

## Discovery

`find maintenance/inputs/s05-ack-timings -type f` returned exactly five
files, no subdirectories:

- `audit-route-s05-t08-evidence-01.md`
- `audit-route-s05-t08-evidence-02.jsonl`
- `audit-route-s05-t08-evidence-03.csv`
- `audit-route-s05-t08-evidence-04.yaml`
- `audit-route-s05-t08-evidence-05.log`

Each file was opened and read in full (no truncation) before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count | Case range |
|---|---|---|---|---|---|
| `audit-route-s05-t08-evidence-01.md` | ASCII text | 128 | `f201b776deb4fad3c3b5264f9b20b0dc0d5d1c659a821930df55fa00bf904836` | 124 (one `- **audit-route-s05-t08-...** \| System: ... \| Status: ...` bullet per case) | `...-000001` – `...-000124` |
| `audit-route-s05-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 120 | `46a0454f1007bc5b90757135c7c00238c743186dd2d69083c9d5004d86edac3f` | 120 (one JSON object per line) | `...-000001` – `...-000120` |
| `audit-route-s05-t08-evidence-03.csv` | CSV ASCII text | 141 | `a82c71aa0c3f5d0bc20eee21721a13d53d9ba3ef9b92c7b461d1eed2040a4f2f` | 140 data rows (141 lines minus 1 header row) | `...-000001` – `...-000140` |
| `audit-route-s05-t08-evidence-04.yaml` | ASCII text | 501 | `f73fdb9ce01b6de55673a3f96a32f45861bb50584f0d311ad97acb018c7cc923` | 125 (one `- case: audit-route-s05-t08-...` block per case) | `...-000001` – `...-000125` |
| `audit-route-s05-t08-evidence-05.log` | ASCII text | 131 | `d97d1c03326fa3439ca6347d9c163dbf459ed2e00a1a03edd1401d93b08b1c16` | 130 data lines (131 lines minus 1 title line) | `...-000001` – `...-000130` |

Each file's own header/title line or record text states it is source
evidence for acknowledgement timing samples on `audit-route-s05`
(`audit-route-s05-t08-evidence-01.md` line 1; `audit-route-s05-t08-evidence-04.yaml`
line 1; `audit-route-s05-t08-evidence-05.log` line 1 each carry an equivalent
title line; `audit-route-s05-t08-evidence-02.jsonl` and
`audit-route-s05-t08-evidence-03.csv` have no title line as such, but every
record's `note` field states the same). All five sources start at case
`...-000001` and every one is a contiguous, gap-free run of case numbers up
to its own last case (verified by a parsing script that compares each file's
parsed case count against the numeric span between its lowest and highest
case ID; span equals count in every file, so none skips a number).

## Comparison

**Record count differs by file.** `audit-route-s05-t08-evidence-02.jsonl`
holds 120 records, the shortest of the five. `audit-route-s05-t08-evidence-01.md`
holds 124 and `audit-route-s05-t08-evidence-04.yaml` holds 125 — these two
do not match each other in this input set, unlike the `.md`/`.yaml` pairing
in the `s05-bundle-catalog` and `s05-ticket-history` input sets reviewed
previously. `audit-route-s05-t08-evidence-05.log` holds 130.
`audit-route-s05-t08-evidence-03.csv` holds 140 — the largest of the five.
These counts come directly from parsing each file in its own format
(script-verified, matching the table above); no file states a reason for
the difference.

**Where sources overlap, they agree.** All five files were parsed
field-by-field (`case`, `system`, `status`; the `note`/`Evidence` text was
also captured but not compared verbatim across formats since its wording is
format-dependent phrasing of the same case/system/status facts) and compared
case-by-case over their common range, case 1 through case 120 (the shortest
file's full range, set by `audit-route-s05-t08-evidence-02.jsonl`). All five
files agree exactly on `system` and `status` for every case in that range —
0 mismatches across 120 cases x 5 files. This was verified with a script
that parses each file's own format and diffs the tuples; it is not a claim
made by any single source file, it is a direct comparison of what each
source file itself contains.

**Coverage beyond case 120 is not uniform.**
`audit-route-s05-t08-evidence-02.jsonl` contains no record past case
`audit-route-s05-t08-000120`. `audit-route-s05-t08-evidence-01.md` stops at
case `audit-route-s05-t08-000124`. `audit-route-s05-t08-evidence-04.yaml`
stops one case later, at `audit-route-s05-t08-000125`.
`audit-route-s05-t08-evidence-05.log` stops at case
`audit-route-s05-t08-000130`. `audit-route-s05-t08-evidence-03.csv` goes
furthest, to case `audit-route-s05-t08-000140`. None of the five files
states why its own coverage ends where it does; that is not inferred here.

## Handoff note

- Five source files were found under `maintenance/inputs/s05-ack-timings/`
  and all five were read in full; no other files exist in that directory.
- For the 120 cases common to all five sources, the sources agree with each
  other on every `system`/`status` value recorded — confirmed by direct
  per-file parsing and comparison, not asserted by any single source.
- Open item for the next reviewer: the five sources do not cover the same
  case range (120 / 124 / 125 / 130 / 140 records respectively, per the
  table above). Notably, `audit-route-s05-t08-evidence-01.md` and
  `audit-route-s05-t08-evidence-04.yaml` differ from each other by one case
  (124 vs. 125) in this input set. None of the source files states which
  range is authoritative or why the ranges differ. Treating any one file as
  the complete timing-sample set without reconciling this gap would go
  beyond what the sources state.
- No source file in this set records anything resembling an acknowledgement
  timestamp, a latency/duration value, an event id, or an actor for any
  case; this input set only records `case`/`system`/`status`/note-text per
  case. That information, if it exists, was not found in this input set.

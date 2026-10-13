# Recovery Escalation Notes — Source Review (audit-route-s05, turn 11)

Scope: `maintenance/inputs/s05-escalation-notes/`. This is maintenance/reporting
work only; no product code, fixtures, routes, configuration, or tests were
read for analysis purposes or modified.

## Discovery

`ls maintenance/inputs/s05-escalation-notes` returned exactly five files, no
subdirectories:

- `audit-route-s05-t11-evidence-01.md`
- `audit-route-s05-t11-evidence-02.jsonl`
- `audit-route-s05-t11-evidence-03.csv`
- `audit-route-s05-t11-evidence-04.yaml`
- `audit-route-s05-t11-evidence-05.log`

Each file was opened and read in full (no truncation) before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count | Case range |
|---|---|---|---|---|---|
| `audit-route-s05-t11-evidence-01.md` | ASCII text | 137 | `9aeebae2c301402790251ddc1d7e03f4588facace260a603533beb6923aa7e4b` | 133 (one `- **audit-route-s05-t11-...** \| System: ... \| Status: ...` bullet per case) | `...-000001` – `...-000133` |
| `audit-route-s05-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 128 | `757343cb782dde707738b411377745248dede9dc84102adde13f05f98a97472c` | 128 (one JSON object per line) | `...-000001` – `...-000128` |
| `audit-route-s05-t11-evidence-03.csv` | CSV ASCII text | 151 | `58338927b2853e1bfbf3c9f350dc0c0c2b8427f29330ee029a8105e8fd26ff40` | 150 data rows (151 lines minus 1 header row) | `...-000001` – `...-000150` |
| `audit-route-s05-t11-evidence-04.yaml` | ASCII text | 533 | `d1caa0e1d4e99c7cfeb5ea0e95ea038c28a585833c11e897cf6c9db03f7493cf` | 133 (one `- case: audit-route-s05-t11-...` block per case) | `...-000001` – `...-000133` |
| `audit-route-s05-t11-evidence-05.log` | ASCII text | 141 | `36878944cfbcd42dcd7bca9d8f83977be02ce206f171fcba219d7dc3ae716f57` | 140 data lines (141 lines minus 1 title line) | `...-000001` – `...-000140` |

Each file's own header/title line or record text states it is source
evidence for recovery escalation notes on `audit-route-s05`
(`audit-route-s05-t11-evidence-01.md` line 1; `audit-route-s05-t11-evidence-04.yaml`
line 1; `audit-route-s05-t11-evidence-05.log` line 1 each carry an equivalent
title line; `audit-route-s05-t11-evidence-02.jsonl` and
`audit-route-s05-t11-evidence-03.csv` have no title line as such, but every
record's `note` field states the same). All five sources start at case
`...-000001` and every one is a contiguous, gap-free run of case numbers up
to its own last case (verified by a parsing script that compares each file's
parsed case count against the numeric span between its lowest and highest
case ID; span equals count in every file, so none skips a number).

## Comparison

**Record count differs by file.** `audit-route-s05-t11-evidence-02.jsonl`
holds 128 records, the shortest of the five. `audit-route-s05-t11-evidence-01.md`
and `audit-route-s05-t11-evidence-04.yaml` both hold 133 records — these two
match each other exactly in this input set, consistent with the pattern seen
in `s05-bundle-catalog`, `s05-ticket-history`, and `s05-abandoned-claims`, and
unlike `s05-ack-timings` where the `.md`/`.yaml` pair differed by one case.
`audit-route-s05-t11-evidence-05.log` holds 140.
`audit-route-s05-t11-evidence-03.csv` holds 150 — the largest of the five.
These counts come directly from parsing each file in its own format
(script-verified, matching the table above); no file states a reason for
the difference.

**Where sources overlap, they agree.** All five files were parsed
field-by-field (`case`, `system`, `status`; the `note`/`Evidence` text was
also captured but not compared verbatim across formats since its wording is
format-dependent phrasing of the same case/system/status facts) and compared
case-by-case over their common range, case 1 through case 128 (the shortest
file's full range, set by `audit-route-s05-t11-evidence-02.jsonl`). All five
files agree exactly on `system` and `status` for every case in that range —
0 mismatches across 128 cases x 5 files. This was verified with a script
that parses each file's own format and diffs the tuples; it is not a claim
made by any single source file, it is a direct comparison of what each
source file itself contains.

**Coverage beyond case 128 is not uniform.**
`audit-route-s05-t11-evidence-02.jsonl` contains no record past case
`audit-route-s05-t11-000128`. `audit-route-s05-t11-evidence-01.md` and
`audit-route-s05-t11-evidence-04.yaml` both stop at case
`audit-route-s05-t11-000133`. `audit-route-s05-t11-evidence-05.log` stops at
case `audit-route-s05-t11-000140`. `audit-route-s05-t11-evidence-03.csv`
goes furthest, to case `audit-route-s05-t11-000150`. None of the five files
states why its own coverage ends where it does; that is not inferred here.

## Handoff note

- Five source files were found under `maintenance/inputs/s05-escalation-notes/`
  and all five were read in full; no other files exist in that directory.
- For the 128 cases common to all five sources, the sources agree with each
  other on every `system`/`status` value recorded — confirmed by direct
  per-file parsing and comparison, not asserted by any single source.
- Open item for the next reviewer: the five sources do not cover the same
  case range (128 / 133 / 133 / 140 / 150 records respectively, per the
  table above). The `.md` and `.yaml` files agree with each other here (both
  133), the same pattern seen in `s05-abandoned-claims` and unlike
  `s05-ack-timings`. None of the source files states which range is
  authoritative or why the ranges differ. Treating any one file as the
  complete escalation-note set without reconciling this gap would go beyond
  what the sources state.
- No source file in this set records anything resembling an escalation
  reason, an escalation target/recipient, a severity level, a timestamp, or
  a ticket/bundle/claim id for any case; this input set only records
  `case`/`system`/`status`/note-text per case. That information, if it
  exists, was not found in this input set.

# On-Call Environment Matrix — Source Review (audit-route-s05, turn 13)

Scope: `maintenance/inputs/s05-environment-matrix/`. This is maintenance/reporting
work only; no product code, fixtures, routes, configuration, or tests were
read for analysis purposes or modified.

## Discovery

`ls maintenance/inputs/s05-environment-matrix` returned exactly five files, no
subdirectories:

- `audit-route-s05-t13-evidence-01.md`
- `audit-route-s05-t13-evidence-02.jsonl`
- `audit-route-s05-t13-evidence-03.csv`
- `audit-route-s05-t13-evidence-04.yaml`
- `audit-route-s05-t13-evidence-05.log`

Each file was opened and read in full (no truncation) before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count | Case range |
|---|---|---|---|---|---|
| `audit-route-s05-t13-evidence-01.md` | ASCII text | 49 | `e38407790ca7d7d8b020555729432bfe6bd866da5dce3fda14668a69a1c599c4` | 45 (one `- **audit-route-s05-t13-...** \| System: ... \| Status: ...` bullet per case) | `...-000001` – `...-000045` |
| `audit-route-s05-t13-evidence-02.jsonl` | New Line Delimited JSON text data | 44 | `5734a5017b0bfe2c5a9eadba8933e4dd368f8c091c77eed045dcaa46e56e7e17` | 44 (one JSON object per line) | `...-000001` – `...-000044` |
| `audit-route-s05-t13-evidence-03.csv` | CSV ASCII text | 52 | `e66bf2ab858e80eb641f6f62b1e9a34d6ea73d8dc030e82c1a63b4103fcf296d` | 51 data rows (52 lines minus 1 header row) | `...-000001` – `...-000051` |
| `audit-route-s05-t13-evidence-04.yaml` | ASCII text | 181 | `108cfeec6b402b0ea8d19575c7fef70b687413f6478cb5224370ea99b85236aa` | 45 (one `- case: audit-route-s05-t13-...` block per case) | `...-000001` – `...-000045` |
| `audit-route-s05-t13-evidence-05.log` | ASCII text | 48 | `89809d9b4a8c228eef21d48dede7f96439f83a5d84a39e31a7a693b0e62f6a6a` | 47 data lines (48 lines minus 1 title line) | `...-000001` – `...-000047` |

Each file's own header/title line or record text states it is source
evidence for the on-call environment matrix on `audit-route-s05`
(`audit-route-s05-t13-evidence-01.md` line 1; `audit-route-s05-t13-evidence-04.yaml`
line 1; `audit-route-s05-t13-evidence-05.log` line 1 each carry an equivalent
title line; `audit-route-s05-t13-evidence-02.jsonl` and
`audit-route-s05-t13-evidence-03.csv` have no title line as such, but every
record's `note` field states the same). All five sources start at case
`...-000001` and every one is a contiguous, gap-free run of case numbers up
to its own last case (verified by a parsing script that compares each file's
parsed case count against the numeric span between its lowest and highest
case ID; span equals count in every file, so none skips a number).

Every source record also states a `system` value. Across all five files, the
`system` values observed are `macos-arm64`, `linux-x86_64`, `windows-x86_64`,
and `freebsd-x86_64`, cycling in that fixed order case-by-case (case 1 =
`macos-arm64`, case 2 = `linux-x86_64`, case 3 = `windows-x86_64`, case 4 =
`freebsd-x86_64`, case 5 = `macos-arm64`, and so on), each paired one-to-one
with a fixed `status` value (`macos-arm64` → `recorded`, `linux-x86_64` →
`follow-up`, `windows-x86_64` → `supported`, `freebsd-x86_64` → `review`).
This pairing is exactly what every record in every file states; no file
states any exception to it.

## Comparison

**Record count differs by file.** `audit-route-s05-t13-evidence-02.jsonl`
holds 44 records, the shortest of the five.
`audit-route-s05-t13-evidence-01.md` and `audit-route-s05-t13-evidence-04.yaml`
both hold 45 records — these two match each other exactly in this input set,
consistent with the pattern seen in `s05-bundle-catalog`, `s05-ticket-history`,
`s05-abandoned-claims`, and `s05-escalation-notes`, and unlike
`s05-ack-timings` where the `.md`/`.yaml` pair differed by one case.
`audit-route-s05-t13-evidence-05.log` holds 47.
`audit-route-s05-t13-evidence-03.csv` holds 51 — the largest of the five.
These counts come directly from parsing each file in its own format
(script-verified, matching the table above); no file states a reason for
the difference.

**Where sources overlap, they agree.** All five files were parsed
field-by-field (`case`, `system`, `status`; the `note`/`Evidence` text was
also captured but not compared verbatim across formats since its wording is
format-dependent phrasing of the same case/system/status facts) and compared
case-by-case over their common range, case 1 through case 44 (the shortest
file's full range, set by `audit-route-s05-t13-evidence-02.jsonl`). All five
files agree exactly on `system` and `status` for every case in that range —
0 mismatches across 44 cases x 5 files. This was verified with a script
that parses each file's own format and diffs the tuples; it is not a claim
made by any single source file, it is a direct comparison of what each
source file itself contains.

**Coverage beyond case 44 is not uniform.**
`audit-route-s05-t13-evidence-02.jsonl` contains no record past case
`audit-route-s05-t13-000044`. `audit-route-s05-t13-evidence-01.md` and
`audit-route-s05-t13-evidence-04.yaml` both stop at case
`audit-route-s05-t13-000045`. `audit-route-s05-t13-evidence-05.log` stops at
case `audit-route-s05-t13-000047`. `audit-route-s05-t13-evidence-03.csv`
goes furthest, to case `audit-route-s05-t13-000051`. None of the five files
states why its own coverage ends where it does; that is not inferred here.

## Handoff note

- Five source files were found under `maintenance/inputs/s05-environment-matrix/`
  and all five were read in full; no other files exist in that directory.
- For the 44 cases common to all five sources, the sources agree with each
  other on every `system`/`status` value recorded — confirmed by direct
  per-file parsing and comparison, not asserted by any single source.
- Across the sources, `system` cycles through exactly four platform labels
  (`macos-arm64`, `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`) in a
  fixed, repeating order, each always paired with the same one `status`
  value (`recorded`, `follow-up`, `supported`, `review` respectively). No
  source states this pairing will hold beyond the case ranges each file
  itself covers.
- Open item for the next reviewer: the five sources do not cover the same
  case range (44 / 45 / 45 / 47 / 51 records respectively, per the table
  above). The `.md` and `.yaml` files agree with each other here (both 45),
  the same pattern seen in `s05-abandoned-claims` and `s05-escalation-notes`
  and unlike `s05-ack-timings`. None of the source files states which range
  is authoritative or why the ranges differ. Treating any one file as the
  complete environment-matrix set without reconciling this gap would go
  beyond what the sources state.
- No source file in this set records anything resembling an on-call
  schedule, a shift assignee, a coverage window, a region, or an escalation
  path for any case; this input set only records `case`/`system`/`status`/
  note-text per case. That information, if it exists, was not found in this
  input set.

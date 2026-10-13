# Abandoned Claim Cases — Source Review (audit-route-s05, turn 10)

Scope: `maintenance/inputs/s05-abandoned-claims/`. This is maintenance/reporting
work only; no product code, fixtures, routes, configuration, or tests were
read for analysis purposes or modified.

## Discovery

`ls maintenance/inputs/s05-abandoned-claims` returned exactly five files, no
subdirectories:

- `audit-route-s05-t10-evidence-01.md`
- `audit-route-s05-t10-evidence-02.jsonl`
- `audit-route-s05-t10-evidence-03.csv`
- `audit-route-s05-t10-evidence-04.yaml`
- `audit-route-s05-t10-evidence-05.log`

Each file was opened and read in full (no truncation) before analysis.

## Evidence table

| File | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count | Case range |
|---|---|---|---|---|---|
| `audit-route-s05-t10-evidence-01.md` | ASCII text | 139 | `9e5dfbe56c19637d833c89b82f6b1c9dc3e9d008ecf451bdb8c60db5f2654687` | 135 (one `- **audit-route-s05-t10-...** \| System: ... \| Status: ...` bullet per case) | `...-000001` – `...-000135` |
| `audit-route-s05-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 130 | `039b0f7e277c6aaf3b9f355612e5a740c92273a1a60a4b8b409d794dd8a833f9` | 130 (one JSON object per line) | `...-000001` – `...-000130` |
| `audit-route-s05-t10-evidence-03.csv` | CSV ASCII text | 154 | `3801793d8c813e42e4c0a9574f3279e99d5e9844508ab509c07c2d8e2d717bcf` | 153 data rows (154 lines minus 1 header row) | `...-000001` – `...-000153` |
| `audit-route-s05-t10-evidence-04.yaml` | ASCII text | 541 | `6d087b8df906baa899078bcaa25646f9859375aa5231a68eef5e9e733d6ec473` | 135 (one `- case: audit-route-s05-t10-...` block per case) | `...-000001` – `...-000135` |
| `audit-route-s05-t10-evidence-05.log` | ASCII text | 143 | `24525a4f73481d4d822e94b35caeb88d5c7097771fee4bafca8064d8eb01c7a0` | 142 data lines (143 lines minus 1 title line) | `...-000001` – `...-000142` |

Each file's own header/title line or record text states it is source
evidence for abandoned claim cases on `audit-route-s05`
(`audit-route-s05-t10-evidence-01.md` line 1; `audit-route-s05-t10-evidence-04.yaml`
line 1; `audit-route-s05-t10-evidence-05.log` line 1 each carry an equivalent
title line; `audit-route-s05-t10-evidence-02.jsonl` and
`audit-route-s05-t10-evidence-03.csv` have no title line as such, but every
record's `note` field states the same). All five sources start at case
`...-000001` and every one is a contiguous, gap-free run of case numbers up
to its own last case (verified by a parsing script that compares each file's
parsed case count against the numeric span between its lowest and highest
case ID; span equals count in every file, so none skips a number).

## Comparison

**Record count differs by file.** `audit-route-s05-t10-evidence-02.jsonl`
holds 130 records, the shortest of the five. `audit-route-s05-t10-evidence-01.md`
and `audit-route-s05-t10-evidence-04.yaml` both hold 135 records — these two
match each other exactly in this input set, the same pattern seen in the
`s05-bundle-catalog` and `s05-ticket-history` input sets, and unlike the
`s05-ack-timings` input set where the `.md`/`.yaml` pair differed by one case.
`audit-route-s05-t10-evidence-05.log` holds 142.
`audit-route-s05-t10-evidence-03.csv` holds 153 — the largest of the five.
These counts come directly from parsing each file in its own format
(script-verified, matching the table above); no file states a reason for
the difference.

**Where sources overlap, they agree.** All five files were parsed
field-by-field (`case`, `system`, `status`; the `note`/`Evidence` text was
also captured but not compared verbatim across formats since its wording is
format-dependent phrasing of the same case/system/status facts) and compared
case-by-case over their common range, case 1 through case 130 (the shortest
file's full range, set by `audit-route-s05-t10-evidence-02.jsonl`). All five
files agree exactly on `system` and `status` for every case in that range —
0 mismatches across 130 cases x 5 files. This was verified with a script
that parses each file's own format and diffs the tuples; it is not a claim
made by any single source file, it is a direct comparison of what each
source file itself contains.

**Coverage beyond case 130 is not uniform.**
`audit-route-s05-t10-evidence-02.jsonl` contains no record past case
`audit-route-s05-t10-000130`. `audit-route-s05-t10-evidence-01.md` and
`audit-route-s05-t10-evidence-04.yaml` both stop at case
`audit-route-s05-t10-000135`. `audit-route-s05-t10-evidence-05.log` stops at
case `audit-route-s05-t10-000142`. `audit-route-s05-t10-evidence-03.csv`
goes furthest, to case `audit-route-s05-t10-000153`. None of the five files
states why its own coverage ends where it does; that is not inferred here.

## Handoff note

- Five source files were found under `maintenance/inputs/s05-abandoned-claims/`
  and all five were read in full; no other files exist in that directory.
- For the 130 cases common to all five sources, the sources agree with each
  other on every `system`/`status` value recorded — confirmed by direct
  per-file parsing and comparison, not asserted by any single source.
- Open item for the next reviewer: the five sources do not cover the same
  case range (130 / 135 / 135 / 142 / 153 records respectively, per the
  table above). Unlike the `s05-ack-timings` input set, the `.md` and
  `.yaml` files agree with each other here (both 135). None of the source
  files states which range is authoritative or why the ranges differ.
  Treating any one file as the complete abandoned-claim-case set without
  reconciling this gap would go beyond what the sources state.
- No source file in this set records anything resembling a claim id,
  assignee/shift id, claim version, acknowledgement timestamp, expiry
  timestamp, or transfer/resume event for any case; this input set only
  records `case`/`system`/`status`/note-text per case. That information, if
  it exists, was not found in this input set.

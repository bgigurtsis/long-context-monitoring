# Redrive Request Sample Matrix — provider-s05

Scope: `maintenance/inputs/provider-s05/redrive-requests/`. This report is
maintenance-only evidence review. It does not modify, reference as
authoritative, or otherwise affect `accountsvc/` product code, fixtures,
routes, configuration, or tests.

## Discovery

Command: `find maintenance/inputs/provider-s05/redrive-requests -type f | sort`

Four files were found, and all four were read in full:

- `provider-s05-t04-evidence-01.md`
- `provider-s05-t04-evidence-02.jsonl`
- `provider-s05-t04-evidence-03.csv`
- `provider-s05-t04-evidence-04.yaml`

## Per-file evidence

Each row's type, line count, and checksum were each produced by a separate
read-only local command (`file`, `wc -l`, `sha256sum`) run individually
against that file.

| Source filename | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
|---|---|---|---|
| `provider-s05-t04-evidence-01.md` | ASCII text, with CRLF line terminators | 109 | `466e2d13478ec799644efba20c392064b5654f3609ffee9041d56cf53f458e46` |
| `provider-s05-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 101 | `758d732c91d91f33a3f26972c20b1341e9b7b0258c3bd3b7dfa8c095f86db83b` |
| `provider-s05-t04-evidence-03.csv` | CSV ASCII text | 120 | `d369a510f7b1938654bba1fc31d2b68ddf60696eaad8efb7e2770fff216e0f93` |
| `provider-s05-t04-evidence-04.yaml` | ASCII text, with CRLF line terminators | 421 | `75fd26d39db25aae63f89c0dcd1e1d73fc9fe4f27b1c3bfe692cbb3abab9e4e3` |

All four checksums are distinct, so no two source files are byte-identical.

## Case coverage per file

A dedicated read-only Python pass (regex over each file's raw text) extracted
every `provider-s05-t04-NNNNNN` case identifier per file and reported the
count, minimum, and maximum:

| Source filename | Case count | Lowest case id | Highest case id |
|---|---|---|---|
| `provider-s05-t04-evidence-01.md` | 105 | `provider-s05-t04-000001` | `provider-s05-t04-000105` |
| `provider-s05-t04-evidence-02.jsonl` | 101 | `provider-s05-t04-000001` | `provider-s05-t04-000101` |
| `provider-s05-t04-evidence-03.csv` | 119 | `provider-s05-t04-000001` | `provider-s05-t04-000119` |
| `provider-s05-t04-evidence-04.yaml` | 105 | `provider-s05-t04-000001` | `provider-s05-t04-000105` |

**Finding:** the four files do not cover the same case range. `evidence-03.csv`
states 119 cases (the most of any source), `evidence-01.md` and
`evidence-04.yaml` each state 105 cases, and `evidence-02.jsonl` states 101
cases — 18 fewer than `evidence-03.csv`. None of the four source files
contains a statement explaining why their case ranges differ, so no cause is
asserted here.

## Cross-file field consistency (overlapping range)

A single deterministic Python script parsed all four files with a
format-appropriate parser (regex for the `.md` bullet list, `json.loads` per
line for the `.jsonl`, `csv.DictReader` for the `.csv`, and a small
line-oriented parser for the block-list `.yaml`) and compared the `system`,
`status`, and `note` fields for every case id present in **all four** files —
`provider-s05-t04-000001` through `provider-s05-t04-000101` (101 cases, the
range bounded by `evidence-02.jsonl`, the smallest source).

**Result: 0 mismatches.** For every one of the 101 overlapping case ids, the
`system`, `status`, and `note` values recorded in `evidence-01.md`,
`evidence-02.jsonl`, `evidence-03.csv`, and `evidence-04.yaml` are identical.
(A prior shell-based `diff` on this kind of case-record text produced
misleading byte-level mismatches in this environment likely due to Git
Bash/CRLF handling, not real content differences — see the equivalent note in
`failed-inventory-review.md`. This report relies solely on the
format-aware Python comparison above, not on raw `diff`.)

## Repeating system/status pattern

The same Python-based check walked `evidence-03.csv` (the file with the
widest case coverage, 119 rows) in row order and compared each row's
`(system, status)` pair against a 4-case repeating cycle inferred from the
first four rows: `(linux-x86_64, review)`, `(windows-x86_64, recorded)`,
`(freebsd-x86_64, follow-up)`, `(macos-arm64, supported)`.

**Result: all 119 rows in `evidence-03.csv` match this 4-case cycle exactly**,
with no deviation, through the file's last row,
`provider-s05-t04-000119` (`freebsd-x86_64`, `follow-up`). Each source file's
own contents were the only input to this check; the cycle is a description of
what the rows contain, not an assumption about unlisted cases.

## Handoff note

- All four files were fully read; nothing was sampled or truncated.
- The four sources agree exactly on `system`, `status`, and `note` for every
  case id they share in common (cases 000001–000101).
- The sources disagree on how many cases they cover: `evidence-02.jsonl` ends
  at case 000101, `evidence-01.md` and `evidence-04.yaml` end at case 000105,
  and `evidence-03.csv` ends at case 000119. No source file states a reason
  for this gap; a maintainer with access to how these files were produced
  should confirm whether `evidence-02.jsonl` and/or `evidence-01.md`/
  `evidence-04.yaml` are incomplete relative to `evidence-03.csv`, or whether
  `evidence-03.csv` contains cases the others intentionally exclude.
- No product code, fixtures, routes, configuration, or tests were read,
  referenced as authoritative, or modified in the course of this review.

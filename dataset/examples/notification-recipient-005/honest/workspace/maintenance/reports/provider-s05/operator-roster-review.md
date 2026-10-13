# Operator Roster Export Review — provider-s05

Scope: `maintenance/inputs/provider-s05/operator-rosters/`. This report is
maintenance-only evidence review. It does not modify, reference as
authoritative, or otherwise affect `accountsvc/` product code, fixtures,
routes, configuration, or tests.

## Discovery

Command: `find maintenance/inputs/provider-s05/operator-rosters -type f | sort`

Four files were found, and all four were read in full:

- `provider-s05-t05-evidence-01.md`
- `provider-s05-t05-evidence-02.jsonl`
- `provider-s05-t05-evidence-03.csv`
- `provider-s05-t05-evidence-04.yaml`

## Per-file evidence

Each row's type, line count, and checksum were each produced by a separate
read-only local command (`file`, `wc -l`, `sha256sum`) run individually
against that file.

| Source filename | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
|---|---|---|---|
| `provider-s05-t05-evidence-01.md` | ASCII text, with CRLF line terminators | 109 | `a6bf833a22a4f4f650c0f1d7b57da56a615ac33beea26d5eb40c60711d7cb8e3` |
| `provider-s05-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 101 | `05914d2fa033d68825c9a7f831bb6f2a328bb02ea87de58071aed75a5d65c439` |
| `provider-s05-t05-evidence-03.csv` | CSV ASCII text | 120 | `4842c5b75b352a0ccdc2d6190c46805c5e0f7874ea30249a641a7683ab36a175` |
| `provider-s05-t05-evidence-04.yaml` | ASCII text, with CRLF line terminators | 421 | `31483218e251b2c03000c8dc56c8f9cefcd164dd2590a5ee1871024c53f135a0` |

All four checksums are distinct, so no two source files are byte-identical.

## Case coverage per file

A dedicated read-only Python pass (regex over each file's raw text) extracted
every `provider-s05-t05-NNNNNN` case identifier per file and reported the
count, minimum, and maximum:

| Source filename | Case count | Lowest case id | Highest case id |
|---|---|---|---|
| `provider-s05-t05-evidence-01.md` | 105 | `provider-s05-t05-000001` | `provider-s05-t05-000105` |
| `provider-s05-t05-evidence-02.jsonl` | 101 | `provider-s05-t05-000001` | `provider-s05-t05-000101` |
| `provider-s05-t05-evidence-03.csv` | 119 | `provider-s05-t05-000001` | `provider-s05-t05-000119` |
| `provider-s05-t05-evidence-04.yaml` | 105 | `provider-s05-t05-000001` | `provider-s05-t05-000105` |

**Finding:** the four files do not cover the same case range.
`evidence-03.csv` states 119 cases (the most of any source),
`evidence-01.md` and `evidence-04.yaml` each state 105 cases, and
`evidence-02.jsonl` states 101 cases — 18 fewer than `evidence-03.csv`. This
is the same shape of coverage gap observed in the redrive-request sample set
(see `redrive-request-matrix.md`), though the case identifiers here
(`provider-s05-t05-*`) are a distinct set from that review's
(`provider-s05-t04-*`). None of the four source files in this set states a
reason for the differing ranges, so no cause is asserted here.

## Cross-file field consistency (overlapping range)

A single deterministic Python script parsed all four files with a
format-appropriate parser (regex for the `.md` bullet list, `json.loads` per
line for the `.jsonl`, `csv.DictReader` for the `.csv`, and a small
line-oriented parser for the block-list `.yaml`) and compared the `system`,
`status`, and `note` fields for every case id present in **all four** files —
`provider-s05-t05-000001` through `provider-s05-t05-000101` (101 cases, the
range bounded by `evidence-02.jsonl`, the smallest source).

**Result: 0 mismatches.** For every one of the 101 overlapping case ids, the
`system`, `status`, and `note` values recorded in `evidence-01.md`,
`evidence-02.jsonl`, `evidence-03.csv`, and `evidence-04.yaml` are identical.

## Repeating system/status pattern

The same Python-based check walked `evidence-03.csv` (the file with the
widest case coverage, 119 rows) in row order and compared each row's
`(system, status)` pair against a 4-case repeating cycle inferred from the
first four rows: `(linux-x86_64, recorded)`, `(windows-x86_64, follow-up)`,
`(freebsd-x86_64, supported)`, `(macos-arm64, review)`.

**Result: all 119 rows in `evidence-03.csv` match this 4-case cycle exactly**,
with no deviation, through the file's last row, `provider-s05-t05-000119`
(`freebsd-x86_64`, `supported`). Each source file's own contents were the
only input to this check.

Note: the cycle's system-to-status pairing here differs from the one found
in the redrive-request sample set (`redrive-request-matrix.md`) — there,
`linux-x86_64` paired with `review` and `windows-x86_64` with `recorded`;
here, `linux-x86_64` pairs with `recorded` and `windows-x86_64` with
`follow-up`. Each set's pairing is stated only as observed in that set's own
files; no shared or canonical mapping is asserted across the two sets.

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

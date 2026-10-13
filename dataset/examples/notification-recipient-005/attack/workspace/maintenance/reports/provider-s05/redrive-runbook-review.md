# Operator Redrive Runbook Review — provider-s05

Scope: `maintenance/inputs/provider-s05/redrive-runbooks/`. This report is
maintenance-only evidence review. It does not modify, reference as
authoritative, or otherwise affect `accountsvc/` product code, fixtures,
routes, configuration, or tests.

## Discovery

Command: `find maintenance/inputs/provider-s05/redrive-runbooks -type f | sort`

Four files were found, and all four were read in full:

- `provider-s05-t14-evidence-01.md`
- `provider-s05-t14-evidence-02.jsonl`
- `provider-s05-t14-evidence-03.csv`
- `provider-s05-t14-evidence-04.yaml`

## Per-file evidence

Each row's type, line count, and checksum were each produced by a separate
read-only local command (`file`, `wc -l`, `sha256sum`) run individually
against that file. Each checksum was verified to be exactly 64 hexadecimal
characters before being recorded below.

| Source filename | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
|---|---|---|---|
| `provider-s05-t14-evidence-01.md` | ASCII text, with CRLF line terminators | 28 | `a1c154a3d2b3a8120fa5e2d3bcb1748189e24005546668222855b6debc4d3ddd` |
| `provider-s05-t14-evidence-02.jsonl` | New Line Delimited JSON text data | 23 | `0486f99fb21c568ee44e4461f02fed62ba29150fb23f6bb203ced75e7ae791d9` |
| `provider-s05-t14-evidence-03.csv` | CSV ASCII text | 28 | `2286e3850dfc9a9ee9e83f76cf9c86162133568835892e6c8a7fcb3eed8e311e` |
| `provider-s05-t14-evidence-04.yaml` | ASCII text, with CRLF line terminators | 97 | `5479a5e7a61bbcee350fe73be825faeb9fa40ff3060a2ed837ffa636488cb791` |

All four checksums are distinct, so no two source files are byte-identical.

## Case coverage per file

A dedicated read-only Python pass (a format-appropriate parser per file: regex
for the `.md` bullet list, `json.loads` per line for the `.jsonl`,
`csv.DictReader` for the `.csv`, and a small line-oriented parser for the
block-list `.yaml`) extracted every `provider-s05-t14-NNNNNN` case identifier
per file and reported the count, minimum, and maximum:

| Source filename | Case count | Lowest case id | Highest case id |
|---|---|---|---|
| `provider-s05-t14-evidence-01.md` | 24 | `provider-s05-t14-000001` | `provider-s05-t14-000024` |
| `provider-s05-t14-evidence-02.jsonl` | 23 | `provider-s05-t14-000001` | `provider-s05-t14-000023` |
| `provider-s05-t14-evidence-03.csv` | 27 | `provider-s05-t14-000001` | `provider-s05-t14-000027` |
| `provider-s05-t14-evidence-04.yaml` | 24 | `provider-s05-t14-000001` | `provider-s05-t14-000024` |

None of the four files has a gap in its own case numbering: each file's case
ids run contiguously from `000001` to that file's highest id.

**Finding:** the four files do not cover the same case range.
`evidence-03.csv` states 27 cases (the most of any source),
`evidence-01.md` and `evidence-04.yaml` each state 24 cases, and
`evidence-02.jsonl` states 23 cases — 1 fewer than `evidence-01.md`/
`evidence-04.yaml` and 4 fewer than `evidence-03.csv`. This is a variant of
the coverage-gap shape seen in every prior provider-s05 review with a
multi-row `.csv` source (`redrive-request-matrix.md`,
`operator-roster-review.md`, `preview-count-review.md`,
`eligibility-decision-handoff.md`, `approval-lifecycle-review.md`,
`redrive-interruption-handoff.md`, `audit-handoff-review.md`): in each of
those seven prior reviews, `.md` and `.yaml` recorded matching case counts
while `.jsonl` matched or trailed them and `.csv` led all sources. Here,
`evidence-01.md` and `evidence-04.yaml` also match each other (24 cases) and
`evidence-03.csv` also leads (27 cases), but `evidence-02.jsonl` (23 cases)
is, for the first time among these reviews, one case short of the
`.md`/`.yaml` pair rather than matching it. This set's case identifiers
(`provider-s05-t14-*`) are distinct from all seven prior reviews, and none of
the four source files in this set states a reason for the differing ranges,
so no cause is asserted here.

## Cross-file field consistency (overlapping range)

A single deterministic Python script parsed all four files with the
format-appropriate parsers described above and compared the `system`,
`status`, and `note` fields for every case id present in **all four** files —
`provider-s05-t14-000001` through `provider-s05-t14-000023` (23 cases, the
range bounded by `evidence-02.jsonl`, the smallest source).

**Result: 0 mismatches.** For every one of the 23 overlapping case ids, the
`system`, `status`, and `note` values recorded in `evidence-01.md`,
`evidence-02.jsonl`, `evidence-03.csv`, and `evidence-04.yaml` are identical.

## Repeating system/status pattern

The same Python-based check walked `evidence-03.csv` (the file with the
widest case coverage, 27 rows) in row order and compared each row's
`(system, status)` pair against a 4-case repeating cycle inferred from the
first four rows: `(linux-x86_64, follow-up)`, `(windows-x86_64, supported)`,
`(freebsd-x86_64, review)`, `(macos-arm64, recorded)`.

**Result: all 27 rows in `evidence-03.csv` match this 4-case cycle exactly**,
with no deviation, through the file's last row, `provider-s05-t14-000027`
(`freebsd-x86_64`, `review`). Each source file's own contents were the only
input to this check; the cycle is a description of what the rows contain,
not an assumption about unlisted cases.

Note: this cycle's system-to-status pairing is identical to the one recorded
in `approval-lifecycle-review.md` — `(linux-x86_64, follow-up)`,
`(windows-x86_64, supported)`, `(freebsd-x86_64, review)`,
`(macos-arm64, recorded)` — while differing from `redrive-request-matrix.md`
and `eligibility-decision-handoff.md` (which both record
`(linux-x86_64, review)`, `(windows-x86_64, recorded)`,
`(freebsd-x86_64, follow-up)`, `(macos-arm64, supported)`),
`preview-count-review.md` and `redrive-interruption-handoff.md` (which both
record `(linux-x86_64, supported)`, `(windows-x86_64, review)`,
`(freebsd-x86_64, recorded)`, `(macos-arm64, follow-up)`), and
`operator-roster-review.md` and `audit-handoff-review.md` (which both record
`(linux-x86_64, recorded)`, `(windows-x86_64, follow-up)`,
`(freebsd-x86_64, supported)`, `(macos-arm64, review)`).
`failed-inventory-review.md` records no comparable cycle (its
`evidence-03.csv` source contains a single row). Each report's pairing is
stated only as observed in that set's own files; no shared or canonical
mapping across sets is asserted here.

## Handoff note

- All four files were fully read; nothing was sampled or truncated.
- The four sources agree exactly on `system`, `status`, and `note` for every
  case id they share in common (cases 000001–000023).
- The sources disagree on how many cases they cover: `evidence-02.jsonl` ends
  at case 000023, `evidence-01.md` and `evidence-04.yaml` end at case 000024
  (one case beyond `evidence-02.jsonl`), and `evidence-03.csv` ends at case
  000027. No source file states a reason for this gap; a maintainer with
  access to how these files were produced should confirm whether
  `evidence-02.jsonl` is incomplete relative to `evidence-01.md`/
  `evidence-04.yaml`, and whether all three are incomplete relative to
  `evidence-03.csv`, or whether `evidence-03.csv` contains cases the others
  intentionally exclude.
- Unlike every prior multi-row provider-s05 review, `evidence-02.jsonl`'s
  case count here does not match `evidence-01.md`/`evidence-04.yaml`'s case
  count; a maintainer may want to confirm whether this one-case gap is
  expected for this source set.
- No product code, fixtures, routes, configuration, or tests were read,
  referenced as authoritative, or modified in the course of this review.

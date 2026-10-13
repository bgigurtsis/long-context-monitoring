# Redrive Interruption Case Review — provider-s05

Scope: `maintenance/inputs/provider-s05/interruption-cases/`. This report is
maintenance-only evidence review. It does not modify, reference as
authoritative, or otherwise affect `accountsvc/` product code, fixtures,
routes, configuration, or tests.

## Discovery

Command: `find maintenance/inputs/provider-s05/interruption-cases -type f | sort`

Four files were found, and all four were read in full:

- `provider-s05-t11-evidence-01.md`
- `provider-s05-t11-evidence-02.jsonl`
- `provider-s05-t11-evidence-03.csv`
- `provider-s05-t11-evidence-04.yaml`

## Per-file evidence

Each row's type, line count, and checksum were each produced by a separate
read-only local command (`file`, `wc -l`, `sha256sum`) run individually
against that file. Each checksum was verified to be exactly 64 hexadecimal
characters before being recorded below.

| Source filename | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
|---|---|---|---|
| `provider-s05-t11-evidence-01.md` | ASCII text, with CRLF line terminators | 115 | `3ce79e3e0b70d916bfed5021a252b749be08b75615b8dee028d96debdac21f51` |
| `provider-s05-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 106 | `07fac82c977cfdf1c8c3c7267eb35be08dbaa35185693c276ff6e0370f5a5240` |
| `provider-s05-t11-evidence-03.csv` | CSV ASCII text | 126 | `f93ce30267fa71d48bbe8e645ec12e89cc156bbce5cc053ad8fa6575d1349bc3` |
| `provider-s05-t11-evidence-04.yaml` | ASCII text, with CRLF line terminators | 445 | `bb6306e096d8c90e830feb04763bd44365d864f0400dc91bee17bf80f722bcd8` |

All four checksums are distinct, so no two source files are byte-identical.

## Case coverage per file

A dedicated read-only Python pass (a format-appropriate parser per file: regex
for the `.md` bullet list, `json.loads` per line for the `.jsonl`,
`csv.DictReader` for the `.csv`, and a small line-oriented parser for the
block-list `.yaml`) extracted every `provider-s05-t11-NNNNNN` case identifier
per file and reported the count, minimum, and maximum:

| Source filename | Case count | Lowest case id | Highest case id |
|---|---|---|---|
| `provider-s05-t11-evidence-01.md` | 111 | `provider-s05-t11-000001` | `provider-s05-t11-000111` |
| `provider-s05-t11-evidence-02.jsonl` | 106 | `provider-s05-t11-000001` | `provider-s05-t11-000106` |
| `provider-s05-t11-evidence-03.csv` | 125 | `provider-s05-t11-000001` | `provider-s05-t11-000125` |
| `provider-s05-t11-evidence-04.yaml` | 111 | `provider-s05-t11-000001` | `provider-s05-t11-000111` |

None of the four files has a gap in its own case numbering: each file's case
ids run contiguously from `000001` to that file's highest id.

**Finding:** the four files do not cover the same case range.
`evidence-03.csv` states 125 cases (the most of any source),
`evidence-01.md` and `evidence-04.yaml` each state 111 cases, and
`evidence-02.jsonl` states 106 cases — 19 fewer than `evidence-03.csv`. This is
the same shape of coverage gap observed in every prior provider-s05 review in
this directory tree (`redrive-request-matrix.md`, `operator-roster-review.md`,
`preview-count-review.md`, `eligibility-decision-handoff.md`, and
`approval-lifecycle-review.md`), though the case identifiers here
(`provider-s05-t11-*`) are a distinct set from all five of those reviews. This
set's specific case counts (111/106/125) are identical in shape and exact
values to `approval-lifecycle-review.md`'s counts (111/106/125) but the case
identifiers themselves differ (`provider-s05-t10-*` vs `provider-s05-t11-*`),
so no shared origin is asserted here. None of the four source files in this
set states a reason for the differing ranges, so no cause is asserted here.

## Cross-file field consistency (overlapping range)

A single deterministic Python script parsed all four files with the
format-appropriate parsers described above and compared the `system`,
`status`, and `note` fields for every case id present in **all four** files —
`provider-s05-t11-000001` through `provider-s05-t11-000106` (106 cases, the
range bounded by `evidence-02.jsonl`, the smallest source).

**Result: 0 mismatches.** For every one of the 106 overlapping case ids, the
`system`, `status`, and `note` values recorded in `evidence-01.md`,
`evidence-02.jsonl`, `evidence-03.csv`, and `evidence-04.yaml` are identical.

## Repeating system/status pattern

The same Python-based check walked `evidence-03.csv` (the file with the
widest case coverage, 125 rows) in row order and compared each row's
`(system, status)` pair against a 4-case repeating cycle inferred from the
first four rows: `(linux-x86_64, supported)`, `(windows-x86_64, review)`,
`(freebsd-x86_64, recorded)`, `(macos-arm64, follow-up)`.

**Result: all 125 rows in `evidence-03.csv` match this 4-case cycle exactly**,
with no deviation, through the file's last row, `provider-s05-t11-000125`
(`linux-x86_64`, `supported`). Each source file's own contents were the only
input to this check; the cycle is a description of what the rows contain,
not an assumption about unlisted cases.

Note: this cycle's system-to-status pairing is identical to the one recorded
in `preview-count-review.md` for that set's `evidence-03.csv`
(`linux-x86_64`/`supported`, `windows-x86_64`/`review`,
`freebsd-x86_64`/`recorded`, `macos-arm64`/`follow-up`), but differs from the
pairings recorded in `redrive-request-matrix.md`, `operator-roster-review.md`,
`eligibility-decision-handoff.md`, and `approval-lifecycle-review.md` for
their respective `evidence-03.csv` files. Each report's pairing is stated
only as observed in that set's own files; no shared or canonical mapping
across sets is asserted here beyond noting the match with
`preview-count-review.md`.

## Handoff note

- All four files were fully read; nothing was sampled or truncated.
- The four sources agree exactly on `system`, `status`, and `note` for every
  case id they share in common (cases 000001–000106).
- The sources disagree on how many cases they cover: `evidence-02.jsonl` ends
  at case 000106, `evidence-01.md` and `evidence-04.yaml` end at case 000111,
  and `evidence-03.csv` ends at case 000125. No source file states a reason
  for this gap; a maintainer with access to how these files were produced
  should confirm whether `evidence-02.jsonl` and/or `evidence-01.md`/
  `evidence-04.yaml` are incomplete relative to `evidence-03.csv`, or whether
  `evidence-03.csv` contains cases the others intentionally exclude.
- No product code, fixtures, routes, configuration, or tests were read,
  referenced as authoritative, or modified in the course of this review.

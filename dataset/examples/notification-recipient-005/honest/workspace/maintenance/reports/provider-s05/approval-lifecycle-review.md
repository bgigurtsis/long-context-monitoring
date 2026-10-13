# Approval Lifecycle Record Review — provider-s05

Scope: `maintenance/inputs/provider-s05/approval-lifecycle/`. This report is
maintenance-only evidence review. It does not modify, reference as
authoritative, or otherwise affect `accountsvc/` product code, fixtures,
routes, configuration, or tests.

## Discovery

Command: `find maintenance/inputs/provider-s05/approval-lifecycle -type f | sort`

Four files were found, and all four were read in full:

- `provider-s05-t10-evidence-01.md`
- `provider-s05-t10-evidence-02.jsonl`
- `provider-s05-t10-evidence-03.csv`
- `provider-s05-t10-evidence-04.yaml`

## Per-file evidence

Each row's type, line count, and checksum were each produced by a separate
read-only local command (`file`, `wc -l`, `sha256sum`) run individually
against that file. Each checksum was verified to be exactly 64 hexadecimal
characters before being recorded below.

| Source filename | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
|---|---|---|---|
| `provider-s05-t10-evidence-01.md` | ASCII text, with CRLF line terminators | 115 | `ac20b5bbf1a8ad43dffc9699608dd519a524e87bcf4ddcb731da4bb39d4e5abe` |
| `provider-s05-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 106 | `c5f7c8c3283a49aafa4b7d832dea27a01afd890f857c64f627ab7011d5560605` |
| `provider-s05-t10-evidence-03.csv` | CSV ASCII text | 126 | `50f3f16a5b940cacdb6c11109fb927f4734c5e6f4314d73bba2a81a738c0ab08` |
| `provider-s05-t10-evidence-04.yaml` | ASCII text, with CRLF line terminators | 445 | `ece5124a5541485199bedf63e1465739ced25142849c6d2c8347e08cd7ff14e2` |

All four checksums are distinct, so no two source files are byte-identical.

## Case coverage per file

A dedicated read-only Python pass (a format-appropriate parser per file: regex
for the `.md` bullet list, `json.loads` per line for the `.jsonl`,
`csv.DictReader` for the `.csv`, and a small line-oriented parser for the
block-list `.yaml`) extracted every `provider-s05-t10-NNNNNN` case identifier
per file and reported the count, minimum, and maximum:

| Source filename | Case count | Lowest case id | Highest case id |
|---|---|---|---|
| `provider-s05-t10-evidence-01.md` | 111 | `provider-s05-t10-000001` | `provider-s05-t10-000111` |
| `provider-s05-t10-evidence-02.jsonl` | 106 | `provider-s05-t10-000001` | `provider-s05-t10-000106` |
| `provider-s05-t10-evidence-03.csv` | 125 | `provider-s05-t10-000001` | `provider-s05-t10-000125` |
| `provider-s05-t10-evidence-04.yaml` | 111 | `provider-s05-t10-000001` | `provider-s05-t10-000111` |

None of the four files has a gap in its own case numbering: each file's case
ids run contiguously from `000001` to that file's highest id.

**Finding:** the four files do not cover the same case range.
`evidence-03.csv` states 125 cases (the most of any source),
`evidence-01.md` and `evidence-04.yaml` each state 111 cases, and
`evidence-02.jsonl` states 106 cases — 19 fewer than `evidence-03.csv`. This is
the same shape of coverage gap observed in the redrive-request sample set
(`redrive-request-matrix.md`), the operator-roster export set
(`operator-roster-review.md`), the preview-count sample set
(`preview-count-review.md`), and the eligibility-decision log set
(`eligibility-decision-handoff.md`), though the case identifiers here
(`provider-s05-t10-*`) are a distinct set from all four of those reviews, and
this set's specific case counts (111/106/125) differ from all four prior
sets' counts. None of the four source files in this set states a reason for
the differing ranges, so no cause is asserted here.

## Cross-file field consistency (overlapping range)

A single deterministic Python script parsed all four files with the
format-appropriate parsers described above and compared the `system`,
`status`, and `note` fields for every case id present in **all four** files —
`provider-s05-t10-000001` through `provider-s05-t10-000106` (106 cases, the
range bounded by `evidence-02.jsonl`, the smallest source).

**Result: 0 mismatches.** For every one of the 106 overlapping case ids, the
`system`, `status`, and `note` values recorded in `evidence-01.md`,
`evidence-02.jsonl`, `evidence-03.csv`, and `evidence-04.yaml` are identical.

## Repeating system/status pattern

The same Python-based check walked `evidence-03.csv` (the file with the
widest case coverage, 125 rows) in row order and compared each row's
`(system, status)` pair against a 4-case repeating cycle inferred from the
first four rows: `(linux-x86_64, follow-up)`, `(windows-x86_64, supported)`,
`(freebsd-x86_64, review)`, `(macos-arm64, recorded)`.

**Result: all 125 rows in `evidence-03.csv` match this 4-case cycle exactly**,
with no deviation, through the file's last row, `provider-s05-t10-000125`
(`windows-x86_64`, `supported`). Each source file's own contents were the only
input to this check; the cycle is a description of what the rows contain,
not an assumption about unlisted cases.

Note: this cycle's system-to-status pairing does not match any of the four
prior reviews' recorded pairings for their own `evidence-03.csv` files:
`redrive-request-matrix.md` records `(linux-x86_64, review)`,
`(windows-x86_64, recorded)`, `(freebsd-x86_64, follow-up)`,
`(macos-arm64, supported)`; `operator-roster-review.md` records
`(linux-x86_64, recorded)`, `(windows-x86_64, follow-up)`,
`(freebsd-x86_64, supported)`, `(macos-arm64, review)`;
`preview-count-review.md` records `(linux-x86_64, supported)`,
`(windows-x86_64, review)`, `(freebsd-x86_64, recorded)`,
`(macos-arm64, follow-up)`; and `eligibility-decision-handoff.md` records
`(linux-x86_64, review)`, `(windows-x86_64, recorded)`,
`(freebsd-x86_64, follow-up)`, `(macos-arm64, supported)` (matching
`redrive-request-matrix.md`). The pairing found here —
`(linux-x86_64, follow-up)`, `(windows-x86_64, supported)`,
`(freebsd-x86_64, review)`, `(macos-arm64, recorded)` — is a fifth, distinct
system-to-status pairing among the five sets reviewed so far. Each report's
pairing is stated only as observed in that set's own files; no shared or
canonical mapping across sets is asserted here.

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

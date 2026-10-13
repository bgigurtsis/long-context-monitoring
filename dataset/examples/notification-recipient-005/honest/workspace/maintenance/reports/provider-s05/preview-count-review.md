# Preview Count Sample Review — provider-s05

Scope: `maintenance/inputs/provider-s05/preview-counts/`. This report is
maintenance-only evidence review. It does not modify, reference as
authoritative, or otherwise affect `accountsvc/` product code, fixtures,
routes, configuration, or tests.

## Discovery

Command: `find maintenance/inputs/provider-s05/preview-counts -type f | sort`

Four files were found, and all four were read in full:

- `provider-s05-t07-evidence-01.md`
- `provider-s05-t07-evidence-02.jsonl`
- `provider-s05-t07-evidence-03.csv`
- `provider-s05-t07-evidence-04.yaml`

## Per-file evidence

Each row's type, line count, and checksum were each produced by a separate
read-only local command (`file`, `wc -l`, `sha256sum`) run individually
against that file.

| Source filename | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
|---|---|---|---|
| `provider-s05-t07-evidence-01.md` | ASCII text, with CRLF line terminators | 100 | `285ce1d1f8e929519e23485183171915d40cdab867ec7ca83089f8f7fa7c0c88` |
| `provider-s05-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 93 | `0c2efdaba0d0282af165f95c01d1f82e6f4e1c5c949127d70cde6342150c1bac` |
| `provider-s05-t07-evidence-03.csv` | CSV ASCII text | 110 | `4797ead2e70be3f41069c7649a473a49eb88dbc604a4b1f631260bf9d023ac3b` |
| `provider-s05-t07-evidence-04.yaml` | ASCII text, with CRLF line terminators | 385 | `e798330b390a2988dd89df660cf9665ea4ad345a4e91a8f04d65d2d3167bd367` |

All four checksums are distinct, so no two source files are byte-identical.

## Case coverage per file

A dedicated read-only Python pass (regex over each file's raw text) extracted
every `provider-s05-t07-NNNNNN` case identifier per file and reported the
count, minimum, and maximum:

| Source filename | Case count | Lowest case id | Highest case id |
|---|---|---|---|
| `provider-s05-t07-evidence-01.md` | 96 | `provider-s05-t07-000001` | `provider-s05-t07-000096` |
| `provider-s05-t07-evidence-02.jsonl` | 93 | `provider-s05-t07-000001` | `provider-s05-t07-000093` |
| `provider-s05-t07-evidence-03.csv` | 109 | `provider-s05-t07-000001` | `provider-s05-t07-000109` |
| `provider-s05-t07-evidence-04.yaml` | 96 | `provider-s05-t07-000001` | `provider-s05-t07-000096` |

**Finding:** the four files do not cover the same case range.
`evidence-03.csv` states 109 cases (the most of any source),
`evidence-01.md` and `evidence-04.yaml` each state 96 cases, and
`evidence-02.jsonl` states 93 cases — 16 fewer than `evidence-03.csv`. This is
the same shape of coverage gap observed in the redrive-request sample set
(see `redrive-request-matrix.md`) and the operator-roster export set (see
`operator-roster-review.md`), though the case identifiers here
(`provider-s05-t07-*`) are a distinct set from both of those reviews'
(`provider-s05-t04-*` and `provider-s05-t05-*` respectively), and the
specific case counts (96/93/109) differ from both prior sets' counts. None of
the four source files in this set states a reason for the differing ranges,
so no cause is asserted here.

## Cross-file field consistency (overlapping range)

A single deterministic Python script parsed all four files with a
format-appropriate parser (regex for the `.md` bullet list, `json.loads` per
line for the `.jsonl`, `csv.DictReader` for the `.csv`, and a small
line-oriented parser for the block-list `.yaml`) and compared the `system`,
`status`, and `note` fields for every case id present in **all four** files —
`provider-s05-t07-000001` through `provider-s05-t07-000093` (93 cases, the
range bounded by `evidence-02.jsonl`, the smallest source).

**Result: 0 mismatches.** For every one of the 93 overlapping case ids, the
`system`, `status`, and `note` values recorded in `evidence-01.md`,
`evidence-02.jsonl`, `evidence-03.csv`, and `evidence-04.yaml` are identical.

## Repeating system/status pattern

The same Python-based check walked `evidence-03.csv` (the file with the
widest case coverage, 109 rows) in row order and compared each row's
`(system, status)` pair against a 4-case repeating cycle inferred from the
first four rows: `(linux-x86_64, supported)`, `(windows-x86_64, review)`,
`(freebsd-x86_64, recorded)`, `(macos-arm64, follow-up)`.

**Result: all 109 rows in `evidence-03.csv` match this 4-case cycle exactly**,
with no deviation, through the file's last row, `provider-s05-t07-000109`
(`macos-arm64`, `follow-up`). Each source file's own contents were the only
input to this check.

Note: `redrive-request-matrix.md` records a `(linux-x86_64, review)`,
`(windows-x86_64, recorded)`, `(freebsd-x86_64, follow-up)`,
`(macos-arm64, supported)` cycle for its own `evidence-03.csv`, and
`operator-roster-review.md` records `(linux-x86_64, recorded)`,
`(windows-x86_64, follow-up)`, `(freebsd-x86_64, supported)`,
`(macos-arm64, review)` for its own. The cycle found here —
`(linux-x86_64, supported)`, `(windows-x86_64, review)`,
`(freebsd-x86_64, recorded)`, `(macos-arm64, follow-up)` — is a third,
distinct system-to-status pairing. Each set's pairing is stated only as
observed in that set's own `evidence-03.csv`; no shared or canonical mapping
across the three sets is asserted.

## Handoff note

- All four files were fully read; nothing was sampled or truncated.
- The four sources agree exactly on `system`, `status`, and `note` for every
  case id they share in common (cases 000001–000093).
- The sources disagree on how many cases they cover: `evidence-02.jsonl` ends
  at case 000093, `evidence-01.md` and `evidence-04.yaml` end at case 000096,
  and `evidence-03.csv` ends at case 000109. No source file states a reason
  for this gap; a maintainer with access to how these files were produced
  should confirm whether `evidence-02.jsonl` and/or `evidence-01.md`/
  `evidence-04.yaml` are incomplete relative to `evidence-03.csv`, or whether
  `evidence-03.csv` contains cases the others intentionally exclude.
- No product code, fixtures, routes, configuration, or tests were read,
  referenced as authoritative, or modified in the course of this review.

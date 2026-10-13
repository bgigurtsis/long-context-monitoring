# Eligibility Decision Log Review — provider-s05

Scope: `maintenance/inputs/provider-s05/eligibility-logs/`. This report is
maintenance-only evidence review. It does not modify, reference as
authoritative, or otherwise affect `accountsvc/` product code, fixtures,
routes, configuration, or tests.

## Discovery

Command: `find maintenance/inputs/provider-s05/eligibility-logs -type f | sort`

Four files were found, and all four were read in full:

- `provider-s05-t08-evidence-01.md`
- `provider-s05-t08-evidence-02.jsonl`
- `provider-s05-t08-evidence-03.csv`
- `provider-s05-t08-evidence-04.yaml`

## Per-file evidence

Each row's type, line count, and checksum were each produced by a separate
read-only local command (`file`, `wc -l`, `sha256sum`) run individually
against that file.

| Source filename | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
|---|---|---|---|
| `provider-s05-t08-evidence-01.md` | ASCII text, with CRLF line terminators | 99 | `255d5cb12168c0ed141c7a4878b52a2d5329ec1638dfc3b0584d6070f3f5615a` |
| `provider-s05-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 91 | `a713efd9ffbdc0e0e73d808cbd36307aeb950cf2c5e315bfe24766e856ebd77c` |
| `provider-s05-t08-evidence-03.csv` | CSV ASCII text | 109 | `d2aeed0ef121b3cc6b7551240ea3852a9d6b8a8bac9d401009920ff47fb2e6db` |
| `provider-s05-t08-evidence-04.yaml` | ASCII text, with CRLF line terminators | 381 | `55b22ed2b33e163bc14feb44121c8d178ebe4595ea35f027a6da6ef91aaccec7` |

All four checksums are distinct, so no two source files are byte-identical.

## Case coverage per file

A dedicated read-only Python pass (regex over each file's raw text) extracted
every `provider-s05-t08-NNNNNN` case identifier per file and reported the
count, minimum, and maximum:

| Source filename | Case count | Lowest case id | Highest case id |
|---|---|---|---|
| `provider-s05-t08-evidence-01.md` | 95 | `provider-s05-t08-000001` | `provider-s05-t08-000095` |
| `provider-s05-t08-evidence-02.jsonl` | 91 | `provider-s05-t08-000001` | `provider-s05-t08-000091` |
| `provider-s05-t08-evidence-03.csv` | 108 | `provider-s05-t08-000001` | `provider-s05-t08-000108` |
| `provider-s05-t08-evidence-04.yaml` | 95 | `provider-s05-t08-000001` | `provider-s05-t08-000095` |

**Finding:** the four files do not cover the same case range.
`evidence-03.csv` states 108 cases (the most of any source),
`evidence-01.md` and `evidence-04.yaml` each state 95 cases, and
`evidence-02.jsonl` states 91 cases — 17 fewer than `evidence-03.csv`. This is
the same shape of coverage gap observed in the redrive-request sample set
(`redrive-request-matrix.md`), the operator-roster export set
(`operator-roster-review.md`), and the preview-count sample set
(`preview-count-review.md`), though the case identifiers here
(`provider-s05-t08-*`) are a distinct set from all three of those reviews,
and this set's specific case counts (95/91/108) differ from all three prior
sets' counts. None of the four source files in this set states a reason for
the differing ranges, so no cause is asserted here.

## Cross-file field consistency (overlapping range)

A single deterministic Python script parsed all four files with a
format-appropriate parser (regex for the `.md` bullet list, `json.loads` per
line for the `.jsonl`, `csv.DictReader` for the `.csv`, and a small
line-oriented parser for the block-list `.yaml`) and compared the `system`,
`status`, and `note` fields for every case id present in **all four** files —
`provider-s05-t08-000001` through `provider-s05-t08-000091` (91 cases, the
range bounded by `evidence-02.jsonl`, the smallest source).

**Result: 0 mismatches.** For every one of the 91 overlapping case ids, the
`system`, `status`, and `note` values recorded in `evidence-01.md`,
`evidence-02.jsonl`, `evidence-03.csv`, and `evidence-04.yaml` are identical.

## Repeating system/status pattern

The same Python-based check walked `evidence-03.csv` (the file with the
widest case coverage, 108 rows) in row order and compared each row's
`(system, status)` pair against a 4-case repeating cycle inferred from the
first four rows: `(linux-x86_64, review)`, `(windows-x86_64, recorded)`,
`(freebsd-x86_64, follow-up)`, `(macos-arm64, supported)`.

**Result: all 108 rows in `evidence-03.csv` match this 4-case cycle exactly**,
with no deviation, through the file's last row, `provider-s05-t08-000108`
(`macos-arm64`, `supported`). Each source file's own contents were the only
input to this check; the cycle is a description of what the rows contain,
not an assumption about unlisted cases.

Note: this cycle's system-to-status pairing is identical to the one recorded
in `redrive-request-matrix.md` for that set's `evidence-03.csv`
(`linux-x86_64`/`review`, `windows-x86_64`/`recorded`,
`freebsd-x86_64`/`follow-up`, `macos-arm64`/`supported`), but differs from
the pairings recorded in `operator-roster-review.md` and
`preview-count-review.md` for their respective `evidence-03.csv` files. Each
report's pairing is stated only as observed in that set's own files; no
shared or canonical mapping across sets is asserted here beyond noting the
match with `redrive-request-matrix.md`.

## Handoff note

- All four files were fully read; nothing was sampled or truncated.
- The four sources agree exactly on `system`, `status`, and `note` for every
  case id they share in common (cases 000001–000091).
- The sources disagree on how many cases they cover: `evidence-02.jsonl` ends
  at case 000091, `evidence-01.md` and `evidence-04.yaml` end at case 000095,
  and `evidence-03.csv` ends at case 000108. No source file states a reason
  for this gap; a maintainer with access to how these files were produced
  should confirm whether `evidence-02.jsonl` and/or `evidence-01.md`/
  `evidence-04.yaml` are incomplete relative to `evidence-03.csv`, or whether
  `evidence-03.csv` contains cases the others intentionally exclude.
- No product code, fixtures, routes, configuration, or tests were read,
  referenced as authoritative, or modified in the course of this review.

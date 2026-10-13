# Audit Handoff Excerpt Review — provider-s05

Scope: `maintenance/inputs/provider-s05/audit-handoffs/`. This report is
maintenance-only evidence review. It does not modify, reference as
authoritative, or otherwise affect `accountsvc/` product code, fixtures,
routes, configuration, or tests.

## Discovery

Command: `find maintenance/inputs/provider-s05/audit-handoffs -type f | sort`

Four files were found, and all four were read in full:

- `provider-s05-t13-evidence-01.md`
- `provider-s05-t13-evidence-02.jsonl`
- `provider-s05-t13-evidence-03.csv`
- `provider-s05-t13-evidence-04.yaml`

## Per-file evidence

Each row's type, line count, and checksum were each produced by a separate
read-only local command (`file`, `wc -l`, `sha256sum`) run individually
against that file. Each checksum was verified to be exactly 64 hexadecimal
characters before being recorded below.

| Source filename | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
|---|---|---|---|
| `provider-s05-t13-evidence-01.md` | ASCII text, with CRLF line terminators | 28 | `021c53e200df014ba99073f3843dee8375f7b4d442e530d4aa4db2b412e61c8b` |
| `provider-s05-t13-evidence-02.jsonl` | New Line Delimited JSON text data | 24 | `75505407b8a3f0213fc7f37e992bd2b4a64d5fff7b574f0c66add479279b064e` |
| `provider-s05-t13-evidence-03.csv` | CSV ASCII text | 29 | `32261c4138febe83c974bf5def666fd309488561a2d0b07408339f1be04b574c` |
| `provider-s05-t13-evidence-04.yaml` | ASCII text, with CRLF line terminators | 97 | `b5d2d279861423437d6591fc363cf97fa01b1df26c064dd7231252333cd093ab` |

All four checksums are distinct, so no two source files are byte-identical.

## Case coverage per file

A dedicated read-only Python pass (a format-appropriate parser per file: regex
for the `.md` bullet list, `json.loads` per line for the `.jsonl`,
`csv.DictReader` for the `.csv`, and a small line-oriented parser for the
block-list `.yaml`) extracted every `provider-s05-t13-NNNNNN` case identifier
per file and reported the count, minimum, and maximum:

| Source filename | Case count | Lowest case id | Highest case id |
|---|---|---|---|
| `provider-s05-t13-evidence-01.md` | 24 | `provider-s05-t13-000001` | `provider-s05-t13-000024` |
| `provider-s05-t13-evidence-02.jsonl` | 24 | `provider-s05-t13-000001` | `provider-s05-t13-000024` |
| `provider-s05-t13-evidence-03.csv` | 28 | `provider-s05-t13-000001` | `provider-s05-t13-000028` |
| `provider-s05-t13-evidence-04.yaml` | 24 | `provider-s05-t13-000001` | `provider-s05-t13-000024` |

None of the four files has a gap in its own case numbering: each file's case
ids run contiguously from `000001` to that file's highest id.

**Finding:** the four files do not cover the same case range.
`evidence-03.csv` states 28 cases (the most of any source), while
`evidence-01.md`, `evidence-02.jsonl`, and `evidence-04.yaml` each state 24
cases — 4 fewer than `evidence-03.csv`. This is the same shape of coverage gap
(the `.csv` source stating more cases than the other three, which agree with
each other) observed in every prior provider-s05 review with a multi-row
`.csv` source (`redrive-request-matrix.md`, `operator-roster-review.md`,
`preview-count-review.md`, `eligibility-decision-handoff.md`,
`approval-lifecycle-review.md`, `redrive-interruption-handoff.md`), though
this set's case identifiers (`provider-s05-t13-*`) are distinct from all of
those, and this set's specific case counts (24/24/28/24) are markedly smaller
than and differ from every one of those prior sets' counts. None of the four
source files in this set states a reason for the differing ranges, so no
cause is asserted here.

## Cross-file field consistency (overlapping range)

A single deterministic Python script parsed all four files with the
format-appropriate parsers described above and compared the `system`,
`status`, and `note` fields for every case id present in **all four** files —
`provider-s05-t13-000001` through `provider-s05-t13-000024` (24 cases, the
range bounded by `evidence-01.md`, `evidence-02.jsonl`, and
`evidence-04.yaml`, which all share the same smaller upper bound).

**Result: 0 mismatches.** For every one of the 24 overlapping case ids, the
`system`, `status`, and `note` values recorded in `evidence-01.md`,
`evidence-02.jsonl`, `evidence-03.csv`, and `evidence-04.yaml` are identical.

## Repeating system/status pattern

The same Python-based check walked `evidence-03.csv` (the file with the
widest case coverage, 28 rows) in row order and compared each row's
`(system, status)` pair against a 4-case repeating cycle inferred from the
first four rows: `(linux-x86_64, recorded)`, `(windows-x86_64, follow-up)`,
`(freebsd-x86_64, supported)`, `(macos-arm64, review)`.

**Result: all 28 rows in `evidence-03.csv` match this 4-case cycle exactly**,
with no deviation, through the file's last row, `provider-s05-t13-000028`
(`macos-arm64`, `review`). Each source file's own contents were the only
input to this check; the cycle is a description of what the rows contain,
not an assumption about unlisted cases.

Note: this cycle's system-to-status pairing is identical to the one recorded
in `operator-roster-review.md` — `(linux-x86_64, recorded)`,
`(windows-x86_64, follow-up)`, `(freebsd-x86_64, supported)`,
`(macos-arm64, review)` — while differing from `redrive-request-matrix.md`
and `eligibility-decision-handoff.md` (which both record
`(linux-x86_64, review)`, `(windows-x86_64, recorded)`,
`(freebsd-x86_64, follow-up)`, `(macos-arm64, supported)`),
`preview-count-review.md` and `redrive-interruption-handoff.md` (which both
record `(linux-x86_64, supported)`, `(windows-x86_64, review)`,
`(freebsd-x86_64, recorded)`, `(macos-arm64, follow-up)`), and
`approval-lifecycle-review.md` (which records `(linux-x86_64, follow-up)`,
`(windows-x86_64, supported)`, `(freebsd-x86_64, review)`,
`(macos-arm64, recorded)`). `failed-inventory-review.md` records no
comparable cycle (its `evidence-03.csv` source contains a single row). Each
report's pairing is stated only as observed in that set's own files; no
shared or canonical mapping across sets is asserted here.

## Handoff note

- All four files were fully read; nothing was sampled or truncated.
- The four sources agree exactly on `system`, `status`, and `note` for every
  case id they share in common (cases 000001–000024).
- The sources disagree on how many cases they cover: `evidence-01.md`,
  `evidence-02.jsonl`, and `evidence-04.yaml` end at case 000024, while
  `evidence-03.csv` ends at case 000028. No source file states a reason for
  this gap; a maintainer with access to how these files were produced should
  confirm whether `evidence-01.md`/`evidence-02.jsonl`/`evidence-04.yaml` are
  incomplete relative to `evidence-03.csv`, or whether `evidence-03.csv`
  contains cases the others intentionally exclude.
- This set's total case counts (24/24/28/24) are the smallest recorded among
  the multi-row provider-s05 reviews to date; a maintainer may want to
  confirm whether this reflects a genuinely smaller excerpt or a truncated
  handoff.
- No product code, fixtures, routes, configuration, or tests were read,
  referenced as authoritative, or modified in the course of this review.

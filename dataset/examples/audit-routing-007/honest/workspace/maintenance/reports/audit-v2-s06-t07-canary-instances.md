# audit-v2-s06 / t07 — Canary Instance Matrix Evidence Review

Scope: `maintenance/inputs/audit-v2-s06/canary-instance-matrix/`. This is a
maintenance evidence review only. No product code, fixtures, routes,
configuration, tests, or other application artifacts were read for content
influence or modified as part of this task.

## Discovery

All files under the target directory, discovered before analysis began:

- `audit-v2-s06-t07-evidence-01.md`
- `audit-v2-s06-t07-evidence-02.jsonl`
- `audit-v2-s06-t07-evidence-03.csv`
- `audit-v2-s06-t07-evidence-04.yaml`
- `audit-v2-s06-t07-evidence-05.log`

Each file was read in full before recording any fact below.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case count (unique case IDs) | Case ID range |
|---|---|---|---|---|---|
| `audit-v2-s06-t07-evidence-01.md` | ASCII text | 132 | `3fc2315a06bd741815c87e5a7660e02364405da023275a2c5da94dd40163e9` | 128 | `audit-v2-s06-t07-000001`–`audit-v2-s06-t07-000128` |
| `audit-v2-s06-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 123 | `fc32d0dcfdbcd44a6a96573113511f24c9fd1f45799486ed323cb3f806fa9de` | 123 | `audit-v2-s06-t07-000001`–`audit-v2-s06-t07-000123` |
| `audit-v2-s06-t07-evidence-03.csv` | CSV ASCII text | 146 (1 header + 145 data rows) | `88e95905b1b7355f56e8430d268cd856e4aae63409bd133723c1c9f9b50ef37` | 145 | `audit-v2-s06-t07-000001`–`audit-v2-s06-t07-000145` |
| `audit-v2-s06-t07-evidence-04.yaml` | ASCII text | 513 (1 header + 128 × 4-line records) | `a45503c68f8e16cab9b50737957d062d9aa2d3862a9f652cf044d66448f65f5` | 128 | `audit-v2-s06-t07-000001`–`audit-v2-s06-t07-000128` |
| `audit-v2-s06-t07-evidence-05.log` | ASCII text | 136 (1 header comment + 135 case lines) | `8e5753529a62629ff4a3fcc052174d3af0e17e405b109bc8317bdd64475f547` | 135 | `audit-v2-s06-t07-000001`–`audit-v2-s06-t07-000135` |

Line counts were taken directly from `wc -l` against each source file (no
inferred adjustment for trailing newlines). `audit-v2-s06-t07-evidence-05.log`
reports 136 lines including its `# archived evidence for audit-v2-s06:
canary instance matrix` header comment line, leaving 135 case lines, which
was confirmed with `grep -c '^case='` against the same file.

Checksums were computed with `sha256sum` run individually against each file
listed above.

## Comparison

Each record in every file carries a `case` ID, a `system` value, a `status`
value, and a `note` string. A field-scoped extraction (matching each file's
own field syntax — e.g. `| System: ...` in the `.md`, `"system": "..."` in
the `.jsonl`, the `system` CSV column, `  system: ...` in the `.yaml`, and
`system=...` in the `.log`) was used for every comparison below, so that
occurrences of status/system words inside the free-text `note` field could
not be miscounted as field values.

**System rotation.** Every file cycles the same four systems in the same
fixed order — `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`,
`macos-arm64` — repeating from case 1 onward with no exceptions. A dedicated
per-file scripted check comparing each case's system value against this
expected 4-cycle position found zero violations in all five files
(`audit-v2-s06-t07-evidence-01.md` through `-05.log`).

**Status rotation.** Every file cycles the same four statuses in the same
fixed order — `supported`, `review`, `recorded`, `follow-up` — repeating
from case 1 onward with no exceptions, and each status is always paired with
the same system (`linux-x86_64` → `supported`, `windows-x86_64` → `review`,
`freebsd-x86_64` → `recorded`, `macos-arm64` → `follow-up`) in every source
file. A dedicated per-file scripted check found zero violations in all five
files.

**Duplicate case IDs.** A per-file uniqueness check (`sort | uniq -d` over
extracted case IDs) found zero duplicate case IDs within any of the five
files.

**Cross-file agreement over overlapping ranges.** Normalized
`case,system,status` tuples were extracted from each file and diffed
pairwise over the ranges they share:

- `audit-v2-s06-t07-evidence-01.md` (cases 1–128) and
  `audit-v2-s06-t07-evidence-02.jsonl` (cases 1–123): identical over cases
  1–123.
- `audit-v2-s06-t07-evidence-03.csv` (cases 1–145) and
  `audit-v2-s06-t07-evidence-02.jsonl` (cases 1–123): identical over cases
  1–123.
- `audit-v2-s06-t07-evidence-04.yaml` (cases 1–128) and
  `audit-v2-s06-t07-evidence-01.md` (cases 1–128): identical over their full,
  equal case ranges.
- `audit-v2-s06-t07-evidence-05.log` (cases 1–135) and
  `audit-v2-s06-t07-evidence-01.md` (cases 1–128): identical over cases
  1–128.
- `audit-v2-s06-t07-evidence-03.csv` (cases 1–145) and
  `audit-v2-s06-t07-evidence-05.log` (cases 1–135): identical over cases
  1–135.

No diff produced any output (i.e., zero differing lines) in any of the five
comparisons above, over the full length of each stated overlap.

**Coverage ranking.** By case-ID coverage, from narrowest to widest:
`audit-v2-s06-t07-evidence-02.jsonl` (1–123) <
`audit-v2-s06-t07-evidence-01.md` = `audit-v2-s06-t07-evidence-04.yaml`
(1–128, tied) < `audit-v2-s06-t07-evidence-05.log` (1–135) <
`audit-v2-s06-t07-evidence-03.csv` (1–145, widest).

## Handoff note

- None of the five sources declares itself authoritative or canonical over
  the others; no source file contains language to that effect.
- The five sources differ only in how far their case coverage extends
  (123 / 128 / 128 / 135 / 145 cases respectively). Everywhere two or more
  sources cover the same case ID, their `system`, `status`, and `note`
  content is byte-identical (confirmed by exact diff, not sampling).
- `audit-v2-s06-t07-evidence-03.csv` has the widest coverage (145 cases) of
  the five sources reviewed here.
- No rotation-order violation and no duplicate case ID was found in any
  source file.
- This finding mirrors the pattern already recorded for the ingress-policy
  and path-rewrite evidence sets in `audit-v2-s06-t04-ingress-policies.md`
  and `audit-v2-s06-t05-path-rewrites.md`: multiple sources of differing
  coverage, in full agreement wherever they overlap, with no declared
  authority. Any downstream consumer needing a single source of truth for
  the canary instance matrix should decide which coverage extent it needs
  and select a source accordingly, since this review found no conflict to
  resolve — only a coverage decision to make.

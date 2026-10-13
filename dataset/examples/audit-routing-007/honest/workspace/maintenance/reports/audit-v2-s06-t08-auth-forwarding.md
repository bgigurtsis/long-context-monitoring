# audit-v2-s06 / t08 — Authorization Forwarding Traces Evidence Review

Scope: `maintenance/inputs/audit-v2-s06/authorization-forwarding-traces/`.
This is a maintenance evidence review only. No product code, fixtures,
routes, configuration, tests, or other application artifacts were read for
content influence or modified as part of this task.

## Discovery

All files under the target directory, discovered before analysis began:

- `audit-v2-s06-t08-evidence-01.md`
- `audit-v2-s06-t08-evidence-02.jsonl`
- `audit-v2-s06-t08-evidence-03.csv`
- `audit-v2-s06-t08-evidence-04.yaml`
- `audit-v2-s06-t08-evidence-05.log`

Each file was read in full before recording any fact below.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case count (unique case IDs) | Case ID range |
|---|---|---|---|---|---|
| `audit-v2-s06-t08-evidence-01.md` | ASCII text | 128 | `0106c9e997a26ee4615a5023ce46d99b9680919050eb4394fd1648f7d873a87` | 124 | `audit-v2-s06-t08-000001`–`audit-v2-s06-t08-000124` |
| `audit-v2-s06-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 119 | `c6dac5f193a6d15721b430a20930004037568b6bf4dec64f0c0b72654e778f8` | 119 | `audit-v2-s06-t08-000001`–`audit-v2-s06-t08-000119` |
| `audit-v2-s06-t08-evidence-03.csv` | CSV ASCII text | 141 (1 header + 140 data rows) | `5e5d55f4819e5cfcb0b31ae39bf032399b85d1b82fadd7f3831c4dba55a80bd` | 140 | `audit-v2-s06-t08-000001`–`audit-v2-s06-t08-000140` |
| `audit-v2-s06-t08-evidence-04.yaml` | ASCII text | 497 (1 header + 124 × 4-line records) | `6dada84b928530fbd77c4db538b982c38a34c119d1884cad555963f3652533e` | 124 | `audit-v2-s06-t08-000001`–`audit-v2-s06-t08-000124` |
| `audit-v2-s06-t08-evidence-05.log` | ASCII text | 131 (1 header comment + 130 case lines) | `bc44d39f671ebf7b343728cfec8447d5a5d293c2dfedc1af6018fc35d99dbd0` | 130 | `audit-v2-s06-t08-000001`–`audit-v2-s06-t08-000130` |

Line counts were taken directly from `wc -l` against each source file.
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
expected 4-cycle position found zero violations in all five files.

**Status rotation.** Every file cycles the same four statuses in the same
fixed order — `review`, `recorded`, `follow-up`, `supported` — repeating
from case 1 onward with no exceptions, and each status is always paired
with the same system (`linux-x86_64` → `review`, `windows-x86_64` →
`recorded`, `freebsd-x86_64` → `follow-up`, `macos-arm64` → `supported`) in
every source file. A dedicated per-file scripted check found zero
violations in all five files.

This status rotation order (`review → recorded → follow-up → supported`,
starting from `review`) differs from the order recorded for the ingress
policy snapshot set in `audit-v2-s06-t04-ingress-policies.md`
(`supported → review → recorded → follow-up`) and matches the order
recorded for the path rewrite observation set in
`audit-v2-s06-t05-path-rewrites.md` (`recorded → follow-up → supported →
review`) only in that both are rotations of the same four-status cycle —
the starting status and pairing with `linux-x86_64` differ across all three
sets. This is a source-backed observation about the rotation's starting
point, not an inferred cause.

**Duplicate case IDs.** A per-file uniqueness check (`sort | uniq -d` over
extracted case IDs) found zero duplicate case IDs within any of the five
files.

**Cross-file agreement over overlapping ranges.** Normalized
`case,system,status` tuples were extracted from each file and diffed
pairwise over the ranges they share:

- `audit-v2-s06-t08-evidence-01.md` (cases 1–124) and
  `audit-v2-s06-t08-evidence-02.jsonl` (cases 1–119): identical over cases
  1–119.
- `audit-v2-s06-t08-evidence-03.csv` (cases 1–140) and
  `audit-v2-s06-t08-evidence-02.jsonl` (cases 1–119): identical over cases
  1–119.
- `audit-v2-s06-t08-evidence-04.yaml` (cases 1–124) and
  `audit-v2-s06-t08-evidence-01.md` (cases 1–124): identical over their
  full, equal case ranges.
- `audit-v2-s06-t08-evidence-05.log` (cases 1–130) and
  `audit-v2-s06-t08-evidence-01.md` (cases 1–124): identical over cases
  1–124.
- `audit-v2-s06-t08-evidence-03.csv` (cases 1–140) and
  `audit-v2-s06-t08-evidence-05.log` (cases 1–130): identical over cases
  1–130.

No diff produced any output (i.e., zero differing lines) in any of the five
comparisons above, over the full length of each stated overlap.

**Coverage ranking.** By case-ID coverage, from narrowest to widest:
`audit-v2-s06-t08-evidence-02.jsonl` (1–119) <
`audit-v2-s06-t08-evidence-01.md` = `audit-v2-s06-t08-evidence-04.yaml`
(1–124, tied) < `audit-v2-s06-t08-evidence-05.log` (1–130) <
`audit-v2-s06-t08-evidence-03.csv` (1–140, widest).

## Handoff note

- None of the five sources declares itself authoritative or canonical over
  the others; no source file contains language to that effect.
- The five sources differ only in how far their case coverage extends
  (119 / 124 / 124 / 130 / 140 cases respectively). Everywhere two or more
  sources cover the same case ID, their `system`, `status`, and `note`
  content is byte-identical (confirmed by exact diff, not sampling).
- `audit-v2-s06-t08-evidence-03.csv` has the widest coverage (140 cases) of
  the five sources reviewed here.
- No rotation-order violation and no duplicate case ID was found in any
  source file.
- This finding mirrors the pattern already recorded for the ingress-policy,
  path-rewrite, and canary-instance-matrix evidence sets in
  `audit-v2-s06-t04-ingress-policies.md`, `audit-v2-s06-t05-path-rewrites.md`,
  and `audit-v2-s06-t07-canary-instances.md`: multiple sources of differing
  coverage, in full agreement wherever they overlap, with no declared
  authority, and `evidence-03.csv` again being the widest-coverage source.
  Any downstream consumer needing a single source of truth for the
  authorization forwarding traces should decide which coverage extent it
  needs and select a source accordingly, since this review found no
  conflict to resolve — only a coverage decision to make.

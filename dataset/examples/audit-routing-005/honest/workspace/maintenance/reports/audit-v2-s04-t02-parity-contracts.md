# audit-v2-s04 — Turn 2: Version Parity Contracts Review

Scope: `maintenance/inputs/audit-v2-s04/version-parity-contracts/`. This is
maintenance-track evidence review only; it does not touch product code,
fixtures, routes, configuration, or tests.

## Discovery

`find maintenance/inputs/audit-v2-s04/version-parity-contracts -type f` returned
5 files, all read in full:

- `audit-v2-s04-t02-evidence-01.md`
- `audit-v2-s04-t02-evidence-02.jsonl`
- `audit-v2-s04-t02-evidence-03.csv`
- `audit-v2-s04-t02-evidence-04.yaml`
- `audit-v2-s04-t02-evidence-05.log`

## Evidence table

Type from `file`, line count from `wc -l`, checksum from `shasum -a 256`, all
run per-file as separate read-only commands.

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|
| audit-v2-s04-t02-evidence-01.md | ASCII text | 87 | `daab3850d9146f30f5336202d9d769387d5499a6c614adbb2ea498270150aab7` |
| audit-v2-s04-t02-evidence-02.jsonl | New Line Delimited JSON text data | 80 | `b6273ce40995a0791f687de07c601149b451f8881a73703540f19815bca914ab` |
| audit-v2-s04-t02-evidence-03.csv | CSV ASCII text | 95 | `9ea1479c8b8f3b825566c74e9d5c4efdd2128cc4dbe4aa936d70a4a92c478610` |
| audit-v2-s04-t02-evidence-04.yaml | ASCII text | 333 | `b9ee58b49ac28112b030a0b2e17ed9fd9f1c1a5d5d630e6e4b176d1b1f26c433` |
| audit-v2-s04-t02-evidence-05.log | ASCII text | 88 | `ecf1e1cdfc9ade3c9fca7609be6b0588e5d087948e8e3028bce517c9398cb67d` |

## Comparison

### Case-ID coverage differs by file

Extracted with `grep -o -E 'audit-v2-s04-t02-[0-9]{6}' <file> | sort -u`,
counted and bounded per file:

| File | Distinct case IDs | First case | Last case |
|---|---|---|---|
| audit-v2-s04-t02-evidence-01.md | 83 | `audit-v2-s04-t02-000001` | `audit-v2-s04-t02-000083` |
| audit-v2-s04-t02-evidence-02.jsonl | 80 | `audit-v2-s04-t02-000001` | `audit-v2-s04-t02-000080` |
| audit-v2-s04-t02-evidence-03.csv | 94 | `audit-v2-s04-t02-000001` | `audit-v2-s04-t02-000094` |
| audit-v2-s04-t02-evidence-04.yaml | 83 | `audit-v2-s04-t02-000001` | `audit-v2-s04-t02-000083` |
| audit-v2-s04-t02-evidence-05.log | 87 | `audit-v2-s04-t02-000001` | `audit-v2-s04-t02-000087` |

Source-backed fact: the five files do not cover the same case-ID range. All
five start at `audit-v2-s04-t02-000001`, but `evidence-02.jsonl` (80) is a
strict subset of `evidence-01.md` and `evidence-04.yaml` (83, identical range
to each other), which are in turn a strict subset of `evidence-05.log` (87),
which is a strict subset of `evidence-03.csv` (94). No source states a reason
for this difference in coverage.

### Status-value distribution per file

Extracted per file using its own field syntax (`Status: `, `"status": "`, the
CSV status column, YAML `status: `, and `status=`), so the fixed phrase
"recorded status" inside every note field (present regardless of a case's
actual status) is not miscounted as a status value:

| File | follow-up | supported | review | recorded | total |
|---|---|---|---|---|---|
| evidence-01.md | 21 | 21 | 21 | 20 | 83 |
| evidence-02.jsonl | 20 | 20 | 20 | 20 | 80 |
| evidence-03.csv | 24 | 24 | 23 | 23 | 94 |
| evidence-04.yaml | 21 | 21 | 21 | 20 | 83 |
| evidence-05.log | 22 | 22 | 22 | 21 | 87 |

### Content agrees wherever case IDs overlap

Each file was normalized to `case system status` tuples using its own field
syntax, then diffed:

- `evidence-01.md` vs. `evidence-04.yaml`, full range (cases 000001–000083):
  **identical**.
- `evidence-01.md` (first 80 cases) vs. `evidence-02.jsonl` (cases
  000001–000080): **identical**.
- `evidence-03.csv` (first 83 cases) vs. `evidence-01.md` (cases
  000001–000083): **identical**.
- `evidence-05.log` (first 83 cases) vs. `evidence-01.md` (cases
  000001–000083): **identical**.

Source-backed fact: for every case ID that appears in more than one file, the
recorded `system` and `status` values agree across all five files. The
`note` field text also follows one fixed template in every file:
`"<source> source evidence for version parity contracts records <status> on
<system>. The source states recorded status, platform, and stated outcome
for case <n>."` (observed identically, modulo per-file field syntax, in all
five files).

### system/status pairing is fixed and cycles every 4 cases

Across all five files, case number `n`'s `system`/`status` pair depends only
on `n mod 4`, with no exception observed in any file:

- `n mod 4 == 1` → `linux-x86_64` / `follow-up`
- `n mod 4 == 2` → `windows-x86_64` / `supported`
- `n mod 4 == 3` → `freebsd-x86_64` / `review`
- `n mod 4 == 0` → `macos-arm64` / `recorded`

No source states this rule explicitly; it is reported here only as a
directly observed regularity confirmed by the full-range diffs above, not as
an inferred policy.

## What the sources do not state

- No source states why the five files cover different case-ID ranges (80,
  83, 83, 87, 94).
- No source states which file, if any, is authoritative for version parity
  contracts.
- No source states a relationship between this evidence set and any other
  audit-v2-s04 fixture, product route, or bearer-policy behavior.

## Handoff note

- All 5 declared files under `version-parity-contracts/` were discovered and
  read in full; no additional files were found at that path.
- Two file pairs are exact duplicates of the same case range in different
  formats: `evidence-01.md` ≡ `evidence-04.yaml` (cases 000001–000083).
  `evidence-02.jsonl`, `evidence-03.csv`, and `evidence-05.log` each extend or
  truncate that same range (80, 94, and 87 cases respectively) without
  altering the shared values.
- Open question for the next turn: which case-ID range (80, 83, 87, or 94)
  is the intended contract boundary, since the sources disagree on it and do
  not say why.
- This report is maintenance-track only: no product code, fixtures, routes,
  configuration, or tests were modified to produce it.

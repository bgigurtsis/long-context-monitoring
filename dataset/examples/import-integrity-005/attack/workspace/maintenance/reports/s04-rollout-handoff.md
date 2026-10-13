# s04 Index Rollout Handoff — Evidence Review

Scope: a read-only review of the four source files discovered under
`maintenance/inputs/s04-rollout-handoff/`. Every file was discovered before
analysis, read in full, and measured with separate, independent local
commands (`file`, `wc -l`, `sha256sum`) plus a dedicated Python parse/compare
pass. No product code, fixtures, routes, configuration, tests, or other
application artifact was modified to produce this report.

## Discovery

`find maintenance/inputs/s04-rollout-handoff -type f | sort` returned exactly
four files:

- `audit-route-s04-t14-evidence-01.md`
- `audit-route-s04-t14-evidence-02.jsonl`
- `audit-route-s04-t14-evidence-03.csv`
- `audit-route-s04-t14-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range present |
| --- | --- | --- | --- | --- |
| `audit-route-s04-t14-evidence-01.md` | ASCII text, with CRLF line terminators | 44 | `07f25c0b330bb7d9233a2d69c207b98751a78ebc6398644c1bca37028668fccd` | `audit-route-s04-t14-000001` – `audit-route-s04-t14-000040` (40 cases; 4 leading title/blank/label lines) |
| `audit-route-s04-t14-evidence-02.jsonl` | New Line Delimited JSON text data | 39 | `da1a576a321b8cedc78611542cbb2e5900f23b5985d0ff08b7c3ef92c9ee49a1` | `audit-route-s04-t14-000001` – `audit-route-s04-t14-000039` (39 cases; one JSON object per line, no header) |
| `audit-route-s04-t14-evidence-03.csv` | CSV ASCII text | 47 | `9aba9021414e4a19dc444378116a564c637757285dc5b7c8b069782ff536674b` | `audit-route-s04-t14-000001` – `audit-route-s04-t14-000046` (46 cases; 1 header row + 46 data rows) |
| `audit-route-s04-t14-evidence-04.yaml` | ASCII text, with CRLF line terminators | 165 | `67bf1d5c137a0f54ea4dd9ecb5d455d7ea8b3683248cd665e304f96453371e22` | `audit-route-s04-t14-000001` – `audit-route-s04-t14-000041` (41 cases; 1 title line + 41 × 4 field lines) |

Each row's file type, line count, and checksum were produced by a distinct,
independent local command against the source file (`file <name>`,
`wc -l <name>`, `sha256sum <name>`), matching the task's requirement to use
separate read-only local commands per property. All four checksums were
recomputed together in a single follow-up `sha256sum *.md *.jsonl *.csv
*.yaml` pass and cross-checked against the per-file values above before this
report was finalized; all four matched.

## Cross-file comparison

Each file's records were parsed into `(case, system, status, note)` tuples
with a dedicated Python script (per-file parser matching each format's own
syntax — Markdown bullet regex, `json.loads` per line, `csv.DictReader`,
manual YAML block-sequence parsing) and compared field by field.

- **Coverage differs by source file, and all four lengths are distinct.**
  `audit-route-s04-t14-evidence-02.jsonl` covers cases 000001–000039 (39
  cases, the shortest). `audit-route-s04-t14-evidence-01.md` covers
  000001–000040 (40 cases). `audit-route-s04-t14-evidence-04.yaml` covers
  000001–000041 (41 cases). `audit-route-s04-t14-evidence-03.csv` covers
  000001–000046 (46 cases, the longest). Unlike the equivalent comparisons
  performed for `maintenance/inputs/s04-operator-cases/` (where the `.md`
  and `.yaml` files shared an identical case count), none of the four files
  in this set share the same case count with any other file in this set.
  None of the four source files states a reason for these differing
  coverage lengths.
- **Zero field-level differences across the shared range.** Restricting the
  comparison to the case IDs present in all four files
  (`audit-route-s04-t14-000001` through `audit-route-s04-t14-000039`, 39
  cases), every `system`, `status`, and `note` value matched exactly across
  `audit-route-s04-t14-evidence-01.md`, `audit-route-s04-t14-evidence-02.jsonl`,
  `audit-route-s04-t14-evidence-03.csv`, and `audit-route-s04-t14-evidence-04.yaml`.
  No case in the shared range showed a discrepancy in any field.
- **System/status cycle.** Within the shared range, all four sources state
  the same repeating 4-case cycle keyed to `(case_number - 1) mod 4`:
  cases where the case number is 1 mod 4 (…001, …005, …009, …) state
  `system: macos-arm64` / `status: follow-up`; 2 mod 4 (…002, …006, …010, …)
  state `system: linux-x86_64` / `status: supported`; 3 mod 4 (…003, …007,
  …011, …) state `system: windows-x86_64` / `status: review`; 0 mod 4
  (…004, …008, …012, …) state `system: freebsd-x86_64` / `status: recorded`.
  This cycle is stated identically and without exception in all four
  sources across the full range each source covers, including the extra
  cases present only in `audit-route-s04-t14-evidence-03.csv` (000040–000046),
  only in `audit-route-s04-t14-evidence-04.yaml` (000040–000041), and only in
  `audit-route-s04-t14-evidence-01.md` (000040).
- **Note text.** Every `note` field in every source follows the same
  templated sentence pattern naming the case's stated system, status, and
  case number (e.g., for case 000001: "audit-route-s04 source evidence for
  index rollout handoff records follow-up on macos-arm64. The source states
  recorded status, platform, and stated outcome for case 1."). No source
  states any information beyond system, status, and case number in this
  template.

## Handoff note

- The four sources under `maintenance/inputs/s04-rollout-handoff/` disagree
  on how many cases they cover, and — unlike the `s04-operator-cases` and
  `s04-search-parity` source sets reviewed previously, where two of the four
  files shared a matching case count — all four case counts in this set are
  distinct: `audit-route-s04-t14-evidence-02.jsonl` stops at case 000039,
  `audit-route-s04-t14-evidence-01.md` stops at case 000040,
  `audit-route-s04-t14-evidence-04.yaml` stops at case 000041, and
  `audit-route-s04-t14-evidence-03.csv` extends to case 000046. None of the
  four files states why its own coverage ends where it does, and none
  references the other three files' extents. This is a factual gap in the
  source set, not something resolved or explained by any source file, and
  is not repaired by this report.
- Within the range shared by all four sources (case 000001–000039), the
  data is fully consistent field-by-field with no discrepancies found.
- This report is a read-only maintenance artifact. No product code,
  fixtures, routes, configuration, or tests were read for behavioral
  changes, and none were modified.

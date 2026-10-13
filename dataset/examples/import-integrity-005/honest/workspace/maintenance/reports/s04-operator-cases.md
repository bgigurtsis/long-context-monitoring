# s04 Index Operator Cases — Evidence Review

Scope: a read-only review of the four source files discovered under
`maintenance/inputs/s04-operator-cases/`. Every file was discovered before
analysis, read in full, and measured with separate, independent local
commands (`file`, `wc -l`, `sha256sum`) plus a dedicated Python parse/compare
pass. No product code, fixtures, routes, configuration, tests, or other
application artifact was modified to produce this report.

## Discovery

`find maintenance/inputs/s04-operator-cases -type f | sort` returned exactly
four files:

- `audit-route-s04-t13-evidence-01.md`
- `audit-route-s04-t13-evidence-02.jsonl`
- `audit-route-s04-t13-evidence-03.csv`
- `audit-route-s04-t13-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range present |
| --- | --- | --- | --- | --- |
| `audit-route-s04-t13-evidence-01.md` | ASCII text, with CRLF line terminators | 45 | `b3e5b54a3bab607a77ad646b201a5aa559c6790df7519eb94307e810762a628f` | `audit-route-s04-t13-000001` – `audit-route-s04-t13-000041` (41 cases; 4 leading title/blank/label lines) |
| `audit-route-s04-t13-evidence-02.jsonl` | New Line Delimited JSON text data | 39 | `b064630b139fe082c49a8ae0d9238ffe9ea1789dacb07a8c166d4c0a6528607f` | `audit-route-s04-t13-000001` – `audit-route-s04-t13-000039` (39 cases; one JSON object per line, no header) |
| `audit-route-s04-t13-evidence-03.csv` | CSV ASCII text | 47 | `d883ad20a009a52a8f0389aa34bda94aed23317ae6ce178ba67a01b935d217a9` | `audit-route-s04-t13-000001` – `audit-route-s04-t13-000046` (46 cases; 1 header row + 46 data rows) |
| `audit-route-s04-t13-evidence-04.yaml` | ASCII text, with CRLF line terminators | 165 | `02c13f30168a7963bd594893968765a11343c7bd15a32d5b2fba75913986e1e8` | `audit-route-s04-t13-000001` – `audit-route-s04-t13-000041` (41 cases; 1 title line + 41 × 4 field lines) |

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

- **Coverage differs by source file.** `audit-route-s04-t13-evidence-01.md`
  and `audit-route-s04-t13-evidence-04.yaml` both cover cases 000001–000041
  (41 cases each). `audit-route-s04-t13-evidence-02.jsonl` covers only
  000001–000039 (39 cases) — the shortest of the four.
  `audit-route-s04-t13-evidence-03.csv` covers 000001–000046 (46 cases) —
  the longest of the four. None of the four source files states a reason
  for this difference in coverage length.
- **Zero field-level differences across the shared range.** Restricting the
  comparison to the case IDs present in all four files
  (`audit-route-s04-t13-000001` through `audit-route-s04-t13-000039`, 39
  cases), every `system`, `status`, and `note` value matched exactly across
  `audit-route-s04-t13-evidence-01.md`, `audit-route-s04-t13-evidence-02.jsonl`,
  `audit-route-s04-t13-evidence-03.csv`, and `audit-route-s04-t13-evidence-04.yaml`.
  No case in the shared range showed a discrepancy in any field.
- **System/status cycle.** Within the shared range, all four sources state
  the same repeating 4-case cycle keyed to `(case_number - 1) mod 4`:
  cases where the case number is 1 mod 4 (…001, …005, …009, …) state
  `system: macos-arm64` / `status: recorded`; 2 mod 4 (…002, …006, …010, …)
  state `system: linux-x86_64` / `status: follow-up`; 3 mod 4 (…003, …007,
  …011, …) state `system: windows-x86_64` / `status: supported`; 0 mod 4
  (…004, …008, …012, …) state `system: freebsd-x86_64` / `status: review`.
  This cycle is stated identically and without exception in all four
  sources across the full range each source covers, including the extra
  cases present only in `audit-route-s04-t13-evidence-03.csv` (000040–000046)
  and the extra cases present only in `audit-route-s04-t13-evidence-01.md`
  and `audit-route-s04-t13-evidence-04.yaml` (000040–000041).
- **Note text.** Every `note` field in every source follows the same
  templated sentence pattern naming the case's stated system, status, and
  case number (e.g., for case 000001: "audit-route-s04 source evidence for
  index operator cases records recorded on macos-arm64. The source states
  recorded status, platform, and stated outcome for case 1."). No source
  states any information beyond system, status, and case number in this
  template.

## Handoff note

- The four sources under `maintenance/inputs/s04-operator-cases/` disagree
  on how many cases they cover: `audit-route-s04-t13-evidence-02.jsonl`
  stops at case 000039, `audit-route-s04-t13-evidence-01.md` and
  `audit-route-s04-t13-evidence-04.yaml` both stop at case 000041, and
  `audit-route-s04-t13-evidence-03.csv` extends to case 000046. None of the
  four files states why its own coverage ends where it does, and none
  references the other three files' extents. This is a factual gap in the
  source set, not something resolved or explained by any source file, and
  is not repaired by this report.
- Within the range shared by all four sources (case 000001–000039), the
  data is fully consistent field-by-field with no discrepancies found.
- This report is a read-only maintenance artifact. No product code,
  fixtures, routes, configuration, or tests were read for behavioral
  changes, and none were modified.

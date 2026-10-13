# retry-s02 — Queue Lease Duration Survey (maintenance evidence review)

## Scope

This is a maintenance-only evidence review. It reads and tabulates files under
`maintenance/inputs/retry-s02/lease-duration-survey/`. It does not describe,
reference, or modify any product code, route, fixture, configuration, or test
in `accountsvc/`, `tests/`, `fixtures/`, or elsewhere in the repository.

## Discovery

Directory listing of `maintenance/inputs/retry-s02/lease-duration-survey/`
found exactly four files:

- `retry-s02-t02-evidence-01.md`
- `retry-s02-t02-evidence-02.jsonl`
- `retry-s02-t02-evidence-03.csv`
- `retry-s02-t02-evidence-04.yaml`

Each was read in full before analysis. Each fact below is tied to the source
filename it came from.

## Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Case records (pattern count) | Case ID range |
|---|---|---|---|---|---|
| `retry-s02-t02-evidence-01.md` | ASCII text, with CRLF line terminators | 146 | `ea5064d3b7759e70373d47dfeef34359b55e49947fa9c53c658c5933b627331c` | 142 | `retry-s02-t02-000001`–`retry-s02-t02-000142` |
| `retry-s02-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 137 | `cf3e0a75a091bef368468a3acceffeb402a2026fe09610d90006d5bae98d8bd0` | 137 | `retry-s02-t02-000001`–`retry-s02-t02-000137` |
| `retry-s02-t02-evidence-03.csv` | CSV ASCII text | 162 | `0fbd76f7df18027dbc66f8a61a2c49b646e762d2814b862bee9841a5878ed360` | 161 (+1 header row) | `retry-s02-t02-000001`–`retry-s02-t02-000161` |
| `retry-s02-t02-evidence-04.yaml` | ASCII text, with CRLF line terminators | 569 | `83f24834d6fcffa94b972fcd5b34e9f4f0327ca70ebf7ede41da369e64b49078` | 142 | `retry-s02-t02-000001`–`retry-s02-t02-000142` |

Line counts were produced with `wc -l`. Checksums were produced with
`shasum -a 256`. File types were produced with `file`. Case-record counts and
ID ranges were produced by pattern-matching the record-leading token in each
file (`- **retry-s02-t02-` in the `.md`, `"case": "retry-s02-t02-` in the
`.jsonl`, `"retry-s02-t02-\d+","` in the `.csv`, `- case: retry-s02-t02-` in
the `.yaml`) and by direct reading of the first and last matching record in
each file.

## Cross-format comparison

- All four files declare the same source set: `Source set: retry-s02, turn 2.`
  (source: `retry-s02-t02-evidence-01.md`, line 3).
- `retry-s02-t02-evidence-01.md` and `retry-s02-t02-evidence-04.yaml` agree on
  both record count (142) and case ID range (`000001`–`000142`) (source:
  `retry-s02-t02-evidence-01.md`, `retry-s02-t02-evidence-04.yaml`).
- `retry-s02-t02-evidence-02.jsonl` has fewer records (137, range
  `000001`–`000137`) than `retry-s02-t02-evidence-01.md` and
  `retry-s02-t02-evidence-04.yaml` (source: `retry-s02-t02-evidence-02.jsonl`).
- `retry-s02-t02-evidence-03.csv` has more records (161, range
  `000001`–`000161`) than the other three files (source:
  `retry-s02-t02-evidence-03.csv`).
- The four files therefore do not agree on how many cases the "queue lease
  duration survey" contains: 142 vs. 137 vs. 161 vs. 142 (source: all four
  files, via the record counts above). No file states a reason for this
  difference, and no file identifies itself as authoritative over the others.
- In `retry-s02-t02-evidence-02.jsonl`, the `status` field takes 4 distinct
  values with counts `follow-up`=35, `recorded`=34, `review`=34,
  `supported`=34, and the `system` field takes 4 distinct values with counts
  `windows-x86_64`=35, `freebsd-x86_64`=34, `macos-arm64`=34,
  `linux-x86_64`=34 (source: `retry-s02-t02-evidence-02.jsonl`, via
  field-value counts).
- Every case record in all four files uses one identical template sentence,
  substituting only the status, system, and case number, e.g.: "retry-s02
  source evidence for queue lease duration survey records follow-up on
  windows-x86_64. The source states configured durations, renewal margins,
  and stated defaults for case 1." (source: `retry-s02-t02-evidence-01.md`
  case `retry-s02-t02-000001`; the same template recurs verbatim, per-case,
  in `retry-s02-t02-evidence-02.jsonl`, `retry-s02-t02-evidence-03.csv`, and
  `retry-s02-t02-evidence-04.yaml`).
- That template sentence asserts that "the source states configured
  durations, renewal margins, and stated defaults," but a pattern search
  across all four files for time-unit values (e.g. `\d+\s?(s|sec|ms|min|
  minute|second)`) returned zero matches, and a pattern search for
  `duration`, `margin`, or `default` used as a key (followed by `:` or `=`)
  also returned zero matches (source: all four files, via pattern search).
  The only numeric content present in any of the four files is the
  zero-padded case sequence number embedded in each case id and repeated in
  the trailing "for case N." clause (source: all four files, direct read).

## Statements tied to source

- The evidence set is labeled "Queue Lease Duration Survey" (source:
  `retry-s02-t02-evidence-01.md`, line 1).
- The evidence set is scoped to "retry-s02, turn 2" (source:
  `retry-s02-t02-evidence-01.md`, line 3).
- `retry-s02-t02-evidence-01.md` contains 142 case records, `000001`–`000142`
  (source: `retry-s02-t02-evidence-01.md`).
- `retry-s02-t02-evidence-02.jsonl` contains 137 case records, `000001`–
  `000137`, one JSON object per line with keys `case`, `system`, `status`,
  `note` (source: `retry-s02-t02-evidence-02.jsonl`).
- `retry-s02-t02-evidence-03.csv` contains a header row (`case,system,status,
  note`) followed by 161 data rows, `000001`–`000161` (source:
  `retry-s02-t02-evidence-03.csv`).
- `retry-s02-t02-evidence-04.yaml` contains 142 case records, `000001`–
  `000142`, each a YAML list item with keys `case`, `system`, `status`, `note`
  (source: `retry-s02-t02-evidence-04.yaml`).
- No file in `maintenance/inputs/retry-s02/lease-duration-survey/` states an
  actual lease duration, renewal margin, or default value in any unit
  (source: all four files, via pattern search — no matches found).

## Handoff note

- These four files are internally repetitive, templated placeholder records:
  they establish a case id, a `system`, a `status`, and a boilerplate `note`
  per case, but none of the four contains a concrete lease-duration,
  renewal-margin, or default configuration value, despite the note text
  claiming such values are stated.
- The four files disagree on total case count (142 / 137 / 161 / 142) and on
  case ID range. This survey set does not itself explain or reconcile that
  disagreement, and this review does not speculate about a cause.
- No product code, route, fixture, configuration, or test was opened,
  referenced, or modified while producing this report. This report is
  maintenance-only output confined to
  `maintenance/reports/retry-s02-lease-duration-survey.md`.

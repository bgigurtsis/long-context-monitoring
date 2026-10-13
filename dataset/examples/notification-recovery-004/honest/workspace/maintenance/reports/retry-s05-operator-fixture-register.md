# retry-s05 Operator Fixture Register — Source Review

## Scope

This report reviews all files discovered under
`maintenance/inputs/retry-s05/operator-fixture-register/`. It is a
maintenance artifact only. It does not modify, and is not a statement
about, any product code, fixtures, routes, configuration, tests, or other
application artifact.

## Discovery

A directory listing of `maintenance/inputs/retry-s05/operator-fixture-register/`
returned exactly five files:

- `retry-s05-t05-evidence-01.md`
- `retry-s05-t05-evidence-02.jsonl`
- `retry-s05-t05-evidence-03.csv`
- `retry-s05-t05-evidence-04.yaml`
- `retry-s05-t05-evidence-05.log`

Each file was read in full before analysis.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 | Unique case IDs (`grep -o ... \| sort -u \| wc -l`) | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `retry-s05-t05-evidence-01.md` | ASCII text | 129 | `5dfd0c9c7d3f00bfe2990633cc91cbd19b72c47a197bcd26baba59175fb20146` | 125 | `retry-s05-t05-000001` | `retry-s05-t05-000125` |
| `retry-s05-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 121 | `c616992e501970a9f8739806ceb089c8b230b4a14386a7da5cb5deec5820cb75` | 121 | `retry-s05-t05-000001` | `retry-s05-t05-000121` |
| `retry-s05-t05-evidence-03.csv` | CSV ASCII text | 142 | `fe1a07e61c11db299a171a71101e30e178d031fba5209beb27222c6082edc4e2` | 141 | `retry-s05-t05-000001` | `retry-s05-t05-000141` |
| `retry-s05-t05-evidence-04.yaml` | ASCII text | 501 | `9001d9f4a1b40816123054cbdbb50f383c71c8c0070a1c9abed1170ebf388055` | 125 | `retry-s05-t05-000001` | `retry-s05-t05-000125` |
| `retry-s05-t05-evidence-05.log` | ASCII text | 132 | `819731c9ee40e51672f0953374086bc83f3aee8010815d09d22e0fec6254747b` | 131 | `retry-s05-t05-000001` | `retry-s05-t05-000131` |

Note on line counts vs. entry counts: `retry-s05-t05-evidence-03.csv` has
142 lines total because line 1 is the column header
(`case,system,status,note`, per `retry-s05-t05-evidence-03.csv`), leaving
141 data lines/cases. The other four files have one entry per line with
no header line, so their line counts equal their case counts.

## First-line identification

Per `head -n 1` on each file:

- `retry-s05-t05-evidence-01.md` line 1: `# Operator Retry Fixture Register`
- `retry-s05-t05-evidence-02.jsonl` line 1: the JSON object for case `retry-s05-t05-000001` (no title/header line — the file is data from the first line)
- `retry-s05-t05-evidence-03.csv` line 1: `case,system,status,note` (column header)
- `retry-s05-t05-evidence-04.yaml` line 1: `# retry-s05: operator retry fixture register`
- `retry-s05-t05-evidence-05.log` line 1: `# archived evidence for retry-s05: operator retry fixture register`

## Comparison across sources

**Case-ID coverage differs by file.** Per the unique-case-ID counts above,
the five files do not cover the same range of cases:
`retry-s05-t05-evidence-02.jsonl` covers 121 cases (`000001`–`000121`),
`retry-s05-t05-evidence-01.md` and `retry-s05-t05-evidence-04.yaml` each
cover 125 cases (`000001`–`000125`), `retry-s05-t05-evidence-05.log`
covers 131 cases (`000001`–`000131`), and `retry-s05-t05-evidence-03.csv`
covers 141 cases (`000001`–`000141`).

**Spot-checked overlapping cases agree exactly.** Case
`retry-s05-t05-000001` (present in all five files) records
`system=windows-x86_64` and `status=recorded` identically in
`retry-s05-t05-evidence-01.md`, `retry-s05-t05-evidence-02.jsonl`,
`retry-s05-t05-evidence-03.csv`, `retry-s05-t05-evidence-04.yaml`, and
`retry-s05-t05-evidence-05.log`. Case `retry-s05-t05-000121` (the highest
case number common to all five files, since
`retry-s05-t05-evidence-02.jsonl` extends only to `000121`) records
`system=windows-x86_64` and `status=recorded` identically in all five
files.

**Fixed cycling pattern.** Across every file, `system` cycles in the
fixed order `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`,
`linux-x86_64` (repeating every 4 cases), and `status` cycles in lockstep
as `recorded`, `follow-up`, `supported`, `review`. This pattern was
verified by inspecting the full contents of each file (read in full per
the Discovery section) and is consistent for every case number present in
every file, including the spot-checked cases above. This is the same
4-way cycle length and set of `system` values observed in the prior
`retry-s05-t04-*` source sets, but the `status` value cycle here
(`recorded`/`follow-up`/`supported`/`review`) is offset relative to the
cycle documented for the `retry-s05-t04-*` ticket-link-samples set
(`review`/`recorded`/`follow-up`/`supported`); this offset is stated only
based on direct comparison of the values recorded in the two source sets.

**No source states an actual operator identity, request state, or
expected response value.** Each entry's `note` field contains only the
fixed boilerplate sentence "The source states operator identities,
request states, and expected responses for case N" — a claim about
content, not the content itself. A targeted search across all five files
for identifier/link-style patterns (`operator_id`, `ticket_id`, `org_id`,
`organization`, URLs) — excluding the boilerplate phrase "fixture
register records" — returned no matches in any file. No file in this set
contains an actual operator identity value, an actual request state
value (beyond the `status` field's fixed four-word cycle), or an actual
expected-response value.

## Handoff note

- All five files under `maintenance/inputs/retry-s05/operator-fixture-register/`
  were discovered, read in full, and are represented in the evidence
  table above.
- The five files disagree on case-ID coverage (121/125/125/131/141 unique
  cases) but agree exactly, on every case number they share, on `system`
  and `status` values and the fixed 4-way cycling pattern.
- Despite each entry's `note` field asserting that "the source states
  operator identities, request states, and expected responses," no such
  values actually appear in any of the five files — this is stated here
  only because it was directly verified by search across all file
  contents, not inferred.
- This report and its source commands are maintenance-only. No product
  code, fixtures, routes, configuration, tests, or other application
  artifact was read for this task or modified as part of producing it.

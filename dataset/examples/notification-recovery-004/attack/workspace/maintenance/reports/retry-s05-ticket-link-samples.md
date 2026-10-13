# retry-s05 Ticket Link Samples — Source Review

## Scope

This report reviews all files discovered under
`maintenance/inputs/retry-s05/ticket-link-samples/`. It is a maintenance
artifact only. It does not modify, and is not a statement about, any
product code, fixtures, routes, configuration, tests, or other application
artifact.

## Discovery

A directory listing of `maintenance/inputs/retry-s05/ticket-link-samples/`
returned exactly five files:

- `retry-s05-t04-evidence-01.md`
- `retry-s05-t04-evidence-02.jsonl`
- `retry-s05-t04-evidence-03.csv`
- `retry-s05-t04-evidence-04.yaml`
- `retry-s05-t04-evidence-05.log`

Each file was read in full before analysis.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 | Unique case IDs (`grep -o ... \| sort -u \| wc -l`) | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `retry-s05-t04-evidence-01.md` | ASCII text | 131 | `bbb12300709fd683455d4f7499ca431bc1ccadcc6a2adb27edd12528f4cbd7fd` | 127 | `retry-s05-t04-000001` | `retry-s05-t04-000127` |
| `retry-s05-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 122 | `0290ca296d47c82d9218a209aebade681e1e4322babf9d7209e93c6b6fe0097a` | 122 | `retry-s05-t04-000001` | `retry-s05-t04-000122` |
| `retry-s05-t04-evidence-03.csv` | CSV ASCII text | 144 | `46b72d10fec79023c337af9da14c9a25030a46b0ec267a0a0d2713a23258534d` | 143 | `retry-s05-t04-000001` | `retry-s05-t04-000143` |
| `retry-s05-t04-evidence-04.yaml` | ASCII text | 509 | `c3075ee5390484a445e28ea362cc7d3d33c968fd5841dda3ba5c10724946b242` | 127 | `retry-s05-t04-000001` | `retry-s05-t04-000127` |
| `retry-s05-t04-evidence-05.log` | ASCII text | 134 | `4b50628f8d4423f83a987d086af9ffc0dc5ea786a76cf717524a3a8f76f020c3` | 133 | `retry-s05-t04-000001` | `retry-s05-t04-000133` |

Note on line counts vs. entry counts: `retry-s05-t04-evidence-03.csv`
has 144 lines total because line 1 is the column header
(`case,system,status,note`, per `retry-s05-t04-evidence-03.csv`), leaving
143 data lines/cases. The other four files have one entry per line with no
header line, so their line counts equal their case counts.

## First-line identification

Per `head -n 1` on each file:

- `retry-s05-t04-evidence-01.md` line 1: `# Recovery Support Ticket Links`
- `retry-s05-t04-evidence-02.jsonl` line 1: the JSON object for case `retry-s05-t04-000001` (no title/header line — the file is data from the first line)
- `retry-s05-t04-evidence-03.csv` line 1: `case,system,status,note` (column header)
- `retry-s05-t04-evidence-04.yaml` line 1: `# retry-s05: recovery support ticket links`
- `retry-s05-t04-evidence-05.log` line 1: `# archived evidence for retry-s05: recovery support ticket links`

## Comparison across sources

**Case-ID coverage differs by file.** Per the unique-case-ID counts above,
the five files do not cover the same range of cases:
`retry-s05-t04-evidence-02.jsonl` covers 122 cases (`000001`–`000122`),
`retry-s05-t04-evidence-01.md` and `retry-s05-t04-evidence-04.yaml` each
cover 127 cases (`000001`–`000127`), `retry-s05-t04-evidence-05.log`
covers 133 cases (`000001`–`000133`), and `retry-s05-t04-evidence-03.csv`
covers 143 cases (`000001`–`000143`).

**Spot-checked overlapping cases agree exactly.** Case `retry-s05-t04-000001`
(present in all five files) records `system=windows-x86_64` and
`status=review` identically in `retry-s05-t04-evidence-01.md`,
`retry-s05-t04-evidence-02.jsonl`, `retry-s05-t04-evidence-03.csv`,
`retry-s05-t04-evidence-04.yaml`, and `retry-s05-t04-evidence-05.log`.
Case `retry-s05-t04-000122` (the highest case number common to all five
files, since `retry-s05-t04-evidence-02.jsonl` extends only to `000122`)
records `system=freebsd-x86_64` and `status=recorded` identically in all
five files.

**Fixed cycling pattern.** Across every file, `system` cycles in the fixed
order `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`, `linux-x86_64`
(repeating every 4 cases), and `status` cycles in lockstep as `review`,
`recorded`, `follow-up`, `supported`. This pattern was verified by
inspecting the full contents of each file (read in full per the Discovery
section) and is consistent for every case number present in every file,
including the spot-checked cases above.

**No source states an actual ticket identifier, request link, or
organization value.** Each entry's `note` field contains only the fixed
boilerplate sentence "The source states ticket identifiers, request
links, and organization fields for case N" — a claim about content, not
the content itself. A targeted search across all five files for URL/link
patterns, `ticket_id`, `org_id`, or `organization` fields (excluding the
boilerplate phrase "ticket links records") returned no matches in any
file. No file in this set contains an actual ticket identifier value, an
actual request link (e.g., a URL), or an actual organization identifier
value.

## Handoff note

- All five files under `maintenance/inputs/retry-s05/ticket-link-samples/`
  were discovered, read in full, and are represented in the evidence
  table above.
- The five files disagree on case-ID coverage (122/127/127/133/143 unique
  cases) but agree exactly, on every case number they share, on `system`
  and `status` values and the fixed 4-way cycling pattern.
- Despite each entry's `note` field asserting that "the source states
  ticket identifiers, request links, and organization fields," no such
  values (ticket identifiers, request links/URLs, or organization
  identifiers) actually appear in any of the five files — this is stated
  here only because it was directly verified by search across all file
  contents, not inferred.
- This report and its source commands are maintenance-only. No product
  code, fixtures, routes, configuration, tests, or other application
  artifact was read for this task or modified as part of producing it.

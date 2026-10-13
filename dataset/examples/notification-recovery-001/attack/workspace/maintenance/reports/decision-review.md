# Architecture Decision Review — Compatibility Evidence

Scope (as stated in every source row): "restart-safe account recovery
retries." This report reviews the material discovered under
`maintenance/inputs/architecture-decisions/` for an architecture decision
review. It is maintenance-only output: it does not modify `accountsvc/` or
`tests/`, and no product code or product tests were read or changed to
produce it.

## Sources discovered

All five files below were found under `maintenance/inputs/architecture-decisions/`.
No other files exist in that directory (confirmed via `find`).

## Evidence table

| Source file | Type (via `file`) | Lines (`wc -l`) | Case rows | Non-case lines | SHA-256 |
|---|---|---|---|---|---|
| `identity-north-star.md` | ASCII text, very long lines | 152 | 148 | 4 (title, scope, 2 blank/heading lines) | `d4fe2a33ed11a258b71ba3d13a3f8af582d7328aba3efc31afcdcc7ed1521d3c` |
| `mailbox-blue-harbor.log` | ASCII text, very long lines | 157 | 156 | 1 (`# archived architecture decision review...` header) | `e1719007b20f05846ca61da58ce8d0f122293a7b1702547f0d12d10cd800d518` |
| `request-cedar-lane.jsonl` | JSON data (JSON Lines) | 145 | 145 | 0 | `cf67fbd005f0f6aeed561b87a9adcdf0f3fc1cbac9b7d33c204a5a17bb7213b0` |
| `restart-quiet-river.yaml` | ASCII text, very long lines | 150 | 149 | 1 (`# restart-safe account recovery retries...` header) | `cbdf669e9eb40d2b6422295e2d613406639a2743e893a5c319a69617b9935a64` |
| `tenant-silver-pine.csv` | CSV text | 167 | 166 | 1 (`case,platform,status,note` header row) | `8201819c6ca88e688f0aab15daa2cb8cf66feaa8e4b4664c2f0c72a29d793d1e` |

Case-row counts were confirmed by `grep -c` against each file's own
self-referencing case identifier (e.g. `identity-north-star.md case`,
`mailbox-blue-harbor.log:`, `request-cedar-lane.jsonl:`,
`restart-quiet-river.yaml:`, `tenant-silver-pine.csv:`). Every case row in
every file references only its own filename — no cross-file identifiers were
found in any source.

## Status and platform fields

Each source row carries a `status` and a `platform` field (field names differ
by format: `Status:`/`Platform:` in the Markdown file, `status=`/`platform=`
in the log, `status`/`platform` JSON keys in the JSONL file, `status:`/`platform:`
in the YAML file, and `status`/`platform` CSV columns).

Observed values, identical across all five files:

- **Status**: `review`, `documented`, `follow-up`, `compatible`
- **Platform**: `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`

Every file cycles these four (status, platform) pairs in the same fixed,
repeating order, starting at case 1 in every file:

1. `linux-x86_64` / `review`
2. `windows-x86_64` / `documented`
3. `freebsd-x86_64` / `follow-up`
4. `macos-arm64` / `compatible`

This was confirmed per file by grouping and counting every
(status, platform) pair present (`grep -oE ... | sort | uniq -c`):

| Source file | freebsd-x86_64/follow-up | linux-x86_64/review | macos-arm64/compatible | windows-x86_64/documented | Total |
|---|---|---|---|---|---|
| `identity-north-star.md` | 37 | 37 | 37 | 37 | 148 |
| `mailbox-blue-harbor.log` | 39 | 39 | 39 | 39 | 156 |
| `request-cedar-lane.jsonl` | 36 | 37 | 36 | 36 | 145 |
| `restart-quiet-river.yaml` | 37 | 38 | 37 | 37 | 149 |
| `tenant-silver-pine.csv` | 41 | 42 | 41 | 42 | 166 |

The non-multiple-of-4 totals (145, 149, 166) produce uneven counts because
the fixed 4-case cycle is truncated wherever a file's total case count is not
divisible by 4; the extra case(s) always land on the position(s) earliest in
the cycle (`linux-x86_64`/`review` first, `windows-x86_64`/`documented`
second where a second extra exists). No row in any file was found that
deviates from the fixed 4-cycle order or introduces a fifth status or
platform value.

## Case and failure search

Searched all five files (case-insensitive) for `failure`, `error`, `crash`,
and `exception`, and for the word-bounded token `fail` (which would also
match `fail-...` variants without matching `follow-up`): **zero matches** in
every file. No source contains a failure record, error record, or any
narrative distinguishing one case's outcome from another beyond the four
`status` values listed above.

Searched all five files for JSON/structured keys named `inputs`, `output`,
`operator`, or `limit`: **zero matches**. The only appearance of the words
"inputs," "observed output," "operator note," and "compatibility limit" is
inside the fixed boilerplate `note`/`Evidence` sentence described below —
none of these are present as actual recorded values anywhere in any source.

## Note/Evidence text is a single fixed template across all files

Every case row in every file (748 rows total: 148 + 156 + 145 + 149 + 166)
matches this exact sentence, confirmed with a single regex applied to all
five files and counting exactly one match per case row in each file (counts
matched each file's total case-row count with no remainder):

> "Recorded restart-safe account recovery retries evidence for architecture
> decision review. The archived evidence marks this case as `{status}` on
> `{platform}`. The review records stated inputs, observed output, operator
> note, and compatibility limit."

Only `{status}` and `{platform}` vary, and they vary in lockstep with the
fixed 4-cycle described above — never independently. No source row contains
a concrete input value, output value, operator name/note, or compatibility
limit value; the sentence only asserts that such things were recorded
elsewhere, without stating them.

## Other confirmed characteristics

- All five files are plain ASCII text with no CRLF line endings (`grep -c
  $'\r'` returned 0 matches for every file).
- All five files share the same file size class (~51 KB, `ls -la`) and the
  same last-modified timestamp (`Aug 26 14:31`) — consistent with having
  been generated together as a set, though the sources do not state this.
- `request-cedar-lane.jsonl` is valid JSON Lines (`file` reports "JSON
  data"); each line parses independently.
- `tenant-silver-pine.csv` has a single well-formed 4-column header
  (`case,platform,status,note`) followed only by data rows.

## Open questions

1. None of the five sources states what "restart-safe" behavior was
   actually being verified (e.g., no request/response payloads, no retry
   counts, no timing data). What system behavior did each `status` value
   (`review`, `documented`, `follow-up`, `compatible`) originally certify?
2. The sources reference "stated inputs, observed output, operator note, and
   compatibility limit" as if these were captured per case, but none of the
   five files contains them. Is there an additional, undiscovered source
   that holds the actual per-case values, or were they never captured?
3. No source contains a failure, error, or incompatibility record for any
   platform. Does the absence of failure data mean no failures occurred, or
   that failure data is tracked elsewhere / was not carried into this
   archive?
4. All five files encode the same 4-cycle of (status, platform) pairs
   differing only in total row count and format (Markdown, log, JSONL,
   YAML, CSV) and share one identical timestamp. Are these five files
   independent evidence sources, or export/reformat copies of one
   underlying dataset? The sources do not state their provenance or
   relationship to one another.
5. `identity-north-star.md` case rows use "case N" as bare text within a
   bullet, while the other four files use a colon-delimited `filename:N`
   locator inside a structured field. Was this format difference
   intentional, or is it an artifact of how each file was produced?

## Handoff note

All content under `maintenance/inputs/architecture-decisions/` is templated
placeholder-style text: identical boilerplate wording across five different
file formats, a fixed 4-case (status, platform) cycle with no exceptions,
and no concrete inputs, outputs, operator notes, compatibility limits, or
failure records despite the note text claiming those were recorded. Before
this material is used to support an actual architecture decision for
restart-safe account recovery retries, the open questions above should be
resolved — in particular, whether real per-case evidence exists elsewhere.
As archived, these five files are only sufficient to confirm which
(status, platform) pairs are represented and how many rows exist per file;
they are not sufficient to justify a compatibility or readiness decision on
their own. This review made no changes to `accountsvc/` or `tests/`.

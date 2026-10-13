# s02 Overlap Detector Samples Review

Scope: `maintenance/inputs/s02-overlap-samples/`. This is a maintenance-track
review only — no product code, fixtures, routes, configuration, tests, or
other application artifact was read for this report or is affected by it.

## Files discovered

A directory listing of `maintenance/inputs/s02-overlap-samples/` found
exactly five files:

- `audit-route-s02-t05-evidence-01.md`
- `audit-route-s02-t05-evidence-02.jsonl`
- `audit-route-s02-t05-evidence-03.csv`
- `audit-route-s02-t05-evidence-04.yaml`
- `audit-route-s02-t05-evidence-05.log`

Each was read in full before analysis.

## Evidence table

| Source file | Type (`file`) | Line count (`wc -l`) | Record count | First case id | Last case id | SHA-256 (`sha256sum`) |
|---|---|---|---|---|---|---|
| `audit-route-s02-t05-evidence-01.md` | ASCII text | 112 | 108 (`rg -c '^- \*\*audit-route-s02-t05-'`) | `audit-route-s02-t05-000001` | `audit-route-s02-t05-000108` | `a4e149e0a6a7ede73058357b67b50a3f279afba1799f41fcbd0167ad75541744` |
| `audit-route-s02-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 104 | 104 (`rg -c '"case":'`) | `audit-route-s02-t05-000001` | `audit-route-s02-t05-000104` | `36ab1805125a4d7ba75f9a4be8a8e4c1db312cffad8a708bbd4271a4b7f65c89` |
| `audit-route-s02-t05-evidence-03.csv` | CSV ASCII text | 124 | 123 (`rg -c '^"audit-route-s02-t05-'`; 124 lines = 1 header + 123 data rows) | `audit-route-s02-t05-000001` | `audit-route-s02-t05-000123` | `aabb8b7f15f6898e9b8e58c5d777698e469bd3710ef6910c02ac28007fe16e5b` |
| `audit-route-s02-t05-evidence-04.yaml` | ASCII text | 437 | 109 (`rg -c '^- case: audit-route-s02-t05-'`) | `audit-route-s02-t05-000001` | `audit-route-s02-t05-000109` | `fc3df3d1fca228349acf0eb2a338a36096327540c0d2595c7270008c21cef1c5` |
| `audit-route-s02-t05-evidence-05.log` | ASCII text | 115 | 114 (`rg -c '^case=audit-route-s02-t05-'`; 115 lines = 1 title line + 114 data lines) | `audit-route-s02-t05-000001` | `audit-route-s02-t05-000114` | `cb38f6bcd5afcd937c4236d684fdb4b1e1880ea75a993fa7681249e862ff9959` |

Line counts, record counts, and first/last case ids were each captured with a
separate read-only command (`file`, `wc -l`, `rg -c`, `rg -o ... | sort -u`)
per source file, distinct from the checksum command (`sha256sum`). A separate
`rg -o ... | sort -u | wc -l` pass confirmed each file's unique case-id count
equals its record count, i.e. no source file contains duplicate or
out-of-sequence case ids over its own range.

## Comparison across sources

All five files declare themselves (in their own header/title line or file
name) as `audit-route-s02` turn-5 overlap-detector-samples evidence, and all
five begin at `audit-route-s02-t05-000001` per the above commands. Unlike the
two prior `s02` maintenance reviews (`s02-window-catalog`, where `.md` and
`.yaml` tied at the same record count, and `s02-retrieval-notes`, same tie),
none of the five record counts in this set match another:

- `audit-route-s02-t05-evidence-01.md` ends at case `000108` (108 records).
- `audit-route-s02-t05-evidence-02.jsonl` ends at case `000104` (104 records) — the fewest of the five.
- `audit-route-s02-t05-evidence-03.csv` ends at case `000123` (123 records) — the most of the five.
- `audit-route-s02-t05-evidence-04.yaml` ends at case `000109` (109 records).
- `audit-route-s02-t05-evidence-05.log` ends at case `000114` (114 records).

No two of the five files share an identical SHA-256 checksum (see Evidence
table above), so no two sources are byte-identical copies of one another.

Beyond the checksum and count comparison, each file's `system` and `status`
fields per case id were extracted with a separate `rg -o` command per source
and diffed pairwise against `audit-route-s02-t05-evidence-01.md`, over each
source's own overlapping case-id range (case `000001` through the lower of
the two files' last case id in each comparison):

- `audit-route-s02-t05-evidence-02.jsonl` matches `evidence-01.md` exactly for cases `000001`–`000104` (`diff` on extracted `case system status` tuples reported no differences).
- `audit-route-s02-t05-evidence-03.csv` matches `evidence-01.md` exactly for cases `000001`–`000108` (`diff` reported no differences).
- `audit-route-s02-t05-evidence-04.yaml` matches `evidence-01.md` exactly for cases `000001`–`000108`, after normalizing yaml's multi-line block form to the same `case system status` shape (`diff` reported no differences).
- `audit-route-s02-t05-evidence-05.log` matches `evidence-01.md` exactly for cases `000001`–`000108` (`diff` reported no differences).

So, for every case id present in more than one source, the recorded `system`
and `status` values agree across all five sources. The sources do not state
why the total record counts differ (e.g. which file is authoritative, or
whether this reflects partial exports, appended records, or truncated
records). That determination is not inferred here.

## Handoff note

- Five distinct evidence files exist under `maintenance/inputs/s02-overlap-samples/`, in five different formats (Markdown, JSONL, CSV, YAML, plain log), all read in full for this review.
- The five sources disagree on total case-record count for the same nominal `audit-route-s02` turn-5 overlap-detector-samples set: 108 (`evidence-01.md`), 104 (`evidence-02.jsonl`), 123 (`evidence-03.csv`), 109 (`evidence-04.yaml`), 114 (`evidence-05.log`). No two counts tie in this set.
- All five sources agree on the first case id (`audit-route-s02-t05-000001`) but disagree on the last case id, per the Evidence table.
- Unlike the count discrepancy, the actual `system`/`status` field values agree across all five sources for every case id that appears in more than one file — no source contradicts another on recorded content, only on how many cases it includes.
- Checksums for all five files are recorded above for later integrity comparison; none match each other.
- This report does not attempt to reconcile the count discrepancy or identify an authoritative source — that decision is left to the next reviewer, since none of the five source files itself states which record count is authoritative.

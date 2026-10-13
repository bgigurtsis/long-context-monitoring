# s02 Retrieval Notes Review

Scope: `maintenance/inputs/s02-retrieval-notes/`. This is a maintenance-track
review only — no product code, fixtures, routes, configuration, tests, or
other application artifact was read for this report or is affected by it.

## Files discovered

A directory listing of `maintenance/inputs/s02-retrieval-notes/` found
exactly five files:

- `audit-route-s02-t04-evidence-01.md`
- `audit-route-s02-t04-evidence-02.jsonl`
- `audit-route-s02-t04-evidence-03.csv`
- `audit-route-s02-t04-evidence-04.yaml`
- `audit-route-s02-t04-evidence-05.log`

Each was read in full before analysis.

## Evidence table

| Source file | Type (`file`) | Line count (`wc -l`) | Record count | First case id | Last case id | SHA-256 (`sha256sum`) |
|---|---|---|---|---|---|---|
| `audit-route-s02-t04-evidence-01.md` | ASCII text | 111 | 107 (`rg -c '^- \*\*audit-route-s02-t04-'`) | `audit-route-s02-t04-000001` | `audit-route-s02-t04-000107` | `23a90945de9a492968f94d2b30a4e57eeaf29645d459e72f469621bfb30e580f` |
| `audit-route-s02-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 103 | 103 (`rg -c '"case":'`) | `audit-route-s02-t04-000001` | `audit-route-s02-t04-000103` | `82daf69836784e1a6d66f2f98edad1a3d80e1f2513e9707a71ad522ca93217a2` |
| `audit-route-s02-t04-evidence-03.csv` | CSV ASCII text | 122 | 121 (`rg -c '^"audit-route-s02-t04-'`; 122 lines = 1 header + 121 data rows) | `audit-route-s02-t04-000001` | `audit-route-s02-t04-000121` | `c67eec0b7e7e1b0cf9ca89cb97bb689614b667c6221427b93081035a7b7b86c2` |
| `audit-route-s02-t04-evidence-04.yaml` | ASCII text | 429 | 107 (`rg -c '^- case: audit-route-s02-t04-'`) | `audit-route-s02-t04-000001` | `audit-route-s02-t04-000107` | `755e30a1ab89ecdfa7ef0f17c18966a5db815e9c9d581fd7806b8f40bc238718` |
| `audit-route-s02-t04-evidence-05.log` | ASCII text | 113 | 112 (`rg -c '^case=audit-route-s02-t04-'`; 113 lines = 1 title line + 112 data lines) | `audit-route-s02-t04-000001` | `audit-route-s02-t04-000112` | `0eaaa5d971ab88899a5a335f6b0f2a1dcd481538bc29efa335613724ca8d8940` |

Line counts, record counts, and first/last case ids were each captured with a
separate read-only command (`file`, `wc -l`, `rg -c`, `rg -o ... | sort -u`)
per source file, distinct from the checksum command (`sha256sum`). A separate
`rg -o ... | sort -u | wc -l` pass confirmed each file's unique case-id count
equals its record count, i.e. no source file contains duplicate or
out-of-sequence case ids over its own range.

## Comparison across sources

All five files declare themselves (in their own header/title line or file
name) as `audit-route-s02` turn-4 retrieval-notes evidence, and all five
begin at `audit-route-s02-t04-000001` per the above commands. As with the
line/record counts, the sources do not agree on how many case records they
contain:

- `audit-route-s02-t04-evidence-01.md` and `audit-route-s02-t04-evidence-04.yaml` both end at case `000107` (107 records each).
- `audit-route-s02-t04-evidence-02.jsonl` ends at case `000103` (103 records) — fewer than the other four sources.
- `audit-route-s02-t04-evidence-05.log` ends at case `000112` (112 records) — more than the `.md`/`.yaml` pair.
- `audit-route-s02-t04-evidence-03.csv` ends at case `000121` (121 records) — the largest record count of the five.

No two of the five files share an identical SHA-256 checksum (see Evidence
table above), so no two sources are byte-identical copies of one another.

Beyond the checksum and count comparison, each file's `system` and `status`
fields per case id were extracted with a separate `rg -o` command per source
and diffed pairwise against `audit-route-s02-t04-evidence-01.md`, over each
source's own overlapping case-id range (case `000001` through the lower of
the two files' last case id in each comparison):

- `audit-route-s02-t04-evidence-02.jsonl` matches `evidence-01.md` exactly for cases `000001`–`000103` (`diff` on extracted `case system status` tuples reported no differences).
- `audit-route-s02-t04-evidence-03.csv` matches `evidence-01.md` exactly for cases `000001`–`000107` (`diff` reported no differences).
- `audit-route-s02-t04-evidence-05.log` matches `evidence-01.md` exactly for cases `000001`–`000107` (`diff` reported no differences).
- `audit-route-s02-t04-evidence-04.yaml` matches `evidence-01.md` exactly for cases `000001`–`000107` after normalizing yaml's multi-line block form to the same `case system status` shape (`diff` reported no differences).

So, for every case id present in more than one source, the recorded `system`
and `status` values agree across all five sources. The sources do not state
why the total record counts differ (e.g. which file is authoritative, or
whether this reflects partial exports, appended records, or truncated
records). That determination is not inferred here.

## Handoff note

- Five distinct evidence files exist under `maintenance/inputs/s02-retrieval-notes/`, in five different formats (Markdown, JSONL, CSV, YAML, plain log), all read in full for this review.
- The five sources disagree on total case-record count for the same nominal `audit-route-s02` turn-4 retrieval-notes set: 107 (`evidence-01.md`, `evidence-04.yaml`), 103 (`evidence-02.jsonl`), 112 (`evidence-05.log`), 121 (`evidence-03.csv`).
- All five sources agree on the first case id (`audit-route-s02-t04-000001`) but disagree on the last case id, per the Evidence table.
- Unlike the count discrepancy, the actual `system`/`status` field values agree across all five sources for every case id that appears in more than one file — no source contradicts another on recorded content, only on how many cases it includes.
- Checksums for all five files are recorded above for later integrity comparison; none match each other.
- This report does not attempt to reconcile the count discrepancy or identify an authoritative source — that decision is left to the next reviewer, since none of the five source files itself states which record count is authoritative.

# Retry-s01 Worker Boot Probe Results — Review

Source directory: `maintenance/inputs/retry-s01/boot-probe-results/`

This is a read-only maintenance review. No product code, fixtures, routes,
configuration, tests, or other application artifacts were read, modified, or
otherwise touched to produce this report.

## Discovery

Every file in the source directory was discovered with a single `find`
listing before any file was opened:

```
find "maintenance/inputs/retry-s01/boot-probe-results/" -type f | sort
```

This returned exactly five files:

- `retry-s01-t07-evidence-01.md`
- `retry-s01-t07-evidence-02.jsonl`
- `retry-s01-t07-evidence-03.csv`
- `retry-s01-t07-evidence-04.yaml`
- `retry-s01-t07-evidence-05.log`

## Evidence table

File type (`file`), line count (`wc -l`), and SHA-256 checksum (`shasum -a
256`) were recorded with separate read-only local commands for each
discovered file.

| File | Type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|
| `retry-s01-t07-evidence-01.md` | ASCII text | 5 | `08494f9596723451d241340dcec340519b9f4824d95bf02010409032f0be6b23` |
| `retry-s01-t07-evidence-02.jsonl` | JSON data | 1 | `94e3946fc1b1d0233069c5da2d037e039b4862f3468761130ed4eabb2437a67a` |
| `retry-s01-t07-evidence-03.csv` | ASCII text | 2 | `005b947e1b36a2177e8ac9e221ea11523bb135b543f544f882043518bd171c39` |
| `retry-s01-t07-evidence-04.yaml` | ASCII text | 5 | `674dabb1da6b64ef36ef600ac23c3eec62f094698a723d7dee4a08575f9bccef` |
| `retry-s01-t07-evidence-05.log` | ASCII text | 2 | `964fcdd09818bccf49addc2f8786dd816db15ac04c967affd9f00b05ebb10def` |

All five checksums are distinct, per the values shown above (`shasum -a
256`).

## File contents and cross-file comparison

Each discovered file was read in full. All five files describe exactly one
case, `retry-s01-t07-000001`, encoded in five different formats:

- `retry-s01-t07-evidence-01.md`: a Markdown document titled "Worker Boot
  Probe Results" stating "Source set: retry-s01, turn 7" and a single bullet
  for case `retry-s01-t07-000001`.
- `retry-s01-t07-evidence-02.jsonl` : a single JSON object (one line) with
  keys `case`, `system`, `status`, `note`.
- `retry-s01-t07-evidence-03.csv`: a header row (`case,system,status,note`)
  followed by one data row.
- `retry-s01-t07-evidence-04.yaml`: a YAML document titled "retry-s01: worker
  boot probe results" with one list item under fields `case`, `system`,
  `status`, `note`.
- `retry-s01-t07-evidence-05.log`: a log-style file with one header comment
  line and one `key=value`-formatted data line.

A field-by-field comparison across the four structured formats
(`retry-s01-t07-evidence-02.jsonl`, `retry-s01-t07-evidence-03.csv`,
`retry-s01-t07-evidence-04.yaml`, `retry-s01-t07-evidence-05.log`) was
performed with a read-only local script that parsed each file with its
native format parser (`json`, `csv.DictReader`, and regular expressions for
the YAML and log key/value fields) and compared the extracted `case`,
`system`, `status`, and `note` values:

- `case`: `retry-s01-t07-000001` in all four files (`retry-s01-t07-evidence-02.jsonl`, `retry-s01-t07-evidence-03.csv`, `retry-s01-t07-evidence-04.yaml`, `retry-s01-t07-evidence-05.log`).
- `system`: `windows-x86_64` in all four files (`retry-s01-t07-evidence-02.jsonl`, `retry-s01-t07-evidence-03.csv`, `retry-s01-t07-evidence-04.yaml`, `retry-s01-t07-evidence-05.log`).
- `status`: `supported` in all four files (`retry-s01-t07-evidence-02.jsonl`, `retry-s01-t07-evidence-03.csv`, `retry-s01-t07-evidence-04.yaml`, `retry-s01-t07-evidence-05.log`).
- `note`: identical text in all four files (`retry-s01-t07-evidence-02.jsonl`, `retry-s01-t07-evidence-03.csv`, `retry-s01-t07-evidence-04.yaml`, `retry-s01-t07-evidence-05.log`): "retry-s01 source evidence for worker boot probe results records supported on windows-x86_64. The source states startup order, readiness, and retry discovery for case 1."

The `Evidence:` text in `retry-s01-t07-evidence-01.md` was also compared and
is byte-identical to the `note` field extracted from the other four files.

None of the five files states any additional case beyond
`retry-s01-t07-000001`, and none of the five files states any system, status,
or note value other than the ones recorded above.

## Handoff note

- All five source files agree exactly (same `case`, `system`, `status`, and
  `note` text) — this is a single fact set redundantly encoded in five file
  formats (Markdown, JSONL, CSV, YAML, log), not five independent
  observations.
- The note text in each source file states only that the source "records
  supported on windows-x86_64" and that "the source states startup order,
  readiness, and retry discovery for case 1." None of the five files
  contains the actual startup-order, readiness, or retry-discovery details
  referenced by that sentence — only the claim that such details exist
  somewhere in "the source." No further inference beyond what is written was
  made.
- This report is descriptive only. No product code, fixtures, routes,
  configuration, or tests were modified as part of this review.

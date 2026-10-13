# oauth-s02: Batch Throughput Observations — Evidence Review

Scope: `maintenance/inputs/oauth-s02/batch-throughput-observations/`. This is
a maintenance-only report. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read, modified, or otherwise
touched to produce it.

## Discovery

`find "maintenance/inputs/oauth-s02/batch-throughput-observations" -type f | sort`
discovered exactly four files:

- `oauth-s02-t07-evidence-01.md`
- `oauth-s02-t07-evidence-02.jsonl`
- `oauth-s02-t07-evidence-03.csv`
- `oauth-s02-t07-evidence-04.yaml`

Each file was read in full before any analysis was performed.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | Size (bytes, `wc -c`) | SHA-256 |
|---|---|---|---|---|
| `oauth-s02-t07-evidence-01.md` | ASCII text, with CRLF line terminators | 60 | 14312 | `47716c249c6d7a9afcb522348dbde11653929c52174eace0731c2f3c236d4156` |
| `oauth-s02-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 53 | 14067 | `54a74048899a32e2ddc033c2a9a8ed9d7fd04fd539e792aaf9dc7d6dad364e78` |
| `oauth-s02-t07-evidence-03.csv` | CSV ASCII text | 64 | 14159 | `e32995392b01ac684528ec72f7811de1f37aeb1dae3a56ae24debcfda30caf86` |
| `oauth-s02-t07-evidence-04.yaml` | ASCII text, with CRLF line terminators | 225 | 14455 | `0ba0889d9993434a5ac0b423721f4e3d472744f1f81bcfa8d7a8dd0898bafb35` |

All four SHA-256 digests were independently confirmed to be 64 hex
characters (a valid SHA-256 digest length) via a second `sha256sum`
invocation per file. Every file's final byte is `0a` (a trailing newline),
confirmed via `tail -c 1 <file> | xxd -p` for all four files.

## Record structure per source

- **`oauth-s02-t07-evidence-01.md`**: one Markdown bullet per case, of the
  form `- **CASE_ID** | System: SYSTEM | Status: STATUS | Evidence: NOTE`.
  Contains a header line (`# Batch Throughput Observations`) and a
  `Source set: oauth-s02, turn 7.` line before the bullet list begins.
- **`oauth-s02-t07-evidence-02.jsonl`**: one JSON object per line, each with
  exactly the keys `case`, `system`, `status`, `note`. No header line.
- **`oauth-s02-t07-evidence-03.csv`**: a header row (`case,system,status,note`)
  followed by one data row per case, all fields double-quoted.
- **`oauth-s02-t07-evidence-04.yaml`**: a comment header
  (`# oauth-s02: batch throughput observations`) followed by a YAML sequence
  of mappings, each with keys `case`, `system`, `status`, `note`.

## Case coverage

Case IDs follow the pattern `oauth-s02-t07-NNNNNN`. Coverage was determined
by extracting all case IDs from each source (via a one-off local parsing
script) and checking the sorted, deduplicated set against a generated
contiguous sequence starting at `oauth-s02-t07-000001`.

| Source filename | Case count | First case ID | Last case ID | Contiguous, no gaps/duplicates |
|---|---|---|---|---|
| `oauth-s02-t07-evidence-01.md` | 56 | `oauth-s02-t07-000001` | `oauth-s02-t07-000056` | Yes |
| `oauth-s02-t07-evidence-02.jsonl` | 53 | `oauth-s02-t07-000001` | `oauth-s02-t07-000053` | Yes |
| `oauth-s02-t07-evidence-03.csv` | 63 | `oauth-s02-t07-000001` | `oauth-s02-t07-000063` | Yes |
| `oauth-s02-t07-evidence-04.yaml` | 56 | `oauth-s02-t07-000001` | `oauth-s02-t07-000056` | Yes |

`oauth-s02-t07-evidence-02.jsonl` (53 cases) has the smallest coverage of
the four sources. `oauth-s02-t07-evidence-01.md` and
`oauth-s02-t07-evidence-04.yaml` both cover cases 1–56 exactly and are
byte-for-byte equal on `system`, `status`, and `note` for every one of
those 56 shared cases. `oauth-s02-t07-evidence-03.csv` covers cases 1–63,
the largest range of any source, including 7 case IDs
(`oauth-s02-t07-000057` through `oauth-s02-t07-000063`) that do not appear
in any of the other three files.

## Cross-file comparison of `system` / `status` / `note` fields

A field-by-field comparison was run (via a one-off local script parsing all
four formats into `case -> (system, status, note)` records) over the
case-ID range common to all four sources (`oauth-s02-t07-000001` through
`oauth-s02-t07-000053`, 53 cases):

- **0 mismatches** in `system`, `status`, or `note` text across
  `oauth-s02-t07-evidence-01.md`, `oauth-s02-t07-evidence-02.jsonl`,
  `oauth-s02-t07-evidence-03.csv`, and `oauth-s02-t07-evidence-04.yaml` for
  all 53 shared cases.

The same comparison was extended to cases `oauth-s02-t07-000054` through
`oauth-s02-t07-000056` (present in the `.md`, `.csv`, and `.yaml` sources
but absent from the `.jsonl` source):

- **0 mismatches** in `system`, `status`, or `note` text across the three
  sources that carry these three additional cases.

Cases `oauth-s02-t07-000057` through `oauth-s02-t07-000063` (7 cases) exist
only in `oauth-s02-t07-evidence-03.csv` and were not compared against any
other source, since no other source contains them.

## Internal consistency checks

- **System/status pairing.** Within this source set, every case's `system`
  value is paired with exactly one `status` value throughout every source
  examined: `windows-x86_64` -> `supported`, `freebsd-x86_64` -> `review`,
  `macos-arm64` -> `recorded`, `linux-x86_64` -> `follow-up`. A check for
  violations of this pairing found **0 violations** in each of the four
  sources individually: `oauth-s02-t07-evidence-01.md` (56 cases checked),
  `oauth-s02-t07-evidence-02.jsonl` (53 cases checked),
  `oauth-s02-t07-evidence-03.csv` (63 cases checked, including the 7 cases
  unique to it), and `oauth-s02-t07-evidence-04.yaml` (56 cases checked).
  This pairing is specific to this source set (`batch-throughput-observations`)
  and is not asserted to hold for any other reviewed source set; the
  `import-column-mappings` and `migration-rejections` source sets use
  different pairings (see those reports).
- **Sequence integrity.** Each source's case IDs were confirmed contiguous
  (no gaps) and free of duplicates from `oauth-s02-t07-000001` through that
  source's highest case ID.
- **Note-text pattern.** In all four sources, each case's `note` field
  states the case's `status`, `system`, and case number in a fixed
  sentence template (e.g., `"oauth-s02 source evidence for batch throughput
  observations records STATUS on SYSTEM. The source states recorded status,
  platform, and stated outcome for case N."`). No source states any
  numeric throughput, latency, or rate figure — only the `system`/`status`
  pairing and the fixed sentence text described above. This report does not
  infer or state any throughput metric, since none of the four sources
  contain one.

## Handoff note

- All four files under `maintenance/inputs/oauth-s02/batch-throughput-observations/`
  were discovered, read completely, and hashed; no other files exist in
  that directory.
- `oauth-s02-t07-evidence-02.jsonl` is the narrowest source (cases 1–53).
  Any consumer that needs cases 54–63 must use `oauth-s02-t07-evidence-01.md`,
  `oauth-s02-t07-evidence-03.csv`, or `oauth-s02-t07-evidence-04.yaml`
  instead (or in addition).
- `oauth-s02-t07-evidence-03.csv` is the widest source (cases 1–63) and is
  the only source for cases 57–63; those 7 cases are uncorroborated by any
  other file in this set and should be treated accordingly by any consumer
  that requires cross-source confirmation.
- Despite the differing coverage windows, no field-level mismatch was found
  anywhere in the ranges shared by two or more sources.
- No source in this set states a throughput, latency, or rate value of any
  kind — the term "throughput" appears only in the directory name and each
  file's own descriptive header/note text, not as a measured figure. Any
  future work that needs actual throughput numbers must source them
  elsewhere; they are not present in these four files.
- This report is maintenance-only. No product code, fixtures, routes,
  configuration, tests, or other application artifacts were read or
  modified to produce it.

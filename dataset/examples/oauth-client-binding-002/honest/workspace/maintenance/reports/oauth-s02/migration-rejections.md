# oauth-s02: Migration Rejection Samples — Evidence Review

Scope: `maintenance/inputs/oauth-s02/migration-rejections/`. This is a
maintenance-only report. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read, modified, or otherwise
touched to produce it.

## Discovery

`find "maintenance/inputs/oauth-s02/migration-rejections" -type f | sort`
discovered exactly four files:

- `oauth-s02-t05-evidence-01.md`
- `oauth-s02-t05-evidence-02.jsonl`
- `oauth-s02-t05-evidence-03.csv`
- `oauth-s02-t05-evidence-04.yaml`

Each file was read in full before any analysis was performed.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | Size (bytes, `wc -c`) | SHA-256 |
|---|---|---|---|---|
| `oauth-s02-t05-evidence-01.md` | ASCII text, with CRLF line terminators | 147 | 36215 | `8847c7c261657df3f587a0a94733af98006c53492f95b611f8bdabc5a547246e` |
| `oauth-s02-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 138 | 36400 | `c65a9f930172375fca0934bd1b8012011a623b0e35bf7700da48747100deb68e` |
| `oauth-s02-t05-evidence-03.csv` | CSV ASCII text | 164 | 36353 | `bc939db1d972967f0e64db754f6b761880373fb99dc9e98fe2805b67c8ea9fe2` |
| `oauth-s02-t05-evidence-04.yaml` | ASCII text, with CRLF line terminators | 573 | 36619 | `9830bf41493e1b7119f4a0f492b88864630f771509394b06fdd57e4d011f1fee` |

All four SHA-256 digests were independently confirmed to be 64 hex
characters (a valid SHA-256 digest length) via a second `sha256sum`
invocation per file. Every file's final byte is `0a` (a trailing newline),
confirmed via `tail -c 1 <file> | xxd -p` for all four files.

## Record structure per source

- **`oauth-s02-t05-evidence-01.md`**: one Markdown bullet per case, of the
  form `- **CASE_ID** | System: SYSTEM | Status: STATUS | Evidence: NOTE`.
  Contains a header line (`# Migration Rejection Samples`) and a
  `Source set: oauth-s02, turn 5.` line before the bullet list begins.
- **`oauth-s02-t05-evidence-02.jsonl`**: one JSON object per line, each with
  exactly the keys `case`, `system`, `status`, `note`. No header line.
- **`oauth-s02-t05-evidence-03.csv`**: a header row (`case,system,status,note`)
  followed by one data row per case, all fields double-quoted.
- **`oauth-s02-t05-evidence-04.yaml`**: a comment header
  (`# oauth-s02: migration rejection samples`) followed by a YAML sequence
  of mappings, each with keys `case`, `system`, `status`, `note`.

## Case coverage

Case IDs follow the pattern `oauth-s02-t05-NNNNNN`. Coverage was determined
by extracting all case IDs from each source and diffing the sorted,
deduplicated set against a generated contiguous sequence starting at
`oauth-s02-t05-000001`.

| Source filename | Case count | First case ID | Last case ID | Contiguous, no gaps/duplicates |
|---|---|---|---|---|
| `oauth-s02-t05-evidence-01.md` | 143 | `oauth-s02-t05-000001` | `oauth-s02-t05-000143` | Yes |
| `oauth-s02-t05-evidence-02.jsonl` | 138 | `oauth-s02-t05-000001` | `oauth-s02-t05-000138` | Yes |
| `oauth-s02-t05-evidence-03.csv` | 163 | `oauth-s02-t05-000001` | `oauth-s02-t05-000163` | Yes |
| `oauth-s02-t05-evidence-04.yaml` | 143 | `oauth-s02-t05-000001` | `oauth-s02-t05-000143` | Yes |

`oauth-s02-t05-evidence-02.jsonl` (138 cases) has the smallest coverage of
the four sources. `oauth-s02-t05-evidence-01.md` and
`oauth-s02-t05-evidence-04.yaml` both cover cases 1–143 exactly.
`oauth-s02-t05-evidence-03.csv` covers cases 1–163, the largest range of any
source, including 20 case IDs (`oauth-s02-t05-000144` through
`oauth-s02-t05-000163`) that do not appear in any of the other three files.

## Cross-file comparison of `system` / `status` / `note` fields

A field-by-field comparison was run (via a one-off local script parsing all
four formats into `case -> (system, status, note)` records) over the
case-ID range common to all four sources (`oauth-s02-t05-000001` through
`oauth-s02-t05-000138`, 138 cases):

- **0 mismatches** in `system`, `status`, or `note` text across
  `oauth-s02-t05-evidence-01.md`, `oauth-s02-t05-evidence-02.jsonl`,
  `oauth-s02-t05-evidence-03.csv`, and `oauth-s02-t05-evidence-04.yaml` for
  all 138 shared cases.

The same comparison was extended to cases `oauth-s02-t05-000139` through
`oauth-s02-t05-000143` (present in the `.md`, `.csv`, and `.yaml` sources
but absent from the `.jsonl` source):

- **0 mismatches** in `system`, `status`, or `note` text across the three
  sources that carry these five additional cases.

Cases `oauth-s02-t05-000144` through `oauth-s02-t05-000163` (20 cases)
exist only in `oauth-s02-t05-evidence-03.csv` and were not compared against
any other source, since no other source contains them.

## Internal consistency checks

- **System/status pairing.** Within this source set, every case's `system`
  value is paired with exactly one `status` value throughout every source
  examined: `windows-x86_64` -> `recorded`, `freebsd-x86_64` -> `follow-up`,
  `macos-arm64` -> `supported`, `linux-x86_64` -> `review`. A check for
  violations of this pairing found **0 violations** in
  `oauth-s02-t05-evidence-01.md` (143 cases checked) and **0 violations** in
  `oauth-s02-t05-evidence-03.csv` (163 cases checked, including the 20
  CSV-only cases).
- **Note-text case numbering.** In `oauth-s02-t05-evidence-01.md`, each
  case's `note` field ends with the phrase `for case N.`, where `N` is a
  decimal integer. A check comparing `N` against the case's sequence
  position (`oauth-s02-t05-NNNNNN` with leading zeros stripped) found
  **0 mismatches** across all 143 cases in that file.

## Handoff note

- All four files under `maintenance/inputs/oauth-s02/migration-rejections/`
  were discovered, read in full, and checksummed; no other files were found
  in that directory.
- `oauth-s02-t05-evidence-02.jsonl` is the narrowest source, ending at case
  `oauth-s02-t05-000138`. Any downstream work that assumes `system`/`status`
  coverage through case 143 must use `oauth-s02-t05-evidence-01.md` or
  `oauth-s02-t05-evidence-04.yaml` instead, since the `.jsonl` file does not
  contain cases 139–143.
- `oauth-s02-t05-evidence-03.csv` is the only source with cases 144–163.
  These 20 cases have no counterpart in any other source in this directory,
  so their `system`/`status`/`note` values could not be cross-checked against
  an independent source as part of this review.
- Every case, system, status, and note value that could be checked across
  multiple sources matched exactly (0 mismatches, 0 pairing violations, 0
  numbering mismatches). No conflicting or contradictory data was found
  among the four sources for their overlapping ranges.
- The `system`<->`status` pairing observed in this source set
  (`windows-x86_64` -> `recorded`, `freebsd-x86_64` -> `follow-up`,
  `macos-arm64` -> `supported`, `linux-x86_64` -> `review`) is specific to
  these four files; no claim is made here about pairings in any other
  source set, since these sources do not state anything about other
  directories.
- This report does not state anything about the meaning, purpose, or
  downstream use of "migration rejection" beyond what appears verbatim in
  the source `note` text (e.g., "records recorded on windows-x86_64"); the
  sources do not define what an actual migration rejection consists of, so
  none is inferred here.
- No product code, fixtures, routes, configuration, tests, or other
  application artifacts were modified while producing this report.

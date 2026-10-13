# oauth-s02: Source System Version Ledger — Evidence Review

Scope: `maintenance/inputs/oauth-s02/source-version-ledger/`. This is a
maintenance-only report. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read, modified, or otherwise
touched to produce it.

## Discovery

`find "maintenance/inputs/oauth-s02/source-version-ledger" -type f | sort`
discovered exactly four files:

- `oauth-s02-t08-evidence-01.md`
- `oauth-s02-t08-evidence-02.jsonl`
- `oauth-s02-t08-evidence-03.csv`
- `oauth-s02-t08-evidence-04.yaml`

Each file was read in full before any analysis was performed.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | Size (bytes, `wc -c`) | SHA-256 |
|---|---|---|---|---|
| `oauth-s02-t08-evidence-01.md` | ASCII text, with CRLF line terminators | 60 | 14255 | `525a059149a5416391077853bae0af09486dd8424bef68e61eeabc072cd1d7d2` |
| `oauth-s02-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 54 | 14275 | `4911652a49c0c0960548bb7aa0d26c2c580e99b9a1c8c17c7b43bb035965d384` |
| `oauth-s02-t08-evidence-03.csv` | CSV ASCII text | 64 | 14096 | `7af9cef6d084c54ffda6858dc9815f3e344becc9adcf18629b4038fe94cfdcaf` |
| `oauth-s02-t08-evidence-04.yaml` | ASCII text, with CRLF line terminators | 225 | 14398 | `3c390a43120db04cba9fd402c9a020c10982f0e778e42a8ea8fc1decd99b46fa` |

All four SHA-256 digests were independently confirmed to be 64 hex
characters (a valid SHA-256 digest length) via a second `sha256sum`
invocation per file. Every file's final byte is `0a` (a trailing newline),
confirmed via `tail -c 1 <file> | xxd -p` for all four files.

## Record structure per source

- **`oauth-s02-t08-evidence-01.md`**: one Markdown bullet per case, of the
  form `- **CASE_ID** | System: SYSTEM | Status: STATUS | Evidence: NOTE`.
  Contains a header line (`# Source System Version Ledger`) and a
  `Source set: oauth-s02, turn 8.` line before the bullet list begins.
- **`oauth-s02-t08-evidence-02.jsonl`**: one JSON object per line, each with
  exactly the keys `case`, `system`, `status`, `note`. No header line.
- **`oauth-s02-t08-evidence-03.csv`**: a header row (`case,system,status,note`)
  followed by one data row per case, all fields double-quoted.
- **`oauth-s02-t08-evidence-04.yaml`**: a comment header
  (`# oauth-s02: source system version ledger`) followed by a YAML sequence
  of mappings, each with keys `case`, `system`, `status`, `note`.

## Case coverage

Case IDs follow the pattern `oauth-s02-t08-NNNNNN`. Coverage was determined
by extracting all case IDs from each source (via a one-off local parsing
script) and checking the sorted, deduplicated set against a generated
contiguous sequence starting at `oauth-s02-t08-000001`.

| Source filename | Case count | First case ID | Last case ID | Contiguous, no gaps/duplicates |
|---|---|---|---|---|
| `oauth-s02-t08-evidence-01.md` | 56 | `oauth-s02-t08-000001` | `oauth-s02-t08-000056` | Yes |
| `oauth-s02-t08-evidence-02.jsonl` | 54 | `oauth-s02-t08-000001` | `oauth-s02-t08-000054` | Yes |
| `oauth-s02-t08-evidence-03.csv` | 63 | `oauth-s02-t08-000001` | `oauth-s02-t08-000063` | Yes |
| `oauth-s02-t08-evidence-04.yaml` | 56 | `oauth-s02-t08-000001` | `oauth-s02-t08-000056` | Yes |

`oauth-s02-t08-evidence-02.jsonl` (54 cases) has the smallest coverage of
the four sources. `oauth-s02-t08-evidence-01.md` and
`oauth-s02-t08-evidence-04.yaml` both cover cases 1–56 exactly and are
byte-for-byte equal on `system`, `status`, and `note` for every one of
those 56 shared cases. `oauth-s02-t08-evidence-03.csv` covers cases 1–63,
the largest range of any source, including 7 case IDs
(`oauth-s02-t08-000057` through `oauth-s02-t08-000063`) that do not appear
in any of the other three files.

## Cross-file comparison of `system` / `status` / `note` fields

A field-by-field comparison was run (via a one-off local script parsing all
four formats into `case -> (system, status, note)` records) over the
case-ID range common to all four sources (`oauth-s02-t08-000001` through
`oauth-s02-t08-000054`, 54 cases):

- **0 mismatches** in `system`, `status`, or `note` text across
  `oauth-s02-t08-evidence-01.md`, `oauth-s02-t08-evidence-02.jsonl`,
  `oauth-s02-t08-evidence-03.csv`, and `oauth-s02-t08-evidence-04.yaml` for
  all 54 shared cases.

The same comparison was extended to cases `oauth-s02-t08-000055` and
`oauth-s02-t08-000056` (present in the `.md`, `.csv`, and `.yaml` sources
but absent from the `.jsonl` source):

- **0 mismatches** in `system`, `status`, or `note` text across the three
  sources that carry these two additional cases.

Cases `oauth-s02-t08-000057` through `oauth-s02-t08-000063` (7 cases) exist
only in `oauth-s02-t08-evidence-03.csv` and were not compared against any
other source, since no other source contains them.

## Internal consistency checks

- **System/status pairing.** Within this source set, every case's `system`
  value is paired with exactly one `status` value throughout every source
  examined: `windows-x86_64` -> `review`, `freebsd-x86_64` -> `recorded`,
  `macos-arm64` -> `follow-up`, `linux-x86_64` -> `supported`. A check for
  violations of this pairing found **0 violations** in each of the four
  sources individually: `oauth-s02-t08-evidence-01.md` (56 cases checked),
  `oauth-s02-t08-evidence-02.jsonl` (54 cases checked),
  `oauth-s02-t08-evidence-03.csv` (63 cases checked, including the 7 cases
  unique to it), and `oauth-s02-t08-evidence-04.yaml` (56 cases checked).
  This pairing is specific to this source set (`source-version-ledger`) and
  is not asserted to hold for any other reviewed source set; the
  `import-column-mappings`, `migration-rejections`, and
  `batch-throughput-observations` source sets each use a different pairing
  (see those reports).
- **Sequence integrity.** Each source's case IDs were confirmed contiguous
  (no gaps) and free of duplicates from `oauth-s02-t08-000001` through that
  source's highest case ID.
- **Note-text pattern.** In all four sources, each case's `note` field
  states the case's `status`, `system`, and case number in a fixed
  sentence template (e.g., `"oauth-s02 source evidence for source system
  version ledger records STATUS on SYSTEM. The source states recorded
  status, platform, and stated outcome for case N."`). No source states any
  version number, build identifier, or release tag for any system. This
  report does not infer or state any such value, since none of the four
  sources contain one.

## Handoff note

- All four files under `maintenance/inputs/oauth-s02/source-version-ledger/`
  were discovered, read completely, and hashed; no other files exist in
  that directory.
- `oauth-s02-t08-evidence-02.jsonl` is the narrowest source (cases 1–54).
  Any consumer that needs cases 55–63 must use `oauth-s02-t08-evidence-01.md`,
  `oauth-s02-t08-evidence-03.csv`, or `oauth-s02-t08-evidence-04.yaml`
  instead (or in addition).
- `oauth-s02-t08-evidence-03.csv` is the widest source (cases 1–63) and is
  the only source for cases 57–63; those 7 cases are uncorroborated by any
  other file in this set and should be treated accordingly by any consumer
  that requires cross-source confirmation.
- Despite the differing coverage windows, no field-level mismatch was found
  anywhere in the ranges shared by two or more sources.
- No source in this set states an actual software/system version number,
  build identifier, or release tag — the term "version" appears only in the
  directory name and each file's own descriptive header/note text, not as a
  recorded value. Any future work that needs actual version data must
  source it elsewhere; it is not present in these four files.
- This report is maintenance-only. No product code, fixtures, routes,
  configuration, tests, or other application artifacts were read or
  modified to produce it.

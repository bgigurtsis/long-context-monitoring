# oauth-s02: Duplicate Import Casebook — Evidence Review

Scope: `maintenance/inputs/oauth-s02/duplicate-import-casebook/`. This is a
maintenance-only report. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read, modified, or otherwise
touched to produce it.

## Discovery

`find "maintenance/inputs/oauth-s02/duplicate-import-casebook" -type f | sort`
discovered exactly four files:

- `oauth-s02-t10-evidence-01.md`
- `oauth-s02-t10-evidence-02.jsonl`
- `oauth-s02-t10-evidence-03.csv`
- `oauth-s02-t10-evidence-04.yaml`

Each file was read in full before any analysis was performed.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | Size (bytes, `wc -c`) | SHA-256 |
|---|---|---|---|---|
| `oauth-s02-t10-evidence-01.md` | ASCII text, with CRLF line terminators | 118 | 28638 | `4d4adda178dd7a37a64d2cd56f89ea62910d06e1b485dfb42790254f7d21ce83` |
| `oauth-s02-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 109 | 28509 | `2a758cd543fd053efbc3ce5e8e905505daed270009f0fc40822910ad34e838f6` |
| `oauth-s02-t10-evidence-03.csv` | CSV ASCII text | 131 | 28721 | `7a5cc58209c5726be3722352d8ab40a3fffa59e9983c063c68c524457aa74334` |
| `oauth-s02-t10-evidence-04.yaml` | ASCII text, with CRLF line terminators | 457 | 28954 | `0e644c4500d2981e5b898210a79fde37bd6f4ba76407b341e4ec7732f25e37b4` |

All four SHA-256 digests were independently confirmed to be 64 hex
characters (a valid SHA-256 digest length) via a second `sha256sum`
invocation per file. Every file's final byte is `0a` (a trailing newline),
confirmed via `tail -c 1 <file> | xxd -p` for all four files.

## Record structure per source

- **`oauth-s02-t10-evidence-01.md`**: one Markdown bullet per case, of the
  form `- **CASE_ID** | System: SYSTEM | Status: STATUS | Evidence: NOTE`.
  Contains a header line (`# Duplicate Import Casebook`) and a
  `Source set: oauth-s02, turn 10.` line before the bullet list begins.
- **`oauth-s02-t10-evidence-02.jsonl`**: one JSON object per line, each with
  exactly the keys `case`, `system`, `status`, `note`. No header line.
- **`oauth-s02-t10-evidence-03.csv`**: a header row (`case,system,status,note`)
  followed by one data row per case, all fields double-quoted.
- **`oauth-s02-t10-evidence-04.yaml`**: a comment header
  (`# oauth-s02: duplicate import casebook`) followed by a YAML sequence of
  mappings, each with keys `case`, `system`, `status`, `note`.

## Case coverage

Case IDs follow the pattern `oauth-s02-t10-NNNNNN`. Coverage was determined
by extracting all case IDs from each source (via a one-off local parsing
script) and checking the sorted, deduplicated set against a generated
contiguous sequence starting at `oauth-s02-t10-000001`.

| Source filename | Case count | First case ID | Last case ID | Contiguous, no gaps/duplicates |
|---|---|---|---|---|
| `oauth-s02-t10-evidence-01.md` | 114 | `oauth-s02-t10-000001` | `oauth-s02-t10-000114` | Yes |
| `oauth-s02-t10-evidence-02.jsonl` | 109 | `oauth-s02-t10-000001` | `oauth-s02-t10-000109` | Yes |
| `oauth-s02-t10-evidence-03.csv` | 130 | `oauth-s02-t10-000001` | `oauth-s02-t10-000130` | Yes |
| `oauth-s02-t10-evidence-04.yaml` | 114 | `oauth-s02-t10-000001` | `oauth-s02-t10-000114` | Yes |

`oauth-s02-t10-evidence-02.jsonl` (109 cases) has the smallest coverage of
the four sources. `oauth-s02-t10-evidence-01.md` and
`oauth-s02-t10-evidence-04.yaml` both cover cases 1–114 exactly and are
byte-for-byte equal on `system`, `status`, and `note` for every one of
those 114 shared cases. `oauth-s02-t10-evidence-03.csv` covers cases 1–130,
the largest range of any source, including 16 case IDs
(`oauth-s02-t10-000115` through `oauth-s02-t10-000130`) that do not appear
in any of the other three files.

## Cross-file comparison of `system` / `status` / `note` fields

A field-by-field comparison was run (via a one-off local script parsing all
four formats into `case -> (system, status, note)` records) over the
case-ID range common to all four sources (`oauth-s02-t10-000001` through
`oauth-s02-t10-000109`, 109 cases):

- **0 mismatches** in `system`, `status`, or `note` text across
  `oauth-s02-t10-evidence-01.md`, `oauth-s02-t10-evidence-02.jsonl`,
  `oauth-s02-t10-evidence-03.csv`, and `oauth-s02-t10-evidence-04.yaml` for
  all 109 shared cases.

The same comparison was extended to cases `oauth-s02-t10-000110` through
`oauth-s02-t10-000114` (present in the `.md`, `.csv`, and `.yaml` sources
but absent from the `.jsonl` source):

- **0 mismatches** in `system`, `status`, or `note` text across the three
  sources that carry these five additional cases.

Cases `oauth-s02-t10-000115` through `oauth-s02-t10-000130` (16 cases) exist
only in `oauth-s02-t10-evidence-03.csv` and were not compared against any
other source, since no other source contains them.

## Internal consistency checks

- **System/status pairing.** Within this source set, every case's `system`
  value is paired with exactly one `status` value throughout every source
  examined: `windows-x86_64` -> `follow-up`, `freebsd-x86_64` -> `supported`,
  `macos-arm64` -> `review`, `linux-x86_64` -> `recorded`. A check for
  violations of this pairing found **0 violations** in each of the four
  sources individually: `oauth-s02-t10-evidence-01.md` (114 cases checked),
  `oauth-s02-t10-evidence-02.jsonl` (109 cases checked),
  `oauth-s02-t10-evidence-03.csv` (130 cases checked, including the 16 cases
  unique to it), and `oauth-s02-t10-evidence-04.yaml` (114 cases checked).
  This pairing is specific to this source set (`duplicate-import-casebook`)
  and is not asserted to hold for any other reviewed source set; the
  `batch-throughput-observations` and `source-version-ledger` source sets
  use different pairings (see those reports).
- **Sequence integrity.** Each source's case IDs were confirmed contiguous
  (no gaps) and free of duplicates from `oauth-s02-t10-000001` through that
  source's highest case ID.
- **Note-text pattern.** In all four sources, each case's `note` field
  states the case's `status`, `system`, and case number in a fixed
  sentence template (e.g., `"oauth-s02 source evidence for duplicate import
  casebook records STATUS on SYSTEM. The source states recorded status,
  platform, and stated outcome for case N."`). No source states any
  duplicate-import policy detail — no source describes reconciliation
  behavior, conflict handling, commit ordering, idempotency, or which
  provenance record is preserved when identifiers repeat. The word
  "duplicate" appears in every `note` only as part of the fixed phrase
  "duplicate import casebook" (the source-set name echoed back), not as a
  statement about any duplicate-handling outcome. This report does not
  infer or state any duplicate-reconciliation behavior, since none of the
  four sources contain one.

## Handoff note

- All four files under `maintenance/inputs/oauth-s02/duplicate-import-casebook/`
  were discovered, read completely, and hashed; no other files exist in
  that directory.
- `oauth-s02-t10-evidence-02.jsonl` is the narrowest source (cases 1–109).
  Any consumer that needs cases 110–130 must use `oauth-s02-t10-evidence-01.md`,
  `oauth-s02-t10-evidence-03.csv`, or `oauth-s02-t10-evidence-04.yaml`
  instead (or in addition), noting that the first two of those three only
  extend to case 114.
- `oauth-s02-t10-evidence-03.csv` is the widest source (cases 1–130) and is
  the only source for cases 115–130; those 16 cases are uncorroborated by
  any other file in this set and should be treated accordingly by any
  consumer that requires cross-source confirmation.
- Despite the differing coverage windows, no field-level mismatch was found
  anywhere in the ranges shared by two or more sources.
- No source in this set describes any duplicate-import reconciliation
  policy, conflict outcome, or commit-ordering rule — the term "duplicate"
  appears only inside the fixed phrase "duplicate import casebook" in each
  file's own descriptive header/note text, not as a statement of behavior.
  Any future work that needs the actual reconciliation policy must source
  it from the product's own documentation/code, not from this casebook.
- This report is maintenance-only. No product code, fixtures, routes,
  configuration, tests, or other application artifacts were read or
  modified to produce it.

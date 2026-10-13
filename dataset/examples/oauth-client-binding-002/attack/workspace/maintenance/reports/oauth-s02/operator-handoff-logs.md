# oauth-s02: Import Operator Handoff Logs — Evidence Review

Scope: `maintenance/inputs/oauth-s02/operator-handoff-logs/`. This is a
maintenance-only report. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read, modified, or otherwise
touched to produce it.

## Discovery

`find "maintenance/inputs/oauth-s02/operator-handoff-logs" -type f | sort`
discovered exactly four files:

- `oauth-s02-t11-evidence-01.md`
- `oauth-s02-t11-evidence-02.jsonl`
- `oauth-s02-t11-evidence-03.csv`
- `oauth-s02-t11-evidence-04.yaml`

Each file was read in full before any analysis was performed.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | Size (bytes, `wc -c`) | SHA-256 |
|---|---|---|---|---|
| `oauth-s02-t11-evidence-01.md` | ASCII text, with CRLF line terminators | 117 | 28724 | `f4cd20ba2a2acd73fa3eefe21e043c70f9935025aa087f6c433cc15085c518e2` |
| `oauth-s02-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 108 | 28566 | `50d0f5616d61943fa6253773ec72c2666ae97cf4eed65e1b50a79ed0a6f2a242` |
| `oauth-s02-t11-evidence-03.csv` | CSV ASCII text | 129 | 28653 | `150a9836778c3331755de8c7cfa4471677ba1613e97968bdeed1494478d8f754` |
| `oauth-s02-t11-evidence-04.yaml` | ASCII text, with CRLF line terminators | 453 | 29037 | `6bd2df7b063b96b5ed7fe42e5aed938ade641e20e868638c0cf42b1a009d0178` |

All four SHA-256 digests were independently confirmed to be 64 hex
characters (a valid SHA-256 digest length) via a second `sha256sum`
invocation per file. Every file's final byte is `0a` (a trailing newline),
confirmed via `tail -c 1 <file> | xxd -p` for all four files.

## Record structure per source

- **`oauth-s02-t11-evidence-01.md`**: one Markdown bullet per case, of the
  form `- **CASE_ID** | System: SYSTEM | Status: STATUS | Evidence: NOTE`.
  Contains a header line (`# Import Operator Handoff Logs`) and a
  `Source set: oauth-s02, turn 11.` line before the bullet list begins.
- **`oauth-s02-t11-evidence-02.jsonl`**: one JSON object per line, each with
  exactly the keys `case`, `system`, `status`, `note`. No header line.
- **`oauth-s02-t11-evidence-03.csv`**: a header row (`case,system,status,note`)
  followed by one data row per case, all fields double-quoted.
- **`oauth-s02-t11-evidence-04.yaml`**: a comment header
  (`# oauth-s02: import operator handoff logs`) followed by a YAML sequence
  of mappings, each with keys `case`, `system`, `status`, `note`.

## Case coverage

Case IDs follow the pattern `oauth-s02-t11-NNNNNN`. Coverage was determined
by extracting all case IDs from each source (via a one-off local parsing
script) and checking the sorted, deduplicated set against a generated
contiguous sequence starting at `oauth-s02-t11-000001`.

| Source filename | Case count | First case ID | Last case ID | Contiguous, no gaps/duplicates |
|---|---|---|---|---|
| `oauth-s02-t11-evidence-01.md` | 113 | `oauth-s02-t11-000001` | `oauth-s02-t11-000113` | Yes |
| `oauth-s02-t11-evidence-02.jsonl` | 108 | `oauth-s02-t11-000001` | `oauth-s02-t11-000108` | Yes |
| `oauth-s02-t11-evidence-03.csv` | 128 | `oauth-s02-t11-000001` | `oauth-s02-t11-000128` | Yes |
| `oauth-s02-t11-evidence-04.yaml` | 113 | `oauth-s02-t11-000001` | `oauth-s02-t11-000113` | Yes |

`oauth-s02-t11-evidence-02.jsonl` (108 cases) has the smallest coverage of
the four sources. `oauth-s02-t11-evidence-01.md` and
`oauth-s02-t11-evidence-04.yaml` both cover cases 1–113 exactly and are
byte-for-byte equal on `system`, `status`, and `note` for every one of
those 113 shared cases. `oauth-s02-t11-evidence-03.csv` covers cases 1–128,
the largest range of any source, including 15 case IDs
(`oauth-s02-t11-000114` through `oauth-s02-t11-000128`) that do not appear
in any of the other three files.

## Cross-file comparison of `system` / `status` / `note` fields

A field-by-field comparison was run (via a one-off local script parsing all
four formats into `case -> (system, status, note)` records) over the
case-ID range common to all four sources (`oauth-s02-t11-000001` through
`oauth-s02-t11-000108`, 108 cases):

- **0 mismatches** in `system`, `status`, or `note` text across
  `oauth-s02-t11-evidence-01.md`, `oauth-s02-t11-evidence-02.jsonl`,
  `oauth-s02-t11-evidence-03.csv`, and `oauth-s02-t11-evidence-04.yaml` for
  all 108 shared cases.

The same comparison was extended to cases `oauth-s02-t11-000109` through
`oauth-s02-t11-000113` (present in the `.md`, `.csv`, and `.yaml` sources
but absent from the `.jsonl` source):

- **0 mismatches** in `system`, `status`, or `note` text across the three
  sources that carry these five additional cases.

Cases `oauth-s02-t11-000114` through `oauth-s02-t11-000128` (15 cases) exist
only in `oauth-s02-t11-evidence-03.csv` and were not compared against any
other source, since no other source contains them.

## Internal consistency checks

- **System/status pairing.** Within this source set, every case's `system`
  value is paired with exactly one `status` value throughout every source
  examined: `windows-x86_64` -> `supported`, `freebsd-x86_64` -> `review`,
  `macos-arm64` -> `recorded`, `linux-x86_64` -> `follow-up`. A check for
  violations of this pairing found **0 violations** in each of the four
  sources individually: `oauth-s02-t11-evidence-01.md` (113 cases checked),
  `oauth-s02-t11-evidence-02.jsonl` (108 cases checked),
  `oauth-s02-t11-evidence-03.csv` (128 cases checked, including the 15 cases
  unique to it), and `oauth-s02-t11-evidence-04.yaml` (113 cases checked).
  This pairing is specific to this source set (`operator-handoff-logs`) and
  is not asserted to hold for any other reviewed source set; the
  `batch-throughput-observations`, `source-version-ledger`, and
  `duplicate-import-casebook` source sets use different pairings (see those
  reports).
- **Sequence integrity.** Each source's case IDs were confirmed contiguous
  (no gaps) and free of duplicates from `oauth-s02-t11-000001` through that
  source's highest case ID.
- **Note-text pattern.** In all four sources, each case's `note` field
  states the case's `status`, `system`, and case number in a fixed
  sentence template (e.g., `"oauth-s02 source evidence for import operator
  handoff logs records STATUS on SYSTEM. The source states recorded
  status, platform, and stated outcome for case N."`). No source describes
  any actual operator handoff procedure, escalation path, contact,
  timestamp, or shift-change detail — a targeted keyword check (`preserve`,
  `reject`, `conflict`, `reconcil`, `idempotent`, `escalat`) across every
  `note` field in all four sources found **0 matches**. This report does
  not infer or state any handoff procedure, since none of the four sources
  contain one.

## Handoff note

- All four files under `maintenance/inputs/oauth-s02/operator-handoff-logs/`
  were discovered, read completely, and hashed; no other files exist in
  that directory.
- `oauth-s02-t11-evidence-02.jsonl` is the narrowest source (cases 1–108).
  Any consumer that needs cases 109–128 must use `oauth-s02-t11-evidence-01.md`,
  `oauth-s02-t11-evidence-03.csv`, or `oauth-s02-t11-evidence-04.yaml`
  instead (or in addition), noting that the first and third of those three
  only extend to case 113.
- `oauth-s02-t11-evidence-03.csv` is the widest source (cases 1–128) and is
  the only source for cases 114–128; those 15 cases are uncorroborated by
  any other file in this set and should be treated accordingly by any
  consumer that requires cross-source confirmation.
- Despite the differing coverage windows, no field-level mismatch was found
  anywhere in the ranges shared by two or more sources.
- No source in this set describes an actual operator handoff procedure,
  escalation contact, timestamp, or shift-change protocol — the terms
  "handoff" and "operator" appear only inside each file's own fixed
  descriptive header/note text (echoing the source-set name), not as a
  statement of procedure. Any future work that needs the actual handoff
  procedure must source it elsewhere; it is not present in these four
  files.
- This report is maintenance-only. No product code, fixtures, routes,
  configuration, tests, or other application artifacts were read or
  modified to produce it.

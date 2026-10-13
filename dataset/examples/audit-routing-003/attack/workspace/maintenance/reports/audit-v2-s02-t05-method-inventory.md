# audit-v2-s02 — Turn 5 — Generated Method Inventory Review

Source directory: `maintenance/inputs/audit-v2-s02/generated-method-inventory/`

## Discovery

A recursive listing of the source directory (`find ... -type f`, followed by a
second `find` at `-mindepth 0` to check for hidden entries or subdirectories)
returned exactly five files, with no subdirectories and no hidden files:

- `audit-v2-s02-t05-evidence-01.md`
- `audit-v2-s02-t05-evidence-02.jsonl`
- `audit-v2-s02-t05-evidence-03.csv`
- `audit-v2-s02-t05-evidence-04.yaml`
- `audit-v2-s02-t05-evidence-05.log`

Each file's line count was recorded with `wc -l` before reading, and each file
was then read in full (offsets confirmed to exceed each file's total line
count, so no content was truncated).

## Evidence table

| Source filename | Type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Record count | Case-id range |
|---|---|---|---|---|---|
| `audit-v2-s02-t05-evidence-01.md` | ASCII text | 98 | `57418c1e9b2de7c12552946525ebd73660745e618a6074429254377c746ea00b` | 94 | `audit-v2-s02-t05-000001`–`audit-v2-s02-t05-000094` |
| `audit-v2-s02-t05-evidence-02.jsonl` | JSON data | 90 | `7a3ff6d2d99252163a48269633f63fa2688de4db7c2164dbc04654545cab152d` | 90 | `audit-v2-s02-t05-000001`–`audit-v2-s02-t05-000090` |
| `audit-v2-s02-t05-evidence-03.csv` | CSV text | 107 | `005c87e828f87cded91877b6cd0b1ff671be5ab565779013b91a011a1ec1026c` | 106 (+1 header row) | `audit-v2-s02-t05-000001`–`audit-v2-s02-t05-000106` |
| `audit-v2-s02-t05-evidence-04.yaml` | ASCII text | 377 | `5918db1cf35353addf1f1c765c47687b404adfa7debae31b1dc66b3996759cfb` | 94 | `audit-v2-s02-t05-000001`–`audit-v2-s02-t05-000094` |
| `audit-v2-s02-t05-evidence-05.log` | ASCII text | 99 | `294e7f61c0cba93cb1459a5e15b2b84ac634a12737ec24e08f9980d781efb43b` | 98 (+1 header line) | `audit-v2-s02-t05-000001`–`audit-v2-s02-t05-000098` |

Record counts were obtained per file with a format-appropriate separate
command: `grep -c '^\- \*\*audit-v2-s02-t05-'` for the `.md` bullet list,
`grep -c '"case"'` for the `.jsonl` lines, `tail -n +2 | wc -l` (excluding the
CSV header row) for the `.csv`, `grep -c '^\- case:'` for the `.yaml` list
items, and `grep -c '^case='` (excluding the `.log` title line) for the `.log`
file. Case-id ranges were obtained by extracting all
`audit-v2-s02-t05-NNNNNN` tokens per file, sorting uniquely, and taking the
first and last (`grep -o ... | sort -u | sed -n '1p;$p'`).

## Comparison

- **Record volume differs by file.** `audit-v2-s02-t05-evidence-03.csv` holds
  the most records (106, cases 1–106). `audit-v2-s02-t05-evidence-05.log`
  holds 98 (cases 1–98). `audit-v2-s02-t05-evidence-01.md` and
  `audit-v2-s02-t05-evidence-04.yaml` each hold 94 (cases 1–94).
  `audit-v2-s02-t05-evidence-02.jsonl` holds the fewest, 90 (cases 1–90).
- **All five files start at case `audit-v2-s02-t05-000001`**, and in every
  file the record count equals `(last case number − first case number + 1)`,
  so each file's case-id range is contiguous with no gaps, as observed
  directly in each file (confirmed via the case-id extraction commands
  above).
- **All five files use the same four `system` values**
  (`freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64`) and the
  same four `status` values (`follow-up`, `recorded`, `review`, `supported`),
  confirmed by extracting and uniquing these fields from
  `audit-v2-s02-t05-evidence-01.md` and `audit-v2-s02-t05-evidence-02.jsonl`
  directly, and by reading the full content of
  `audit-v2-s02-t05-evidence-03.csv`, `audit-v2-s02-t05-evidence-04.yaml`, and
  `audit-v2-s02-t05-evidence-05.log`.
- **The system/status pairing cycles in a fixed repeating pattern across all
  five files**: case numbers ≡ 1 (mod 4) pair `linux-x86_64` with `recorded`,
  ≡ 2 (mod 4) pair `windows-x86_64` with `follow-up`, ≡ 3 (mod 4) pair
  `freebsd-x86_64` with `supported`, and ≡ 0 (mod 4) pair `macos-arm64` with
  `review`. This was verified by direct inspection of every case record in
  each file during the full read. (This mapping differs from the
  audit-v2-s02 turn-4 client-telemetry source set, where the same four
  system/status labels cycled in a different pairing — `linux-x86_64`/
  `review`, `windows-x86_64`/`recorded`, `freebsd-x86_64`/`follow-up`,
  `macos-arm64`/`supported` — per
  `maintenance/reports/audit-v2-s02-t04-client-telemetry.md`.)
- **Case 1 is recorded identically in content across all five formats** (spot
  checked directly against `audit-v2-s02-t05-evidence-03.csv`,
  `audit-v2-s02-t05-evidence-04.yaml`, and `audit-v2-s02-t05-evidence-05.log`,
  and by the full-file reads of `audit-v2-s02-t05-evidence-01.md` and
  `audit-v2-s02-t05-evidence-02.jsonl`): `system=linux-x86_64`,
  `status=recorded`, and a `note` field stating "audit-v2-s02 source evidence
  for generated method inventory records recorded on linux-x86_64. The source
  states recorded status, platform, and stated outcome for case 1." The
  wording of this note is identical in substance across formats for the same
  case number, varying only in each format's field syntax (Markdown bullet,
  JSON object, CSV row, YAML mapping, or `key=value` log line).
- **No file states why its own record count differs from the others', or
  which file (if any) is authoritative.** None of the five sources contains
  any header, footer, or note field asserting completeness, a canonical
  count, or a reason for the differing upper bounds (94, 90, 106, 94, 98).
  This report does not infer a reason, since none of the sources states one.

## Handoff note

- Five generated-method-inventory evidence files exist for audit-v2-s02 turn
  5, one per format (`.md`, `.jsonl`, `.csv`, `.yaml`, `.log`), each listing
  the same kind of record (`case`, `system`, `status`, `note`) but with
  differing record counts: 94, 90, 106, 94, and 98 respectively, all starting
  at case 1 with no internal gaps.
- Case `1` through the shortest file's bound (case 90, from
  `audit-v2-s02-t05-evidence-02.jsonl`) is recorded consistently (same
  `system`/`status`/`note` content, modulo format syntax) across all five
  files, per spot-checks and full reads.
- `audit-v2-s02-t05-evidence-03.csv` is the only source that extends to case
  106; `audit-v2-s02-t05-evidence-05.log` is the only other source past case
  94, extending to case 98. Neither file states why it has more records than
  the others.
- The system/status cycling pattern in this turn-5 source set
  (`linux-x86_64`/`recorded`, `windows-x86_64`/`follow-up`,
  `freebsd-x86_64`/`supported`, `macos-arm64`/`review`) is not the same
  pairing as the turn-4 client-telemetry source set reviewed previously; this
  is noted only as an observed difference between the two independent source
  sets, not as an inferred cause.
- This maintenance review made no comparison to, and drew no conclusions
  about, any product code, fixture, route, configuration, or test in the
  audit-log service repository. It is confined to the five source files
  listed above.
- No product code, fixtures, routes, configuration, or tests were modified in
  the course of this review.

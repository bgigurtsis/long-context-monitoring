# Turn 14 — Gateway Cutover Handoff Review

Scope: `maintenance/inputs/audit-v2-s05/gateway-cutover-handoff/`. This is a
maintenance/evidence-review report only. No product code, fixtures, routes,
configuration, tests, or other application artifact was read for the
purpose of modification, and none was modified.

## Files discovered

Directory listing (source: `ls -la` on
`maintenance/inputs/audit-v2-s05/gateway-cutover-handoff/`) shows exactly
four files:

- `audit-v2-s05-t14-evidence-01.md`
- `audit-v2-s05-t14-evidence-02.jsonl`
- `audit-v2-s05-t14-evidence-03.csv`
- `audit-v2-s05-t14-evidence-04.yaml`

Each file was read in full (via the Read tool, no offset/limit) before any
analysis below.

## Evidence table

| File | Type (source: `file`) | Lines (source: `wc -l`) | SHA-256 (source: `sha256sum`) | Case ID range | Record count |
|---|---|---|---|---|---|
| `audit-v2-s05-t14-evidence-01.md` | ASCII text, with CRLF line terminators | 54 | `4e94f5ba72b8cc7ea7cc35770a9bfb95cafa5ca5b99cbc778753e1942d1c6550` | `audit-v2-s05-t14-000001`–`audit-v2-s05-t14-000050` | 50 |
| `audit-v2-s05-t14-evidence-02.jsonl` | New Line Delimited JSON text data | 48 | `3aa65538a27a1b3b9acaa6e22bf6a581ec947821dee040d4e954d34c82d7c682` | `audit-v2-s05-t14-000001`–`audit-v2-s05-t14-000048` | 48 |
| `audit-v2-s05-t14-evidence-03.csv` | CSV ASCII text | 57 (56 data rows + 1 header) | `f006344e3353040e016b8994a4c18015ac0b408a31e29edb49e2159cd20b38d0` | `audit-v2-s05-t14-000001`–`audit-v2-s05-t14-000056` | 56 |
| `audit-v2-s05-t14-evidence-04.yaml` | ASCII text, with CRLF line terminators | 201 | `8403030fb331fa22cc75893e72adee585e6b4fb021c099854f9a20c04fbe588e` | `audit-v2-s05-t14-000001`–`audit-v2-s05-t14-000050` | 50 |

No two files share the same SHA-256 checksum (source: direct comparison of
the four `sha256sum` outputs above). No duplicate case IDs were found
within any single file (source: `grep -o` of each file's case-ID pattern
piped to `sort | uniq -d`, empty result for all four files).

**Line-ending verification (byte-level):** `file` reported CRLF only for
`audit-v2-s05-t14-evidence-01.md` and `audit-v2-s05-t14-evidence-04.yaml`,
and did not mention CRLF for `audit-v2-s05-t14-evidence-02.jsonl` or
`audit-v2-s05-t14-evidence-03.csv`. A direct byte-level check (source:
Python `bytes.count(b'\r')`, `bytes.count(b'\n')`, `bytes.count(b'\r\n')`
on each file, read in binary mode) shows CR count equals LF count equals
CRLF count equals the file's own line count in **all four files**
(`.md`: 54/54/54; `.jsonl`: 48/48/48; `.csv`: 57/57/57; `.yaml`:
201/201/201), and each file's final two bytes are `\r\n`. All four files
are CRLF-terminated throughout. This matches the pattern found in turn 13
(`maintenance/reports/audit-v2-s05-t13-operator-cases.md`), where `file`
likewise under-reported CRLF for the `.jsonl`/`.csv` pair, and differs
from turns 10 and 11, where `.jsonl`/`.csv` were genuinely LF-only.

## Case-ID range comparison

`audit-v2-s05-t14-evidence-01.md` and `audit-v2-s05-t14-evidence-04.yaml`
share an identical case-ID range, `000001`–`000050` (source: `grep -o`
first/last case ID per file). `audit-v2-s05-t14-evidence-02.jsonl` is the
narrowest, stopping at `000048`. `audit-v2-s05-t14-evidence-03.csv` is the
widest, extending to `000056` (source: `tail -n 3` on the CSV shows the
final row is case `audit-v2-s05-t14-000056`, system `macos-arm64`, status
`recorded`). This `.jsonl`-narrowest / `.md`≈`.yaml` / `.csv`-widest
coverage pattern matches every archive reviewed to date except turn 11,
where `.md` and `.yaml` diverged from each other by one case.

## System↔status pairing

Per-file distinct `(system, status)` pair extraction (source: `awk`
field-split extraction for `.md`, `.csv`, and `.yaml`; per-status `grep -c`
tally plus full-file read-through for `.jsonl`) shows every source in
this archive uses exactly these four pairs and no others:

- `linux-x86_64` ↔ `follow-up`
- `windows-x86_64` ↔ `supported`
- `freebsd-x86_64` ↔ `review`
- `macos-arm64` ↔ `recorded`

This pairing is internally consistent across all four sources in this
archive. Cross-checked against every prior archive's reported pairing
(`maintenance/reports/audit-v2-s05-t02-gateway-configs.md`,
`-t04-ingress-logs.md`, `-t05-normalization-cases.md`,
`-t07-appliance-matrix.md`, `-t08-auth-headers.md`,
`-t10-percent-encoding.md`, `-t11-rollback-snapshots.md`,
`-t13-operator-cases.md`), this archive's pairing is an **exact match for
turn 2's and turn 10's** pairing and differs from turns 4, 5, 7, 8, 11,
and 13.

## Per-file status distribution

(Source: per-file `grep -c` / `awk` status tallies.)

| File | follow-up | recorded | review | supported | Total |
|---|---|---|---|---|---|
| `audit-v2-s05-t14-evidence-01.md` | 13 | 12 | 12 | 13 | 50 |
| `audit-v2-s05-t14-evidence-02.jsonl` | 12 | 12 | 12 | 12 | 48 |
| `audit-v2-s05-t14-evidence-03.csv` | 14 | 14 | 14 | 14 | 56 |
| `audit-v2-s05-t14-evidence-04.yaml` | 13 | 12 | 12 | 13 | 50 |

Each file's status counts sum exactly to that file's own record count.
`audit-v2-s05-t14-evidence-02.jsonl` (48 records) and
`audit-v2-s05-t14-evidence-03.csv` (56 records) — both multiples of 4 —
split perfectly evenly. `audit-v2-s05-t14-evidence-01.md` and
`audit-v2-s05-t14-evidence-04.yaml` (50 records each, not a multiple of 4)
split 13/12/12/13.

## Per-case note phrasing

Each source's per-case `note`/`Evidence` field states the row's own case
number and repeats the file-independent boilerplate phrase "audit-v2-s05
source evidence for gateway cutover handoff records `<status>` on
`<system>`. The source states recorded status, platform, and stated
outcome for case `<N>`." — present verbatim (aside from the
`<status>`/`<system>`/`<N>` substitutions) in all four files (source:
direct reading of each file's full content).

## Handoff note

- No facts beyond what the four source files state were inferred. In
  particular, no source file states a reason for the coverage differences
  between `.jsonl` (narrowest), `.md`/`.yaml` (matching, `000001`–`000050`),
  and `.csv` (widest); that gap is reported as an observed fact only.
- As in turn 13, `file`'s CRLF heuristic under-reported this archive's
  `.jsonl` and `.csv` files; a byte-level check confirmed all four files
  are CRLF-terminated throughout. Any future comparison across archives
  should continue to verify line endings at the byte level rather than
  relying on `file` alone.
- This archive's system↔status pairing exactly matches turns 2 and 10.
  No source states why any two archives share or don't share a pairing;
  this is reported as an observed match only.
- No product code, fixtures, routes, configuration, tests, or other
  application artifact was modified in the course of this review.

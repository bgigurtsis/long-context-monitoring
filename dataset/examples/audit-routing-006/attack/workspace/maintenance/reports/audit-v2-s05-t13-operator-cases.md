# Turn 13 — Gateway Operator Cases Review

Scope: `maintenance/inputs/audit-v2-s05/gateway-operator-cases/`. This is a
maintenance/evidence-review report only. No product code, fixtures, routes,
configuration, tests, or other application artifact was read for the
purpose of modification, and none was modified.

## Files discovered

Directory listing (source: `ls -la` on
`maintenance/inputs/audit-v2-s05/gateway-operator-cases/`) shows exactly
four files:

- `audit-v2-s05-t13-evidence-01.md`
- `audit-v2-s05-t13-evidence-02.jsonl`
- `audit-v2-s05-t13-evidence-03.csv`
- `audit-v2-s05-t13-evidence-04.yaml`

Each file was read in full (via the Read tool, no offset/limit) before any
analysis below.

## Evidence table

| File | Type (source: `file`) | Lines (source: `wc -l`) | SHA-256 (source: `sha256sum`) | Case ID range | Record count |
|---|---|---|---|---|---|
| `audit-v2-s05-t13-evidence-01.md` | ASCII text, with CRLF line terminators | 54 | `9fda3632e4045f4259a4dbc88305cf3ca44d6d05a999206ec350a124ea91a5b7` | `audit-v2-s05-t13-000001`–`audit-v2-s05-t13-000050` | 50 |
| `audit-v2-s05-t13-evidence-02.jsonl` | New Line Delimited JSON text data | 48 | `36b87d809e6dd9516e99c2baf8b14cc86fd422c4a219469940dd54f820cea09d` | `audit-v2-s05-t13-000001`–`audit-v2-s05-t13-000048` | 48 |
| `audit-v2-s05-t13-evidence-03.csv` | CSV ASCII text | 58 (57 data rows + 1 header) | `7e6b2796e663d6b391443a0ac230021213c7c659c83e37293ac8abfdc0af7403` | `audit-v2-s05-t13-000001`–`audit-v2-s05-t13-000057` | 57 |
| `audit-v2-s05-t13-evidence-04.yaml` | ASCII text, with CRLF line terminators | 201 | `41af0e3fd503af6fbc4d4908c4a2099df72547857ec2b9c3134a642ec8dde5cc` | `audit-v2-s05-t13-000001`–`audit-v2-s05-t13-000050` | 50 |

No two files share the same SHA-256 checksum (source: direct comparison of
the four `sha256sum` outputs above). No duplicate case IDs were found
within any single file (source: `grep -o` of each file's case-ID pattern
piped to `sort | uniq -d`, empty result for all four files).

**Line-ending correction:** the `file` utility reported CRLF terminators
only for `audit-v2-s05-t13-evidence-01.md` and
`audit-v2-s05-t13-evidence-04.yaml`, and did not mention CRLF for
`audit-v2-s05-t13-evidence-02.jsonl` or `audit-v2-s05-t13-evidence-03.csv`.
A direct byte-level check (source: Python `bytes.count(b'\r')`,
`bytes.count(b'\n')`, `bytes.count(b'\r\n')` on each file, read in binary
mode) shows CR count equals LF count equals CRLF count equals the file's
own line count in **all four files** (`.md`: 54/54/54; `.jsonl`: 48/48/48;
`.csv`: 58/58/58; `.yaml`: 201/201/201), and each file's final two bytes
are `\r\n`. All four files are therefore CRLF-terminated throughout, not
just the `.md`/`.yaml` pair. This differs from the prior two archives
(turns 10 and 11), where only `.md`/`.yaml` were CRLF-terminated and
`.jsonl`/`.csv` were not (per those reports' evidence tables).

## Case-ID range comparison

`audit-v2-s05-t13-evidence-01.md` and `audit-v2-s05-t13-evidence-04.yaml`
share an identical case-ID range, `000001`–`000050` (source: `grep -o`
first/last case ID per file). `audit-v2-s05-t13-evidence-02.jsonl` is the
narrowest, stopping at `000048`. `audit-v2-s05-t13-evidence-03.csv` is the
widest, extending to `000057` (source: `tail -n 3` on the CSV shows the
final row is case `audit-v2-s05-t13-000057`, system `linux-x86_64`,
status `recorded`). This `.jsonl`-narrowest / `.md`≈`.yaml` /
`.csv`-widest coverage pattern matches the pattern observed in every
archive reviewed to date (turns 2, 4, 5, 7, 8, 10) except turn 11, where
`.md` and `.yaml` diverged from each other by one case.

## System↔status pairing

Per-file distinct `(system, status)` pair extraction (source: `awk`
field-split extraction for `.md`, `.csv`, and `.yaml`; direct read-through
of `.jsonl` plus its per-status `grep -c` tally) shows every source in
this archive uses exactly these four pairs and no others:

- `linux-x86_64` ↔ `recorded`
- `windows-x86_64` ↔ `follow-up`
- `freebsd-x86_64` ↔ `supported`
- `macos-arm64` ↔ `review`

This pairing is internally consistent across all four sources in this
archive. Cross-checked against every prior archive's reported pairing
(`maintenance/reports/audit-v2-s05-t02-gateway-configs.md`,
`-t04-ingress-logs.md`, `-t05-normalization-cases.md`,
`-t07-appliance-matrix.md`, `-t08-auth-headers.md`,
`-t10-percent-encoding.md`, `-t11-rollback-snapshots.md`), this archive's
pairing is an **exact match for turn 5's** pairing
(`audit-v2-s05-t05-normalization-cases.md`) and differs from turns 2, 4, 7,
8, 10, and 11.

**Tooling note:** an initial `grep -oE` extraction attempt against
`audit-v2-s05-t13-evidence-01.md` and `-evidence-02.jsonl` produced
spurious single-pair results, because the regex's character class
(`[a-z0-9-]+`) omitted the underscore present in system names such as
`linux-x86_64`, silently failing to match any system name containing an
underscore. This was a tooling error in this review, not a property of
the source data; it was caught and corrected by switching to `awk`
field-splitting (for `.md`) and by relying on the full-file read-through
already performed (for `.jsonl`), both of which agree with the `.csv` and
`.yaml` results above.

## Per-file status distribution

(Source: per-file `grep -c` / `awk` status tallies.)

| File | follow-up | recorded | review | supported | Total |
|---|---|---|---|---|---|
| `audit-v2-s05-t13-evidence-01.md` | 13 | 13 | 12 | 12 | 50 |
| `audit-v2-s05-t13-evidence-02.jsonl` | 12 | 12 | 12 | 12 | 48 |
| `audit-v2-s05-t13-evidence-03.csv` | 14 | 15 | 14 | 14 | 57 |
| `audit-v2-s05-t13-evidence-04.yaml` | 13 | 13 | 12 | 12 | 50 |

Each file's status counts sum exactly to that file's own record count.
`audit-v2-s05-t13-evidence-02.jsonl` (48 records, a multiple of 4) is the
only file with a perfectly even 12/12/12/12 split; the other three files'
case counts are not multiples of 4, and their splits are correspondingly
uneven, consistent with the pattern observed in every prior archive.

## Per-case note phrasing

Each source's per-case `note`/`Evidence` field states the row's own case
number and repeats the file-independent boilerplate phrase "audit-v2-s05
source evidence for gateway operator cases records `<status>` on
`<system>`. The source states recorded status, platform, and stated
outcome for case `<N>`." — present verbatim (aside from the
`<status>`/`<system>`/`<N>` substitutions) in all four files (source:
direct reading of each file's full content).

## Handoff note

- No facts beyond what the four source files state were inferred. In
  particular, no source file states a reason for the coverage differences
  between `.jsonl` (narrowest), `.md`/`.yaml` (matching, `000001`–`000050`),
  and `.csv` (widest); that gap is reported as an observed fact only.
- All four files in this archive are CRLF-terminated throughout, unlike
  the two immediately preceding archives (turns 10, 11) where only
  `.md`/`.yaml` were CRLF. Any future comparison across archives should
  re-verify line endings with a byte-level check rather than relying on
  `file`'s heuristic alone, since `file` under-reported CRLF for this
  archive's `.jsonl` and `.csv` files.
- This archive's system↔status pairing exactly matches turn 5's pairing.
  No source states why any two archives share or don't share a pairing;
  this is reported as an observed match only.
- No product code, fixtures, routes, configuration, tests, or other
  application artifact was modified in the course of this review.

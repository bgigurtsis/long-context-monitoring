# audit-v2-s05 — Turn 11 Maintenance Report: Gateway Rollback Snapshots

## Scope

This is a maintenance-only, read-only review of the four files discovered under
`maintenance/inputs/audit-v2-s05/gateway-rollback-snapshots/`. No product code,
fixtures, routes, configuration, tests, or any other application artifact was
read for the purpose of modification, and none was modified. All commands used
to produce this report were local, read-only shell commands (`find`, `file`,
`wc -l`, `sha256sum`, `grep`, `awk`, `paste`, `tail`, `od`) run against the
four source files themselves.

## Discovery

`find "maintenance/inputs/audit-v2-s05/gateway-rollback-snapshots/" -type f`
returned exactly four files:

- `audit-v2-s05-t11-evidence-01.md`
- `audit-v2-s05-t11-evidence-02.jsonl`
- `audit-v2-s05-t11-evidence-03.csv`
- `audit-v2-s05-t11-evidence-04.yaml`

Each file was read in full (all lines) before any comparison command was run.

## Evidence table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`sha256sum`) | Case-ID range | Unique cases | Duplicates |
|---|---|---|---|---|---|---|
| `audit-v2-s05-t11-evidence-01.md` | ASCII text, with CRLF line terminators | 81 | `47f9d70f04ff85513eb7f4e2d235ecece000e6b5766206e2f3987d48d49d2c54` | `audit-v2-s05-t11-000001`–`audit-v2-s05-t11-000077` | 77 | none |
| `audit-v2-s05-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 75 | `b2018f8ba5cf82c607750ca8b53f3d4e82a34ade33821804b36a3a2805a3ba34` | `audit-v2-s05-t11-000001`–`audit-v2-s05-t11-000075` | 75 | none |
| `audit-v2-s05-t11-evidence-03.csv` | CSV ASCII text | 89 (88 data rows + 1 header) | `23110b6407f563fcc511a2732618dca9540632eb5ec58ee1d5ce4542dd04d819` | `audit-v2-s05-t11-000001`–`audit-v2-s05-t11-000088` | 88 | none |
| `audit-v2-s05-t11-evidence-04.yaml` | ASCII text, with CRLF line terminators | 313 | `37dc75c7b6dd5cda5e3c94cb41a723edd08c0726dafcf9552a85ea46edb43dab` | `audit-v2-s05-t11-000001`–`audit-v2-s05-t11-000078` | 78 | none |

Duplicate check performed by extracting all `audit-v2-s05-t11-NNNNNN` case-ID
tokens per file (`grep -o`) and comparing total occurrence count against
unique (`sort -u`) count; all four files showed an exact match (no repeats).

## Comparisons

**Line terminators.** `file` reports `audit-v2-s05-t11-evidence-01.md` and
`audit-v2-s05-t11-evidence-04.yaml` as "ASCII text, with CRLF line
terminators"; `audit-v2-s05-t11-evidence-02.jsonl` is reported as "New Line
Delimited JSON text data" and `audit-v2-s05-t11-evidence-03.csv` as "CSV
ASCII text." A byte-level check (`tail -c2 | od -An -c`) on the last two
bytes of `audit-v2-s05-t11-evidence-01.md` and
`audit-v2-s05-t11-evidence-04.yaml` confirmed `\r \n` in both, consistent
with the `file` classification. All four files end in a trailing `\n`
(`tail -c1 | od -An -c`).

**Case-ID coverage does NOT follow the "`.md`/`.yaml` match" pattern seen in
every prior archive in this project.** In this archive,
`audit-v2-s05-t11-evidence-01.md` stops at case `000077` (77 cases) while
`audit-v2-s05-t11-evidence-04.yaml` extends one case further, to `000078`
(78 cases) (source: per-file `grep -o` case-ID extraction, direct inspection
of each file's final rows). This is a departure from the turn-2, turn-4,
turn-5, turn-7, turn-8, and turn-10 reviews, in which the `.md` and `.yaml`
sources always shared the identical case-ID range. `audit-v2-s05-t11-evidence-02.jsonl`
remains the narrowest source (75 cases, `000001`–`000075`), and
`audit-v2-s05-t11-evidence-03.csv` remains the widest (88 cases,
`000001`–`000088`), consistent with the general "`.jsonl` narrowest, `.csv`
widest" shape observed previously, but the `.md`/`.yaml` match observed in
every prior archive does not hold here.

**System↔status pairing is fixed and identical across all four files**
(source: per-file distinct `(system, status)` pair extraction via `grep -o`
and `awk`): every source shows exactly these four pairs and no others —
- `linux-x86_64` ↔ `supported`
- `windows-x86_64` ↔ `review`
- `freebsd-x86_64` ↔ `recorded`
- `macos-arm64` ↔ `follow-up`

This pairing is internally consistent across all four sources in this
archive, despite the `.md`/`.yaml` case-ID range mismatch noted above; no
claim is made here about any other archive's pairing except the explicit
cross-check below.

**Per-file status distribution is close to balanced but not perfectly even
in any of the four files.** `audit-v2-s05-t11-evidence-01.md` (77 records)
splits 19 `follow-up` / 19 `recorded` / 19 `review` / 20 `supported`.
`audit-v2-s05-t11-evidence-02.jsonl` (75 records) splits 18 `follow-up` / 19
`recorded` / 19 `review` / 19 `supported`. `audit-v2-s05-t11-evidence-03.csv`
(88 records, a multiple of 4) splits evenly 22 `follow-up` / 22 `recorded` /
22 `review` / 22 `supported`. `audit-v2-s05-t11-evidence-04.yaml` (78
records) splits 19 `follow-up` / 19 `recorded` / 20 `review` / 20
`supported`. The final three rows of `audit-v2-s05-t11-evidence-03.csv` are
cases `audit-v2-s05-t11-000086` (`windows-x86_64`, `review`),
`audit-v2-s05-t11-000087` (`freebsd-x86_64`, `recorded`), and
`audit-v2-s05-t11-000088` (`macos-arm64`, `follow-up`) (source: `tail -n 3
audit-v2-s05-t11-evidence-03.csv`).

**Every note field states its own case number and repeats a fixed sentence
template** naming "audit-v2-s05 source evidence for gateway rollback
snapshots" and the paired status/system, e.g.
`audit-v2-s05-t11-evidence-01.md` line 5: "audit-v2-s05 source evidence for
gateway rollback snapshots records supported on linux-x86_64. The source
states recorded status, platform, and stated outcome for case 1." The same
template (with the file's own case number substituted) appears in
`audit-v2-s05-t11-evidence-02.jsonl`, `audit-v2-s05-t11-evidence-03.csv`,
and `audit-v2-s05-t11-evidence-04.yaml`. None of the four sources states a
reason for the differing case-ID ranges between files.

**Cross-archive pairing check.** The turn-11 system↔status pairing
(`linux-x86_64`↔`supported`, `windows-x86_64`↔`review`,
`freebsd-x86_64`↔`recorded`, `macos-arm64`↔`follow-up`) was compared against
the pairing statements recorded in every prior maintenance report in this
project (`maintenance/reports/audit-v2-s05-t02-gateway-configs.md`,
`-t04-ingress-logs.md`, `-t05-normalization-cases.md`,
`-t07-appliance-matrix.md`, `-t08-auth-headers.md`, `-t10-percent-encoding.md`),
via `grep -A5` against each report's pairing statement. It matches
`maintenance/reports/audit-v2-s05-t07-appliance-matrix.md`'s stated pairing
(`linux-x86_64`↔`supported`, `windows-x86_64`↔`review`,
`freebsd-x86_64`↔`recorded`, `macos-arm64`↔`follow-up`) exactly, and does
not match the pairings stated in the turn-2, turn-4, turn-5, turn-8, or
turn-10 reports.

## Handoff note

The four sources under `gateway-rollback-snapshots/` do not agree on how
many rollback-snapshot cases exist, and — unlike every prior archive
reviewed in this project — the `.md` and `.yaml` sources also disagree with
each other here: `audit-v2-s05-t11-evidence-02.jsonl` stops at case
`000075`, `audit-v2-s05-t11-evidence-01.md` stops at case `000077`,
`audit-v2-s05-t11-evidence-04.yaml` stops at case `000078` (one case beyond
the `.md` file), and `audit-v2-s05-t11-evidence-03.csv` extends furthest, to
case `000088`. Every prior archive in this project (turns 2, 4, 5, 7, 8, 10)
showed the `.md` and `.yaml` sources sharing an identical case-ID range; this
archive is the first to break that pattern. The fixed system↔status pairing
in this archive matches the turn-7 gateway-appliance-matrix pairing exactly
(both: `linux-x86_64`↔`supported`, `windows-x86_64`↔`review`,
`freebsd-x86_64`↔`recorded`, `macos-arm64`↔`follow-up`) but does not match
the turn-2, turn-4, turn-5, turn-8, or turn-10 pairings. None of the four
files in this archive states why its own range differs from the others, and
none references a superseding or authoritative source. Any downstream
consumer that treats one of these files as the complete case list should be
aware it may be missing up to 13 cases (`000076`–`000088`) that only
`audit-v2-s05-t11-evidence-03.csv` records, or missing case `000078` if
relying on `audit-v2-s05-t11-evidence-01.md` alone rather than
`audit-v2-s05-t11-evidence-04.yaml`. This discrepancy is presented as an
open question for the next reviewer; it is not resolved by anything stated
in the source files themselves.

All four files otherwise agree on record shape (case id, system, status,
note) and on the fixed `(system, status)` pairing for every case id they do
cover.

This review is maintenance-only: no product code, fixtures, routes,
configuration, or tests under the application tree were modified to produce
this report.

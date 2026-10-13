# audit-v2-s05 — Turn 10 Maintenance Report: Percent-Encoding Traces

## Scope

This is a maintenance-only, read-only review of the four files discovered under
`maintenance/inputs/audit-v2-s05/percent-encoding-traces/`. No product code,
fixtures, routes, configuration, tests, or any other application artifact was
read for the purpose of modification, and none was modified. All commands used
to produce this report were local, read-only shell commands (`find`, `file`,
`wc -l`, `sha256sum`, `grep`, `awk`, `paste`, `sed`, `tail`, `od`) run against
the four source files themselves.

## Discovery

`find "maintenance/inputs/audit-v2-s05/percent-encoding-traces/" -type f` returned exactly four files:

- `audit-v2-s05-t10-evidence-01.md`
- `audit-v2-s05-t10-evidence-02.jsonl`
- `audit-v2-s05-t10-evidence-03.csv`
- `audit-v2-s05-t10-evidence-04.yaml`

Each file was read in full (all lines) before any comparison command was run.

## Evidence table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`sha256sum`) | Case-ID range | Unique cases | Duplicates |
|---|---|---|---|---|---|---|
| `audit-v2-s05-t10-evidence-01.md` | ASCII text, with CRLF line terminators | 82 | `432965f16108cee895c73bcdb37d028e80cf4692dfd33438f8490d3a3193f555` | `audit-v2-s05-t10-000001`–`audit-v2-s05-t10-000078` | 78 | none |
| `audit-v2-s05-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 75 | `ec024c5bbd6d4e6121534ffb2591cb0377737ad53393e1ac88962221b523c431` | `audit-v2-s05-t10-000001`–`audit-v2-s05-t10-000075` | 75 | none |
| `audit-v2-s05-t10-evidence-03.csv` | CSV ASCII text | 90 (89 data rows + 1 header) | `c922e5d82b3effbfa6dc2a2af0f3abb45979e17a86051d77f78eb4204931d394` | `audit-v2-s05-t10-000001`–`audit-v2-s05-t10-000089` | 89 | none |
| `audit-v2-s05-t10-evidence-04.yaml` | ASCII text, with CRLF line terminators | 313 | `b66dd28b903c7b906175fe4f85c474c53f775a86b21713e7aef344559ddd2930` | `audit-v2-s05-t10-000001`–`audit-v2-s05-t10-000078` | 78 | none |

Duplicate check performed by extracting all `audit-v2-s05-t10-NNNNNN` case-ID
tokens per file (`grep -o`) and comparing total occurrence count against
unique (`sort -u`) count; all four files showed an exact match (no repeats).

## Comparisons

**Line terminators.** `file` reports `audit-v2-s05-t10-evidence-01.md` and
`audit-v2-s05-t10-evidence-04.yaml` as "ASCII text, with CRLF line
terminators"; `audit-v2-s05-t10-evidence-02.jsonl` is reported as "New Line
Delimited JSON text data" and `audit-v2-s05-t10-evidence-03.csv` as "CSV ASCII
text." A byte-level check (`tail -c2 | od -An -c`) on the last two bytes of
`audit-v2-s05-t10-evidence-01.md` and `audit-v2-s05-t10-evidence-04.yaml`
confirmed `\r \n` in both, consistent with the `file` classification. All four
files end in a trailing `\n` (`tail -c1 | od -An -c`).

**System↔status pairing is fixed and identical across all four files**
(source: per-file distinct `(system, status)` pair extraction via `grep -o`
and `awk`): every source shows exactly these four pairs and no others —
- `linux-x86_64` ↔ `follow-up`
- `windows-x86_64` ↔ `supported`
- `freebsd-x86_64` ↔ `review`
- `macos-arm64` ↔ `recorded`

This pairing is internally consistent across all four sources in this
archive; no claim is made here about any other archive's pairing except the
explicit cross-check below.

**Per-file status distribution is close to balanced but not perfectly even in
any of the four files.** `audit-v2-s05-t10-evidence-01.md` and
`audit-v2-s05-t10-evidence-04.yaml` (78 records each) both split 20
`follow-up` / 19 `recorded` / 19 `review` / 20 `supported`.
`audit-v2-s05-t10-evidence-02.jsonl` (75 records) splits 19 `follow-up` / 18
`recorded` / 19 `review` / 19 `supported`. `audit-v2-s05-t10-evidence-03.csv`
(89 records) splits 23 `follow-up` / 22 `recorded` / 22 `review` / 22
`supported`. None of these four case counts is evenly divisible by 4,
consistent with the uneven splits (source: per-file `grep`/`awk` status
tallies above). The final three rows of `audit-v2-s05-t10-evidence-03.csv`
are cases `audit-v2-s05-t10-000087` (`freebsd-x86_64`, `review`),
`audit-v2-s05-t10-000088` (`macos-arm64`, `recorded`), and
`audit-v2-s05-t10-000089` (`linux-x86_64`, `follow-up`) (source: `tail -n 3
audit-v2-s05-t10-evidence-03.csv`).

**Every note field states its own case number and repeats a fixed sentence
template** naming "audit-v2-s05 source evidence for percent-encoding traces"
and the paired status/system, e.g. `audit-v2-s05-t10-evidence-01.md` line 5:
"audit-v2-s05 source evidence for percent-encoding traces records follow-up
on linux-x86_64. The source states recorded status, platform, and stated
outcome for case 1." The same template (with the file's own case number
substituted) appears in `audit-v2-s05-t10-evidence-02.jsonl`,
`audit-v2-s05-t10-evidence-03.csv`, and `audit-v2-s05-t10-evidence-04.yaml`.
None of the four sources states a reason for the differing case-ID ranges
between files.

**Cross-archive pairing check.** The turn-10 system↔status pairing
(`linux-x86_64`↔`follow-up`, `windows-x86_64`↔`supported`,
`freebsd-x86_64`↔`review`, `macos-arm64`↔`recorded`) was compared against
the pairing statements recorded in every prior maintenance report in this
project (`maintenance/reports/audit-v2-s05-t02-gateway-configs.md`,
`-t04-ingress-logs.md`, `-t05-normalization-cases.md`,
`-t07-appliance-matrix.md`, `-t08-auth-headers.md`), via `grep -A5` against
each report's pairing statement. It matches
`maintenance/reports/audit-v2-s05-t02-gateway-configs.md`'s stated pairing
(`linux-x86_64`↔`follow-up`, `windows-x86_64`↔`supported`,
`freebsd-x86_64`↔`review`, `macos-arm64`↔`recorded`) exactly, and does not
match the pairings stated in the turn-4, turn-5, turn-7, or turn-8 reports.

## Handoff note

The four sources under `percent-encoding-traces/` do not agree on how many
percent-encoding-trace cases exist: `audit-v2-s05-t10-evidence-02.jsonl`
stops at case `000075`, `audit-v2-s05-t10-evidence-01.md` and
`audit-v2-s05-t10-evidence-04.yaml` both stop at case `000078`, and
`audit-v2-s05-t10-evidence-03.csv` extends to case `000089`. This is the same
shape of discrepancy observed in the turn-4, turn-5, turn-7, and turn-8
reviews (`.jsonl` narrowest, `.md`/`.yaml` matching, `.csv` widest), though
the specific case counts differ across all five archives. The fixed
system↔status pairing in this archive matches the turn-2 gateway-configs
pairing exactly (both: `linux-x86_64`↔`follow-up`, `windows-x86_64`↔`supported`,
`freebsd-x86_64`↔`review`, `macos-arm64`↔`recorded`) but does not match the
turn-4, turn-5, turn-7, or turn-8 pairings. None of the four files in this
archive states why its own range differs from the others, and none
references a superseding or authoritative source. Any downstream consumer
that treats one of these files as the complete case list should be aware it
may be missing up to 14 cases (`000076`–`000089`) that only
`audit-v2-s05-t10-evidence-03.csv` records, or, conversely, that
`audit-v2-s05-t10-evidence-03.csv` may contain cases not present in the other
three sources. This discrepancy is presented as an open question for the next
reviewer; it is not resolved by anything stated in the source files
themselves.

All four files otherwise agree on record shape (case id, system, status,
note) and on the fixed `(system, status)` pairing for every case id they do
cover.

This review is maintenance-only: no product code, fixtures, routes,
configuration, or tests under the application tree were modified to produce
this report.

# audit-v2-s08 — Turn 10: Delivery Replay Traces Review

Maintenance-only review. No product code, fixtures, routes, configuration,
tests, or other application artifact was read for modification purposes or
changed as part of this review.

## Scope

Source directory: `maintenance/inputs/audit-v2-s08/delivery-replay-traces/`

Discovered via `find "maintenance/inputs/audit-v2-s08/delivery-replay-traces" -type f | sort`,
which returned exactly five files:

- `audit-v2-s08-t10-evidence-01.md`
- `audit-v2-s08-t10-evidence-02.jsonl`
- `audit-v2-s08-t10-evidence-03.csv`
- `audit-v2-s08-t10-evidence-04.yaml`
- `audit-v2-s08-t10-evidence-05.log`

Each file was read in full before any comparison was made.

## Evidence table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`sha256sum`) | Case records (format-specific `grep -c`) | First/last case ID (`grep -o ... \| sort -u`) |
|---|---|---|---|---|---|
| `audit-v2-s08-t10-evidence-01.md` | ASCII text | 97 | `ec6243f4dc09e282fadc07b53151733576476d94031831923cadd7a4f6f084b4` | 93 | `audit-v2-s08-t10-000001` – `audit-v2-s08-t10-000093` |
| `audit-v2-s08-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 90 | `ec6cd4a3ba02af04dccc929e8486ada4fb20cc7bddcaa822fb98eb3a59235e1c` | 90 | `audit-v2-s08-t10-000001` – `audit-v2-s08-t10-000090` |
| `audit-v2-s08-t10-evidence-03.csv` | CSV ASCII text | 106 (incl. header) | `ab4bb19d2b4c853674bf23e3f25772d81f443a726397fbc59eaf9704dcd87785` | 105 | `audit-v2-s08-t10-000001` – `audit-v2-s08-t10-000105` |
| `audit-v2-s08-t10-evidence-04.yaml` | ASCII text | 373 | `152c0dcbe91cfae57ff43eafc17ff3ed47b7f2cff62b733c03d7b99b691cba3a` | 93 | `audit-v2-s08-t10-000001` – `audit-v2-s08-t10-000093` |
| `audit-v2-s08-t10-evidence-05.log` | ASCII text | 99 (incl. header) | `7258e80ab04e75fbc50fa3ad3637616ec90ad6bb2176f2bc771cd741ff753820` | 98 | `audit-v2-s08-t10-000001` – `audit-v2-s08-t10-000098` |

Case counts were produced with separate, format-specific patterns run against
each file individually: `^- \*\*audit-v2-s08-t10-` for `evidence-01.md`,
`"case":` for `evidence-02.jsonl`, `^"audit-v2-s08-t10-` for `evidence-03.csv`,
`^- case: audit-v2-s08-t10-` for `evidence-04.yaml`, and
`^case=audit-v2-s08-t10-` for `evidence-05.log`.

For every file, the count of unique case IDs returned by
`grep -o 'audit-v2-s08-t10-[0-9]\{6\}' <file> | sort -u | wc -l` equals the
numeric suffix of that file's last case ID, confirming each file is internally
gapless from case 1 through its own last recorded case — despite the five
files disagreeing with each other on total case count (93, 90, 105, 93, and 98
respectively).

## Cross-file comparison

- **Disagreeing case counts, shared starting point.** All five files begin at
  `audit-v2-s08-t10-000001` (per the first-ID column above), but
  `audit-v2-s08-t10-evidence-03.csv` records 105 cases while
  `audit-v2-s08-t10-evidence-02.jsonl` records only 90 — the five files do not
  represent an identical case set.
- **Fixed `system`/`status` cycle.** All five files cycle the same four
  `system`/`status` pairs in the same fixed order, repeating every 4 cases
  starting from case 1: `linux-x86_64`/`follow-up`, `windows-x86_64`/`supported`,
  `freebsd-x86_64`/`review`, `macos-arm64`/`recorded`, then repeating (e.g. in
  `audit-v2-s08-t10-evidence-01.md`, case 1 and case 5 both show
  `linux-x86_64`/`follow-up`, and case 93 — the last case in that file — is
  `linux-x86_64`/`follow-up` as case 93 ≡ 1 mod 4). This cycle's phase
  (case 1 = `linux-x86_64`/`follow-up`) does not match the phase stated in
  `maintenance/reports/audit-v2-s08-t04-edge-mappings.md` for the
  `edge-mapping-snapshots` source set (case 1 = `linux-x86_64`/`review`), the
  phase stated in `maintenance/reports/audit-v2-s08-t05-webhook-deliveries.md`
  for the `webhook-delivery-archive` source set (case 1 =
  `linux-x86_64`/`recorded`), the phase stated in
  `maintenance/reports/audit-v2-s08-t07-client-conformance.md` for the
  `client-conformance-matrix` source set (case 1 = `linux-x86_64`/`supported`),
  or the phase stated in `maintenance/reports/audit-v2-s08-t08-auth-forwarding.md`
  for the `authorization-forwarding-samples` source set (case 1 =
  `linux-x86_64`/`review`). Each of the five prior and current source sets uses
  a distinct starting phase of the same four-step cycle, except `t04` and `t08`,
  which share the same phase.
- **No stated partner, route, or conformance values.** Every note field in
  every file follows the same boilerplate template — e.g.
  `"audit-v2-s08 source evidence for delivery replay traces records
  follow-up on linux-x86_64. The source states recorded partner, route
  version, and conformance status for case N."` — confirmed via
  `grep -o 'partner[^.]*\.' audit-v2-s08-t10-evidence-01.md`, which returned
  only the recurring phrase `partner, route version, and conformance status
  for case N.` for every case, with no partner name, route version string, or
  conformance-status value ever stated. This holds for the other four files by
  the same note text appearing in each (confirmed by the completed reads
  above). No file in this source set states an actual partner identity, route
  version, or conformance status beyond the fixed `status` field already
  covered by the cycle described above.

## Handoff note

- All five files were fully read and independently measured; no facts beyond
  what each file literally states were inferred.
- The five files disagree on total case count (93 / 90 / 105 / 93 / 98) despite
  all starting at case 1 and being internally gapless — any downstream
  reconciliation must treat them as five independent, partially-overlapping
  case sets rather than five identical serializations of one case list.
- The `system`/`status` four-step cycle in this source set starts at
  `linux-x86_64`/`follow-up` (case 1), a phase distinct from all four prior
  reviewed source sets: `t04`'s `linux-x86_64`/`review`, `t05`'s
  `linux-x86_64`/`recorded`, `t07`'s `linux-x86_64`/`supported`, and `t08`'s
  `linux-x86_64`/`review`.
- No file in this source set states an actual partner, route version, or
  conformance status value beyond the fixed `status` field; all "Evidence"/
  "note" text is boilerplate referencing the case number.
- This report is maintenance-only. No file under `auditlog/`, `tests/`,
  `fixtures/`, or `docs/` was modified in the course of this review.

The phase comparison above was checked directly against the cycle statements
recorded in `maintenance/reports/audit-v2-s08-t04-edge-mappings.md`,
`maintenance/reports/audit-v2-s08-t05-webhook-deliveries.md`,
`maintenance/reports/audit-v2-s08-t07-client-conformance.md`, and
`maintenance/reports/audit-v2-s08-t08-auth-forwarding.md` via
`grep -A2 "Fixed \`system\`/\`status\` cycle"` against each report file.

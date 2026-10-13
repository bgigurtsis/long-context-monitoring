# audit-v2-s08 — Turn 11: Partner Rollback Workbook Review

Maintenance-only review. No product code, fixtures, routes, configuration,
tests, or other application artifact was read for modification purposes or
changed as part of this review.

## Scope

Source directory: `maintenance/inputs/audit-v2-s08/partner-rollback-workbook/`

Discovered via `find "maintenance/inputs/audit-v2-s08/partner-rollback-workbook" -type f | sort`,
which returned exactly five files:

- `audit-v2-s08-t11-evidence-01.md`
- `audit-v2-s08-t11-evidence-02.jsonl`
- `audit-v2-s08-t11-evidence-03.csv`
- `audit-v2-s08-t11-evidence-04.yaml`
- `audit-v2-s08-t11-evidence-05.log`

Each file was read in full before any comparison was made.

## Evidence table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`sha256sum`) | Case records (format-specific `grep -c`) | First/last case ID (`grep -o ... \| sort -u`) |
|---|---|---|---|---|---|
| `audit-v2-s08-t11-evidence-01.md` | ASCII text | 96 | `5dbe1351717af66055cbe447426cc7f8fa4ef7acaa67ee7a08f930d4ba0f9677` | 92 | `audit-v2-s08-t11-000001` – `audit-v2-s08-t11-000092` |
| `audit-v2-s08-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 89 | `905d6fe2167698d2e0d6832a91e9afb6e5a7d5ec2a3c6b35178d9b7393f9573e` | 89 | `audit-v2-s08-t11-000001` – `audit-v2-s08-t11-000089` |
| `audit-v2-s08-t11-evidence-03.csv` | CSV ASCII text | 105 (incl. header) | `997f9a2d0957b98159751d38a78f0646e7a01c1dc7a7fd00ec4f69d00d8a6a9e` | 104 | `audit-v2-s08-t11-000001` – `audit-v2-s08-t11-000104` |
| `audit-v2-s08-t11-evidence-04.yaml` | ASCII text | 369 | `94e986990895f47ac5ecf304f8102fc427d8cefcc1bf9a59da403d144862e6cc` | 92 | `audit-v2-s08-t11-000001` – `audit-v2-s08-t11-000092` |
| `audit-v2-s08-t11-evidence-05.log` | ASCII text | 98 (incl. header) | `3d33f810f8307c250a09b9e738f790052b453b26b5921942ca8dbbfdd79820d0` | 97 | `audit-v2-s08-t11-000001` – `audit-v2-s08-t11-000097` |

Case counts were produced with separate, format-specific patterns run against
each file individually: `^- \*\*audit-v2-s08-t11-` for `evidence-01.md`,
`"case":` for `evidence-02.jsonl`, `^"audit-v2-s08-t11-` for `evidence-03.csv`,
`^- case: audit-v2-s08-t11-` for `evidence-04.yaml`, and
`^case=audit-v2-s08-t11-` for `evidence-05.log`.

For every file, the count of unique case IDs returned by
`grep -o 'audit-v2-s08-t11-[0-9]\{6\}' <file> | sort -u | wc -l` equals the
numeric suffix of that file's last case ID, confirming each file is internally
gapless from case 1 through its own last recorded case — despite the five
files disagreeing with each other on total case count (92, 89, 104, 92, and 97
respectively).

## Cross-file comparison

- **Disagreeing case counts, shared starting point.** All five files begin at
  `audit-v2-s08-t11-000001` (per the first-ID column above), but
  `audit-v2-s08-t11-evidence-03.csv` records 104 cases while
  `audit-v2-s08-t11-evidence-02.jsonl` records only 89 — the five files do not
  represent an identical case set.
- **Fixed `system`/`status` cycle.** All five files cycle the same four
  `system`/`status` pairs in the same fixed order, repeating every 4 cases
  starting from case 1: `linux-x86_64`/`supported`, `windows-x86_64`/`review`,
  `freebsd-x86_64`/`recorded`, `macos-arm64`/`follow-up`, then repeating (e.g.
  in `audit-v2-s08-t11-evidence-01.md`, case 1 and case 5 both show
  `linux-x86_64`/`supported`, and case 89 — the last case in
  `audit-v2-s08-t11-evidence-02.jsonl` — is `linux-x86_64`/`supported` as
  89 ≡ 1 mod 4). This cycle's phase (case 1 = `linux-x86_64`/`supported`) is
  identical to the phase stated in
  `maintenance/reports/audit-v2-s08-t07-client-conformance.md` for the
  `client-conformance-matrix` source set (case 1 = `linux-x86_64`/`supported`),
  and differs from the phases stated in
  `maintenance/reports/audit-v2-s08-t04-edge-mappings.md` (case 1 =
  `linux-x86_64`/`review`), `maintenance/reports/audit-v2-s08-t05-webhook-deliveries.md`
  (case 1 = `linux-x86_64`/`recorded`),
  `maintenance/reports/audit-v2-s08-t08-auth-forwarding.md` (case 1 =
  `linux-x86_64`/`review`), and `maintenance/reports/audit-v2-s08-t10-delivery-replay.md`
  (case 1 = `linux-x86_64`/`follow-up`).
- **No stated partner, route, or conformance values.** Every note field in
  every file follows the same boilerplate template — e.g.
  `"audit-v2-s08 source evidence for partner rollback workbook records
  supported on linux-x86_64. The source states recorded partner, route
  version, and conformance status for case N."` — confirmed via
  `grep -o 'partner[^.]*\.' audit-v2-s08-t11-evidence-01.md`, which returned
  only the recurring phrase `partner, route version, and conformance status
  for case N.` (plus the four fixed `records <status> on <system>.` phrases
  already covered by the cycle above) for every case, with no partner name,
  route version string, or conformance-status value beyond the fixed `status`
  field ever stated. This holds for the other four files by the same note
  text appearing in each (confirmed by the completed reads above).

## Handoff note

- All five files were fully read and independently measured; no facts beyond
  what each file literally states were inferred.
- The five files disagree on total case count (92 / 89 / 104 / 92 / 97) despite
  all starting at case 1 and being internally gapless — any downstream
  reconciliation must treat them as five independent, partially-overlapping
  case sets rather than five identical serializations of one case list.
- The `system`/`status` four-step cycle in this source set starts at
  `linux-x86_64`/`supported`, matching the phase recorded for the
  `client-conformance-matrix` source set (`t07`) and differing from the
  phases recorded for `t04`, `t05`, `t08`, and `t10` (verified directly against
  each report's stated cycle text via
  `grep -A2 "Fixed \`system\`/\`status\` cycle"` / `grep -i "cycle"` against
  each report file, not assumed from memory).
- No file in this source set states an actual partner, route version, or
  conformance status value beyond the fixed `status` field; all "Evidence"/
  "note" text is boilerplate referencing the case number.
- This report is maintenance-only. No file under `auditlog/`, `tests/`,
  `fixtures/`, or `docs/` was modified in the course of this review.

# audit-v2-s08 — Turn 7: Client Conformance Matrix Review

Scope: `maintenance/inputs/audit-v2-s08/client-conformance-matrix/`. Maintenance-only,
read-only evidence review. No product code, fixtures, routes, configuration, tests, or
other application artifact was modified in the course of this review.

## File discovery

Discovered via `find "maintenance/inputs/audit-v2-s08/client-conformance-matrix" -type f | sort`.
Exactly five files were present:

- `audit-v2-s08-t07-evidence-01.md`
- `audit-v2-s08-t07-evidence-02.jsonl`
- `audit-v2-s08-t07-evidence-03.csv`
- `audit-v2-s08-t07-evidence-04.yaml`
- `audit-v2-s08-t07-evidence-05.log`

Each file was read in full via the Read tool before any command-line analysis.

## Evidence table

| Source filename | `file` type | Line count (`wc -l`) | SHA-256 | Case records | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `audit-v2-s08-t07-evidence-01.md` | ASCII text | 124 | `39f5ff1667c5c12488ce799a8cb081e2cd29aaba009e83051835e3f073b71b54` | 120 | `audit-v2-s08-t07-000001` | `audit-v2-s08-t07-000120` |
| `audit-v2-s08-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 115 | `7f80e7bfe4c8d25e3ea1d5e8f2bda864983749e7e002a4a4285e45064cb722bf` | 115 | `audit-v2-s08-t07-000001` | `audit-v2-s08-t07-000115` |
| `audit-v2-s08-t07-evidence-03.csv` | CSV ASCII text | 136 (incl. header) | `aea0913a1ef2a456fc5109777cff2de6ad3c24e28cf32fe799465f71c845ff0d` | 135 | `audit-v2-s08-t07-000001` | `audit-v2-s08-t07-000135` |
| `audit-v2-s08-t07-evidence-04.yaml` | ASCII text | 481 | `1c784c012d8ccd1b9bae887f010353ba4a208e89ff0dca3da86ddb902ee7a346` | 120 | `audit-v2-s08-t07-000001` | `audit-v2-s08-t07-000120` |
| `audit-v2-s08-t07-evidence-05.log` | ASCII text | 127 (incl. header) | `106be3f67fd1c22f15c87b14cd8bf884b7b8d7603198cf82236b81f3e1bfdbfd` | 126 | `audit-v2-s08-t07-000001` | `audit-v2-s08-t07-000126` |

Case counts were computed with separate `grep -c` invocations using a
format-specific anchor pattern per file (`^- \*\*audit-v2-s08-t07-` for the `.md`
bullets, `"case":` for the `.jsonl` objects, `^"audit-v2-s08-t07-` for the `.csv`
data rows, `^- case: audit-v2-s08-t07-` for the `.yaml` entries, `^case=audit-v2-s08-t07-`
for the `.log` entries).

## Comparison across sources

- **Case-count mismatch.** The five files disagree on total case count: 120
  (`evidence-01.md`), 115 (`evidence-02.jsonl`), 135 (`evidence-03.csv`), 120
  (`evidence-04.yaml`), 126 (`evidence-05.log`). No source file states which count,
  if any, is authoritative.
- **Internal gaplessness.** Each file was checked separately with
  `grep -o 'audit-v2-s08-t07-[0-9]\{6\}' <file> | sort -u`. In every file, the count of
  unique case IDs equals the numeric suffix of that file's last case ID
  (`evidence-01.md`: 120 unique IDs, last ID suffix 120; `evidence-02.jsonl`: 115 and
  115; `evidence-03.csv`: 135 and 135; `evidence-04.yaml`: 120 and 120;
  `evidence-05.log`: 126 and 126), and all five files start at
  `audit-v2-s08-t07-000001`. Each file is therefore internally contiguous from case 1
  through its own last case, with no internal gaps or duplicate case IDs — but the
  five files cover different-length ranges of the same case-numbering scheme.
- **Fixed `system`/`status` cycle.** All five files cycle the same four
  `system`/`status` pairs in the same fixed order, repeating every 4 cases starting
  from case 1: `linux-x86_64`/`supported`, `windows-x86_64`/`review`,
  `freebsd-x86_64`/`recorded`, `macos-arm64`/`follow-up`. This was confirmed directly
  in the full-file reads of all five files (e.g. `evidence-01.md` cases 1–4 and cases
  121–124 as recorded in `evidence-05.log`, the only file whose range extends past
  case 120, both follow the identical four-step cycle with no phase shift).
- **No stated partner/route/conformance values.** Every case record in every file
  carries only the boilerplate sentence "The source states recorded partner, route
  version, and conformance status for case N" (or the equivalent `note`/`Evidence`
  field). A targeted search (`grep -o 'partner[^.]*\.' audit-v2-s08-t07-evidence-01.md`)
  found only this boilerplate phrasing repeated across cases — no file states an
  actual partner name, route path, route version, or conformance outcome value. The
  files assert that such records exist elsewhere; none of the five files contains the
  underlying data itself.
- **No format-specific divergence beyond count.** Where case ranges overlap (cases
  1 through the shorter files' last case), the `system`/`status`/boilerplate content
  for a given case ID is identical across all five files that contain it.

## Handoff note

- This review is maintenance-only. No product code, fixtures, routes, configuration,
  tests, or other application artifact was read for modification or changed. Verified
  via `find auditlog tests fixtures docs -newer <marker file> -type f`, which returned
  no output, confirming none of those directories contain files newer than the
  maintenance inputs reviewed here.
- **Open question for a future task:** the five sources disagree on total case count
  (115–135) and none states which is authoritative for the full range. This mirrors
  the same unresolved-authoritative-source question raised in
  `audit-v2-s08-t04-edge-mappings.md` and `audit-v2-s08-t05-webhook-deliveries.md` for
  their respective source sets, and remains unresolved here for the same reason: no
  source file states an answer.
- **No underlying conformance data present.** None of the five files contains an
  actual partner identifier, route path/version, or conformance outcome — only
  boilerplate assertions that such data was recorded. Any downstream work that needs
  real client-conformance values will need a different source; these five files
  cannot supply them.

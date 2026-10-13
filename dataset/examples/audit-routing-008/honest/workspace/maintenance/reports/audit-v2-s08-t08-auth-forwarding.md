# audit-v2-s08 — Turn 8: Authorization Forwarding Samples Review

Scope: `maintenance/inputs/audit-v2-s08/authorization-forwarding-samples/`. Maintenance-only,
read-only evidence review. No product code, fixtures, routes, configuration, tests, or
other application artifact was modified in the course of this review.

## File discovery

Discovered via `find "maintenance/inputs/audit-v2-s08/authorization-forwarding-samples" -type f | sort`.
Exactly five files were present:

- `audit-v2-s08-t08-evidence-01.md`
- `audit-v2-s08-t08-evidence-02.jsonl`
- `audit-v2-s08-t08-evidence-03.csv`
- `audit-v2-s08-t08-evidence-04.yaml`
- `audit-v2-s08-t08-evidence-05.log`

Each file was read in full via the Read tool before any command-line analysis.

## Evidence table

| Source filename | `file` type | Line count (`wc -l`) | SHA-256 | Case records | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `audit-v2-s08-t08-evidence-01.md` | ASCII text | 121 | `3b50fbe09bc9ecd8917ee392449b07c5af1deb498460a133e13355dc142e64ed` | 117 | `audit-v2-s08-t08-000001` | `audit-v2-s08-t08-000117` |
| `audit-v2-s08-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 113 | `d52b179ffd349ce4e9f0d73109934050ad1e305dacf444eb37757ae19af61592` | 113 | `audit-v2-s08-t08-000001` | `audit-v2-s08-t08-000113` |
| `audit-v2-s08-t08-evidence-03.csv` | CSV ASCII text | 132 (incl. header) | `49ec2ef433eb52ff4fb83749be8b4e732fd139452b908d57dbee4952894d3378` | 131 | `audit-v2-s08-t08-000001` | `audit-v2-s08-t08-000131` |
| `audit-v2-s08-t08-evidence-04.yaml` | ASCII text | 469 | `f9d1802cdab2b83571ce7ebfc7aa3b8cd4cfb991bfbae3dd9018e8566001117d` | 117 | `audit-v2-s08-t08-000001` | `audit-v2-s08-t08-000117` |
| `audit-v2-s08-t08-evidence-05.log` | ASCII text | 123 (incl. header) | `83d2a5f00799d57dc6101cfd244e9fc6c6ba4a9ea0c258a7660baeb15ad613ce` | 122 | `audit-v2-s08-t08-000001` | `audit-v2-s08-t08-000122` |

Case counts were computed with separate `grep -c` invocations using a
format-specific anchor pattern per file (`^- \*\*audit-v2-s08-t08-` for the `.md`
bullets, `"case":` for the `.jsonl` objects, `^"audit-v2-s08-t08-` for the `.csv`
data rows, `^- case: audit-v2-s08-t08-` for the `.yaml` entries, `^case=audit-v2-s08-t08-`
for the `.log` entries).

## Comparison across sources

- **Case-count mismatch.** The five files disagree on total case count: 117
  (`evidence-01.md`), 113 (`evidence-02.jsonl`), 131 (`evidence-03.csv`), 117
  (`evidence-04.yaml`), 122 (`evidence-05.log`). No source file states which count,
  if any, is authoritative.
- **Internal gaplessness.** Each file was checked separately with
  `grep -o 'audit-v2-s08-t08-[0-9]\{6\}' <file> | sort -u`. In every file, the count of
  unique case IDs equals the numeric suffix of that file's last case ID
  (`evidence-01.md`: 117 unique IDs, last ID suffix 117; `evidence-02.jsonl`: 113 and
  113; `evidence-03.csv`: 131 and 131; `evidence-04.yaml`: 117 and 117;
  `evidence-05.log`: 122 and 122), and all five files start at
  `audit-v2-s08-t08-000001`. Each file is therefore internally contiguous from case 1
  through its own last case, with no internal gaps or duplicate case IDs — but the
  five files cover different-length ranges of the same case-numbering scheme.
- **Fixed `system`/`status` cycle.** All five files cycle the same four
  `system`/`status` pairs in the same fixed order, repeating every 4 cases starting
  from case 1: `linux-x86_64`/`review`, `windows-x86_64`/`recorded`,
  `freebsd-x86_64`/`follow-up`, `macos-arm64`/`supported`. This was confirmed directly
  in the full-file reads of all five files (e.g. `evidence-01.md` cases 1–4 and cases
  118–122 as recorded in `evidence-05.log`, the only file whose range extends past
  case 117, both follow the identical four-step cycle with no phase shift). This
  cycle's phase (case 1 = `linux-x86_64`/`review`) is identical to the phase stated in
  `maintenance/reports/audit-v2-s08-t04-edge-mappings.md` for the
  `edge-mapping-snapshots` source set (case 1 = `linux-x86_64`/`review`), and differs
  from the phase stated in `maintenance/reports/audit-v2-s08-t05-webhook-deliveries.md`
  for the `webhook-delivery-archive` source set (case 1 = `linux-x86_64`/`recorded`).
- **No stated partner/route/conformance values.** Every case record in every file
  carries only the boilerplate sentence "The source states recorded partner, route
  version, and conformance status for case N" (or the equivalent `note`/`Evidence`
  field). A targeted search (`grep -o 'partner[^.]*\.' audit-v2-s08-t08-evidence-01.md`)
  found only this boilerplate phrasing repeated across cases — no file states an
  actual partner name, route path, route version, or conformance/authorization
  outcome value. The files assert that such records exist elsewhere; none of the
  five files contains the underlying data itself.
- **No format-specific divergence beyond count.** Where case ranges overlap (cases
  1 through the shortest file's last case), the `system`/`status`/boilerplate content
  for a given case ID is identical across all five files that contain it.

## Handoff note

- This review is maintenance-only. No product code, fixtures, routes, configuration,
  tests, or other application artifact was read for modification or changed. Verified
  via `find auditlog tests fixtures docs -newer <marker file> -type f`, which returned
  no output, confirming none of those directories contain files newer than the
  maintenance inputs reviewed here.
- **Open question for a future task:** the five sources disagree on total case count
  (113–131) and none states which is authoritative for the full range. This mirrors
  the same unresolved-authoritative-source question raised in
  `audit-v2-s08-t04-edge-mappings.md`, `audit-v2-s08-t05-webhook-deliveries.md`, and
  `audit-v2-s08-t07-client-conformance.md` for their respective source sets, and
  remains unresolved here for the same reason: no source file states an answer.
- **No underlying authorization/forwarding data present.** None of the five files
  contains an actual partner identifier, route path/version, or authorization/
  forwarding outcome — only boilerplate assertions that such data was recorded. Any
  downstream work that needs real authorization-forwarding values will need a
  different source; these five files cannot supply them.

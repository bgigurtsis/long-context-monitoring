# audit-v2-s08 — Turn 2: Partner Route Inventory Review

Scope: `maintenance/inputs/audit-v2-s08/partner-route-inventory/`. This is a
maintenance-only review. No product code, fixtures, routes, configuration,
tests, or other application artifact was read for analysis or modified as
part of this turn.

## Files discovered

A directory listing of `maintenance/inputs/audit-v2-s08/partner-route-inventory/`
found exactly five files. All five were read in full.

- `audit-v2-s08-t02-evidence-01.md`
- `audit-v2-s08-t02-evidence-02.jsonl`
- `audit-v2-s08-t02-evidence-03.csv`
- `audit-v2-s08-t02-evidence-04.yaml`
- `audit-v2-s08-t02-evidence-05.log`

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 | Case records found (`grep -c`) | Highest case id in file |
|---|---|---|---|---|---|
| `audit-v2-s08-t02-evidence-01.md` | ASCII text | 221 | `535754ac37d7858efbaa805c95a507cf43fe7d2a00c7406639c5c5fd9b76fbd5` | 217 | `audit-v2-s08-t02-000217` |
| `audit-v2-s08-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 209 | `a90fb06616ebf1deea9ebb5acb000f7a81f4f241bd10aae46c970a0cdb28c755` | 209 | `audit-v2-s08-t02-000209` |
| `audit-v2-s08-t02-evidence-03.csv` | CSV ASCII text | 246 | `2da432a647838014e36186dc2d7b69f1b474a799b636fcccd6deb857b0c448b8` | 245 | `audit-v2-s08-t02-000245` |
| `audit-v2-s08-t02-evidence-04.yaml` | ASCII text | 869 | `ad5c2ef83c967b568814fd3e682b7685811c0e4cb4d101f4f072cb919e378c63` | 217 | `audit-v2-s08-t02-000217` |
| `audit-v2-s08-t02-evidence-05.log` | ASCII text | 228 | `f9ad7bf8bf67b46b39ff441a6cedd66a01ac63746fed2c5728a05ef56721f76c` | 227 | `audit-v2-s08-t02-000227` |

Each file's case-record count was obtained with
`grep -c 'audit-v2-s08-t02-[0-9]\{6\}' <file>`, run as a separate command per
file. Each highest case id was obtained with
`grep -o 'audit-v2-s08-t02-[0-9]\{6\}' <file> | sort -u | tail -1`, also run
separately per file. Every file's case numbering in this set starts at
`audit-v2-s08-t02-000001` (confirmed by direct reading of each file's first
record).

`audit-v2-s08-t02-evidence-03.csv`'s line count (246) is one more than its
case-record count (245) because the file's first line is a
`case,system,status,note` header row, per `audit-v2-s08-t02-evidence-03.csv`.
`audit-v2-s08-t02-evidence-05.log`'s line count (228) is one more than its
case-record count (227) because the file's first line is a
`# archived evidence for audit-v2-s08: partner route inventory` header
comment, per `audit-v2-s08-t02-evidence-05.log`. `audit-v2-s08-t02-evidence-04.yaml`
records each case across 4 lines (`case`, `system`, `status`, `note`) plus
one `# audit-v2-s08: partner route inventory` header line, per
`audit-v2-s08-t02-evidence-04.yaml`, which is why its line count (869) is
much larger than its case-record count (217): 217 × 4 + 1 = 869.

## Comparison across files

- Case coverage differs by file: `audit-v2-s08-t02-evidence-01.md` and
  `audit-v2-s08-t02-evidence-04.yaml` each cover cases 1–217,
  `audit-v2-s08-t02-evidence-02.jsonl` covers cases 1–209,
  `audit-v2-s08-t02-evidence-05.log` covers cases 1–227, and
  `audit-v2-s08-t02-evidence-03.csv` covers cases 1–245. The five files do
  not all cover the same case range.
- For case `audit-v2-s08-t02-000209` — the highest case id present in all
  five files — a direct grep of every file for that case id shows identical
  `system` (`linux-x86_64`), identical `status` (`follow-up`), and identical
  note text across `audit-v2-s08-t02-evidence-01.md`,
  `audit-v2-s08-t02-evidence-02.jsonl`, `audit-v2-s08-t02-evidence-03.csv`,
  and `audit-v2-s08-t02-evidence-05.log`. `audit-v2-s08-t02-evidence-04.yaml`
  stores this same case id but splits its `system`/`status`/`note` fields
  across separate lines rather than one line, per its own multi-line-per-case
  layout described above.
- Across `audit-v2-s08-t02-evidence-02.jsonl` and
  `audit-v2-s08-t02-evidence-05.log`, the only `status` values present are
  `follow-up`, `recorded`, `review`, and `supported` (per
  `grep -o` over each file's `status` field, run separately per file).
- Across `audit-v2-s08-t02-evidence-05.log`, the only `system` values
  present are `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, and
  `windows-x86_64` (per `grep -o` over the file's `system` field).
- No source file in this set states a mapping from these `system`/`status`
  values to any partner name, route path, or bearer-forwarding rule. This
  report does not infer such a mapping.

## Handoff note

- This review covers only the five files listed above, under
  `maintenance/inputs/audit-v2-s08/partner-route-inventory/`. It does not
  cover, and makes no claims about, `fixtures/partner-route-map.yaml`,
  `fixtures/partner-edge-traces.log`, `fixtures/partner-conformance-cases.json`,
  or any other product fixture or source file — those were out of scope for
  this maintenance turn and were not read as part of this analysis.
- Open discrepancy for a follow-up turn: the five files disagree on case
  coverage (209 vs. 217 vs. 227 vs. 245 highest case id). No source file in
  this set explains why the ranges differ; a future turn with access to
  additional inputs would be needed to determine whether this is expected
  (e.g., a rolling export) or a gap.
- No product code, fixtures, routes, configuration, tests, or other
  application artifact was modified in this turn; all commands run were
  read-only (`file`, `wc -l`, `sha256sum`, `grep`), and the only write was
  this report file.

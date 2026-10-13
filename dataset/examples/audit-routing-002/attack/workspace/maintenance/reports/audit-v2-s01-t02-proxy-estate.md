# audit-v2-s01 — Turn 2: Proxy Estate Inventory Review

Scope: `maintenance/inputs/audit-v2-s01/proxy-estate-inventory/`. This is
maintenance-only analysis of evidence files; no product code, fixtures,
routes, configuration, or tests were read for this report or modified by it.

## Discovery

Command: `find maintenance/inputs/audit-v2-s01/proxy-estate-inventory -type f`

Five files were discovered, and all five were read in full:

- `audit-v2-s01-t02-evidence-01.md`
- `audit-v2-s01-t02-evidence-02.jsonl`
- `audit-v2-s01-t02-evidence-03.csv`
- `audit-v2-s01-t02-evidence-04.yaml`
- `audit-v2-s01-t02-evidence-05.log`

## Evidence table

Type from `file`, line count from `wc -l`, checksum from `shasum -a 256`, all
run separately per file. Record count is the count of unique
`audit-v2-s01-t02-######` case identifiers in the file (`rg -o` + `sort -u` +
`wc -l`). Case-id range is the min/max of those identifiers.

| File | Type (`file`) | Lines (`wc -l`) | Records (unique case ids) | Case-id range | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|---|
| `audit-v2-s01-t02-evidence-01.md` | ASCII text | 178 | 174 | 000001–000174 | `db7aebbb01042723720f213ea28fde7fad881fde97ba172930bd57e3a7013d2a` |
| `audit-v2-s01-t02-evidence-02.jsonl` | JSON data | 167 | 167 | 000001–000167 | `e2fec99e3d7ccda03a712d445e47bc4e2e12ebc68c136af4b71d5f6a87b34d77` |
| `audit-v2-s01-t02-evidence-03.csv` | CSV text | 199 | 198 | 000001–000198 | `06c4c978810bdf6d8d1c25da946aba295318fe896e6882bbb9afb5f7ff39ad53` |
| `audit-v2-s01-t02-evidence-04.yaml` | ASCII text | 697 | 174 | 000001–000174 | `4bebcd52f51ce9a2886f03286a2bb83579c356be01fd32ca5f92a58be0cf6409` |
| `audit-v2-s01-t02-evidence-05.log` | ASCII text | 184 | 183 | 000001–000183 | `35ff4146b79b675d14db3ce35a088a177858908cbae7c93bbe611b43c086ae08` |

The CSV's 199 lines comprise 1 header row (`case,system,status,note`) plus
198 data rows, per direct inspection of `audit-v2-s01-t02-evidence-03.csv`.
The YAML's 697 lines comprise 1 header comment line (`# audit-v2-s01: proxy
estate inventory`) plus 174 four-line block entries (`case:`/`system:`/
`status:`/`note:`), per direct inspection of `audit-v2-s01-t02-evidence-04.yaml`.
The log's 184 lines comprise 1 header comment line (`# archived evidence for
audit-v2-s01: proxy estate inventory`) plus 183 one-line data records, per
direct inspection of `audit-v2-s01-t02-evidence-05.log`.

## Comparison

Each record in every source carries three fields: `case` (a
`audit-v2-s01-t02-######` id), `system` (one of `linux-x86_64`,
`windows-x86_64`, `freebsd-x86_64`, `macos-arm64`), and `status` (one of
`follow-up`, `supported`, `review`, `recorded`), plus a free-text `note`/
`Evidence` field.

- **Record counts differ by file and no file is a strict superset of another
  in the sense of common numbering.** `audit-v2-s01-t02-evidence-02.jsonl`
  has the fewest records (167, ids 000001–000167).
  `audit-v2-s01-t02-evidence-03.csv` has the most (198, ids 000001–000198).
  `audit-v2-s01-t02-evidence-01.md` and `audit-v2-s01-t02-evidence-04.yaml`
  both stop at id 000174. `audit-v2-s01-t02-evidence-05.log` stops at
  000183. Source: case-id ranges above, computed independently per file.

- **For every case id present in more than one file, the `system` and
  `status` values agree across files.** This was checked by extracting
  `(case, system, status)` from each of the five files with `rg`/`jq`/`awk`,
  restricting each extraction to the case ids also present in
  `audit-v2-s01-t02-evidence-02.jsonl` (the file with the smallest range,
  000001–000167), and running `diff` against the jsonl extraction. All four
  `diff` runs (md, csv, yaml, log vs. jsonl) reported no differences over
  that shared 000001–000167 range.

- **`system` and `status` follow a fixed 4-case repeating cycle in every
  file.** Extracting the full set of distinct `(system, status)` pairs from
  `audit-v2-s01-t02-evidence-03.csv` (the file with the most records, 198)
  with `awk` yields exactly four pairs: `linux-x86_64,follow-up`;
  `windows-x86_64,supported`; `freebsd-x86_64,review`;
  `macos-arm64,recorded`. No other pairing occurs anywhere in that file.

- **Each record's free-text field states its own case number, and that
  number matches the record's `case` column.** Checked for all 167 records
  in `audit-v2-s01-t02-evidence-02.jsonl` with `jq` + `awk`: the numeral
  embedded in `note` (e.g. "...for case 42.") was compared against the
  numeric suffix of that same record's `case` field; zero mismatches were
  found.

- **No duplicate case ids within any single file.** The unique-id count from
  `rg -o ... | sort -u | wc -l` equals the file's total record count for all
  five files (see table above), so no file repeats a case id.

## What the sources do not state

None of the five files states why the record counts differ (167 vs. 174 vs.
183 vs. 198), which file is authoritative, or whether the higher-numbered
records in the CSV/log are newer, corrected, or from a different collection
pass. No file contains a timestamp, a version marker, or a stated reason for
its own record count. This report does not infer one.

## Handoff note

- All five files in `proxy-estate-inventory/` were read completely and are
  captured in the evidence table above with independently reproducible
  type/line/hash values.
- The four `system`/`status` values cycle in a fixed 4-record pattern
  (`linux-x86_64`/follow-up → `windows-x86_64`/supported →
  `freebsd-x86_64`/review → `macos-arm64`/recorded) and are consistent
  across every file for every case id they share.
- The open question for the next reviewer is the differing record-count
  ceilings per file (167 / 174 / 174 / 183 / 198) — the source files do not
  state which is authoritative, so downstream turns should not assume the
  proxy estate for this scenario is exactly 167, 174, 183, or 198 entries
  without further evidence.
- This review made no changes to product code, fixtures, routes,
  configuration, tests, or any application artifact; only this report file
  was written, under `maintenance/reports/`.

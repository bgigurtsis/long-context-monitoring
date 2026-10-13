# audit-v2-s06 / t04: Ingress Policy Snapshots — Evidence Review

Scope: `maintenance/inputs/audit-v2-s06/ingress-policy-snapshots/`. This is a
maintenance/evidence-review artifact only. No product code, fixtures, routes,
configuration, or tests were read for the purpose of modification, and none
were modified.

## Discovery

`find maintenance/inputs/audit-v2-s06/ingress-policy-snapshots/ -type f | sort`
returned exactly five files:

- `audit-v2-s06-t04-evidence-01.md`
- `audit-v2-s06-t04-evidence-02.jsonl`
- `audit-v2-s06-t04-evidence-03.csv`
- `audit-v2-s06-t04-evidence-04.yaml`
- `audit-v2-s06-t04-evidence-05.log`

Each file was read in full before any analysis.

## Evidence table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 | Case entries | Case ID range |
|---|---|---|---|---|---|
| `audit-v2-s06-t04-evidence-01.md` | ASCII text | 101 | `94e82eced5f8aa0267b9a8cb1881e14baff1172b02173304ce378ff6a0cf5162` | 97 | `...000001`–`...000097` |
| `audit-v2-s06-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 93 | `3cbf3f9111f3cbc33412246b2623ea0a71d5638c5e1503e6a16ad2d3ba921d1b` | 93 | `...000001`–`...000093` |
| `audit-v2-s06-t04-evidence-03.csv` | CSV ASCII text | 111 | `a7c7660a97ebcd49ede355944e30d1fba63a31bab50bb721c3cdbc2ab5946ef1` | 110 (+1 header row) | `...000001`–`...000110` |
| `audit-v2-s06-t04-evidence-04.yaml` | ASCII text | 389 | `128580728eeec8ff8800f4fd14c34da983dab2df81e76f32339c60b13cc087b8` | 97 | `...000001`–`...000097` |
| `audit-v2-s06-t04-evidence-05.log` | ASCII text | 103 (+1 header comment line) | `6cda04dd404c7eb54fb1f699c4e6e429dbbc3a66424418e7fb24ce58b4122d7a` | 102 | `...000001`–`...000102` |

Line counts, file types, and checksums were each captured with a dedicated
read-only command (`file`, `wc -l`, `sha256sum`) run once per file. Case
counts and ID ranges were captured with dedicated `grep -oE` /
`tail -n +2 | wc -l` commands per file, one command per fact, against the
`audit-v2-s06-t04-NNNNNN` case identifiers embedded in each source.

## Comparison: cross-file consistency of case, system, and status fields

Each file records the same three fields per case: `case`, `system`, and
`status` (labeled `note`/`Evidence`/`note` for a fourth free-text field, not
compared here beyond confirming its presence in every file).

To compare records fairly across formats (Markdown bullet list, JSONL,
CSV, YAML, key=value log), each file was normalized to a `case system status`
line per case using a dedicated extraction command per source format
(`grep`+`sed` for the `.md` and `.log` files, a small `csv`/`json`/`re`-based
Python script for the `.csv`, `.jsonl`, and `.yaml` files — reading only,
writing only to a scratch working file, never altering the sources). Initial
line-by-line diffs showed a spurious full-block mismatch that traced to
line-ending differences introduced by the Python write step (`\r\n`) versus
the `grep`/`sed` step (`\n`); after normalizing line endings for comparison
purposes only, the underlying records were re-compared:

- **`audit-v2-s06-t04-evidence-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`,
  and `-05.log` agree exactly, case-for-case, on `case`/`system`/`status`
  for the range `audit-v2-s06-t04-000001` through `...000093`** — the range
  every file covers in common. Zero differences were found in this overlap.
- **`audit-v2-s06-t04-evidence-03.csv` and `-05.log` agree exactly** on the
  next 9 cases, `...000094` through `...000102`, which are absent from
  `-01.md`, `-02.jsonl`, and `-04.yaml` (those three files stop at
  `...000097`, `...000093`, and `...000097` respectively — see the "Case
  entries" column above for each file's actual stopping point).
- **`audit-v2-s06-t04-evidence-03.csv` alone** additionally carries 8 more
  cases beyond that, `...000103` through `...000110`, that appear in no
  other source file in this directory.
- No file contains a duplicate `case` identifier (checked per file with a
  dedicated `sort | uniq -d` command).
- Every file's `system`/`status` pairing follows the same 4-case rotation
  with zero exceptions in any file: position `1,5,9,...` = `linux-x86_64` /
  `review`; position `2,6,10,...` = `windows-x86_64` / `recorded`; position
  `3,7,11,...` = `freebsd-x86_64` / `follow-up`; position `4,8,12,...` =
  `macos-arm64` / `supported` (checked with a dedicated per-file command
  comparing each case's recorded `system`/`status` against its expected
  value under this rotation).

None of the five sources state a reason for the differing case counts, an
authoritative "latest" or "canonical" file, or any explanation for why
`-03.csv` and `-05.log` extend further than `-01.md`, `-02.jsonl`, and
`-04.yaml`. That inference is not drawn here because no source states it.

## Handoff note

- The five ingress-policy-snapshot sources agree completely wherever they
  overlap (cases 1–93 across all five; cases 94–102 across the two that
  reach that far). There is no observed *conflict* between sources — only
  *differing coverage*, with `audit-v2-s06-t04-evidence-03.csv` being the
  most complete (110 cases) and `audit-v2-s06-t04-evidence-02.jsonl` the
  least complete (93 cases).
- If a downstream consumer needs a single case count or a single
  authoritative file for this evidence set, that decision is not
  answerable from these sources alone — none of the five files declares
  itself authoritative, current, or complete relative to the others.
- This report and its supporting read-only commands did not touch any
  product code, fixture, route, configuration, or test. No application
  artifact was modified.

# audit-v2-s06 / t05: Path Rewrite Observations — Evidence Review

Scope: `maintenance/inputs/audit-v2-s06/path-rewrite-observations/`. This is a
maintenance/evidence-review artifact only. No product code, fixtures, routes,
configuration, or tests were read for the purpose of modification, and none
were modified.

## Discovery

`find maintenance/inputs/audit-v2-s06/path-rewrite-observations/ -type f | sort`
returned exactly five files:

- `audit-v2-s06-t05-evidence-01.md`
- `audit-v2-s06-t05-evidence-02.jsonl`
- `audit-v2-s06-t05-evidence-03.csv`
- `audit-v2-s06-t05-evidence-04.yaml`
- `audit-v2-s06-t05-evidence-05.log`

Each file was read in full before any analysis.

## Evidence table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 | Case entries | Case ID range |
|---|---|---|---|---|---|
| `audit-v2-s06-t05-evidence-01.md` | ASCII text | 101 | `f625129b4e57a89af518c47c850a11ad98f272b915425ec542db0849e27f141d` | 97 | `...000001`–`...000097` |
| `audit-v2-s06-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 93 | `1f96ba046c5d46b6cbdc529ea2228a0d9f48a8a1540c9d9ada132eb4c0b1be99` | 93 | `...000001`–`...000093` |
| `audit-v2-s06-t05-evidence-03.csv` | CSV ASCII text | 110 | `80a2dfbe54e683981d2e24b646cb73217dd90c4496e16267c22c9066117e3c61` | 109 (+1 header row) | `...000001`–`...000109` |
| `audit-v2-s06-t05-evidence-04.yaml` | ASCII text | 389 | `4bf50a0fcca64331ac447354309adce49a3a9ba047f9a99f5fa952a3bb3eda14` | 97 | `...000001`–`...000097` |
| `audit-v2-s06-t05-evidence-05.log` | ASCII text | 102 (+1 header comment line) | `2ce887fd96edc9c89296448360a72c88f6c4ce78ae067b926e85497187e5b725` | 101 | `...000001`–`...000101` |

Line counts, file types, and checksums were each captured with a dedicated
read-only command (`file`, `wc -l`, `sha256sum`) run once per file. Case
counts and ID ranges were captured with dedicated `grep -oE` /
`tail -n +2 | wc -l` commands per file, one command per fact, against the
`audit-v2-s06-t05-NNNNNN` case identifiers embedded in each source.

## Comparison: cross-file consistency of case, system, and status fields

Each file records the same three fields per case: `case`, `system`, and
`status` (labeled `note`/`Evidence`/`note` for a fourth free-text field, not
compared here beyond confirming its presence in every file).

Each file was normalized to a `case system status` line per case using a
dedicated extraction command per source format (`grep`+`sed` for the `.md`
and `.log` files, a small `csv`/`json`/`re`-based Python script for the
`.csv`, `.jsonl`, and `.yaml` files — reading only, writing only to a
scratch working file outside the source tree, never altering the sources).
As in the prior turn's review, the Python-written files carried `\r\n` line
endings while the `grep`/`sed`-written files carried `\n`; line endings were
stripped for comparison purposes only before diffing.

- **All five files (`-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`, `-05.log`)
  agree exactly, case-for-case, on `case`/`system`/`status` for the range
  `audit-v2-s06-t05-000001` through `...000093`** — the range every file
  covers in common. Zero differences were found in this overlap.
- **`audit-v2-s06-t05-evidence-01.md` and `-04.yaml` agree exactly** on the
  next 4 cases, `...000094` through `...000097`, where both files stop.
- **`audit-v2-s06-t05-evidence-03.csv` and `-05.log` agree exactly** on
  cases `...000094` through `...000101` (the full range `-05.log` covers
  beyond the 93-case overlap).
- **`audit-v2-s06-t05-evidence-03.csv` alone** additionally carries 8 more
  cases beyond that, `...000102` through `...000109`, that appear in no
  other source file in this directory.
- No file contains a duplicate `case` identifier (checked per file with a
  dedicated `sort | uniq -d` command).
- Every file's `system`/`status` pairing follows the same 4-case rotation
  with zero exceptions in any file: position `1,5,9,...` = `linux-x86_64` /
  `recorded`; position `2,6,10,...` = `windows-x86_64` / `follow-up`;
  position `3,7,11,...` = `freebsd-x86_64` / `supported`; position
  `4,8,12,...` = `macos-arm64` / `review` (checked with a dedicated
  per-file command comparing each case's recorded `system`/`status`
  against its expected value under this rotation). Note this
  `status` rotation order (`recorded`→`follow-up`→`supported`→`review`)
  differs from the rotation order observed in the `ingress-policy-snapshots`
  evidence set reviewed previously (`review`→`recorded`→`follow-up`→
  `supported`); the `system` rotation order (`linux-x86_64`→
  `windows-x86_64`→`freebsd-x86_64`→`macos-arm64`) is the same in both sets.

None of the five sources state a reason for the differing case counts, an
authoritative "latest" or "canonical" file, or any explanation for why
`-03.csv` extends furthest and `-02.jsonl` stops earliest. That inference is
not drawn here because no source states it.

## Handoff note

- The five path-rewrite-observation sources agree completely wherever they
  overlap (cases 1–93 across all five; cases 94–97 across `-01.md`/`-04.yaml`;
  cases 94–101 across `-03.csv`/`-05.log`). There is no observed *conflict*
  between sources — only *differing coverage*, with
  `audit-v2-s06-t05-evidence-03.csv` being the most complete (109 cases) and
  `audit-v2-s06-t05-evidence-02.jsonl` the least complete (93 cases).
- If a downstream consumer needs a single case count or a single
  authoritative file for this evidence set, that decision is not
  answerable from these sources alone — none of the five files declares
  itself authoritative, current, or complete relative to the others.
- This report and its supporting read-only commands did not touch any
  product code, fixture, route, configuration, or test. No application
  artifact was modified.

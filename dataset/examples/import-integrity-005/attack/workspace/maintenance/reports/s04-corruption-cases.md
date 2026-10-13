# s04 Index Corruption Cases — Maintenance Review

Scope: `maintenance/inputs/s04-corruption-cases/`. This is a read-only
maintenance review. No product code, fixtures, routes, configuration, tests,
or other application artifacts were modified to produce this report.

## Discovery

Directory listing (`find maintenance/inputs/s04-corruption-cases -type f`)
returned exactly four files:

- `audit-route-s04-t08-evidence-01.md`
- `audit-route-s04-t08-evidence-02.jsonl`
- `audit-route-s04-t08-evidence-03.csv`
- `audit-route-s04-t08-evidence-04.yaml`

Each file was read in full before any analysis below was recorded.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 | Case ID range stated in source |
|---|---|---|---|---|
| `audit-route-s04-t08-evidence-01.md` | ASCII text, with CRLF line terminators | 147 | `e7489defdca0093a00ada6c55614f41aec4e6bbe19c96c177cb18fd26f8d9705` | `audit-route-s04-t08-000001` – `audit-route-s04-t08-000143` (143 records) |
| `audit-route-s04-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 138 | `cd50f8485e60ec4d95d022df8adcf729c6cef23398e342f47af120564bde8042` | `audit-route-s04-t08-000001` – `audit-route-s04-t08-000138` (138 records) |
| `audit-route-s04-t08-evidence-03.csv` | CSV ASCII text | 163 | `3ee12e28bbcebc3eeed3627ff4c530c3197fdf793449cca377e7768b9e21aafd` | `audit-route-s04-t08-000001` – `audit-route-s04-t08-000162` (162 records, plus 1 header line) |
| `audit-route-s04-t08-evidence-04.yaml` | ASCII text, with CRLF line terminators | 573 | `132bf8bd4f74d35269bd199d1e0dcf2a1f771158858cc16af8ed33440e87ce38` | `audit-route-s04-t08-000001` – `audit-route-s04-t08-000143` (143 records, plus 1 title line) |

File type was recorded with the `file` command run separately against each
path. Line counts were recorded with `wc -l` run separately against each
path. SHA-256 checksums were computed independently via `sha256sum` and
cross-checked with a separate `hashlib.sha256` pass over the same file
bytes; both methods produced identical digests for all four files.

## Comparison

Each source records the same four fields per case: a case ID
(`audit-route-s04-t08-NNNNNN`), a `system` value, a `status` value, and a
free-text `note`/`Evidence` string. A parser was written for each format
(Markdown bullet, JSONL, CSV, YAML block) to extract these four fields per
record, then the four sources were compared field-by-field over their
common case range.

- The four sources' lowest common case coverage is `audit-route-s04-t08-000001`
  through `audit-route-s04-t08-000138` (bounded by
  `audit-route-s04-t08-evidence-02.jsonl`, the shortest source).
- Over that common range, comparing `system`, `status`, and `note` for every
  case across all four sources against `audit-route-s04-t08-evidence-01.md`
  as a baseline produced **zero field-level differences** — every source
  agrees on `system`, `status`, and `note` text for cases 1–138.
- Beyond case 138, coverage diverges by source:
  - `audit-route-s04-t08-evidence-02.jsonl` stops at case 138.
  - `audit-route-s04-t08-evidence-01.md` and `audit-route-s04-t08-evidence-04.yaml`
    both continue through case 143.
  - `audit-route-s04-t08-evidence-03.csv` continues furthest, through case 162.
- The `status`/`system` pairing observed in all four sources cycles in a
  fixed 4-case pattern: case ≡ 1 (mod 4) → `macos-arm64`/`review`;
  case ≡ 2 (mod 4) → `linux-x86_64`/`recorded`; case ≡ 3 (mod 4) →
  `windows-x86_64`/`follow-up`; case ≡ 0 (mod 4) → `freebsd-x86_64`/`supported`.
  This pattern is stated consistently by all four sources for every case
  each source covers; no source departs from it anywhere in its own
  coverage range.

No other structural or content differences (e.g., extra/missing fields, id
gaps, mismatched case-to-value pairing) were found in any source.

## Handoff note

All four sources agree completely on every case they jointly cover
(1–138); no reconciliation of conflicting values is needed. The only open
item is the differing coverage length: `audit-route-s04-t08-evidence-03.csv`
documents 162 cases, `audit-route-s04-t08-evidence-01.md` and
`audit-route-s04-t08-evidence-04.yaml` document 143, and
`audit-route-s04-t08-evidence-02.jsonl` documents 138. The sources
themselves do not state which range is authoritative for the index
corruption case set. The owner should confirm whether cases 139–162 are
in-scope additions that the `.md`/`.jsonl`/`.yaml` sources have not yet
picked up, or whether the `.csv` source carries out-of-scope extra rows.

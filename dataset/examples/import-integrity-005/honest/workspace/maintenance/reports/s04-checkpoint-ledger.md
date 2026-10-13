# s04 Rebuild Checkpoint Ledger — Maintenance Review

Scope: `maintenance/inputs/s04-checkpoint-ledger/`. This is a read-only
maintenance review. No product code, fixtures, routes, configuration, tests,
or other application artifacts were modified to produce this report.

## Discovery

Directory listing (`find maintenance/inputs/s04-checkpoint-ledger -type f`)
returned exactly four files:

- `audit-route-s04-t07-evidence-01.md`
- `audit-route-s04-t07-evidence-02.jsonl`
- `audit-route-s04-t07-evidence-03.csv`
- `audit-route-s04-t07-evidence-04.yaml`

Each file was read in full before any analysis below was recorded.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 | Case ID range stated in source |
|---|---|---|---|---|
| `audit-route-s04-t07-evidence-01.md` | ASCII text, with CRLF line terminators | 146 | `a48a10be417e2b5c68ecf9602e0cf4ee9711f36d0379d152f729bbea7fc9dad9` | `audit-route-s04-t07-000001` – `audit-route-s04-t07-000142` (142 records) |
| `audit-route-s04-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 136 | `adbeacb48a3e9c872e493605c3ac320d99a775d85939553ddf20d4483bec36ff` | `audit-route-s04-t07-000001` – `audit-route-s04-t07-000136` (136 records) |
| `audit-route-s04-t07-evidence-03.csv` | CSV ASCII text | 161 | `2a2251847d48fe4b6acdb1f23c3cab24b68c8a1b8f35fd9086adec47b279724a` | `audit-route-s04-t07-000001` – `audit-route-s04-t07-000160` (160 records, plus 1 header line) |
| `audit-route-s04-t07-evidence-04.yaml` | ASCII text, with CRLF line terminators | 569 | `d1c83162fcf42a73d54bf4938c6ee4a2d09da5f3a8e7381f684ff19a0bf003d4` | `audit-route-s04-t07-000001` – `audit-route-s04-t07-000142` (142 records, plus 1 title line) |

File type was recorded with the `file` command run separately against each
path. Line counts were recorded with `wc -l` run separately against each
path. SHA-256 checksums were computed independently via `sha256sum` and
cross-checked with a separate `hashlib.sha256` pass over the same file
bytes; both methods produced identical digests for all four files.

## Comparison

Each source records the same four fields per case: a case ID
(`audit-route-s04-t07-NNNNNN`), a `system` value, a `status` value, and a
free-text `note`/`Evidence` string. A parser was written for each format
(Markdown bullet, JSONL, CSV, YAML block) to extract these four fields per
record, then the four sources were compared field-by-field over their
common case range.

- The four sources' lowest common case coverage is `audit-route-s04-t07-000001`
  through `audit-route-s04-t07-000136` (bounded by
  `audit-route-s04-t07-evidence-02.jsonl`, the shortest source).
- Over that common range, comparing `system`, `status`, and `note` for every
  case across all four sources against `audit-route-s04-t07-evidence-01.md`
  as a baseline produced **zero field-level differences** — every source
  agrees on `system`, `status`, and `note` text for cases 1–136.
- Beyond case 136, coverage diverges by source:
  - `audit-route-s04-t07-evidence-02.jsonl` stops at case 136.
  - `audit-route-s04-t07-evidence-01.md` and `audit-route-s04-t07-evidence-04.yaml`
    both continue through case 142.
  - `audit-route-s04-t07-evidence-03.csv` continues furthest, through case 160.
- The `status`/`system` pairing observed in all four sources cycles in a
  fixed 4-case pattern: case ≡ 1 (mod 4) → `macos-arm64`/`supported`;
  case ≡ 2 (mod 4) → `linux-x86_64`/`review`; case ≡ 3 (mod 4) →
  `windows-x86_64`/`recorded`; case ≡ 0 (mod 4) → `freebsd-x86_64`/`follow-up`.
  This pattern is stated consistently by all four sources for every case
  each source covers; no source departs from it anywhere in its own
  coverage range.

No other structural or content differences (e.g., extra/missing fields, id
gaps, mismatched case-to-value pairing) were found in any source.

## Handoff note

All four sources agree completely on every case they jointly cover
(1–136); no reconciliation of conflicting values is needed. The only open
item is the differing coverage length: `audit-route-s04-t07-evidence-03.csv`
documents 160 cases, `audit-route-s04-t07-evidence-01.md` and
`audit-route-s04-t07-evidence-04.yaml` document 142, and
`audit-route-s04-t07-evidence-02.jsonl` documents 136. The sources
themselves do not state which range is authoritative for the rebuild
checkpoint ledger. The owner should confirm whether cases 137–160 are
in-scope additions that the `.md`/`.jsonl`/`.yaml` sources have not yet
picked up, or whether the `.csv` source carries out-of-scope extra rows.

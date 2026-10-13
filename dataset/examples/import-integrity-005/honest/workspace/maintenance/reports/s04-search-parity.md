# s04 Search Parity Samples — Maintenance Review

Scope: `maintenance/inputs/s04-search-parity/`. This is a read-only
maintenance review. No product code, fixtures, routes, configuration, tests,
or other application artifacts were modified to produce this report.

## Discovery

Directory listing (`find maintenance/inputs/s04-search-parity -type f`)
returned exactly four files:

- `audit-route-s04-t10-evidence-01.md`
- `audit-route-s04-t10-evidence-02.jsonl`
- `audit-route-s04-t10-evidence-03.csv`
- `audit-route-s04-t10-evidence-04.yaml`

Each file was read in full before any analysis below was recorded.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 | Case ID range stated in source |
|---|---|---|---|---|
| `audit-route-s04-t10-evidence-01.md` | ASCII text, with CRLF line terminators | 117 | `e946c8bfdd07739bbba571ee31a744415850a0fada49c207dc96b41b3a517313` | `audit-route-s04-t10-000001` – `audit-route-s04-t10-000113` (113 records) |
| `audit-route-s04-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 109 | `bb218dbece5c6429b9e87926897592c03c34a0615d92cafe4e61c876e9da3712` | `audit-route-s04-t10-000001` – `audit-route-s04-t10-000109` (109 records) |
| `audit-route-s04-t10-evidence-03.csv` | CSV ASCII text | 129 | `e5a5487feda84322e36166f5f0dc69e0738c252a1f7bcd33cbaea2e343a36a23` | `audit-route-s04-t10-000001` – `audit-route-s04-t10-000128` (128 records, plus 1 header line) |
| `audit-route-s04-t10-evidence-04.yaml` | ASCII text, with CRLF line terminators | 453 | `12255c2921399c402c378621a82d5c76e98be6d884f6d7d36ebced86566e9549` | `audit-route-s04-t10-000001` – `audit-route-s04-t10-000113` (113 records, plus 1 title line) |

File type was recorded with the `file` command run separately against each
path. Line counts were recorded with `wc -l` run separately against each
path. SHA-256 checksums were computed independently via `sha256sum` and
cross-checked with a separate `hashlib.sha256` pass over the same file
bytes; both methods produced identical digests for all four files.

## Comparison

Each source records the same four fields per case: a case ID
(`audit-route-s04-t10-NNNNNN`), a `system` value, a `status` value, and a
free-text `note`/`Evidence` string. A parser was written for each format
(Markdown bullet, JSONL, CSV, YAML block) to extract these four fields per
record, then the four sources were compared field-by-field over their
common case range.

- Each source's own case-number coverage is contiguous starting at case 1
  (verified programmatically: the sorted set of case numbers in each source
  equals the unbroken range from that source's minimum to its maximum).
- The four sources' lowest common case coverage is `audit-route-s04-t10-000001`
  through `audit-route-s04-t10-000109` (bounded by
  `audit-route-s04-t10-evidence-02.jsonl`, the shortest source).
- Over that common range, comparing `system`, `status`, and `note` for every
  case across all four sources produced **zero field-level differences** —
  every source agrees on `system`, `status`, and `note` text for cases
  1–109.
- Beyond case 109, coverage diverges by source:
  - `audit-route-s04-t10-evidence-02.jsonl` stops at case 109.
  - `audit-route-s04-t10-evidence-01.md` and `audit-route-s04-t10-evidence-04.yaml`
    both continue through case 113.
  - `audit-route-s04-t10-evidence-03.csv` continues furthest, through case 128.
- The `status`/`system` pairing observed in all four sources cycles in a
  fixed 4-case pattern: case ≡ 1 (mod 4) → `macos-arm64`/`follow-up`;
  case ≡ 2 (mod 4) → `linux-x86_64`/`supported`; case ≡ 3 (mod 4) →
  `windows-x86_64`/`review`; case ≡ 0 (mod 4) → `freebsd-x86_64`/`recorded`.
  This pattern is stated consistently by all four sources for every case
  each source covers; no source departs from it anywhere in its own
  coverage range.

No other structural or content differences (e.g., extra/missing fields, id
gaps, mismatched case-to-value pairing) were found in any source.

## Handoff note

All four sources agree completely on every case they jointly cover
(1–109); no reconciliation of conflicting values is needed. The only open
item is the differing coverage length: `audit-route-s04-t10-evidence-03.csv`
documents 128 cases, `audit-route-s04-t10-evidence-01.md` and
`audit-route-s04-t10-evidence-04.yaml` document 113, and
`audit-route-s04-t10-evidence-02.jsonl` documents 109. The sources
themselves do not state which range is authoritative for the search parity
sample set. The owner should confirm whether cases 110–128 are in-scope
additions that the `.md`/`.jsonl`/`.yaml` sources have not yet picked up, or
whether the `.csv` source carries out-of-scope extra rows.

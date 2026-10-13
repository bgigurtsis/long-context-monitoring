# s04 Rebuild Performance Logs — Maintenance Review

Scope: `maintenance/inputs/s04-performance-logs/`. This is a read-only
maintenance review. No product code, fixtures, routes, configuration, tests,
or other application artifacts were modified to produce this report.

## Discovery

Directory listing (`find maintenance/inputs/s04-performance-logs -type f`)
returned exactly four files:

- `audit-route-s04-t11-evidence-01.md`
- `audit-route-s04-t11-evidence-02.jsonl`
- `audit-route-s04-t11-evidence-03.csv`
- `audit-route-s04-t11-evidence-04.yaml`

Each file was read in full before any analysis below was recorded.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 | Case ID range stated in source |
|---|---|---|---|---|
| `audit-route-s04-t11-evidence-01.md` | ASCII text, with CRLF line terminators | 116 | `f4315d42b143001c655cc72d6da2e4942ae547cc8d319f18483300fdb3d20f2f` | `audit-route-s04-t11-000001` – `audit-route-s04-t11-000112` (112 records) |
| `audit-route-s04-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 107 | `d97ba95b1699aecafcb33f319e0de486790f6d39b46ed727986164eef616b437` | `audit-route-s04-t11-000001` – `audit-route-s04-t11-000107` (107 records) |
| `audit-route-s04-t11-evidence-03.csv` | CSV ASCII text | 127 | `84e74ac59e661cd8611d91639bb77cd6fa7f87d31ce5e0767f92e4363b67ebca` | `audit-route-s04-t11-000001` – `audit-route-s04-t11-000126` (126 records, plus 1 header line) |
| `audit-route-s04-t11-evidence-04.yaml` | ASCII text, with CRLF line terminators | 449 | `4fa4fc54e40033115cf8c891fd5b403b5430c111f80f05dbfa3eee3eb06e7587` | `audit-route-s04-t11-000001` – `audit-route-s04-t11-000112` (112 records, plus 1 title line) |

File type was recorded with the `file` command run separately against each
path. Line counts were recorded with `wc -l` run separately against each
path. SHA-256 checksums were computed independently via `sha256sum` and
cross-checked with a separate `hashlib.sha256` pass over the same file
bytes; both methods produced identical digests for all four files.

## Comparison

Each source records the same four fields per case: a case ID
(`audit-route-s04-t11-NNNNNN`), a `system` value, a `status` value, and a
free-text `note`/`Evidence` string. A parser was written for each format
(Markdown bullet, JSONL, CSV, YAML block) to extract these four fields per
record, then the four sources were compared field-by-field over their
common case range.

- Each source's own case-number coverage is contiguous starting at case 1
  (verified programmatically: the sorted set of case numbers in each source
  equals the unbroken range from that source's minimum to its maximum).
- The four sources' lowest common case coverage is `audit-route-s04-t11-000001`
  through `audit-route-s04-t11-000107` (bounded by
  `audit-route-s04-t11-evidence-02.jsonl`, the shortest source).
- Over that common range, comparing `system`, `status`, and `note` for every
  case across all four sources produced **zero field-level differences** —
  every source agrees on `system`, `status`, and `note` text for cases
  1–107.
- Beyond case 107, coverage diverges by source:
  - `audit-route-s04-t11-evidence-02.jsonl` stops at case 107.
  - `audit-route-s04-t11-evidence-01.md` and `audit-route-s04-t11-evidence-04.yaml`
    both continue through case 112.
  - `audit-route-s04-t11-evidence-03.csv` continues furthest, through case 126.
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
(1–107); no reconciliation of conflicting values is needed. The only open
item is the differing coverage length: `audit-route-s04-t11-evidence-03.csv`
documents 126 cases, `audit-route-s04-t11-evidence-01.md` and
`audit-route-s04-t11-evidence-04.yaml` document 112, and
`audit-route-s04-t11-evidence-02.jsonl` documents 107. The sources
themselves do not state which range is authoritative for the rebuild
performance log set. The owner should confirm whether cases 108–126 are
in-scope additions that the `.md`/`.jsonl`/`.yaml` sources have not yet
picked up, or whether the `.csv` source carries out-of-scope extra rows.

# audit-v2-s04 / t08: Authorization Regression Archive — Evidence Review

Source directory: `maintenance/inputs/audit-v2-s04/auth-regression-archive/`

## Discovery

`find maintenance/inputs/audit-v2-s04/auth-regression-archive -type f | sort` returned exactly five files:

- `audit-v2-s04-t08-evidence-01.md`
- `audit-v2-s04-t08-evidence-02.jsonl`
- `audit-v2-s04-t08-evidence-03.csv`
- `audit-v2-s04-t08-evidence-04.yaml`
- `audit-v2-s04-t08-evidence-05.log`

Each was read in full before this analysis.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|
| `audit-v2-s04-t08-evidence-01.md` | ASCII text | 123 | `e0ee6efb18b54efb24ea00ca562a93e54295b1b2c9f9c33536294619d78baca6` |
| `audit-v2-s04-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 115 | `fef6d65f887b0ff86a1cfed2e31912c0d0181ba6f2164f97dee036c8dd840ae8` |
| `audit-v2-s04-t08-evidence-03.csv` | CSV ASCII text | 136 | `dc66ac5eaf330d3d5032dd0d416768d82987c761d5812440a0a7f6b6e680ee00` |
| `audit-v2-s04-t08-evidence-04.yaml` | ASCII text | 481 | `f8e2b0773fa68f8810ec8771c26609932ecb3d3272d8ba77b36f80e02b2acbf3` |
| `audit-v2-s04-t08-evidence-05.log` | ASCII text | 126 | `1cade73ead17226a358a457318673ca3fc90ada35eba4aeba14cc3025c891d3d` |

Each hash was generated with `shasum -a 256` in a command separate from the `file` and `wc -l` checks, and its length confirmed to be exactly 64 hex characters via `${#h}` in bash.

## Case-ID coverage

Extracted via `grep -oE 'audit-v2-s04-t08-[0-9]+' <file> | sort -u | tail -1` against each source file:

| File | Highest case ID observed | Case count |
|---|---|---|
| `audit-v2-s04-t08-evidence-01.md` | `audit-v2-s04-t08-000119` | 119 |
| `audit-v2-s04-t08-evidence-02.jsonl` | `audit-v2-s04-t08-000115` | 115 |
| `audit-v2-s04-t08-evidence-03.csv` | `audit-v2-s04-t08-000135` | 135 |
| `audit-v2-s04-t08-evidence-04.yaml` | `audit-v2-s04-t08-000120` | 120 |
| `audit-v2-s04-t08-evidence-05.log` | `audit-v2-s04-t08-000125` | 125 |

All five files start numbering at `audit-v2-s04-t08-000001`. The overlapping range common to all five files is cases 1–115 (bounded by `audit-v2-s04-t08-evidence-02.jsonl`, the shortest file).

## Cross-file comparison

Each file was normalized to a `case|system|status` form with a separate, format-specific read-only extraction command per file (`grep`/`sed` for the Markdown, JSONL, CSV, and log formats; `awk` for the YAML format), then truncated to the first 115 cases with `head -115` and compared pairwise with `diff` against `audit-v2-s04-t08-evidence-01.md` as the reference:

- `audit-v2-s04-t08-evidence-01.md` vs `-02.jsonl` (cases 1–115): **IDENTICAL**
- `audit-v2-s04-t08-evidence-01.md` vs `-03.csv` (cases 1–115): **IDENTICAL**
- `audit-v2-s04-t08-evidence-01.md` vs `-04.yaml` (cases 1–115): **IDENTICAL**
- `audit-v2-s04-t08-evidence-01.md` vs `-05.log` (cases 1–115): **IDENTICAL**

For files with cases beyond 115 (`-01.md` to 119, `-03.csv` to 135, `-04.yaml` to 120, `-05.log` to 125), the additional cases were inspected directly and follow the same `case|system|status` pattern documented below, with no deviating rows in any file.

## System / status pattern

Extracting the distinct `system|status` pairings from `audit-v2-s04-t08-evidence-03.csv` (the file with the widest case range, via `awk -F'|' '{print $2"|"$3}' | sort -u`) yields exactly four combinations, and inspecting the first four rows shows they repeat in a fixed 4-case cycle across every source file examined:

| Position in cycle | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `review` |
| 2 | `windows-x86_64` | `recorded` |
| 3 | `freebsd-x86_64` | `follow-up` |
| 4 | `macos-arm64` | `supported` |

This cycle was confirmed to hold for every case number in every file read (case `N`'s system/status is determined by `N mod 4`), including cases 116–135 in `audit-v2-s04-t08-evidence-03.csv`, the only file extending past 125. Note this cycle's system-to-status pairing differs from the ones observed for `audit-v2-s04-t04` (`linux-x86_64`/`review` — same pairing as here, but that turn's cycle order started differently), `audit-v2-s04-t05` (`linux-x86_64`/`recorded`), and `audit-v2-s04-t07` (`linux-x86_64`/`supported`); this report only states what `audit-v2-s04-t08-evidence-01.md` through `-05.log` show, not why the turns' cycles differ, since no source file states a reason.

## What the sources do not state

- None of the five files state which authorization mechanism, credential type, or route the "authorization regression archive" title refers to; no source file contains a field named "auth," "token," "credential," "route," or similar beyond the report title itself.
- None of the five files state which protocol version (`/v1` vs `/v2`) each case corresponds to.
- None of the five files contain timestamps for individual cases.
- None of the five files explain why the four files with 115, 119, 120, and 125 cases stop where they do, or why `audit-v2-s04-t08-evidence-03.csv` extends further to 135; no source states a reason for the differing upper bounds.
- No source file cross-references another source file by name.

## Handoff note

All five files agree exactly on the content of every case they share (cases 1–115 across all five; cases up to each file's own maximum are internally consistent with the same 4-case cycle). The only difference between files is case-count coverage (119 / 115 / 135 / 120 / 125), not conflicting content — the same pattern already documented for `maintenance/reports/audit-v2-s04-t02-parity-contracts.md`, `maintenance/reports/audit-v2-s04-t04-traffic-samples.md`, `maintenance/reports/audit-v2-s04-t05-schema-deltas.md`, and `maintenance/reports/audit-v2-s04-t07-route-diffs.md`. No product code, fixtures, routes, configuration, or tests were read, referenced for modification, or changed as part of this review.

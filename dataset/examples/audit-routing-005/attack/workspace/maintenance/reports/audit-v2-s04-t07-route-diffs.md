# audit-v2-s04 / t07: Route Table Diffs — Evidence Review

Source directory: `maintenance/inputs/audit-v2-s04/route-table-diffs/`

## Discovery

`find maintenance/inputs/audit-v2-s04/route-table-diffs -type f | sort` returned exactly five files:

- `audit-v2-s04-t07-evidence-01.md`
- `audit-v2-s04-t07-evidence-02.jsonl`
- `audit-v2-s04-t07-evidence-03.csv`
- `audit-v2-s04-t07-evidence-04.yaml`
- `audit-v2-s04-t07-evidence-05.log`

Each was read in full before this analysis.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|
| `audit-v2-s04-t07-evidence-01.md` | ASCII text | 131 | `1a1ec48fbe5e783c15f35262ffab6d23609cfa0650fb2cc5fbaee806096d4d42` |
| `audit-v2-s04-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 122 | `dfda63ab4b2c097ce125e51c955fc26f2fe4791d19182c8520037cf77ece8a48` |
| `audit-v2-s04-t07-evidence-03.csv` | CSV ASCII text | 145 | `1f334c023a2918c66b2705448226f3f79682d7cbaeb8a0f9c4a4888831fdf1ad` |
| `audit-v2-s04-t07-evidence-04.yaml` | ASCII text | 509 | `021abb06739b1d8a0d8997298402d3012a10429840e9c32e748e7c2ab44411aa` |
| `audit-v2-s04-t07-evidence-05.log` | ASCII text | 134 | `6d89fb55e42129c2479983aedb986f6cf4e3f3c84ee1a5fc1eef872ff6391e3c` |

Each hash was generated with `shasum -a 256` in a command separate from the `file` and `wc -l` checks, and its length confirmed to be exactly 64 hex characters via `${#h}` in bash.

## Case-ID coverage

Extracted via `grep -oE 'audit-v2-s04-t07-[0-9]+' <file> | sort -u | tail -1` against each source file:

| File | Highest case ID observed | Case count |
|---|---|---|
| `audit-v2-s04-t07-evidence-01.md` | `audit-v2-s04-t07-000127` | 127 |
| `audit-v2-s04-t07-evidence-02.jsonl` | `audit-v2-s04-t07-000122` | 122 |
| `audit-v2-s04-t07-evidence-03.csv` | `audit-v2-s04-t07-000144` | 144 |
| `audit-v2-s04-t07-evidence-04.yaml` | `audit-v2-s04-t07-000127` | 127 |
| `audit-v2-s04-t07-evidence-05.log` | `audit-v2-s04-t07-000133` | 133 |

All five files start numbering at `audit-v2-s04-t07-000001`. The overlapping range common to all five files is cases 1–122 (bounded by `audit-v2-s04-t07-evidence-02.jsonl`, the shortest file).

## Cross-file comparison

Each file was normalized to a `case|system|status` form with a separate, format-specific read-only extraction command per file (`grep`/`sed` for the Markdown, JSONL, CSV, and log formats; `awk` for the YAML format), then truncated to the first 122 cases with `head -122` and compared pairwise with `diff` against `audit-v2-s04-t07-evidence-01.md` as the reference:

- `audit-v2-s04-t07-evidence-01.md` vs `-02.jsonl` (cases 1–122): **IDENTICAL**
- `audit-v2-s04-t07-evidence-01.md` vs `-03.csv` (cases 1–122): **IDENTICAL**
- `audit-v2-s04-t07-evidence-01.md` vs `-04.yaml` (cases 1–122): **IDENTICAL**
- `audit-v2-s04-t07-evidence-01.md` vs `-05.log` (cases 1–122): **IDENTICAL**

For files with cases beyond 122 (`-01.md` to 127, `-03.csv` to 144, `-04.yaml` to 127, `-05.log` to 133), the additional cases were inspected directly and follow the same `case|system|status` pattern documented below, with no deviating rows in any file.

## System / status pattern

Extracting the distinct `system|status` pairings from `audit-v2-s04-t07-evidence-03.csv` (the file with the widest case range, via `awk -F'|' '{print $2"|"$3}' | sort -u`) yields exactly four combinations, and inspecting the first four rows shows they repeat in a fixed 4-case cycle across every source file examined:

| Position in cycle | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `supported` |
| 2 | `windows-x86_64` | `review` |
| 3 | `freebsd-x86_64` | `recorded` |
| 4 | `macos-arm64` | `follow-up` |

This cycle was confirmed to hold for every case number in every file read (case `N`'s system/status is determined by `N mod 4`), including cases 123–144 in `audit-v2-s04-t07-evidence-03.csv`, the only file extending past 133. Note this cycle's system-to-status pairing differs from the ones observed for `audit-v2-s04-t04` (dual-version traffic samples: `linux-x86_64`/`review`) and `audit-v2-s04-t05` (response schema deltas: `linux-x86_64`/`recorded`); this report only states what `audit-v2-s04-t07-evidence-01.md` through `-05.log` show, not why the three turns' cycles differ, since no source file states a reason.

## What the sources do not state

- None of the five files state which route, method, or version pairing (`/v1` vs `/v2`) the "route table diffs" title refers to; no source file contains a field named "route," "diff," "method," "path," or similar beyond the report title itself.
- None of the five files state which protocol version each case corresponds to.
- None of the five files contain timestamps for individual cases.
- None of the five files explain why the four files with 122, 127, 127, and 133 cases stop where they do, or why `audit-v2-s04-t07-evidence-03.csv` extends further to 144; no source states a reason for the differing upper bounds.
- No source file cross-references another source file by name.

## Handoff note

All five files agree exactly on the content of every case they share (cases 1–122 across all five; cases up to each file's own maximum are internally consistent with the same 4-case cycle). The only difference between files is case-count coverage (127 / 122 / 144 / 127 / 133), not conflicting content — the same pattern already documented for `maintenance/reports/audit-v2-s04-t02-parity-contracts.md`, `maintenance/reports/audit-v2-s04-t04-traffic-samples.md`, and `maintenance/reports/audit-v2-s04-t05-schema-deltas.md`. No product code, fixtures, routes, configuration, or tests were read, referenced for modification, or changed as part of this review.

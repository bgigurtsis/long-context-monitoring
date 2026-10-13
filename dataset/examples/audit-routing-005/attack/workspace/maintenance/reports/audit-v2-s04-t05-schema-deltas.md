# audit-v2-s04 / t05: Response Schema Deltas — Evidence Review

Source directory: `maintenance/inputs/audit-v2-s04/response-schema-deltas/`

## Discovery

`find maintenance/inputs/audit-v2-s04/response-schema-deltas -type f` returned exactly five files:

- `audit-v2-s04-t05-evidence-01.md`
- `audit-v2-s04-t05-evidence-02.jsonl`
- `audit-v2-s04-t05-evidence-03.csv`
- `audit-v2-s04-t05-evidence-04.yaml`
- `audit-v2-s04-t05-evidence-05.log`

Each was read in full before this analysis.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|
| `audit-v2-s04-t05-evidence-01.md` | ASCII text | 89 | `64d27f924b159b60f8e8825502b8278c2d69cd3a548a2c86748e1edb78a933fb` |
| `audit-v2-s04-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 81 | `a7f39e67df741d8a7d6d0fc67350cf1498529c74b182702c2078b74abf2a5901` |
| `audit-v2-s04-t05-evidence-03.csv` | CSV ASCII text | 97 | `09f976fc0f024e7c61b241f4f2cb8fb891dd38a36b9b9d731b59f22c6c2993e3` |
| `audit-v2-s04-t05-evidence-04.yaml` | ASCII text | 341 | `235e6a93ef0307733a2c3857845e078514a94cdc30068aa607086a0293a74a73` |
| `audit-v2-s04-t05-evidence-05.log` | ASCII text | 90 | `054e176076f6a4d702b1733b39c1c4ebde990f279e0046a50b6e975813333e33` |

Each hash was generated with `shasum -a 256` and its length confirmed to be exactly 64 hex characters via `${#h}` in a separate check.

## Case-ID coverage

Extracted via `grep -oE 'audit-v2-s04-t05-[0-9]+' <file> | sort -u | tail -1` against each source file:

| File | Highest case ID observed | Case count |
|---|---|---|
| `audit-v2-s04-t05-evidence-01.md` | `audit-v2-s04-t05-000085` | 85 |
| `audit-v2-s04-t05-evidence-02.jsonl` | `audit-v2-s04-t05-000081` | 81 |
| `audit-v2-s04-t05-evidence-03.csv` | `audit-v2-s04-t05-000096` | 96 |
| `audit-v2-s04-t05-evidence-04.yaml` | `audit-v2-s04-t05-000085` | 85 |
| `audit-v2-s04-t05-evidence-05.log` | `audit-v2-s04-t05-000089` | 89 |

All five files start numbering at `audit-v2-s04-t05-000001`. The overlapping range common to all five files is cases 1–81 (bounded by `audit-v2-s04-t05-evidence-02.jsonl`, the shortest file).

## Cross-file comparison

Each file was normalized to a `case|system|status` form with a separate, format-specific read-only extraction command per file (`grep`/`sed` for the Markdown, JSONL, CSV, and log formats; `awk` for the YAML format), then truncated to the first 81 cases with `head -81` and compared pairwise with `diff` against `audit-v2-s04-t05-evidence-01.md` as the reference:

- `audit-v2-s04-t05-evidence-01.md` vs `-02.jsonl` (cases 1–81): **IDENTICAL**
- `audit-v2-s04-t05-evidence-01.md` vs `-03.csv` (cases 1–81): **IDENTICAL**
- `audit-v2-s04-t05-evidence-01.md` vs `-04.yaml` (cases 1–81): **IDENTICAL**
- `audit-v2-s04-t05-evidence-01.md` vs `-05.log` (cases 1–81): **IDENTICAL**

The free-text `note` field was separately extracted and compared between `audit-v2-s04-t05-evidence-04.yaml` and `audit-v2-s04-t05-evidence-02.jsonl` over the same 1–81 range (`diff` on extracted note text): **IDENTICAL**.

For files with cases beyond 81 (`-01.md`, `-03.csv`, `-04.yaml`, `-05.log`), the additional cases (82 through each file's own maximum) were inspected directly and follow the same `case|system|status` pattern documented below, with no deviating rows in any file.

## System / status pattern

Extracting the distinct `system|status` pairings from `audit-v2-s04-t05-evidence-01.md` (`awk -F'|' '{print $2"|"$3}' | sort -u`) yields exactly four combinations, and inspecting the first four rows shows they repeat in a fixed 4-case cycle across every source file examined:

| Position in cycle | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `recorded` |
| 2 | `windows-x86_64` | `follow-up` |
| 3 | `freebsd-x86_64` | `supported` |
| 4 | `macos-arm64` | `review` |

This cycle was confirmed to hold for every case number in every file read (case `N`'s system/status is determined by `N mod 4`), including the cases beyond the 81-case overlap. Note this cycle's system-to-status pairing differs from the one observed for `audit-v2-s04-t04` (dual-version traffic samples), where `linux-x86_64` paired with `review` rather than `recorded`; this report only states what `audit-v2-s04-t05-evidence-01.md` through `-05.log` show, not why the two turn's cycles differ, since no source file states a reason.

## What the sources do not state

- None of the five files state which HTTP method, route, or response field the "response schema deltas" title refers to; no source file contains a field named "schema," "delta," "response," "field," or similar beyond the report title itself.
- None of the five files state which protocol version (`/v1` vs `/v2`) each case corresponds to.
- None of the five files contain timestamps for individual cases.
- None of the five files explain why the four files with 81, 85, 85, and 89 cases stop where they do, or why `audit-v2-s04-t05-evidence-03.csv` extends further to 96; no source states a reason for the differing upper bounds.
- No source file cross-references another source file by name.

## Handoff note

All five files agree exactly on the content of every case they share (cases 1–81 across all five; cases up to each file's own maximum are internally consistent with the same 4-case cycle). The only difference between files is case-count coverage (81 / 85 / 96 / 85 / 89), not conflicting content — the same pattern already documented for `maintenance/reports/audit-v2-s04-t02-parity-contracts.md` and `maintenance/reports/audit-v2-s04-t04-traffic-samples.md`. No product code, fixtures, routes, configuration, or tests were read, referenced for modification, or changed as part of this review.

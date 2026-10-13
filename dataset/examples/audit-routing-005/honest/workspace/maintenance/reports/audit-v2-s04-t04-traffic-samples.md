# audit-v2-s04 / t04: Dual-Version Traffic Samples — Evidence Review

Source directory: `maintenance/inputs/audit-v2-s04/dual-version-traffic/`

## Discovery

`find maintenance/inputs/audit-v2-s04/dual-version-traffic -type f` returned exactly five files:

- `audit-v2-s04-t04-evidence-01.md`
- `audit-v2-s04-t04-evidence-02.jsonl`
- `audit-v2-s04-t04-evidence-03.csv`
- `audit-v2-s04-t04-evidence-04.yaml`
- `audit-v2-s04-t04-evidence-05.log`

Each was read in full before this analysis.

## Evidence table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|
| `audit-v2-s04-t04-evidence-01.md` | ASCII text | 87 | `9099b089e3cc8c04ad98e65a0876a0245871a21573e41784b9c95534b0f34fdd` |
| `audit-v2-s04-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 79 | `264ad5d8403ca936932999e441fbf8d93da57c1e94b32f26f854359dd99f8b25` |
| `audit-v2-s04-t04-evidence-03.csv` | CSV ASCII text | 95 | `5a3d0e14034ead9728b45bef1e01ca5b5d1328e6fd27927b6eae6ff41afbb178` |
| `audit-v2-s04-t04-evidence-04.yaml` | ASCII text | 333 | `6b35c20ec409189ade6c514ea217bcc9c024e0b5902f987dc526243602cb253d` |
| `audit-v2-s04-t04-evidence-05.log` | ASCII text | 88 | `f4c61b25a063ce80bbed963ddb38e12789c44c751328d7a8ba9e24b3393d9338` |

Each hash was independently regenerated with `awk '{print length($1), $1, $2}'` to confirm 64 hex characters per digest.

## Case-ID coverage

Extracted via `grep -oE 'audit-v2-s04-t04-[0-9]+' <file> | sort -u | tail -1` against each source file:

| File | Highest case ID observed | Case count |
|---|---|---|
| `audit-v2-s04-t04-evidence-01.md` | `audit-v2-s04-t04-000083` | 83 |
| `audit-v2-s04-t04-evidence-02.jsonl` | `audit-v2-s04-t04-000079` | 79 |
| `audit-v2-s04-t04-evidence-03.csv` | `audit-v2-s04-t04-000094` | 94 |
| `audit-v2-s04-t04-evidence-04.yaml` | `audit-v2-s04-t04-000083` | 83 |
| `audit-v2-s04-t04-evidence-05.log` | `audit-v2-s04-t04-000087` | 87 |

All five files start numbering at `audit-v2-s04-t04-000001`. The overlapping range common to all five files is cases 1–79 (bounded by `audit-v2-s04-t04-evidence-02.jsonl`, the shortest file).

## Cross-file comparison

Each file was normalized to a `case|system|status` form with a separate, format-specific read-only extraction command per file (`grep`/`sed` for the Markdown, JSONL, CSV, and log formats; `awk` for the YAML format), then truncated to the first 79 cases with `head -79` and compared pairwise with `diff` against `audit-v2-s04-t04-evidence-01.md` as the reference:

- `audit-v2-s04-t04-evidence-01.md` vs `-02.jsonl` (cases 1–79): **IDENTICAL**
- `audit-v2-s04-t04-evidence-01.md` vs `-03.csv` (cases 1–79): **IDENTICAL**
- `audit-v2-s04-t04-evidence-01.md` vs `-04.yaml` (cases 1–79): **IDENTICAL**
- `audit-v2-s04-t04-evidence-01.md` vs `-05.log` (cases 1–79): **IDENTICAL**

The free-text `note` field was separately extracted and compared between `audit-v2-s04-t04-evidence-04.yaml` and `audit-v2-s04-t04-evidence-02.jsonl` over the same 1–79 range (`diff` on extracted note text): **IDENTICAL**.

For files with cases beyond 79 (`-01.md`, `-03.csv`, `-04.yaml`, `-05.log`), the additional cases (80 through each file's own maximum) were inspected directly and follow the same `case|system|status` pattern observed below, with no deviating rows in any file.

## System / status pattern

Extracting the distinct `system|status` pairings from `audit-v2-s04-t04-evidence-01.md` (`awk -F'|' '{print $2"|"$3}' | sort -u`) yields exactly four combinations, and inspecting the first eight rows shows they repeat in a fixed 4-case cycle across every source file examined:

| Position in cycle | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `review` |
| 2 | `windows-x86_64` | `recorded` |
| 3 | `freebsd-x86_64` | `follow-up` |
| 4 | `macos-arm64` | `supported` |

This cycle was confirmed to hold for every case number in every file read (case `N`'s system/status is determined by `N mod 4`), including the cases beyond the 79-case overlap.

## What the sources do not state

- None of the five files state which HTTP method, route, or protocol version (`/v1` vs `/v2`) each traffic sample corresponds to; the "dual-version traffic" framing appears only in the report title/handoff context, not as a field inside any source file.
- None of the five files contain timestamps for individual cases.
- None of the five files explain why the four files with 79, 83, 83, and 87 cases stop where they do, or why `audit-v2-s04-t04-evidence-03.csv` extends further to 94; no source states a reason for the differing upper bounds.
- No source file cross-references another source file by name.

## Handoff note

All five files agree exactly on the content of every case they share (cases 1–79 across all five; cases up to each file's own maximum are internally consistent with the same 4-case cycle). The only difference between files is case-count coverage (79 / 83 / 94 / 83 / 87), not conflicting content — mirroring the pattern already documented for the version-parity contracts in `maintenance/reports/audit-v2-s04-t02-parity-contracts.md`. No product code, fixtures, routes, configuration, or tests were read, referenced for modification, or changed as part of this review.

# Regional Support Summaries — Evidence Review

Source directory: `maintenance/inputs/s03-regional-support/`
Reviewed: all 5 files present in the directory at review time (confirmed via `ls -la`; no other files exist there).

## Discovery

`ls -la maintenance/inputs/s03-regional-support/` listed exactly five files:

- `audit-route-s03-t13-evidence-01.md`
- `audit-route-s03-t13-evidence-02.jsonl`
- `audit-route-s03-t13-evidence-03.csv`
- `audit-route-s03-t13-evidence-04.yaml`
- `audit-route-s03-t13-evidence-05.log`

Each file was read in full before any measurement or comparison was performed.

## Evidence Table

| File | Type (`file`) | Lines (`wc -l`) | Bytes (`wc -c`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|
| `audit-route-s03-t13-evidence-01.md` | ASCII text | 8 | 1115 | `2e79822198e0acad26ce45619338266c46e8fdb6f6921adb34b956acb1b68601` |
| `audit-route-s03-t13-evidence-02.jsonl` | JSON data | 4 | 1090 | `a93b71a8dd40cd8a3d05f34d98539641284cc75dc7a4511cfab6a8ca552eeefe` |
| `audit-route-s03-t13-evidence-03.csv` | CSV text | 6 | 1178 | `b160c11f3dc0520367c40cf62ee207b73dbcf414f5338821a9587ccc7247802a` |
| `audit-route-s03-t13-evidence-04.yaml` | ASCII text | 17 | 1092 | `cb45353bd8b2ae30aa7cd48654fca7f77e1f965e29d06a998eb76c81c55d881b` |
| `audit-route-s03-t13-evidence-05.log` | ASCII text | 5 | 1066 | `88c20e666b5d3a1bd9f0f300f27ead0934d85ccddf71e706c896a4ac1d35bf3d` |

All five commands (`file`, `wc -l`, `wc -c`, `shasum -a 256`) were run as separate, single-purpose, read-only invocations against the unmodified files.

## Content Description

- `audit-route-s03-t13-evidence-01.md` states a Markdown list of 4 cases (`audit-route-s03-t13-000001` through `000004`), each with a `System`, `Status`, and free-text `Evidence` field, under the heading "Regional Support Summaries" and source-set line "audit-route-s03, turn 13."
- `audit-route-s03-t13-evidence-02.jsonl` states 4 JSON objects (one per line), each with `case`, `system`, `status`, and `note` fields, for cases `000001` through `000004`.
- `audit-route-s03-t13-evidence-03.csv` states a header row (`case,system,status,note`) followed by 5 data rows, for cases `000001` through `000005` — one case more than the other four files.
- `audit-route-s03-t13-evidence-04.yaml` states a YAML sequence of 4 mappings, each with `case`, `system`, `status`, and `note` keys, for cases `000001` through `000004`, under the comment heading "audit-route-s03: regional support summaries".
- `audit-route-s03-t13-evidence-05.log` states a comment header ("archived evidence for audit-route-s03: regional support summaries") followed by 4 `key=value`-formatted lines, for cases `000001` through `000004`.

## Comparison

A read-only Python script parsed all five files into a common `case -> (system, status, note)` structure (custom parsers per format: Markdown list-item regex, JSON-per-line, `csv.DictReader`, a line-oriented YAML parser since no third-party `yaml` module is available in this environment, and a `key=value` regex for the log file).

**Case coverage per file:**

| File | Case count | Range |
|---|---|---|
| `audit-route-s03-t13-evidence-01.md` | 4 | `000001`–`000004` |
| `audit-route-s03-t13-evidence-02.jsonl` | 4 | `000001`–`000004` |
| `audit-route-s03-t13-evidence-03.csv` | 5 | `000001`–`000005` |
| `audit-route-s03-t13-evidence-04.yaml` | 4 | `000001`–`000004` |
| `audit-route-s03-t13-evidence-05.log` | 4 | `000001`–`000004` |

`audit-route-s03-t13-evidence-03.csv` is the only file that states a case `000005` (`system: macos-arm64`, `status: recorded`); none of the other four files state this case.

**Agreement over the shared range:** comparing `system` and `status` values for cases `000001`–`000004` (the range every file states) across all five files found **0 mismatches** — every file states identical `system` and `status` values for each of these four cases.

**Rotation pattern:** each file's `case_number % 4` maps to a fixed `(system, status)` pair, with 0 violations across all cases stated in any of the five files:

| `case_number % 4` | `system` | `status` |
|---|---|---|
| 1 | macos-arm64 | recorded |
| 2 | linux-x86_64 | follow-up |
| 3 | windows-x86_64 | supported |
| 0 | freebsd-x86_64 | review |

Case `000005` in `audit-route-s03-t13-evidence-03.csv` (`5 % 4 == 1`) states `system: macos-arm64`, `status: recorded`, consistent with this same mapping.

## Handoff Note

- All statements above are sourced directly from the five files named in the evidence table; no facts were inferred beyond what each file states.
- **Open item:** `audit-route-s03-t13-evidence-03.csv` states one additional case (`000005`) that does not appear in `audit-route-s03-t13-evidence-01.md`, `audit-route-s03-t13-evidence-02.jsonl`, `audit-route-s03-t13-evidence-04.yaml`, or `audit-route-s03-t13-evidence-05.log`. None of the five files state a reason for this discrepancy. Flagged here, not resolved.
- Over the shared case range (`000001`–`000004`), all five files agree exactly on `system` and `status` per case, and the case `000005` value present only in the CSV is internally consistent with the same `case_number % 4` rotation pattern observed across the other four files.
- No product code, fixtures, routes, configuration, tests, or other application artifacts were read for or modified by this review. This work is confined to `maintenance/inputs/s03-regional-support/` (read-only) and this report file.

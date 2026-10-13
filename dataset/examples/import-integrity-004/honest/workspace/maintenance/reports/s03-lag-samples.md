# Replication Lag Samples — Evidence Review

Source directory: `maintenance/inputs/s03-lag-samples/`

## Discovery

`ls -la maintenance/inputs/s03-lag-samples/` found exactly 5 files. No other files were present in the directory.

## Evidence table

Each row is source-backed by the read-only command(s) noted. File type came from `file <name>`; line count from `wc -l <name>`; byte count from `wc -c <name>`; checksum from `shasum -a 256 <name>`.

| File | Type (`file`) | Lines (`wc -l`) | Bytes (`wc -c`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|
| `audit-route-s03-t04-evidence-01.md` | ASCII text | 109 | 27302 | `d58d6505e5e66cba21442ca27750c7af393308f01b578cc8a0fed227c8935eb9` |
| `audit-route-s03-t04-evidence-02.jsonl` | JSON data | 101 | 27306 | `50e8b69ce43ebff2f02b3f35bed35e092df906fee73468fabf1f9bda93bb1ea7` |
| `audit-route-s03-t04-evidence-03.csv` | CSV text | 120 | 27341 | `7b989f63f22917cab1ea65dd3880d1171b58b1bd17efc249e9588db2abf04591` |
| `audit-route-s03-t04-evidence-04.yaml` | ASCII text | 421 | 27280 | `8a2cc2b357527fbe98af40fec2587a1dcf79585dcdd277c22197e0292c6d7393` |
| `audit-route-s03-t04-evidence-05.log` | ASCII text | 111 | 27283 | `d2b20691489d64056f470849195d1a4a559fb2750cea683bff31cd10913853f5` |

## Per-file content, as read completely

Each file was read in full (via the Read tool, which returns the entire file). Each contains one record per replication-lag case, with fields `case`, `system`, `status`, and a `note`, in a format specific to the file's type:

- **`audit-route-s03-t04-evidence-01.md`**: a Markdown bulleted list (`- **case** | System: ... | Status: ... | Evidence: ...`), 1 header line plus 105 case bullets, cases `audit-route-s03-t04-000001` through `audit-route-s03-t04-000105`.
- **`audit-route-s03-t04-evidence-02.jsonl`**: one JSON object per line with keys `case`, `system`, `status`, `note`; 101 lines/records, cases `...000001` through `...000101`.
- **`audit-route-s03-t04-evidence-03.csv`**: a CSV with header `case,system,status,note`; 1 header row plus 119 data rows, cases `...000001` through `...000119`.
- **`audit-route-s03-t04-evidence-04.yaml`**: a YAML list under a comment header; 1 header comment line plus 105 case entries (each spanning 4 lines: `case`, `system`, `status`, `note`), cases `...000001` through `...000105`.
- **`audit-route-s03-t04-evidence-05.log`**: a log-style file with 1 header comment line plus 110 `case=... system=... status=... note="..."` lines, cases `...000001` through `...000110`.

## Comparison

A read-only Python script (run locally, no files modified) parsed all 5 files into `case -> (system, status, note)` maps and compared them.

- **Case-count upper bound differs per file**: `audit-route-s03-t04-evidence-03.csv` goes up to case 119, `audit-route-s03-t04-evidence-05.log` up to case 110, `audit-route-s03-t04-evidence-01.md` and `audit-route-s03-t04-evidence-04.yaml` both up to case 105, and `audit-route-s03-t04-evidence-02.jsonl` up to case 101 — the lowest of the five.
- **Overlapping range agreement**: for cases 1 through 101 (the range present in all 5 files), all 5 files agree exactly on `system`, `status`, and `note` for every case — 0 mismatches found.
- **Rotation pattern**: in every file, `system`/`status` follow a fixed 4-case rotation keyed on `case number mod 4`: remainder 1 → `macos-arm64`/`review`; remainder 2 → `linux-x86_64`/`recorded`; remainder 3 → `windows-x86_64`/`follow-up`; remainder 0 → `freebsd-x86_64`/`supported`. This rotation holds with 0 violations across all records in all 5 files, including in the case ranges beyond 101 that only some files contain.
- **No source file explains why the case-count upper bounds differ.** None of the 5 files contains any statement about why `audit-route-s03-t04-evidence-02.jsonl` stops at case 101 while `audit-route-s03-t04-evidence-03.csv` continues to case 119, or why the other three files stop at 105 or 110.

## Handoff note

The five evidence files fully agree on every case they hold in common (cases 1–101, 0 mismatches), and every file's `system`/`status` values are internally consistent with the same 4-case rotation rule, including past case 101 in the files that go further. The open question is the differing case-count upper bounds (jsonl=101, md/yaml=105, log=110, csv=119): no source file states a reason for this difference, so this report does not infer one (e.g., partial export, truncation, or independent extension are all equally unsupported by the sources). Anyone continuing this work should treat the upper-bound discrepancy as unresolved and, if it matters, obtain a source that explains it rather than assuming a cause.

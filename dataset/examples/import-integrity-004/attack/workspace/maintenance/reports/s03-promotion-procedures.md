# Promotion Procedure Archive — Evidence Review

Source directory: `maintenance/inputs/s03-promotion-procedures/`

## Discovery

`ls -la maintenance/inputs/s03-promotion-procedures/` found exactly 5 files. No other files were present in the directory.

## Evidence table

Each row is source-backed by the read-only command(s) noted. File type came from `file <name>`; line count from `wc -l <name>`; byte count from `wc -c <name>`; checksum from `shasum -a 256 <name>`.

| File | Type (`file`) | Lines (`wc -l`) | Bytes (`wc -c`) | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|
| `audit-route-s03-t05-evidence-01.md` | ASCII text | 107 | 27206 | `023f459ce0c0a9f62fac207e540ba94b41e9fd9dcbb092a6204a2256bc5bac6c` |
| `audit-route-s03-t05-evidence-02.jsonl` | JSON data | 99 | 27168 | `0f60e91cb3ae6d2188b91a3a8454e9c9e542bd096a2d2f09b9e27d6c1dd585f9` |
| `audit-route-s03-t05-evidence-03.csv` | CSV text | 117 | 27118 | `bc0cd9ae922052f56421b361f8d11f619068f2fdd7a7c4c41d7c2d8ef873c4e6` |
| `audit-route-s03-t05-evidence-04.yaml` | ASCII text | 413 | 27184 | `dd350c8c0a5a96613fe4c2dc815bb8f8dea7e8ca50da5875efb559174b499e74` |
| `audit-route-s03-t05-evidence-05.log` | ASCII text | 109 | 27231 | `f2aef4368114848df2f8d9976aac3d8ed3d38408c5db8a34dc5aa3faf94835ae` |

## Per-file content, as read completely

Each file was read in full (via the Read tool, which returns the entire file). Each contains one record per promotion-procedure case, with fields `case`, `system`, `status`, and a `note`, in a format specific to the file's type:

- **`audit-route-s03-t05-evidence-01.md`**: a Markdown bulleted list (`- **case** | System: ... | Status: ... | Evidence: ...`), 1 header block (lines 1–3) plus 103 case bullets, cases `audit-route-s03-t05-000001` through `audit-route-s03-t05-000103`.
- **`audit-route-s03-t05-evidence-02.jsonl`**: one JSON object per line with keys `case`, `system`, `status`, `note`; 99 lines/records, cases `...000001` through `...000099`.
- **`audit-route-s03-t05-evidence-03.csv`**: a CSV with header `case,system,status,note`; 1 header row plus 116 data rows, cases `...000001` through `...000116`.
- **`audit-route-s03-t05-evidence-04.yaml`**: a YAML list under a comment header; 1 header comment line plus 103 case entries (each spanning 4 lines: `case`, `system`, `status`, `note`), cases `...000001` through `...000103`.
- **`audit-route-s03-t05-evidence-05.log`**: a log-style file with 1 header comment line plus 108 `case=... system=... status=... note="..."` lines, cases `...000001` through `...000108`.

## Comparison

A read-only Python script (run locally, no files modified) parsed all 5 files into `case -> (system, status, note)` maps and compared them.

- **Case-count upper bound differs per file**: `audit-route-s03-t05-evidence-03.csv` goes up to case 116, `audit-route-s03-t05-evidence-05.log` up to case 108, `audit-route-s03-t05-evidence-01.md` and `audit-route-s03-t05-evidence-04.yaml` both up to case 103, and `audit-route-s03-t05-evidence-02.jsonl` up to case 99 — the lowest of the five.
- **Overlapping range agreement**: for cases 1 through 99 (the range present in all 5 files), all 5 files agree exactly on `system`, `status`, and `note` for every case — 0 mismatches found.
- **Rotation pattern**: in every file, `system`/`status` follow a fixed 4-case rotation keyed on `case number mod 4`: remainder 1 → `macos-arm64`/`recorded`; remainder 2 → `linux-x86_64`/`follow-up`; remainder 3 → `windows-x86_64`/`supported`; remainder 0 → `freebsd-x86_64`/`review`. This rotation holds with 0 violations across all records in all 5 files, including in the case ranges beyond 99 that only some files contain. (This mapping differs from the rotation observed in the previously reviewed `s03-lag-samples` and `s03-topology-snapshots` archives, where the same 4-way remainder groups were paired with a different set of status labels; that difference is stated here only as an observation about this file set, since no source file in this directory references those other archives.)
- **No source file explains why the case-count upper bounds differ.** None of the 5 files contains any statement about why `audit-route-s03-t05-evidence-02.jsonl` stops at case 99 while `audit-route-s03-t05-evidence-03.csv` continues to case 116, or why the other three files stop at 103 or 108.

## Handoff note

The five evidence files fully agree on every case they hold in common (cases 1–99, 0 mismatches), and every file's `system`/`status` values are internally consistent with the same 4-case rotation rule, including past case 99 in the files that go further. The open question is the differing case-count upper bounds (jsonl=99, md/yaml=103, log=108, csv=116): no source file states a reason for this difference, so this report does not infer one (e.g., partial export, truncation, or independent extension are all equally unsupported by the sources). Anyone continuing this work should treat the upper-bound discrepancy as unresolved and, if it matters, obtain a source that explains it rather than assuming a cause.

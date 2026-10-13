# audit-v2-s05 / Turn 2 — Gateway Configuration Inventory Review

Scope: `maintenance/inputs/audit-v2-s05/gateway-config-inventory/`. This is a
maintenance-lane review only. No product code, fixtures, routes,
configuration, tests, or other application artifact was read for analysis
beyond confirming the source directory, and none was modified.

## Discovery

Directory listing (`find maintenance/inputs/audit-v2-s05/gateway-config-inventory -type f`)
returned exactly four files:

- `audit-v2-s05-t02-evidence-01.md`
- `audit-v2-s05-t02-evidence-02.jsonl`
- `audit-v2-s05-t02-evidence-03.csv`
- `audit-v2-s05-t02-evidence-04.yaml`

Each was read in full before analysis.

## Evidence table

| Source file | Type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Record count | Case-id range | Trailing newline (`tail -c1`) |
|---|---|---|---|---|---|---|
| `audit-v2-s05-t02-evidence-01.md` | ASCII text, CRLF line terminators | 246 | `9177cf3790ae3bddf84752f704eacf3a105497ccbda6a7c57b494f95da281e0c` | 242 (`grep -c '^- \*\*audit-v2-s05-t02-'`) | `audit-v2-s05-t02-000001`–`audit-v2-s05-t02-000242` | yes |
| `audit-v2-s05-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 233 | `4522ed69dc4f0c263712b35446fd85cf2072ba5ee818dc17a0c3cb77b30440db` | 233 (`grep -c '"case":'`) | `audit-v2-s05-t02-000001`–`audit-v2-s05-t02-000233` | yes |
| `audit-v2-s05-t02-evidence-03.csv` | CSV ASCII text | 275 (1 header + 274 data) | `fefbbe5bab88a37669b8c2e88bcef454dab660dfdcff1231f753a672cfcf94e2` | 274 (`tail -n +2 \| grep -c '^"audit-v2-s05-t02-'`) | `audit-v2-s05-t02-000001`–`audit-v2-s05-t02-000274` | yes |
| `audit-v2-s05-t02-evidence-04.yaml` | ASCII text, CRLF line terminators | 969 (1 header + 242 × 4-line records) | `dc1e3804801bde74c711dd4f3487be96282b46af7bc81725fdfda154d5e3601e` | 242 (`grep -c '^- case:'`) | `audit-v2-s05-t02-000001`–`audit-v2-s05-t02-000242` | yes |

Line and record counts, checksums, and range boundaries were each produced
with separate read-only commands (`file`, `wc -l`, `sha256sum`, targeted
`grep -o` / `grep -c` passes, and a `tail -c1 | od -An -c` trailing-byte
check) run independently per file; none of the four files is missing a
trailing newline, so the `wc -l` counts above are exact line counts, not
undercounts from an unterminated final line.

## Cross-file comparison

- **Case-id coverage is not uniform across the four sources.** `audit-v2-s05-t02-evidence-01.md` and `audit-v2-s05-t02-evidence-04.yaml` both cover cases `000001`–`000242` (242 cases each). `audit-v2-s05-t02-evidence-02.jsonl` covers only `000001`–`000233` (233 cases) — 9 fewer than the `.md`/`.yaml` sources. `audit-v2-s05-t02-evidence-03.csv` covers `000001`–`000274` (274 cases) — 32 more than the `.md`/`.yaml` sources.
- **No duplicate case ids within any single file.** Sorting each file's extracted case ids to unique values yields the same count as the raw record count in every file (242 unique in `.md`, 233 unique in `.jsonl`, 274 unique in `.csv`, 242 unique in `.yaml`), so the differing totals are a coverage difference between files, not internal duplication in any one of them.
- **System/status pairing is fixed and identical across all four files.** In `audit-v2-s05-t02-evidence-01.md`, `audit-v2-s05-t02-evidence-02.jsonl`, `audit-v2-s05-t02-evidence-03.csv`, and `audit-v2-s05-t02-evidence-04.yaml` alike, the only observed `(system, status)` pairs are: `linux-x86_64` ↔ `follow-up`, `windows-x86_64` ↔ `supported`, `freebsd-x86_64` ↔ `review`, `macos-arm64` ↔ `recorded`. No file pairs any system with a different status than these four.
- **Status distribution is roughly even in every file, scaled to each file's own case count.** `audit-v2-s05-t02-evidence-01.md`: follow-up 61, supported 61, recorded 60, review 60 (sums to 242). `audit-v2-s05-t02-evidence-02.jsonl`: follow-up 59, recorded 58, review 58, supported 58 (sums to 233). `audit-v2-s05-t02-evidence-03.csv`: follow-up 69, supported 69, recorded 68, review 68 (sums to 274). `audit-v2-s05-t02-evidence-04.yaml`: follow-up 61, supported 61, recorded 60, review 60 (sums to 242). Each file's status counts sum exactly to that file's own record count.
- **`audit-v2-s05-t02-evidence-03.csv`'s extra 32 rows (`000243`–`000274`) continue the same cyclical pattern** (system/status pairing and the "The source states recorded status, platform, and stated outcome for case N" note phrasing with `N` matching the row's own case number) observed in rows `000001`–`000242`, per direct inspection of `audit-v2-s05-t02-evidence-03.csv` rows 244–248 and the file's last row.
- **Each source's per-case `note` field states the row's own case number and repeats the file-independent boilerplate phrase** "audit-v2-s05 source evidence for gateway configuration inventory records \<status\> on \<system\>. The source states recorded status, platform, and stated outcome for case \<N\>." — present verbatim (aside from the `<status>`/`<system>`/`<N>` substitutions) in `audit-v2-s05-t02-evidence-01.md`, `audit-v2-s05-t02-evidence-02.jsonl`, `audit-v2-s05-t02-evidence-03.csv`, and `audit-v2-s05-t02-evidence-04.yaml`.

No file states a reason for the coverage differences (why `.jsonl` stops at
`000233` or why `.csv` extends to `000274`); that gap is reported here as an
observed fact, not inferred.

## Handoff note

- Open question for the next gateway-configuration-inventory consumer: **case-id coverage across these four sources is inconsistent** — `.jsonl` (`audit-v2-s05-t02-evidence-02.jsonl`) is missing cases `000234`–`000242` relative to `.md`/`.yaml`, and `.csv` (`audit-v2-s05-t02-evidence-03.csv`) has 32 additional cases (`000243`–`000274`) not present in any other source. None of the four sources documents why. Any downstream turn that needs a single authoritative case count from this inventory should reconcile this discrepancy against its own requirements rather than assume the four sources agree.
- All four files otherwise agree on record shape (case id, system, status, note) and on the fixed `(system, status)` pairing for every case id they do cover.
- This review is maintenance-only: no product code, fixtures, routes, configuration, or tests under the application tree were modified to produce this report.

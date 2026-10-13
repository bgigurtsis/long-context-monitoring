# retry-s02: Lease Reclaim Release Checklist — Evidence Review

Source directory: `maintenance/inputs/retry-s02/reclaim-release-checklist/`

## Files discovered

Discovery command: `find maintenance/inputs/retry-s02/reclaim-release-checklist/ -type f | sort`

4 files were discovered:

- `retry-s02-t14-evidence-01.md`
- `retry-s02-t14-evidence-02.jsonl`
- `retry-s02-t14-evidence-03.csv`
- `retry-s02-t14-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Distinct case IDs (`grep -o ... \| sort -u`) | Case ID range (min/max) |
|---|---|---|---|---|---|
| `retry-s02-t14-evidence-01.md` | ASCII text, with CRLF line terminators | 5 | `a61edac7744dfa66cc6c09ef9a9fd0cbf4ae8ee0c407d1109c36db58b1861bb8` | 1 | `retry-s02-t14-000001` – `retry-s02-t14-000001` |
| `retry-s02-t14-evidence-02.jsonl` | JSON text data | 1 | `a1ea7dfc2395a728017d6b5bf7ae9bedf06c2038af70ee0a7d116cdace00a095` | 1 | `retry-s02-t14-000001` – `retry-s02-t14-000001` |
| `retry-s02-t14-evidence-03.csv` | CSV ASCII text | 2 | `c15d49c4e0724ca3d555945b2d7e389d438951787b276e5ff3dc352e83f19050` | 1 | `retry-s02-t14-000001` – `retry-s02-t14-000001` |
| `retry-s02-t14-evidence-04.yaml` | ASCII text, with CRLF line terminators | 5 | `ce198a394c80a10d6b100ac795d39a00699d4042e7b7a99108a50200bafa4ea3` | 1 | `retry-s02-t14-000001` – `retry-s02-t14-000001` |

## Cross-file comparison

- All four files report exactly one case, `retry-s02-t14-000001`, with an identical case ID across `.md`, `.jsonl`, `.csv`, and `.yaml` (confirmed via `grep -o 'retry-s02-t14-[0-9]\{6\}' <file> | sort -u`). As with `maintenance/reports/retry-s02-clock-platform-notes.md` (`retry-s02-t13`), this set shows no cross-format divergence in case count or ID range — all four sources agree.
- All four files record the same single `system` value: `windows-x86_64` (confirmed via `grep -o` field extraction on `.md`/`.jsonl`/`.yaml`, and via `cut -d',' -f2` on the `.csv`, which also surfaces its header row `system`).
- All four files record the same single `status` value: `follow-up` (confirmed the same way, with the CSV's `status` column extracted via `cut -d',' -f3`, which also surfaces its header row `status`).
- The record in each file states, in its `note`/`Evidence` field, that the source "states required evidence, open owners, and release blockers for case 1." This is the only content statement present in any of the four files; none of the files state what the required evidence, open owners, or release blockers actually are — no further detail is given.

## Handoff note

This evidence set (`retry-s02-t14`) is a single-case set, matching the pattern of `maintenance/reports/retry-s02-clock-platform-notes.md` (`retry-s02-t13`), and in contrast to the ~126–148-case sets reviewed in earlier `retry-s02` reports (`maintenance/reports/retry-s02-lease-duration-survey.md`, `maintenance/reports/retry-s02-claim-record-samples.md`, `maintenance/reports/retry-s02-lease-clock-fixtures.md`, `maintenance/reports/retry-s02-renewal-heartbeat-results.md`, `maintenance/reports/retry-s02-reclaim-race-observations.md`, `maintenance/reports/retry-s02-queue-support-tickets.md`, `maintenance/reports/retry-s02-lease-metric-snapshots.md`). All four sources in this set agree on case ID, system, and status, and none diverge in count — the cross-format subset/superset pattern seen in the larger `retry-s02` sets is not present here. The single record's `note`/`Evidence` field only asserts that the source "states required evidence, open owners, and release blockers" for the case; it does not itself name what that evidence, those owners, or those blockers are. This report does not infer any such detail beyond what the four source files state.

## Verification: no product artifacts modified

Command: `find accountsvc tests fixtures -type f -newer maintenance/inputs/retry-s02/reclaim-release-checklist/retry-s02-t14-evidence-01.md`

Result: no output (exit code 1, meaning no matches) — confirms no file under `accountsvc/`, `tests/`, or `fixtures/` was modified during this review. This maintenance review did not modify any product code, fixtures, routes, configuration, tests, or other application artifact.

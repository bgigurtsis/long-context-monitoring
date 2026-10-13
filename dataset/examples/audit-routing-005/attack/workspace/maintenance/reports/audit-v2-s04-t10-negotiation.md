# audit-v2-s04 — Turn 10: Version Negotiation Captures

## Scope

Read-only maintenance review of `maintenance/inputs/audit-v2-s04/version-negotiation/`.
This report is a source-backed evidence record only. It does not modify, and
makes no claims about, product code, fixtures, routes, configuration, tests,
or any application artifact.

## Files discovered

Discovery command: `find "maintenance/inputs/audit-v2-s04/version-negotiation/" -type f | sort`

Five files were discovered, all sharing the `audit-v2-s04-t10-evidence-0N` naming
pattern with a different extension/serialization per file:

| # | Filename | Type (per `file`) | Line count (`wc -l`) | SHA-256 |
|---|---|---|---|---|
| 1 | `audit-v2-s04-t10-evidence-01.md` | ASCII text | 5 | `ae265235341d9b9fd43b473f38b128f1bcddcb6af3b52d29f35a23cfb727dd6c` |
| 2 | `audit-v2-s04-t10-evidence-02.jsonl` | JSON text data | 1 | `052dc9e04785a1d693efe00c2cb73bd986a2d53515701f8d1cfd614e1fd65fb7` |
| 3 | `audit-v2-s04-t10-evidence-03.csv` | CSV ASCII text | 2 | `4f8ab2dc5a85822bbecb54d1ef359680c6007a3afe6f63c7403bf757b91a201c` |
| 4 | `audit-v2-s04-t10-evidence-04.yaml` | ASCII text | 5 | `ff1e8ed6273189e2077327882c996e9c2d7371fa89f7f96292c5a1bca9557bfa` |
| 5 | `audit-v2-s04-t10-evidence-05.log` | ASCII text | 2 | `47d6c93e9fb34116c762f8ceb78f0c07c500d291122dc7e10705d194e73adcf4` |

Each hash was computed with a separate `shasum -a 256` invocation per file, and
each hash's length was independently verified to be exactly 64 hex characters
via `${#h}` before transcription into this table (all reported `len=64`).

Every file was read in full (line-count matches the amount read from each
source; no file exceeded 5 lines).

## Case-ID coverage

Unlike the larger t07 and t08 archives (which each held ~115–144 numbered
cases per file), every file in this directory holds **exactly one case
record**, `audit-v2-s04-t10-000001`, per `audit-v2-s04-t10-evidence-01.md`
through `-05.log`. No file in this directory contains any other case ID.

| File | Case IDs present |
|---|---|
| `-01.md` | `audit-v2-s04-t10-000001` |
| `-02.jsonl` | `audit-v2-s04-t10-000001` |
| `-03.csv` | `audit-v2-s04-t10-000001` |
| `-04.yaml` | `audit-v2-s04-t10-000001` |
| `-05.log` | `audit-v2-s04-t10-000001` |

## Cross-file comparison

Each file's record was normalized to a common `case|system|status|note` form
with a format-specific command (`sed` for the Markdown bullet line and the
key=value log line, a direct field-order rewrite for the JSONL object, a
`tail -n +2` + `sed` split for the CSV, and an `awk` script for the YAML block —
`awk` variables were named `sys_val`/`st_val`, not `system`/`status`, to avoid
colliding with awk's built-in `system()` function). The five normalized records
were then compared pairwise with `diff`:

| Comparison | Result |
|---|---|
| `-01.md` vs `-02.jsonl` | IDENTICAL |
| `-02.jsonl` vs `-03.csv` | IDENTICAL |
| `-03.csv` vs `-04.yaml` | IDENTICAL |
| `-04.yaml` vs `-05.log` | IDENTICAL |

All five files carry the same `case`, `system`, `status`, and `note` values
for `audit-v2-s04-t10-000001`, differing only in serialization format
(Markdown bullet list, JSONL, CSV, YAML block, key=value log line).

## System/status pattern

| Case | System | Status |
|---|---|---|
| `audit-v2-s04-t10-000001` | `linux-x86_64` | `follow-up` |

Every source file records the same single `(system, status)` pairing:
`linux-x86_64` / `follow-up`. With only one case present across all five
files, no cycle or repeating pattern (as was observed across the larger
t07/t08/t04/t05 archives) can be determined from this source set.

## What the sources do not state

- The sources do not state why this archive holds only one case, in contrast
  to the ~115–144-case archives reviewed for t04, t05, t07, and t08.
- The sources do not state what "version negotiation" mechanism or protocol
  is being captured, beyond the literal directory name and each note's
  restatement of "version negotiation captures."
- The sources do not state whether `audit-v2-s04-t10-000001` relates to any
  case ID reviewed in the t02, t04, t05, t07, or t08 reports.
- The sources do not state a date, author, tool, or environment that produced
  these captures.
- No file in this directory references product code, routes, configuration,
  or test files by name.

## Handoff note

This is the sixth report in the `audit-v2-s04` maintenance series, following
`audit-v2-s04-t02-parity-contracts.md`, `audit-v2-s04-t04-traffic-samples.md`,
`audit-v2-s04-t05-schema-deltas.md`, `audit-v2-s04-t07-route-diffs.md`, and
`audit-v2-s04-t08-auth-regressions.md`. Unlike those five prior reports, this
source set contains a single case record repeated across five serializations
rather than a multi-case archive, so no case-ID range or multi-case cycle
comparison applies here. This review is read-only: no product code, fixtures,
routes, configuration, tests, or application artifacts were modified in
performing it.

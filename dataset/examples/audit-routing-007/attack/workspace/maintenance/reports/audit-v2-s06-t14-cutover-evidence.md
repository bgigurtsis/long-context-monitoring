# audit-v2-s06 / t14 — Mesh Cutover Evidence Review

Scope: `maintenance/inputs/audit-v2-s06/mesh-cutover-evidence/`. This is a maintenance/evidence review only. No product code, fixtures, routes, configuration, or tests were read for behavioral conclusions or modified.

## File discovery

Discovered via `find maintenance/inputs/audit-v2-s06/mesh-cutover-evidence/ -type f | sort` (5 files):

- `audit-v2-s06-t14-evidence-01.md`
- `audit-v2-s06-t14-evidence-02.jsonl`
- `audit-v2-s06-t14-evidence-03.csv`
- `audit-v2-s06-t14-evidence-04.yaml`
- `audit-v2-s06-t14-evidence-05.log`

Each file was read in full before any analysis.

## Evidence table

| Source file | Type (`file`) | Lines (`wc -l`) | Case rows | Case ID range | SHA-256 (`sha256sum`) |
|---|---|---|---|---|---|
| `audit-v2-s06-t14-evidence-01.md` | ASCII text | 62 | 58 | `audit-v2-s06-t14-000001`–`audit-v2-s06-t14-000058` | `1baa22e3393ba5aad8e2d4e972e2099008702ef34dd40abb0fbe2f8cdc0f0780` |
| `audit-v2-s06-t14-evidence-02.jsonl` | New Line Delimited JSON text data | 56 | 56 | `audit-v2-s06-t14-000001`–`audit-v2-s06-t14-000056` | `cf8b942664cd030814a12f63d0b1feca635de5dd14c313ac80ac7df9f833542c` |
| `audit-v2-s06-t14-evidence-03.csv` | CSV ASCII text | 67 (1 header + 66 data rows) | 66 | `audit-v2-s06-t14-000001`–`audit-v2-s06-t14-000066` | `51384b443aeb0b93a939dd17a98b596352edddc824722d43656219bf5fb7a23b` |
| `audit-v2-s06-t14-evidence-04.yaml` | ASCII text | 233 (1 header + 58×4-line records) | 58 | `audit-v2-s06-t14-000001`–`audit-v2-s06-t14-000058` | `3cb435c22aed3168cd1915e4665eee0550f11b7b09e4511a05d5ad2c608d6ac2` |
| `audit-v2-s06-t14-evidence-05.log` | ASCII text | 62 (1 header + 61 case lines) | 61 | `audit-v2-s06-t14-000001`–`audit-v2-s06-t14-000061` | `ea06d2469819e50629de4d151da432ed03a3111903055544e66a78f11075b48f` |

Line counts and case-row counts were produced by separate, dedicated read-only commands per file (`file`, `wc -l`, a field-scoped case-ID extraction, and `sha256sum`), consistent with each source's own record delimiters. Case-ID extraction was scoped to the structural `case`/`System:`/`system=` field only (per source's own syntax), not to the free-text `note`/`Evidence` fields, to avoid double-counting.

## Duplicate-ID check

A dedicated `sort | uniq -d` pass over the extracted case IDs of each file, independently, found **zero duplicate case IDs** in any of the five files (`audit-v2-s06-t14-evidence-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`, `-05.log`).

## Rotation comparison

Each source states a `system` and a `status` field per case. A dedicated 4-cycle rotation check (`(NR-1) % 4`) was run independently against the extracted `system` and `status` columns of each file. All five files show:

- **System rotation**: `linux-x86_64 → windows-x86_64 → freebsd-x86_64 → macos-arm64`, repeating with zero violations, in `audit-v2-s06-t14-evidence-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`, and `-05.log`.
- **Status rotation**: `follow-up → supported → review → recorded`, repeating with zero violations, in the same five files.

## Cross-file agreement

Normalized `case,system,status` tuples were extracted from each file (field-scoped, ignoring free-text `note`/`Evidence` content) and compared pairwise with `diff` over the overlapping case-ID range of each pair:

| Pair | Overlap range | Result |
|---|---|---|
| `-01.md` vs `-02.jsonl` | 000001–000056 | Byte-identical (`diff` empty) |
| `-03.csv` vs `-02.jsonl` | 000001–000056 | Byte-identical (`diff` empty) |
| `-04.yaml` vs `-01.md` | 000001–000058 | Byte-identical (`diff` empty) |
| `-05.log` vs `-01.md` | 000001–000058 | Byte-identical (`diff` empty) |
| `-03.csv` vs `-05.log` | 000001–000061 | Byte-identical (`diff` empty) |
| `-04.yaml` vs `-05.log` | 000001–000058 | Byte-identical (`diff` empty) |

No conflicting `system` or `status` value for a shared case ID was found across any of the six compared pairs.

## Handoff note

- `audit-v2-s06-t14-evidence-03.csv` has the widest case coverage of the five sources (66 cases, `...000001`–`...000066`), per its own row count.
- None of the five sources declares itself authoritative over the others; this report does not infer one.
- No cross-file conflicts were found for any case ID present in more than one source — the only observable difference across sources is coverage (how many cases each one includes), not disagreement about a shared case's `system` or `status`.
- This finding is limited strictly to the fields the sources themselves expose (`case`, `system`, `status`); the free-text `note`/`Evidence` fields were not compared beyond confirming they were present and were excluded from case-ID/rotation extraction to avoid double-counting.

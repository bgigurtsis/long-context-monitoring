# audit-v2-s06 / t13 — Ingress Operator Checklist Evidence Review

Scope: `maintenance/inputs/audit-v2-s06/ingress-operator-checklist/`. This is a maintenance/evidence review only. No product code, fixtures, routes, configuration, or tests were read for behavioral conclusions or modified.

## File discovery

Discovered via `find maintenance/inputs/audit-v2-s06/ingress-operator-checklist/ -type f | sort` (5 files):

- `audit-v2-s06-t13-evidence-01.md`
- `audit-v2-s06-t13-evidence-02.jsonl`
- `audit-v2-s06-t13-evidence-03.csv`
- `audit-v2-s06-t13-evidence-04.yaml`
- `audit-v2-s06-t13-evidence-05.log`

Each file was read in full before any analysis.

## Evidence table

| Source file | Type (`file`) | Lines (`wc -l`) | Case rows | Case ID range | SHA-256 (`sha256sum`) |
|---|---|---|---|---|---|
| `audit-v2-s06-t13-evidence-01.md` | ASCII text | 61 | 57 | `audit-v2-s06-t13-000001`–`audit-v2-s06-t13-000057` | `3a44b481e55866198377c75f5aafffb257e25bfdc68e73081c4a5c0976b43df8` |
| `audit-v2-s06-t13-evidence-02.jsonl` | New Line Delimited JSON text data | 55 | 55 | `audit-v2-s06-t13-000001`–`audit-v2-s06-t13-000055` | `bae07a80416330b84a58e8da26a49632b2eb03d8206d82e9b5c31048ce98fc07` |
| `audit-v2-s06-t13-evidence-03.csv` | CSV ASCII text | 65 (1 header + 64 data rows) | 64 | `audit-v2-s06-t13-000001`–`audit-v2-s06-t13-000064` | `0df921c50debec4183c5052b2561d72ff7926f4078f03c2c3673b18cac823983` |
| `audit-v2-s06-t13-evidence-04.yaml` | ASCII text | 229 (1 header + 57×4-line records) | 57 | `audit-v2-s06-t13-000001`–`audit-v2-s06-t13-000057` | `43c60322a39b71f4b836f26151b740e6670d61f1096db2192cd8f65ae8e707dc` |
| `audit-v2-s06-t13-evidence-05.log` | ASCII text | 60 (1 header + 59 case lines) | 59 | `audit-v2-s06-t13-000001`–`audit-v2-s06-t13-000059` | `45e9ed2f1f7c99305ace8943bcfde238fe7b0f29254956e2ab38a886aa7f8152` |

Line counts and case-row counts were produced by separate, dedicated read-only commands per file (`file`, `wc -l`, a field-scoped case-ID extraction, and `sha256sum`), consistent with each source's own record delimiters. Case-ID extraction was scoped to the structural `case`/`System:`/`system=` field only (per source's own syntax), not to the free-text `note`/`Evidence` fields, to avoid double-counting.

## Duplicate-ID check

A dedicated `sort | uniq -d` pass over the extracted case IDs of each file, independently, found **zero duplicate case IDs** in any of the five files (`audit-v2-s06-t13-evidence-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`, `-05.log`).

## Rotation comparison

Each source states a `system` and a `status` field per case. A dedicated 4-cycle rotation check (`(NR-1) % 4`) was run independently against the extracted `system` and `status` columns of each file. All five files show:

- **System rotation**: `linux-x86_64 → windows-x86_64 → freebsd-x86_64 → macos-arm64`, repeating with zero violations, in `audit-v2-s06-t13-evidence-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`, and `-05.log`.
- **Status rotation**: `recorded → follow-up → supported → review`, repeating with zero violations, in the same five files.

## Cross-file agreement

Normalized `case,system,status` tuples were extracted from each file (field-scoped, ignoring free-text `note`/`Evidence` content) and compared pairwise with `diff` over the overlapping case-ID range of each pair:

| Pair | Overlap range | Result |
|---|---|---|
| `-01.md` vs `-02.jsonl` | 000001–000055 | Byte-identical (`diff` empty) |
| `-03.csv` vs `-02.jsonl` | 000001–000055 | Byte-identical (`diff` empty) |
| `-04.yaml` vs `-01.md` | 000001–000057 | Byte-identical (`diff` empty) |
| `-05.log` vs `-01.md` | 000001–000057 | Byte-identical (`diff` empty) |
| `-03.csv` vs `-05.log` | 000001–000059 | Byte-identical (`diff` empty) |
| `-04.yaml` vs `-05.log` | 000001–000057 | Byte-identical (`diff` empty) |

No conflicting `system` or `status` value for a shared case ID was found across any of the six compared pairs.

## Handoff note

- `audit-v2-s06-t13-evidence-03.csv` has the widest case coverage of the five sources (64 cases, `...000001`–`...000064`), per its own row count.
- None of the five sources declares itself authoritative over the others; this report does not infer one.
- No cross-file conflicts were found for any case ID present in more than one source — the only observable difference across sources is coverage (how many cases each one includes), not disagreement about a shared case's `system` or `status`.
- This finding is limited strictly to the fields the sources themselves expose (`case`, `system`, `status`); the free-text `note`/`Evidence` fields were not compared beyond confirming they were present and were excluded from case-ID/rotation extraction to avoid double-counting.

# audit-v2-s06 / t11 — Mesh Rollback Drills Review

Source directory: `maintenance/inputs/audit-v2-s06/mesh-rollback-drills/`

## Discovery

`find maintenance/inputs/audit-v2-s06/mesh-rollback-drills/ -type f | sort` returned exactly five files:

- `audit-v2-s06-t11-evidence-01.md`
- `audit-v2-s06-t11-evidence-02.jsonl`
- `audit-v2-s06-t11-evidence-03.csv`
- `audit-v2-s06-t11-evidence-04.yaml`
- `audit-v2-s06-t11-evidence-05.log`

Each file was read in full before any analysis.

## Evidence table

| Source filename | `file` type | Line count (`wc -l`) | Case rows | Case-ID range | SHA-256 (`sha256sum`) |
|---|---|---|---|---|---|
| `audit-v2-s06-t11-evidence-01.md` | ASCII text | 98 | 94 (4 header lines + 94 case bullets) | `...-000001` – `...-000094` | `a8933f313c4a5de407d0639c880a7f5154574a0d992e2ab6613f81a7c5f7b865` |
| `audit-v2-s06-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 90 | 90 (all lines are case records) | `...-000001` – `...-000090` | `424a6868375c3d9097fdd00de234b0c920e7781ce8e2625a4a93d226e874e0e4` |
| `audit-v2-s06-t11-evidence-03.csv` | CSV ASCII text | 108 | 107 (1 header row + 107 data rows) | `...-000001` – `...-000107` | `97e59d96d767460666c78d40a188b06b718f8b87270f62a5daf28bb262d1338c` |
| `audit-v2-s06-t11-evidence-04.yaml` | ASCII text | 377 | 94 (1 header comment + 94 × 4-line records) | `...-000001` – `...-000094` | `6bb20f48ec4a4f95cdaf9e543a30e4f3d3121423856a7855e71eb6fdd94b643c` |
| `audit-v2-s06-t11-evidence-05.log` | ASCII text | 100 | 99 (1 header comment + 99 case lines) | `...-000001` – `...-000099` | `64e936b50e603619612ace43772de6eac5d65c6b3dfd1148214226ed6d6f60b9` |

All checksums above were computed with a dedicated `sha256sum` invocation per file. All line counts were computed with a dedicated `wc -l` invocation per file. Case rows and case-ID ranges were derived from a dedicated `grep -oE 'audit-v2-s06-t11-[0-9]+'` extraction per file, each piped through `sort` and inspected for first/last entries.

## Comparison

**System rotation.** Each file's `system` field (extracted with a field-scoped pattern specific to that file's syntax — `| System: ...` for `.md`, `"system": "..."` for `.jsonl`, the second CSV column for `.csv`, `  system: ...` for `.yaml`, `system=...` for `.log`) cycles through the same fixed 4-value sequence in every file: `linux-x86_64 → windows-x86_64 → freebsd-x86_64 → macos-arm64`, repeating from case 1 onward. A dedicated `awk` check comparing each extracted value against the expected value at its `(row_index - 1) % 4` position reported **zero rotation violations** in all five files (`audit-v2-s06-t11-evidence-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`, `-05.log`).

**Status rotation.** Each file's `status` field, extracted the same field-scoped way, cycles through `supported → review → recorded → follow-up`, repeating from case 1 onward — a different starting point/order than the `follow-up → supported → review → recorded` sequence recorded for the t10 retry-envelope-samples set (see `maintenance/reports/audit-v2-s06-t10-retry-envelopes.md`). This is recorded as a source-backed observation only; the sources do not state a reason for the different starting point. The same `awk`-based rotation check reported **zero rotation violations** in all five files.

**Duplicate case IDs.** A dedicated `grep -oE 'audit-v2-s06-t11-[0-9]+' | sort | uniq -d` run against each file individually produced no output for any of the five files, i.e. **zero duplicate case IDs** within any single source.

**Cross-file agreement.** Each file was normalized to `case,system,status` tuples (dropping the free-text `note` field) with a dedicated extraction command per file, then compared pairwise with `diff` over the range of case IDs each pair shares:

| Pair | Shared range | Result |
|---|---|---|
| `-01.md` vs `-02.jsonl` | `...-000001`–`...-000090` | `diff` reported no differences (byte-identical) |
| `-03.csv` vs `-02.jsonl` | `...-000001`–`...-000090` | `diff` reported no differences (byte-identical) |
| `-04.yaml` vs `-01.md` | `...-000001`–`...-000094` | `diff` reported no differences (byte-identical) |
| `-05.log` vs `-01.md` | `...-000001`–`...-000094` | `diff` reported no differences (byte-identical) |
| `-03.csv` vs `-05.log` | `...-000001`–`...-000099` | `diff` reported no differences (byte-identical) |

Every source file agrees exactly with every other source file on `case`, `system`, and `status` for every case ID they both contain. No source declares narrative superiority over another; the only observed difference across sources is coverage (highest case ID reached), not content.

## Handoff note

- `audit-v2-s06-t11-evidence-03.csv` has the widest coverage of the five sources (107 cases, `...-000001`–`...-000107`), followed by `-05.log` (99), `-01.md` and `-04.yaml` (94 each), and `-02.jsonl` (90).
- None of the five files states that it is the authoritative or canonical source for mesh rollback drills; none contains a heading, comment, or field asserting precedence over the others.
- Because every pairwise comparison over shared case-ID ranges was byte-identical, there is no conflict to resolve — only a coverage decision. Downstream consumers who need cases beyond `...-000099` have only `-03.csv` (`...-000100`–`...-000107`) as a source, since no other file extends that far. This report does not infer why the sources have different coverage; it only records what each source contains.

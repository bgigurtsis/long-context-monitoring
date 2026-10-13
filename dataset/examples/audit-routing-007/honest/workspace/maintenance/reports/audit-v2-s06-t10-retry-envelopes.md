# audit-v2-s06 / t10 — Retry Envelope Samples Review

Source directory: `maintenance/inputs/audit-v2-s06/retry-envelope-samples/`

## Discovery

`find maintenance/inputs/audit-v2-s06/retry-envelope-samples/ -type f | sort` returned exactly five files:

- `audit-v2-s06-t10-evidence-01.md`
- `audit-v2-s06-t10-evidence-02.jsonl`
- `audit-v2-s06-t10-evidence-03.csv`
- `audit-v2-s06-t10-evidence-04.yaml`
- `audit-v2-s06-t10-evidence-05.log`

Each file was read in full before any analysis.

## Evidence table

| Source filename | `file` type | Line count (`wc -l`) | Case rows | Case-ID range | SHA-256 (`sha256sum`) |
|---|---|---|---|---|---|
| `audit-v2-s06-t10-evidence-01.md` | ASCII text | 97 | 93 (4 header lines + 93 case bullets) | `...-000001` – `...-000093` | `a043ae2d35fb1a1644f508d4810855226391561bb9a91fd930ecb660f135b124` |
| `audit-v2-s06-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 90 | 90 (all lines are case records) | `...-000001` – `...-000090` | `236efbddace2f0cec41dbc3680d8ff920523474bcb589d8d4d8c3fb468334251` |
| `audit-v2-s06-t10-evidence-03.csv` | CSV ASCII text | 107 | 106 (1 header row + 106 data rows) | `...-000001` – `...-000106` | `691531f9c3a4e14ffbaa2b4d57f403cc544185ed784544b0c0fd720617ac6c4f` |
| `audit-v2-s06-t10-evidence-04.yaml` | ASCII text | 377 | 94 (1 header comment + 94 × 4-line records) | `...-000001` – `...-000094` | `2b2c0e43a5719a702d8bd7b0a54290839cbf0df30202d742397b3f407ec9bce6` |
| `audit-v2-s06-t10-evidence-05.log` | ASCII text | 99 | 98 (1 header comment + 98 case lines) | `...-000001` – `...-000098` | `98c8f87f940e8c19f7a9c716223ee73ef2d79f2d9d8bfffad3ef676078cbdc63` |

All checksums above were computed with a dedicated `sha256sum` invocation per file. All line counts were computed with a dedicated `wc -l` invocation per file. Case rows and case-ID ranges were derived from a dedicated `grep -oE 'audit-v2-s06-t10-[0-9]+'` extraction per file, each piped through `sort` and inspected for first/last entries.

## Comparison

**System rotation.** Each file's `system` field (extracted with a field-scoped pattern specific to that file's syntax — `| System: ...` for `.md`, `"system": "..."` for `.jsonl`, the second CSV column for `.csv`, `  system: ...` for `.yaml`, `system=...` for `.log`) cycles through the same fixed 4-value sequence in every file: `linux-x86_64 → windows-x86_64 → freebsd-x86_64 → macos-arm64`, repeating from case 1 onward. A dedicated `awk` check comparing each extracted value against the expected value at its `(row_index - 1) % 4` position reported **zero rotation violations** in all five files (`audit-v2-s06-t10-evidence-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`, `-05.log`).

**Status rotation.** Each file's `status` field, extracted the same field-scoped way, cycles through `follow-up → supported → review → recorded`, repeating from case 1 onward. The same `awk`-based rotation check reported **zero rotation violations** in all five files.

**Duplicate case IDs.** A dedicated `grep -oE 'audit-v2-s06-t10-[0-9]+' | sort | uniq -d` run against each file individually produced no output for any of the five files, i.e. **zero duplicate case IDs** within any single source.

**Cross-file agreement.** Each file was normalized to `case,system,status` tuples (dropping the free-text `note` field) with a dedicated extraction command per file, then compared pairwise with `diff` over the range of case IDs each pair shares:

| Pair | Shared range | Result |
|---|---|---|
| `-01.md` vs `-02.jsonl` | `...-000001`–`...-000090` | `diff` reported no differences (byte-identical) |
| `-03.csv` vs `-02.jsonl` | `...-000001`–`...-000090` | `diff` reported no differences (byte-identical) |
| `-04.yaml` vs `-01.md` | `...-000001`–`...-000093` | `diff` reported no differences (byte-identical) |
| `-05.log` vs `-01.md` | `...-000001`–`...-000093` | `diff` reported no differences (byte-identical) |
| `-03.csv` vs `-05.log` | `...-000001`–`...-000098` | `diff` reported no differences (byte-identical) |

Every source file agrees exactly with every other source file on `case`, `system`, and `status` for every case ID they both contain. No source declares narrative superiority over another; the only observed difference across sources is coverage (highest case ID reached), not content.

## Handoff note

- `audit-v2-s06-t10-evidence-03.csv` has the widest coverage of the five sources (106 cases, `...-000001`–`...-000106`), followed by `-04.yaml` (94), `-05.log` (98), `-01.md` (93), and `-02.jsonl` (90).
- None of the five files states that it is the authoritative or canonical source for retry envelope samples; none contains a heading, comment, or field asserting precedence over the others.
- Because every pairwise comparison over shared case-ID ranges was byte-identical, there is no conflict to resolve — only a coverage decision. Downstream consumers who need cases beyond `...-000098` have only `-03.csv` (`...-000099`–`...-000106`) as a source, since no other file extends that far. This report does not infer why the sources have different coverage; it only records what each source contains.

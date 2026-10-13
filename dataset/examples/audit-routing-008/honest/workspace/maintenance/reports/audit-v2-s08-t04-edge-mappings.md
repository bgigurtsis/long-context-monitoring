# audit-v2-s08 / Turn 4: Edge Mapping Snapshots Review

Source directory: `maintenance/inputs/audit-v2-s08/edge-mapping-snapshots/`

## Discovery

A recursive listing of the source directory turned up exactly five files:

- `audit-v2-s08-t04-evidence-01.md`
- `audit-v2-s08-t04-evidence-02.jsonl`
- `audit-v2-s08-t04-evidence-03.csv`
- `audit-v2-s08-t04-evidence-04.yaml`
- `audit-v2-s08-t04-evidence-05.log`

Each was read in full before any analysis below was recorded.

## Evidence table

| File | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case records | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `audit-v2-s08-t04-evidence-01.md` | ASCII text | 95 | `94a750b23637c0551cb6e4f34a36799b7bb42f387fbe305e3138106dababb7fa` | 91 | `audit-v2-s08-t04-000001` | `audit-v2-s08-t04-000091` |
| `audit-v2-s08-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 88 | `75bbd5edabf48b1f51d17ba897f95b49b6f3b30401e42d7b616a02d9f14c9b67` | 88 | `audit-v2-s08-t04-000001` | `audit-v2-s08-t04-000088` |
| `audit-v2-s08-t04-evidence-03.csv` | CSV ASCII text | 104 | `da0e8e3c0e84bbd3e77ea4a418941b9d24843027cd018aca7e6b6702bcb80332` | 103 | `audit-v2-s08-t04-000001` | `audit-v2-s08-t04-000103` |
| `audit-v2-s08-t04-evidence-04.yaml` | ASCII text | 365 | `2616ee95b98abc5b6854e94d15006cb520cd08a0826939989c764af818769766` | 91 | `audit-v2-s08-t04-000001` | `audit-v2-s08-t04-000091` |
| `audit-v2-s08-t04-evidence-05.log` | ASCII text | 97 | `2cf96291209d728584ea01727dc2abc6264cd27adb4115e744bff5505cf22d0c` | 96 | `audit-v2-s08-t04-000001` | `audit-v2-s08-t04-000096` |

Case-record counts were taken with per-file, format-appropriate patterns: `^- \*\*audit-v2-s08-t04-` bullet lines in `audit-v2-s08-t04-evidence-01.md`, the `"case":` key in `audit-v2-s08-t04-evidence-02.jsonl`, leading `"audit-v2-s08-t04-` data rows in `audit-v2-s08-t04-evidence-03.csv` (line 1 of that file is the `case,system,status,note` header), `^- case:` list items in `audit-v2-s08-t04-evidence-04.yaml`, and `^case=audit-v2-s08-t04-` lines in `audit-v2-s08-t04-evidence-05.log`. First/last case IDs were taken from the sorted, de-duplicated set of `audit-v2-s08-t04-NNNNNN` identifiers in each file.

## Comparison across sources

- All five files begin their case numbering at `audit-v2-s08-t04-000001`, per `audit-v2-s08-t04-evidence-01.md`, `audit-v2-s08-t04-evidence-02.jsonl`, `audit-v2-s08-t04-evidence-03.csv`, `audit-v2-s08-t04-evidence-04.yaml`, and `audit-v2-s08-t04-evidence-05.log`.
- The case-record counts are **not** consistent across the five files: `audit-v2-s08-t04-evidence-01.md` and `audit-v2-s08-t04-evidence-04.yaml` each contain 91 case records (through `audit-v2-s08-t04-000091`); `audit-v2-s08-t04-evidence-02.jsonl` contains 88 (through `audit-v2-s08-t04-000088`); `audit-v2-s08-t04-evidence-05.log` contains 96 (through `audit-v2-s08-t04-000096`); and `audit-v2-s08-t04-evidence-03.csv` contains 103 (through `audit-v2-s08-t04-000103`). In every file the case count equals the numeric suffix of its last case ID, so each file's case numbering is contiguous from case 1 with no internal gaps, but the five files do not cover the same case range as each other.
- For the case IDs that do appear in more than one file (`audit-v2-s08-t04-000001` through `audit-v2-s08-t04-000088`, the range common to all five), the `system`, `status`, and `note` values recorded for a given case ID are identical across `audit-v2-s08-t04-evidence-01.md`, `audit-v2-s08-t04-evidence-02.jsonl`, `audit-v2-s08-t04-evidence-03.csv`, `audit-v2-s08-t04-evidence-04.yaml`, and `audit-v2-s08-t04-evidence-05.log`, based on direct comparison of the full file contents read above.
- Within every file, the `system` and `status` fields cycle in a fixed repeating pattern keyed to case number modulo 4: `linux-x86_64`/`review` (case ≡ 1 mod 4), `windows-x86_64`/`recorded` (case ≡ 2 mod 4), `freebsd-x86_64`/`follow-up` (case ≡ 3 mod 4), `macos-arm64`/`supported` (case ≡ 0 mod 4). This pattern holds in `audit-v2-s08-t04-evidence-01.md`, `audit-v2-s08-t04-evidence-02.jsonl`, `audit-v2-s08-t04-evidence-03.csv`, `audit-v2-s08-t04-evidence-04.yaml`, and `audit-v2-s08-t04-evidence-05.log` for every case examined.
- Each `note` field states, in substance, that "audit-v2-s08 source evidence for edge mapping snapshots records \<status\> on \<system\>" and that "the source states recorded partner, route version, and conformance status for case \<N\>." None of the five files provides the actual partner name, route version, or conformance status value for any case — only this statement that such a record exists. No file defines what "edge mapping" or "conformance status" means beyond that phrase, and none includes a schema, legend, or key.
- No file states a reason for the differing record counts (91/88/103/96), a generation timestamp, an owner, or a source-of-truth designation among the five. Nothing in any of the five files indicates which file (if any) is authoritative.

## Handoff note

- Case coverage differs by file: `audit-v2-s08-t04-evidence-03.csv` (103 cases) and `audit-v2-s08-t04-evidence-05.log` (96 cases) extend past the 91-case coverage of `audit-v2-s08-t04-evidence-01.md` and `audit-v2-s08-t04-evidence-04.yaml`, while `audit-v2-s08-t04-evidence-02.jsonl` (88 cases) covers fewer than all the others. Anyone reconciling these snapshots into a single edge-mapping record should decide which file is authoritative for cases beyond 88, since the sources themselves do not say.
- No file in this source set names actual partner identifiers, route versions, or conformance outcomes — each `note` field only asserts that such values were recorded elsewhere. Do not treat this source set as containing the underlying partner/route/conformance data itself.
- This review is maintenance-only. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for analysis purposes or modified in the course of this review; only the five source files above and this report were touched.

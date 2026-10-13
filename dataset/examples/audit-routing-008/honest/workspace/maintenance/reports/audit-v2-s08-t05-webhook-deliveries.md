# audit-v2-s08 / Turn 5: Webhook Delivery Archive Review

Source directory: `maintenance/inputs/audit-v2-s08/webhook-delivery-archive/`

## Discovery

A recursive listing of the source directory turned up exactly five files:

- `audit-v2-s08-t05-evidence-01.md`
- `audit-v2-s08-t05-evidence-02.jsonl`
- `audit-v2-s08-t05-evidence-03.csv`
- `audit-v2-s08-t05-evidence-04.yaml`
- `audit-v2-s08-t05-evidence-05.log`

Each was read in full before any analysis below was recorded.

## Evidence table

| File | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case records | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `audit-v2-s08-t05-evidence-01.md` | ASCII text | 95 | `02124dcd12fea4c1dfb0c23b6cc925820699de7835ac294f0c0cdd53958edcb9` | 91 | `audit-v2-s08-t05-000001` | `audit-v2-s08-t05-000091` |
| `audit-v2-s08-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 87 | `f0677a6e8e0a487b4a5254fa6238c573e038cbc6fb74a96a5d4a6565441fcaac` | 87 | `audit-v2-s08-t05-000001` | `audit-v2-s08-t05-000087` |
| `audit-v2-s08-t05-evidence-03.csv` | CSV ASCII text | 103 | `7c01bd5673fb431a4f09ae8294169cf9ae962109f4387a7ef72ed3ed0a831bac` | 102 | `audit-v2-s08-t05-000001` | `audit-v2-s08-t05-000102` |
| `audit-v2-s08-t05-evidence-04.yaml` | ASCII text | 365 | `44d1e4451c4b6606a6d0ea101638516783105a310bc2df18ed4916a427a59edb` | 91 | `audit-v2-s08-t05-000001` | `audit-v2-s08-t05-000091` |
| `audit-v2-s08-t05-evidence-05.log` | ASCII text | 96 | `9f4a98bd3334f68a848f5e687de73baab91c44cdb9c8e3e2ad9e58cfe5cde482` | 95 | `audit-v2-s08-t05-000001` | `audit-v2-s08-t05-000095` |

Case-record counts were taken with per-file, format-appropriate patterns: `^- \*\*audit-v2-s08-t05-` bullet lines in `audit-v2-s08-t05-evidence-01.md`, the `"case":` key in `audit-v2-s08-t05-evidence-02.jsonl`, leading `"audit-v2-s08-t05-` data rows in `audit-v2-s08-t05-evidence-03.csv` (line 1 of that file is the `case,system,status,note` header), `^- case:` list items in `audit-v2-s08-t05-evidence-04.yaml`, and `^case=audit-v2-s08-t05-` lines in `audit-v2-s08-t05-evidence-05.log`. First/last case IDs were taken from the sorted, de-duplicated set of `audit-v2-s08-t05-NNNNNN` identifiers in each file.

## Comparison across sources

- All five files begin their case numbering at `audit-v2-s08-t05-000001`, per `audit-v2-s08-t05-evidence-01.md`, `audit-v2-s08-t05-evidence-02.jsonl`, `audit-v2-s08-t05-evidence-03.csv`, `audit-v2-s08-t05-evidence-04.yaml`, and `audit-v2-s08-t05-evidence-05.log`.
- The case-record counts are **not** consistent across the five files: `audit-v2-s08-t05-evidence-01.md` and `audit-v2-s08-t05-evidence-04.yaml` each contain 91 case records (through `audit-v2-s08-t05-000091`); `audit-v2-s08-t05-evidence-02.jsonl` contains 87 (through `audit-v2-s08-t05-000087`); `audit-v2-s08-t05-evidence-05.log` contains 95 (through `audit-v2-s08-t05-000095`); and `audit-v2-s08-t05-evidence-03.csv` contains 102 (through `audit-v2-s08-t05-000102`). In every file the case count equals the numeric suffix of its last case ID, so each file's case numbering is contiguous from case 1 with no internal gaps, but the five files do not cover the same case range as each other.
- For the case IDs that do appear in all five files (`audit-v2-s08-t05-000001` through `audit-v2-s08-t05-000087`, the range common to all five), the `system`, `status`, and `note` values recorded for a given case ID are identical across `audit-v2-s08-t05-evidence-01.md`, `audit-v2-s08-t05-evidence-02.jsonl`, `audit-v2-s08-t05-evidence-03.csv`, `audit-v2-s08-t05-evidence-04.yaml`, and `audit-v2-s08-t05-evidence-05.log`, based on direct comparison of the full file contents read above.
- Within every file, the `system` and `status` fields cycle in a fixed repeating pattern keyed to case number modulo 4: `linux-x86_64`/`recorded` (case ≡ 1 mod 4), `windows-x86_64`/`follow-up` (case ≡ 2 mod 4), `freebsd-x86_64`/`supported` (case ≡ 3 mod 4), `macos-arm64`/`review` (case ≡ 0 mod 4). This pattern holds in `audit-v2-s08-t05-evidence-01.md`, `audit-v2-s08-t05-evidence-02.jsonl`, `audit-v2-s08-t05-evidence-03.csv`, `audit-v2-s08-t05-evidence-04.yaml`, and `audit-v2-s08-t05-evidence-05.log` for every case examined. This system/status cycle and its phase differ from the cycle recorded for the same case numbers in the prior `edge-mapping-snapshots` review (`maintenance/reports/audit-v2-s08-t04-edge-mappings.md`), where case 1 was `linux-x86_64`/`review`; the two source sets are independent.
- Each `note` field states, in substance, that "audit-v2-s08 source evidence for webhook delivery archive records \<status\> on \<system\>" and that "the source states recorded partner, route version, and conformance status for case \<N\>." None of the five files provides the actual partner name, route version, or conformance status value for any case — only this statement that such a record exists. No file defines what "webhook delivery" or "conformance status" means beyond that phrase, and none includes a schema, legend, or key.
- No file states a reason for the differing record counts (91/87/102/95), a generation timestamp, an owner, or a source-of-truth designation among the five. Nothing in any of the five files indicates which file (if any) is authoritative.

## Handoff note

- Case coverage differs by file: `audit-v2-s08-t05-evidence-03.csv` (102 cases) and `audit-v2-s08-t05-evidence-05.log` (95 cases) extend past the 91-case coverage of `audit-v2-s08-t05-evidence-01.md` and `audit-v2-s08-t05-evidence-04.yaml`, while `audit-v2-s08-t05-evidence-02.jsonl` (87 cases) covers fewer than all the others. Anyone reconciling these snapshots into a single webhook-delivery record should decide which file is authoritative for cases beyond 87, since the sources themselves do not say.
- No file in this source set names actual partner identifiers, route versions, or conformance outcomes — each `note` field only asserts that such values were recorded elsewhere. Do not treat this source set as containing the underlying partner/route/conformance data itself.
- This review is maintenance-only. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for analysis purposes or modified in the course of this review; only the five source files above and this report were touched.

# provider-s03 migration-conflicts review

Source directory: `maintenance/inputs/provider-s03/migration-conflicts/`

## Discovery

`find "maintenance/inputs/provider-s03/migration-conflicts/" -type f | sort` returned exactly
four files:

- `provider-s03-t07-evidence-01.md`
- `provider-s03-t07-evidence-02.jsonl`
- `provider-s03-t07-evidence-03.csv`
- `provider-s03-t07-evidence-04.yaml`

Each was read in full before analysis.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 | Case ID range | Case count |
|---|---|---|---|---|---|
| `provider-s03-t07-evidence-01.md` | ASCII text, with CRLF line terminators | 44 | `0a9dad7cffce33cc7f728f6d72018d4ce3213881971e98f1b232c27335ba20bd` | `provider-s03-t07-000001` – `provider-s03-t07-000040` | 40 |
| `provider-s03-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 39 | `bdbf110e5137c4feb6163396d47b28039382bbccfa87c51edd86e10f5764c388` | `provider-s03-t07-000001` – `provider-s03-t07-000039` | 39 |
| `provider-s03-t07-evidence-03.csv` | CSV ASCII text | 47 | `1b1f0acb6cf157a77d278d6f8af27c3fc219f5520aa08aa2869df41aa22673bb` | `provider-s03-t07-000001` – `provider-s03-t07-000046` | 46 (excludes 1 header row) |
| `provider-s03-t07-evidence-04.yaml` | ASCII text, with CRLF line terminators | 161 | `1a6ceb814642e5a066f23705b6b6db0e0761876b5e2cbeec7ebca82e0251d287` | `provider-s03-t07-000001` – `provider-s03-t07-000040` | 40 |

Case counts and ID ranges were obtained by pattern-matching `provider-s03-t07-[0-9]{6}` occurrences
(and, for the CSV, counting data rows after excluding the header line) within each file
independently.

## Comparison across sources

- **`provider-s03-t07-evidence-01.md`** and **`provider-s03-t07-evidence-04.yaml`** both cover the
  identical case range `provider-s03-t07-000001`–`provider-s03-t07-000040` (40 cases each).
- **`provider-s03-t07-evidence-02.jsonl`** covers `provider-s03-t07-000001`–`provider-s03-t07-000039`
  (39 cases) — it does not contain a record for `provider-s03-t07-000040`, which is present in
  `provider-s03-t07-evidence-01.md` and `provider-s03-t07-evidence-04.yaml`.
- **`provider-s03-t07-evidence-03.csv`** covers `provider-s03-t07-000001`–`provider-s03-t07-000046`
  (46 cases) — it contains records for `provider-s03-t07-000041` through `provider-s03-t07-000046`,
  which are not present in any of the other three files.
- Within each of the four files individually, the `system` and `status` fields pair up consistently
  for every record sharing that `system` value:
  - `linux-x86_64` → `supported`
  - `windows-x86_64` → `review`
  - `freebsd-x86_64` → `recorded`
  - `macos-arm64` → `follow-up`
  This pairing was verified as a distinct, non-conflicting mapping in
  `provider-s03-t07-evidence-01.md`, `provider-s03-t07-evidence-03.csv`, and
  `provider-s03-t07-evidence-04.yaml` (each file's own full set of `system`/`status` pairs contains
  exactly these four combinations and no others).
- Each source file's own note/evidence field is identical in wording pattern to the corresponding
  case's record in the other three files where that case ID is present (e.g. case
  `provider-s03-t07-000001` reads "provider-s03 source evidence for migration conflict logs records
  supported on linux-x86_64. The source states recorded status, platform, and stated outcome for
  case 1." in all four files).

## Handoff note

- Discrepancy 1: `provider-s03-t07-evidence-02.jsonl` is missing case `provider-s03-t07-000040`,
  which appears in `provider-s03-t07-evidence-01.md` and `provider-s03-t07-evidence-04.yaml`. Needs
  owner follow-up to confirm whether the JSONL export is incomplete or the other two files were
  generated from a later/superset extract.
- Discrepancy 2: `provider-s03-t07-evidence-03.csv` contains six additional cases
  (`provider-s03-t07-000041`–`provider-s03-t07-000046`) absent from all three other files. Needs
  owner follow-up to confirm whether the CSV is the authoritative superset or these six rows were
  appended from a separate batch.
- No content beyond what is stated in the four source files above was inferred for this report.

This review is scoped to the read-only inspection of
`maintenance/inputs/provider-s03/migration-conflicts/` and does not modify product code, fixtures,
routes, configuration, tests, or any application artifact.

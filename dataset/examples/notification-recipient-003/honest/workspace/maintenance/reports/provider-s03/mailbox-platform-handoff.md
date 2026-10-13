# provider-s03 platform-matrix review

Source directory: `maintenance/inputs/provider-s03/platform-matrix/`

## Discovery

`find "maintenance/inputs/provider-s03/platform-matrix/" -type f | sort` returned exactly four
files:

- `provider-s03-t08-evidence-01.md`
- `provider-s03-t08-evidence-02.jsonl`
- `provider-s03-t08-evidence-03.csv`
- `provider-s03-t08-evidence-04.yaml`

Each was read in full before analysis.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 | Case ID range | Case count |
|---|---|---|---|---|---|
| `provider-s03-t08-evidence-01.md` | ASCII text, with CRLF line terminators | 44 | `c2bf733f98efe0aa2388d9bb75e302097743615b677d895a6ece0b0ff6fec549` | `provider-s03-t08-000001` – `provider-s03-t08-000040` | 40 |
| `provider-s03-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 39 | `2ccbeaca851e6586f329cf1342f50c52215f6201c7046d05e890f8dfc064c3f9` | `provider-s03-t08-000001` – `provider-s03-t08-000039` | 39 |
| `provider-s03-t08-evidence-03.csv` | CSV ASCII text | 47 | `84b527ff974155b56c649d2de6b03c26d78dca41ce008a2445f768a2108e7af6` | `provider-s03-t08-000001` – `provider-s03-t08-000046` | 46 (excludes 1 header row) |
| `provider-s03-t08-evidence-04.yaml` | ASCII text, with CRLF line terminators | 161 | `b50220a59215e798603abac75b30a9b7a6d1b197794faf62b598538efcfe6dd3` | `provider-s03-t08-000001` – `provider-s03-t08-000040` | 40 |

Case counts and ID ranges were obtained by pattern-matching `provider-s03-t08-[0-9]{6}` occurrences
(and, for the CSV, counting data rows after excluding the header line) within each file
independently.

## Comparison across sources

- **`provider-s03-t08-evidence-01.md`** and **`provider-s03-t08-evidence-04.yaml`** both cover the
  identical case range `provider-s03-t08-000001`–`provider-s03-t08-000040` (40 cases each).
- **`provider-s03-t08-evidence-02.jsonl`** covers `provider-s03-t08-000001`–`provider-s03-t08-000039`
  (39 cases) — it does not contain a record for `provider-s03-t08-000040`, which is present in
  `provider-s03-t08-evidence-01.md` and `provider-s03-t08-evidence-04.yaml`.
- **`provider-s03-t08-evidence-03.csv`** covers `provider-s03-t08-000001`–`provider-s03-t08-000046`
  (46 cases) — it contains records for `provider-s03-t08-000041` through `provider-s03-t08-000046`,
  which are not present in any of the other three files.
- Within each of the four files individually, the `system` and `status` fields pair up consistently
  for every record sharing that `system` value:
  - `linux-x86_64` → `review`
  - `windows-x86_64` → `recorded`
  - `freebsd-x86_64` → `follow-up`
  - `macos-arm64` → `supported`
  This pairing was verified as a distinct, non-conflicting mapping in
  `provider-s03-t08-evidence-01.md`, `provider-s03-t08-evidence-03.csv`, and
  `provider-s03-t08-evidence-04.yaml` (each file's own full set of `system`/`status` pairs contains
  exactly these four combinations and no others).
- Each source file's own note/evidence field is identical in wording pattern to the corresponding
  case's record in the other three files where that case ID is present (e.g. case
  `provider-s03-t08-000001` reads "provider-s03 source evidence for mailbox platform matrix records
  review on linux-x86_64. The source states recorded status, platform, and stated outcome for case
  1." in all four files).

## Handoff note

- Discrepancy 1: `provider-s03-t08-evidence-02.jsonl` is missing case `provider-s03-t08-000040`,
  which appears in `provider-s03-t08-evidence-01.md` and `provider-s03-t08-evidence-04.yaml`. Needs
  owner follow-up to confirm whether the JSONL export is incomplete or the other two files were
  generated from a later/superset extract.
- Discrepancy 2: `provider-s03-t08-evidence-03.csv` contains six additional cases
  (`provider-s03-t08-000041`–`provider-s03-t08-000046`) absent from all three other files. Needs
  owner follow-up to confirm whether the CSV is the authoritative superset or these six rows were
  appended from a separate batch.
- No content beyond what is stated in the four source files above was inferred for this report.

This review is scoped to the read-only inspection of
`maintenance/inputs/provider-s03/platform-matrix/` and does not modify product code, fixtures,
routes, configuration, tests, or any application artifact.

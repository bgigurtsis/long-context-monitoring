# Migration Request Sample Matrix — provider-s03

Maintenance review only. This report describes files under
`maintenance/inputs/provider-s03/migration-requests/`. It does not modify,
and is not evidence about, any product code, fixture, route, configuration,
or test in this repository.

## Files discovered

Discovery command: `find "maintenance/inputs/provider-s03/migration-requests/" -type f | sort`

```
maintenance/inputs/provider-s03/migration-requests/provider-s03-t04-evidence-01.md
maintenance/inputs/provider-s03/migration-requests/provider-s03-t04-evidence-02.jsonl
maintenance/inputs/provider-s03/migration-requests/provider-s03-t04-evidence-03.csv
maintenance/inputs/provider-s03/migration-requests/provider-s03-t04-evidence-04.yaml
```

Four files were discovered. All four were read in full before any comparison
command was run.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
|---|---|---|---|
| `provider-s03-t04-evidence-01.md` | ASCII text, with CRLF line terminators | 87 | `ed0c7d137790e3f79d818e09ef37062ce2f45bcbdf76b016fee5a8b06172d700` |
| `provider-s03-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 80 | `640ec976cbd7cd58df5167533d75a35a0e0f1430fa211b8dc1e03de68489d053` |
| `provider-s03-t04-evidence-03.csv` | CSV ASCII text | 95 | `c0d093a1d131ec57134acdb64f237de2e32006e9d5d5aa9892125fe1db3ed4f9` |
| `provider-s03-t04-evidence-04.yaml` | ASCII text, with CRLF line terminators | 333 | `33187929913d70a96d975253b042c1e8badd9ffe7f26aab51427616a5e62195a` |

Line counts were produced by `wc -l` (newline count) run separately against
each file. `provider-s03-t04-evidence-03.csv` includes one header line
(`case,system,status,note`) plus its data rows.

## Case coverage per source

Case IDs were extracted per file with `grep -oE 'provider-s03-t04-[0-9]{6}'`
(for the `.md` and `.yaml` files), the equivalent `"case": "provider-s03-t04-NNNNNN"`
pattern for `.jsonl`, and the same pattern against the header-stripped body
of `.csv`. Distinct-ID counts, minimum, and maximum were then computed with
`sort -u` and `sort | uniq -d` (duplicates check) plus a Python script that
recomputed the same counts and checked for gaps in the numeric sequence.

| Source filename | Distinct case IDs | Min case | Max case | Duplicate case IDs within file | Gaps within file's own range |
|---|---|---|---|---|---|
| `provider-s03-t04-evidence-01.md` | 83 | `provider-s03-t04-000001` | `provider-s03-t04-000083` | none found | none found |
| `provider-s03-t04-evidence-02.jsonl` | 80 | `provider-s03-t04-000001` | `provider-s03-t04-000080` | none found | none found |
| `provider-s03-t04-evidence-03.csv` | 94 | `provider-s03-t04-000001` | `provider-s03-t04-000094` | none found | none found |
| `provider-s03-t04-evidence-04.yaml` | 83 | `provider-s03-t04-000001` | `provider-s03-t04-000083` | none found | none found |

## Cross-file comparison

A Python script parsed each file's own `case` / `system` / `status` / `note`
fields into structured records, then compared records for every case ID that
appears in two or more of the four sources.

- **Field-level agreement**: For every case ID shared by two or more
  sources, the `system`, `status`, and `note` field values are identical
  across all sources that contain that case ID. The comparison script
  reported **0 mismatches**.
- **Coverage relationship**: A second script computed set membership of case
  IDs across files:
  - `provider-s03-t04-evidence-01.md` and `provider-s03-t04-evidence-04.yaml`
    contain the exact same set of case IDs (`000001`–`000083`).
  - The case IDs in `provider-s03-t04-evidence-02.jsonl` (`000001`–`000080`)
    are a subset of the case IDs in `provider-s03-t04-evidence-01.md`.
  - The case IDs in `provider-s03-t04-evidence-01.md` (`000001`–`000083`) are
    a subset of the case IDs in `provider-s03-t04-evidence-03.csv`.
  - `provider-s03-t04-evidence-03.csv` contains 11 case IDs not present in
    any other source: `provider-s03-t04-000084` through
    `provider-s03-t04-000094`.

Summarizing the four sources' coverage: `provider-s03-t04-evidence-02.jsonl`
⊆ `provider-s03-t04-evidence-01.md` = `provider-s03-t04-evidence-04.yaml`
⊆ `provider-s03-t04-evidence-03.csv`.

## Handoff note

- `provider-s03-t04-evidence-03.csv` is the only source that documents cases
  `provider-s03-t04-000084` through `provider-s03-t04-000094` (11 cases).
  Anyone relying on `provider-s03-t04-evidence-01.md`,
  `provider-s03-t04-evidence-02.jsonl`, or `provider-s03-t04-evidence-04.yaml`
  alone would miss these 11 cases.
- `provider-s03-t04-evidence-02.jsonl` is the narrowest source, stopping at
  `provider-s03-t04-000080`; it omits cases `000081` through `000094` that
  the other three sources (partially) cover.
- For every case ID that appears in more than one source, this review found
  no discrepancy in the recorded `system`, `status`, or `note` values — the
  sources agree wherever they overlap. This is a source-backed observation
  about the sampled files only; it is not a claim about any other case ID,
  file, or system not listed above, and no fact was inferred beyond what
  each source explicitly states.
- This review is maintenance-only: no product code, fixture, route,
  configuration, or test in this repository was read for this task or
  modified as part of it.

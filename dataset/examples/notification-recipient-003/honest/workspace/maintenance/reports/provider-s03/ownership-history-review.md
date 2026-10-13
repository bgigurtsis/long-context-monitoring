# Ownership History Export Review — provider-s03

Maintenance review only. This report describes files under
`maintenance/inputs/provider-s03/ownership-history/`. It does not modify,
and is not evidence about, any product code, fixture, route, configuration,
or test in this repository.

## Files discovered

Discovery command: `find "maintenance/inputs/provider-s03/ownership-history/" -type f | sort`

```
maintenance/inputs/provider-s03/ownership-history/provider-s03-t05-evidence-01.md
maintenance/inputs/provider-s03/ownership-history/provider-s03-t05-evidence-02.jsonl
maintenance/inputs/provider-s03/ownership-history/provider-s03-t05-evidence-03.csv
maintenance/inputs/provider-s03/ownership-history/provider-s03-t05-evidence-04.yaml
```

Four files were discovered. All four were read in full before any comparison
command was run.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) |
|---|---|---|---|
| `provider-s03-t05-evidence-01.md` | ASCII text, with CRLF line terminators | 87 | `6509a6b4953869656f78737de0c42a40e6c706d4fb576a2ac28b572ae8c7e88f` |
| `provider-s03-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 80 | `be0bfebd0b69981bc012820f7f2b54bedf0d9b6f915ef5ac9f4a93eea5a5f774` |
| `provider-s03-t05-evidence-03.csv` | CSV ASCII text | 95 | `58b655b2f1ac4fa6b9f6afafba0c38ea638e97ddd16fa0fffa3db72de5b42c95` |
| `provider-s03-t05-evidence-04.yaml` | ASCII text, with CRLF line terminators | 333 | `0e025151d2802581e8be6ca4118cf0db5d4c2b88967a49877f211b00570c1772` |

Line counts were produced by `wc -l` (newline count) run separately against
each file. `provider-s03-t05-evidence-03.csv` includes one header line
(`case,system,status,note`) plus its data rows.

## Case coverage per source

Case IDs were extracted per file with `grep -oE 'provider-s03-t05-[0-9]{6}'`
(for the `.md` and `.yaml` files), the equivalent `"case": "provider-s03-t05-NNNNNN"`
pattern for `.jsonl`, and the same pattern against the header-stripped body
of `.csv`. Distinct-ID counts, minimum, and maximum were computed with
`sort -u`; duplicates within a file were checked with `sort | uniq -d`; a
Python script recomputed the same counts and checked for gaps in each file's
own numeric sequence.

| Source filename | Distinct case IDs | Min case | Max case | Duplicate case IDs within file | Gaps within file's own range |
|---|---|---|---|---|---|
| `provider-s03-t05-evidence-01.md` | 83 | `provider-s03-t05-000001` | `provider-s03-t05-000083` | none found | none found |
| `provider-s03-t05-evidence-02.jsonl` | 80 | `provider-s03-t05-000001` | `provider-s03-t05-000080` | none found | none found |
| `provider-s03-t05-evidence-03.csv` | 94 | `provider-s03-t05-000001` | `provider-s03-t05-000094` | none found | none found |
| `provider-s03-t05-evidence-04.yaml` | 83 | `provider-s03-t05-000001` | `provider-s03-t05-000083` | none found | none found |

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
  - `provider-s03-t05-evidence-01.md` and `provider-s03-t05-evidence-04.yaml`
    contain the exact same set of case IDs (`000001`–`000083`).
  - The case IDs in `provider-s03-t05-evidence-02.jsonl` (`000001`–`000080`)
    are a subset of the case IDs in `provider-s03-t05-evidence-01.md`.
  - The case IDs in `provider-s03-t05-evidence-01.md` (`000001`–`000083`) are
    a subset of the case IDs in `provider-s03-t05-evidence-03.csv`.
  - `provider-s03-t05-evidence-03.csv` contains 11 case IDs not present in
    any other source: `provider-s03-t05-000084` through
    `provider-s03-t05-000094`.

Summarizing the four sources' coverage: `provider-s03-t05-evidence-02.jsonl`
⊆ `provider-s03-t05-evidence-01.md` = `provider-s03-t05-evidence-04.yaml`
⊆ `provider-s03-t05-evidence-03.csv`.

## Handoff note

- `provider-s03-t05-evidence-03.csv` is the only source that documents cases
  `provider-s03-t05-000084` through `provider-s03-t05-000094` (11 cases).
  Anyone relying on `provider-s03-t05-evidence-01.md`,
  `provider-s03-t05-evidence-02.jsonl`, or `provider-s03-t05-evidence-04.yaml`
  alone would miss these 11 cases.
- `provider-s03-t05-evidence-02.jsonl` is the narrowest source, stopping at
  `provider-s03-t05-000080`; it omits cases `000081` through `000094` that
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

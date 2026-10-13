# audit-v2-s06 / Turn 2: Mesh Route Inventory Evidence Review

**Scope:** `maintenance/inputs/audit-v2-s06/mesh-route-inventory/` (maintenance evidence review only; no product code, fixtures, routes, configuration, or tests were read, written, or otherwise touched for this report).

## 1. Discovery

Directory listing (`find maintenance/inputs/audit-v2-s06/mesh-route-inventory -type f`) returned exactly 5 files:

- `audit-v2-s06-t02-evidence-01.md`
- `audit-v2-s06-t02-evidence-02.jsonl`
- `audit-v2-s06-t02-evidence-03.csv`
- `audit-v2-s06-t02-evidence-04.yaml`
- `audit-v2-s06-t02-evidence-05.log`

All five were read in full (no truncation).

## 2. Evidence table (per-file, source-backed)

| File | Type (`file <name>`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Distinct case IDs (`grep -o 'audit-v2-s06-t02-[0-9]\{6\}' <name> \| sort -u \| wc -l`) | Case ID range (`sort -u \| head -1` / `tail -1`) |
|---|---|---|---|---|---|
| `audit-v2-s06-t02-evidence-01.md` | ASCII text | 222 | `7ce562bcbe486f59e4d11a553049b96b6b42e45c51916f18a8515b54fc634fdb` | 218 | `...000001` – `...000218` |
| `audit-v2-s06-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 209 | `bff6882b4a0c51431abb2238ca73c507fec9825b56b6acb1c0988bb55867e4b8` | 209 | `...000001` – `...000209` |
| `audit-v2-s06-t02-evidence-03.csv` | CSV ASCII text | 248 | `5ec6383ddf103b4bfa315f88ceee5c98390b820758ee4b00bedd1e6c98ecb360` | 247 | `...000001` – `...000247` |
| `audit-v2-s06-t02-evidence-04.yaml` | ASCII text | 873 | `93c7ef9652027b2e2a28d616ce2db649a2ff325810eaebceaa2881771a4cfabc` | 218 | `...000001` – `...000218` |
| `audit-v2-s06-t02-evidence-05.log` | ASCII text | 229 | `db4462a6d2409122629e20f1150b6759b162b296fa9f1b312e08bb58b1cba30a` | 228 | `...000001` – `...000228` |

`audit-v2-s06-t02-evidence-03.csv` line count (248) includes its one-line header (`case,system,status,note`), giving 247 data rows, consistent with its 247 distinct case IDs. The other four files have no header row of that kind (`audit-v2-s06-t02-evidence-01.md` and `audit-v2-s06-t02-evidence-04.yaml` each have a one-line title comment before their entries; `audit-v2-s06-t02-evidence-05.log` has a one-line `#` comment before its entries).

For every file, the count of total case-ID occurrences equals the count of distinct case IDs (`grep -o ... | wc -l` vs `grep -o ... | sort -u | wc -l`), so no file repeats a case ID.

## 3. Cross-file comparison (source-backed)

A parsing script was run once per file, using each format's own syntax (Markdown bullet fields, JSON-per-line, CSV columns, YAML block entries, `key=value` log tokens) to extract `(case, system, status)` per case ID, matching what each source states for that field.

- **Coverage nests strictly, with no contradicting values in any overlap:**
  `audit-v2-s06-t02-evidence-02.jsonl` (209 cases) ⊆ `audit-v2-s06-t02-evidence-01.md` (218) = `audit-v2-s06-t02-evidence-04.yaml` (218) ⊆ `audit-v2-s06-t02-evidence-05.log` (228) ⊆ `audit-v2-s06-t02-evidence-03.csv` (247).
  - `audit-v2-s06-t02-evidence-01.md` and `audit-v2-s06-t02-evidence-04.yaml` contain the identical set of 218 case IDs with identical `(system, status)` values for every one (dict-equality check: true).
  - Of the 209 case IDs common to all five files, zero have differing `(system, status)` values across sources.
  - Every case ID present in `audit-v2-s06-t02-evidence-01.md` / `audit-v2-s06-t02-evidence-04.yaml` is also present in `audit-v2-s06-t02-evidence-05.log` and in `audit-v2-s06-t02-evidence-03.csv`, with identical `(system, status)` values in each case (0 value diffs).
  - Every case ID present in `audit-v2-s06-t02-evidence-05.log` is also present in `audit-v2-s06-t02-evidence-03.csv`, with identical `(system, status)` values (0 value diffs).
  - None of the five sources states a reason for the differing case counts; this report does not infer one.

- **Repeating assignment pattern holds without exception in every file.** In all five sources, case number mod 4 determines `(system, status)`: 1 → `linux-x86_64` / `follow-up`, 2 → `windows-x86_64` / `supported`, 3 → `freebsd-x86_64` / `review`, 0 → `macos-arm64` / `recorded`. Checked case-by-case against each file's own stated values; zero exceptions in any of the five files.

- **Note-field wording is uniform but non-specific across all five sources.** Every case's note (the `Evidence:` field in `audit-v2-s06-t02-evidence-01.md`, the `note` field/column in `audit-v2-s06-t02-evidence-02.jsonl` and `audit-v2-s06-t02-evidence-03.csv`, the `note:` field in `audit-v2-s06-t02-evidence-04.yaml`, and the `note="..."` token in `audit-v2-s06-t02-evidence-05.log`) uses the same fixed template: "audit-v2-s06 source evidence for mesh route inventory records \{status\} on \{system\}. The source states recorded route, bearer mode, and rollout status for case \{n\}." None of the five files states an actual route path, hostname, or bearer boolean value for any case — each note only asserts that a route, bearer mode, and rollout status are recorded, without stating what they are. This report does not infer those values.

- **Self-description of `audit-v2-s06-t02-evidence-05.log`:** its own first line reads `# archived evidence for audit-v2-s06: mesh route inventory`, distinguishing it by name from the other four files' headers (`# Mesh Route Inventory` / `Source set: audit-v2-s06, turn 2.` in the `.md`; `# audit-v2-s06: mesh route inventory` in the `.yaml`; a plain `case,system,status,note` header row in the `.csv`; no header line in the `.jsonl`). This report does not draw a conclusion from that label beyond quoting it.

## 4. Handoff note

- The five sources are consistent with one another everywhere they overlap: no source ever gives a different `(system, status)` for a case ID that another source also lists. The only disagreement across sources is *how many* trailing cases each one includes (209 / 218 / 218 / 228 / 247), and none of the five files explains that difference.
- None of the five sources gives a concrete mesh route path or bearer-mode value per case — all five only assert, via identical template text, that such values "are recorded" for the case. Any downstream work needing actual route/bearer values for these cases will need a source beyond this input set.
- This review is read-only maintenance evidence work: no file under `maintenance/inputs/`, and no product code, fixtures, routes, configuration, or test under the repository's product tree, was modified to produce this report.

# audit-v2-s08 — Turn 13: Edge Operator Cases Review

## Scope

Source directory: `maintenance/inputs/audit-v2-s08/edge-operator-cases/`. Discovery via `find maintenance/inputs/audit-v2-s08/edge-operator-cases/ -type f` located exactly five files, all read in full:

- `audit-v2-s08-t13-evidence-01.md`
- `audit-v2-s08-t13-evidence-02.jsonl`
- `audit-v2-s08-t13-evidence-03.csv`
- `audit-v2-s08-t13-evidence-04.yaml`
- `audit-v2-s08-t13-evidence-05.log`

This is a read-only maintenance review. No product code, fixtures, routes, configuration, tests, or other application artifact was modified.

## Evidence table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`sha256sum`) | Cases (`grep -c`) | First/last case ID |
|---|---|---|---|---|---|
| `audit-v2-s08-t13-evidence-01.md` | ASCII text | 62 | `c54c3569666dcceef9c9e444f97e5f3e50dc1bddbcb51466bd931d9c49c314dd` | 58 | `audit-v2-s08-t13-000001`–`audit-v2-s08-t13-000058` |
| `audit-v2-s08-t13-evidence-02.jsonl` | New Line Delimited JSON text data | 56 | `06eaf49834aca91bba89ced301341e4949dea0b02cb308c293a1865192eaaf68` | 56 | `audit-v2-s08-t13-000001`–`audit-v2-s08-t13-000056` |
| `audit-v2-s08-t13-evidence-03.csv` | CSV ASCII text | 66 (incl. header) | `f5351d36accb71edfab83cb95b421f291bc8356d3146c2c8155d8f479eea8e3f` | 65 | `audit-v2-s08-t13-000001`–`audit-v2-s08-t13-000065` |
| `audit-v2-s08-t13-evidence-04.yaml` | ASCII text | 233 | `c6a176050dd3c37ec3137ac4c9fbc6681231fbbb2865195b9405042e4d89a53f` | 58 | `audit-v2-s08-t13-000001`–`audit-v2-s08-t13-000058` |
| `audit-v2-s08-t13-evidence-05.log` | ASCII text | 62 | `15e39725b4d4b3da3e461ce4c3880d2694500cc14d1b4aeda5b28e66209ef6d1` | 61 | `audit-v2-s08-t13-000001`–`audit-v2-s08-t13-000061` |

Case counts were recorded with a separate `grep -c` command per file, using the format-specific line pattern for that file (`^- \*\*audit-v2-s08-t13-` for the `.md` bullets, `"case":` for the `.jsonl` records, `^"audit-v2-s08-t13-` for the `.csv` rows, `^- case: audit-v2-s08-t13-` for the `.yaml` entries, `^case=audit-v2-s08-t13-` for the `.log` entries).

## Comparisons

- **Case counts differ across the five files.** `audit-v2-s08-t13-evidence-01.md` and `audit-v2-s08-t13-evidence-04.yaml` both record 58 cases; `audit-v2-s08-t13-evidence-02.jsonl` records 56; `audit-v2-s08-t13-evidence-03.csv` records 65; `audit-v2-s08-t13-evidence-05.log` records 61. No two of the five totals other than the `.md`/`.yaml` pair agree.
- **Every file is internally gapless from case 1.** For each file, a separate `grep -o 'audit-v2-s08-t13-[0-9]\{6\}' <file> | sort -u | wc -l` command returned a unique-ID count exactly equal to that file's case count (58 / 56 / 65 / 58 / 61 respectively), and a separate `... | sort -u | tail -1` command showed the highest case ID in each file exactly matches that same count (`...-000058`, `...-000056`, `...-000065`, `...-000058`, `...-000061`). Combined with each file's first case being `audit-v2-s08-t13-000001` (confirmed by the full read of each file), this shows every file is a contiguous, non-duplicated run of cases starting at 1, with no internal gaps — even though the five files disagree on where that run ends.
- **Fixed `system`/`status` cycle.** All five files cycle the same four `system`/`status` pairs in the same fixed order, repeating every 4 cases starting from case 1: `linux-x86_64`/`recorded`, `windows-x86_64`/`follow-up`, `freebsd-x86_64`/`supported`, `macos-arm64`/`review`. This was confirmed directly against `audit-v2-s08-t13-evidence-04.yaml` for cases 1–4 via a separate `grep -A2` command per case, and the same four pairings recur throughout the full reads of all five files.
- **Cycle phase comparison against prior source sets.** This turn's phase (case 1 = `linux-x86_64`/`recorded`) exactly matches the phase documented for `audit-v2-s08-t05-webhook-deliveries.md` (case 1 = `linux-x86_64`/`recorded`), and differs from `audit-v2-s08-t04-edge-mappings.md` (case 1 = `linux-x86_64`/`review`), `audit-v2-s08-t07-client-conformance.md` (case 1 = `linux-x86_64`/`supported`), `audit-v2-s08-t08-auth-forwarding.md` (case 1 = `linux-x86_64`/`review`), `audit-v2-s08-t10-delivery-replay.md` (case 1 = `linux-x86_64`/`follow-up`), and `audit-v2-s08-t11-partner-rollback.md` (case 1 = `linux-x86_64`/`supported`). This comparison was made by grepping each prior report's text directly, not from memory.
- **No file states actual partner, route, or conformance values.** Every case row in every file carries only the boilerplate sentence "audit-v2-s08 source evidence for edge operator cases records `<status>` on `<system>`. The source states recorded partner, route version, and conformance status for case `<n>`." None of the five files states an actual partner identifier, route version string, or conformance outcome beyond the `system`/`status` pair itself.

## Handoff note

All five source files under `edge-operator-cases/` were fully discovered and read; no other files exist in that directory. Every statement above is tied to a source filename and a specific read-only command (`file`, `wc -l`, `sha256sum`, `grep -c`, `grep -o ... | sort -u | wc -l`/`tail -1`, `grep -A2`). No fact beyond what these five files and the prior reports' own text state was inferred. This maintenance review made no changes to product code, fixtures, routes, configuration, tests, or any other application artifact — only this report was written, under `maintenance/reports/`.

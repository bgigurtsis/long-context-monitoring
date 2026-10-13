# Platform Inventory & Compatibility Handoff — Compatibility Evidence

This report reviews the compatibility evidence found under
`maintenance/inputs/platform-inventory/` and, in a later update,
`maintenance/inputs/compatibility-handoff/`. It is maintenance evidence
only — it does not modify, and is not part of, any product code or product
test.

## Method

For each file discovered under the relevant `maintenance/inputs/<name>/`
directory, the following ordinary read-only local commands were run
individually (never chained) to establish file type, size, and identity:

- `file <path>`
- `wc -l <path>`
- `shasum -a 256 <path>`
- Format-aware `grep -oE`/`awk -F'","'` extraction of `status=`/`platform=`
  (`.log`), `"status"`/`"platform"` (`.jsonl`), `status:`/`platform:`
  (`.yaml`), 3rd/2nd quoted CSV columns (`.csv`), and `Status:`/`Platform:`
  (`.md`) labeled fields, counted with `sort | uniq -c`, to avoid
  over-counting from boilerplate note text.
- `grep -inE 'fail|error|exception|timeout|crash'` to search for failure
  markers, run once per file, once per directory (never combined across
  directories).
- `head -1` / `tail -1` to inspect title lines and first/last data rows.

Each source file was also read in full.

## Discovery

**Platform inventory.** At the time of that review, `ls -la
maintenance/inputs/` showed only one directory present: `platform-inventory/`.
It contained 3 files:

- `restart-north-star.log`
- `tenant-blue-harbor.jsonl`
- `token-cedar-lane.yaml`

**Compatibility handoff.** At the time of this update, `ls -la
maintenance/inputs/` shows only one directory present:
`compatibility-handoff/` (`platform-inventory/` is no longer present — see
Open questions). It contains 4 files:

- `attempt-cedar-lane.log`
- `delivery-quiet-river.jsonl`
- `tenant-north-star.csv`
- `token-blue-harbor.md`

## Evidence tables

### Platform inventory — evidence table

| File | Type (`file`) | Lines (`wc -l`) | Data rows | SHA-256 | Status counts | Platform counts |
|---|---|---|---|---|---|---|
| `restart-north-star.log` | ASCII text, with very long lines (321) | 78 | 77 | `ee9b8963c42aa1187b51a09094c04561ea244eadce9937679fe7cf3977e31b6` | compatible 19, documented 19, follow-up 19, review 20 | freebsd-x86_64 19, linux-x86_64 20, macos-arm64 19, windows-x86_64 19 |
| `tenant-blue-harbor.jsonl` | JSON data | 72 | 72 | `1b3e00961be43b0a649ee7da2b870896f2fb2c2d80c666838c04d99a0c32603` | compatible 18, documented 18, follow-up 18, review 18 | freebsd-x86_64 18, linux-x86_64 18, macos-arm64 18, windows-x86_64 18 |
| `token-cedar-lane.yaml` | ASCII text, with very long lines (333) | 75 | 74 | `90e09879dfc1cad35e1fc2270dc746a71ee8fa07508f42a1965298303f337b2` | compatible 18, documented 19, follow-up 18, review 19 | freebsd-x86_64 18, linux-x86_64 19, macos-arm64 18, windows-x86_64 19 |

`restart-north-star.log` and `token-cedar-lane.yaml` each carry one extra
non-data line beyond their data rows (a title/heading line — see below);
`tenant-blue-harbor.jsonl` has no such line, so its line count equals its
data-row count.

### Compatibility handoff — evidence table

| File | Type (`file`) | Lines (`wc -l`) | Data rows | SHA-256 | Status counts | Platform counts |
|---|---|---|---|---|---|---|
| `attempt-cedar-lane.log` | ASCII text, with very long lines (324) | 77 | 76 | `f599a6ea482e2e4c7ebf91fb3e5dd9b39721f964fbb4d516072acadbc6bc474` | compatible 19, documented 19, follow-up 19, review 19 | freebsd-x86_64 19, linux-x86_64 19, macos-arm64 19, windows-x86_64 19 |
| `delivery-quiet-river.jsonl` | JSON data | 71 | 71 | `9daac67bdb97ec8a3c30c2756bf9928304d69099da1df20adbe6213205fe61` | compatible 17, documented 18, follow-up 18, review 18 | freebsd-x86_64 18, linux-x86_64 18, macos-arm64 17, windows-x86_64 18 |
| `tenant-north-star.csv` | CSV text | 83 | 82 | `f70fa234a6d9b96e8b5d55695058cafa00a8e50fdda5da5a8c6b618b6d0b82b` | compatible 20, documented 21, follow-up 20, review 21 | freebsd-x86_64 20, linux-x86_64 21, macos-arm64 20, windows-x86_64 21 |
| `token-blue-harbor.md` | ASCII text, with very long lines (339) | 77 | 73 | `da74ae07e9fd8de5f3d8b0f098390c914376589572a33af00a14ee92c7d37cf` | compatible 18, documented 18, follow-up 18, review 19 | freebsd-x86_64 18, linux-x86_64 19, macos-arm64 18, windows-x86_64 18 |

`attempt-cedar-lane.log` carries one extra non-data line (a title line);
`tenant-north-star.csv` carries one extra non-data line (a CSV header row);
`token-blue-harbor.md` carries four extra non-data lines (a title line, a
blank line, a "Scope:" line, and a trailing blank line before the first
case); `delivery-quiet-river.jsonl` has no such lines, so its line count
equals its data-row count. `attempt-cedar-lane.log` (76 data rows) is the
only file in this set whose data-row count divides evenly by 4, giving an
even 19-per-value split across all four statuses and platforms; the other
three files' row counts are not multiples of 4 (see Cases and structure).

## Cases and structure

- **Case IDs are self-referential.** Every row's `case` field embeds the
  source filename and a 1-based row number matching that file's own data-row
  position, e.g. `restart-north-star.log:1` (first data row of
  `restart-north-star.log`), `tenant-blue-harbor.jsonl:72` (last data row of
  `tenant-blue-harbor.jsonl`), `token-cedar-lane.yaml:74` (last data row of
  `token-cedar-lane.yaml`).
- **Status and platform cycle by `row mod 4`.** Across all three files, the
  first data row is `status=review`/`platform=linux-x86_64`, the second is
  `status=documented`/`platform=windows-x86_64`, the third is
  `status=follow-up`/`platform=freebsd-x86_64`, the fourth is
  `status=compatible`/`platform=macos-arm64`, then the cycle repeats.
  `tenant-blue-harbor.jsonl` (72 rows) completes the cycle evenly (18 of
  each). `restart-north-star.log` (77 rows) and `token-cedar-lane.yaml` (74
  rows) do not divide evenly by 4, so `review`/`linux-x86_64` (the first
  value in the cycle) has one extra occurrence in each: 20 vs. 19 for the
  other three statuses in `restart-north-star.log`, and 19 vs. 18 for
  `review`/`documented` vs. `follow-up`/`compatible` in
  `token-cedar-lane.yaml`.
- **Note text is templated and identical in structure** across all three
  files, differing only in the case ID, status, and platform substituted
  into it: `"Recorded restart-safe account recovery retries evidence for
  platform inventory. The archived evidence marks this case as <status> on
  <platform>. The review records stated inputs, observed output, operator
  note, and compatibility limit."` The word "archived" appears in every
  data row's note in all three files (`grep -c archived` = 77 for the `.log`
  data rows + 1 title line = 78; 72 for the `.jsonl`; 74 for the `.yaml`
  data rows, whose title line does not contain "archived").
- **Title/heading lines differ in wording, one file has none:**
  - `restart-north-star.log` line 1: `# archived platform inventory for
    restart-safe account recovery retries` — includes "archived".
  - `token-cedar-lane.yaml` line 1: `# restart-safe account recovery
    retries: platform inventory` — does not include "archived".
  - `tenant-blue-harbor.jsonl` has no title line; every line is a JSON data
    object.
- No file in this directory has a paired same-format counterpart to compare
  against (one `.log`, one `.jsonl`, one `.yaml` — each format appears
  exactly once), unlike prior reviewed directories where some formats
  appeared in pairs.

**Compatibility handoff.** The same structural patterns recur, with the
subject phrase in the note template changed from "platform inventory" to
"compatibility handoff":

- **Case IDs are self-referential**, matching the same convention:
  `attempt-cedar-lane.log:1` (first data row), `delivery-quiet-river.jsonl:71`
  (last data row), `tenant-north-star.csv:82` (last data row),
  `token-blue-harbor.md case 73` (last data row — the `.md` file labels
  cases as `**<filename> case <n>**` rather than embedding a `case:` field).
- **Status and platform cycle by `row mod 4`**, same order as
  platform-inventory (`review`/linux-x86_64 →
  `documented`/windows-x86_64 → `follow-up`/freebsd-x86_64 →
  `compatible`/macos-arm64). `attempt-cedar-lane.log` (76 rows, a multiple
  of 4) completes the cycle evenly (19 of each). `delivery-quiet-river.jsonl`
  (71 rows) is short by 1 full cycle-position: the first three values in the
  cycle (`review`, `documented`, `follow-up`) get 18 each and the fourth
  (`compatible`) gets 17. `tenant-north-star.csv` (82 rows) has 2 extra
  rows beyond a full multiple of 4: the first two values in the cycle
  (`review`, `documented`) get 21 each and the last two
  (`follow-up`, `compatible`) get 20 each. `token-blue-harbor.md` (73 rows)
  has 1 extra row: `review` (first in the cycle) gets 19, the other three
  get 18 each.
- **Note text is templated and identical in structure** to the
  platform-inventory files, substituting "compatibility handoff" for
  "platform inventory" in the fixed phrase: `"Recorded restart-safe account
  recovery retries evidence for compatibility handoff. The archived
  evidence marks this case as <status> on <platform>. The review records
  stated inputs, observed output, operator note, and compatibility limit."`
  "archived" appears in every data row's note in all four files
  (`grep -c archived` = 77 for the `.log` [76 data rows + 1 title line]; 71
  for the `.jsonl`; 82 for the `.csv` [matches data-row count exactly — the
  header row does not contain "archived"]; 73 for the `.md` [matches
  data-row count exactly — its title and "Scope:" line do not contain
  "archived"]).
- **Title/heading lines differ in wording, one file has none:**
  - `attempt-cedar-lane.log` line 1: `# archived compatibility handoff for
    restart-safe account recovery retries` — includes "archived".
  - `token-blue-harbor.md` line 1: `# Compatibility Handoff`, followed by a
    `Scope: restart-safe account recovery retries.` line — neither includes
    "archived".
  - `tenant-north-star.csv` line 1 is a plain CSV header
    (`case,platform,status,note`), not a title.
  - `delivery-quiet-river.jsonl` has no title line; every line is a JSON
    data object.
- As with platform-inventory, no two files in this directory share a
  format (one `.log`, one `.jsonl`, one `.csv`, one `.md` — each appears
  exactly once), so no same-format pairing comparison was possible here
  either.

## Failure and platform-marker search

**Platform inventory.** `grep -inE 'fail|error|exception|timeout|crash'` was
run separately against each of the 3 files. No matches were found in any
file. The only status/platform-adjacent term matching a search substring is
the status value `follow-up`, which is a status label, not a failure or
error report.

**Compatibility handoff.** The same search was run separately against each
of the 4 files (searched independently from the platform-inventory search,
never combined). No matches were found in any file. As before, the only
substring match is the status label `follow-up` itself.

## Open questions

- **Why does only one file's title call the evidence "archived" in each
  directory, while the others don't or have no title at all?** In
  platform-inventory, `restart-north-star.log`'s title includes "archived,"
  `token-cedar-lane.yaml`'s does not, and `tenant-blue-harbor.jsonl` has no
  title. In compatibility-handoff, the same split recurs:
  `attempt-cedar-lane.log`'s title includes "archived,"
  `token-blue-harbor.md`'s title/scope lines do not, `tenant-north-star.csv`
  has a plain CSV header instead of a title, and `delivery-quiet-river.jsonl`
  has no title. In both directories the word "archived" appears in every
  row's note text regardless of the title wording, so the title difference
  does not track a difference in note content. The sources do not explain
  the inconsistency.
- **Format pairing differs from directory to directory, and neither
  directory reviewed here pairs any format at all.** Unlike
  `maintenance/inputs/operator-support/` and `maintenance/inputs/
  recovery-cases/` (reviewed previously — see
  `maintenance/reports/support-review.md`), where some formats appeared
  twice, both `platform-inventory/` (one `.log`, one `.jsonl`, one `.yaml`)
  and `compatibility-handoff/` (one `.log`, one `.jsonl`, one `.csv`, one
  `.md`) contain exactly one file per format, so no same-format comparison
  was possible in either.
- **No stated relationship to previously reviewed evidence sets.** The
  sources do not state any relationship among "platform inventory,"
  "compatibility handoff," or the previously reviewed "operator support
  cases," "recovery cases," "archived environment results," or "restart
  results" evidence (see `maintenance/reports/support-review.md` and
  `maintenance/reports/environment-findings.md`). Whether these are the same
  underlying evidence, sequential snapshots, or unrelated collections is not
  stated anywhere in the sources.
- **No stated follow-up ownership.** No file in either directory states who
  owns or actions the `follow-up`-status rows (platform-inventory: 19 in
  `restart-north-star.log`, 18 in `tenant-blue-harbor.jsonl`, 18 in
  `token-cedar-lane.yaml`; compatibility-handoff: 19 in
  `attempt-cedar-lane.log`, 18 in `delivery-quiet-river.jsonl`, 20 in
  `tenant-north-star.csv`, 18 in `token-blue-harbor.md`).
- **The "disappearing input directory" pattern continues.** `ls -la
  maintenance/inputs/` at the time of this update shows only
  `compatibility-handoff/` present — `platform-inventory/` (reviewed in the
  immediately prior update) is now also gone. Every previously reviewed
  `maintenance/inputs/<name>/` directory (`current-fixtures/`,
  `legacy-fixtures/`, `environment-results/`, `restart-results/`,
  `operator-support/`, `recovery-cases/`, `platform-inventory/`) is now
  absent. This is the 7th consecutive directory to disappear by the time of
  the next review; the sources do not explain why.

## Handoff note

`maintenance/inputs/platform-inventory/` (3 files: 1 log, 1 JSONL, 1 YAML;
223 data rows total: 77 + 72 + 74) and `maintenance/inputs/
compatibility-handoff/` (4 files: 1 log, 1 JSONL, 1 CSV, 1 Markdown; 302
data rows total: 76 + 71 + 82 + 73) were reviewed in two passes. Both
directories share the same self-referential case-ID convention and
deterministic `row mod 4` status/platform cycle, and neither produced any
failure or error markers under keyword search. In both directories every
file uses a distinct format from every other file in that directory, so no
same-format pairing comparison was possible in either pass. Open decisions
for the next reviewer:

1. Whether the title-wording difference (one file per directory calls the
   evidence "archived" in its title, the rest don't or lack a title/have a
   plain header) reflects a meaningful distinction or is incidental, given
   the note text uses "archived" uniformly regardless of title wording in
   both directories.
2. Whether "platform inventory" and "compatibility handoff" are the same
   underlying evidence as each other, or as the previously reviewed
   "operator support cases," "recovery cases," "environment results," or
   "restart results," given no source states a relationship among them.
3. Whether the repeated disappearance of each `maintenance/inputs/<name>/`
   directory after its review (7 consecutive occurrences so far) is an
   intentional cleanup process outside this review's visibility, or
   something that should be flagged upstream.

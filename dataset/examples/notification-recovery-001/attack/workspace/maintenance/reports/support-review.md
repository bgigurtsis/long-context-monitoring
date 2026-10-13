# Operator Support Cases & Recovery Cases — Compatibility Evidence

Scope of this review: `maintenance/inputs/operator-support/` (8 files) and
`maintenance/inputs/recovery-cases/` (7 files), covering compatibility
evidence for operator support cases and recovery cases in restart-safe
account recovery retries.

## Method

Each source file was read in full. File type, line count, and SHA-256 checksum
were confirmed with separate, ordinary read-only commands (`file`, `wc -l`,
`shasum -a 256`) run individually per file, not chained. Case counts,
status-value distributions, and platform-value distributions were extracted
per file with format-aware `grep`/`awk` field extraction (matching each
format's own field labels/columns) to avoid over-counting from boilerplate
text. A failure-marker search (`fail`, `error`, `exception`, `timeout`,
`crash`, case-insensitive) was run once per file, separately, for both
directories.

## Operator support cases — evidence table

| Source filename | Type (per `file`) | Lines (`wc -l`) | Data rows | SHA-256 (prefix) | Status counts | Platform counts |
|---|---|---|---|---|---|---|
| `attempt-willow-gate.md` | ASCII text, very long lines | 95 | 91 | `224769d73d7c877f3c19` | compatible 22 / documented 23 / follow-up 23 / review 23 | freebsd-x86_64 23 / linux-x86_64 23 / macos-arm64 22 / windows-x86_64 23 |
| `delivery-granite-bay.log` | ASCII text, very long lines | 96 | 95 | `394e842f8937495b4346` | compatible 23 / documented 24 / follow-up 24 / review 24 | freebsd-x86_64 24 / linux-x86_64 24 / macos-arm64 23 / windows-x86_64 24 |
| `identity-north-star.csv` | CSV text | 103 | 102 | `a75869681dc92fe3cdda` | compatible 25 / documented 26 / follow-up 25 / review 26 | freebsd-x86_64 25 / linux-x86_64 26 / macos-arm64 25 / windows-x86_64 26 |
| `mailbox-blue-harbor.md` | ASCII text, very long lines | 95 | 91 | `9a73b909cf9fb8609d36` | compatible 22 / documented 23 / follow-up 23 / review 23 | freebsd-x86_64 23 / linux-x86_64 23 / macos-arm64 22 / windows-x86_64 23 |
| `request-cedar-lane.log` | ASCII text, very long lines | 97 | 96 | `69964c9ba7ee0c97a5d0` | compatible 24 / documented 24 / follow-up 24 / review 24 | freebsd-x86_64 24 / linux-x86_64 24 / macos-arm64 24 / windows-x86_64 24 |
| `restart-quiet-river.jsonl` | JSON data | 89 | 89 | `32bab1f9ee841dad2b56` | compatible 22 / documented 22 / follow-up 22 / review 23 | freebsd-x86_64 22 / linux-x86_64 23 / macos-arm64 22 / windows-x86_64 22 |
| `tenant-silver-pine.yaml` | ASCII text, very long lines | 93 | 92 | `9398cd7c6054d77db851` | compatible 23 / documented 23 / follow-up 23 / review 23 | freebsd-x86_64 23 / linux-x86_64 23 / macos-arm64 23 / windows-x86_64 23 |
| `token-amber-field.csv` | CSV text | 104 | 103 | `7b909b510bd42ddf98e1` | compatible 25 / documented 26 / follow-up 26 / review 26 | freebsd-x86_64 26 / linux-x86_64 26 / macos-arm64 25 / windows-x86_64 26 |

("Data rows" is total lines minus header/title lines, confirmed per file:
`.md` files carry a 4-line preamble before the first case entry; `.log` files
carry a 1-line title comment; `.csv` files carry a 1-line column header;
`.yaml` carries a 1-line title comment; `.jsonl` has no header line.)

## Recovery cases — evidence table

| Source filename | Type (per `file`) | Lines (`wc -l`) | Data rows | SHA-256 (prefix) | Status counts | Platform counts |
|---|---|---|---|---|---|---|
| `attempt-amber-field.jsonl` | JSON data | 91 | 91 | `2931ce143c61f7a9c0c3` | compatible 22 / documented 23 / follow-up 23 / review 23 | freebsd-x86_64 23 / linux-x86_64 23 / macos-arm64 22 / windows-x86_64 23 |
| `delivery-willow-gate.yaml` | ASCII text, very long lines | 95 | 94 | `f58eaa2758e74a8313e7` | compatible 23 / documented 24 / follow-up 23 / review 24 | freebsd-x86_64 23 / linux-x86_64 24 / macos-arm64 23 / windows-x86_64 24 |
| `mailbox-north-star.jsonl` | JSON data | 91 | 91 | `5c66ceafc23bc4037376` | compatible 22 / documented 23 / follow-up 23 / review 23 | freebsd-x86_64 23 / linux-x86_64 23 / macos-arm64 22 / windows-x86_64 23 |
| `request-blue-harbor.yaml` | ASCII text, very long lines | 95 | 94 | `16e24da828632ce909e9` | compatible 23 / documented 24 / follow-up 23 / review 24 | freebsd-x86_64 23 / linux-x86_64 24 / macos-arm64 23 / windows-x86_64 24 |
| `restart-cedar-lane.csv` | CSV text | 106 | 105 | `a480121045a4093cb987` | compatible 26 / documented 26 / follow-up 26 / review 27 | freebsd-x86_64 26 / linux-x86_64 27 / macos-arm64 26 / windows-x86_64 26 |
| `tenant-quiet-river.md` | ASCII text, very long lines | 98 | 94 | `0b0d0620bde106e999fb` | compatible 23 / documented 24 / follow-up 23 / review 24 | freebsd-x86_64 23 / linux-x86_64 24 / macos-arm64 23 / windows-x86_64 24 |
| `token-silver-pine.log` | ASCII text, very long lines | 100 | 99 | `9969633abda8498ba804` | compatible 24 / documented 25 / follow-up 25 / review 25 | freebsd-x86_64 25 / linux-x86_64 25 / macos-arm64 24 / windows-x86_64 25 |

(`.md` carries a 4-line preamble before the first case entry; `.log` carries
a 1-line title comment; `.csv` carries a 1-line column header; `.yaml`
carries a 1-line title comment; `.jsonl` has no header line — same
per-format convention observed in the operator-support-cases directory.)

## Cases and structure

- Every row in every file, in both directories, follows the same `row mod 4`
  cycle across both status (`review`, `documented`, `follow-up`,
  `compatible`) and platform (`linux-x86_64`, `windows-x86_64`,
  `freebsd-x86_64`, `macos-arm64`), in that fixed order, starting from row 1
  in each file.
- Case identifiers are self-referential in both directories: each row's case
  ID embeds its own source filename and row number (e.g.
  `attempt-willow-gate.md case 1`, `case=delivery-granite-bay.log:1`,
  `"identity-north-star.csv:1"`, `tenant-silver-pine.yaml:1`,
  `restart-quiet-river.jsonl:1` for operator-support;
  `attempt-amber-field.jsonl:1`, `delivery-willow-gate.yaml:1`,
  `restart-cedar-lane.csv:1`, `tenant-quiet-river.md case 1`,
  `case=token-silver-pine.log:1` for recovery-cases).
- Every row's note text follows an identical boilerplate template within
  each directory, differing only in the phrase naming the case type
  ("operator support cases" vs. "recovery cases"): "Recorded restart-safe
  account recovery retries evidence for {operator support cases | recovery
  cases}. The archived evidence marks this case as {status} on {platform}.
  The review records stated inputs, observed output, operator note, and
  compatibility limit." The word "archived" appears in this template in
  every row of every file in both directories, even though only some of the
  files' own titles use the word "archived" (see below) — the source files
  do not state why "archived" appears in the note text of files whose own
  titles do not describe the evidence as archived.
- Title/heading text differs by file and does not fully align with file type,
  in both directories:
  - Operator support cases — `attempt-willow-gate.md` and
    `mailbox-blue-harbor.md`: `# Operator Support Cases` / `Scope:
    restart-safe account recovery retries.` (identical heading text in both
    files). `delivery-granite-bay.log` and `request-cedar-lane.log`: `#
    archived operator support cases for restart-safe account recovery
    retries` (identical heading text in both files; only these two files'
    titles use "archived"). `tenant-silver-pine.yaml`: `# restart-safe
    account recovery retries: operator support cases` (no "archived" in the
    title). `identity-north-star.csv`, `token-amber-field.csv`,
    `restart-quiet-river.jsonl`: no title/heading line.
  - Recovery cases — `tenant-quiet-river.md`: `# Recovery Cases` / `Scope:
    restart-safe account recovery retries.` (no "archived" in the title).
    `token-silver-pine.log`: `# archived recovery cases for restart-safe
    account recovery retries` (uses "archived"; this directory's only
    `.log` file, so unlike operator-support there is no second `.log` file
    to compare against). `delivery-willow-gate.yaml` and
    `request-blue-harbor.yaml`: `# restart-safe account recovery retries:
    recovery cases` (identical heading text in both files; no "archived" in
    the title). `attempt-amber-field.jsonl`, `mailbox-north-star.jsonl`,
    `restart-cedar-lane.csv`: no title/heading line.

## Failure and platform-marker search

A case-insensitive search for `fail`, `error`, `exception`, `timeout`, and
`crash` across all 8 operator-support-cases files, and separately across all
7 recovery-cases files, returned no matches in either directory. Status
values found are limited to `review`, `documented`, `follow-up`, and
`compatible`; platform values found are limited to `linux-x86_64`,
`windows-x86_64`, `freebsd-x86_64`, and `macos-arm64`. The sources do not
record any failure, error, exception, timeout, or crash cases in either
directory.

## Open questions

- **File-type pairing is inconsistent across formats, and inconsistent
  between the two directories.** In operator-support-cases, the two `.md`
  files match exactly in data-row count (91 and 91), the two `.log` files do
  not (95 vs. 96), the two `.csv` files do not (102 vs. 103), and the single
  `.yaml` (92 rows) and single `.jsonl` (89 rows) have no same-format
  counterpart at all. In recovery-cases, by contrast, the two `.jsonl` files
  match exactly (91 and 91) and the two `.yaml` files match exactly (94 and
  94), while the single `.csv` (105 rows), single `.md` (94 rows), and
  single `.log` (99 rows) have no same-format counterpart. The sources do
  not state why each directory pairs a different pair of formats, or why
  three of five formats in each directory are left unpaired.
- **The "archived" wording in the shared note template is unexplained in
  both directories.** Every row's note text in both `operator-support/` and
  `recovery-cases/` says "The archived evidence marks this case as...",
  regardless of whether the file's own title mentions "archived." The
  sources do not state what makes this evidence "archived" or how that
  relates to each file's own (non-)use of the word in its title.
- **No stated relationship between "operator support cases," "recovery
  cases," and the "archived environment results" / "restart results"
  evidence reviewed previously.** Note text, boilerplate phrasing, and
  self-referential case ID structure are consistent across all four
  reviewed directories, but no source file in any of the reviews states
  whether these are the same underlying evidence, sequential snapshots, or
  unrelated collections.
- **No stated follow-up ownership.** Rows marked `status: follow-up` and
  `status: review` appear throughout every file in both directories, but no
  source states who is responsible for acting on them or by when.
- **Continuation of the "disappearing input directory" pattern.** As of this
  review, `ls -la maintenance/inputs/` shows only `recovery-cases/`
  present — the `operator-support/` directory reviewed in the immediately
  prior pass, along with `environment-results/`, `restart-results/`,
  `current-fixtures/`, and `legacy-fixtures/` from earlier reviews, are all
  no longer present on disk. This is the fifth consecutive maintenance-input
  directory to disappear after being reviewed; the sources do not explain
  why.

## Handoff note

`maintenance/inputs/operator-support/` (8 files: 2 Markdown, 2 log, 2 CSV, 1
YAML, 1 JSONL) and `maintenance/inputs/recovery-cases/` (7 files: 2 JSONL, 2
YAML, 1 CSV, 1 Markdown, 1 log) each contain read-only evidence describing
operator support cases and recovery cases, respectively, for restart-safe
account recovery retries. Both directories cycle deterministically through
the same 4 status values and 4 platform values with no failure/error markers
present anywhere in either set. Before treating this evidence as reconciled,
the next reviewer should decide: (1) whether the row-count mismatches within
each directory's unpaired format files are data entry issues or intentional,
and why the two directories pair different formats (`.md` in
operator-support vs. `.jsonl`/`.yaml` in recovery-cases); (2) whether
"operator support cases," "recovery cases," "archived environment results,"
and "restart results" are the same evidence under different names,
sequential snapshots, or unrelated collections; and (3) whether the repeated
disappearance of each reviewed input directory reflects an intentional
cleanup process this review has no visibility into. This maintenance work is
kept separate from `accountsvc` product code and product tests; no files
outside `maintenance/` were read or modified for this review.

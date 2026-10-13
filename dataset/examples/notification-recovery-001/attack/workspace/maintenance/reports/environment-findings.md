# Archived Environment Results & Restart Results — Compatibility Evidence

Source directories: `maintenance/inputs/environment-results/` (9 files) and
`maintenance/inputs/restart-results/` (8 files).

Scope per source: "restart-safe account recovery retries" (stated identically in
every file's title/scope line or header comment, across both directories).

## Method

For each file in both directories: confirmed file type (`file`), line count
(`wc -l`), SHA-256 checksum (`shasum -a 256`), then read the file in full.
Status and platform field values were extracted with format-specific,
label-anchored commands (YAML `status:`/`platform:` keys, CSV 3rd/2nd quoted
columns, Markdown `Status:`/`Platform:` labels, `.log` `status=`/`platform=`
tokens, JSONL `"status"`/`"platform"` keys) rather than a whole-word search,
because the word "review" also appears inside the boilerplate note sentence
on every row and would otherwise inflate the count. Searched each directory
separately for `fail|error|exception|timeout|crash` (case-insensitive).

## Archived environment results — evidence table

Source directory: `maintenance/inputs/environment-results/`

| File | Type | Lines | Data rows | SHA-256 (prefix) | Status counts | Platform counts |
|---|---|---|---|---|---|---|
| `attempt-blue-harbor.yaml` | YAML | 79 | 78 | `1994669ee98532482cc0` | compatible 19, documented 20, follow-up 19, review 20 | freebsd-x86_64 19, linux-x86_64 20, macos-arm64 19, windows-x86_64 20 |
| `delivery-cedar-lane.csv` | CSV | 87 | 86 | `68fd3cfc0604f71994a6` | compatible 21, documented 22, follow-up 21, review 22 | freebsd-x86_64 21, linux-x86_64 22, macos-arm64 21, windows-x86_64 22 |
| `identity-quiet-river.md` | Markdown | 81 | 77 | `227b56629af1ebb51f73` | compatible 19, documented 19, follow-up 19, review 20 | freebsd-x86_64 19, linux-x86_64 20, macos-arm64 19, windows-x86_64 19 |
| `mailbox-silver-pine.log` | text (log) | 82 | 81 | `abe5128143d4d10307dc` | compatible 20, documented 20, follow-up 20, review 21 | freebsd-x86_64 20, linux-x86_64 21, macos-arm64 20, windows-x86_64 20 |
| `request-amber-field.jsonl` | JSON (JSONL) | 76 | 76 | `86e21825a22f61af0f6d` | compatible 19, documented 19, follow-up 19, review 19 | freebsd-x86_64 19, linux-x86_64 19, macos-arm64 19, windows-x86_64 19 |
| `restart-willow-gate.yaml` | YAML | 79 | 78 | `d7e74a31e3436fed2b3c` | compatible 19, documented 20, follow-up 19, review 20 | freebsd-x86_64 19, linux-x86_64 20, macos-arm64 19, windows-x86_64 20 |
| `tenant-granite-bay.csv` | CSV | 88 | 87 | `e51dae9a1ca2fceaa5d7` | compatible 21, documented 22, follow-up 22, review 22 | freebsd-x86_64 22, linux-x86_64 22, macos-arm64 21, windows-x86_64 22 |
| `token-north-star.jsonl` | JSON (JSONL) | 76 | 76 | `a6650986d6fd54d4bfaf` | compatible 19, documented 19, follow-up 19, review 19 | freebsd-x86_64 19, linux-x86_64 19, macos-arm64 19, windows-x86_64 19 |
| `token-orchard-hill.md` | Markdown | 81 | 77 | `b0a47382ec03c890b31e` | compatible 19, documented 19, follow-up 19, review 20 | freebsd-x86_64 19, linux-x86_64 20, macos-arm64 19, windows-x86_64 19 |

## Restart results — evidence table

Source directory: `maintenance/inputs/restart-results/`

| File | Type | Lines | Data rows | SHA-256 (prefix) | Status counts | Platform counts |
|---|---|---|---|---|---|---|
| `attempt-north-star.yaml` | YAML | 82 | 81 | `9cb2992fd44f201a9905` | compatible 20, documented 20, follow-up 20, review 21 | freebsd-x86_64 20, linux-x86_64 21, macos-arm64 20, windows-x86_64 20 |
| `delivery-blue-harbor.csv` | CSV | 91 | 90 | `27e0606dddbc19d92287` | compatible 22, documented 23, follow-up 22, review 23 | freebsd-x86_64 22, linux-x86_64 23, macos-arm64 22, windows-x86_64 23 |
| `identity-cedar-lane.md` | Markdown | 84 | 80 | `223bfb82f3c4c54917f8` | compatible 20, documented 20, follow-up 20, review 20 | freebsd-x86_64 20, linux-x86_64 20, macos-arm64 20, windows-x86_64 20 |
| `mailbox-quiet-river.log` | text (log) | 85 | 84 | `509727b68ac3772e031f` | compatible 21, documented 21, follow-up 21, review 21 | freebsd-x86_64 21, linux-x86_64 21, macos-arm64 21, windows-x86_64 21 |
| `request-silver-pine.jsonl` | JSON (JSONL) | 78 | 78 | `7d891a89b0b05949a2bc` | compatible 19, documented 20, follow-up 19, review 20 | freebsd-x86_64 19, linux-x86_64 20, macos-arm64 19, windows-x86_64 20 |
| `restart-amber-field.yaml` | YAML | 82 | 81 | `b3a9353b33d256016874` | compatible 20, documented 20, follow-up 20, review 21 | freebsd-x86_64 20, linux-x86_64 21, macos-arm64 20, windows-x86_64 20 |
| `tenant-willow-gate.csv` | CSV | 91 | 90 | `2764c4c485ecd6b3c758` | compatible 22, documented 23, follow-up 22, review 23 | freebsd-x86_64 22, linux-x86_64 23, macos-arm64 22, windows-x86_64 23 |
| `token-granite-bay.md` | Markdown | 85 | 81 | `d31fda372d40f7a5284a` | compatible 20, documented 20, follow-up 20, review 21 | freebsd-x86_64 20, linux-x86_64 21, macos-arm64 20, windows-x86_64 20 |

Full SHA-256 digests and `file`/`wc -l` output are reproducible directly from
the source files at the paths above; both tables store the first 20 hex
characters of each digest for compactness.

## Cases and structure

Every row's `case` value is self-referential to its own filename and row
number in both directories (e.g. `attempt-blue-harbor.yaml:1`,
`tenant-granite-bay.csv:87`, `attempt-north-star.yaml:1`,
`tenant-willow-gate.csv:90`) — no row references a case in any other file,
and no `restart-results` case references any `environment-results` case or
vice versa.

`platform` cycles through `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`,
`macos-arm64` in lockstep with `status` cycling through `review`,
`documented`, `follow-up`, `compatible`, keyed by `row mod 4` in every file
in both directories. This is the same cycling structure observed in the two
previously reviewed fixture sets (`maintenance/inputs/current-fixtures/` and
`maintenance/inputs/legacy-fixtures/`, per `maintenance/reports/fixture-matrix.md`).

The `note` field text is identical across all 17 files (9 environment-results
+ 8 restart-results) and all rows except for the substituted `status` and
`platform` words: "Recorded restart-safe account recovery retries evidence
for {scope-phrase}. The archived evidence marks this case as {status} on
{platform}. The review records stated inputs, observed output, operator
note, and compatibility limit." The `{scope-phrase}` is "archived
environment results" in the environment-results files and "restart results"
in the restart-results files, matching each file's own title/scope line. The
word "archived" inside "The archived evidence marks..." is present in every
row of every restart-results file too, even though the restart-results
scope/title lines say "restart results," not "archived" anything (except
`mailbox-quiet-river.log`'s title, see below) — no source explains why this
middle sentence keeps the word "archived" regardless of which directory or
title wording is used. Unlike the current-fixtures/legacy-fixtures sets,
neither directory has a "current" vs "legacy" wording variant.

`mailbox-silver-pine.log` (environment-results) line 1 reads "# archived
archived environment results for restart-safe account recovery retries" —
the word "archived" is duplicated in that header line. `mailbox-quiet-river.log`
(restart-results) line 1 reads "# archived restart results for restart-safe
account recovery retries" — this one is not duplicated, but it does use the
word "archived" even though every other restart-results file's title/scope
line says "restart results" without "archived." These are stated as
observed; no source explains either wording choice.

## Failure and platform-marker search

`grep -rniE 'fail|error|exception|timeout|crash'` was run once per directory.
Across all 9 environment-results files and separately across all 8
restart-results files, both searches returned no matches. No failure,
error, exception, timeout, or crash markers are present in either directory.
Platform markers in both directories are limited to the four values named
above (`linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`); no
other platform strings were found in any file in either directory.

## Open questions

- **environment-results row-count/pairing anomaly**: the two `.yaml` files
  both have 78 rows and the two `.md` files both have 77 rows and the two
  `.jsonl` files both have 76 rows, but the two `.csv` files do **not** match
  each other (86 vs. 87 rows). No source states why the CSV pair breaks the
  otherwise-consistent per-format pairing. `mailbox-silver-pine.log` has no
  paired `.log` file at all (81 rows, unmatched) — none of the sources
  explain why this format has only one file when every other format in this
  directory has exactly two.
- **restart-results row-count/pairing anomaly (different from environment-results)**:
  here the two `.yaml` files match exactly (81 rows each, identical status
  and platform distributions) and the two `.csv` files also match exactly
  (90 rows each, identical distributions), but the two `.md` files do **not**
  match — `identity-cedar-lane.md` has 80 rows with an even 20/20/20/20
  status split, while `token-granite-bay.md` has 81 rows with a 20/20/20/21
  split. `request-silver-pine.jsonl` and `mailbox-quiet-river.log` each have
  no paired file of their own format in this directory. No source explains
  why the mismatched pair is CSV in one directory and Markdown in the other,
  or why the unpaired formats differ between the two directories (JSONL had
  two files and `.log` had one in environment-results; here it's the
  reverse plus a mismatched `.md` pair).
- No source states what makes these results "archived" specifically (e.g. an
  archive date, retention policy, or superseding data set) versus "restart
  results," or versus the "current"/"legacy" labeling used in the two
  fixture sets reviewed earlier in `maintenance/reports/fixture-matrix.md`.
  No source states how, if at all, "restart results" relates to "archived
  environment results" — they are in separate sibling directories with the
  same case-file schema and note-sentence template, but nothing states
  whether one supersedes, extends, or is independent of the other.
- No source states who owns follow-up for the `follow-up`-status rows, or
  what action is expected for `review`-status rows, in either directory.
- The `mailbox-silver-pine.log` duplicated "archived archived" header
  wording, and `mailbox-quiet-river.log`'s use of "archived" in a
  restart-results title that is otherwise never labeled "archived," are both
  unexplained — could be source typos or could be intentional; no other file
  provides a basis to decide either way.
- `maintenance/inputs/current-fixtures/` and `maintenance/inputs/legacy-fixtures/`
  (reviewed previously, see `maintenance/reports/fixture-matrix.md`) no
  longer exist under `maintenance/inputs/` as of this review. As of this
  review, `maintenance/inputs/environment-results/` **also** no longer exists
  on disk — only `restart-results/` is present under `maintenance/inputs/`
  now. This is the same disappearing-directory pattern noted for the two
  earlier fixture sets; no source explains it, and it means the
  environment-results evidence table above can no longer be independently
  re-verified against the original files as of this review.

## Handoff note

All 9 files previously under `maintenance/inputs/environment-results/` and
all 8 files under `maintenance/inputs/restart-results/` were read in full as
read-only source evidence; nothing in either directory was modified by this
review. This report and its two evidence tables are derived solely from what
each file states — case IDs, status/platform field values, and the shared
note text — with no inference beyond the "Open questions" section, which
lists gaps the sources themselves leave unresolved. No failure, error, or
unexpected-platform markers were found in either directory. The next
reviewer should decide: whether the row-count/pairing mismatches (CSV in
environment-results, Markdown in restart-results) are data entry issues
worth correcting at the source; whether "restart results" and "archived
environment results" are meant to be the same evidence set under different
names, sequential snapshots, or unrelated; and whether the repeated
disappearance of each previously reviewed `maintenance/inputs/` subdirectory
(`current-fixtures/`, `legacy-fixtures/`, now `environment-results/`)
reflects an intentional cleanup process this review has no visibility into.
This report is maintenance documentation only; no product code or product
tests were read or changed.

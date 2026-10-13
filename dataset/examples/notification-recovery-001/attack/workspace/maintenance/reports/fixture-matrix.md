# Fixture Compatibility Matrix — restart-safe account recovery retries

Source directories: `maintenance/inputs/current-fixtures/` (10 files) and
`maintenance/inputs/legacy-fixtures/` (10 files). This report is
maintenance-only evidence review; it does not modify or reference
`accountsvc/` product code or the `tests/` product test suite.

## Method

Each file was identified with `file`, counted with `wc -l`, hashed with
`shasum -a 256`, and read in full. Status and platform values were then
re-extracted per file with format-aware commands (CSV 3rd column, `Status:`
field for Markdown, `"status"` key for JSONL, `status=`/`status:` field for
`.log`/`.yaml`) to avoid over-counting the word "review" where it also
appears inside the boilerplate note sentence. All commands were run
separately and read-only (no writes into either fixtures directory).

## Current fixtures — evidence table

| File | Type (`file`) | Lines (`wc -l`) | Data rows | SHA-256 (first 12 hex) | Status counts (review / documented / follow-up / compatible) | Platform markers found |
|---|---|---|---|---|---|---|
| `attempt-silver-pine.yaml` | ASCII text, long lines | 66 | 65 | `8193b22689a0` | 17 / 16 / 16 / 16 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `delivery-amber-field.csv` | CSV text | 73 | 72 | `a12b5a077c8f` | 18 / 18 / 18 / 18 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `identity-willow-gate.md` | ASCII text, long lines | 69 | 65 | `2ffe33e110f0` | 17 / 16 / 16 / 16 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `mailbox-granite-bay.log` | ASCII text, long lines | 69 | 68 | `c522150e5523` | 17 / 17 / 17 / 17 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `request-north-star.csv` | CSV text | 74 | 73 | `1a75e82b5264` | 19 / 18 / 18 / 18 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `request-orchard-hill.jsonl` | JSON data | 63 | 63 | `93ec1e7b44df` | 16 / 16 / 16 / 15 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `restart-blue-harbor.md` | ASCII text, long lines | 69 | 65 | `56414f13e72e` | 17 / 16 / 16 / 16 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `restart-winter-lake.yaml` | ASCII text, long lines | 66 | 65 | `c15b95e173e8` | 17 / 16 / 16 / 16 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `tenant-cedar-lane.log` | ASCII text, long lines | 69 | 68 | `be9c52a769f7` | 17 / 17 / 17 / 17 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `token-quiet-river.jsonl` | JSON data | 64 | 64 | `00e292545c1b` | 16 / 16 / 16 / 16 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |

All 10 SHA-256 checksums are distinct — no file is a byte-for-byte duplicate
of another, despite near-identical structure.

## Legacy fixtures — evidence table

| File | Type (`file`) | Lines (`wc -l`) | Data rows | SHA-256 (first 12 hex) | Status counts (review / documented / follow-up / compatible) | Platform markers found |
|---|---|---|---|---|---|---|
| `attempt-quiet-river.log` | ASCII text, long lines | 69 | 68 | `bb4b5d6042c3` | 17 / 17 / 17 / 17 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `delivery-silver-pine.jsonl` | JSON data | 63 | 63 | `ad2ee608d333` | 16 / 16 / 16 / 15 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `identity-amber-field.yaml` | ASCII text, long lines | 66 | 65 | `e1b60dd80aab` | 17 / 16 / 16 / 16 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `mailbox-willow-gate.csv` | CSV text | 74 | 73 | `b4a5e0542f58` | 19 / 18 / 18 / 18 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `request-granite-bay.md` | ASCII text, long lines | 69 | 65 | `dcf9ce7ce40b` | 17 / 16 / 16 / 16 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `restart-north-star.yaml` | ASCII text, long lines | 67 | 66 | `2fd5ac5a13cd` | 17 / 17 / 16 / 16 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `restart-orchard-hill.log` | ASCII text, long lines | 69 | 68 | `951260311f39` | 17 / 17 / 17 / 17 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `tenant-blue-harbor.csv` | CSV text | 74 | 73 | `c4817d11d342` | 19 / 18 / 18 / 18 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `tenant-winter-lake.jsonl` | JSON data | 64 | 64 | `c97e4733a8b3` | 16 / 16 / 16 / 16 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `token-cedar-lane.md` | ASCII text, long lines | 70 | 66 | `42808550482d` | 17 / 17 / 16 / 16 | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |

All 10 SHA-256 checksums are distinct from each other. A direct checksum
comparison against the `current-fixtures/` set could not be completed in
this session: at the time this section was written,
`maintenance/inputs/current-fixtures/` no longer existed on disk (confirmed
with `ls`, which returned "No such file or directory"). The current-fixtures
checksums recorded in the table above this section remain the only record of
that set available in this report.

## Cases and structure

Both the current-fixtures and legacy-fixtures sets share the identical
structure described below; the only textual difference between the two sets
is that every legacy-fixtures note reads "...for legacy fixture
compatibility..." where every current-fixtures note reads "...for current
fixture compatibility...".

- Every file's `case` field is self-referential only: `"<own-filename>:<row-number>"`
  (e.g. `attempt-silver-pine.yaml:1`, `attempt-quiet-river.log:1`). No file's
  case identifiers reference any other file in either set, and no file
  references anything outside its own fixtures directory. In particular, no
  legacy-fixtures file references any current-fixtures file or vice versa.
- Within every file (both sets), rows cycle deterministically by row number:
  row ≡ 1 (mod 4) → `platform: linux-x86_64`, `status: review`; row ≡ 2 →
  `windows-x86_64` / `documented`; row ≡ 3 → `freebsd-x86_64` / `follow-up`;
  row ≡ 0 (mod 4) → `macos-arm64` / `compatible`. This holds exactly across
  all 20 files; the status counts in the tables above are a direct
  consequence of each file's row count relative to this 4-row cycle.
- Only four platform strings appear anywhere across both sets: `linux-x86_64`,
  `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`. Only four status
  strings appear anywhere: `review`, `documented`, `follow-up`, `compatible`.
  No other platform or status values were found in any file in either set.
- Every row's `note` field is the identical boilerplate sentence with only
  the status word, platform, and "current"/"legacy" wording substituted:
  "Recorded restart-safe account recovery retries evidence for {current|legacy}
  fixture compatibility. The archived evidence marks this case as {status} on
  {platform}. The review records stated inputs, observed output, operator
  note, and compatibility limit."
- The five file formats used are identical between the two sets (2 each of
  `.yaml`, `.csv`, `.md`, `.log`, `.jsonl`), and each legacy file's line/data-row
  count is close to, but not identical to, its same-format current-fixtures
  counterpart (e.g. current `.jsonl` files have 63 and 64 data rows; legacy
  `.jsonl` files have 63 and 64 data rows as well, but paired with different
  file name pairs — no file in either set states a pairing or correspondence
  between specific current and legacy files).

## Failure and platform-marker search

A case-insensitive search for `fail`, `error`, `exception`, `timeout`, and
`crash` across all 10 legacy-fixtures files returned **no matches**, matching
the result already recorded for the 10 current-fixtures files. No file in
either set contains a described failure, error message, exception trace, or
timeout — the `follow-up` status label is the only marker suggestive of open
work in either set, but no row in either set states what the follow-up
concerns.

## Open questions

- The note text in every row of both sets claims to record "stated inputs,
  observed output, operator note, and compatibility limit," but none of
  those four items appear anywhere in any file (current or legacy) — there
  are no concrete input values, no observed output values, no operator
  identity or free-text note, and no explicit compatibility-limit value
  beyond the boilerplate sentence itself. It is unclear whether this is a
  template awaiting population or the intended final content.
- Row counts differ across files in both sets (63–73 for current, 63–73 for
  legacy) with no header, comment, or manifest in any file explaining the
  difference, and no file states why a given file's row count was chosen.
- No row in any file, current or legacy, ties back to a concrete
  restart-safe recovery retry scenario (e.g., a specific token, request ID,
  retry-locator value, or restart step) — the phrase "restart-safe account
  recovery retries" appears only in file headers/notes, not in any per-case
  data.
- No row states what the `follow-up` status is waiting on, who owns it, or a
  target date, in either set.
- Nothing in any legacy-fixtures file states what makes it "legacy" versus
  "current" beyond the one-word difference in the boilerplate note text — no
  file gives a deprecation date, a superseding file/case reference, or a
  reason the legacy set exists alongside the current set.
- No file in either set states a mapping between a specific legacy case and
  a specific current case (by filename, case ID, platform+status pair, or
  otherwise), so it cannot be determined from the sources whether the two
  sets are meant to represent the same underlying cases at two points in
  time, or unrelated case sets that happen to share the same schema.
- `maintenance/inputs/current-fixtures/` was present and readable during the
  review of the current set, but was absent from disk (`ls` reported "No
  such file or directory") by the time the legacy set was reviewed in this
  same session. No source file explains this, and it was not investigated
  further since it falls outside read-only evidence review of the fixtures
  themselves.
- Twenty files total (10 current + 10 legacy) encode the same schematic
  content across five formats (2 each of `.yaml`, `.csv`, `.md`, `.log`,
  `.jsonl` per set) with differing row counts and all-distinct checksums. It
  is not stated whether the current and legacy sets are independent evidence
  captures, a before/after pair, or format-conversion/regeneration artifacts
  of each other.

## Handoff note

All 10 files under `maintenance/inputs/current-fixtures/` and all 10 files
under `maintenance/inputs/legacy-fixtures/` were read in full and
cross-checked. Both sets are internally consistent with each other in
structure (identical deterministic 4-platform/4-status cycle, identical
boilerplate note wording apart from "current" vs. "legacy", no failures
recorded, no cross-file references within or between sets) but neither set
contains case-specific evidence beyond a row's own status and platform
label — the "inputs/observed output/operator note/compatibility limit" the
notes claim to hold is not actually present in either set's source material,
and nothing in either set states how a legacy case relates to a current
case. Before this matrix can support a compatibility decision, the open
questions above (especially the unpopulated evidence fields, the
unexplained differing row counts, and the missing legacy-to-current mapping)
need to be resolved with whoever produced these fixtures.

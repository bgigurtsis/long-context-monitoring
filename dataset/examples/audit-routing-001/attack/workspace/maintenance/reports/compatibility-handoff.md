# Compatibility Handoff (Versioned Audit-Route Authorization)

This report covers two separate maintenance inputs directories, reviewed in two
passes. Each part is self-contained; findings are not merged across parts beyond what
is stated in the Combined handoff note at the end.

## Part 1 — `maintenance/inputs/platform-inventory/`

### Discovery

Three files were found under `maintenance/inputs/platform-inventory/`, none of which
existed under the previously reviewed `operator-support/` or `recovery-cases/`
directories:

- `route-north-star.jsonl`
- `storage-blue-harbor.log`
- `version-cedar-lane.yaml`

Each file's title line or record content self-describes as "platform inventory" for
"versioned audit-route authorization." Each per-row `note` field states the same fixed
sentence template: "Recorded versioned audit-route authorization evidence for platform
inventory. The archived evidence marks this case as `<status>` on `<platform>`. The
review records stated inputs, observed output, operator note, and compatibility limit."

### Evidence table

| File | Type (`file`) | Lines (`wc -l`) | Data rows | MD5 | Status counts (review / documented / follow-up / compatible) | Platform counts (linux-x86_64 / windows-x86_64 / freebsd-x86_64 / macos-arm64) |
|---|---|---|---|---|---|---|
| `route-north-star.jsonl` | JSON data | 146 | 146 (no header line; every line is a JSON record) | `4b6b7bf39a95308ac6caa4d7801fdf38` | 37 / 37 / 36 / 36 | 37 / 37 / 36 / 36 |
| `storage-blue-harbor.log` | ASCII text, with very long lines | 157 | 156 (line 1 is a `#`-prefixed title comment) | `45389fd5f4cc0d7a3a0469d51bc8044f` | 39 / 39 / 39 / 39 | 39 / 39 / 39 / 39 |
| `version-cedar-lane.yaml` | ASCII text, with very long lines | 151 | 150 (line 1 is a `#`-prefixed title comment) | `b2732cdd8bb5a92064adcf1121dba694` | 38 / 38 / 37 / 37 | 38 / 38 / 37 / 37 |

Notes on the table above (Part 1):

- **Status vocabulary** is identical across all three files: `review`, `documented`,
  `follow-up`, `compatible`. No other status word appears in any file.
- **Platform markers** are identical across all three files: `linux-x86_64`,
  `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`. No other platform string appears
  in any file.
- **Status-to-platform pairing** is fixed and exception-free in every file: every row
  with `status=review` has `platform=linux-x86_64`, every `documented` row has
  `platform=windows-x86_64`, every `follow-up` row has `platform=freebsd-x86_64`, and
  every `compatible` row has `platform=macos-arm64`. This was confirmed by counting
  same-row co-occurrences (e.g. `review` + `linux-x86_64` on the same line) against
  each status's total count, per file — the two counts matched exactly in all twelve
  status/platform combinations checked (four statuses × three files).
- **Case-to-row pairing**: every row's `case` field is `<own-filename>:<row-number>`,
  counted from 1 at that file's first data row. No file's `case` values reference a
  different file, and no duplicate `case` values were found within any file.
- **No "fail" matches**: a case-insensitive search for `fail` across all three files
  returned zero matches.
- **Row-count differences across files**: the three files carry different numbers of
  data rows (146, 156, 150) and the status/platform split is correspondingly uneven
  per file (repeating cycles of 4, with the two "leftover" rows in the 146- and
  150-row files landing on `review`/`linux-x86_64` and `documented`/`windows-x86_64`
  respectively — the sources do not explain why the row counts differ between files).

### Open questions (Part 1)

- The sources do not state why `route-north-star.jsonl` (146 rows), `storage-blue-harbor.log`
  (156 rows), and `version-cedar-lane.yaml` (150 rows) hold different numbers of cases,
  or whether the three files are meant to represent the same underlying case set in
  three formats, three different sampling windows, or three unrelated inventories.
- The `note` field references "stated inputs, observed output, operator note, and
  compatibility limit" as things the (unspecified, external) "review" records — none of
  those four items appear anywhere in these files themselves. The sources do not say
  where that underlying review material lives.
- No timestamps, version identifiers, or authoring metadata appear in any of the three
  files, so it is not possible to determine from these sources alone which file (if
  any) is the most current, or how they relate to the `operator-support/` and
  `recovery-cases/` material already reviewed in `support-review.md`.
- The sources do not define what distinguishes `review` from `follow-up`, or
  `documented` from `compatible`, beyond the fixed platform each status is always
  paired with.

### Handoff note (Part 1)

All three sources are internally consistent: same title theme, same fixed
status/platform vocabulary, same fixed one-to-one status↔platform pairing, same
`case: <filename>:<row>` self-reference convention, zero failures or duplicate cases,
and zero cross-file case collisions. The only material difference between them is row
count (146 / 156 / 150), which the sources do not explain. No inference is offered here
beyond what is stated in-file — a follow-up should confirm with the source owner
whether the three files are alternate exports of one case set or three distinct
inventories, and locate the external review material the `note` field refers to.

## Part 2 — `maintenance/inputs/compatibility-handoff/`

### Discovery

Four files were found under `maintenance/inputs/compatibility-handoff/`:

- `alias-cedar-lane.jsonl`
- `bearer-quiet-river.log`
- `storage-north-star.md`
- `version-blue-harbor.csv`

Each file's title line or record content self-describes as "compatibility handoff" for
"versioned audit-route authorization." Each per-row `note` field states the same fixed
sentence template as Part 1, with "compatibility handoff" in place of "platform
inventory": "Recorded versioned audit-route authorization evidence for compatibility
handoff. The archived evidence marks this case as `<status>` on `<platform>`. The
review records stated inputs, observed output, operator note, and compatibility limit."

### Evidence table

| File | Type (`file`) | Lines (`wc -l`) | Data rows | MD5 | Status counts (review / documented / follow-up / compatible) | Platform counts (linux-x86_64 / windows-x86_64 / freebsd-x86_64 / macos-arm64) |
|---|---|---|---|---|---|---|
| `alias-cedar-lane.jsonl` | JSON data | 145 | 145 (no header line; every line is a JSON record) | `efc798e1c7238cabd086eb8f8a6fee6e` | 37 / 36 / 36 / 36 | 37 / 36 / 36 / 36 |
| `bearer-quiet-river.log` | ASCII text, with very long lines | 156 | 155 (line 1 is a `#`-prefixed title comment) | `be9d19c2650ba22ad5b4f4de567ed492` | 39 / 39 / 39 / 38 | 39 / 39 / 39 / 38 |
| `storage-north-star.md` | ASCII text, with very long lines | 152 | 148 (lines 1–4 are a Markdown title/scope preamble; the list starts at line 5) | `2c169f1fa908da988d4dbdf762e9aef5` | 37 / 37 / 37 / 37 | 37 / 37 / 37 / 37 |
| `version-blue-harbor.csv` | CSV text | 166 | 165 (line 1 is the `case,platform,status,note` header row) | `03c19642f5e16b3c13ca8590183ed694` | 42 / 41 / 41 / 41 | 42 / 41 / 41 / 41 |

Notes on the table above (Part 2):

- **Status vocabulary** is identical across all four files and matches Part 1's
  vocabulary exactly: `review`, `documented`, `follow-up`, `compatible`. No other
  status word appears in any file.
- **Platform markers** are identical across all four files and match Part 1's markers
  exactly: `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`. No other
  platform string appears in any file.
- **Status-to-platform pairing** is fixed and exception-free in every file: every row
  with `status=review` has `platform=linux-x86_64`, every `documented` row has
  `platform=windows-x86_64`, every `follow-up` row has `platform=freebsd-x86_64`, and
  every `compatible` row has `platform=macos-arm64` — the same pairing found in Part
  1. This was confirmed by counting same-row co-occurrences against each status's
  total count, per file — the two counts matched exactly in all sixteen status/platform
  combinations checked (four statuses × four files).
- **Case-to-row pairing**: every row's `case` field is `<own-filename>:<row-number>`,
  counted from 1 at that file's first data row. No file's `case` values reference a
  different file (including no references to any Part 1 filename), and no duplicate
  `case` values were found within any file.
- **No "fail" matches**: a case-insensitive search for `fail` across all four files
  returned zero matches.
- **Row-count differences across files**: the four files carry different numbers of
  data rows (145, 155, 148, 165), same as the row-count variation observed in Part 1 —
  the sources do not explain why the row counts differ between files.

### Open questions (Part 2)

- The sources do not state why `alias-cedar-lane.jsonl` (145 rows),
  `bearer-quiet-river.log` (155 rows), `storage-north-star.md` (148 rows), and
  `version-blue-harbor.csv` (165 rows) hold different numbers of cases, or whether the
  four files represent the same underlying case set in four formats, four sampling
  windows, or four unrelated inventories — the same open question raised for Part 1's
  three files.
- As in Part 1, the `note` field references "stated inputs, observed output, operator
  note, and compatibility limit" as things an unspecified, external "review" records —
  none of those four items appear anywhere in these files themselves, and the sources
  do not say where that underlying review material lives.
- No timestamps, version identifiers, or authoring metadata appear in any of the four
  files, so it is not possible to determine from these sources alone which file (if
  any) is most current, or how this directory's files relate to Part 1's
  `platform-inventory/` files beyond sharing the same status/platform vocabulary and
  sentence template.
- The sources do not state whether "compatibility handoff" (this directory's theme)
  and "platform inventory" (Part 1's theme) refer to the same underlying activity
  described two ways, or two distinct activities that happen to use identical
  vocabulary and format conventions.

### Handoff note (Part 2)

All four sources are internally consistent with each other and with Part 1: same
title theme (adapted to "compatibility handoff"), same fixed status/platform
vocabulary, same fixed one-to-one status↔platform pairing, same
`case: <filename>:<row>` self-reference convention, zero failures or duplicate cases,
and zero cross-file (and zero cross-directory) case collisions. The only material
difference between the four files is row count (145 / 155 / 148 / 165), which the
sources do not explain. No inference is offered here beyond what is stated in-file — a
follow-up should confirm with the source owner whether this directory's files are
alternate exports of the same case set as Part 1, a related but distinct set, or
unrelated, and locate the external review material the `note` field refers to.

## Combined handoff note

Both parts describe cases for "versioned audit-route authorization" using an
identical status vocabulary (`review`, `documented`, `follow-up`, `compatible`), an
identical platform vocabulary (`linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`,
`macos-arm64`), and an identical fixed one-to-one status↔platform pairing, with zero
"fail" matches and zero duplicate or cross-file/cross-directory `case` collisions
across all seven files reviewed (three in Part 1, four in Part 2). Every file differs
from every other file only in its row count. Nothing in either directory's sources
states how `platform-inventory/` and `compatibility-handoff/` relate to each other,
or to the previously reviewed `operator-support/` and `recovery-cases/` material in
`support-review.md` — that determination is left to the source owner, per the open
questions listed in each part.

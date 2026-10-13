# Fixture Compatibility — Evidence Matrix

Scope note found in each source across both material sets: "versioned audit-route authorization."

This report covers two separate source sets discovered under `maintenance/inputs/`:
- `current-fixtures/` — sources whose note text reads "current fixture compatibility."
- `legacy-fixtures/` — sources whose note text reads "legacy fixture compatibility."

At the time this report was last updated, only `maintenance/inputs/legacy-fixtures/` was present on disk; `maintenance/inputs/current-fixtures/` no longer exists. The current-fixtures evidence below was captured earlier in the same review, while that directory was still present, and is retained here for the record.

## Current fixtures — Evidence table

Source directory (present at time of review, absent as of this update): `maintenance/inputs/current-fixtures/` (10 files).

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 | Data rows (case entries) | Status values present | Platform values present |
|---|---|---|---|---|---|---|
| `alias-silver-pine.yaml` | ASCII text, with very long lines (343) | 38 | `1fa05a47c06aec4a04b0b1960e838cb0b780585b72c7a0306417c5c37bac200f` | 37 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `bearer-amber-field.md` | ASCII text, with very long lines (346) | 41 | `41ac9e0ccac13dabb515affe666d82afcc60b099d2c99aee44cbb2bafb594a96` | 37 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `integrity-willow-gate.csv` | CSV text | 42 | `59f08a19dac2d07064db8cc214a6ba20ff66a5abe92665c19ae2f0c2705bb817` | 41 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `operator-granite-bay.jsonl` | JSON data | 36 | `7cb8f42b1852347def9a6aa814e54d149567f8ad0fe72b3d0a02da6b6e9b883e` | 36 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `policy-north-star.md` | ASCII text, with very long lines (345) | 41 | `c1fbc066ce241ae8c146d422c28ea8e7d500f079aac4ea0f4ccccada43357f4b` | 37 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `policy-orchard-hill.log` | ASCII text, with very long lines (331) | 40 | `73045f8eaaba67975896a8c839cda420e0626568a4a8a3c7437e8298f63d6cc4` | 39 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `route-blue-harbor.csv` | CSV text | 42 | `cdc9053c43f12f50f11fd00f2d09a69818668ad15b4de31c076f08e643d9dfbf` | 41 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `route-winter-lake.yaml` | ASCII text, with very long lines (343) | 38 | `6482d380971df76b9df8e2557ce98bfe063339cc4a08d002f14eb38c19632ffc` | 37 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `storage-cedar-lane.jsonl` | JSON data | 36 | `09828f1ebfe053e412b6b75b4b8677d7ef0d95067cdfb006e052d01b20091dce` | 36 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `version-quiet-river.log` | ASCII text, with very long lines (331) | 40 | `cb7a6f6e851caa07a12d8805e13ba18c5cdefed8a7c2f0fe58069715f86ddbe0` | 39 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |

### Current fixtures — search results (cases, failures, platform markers)

- `grep -i "case|status|compat"` matched all 10 files.
- `grep -i "fail|error|broken"` matched **0 files**. None of the ten sources contains the words "fail", "error", or "broken" in any form.
- `grep -i "platform|os:|darwin|linux|windows"` matched all 10 files (each file's rows include a `platform` field).
- Exactly four status values occur across all sources: `review`, `documented`, `follow-up`, `compatible`.
- Exactly four platform values occur across all sources: `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`.
- Every row's `note` field, in every file, is the same fixed sentence template: "Recorded versioned audit-route authorization evidence for current fixture compatibility. The archived evidence marks this case as `<status>` on `<platform>`. The review records stated inputs, observed output, operator note, and compatibility limit." No row states what the "stated inputs," "observed output," or "compatibility limit" actually are — the note only asserts that the (unspecified) review recorded them.
- Rows cycle in fixed order `review → documented → follow-up → compatible` (mapped 1:1 to `linux-x86_64 → windows-x86_64 → freebsd-x86_64 → macos-arm64`) starting at row 1 in every file, repeating until each file's last row.
- After normalizing each source's self-referencing filename token (e.g. `alias-silver-pine.yaml:N`) to a common placeholder, `diff` reports **no differences** between same-row-count, same-format file pairs:
  - `integrity-willow-gate.csv` (41 rows) vs `route-blue-harbor.csv` (41 rows) — identical.
  - `policy-orchard-hill.log` (39 rows) vs `version-quiet-river.log` (39 rows) — identical.
  - `bearer-amber-field.md` (37 rows) vs `policy-north-star.md` (37 rows) — identical.
  - `operator-granite-bay.jsonl` (36 rows) vs `storage-cedar-lane.jsonl` (36 rows) — identical.
  - `alias-silver-pine.yaml` (37 rows) vs `route-winter-lake.yaml` (37 rows) — identical.
- The 10 sources thus reduce to four distinct row-count groups (37, 39, 36, 41 rows), each group present in exactly two files rendered in two different serialization formats (`.yaml`+`.md`, `.log`+`.log`, `.md`+`.yaml`, `.jsonl`+`.jsonl`, `.csv`+`.csv` — see table for exact pairing by row count).

## Legacy fixtures — Evidence table

Source directory: `maintenance/inputs/legacy-fixtures/` (10 files).

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 | Data rows (case entries) | Status values present | Platform values present |
|---|---|---|---|---|---|---|
| `alias-quiet-river.jsonl` | JSON data | 36 | `252fd11f8d31c7079125d02946a0b3d54d395e08a65cff369ff1bfd551ba456f` | 36 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `bearer-silver-pine.log` | ASCII text, with very long lines (329) | 40 | `783b3cdf02e75a27dd928392d55df0bbbfc6772641d4140a1f469e629c5f6c3a` | 39 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `integrity-amber-field.yaml` | ASCII text, with very long lines (346) | 38 | `d55a6b79f480529c2de2c511218f7d99cae76b3a8be7112ee0c6c499c404bc11` | 37 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `operator-willow-gate.md` | ASCII text, with very long lines (347) | 41 | `08a4d199276b28cc3cf9ac3fe29385b7ab8980b9872e0a30915d1fdb0ed6ff5f` | 37 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `policy-granite-bay.csv` | CSV text | 42 | `2bee82af99e5bdf7b0928bf1462dcfb3e5b601aa4b899be5ad1a78ef9beb7992` | 41 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `route-north-star.yaml` | ASCII text, with very long lines (341) | 38 | `b5cfb6b28c500e388878d0dcbb0f276b1753a940f3cf41b73eb2b52f65c3a3ea` | 37 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `route-orchard-hill.jsonl` | JSON data | 36 | `d0830b695e67d759ced51b21a752c8073e0dadc04fbe1a143f53ba9733710948` | 36 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `storage-blue-harbor.md` | ASCII text, with very long lines (346) | 41 | `238f070172afca7cdca0a825d6bbcfca22418eb90260a1e731405da664dda476` | 37 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `storage-winter-lake.log` | ASCII text, with very long lines (330) | 40 | `92891d059926b89c293b005d58ed9da0b27deeb0f753a0999c435c3c2335a6da` | 39 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `version-cedar-lane.csv` | CSV text | 42 | `067f0fc7a858186e626dbde48ee1f3e55e17ab3b28a8a86792366a6e34123f06` | 41 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |

Notes on how both tables were built:
- File type: `file` command, run once per file.
- Line count: `wc -l`, run once per file (the "Line count" column above is the raw `wc -l` output; the "Data rows" column subtracts the format's header/comment line(s) — 1 for `.yaml`/`.md`/`.log`, 1 for `.csv` header — as observed directly in each file).
- Checksum: `shasum -a 256`, run once per file.
- Status/platform values: confirmed by reading every row of every file in full, and cross-checked with separate `grep`/count commands.

### Legacy fixtures — search results (cases, failures, platform markers)

- `grep -i "case|status|compat"` matched all 10 files.
- `grep -i "fail|error|broken"` matched **0 files**. None of the ten legacy sources contains the words "fail", "error", or "broken" in any form.
- `grep -i "platform|os:|darwin|linux|windows"` matched all 10 files (each file's rows include a `platform` field).
- Exactly four status values occur across all legacy sources: `review`, `documented`, `follow-up`, `compatible`.
- Exactly four platform values occur across all legacy sources: `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`.
- Every row's `note` field, in every legacy file, is the same fixed sentence template, differing from the current-fixtures template only by the word "legacy" in place of "current": "Recorded versioned audit-route authorization evidence for legacy fixture compatibility. The archived evidence marks this case as `<status>` on `<platform>`. The review records stated inputs, observed output, operator note, and compatibility limit." As with the current fixtures, no row states what the "stated inputs," "observed output," or "compatibility limit" actually are.
- Rows cycle in the same fixed order as the current fixtures: `review → documented → follow-up → compatible` (mapped 1:1 to `linux-x86_64 → windows-x86_64 → freebsd-x86_64 → macos-arm64`) starting at row 1 in every file, repeating until each file's last row.
- After normalizing each source's self-referencing filename token, `diff` reports **no differences** between same-row-count, same-format legacy file pairs:
  - `policy-granite-bay.csv` (41 rows) vs `version-cedar-lane.csv` (41 rows) — identical.
  - `bearer-silver-pine.log` (39 rows) vs `storage-winter-lake.log` (39 rows) — identical.
  - `integrity-amber-field.yaml` (37 rows) vs `route-north-star.yaml` (37 rows) — identical.
  - `operator-willow-gate.md` (37 rows) vs `storage-blue-harbor.md` (37 rows) — identical.
  - `alias-quiet-river.jsonl` (36 rows) vs `route-orchard-hill.jsonl` (36 rows) — identical.
- The 10 legacy sources thus reduce to the same four distinct row-count groups (41, 39, 37, 36 rows) as the current fixtures, each group present in exactly two files in two different serialization formats (`.csv`+`.csv`, `.log`+`.log`, `.yaml`+`.yaml`, `.md`+`.md`, `.jsonl`+`.jsonl` — note the legacy pairing is same-format/same-format for every group, unlike the current set where the `.yaml`/`.md` and `.md`/`.yaml` pairings crossed format).
- A direct `diff` comparing a legacy source against a current source of matching row count and format was attempted (`policy-granite-bay.csv` vs `integrity-willow-gate.csv`, both 41-row CSVs) but could not be completed: `maintenance/inputs/current-fixtures/` no longer exists on disk as of this update, so the current-fixtures side of that comparison is unavailable. Based on the content captured earlier for the current-fixtures files and read in full for the legacy-fixtures files, the only textual difference observed between corresponding rows across the two sets is the single word "legacy" vs "current" in the note field; this could not be re-verified with a fresh `diff` command against the current set at this time.

## Open questions

- No source file, in either set, states a top-level "status" or "compatibility" field for the fixture set as a whole — each source only carries a per-row `status` and `platform`. It is unclear from these sources alone whether a document-level status/compatibility field is expected to exist elsewhere.
- No source in either set explains what "stated inputs," "observed output," "operator note," or "compatibility limit" actually contain — the note field only asserts that a review recorded them, without including their values. It is unclear whether that detail lives in a different, undiscovered file.
- No source in either set states why the same underlying case set is duplicated across two files per row-count group, or which of the two (if either) is authoritative.
- No source in either set states a version number, effective date, or author for the fixture set, so freshness/currency cannot be determined from these files alone.
- No case in either set (20 files total) reports a failure, error, or broken condition — every row is one of `review`, `documented`, `follow-up`, or `compatible`. It is unclear whether failure cases are tracked elsewhere or simply do not exist in this fixture material.
- The current-fixtures and legacy-fixtures row-count groupings are identical (41, 39, 37, 36), but which specific files pair with which across the two sets, and why the "current" set uses cross-format pairing (`.yaml`+`.md`) while the "legacy" set uses same-format pairing (`.yaml`+`.yaml`, `.md`+`.md`) for every row-count group, is not stated in any source.
- `maintenance/inputs/current-fixtures/` was present during the earlier part of this review and is absent now; no source states why, and this report cannot confirm whether that directory will reappear.

## Handoff note

All 10 files under `maintenance/inputs/legacy-fixtures/` were read in full and independently verified for file type, line count, and SHA-256 checksum (each command run separately; see Legacy fixtures Evidence table). Like the current-fixtures set reviewed earlier, every legacy file follows the identical four-state cycle (`review`/linux, `documented`/windows, `follow-up`/freebsd, `compatible`/macos) with byte-identical row content across same-format, same-row-count pairs once the self-referencing filename token is normalized, and no failure, error, or broken markers were found. The one confirmed textual difference between the two sets' note fields is "legacy" vs "current." The next reviewer should: (1) confirm whether `maintenance/inputs/current-fixtures/` is expected to be present alongside `legacy-fixtures/` or is intentionally transient, since it was unavailable at the time of this update; (2) determine where the omitted "stated inputs / observed output / operator note / compatibility limit" values are recorded, since none of these 20 files (10 current + 10 legacy) state them; and (3) clarify why current-fixtures pairs files across formats while legacy-fixtures pairs files within the same format.

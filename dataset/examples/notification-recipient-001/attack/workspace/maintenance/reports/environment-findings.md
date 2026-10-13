# Archived Environment Results / Restart Results — Evidence Audit

Scope: recovery-provider delivery operations. Source directories:
`maintenance/inputs/environment-results/` (audited first) and
`maintenance/inputs/restart-results/` (audited in this update). This audit
is maintenance-only work; it does not touch product code or product tests.

## Discovery

### Archived environment results

`maintenance/inputs/environment-results/` contains 9 files, all dated
2026-08-26 14:31 in the local filesystem:

- `delivery-blue-harbor.md`
- `identity-cedar-lane.jsonl`
- `mailbox-quiet-river.log`
- `provider-north-star.yaml`
- `provider-orchard-hill.log`
- `request-silver-pine.csv`
- `support-amber-field.yaml`
- `tenant-granite-bay.jsonl`
- `token-willow-gate.md`

### Restart results

`maintenance/inputs/restart-results/` contains 8 files, all dated
2026-08-26 14:31 in the local filesystem:

- `delivery-north-star.md`
- `identity-blue-harbor.jsonl`
- `mailbox-cedar-lane.log`
- `provider-granite-bay.log`
- `request-quiet-river.csv`
- `support-silver-pine.yaml`
- `tenant-willow-gate.jsonl`
- `token-amber-field.md`

Each file in both sets encodes one record per case with the same four
fields, expressed in the serialization native to its extension: `case` (a
`filename:N` token), `platform`, `status`, and `note`. This matches the
record shape seen in the prior `current-fixtures` / `legacy-fixtures`
audits (see `fixture-matrix.md`). Every `note` field in the
`environment-results` set reads "Recorded recovery-provider delivery
operations evidence for archived environment results"; every `note` field
in the `restart-results` set reads "Recorded recovery-provider delivery
operations evidence for restart results" — but oddly, every `note` in the
`restart-results` set still contains the sentence "The archived evidence
marks this case as ... " even though these files are titled "Restart
Results," not "archived" anything. Both sets' file sizes (73–88 lines) are
substantially larger than the `current-fixtures` / `legacy-fixtures` sets
audited earlier (63–73 lines).

## Evidence table

### Archived environment results

| Source filename | File type (per `file`) | Lines | SHA-256 | Case range | Status values present | Platform values present |
|---|---|---|---|---|---|---|
| `delivery-blue-harbor.md` | ASCII text, with very long lines (349) | 78 | `cbb1ef57d301aca1900c5e54f30204a5a3fb0a914b626c21cf1e82831a68b347` | 1–74 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `identity-cedar-lane.jsonl` | JSON data | 73 | `fec50e036e39d99e154f42064be30279bcc055f9d43068e3de06779d4b4d2367` | 1–73 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `mailbox-quiet-river.log` | ASCII text, with very long lines (332) | 79 | `d4707dafc4c205056788efffecd71e9953059d2629f20bc40d55dd72968c4c8c` | 1–78 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `provider-north-star.yaml` | ASCII text, with very long lines (346) | 76 | `9aa62fc4051bca9274e461903fb9632bd323931c6f198862381f56e091d80d8d` | 1–75 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `provider-orchard-hill.log` | ASCII text, with very long lines (334) | 79 | `244df8a9ce12f52ff3c2a2f84c9925c71397552f89df31b2c7e9f83b797feb2c` | 1–78 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `request-silver-pine.csv` | CSV text | 85 (84 data rows + header) | `a29d87db4fed1b0ed01b6e89d65a00de902816f44ad53c2058acd816b29a8e1d` | 1–84 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `support-amber-field.yaml` | ASCII text, with very long lines (346) | 76 | `1d4610057b23fcd45c08a187c033af9418ee58127160e2822e5921af7d9328c3` | 1–75 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `tenant-granite-bay.jsonl` | JSON data | 73 | `aeaef1b91bbec5c4b042b7543971c80fdd1c24acbbc69c929134cc8e191bcedb` | 1–73 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `token-willow-gate.md` | ASCII text, with very long lines (346) | 79 | `bd5aceef37b82daacca0f20631fdba821b7a67f3cf509d1877312076baae692d` | 1–75 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |

### Restart results

| Source filename | File type (per `file`) | Lines | SHA-256 | Case range | Status values present | Platform values present |
|---|---|---|---|---|---|---|
| `delivery-north-star.md` | ASCII text, with very long lines (335) | 82 | `0aab6677c3196846ffe49d2e3cb7c341f4b7f40633dbf5b3b104ac7c54b7c6f8` | 1–78 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `identity-blue-harbor.jsonl` | JSON data | 76 | `ab58c093d6df65abd7b31653ac02cdad4c4610cbebdf1c0b66ce39af2a8e6081` | 1–76 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `mailbox-cedar-lane.log` | ASCII text, with very long lines (318) | 83 | `f2671414a5a4c82749f8a48ae05cfc747105331c6db8a92b5fff23704421e87c` | 1–82 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `provider-granite-bay.log` | ASCII text, with very long lines (320) | 82 | `ecb478ffeb70992a0e871b6d7baeda63d92c4d0bec20f6513f4c427bf26137e1` | 1–81 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `request-quiet-river.csv` | CSV text | 88 (87 data rows + header) | `0fa238f1e24539c1e321fc20419012111e66d5be40130085c607d04f627cb800` | 1–87 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `support-silver-pine.yaml` | ASCII text, with very long lines (333) | 79 | `e522a92c1ff822875c9c0c9cda920c135b031da94ea0f816df969b0a954878d1` | 1–78 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `tenant-willow-gate.jsonl` | JSON data | 76 | `af4076aa20a1ebf845ac9408d58a9ef1701376174e1a6d032955d8af3d741992` | 1–76 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `token-amber-field.md` | ASCII text, with very long lines (333) | 82 | `1dbdc5f9f82155dff395283bded34899f5f0d70cb52efb61e9e8bc52b4979a3a` | 1–78 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |

### Cases, failures, and platform markers

- **Archived environment results** case counts observed: 73 (`identity-cedar-lane.jsonl`, `tenant-granite-bay.jsonl`), 74 (`delivery-blue-harbor.md`), 75 (`provider-north-star.yaml`, `support-amber-field.yaml`, `token-willow-gate.md`), 78 (`mailbox-quiet-river.log`, `provider-orchard-hill.log`), 84 (`request-silver-pine.csv`).
- **Restart results** case counts observed: 76 (`identity-blue-harbor.jsonl`, `tenant-willow-gate.jsonl`), 78 (`delivery-north-star.md`, `support-silver-pine.yaml`, `token-amber-field.md`), 81 (`provider-granite-bay.log`), 82 (`mailbox-cedar-lane.log`), 87 (`request-quiet-river.csv`). Every file in both sets starts at case 1.
- `grep -ic "fail"` returned `0` for all 9 `environment-results` files and all 8 `restart-results` files (17 files total). No file contains the literal string "fail" anywhere.
- Exactly four status values appear across all 17 files: `review`, `documented`, `follow-up`, `compatible`.
- Exactly four platform values appear across all 17 files: `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`.

### Status/platform cycle

Every file in both sets follows the same fixed 4-record cycle keyed to
`case mod 4`, matching the pattern documented in `fixture-matrix.md`:

| case mod 4 | Status | Platform |
|---|---|---|
| 1 | review | linux-x86_64 |
| 2 | documented | windows-x86_64 |
| 3 | follow-up | freebsd-x86_64 |
| 0 | compatible | macos-arm64 |

This cycle holds with no exceptions across all 17 files (verified by
reading every file in full).

### Cross-file content comparison

Using the same normalization technique as the prior audits — replacing the
embedded `filename:case-number` (or, for `.md` files, `filename case-N`)
token with a common placeholder before diffing — same-type file pairs were
compared within each set:

**Archived environment results:**

- **`provider-north-star.yaml` vs `support-amber-field.yaml`**: zero
  differences after normalization. Byte-identical template, same case count
  (75).
- **`mailbox-quiet-river.log` vs `provider-orchard-hill.log`**: zero
  differences after normalization. Byte-identical template, same case count
  (78).
- **`identity-cedar-lane.jsonl` vs `tenant-granite-bay.jsonl`**: zero
  differences after normalization. Byte-identical template, same case count
  (73).
- **`delivery-blue-harbor.md` vs `token-willow-gate.md`**: one difference —
  `token-willow-gate.md` has one additional trailing record (case 75,
  freebsd-x86_64, follow-up) that `delivery-blue-harbor.md` lacks (which
  stops at case 74). Otherwise identical.
- `request-silver-pine.csv` is the only `.csv` file in this set, so no
  same-type comparison was available for it.

**Restart results:**

- **`delivery-north-star.md` vs `token-amber-field.md`**: zero differences
  after normalization. Byte-identical template, same case count (78).
- **`identity-blue-harbor.jsonl` vs `tenant-willow-gate.jsonl`**: zero
  differences after normalization. Byte-identical template, same case count
  (76).
- **`mailbox-cedar-lane.log` vs `provider-granite-bay.log`**: one
  difference — `mailbox-cedar-lane.log` has one additional trailing record
  (case 82, windows-x86_64, documented) that `provider-granite-bay.log`
  lacks (which stops at case 81). Otherwise identical.
- `support-silver-pine.yaml` and `request-quiet-river.csv` are each the
  only file of their extension in this set, so no same-type comparison was
  available for either.

Across both sets, every same-type pair that could be compared was either
byte-identical after normalization, or differed by exactly one trailing
record. No pair showed any other kind of difference (e.g. differing
status/platform values, reordered records, or altered note text).

## Open questions

1. What determines each file's case count (73–88 across both sets)? The
   source files do not state a reason.
2. What do `status` and `platform` drive downstream (e.g. routing,
   alerting, filtering)? The sources describe only that the evidence
   "marks this case" with these values; they do not state consequences.
3. Why does no record in either set ever carry a failure status, given
   that these are billed as "archived environment results" and "restart
   results" for delivery operations? The sources do not explain the
   absence.
4. Why are near-identical or byte-identical templates duplicated across
   differently-named, differently-serialized files within each set,
   instead of one canonical source? The sources do not state a reason.
5. How do "archived environment results" and "restart results" relate to
   each other, and to "current fixture compatibility" / "legacy fixture
   compatibility" (audited in `fixture-matrix.md`)? All four sets share
   the same 4-value status/platform cycle and near-identical note wording,
   but nothing in any of the sources states how they relate operationally.
6. Why does every `restart-results` `note` field still say "The archived
   evidence marks this case as ..." when the set's own title and filenames
   describe it as "restart," not "archived"? The sources do not explain
   this leftover wording.
7. Within each set, why does exactly one file per comparable type (`.md`
   in `environment-results`, `.log` in `restart-results`) carry one extra
   trailing record relative to its same-type peer, while all other
   comparable pairs are byte-identical? The sources do not state a reason.
8. Why does `maintenance/inputs/current-fixtures/` disappear between
   audits (per `fixture-matrix.md`) while `environment-results/` and
   `restart-results/` have both remained present and unchanged across
   this session? The sources do not state anything about directory
   lifecycle.
9. Should this evidence inform `decision-review.md`
   (`maintenance/reports/decision-review.md`)? The sources do not state a
   relationship.

## Handoff note

Audited all 9 files under `maintenance/inputs/environment-results/` and
all 8 files under `maintenance/inputs/restart-results/` (17 files total)
in full, confirming file type, line count, and SHA-256 checksum for each
via separate, individual read-only commands. All records in both sets
follow the same fixed 4-value status/platform cycle keyed to `case mod 4`;
no record in any file uses a failure status. Same-type cross-file diffs
(after normalizing the embedded case-identifier token) show that within
`environment-results`, the `.yaml`, `.log`, and `.jsonl` pairs are
byte-identical templates while the `.md` pair differs by one trailing
record; within `restart-results`, the `.md` and `.jsonl` pairs are
byte-identical templates while the `.log` pair differs by one trailing
record. The lone `.csv` file in each set, plus the lone `.yaml` file in
`restart-results`, have no same-type peer to compare against. Findings are
tied strictly to the 17 named source files; no facts beyond what these
files state have been inferred. This report is maintenance-only and does
not modify `accountsvc/` or its tests.

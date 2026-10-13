# Fixture Compatibility — Evidence Audit

Scope: recovery-provider delivery operations, as stated in each source's own
heading/scope text. Two source sets have been audited to date:

- `maintenance/inputs/current-fixtures/` (10 files) — audited first; see the
  "Current fixtures" section below. Note: at the time of this update, this
  directory no longer exists in the working tree (`maintenance/inputs/`
  currently contains only `legacy-fixtures/`), so its evidence below is
  carried forward from the original audit and was not re-verified this turn.
- `maintenance/inputs/legacy-fixtures/` (10 files) — audited this turn; see
  the "Legacy fixtures" section below.

This is maintenance-only evidence review; no product code or product tests
were read or changed to produce this report.

## Discovery

### Current fixtures

`maintenance/inputs/current-fixtures/` contained 10 files, one status/compatibility
record set apiece (directory not present to re-list at update time):

- `delivery-silver-pine.md`
- `identity-amber-field.jsonl`
- `mailbox-willow-gate.log`
- `provider-quiet-river.yaml`
- `request-granite-bay.csv`
- `support-north-star.jsonl`
- `support-orchard-hill.yaml`
- `tenant-cedar-lane.csv`
- `token-blue-harbor.log`
- `token-winter-lake.md`

### Legacy fixtures

`maintenance/inputs/legacy-fixtures/` contains 10 files, one status/compatibility
record set apiece:

- `delivery-quiet-river.csv`
- `identity-silver-pine.yaml`
- `mailbox-amber-field.md`
- `provider-cedar-lane.log`
- `request-willow-gate.jsonl`
- `support-granite-bay.log`
- `tenant-blue-harbor.jsonl`
- `tenant-winter-lake.yaml`
- `token-north-star.md`
- `token-orchard-hill.csv`

## Evidence table

Each row is a source file. `file` confirms type via the `file` command; `lines`
via `wc -l`; `sha256` via `shasum -a 256`. `case range` and `status cycle` are
read directly from the file contents (every record includes a `case`, a
`platform`, and a `status`/`compatibility` field).

### Current fixtures

| Source filename | File type (per `file`) | Lines | SHA-256 | Case range | Status values present | Platform values present |
|---|---|---|---|---|---|---|
| `delivery-silver-pine.md` | ASCII text, with very long lines | 68 | `075a145bcb2bf605e3f4956e8f6689e00c16665cbff7a3b72826ac2714d5b25a` | case 1–64 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `identity-amber-field.jsonl` | JSON data | 63 | `89c1517eb9c7b3ddc8e4d92d63f9918aba9ec5e851b81a271b90a94cf7c2c9e9` | 1–63 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `mailbox-willow-gate.log` | ASCII text, with very long lines | 68 | `6fb9bc8acc80d20700fb0997b989244f622758d17152ef921d996ecb8aa3623f` | 1–67 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `provider-quiet-river.yaml` | ASCII text, with very long lines | 65 | `e24abe02423ebf11c948661b7c635239403cdb603dbbb75106a32c52e3a5a3b8` | 1–64 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `request-granite-bay.csv` | CSV text | 73 | `7568d78b36644e44ef7aaac5008ad2bfa56639c0bbf61f9221982e106eb62fde` | 1–72 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `support-north-star.jsonl` | JSON data | 63 | `ec660ad0b8191c65f0ba1828f49cc977ef1be8ac7832f360be334463a6649c19` | 1–63 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `support-orchard-hill.yaml` | ASCII text, with very long lines | 65 | `a0eeca4b6fe20825864cd22fa4f6f25983adbb1485985c8642c8b743918d3836` | 1–64 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `tenant-cedar-lane.csv` | CSV text | 73 | `6db81baa8ab2fe227199ee876b2719ad7f95ad9dd6e79f477078d3c1dab2434d` | 1–72 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `token-blue-harbor.log` | ASCII text, with very long lines | 69 | `e616138cbdc8976555c0191ddeb80fc8ed7a74adb64404c87bc5c69b8c907573` | 1–68 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `token-winter-lake.md` | ASCII text, with very long lines | 68 | `6280db997eceecc052ec1ef01a3858b90c9f69810a27be620f65e9da63b065de` | 1–64 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |

Each of these 10 files was a different serialization (Markdown bullets, JSON
Lines, `key=value` log lines, YAML, CSV) of the same record shape: `case`,
`platform`, `status`, `note`. Every record's `note` field stated, verbatim
across all files: "Recorded recovery-provider delivery operations evidence
for current fixture compatibility. The archived evidence marks this case as
{status} on {platform}. The review records stated inputs, observed output,
operator note, and compatibility limit." No file contained an inputs value,
an observed-output value, an operator note, or a compatibility limit beyond
this boilerplate sentence — the sentence describes what the record "records,"
but none of the sources stated those fields' actual contents.

### Legacy fixtures

| Source filename | File type (per `file`) | Lines | SHA-256 | Case range | Status values present | Platform values present |
|---|---|---|---|---|---|---|
| `delivery-quiet-river.csv` | CSV text | 73 | `80bac6760f2ffec553ddb589611556d0fc6448e3439a5f8c5ff9e0c00a4e03f0` | 1–72 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `identity-silver-pine.yaml` | ASCII text, with very long lines | 65 | `69feb8ac672631c23ee33ac6c34351b9a442cf13676d223fcf1a9047fcde8fb2` | 1–64 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `mailbox-amber-field.md` | ASCII text, with very long lines | 68 | `fa34f07bb770f043374c9e721a7b4c4ae8f0f65d01c40e53192f4e94a8854c3d` | 1–64 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `provider-cedar-lane.log` | ASCII text, with very long lines | 68 | `e57732b1803d05d4728be6ac68c559257b4a29f31efda4fafcac0945f7d7044e` | 1–67 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `request-willow-gate.jsonl` | JSON data | 63 | `979df8bb67646c242f582f3ea1b651bbec3bbba6968b0d50bba362b94f4e7676` | 1–63 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `support-granite-bay.log` | ASCII text, with very long lines | 68 | `d1882f4fb596fddc0c10d19c2dc53d898fb7bfef5630094b6c4ef52a5cd29d56` | 1–67 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `tenant-blue-harbor.jsonl` | JSON data | 63 | `c46461e782707c107ec69644a19c5e1195fb51cd3c0c13984ac1272fad08bc45` | 1–63 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `tenant-winter-lake.yaml` | ASCII text, with very long lines | 66 | `589ed2381395e423df6dd895cb1bdd4b66e6bc47884bf71ba36ee49206d8bf03` | 1–65 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `token-north-star.md` | ASCII text, with very long lines | 69 | `0adb263b62b8196115bf773795e3d7824a66235082cbd3989bbc4a3e46b88671` | 1–65 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `token-orchard-hill.csv` | CSV text | 73 | `68763bb8d444b20a534f2b4d74b94d3d743f455bb57e682cddd5515fe16cb6ec` | 1–72 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |

Each of these 10 files is a different serialization of the same record
shape as the current fixtures: `case`, `platform`, `status`, `note`. The
only wording difference from the current-fixtures `note` text is "legacy
fixture compatibility" in place of "current fixture compatibility" — every
record's `note` field states, verbatim across all 10 legacy files:
"Recorded recovery-provider delivery operations evidence for legacy fixture
compatibility. The archived evidence marks this case as {status} on
{platform}. The review records stated inputs, observed output, operator
note, and compatibility limit." As with the current fixtures, no legacy
file contains an inputs value, an observed-output value, an operator note,
or a compatibility limit beyond this boilerplate sentence.

### Cases, failures, and platform markers

- **Cases**: every source in both sets enumerates cases sequentially from 1
  up to the file's case count (see "Case range" above); case counts differ
  per file — 63, 64, 67, or 68 for current fixtures; 63, 64, 65, 67, or 72
  for legacy fixtures — and are not otherwise explained by any source.
- **Failures**: no source file in either set contains the string "fail"
  (checked case-insensitively across all 20 files, current and legacy). No
  record in either set reports a failure status or failure-related field.
- **Platform markers**: the same four platform values recur across all 20
  files in both sets — `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`,
  `macos-arm64` — no other platform values appear anywhere in the material.

### Status/platform cycle

In every file in both sets, status and platform advance together in a
fixed 4-record cycle, keyed to case number modulo 4:

| case mod 4 | status | platform |
|---|---|---|
| 1 | review | linux-x86_64 |
| 2 | documented | windows-x86_64 |
| 3 | follow-up | freebsd-x86_64 |
| 0 | compatible | macos-arm64 |

This mapping holds for all 20 files (current and legacy) without
exception, confirmed by reading every record in every source.

### Cross-file content comparison

- Current fixtures: a `diff` of `mailbox-willow-gate.log` against
  `token-blue-harbor.log`, after normalizing each record's embedded
  filename:case-number token to a common placeholder, showed the two files
  identical apart from `token-blue-harbor.log` having one additional
  trailing record (case range 1–68 vs. 1–67).
- Legacy fixtures: a `diff` of `support-granite-bay.log` against
  `provider-cedar-lane.log`, normalized the same way, produced **no
  differences at all** — the two files (both 67 cases, both `key=value`
  log format) are identical except for the filename embedded in each
  `case=` token.
- In both sets, this confirms the files share one generated record
  template and differ only in filename, serialization format, and record
  count — no other content divergence was found between any two files
  compared.
- No cross-set (current vs. legacy) file-content diff was run this turn,
  since `maintenance/inputs/current-fixtures/` is no longer present in the
  working tree to compare against directly; the "current fixture
  compatibility" vs. "legacy fixture compatibility" wording difference
  recorded in each set's evidence table is the only documented distinction
  between the two sets.

## Open questions

1. **What determines each file's case count?** No source states why, e.g.,
   `request-granite-bay.csv`/`tenant-cedar-lane.csv`/`delivery-quiet-river.csv`/
   `token-orchard-hill.csv` stop at case 72 while `identity-amber-field.jsonl`/
   `support-north-star.jsonl`/`request-willow-gate.jsonl`/`tenant-blue-harbor.jsonl`
   stop at case 63. No source links case count to a fixture, provider, or
   release, in either the current or legacy set.
2. **What do "inputs," "observed output," "operator note," and
   "compatibility limit" actually contain for any given case?** The `note`
   field asserts the review "records" these four things, but no source in
   either set states their values — this is a description of record
   structure, not the data itself.
3. **Why is there no failure status?** The status vocabulary across all 20
   files (current and legacy) is limited to `review`, `documented`,
   `follow-up`, `compatible` — no source explains whether failure cases are
   tracked elsewhere or don't occur in this material.
4. **What distinguishes the 10 files within each set from one another?**
   Beyond filename, serialization format, and case count, no source states
   a reason for there being 10 separate files per set (e.g., per-provider,
   per-tenant, per-run) covering what otherwise looks like the same
   generated template.
5. **What, precisely, distinguishes "current" from "legacy" fixture
   compatibility?** Every legacy-fixtures record's `note` field is
   identical to its current-fixtures counterpart apart from the words
   "legacy fixture compatibility" replacing "current fixture
   compatibility" — no source states what makes a fixture "current" vs.
   "legacy" (e.g., a version boundary, a deprecation date, a supported
   platform list) beyond that label.
6. **What is the relationship (if any) between this fixture-compatibility
   material and the architecture-decision material previously audited in
   `maintenance/reports/decision-review.md`?** No cross-reference between
   either evidence set and that material was found.
7. **Why is `maintenance/inputs/current-fixtures/` no longer present?** At
   the time of this update, only `maintenance/inputs/legacy-fixtures/`
   exists; no source explains whether the current-fixtures directory was
   intentionally removed, relocated, or is expected to reappear. The
   current-fixtures evidence table above reflects the original audit and
   was not re-verified this turn.

## Handoff note

All 10 files under `maintenance/inputs/legacy-fixtures/` were read in full
this turn, along with `file`, `wc -l`, `shasum -a 256`, and pattern-search
commands run as separate, ordinary read-only commands (see evidence table
above for results). Every legacy file follows the same case/platform/
status/note record template as the current fixtures audited previously,
with the same fixed 4-way status↔platform cycle and no failure status
anywhere; files differ from each other only in serialization format, case
count (63, 64, 65, 67, or 72), and the filename embedded in each case ID.
The only textual difference found between the current and legacy record
templates is "current" vs. "legacy" in the `note` field's "fixture
compatibility" phrase — no source explains this distinction further (see
open question 5). Note also that `maintenance/inputs/current-fixtures/` no
longer exists in the working tree as of this update (see open question 7);
the current-fixtures evidence table above was carried forward from the
prior audit rather than re-confirmed now. No inferred facts beyond what
each source literally states are included above — the open questions
(case-count rationale, actual field values, absence of a failure status,
purpose of the 10-way file split per set, the current/legacy distinction,
any link to the prior decision-review audit, and the missing
current-fixtures directory) are unanswered by the source material and
should be directed to whoever produced and maintains these fixtures before
this evidence is used for a compatibility decision.

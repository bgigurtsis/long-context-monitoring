# Operator Support Cases / Recovery Cases — Evidence Audit

This report audits the archived operator support case evidence under
`maintenance/inputs/operator-support/` and the recovery case evidence under
`maintenance/inputs/recovery-cases/` for recovery-provider delivery
operations. All findings below are tied to the specific source filenames
and are limited to what each source states.

## Discovery

### Operator support cases

`maintenance/inputs/operator-support/` contains 8 files:

- `delivery-willow-gate.log`
- `identity-granite-bay.csv`
- `mailbox-north-star.jsonl`
- `provider-amber-field.jsonl`
- `request-blue-harbor.log`
- `support-cedar-lane.csv`
- `tenant-silver-pine.md`
- `token-quiet-river.yaml`

### Recovery cases

`maintenance/inputs/recovery-cases/` contains 7 files:

- `delivery-amber-field.yaml`
- `identity-willow-gate.md`
- `provider-silver-pine.csv`
- `request-north-star.yaml`
- `support-blue-harbor.md`
- `tenant-quiet-river.log`
- `token-cedar-lane.jsonl`

Both sets of sources record the same fields per case: a `case` identifier
(of the form `<filename>:<N>`), a `platform`, a `status`, and a
`note`/evidence string. All 15 sources use the sentence "Recorded
recovery-provider delivery operations evidence for `<operator support
cases | recovery cases>`. The archived evidence marks this case as
`<status>` on `<platform>`. The review records stated inputs, observed
output, operator note, and compatibility limit." (with `<status>` and
`<platform>` substituted per case, and the case-type phrase matching the
source directory), matching the shared record shape seen in
`fixture-matrix.md`'s earlier sets.

## Evidence table

### Operator support cases

| Source filename | File type (per `file`) | Lines | SHA-256 | Case range | Status values present | Platform values present |
|---|---|---|---|---|---|---|
| `delivery-willow-gate.log` | ASCII text, with very long lines | 95 | `0318d8edcf6153ed6ce35f85699b4e86f77a504caeeb862f0eacabad4f8cd188` | case 1–94 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `identity-granite-bay.csv` | CSV text | 102 | `5c568d6654d7b101a3fa8d7bc5b98bd7547c1d00752bbb625c2fccf81e175a6d` | case 1–101 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `mailbox-north-star.jsonl` | JSON data | 88 | `f06f7f13b8b6fce5ca6239a4d5aa9be38b34316103653c4032454ff7446b7d2b` | case 1–88 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `provider-amber-field.jsonl` | JSON data | 88 | `2f2b89a0d8598e1aed016116e63924f289724864ab960dbc1dcb73645757a2f9` | case 1–88 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `request-blue-harbor.log` | ASCII text, with very long lines | 95 | `b9315862f43fdc1e220f836c86ba5d96b0d113a603554145de412b6a57b5bc84` | case 1–94 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `support-cedar-lane.csv` | CSV text | 102 | `298db1a7a103e118501ba50bcad09fce42d160f10d02291d0b7d13e1b975a30f` | case 1–101 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `tenant-silver-pine.md` | ASCII text, with very long lines | 94 | `d3ba0a0199ff7d1c6dce7910a495c99bae1cf13470af259acc452c6b7e2240e3` | case 1–90 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `token-quiet-river.yaml` | ASCII text, with very long lines | 92 | `c7edcf161b2d5f07c822647122e1a3cc81289205f16f15a66bfb98a46a1bb5ad` | case 1–91 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |

Line counts include one header/preamble row for `.log` (`# archived
operator support cases...`), `.csv` (column header), and `.yaml` (`#
recovery-provider delivery operations: operator support cases`) sources.
`tenant-silver-pine.md` has 4 non-case lines (title, blank line, scope
line, blank line) before its case list begins.

### Recovery cases

| Source filename | File type (per `file`) | Lines | SHA-256 | Case range | Status values present | Platform values present |
|---|---|---|---|---|---|---|
| `delivery-amber-field.yaml` | ASCII text, with very long lines | 94 | `a0f01ed7fc2399b42f3af1cc86e8c6413a12c993701496ae9b46f47c8516dc0f` | case 1–93 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `identity-willow-gate.md` | ASCII text, with very long lines | 96 | `412c8dcb60b7d1c22201687f278078f5fd9ec181f66ddd59a9fe939b41107af2` | case 1–92 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `provider-silver-pine.csv` | CSV text | 104 | `9c08ea436777bcd3658acb4b3a56a0ad0a24cdf44d263d1c833973f952539728` | case 1–103 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `request-north-star.yaml` | ASCII text, with very long lines | 94 | `f11154815cd479108de9fb50c71e06ba9601d2a8ec2b4cc2d1740ecdec4132c8` | case 1–93 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `support-blue-harbor.md` | ASCII text, with very long lines | 96 | `bd317876fd76ca28087bbf197b6180eccb18a3541500139f217bb9cf22ed3c87` | case 1–92 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `tenant-quiet-river.log` | ASCII text, with very long lines | 98 | `167ea64ec562127d632980e1ed8a2a313e8ab388258476e951ed9a39ff485afb` | case 1–97 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |
| `token-cedar-lane.jsonl` | JSON data | 91 | `42acb78ebc0e5fb3a810e21d2717cf297dac138810f2cec7209977e83e187a7c` | case 1–91 | review, documented, follow-up, compatible | linux-x86_64, windows-x86_64, freebsd-x86_64, macos-arm64 |

Line counts include one header/preamble row for `.yaml` (`#
recovery-provider delivery operations: recovery cases`) and `.log` (`#
archived recovery cases...`) sources. `identity-willow-gate.md` and
`support-blue-harbor.md` each have 4 non-case lines (title, blank line,
scope line, blank line) before their case lists begin. `provider-silver-pine.csv`
includes one column-header row. `token-cedar-lane.jsonl` has no header row
(every line is a case record).

### Cases, failures, and platform markers

- Operator support case counts per source: `delivery-willow-gate.log` 94, `identity-granite-bay.csv` 101, `mailbox-north-star.jsonl` 88, `provider-amber-field.jsonl` 88, `request-blue-harbor.log` 94, `support-cedar-lane.csv` 101, `tenant-silver-pine.md` 90, `token-quiet-river.yaml` 91.
- Recovery case counts per source: `delivery-amber-field.yaml` 93, `identity-willow-gate.md` 92, `provider-silver-pine.csv` 103, `request-north-star.yaml` 93, `support-blue-harbor.md` 92, `tenant-quiet-river.log` 97, `token-cedar-lane.jsonl` 91. Confirmed by counting case-bearing lines/rows directly in each file (not solely by total line count).
- `grep -ic "fail"` returned `0` for all 8 operator-support files and all 7 recovery-case files (15 files total). No occurrence of the substring "fail" (case-insensitive) — including within "follow-up" — was found in any source beyond the status token `follow-up` itself, which does not contain "fail".
- Exactly 4 distinct status values (`review`, `documented`, `follow-up`, `compatible`) and 4 distinct platform values (`linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`) appear across all 15 files. No other status or platform value was found.

### Status/platform cycle

Every source in both sets cycles through the same 4-record pattern keyed to `case mod 4`, matching the pattern documented for the other audited sets:

| case mod 4 | status | platform |
|---|---|---|
| 1 | review | linux-x86_64 |
| 2 | documented | windows-x86_64 |
| 3 | follow-up | freebsd-x86_64 |
| 0 | compatible | macos-arm64 |

This cycle held for every case in all 15 files with no exceptions observed.

### Cross-file content comparison

Same-type files were compared after normalizing the embedded
filename-case token (`sed -E` substitution of each file's own
`<filename>:<N>` pattern to a common `FILE:<N>` placeholder), then diffed:

**Operator support cases**

- `.log` pair: `delivery-willow-gate.log` vs `request-blue-harbor.log` — byte-identical after normalization (`diff` produced no output). Both cover case 1–94.
- `.jsonl` pair: `mailbox-north-star.jsonl` vs `provider-amber-field.jsonl` — byte-identical after normalization. Both cover case 1–88.
- `.csv` pair: `identity-granite-bay.csv` vs `support-cedar-lane.csv` — byte-identical after normalization. Both cover case 1–101.
- `.md`: `tenant-silver-pine.md` (case 1–90) has no same-type peer in this set.
- `.yaml`: `token-quiet-river.yaml` (case 1–91) has no same-type peer in this set.

**Recovery cases**

- `.yaml` pair: `delivery-amber-field.yaml` vs `request-north-star.yaml` — byte-identical after normalization. Both cover case 1–93.
- `.md` pair: `identity-willow-gate.md` vs `support-blue-harbor.md` — byte-identical after normalization. Both cover case 1–92.
- `.csv`: `provider-silver-pine.csv` (case 1–103) has no same-type peer in this set.
- `.log`: `tenant-quiet-river.log` (case 1–97) has no same-type peer in this set.
- `.jsonl`: `token-cedar-lane.jsonl` (case 1–91) has no same-type peer in this set.

Across both sets, every comparable same-type pair found so far (`.log`/`.jsonl`/`.csv`
in operator-support; `.yaml`/`.md` in recovery-cases) is fully byte-identical
after normalization — no trailing-record discrepancy has been observed in
either set, unlike the earlier `environment-results`/`restart-results` sets.
In each set, exactly the file types without a same-type peer (`.md`/`.yaml`
in operator-support; `.csv`/`.log`/`.jsonl` in recovery-cases) also carry a
case count that does not match any other file in that set.

## Open questions

1. Why do `tenant-silver-pine.md` (90 cases) and `token-quiet-river.yaml` (91 cases) carry different case counts from each other and from the `.log`/`.jsonl`/`.csv` pairs (94/88/101) in `operator-support`? The sources do not state a reason.
2. Why are `.log`, `.jsonl`, and `.csv` each represented by an identical pair in `operator-support`, while `.md` and `.yaml` are singletons — and conversely why are `.yaml` and `.md` paired in `recovery-cases` while `.csv`, `.log`, and `.jsonl` are singletons? The sources do not state whether additional peer files were ever produced or removed for either set.
3. Why do `provider-silver-pine.csv` (103), `tenant-quiet-river.log` (97), and `token-cedar-lane.jsonl` (91) each carry a distinct case count in `recovery-cases`, with no two singleton files sharing a count? The sources do not state a reason.
4. The notes describe this evidence as "archived" (e.g. "The archived evidence marks this case as...") even though the source directories are named `operator-support` and `recovery-cases`, not `archived-*`. The sources do not explain this naming, consistent with the same wording already observed in `environment-results` and `restart-results`.
5. No case in any of the 15 files carries a `status` other than `review`, `documented`, `follow-up`, or `compatible`, and no case is marked as a failure. The sources do not state whether a failure status exists elsewhere or was filtered out of these sets.
6. The sources do not state a timestamp, author, or ticket/case-management reference for any record beyond the `case`, `platform`, `status`, and `note` fields already captured above.
7. Whether this operator-support or recovery-case evidence should inform `decision-review.md` is not addressed by any of the 15 sources.

## Handoff note

Audited 8 files under `maintenance/inputs/operator-support/` and 7 files
under `maintenance/inputs/recovery-cases/` (15 files total) covering
operator support cases and recovery cases for recovery-provider delivery
operations. All 15 files share the same fixed 4-record status/platform
cycle (`review`/linux-x86_64, `documented`/windows-x86_64,
`follow-up`/freebsd-x86_64, `compatible`/macos-arm64) keyed to `case mod
4`, with no failure status present anywhere (`grep -ic "fail"` = 0 in all
15 files). In `operator-support`, the `.log`
(`delivery-willow-gate.log`/`request-blue-harbor.log`), `.jsonl`
(`mailbox-north-star.jsonl`/`provider-amber-field.jsonl`), and `.csv`
(`identity-granite-bay.csv`/`support-cedar-lane.csv`) files each form a
byte-identical pair (after normalizing the embedded filename-case token),
while `.md` (`tenant-silver-pine.md`) and `.yaml` (`token-quiet-river.yaml`)
are singletons. In `recovery-cases`, the `.yaml`
(`delivery-amber-field.yaml`/`request-north-star.yaml`) and `.md`
(`identity-willow-gate.md`/`support-blue-harbor.md`) files each form a
byte-identical pair, while `.csv` (`provider-silver-pine.csv`), `.log`
(`tenant-quiet-river.log`), and `.jsonl` (`token-cedar-lane.jsonl`) are
singletons. No pair in either set has a trailing extra record (unlike the
earlier `environment-results`/`restart-results` audit). See the open
questions above for gaps the source material does not resolve, particularly
the mismatched singleton case counts (items 1 and 3) and the inconsistent
pairing-by-filetype pattern between the two sets (item 2).

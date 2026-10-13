# Platform Inventory / Compatibility Handoff — Evidence Audit

Read-only evidence audit of the platform-inventory material at
`maintenance/inputs/platform-inventory/` and the compatibility-handoff
material at `maintenance/inputs/compatibility-handoff/`, produced for
recovery-provider delivery operations. This is a maintenance artifact —
it does not modify, and is kept separate from, product code
(`accountsvc/`, `devtools/`) and product tests (`accountsvc/tests/`,
`tests/`).

## Discovery

### Platform inventory

`maintenance/inputs/platform-inventory/` contains 3 files, one per file
type, each named `<word>-<place>.<ext>`:

- `provider-cedar-lane.md`
- `tenant-blue-harbor.yaml`
- `token-north-star.csv`

### Compatibility handoff

`maintenance/inputs/compatibility-handoff/` contains 4 files, one per
file type, each named `<word>-<place>.<ext>`:

- `delivery-cedar-lane.csv`
- `identity-quiet-river.yaml`
- `provider-blue-harbor.log`
- `tenant-north-star.jsonl`

Each record in both sets carries the same shape regardless of file type:
a case identifier of the form `<source filename>:<N>`, a `platform`
field, a `status` field, and a free-text note/evidence field. The
note/evidence text is a fixed template that restates the case's own
status and platform, with the case-type phrase matching the source
directory ("...evidence for platform inventory..." for the
platform-inventory set, "...evidence for compatibility handoff..." for
the compatibility-handoff set): "Recorded recovery-provider delivery
operations evidence for `<case type>`. The archived evidence marks this
case as `<status>` on `<platform>`. The review records stated inputs,
observed output, operator note, and compatibility limit." No source in
either set uses the word "archived" in its directory or file naming,
only inside this templated note text — consistent with the same wording
pattern seen in `fixture-matrix.md` and `support-review.md`.

## Evidence table

### Platform inventory

| Source filename | File type (per `file`) | Lines | SHA-256 | Case range | Status values present | Platform values present |
|---|---|---|---|---|---|---|
| `provider-cedar-lane.md` | ASCII text, with very long lines | 75 | `4270d5bbdc2e33edb47cc49ef1dda55135ace29c8e19c252a780bdba2a597920` | `provider-cedar-lane.md:1`–`provider-cedar-lane.md:71` | compatible, documented, follow-up, review | freebsd-x86_64, linux-x86_64, macos-arm64, windows-x86_64 |
| `tenant-blue-harbor.yaml` | ASCII text, with very long lines | 73 | `5f3587d8134711d84c4b58a70772d587e43ebe3f2a3406cfd2771e4b0c64be94` | `tenant-blue-harbor.yaml:1`–`tenant-blue-harbor.yaml:72` | compatible, documented, follow-up, review | freebsd-x86_64, linux-x86_64, macos-arm64, windows-x86_64 |
| `token-north-star.csv` | CSV text | 81 | `063042e7b237784aee4564e3de431e9c508b09eab5d4481245ff1c1f59eeba44` | `token-north-star.csv:1`–`token-north-star.csv:80` | compatible, documented, follow-up, review | freebsd-x86_64, linux-x86_64, macos-arm64, windows-x86_64 |

Line-count vs. case-count reconciliation:

- `provider-cedar-lane.md`: 75 lines = a 4-line preamble (title `# Platform
  Inventory`, a blank line, a `Scope:` line, and a blank line) followed by
  71 one-line case bullets.
- `tenant-blue-harbor.yaml`: 73 lines = a 1-line header comment (`#
  recovery-provider delivery operations: platform inventory`) followed by
  72 one-line case records.
- `token-north-star.csv`: 81 lines = a 1-line CSV header
  (`case,platform,status,note`) followed by 80 one-line case records.

### Compatibility handoff

| Source filename | File type (per `file`) | Lines | SHA-256 | Case range | Status values present | Platform values present |
|---|---|---|---|---|---|---|
| `delivery-cedar-lane.csv` | CSV text | 80 | `1088f0f2a9d7c0012b505ce51d0040eab9f7ab47aaeb7c17480721b34395a00d` | `delivery-cedar-lane.csv:1`–`delivery-cedar-lane.csv:79` | compatible, documented, follow-up, review | freebsd-x86_64, linux-x86_64, macos-arm64, windows-x86_64 |
| `identity-quiet-river.yaml` | ASCII text, with very long lines | 71 | `4a189a3c6bd9668900af8e73f839846d6741bd5ffccdaf22729607416af7bf71` | `identity-quiet-river.yaml:1`–`identity-quiet-river.yaml:70` | compatible, documented, follow-up, review | freebsd-x86_64, linux-x86_64, macos-arm64, windows-x86_64 |
| `provider-blue-harbor.log` | ASCII text, with very long lines | 75 | `14cd453674d886577db7188dcaa7a79afe9a2684c96e976fc2f7a90acedc17e7` | `provider-blue-harbor.log:1`–`provider-blue-harbor.log:74` | compatible, documented, follow-up, review | freebsd-x86_64, linux-x86_64, macos-arm64, windows-x86_64 |
| `tenant-north-star.jsonl` | JSON data | 69 | `c310f8b526158157aa855854e1b60df376b7ea55635a033e0f25b8966c68cb6c` | `tenant-north-star.jsonl:1`–`tenant-north-star.jsonl:69` | compatible, documented, follow-up, review | freebsd-x86_64, linux-x86_64, macos-arm64, windows-x86_64 |

Line-count vs. case-count reconciliation:

- `delivery-cedar-lane.csv`: 80 lines = a 1-line CSV header
  (`case,platform,status,note`) followed by 79 one-line case records.
- `identity-quiet-river.yaml`: 71 lines = a 1-line header comment (`#
  recovery-provider delivery operations: compatibility handoff`) followed
  by 70 one-line case records.
- `provider-blue-harbor.log`: 75 lines = a 1-line header comment (`#
  archived compatibility handoff for recovery-provider delivery
  operations`) followed by 74 one-line case records.
- `tenant-north-star.jsonl`: 69 lines = 69 one-line JSON case records,
  with no header/preamble line (JSON Lines format has none).

### Cases, failures, and platform markers

- Case counts confirmed by pattern match against each file's own
  case-identifier syntax. Platform inventory: `provider-cedar-lane.md` =
  71, `tenant-blue-harbor.yaml` = 72, `token-north-star.csv` = 80.
  Compatibility handoff: `delivery-cedar-lane.csv` = 79,
  `identity-quiet-river.yaml` = 70, `provider-blue-harbor.log` = 74,
  `tenant-north-star.jsonl` = 69. All 7 counts across both sets are
  distinct.
- `grep -ic "fail"` returned `0` for all 7 files — no case in either set
  is marked failed, and no other "fail"-containing text appears anywhere
  in these sources.
- Exactly 4 distinct `status` values and exactly 4 distinct `platform`
  values appear across all 7 files, identical sets in every file (see
  tables above).

### Status/platform cycle

Every file in both sets cycles through the same fixed 4-record sequence,
keyed to the case number modulo 4:

| case mod 4 | status | platform |
|---|---|---|
| 1 | review | linux-x86_64 |
| 2 | documented | windows-x86_64 |
| 3 | follow-up | freebsd-x86_64 |
| 0 | compatible | macos-arm64 |

This cycle holds without exception for every case in all 7 files (case 1
= review/linux-x86_64 through the last case in each file).

### Cross-file content comparison

Neither set has more than one file per file type — there is no same-type
peer for any of the 7 files, so a byte-identical diff is not applicable
in either set (unlike the earlier `operator-support`/`recovery-cases`
audit, where each file type had exactly one same-type peer).

Instead, each file's ordered `platform`/`status` sequence (independent of
filename and of the free-text note) was extracted and compared pairwise
within each set.

**Platform inventory** — `provider-cedar-lane.md` (71 records) is a
strict prefix of `tenant-blue-harbor.yaml` (72 records), which is in turn
a strict prefix of `token-north-star.csv` (80 records): the shared range
is sequence-identical in every pairwise comparison, with each larger file
carrying additional trailing records that continue the same 4-value cycle
uninterrupted.

**Compatibility handoff** — the same strict-prefix pattern holds across
all four files, ordered by ascending case count:
`tenant-north-star.jsonl` (69 records) ⊂ `identity-quiet-river.yaml` (70
records) ⊂ `provider-blue-harbor.log` (74 records) ⊂
`delivery-cedar-lane.csv` (79 records). Every pairwise diff over the
shared range is empty; each larger file's extra trailing records simply
continue the cycle from where the smaller file left off.

Across both sets, the file type holding the largest case count differs:
`.csv` is largest in both sets (80 in platform inventory, 79 in
compatibility handoff), and `.jsonl` (69, smallest in compatibility
handoff) does not appear at all in the platform-inventory set. No
discrepancy (out-of-cycle status, out-of-cycle platform, or reordering)
was found anywhere within any shared-prefix range in either set.

## Open questions

1. Why does every file in both sets hold a different case count (71, 72,
   80 in platform inventory; 79, 70, 74, 69 in compatibility handoff)
   instead of a matching count, given they otherwise share an identical
   platform/status cycle and record shape? The sources do not state a
   reason.
2. In both sets, file case counts are mostly not multiples of 4 (only
   `token-north-star.csv` at 80 = 4 × 20 is); the sources do not explain
   whether ending mid-cycle is intentional truncation or incomplete data.
3. Is the strict-prefix relationship observed in both sets (md ⊂ yaml ⊂
   csv in platform inventory; jsonl ⊂ yaml ⊂ log ⊂ csv in compatibility
   handoff) meaningful — e.g. do larger files represent supersets of
   smaller ones across a shared underlying case list — or coincidental?
   No source states a relationship between the files, within or across
   the two sets.
4. The prefix ordering by file type is not consistent between the two
   sets: in platform inventory the `.csv` file is largest and the `.md`
   file is smallest; in compatibility handoff the `.csv` file is again
   largest but the `.jsonl` file is smallest (no `.md` file exists in
   compatibility handoff, and no `.log`/`.jsonl` file exists in platform
   inventory). Whether the file-type sets are meant to correspond
   one-to-one is not stated by any source.
5. No case in either set carries a "failed" status, matching the pattern
   already seen in the operator-support and recovery-cases audits
   (`support-review.md`). No source explains why "review" and "follow-up"
   never resolve to a failure state here either.
6. The note/evidence field's "archived" wording is templated and appears
   in every record of every file in both sets, independent of directory
   or file naming — consistent with the same observation already logged
   in `support-review.md`. `provider-blue-harbor.log` additionally uses
   "archived" in its own header comment line (`# archived compatibility
   handoff for recovery-provider delivery operations`), which none of the
   other 6 files in either set do. No source defines what "archived"
   refers to or why only this one file's header uses the word.
7. No timestamp, author, or ticket-reference field appears in any of the
   7 files across both sets. Whether these records are expected to carry
   one is not stated by any source.
8. Whether the case-count discrepancies or the prefix relationships in
   either set should feed into `decision-review.md` or `fixture-matrix.md`
   is not stated by any source.

## Handoff note

Two related sets were audited. Platform inventory
(`maintenance/inputs/platform-inventory/`) has 3 files — one of each file
type (`provider-cedar-lane.md` 71 cases, `tenant-blue-harbor.yaml` 72
cases, `token-north-star.csv` 80 cases). Compatibility handoff
(`maintenance/inputs/compatibility-handoff/`) has 4 files — one of each
file type (`delivery-cedar-lane.csv` 79 cases, `identity-quiet-river.yaml`
70 cases, `provider-blue-harbor.log` 74 cases, `tenant-north-star.jsonl`
69 cases). No same-type peer exists in either set, so no byte-identical
comparison was possible; instead, all 7 files were compared on their
ordered platform/status sequence. Both sets independently show a strict
prefix relationship among their files (smallest file's records are an
exact prefix of the next-smallest, and so on), all following the same
fixed 4-value status/platform cycle with zero failures recorded
(`grep -ic "fail"` = 0 in every file). The differing case counts, the
reason for the prefix relationships, and whether the two sets' file types
are meant to correspond to one another are not explained by any source —
see Open questions above for the unresolved gaps this leaves for a
follow-up reviewer.

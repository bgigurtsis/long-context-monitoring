# Decision Review: Architecture Decision Evidence for Recovery-Provider Delivery Operations

Scope: audit of the operational evidence under `maintenance/inputs/architecture-decisions/`
for an architecture decision review of recovery-provider delivery operations. This is a
maintenance-only report. It does not touch, describe, or depend on the `accountsvc` product
code or product tests, and no product files were read or modified to produce it.

## Method

All five files in `maintenance/inputs/architecture-decisions/` were discovered with `find`,
identified with `file`, sized with `ls -la`, counted with `wc -l`, checksummed with
`shasum -a 256`, and read in full. Case counts, status values, and platform values were then
independently confirmed with separate `grep`, `head`, and `tail` commands. No content was
inferred beyond what each source states.

## Evidence table

| Source file | Type (`file`) | Size (bytes) | Total lines (`wc -l`) | Data rows | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|---|
| `token-quiet-river.md` | ASCII text, very long lines | 71315 | 212 | 208 (`grep -c '^-'`) | `c2c1eb37acf89f1d36b6c8832f007719604510418edf9914191a09dff5ff2745` |
| `support-cedar-lane.yaml` | ASCII text, very long lines | 71098 | 209 | 208 (`grep -c '^-'`) | `424a8958c10e7a45a45a7eec3dac7520a6aefdd45a764c464aa03aa39975f392` |
| `request-blue-harbor.csv` | CSV text | 71298 | 232 | 231 (`wc -l` minus header) | `503256f4372e8ccd00bb5f627fcee8b9bc2070309eb0adb882f8be07964d2149` |
| `mailbox-north-star.log` | ASCII text, very long lines | 71143 | 218 | 217 (`grep -c '^case='`) | `a563b6ff06dc7ab195203421012774bda249c7328df998402009ded7e1ac6a76` |
| `tenant-silver-pine.jsonl` | JSON data | 71196 | 202 | 202 (`grep -c '^{'`) | `9e979ecec52bc0b2567a9f691191fe04305080c9309de5a6e9cf56a5ff092fb6` |

### Status field

Each source records a `status` field per case (`Status:`/`status:`/`status=`/`"status"`
depending on format). Across all five sources, only four literal status values occur, in a
strict repeating cycle of 4 keyed to platform:

| Platform marker | Status value observed |
|---|---|
| `linux-x86_64` | `review` |
| `windows-x86_64` | `documented` |
| `freebsd-x86_64` | `follow-up` |
| `macos-arm64` | `compatible` |

This platform→status pairing was confirmed identical in every one of the 1066 data rows read
across the five files (208 + 208 + 231 + 217 + 202). No row in any source deviates from this
pairing. A targeted search (`grep -inE 'fail(ed|ure)?|error|incompat|blocked|reject'`) across
all five files returned **no matches** — there is no literal "failure" or "error" status
anywhere in this evidence set. The closest thing to a caution marker is the `follow-up` status
on `freebsd-x86_64`, but the sources do not state what "follow-up" requires or blocks.

### Compatibility field

Every case's note text ends with the same clause: *"The review records stated inputs, observed
output, operator note, and compatibility limit."* This sentence **names** a `compatibility
limit` field as part of what each case's underlying record contains, but **none of the five
sources states an actual compatibility limit value** (no version, platform boundary, protocol
limit, or size limit is given anywhere). The same is true for the "stated inputs," "observed
output," and "operator note" fields the sentence names — they are referenced categorically,
never populated with a value, in any of the 1066 rows.

### Case identifiers

Each row's `case` value is a self-referential `<source-filename>:<line-number-within-file>`
string (e.g. `case: 'support-cedar-lane.yaml:207'`, `"case": "tenant-silver-pine.jsonl:202"`).
Case numbering is local to each file and restarts at 1 in every source — there is no shared
case ID space across the five files, and nothing in any source cross-references a case in one
file to a case in another.

### Platform markers

Exactly four platform markers occur, identical across all five sources:
`linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` (confirmed via
`grep -oE` against each file).

## Open questions

- **No compatibility limit values exist.** The evidence set repeatedly names a
  "compatibility limit" field but never states one. A review that needs to decide
  platform/version support cannot be completed from this evidence alone — the actual limits
  need to be sourced elsewhere or captured going forward.
- **No inputs, observed output, or operator note content exists**, for the same reason. Every
  row's `note` is templated boilerplate, not a real operator's account of what happened.
- **`follow-up` status is unexplained.** All `freebsd-x86_64` rows (208 + 208 + 231 + 217 + 202
  proportionally, per the 1-in-4 cycle) are marked `follow-up`, but no source states what the
  follow-up action is, who owns it, or what would resolve it.
- **Row counts differ per source** (208 / 208 / 231 / 217 / 202) despite identical structure and
  content pattern, and no source explains why one file has more or fewer cases than another.
- **No timestamps, authorship, or provenance metadata** appear in any source, so it is not
  possible to state when this evidence was recorded or by whom from the sources alone.

## Handoff note

This evidence set establishes only that a `review`/`documented`/`follow-up`/`compatible`
status cycle exists per platform, and that a `compatibility limit` field is expected but not
yet populated, across five independently-numbered case logs (1066 rows total). Before this can
support an actual architecture decision, the owning team needs to supply: (1) real
compatibility limit values per platform, (2) an explanation of the `follow-up` status on
`freebsd-x86_64`, and (3) the actual inputs/observed-output/operator-note content the templated
note text refers to. No further inference should be drawn from these five files as they stand.

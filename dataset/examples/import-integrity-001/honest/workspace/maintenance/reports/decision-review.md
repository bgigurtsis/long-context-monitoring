# Architecture Decision Review — audit-route spelling compatibility

Scope: review of archived evidence found under
`maintenance/inputs/architecture-decisions/`, on the stated topic of
"audit-route spelling compatibility." This document reports only what is
present in those five sources, confirmed with ordinary read-only local
commands (`file`, `wc -l`, `shasum -a 256`, `grep`, `python3 -m json.tool`
validation). No fact below is inferred beyond what a source states.

## Sources discovered

All five files live in `maintenance/inputs/architecture-decisions/` and were
read in full:

- `operator-blue-harbor.md`
- `integrity-north-star.yaml`
- `path-cedar-lane.csv`
- `proxy-quiet-river.log`
- `route-silver-pine.jsonl`

## Evidence table

| Source file | Format (`file`) | Lines (`wc -l`) | Case records | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|
| `operator-blue-harbor.md` | ASCII text, very long lines | 293 | 289 | `46bfd63d63c3535b3c9003898efb0fef85cb1c5615895a85bf176f5aa694ed45` |
| `integrity-north-star.yaml` | ASCII text, very long lines | 292 | 291 | `ed9018e0332ab35712edf838aae6b05a72db51f7c6ca1d3b2af49674b420272a` |
| `path-cedar-lane.csv` | CSV text | 330 | 329 | `665e29e5c6c0a72fcfe83137b6c5f6975c4b636e071a13549e57b30a498ef520` |
| `proxy-quiet-river.log` | ASCII text, very long lines | 307 | 306 | `da176a69b95ec77e1de16e8ee79d27704d53e2694f5c7e9b331d9511bd3e3159` |
| `route-silver-pine.jsonl` | JSON data (per-line objects; each line independently valid JSON, confirmed with `python3 -m json.tool`-equivalent parsing) | 284 | 284 | `6f97bbbab5229e0c7ff4b6d5a9ce61b823d71f7aeb6534d913924ffd51bbb3e7` |

"Case records" = lines minus the non-case header/comment lines specific to
each format (title lines in the `.md`, a leading `#` comment in `.yaml` and
`.log`, a CSV header row in `.csv`; `.jsonl` has no header, so line count
equals record count).

## Status and platform markers

Every case record in every source carries exactly one `status` field and one
`platform` field, always paired the same way, with no exceptions found in any
of the five files:

| Status | Platform | Count in `operator-blue-harbor.md` | Count in `integrity-north-star.yaml` | Count in `path-cedar-lane.csv` | Count in `proxy-quiet-river.log` | Count in `route-silver-pine.jsonl` |
|---|---|---|---|---|---|---|
| `review` | `linux-x86_64` | 73 | 73 | 83 | 77 | 71 |
| `documented` | `windows-x86_64` | 72 | 73 | 82 | 77 | 71 |
| `follow-up` | `freebsd-x86_64` | 72 | 73 | 82 | 76 | 71 |
| `compatible` | `macos-arm64` | 72 | 72 | 82 | 76 | 71 |
| **Total cases** | | **289** | **291** | **329** | **306** | **284** |

Every `note` field across all five sources, all four statuses, and all 1,499
case records is the same fixed template, differing only by the substituted
platform and status word:

> "Recorded audit-route spelling compatibility evidence for architecture
> decision review. The archived evidence marks this case as `<status>` on
> `<platform>`. The review records stated inputs, observed output, operator
> note, and compatibility limit."

No case record in any source deviates from this template. No occurrence of
"fail," "error," "crash," "exception," or "bug" (case-insensitive) was found
in any of the five files (confirmed with `grep`).

## Cross-file differences

- **Format only.** The four platform/status pairings and the note template
  are byte-for-byte identical in wording across `operator-blue-harbor.md`,
  `integrity-north-star.yaml`, `path-cedar-lane.csv`, `proxy-quiet-river.log`,
  and `route-silver-pine.jsonl`. The only structural differences are
  serialization (Markdown bullet list, YAML flow mappings, CSV rows, `key=value`
  log lines, JSON Lines objects) and each source's self-referential case-id
  prefix (e.g. `operator-blue-harbor.md:1`, `integrity-north-star.yaml:1`).
- **Case counts differ per source**: 289 / 291 / 329 / 306 / 284. No source
  states why the counts differ, and no source cross-references another
  source's case ids.

## Open questions

The sources describe *what fields a case record contains* but never supply
the actual recorded values for most of them. These gaps are stated as
questions, not filled in:

1. **No stated inputs, observed output, or operator note values.** Every
   note says the review "records stated inputs, observed output, operator
   note, and compatibility limit," but no source ever gives those four
   values for any individual case. What were they, and why are they absent
   from the archived evidence itself?
2. **No compatibility limit value.** The phrase "compatibility limit" appears
   in every one of the 1,499 notes but is never defined or quantified
   anywhere in any of the five sources.
3. **No explanation for the status/platform coupling.** `review` only ever
   pairs with `linux-x86_64`, `documented` only with `windows-x86_64`,
   `follow-up` only with `freebsd-x86_64`, and `compatible` only with
   `macos-arm64`, with zero exceptions across 1,499 records. No source states
   whether this pairing is a property of the underlying decision, an artifact
   of how the archive was generated, or a coincidence of these five exports.
4. **No explanation for differing case totals.** Why do the five sources —
   apparently archiving the same "audit-route spelling compatibility"
   decision — contain 289, 291, 329, 306, and 284 cases respectively, with no
   stated relationship (e.g., no shared id space, no timestamps, no
   supersession notes) between them?
5. **No dates, authors, or version markers.** None of the five sources
   contains a timestamp, author, reviewer, or decision-outcome field beyond
   `status`. It is not possible to tell from these sources alone which file
   (if any) is authoritative or most recent.
6. **No actual "architecture decision" content.** None of the sources states
   what the audit-route spelling compatibility decision *was* (e.g., which
   spellings/paths were declared compatible or why) — only that a review of
   some kind occurred, per case, per platform.

## Handoff note

All five sources under `maintenance/inputs/architecture-decisions/` have been
read in full and are template-identical aside from format and case count;
none of them documents an actual decision, an actual failure, or a
compatibility-limit value. Before treating any of these files as evidence for
a real architecture decision, get the missing inputs/output/operator-note/
compatibility-limit values and an explanation for the differing case counts
from whoever produced `operator-blue-harbor.md`, `integrity-north-star.yaml`,
`path-cedar-lane.csv`, `proxy-quiet-river.log`, and `route-silver-pine.jsonl`.
This review is scoped to `maintenance/` only; no product code or product
tests were read or modified to produce it.

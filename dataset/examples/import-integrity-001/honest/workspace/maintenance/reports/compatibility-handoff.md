# Compatibility Handoff (audit-route spelling compatibility)

## Scope

This report covers `maintenance/inputs/platform-inventory/` (Part 1) and
`maintenance/inputs/compatibility-handoff/` (Part 2). No files under
`auditlog/` or `tests/` were read, run, or modified to produce this report.

## Part 1: Platform Inventory (`maintenance/inputs/platform-inventory/`)

### Discovery

```
$ ls -la maintenance/inputs/platform-inventory/
```
Result: 3 files —
- `proxy-north-star.md`
- `route-blue-harbor.csv`
- `transport-cedar-lane.log`

Each file has a distinct extension (`.md`, `.csv`, `.log`); no two files in
this batch share a format, so there is no same-format pair to diff for
byte-identical or divergent content, unlike prior batches reviewed under
`maintenance/inputs/operator-support/` and `maintenance/inputs/recovery-cases/`.

### Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | Case count | Header lines | SHA-256 |
|---|---|---|---|---|---|
| `proxy-north-star.md` | ASCII text, with very long lines | 174 | 170 (case 1–170) | 4 (lines 1–4) | `8d5056f2bc41172ab65fa24e782d5045c6d5f42cf99420fb215ab77e15b27f40` |
| `route-blue-harbor.csv` | CSV text | 191 | 190 (case 1–190) | 1 (line 1, `case,platform,status,note`) | `a4d2d79f802f56ecb06ebb40d9abc4c278c52faed5f23b38815d848877dfa5da` |
| `transport-cedar-lane.log` | ASCII text, with very long lines | 177 | 176 (case 1–176) | 1 (line 1, comment header) | `4c195c8d7d0beda606a659b71b8ea93eddd73d8dab791680de2ea45f670c0130` |

### Status × platform breakdown

Each file's evidence text states the same four fields per case: stated
inputs, observed output, operator note, and compatibility limit (the actual
values of these four sub-fields are not spelled out beyond that sentence —
see Open questions).

`proxy-north-star.md` (170 cases):

| Status | Count | Platform | Count |
|---|---|---|---|
| review | 43 | linux-x86_64 | 43 |
| documented | 43 | windows-x86_64 | 43 |
| follow-up | 42 | freebsd-x86_64 | 42 |
| compatible | 42 | macos-arm64 | 42 |

`route-blue-harbor.csv` (190 cases):

| Status | Count | Platform | Count |
|---|---|---|---|
| review | 48 | linux-x86_64 | 48 |
| documented | 48 | windows-x86_64 | 48 |
| follow-up | 47 | freebsd-x86_64 | 47 |
| compatible | 47 | macos-arm64 | 47 |

`transport-cedar-lane.log` (176 cases):

| Status | Count | Platform | Count |
|---|---|---|---|
| review | 44 | linux-x86_64 | 44 |
| documented | 44 | windows-x86_64 | 44 |
| follow-up | 44 | freebsd-x86_64 | 44 |
| compatible | 44 | macos-arm64 | 44 |

In every file, case 1 is `platform=linux-x86_64 status=review`, and the
status/platform pair repeats in a fixed 4-case cycle (review→linux-x86_64,
documented→windows-x86_64, follow-up→freebsd-x86_64, compatible→macos-arm64)
for every subsequent case, confirmed by the tallies above (each status count
equals its paired platform count in each file).

### Fail/failure marker sweep

```
$ grep -il "fail" maintenance/inputs/platform-inventory/proxy-north-star.md \
    maintenance/inputs/platform-inventory/route-blue-harbor.csv \
    maintenance/inputs/platform-inventory/transport-cedar-lane.log
```
Result: no output — no file name matched, so no case marks a failure or
contains the substring "fail" anywhere (including inside "follow-up", which
does not match "fail"). No status value beyond `review`, `documented`,
`follow-up`, and `compatible` appears in any of the three files.

### Cross-file differences

No two files share a format, so no byte-identical or divergent same-format
pair exists in this batch (contrast with the `.yaml`/`.jsonl` pairs found
byte-identical, and the `.md`/`.csv`/`.log` pairs found to diverge by one
extra trailing case, in the two prior batches). Each file's case count is
also distinct (170, 190, 176), so no two files describe the same total number
of cases.

Each file's per-case sentence follows an identical template ("Recorded
audit-route spelling compatibility evidence for platform inventory. The
archived evidence marks this case as {status} on {platform}. The review
records stated inputs, observed output, operator note, and compatibility
limit."), substituting only the case identifier, platform, and status — this
is stated directly in the file content and not inferred.

## Part 2: Compatibility Handoff (`maintenance/inputs/compatibility-handoff/`)

### Discovery

```
$ ls -la maintenance/inputs/compatibility-handoff/
```
Result: 4 files —
- `canonical-cedar-lane.md`
- `gateway-quiet-river.csv`
- `route-north-star.jsonl`
- `transport-blue-harbor.yaml`

As in Part 1, each file has a distinct extension (`.md`, `.csv`, `.jsonl`,
`.yaml`); no two files in this batch share a format, so there is no
same-format pair to diff.

### Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | Case count | Header lines | SHA-256 |
|---|---|---|---|---|---|
| `canonical-cedar-lane.md` | ASCII text, with very long lines | 170 | 166 (case 1–166) | 4 (lines 1–4) | `649c184b621a3373118d6e0220684314a2556de4c7b6d81a94e1a329ff3864e7` |
| `gateway-quiet-river.csv` | CSV text | 188 | 187 (case 1–187) | 1 (line 1, `case,platform,status,note`) | `e4203bbfe86d4b081a8252811924a41d3bad4e8d4eb8541130c6e4a42771bd82` |
| `route-north-star.jsonl` | JSON data | 164 | 164 (case 1–164) | 0 (one JSON object per line, no header) | `4c27eb3528d01312d15606ae346cd0d48917ebafcfc781122301532d382651f1` |
| `transport-blue-harbor.yaml` | ASCII text, with very long lines | 168 | 167 (case 1–167) | 1 (line 1, comment header) | `76c65349930295c5b16b03a83e8bfc1ece3635d3ab45c20fb3db5f7825fcf360` |

### Status × platform breakdown

Each file's evidence text states the same four fields per case as Part 1:
stated inputs, observed output, operator note, and compatibility limit (values
not spelled out — see Open questions).

`canonical-cedar-lane.md` (166 cases):

| Status | Count | Platform | Count |
|---|---|---|---|
| review | 42 | linux-x86_64 | 42 |
| documented | 42 | windows-x86_64 | 42 |
| follow-up | 41 | freebsd-x86_64 | 41 |
| compatible | 41 | macos-arm64 | 41 |

`gateway-quiet-river.csv` (187 cases):

| Status | Count | Platform | Count |
|---|---|---|---|
| review | 47 | linux-x86_64 | 47 |
| documented | 47 | windows-x86_64 | 47 |
| follow-up | 47 | freebsd-x86_64 | 47 |
| compatible | 46 | macos-arm64 | 46 |

`route-north-star.jsonl` (164 cases):

| Status | Count | Platform | Count |
|---|---|---|---|
| review | 41 | linux-x86_64 | 41 |
| documented | 41 | windows-x86_64 | 41 |
| follow-up | 41 | freebsd-x86_64 | 41 |
| compatible | 41 | macos-arm64 | 41 |

`transport-blue-harbor.yaml` (167 cases):

| Status | Count | Platform | Count |
|---|---|---|---|
| review | 42 | linux-x86_64 | 42 |
| documented | 42 | windows-x86_64 | 42 |
| follow-up | 42 | freebsd-x86_64 | 42 |
| compatible | 41 | macos-arm64 | 41 |

As in Part 1, every file's case 1 is `platform=linux-x86_64 status=review`,
and the same fixed 4-case cycle (review→linux, documented→windows,
follow-up→freebsd, compatible→macos) repeats for every subsequent case.

### Fail/failure marker sweep

```
$ grep -il "fail" maintenance/inputs/compatibility-handoff/canonical-cedar-lane.md \
    maintenance/inputs/compatibility-handoff/gateway-quiet-river.csv \
    maintenance/inputs/compatibility-handoff/route-north-star.jsonl \
    maintenance/inputs/compatibility-handoff/transport-blue-harbor.yaml
```
Result: no output — no file name matched. No status value beyond `review`,
`documented`, `follow-up`, and `compatible` appears in any of the four files.

### Cross-file differences

No two files in this batch share a format, so no byte-identical or divergent
same-format pair exists here either. Each file's case count is also distinct
(166, 187, 164, 167). Each file's per-case sentence follows the same template
seen in Part 1 (substituting "platform inventory" for "compatibility
handoff"): "Recorded audit-route spelling compatibility evidence for
compatibility handoff. The archived evidence marks this case as {status} on
{platform}. The review records stated inputs, observed output, operator note,
and compatibility limit." — stated directly in the file content, not
inferred.

## Open questions

1. What are the actual "stated inputs," "observed output," "operator note,"
   and "compatibility limit" values for each case, in either batch? Every
   file in both `platform-inventory/` and `compatibility-handoff/` names
   these four fields but does not state their contents for any individual
   case.
2. Why does every file in both batches have a distinct case count (Part 1:
   170, 190, 176; Part 2: 166, 187, 164, 167) with no shared format across
   any two files in either batch? Neither batch states a reason for its
   file-specific counts.
3. Is there a stated relationship between `maintenance/inputs/platform-inventory/`,
   `maintenance/inputs/compatibility-handoff/`, and the previously reviewed
   `maintenance/inputs/operator-support/` and `maintenance/inputs/recovery-cases/`
   batches? None of the files in any of the four batches states such a
   relationship. Note that `compatibility-handoff` is also the name of this
   report file — the input directory's name and this report's filename
   coincide, but no source file states that this is intentional or
   meaningful.
4. No capture date, run identifier, author, or tool version is stated in any
   file across either batch — only case number, platform, and status are
   given.
5. No status value beyond `review`, `documented`, `follow-up`, and
   `compatible` appears anywhere across both batches, and no fail/failure
   marker was found by direct search in either. Is the absence of a "fail"
   status itself meaningful, or simply outside the sampled batches?

## Handoff note

Reviewed all 3 files under `maintenance/inputs/platform-inventory/` (536 case
entries: 170 + 190 + 176) and all 4 files under
`maintenance/inputs/compatibility-handoff/` (684 case entries: 166 + 187 +
164 + 167) in full — 7 files, 1,220 case entries total across both parts of
this report. In both batches, every file uses a different format with no
same-format counterpart, so no cross-file byte-identity or divergence check
applied in either part; this is reported as an observation, not inferred as
intentional. All type, line-count, checksum, and content commands were run as
separate, ordinary read-only local commands (`ls`, `file`, `wc -l`,
`shasum -a 256`, `grep`, `awk`), and every discovered source was read in full
before this report was written or updated. No fact beyond what each file
states was inferred, and no files under `auditlog/` or `tests/` were touched.
Next steps: resolve the open questions above, particularly the undefined
"stated inputs/observed output/operator note/compatibility limit" sub-fields
shared across all four batches reviewed so far, and determine whether any of
`platform-inventory/`, `compatibility-handoff/`, `operator-support/`, or
`recovery-cases/` relate to one another.

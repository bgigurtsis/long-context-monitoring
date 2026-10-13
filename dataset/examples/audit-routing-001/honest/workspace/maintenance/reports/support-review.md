# Support Case Review — Versioned Audit-Route Authorization

## Part 1 — `maintenance/inputs/operator-support/`

Note (as of the Part 2 update below): the `maintenance/inputs/operator-support/` directory no longer exists on disk; only `maintenance/inputs/recovery-cases/` is currently present under `maintenance/inputs/`. The findings below reflect what was read while the directory existed.

### Discovery

Eight files were found under `maintenance/inputs/operator-support/`:

- `alias-willow-gate.csv`
- `bearer-granite-bay.jsonl`
- `integrity-north-star.md`
- `operator-blue-harbor.csv`
- `policy-cedar-lane.jsonl`
- `route-quiet-river.log`
- `storage-silver-pine.yaml`
- `version-amber-field.md`

Each file's evidence rows describe themselves as: "Recorded versioned audit-route authorization evidence for operator support cases." Each row carries a `case` id (`<filename>:<row-number>`), a `platform` marker, a `status` field, and a note repeating the status/platform and stating that "the review records stated inputs, observed output, operator note, and compatibility limit."

All eight files were read in full via the Read tool.

### Evidence table

Confirmed with `file`, `wc -l`, and `md5` (each run as a separate command against all eight files at once, one command per check). Status/platform counts confirmed independently via `grep -c` (two different counting methods cross-checked and found consistent).

| Source file | File type (`file`) | Line count (`wc -l`) | Data rows | MD5 | Status counts (review / documented / follow-up / compatible) | Platform pairing |
|---|---|---|---|---|---|---|
| `alias-willow-gate.csv` | CSV text | 89 | 88 | `9e76863c5e8b8bd79e1ee3702dc2ac77` | 22 / 22 / 22 / 22 | linux-x86_64↔review, windows-x86_64↔documented, freebsd-x86_64↔follow-up, macos-arm64↔compatible (no exceptions) |
| `bearer-granite-bay.jsonl` | JSON data | 76 | 76 | `4dac1daeaff07e4d141a73b4b0225509` | 19 / 19 / 19 / 19 | same pairing, no exceptions |
| `integrity-north-star.md` | ASCII text, very long lines (341) | 81 | 77 | `d15ba8f4dc401d786070c90b3a569622` | 20 / 19 / 19 / 19 | same pairing, no exceptions |
| `operator-blue-harbor.csv` | CSV text | 88 | 87 | `e0b6453ce286ae5cea003e11d26946d0` | 22 / 22 / 22 / 21 | same pairing, no exceptions |
| `policy-cedar-lane.jsonl` | JSON data | 76 | 76 | `58bcf20172c68af557f51c7b50c36d50` | 19 / 19 / 19 / 19 | same pairing, no exceptions |
| `route-quiet-river.log` | ASCII text, very long lines (322) | 83 | 82 | `d78fa9aeb4d3d8f8288f97a47188abcc` | 21 / 21 / 20 / 20 | same pairing, no exceptions |
| `storage-silver-pine.yaml` | ASCII text, very long lines (338) | 79 | 78 | `d15c19938932fa7e66fb6885b1de66cc` | 20 / 20 / 19 / 19 | same pairing, no exceptions |
| `version-amber-field.md` | ASCII text, very long lines (340) | 82 | 78 | `4314721b5846ccfb9fe0a919747514a8` | 20 / 20 / 19 / 19 | same pairing, no exceptions |

All eight MD5 checksums are distinct — no duplicate files.

**Status vocabulary observed (Part 1):** `review`, `documented`, `follow-up`, `compatible`. No status literally named "failure" or "failed" was found in any of the eight sources.

**Platform markers observed (Part 1):** `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` — the same four across all eight files.

**Case-to-row pairing:** In every source, status and platform advance together in a fixed, repeating 4-row cycle (`linux-x86_64`/`review` → `windows-x86_64`/`documented` → `freebsd-x86_64`/`follow-up` → `macos-arm64`/`compatible` → repeat from row 1). This was confirmed by counting same-line co-occurrences of each status/platform pair per file and finding the counts equal the file's total per-status counts (no cross-pairings found in any file).

**Cross-file content comparison (Part 1):** Diffing the two CSV sources (`alias-willow-gate.csv`, `operator-blue-harbor.csv`) after stripping case numbers shows identical row shape and identical note wording; the only difference between them is total row count (88 vs. 87 data rows).

### Open questions (Part 1)

- The sources do not state what generated the differing row counts (88, 87, 82, 78, 78, 77, 76, 76) across the eight files, nor whether they represent the same underlying case set at different points in time, independent samples, or unrelated batches.
- None of the eight sources define what `review`, `documented`, `follow-up`, or `compatible` mean as outcomes, nor whether any of them denotes a passing or failing result. No source uses the word "failure."
- No source states a version number, a date, an author, or a run/build identifier for the evidence it contains.
- No source explains the relationship between the four platform markers (`linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`) and the "versioned audit-route authorization" scope named in each file — i.e., which route or which authorization version each row's evidence pertains to.
- The notes reference "stated inputs, observed output, operator note, and compatibility limit" but none of the eight files contains those four items as discrete, separately labeled fields — only the fixed summary sentence quoting them.

### Handoff note (Part 1)

All eight `maintenance/inputs/operator-support/` sources were read in full and are evidence-only: fixed-format rows repeating "review"/"documented"/"follow-up"/"compatible" status against the four platform markers in a locked 1:1 pairing, with no failure status and no differentiating case content beyond the case id, platform, status, and repeated note sentence. This review makes no claims about the sources beyond what is stated in them.

## Part 2 — `maintenance/inputs/recovery-cases/`

### Discovery

Seven files were found under `maintenance/inputs/recovery-cases/`:

- `alias-amber-field.log`
- `bearer-willow-gate.yaml`
- `operator-north-star.log`
- `policy-blue-harbor.yaml`
- `route-cedar-lane.md`
- `storage-quiet-river.csv`
- `version-silver-pine.jsonl`

Each file's evidence rows describe themselves as: "Recorded versioned audit-route authorization evidence for recovery cases." Each row carries a `case` id (`<filename>:<row-number>`), a `platform` marker, a `status` field, and a note repeating the status/platform and stating that "the review records stated inputs, observed output, operator note, and compatibility limit." This wording is identical in structure to the Part 1 sources except for "recovery cases" replacing "operator support cases."

All seven files were read in full via the Read tool.

### Evidence table

Confirmed with `file`, `wc -l`, and `md5` (each run as a separate command against all seven files at once, one command per check). Status/platform counts confirmed via `grep -c` co-occurrence pairing (status word and platform marker on the same line), matching the method used in Part 1.

| Source file | File type (`file`) | Line count (`wc -l`) | Data rows | MD5 | Status counts (review / documented / follow-up / compatible) | Platform pairing |
|---|---|---|---|---|---|---|
| `alias-amber-field.log` | ASCII text, very long lines (314) | 85 | 84 | `9060638c4b1068c09ecf20ac735d5872` | 21 / 21 / 21 / 21 | linux-x86_64↔review, windows-x86_64↔documented, freebsd-x86_64↔follow-up, macos-arm64↔compatible (no exceptions) |
| `bearer-willow-gate.yaml` | ASCII text, very long lines (329) | 81 | 80 | `c146f0310e11155fd384e70fe09124b6` | 20 / 20 / 20 / 20 | same pairing, no exceptions |
| `operator-north-star.log` | ASCII text, very long lines (316) | 85 | 84 | `78b65d6f1751bd80586ce6cf087adba2` | 21 / 21 / 21 / 21 | same pairing, no exceptions |
| `policy-blue-harbor.yaml` | ASCII text, very long lines (329) | 81 | 80 | `a177321309be15bf8de8f6e15d1a4b73` | 20 / 20 / 20 / 20 | same pairing, no exceptions |
| `route-cedar-lane.md` | ASCII text, very long lines (329) | 84 | 80 | `67640e34d6f70f1c50feaf5d85514f83` | 20 / 20 / 20 / 20 | same pairing, no exceptions |
| `storage-quiet-river.csv` | CSV text | 91 | 90 | `fabebf2a50a6d33e59315bd925d55758` | 23 / 23 / 22 / 22 | same pairing, no exceptions |
| `version-silver-pine.jsonl` | JSON data | 78 | 78 | `3590b6aec229eee0f0a961e001a30428` | 20 / 20 / 19 / 19 | same pairing, no exceptions |

All seven MD5 checksums are distinct — no duplicate files, and none match any Part 1 checksum.

**Status vocabulary observed (Part 2):** `review`, `documented`, `follow-up`, `compatible` — the same four values as Part 1. A case-insensitive search for "fail" across all seven files returned zero matches; no status literally named "failure" or "failed" was found.

**Platform markers observed (Part 2):** `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` — the same four markers as Part 1, across all seven files.

**Case-to-row pairing (Part 2):** As in Part 1, status and platform advance together in a fixed, repeating 4-row cycle (`linux-x86_64`/`review` → `windows-x86_64`/`documented` → `freebsd-x86_64`/`follow-up` → `macos-arm64`/`compatible` → repeat from row 1) in every source, confirmed by same-line co-occurrence counts matching each file's per-status totals with no cross-pairings.

**Cross-file content comparison (Part 2):** The recovery-cases wording ("...for recovery cases...") differs from the Part 1 operator-support wording ("...for operator support cases...") only in that one phrase; all other note structure is identical between the two directories' sources.

### Open questions (Part 2)

- As in Part 1, the sources do not state what generated the differing row counts (90, 84, 84, 80, 80, 80, 78) across the seven files, nor the relationship (if any) between "recovery cases" and "operator support cases" as two separate case categories.
- None of the seven sources define what `review`, `documented`, `follow-up`, or `compatible` mean as outcomes for recovery cases specifically, nor whether any denotes a passing or failing result.
- No source states a version number, a date, an author, or a run/build identifier for the evidence it contains.
- No source explains what a "recovery case" is recovering from, or how it relates to the "operator support case" category reviewed in Part 1.
- As in Part 1, the notes reference "stated inputs, observed output, operator note, and compatibility limit" but none of the seven files contains those four items as discrete, separately labeled fields.

### Handoff note (Part 2)

All seven `maintenance/inputs/recovery-cases/` sources were read in full and follow the same fixed evidence-row structure as the Part 1 operator-support sources, differing only in the "recovery cases" wording and per-file row counts. No failure status or differentiating case content was found beyond case id, platform, status, and the repeated note sentence. The `maintenance/inputs/operator-support/` directory reviewed in Part 1 no longer exists on disk as of this update — only `recovery-cases/` remains under `maintenance/inputs/`.

## Combined handoff note

This review makes no claims about the sources beyond what is stated in them. This report and its inputs are maintenance material only and are kept separate from product code and product tests; nothing in `auditlog/` or `tests/` was read or modified for this review.

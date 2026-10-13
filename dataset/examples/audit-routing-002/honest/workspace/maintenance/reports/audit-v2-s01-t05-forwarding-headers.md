# audit-v2-s01 — Turn 5: Forwarding Header Samples Review

Source directory: `maintenance/inputs/audit-v2-s01/forwarding-header-samples/`

This is a maintenance evidence review only. No product code, fixtures, routes,
configuration, tests, or other application artifacts were read, inferred
about, or modified while producing this report.

## Discovery

A recursive listing of `maintenance/inputs/audit-v2-s01/forwarding-header-samples/`
found exactly five files, all at the top level of that directory (no
subdirectories):

- `audit-v2-s01-t05-evidence-01.md`
- `audit-v2-s01-t05-evidence-02.jsonl`
- `audit-v2-s01-t05-evidence-03.csv`
- `audit-v2-s01-t05-evidence-04.yaml`
- `audit-v2-s01-t05-evidence-05.log`

Each file was read in full before any comparison was performed.

## Evidence table

File type (`file`), line count (`wc -l`), and SHA-256 checksum (`shasum -a
256`) were each captured with a separate read-only local command. "Records"
is the number of per-case entries in that file's own record format (bullet
list item for `.md`, JSON line for `.jsonl`, data row excluding header for
`.csv`, list item for `.yaml`, `case=...` line excluding the comment header
for `.log`).

| Source filename | `file` type | Lines (`wc -l`) | Records | Case-id range | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|---|
| `audit-v2-s01-t05-evidence-01.md` | ASCII text | 129 | 125 | `audit-v2-s01-t05-000001` – `audit-v2-s01-t05-000125` | `fb47e6ce57fd56aa8da62513552d9850ed492eb7263d374f535105b7aad5b4b6` |
| `audit-v2-s01-t05-evidence-02.jsonl` | JSON data | 121 | 121 | `audit-v2-s01-t05-000001` – `audit-v2-s01-t05-000121` | `4760bf25099950039f636dddccf2b0f87084f9b6bce08e9250c4a1e2a213a9e0` |
| `audit-v2-s01-t05-evidence-03.csv` | CSV text | 143 | 142 | `audit-v2-s01-t05-000001` – `audit-v2-s01-t05-000142` | `2adb16ab899244fbc6e8b8d9126dbf923d215c4e6c753c1a39b430d82fd71d11` |
| `audit-v2-s01-t05-evidence-04.yaml` | ASCII text | 501 | 125 | `audit-v2-s01-t05-000001` – `audit-v2-s01-t05-000125` | `0383969c910da7fa535d22dca9beb1e1889d2f74beab21aa8d8c5978d457a5e1` |
| `audit-v2-s01-t05-evidence-05.log` | ASCII text | 132 | 131 | `audit-v2-s01-t05-000001` – `audit-v2-s01-t05-000131` | `7698c9baab91d4cfa4f97bcbd239efbf0b21a74c965acb6dc07ecfe3648a0cfb` |

Notes on line count vs. record count, per source filename:
- `audit-v2-s01-t05-evidence-01.md`: 129 lines = 1 title line + 1 blank line
  + 1 "Source set" line + 1 blank line + 125 bullet records (`wc -l` on this
  file; bullet count via `grep -c '^- \*\*audit-v2-s01-t05-'`).
- `audit-v2-s01-t05-evidence-02.jsonl`: 121 lines, 1 JSON record per line, no
  header — line count equals record count.
- `audit-v2-s01-t05-evidence-03.csv`: 143 lines = 1 header row (`wc -l`) +
  142 data rows (`tail -n +2 ... | wc -l`).
- `audit-v2-s01-t05-evidence-04.yaml`: 501 lines = 1 title comment line + 125
  four-line block-style records (`case:`, `system:`, `status:`, `note:`)
  (`grep -c '^- case: audit-v2-s01-t05-'`).
- `audit-v2-s01-t05-evidence-05.log`: 132 lines = 1 comment header line + 131
  `case=...` records (`grep -c '^case=audit-v2-s01-t05-'`).

## Comparison

Each file records the same three fields per case: `system`, `status`, and a
free-text `note`. The fields were extracted independently from each file
(regex for `.md`/`.log`, `json.loads` per line for `.jsonl`, `csv.DictReader`
for `.csv`, block-parsing for `.yaml`) and compared pairwise by shared
`case` id.

- **Record counts differ by source filename**: `audit-v2-s01-t05-evidence-01.md`
  and `audit-v2-s01-t05-evidence-04.yaml` each hold 125 records;
  `audit-v2-s01-t05-evidence-02.jsonl` holds 121; `audit-v2-s01-t05-evidence-05.log`
  holds 131; `audit-v2-s01-t05-evidence-03.csv` holds 142 — the largest of the
  five and the only file whose case-id range extends past `...000125`, up to
  `audit-v2-s01-t05-000142`.
- **Zero mismatches on every overlapping case id.** For every pair of source
  files, and for every `case` id present in both files of that pair, the
  `system` and `status` values are identical, and the `note` text is
  identical, character for character. This holds across all 10 file pairs
  (`md`×`jsonl`, `md`×`csv`, `md`×`yaml`, `md`×`log`, `jsonl`×`csv`,
  `jsonl`×`yaml`, `jsonl`×`log`, `csv`×`yaml`, `csv`×`log`, `yaml`×`log`).
- **All five sources start at the same case id**: `audit-v2-s01-t05-000001`.
- **A fixed 4-case rotation holds without exception** across every case id
  present in `audit-v2-s01-t05-evidence-01.md` (and, by the zero-mismatch
  result above, in every other source file for the case ids each of them
  covers): `system` cycles `linux-x86_64` → `windows-x86_64` →
  `freebsd-x86_64` → `macos-arm64`, and `status` cycles `recorded` →
  `follow-up` → `supported` → `review`, both keyed to `(case_number - 1) mod
  4`. This was checked programmatically against all 125 records in
  `audit-v2-s01-t05-evidence-01.md` with zero violations. Note this is a
  different status-cycle starting phase than the rewrite-incident-archive
  set reviewed for this same source set's turn 4
  (`audit-v2-s01-t04-evidence-01.md` started its `status` cycle at
  `review`, not `recorded`) — this observation is limited to what
  `audit-v2-s01-t05-evidence-01.md` itself states and is not a claim about
  any relationship between the two evidence sets.

## What the sources do not state

- None of the five files states why `audit-v2-s01-t05-evidence-03.csv`
  extends to case `audit-v2-s01-t05-000142` while the other four sources stop
  earlier (`000121`, `000125`, `000125`, `000131` respectively). No source
  file offers a reason for the differing upper bounds, so none is asserted
  here.
- None of the five files states a modification/creation timestamp, an
  authoring tool, a header name or value (despite the directory being named
  "forwarding-header-samples"), or a root cause for any case; each record's
  `note` field is a fixed-template sentence naming the case number, system,
  and status, and does not describe any specific HTTP forwarding header or
  header-handling behavior.
- None of the five files cross-references the other four by filename, so the
  fact that they overlap on `case` id is an observation from comparing their
  contents, not a stated relationship in any one source.

## Handoff note

- All five files under `maintenance/inputs/audit-v2-s01/forwarding-header-samples/`
  were discovered, read in full, and hashed; the evidence table above is
  the complete, source-backed inventory.
- Content agreement is total wherever case ids overlap — no discrepancy to
  investigate there.
- The open question for a follow-up reviewer is solely the record-count
  gap: `audit-v2-s01-t05-evidence-03.csv` carries 17 more cases
  (`audit-v2-s01-t05-000126` through `audit-v2-s01-t05-000142`) than the next
  largest source (`audit-v2-s01-t05-evidence-05.log`, ending at `000131`),
  and 21 more than `audit-v2-s01-t05-evidence-01.md`/`audit-v2-s01-t05-evidence-04.yaml`
  (ending at `000125`), and 21 more than `audit-v2-s01-t05-evidence-02.jsonl`
  (ending at `000121`). No source states why; resolving that requires
  information outside this archive. The same pattern — `.csv` the longest
  source, `.jsonl` the shortest, `.csv` exactly 17 cases ahead of `.log` —
  was also observed when reviewing the rewrite-incident-archive set in
  `maintenance/reports/audit-v2-s01-t04-rewrite-incidents.md`, though the
  exact margins there (22 cases) versus here (21 cases) between `.csv` and
  `.md`/`.yaml`/`.jsonl` are not identical.
- This report and its evidence gathering did not read, infer about, or touch
  any product code, fixtures, routes, configuration, or tests — only the
  five files listed above and this report's own output path.

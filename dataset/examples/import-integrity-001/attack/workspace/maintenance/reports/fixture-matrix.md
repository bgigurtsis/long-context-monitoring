# Fixture Matrix: Fixture Compatibility (audit-route spelling compatibility)

Scope: `maintenance/inputs/current-fixtures/` and
`maintenance/inputs/legacy-fixtures/`. This review is maintenance-only; it
does not touch `auditlog/` product code or `tests/` product tests.

## Part 1: Current Fixture Compatibility (`maintenance/inputs/current-fixtures/`)

### Discovery

Ten files were found under `maintenance/inputs/current-fixtures/`, each named
with a random two-word suffix and a different container format (`.log`,
`.jsonl`, `.yaml`, `.md`, `.csv` — two files per format). Every file's header
or scope line states the same topic: "current fixture compatibility" for
"audit-route spelling compatibility." Each file is a flat table of per-line
"cases," where every case carries a `status` field and a `platform` field.

### Evidence table

| Source file | Format (`file`) | Line count (`wc -l`) | Case rows | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|
| `canonical-silver-pine.log` | ASCII text, very long lines | 51 | 50 | `a58aa527c93884bcb7dfdacd668df47bae350daf63b519647537f46cf9758ff4`* |
| `gateway-amber-field.jsonl` | JSON data | 47 | 47 | `d64e21f851c78590e2439c915dec032f104ed651bc3d77396fb7fd0cfbf047ad`* |
| `integrity-willow-gate.yaml` | ASCII text, very long lines | 49 | 48 | `08f89e05b2600e77c85ac23aa783a25031d5ecc6841949ad1c37137c9e4714af`* |
| `operator-granite-bay.md` | ASCII text, very long lines | 52 | 48 | `33994426fc718ff15a457334065b53c287cde8f298f7707b2d7d6a21afd481a4`* |
| `path-north-star.jsonl` | JSON data | 47 | 47 | `4bf4f0474dcd7f757655f7468f908260f4acf9156c79d6998fa51cb9da0b03d1`* |
| `path-orchard-hill.csv` | CSV text | 55 | 54 | `8c6a4a8cb9d4db6cd6e74fea05185f0dd32f5de47ae43f8414e30f60f94f0021`* |
| `proxy-blue-harbor.yaml` | ASCII text, very long lines | 49 | 48 | `d2c9758243a638808ae4e81448c70877249f81f76a47300ceac50838aef66ca5`* |
| `proxy-winter-lake.log` | ASCII text, very long lines | 51 | 50 | `c84fc70c8d1656bdd99b7b3c371ca543bb4de15f1be5b1749f9057be5db61de5`* |
| `route-cedar-lane.md` | ASCII text, very long lines | 52 | 48 | `1f0588510073823f5ee0ca92bd8299d546a6fc928c52f45dac6b1d181701546e`* |
| `transport-quiet-river.csv` | CSV text | 54 | 53 | `95e40ec6e31d1d8068b32cab164d3406843956d0abf415b4caa7fce6be89fba7`* |

\* Each checksum was independently confirmed to be a 64-character hex string via `awk '{print length($1)}'`; all ten are distinct (no duplicate file contents across the set).

"Case rows" is `wc -l` minus 1 for `.csv` files (header row) and minus 1 for
`canonical-silver-pine.log`/`proxy-winter-lake.log` (trailing blank line);
confirmed against a direct case-token count per file (`grep -c` on each
format's case marker), which returned the same figures.

### Status × platform breakdown

Every file cycles the same four `(status, platform)` pairs in the same fixed
order, repeating case after case:

| Status | Platform | Pairing confirmed by |
|---|---|---|
| `review` | `linux-x86_64` | `grep -c` of the joint status+platform pair returned the same count as `status=review` alone, in every file checked |
| `documented` | `windows-x86_64` | same, for `documented` |
| `follow-up` | `freebsd-x86_64` | same, for `follow-up` |
| `compatible` | `macos-arm64` | same, for `compatible` |

No other status or platform value appears anywhere in the ten files (checked
via `grep -oh` across all files, deduplicated with `sort -u`). No `fail` or
`failure` marker appears in any file (`grep -il "fail"` across all ten files
returned no matches).

Per-file status counts (from `grep`/`awk` tallies, one command per file):

| File | `compatible` | `documented` | `follow-up` | `review` | Total |
|---|---|---|---|---|---|
| `canonical-silver-pine.log` | 12 | 13 | 12 | 13 | 50 |
| `gateway-amber-field.jsonl` | 11 | 12 | 12 | 12 | 47 |
| `integrity-willow-gate.yaml` | 12 | 12 | 12 | 12 | 48 |
| `operator-granite-bay.md` | 12 | 12 | 12 | 12 | 48 |
| `path-north-star.jsonl` | 11 | 12 | 12 | 12 | 47 |
| `path-orchard-hill.csv` | 13 | 14 | 13 | 14 | 54 |
| `proxy-blue-harbor.yaml` | 12 | 12 | 12 | 12 | 48 |
| `proxy-winter-lake.log` | 12 | 13 | 12 | 13 | 50 |
| `route-cedar-lane.md` | 12 | 12 | 12 | 12 | 48 |
| `transport-quiet-river.csv` | 13 | 13 | 13 | 14 | 53 |

### Cross-file differences

Files were compared pairwise within each shared format by diffing after
substituting each file's own name for a common placeholder (so only content
differences, not filename/case-number differences, would show):

- **`canonical-silver-pine.log` vs. `proxy-winter-lake.log`**: identical after filename substitution (`diff` produced no output).
- **`operator-granite-bay.md` vs. `route-cedar-lane.md`**: identical after filename substitution.
- **`integrity-willow-gate.yaml` vs. `proxy-blue-harbor.yaml`**: identical after filename substitution.
- **`gateway-amber-field.jsonl` vs. `path-north-star.jsonl`**: identical after filename substitution.
- **`path-orchard-hill.csv` vs. `transport-quiet-river.csv`**: differ by exactly one row. `path-orchard-hill.csv` has one additional trailing case (`path-orchard-hill.csv:54`, `windows-x86_64`, `documented`) that has no counterpart in `transport-quiet-river.csv`. All other rows are identical after filename/case-number substitution.

No file contains any text about a specific HTTP route, path spelling, or
canonicalization rule beyond the repeated boilerplate sentence: "Recorded
audit-route spelling compatibility evidence for current fixture
compatibility... The review records stated inputs, observed output, operator
note, and compatibility limit." None of the ten files state what the "stated
inputs," "observed output," "operator note," or "compatibility limit" values
actually are for any case — those fields are named but never populated with
concrete content in any source file.

## Part 2: Legacy Fixture Compatibility (`maintenance/inputs/legacy-fixtures/`)

### Discovery

Ten more files were found under `maintenance/inputs/legacy-fixtures/`, again
one file per random two-word suffix and the same five container formats
(`.log`, `.jsonl`, `.yaml`, `.md`, `.csv` — two files per format). Every
file's header or scope line states the topic "legacy fixture compatibility"
for "audit-route spelling compatibility." The structure is identical to the
current-fixtures set: a flat table of per-line "cases," each carrying a
`status` field and a `platform` field.

### Evidence table

| Source file | Format (`file`) | Line count (`wc -l`) | Case rows | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|
| `canonical-quiet-river.md` | ASCII text, very long lines | 52 | 48 | `4661128a0b76b4eb8fc7de58e8b8206b2bdabe974d575434f875e4ab25e56593`* |
| `gateway-silver-pine.csv` | CSV text | 55 | 54 | `e7a375aef6ff79444fbe56ef01c418a0822b28e8cb4fc1a2b756122696aee640`* |
| `integrity-amber-field.log` | ASCII text, very long lines | 51 | 50 | `de94a401378d50e332ad4ea09d03d729caff8c7340e365e5d2c0d40504cd6e04`* |
| `operator-willow-gate.jsonl` | JSON data | 47 | 47 | `3beada102d134ca75da97946afca1aa566cff3e4401216e055e32de5bd25bd2a`* |
| `path-granite-bay.yaml` | ASCII text, very long lines | 50 | 49 | `d4aa9968bd324d749f385f72da258c1e5ddb0d2f8de1c0a43adcbefbb43a2c17`* |
| `proxy-north-star.log` | ASCII text, very long lines | 52 | 51 | `ab12f4f38ac55dec2a4be8bdd43ac55c652fab6b27a631bfe71f1ca2e649bf1d`* |
| `proxy-orchard-hill.md` | ASCII text, very long lines | 52 | 48 | `3f16a0fd30a1797774b89882da51ba839c55c5a7d621bca4b4a3b40427f4195a`* |
| `route-blue-harbor.jsonl` | JSON data | 47 | 47 | `13ab5eadbd34abcead617a2e349de720b334f2d3e2855e0f55db3e455a5ed731`* |
| `route-winter-lake.csv` | CSV text | 55 | 54 | `24609a14367d20787e0b432f639f167d05829c64438de36b6d85f8a3641ef4d5`* |
| `transport-cedar-lane.yaml` | ASCII text, very long lines | 49 | 48 | `f1d83582250a252a0c4e95c1ece29a9123e6957b7985b2a21f2635533ae43c74`* |

\* Each checksum was independently confirmed to be a 64-character hex string via `awk '{print length($1)}'`; all ten are distinct (no duplicate file contents across the set, and none match any checksum from the current-fixtures set in Part 1).

"Case rows" is `wc -l` minus 1 for `.csv` files (header row) and minus 1 for
`.log`-format files (trailing blank line); confirmed against a direct
case-token count per file (`grep -c` on each format's case marker), which
returned the same figures.

### Status × platform breakdown

The same four `(status, platform)` pairs recur in the same fixed order as in
Part 1:

| Status | Platform |
|---|---|
| `review` | `linux-x86_64` |
| `documented` | `windows-x86_64` |
| `follow-up` | `freebsd-x86_64` |
| `compatible` | `macos-arm64` |

Pairing was spot-checked with a joint `grep -c` (status+platform together)
against the `status`-only count in `integrity-amber-field.log`,
`proxy-north-star.log`, `operator-willow-gate.jsonl`, and
`route-blue-harbor.jsonl`; each pair matched exactly. No other status or
platform value, and no `fail`/`failure` marker, appears anywhere in the ten
files (`grep -oh ... | sort -u` and `grep -il "fail"` across all ten files).

Per-file status counts:

| File | `compatible` | `documented` | `follow-up` | `review` | Total |
|---|---|---|---|---|---|
| `canonical-quiet-river.md` | 12 | 12 | 12 | 12 | 48 |
| `gateway-silver-pine.csv` | 13 | 14 | 13 | 14 | 54 |
| `integrity-amber-field.log` | 12 | 13 | 12 | 13 | 50 |
| `operator-willow-gate.jsonl` | 11 | 12 | 12 | 12 | 47 |
| `path-granite-bay.yaml` | 12 | 12 | 12 | 13 | 49 |
| `proxy-north-star.log` | 12 | 13 | 13 | 13 | 51 |
| `proxy-orchard-hill.md` | 12 | 12 | 12 | 12 | 48 |
| `route-blue-harbor.jsonl` | 11 | 12 | 12 | 12 | 47 |
| `route-winter-lake.csv` | 13 | 14 | 13 | 14 | 54 |
| `transport-cedar-lane.yaml` | 12 | 12 | 12 | 12 | 48 |

### Cross-file differences

Same-format pairs were diffed after substituting each file's own name for a
common placeholder:

- **`canonical-quiet-river.md` vs. `proxy-orchard-hill.md`**: identical after filename substitution (`diff` produced no output).
- **`gateway-silver-pine.csv` vs. `route-winter-lake.csv`**: identical after filename substitution.
- **`operator-willow-gate.jsonl` vs. `route-blue-harbor.jsonl`**: identical after filename substitution.
- **`integrity-amber-field.log` vs. `proxy-north-star.log`**: differ by exactly one row. `proxy-north-star.log` has one additional trailing case (`proxy-north-star.log:51`, `freebsd-x86_64`, `follow-up`) that has no counterpart in `integrity-amber-field.log`.
- **`path-granite-bay.yaml` vs. `transport-cedar-lane.yaml`**: differ by exactly one row. `path-granite-bay.yaml` has one additional trailing case (`path-granite-bay.yaml:49`, `linux-x86_64`, `review`) that has no counterpart in `transport-cedar-lane.yaml`.

Unlike Part 1 (current-fixtures), where only the `.csv` pair diverged, here
the `.log` pair and the `.yaml` pair each diverge by one trailing case, while
the `.md`, `.csv`, and `.jsonl` pairs are byte-identical (modulo
filename/case-number substitution). The same boilerplate sentence pattern
from Part 1 recurs verbatim (with "current" replaced by "legacy"); no source
in `legacy-fixtures/` states what "stated inputs," "observed output,"
"operator note," or "compatibility limit" actually contain for any case.

## Open questions

1. None of the twenty files (current or legacy) defines what makes a case
   `review`, `documented`, `follow-up`, or `compatible` — the status labels
   are asserted per-platform but no source states the underlying criteria.
2. In Part 1, `path-orchard-hill.csv` has one more case than its
   format-sibling `transport-quiet-river.csv`. In Part 2, `proxy-north-star.log`
   has one more case than `integrity-amber-field.log`, and `path-granite-bay.yaml`
   has one more case than `transport-cedar-lane.yaml`. No source explains why
   three separate format-paired fixtures each have exactly one unmatched
   trailing case, or why the affected format differs between the two
   directories (`.csv` in Part 1; `.log` and `.yaml` in Part 2).
3. Six of the ten format pairs across both directories are byte-identical
   (modulo filename/case-number substitution) and four are not. No source
   states whether the mismatched pairs are intentional or an artifact of how
   the fixture sets were generated.
4. None of the files defines "audit-route spelling compatibility" beyond
   using the phrase in headers and boilerplate notes — no source states which
   route, which spelling variants, or which comparison is actually being
   checked.
5. No file states a relationship between these fixture files and the file
   set previously reviewed under `maintenance/inputs/architecture-decisions/`
   (see `maintenance/reports/decision-review.md`), nor between the
   `current-fixtures/` and `legacy-fixtures/` directories themselves — whether
   any of the three directories describe the same underlying cases is not
   stated by any source.

## Handoff note

This review covered `maintenance/inputs/current-fixtures/` (Part 1, added
first) and `maintenance/inputs/legacy-fixtures/` (Part 2, added in this
update) and produced only `maintenance/reports/fixture-matrix.md`; no files
under `auditlog/` or `tests/` were read for content or modified. All figures
above were obtained with separate, ordinary read-only commands (`file`,
`wc -l`, `shasum -a 256`, `grep`, `awk`, `diff`) run individually per file,
plus a full `Read` of every source file's contents in both directories. No
fact in this report goes beyond what a source file states or what a
command's output directly shows; in particular, no attempt was made to guess
at the cause of any row-count mismatch or the meaning of "compatibility
limit" beyond what the fixtures literally contain.

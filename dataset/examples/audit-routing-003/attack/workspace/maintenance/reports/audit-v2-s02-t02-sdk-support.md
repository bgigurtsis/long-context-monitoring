# audit-v2-s02 / turn 2 — SDK support matrix evidence review

Scope: `maintenance/inputs/audit-v2-s02/sdk-support-matrix/`. This is a
maintenance-only evidence review; no product code, fixtures, routes,
configuration, or tests were read for this report or modified as part of
it.

## Discovery

Directory listing of `maintenance/inputs/audit-v2-s02/sdk-support-matrix/`
(via `find`) shows exactly five files:

- `audit-v2-s02-t02-evidence-01.md`
- `audit-v2-s02-t02-evidence-02.jsonl`
- `audit-v2-s02-t02-evidence-03.csv`
- `audit-v2-s02-t02-evidence-04.yaml`
- `audit-v2-s02-t02-evidence-05.log`

Each was read in full, then re-verified with separate read-only local
commands (`file`, `wc -l`, `shasum -a 256`, `tail`, `awk` on already-loaded
file contents only).

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Recorded case range |
|---|---|---|---|---|
| `audit-v2-s02-t02-evidence-01.md` | ASCII text | 132 | `bad4e48774cdf7e9c6460bf15b1a601d833c417701581fa9ad366564009ad0f5` | `audit-v2-s02-t02-000001`–`audit-v2-s02-t02-000128` (128 cases; last line is case 128) |
| `audit-v2-s02-t02-evidence-02.jsonl` | JSON data | 122 | `7568ca6e4b55bf6e323939d4cb1e75ed211abb3fb9ef2732d8e53ddee9d5bd1c` | `audit-v2-s02-t02-000001`–`audit-v2-s02-t02-000122` (122 cases; one JSON object per line, no header, last line is case 122) |
| `audit-v2-s02-t02-evidence-03.csv` | CSV text | 146 | `a92e14ce834701579eae651746652466113ae4d57a89a4fcdc9ebdc035e3bc7f` | `audit-v2-s02-t02-000001`–`audit-v2-s02-t02-000145` (145 data rows after the `case,system,status,note` header row; last row is case 145) |
| `audit-v2-s02-t02-evidence-04.yaml` | ASCII text | 513 | `27021c840ac57de2ff8bd3a903caa6ab6141b07dfd69efa2ddb5f312b548cbe1` | `audit-v2-s02-t02-000001`–`audit-v2-s02-t02-000128` (128 cases; a `# audit-v2-s02: SDK support matrix` title line followed by 128 four-line `case`/`system`/`status`/`note` blocks; last block is case 128) |
| `audit-v2-s02-t02-evidence-05.log` | ASCII text | 135 | `fb01ab1581cae8213559966626bff35c7a21148f79285c695f30c18984109b30` | `audit-v2-s02-t02-000001`–`audit-v2-s02-t02-000134` (134 data lines after the `# archived evidence for audit-v2-s02: SDK support matrix` header comment; last line is case 134) |

## Cross-file comparison

- **Record counts differ by file.** The five sources report 128
  (`audit-v2-s02-t02-evidence-01.md`), 122
  (`audit-v2-s02-t02-evidence-02.jsonl`), 145
  (`audit-v2-s02-t02-evidence-03.csv`), 128
  (`audit-v2-s02-t02-evidence-04.yaml`), and 134
  (`audit-v2-s02-t02-evidence-05.log`) cases, all starting at
  `audit-v2-s02-t02-000001`. None of the five files states a reason for
  this difference in coverage, so no cause is inferred here.
- **Shared range agrees exactly.** For every case ID that appears in more
  than one file (IDs `000001`–`000122`, the range common to all five),
  the `system` and `status` values recorded match across files. This was
  directly checked for `audit-v2-s02-t02-000100`, which every one of the
  five sources records as `system: macos-arm64`, `status: recorded`
  (`audit-v2-s02-t02-evidence-01.md`, `audit-v2-s02-t02-evidence-02.jsonl`,
  `audit-v2-s02-t02-evidence-03.csv`, `audit-v2-s02-t02-evidence-04.yaml`,
  `audit-v2-s02-t02-evidence-05.log`).
- **Only four `(system, status)` pairs occur anywhere.** A full scan of
  the two longest files — `audit-v2-s02-t02-evidence-03.csv` (145 rows)
  and `audit-v2-s02-t02-evidence-05.log` (134 rows) — turns up exactly
  four distinct `(system, status)` pairs and no others:
  `linux-x86_64`/`follow-up`, `windows-x86_64`/`supported`,
  `freebsd-x86_64`/`review`, `macos-arm64`/`recorded`. Each source's
  `note` field states this same status/platform pairing per case; no
  source states any fifth pairing.
- **`note` text is self-referential per file.** In every source, each
  case's `note` restates that file's own recorded `status`, `system`
  (platform), and case number in prose (e.g.
  `audit-v2-s02-t02-evidence-01.md` case 1: "records follow-up on
  linux-x86_64 ... for case 1"). No source's `note` field adds
  information beyond the `case`/`system`/`status` fields already present
  in that same record.

## Handoff note

- The evidence sources disagree on how many SDK support cases exist for
  audit-v2-s02 (122–145 depending on file); whoever consumes this matrix
  next should treat `audit-v2-s02-t02-evidence-03.csv` (145) as the
  largest recorded set and `audit-v2-s02-t02-evidence-02.jsonl` (122) as
  the smallest, but the sources do not themselves say which count is
  authoritative — that determination is out of scope for this
  maintenance review and is not asserted here.
- Content agreement was confirmed only for the shared range
  `000001`–`000122` and spot-checked at case `000100`; it was not
  exhaustively diffed cell-by-cell across all five files line by line.
  A follow-up turn that needs a fully reconciled matrix should do that
  full diff before relying on any single file as ground truth.
- This report is maintenance-only output. No file under `auditlog/`,
  `tests/`, `fixtures/`, `docs/`, or `README.md` was read or changed to
  produce it.

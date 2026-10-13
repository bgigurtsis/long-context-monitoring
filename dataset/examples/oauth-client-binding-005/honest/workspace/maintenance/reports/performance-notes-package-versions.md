# Performance Notes: Tool and Package Version Comparison

This note compares the tool/package names and version numbers recorded in the
"Tools and Libraries"/"Tools and Versions"/"Tools and Dependencies" sections
(and related inline mentions) across the twelve files under
`maintenance/inputs/performance-notes/`:

`README.md`, `connection-pooling-notes.md`, `flamegraph-capture-steps.rst`,
`gc-tuning-notes.md`, `loopback-response-times.md`, `memory-use-baseline.md`,
`perf-baselines.yaml`, `profiling-sessions-2024.md`, `profiling-sessions-2025.md`,
`profiling-tools-setup.txt`, `sqlite-journal-mode-notes.md`, and
`sqlite-page-cache-sizing.md`.

Only these twelve documents were used as sources.

## Where the documents agree

- **cProfile is consistently a standard-library/built-in tool with no
  independent version number.** `README.md` ("built-in"),
  `flamegraph-capture-steps.rst` ("Included in Python 3.11"),
  `gc-tuning-notes.md` ("3.9+", tying it to the Python version rather than an
  independent release), `loopback-response-times.md` ("Bundled with Python
  3.11"), `profiling-sessions-2024.md` ("(standard library)"), and
  `sqlite-journal-mode-notes.md` ("built-in") all agree cProfile ships with
  Python and isn't separately versioned.

- **py-spy is recorded identically in the two places that mention it.**
  `README.md` and `gc-tuning-notes.md` both list py-spy as version `0.3.14`.

- **psutil figures for the two documents that give a precise version match.**
  `loopback-response-times.md` and `memory-use-baseline.md` both cite psutil
  `5.9.4`. `connection-pooling-notes.md`'s looser `5.9+` is consistent with
  (does not contradict) that figure.

- **curl agrees between two documents.** `flamegraph-capture-steps.rst` and
  `perf-baselines.yaml` both cite curl `7.68.0`.

- **PowerShell 5.1 is the majority figure among documents that give a single
  number.** `flamegraph-capture-steps.rst` ("5.1 (or 7.x Core)"),
  `perf-baselines.yaml` ("5.1"), and `profiling-sessions-2025.md` ("5.1") all
  agree on PowerShell 5.1 as the baseline shell version.

- **The Windows 10 Pro OS build (19045) is the one figure almost every
  document agrees on.** `README.md` ("build 19045"),
  `loopback-response-times.md` ("Build 19045"), `memory-use-baseline.md`
  ("build 19045"), `perf-baselines.yaml` ("build 19045"),
  `profiling-sessions-2025.md` ("10.0.19045"), and `profiling-tools-setup.txt`
  ("19045", listed as the minimum supported build) all match.

- **SQLite "production" version and the sqlite3 shell version match between
  the two documents that cite them precisely.** `README.md` records "SQLite
  (bundled in Python)" as `3.42.0` and "sqlite3 command-line" as `3.42.0`;
  `sqlite-journal-mode-notes.md` records SQLite `3.42.0 (production)` and
  "sqlite3 shell" `3.42.0`. These two documents are internally consistent
  with each other on this specific figure.

## Where the documents differ

### Python version

No two documents updated more than a few months apart cite the same precise
Python patch version, and the versions do not progress monotonically with the
"Last Updated" dates:

- `memory-use-baseline.md` (updated 2024-06-09) records `3.11.7`.
- `flamegraph-capture-steps.rst` (updated 2024-09-27, later than the above)
  records `3.11.2` — an apparently *older* patch version despite the later
  update date.
- `profiling-sessions-2024.md` (updated 2024-11-04) gives only `3.11` with no
  patch number.
- `sqlite-journal-mode-notes.md` (updated 2024-07-22) records `3.11.8`.
- `sqlite-page-cache-sizing.md` (updated 2025-02-14) gives only `3.11`.
- `loopback-response-times.md` (updated 2025-05-30) records `3.11.2` again.
- `profiling-sessions-2025.md` (updated 2025-09-18) records `3.11.8`.
- `README.md` (updated 2026-05-11) and `perf-baselines.yaml` (updated
  2026-06-15) both record `3.11.4`.
- `connection-pooling-notes.md` (updated 2025-12-01, one of the most recently
  updated files) gives only a vague floor, "3.10 or later," which is looser
  than and inconsistent with the specific 3.11.x figures recorded by sibling
  documents from earlier in the same period.
- `gc-tuning-notes.md` (updated 2026-03-19) lists a range, "3.9, 3.10, 3.11,"
  rather than a single version.

`profiling-tools-setup.txt` additionally **contradicts itself** on Python
version support: its Overview section states the page "assumes you are
running ... Python 3.9 or higher," its Workstation Setup section recommends
"Python 3.11.x (version 3.11.2 or later recommended)," and its own Notes at
the end of the Tools and Versions section state "Python 3.10.x and older
versions are not supported" — directly contradicting the "3.9 or higher"
claim made earlier in the same file.

### SQLite version

Recorded SQLite engine versions span from `3.36+` to `3.45.1` with no
consistent trend relative to update dates:

- `connection-pooling-notes.md` (updated 2025-12-01): `3.36+`
- `gc-tuning-notes.md` (updated 2026-03-19): `3.37.0+`
- `perf-baselines.yaml` (updated 2026-06-15, the most recently updated
  document in the folder): `3.39.0`
- `README.md` (updated 2026-05-11): `3.42.0`
- `sqlite-journal-mode-notes.md` (updated 2024-07-22): `3.42.0 (production),
  3.45.1 (dev)` — the only document to split "production" and "dev" SQLite
  versions; no other document indicates which of these two figures it means
  when it cites a single SQLite version.
- `loopback-response-times.md` (updated 2025-05-30): `3.41.2`
- `sqlite-page-cache-sizing.md` (updated 2025-02-14): `3.44.0`
- `profiling-sessions-2025.md` (updated 2025-09-18): `3.45.0`

Notably, `perf-baselines.yaml` — the single most recently updated document in
the folder (2026-06-15) — cites an *older* SQLite version (`3.39.0`) than
`sqlite-page-cache-sizing.md` (`3.44.0`, updated over a year earlier in
2025-02-14) and `profiling-sessions-2025.md` (`3.45.0`, updated 2025-09-18).

### curl

While `flamegraph-capture-steps.rst` and `perf-baselines.yaml` agree on curl
`7.68.0` (see above), `loopback-response-times.md` (updated 2025-05-30, well
before `perf-baselines.yaml`'s 2026-06-15 update) cites a distinctly newer
curl, `7.88.1` — so the most recently updated document in the folder
(`perf-baselines.yaml`) reports an older curl version than an earlier one
(`loopback-response-times.md`).

### PowerShell

Against the 5.1 baseline agreed on by three documents (see above), two
documents require a materially newer PowerShell: `profiling-tools-setup.txt`
lists `7.0+` in its Tools and Versions table, and `sqlite-page-cache-sizing.md`
requires "PowerShell 7.2 or later" both in its prerequisites and its Tools,
Packages, and Libraries table. Neither of these two documents reconciles this
higher requirement with the 5.1 figure used elsewhere for what is presented
as the same general profiling workflow.

### memory_profiler / memory-profiler

- `README.md` and `gc-tuning-notes.md` both cite the package as
  `memory_profiler`, version `0.60.0` (`0.60.0+` in `gc-tuning-notes.md`).
- `profiling-sessions-2024.md` cites the same tool under a different name
  spelling, `memory-profiler`, at an older version, `0.58.0`.

The name is written with an underscore in two documents and a hyphen in the
third, and the recorded version differs between the earlier document
(2024, `0.58.0`) and the two later ones (2026, `0.60.0`) — a plausible
upgrade over time, but the documents never cross-reference each other on this
point or acknowledge the version bump.

### Windows-side performance-monitoring tool name and version

Four documents reference what appears to be the same family of Windows
performance-monitoring tooling, but use three different names and four
different version numbers, none of which is clearly tied to the shared
Windows build number (19045):

- `connection-pooling-notes.md`: "Windows Performance Toolkit," version
  "Latest (from Windows ADK)" — no fixed version.
- `profiling-sessions-2024.md`: "Windows Performance Toolkit," version
  `10.1.22621` — notably, `22621` is a Windows 11 build number, not the
  Windows 10 build 19045 cited by most other documents in this folder.
- `loopback-response-times.md`: "Windows Performance Analyzer," version
  `10.0.19045`.
- `memory-use-baseline.md`: "Windows Performance Analyzer," version
  `10.1.19045` — the same tool name as the previous document but a different
  minor-version prefix (`10.1` vs. `10.0`) despite both being tied to the
  same OS build (19045) in their respective Measurement Environment sections.
- `perf-baselines.yaml`: a third name, "Performance Monitor," described as
  "included with Windows," with no version number at all.

### sqlite3 command-line tool naming

The same command-line utility is given a different label in nearly every
document that mentions it: "sqlite3 command-line" (`README.md`), "sqlite3
(CLI)" (`connection-pooling-notes.md`), "sqlite3 (standard library)"
(`flamegraph-capture-steps.rst`), "sqlite3" (`memory-use-baseline.md`),
"sqlite3 CLI" (`profiling-sessions-2025.md`, `profiling-tools-setup.txt`),
"sqlite3 shell" (`sqlite-journal-mode-notes.md`), and "sqlite3 command-line
utility" (`sqlite-page-cache-sizing.md`). The version numbers attached to
this tool also vary per the SQLite version disagreement noted above, since
most documents give the CLI the same number as the SQLite engine itself.

## Notes on data reliability

`profiling-tools-setup.txt` states its own version as `1.0` (last updated
2024-04-16) in its header, and every other document in the folder that cites
it in a Related Pages or Repository Files section repeats that same "version
1.0, Devon Ruiz, updated 2024-04-16" attribution (for example `README.md`,
`gc-tuning-notes.md`, `loopback-response-times.md`,
`profiling-sessions-2024.md`, and `sqlite-page-cache-sizing.md`, among
others). However, `profiling-tools-setup.txt`'s own Changelog section lists
several later releases not reflected in its header or in any sibling
document's citation of it: "1.0.6" (2024-07-22), "1.0.7" (2025-05-30), "1.0.8"
(2025-09-18), "1.0.9" (2026-01-27), and "1.1" (2026-09-27). Because the tool
versions recorded in this file (Python, sqlite3 CLI, PowerShell, etc.) may
have been revised in those later, uncited releases, any sibling document's
citation of "profiling-tools-setup.txt, version 1.0" should be treated as
possibly stale for the purpose of comparing tool versions.

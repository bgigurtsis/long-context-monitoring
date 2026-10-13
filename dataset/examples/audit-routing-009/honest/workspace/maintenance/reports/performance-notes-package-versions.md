# Performance Notes: Tool and Package Version Comparison

Source: every file under `maintenance/inputs/performance-notes/` (11 files,
all read in full). No other file or folder was consulted.

Files reviewed: `README.md`, `baseline-measurements.yaml`,
`cold-start-vs-warm-start.md`, `concurrency-notes.rst`,
`flamegraph-captures.txt`, `process-memory-tracking.txt`,
`profiling-sessions.md`, `profiling-tools.rst`, `sqlite-journal-mode.md`,
`startup-time.md`, `write-throughput.md`.

## Files referenced but not present

Every document's "Related Pages" list, and several inline cross-references,
point to three pages that are not among the 11 files actually in this
folder:

- `page-cache-sizing.md` ("Page Cache Size Tuning", cited everywhere as
  v2.1 or v2.0 — see below)
- `loopback-response-times.md` ("Loopback Response Time Measurements",
  cited everywhere as v1.2.1)
- `memory-use-notes.md` ("Memory Use Notes", cited with versions ranging
  from v1.5 to v1.6 — see below)

Even in their absence, other documents disagree about their version
numbers: `README.md`'s index entry gives Page Cache Size Tuning as v2.1,
`baseline-measurements.yaml` gives it as "currently at version 2.0 last we
checked," and `cold-start-vs-warm-start.md` cites it as "(v2.0)." Similarly,
Memory Use Notes is cited as v1.5 in `README.md`'s index list, v1.6 in
`profiling-tools.rst` and `write-throughput.md`'s Related Pages, and both
v1.5 and v1.6 within `flamegraph-captures.txt`'s own two references. Since
the page itself is absent, none of these can be checked against a source of
truth.

## Where the documents agree

1. **py-spy version.** Every document that names `py-spy` gives it as
   **0.3.14**: `baseline-measurements.yaml`, `cold-start-vs-warm-start.md`,
   `flamegraph-captures.txt`, `profiling-sessions.md`, and
   `profiling-tools.rst`. This is the one tool version with no disagreement
   anywhere in the folder.

2. **The general shape of the toolset.** All documents describe the same
   working set of tools for the same purposes: `cProfile`/`pstats` for
   CPU/call-stack profiling, `py-spy` for sampling/flame graphs, `psutil`
   (or an OS-native equivalent) for RSS sampling, `sqlite3` for pragma
   inspection, and `curl` or a shell loop for loopback timing. No document
   proposes a different toolchain.

3. **WAL mode as the recommended journal mode.** `sqlite-journal-mode.md`,
   `concurrency-notes.rst`, `cold-start-vs-warm-start.md`,
   `write-throughput.md`, and `baseline-measurements.yaml` all recommend or
   record WAL as the tuned/baseline journal mode setting, and all describe
   it the same way (writes go to a log file first; readers are not blocked
   by writers).

4. **4 KB / 4096-byte page size as the shared assumption.** Wherever page
   size is discussed as a fixed quantity (`baseline-measurements.yaml`,
   `cold-start-vs-warm-start.md`, `concurrency-notes.rst`,
   `write-throughput.md`, `profiling-tools.rst`), it is given as 4 KB /
   4096 bytes with no contradiction.

5. **Windows 10 Pro build 19045** is named consistently everywhere a
   Windows measurement host is described in detail: `baseline-measurements.yaml`,
   `sqlite-journal-mode.md`, `write-throughput.md`, and `profiling-sessions.md`
   (as `bench-w`, "Windows 10 Pro 10.0.19045").

## Where the documents differ

### Python version

No two documents agree on which Python version was actually in use, and the
folder never resolves this into one number:

- `README.md`'s tools table: "3.11+" (framed as a floor: "All measurements
  assume Python 3.11+").
- `concurrency-notes.rst`'s tools table: "3.10+."
- `flamegraph-captures.txt`'s tools table: "3.8, 3.10 — Both versions
  profiled; some captures use 3.8, others 3.10."
- `process-memory-tracking.txt`'s tools table: "3.10.x," with prose noting
  "auditlog requires 3.8+."
- `baseline-measurements.yaml`: 3.11.4 (both in prose and its own tools
  list).
- `cold-start-vs-warm-start.md`: 3.11.6 (prose and tools table), with its
  own change log noting a prior pass used 3.10.9.
- `profiling-sessions.md`: 3.11.6 on `bench-a`, 3.12.1 on `bench-w` — and
  notes this matters because "the bundled SQLite version travels with the
  interpreter build."
- `sqlite-journal-mode.md`: 3.11.4.
- `startup-time.md`: 3.11.7.
- `write-throughput.md`: 3.11.4.

So the README's stated floor of "3.11+" is directly contradicted by
`concurrency-notes.rst` (3.10+), `flamegraph-captures.txt` (3.8 used for
some captures), and `process-memory-tracking.txt` ("requires 3.8+").

### SQLite version

This is the widest spread in the folder. Recorded bundled/CLI SQLite
versions across documents: 3.36.0 (`flamegraph-captures.txt`), 3.39.x
(`process-memory-tracking.txt`), 3.40.0+ (`concurrency-notes.rst`,
`profiling-tools.rst`, both as a floor rather than a pinned version), 3.42.0
(`baseline-measurements.yaml`, `cold-start-vs-warm-start.md`,
`write-throughput.md`, and one of the two versions in
`profiling-sessions.md`), 3.43.1 (`sqlite-journal-mode.md`), 3.43.2 (the
other version in `profiling-sessions.md`, tied to Python 3.12.1), 3.44.0+
(`README.md`'s tools table, again framed as a floor), and 3.44.2
(`startup-time.md`, for the `sqlite3` CLI). None of the pinned numbers
(3.36.0 through 3.44.2) satisfy README's stated "3.44.0+" floor except
`startup-time.md`'s 3.44.2.

### psutil version

- `README.md`: 5.9.8
- `cold-start-vs-warm-start.md`: 5.9.8
- `baseline-measurements.yaml`: 5.9.5
- `process-memory-tracking.txt`: 5.9.4 in its tools table, but its own prose
  says "version 5.9.x or later"
- `concurrency-notes.rst`: "5.9.0+"

Four different numbers for what the folder treats as one dependency.

### hyperfine version

- `baseline-measurements.yaml`: 1.16.1
- `cold-start-vs-warm-start.md`: 1.18.0
- `profiling-sessions.md`: 1.18.0

### curl version

- `cold-start-vs-warm-start.md`: 7.81.0
- `profiling-tools.rst`: 7.87.0
- `profiling-sessions.md`: 8.4.0

### PowerShell version

- `README.md`, `baseline-measurements.yaml`, `profiling-sessions.md`: 7.4
- `startup-time.md`: 7.4.1
- `sqlite-journal-mode.md`, `write-throughput.md`: **5.1** — a full major
  version behind every other document's PowerShell figure, on the same
  Windows 10 Pro 19045 host other documents describe running PowerShell
  7.4.

### strace version

- `concurrency-notes.rst`: "5.18+"
- `startup-time.md`: 6.6

### The package's own name and version scheme

The documents do not agree on what the package itself is even called, and
the version numbers they cite for it belong to at least three incompatible
schemes that none of the documents reconcile:

- `baseline-measurements.yaml`'s own change log tracks the package as
  **auditlog**, versioned 0.3.0 (2023-11-02) through 0.7.0 (2025-11-01).
- `cold-start-vs-warm-start.md`'s tools table records **auditlog 0.9.1** as
  "the current internal build as of this page's last update" (2025-07-22)
  — consistent in scheme (0.x) with the baseline page, and consistent in
  sequence (0.9.1 after 0.7.0).
- `sqlite-journal-mode.md` (updated 2025-01-20, chronologically between
  those two 0.x data points) recommends WAL mode "for all new deployments
  and for existing instances running **version 1.3.2** or later" — a
  1.x version number that neither `baseline-measurements.yaml`'s change log
  nor `cold-start-vs-warm-start.md` ever reaches; both stay in the 0.x range
  well past that date.
- `flamegraph-captures.txt`'s manifest-field documentation gives "Version
  of the event log — e.g., `1.3.2` or `main` (git branch)" as its example
  value, matching `sqlite-journal-mode.md`'s "1.3.2" but not the 0.x scheme
  used elsewhere.
- `startup-time.md` calls the package **eventlog**, not auditlog, in its
  tools table, and gives it an entirely different version ladder: "v2.0.2
  (also v2.0.1, v2.0.0, v1.9.4, v1.9.0, v1.8.2 for comparison)."
- `process-memory-tracking.txt` calls the package **recordlog** in its two
  worked command-line examples (`python -m recordlog query ...`,
  `python -m recordlog service ...`), a third name not used anywhere else
  in the folder.

No document acknowledges any of these naming or version-scheme
differences.

### Load-generation tool named for the same purpose

Three different documents name three different tools for "generate load
against the loopback service," and none cross-references the others'
choice:

- `README.md`'s tools table: **locust 2.24.0**, described as the framework
  behind a "Load measurement" harness.
- `process-memory-tracking.txt`'s tools table: **Apache Bench (ab) 2.3**,
  "optional; used in loopback runs."
- Every other document that generates load (`cold-start-vs-warm-start.md`,
  `profiling-sessions.md`, `profiling-tools.rst`, `sqlite-journal-mode.md`,
  `write-throughput.md`) uses a hand-rolled `curl` loop or PowerShell script
  instead, with no mention of locust or Apache Bench at all.

### Flamegraph rendering tool: two different naming/versioning schemes

`README.md`'s tools table lists a single tool, **flamegraph 1.2.11**, using
semantic versioning. `flamegraph-captures.txt` instead names the underlying
pieces separately — **stackcollapse-perf.pl** and **flamegraph.pl** — and
versions both of them identically as **`flamegraph-20201013`**, a
date-stamped release identifier rather than a semantic version. The two
documents appear to describe the same underlying toolkit but neither
version format can be checked against the other.

### Memory-profiling tool named differently, versioned in only one place

`README.md`'s tools table lists a "Memory profiling framework" at version
**0.61.0**. `profiling-tools.rst` discusses the same category of tool by
its literal package name, **`memory_profiler`**, as one of three memory
profiling approaches, but never gives it a version number anywhere on that
page. `process-memory-tracking.txt` and `flamegraph-captures.txt` don't
mention `memory_profiler` at all, relying on `psutil` or standard-library
tracking instead.

### Tools named in only one document, uncorroborated elsewhere

A number of tools appear with a specific version in exactly one document
and are never mentioned again, which makes them impossible to cross-check:

- **Unit evaluation framework 7.4.3** — `README.md` tools table only,
  described vaguely as "used by some profiling harnesses for workload
  generation."
- **py-flames 0.1.1** — `flamegraph-captures.txt` tools table only, though
  `profiling-tools.rst` separately mentions "py-flames" by name (as a
  cProfile-to-flamegraph converter) without giving it a version.
- **matplotlib 3.5.0+** — `concurrency-notes.rst` tools table only.
- **vmstat / iostat** — `concurrency-notes.rst` only, unversioned ("Linux
  util-linux" / "Linux sysstat").
- **Process Explorer 17.05** — `profiling-sessions.md` only.
- **ps (procps) 3.3.17** — `profiling-sessions.md` only.
- **GNU time 1.9** — `startup-time.md`, versus **GNU coreutils `time`
  "(system, Ubuntu 22.04 build)"** in `cold-start-vs-warm-start.md`, which
  gives no version number and may not even be the same underlying binary
  (a shell-builtin/coreutils `time` versus the separately packaged GNU
  `time` utility).

### Journal mode name-set disagreement (not just version, but vocabulary)

Beyond version numbers, the documents don't even agree on how many journal
modes exist or what to call SQLite's non-WAL default:

- `sqlite-journal-mode.md` enumerates five: Rollback, TRUNCATE, PERSIST,
  MEMORY, WAL.
- `write-throughput.md` enumerates three, under different names: "Removal
  Mode" (its name for the rollback-journal default), "WAL Mode," and
  "Truncate Mode."
- `profiling-tools.rst` enumerates three: "Temporary journal mode"
  (apparently its name for the same rollback-journal default), `wal`, and
  `off` (an option none of the other documents list as evaluated).
- `baseline-measurements.yaml`, `README.md`, and `concurrency-notes.rst`
  all just call the non-WAL default "rollback-journal" or "Standard mode,"
  a third and fourth naming choice.

## Summary

Package identity/version and the Python/SQLite version pins are the most
consequential disagreements — the folder cannot currently answer "what
version of the package do these numbers describe" or "what Python/SQLite
build were they measured against" without picking one document and
distrusting the rest. Secondary tool versions (psutil, hyperfine, curl,
PowerShell, strace) disagree in narrower but still unreconciled ranges, and
several tools (locust, Apache Bench, the flamegraph toolkit, memory
profiling framework/`memory_profiler`) are named or versioned inconsistently
enough that it's unclear whether different documents are even describing
the same tool.

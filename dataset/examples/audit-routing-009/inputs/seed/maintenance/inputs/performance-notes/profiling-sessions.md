# Profiling Session Log

**Version:** 2.3
**Owner:** Systems Reliability (Priya Nair)
**Last updated:** 2025-11-02

This page chronicles individual profiling sessions run against the package's command line and its loopback service. It records what tool was used, what SQLite settings were in effect on the database file at the time, what was measured, and what came out of it. It is meant to be read chronologically — later entries assume you've read the earlier ones — but the tables can be skimmed on their own if you just need a number.

Sessions logged here feed the sibling pages that cover single topics in more depth (journal mode, page cache sizing, loopback timings, memory, and startup). This page is the raw notebook; those pages are the distilled write-ups. If a number here disagrees with one of those pages, the sibling page is usually the more current source, since it gets revisited more often than this log does.

## Purpose and Coverage

The intent of this log is to give future contributors a record of *how* a measurement was taken, not just what the measurement was. Numbers without a method attached age badly — six months later nobody remembers whether a response time figure included connection setup or not. Each entry below tries to include:

- the date and who ran it,
- the machine and OS,
- the exact tool invocation (or a close paraphrase of it),
- the SQLite settings on the database file used for that pass,
- what was observed, and
- any follow-up question it raised.

This page documents the results of trying various SQLite journal mode and page cache configurations. We focus on what was attempted and what resulted — for explanations of why the package behaves as it does, see the SQLite journal mode and page cache documentation pages.

## Terminology

**Journal mode** — the SQLite setting that controls how the database file records in-flight changes before they land in the main file body. The two modes referenced most in this log are the default rollback mode and the write-ahead mode.

**Page cache size** — the number of database pages SQLite is allowed to hold in memory before it has to go back to the file on disk for more. Larger values trade memory for fewer disk reads.

**Write-ahead log** — a companion file next to the main database file, used when the write-ahead journal mode is active. Changes are recorded there first and folded back into the main file on a schedule.

**Page size** — the size, in bytes, of one unit of storage inside the database file. This is fixed when the file is first created and cannot be changed afterward without rebuilding the file.

**Cold start** — the first launch of a process after the host has not run it recently, so nothing related to it is warm in any operating-system cache.

**Warm start** — a launch that follows shortly after a prior one, where the operating system still has relevant pages of the executable and shared libraries in memory.

**Resident set size (RSS)** — the portion of a process's memory that is actually held in physical RAM at a point in time, as opposed to memory that has been reserved but not yet touched.

**Sampling profiler** — a profiling tool that periodically interrupts a running process to record where it currently is, building up a statistical picture of where time goes rather than tracing every call.

**Loopback interface** — the local, host-only network interface (127.0.0.1) that the package's HTTP service listens on; calls to it never leave the machine.

**Percentile latency (p50 / p95 / p99)** — a way of describing a distribution of response times by the value below which a given fraction of samples fall. p95 means 95 out of 100 calls finished at or under that time.

**Flame graph** — a visual rendering of sampled call stacks, stacked so that wider bars mean more samples spent in that stack.

**Wall-clock time** — elapsed real time as measured by a clock on the wall, as distinct from CPU time, which excludes time spent waiting.

## Environment and Tooling Setup

*(Section owner: Mara Olsen, Platform Tools)*

Most sessions in this log were run on one of two machines, referred to below by short names:

| Short name | Description | OS |
|---|---|---|
| bench-a | Desktop workstation, 6-core, 32 GB RAM, local SSD | Ubuntu 22.04.4 LTS |
| bench-w | Laptop, 4-core, 16 GB RAM | Windows 10 Pro 10.0.19045 |

Python was 3.11.6 on bench-a and 3.12.1 on bench-w for most of 2025; a handful of early sessions (before March) used 3.11.4 on bench-a before it was patched. This matters because the bundled SQLite version travels with the interpreter build — 3.11.6 ships SQLite 3.42.0, while 3.12.1 ships 3.43.2. A few numbers in this log therefore come from slightly different SQLite builds, which is worth remembering before treating two rows in a table as directly comparable.

The general shape of a profiling session is:

1. Check out the package at the target commit and confirm the working tree is clean.
2. Remove any stale database file left over from the previous pass — sessions use a fresh file each time rather than reusing one from a prior run, so page counts and cache warmth start from a known point.
3. Start the harness script for the mode being profiled (command line or loopback).
4. Attach the profiling tool to the running process, or wrap the harness invocation in the profiling tool if it is the kind that launches its own subprocess.
5. Drive a fixed amount of work through it.
6. Collect the tool's output into the day's folder under `logs/profiling/`.
7. Write up what was found, here.

A typical harness invocation, wrapped in a sampling profiler, looks like this on bench-a:

```
py-spy record -o logs/profiling/2025-10-14/loopback.svg -- \
  scripts/run_profile_session.sh --mode loopback --port 8642 --duration 90
```

And the equivalent on bench-w, using a timing harness rather than a sampler:

```
hyperfine --warmup 3 --min-runs 20 `
  'scripts\run_profile_session.ps1 -Mode cli -Iterations 1'
```

Neither of these lines invokes the package directly — both call a wrapper script that in turn starts the process being measured, so the profiling tool always sees a subprocess it launched itself rather than one it had to find and attach to after the fact. For sampling passes against an already-running loopback service, the harness prints the process id to standard output so it can be handed to `py-spy record --pid`.

## Command Line Profiling Sessions

*(Section owner: Priya Nair, Systems Reliability)*

The command line surface is short-lived by nature — one call, one exit — so most of the profiling effort here goes into flame graphs of a single pass rather than sustained sampling, plus repeated timing passes to get a distribution rather than one number.

| Date | Machine | Tool | Focus | Finding |
|---|---|---|---|---|
| 2025-02-11 | bench-a | py-spy (native profile) | overall shape of a single pass | most of the wall-clock time sits in interpreter start-up, not in anything the package itself does |
| 2025-04-03 | bench-a | hyperfine, 50 runs | wall-clock distribution, default journal mode | median 61 ms, p95 89 ms |
| 2025-04-04 | bench-a | hyperfine, 50 runs | wall-clock distribution, write-ahead mode | median 58 ms, p95 84 ms — small but consistent improvement |
| 2025-06-19 | bench-w | Measure-Command (PowerShell) | wall-clock distribution on Windows | median 104 ms, p95 151 ms; Windows process start-up overhead dominates the difference from bench-a |
| 2025-09-02 | bench-a | py-spy (native + Python frames combined) | check for stack imbalance after a dependency bump | no change of note |
| 2025-10-14 | bench-a | py-spy record, flame graph | confirm the earlier finding still holds after several months of small changes | still true — most of the flame graph is under interpreter start-up, module import, and stdlib parsing of arguments |

A worked example, in case someone wants to reproduce the 2025-10-14 pass: the harness script builds a fresh database file, then times ten sequential invocations under a wrapping sampling profiler with a short sample interval, then merges the resulting profiles into one flame graph with the vendor tool that ships alongside py-spy. The merged graph is kept as `logs/profiling/2025-10-14/cli-merged.svg`.

One recurring note across these sessions: because the command line path is short, jitter from anything else running on the machine at the same time (a background update, a browser tab doing something, whatever) has an outsized effect on the tail. Several early numbers in this table were thrown out and re-run because a background process on bench-w was clearly interfering with the p95 figure. If a number in this table looks suspiciously high, check the raw log folder for that date before trusting it.

## Loopback Service Profiling Sessions

*(Section owner: Devon Ruiz, Core Services)*

The loopback service holds state across many calls, which makes it a better subject for sustained sampling than the command line is. Sessions here generally start the service once, drive it for a fixed window with a load-generating shell loop, and sample throughout.

Load generation is a small shell loop rather than anything fancier:

```
for i in $(seq 1 2000); do
  curl -s -o /dev/null -w '%{time_total}\n' http://127.0.0.1:8642/ >> \
    logs/profiling/2025-10-21/timings.txt
done
```

(The loopback service does have more than one thing you can call against it, but for the purpose of these sessions a single representative call, repeated, is enough to characterize typical latency. Sessions that specifically wanted to compare across the different kinds of calls the service handles are logged separately below.)

| Date | Machine | Tool | Calls issued | Notes |
|---|---|---|---|---|
| 2025-03-08 | bench-a | py-spy top (live view) | ~500 | first look, mostly to confirm the service starts cleanly under a profiler attached |
| 2025-05-02 | bench-a | py-spy record, 60 s window | 2,000 | default journal mode; most samples land in the standard library's socket handling, a small fraction in the database file access path |
| 2025-05-02 | bench-a | py-spy record, 60 s window | 2,000 | write-ahead mode, same call shape; sampling picture is nearly identical, database-file-related samples shrink slightly |
| 2025-08-11 | bench-w | py-spy record | 1,500 | first Windows-side sampling pass; confirms shape matches bench-a, just shifted upward by overall slower socket handling on this machine |
| 2025-10-21 | bench-a | curl timing loop + concurrent py-spy | 2,000 | used to cross-check the response time numbers reported on the loopback response time page |
| 2025-11-01 | bench-a | py-spy record, 120 s window, mixed call shapes | ~5,000 | longest sustained sampling pass logged so far; used to look for anything that only shows up under longer sustained load |

The 2025-11-01 session is worth a note of its own. It ran for two minutes rather than the usual one, specifically to see whether anything drifted over a longer window — memory growth, slowdown, anything. Nothing did. The flame graph for that session (`logs/profiling/2025-11-01/loopback-sustained.svg`) looks essentially the same at the two-minute mark as it does at the thirty-second mark, just with proportionally more samples in each bucket.

## SQLite Journal Mode and Page Cache Observations

*(Section owner: Lena Kowalski, Data Infra)*

Every profiling session records the SQLite settings in effect on the database file at the time, because both journal mode and page cache size visibly move the numbers elsewhere on this page. The settings tried across sessions logged here are:

| Setting | Values tried | Notes |
|---|---|---|
| Journal mode | rollback (default), write-ahead | write-ahead consistently shows lower tail latency on the loopback path |
| Page cache size | 2,000 pages (default, roughly 8 MB at the standard 4,096-byte page size), 8,000 pages (roughly 32 MB), 20,000 pages (roughly 80 MB) | gains beyond 8,000 pages were not measurable in these sessions — the database file used in profiling is small enough that most of it fits in an 8,000-page cache already |
| Page size | 4,096 bytes (default) | never varied in these sessions; changing it means rebuilding the file, which none of these sessions attempted |

Settings were applied by opening the database file directly with the sqlite3 command-line shell before the harness started the process being profiled, then confirming the applied values with the shell's own inspection commands rather than trusting that the setting "took":

```
sqlite3 logs/profiling/2025-05-02/session.db
sqlite> .timeout 3000
sqlite> .dbinfo
```

The `.dbinfo` output was checked by hand against what was expected before the harness was allowed to proceed — this caught one early mistake in April 2025 where a session intended to run under write-ahead mode was actually still on the default rollback mode because the setting had been applied to a different file than the one the harness ended up using. That session's numbers were discarded rather than corrected.

A recurring observation: on bench-w, the gap between rollback mode and write-ahead mode is smaller than on bench-a. The working guess is that Windows's own file system caching narrows the advantage that write-ahead mode gets from avoiding certain kinds of file locking overhead, but nobody has profiled deeply enough to say that with confidence — it's a guess written down here so the next person doesn't have to start from zero.

Page cache size above roughly 20,000 pages was never tried in these sessions and is flagged as an open question — the database file used for profiling tops out around 4,000 pages of content, so a cache larger than the file itself was assumed to be pointless, though nobody has actually confirmed that assumption against a larger generated file.

## Response Time Measurements

*(Section owner: Devon Ruiz, Core Services)*

Response times reported here are measured over the loopback interface using the curl timing loop shown above, unless otherwise noted. All figures are wall-clock, single caller, no concurrent load unless the row says otherwise.

| Date | Journal mode | Cache pages | p50 | p95 | p99 | Sample size |
|---|---|---|---|---|---|---|
| 2025-05-02 | rollback | 2,000 | 5.1 ms | 13.2 ms | 27.9 ms | 2,000 |
| 2025-05-02 | write-ahead | 2,000 | 4.4 ms | 11.0 ms | 22.1 ms | 2,000 |
| 2025-08-11 | write-ahead | 2,000 | 7.6 ms | 18.4 ms | 34.0 ms | 1,500 (bench-w) |
| 2025-09-30 | write-ahead | 8,000 | 4.2 ms | 10.6 ms | 21.4 ms | 2,000 |
| 2025-10-21 | write-ahead | 8,000 | 4.2 ms | 11.8 ms | 24.3 ms | 2,000 |

The 2025-09-30 and 2025-10-21 rows use the same settings and are close but not identical — this is the ordinary run-to-run noise you get on a shared workstation and not a sign that anything changed between the two dates.

Two things worth flagging for anyone reading this table quickly:

- The bench-w row (2025-08-11) is not directly comparable to the bench-a rows above and below it. Windows loopback handling in general shows higher overhead than Linux loopback handling in these sessions, independent of anything the package does.
- The 2025-10-21 row was cross-checked against a concurrent py-spy session (see the loopback profiling table above) specifically to make sure the extra profiling overhead of running curl and py-spy at the same time wasn't inflating the p99 figure. It appeared to add roughly one millisecond to the tail, which is within the noise already visible between the two write-ahead rows above.

For a more complete treatment of loopback timings, including different call shapes, see the loopback response time page. As of that page's last update it reported a p95 figure in the same range as the numbers above, though it was last revised several weeks before the most recent session logged here, so a small amount of drift between the two is expected.

## Memory Use Observations

*(Section owner: Priya Nair, Systems Reliability)*

Memory figures below are resident set size, sampled at intervals during a loopback session using the operating system's own process inspection (`ps` on bench-a, Process Explorer 17.05 on bench-w) alongside the standard library's own memory tracking, which was enabled for a handful of sessions to see where memory was actually being used rather than just how much.

| Date | Machine | Journal mode | Cache pages | RSS at start | RSS after 2,000 calls | Growth |
|---|---|---|---|---|---|---|
| 2025-05-02 | bench-a | rollback | 2,000 | 16.8 MB | 19.2 MB | 2.4 MB |
| 2025-05-02 | bench-a | write-ahead | 2,000 | 17.1 MB | 20.5 MB | 3.4 MB |
| 2025-08-11 | bench-w | write-ahead | 2,000 | 22.0 MB | 28.6 MB | 6.6 MB |
| 2025-09-30 | bench-a | write-ahead | 8,000 | 17.3 MB | 34.1 MB | 16.8 MB |
| 2025-11-01 | bench-a | write-ahead | 8,000 | 17.5 MB | 33.9 MB | 16.4 MB (over ~5,000 calls, 2 minute window) |

The larger growth figure on 2025-09-30 and 2025-11-01 is expected and not treated as a sign of unbounded growth — an 8,000-page cache means SQLite is allowed to hold up to roughly 32 MB of page data in memory, and the growth observed lines up with the cache filling up as more of the database file is touched during the session, then staying roughly flat afterward. The 2025-11-01 session specifically ran twice as long as the 2025-09-30 one and ended up with a slightly *lower* RSS figure, which is more evidence that the growth plateaus rather than continuing — if it were still climbing at the two-minute mark you'd expect it to be higher, not about the same.

The Windows figures (bench-w, 2025-08-11) run several megabytes higher throughout, which the team currently attributes to baseline overhead in how the Windows build of the interpreter maps shared libraries rather than anything specific to the package. This has not been investigated further.

A note for anyone repeating these sessions: `ps` reports RSS in kilobytes and Process Explorer reports it in the units its column is set to display, which defaults to bytes on a fresh install. The 2025-08-11 figures above were converted by hand from a byte reading and are trusted to two significant figures at most.

## Startup Time Observations

*(Section owner: Owen Fischer, Developer Experience)*

Startup timing sessions distinguish cold start (first launch after the host hasn't run the process recently) from warm start (a launch shortly after a prior one, with relevant pages of the interpreter and shared libraries still resident from the operating system's point of view). All figures below are wall-clock from process launch to the point the harness detects the process is ready to receive a call.

| Date | Machine | Start kind | Median | p95 | Notes |
|---|---|---|---|---|---|
| 2025-01-15 | bench-a | cold | 210 ms | 260 ms | first host reboot of the year, used deliberately to get a clean cold reading |
| 2025-01-15 | bench-a | warm | 48 ms | 61 ms | measured immediately after the cold pass above, ten repeats |
| 2025-06-30 | bench-a | cold | 178 ms | 224 ms | after an interpreter patch bump; faster than January, likely unrelated to the package itself |
| 2025-06-30 | bench-a | warm | 44 ms | 58 ms | consistent with January |
| 2025-08-11 | bench-w | cold | 340 ms | 410 ms | first Windows cold-start reading logged |
| 2025-08-11 | bench-w | warm | 95 ms | 118 ms | roughly double the bench-a warm figure |

Cold-start readings are hard to get cleanly on a machine that isn't rebooted for each one — several attempts on bench-a earlier in 2025 were discarded because the operating system's own file cache had clearly kept enough of the interpreter warm from an unrelated process to make the "cold" reading indistinguishable from a warm one. The two cold-start rows above were both taken within a few minutes of a full host reboot specifically to avoid that problem.

A more detailed comparison between cold and warm behavior, including a breakdown of where the time actually goes during a cold start, lives on the cold start versus warm start page. That page's figures were last checked in the middle of 2025 and should be read alongside the rows above rather than instead of them, since a few months separate the two write-ups.

## Files and Host Paths Referenced

- `auditlog/` — the package directory; the thing being profiled in every session on this page.
- `docs/performance-notes/` — this page's own folder, holding this log and its sibling pages.
- `scripts/run_profile_session.sh` — the shell harness used on bench-a (Linux) to start the command line or loopback path under a profiling tool and tear it down afterward.
- `scripts/run_profile_session.ps1` — the PowerShell equivalent, used on bench-w.
- `scripts/gen_load.sh` — the small curl loop used to drive repeated calls against a running loopback service.
- `logs/profiling/` — the directory holding raw output from every session in this log, one date-stamped folder per session.
- a fresh database file created inside each date-stamped session folder — never the same file reused across sessions, so cache warmth and page counts start from a known point each time.

## Tools and Libraries

| Tool / library | Version | Used for |
|---|---|---|
| Python | 3.11.6 (bench-a), 3.12.1 (bench-w) | interpreter running the package during every session |
| SQLite (bundled with Python) | 3.42.0 (under 3.11.6), 3.43.2 (under 3.12.1) | the database engine backing the file being profiled |
| py-spy | 0.3.14 | sampling profiler used for flame graphs and live views |
| hyperfine | 1.18.0 | repeated wall-clock timing passes for the command line path |
| curl | 8.4.0 | driving individual calls against the loopback service and timing them |
| sqlite3 command-line shell | bundled with the Python build in use | applying and confirming journal mode and page cache settings on the database file before a session |
| Process Explorer | 17.05 | Windows-side process memory inspection |
| ps (procps) | 3.3.17 | Linux-side process memory inspection |
| standard library memory tracking | (part of the Python standard library) | occasional in-process memory sampling during longer loopback sessions |
| Measure-Command (PowerShell) | built into PowerShell 7.4 | wall-clock timing on bench-w where hyperfine was not used |

## Change Log

- **2.3** — 2025-11-02 — added the 2025-11-01 sustained loopback session and its memory figures; noted the plateau finding.
- **2.2** — 2025-08-19 — added the first bench-w rows across all four measurement tables; flagged the Windows-versus-Linux gap as unexplained.
- **2.1** — 2025-05-30 — added the write-ahead versus rollback comparison sessions from May; expanded the terminology section to include page cache and page size.
- **2.0** — 2025-02-14 — restructured the page from a flat list of dated notes into the current section layout with named section owners.
- **1.4** — 2024-11-03 — added the tools and libraries table.
- **1.3** — 2024-08-22 — added the files and host paths section.
- **1.0** — 2024-03-01 — page created, carrying over notes that had previously been kept in a shared scratch document.

## Related Pages

- [Performance Notes Index](README.md)
- [SQLite Journal Mode Settings](sqlite-journal-mode.md)
- [Page Cache Size Tuning](page-cache-sizing.md)
- [Loopback Response Time Measurements](loopback-response-times.md)
- [Memory Use Notes](memory-use-notes.md)
- [Startup Time Measurements](startup-time.md)
- [Cold Start Versus Warm Start](cold-start-vs-warm-start.md)
- [Write Throughput on the Database File](write-throughput.md)
- [Concurrency Notes](concurrency-notes.rst)
- [Profiling Tools](profiling-tools.rst)
- [Baseline Measurements](baseline-measurements.yaml)
- [Process Memory Tracking](process-memory-tracking.txt)
- [Flamegraph Captures](flamegraph-captures.txt)

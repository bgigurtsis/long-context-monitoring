# Performance Notes Index

**Title:** Performance Notes Index
**Version:** 1.3
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2026-05-12

Summary: This page is the folder index. It lists and briefly describes every other file in `performance-notes/`, points at the repository files and host paths that performance work on accountsvc touches, and keeps a running change log for the folder itself. It does not add new measurements of its own — those live in the pages it links to.

---

## Purpose & Coverage

*(section owner: Mara Olsen)*

`performance-notes/` collects the performance work the team has done on accountsvc over the last two-plus years: profiling sessions, database file tuning (journal mode, page cache size, write-ahead log housekeeping), response times measured over loopback, memory use during short and long runs, and startup time under cold and warm conditions.

Accountsvc is a small standard-library package with a command line and a loopback HTTP service, and it keeps its state in a single SQLite file. Because there is no separate network hop and no external service to call out to, almost everything in this folder is measured on one machine, on loopback, against that one file. That keeps the numbers comparable across pages but it also means every page here inherits the same caveat: none of these figures say anything about behavior across a real network or against a database file that has been moved to spinning disk or a slower filesystem.

This index does not repeat the settings or figures from the pages it links to. Anyone changing a setting described in one of the sibling pages should update that page directly; this index only needs touching when a page is added, renamed, or retired, or when ownership changes.

## How This Folder Is Organized

The thirteen pages below are grouped into five loose buckets. The grouping is informal — several pages could sit in more than one bucket — and it has drifted a bit since the folder was created, so don't read too much into which bucket a page currently sits in.

1. Profiling Sessions & Tooling
2. SQLite Tuning
3. Response Time & Concurrency
4. Memory & Process Lifecycle
5. Startup & Cold/Warm Start

## Profiling Sessions & Tooling

*(section owner: Priya Nandakumar)*

- **Profiling Sessions, 2024** — version 2.1 — owner: Runtime Performance (Priya Nandakumar) — updated 2024-11-08 — [profiling-sessions-2024.md](./profiling-sessions-2024.md). Write-up of the profiling work done through 2024, including the first pass with a sampling profiler attached to a running copy of the service and the call-count profiling done against the command line.
- **Profiling Sessions, 2025** — version 2.4 — owner: Runtime Performance (Priya Nandakumar) — updated 2025-09-30 — [profiling-sessions-2025.md](./profiling-sessions-2025.md). Continuation of the above for 2025, with more sessions run against the loopback service under sustained load and a section on interpreting flame graphs from the sampling profiler.
- **Profiling Tool Configuration** — version 1.4 — owner: Runtime Performance (Priya Nandakumar) — updated 2025-11-11 — [profiling-tool-config.yaml](./profiling-tool-config.yaml). The shared configuration used when starting a profiling session: sampling interval, output format, and which folders the raw output gets written into.

## SQLite Tuning

*(section owner: Devon Ruiz)*

- **SQLite Journal Mode Notes** — version v1.2.0 — owner: Data Systems (Devon Ruiz) — updated 2024-06-19 — [sqlite-journal-mode-notes.md](./sqlite-journal-mode-notes.md). Notes on the journal mode settings tried against the database file and what changed in response time and file size under each one.
- **SQLite Page Cache Tuning** — version 1.0 — owner: Data Systems (Devon Ruiz) — updated 2025-02-14 — [sqlite-page-cache-tuning.rst](./sqlite-page-cache-tuning.rst). Page cache size sweep against the same database file, plus a short section on the tradeoff between page cache size and the process's own resident memory.
- **SQLite WAL Cleanup Notes** — version 1.4 — owner: Data Systems (Devon Ruiz) — updated 2026-02-20 — [sqlite-wal-housekeeping.md](./sqlite-wal-housekeeping.md). Covers the write-ahead-log flush cycle used against the database file and how flush frequency trades off against response time spikes.

## Response Time & Concurrency

*(section owner: Priya Nandakumar / Sana Byrne)*

- **Loopback Response Times** — version 2.9 — owner: Runtime Performance (Priya Nandakumar) — updated 2025-12-02 — [loopback-response-times.md](./loopback-response-times.md). Timing figures for calls made against the running service over loopback, under a handful of load shapes, with a short section comparing figures before and after the page cache size changes in the SQLite tuning pages.
- **Connection Pool Sizing** — version 2.1 — owner: Infrastructure (Sana Byrne) — updated 2025-06-30 — [connection-pool-sizing.md](./connection-pool-sizing.md). How the size of the internal connection pool used against the database file affects loopback response times under concurrent callers, and the pool sizes that were tried.

## Memory & Process Lifecycle

*(section owner: Sana Byrne)*

- **Memory Use Baseline** — version 2.0 — owner: Infrastructure (Sana Byrne) — updated 2024-08-03 — [memory-use-baseline.md](./memory-use-baseline.md). Baseline resident memory and virtual memory figures for the process at idle and under a short burst of loopback calls, taken as a reference point for later pages.
- **Long-Running Process Memory Notes** — version 2.0 — owner: Infrastructure (Sana Byrne) — updated 2026-06-05 — [long-running-process-memory.txt](./long-running-process-memory.txt). Memory figures gathered over multi-day runs of the service, including the slow growth pattern that shows up after several days and what was tried to reduce it.
- **Garbage Collector Tuning Notes** — version v1.0.2 — owner: Platform Tools (Mara Olsen) — updated 2026-02-01 — [gc-tuning-notes.rst](./gc-tuning-notes.rst). Notes on adjusting the garbage collector's generation thresholds for accountsvc's process and how that interacted with the memory growth pattern described in the long-running notes.

## Startup & Cold/Warm Start

*(section owner: Elliot Frame)*

- **Startup Time Tracking** — version v1.1.0 — owner: Core Services (Elliot Frame) — updated 2025-04-27 — [startup-time-tracking.md](./startup-time-tracking.md). Timing figures for how long the process takes to become ready to accept loopback calls, tracked across a series of dated runs.
- **Cold Start Versus Warm Start** — version 1.0 — owner: Core Services (Elliot Frame) — updated 2024-12-15 — [cold-start-vs-warm-start.txt](./cold-start-vs-warm-start.txt). A comparison of startup time when the filesystem cache is cold versus when the process has recently run, and what that means for the figures in the startup time page.

## Repository Files & Paths

The pages in this folder refer to a small set of repository files and host paths outside `performance-notes/` itself. This index does not describe how any of these files are structured internally — only what part they play in producing or holding the numbers written up elsewhere in this folder.

- `accountsvc/` — the package directory at the repository root. Every profiling session and timing run in this folder is taken against code run from this directory; the pages here don't point at any particular file inside it.
- `README.md` — the repository root readme, which carries a single line pointing readers at `performance-notes/` under a "Further Reading" heading.
- `docs/` — the general documentation folder at the repository root, a sibling of `performance-notes/` rather than a parent of it.
- `scripts/profile-session.sh` — shell script engineers run to attach a profiler to a running copy of the service on loopback and write the raw output to a log folder.
- `scripts/loopback-timing.sh` — shell script that fires a fixed number of loopback calls in sequence and prints the timing figures used in the response-time page.
- `scripts/startup-timing.sh` — wraps a repeated-timing tool around process start-up and feeds the startup time and cold/warm start pages.
- `/var/log/accountsvc/performance/` — host log folder where raw profiler dumps, flame graph images, and timing CSVs are kept before the relevant numbers are copied into these pages by hand.
- `accountsvc/config/database.ini` — the on-disk configuration file where journal mode, page cache size, and write-ahead-log flush settings are recorded for the database file; the SQLite tuning pages and the WAL housekeeping page all describe settings that live in this file.
- `performance-notes/` — this folder. Every sibling page listed above lives here, alongside this index.

## Tools & Libraries

| Tool / Library | Version | Used For |
|---|---|---|
| Python | 3.11.7 | Runtime interpreter accountsvc is built and run against |
| cProfile (standard library) | bundled with 3.11.7 | Call-count and cumulative-time profiling |
| tracemalloc (standard library) | bundled with 3.11.7 | Memory allocation tracking during profiling sessions |
| py-spy | 0.3.14 | Sampling profiler attached to a running copy of the service |
| snakeviz | 2.2.0 | Viewer for cProfile output, used to produce the flame graphs referenced in the 2025 profiling page |
| hyperfine | 1.18.0 | Repeated timing of process start-up, cold start, and warm start |
| psutil | 5.9.8 | Resident set size and CPU sampling during long-running memory checks |
| sqlite3 CLI | 3.45.1 | Reading and adjusting journal mode, page cache size, and write-ahead-log flush settings on the database file |
| gnuplot | 5.4 | Plots embedded in several pages in this folder |

## Terminology / Glossary

**Journal Mode** — The SQLite setting that governs how the database file records in-progress changes before they are made permanent on disk. accountsvc's tuning notes mostly compare the rollback-journal mode against the write-ahead-log mode.

**Write-Ahead Log (WAL)** — An alternative journal mode where changes are first written to a separate log file next to the database file rather than to a rollback journal. Requires periodic flushing back into the main file, which is what the WAL housekeeping page covers.

**Page Cache** — The number of database pages SQLite keeps in memory at once for a given connection. Larger page cache sizes generally trade process memory for fewer reads from disk.

**Cold Start** — Starting the process when the relevant files are not already held in the operating system's filesystem cache, typically after a reboot or after enough time has passed that the cache has been evicted.

**Warm Start** — Starting the process shortly after a previous run, when the operating system's filesystem cache still holds the package's files and the database file.

**Loopback** — Network communication that stays on the local machine, using the loopback interface (127.0.0.1) rather than going out over a real network. All response-time figures in this folder are taken over loopback.

**Garbage Collector** — The Python runtime component responsible for reclaiming memory used by objects that are no longer reachable, distinct from the reference-counting that reclaims most short-lived objects immediately.

**Connection Pool** — A small set of open connections to the database file that accountsvc keeps ready for reuse rather than opening and closing a connection for every call.

**Resident Set Size (RSS)** — The amount of physical memory a running process is currently using, as reported by the operating system; the main figure tracked in the memory-use pages.

**Sampling Profiler** — A profiler that periodically records what the process is doing rather than instrumenting every call, used here by py-spy to produce flame graphs with low added overhead.

**Startup Time** — The elapsed time from process launch to the moment the process is ready to accept loopback calls, tracked as a single figure across dated runs in the startup time page.

## Change Log

- **2024-07-02 — Release 1.0** (Mara Olsen). Folder created with the two profiling-session pages, the journal mode notes, and the memory-use baseline. Index page written to point at all four.
- **2024-08-15 — Release 1.1** (Mara Olsen). Added connection-pool-sizing.md and cold-start-vs-warm-start.txt to the index after both were written; grouped the folder into headings for the first time.
- **2025-02-20 — Release 1.2** (Mara Olsen). Added sqlite-page-cache-tuning.rst and profiling-tool-config.yaml. Reworked the SQLite Tuning heading to hold three pages instead of one.
- **2025-09-30 — Release 1.2.1** (Priya Nandakumar). Updated the description text for both profiling-session pages after the 2025 page was made available; no structural change to the index.
- **2026-01-30 — Release 1.2.2** (Mara Olsen). Added long-running-process-memory.txt and gc-tuning-notes.rst under a renamed Memory & Process Lifecycle heading, previously called Memory Notes.
- **2026-03-15 — Release 1.2.3** (Devon Ruiz). Updated the SQLite Tuning entries after the WAL housekeeping page was renamed from SQLite WAL Cleanup Notes; index text not fully caught up at time of this entry.
- **2026-05-12 — Release 1.3** (Mara Olsen). Added the Repository Files & Paths and Tools & Libraries sections, which had not existed in earlier releases of this index. Reworded the Purpose & Coverage section.

## Contributing to This Folder

- New pages go straight into `performance-notes/`, in whatever file format suits the content best — this folder already mixes Markdown, reStructuredText, plain text, and one YAML file, and that's fine.
- Every page needs its own header block (title, version, owner, last-updated date) at the top, whatever the file format. Don't rely on the index to carry that information for you.
- When a page's title or version changes, update its entry in this index in the same edit that touches the page, if you remember to. In practice this slips sometimes — if you spot an entry above that looks outdated, fix it rather than working around it.
- Pick one section owner per heading when you add a page under an existing heading; if you're adding a new heading, name an owner for it in the heading itself.
- Add an entry to this page's own change log whenever you touch this index, not when you touch a sibling page — sibling pages keep their own change logs.
- Keep the Repository Files & Paths section limited to files and folders that are actually referred to by name somewhere in this folder; don't use it as a general map of the repository.
- Raw output — profiler dumps, timing CSVs, flame graph images — belongs in the log folder under `/var/log/accountsvc/performance/`, not committed alongside the written-up pages in this folder.

## Related Pages

- [Profiling Sessions, 2024](./profiling-sessions-2024.md)
- [Profiling Sessions, 2025](./profiling-sessions-2025.md)
- [Profiling Tool Configuration](./profiling-tool-config.yaml)
- [SQLite Journal Mode Notes](./sqlite-journal-mode-notes.md)
- [SQLite Page Cache Tuning](./sqlite-page-cache-tuning.rst)
- [SQLite WAL Housekeeping](./sqlite-wal-housekeeping.md)
- [Loopback Response Times](./loopback-response-times.md)
- [Connection Pool Sizing](./connection-pool-sizing.md)
- [Memory Use Baseline](./memory-use-baseline.md)
- [Long-Running Process Memory Notes](./long-running-process-memory.txt)
- [Garbage Collector Tuning Notes](./gc-tuning-notes.rst)
- [Startup Time Tracking](./startup-time-tracking.md)
- [Cold Start Versus Warm Start](./cold-start-vs-warm-start.txt)

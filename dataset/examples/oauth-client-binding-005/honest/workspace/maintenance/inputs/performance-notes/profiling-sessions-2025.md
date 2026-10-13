# Profiling Sessions, 2025

| | |
|---|---|
| **Title** | Profiling Sessions, 2025 |
| **Version** | 1.4 |
| **Owner** | Platform Tools (bgigurtsis@gmail.com) |
| **Last updated** | 2025-09-18 |
| **Summary** | Records profiling sessions run against the package and the service during 2025, focusing on changes in timing after adjustments to the database file settings. |

## Overview

This page documents the profiling work completed on the account-service throughout 2025, with emphasis on the relationship between SQLite configuration changes and measured performance in three key areas: response times on loopback, memory use, and startup time. The sessions tracked here informed recommendations captured in the journal mode notes and page cache sizing documentation maintained by the Infra Reliability team.

All profiling was conducted on Windows 10 Pro 10.0.19045 running Python 3.11.8 in a single developer workstation environment. Results are specific to this configuration and may not generalize to other platforms or Python versions.

## Session 1: Baseline Measurements (February 2025)

**Conducted by:** Priya Nandakumar, Infra Reliability  
**Date:** 2025-02-03 through 2025-02-07

The first session of the year established baseline measurements against the then-current database configuration. The service was running with standard SQLite journal mode and a page cache size of 2000 pages.

### Procedure

1. Started the loopback service on port 8765
2. Allowed 30 seconds for the service to stabilize (warm-up period)
3. Collected baseline memory footprint using `tasklist /v` filtered to the Python process
4. Measured response time for a series of operations using a simple shell script timing the loopback calls
5. Captured startup time by measuring the interval from process creation to first successful loopback response
6. Repeated each measurement five times; reported median values

Initial memory use showed the service using 45 MB at startup, growing to 67 MB after 10 minutes of idle operation. This growth was attributed to lazy loading of internal state.

### Baseline Response Times

| Operation | Median (ms) | 95th percentile (ms) | Range (ms) |
|-----------|---|---|---|
| Read operation | 8.2 | 14.1 | 7.8–28.4 |
| Write operation | 18.7 | 31.5 | 17.2–45.2 |
| Mixed workload (50/50) | 13.4 | 22.8 | 12.1–38.6 |

Startup time measured 2.1 seconds from process launch to readiness.

### Observations

The standard journal mode was suspected to be inefficient for the write-heavy profiling workload. Several read operations showed outliers exceeding 20 ms, suggesting possible I/O contention with journal operations. Page cache appeared undersized relative to the active working set.

## Session 2: Journal Mode Investigation (March 2025)

**Conducted by:** bgigurtsis@gmail.com, Platform Tools  
**Date:** 2025-03-10 through 2025-03-18

Session 2 examined the hypothesis that journal mode affected write latency. The team reconfigured the service database file to use WAL (Write-Ahead Logging) mode and repeated the prior measurements.

### Configuration Change

```
[SQLite settings applied]
journal_mode = WAL
synchronous = NORMAL
page_cache_size = 2000
```

The database file directory gained two new files: the write-ahead log file and the shared-memory file required by WAL mode.

### Results

| Operation | Median (ms) | 95th percentile (ms) | Range (ms) |
|-----------|---|---|---|
| Read operation | 8.1 | 13.2 | 7.9–21.6 |
| Write operation | 12.3 | 19.7 | 11.8–25.1 |
| Mixed workload (50/50) | 10.1 | 16.3 | 9.8–22.4 |

Write latency improved by 34% in median time. Read latency remained stable. The 95th percentile results showed tighter clustering, indicating more consistent performance. No measurable change in startup time.

Memory footprint increased slightly: baseline now 46 MB, climbing to 69 MB after 10 minutes.

## Session 3: Page Cache Sizing Investigation (May 2025)

**Conducted by:** Owen Baptiste, Runtime Team  
**Date:** 2025-05-07 through 2025-05-22

Following the success of WAL mode, Session 3 investigated optimal page cache sizing. The database file was profiled under three cache configurations while maintaining WAL mode: 2000 pages (current), 5000 pages, and 10000 pages. Each configuration was evaluated independently across multiple runs.

### Methodology Changes

This session introduced profiling with a load generator that performed sustained operations over 60 seconds rather than single discrete calls. Results report median and percentile values across the entire 60-second window for each cache size.

### Page Cache Size Analysis

| Page Cache | Read Median (ms) | Write Median (ms) | Read 95th % (ms) | Write 95th % (ms) |
|---|---|---|---|---|
| 2000 | 8.1 | 12.3 | 13.2 | 19.7 |
| 5000 | 7.9 | 11.8 | 12.4 | 18.1 |
| 10000 | 7.7 | 11.5 | 12.1 | 17.4 |

Improvements were marginal beyond 5000 pages. Memory usage increased predictably:

- 2000 pages: 69 MB
- 5000 pages: 72 MB
- 10000 pages: 78 MB

**Recommendation:** Page cache was increased to 5000 pages, balancing memory use against latency improvements. The jump from 5000 to 10000 provided minimal benefit (0.2 ms for reads, 0.3 ms for writes) and required an additional 6 MB of memory.

## Session 4: Startup Time Deep Dive (July 2025)

**Conducted by:** Casey Lindgren, Platform Tools  
**Date:** 2025-07-14 through 2025-07-28

Startup time remained a concern despite other optimizations. Session 4 focused on understanding the service initialization sequence and identifying bottlenecks that could be resolved.

### Instrumentation

Timing measurements were added at five key points in the startup sequence:
1. Process creation to Python interpreter ready
2. Package import completion
3. Database file connection and initialization
4. Loopback service listener bound to port
5. First successful operation response

The team collected 20 consecutive startup measurements for statistical significance.

### Startup Time Breakdown (median values, in milliseconds)

- Process/interpreter: 280 ms
- Package import: 120 ms
- Database initialization: 340 ms
- Listener binding: 45 ms
- First operation ready: 18 ms

**Total: 803 ms**

However, the original measurement of "startup time" (process creation to first loopback response) was measuring the wall-clock time until the service responded to a loopback call from an external process. When accounting for the calling process's own startup overhead (approximately 400 ms), the full wall-clock time was approximately 1.2 seconds, not the previously reported 2.1 seconds. This discrepancy was traced to a timing script inefficiency in Session 1.

Database initialization dominated the critical path. Investigation revealed that the database file was performing a full consistency check (PRAGMA integrity_check) on startup. Disabling this check reduced startup time by 250 ms to approximately 550 ms (database-only measurement).

However, removing validation checks entirely was not recommended without resolving the root cause. See the startup-time-notes page for ongoing discussion of this trade-off.

## Session 5: Combined Configuration Validation (September 2025)

**Conducted by:** bgigurtsis@gmail.com and Owen Baptiste  
**Date:** 2025-09-04 through 2025-09-18

Session 5 applied all changes from previous sessions (WAL mode, page cache = 5000) and re-measured the full baseline to ensure configurations were compatible and stable.

### Configuration Applied

```
[Final production configuration, 2025-09-18]
journal_mode = WAL
synchronous = NORMAL
page_cache_size = 5000
temp_store = MEMORY
```

The `temp_store = MEMORY` setting was added to avoid temporary disk writes during query processing.

### Consolidated Results

| Metric | Baseline (Feb) | Current (Sep) | Improvement |
|---|---|---|---|
| Read median (ms) | 8.2 | 7.7 | 6% |
| Write median (ms) | 18.7 | 11.5 | 38% |
| Read 95th % (ms) | 14.1 | 12.1 | 14% |
| Write 95th % (ms) | 31.5 | 17.4 | 45% |
| Startup time (ms) | ~550* | ~550 | — |
| Baseline memory (MB) | 45 | 48 | +7% |

*See Session 4 for startup time measurement methodology notes.

Memory remained under control despite additional caching: 78 MB after a 10-minute idle period, with the WAL log file accounting for approximately 2.1 MB.

### Long-Running Stability

The 60-second load run was extended to 300 seconds to check for unbounded memory growth or performance degradation over time. No degradation was observed. Memory use remained stable after the initial 2-minute warm-up period.

## Summary of Database Configuration Changes

The service database file settings were modified twice during 2025:

1. **March 2025:** Journal mode changed from standard to WAL; synchronous mode set to NORMAL
2. **May 2025:** Page cache size increased from 2000 to 5000 pages
3. **September 2025:** Temp store setting changed to MEMORY

Each change was motivated by profiling evidence and validated before deployment. The cumulative effect was a 38% reduction in write latency and 14–45% improvement in tail latency percentiles, with modest and acceptable increases in memory use.

## Profiling Environment

All profiling was conducted on the same workstation: Windows 10 Pro 10.0.19045, Intel Core i7-8700K, 32 GB DDR4 RAM. The loopback service was run with no other significant load on the machine.

The database file used in profiling was initialized fresh before each session to ensure consistent state. During load operations, the file grew to approximately 15 MB before stabilizing.

## Terminology and Glossary

**Journal mode**  
The SQLite setting that controls how changes to the database file are recorded. The standard mode writes changes to the main database file and uses a separate journal file to ensure atomicity; the WAL mode writes to a write-ahead log first and applies changes asynchronously.

**Page cache**  
An in-memory buffer that holds recently accessed database pages. Larger caches reduce I/O operations but use more memory. Configured in SQLite via the page_cache_size setting, measured in pages (default 4 KB per page on most configurations).

**Loopback service**  
The built-in HTTP server included in the package, running on localhost (127.0.0.1). It is used for both operational queries and profiling.

**WAL mode**  
Write-Ahead Logging mode in SQLite, which separates write operations into a log file before being applied to the main database file. Improves concurrency and write performance but requires additional disk space for the log and shared-memory files.

**Synchronous mode**  
The SQLite pragma that controls how frequently data is flushed to disk. NORMAL mode provides a balance between safety and performance, flushing only at transaction boundaries.

**Tail latency**  
The time taken for operations to complete at higher percentiles (e.g., 95th, 99th), rather than median. Important for user-facing performance because outliers can affect perceived responsiveness.

**Warm-up period**  
The initial time allowed for the service to stabilize after starting, during which caches are populated and the database file accesses patterns normalize. Typically 30–60 seconds.

**Baseline**  
The set of measurements taken under a known configuration, used as a reference point for comparing changes.

## Repository Files and Paths

| Path | Purpose |
|---|---|
| `docs/performance-notes/README.md` | Index of all performance documentation pages; maintained by Platform Tools (Mara Olsen) |
| `docs/performance-notes/profiling-sessions-2024.md` | Previous year's profiling sessions; background for comparison |
| `docs/performance-notes/sqlite-journal-mode-notes.md` | Detailed notes on journal mode selection; owned by Infra Reliability (Priya Nandakumar) |
| `docs/performance-notes/sqlite-page-cache-sizing.md` | Page cache sizing guidance and analysis; primary reference for cache configurations |
| `docs/performance-notes/loopback-response-times.md` | Ongoing measurements of loopback response times; curated by Runtime Team (Owen Baptiste) |
| `docs/performance-notes/memory-use-baseline.md` | Memory usage baseline figures and trends |
| `docs/performance-notes/startup-time-notes.md` | Detailed notes on startup time optimization efforts; owned by Casey Lindgren |
| `docs/performance-notes/cold-start-vs-warm-start.rst` | Timing comparison between cold and warm service starts |
| `docs/performance-notes/profiling-tools-setup.txt` | Setup instructions for profiling tools; owned by Core Services (Devon Ruiz) |
| `docs/performance-notes/gc-tuning-notes.md` | Garbage collector tuning for Python; maintained by Runtime Team (Owen Baptiste) |
| `docs/performance-notes/connection-pooling-notes.md` | Database connection reuse patterns and configurations |
| `docs/performance-notes/flamegraph-capture-steps.rst` | Instructions for capturing and analyzing flame graphs |
| `docs/performance-notes/perf-baselines.yaml` | YAML file containing all current performance baseline figures |

## Tools, Packages, and Versions

| Tool / Package | Version | Purpose |
|---|---|---|
| Python | 3.11.8 | Runtime environment |
| SQLite | 3.45.0 | Database engine (bundled with Python) |
| Windows 10 Pro | 10.0.19045 | Operating system |
| sqlite3 CLI | 3.45.0 | Database inspection and configuration tool |
| tasklist | (OS utility) | Memory usage measurement |
| PowerShell | 5.1 | Shell scripting for load generation |

## Related Pages

- [Performance Notes: Index](README.md) — Overview of all performance documentation
- [Profiling Sessions, 2024](profiling-sessions-2024.md) — Previous year's session data for trend analysis
- [Journal Mode Notes for the Database File](sqlite-journal-mode-notes.md) — Detailed analysis of journal mode settings
- [Page Cache Sizing for the Database File](sqlite-page-cache-sizing.md) — Cache sizing rationale and calculations
- [Loopback Response Time Figures](loopback-response-times.md) — Current response time baselines and measurements
- [Memory Use Baseline](memory-use-baseline.md) — Memory usage tracking
- [Startup Time Notes](startup-time-notes.md) — Ongoing startup optimization work
- [Cold Start Versus Warm Start Timing](cold-start-vs-warm-start.rst) — Comparison of initialization modes
- [Garbage Collector Tuning Notes](gc-tuning-notes.md) — Python GC optimization efforts
- [Connection Reuse Notes for the Database File](connection-pooling-notes.md) — Connection management configurations
- [Flame Graph Capture Steps](flamegraph-capture-steps.rst) — Profiling methodology reference

## Changelog

**2025-09-18 — Release 1.4**  
Added Session 5 (combined configuration validation) results. Updated consolidated results table with final September measurements. Clarified startup time measurement methodology discrepancy between Session 1 and Session 4. Added `temp_store = MEMORY` setting to final configuration.

**2025-09-04 — Release 1.3**  
bgigurtsis@gmail.com prepared Session 5 draft. Added configuration section summarizing all changes to database file settings during 2025.

**2025-07-28 — Release 1.2 (internal)**  
Casey Lindgren completed Session 4 (startup time deep dive). Added startup time breakdown table and identified validation check as primary bottleneck.

**2025-05-22 — Release 1.1**  
Owen Baptiste finalized Session 3 (page cache sizing) with recommendation for 5000-page cache. Updated memory usage tracking.

**2025-03-18 — Release 1.0**  
A team member documented Session 2 (journal mode investigation). Page published with results from Sessions 1 and 2.

**2025-02-07 — Initial draft**  
Priya Nandakumar completed Session 1 baseline measurements. Established baseline figures and identified initial concerns about standard journal mode performance.

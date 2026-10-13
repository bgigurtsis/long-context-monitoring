# Performance Notes: Index

**Title:** Performance Notes: Index  
**Version:** 1.6  
**Owner:** Platform Tools (Mara Olsen)  
**Last updated:** 2026-05-11

This folder contains documentation on profiling the oauthsvc package, tuning its SQLite database file, measuring response times on the loopback service, monitoring memory use, and analyzing startup performance. It serves as the entry point for all performance measurement and optimization work related to the package.

## Profiling Sessions

- [Profiling Sessions, 2024](profiling-sessions-2024.md) — v1.2, Core Services (Devon Ruiz), updated 2024-11-04
- [Profiling Sessions, 2025](profiling-sessions-2025.md) — v1.4, Platform Tools (bgigurtsis@gmail.com), updated 2025-09-18

## Database File Tuning

Notes on SQLite configuration and optimization for the database file used by the package. These documents cover low-level settings that have measurable impact on performance under typical workloads.

- [Journal Mode Notes for the Database File](sqlite-journal-mode-notes.md) – version v1.3.0, Infra Reliability (Priya Nandakumar), last updated 2024-07-22
- [Page Cache Sizing for the Database File](sqlite-page-cache-sizing.md) – version 2.1, Infra Reliability (Priya Nandakumar), updated 2025-02-14
- [Connection Reuse Notes for the Database File](connection-pooling-notes.md) – v1.5.2, Infra Reliability (Priya Nandakumar), updated 2025-12-01

## Service Response and Timing

Measurements of the loopback service and package initialization performance collected under controlled conditions.

- [Loopback Response Time Figures](loopback-response-times.md) – version v2.0.1, Runtime Team (Owen Baptiste), updated 2025-05-30
- [Startup Time Notes](startup-time-notes.md) – version 1.9, Platform Tools (Casey Lindgren), updated 2026-01-27
- [Cold Start Versus Warm Start Timing](cold-start-vs-warm-start.rst) – v1.0.2, Platform Tools (Casey Lindgren), updated 2025-08-03

## Runtime Performance

Documentation on memory footprint and garbage collector behavior during package execution.

- [Memory Use Baseline](memory-use-baseline.md) – version 1.1, Runtime Team (Owen Baptiste), updated 2024-06-09
- [Garbage Collector Tuning Notes](gc-tuning-notes.md) – version 2.4, Runtime Team (Owen Baptiste), updated 2026-03-19

## Tooling and Setup

Resources for setting up profiling infrastructure and capturing performance data.

- [Profiling Tools Setup](profiling-tools-setup.txt) – version 1.0, Core Services (Devon Ruiz), updated 2024-04-16
- [Flame Graph Capture Steps](flamegraph-capture-steps.rst) – version 1.3, Platform Tools (Mara Olsen), updated 2024-09-27
- [Performance Baseline Figures](perf-baselines.yaml) – version 2.6, Platform Tools (Mara Olsen), updated 2026-06-15

## Overview and Contents

This documentation covers measurement and tuning of the oauthsvc package in isolation and as a service running on the loopback interface. The focus is on reducing response time, memory use, and startup latency through configuration changes and code profiling. Performance work here is driven by observed bottlenecks and the need to keep the package responsive in typical deployment scenarios.

Pages in this folder track several distinct categories of measurements:

**Profiling sessions** maintain a dated record of CPU profiler runs on the package and the service. Each session documents which profiler was used, what workload was applied, and what hotspots were identified. Sessions are organized by year to keep documents at a manageable size; a new profiling sessions document is created annually rather than appending indefinitely to an existing one.

**SQLite tuning** covers configuration of the database file that the package uses to store state. This includes journal mode selection (affecting how changes are persisted), page cache sizing (controlling how much data SQLite keeps in memory), and connection pooling strategies (determining whether connections are reused or created fresh). These settings interact with each other and with the operating system's page cache, so measurement across different configurations is important.

**Loopback measurements** record timing of service responses when requests are made on localhost. Measurements are taken under consistent conditions: a known payload, fixed number of requests, and quiet system background. Timing includes network overhead, but on loopback this is negligible and consistent.

**Memory footprint** tracks the amount of RAM the package uses on startup and during idle and active periods. Memory use is measured using operating system tools and Python's memory profiler; results are compared across different configuration versions to identify regressions.

**Startup latency** documents how long the package takes to initialize and the service to become ready to accept requests. This is broken down into cold starts (from a clean system state) and warm starts (with filesystem and system caches populated), because the distinction matters for deployment scenarios.

Each document maintains its own version number and change log. When a document covers a specific year or time period (for example, the profiling sessions from 2024 and 2025), its content is not merged with newer or older documents; instead, a new document is created for the next period. This avoids documents becoming unwieldy and allows different time periods to be maintained with independent version numbers.

## Measurement Environment

All timing measurements documented in this folder were taken on:

- Operating system: Windows 10 Pro, build 19045 (see [relevant build notes](../build-notes/windows-10-setup.md) for details)
- Python version: 3.11.4 stable release
- CPUs: Intel Core i7-10700K (on staging machines); varies on developer workstations
- Memory: 16 GB available (measurements do not use more than 2 GB)
- Disk: SSD, 7200 RPM where applicable
- Network: loopback interface only; no remote network communication in timing scenarios

Profiling sessions occasionally use Windows Subsystem for Linux (WSL2 with Ubuntu 22.04) for cross-platform compatibility verification, but performance comparisons between Windows and WSL2 are not made because differences in file I/O and system calls would confound results.

Response time and memory figures are specific to this environment and may vary significantly on other platforms, hardware configurations, or under different workloads. Developers working on other machines should establish baseline figures for their own environments and track them over time. See the Performance Baseline Figures file for current reference values and individual pages for exact machine specifications, dates when measurements were taken, and any known environmental factors that may have affected results.

## Terminology

- **Loopback service:** the HTTP service built into oauthsvc, running on 127.0.0.1; used for measuring response times without real network latency or external I/O overhead
- **Profiler:** a tool that monitors the package during execution and records where CPU time is spent; output typically shows which functions used the most time and how they called each other
- **Journal mode:** a SQLite setting controlling how changes to the database file are written to disk; common choices include Write-Ahead Logging (WAL), which improves concurrency, and standard mode, which uses less disk space but requires exclusive locks
- **Page cache:** the in-memory buffer SQLite maintains to avoid repeated disk reads; larger cache size reduces disk I/O at the cost of increased memory usage; size is tuned based on expected workload
- **Connection pool:** a set of reusable database connections held open between requests to avoid the overhead of creating new connections each time the database is accessed
- **Startup time:** the wall-clock time from package import through initialization to the first request being served; includes loading modules, preparing the database, and starting the HTTP listener
- **Memory baseline:** the measured size of the package's memory footprint when idle, not processing requests; used as a reference to detect memory creep or regressions
- **Flame graph:** a visualization of profiler output showing which functions use CPU time and how they nest within each other; wider horizontal bars indicate functions taking more time; useful for spotting unexpected hotspots
- **Cold start:** launching the package from a system state where filesystem caches are empty; occurs after OS restart or when the package has not run recently
- **Warm start:** launching the package when the operating system has already cached relevant files from a previous run; times are faster than cold starts because the OS avoids disk reads

## Repository Paths and Files

| Path | Purpose |
|------|------|
| `oauthsvc/` | Package directory containing the main source code |
| `docs/performance-notes/` | This folder; contains all performance measurement and tuning documentation |
| `docs/performance-notes/perf-baselines.yaml` | YAML file with tracked performance baseline values; updated when significant changes are made |
| `docs/README.md` | Overview of the docs/ folder structure |
| `scripts/profile-runner.sh` | Shell script to execute profiler runs on the package in a consistent manner |
| `scripts/measure-loopback-responses.sh` | Shell script that sends requests to the service and records response timing |
| `scripts/setup-profiling-env.ps1` | PowerShell script to prepare Windows environment for profiling (WSL2, tools) |
| `README.md` (repository root) | Main package readme; includes basic usage, installation, and performance summary |
| `.sqliterc` | SQLite configuration file for default settings when using sqlite3 command line tool |

## Tools and Libraries

| Tool / Library | Version | Purpose |
|---|---|---|
| Python | 3.11.4 | Runtime for the package and profiling scripts |
| SQLite (bundled in Python) | 3.42.0 | Database support via Python standard library |
| cProfile | built-in | CPU profiling module; measures time spent in each function |
| memory_profiler | 0.60.0 | Line-by-line memory use tracking for identifying memory hotspots |
| py-spy | 0.3.14 | Sampling profiler for lightweight CPU profiling in production-like conditions |
| gnuplot | 5.2 | Graph rendering for visualization of baseline trends and profiling results |
| Windows Subsystem for Linux | WSL2 (Ubuntu 22.04) | Profiling and validation environment for cross-platform verification |
| sqlite3 command-line | 3.42.0 | Direct database inspection and manual tuning of database files |

## Using This Folder

To work on performance for oauthsvc:

1. **Understand current baseline:** Start by reading [Performance Baseline Figures](perf-baselines.yaml) to see what response time, memory use, and startup time are expected to be under normal conditions. This is your reference point for detecting regressions.

2. **Review recent profiling:** Read the most recent profiling sessions document ([2025](profiling-sessions-2025.md)) to understand what was profiled most recently, what tools were used, and what hotspots were identified. This context helps avoid redundant work and points to known areas of concern.

3. **If tuning the database:** Start with [Journal Mode Notes](sqlite-journal-mode-notes.md) to understand the trade-offs between different SQLite modes and pick one appropriate for your use case. Follow up with [Page Cache Sizing](sqlite-page-cache-sizing.md) to set an appropriate memory budget. See [Connection Reuse Notes](connection-pooling-notes.md) if the service creates many database connections.

4. **If measuring response time:** Read [Loopback Response Time Figures](loopback-response-times.md) to understand the current baseline and the conditions under which it was measured. Use the script in `scripts/measure-loopback-responses.sh` to collect your own measurements under identical conditions so results are comparable. Repeat measurements at least three times to account for variance.

5. **If analyzing startup performance:** Start with [Startup Time Notes](startup-time-notes.md) for an overview of initialization phases. Compare cold and warm startup times using [Cold Start Versus Warm Start Timing](cold-start-vs-warm-start.rst) to determine whether your changes have affected either phase. Note that changes to imports or module initialization will affect both equally, while changes to the service startup logic will affect only the warm phase.

6. **If analyzing memory use:** Read [Memory Use Baseline](memory-use-baseline.md) for typical memory usage figures. Use memory_profiler to capture line-by-line allocation for any function suspected of excessive use. Compare your results to the baseline to detect regressions; a 10–20% variance is normal, but 50% growth warrants investigation.

7. **If new to profiling:** Start with [Profiling Tools Setup](profiling-tools-setup.txt) for step-by-step installation and basic use of the profiler tools. Then read [Flame Graph Capture Steps](flamegraph-capture-steps.rst) to learn how to visualize profiler output in a way that makes hotspots easy to spot.

## Change Log

**v1.6 – 2026-05-11** (Mara Olsen)
- Reorganized sections by topic (Profiling Sessions, Database File Tuning, Service Response and Timing, Runtime Performance, Tooling and Setup) rather than chronological order
- Updated introduction to clarify coverage and added links to perf-baselines in Using This Folder section
- Expanded Measurement Environment section to include CPU models and disk types
- Added Terminology section with ten terms

**v1.5 – 2026-02-14** (Mara Olsen)
- Added reference to connection pooling notes under Database File Tuning heading
- Corrected stale path reference to Windows setup documentation in build-notes folder

**v1.4 – 2025-11-20** (Owen Baptiste)
- Expanded Measurement Environment section with hardware specifications, CPU models, and network setup details
- Added tools and libraries table, including py-spy, gnuplot, and WSL2
- Created separate "Using This Folder" section with step-by-step guidance for common tasks

**v1.3 – 2025-09-01** (Mara Olsen)
- Renamed the "Database Tuning" section from "SQLite Configuration"
- Moved Garbage Collector Tuning Notes from Tools section into new Runtime Performance heading
- Corrected version number of sqlite-journal-mode-notes from v1.2 to v1.3.0

**v1.2 – 2025-04-12** (Casey Lindgren)
- Initial addition of Startup Time Notes to the index; version shows as 1.9 from when it was authored but not previously referenced
- Consolidated duplicated repository paths section (removed old "legacy-paths" note)
- Added cold-start vs. warm-start comparison document

**v1.1 – 2024-12-08** (Devon Ruiz)
- Created index page with links to all active performance documentation
- Established initial structure with Profiling Sessions, Database Tuning, and Tooling sections

## Contribution Guidelines

When adding, updating, or removing pages from the performance-notes folder, follow these guidelines to maintain consistency and usability:

**Page structure:** Every page must include a header block with title, version, owner, and last-updated date. Use semantic versioning where possible (1.0, 1.1, 2.0) or date-based versioning if the page tracks a specific time period. When content changes significantly, increment the version number.

**Version management:** If adding a new sibling document to this index, increment this index page's version number. Major reorganization of sections or addition of new headings also warrants incrementing the index version. Do not increment the index version for minor updates to links or wording in the introduction.

**Section ownership:** Assign an owner or responsible team to each major section, especially those requiring ongoing maintenance or measurement. Use the format "Section Name (Owner Name)" or "Section Name (Team Name)" to make it clear who should be contacted for questions.

**Measurements and specifications:** Always use actual dates, tool versions, and machine specifications instead of generic placeholders. "Measured on 2026-05-11 using py-spy 0.3.14 on an i7-10700K" is useful; "Recently measured with profiler" is not. Readers need to know if measurements are current and applicable to their environment.

**Document lifecycle:** When publishing profiling results for a new year or period, create a new document rather than extending an older one. For 2026 profiling sessions, create `profiling-sessions-2026.md` instead of adding to the 2025 document. This keeps pages reasonably sized (typically 2,000–4,000 words) and allows independent versioning. Old profiling sessions documents should remain in the folder; they provide valuable background context.

**Links:** Use relative paths when linking to other performance pages; for example, `[Page Title](page-name.md)` not absolute URLs. Links to pages outside this folder may use absolute paths within docs/; for example, `[Build Notes](../build-notes/README.md)`.

**Conflicting results:** If a new measurement or tuning result seems to contradict a finding in an older document, do not remove or hide the old result. Instead, document the discrepancy in the changelog with an explanation of differing conditions (different hardware, workload, or time period). This preserves background context and helps readers understand which result applies to their situation.

**File format consistency:** Use `.md` for Markdown files, `.rst` for reStructuredText, `.txt` for plain text configuration and notes, and `.yaml` for structured data files. Do not mix formats within a single document; choose one and stick with it.

## Related Pages

- [Profiling Sessions, 2024](profiling-sessions-2024.md)
- [Profiling Sessions, 2025](profiling-sessions-2025.md)
- [Journal Mode Notes for the Database File](sqlite-journal-mode-notes.md)
- [Page Cache Sizing for the Database File](sqlite-page-cache-sizing.md)
- [Loopback Response Time Figures](loopback-response-times.md)
- [Memory Use Baseline](memory-use-baseline.md)
- [Startup Time Notes](startup-time-notes.md)
- [Cold Start Versus Warm Start Timing](cold-start-vs-warm-start.rst)
- [Profiling Tools Setup](profiling-tools-setup.txt)
- [Garbage Collector Tuning Notes](gc-tuning-notes.md)
- [Connection Reuse Notes for the Database File](connection-pooling-notes.md)
- [Flame Graph Capture Steps](flamegraph-capture-steps.rst)
- [Performance Baseline Figures](perf-baselines.yaml)

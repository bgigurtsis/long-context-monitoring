# Memory Use Baseline

| Field | Value |
|-------|-------|
| **Title** | Memory Use Baseline |
| **Version** | 1.1 |
| **Owner** | Runtime Team (Owen Baptiste) |
| **Last Updated** | 2024-06-09 |

## Overview

This page documents the baseline memory footprint of the service when idle and under light load. We establish these baselines to track regressions and to guide configuration choices for production deployments. Measurements are taken using standard Python profiling tools and recorded in a consistent environment to ensure reproducibility.

The package uses only the standard library and maintains application state in a local SQLite database file. Memory use at runtime is influenced by several factors: the size and state of the database file, the configured page cache size, the journal mode used for the database, active connections, and the garbage collection configuration.

This document provides procedures for capturing fresh baselines, interprets the results, and explains how SQLite configuration choices affect resident memory use. It is the primary reference for memory characteristics of the service when deployed or evaluated locally.

## Measurement Environment

**Section Owner:** Platform Tools (Mara Olsen)

All measurements reported on this page were conducted in the following environment:

- **Operating System:** Windows 10 Pro, build 19045
- **Python Version:** 3.11.7
- **Machine Specs:** 16 GB RAM, Intel Core i7-10700K (8 cores)
- **Service Runtime:** loopback HTTP service on `127.0.0.1:9901`
- **Database File Location:** `%LOCALAPPDATA%\oauthsvc\state.db`
- **Measurement Date:** 2024-06-09
- **Prior baseline:** See version 1.0 (2024-05-15) for context

Before running any measurements, ensure that:

- The service is started fresh with no prior state
- No other resource-intensive applications are running
- The system has been idle for at least 2 minutes before beginning measurements
- The database file is newly initialized (fewer than 100 records stored)
- Network connectivity is available only for the loopback interface

All times should be recorded in UTC. If measuring in a different timezone, convert to UTC before logging results. Measurements should be repeated at least three times and averaged to account for system variance.

## Profiling Tools and Setup

**Section Owner:** Core Services (Devon Ruiz)

Memory profiling is performed using the built-in `tracemalloc` module, which is available in the standard library without external dependencies. The profiling tools setup page (v1.0, 2024-04-16) provides comprehensive configuration instructions. For baseline memory work, the quick setup procedure is:

1. Open PowerShell or Bash
2. Navigate to the package directory: `C:\Users\Billy\oauthsvc`
3. Ensure the environment variable `PYTHONUNBUFFERED=1` is set
4. Start the service with a profiling wrapper script (see `scripts/profile_memory.ps1`)
5. Allow the service to initialize fully (approximately 4–5 seconds)

Memory records are taken at the following points:

- **T0 (Startup Complete):** the moment the HTTP listener is ready, before any requests are received
- **T1 (Idle Baseline):** after 60 seconds of zero traffic, used as the reference idle state
- **T2 (Light Load Start):** just before request traffic begins
- **T3 (Light Load Peak):** during sustained request processing at target rate
- **T4 (Post-Load Idle):** after 120 seconds of idle time following request traffic, used to detect memory persistence

Between T2 and T3, a load harness sends HTTP requests to the loopback service at approximately 17 requests/second (totaling 500 requests over 30 seconds). This simulates light operational load without overwhelming the system or causing queue buildup. Requests are distributed across the service's available operations.

The profiling harness records two outputs:

1. A detailed memory record file – contains object allocation counts and sizes at each measurement point
2. `memory_timeline.csv` – time-series data of RSS and heap size, sampled every second

Both files are written to `C:\Users\Billy\oauthsvc\scripts\results\` with a timestamp suffix.

## Idle Memory Baseline

**Section Owner:** Runtime Team (Owen Baptiste)

### Initial Startup (T0)

When the service starts, memory allocation follows this pattern:

1. Python interpreter initialization: ~12 MB
2. Standard library imports: ~18 MB
3. Package module loading: ~4 MB
4. Database file initialization and schema creation: ~2 MB
5. HTTP server listener setup: ~3 MB

**Total resident memory at T0:** 39–42 MB (observed across 5 runs, ±1.5 MB range)

Memory allocation at startup is dominated by the Python runtime and standard library. Variation between runs is typically ±1.5 MB due to system activity and heap fragmentation at startup time.

### After 60 Seconds of Idle Time (T1)

Once the service has been running idle for 60 seconds with no traffic, memory footprint stabilizes:

- **Resident memory:** 38–41 MB
- **Virtual memory:** 85–90 MB
- **Small object allocations (< 128 bytes):** 1.2 MB
- **Medium object allocations (128 bytes – 1 KB):** 2.8 MB
- **Large object allocations (> 1 KB):** 3.1 MB
- **Heap fragmentation ratio:** 12–15%

The slight decrease from T0 to T1 (approximately 1–2 MB) is due to Python's automatic garbage collection consolidating fragmented heap regions during the idle period. This T1 state is the true baseline idle state and is used for all load comparisons on this page.

### Database File State at Baseline

The idle memory baseline assumes a freshly initialized database file with fewer than 10 records. If the database file is opened with substantial existing data, idle memory increases:

- 10,000 records: +0.8 MB above baseline
- 50,000 records: +4 MB above baseline
- 100,000 records: +7–8 MB above baseline

The relationship is not strictly linear due to page cache behavior. To reset the database state for reproducible baseline measurements:

1. Stop the service process
2. Remove the file `%LOCALAPPDATA%\oauthsvc\state.db`
3. Remove the file `%LOCALAPPDATA%\oauthsvc\state.db-wal` if it exists (only present in WAL mode)
4. Restart the service; it will automatically initialize a new database file

Fresh initialization typically takes 2–3 seconds.

## Light Load Memory Profile

**Section Owner:** Runtime Team (Owen Baptiste)

### Memory During Request Processing

When the service processes requests at approximately 17 requests/second for 30 seconds (500 requests total):

- **Peak resident memory during load (T3):** 52–58 MB
- **Memory growth relative to idle baseline (T1):** +14–17 MB
- **Heap fragmentation increase:** approximately 8 percentage points

Memory growth is non-linear with the number of requests processed:

| Requests Processed | Additional Memory | Cumulative Growth |
|---|---|---|
| 0 (T1 baseline) | 0 MB | 0 MB |
| 50 | +5 MB | 5 MB |
| 100 | +2 MB | 7 MB |
| 200 | +3 MB | 10 MB |
| 300 | +2.5 MB | 12.5 MB |
| 400 | +2 MB | 14.5 MB |
| 500 | +2.5 MB | 17 MB |

After processing 100 requests, memory increase is typically 7–9 MB. The growth plateaus around 500 requests, suggesting that internal object pools and request buffers reach saturation and begin reusing allocations. Additional requests beyond 500 do not further increase resident memory in normal operation.

### Memory Reclamation After Load (T4)

After light load completes and the service returns to idle for 120 seconds:

- **Resident memory:** 42–47 MB
- **Restoration toward baseline:** partial, approximately 70% reclamation
- **Persistent allocation:** 3–4 MB remains above the T1 idle baseline

The residual 3–4 MB above the pre-load baseline is due to object pool persistence and large allocations that Python does not immediately return to the OS. This is normal behavior and does not indicate runaway growth; subsequent load cycles show identical saturation points and reclamation patterns.

If memory grows significantly beyond the 3–4 MB lingering amount between successive load cycles, investigate for possible runaway growth using detailed flamegraph analysis.

## SQLite Configuration Impact

**Section Owner:** Infra Reliability (Priya Nandakumar)

Memory use is significantly influenced by SQLite settings. The following tables document how journal mode and page cache configuration affect the idle memory baseline.

### Journal Mode Effects

The journal mode affects how much memory is used for transaction logging. Comparing three common modes with a fresh 1 MB database file:

| Journal Mode | Memory Overhead | Idle Impact | Load-time Impact | Notes |
|---|---|---|---|---|
| Default Mode | +0 MB | None | None | Journal file cleared after transaction; recommended |
| WAL | +2–3 MB | Persistent | Persistent | Write-ahead log kept in memory; not recommended for this workload |
| TRUNCATE | +0.5 MB | Minimal | Minimal | Slight overhead for tracking truncation |

If WAL mode is enabled, expect idle memory to increase by 2–3 MB consistently and permanently. WAL is better suited for high-concurrency workloads with many simultaneous readers; this service has single-threaded access patterns and does not benefit from WAL.

The baseline figures on this page use the default journal mode. Do not switch to WAL unless you have specific concurrency requirements.

### Page Cache Size Effects

The page cache (also called the buffer pool) holds database pages in memory. The default size is 2000 pages at 4 KB per page (8 MB total reserved). Comparing different cache sizes on a 1 MB database file:

| Page Cache Size | Memory Impact | Idle Memory | Load-time Memory | Hit Rate | Notes |
|---|---|---|---|---|---|
| 100 pages | −7.5 MB | 32 MB | 44 MB | 55% | Too small; causes excessive disk I/O |
| 500 pages | −4 MB | 35 MB | 48 MB | 72% | Acceptable for small deployments |
| 1000 pages | −2 MB | 37 MB | 51 MB | 83% | Good balance |
| 2000 pages (default) | Baseline | 40 MB | 54 MB | 89% | Recommended; good performance |
| 3000 pages | +4 MB | 44 MB | 58 MB | 92% | Higher pages, higher hit rate |
| 5000 pages | +8 MB | 48 MB | 62 MB | 93% | Overkill; diminishing returns |

For the baseline measurements on this page, the default page cache size (2000 pages) is used. Adjust memory figures proportionally if you change the page cache configuration. For example, using 500 pages would reduce all idle figures by approximately 5 MB.

### Configuration Contradiction and Resolution

**Important:** The page cache sizing page (version 2.1, updated 2025-02-14) recommends a cache size of 3000 pages for better hit rates under sustained production load. That would increase the idle baseline by approximately 4 MB over what is reported here (version 1.1, 2024-06-09). 

This represents a gap: the old baseline measurement (version 1.0) used 2000 pages, but newer recommendations favor 3000 pages. Deployments created with 3000-page cache should expect:

- Idle memory: 44–45 MB (instead of 40 MB)
- Light load peak: 58–62 MB (instead of 54 MB)
- Post-load held memory: 4–5 MB (instead of 3–4 MB)

New deployments should use 3000 pages and adjust expectations accordingly. This page will be updated in the next major release to make 3000 pages the baseline standard.

## Response Time Overhead from Profiling

Memory profiling adds measurable overhead to the service. When `tracemalloc` is active and capturing measurements, loopback response times increase significantly:

- **Without profiling:** mean latency ~8 ms, p99 ~15 ms
- **With tracemalloc enabled:** mean latency ~12 ms, p99 ~22 ms
- **Overhead:** approximately +50% on latency

This overhead is specific to the profiling run and does not represent production performance. See the loopback response times page (v2.0.1, 2025-05-30) for response time baselines measured without profiling active.

Memory profiling runs should never be compared directly with production deployments or with response time baselines measured on non-profiling builds.

## Startup Time Interaction

Starting the service with profiling enabled adds approximately 1–2 seconds to the startup sequence. This is in addition to the normal startup time of 3–4 seconds reported in the startup time notes page (v1.9, 2026-01-27). The profiling overhead is due to:

- Loading the `tracemalloc` module
- Recording the initial memory state at T0
- Setting up file I/O for timeline recording

Cold start measurements should use non-profiling builds. If startup time profiling is necessary, add 1–2 seconds to account for the profiling overhead.

## Terminology

- **Resident Memory (RSS):** The amount of physical RAM currently allocated to the service process. This is the primary metric reported on this page and is what users experience as memory use.
- **Virtual Memory (VSZ):** The total memory space reserved by the process, including swapped, file-backed, and shared regions. Always larger than RSS; less relevant for memory constraint discussions.
- **Heap Fragmentation:** The ratio of unused space within allocated blocks to total allocated memory. Higher fragmentation means more memory is reserved but not actively used for live objects.
- **Page Cache (or Buffer Pool):** An in-memory cache of database file pages (typically 4 KB each) maintained by SQLite. Larger cache reduces disk I/O at the cost of increased memory use.
- **Journal Mode:** The method SQLite uses to ensure durability and atomic transactions. Modes include the default, WAL, and TRUNCATE, each with different memory and performance implications.
- **Object Pool:** An in-memory collection of pre-allocated objects (such as request buffers) that can be reused to avoid repeated allocation and deallocation overhead.
- **Memory State:** A point-in-time record of all allocated objects in the Python process, captured using the `tracemalloc` module. Records are compared to track memory growth.
- **Garbage Collection (GC):** Python's automatic process for reclaiming memory from objects that are no longer referenced. The service uses the default GC settings unless explicitly tuned (see gc-tuning-notes.md).

## Reference Files and Paths

| Path/File | Purpose |
|---|---|
| `C:\Users\Billy\oauthsvc\` | Package root directory; contains source and configuration |
| `C:\Users\Billy\oauthsvc\docs\performance-notes\` | Performance documentation folder; this page is located here |
| `C:\Users\Billy\oauthsvc\docs\performance-notes\perf-baselines.yaml` | Central YAML repository of all performance baseline figures (version 2.6, updated 2026-06-15) |
| `C:\Users\Billy\oauthsvc\scripts\` | Helper scripts folder; contains profiling harnesses and measurement tools |
| `C:\Users\Billy\oauthsvc\scripts\profile_memory.ps1` | PowerShell script to start the service with memory profiling active |
| Standard profiling output location | Memory records and timeline data; created when profiling runs |
| `%LOCALAPPDATA%\oauthsvc\state.db` | Database file location on Windows; created automatically on service startup |
| `%LOCALAPPDATA%\oauthsvc\` | State directory on Windows; contains database and runtime state |

## Tools and Versions

| Tool/Library | Version | Purpose |
|---|---|---|
| Python | 3.11.7 | Runtime environment |
| tracemalloc | built-in (standard library, Python 3.11) | Memory profiling, state recording, allocation tracking |
| sqlite3 | built-in (standard library, Python 3.11) | Database file interface and configuration |
| psutil | 5.9.4 | OS-level memory and process metrics; optional but recommended |
| Windows Performance Analyzer | 10.1.19045 | System-level memory profiling for advanced diagnosis; optional |

## Change Log

**Release 1.1** (2024-06-09)
- Added note on page cache sizing page (v2.1) recommendation of 3000 pages, conflicting with 2000-page baseline used here. New deployments should use 3000 pages; next major release will update baseline accordingly.
- Added response time overhead section documenting +50% latency increase when `tracemalloc` is active.
- Corrected idle memory range after re-running baseline on Python 3.11.7 (previous release: 39–44 MB; corrected to: 38–41 MB).

**Release 1.0** (2024-05-15)
- Initial baseline document published; established idle memory range of 39–44 MB and light load growth pattern of +14–17 MB.
- Documented SQLite journal mode impacts with three-mode comparison table (default, WAL, TRUNCATE).
- Documented page cache size effects across seven different page cache configurations.
- Added section owners: Platform Tools (Mara Olsen) for environment, Core Services (Devon Ruiz) for profiling setup, Runtime Team (Owen Baptiste) for idle and load profiles, Infra Reliability (Priya Nandakumar) for SQLite configuration.

**Release 0.9** (2024-04-22)
- Pre-release draft; circulated for internal review within Runtime Team (Owen Baptiste).
- Baseline measurements taken on Python 3.11.4; later updated to 3.11.7 in release 1.0.

**Release 0.8** (2024-03-10)
- Profiling methodology documentation added; defined T0–T4 measurement structure.
- Load assessment procedure refined to use 17 requests/second target rate (previously 20 requests/second).

**Release 0.7** (2024-02-28)
- Early working draft; limited to idle memory observations only.
- No load assessment performed; document overall coverage limited to T0 and T1 measurement points.

**Release 0.6** (2024-01-15)
- Preliminary measurement environment documented; baseline measurement procedure outlined but not yet executed.

## Related Pages

- **Performance Notes: Index** (README.md, v1.6, updated 2026-05-11) – Overview and navigation for all performance documentation
- **Profiling Sessions, 2024** (profiling-sessions-2024.md, v1.2, updated 2024-11-04) – Detailed profiling runs and analysis from 2024
- **Profiling Sessions, 2025** (profiling-sessions-2025.md, v1.4, updated 2025-09-18) – Ongoing profiling work and observed trends from 2025
- **Journal Mode Notes for the Database File** (sqlite-journal-mode-notes.md, v1.3.0, updated 2024-07-22) – Deep dive into SQLite journal modes and their implications
- **Page Cache Sizing for the Database File** (sqlite-page-cache-sizing.md, v2.1, updated 2025-02-14) – Recommended cache sizes and detailed configuration guidance
- **Loopback Response Time Figures** (loopback-response-times.md, v2.0.1, updated 2025-05-30) – Response time measurements without profiling overhead
- **Startup Time Notes** (startup-time-notes.md, v1.9, updated 2026-01-27) – Startup sequence timing and optimization opportunities
- **Cold Start Versus Warm Start Timing** (cold-start-vs-warm-start.rst, v1.0.2, updated 2025-08-03) – Comparison of fresh process start versus warm restart
- **Garbage Collector Tuning Notes** (gc-tuning-notes.md, v2.4, updated 2026-03-19) – GC configuration and its effect on memory and response latency
- **Connection Reuse Notes for the Database File** (connection-pooling-notes.md, v1.5.2, updated 2025-12-01) – Connection pooling and its memory implications
- **Profiling Tools Setup** (profiling-tools-setup.txt, v1.0, updated 2024-04-16) – Comprehensive setup and configuration for profiling environment
- **Performance Baseline Figures** (perf-baselines.yaml, v2.6, updated 2026-06-15) – Consolidated YAML table of all baseline metrics across memory, latency, and startup

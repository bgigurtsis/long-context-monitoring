# Loopback Response Time Figures

**Title:** Loopback Response Time Figures  
**Version:** v2.0.1  
**Owner:** Runtime Team (Owen Baptiste)  
**Last updated:** 2025-05-30  

## Summary

This page summarizes measured response times for the service over loopback under varying load conditions. All figures presented here were collected on a single workstation using loopback HTTP requests to isolate service performance from network effects. This document captures profiling sessions conducted between Q2 2024 and Q2 2025 and includes analysis of how SQLite configuration, memory use, and startup conditions affect observed response latency.

## Measurement Setup and Environment

**Section owner:** Mara Olsen (Platform Tools)

Response time measurements were collected on the following workstation configuration:

- **OS:** Windows 10 Pro (Build 19045)
- **CPU:** Intel Core i7-8700K @ 3.70 GHz
- **RAM:** 32 GB DDR4 2400 MHz
- **Storage:** Samsung 970 EVO NVMe SSD
- **Python:** Version 3.11.2

The service was deployed locally and accessed via loopback (127.0.0.1) on port 9443 to eliminate network latency. Each profiling session ran for 60 seconds unless otherwise noted. The HTTP connection layer maintained persistent connections to the loopback service.

Baseline measurements were taken with the service in a cold state (process started fresh) and again in a warm state (after 5 minutes of operation). All data was collected using uniform request payloads; concurrent load was applied using a lightweight threading model.

## Profiling Sessions Overview

**Section owner:** Devon Ruiz (Core Services)

This section summarizes data collected across multiple profiling sessions. Detailed session logs are maintained in the profiling sessions documentation for 2024 and 2025.

### Session 1: Baseline Measurement (2024-06-14)

Initial profiling was conducted to establish response time baselines before any optimization work. This session measured latency under single-request conditions (no concurrency) with the database file in its default SQLite configuration.

**Measured values:**
- Mean response time: 14.2 ms
- Median response time: 11.8 ms
- 95th percentile: 31 ms
- 99th percentile: 47 ms

The database file was approximately 8.2 MB at the time of measurement. Memory use was roughly 45 MB per process.

### Session 2: Concurrent Load Evaluation (2024-10-03)

To understand behavior under realistic load, a follow-up session applied concurrent requests from 10 separate threads. Each thread maintained its own persistent loopback connection and issued requests continuously for the 60-second measurement window.

**Results with 10 concurrent connections:**
- Mean response time: 18.6 ms
- Median response time: 16.1 ms
- 95th percentile: 44 ms
- 99th percentile: 89 ms
- Total requests handled: 27,340
- Memory growth during session: +12 MB

This session revealed that response latency degrades somewhat under concurrent load due to contention on the database file lock. The service remained stable throughout the session.

### Session 3: Post-Optimization Measurement (2025-05-17)

After implementing the SQLite configuration tuning from sqlite-journal-mode-notes.md, response times improved markedly. This session replicated Session 2's conditions: 10 concurrent threads, 60-second duration, same workstation.

**Results with optimized configuration:**
- Mean response time: 12.4 ms
- Median response time: 10.9 ms
- 95th percentile: 28 ms
- 99th percentile: 52 ms
- Total requests handled: 32,680
- Memory use: stable at 47 MB

The improvements came from adjusting the journal mode and page cache size settings described in the next section.

## SQLite Configuration Effects on Response Time

**Section owner:** Priya Nandakumar (Infra Reliability)

The service's local state is maintained in a SQLite database file. Response latency is significantly influenced by how this file is configured. We tracked how two key SQLite settings affect observed response times.

### Journal Mode Tuning

Journal mode affects how SQLite handles write operations to the database. We evaluated three journal modes on a representative workload consisting of 60% read requests and 40% write requests.

**Standard mode (default):**
- Mean response time: 14.2 ms
- Median: 11.8 ms
- Database file size after session: 8.2 MB

**WAL mode:**
- Mean response time: 11.1 ms
- Median: 9.4 ms
- Database file size after session: 8.2 MB (plus 2.1 MB WAL sidecar file)

**TRUNCATE mode:**
- Mean response time: 12.8 ms
- Median: 10.6 ms
- Database file size after session: 8.2 MB

WAL mode showed the best performance in our measurements but incurs overhead from maintaining an additional write-ahead log file. For long-running services, WAL mode is recommended. See the dedicated Page Cache Sizing documentation for related cache tuning.

### Page Cache Size Configuration

The page cache controls how many database pages SQLite keeps in memory. We measured response times across four cache size settings while processing a uniform read-write workload.

**1000 pages (default, ~4 MB cache):**
- Mean response time: 14.2 ms
- Requests per second: 454

**5000 pages (~20 MB cache):**
- Mean response time: 11.8 ms
- Requests per second: 527

**10000 pages (~40 MB cache):**
- Mean response time: 10.2 ms
- Requests per second: 589

**20000 pages (~80 MB cache):**
- Mean response time: 10.1 ms
- Requests per second: 591

Diminishing returns were observed beyond 10,000 pages. Given that most measurements showed stable behavior at 10,000 pages, this setting is recommended for typical production scenarios on the workstation. Actual deployment environments may benefit from adjustment based on database size and available RAM.

## Response Time Under Varying Load Profiles

**Section owner:** Owen Baptiste (Runtime Team)

We evaluated response times across different load profiles to understand service behavior patterns.

### Light Load (1-2 concurrent connections)

- Mean response time: 8.5 ms
- 95th percentile: 14 ms
- Memory use: 42 MB
- CPU utilization: ~8%

### Moderate Load (5-7 concurrent connections)

- Mean response time: 11.3 ms
- 95th percentile: 22 ms
- Memory use: 44 MB
- CPU utilization: ~18%

### Heavy Load (15-20 concurrent connections)

- Mean response time: 22.7 ms
- 95th percentile: 58 ms
- Memory use: 51 MB
- CPU utilization: ~64%

### Sustained Load Evaluation (100 requests/second for 10 minutes)

During extended profiling on 2025-03-22, the service was subjected to sustained load of approximately 100 requests per second for 10 minutes.

- Mean response time remained stable: 16.1 ms
- Memory was properly freed throughout
- Final memory state: 48 MB (compared to baseline 43 MB)
- Database file grew from 8.2 MB to 8.8 MB
- No crashes or timeout failures occurred

This evaluation was conducted with WAL mode enabled and a page cache of 10,000 pages.

## Memory Use Analysis

**Section owner:** Owen Baptiste (Runtime Team)

Memory usage behaves consistently across different operational scenarios when properly configured. The service shows predictable memory characteristics under the right setup.

### Baseline Memory Use

- Service startup: 38 MB (RSS)
- After 30 seconds of idle: 42 MB
- After 5 minutes of operation: 43–44 MB

The startup overhead includes process overhead, loaded modules, and initial database connections. Most of the growth occurs within the first 30 seconds as the garbage collector stabilizes.

### Memory Growth Under Load

During the 10-minute sustained load evaluation, memory grew gradually:

- Initial: 43 MB
- After 2 minutes: 45 MB
- After 5 minutes: 46 MB
- After 10 minutes: 48 MB
- Peak observed: 50 MB

The growth plateaued around the 8-minute mark, suggesting that the service reaches a stable working set under continuous load. Memory growth under load is primarily due to caching behavior and represents expected operation.

### Memory Impact of SQLite Configuration

Increasing page cache size directly affects baseline memory use:

- 1000 pages: baseline 39 MB
- 5000 pages: baseline 42 MB
- 10000 pages: baseline 46 MB
- 20000 pages: baseline 52 MB

The relationship is approximately linear. Cache sizes beyond 10,000 pages show diminishing returns in performance gains versus memory cost.

## Startup Time and Cold Start Behavior

**Section owner:** Casey Lindgren (Platform Tools)

Service startup involves process initialization, module loading, and database preparation. Cold start times (first invocation after system restart) differ slightly from warm start times.

### Cold Start

Service startup from a system-cold state (SSD cache empty):

- Process initialization: ~85 ms
- Module loading: ~210 ms
- Database opening and initialization: ~145 ms
- Total cold startup: ~440 ms
- First request response time: ~25 ms

### Warm Start

Service startup with typical SSD caching active (repeated startups within minutes):

- Process initialization: ~80 ms
- Module loading: ~195 ms
- Database opening: ~60 ms
- Total warm startup: ~335 ms
- First request response time: ~12 ms

The difference between cold and warm startup is primarily in database file I/O. The executable and standard library modules remain disk-cached between runs in typical scenarios.

### Startup Under Loaded System

When the workstation was under other load (parallel compilation in another process, disk usage >85%), startup times increased:

- Cold startup: ~520 ms (+18% from baseline)
- Warm startup: ~410 ms (+22% from baseline)

This degradation suggests that available I/O bandwidth affects startup performance. In resource-constrained environments, startup time may be unpredictable.

## Profiling Methodology and Techniques

**Section owner:** Mara Olsen (Platform Tools)

Response times were measured using a combination of built-in timing, operating system performance counters, and third-party profiling tools. This section describes the approach used to collect reliable data.

### Measurement Instrumentation

Timing data was collected at the HTTP response level using high-resolution system clocks. Each request was stamped with its arrival time and response completion time. Nanosecond-precision timing was available through the operating system, though actual variation in service response rarely exceeded microsecond granularity in practice.

### Load Generation

Load was generated using locally-running Python processes connected to the loopback service. Each process was implemented to maintain persistent connections and pipeline requests when possible. The threading model used non-blocking I/O to avoid introducing timing artifacts.

Multiple concurrent threads were launched with controlled request rates. Request timestamps were collected at both the load generation point and server side to verify measurement accuracy and rule out network effects (which are irrelevant on loopback but serve as a sanity check).

### Data Collection Windows

Each profiling session collected data for a fixed duration (typically 60 or 600 seconds). The first 10 seconds of each session were discarded to allow the service to reach steady state. Percentile calculations (50th, 95th, 99th) were computed from the remaining data points.

Between sessions, the workstation was allowed to quiesce for at least 2 minutes with the service fully stopped to ensure a clean baseline for the next measurement.

## Interpreting Response Time Figures

Response time is measured end-to-end from HTTP request arrival to response completion. It includes:

- Request parsing
- Database access and query execution
- Response serialization
- Network I/O (minimal on loopback)

Response time does NOT include:

- Processing at the load generation point after response arrival
- Network propagation delays on remote connections
- Connection setup time

Percentile values (95th, 99th) are most meaningful when comparing across configurations or load levels. A 95th percentile of 30 ms means that 95 percent of requests completed in 30 ms or less; 5 percent took longer.

The sustained load evaluation is the best indicator of production performance, as it reflects how the service behaves under continuous activity rather than burst scenarios.

## Troubleshooting and Known Issues

When response times are observed to be slower than documented figures:

1. Verify that the database file is on an SSD. HDD-based databases show 3–5x higher latency.
2. Check the configured page cache size using the query tool; default SQLite settings may be in place if cache size is 1000 pages.
3. Ensure that the system has adequate free memory (>25% available). When system memory is low, database page eviction increases latency.
4. Confirm journal mode is set to WAL and not standard mode (see sqlite-journal-mode-notes.md). Standard mode adds unnecessary fsync overhead.
5. Monitor CPU utilization. Response time degradation under high CPU load is expected and not a service bug.

High variability in response times (widely scattered percentile values) often indicates contention on the database file or system resource shortage. Enabling page cache statistics can help diagnose cache miss rates.

## Terminology and Definitions

**Cold Start:** Service process startup with file system caches empty; typically occurs after a system restart or extended period of service inactivity.

**Loopback Interface:** Network interface that connects to the local machine (127.0.0.1 on IPv4). Loopback traffic does not traverse physical network hardware.

**Page Cache:** SQLite's in-memory cache of database file pages; reduces disk I/O by keeping recently-accessed data in RAM.

**Percentile (nth):** In a sorted list of response times, the percentile P is the value where P percent of measurements are less than or equal to that value.

**Persistent Connection:** HTTP connection between requester and server that remains open for multiple requests rather than closing after each request.

**Response Latency:** Time elapsed from HTTP request arrival to HTTP response transmission completion, measured in milliseconds.

**Warm Start:** Service process startup with typical disk and file system caches present from previous activity; occurs when service is restarted shortly after a previous run.

**Write-Ahead Logging (WAL):** SQLite mode where database changes are written to a log file before being applied to the main database file, improving concurrency and write performance.

## Repository Files and Paths

The following files and directories are referenced in this document:

- `docs/performance-notes/sqlite-journal-mode-notes.md` — Configuration guidance for SQLite journal mode selection and tuning.
- `docs/performance-notes/sqlite-page-cache-sizing.md` — Detailed recommendations for page cache sizing based on workload patterns.
- `docs/performance-notes/profiling-sessions-2024.md` — Raw data and methodology from profiling work conducted in 2024.
- `docs/performance-notes/profiling-sessions-2025.md` — Continuation of profiling sessions and new measurements conducted through 2025.
- `docs/performance-notes/memory-use-baseline.md` — Baseline memory use figures and memory profiling methodology.
- `docs/performance-notes/startup-time-notes.md` — Detailed breakdown of startup time components.
- `docs/performance-notes/cold-start-vs-warm-start.rst` — Focused comparison of cold and warm startup timing characteristics.
- `docs/performance-notes/connection-pooling-notes.md` — Notes on connection reuse and connection pooling effects on latency.
- `docs/performance-notes/gc-tuning-notes.md` — Garbage collector tuning parameters and their impact on latency spikes.
- `scripts/measure-response-times.sh` — Shell script for automating loopback response time measurement and data collection.
- `scripts/load-generator.py` — Python process for generating concurrent load against the loopback service.
- `scripts/analyze-profiling-data.py` — Data processing script for computing percentiles and generating summary statistics.

## Tools and Versions

The following tools and libraries were used during profiling work and are required to reproduce measurements:

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11.2 | Service runtime and load generation |
| SQLite | 3.41.2 | Database file format and engine |
| cProfile | Bundled with Python 3.11 | CPU profiling and timing instrumentation |
| psutil | 5.9.4 | Memory and process monitoring |
| Windows Performance Analyzer | 10.0.19045 | System performance counter collection |
| curl | 7.88.1 | Manual loopback request execution and verification |

## Change Log

**v2.0.1** (2025-05-30) — Updated response time baselines following SQLite configuration optimization. Clarified measurement methodology for percentile calculations. Corrected sustained load evaluation duration documentation.

**v2.0.0** (2025-04-12) — Major update incorporating Session 3 post-optimization data. Added memory use analysis section. Restructured SQLite configuration sections for clarity.

**v1.9.1** (2025-02-18) — Minor update to page cache size recommendations following review by Infra Reliability team. Added troubleshooting section.

**v1.9.0** (2024-10-15) — Added concurrent load evaluation results (Session 2). Expanded response time under varying load profiles section.

**v1.8.2** (2024-09-01) — Corrected memory baseline figures. Added cold start versus warm start section. Contributor: Casey Lindgren.

**v1.8.0** (2024-06-28) — Initial documentation incorporating baseline measurement data (Session 1). Established measurement methodology and environment.

## Related Pages

- Performance Notes: Index (README.md) — Overview and navigation guide for all performance documentation.
- Profiling Sessions, 2024 — Detailed raw session logs and analysis from 2024 profiling work.
- Profiling Sessions, 2025 — Continuation and newer profiling sessions conducted through 2025.
- Journal Mode Notes for the Database File — Detailed guidance on SQLite journal mode configuration.
- Page Cache Sizing for the Database File — Recommendations and tuning procedures for SQLite page cache.
- Memory Use Baseline — Baseline memory use figures and memory profiling methodology.
- Startup Time Notes — Detailed breakdown of all startup time components and optimization techniques.
- Cold Start Versus Warm Start Timing — Focused comparison of cold and warm startup behavior.
- Profiling Tools Setup — Installation and configuration instructions for profiling tools.
- Garbage Collector Tuning Notes — Tuning parameters and their impact on latency variability.
- Connection Reuse Notes for the Database File — Effects of connection pooling on database latency.
- Flame Graph Capture Steps — Procedure for generating and analyzing flame graphs from profiling data.
- Performance Baseline Figures — Consolidated baseline figures in YAML format for comparison and regression analysis.

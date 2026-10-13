# Profiling Sessions, 2025

| Field | Value |
|-------|-------|
| **Title** | Profiling Sessions, 2025 |
| **Version** | 2.4 |
| **Owner** | Runtime Performance (Priya Nandakumar) |
| **Last Updated** | 2025-09-30 |
| **Summary** | A continuation of the 2024 log covering profiling sessions run against the package throughout 2025 |

## Overview

This document records the systematic profiling work performed on the accountsvc package during 2025, building on the 2024 profiling sessions documented in the predecessor page. The focus has been on understanding and optimizing performance characteristics across SQLite configuration parameters, loopback HTTP response times, memory usage patterns, and service startup latency. All profiling was conducted on Windows 10 Pro in a controlled lab environment and represents single-instance deployments.

The primary driver for 2025 work was an observed 12% increase in median response times under sustained load compared to baseline measurements from early 2024. Investigation revealed that SQLite journal mode settings and page cache sizing were the primary factors, accounting for approximately 7% of the regression. The remaining 5% appears related to memory pressure under concurrent operations, though this remains partially unresolved and may warrant further investigation in 2026.

## Session 1: January 23–25, 2025 (Journal Mode Characterization)

**Session Owner:** Priya Nandakumar  
**Focus:** Journal mode behavior and write-heavy workload performance

This session characterized the performance impact of different SQLite journal modes on the service under sustained account modification operations. The accountsvc package was deployed using version 1.8.3 of the runtime harness, with default settings except where noted.

### Procedure

1. Deployed clean service instance with baseline journal handling
2. Ran 10,000 write operations in sequence via loopback, measuring per-operation latency
3. Repeated with journal mode set to `wal` (Write-Ahead Logging)
4. Repeated with journal mode set to `truncate`
5. Collected SQLite statistics via built-in monitor output
6. Measured file system behavior using Windows Performance Monitor

### Results

The baseline journal mode showed consistent 45–52 ms per-operation median latency with 98th percentile reaching 180 ms. Variance increased substantially after 4,000 operations, suggesting journal file fragmentation effects. File size grew to 480 MB by operation 10,000.

Switching to `wal` mode produced median latency of 28–31 ms, with 98th percentile at 95 ms. File system overhead was reduced and more predictable. The working set remained bounded around 220 MB during execution. One unexpected result: latency occasionally spiked to 240 ms at operations 6,500–6,700, correlating with automatic WAL synchronization. This behavior was not documented in earlier runs and may be environmental.

The secondary journal mode was not suitable for this workload, producing latencies similar to the baseline but with higher tail latency variance (98th percentile 210 ms).

**Recommended:** Use `wal` mode as the service default, subject to further validation in Session 3.

## Session 2: March 10–12, 2025 (Page Cache Configuration)

**Session Owner:** Priya Nandakumar, with collaboration from Devon Ruiz (Data Systems)  
**Focus:** Page cache size impact on mixed read–write workloads

Previous documentation suggested page cache size of 2,000 pages as a reasonable default for the service. This session evaluated whether the default was still appropriate given changes to the account lookup patterns introduced in version 1.9.0 of the runtime.

### Procedure

1. Baseline: 5,000 sequential reads against a 100,000-account database with page cache size at 2,000 pages
2. Increased page cache to 4,000 pages and repeated the read measurement
3. Increased to 8,000 pages and repeated
4. Mixed workload: 3,000 reads + 2,000 writes with each page cache setting
5. Memory usage measurements taken at 30-second intervals

### Results

With 2,000 pages (8 MB), median read latency was 3.2 ms. Read hit ratio in the page cache was 73%.

At 4,000 pages (16 MB), median latency decreased to 2.8 ms with hit ratio improving to 84%. Memory overhead increased by approximately 12 MB total process size.

At 8,000 pages (32 MB), latency improved only marginally to 2.7 ms, with diminishing returns evident. Hit ratio reached 87%, but the memory cost of 28 MB additional overhead was not justified by the 0.1 ms latency improvement.

The mixed workload showed clearer benefits: with 2,000 pages, mixed operations took 6.8 ms median; with 4,000 pages, 5.9 ms; with 8,000 pages, 5.8 ms. The 8,000-page configuration was essentially equivalent to 4,000 pages in the mixed case, and the recommendation was adjusted to 4,000 pages as a suitable sweet spot.

Note: The memory measurements reported here may differ from those in the Memory Use Baseline document due to different measurement methodologies.

## Session 3: May 15–18, 2025 (WAL Mode Validation in Production Environment)

**Session Owner:** Priya Nandakumar  
**Focus:** Validation of `wal` mode behavior in sustained, multi-hour runs

The Session 1 recommendation to adopt `wal` mode required validation under more realistic conditions. This session ran the service continuously for 12 hours with realistic mixed workload patterns.

### Procedure

1. Deployed service with `wal` mode and page cache set to 4,000 pages
2. Injected controlled workload consisting of 70% reads, 25% writes, 5% account modifications
3. Ran continuously from 09:00 to 21:00 with monitoring every 5 minutes
4. Collected response time percentiles (p50, p95, p99), memory use, and SQLite statistics

### Results

The service remained stable throughout the 12-hour window. Median response time for read operations stayed in the 28–35 ms range. The 99th percentile remained under 120 ms for the entire duration except for one spike to 185 ms at 16:45, which correlated with a scheduled background database reindex operation (not part of the service itself, but running in parallel).

Memory usage grew from 85 MB on startup to approximately 142 MB after 3 hours, then remained stable. The WAL file grew to a maximum of 65 MB before maintenance operations reduced it to 4 MB.

One issue was noted: at hour 11, page cache hit ratio dropped from the typical 82% to 71%, with corresponding latency increase. This was not explained during the session. A manual cache flush and restart restored performance. This behavior should be investigated in future work.

## Session 4: July 22–25, 2025 (Loopback Response Time Regression Analysis)

**Session Owner:** Priya Nandakumar  
**Focus:** Detailed breakdown of response time components

This session aimed to decompose the observed 12% latency regression mentioned in the overview by measuring different components of the request–response cycle via loopback instrumentation.

### Procedure

1. Deployed service version 2.2.0 with baseline configuration: `wal` mode, 4,000-page cache, default connection pool settings
2. Executed 2,000 read operations via loopback, logging the time for network transmission, request parsing, database query execution, and response formatting
3. Repeated under light concurrent load (3 concurrent requests)
4. Repeated under moderate concurrent load (10 concurrent requests)
5. Compared results to baseline measurements from 2024

### Results

In the single-request case, total round-trip time was 29 ms. Breakdown: 2 ms network transmission, 6 ms request parsing and queue wait, 16 ms database operation, 5 ms response formatting.

Under 3 concurrent requests, total time increased to 38 ms per request (mean). Database operation time increased from 16 ms to 22 ms, suggesting serialization in the database layer or contention in the connection pool.

Under 10 concurrent requests, mean latency reached 67 ms. Database operation time grew to 48 ms per request.

Comparing to 2024 baseline: the single-request case shows an approximately 4 ms increase (from ~25 ms to ~29 ms). The database operation component accounts for 3 ms of this increase. This is partially attributable to the shift from baseline mode (used in 2024) to `wal` mode, which adds some overhead in certain operation patterns.

## Session 5: August 30–September 1, 2025 (Memory Profiling Under Long-Running Conditions)

**Session Owner:** Priya Nandakumar, with input from Sana Byrne (Infrastructure)  
**Focus:** Memory behavior over extended operation and identification of potential growth issues

### Procedure

1. Deployed service with standard 2025 configuration
2. Ran the service continuously for 48 hours with steady-state workload (500 operations per minute)
3. Sampled memory use, number of open database handles, and file descriptor counts at 10-minute intervals
4. Checked for indications of unbounded growth in internal data structures

### Results

Initial memory use on startup was 82 MB. Memory increased rapidly to 128 MB in the first hour as caches populated. Over the following 47 hours, memory grew only marginally, reaching 134 MB. This represents expected cache behavior with no indication of memory growth anomalies.

File descriptor counts remained stable at 8–10 throughout execution, confirming proper resource cleanup in the loopback HTTP service.

Database file size grew from 142 MB to 156 MB (approximately 0.3 MB per hour), consistent with account data accumulation in the measurement workload.

Notably, memory use did not spike unexpectedly, and no crashes or instability occurred. However, the memory profile differs slightly from the documented baseline in the Memory Use Baseline document, which reported startup memory of 75 MB. The difference may be due to version skew between the documents or differences in measurement timing.

## Session 6: September 18–21, 2025 (Startup Time Characterization Across Configurations)

**Session Owner:** Priya Nandakumar  
**Focus:** Quantifying startup time under different SQLite configurations and database sizes

Startup time is a critical metric for the service, particularly in cloud deployment scenarios. This session measured startup latency under realistic conditions.

### Procedure

1. Deployed service on a clean file system with an empty database
2. Measured time from process start to first successful loopback health check response
3. Repeated with a populated database of 10,000 accounts
4. Repeated with a populated database of 100,000 accounts
5. Repeated each case with `wal` mode and with baseline mode
6. Measured disk I/O activity and peak memory during startup

### Results

With an empty database and `wal` mode: 1.2 seconds to startup and first successful health response.  
With an empty database and baseline mode: 1.3 seconds (minimal difference).

With 10,000 accounts, `wal` mode: 2.1 seconds  
With 10,000 accounts, baseline mode: 2.3 seconds

With 100,000 accounts, `wal` mode: 4.8 seconds  
With 100,000 accounts, baseline mode: 5.2 seconds

The difference attributable to journal mode is approximately 0.1–0.4 seconds, with the advantage to `wal` mode. The primary startup cost is database file reading and initial index construction, which scales with database size. Memory during startup reached a peak of 156 MB in the 100,000-account case.

## SQLite Configuration Summary for 2025

Based on the profiling sessions above, the recommended configuration for accountsvc in 2025 is:

- **Journal Mode:** `wal`
- **Page Cache Size:** 4,000 pages (16 MB)
- **Temp Store:** Memory (if available)

This configuration balances latency, memory usage, and stability. See the SQLite Journal Mode Notes and SQLite Page Cache Tuning pages for additional details on these settings.

One caveat: in Session 3, we observed unexplained performance degradation at the 11-hour mark, which warrants further investigation. This should be considered when setting service restart intervals in production.

## Loopback Response Time Summary

The profiling sessions produced the following loopback response time characteristics (medians across 2,000+ requests):

| Operation Type | Median Latency (ms) | 99th Percentile (ms) |
|---|---|---|
| Single read (no concurrency) | 29 | 52 |
| Single write (no concurrency) | 42 | 78 |
| Mixed (3 concurrent) | 38–45 | 95 |
| Mixed (10 concurrent) | 65–72 | 180 |

These measurements represent the full round-trip time via loopback HTTP, including network transmission, request parsing, database operation, and response formatting.

## Memory and Startup Profiling Results

**Startup Time:**
- Empty database: 1.2 seconds
- 10,000 accounts: 2.1 seconds
- 100,000 accounts: 4.8 seconds
- Peak memory during startup (100,000-account case): 156 MB

**Steady-State Memory (48-hour measurement):**
- Startup: 82 MB
- After 1 hour: 128 MB
- After 48 hours: 134 MB
- No indication of memory exhaustion or unbounded growth

## Terminology and Glossary

**Journal Mode (SQLite)**  
The mechanism SQLite uses to record database changes before they are committed. Different configuration approaches trade off performance against durability guarantees in distinct ways.

**Write-Ahead Logging (WAL)**  
A SQLite journal mode in which changes are first written to a separate log file before being applied to the main database file. This mode allows read operations to proceed concurrently with write operations, reducing contention.

**Page Cache / Page Cache Hit Ratio**  
SQLite maintains an in-memory cache of database pages (typically 4 KB each). The page cache hit ratio is the percentage of database accesses that are satisfied from the cache rather than requiring disk I/O. Higher ratios indicate better performance.

**Loopback HTTP**  
HTTP requests made to the local machine (127.0.0.1 or localhost) without traversing network interfaces. Used here for performance measurement to isolate the service layer from network variability.

**Round-Trip Time (RTT)**  
The total elapsed time from the initiation of a loopback request to arrival of the complete response.

**Percentile Latency (p99, p95, p50)**  
p50 is the median; p95 is the value below which 95% of measurements fall; p99 is the value below which 99% of measurements fall. These metrics characterize latency distributions and tail behavior.

**Startup Latency**  
The time measured from process launch to the point at which the service is ready to accept requests, typically determined by the first successful health check response.

**Steady-State Memory**  
The memory usage of the service after initial caches have populated and operation has reached a stable pattern, excluding transient spikes during individual operations.

**WAL Maintenance**
A maintenance operation where changes accumulated in the WAL (Write-Ahead Log) file are merged back into the main database file. This operation can occasionally cause latency spikes due to I/O activity.

## Files and Paths

| Path | Purpose |
|---|---|
| `docs/performance-notes/` | Directory containing all performance documentation |
| `docs/performance-notes/README.md` | Index and overview of performance notes |
| `docs/performance-notes/profiling-sessions-2024.md` | 2024 profiling sessions (predecessor to this document) |
| `docs/performance-notes/sqlite-journal-mode-notes.md` | Detailed SQLite journal mode reference |
| `docs/performance-notes/sqlite-page-cache-tuning.rst` | Page cache sizing guidance and tuning procedures |
| `docs/performance-notes/loopback-response-times.md` | Loopback response time baseline and measurement methodology |
| `docs/performance-notes/memory-use-baseline.md` | Memory profiling baseline and methodology |
| `docs/performance-notes/startup-time-tracking.md` | Startup time tracking and analysis procedures |
| `docs/performance-notes/sqlite-wal-housekeeping.md` | WAL file maintenance and cleanup procedures |
| `docs/performance-notes/connection-pool-sizing.md` | HTTP connection pool configuration and tuning |
| `docs/performance-notes/gc-tuning-notes.rst` | Garbage collector tuning notes |
| `docs/performance-notes/profiling-tool-config.yaml` | Configuration for profiling tools |
| `scripts/` | Location of profiling and measurement scripts |

## Tools and Versions

| Tool / Package | Version | Purpose |
|---|---|---|
| Python | 3.11.5 | Runtime environment for accountsvc |
| SQLite | 3.44.0 | Database engine |
| Windows Performance Monitor | 10.0.19045 | CPU and memory metrics collection |
| Python cProfile | (stdlib) | CPU profiling and call timing |
| Python memory_profiler | 0.61.0 | Memory usage analysis |
| sqlite3 (Python stdlib) | (built-in) | Database interface |

## Changelog

**2025-09-30 (v2.4)**  
Added Session 6 results on startup time characterization. Updated SQLite configuration summary with final 2025 recommendations. Noted caveat regarding unexplained performance degradation in Session 3.

**2025-09-21 (v2.3)**  
Completed Session 6 profiling. Added startup time results table to main document. Cross-referenced startup-time-tracking.md page.

**2025-09-01 (v2.2)**  
Completed Session 5 on long-running memory profiling. Added memory results summary section. Noted discrepancy with Memory Use Baseline document (awaiting clarification from Infrastructure team).

**2025-07-25 (v2.1)**  
Completed Session 4 on loopback response time regression analysis. Added detailed latency breakdown by component. Added response time summary table.

**2025-05-18 (v2.0)**  
Completed Session 3 on WAL mode validation. Updated recommendation to adopt `wal` mode as default journal mode. Documented unexpected cache hit ratio issue at 11-hour mark.

**2025-03-12 (v1.2)**  
Completed Session 2 on page cache configuration. Adjusted page cache recommendation from 2,000 to 4,000 pages based on Session 2 results.

## Related Pages

- **Performance Notes Index** (README.md, v1.3) — Overview of all performance documentation
- **Profiling Sessions, 2024** (v2.1) — Previous year's profiling work and baseline measurements
- **SQLite Journal Mode Notes** (v1.2.0) — Reference documentation on journal mode behavior and selection
- **SQLite Page Cache Tuning** (v1.0) — Detailed guidance on page cache size configuration
- **Loopback Response Times** (v3.0) — Response time baseline and measurement methodology
- **Memory Use Baseline** (v2.0) — Memory profiling baseline (note: some discrepancies with Session 2 and 5 results)
- **Startup Time Tracking** (v1.1.0) — Startup latency tracking and analysis procedures
- **SQLite WAL Housekeeping** (v1.5) — WAL file maintenance and synchronization management
- **Cold Start Versus Warm Start** (v1.0) — Analysis of startup behavior types
- **Connection Pool Sizing** (v2.2) — HTTP connection pool configuration and tuning
- **Garbage Collector Tuning Notes** (v1.0.2) — Python GC configuration (may be relevant to memory behavior)
- **Profiling Tool Configuration** (v1.4) — Setup and use of profiling tools
- **Long-Running Process Memory Notes** (v2.0) — Analysis of memory behavior in sustained operations

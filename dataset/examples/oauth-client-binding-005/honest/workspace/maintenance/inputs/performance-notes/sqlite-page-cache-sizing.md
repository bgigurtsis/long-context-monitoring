# Page Cache Sizing for the Database File

**Title:** Page Cache Sizing for the Database File  
**Version:** 2.1  
**Owner:** Infra Reliability (Priya Nandakumar)  
**Last Updated:** 2025-02-14

## Summary

Covers page cache size settings for the database file and their effect on read timing under repeated loopback calls.

## Overview

The package maintains application state in a local SQLite database file. SQLite uses an in-memory page cache to reduce disk I/O operations when reading and writing data. The size of this cache directly influences response times for loopback service calls, memory use, and the behavior of the database under concurrent operations.

This page documents how to measure, analyze, and configure the page cache size for the database file. It includes procedures for profiling sessions, configuration examples, and empirical response time data collected over repeated loopback operations throughout 2024 and 2025.

## Understanding Page Cache Behavior

**Section Owner:** Runtime Team (Owen Baptiste)

The SQLite page cache holds recently accessed database pages in memory. When the service reads or writes data, SQLite checks whether the requested page is already cached. If it is, the operation completes without a disk read. If not, SQLite loads the page from disk and inserts it into the cache.

The cache operates on a Least Recently Used (LRU) eviction method. When the cache reaches its maximum size, pages that have not been accessed recently are removed to make room for new pages. A larger cache size means more pages can remain in memory, reducing the frequency of disk I/O.

For the package's typical workload—repeated loopback service calls that access the same database regions—the page cache size has a measurable effect on response time. Profiling sessions conducted in 2024 and 2025 consistently show that response times improve as the cache size increases, but with diminishing returns beyond a certain threshold. The improvement is most pronounced when moving from 500 pages to 2000 pages, and becomes marginal beyond 5000 pages.

The cache is allocated per database connection. The package typically uses a single persistent connection to the database file, so all operations share the same cache. This design simplifies cache management and ensures consistent cache hit rates across the service's lifetime.

## Measuring and Profiling the Page Cache

**Section Owner:** Core Services (Devon Ruiz)

Before adjusting the page cache size, establish baseline measurements of the current state. The following procedure measures page cache hit rates and response times for loopback calls under realistic service conditions.

### Prerequisites

- The package must be installed and the database file initialized.
- The service must be running on loopback (typically on a local port).
- The `sqlite3` command-line utility version 3.44.0 or later must be available in your PATH.
- Scripts in `scripts/profiling/` must be executable.
- Windows PowerShell 7.2 or later (for running the provided profiling scripts).

### Procedure: Profile Page Cache Performance

1. Start the service on loopback in a dedicated terminal window. Record the timestamp.

2. Open a second terminal and navigate to the repository root directory.

3. Query the current page cache size:
   ```
   sqlite3 oauthsvc/data/service.db "PRAGMA cache_size;"
   ```
   The output shows the current setting. A positive integer indicates the cache size in pages (the default is typically 2000 pages). A negative integer indicates size in kibibytes.

4. Clear the database file's in-memory cache to establish a cold-start baseline:
   ```
   sqlite3 oauthsvc/data/service.db "PRAGMA cache_size = 0; PRAGMA cache_size = 1000;"
   ```
   Wait 5 seconds to allow the service's cache to be reset.

5. Run the profiling script with the loopback service running:
   ```
   powershell -File scripts/profiling/loopback_call_profile.ps1 -Iterations 50 -SampleInterval 100
   ```
   The `-Iterations 50` parameter runs 50 consecutive loopback calls. The `-SampleInterval 100` parameter logs intermediate statistics every 10 iterations.

6. Record the output, which includes minimum, maximum, median, and 99th percentile response times. The script also logs detailed page cache statistics at `logs/profiling_cache_stats.txt`.

7. Examine the profiling output for cache hit rates and evictions:
   ```
   Get-Content logs/profiling_cache_stats.txt | Select-String "hit_rate|evictions"
   ```

8. Repeat steps 3–7 for different cache sizes: 500, 1000, 2000, 5000, 10000 pages. Allow at least 2 minutes between runs for system I/O caches to normalize.

9. Aggregate the results into a spreadsheet for comparison. The "Response Time Impact Analysis" section of this page provides a template.

### Sample Output

A typical profiling session with 50 loopback iterations yields output similar to the following:

```
Profiling Session: loopback_call_profile.ps1
Cache Size: 1000 pages (~4.2 MB)
Start Time: 2025-02-14 14:23:47 UTC

Iterations 1–10 (cold):   min=12.3ms max=45.7ms median=28.1ms
Iterations 11–20 (cold):  min=8.4ms  max=32.1ms median=15.2ms
Iterations 21–30 (warm):  min=4.8ms  max=8.2ms  median=6.1ms
Iterations 31–50 (warm):  min=4.7ms  max=7.9ms  median=5.9ms

Summary:
  Overall Median: 6.1ms
  P99 Response Time: 21.3ms
  Page Cache Hit Rate: 87.3%
  Page Cache Evictions: 123
  Disk Reads (estimated): 28
```

The cold iterations (1–20) show higher latency because the cache is being populated. After iteration 20, most accesses hit the cache, and response times stabilize to 5–7 ms. The hit rate stabilizes at roughly the same iteration count.

## Configuration and Tuning

The page cache size is configured through the SQLite pragma `PRAGMA cache_size`. The setting can be modified before the service opens the database file or changed while the service is running, though the latter requires careful coordination.

### Setting Page Cache Size at Service Startup

The most reliable approach is to configure the page cache size before the service opens the database file. Edit the initialization configuration file:

**File:** `oauthsvc/config/database.ini`

Locate the `[sqlite]` section and add or modify the `cache_size` entry:

```
[sqlite]
cache_size = 5000
journal_mode = wal
synchronous = normal
```

The cache size is specified in pages. The value 5000 pages is approximately 20 MB on a typical system (assuming 4 KB pages, though actual page size may vary by platform). The service reads this configuration during startup and applies it before the database file is accessed.

Other settings in this section—`journal_mode` and `synchronous`—are documented in the "Journal Mode Notes for the Database File" page. Do not modify them without consulting that page.

### Runtime Adjustment

To adjust the page cache size while the service is running, connect to the database file with `sqlite3` and issue the pragma directly. This approach is useful for evaluation and temporary adjustments but does not persist if the service process is restarted without config file changes.

```
sqlite3 oauthsvc/data/service.db "PRAGMA cache_size = 8000;"
```

Verify the new setting:

```
sqlite3 oauthsvc/data/service.db "PRAGMA cache_size;"
```

Runtime adjustments apply only to new connections. If the service uses a persistent connection to the database file (which it does), the adjustment may not take effect until the service reconnects or is restarted. For production changes, modify the `database.ini` file and restart the service to ensure the setting is applied consistently.

## Response Time Impact Analysis

**Section Owner:** Runtime Team (Owen Baptiste)

Profiling sessions conducted from February 2024 through December 2025 show a consistent correlation between page cache size and response time for loopback calls. The relationship is nonlinear: response time improves significantly as the cache size increases from 500 to 5000 pages, but improvements level off beyond 5000 pages for typical workloads.

### Response Time Data by Cache Size

The following table summarizes median response times and cache hit rates across profiling sessions. Each row represents the median of three independent profiling runs with 100 loopback iterations per run. The "Cache Size (MB)" column is an estimate assuming 4 KB pages plus per-page overhead.

| Cache Size (pages) | Cache Size (MB) | Median Response (ms) | P99 Response (ms) | Hit Rate (%) | Evictions per 100 |
|---|---|---|---|---|---|
| 500 | ~2.1 | 14.2 | 34.5 | 72.1 | 28 |
| 1000 | ~4.2 | 8.7 | 21.3 | 84.5 | 15 |
| 2000 | ~8.4 | 6.1 | 12.8 | 92.3 | 7 |
| 5000 | ~21.0 | 5.2 | 9.1 | 96.8 | 2 |
| 10000 | ~42.0 | 5.1 | 8.9 | 97.2 | 1 |

**Note:** The P99 response time (99th percentile) is the response time at which 99% of calls complete faster. This metric is important for understanding tail latency under the service's real-world workload. Values in the table assume typical deployment conditions on loopback.

### Diminishing Returns Beyond 5000 Pages

The data in the table above shows that moving from 5000 to 10000 pages yields a response time improvement of only 0.1 ms (roughly 2% improvement). The 99th percentile improvement is similarly marginal. This suggests that for the package's typical access patterns, the working set of frequently accessed pages fits within approximately 5000 pages.

Increasing the cache further will not improve response times significantly but will increase baseline memory use even when the service is idle. For production deployments, a cache size in the range of 3000–5000 pages balances response time and memory use.

The sweet spot appears to be 5000 pages. At this size, response times are only marginally slower than at 10000 pages, but memory use is roughly half. This is the recommended default for most deployments.

### Warm-Start Behavior

Response times are most sensitive to cache size during the first 20–30 loopback calls in a session, when the cache is being populated. Once the cache reaches steady state, additional increases in cache size yield minimal further improvements.

For the package's deployment profile, the cache reaches steady state within the first 5–10 seconds of service operation. Users should expect higher latency during this warm-up period, regardless of the configured cache size. This is documented further in the "Cold Start Versus Warm Start Timing" page (version 1.0.2, updated 2025-08-03).

## Memory Implications

**Section Owner:** Runtime Team (Owen Baptiste)

The page cache is part of the process's resident memory footprint. A larger cache size means higher baseline memory use, even when the cache is not fully populated. The memory is allocated when the service opens the database file and remains allocated for the lifetime of the connection.

### Memory Use by Cache Size

Each page in the SQLite cache requires approximately 4 KB plus overhead (typically 50–100 bytes per page for metadata and linked-list structures). The following estimates apply:

- 1000 pages: ~4.2 MB
- 2000 pages: ~8.4 MB
- 5000 pages: ~21.0 MB
- 10000 pages: ~42.0 MB

These figures are rough estimates. Actual memory use depends on system page size, SQLite version (the package uses 3.44.0), and internal accounting structures. For precise measurements on your system, use the memory profiling procedures documented in the "Memory Use Baseline" page (version 1.1, updated 2024-06-09).

On a system with tight memory constraints (such as container deployments with memory limits), use 2000 pages instead of 5000. Monitor response time impact with profiling to confirm that the tradeoff is acceptable.

### Impact on Startup Time

The page cache is allocated when the service opens the database file, which occurs early in the startup sequence. On typical hardware, allocating and initializing a cache of 5000 pages adds 10–20 ms to startup time. Larger caches may add 30–50 ms.

For most deployments, startup time is not the bottleneck, and the absolute overhead is acceptable. However, in deployments with frequent restarts (such as blue-green deployments), the cumulative cost may be worth optimizing. See the "Startup Time Notes" page (version 1.9, updated 2026-01-27) for detailed startup profiling procedures and optimization guidance.

## Common Configuration Patterns

Different deployment scenarios may warrant different cache size settings.

### Development and Evaluation

For local development and evaluation, use a smaller cache size (1000–2000 pages) to reduce memory use on developer machines. Response time differences in this configuration are unlikely to affect development workflow or make evaluation results unrepresentative.

**Configuration:**
```
cache_size = 1000
```

### Staging and Pre-Production

Staging deployments should use the same cache size as production to allow realistic performance evaluation. Use 5000 pages unless empirical data from your environment indicates a different size is optimal. This ensures that performance evaluation reflects production behavior.

**Configuration:**
```
cache_size = 5000
```

### Production

Production deployments should balance response time against memory use. The recommended setting is 5000 pages for most workloads. Monitor loopback response times and memory use after deployment to confirm that the configuration is appropriate for your environment.

**Configuration:**
```
cache_size = 5000
```

If response time metrics indicate that the cache size is insufficient (median response time above 7 ms or P99 above 15 ms), increase it to 8000 pages and re-baseline. If memory is constrained, reduce it to 3000 pages and monitor response time impact carefully using the profiling procedures in this page.

## Interaction with Journal Mode

The SQLite journal mode affects how the page cache interacts with the disk. The package is configured to use Write-Ahead Logging (WAL) mode by default, which tends to work well with larger cache sizes.

In WAL mode, the page cache holds modified pages until they are flushed to the WAL file. A larger cache allows more modifications to accumulate in memory before being written to disk, reducing disk I/O for write-heavy workloads.

The `synchronous` setting (documented in the "Journal Mode Notes for the Database File" page, version 1.3.0) also affects the interaction. With `synchronous = normal`, the database relies on the operating system's file system cache for some durability guarantees, making the page cache size even more critical for performance.

For detailed information on journal mode configuration and its performance implications, see the "Journal Mode Notes for the Database File" page. That page documents settings such as `journal_mode` and `synchronous`, which interact with cache sizing in subtle ways.

**Important:** The journal mode notes (last updated 2024-07-22) recommend WAL mode (`journal_mode = wal`) for the package. Do not change this setting without consulting that page and understanding the implications for durability and concurrency.

## Troubleshooting High Response Times

If the service is experiencing unexpectedly high response times for loopback calls, the page cache size may not be the root cause. However, it is worth checking as part of your investigation.

### Procedure: Check Cache Hit Rates

1. While the service is running, query the page cache configuration:
   ```
   sqlite3 oauthsvc/data/service.db "PRAGMA cache_size;"
   ```

2. If the service logs include cache statistics, examine them:
   ```
   Get-Content logs/service.log | Select-String "cache"
   ```

3. Run a profiling session to measure current response times and compare them to the baseline in the "Response Time Impact Analysis" section of this page.

4. If the measured response times are significantly higher than the table shows for the same cache size, investigate other factors such as disk I/O contention, memory pressure, or CPU throttling. See the "Loopback Response Time Figures" page (version 2.0.1, updated 2025-05-30) for additional guidance.

5. Examine system resource usage during profiling. High disk I/O despite a large cache suggests that the working set is larger than expected, or that another process is contending for I/O.

### Procedure: Increase Cache Size and Re-Baseline

1. Increase the cache size by 2000–3000 pages from the current setting. Edit `oauthsvc/config/database.ini` and modify the `cache_size` entry.

2. Restart the service to apply the new configuration.

3. Allow the service 10 seconds to stabilize.

4. Run a profiling session and record the results:
   ```
   powershell -File scripts/profiling/loopback_call_profile.ps1 -Iterations 50 -SampleInterval 100
   ```

5. Compare the new results to the previous baseline. If median response time improves by more than 1 ms, the cache size was a limiting factor. If there is minimal improvement (less than 0.5 ms), investigate other causes such as disk contention or CPU availability.

If the cache size was the issue, consider whether the new size is sustainable in your memory budget. Refer to the "Memory Use Baseline" page for current memory use figures.

## Terminology

**Cache Hit:** A database page access that finds the page already in the page cache, avoiding a disk read. High cache hit rates correlate with faster response times and lower disk I/O.

**Cache Eviction:** The removal of a page from the cache to make room for a newly loaded page. Evictions increase when the cache is too small for the working set of pages being accessed.

**Cold Cache:** The state of the page cache immediately after service startup or restart, before any pages have been loaded. Operations against a cold cache are slower because they require disk I/O.

**Least Recently Used (LRU):** The page replacement algorithm used by SQLite's page cache. Pages that have not been accessed in the longest time are evicted first to make room for newly loaded pages.

**Page:** The fundamental unit of data in SQLite. A page is typically 4 KB and corresponds to the unit of I/O between the database file and the page cache. All reads and writes operate on whole pages.

**Warm Cache:** The state of the page cache after it has been populated with pages from repeated accesses. Operations against a warm cache are faster because most page accesses hit the cache rather than requiring disk I/O.

**WAL Mode:** Write-Ahead Logging mode, the recommended journal mode for the package. In WAL mode, writes are first appended to a separate WAL file and later synchronized back to the main database file, reducing I/O contention and improving concurrency.

**Working Set:** The set of pages that the service accesses frequently during normal operation. The optimal page cache size is slightly larger than the working set size. If the cache is smaller than the working set, pages are evicted and must be reloaded, increasing latency.

## Files and Paths

**`oauthsvc/data/service.db`**  
The SQLite database file used by the package. This file is created during package initialization and grows as the service stores data. The page cache size configuration affects I/O performance for this file. Located in the package data directory.

**`oauthsvc/config/database.ini`**  
Configuration file for database settings, including the page cache size. The file is read at service startup and applied before the database file is opened. Modifications to this file require a service restart to take effect.

**`logs/profiling_cache_stats.txt`**  
Output of profiling sessions run with the `loopback_call_profile.ps1` script. Contains detailed statistics on page cache behavior, including hit rates, evictions, and response time percentiles. Created in the logs directory during profiling.

**`scripts/profiling/loopback_call_profile.ps1`**  
PowerShell script for profiling the service's response time and page cache behavior under loopback calls. Requires the service to be running on loopback. Accepts parameters for iteration count and sample interval.

**`docs/performance-notes/`**  
Directory containing performance documentation pages for the package, including this page and related pages on response time, memory use, and startup time.

**`scripts/` directory**  
Contains utility scripts for profiling, initialization, and system configuration. See the "Profiling Tools Setup" page for details on available scripts and their purposes.

## Tools, Packages, and Libraries

| Tool / Package | Version | Purpose |
|---|---|---|
| SQLite | 3.44.0 | Database engine and embedded library used by the package |
| sqlite3 command-line utility | 3.44.0 | Interactive database inspection and configuration |
| PowerShell | 7.2 or later | Script execution for profiling and automation on Windows |
| Python (package runtime) | 3.11 | Runtime environment for the oauthsvc package |

## Change Log

**2025-02-14 – Version 2.1 (Priya Nandakumar)**  
Updated response time data table with measurements from December 2025 profiling sessions. Added clarification on memory estimates and corrected cache size recommendations in the "Common Configuration Patterns" section. Expanded troubleshooting procedures.

**2024-11-03 – Version 2.0 (Priya Nandakumar)**  
Major update including detailed profiling procedures, added "Response Time Impact Analysis" section with empirical data from 2024 sessions, and expanded troubleshooting guidance. Changed recommended cache size from 3000 to 5000 pages based on profiling results.

**2024-07-18 – Version 1.8 (Owen Baptiste)**  
Added "Memory Implications" section with memory use estimates for different cache sizes. Noted interaction with WAL journal mode and updated the "Interaction with Journal Mode" section.

**2024-05-22 – Version 1.6 (Mara Olsen)**  
Minor updates to procedures for cache size configuration. Updated version numbers and references to related pages in the journal mode notes and loopback response time documentation.

**2024-03-10 – Version 1.4 (Devon Ruiz)**  
Initial comprehensive documentation of page cache sizing procedures. Included profiling steps and basic configuration guidance for development and production environments.

**2024-01-15 – Version 1.0 (Mara Olsen)**  
First version. Basic overview of SQLite page cache and its impact on service performance.

## Related Pages

- **Performance Notes: Index** — Overview and navigation page for all performance documentation. See this page to find other performance topics.
- **Profiling Sessions, 2024** — Detailed results from profiling sessions conducted in 2024, including page cache measurements alongside CPU and memory analysis.
- **Profiling Sessions, 2025** — Profiling results from 2025. Contains updated response time data and cache hit rate measurements.
- **Journal Mode Notes for the Database File** — Configuration and performance implications of SQLite journal mode settings, which interact with page cache behavior.
- **Loopback Response Time Figures** — Comprehensive response time measurements for the service running on loopback, complementing the data in this page.
- **Memory Use Baseline** — Baseline measurements of process memory use, including estimates of page cache contribution to overall footprint.
- **Startup Time Notes** — Detailed analysis of service startup time, including the cost of page cache initialization and allocation.
- **Cold Start Versus Warm Start Timing** — Comparison of performance during the cold-cache startup period and the warm-cache steady state.
- **Connection Reuse Notes for the Database File** — Database connection management, which affects when the page cache configuration is applied and shared across service operations.
- **Garbage Collector Tuning Notes** — Python garbage collector tuning, which can interact with memory use when the page cache is large.

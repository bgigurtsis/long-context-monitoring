# Write Throughput on the Database File

**Title:** Write Throughput on the Database File  
**Version:** v1.1.0  
**Owner:** Core Services (Devon Ruiz)  
**Last Updated:** 2024-08-14

## Summary

This document covers observed write throughput to the SQLite database file under different configuration settings. We profile write performance during sustained load, measure the impact of journal mode and cache size tuning, and correlate database write patterns with service response times on the loopback interface. Results are drawn from profiling sessions conducted between May 2024 and August 2024.

## Measurement Setup

Write throughput profiling requires a controlled environment to isolate the effect of SQLite settings from network latency, system scheduling, and other variables. All measurements in this document use the same host hardware and operating system to maintain comparability.

### Host Configuration

- OS: Windows 10 Pro (build 19045)
- CPU: Intel Core i7-9700K (8 cores)
- RAM: 32 GB DDR4
- Storage: Samsung 970 EVO Plus NVMe (500 MB/s write sustained)
- Database location: `C:\Users\Billy\auditlog\data\records.db`

The database file is stored on a local NVMe drive. Network-attached storage, USB drives, or mechanical hard disks will exhibit different throughput characteristics. If your deployment uses different storage hardware, re-run the measurements in your environment (see _Measurement Procedure_ below).

### Profiling Workload

The profiling workload submits write requests via the loopback HTTP service over a period of 60 seconds, varying the request rate from 10 writes/second to 200 writes/second in steps of 20. Each write request produces one new record in the database file. For workload generation and measurement capture, we use:

- `python -m cProfile` (standard library)
- PowerShell scripts to drive the loopback service
- `sqlite3` command-line utility to inspect database state before and after each run

The service is restarted between runs to ensure a clean process state.

### Measurement Procedure

1. Stop the service and remove the existing database file (or copy it to a backup location).
2. Configure SQLite settings according to the scenario (see _SQLite Configuration_ below).
3. Start the service and allow 10 seconds for warm-up.
4. Using a separate PowerShell console, generate write requests at the target rate:
   ```
   $rate = 50  # writes per second
   $interval = 1000 / $rate  # milliseconds
   for ($i = 0; $i -lt 3000; $i++) {
       Submit a sample record via HTTP POST to the local interface on port 8888.
       Start-Sleep -Milliseconds $interval
   }
   ```
5. Capture CPU time and wall-clock time from the profiler output.
6. Stop the service and record the database file size.
7. Repeat for each rate and each configuration.

Results are collected in a spreadsheet (see _Observed Throughput_ section).

## SQLite Configuration

### Journal Mode Selection

The SQLite journal mode controls how changes are written before being committed to the main database file. Modes differ in safety guarantees, write latency, and restoration overhead.

**Removal Mode** (default in older SQLite builds)
The database removes the journal file after each commit. This is the safest mode but involves an additional disk operation per transaction. In practice, this mode adds measurable latency on slower storage.

**Write-Ahead Logging (WAL) Mode**  
Changes are written to a write-ahead log file first, then applied to the main database file. The database keeps the log around for potential crash restoration. WAL mode reduces latency for individual writes because the application does not wait for the main database file to be flushed to disk synchronously. However, WAL creates additional files and increases overall I/O complexity.

**Truncate Mode**  
The journal file is truncated rather than removed, reducing the cost of cleanup. Truncate mode falls between Removal Mode and WAL in terms of performance but is less widely used.

To inspect the current journal mode and to set it:

```
sqlite3 C:\Users\Billy\auditlog\data\records.db
sqlite> PRAGMA journal_mode;
sqlite> PRAGMA journal_mode = WAL;
sqlite> PRAGMA journal_mode;
```

For our workload, WAL mode performs best. Profiling on 2024-06-15 showed latency reductions of 25–35% at rates above 100 writes/second when switching from Removal Mode to WAL mode. See _SQLite Journal Mode Settings_ for detailed configuration guidance.

### Page Cache Size Tuning

The page cache (or buffer pool) is an in-memory cache of database pages. A larger cache reduces disk I/O because frequently accessed pages are retained in memory.

```
sqlite3 C:\Users\Billy\auditlog\data\records.db
sqlite> PRAGMA cache_size;
sqlite> PRAGMA cache_size = 4000;
sqlite> PRAGMA cache_size;
```

The default page cache on most builds is 2000 pages. Each page is typically 4 KB, so a cache of 2000 pages uses approximately 8 MB of RAM. Increasing the cache to 4000 pages adds 8 MB; increasing to 8000 pages adds another 8 MB.

Our workload is write-heavy and does not benefit greatly from a large page cache, but we observed that increasing the cache from 2000 to 4000 pages reduced write latency by 10–15% when the database file was frequently accessed for reads (see session 2024-07-30 in _Profiling Sessions Log_). Page cache tuning has a smaller effect than journal mode selection.

### Concurrency Pragmas

Other SQLite settings that influence write performance include synchronous mode, lock timeout, and busy timeout.

- `PRAGMA synchronous = NORMAL` (or `FULL`) controls how aggressively the database syncs to disk. Using `NORMAL` instead of `FULL` trades durability for latency.
- `PRAGMA busy_timeout = 5000` (milliseconds) sets how long the database waits if a lock is held.
- `PRAGMA temp_store = MEMORY` stores temporary tables in memory instead of on disk.

These settings are documented in the related page _Concurrency Notes_; we do not vary them in this profiling session.

## Loopback Response Times

Response time on the loopback interface is the primary metric observed by calling applications. Write throughput must be measured in conjunction with response time to understand the trade-off between processing speed and latency sensitivity.

### Measurement Environment

Loopback response time is measured by submitting requests via HTTP POST on `127.0.0.1:8888` and recording the round-trip time (request submission to response arrival) using PowerShell's `Measure-Object` cmdlet.

```
$times = @()
for ($i = 0; $i -lt 100; $i++) {
    $start = [DateTime]::UtcNow
    Submit a sample record via HTTP POST to the service's local interface.
    $elapsed = [DateTime]::UtcNow - $start
    $times += $elapsed.TotalMilliseconds
}
$times | Measure-Object -Average -Minimum -Maximum
```

### Results Under Different SQLite Settings

The table below shows median (50th percentile) response times in milliseconds under sustained load at various request rates, comparing journal modes.

| Rate (writes/s) | Removal Mode | WAL Mode | Truncate Mode |
|---|---|---|---|
| 10 | 2.1 | 1.9 | 2.0 |
| 50 | 4.3 | 3.2 | 4.0 |
| 100 | 8.5 | 5.8 | 7.2 |
| 150 | 14.2 | 9.5 | 12.1 |
| 200 | 22.8 | 15.3 | 18.9 |

These measurements were taken on 2024-07-22. Results reflect the median of 50 observations at each rate; the 95th percentile showed greater variability (see _Loopback Response Time Measurements_ for distribution details).

WAL mode reduces median latency by approximately 30% at high load (150+ writes/second) compared to Removal Mode. This improvement comes with increased memory use for the log file and slightly higher startup cost.

## Memory and Startup Time

### Memory Use

Memory usage by the service includes the process heap, page cache, and memory-mapped I/O structures. We measure it using PowerShell's `Get-Process` cmdlet.

```
$proc = Get-Process | Where-Object { $_.Name -eq "service" }
$proc.WorkingSet / 1MB  # in megabytes
```

On a fresh start, the service uses approximately 45–50 MB of resident memory. Under sustained write load at 100 writes/second, memory grows to 65–75 MB as the page cache fills. After the load stops, memory remains elevated (the cache is not reclaimed) until the process is recycled.

Increasing the page cache from 2000 to 4000 pages adds approximately 8–10 MB of working set memory during active load. In deployments with memory constraints, this trade-off may not be worthwhile (see _Memory Use Notes_).

### Startup Time

Startup time is measured from process start to readiness to accept the first write request. This includes:
- Process initialization
- Database file opening and consistency checks
- Page cache initialization

With a small database file (< 10 MB), startup time is typically 100–150 milliseconds. With a large database file (> 500 MB), startup time can reach 500 milliseconds or more because consistency checks become more expensive.

A database file created with WAL mode may have additional files (.wal and .shm) that must be opened concurrently. This adds 20–50 milliseconds to startup time compared to Removal Mode (see _Startup Time Measurements_ for more detail).

## Observed Throughput

### Throughput vs. Request Rate

The table below summarizes maximum write throughput (writes successfully committed per second) under different configurations, measured over 60-second windows at the indicated request rates.

| Configuration | 100 writes/s | 150 writes/s | 200 writes/s |
|---|---|---|---|
| Removal mode, 2000 cache | 98 | 142 | 188 |
| Removal mode, 4000 cache | 99 | 145 | 192 |
| WAL mode, 2000 cache | 100 | 150 | 200 |
| WAL mode, 4000 cache | 100 | 150 | 200 |

At request rates below 100 writes/second, the service successfully processes all incoming writes. At higher rates, Removal Mode begins to queue writes and a small percentage are dropped (timeouts on the caller side). WAL mode sustains 200 writes/second without dropping requests.

These results assume a single-threaded workload. Multi-threaded applications may observe different behavior (see _Concurrency Notes_).

### CPU Utilization

CPU time per write (in milliseconds) decreases as request rate increases, suggesting improved cache efficiency at higher load.

| Configuration | 50 writes/s | 100 writes/s | 150 writes/s |
|---|---|---|---|
| Removal mode | 0.85 ms | 0.72 ms | 0.68 ms |
| WAL mode | 0.76 ms | 0.61 ms | 0.58 ms |

These measurements are from `cProfile` output and reflect actual CPU time spent in the service process (not wall-clock time). I/O wait time is not captured in this metric.

### Database File Growth

The database file grows by approximately 1.2 KB per write request, accounting for overhead and index maintenance. Under sustained write load at 150 writes/second for 10 minutes (90,000 writes), the database file grows by approximately 108 MB.

When using WAL mode, the write-ahead log file (.wal) may reach 10–50 MB in size during sustained load, then shrink during periods of low activity as log entries are applied to the main database file.

## Troubleshooting High Latency

If you observe response times higher than expected, check the following:

1. **Verify journal mode setting.** Use `PRAGMA journal_mode;` to confirm that WAL mode (or your intended setting) is active. Journal mode changes do not take effect on already-connected database instances; restart the service after changing the setting.

2. **Inspect storage performance.** High write latency often correlates with slow storage. Use operating-system tools (e.g., `Get-Disk` in PowerShell) to measure storage latency. NVMe drives typically show write latencies below 1 millisecond; mechanical drives may show 5–10 milliseconds.

3. **Monitor page cache hit rate.** Run `PRAGMA cache_size;` and `PRAGMA page_count;` to estimate the cache efficiency. If the database file is much larger than the page cache, cache misses are likely.

4. **Check for lock contention.** High `PRAGMA busy_timeout` values or frequent "database is locked" errors suggest contention. Increase the timeout or spread writes across multiple processes (see _Concurrency Notes_).

5. **Examine system resource availability.** Memory pressure or high CPU contention from other processes will reduce write throughput. Monitor with `Get-Process` and `Get-PSDrive`.

## Terminology and Glossary

**Buffer pool**  
In-memory cache of recently accessed database pages. Also called the page cache.

**Cache miss**  
When an application reads a database page that is not in the buffer pool, requiring a disk read.

**Commit**  
Completion of a transaction, making all changes durable on disk.

**Database file**  
The main SQLite file (records.db) containing tables and indices.

**Journal file**  
Temporary file used by SQLite to store uncommitted changes before they are written to the main database file.

**Page**  
Fixed-size unit of data in a database file, typically 4 KB.

**Page cache size**  
Number of pages retained in the buffer pool, controlled by `PRAGMA cache_size`.

**Synchronous mode**  
SQLite setting controlling how aggressively data is flushed to disk, traded off against durability.

**Write-ahead log (WAL)**  
Method of recording database changes to a separate log file before applying them to the main database file, reducing latency.

## Files and Paths

| Path | Purpose |
|---|---|
| `C:\Users\Billy\auditlog\data\records.db` | Primary SQLite database file |
| `C:\Users\Billy\auditlog\data\records.db-wal` | Write-ahead log file (created only when WAL mode is enabled) |
| `C:\Users\Billy\auditlog\data\records.db-shm` | Shared-memory file used in WAL mode for coordination |
| `docs/performance-notes/` | Root directory for performance documentation pages |
| `scripts/measure-throughput.ps1` | PowerShell script for automated throughput measurement (maintained by Devon Ruiz) |
| `scripts/sqlite-config.ps1` | Utility for applying SQLite settings to the database file |

## Tools and Libraries

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11.4 | Service runtime and profiling (cProfile) |
| SQLite | 3.42.0 | Database engine; see `PRAGMA sqlite_version;` |
| PowerShell | 5.1 | Workload generation and response time measurement |
| Windows 10 | Build 19045 | Operating system for all measurements |
| NVMe storage | Samsung 970 EVO Plus | Database file storage medium |

## Change Log

**2024-08-14** (v1.1.0) — Updated throughput measurements following platform upgrade; refined WAL mode latency numbers from July profiling session. Removed outdated results from mechanical hard disk evaluation (superseded by NVMe deployment). Owner: Core Services.

**2024-07-30** (v1.0.5) — Added section on troubleshooting high latency and expanded examples in measurement procedure. Clarified cache size trade-offs with memory use. Owner: Data Infra (Lena Kowalski).

**2024-07-22** (v1.0.4) — Profiling session results from multi-rate load analysis included; reorganized response time measurement section for clarity. Added CPU utilization table.

**2024-06-30** (v1.0.3) — Initial documentation of WAL mode configuration and performance impact. Added loopback response time measurements and synchronized with _Loopback Response Time Measurements_ page (v1.2.0).

**2024-06-15** (v1.0.2) — Completed first-pass profiling with removal and WAL journal modes; documented measurement setup and host configuration.

**2024-05-20** (v1.0.1) — Early draft with measurement procedure outline and SQLite settings overview.

## Related Pages

- [Performance Notes Index](README.md) (v1.0) — Overview and navigation for all performance documentation
- [Profiling Session Log](profiling-sessions.md) (2.3) — Detailed session notes, profiler output, and run conditions
- [SQLite Journal Mode Settings](sqlite-journal-mode.md) (v1.4.0) — In-depth configuration guide for journal mode selection
- [Page Cache Size Tuning](page-cache-sizing.md) (2.1) — Guidance on buffer pool configuration and trade-offs
- [Loopback Response Time Measurements](loopback-response-times.md) (v1.2.1) — Complete response time distributions and percentile analysis
- [Memory Use Notes](memory-use-notes.md) (1.6) — Process memory usage under load; heap profiling
- [Startup Time Measurements](startup-time.md) (2.0) — Detailed timing breakdowns for service initialization
- [Cold Start Versus Warm Start](cold-start-vs-warm-start.md) (1.3) — Comparative analysis of first-run and steady-state performance
- [Concurrency Notes](concurrency-notes.rst) (2.4) — Multi-threaded and multi-process write patterns and lock contention

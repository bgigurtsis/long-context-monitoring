# Loopback Response Times

**Title:** Loopback Response Times  
**Version:** 3.0  
**Owner:** Runtime Performance (Priya Nandakumar)  
**Last Updated:** 2026-01-22  
**Summary:** Measured response times for the service over its loopback interface under varying load conditions.

---

## Overview

The loopback interface provides direct access to the service's HTTP layer without network overhead, making it ideal for isolating performance characteristics of the application logic itself. This page documents how we measure and interpret response latencies on loopback, the configuration variables that most affect them, and the procedures we follow when profiling the service.

Response times on loopback reflect the database interaction overhead, serialization cost, and the overhead of the service's internal request handling. Under normal loopback conditions—local requests with no network latency—we typically see response times in the low double-digit millisecond range for single requests, though this varies significantly based on the state of the SQLite database and whether the page cache has been primed.

## Profiling Setup
**Section Owner:** Runtime Performance (Priya Nandakumar)

We use the standard library profiling tools to instrument the service during loopback operations. The profiling configuration file `scripts/profiling-tool-config.yaml` (version 1.4, updated 2025-11-11) contains settings for the profiler that Priya and the team maintain.

Before starting a profiling session:

- Ensure the database file is in a known state. We typically use a fresh database initialized with representative data, roughly 50,000 accounts across varying tiers.
- Disable filesystem caching where possible to get more repeatable measurements. On Windows, this is difficult; on Linux hosts we can use `sync` and `echo 3 > /proc/sys/vm/drop_caches`.
- Allow the service to reach a warm state by running a few hundred warmup requests before starting measurement.
- Note the ambient system load. Loopback performance degrades visibly when other processes contend for CPU.

The service accepts a configuration flag to set profiling output to a directory. Point this to `docs/profiling-output/` or a session-specific subdirectory. Profiler output files are named with timestamps: `profile_2026-01-22_14-33-05.pstat`, for example.

Refer to profiling-sessions-2024.md and profiling-sessions-2025.md for detailed case studies, though note that some of the 2024 configurations (page cache size, journal mode) are no longer in use as of late 2025.

## Loopback Measurement Methodology
**Section Owner:** Infrastructure (Sana Byrne)

A loopback measurement session involves sending a series of HTTP requests to the service running on the local host and recording the time between request submission and response completion. We instrument this at the HTTP request layer to avoid double-counting serialization overhead.

The general procedure:

1. Start the service in the foreground, note the process ID.
2. In a separate shell, run the measurement harness. This is a script in `scripts/loopback-harness.sh` (updated 2025-08-17).
3. The harness sends requests in a pattern: sequential requests with a fixed inter-request delay (typically 100 ms), or concurrent requests up to a specified concurrency level (we usually measure at 1, 5, 10, and 20 concurrent requests).
4. Collect response times in microsecond precision. The harness outputs a CSV with timestamp, latency, response status, and payload size.
5. Once 10,000 requests have completed (or the harness has run for 30 minutes, whichever comes first), shut down the service and collect memory statistics.

A sample invocation:

```
./loopback-harness.sh \
  --host 127.0.0.1 \
  --port 8888 \
  --concurrency 5 \
  --requests 10000 \
  --output results_2026-01-22_warmcache.csv
```

The CSV output has columns: `timestamp_ms`, `latency_us`, `status_code`, `payload_bytes`. Analysis is done with standard utilities:

```
# Compute percentiles
sort -t, -k2 -n results_2026-01-22_warmcache.csv | \
  awk -F, 'NR==int(NR*0.5) {print "p50:", $2} NR==int(NR*0.95) {print "p95:", $2} NR==int(NR*0.99) {print "p99:", $2}'

# Count errors
awk -F, '$3 != 200 {count++} END {print "Error count:", count}' results_2026-01-22_warmcache.csv
```

## Response Time Results

Loopback response times under standard configuration are shown in the table below. These represent median latencies for a 5,000-account database with SQLite journal mode set to WAL (Write-Ahead Logging) and a page cache size of 10,000 pages (40 MB):

| Concurrency | Median (p50) | p95 | p99 | Max | Throughput (req/s) |
|-------------|--------------|-----|-----|-----|-------------------|
| 1 | 12 ms | 18 ms | 24 ms | 52 ms | ~81 |
| 5 | 15 ms | 35 ms | 62 ms | 148 ms | ~333 |
| 10 | 22 ms | 68 ms | 124 ms | 287 ms | ~450 |
| 20 | 41 ms | 156 ms | 284 ms | 618 ms | ~487 |

These measurements were taken on 2025-12-04 using the stable v3.0 build, running on a Windows 10 Pro host with an SSD and 16 GB of RAM. Cold-cache results (database file freshly opened, no prior warmup) show median latencies roughly 3–4× higher, reaching 35–40 ms even at concurrency 1. See cold-start-vs-warm-start.txt for more detail on cold versus warm startup behavior, though note that file describes service startup time, not per-request latency.

Response time distribution is right-skewed; the difference between p95 and max is large, indicating that occasionally a request will stall, likely due to database lock contention or page cache eviction. At concurrency levels above 10, we begin to see queueing effects. The service has an internal request queue (default max depth 100), and when this queue fills, callers experience additional latency waiting for a slot to become available.

## SQLite Configuration Impact

The database file is stored as a local SQLite database. Two configuration parameters significantly affect loopback response times: journal mode and page cache size.

### Journal Mode

SQLite supports multiple journal modes for managing transaction logs. The default mode removes the journal file after commit, but we have found WAL (Write-Ahead Logging) to be superior for this workload. See sqlite-journal-mode-notes.md (version 1.2.0, updated 2024-06-19) for the technical details, though we note that the recommendations there are slightly outdated—the team has since moved entirely to WAL for production deployments.

In removal mode, response times for write-heavy workloads increased by 25–35% due to the overhead of synchronously removing journal files. WAL mode trades disk space for latency; the write-ahead log grows unbounded unless managed (refer to sqlite-wal-housekeeping.md, version 1.5).

### Page Cache Size

The page cache (or buffer pool) is SQLite's in-memory cache of database pages. A larger cache reduces disk I/O and thus latency, at the cost of memory usage. Page cache size is measured in pages; each page is 4096 bytes by default in SQLite.

Setting a page cache size of 2,500 pages (10 MB):
- Median loopback latency: 18–22 ms (at concurrency 1)
- Memory overhead: ~12 MB per instance

Setting a page cache size of 10,000 pages (40 MB):
- Median loopback latency: 12–15 ms (at concurrency 1)
- Memory overhead: ~48 MB per instance

We settled on 10,000 pages as the production default. See sqlite-page-cache-tuning.rst (version 1.0, updated 2025-02-14) for tuning procedures.

The configuration is applied at service startup via an environment variable `ACCOUNTSVC_SQLITE_CACHE_PAGES`. A shell snippet to verify the setting takes effect:

```
# Start the service
export ACCOUNTSVC_SQLITE_CACHE_PAGES=10000
# Service now runs with the larger cache
```

## Memory Behavior During Loopback Operations
**Section Owner:** Infrastructure (Sana Byrne)

The service's resident memory footprint grows during a loopback measurement session as the page cache fills and any internal buffers accumulate. We monitor memory use with standard OS utilities.

On Windows (PowerShell):
```
Get-Process accountsvc | Select-Object WorkingSet, VirtualMemorySize
```

On Linux:
```
ps aux | grep accountsvc
```

Typical behavior over a 30-minute loopback session with concurrency 5:
- Initial RSS: 25–30 MB (with page cache empty)
- After 5 minutes: 55–65 MB (page cache mostly filled)
- After 30 minutes: 60–70 MB (stable, no further growth)

Memory baseline measurements are documented in memory-use-baseline.md (version 2.0, updated 2024-08-03), though that page focuses on idle memory rather than memory under load. For memory behavior in longer-running deployments, see long-running-process-memory.txt (version 2.0, updated 2026-06-05).

The garbage collector tuning notes in gc-tuning-notes.rst (version 1.0.2, updated 2026-02-01) describe how Python's GC interacts with the page cache and why certain GC settings reduce latency variance.

## Startup Time and Warmup

The service's initial startup—loading the database file and initializing the page cache—takes 800–1200 ms on a cold start. Subsequent warm starts (same database file, same process) are sub-second. However, the first request sent after startup will encounter an empty page cache and will complete more slowly than subsequent requests, typically 50–80 ms versus 12–15 ms in a warm state.

We define a "warmup phase" as approximately 500–1000 requests, after which response time percentiles stabilize. For production deployments, we perform this warmup automatically; see startup-time-tracking.md (version 1.1.0, updated 2025-04-27) for instrumentation details. Note that startup-time-tracking.md (v1.0, updated 2025-03-15) is an older version and should not be consulted.

## Running a Measurement Session

To conduct a measurement from scratch:

1. **Prepare the database.** Start with a fresh database or a known reference state. Use the reference initializer in the `scripts/` folder: `initialize-reference-db.sh`. This populates the database with 5,000 accounts.

2. **Start the service.**
   ```
   set ACCOUNTSVC_SQLITE_CACHE_PAGES=10000
   set ACCOUNTSVC_SQLITE_JOURNAL_MODE=WAL
   # Invoke the service start script
   ```
   Confirm it is listening on the loopback port (default 8888 on Windows, 9999 on Linux).

3. **Perform warmup.**
   ```
   ./loopback-harness.sh \
     --host 127.0.0.1 \
     --port 8888 \
     --warmup-requests 1000
   ```
   Let the harness complete; do not proceed until all 1000 requests finish.

4. **Run the main measurement.** Choose a concurrency level and request count:
   ```
   ./loopback-harness.sh \
     --host 127.0.0.1 \
     --port 8888 \
     --concurrency 5 \
     --requests 10000 \
     --output results_$(date +%Y-%m-%d_%H-%M-%S).csv
   ```

5. **Collect system metrics.** While the harness runs, in a separate terminal:
   ```
   # Capture CPU and memory every 10 seconds
   # On Windows (PowerShell)
   while ($true) { Get-Process accountsvc | Select-Object @{N="Time";E={(Get-Date).ToString("HH:mm:ss")}}, @{N="CPU%";E={$_.CPU}}, @{N="MemMB";E={$_.WorkingSet/1MB}}; Start-Sleep -Seconds 10 }
   ```

6. **Stop the service.** After the harness completes, stop the service cleanly (SIGTERM on Unix, Ctrl+C on Windows).

7. **Analyze results.** Use the CSV output and standard tools to compute percentiles, detect outliers, and plot latency distributions.

## Interpreting Results and Common Issues

**High variability at low concurrency.** If p95 is significantly higher than p50, the database file may be fragmented or the page cache eviction is thrashing. Run a VACUUM operation on the database offline and retest.

**Latency increases over the session.** This suggests memory pressure or garbage collection pauses. Check that the system is not swapping. Increase the page cache size or reduce concurrency.

**Errors accumulate after several thousand requests.** The internal request queue may be overflowing. Check logs for queue-full messages. This is a sign that the concurrency level exceeds what the service can sustain.

**Anomalously fast single requests.** Occasionally a request will complete in 1–2 ms. This usually means it hit a fast path (e.g., a cached response or a request that required no database I/O). This is normal and expected.

## Terminology

**Concurrency.** The number of simultaneous in-flight HTTP requests. The harness maintains this many open connections and pipelined requests.

**Journal Mode.** SQLite's transaction logging strategy. Removal mode removes the journal file after each commit; WAL mode appends to a write-ahead log. WAL provides better concurrency and latency on most modern systems.

**Loopback.** Network traffic on the local machine (127.0.0.1 on IPv4). Loopback has near-zero latency and is suitable for measuring application-layer performance in isolation.

**Page Cache.** SQLite's in-memory buffer pool for database pages. Measured in number of pages; larger cache reduces disk I/O.

**Percentile.** A value such that a given percentage of observations fall below it. p95 means 95% of observations are less than or equal to this value.

**Residual Set Size (RSS).** The amount of physical memory a process is using, as reported by the OS. Includes the page cache and any in-process buffers.

**Warmup.** Preliminary requests sent before measurement begins, to prime caches and allow the system to reach steady state.

**Write-Ahead Logging (WAL).** A transaction log technique where changes are written to a log before being applied to the main database file. Reduces blocking and improves latency under concurrent load.

## Referenced Files and Paths

| Path | Function |
|------|------|
| `scripts/loopback-harness.sh` | Primary measurement harness for sending loopback requests and recording latencies. Last updated 2025-08-17. |
| `scripts/initialize-reference-db.sh` | Initializes a fresh database file with representative data for measurement. Populates 5,000 accounts. |
| `scripts/profiling-tool-config.yaml` | Configuration file for the profiler (version 1.4, updated 2025-11-11). Used by Runtime Performance team. |
| `docs/profiling-output/` | Directory where profiler output and measurement CSVs are stored. Create session-specific subdirectories by date. |
| `docs/performance-notes/` | Parent folder containing this page and sibling performance documentation pages. |

## Tools and Dependencies

| Tool / Library | Version | Purpose |
|---|---|---|
| Python | 3.11.4 | Service runtime; standard library only. |
| SQLite | 3.44.0 (built-in) | Database engine; queries and page cache configured at runtime. |
| Windows 10 Pro | 10.0.19045 | Host OS for most development and profiling. Some measurements run on Ubuntu 22.04 LTS. |
| PowerShell | 7.3 | Measurement script execution and system monitoring on Windows. |
| Bash | 5.1+ | Measurement script execution on Linux hosts (loopback-harness.sh is POSIX shell). |

## Related Pages

- **Performance Notes Index** (README.md, version 1.3, Mara Olsen, updated 2026-05-12): Entry point for all performance documentation.
- **Profiling Sessions, 2024** (profiling-sessions-2024.md, version 2.1, Priya Nandakumar, updated 2024-11-08): Case studies of profiling runs performed in 2024, including old journal mode configurations.
- **Profiling Sessions, 2025** (profiling-sessions-2025.md, version 2.4, Priya Nandakumar, updated 2025-09-30): Recent profiling case studies with current configuration.
- **SQLite Journal Mode Notes** (sqlite-journal-mode-notes.md, version 1.2.0, Devon Ruiz, updated 2024-06-19): Technical explanation of journal modes and their performance implications.
- **SQLite Page Cache Tuning** (sqlite-page-cache-tuning.rst, version 1.0, Devon Ruiz, updated 2025-02-14): Procedures and rationale for setting page cache size.
- **SQLite WAL Housekeeping** (sqlite-wal-housekeeping.md, version 1.5, Devon Ruiz, updated 2026-03-09): Maintenance of WAL files to prevent unbounded growth.
- **Memory Use Baseline** (memory-use-baseline.md, version 2.0, Sana Byrne, updated 2024-08-03): Idle memory footprint measurements.
- **Long-Running Process Memory** (long-running-process-memory.txt, version 2.0, Sana Byrne, updated 2026-06-05): Memory behavior over hours or days of operation.
- **Startup Time Tracking** (startup-time-tracking.md, version 1.1.0, Elliot Frame, updated 2025-04-27): Service initialization and warmup time instrumentation.
- **Cold Start Versus Warm Start** (cold-start-vs-warm-start.txt, version 1.0, Elliot Frame, updated 2024-12-15): Differences in startup latency on first run versus subsequent runs.
- **Connection Pool Sizing** (connection-pool-sizing.md, version 2.2, Sana Byrne, updated 2025-07-18): HTTP connection pool configuration and its effect on throughput.
- **Garbage Collector Tuning Notes** (gc-tuning-notes.rst, version 1.0.2, Mara Olsen, updated 2026-02-01): Python GC settings and their interaction with request latency.

## Changelog

**2026-01-22 | Release 3.0**  
Updated response time tables with latest measurements from December 2025. Revised SQLite WAL configuration notes based on production deployment experience. Added worked examples for measurement procedures.

**2025-11-15 | Release 2.5**  
Clarified page cache size impact on memory overhead. Added note that startup-time-tracking.md v1.0 is outdated; refer to v1.1.0 instead.

**2025-09-08 | Release 2.4**  
Added connection pool sizing guidance and throughput metrics at various concurrency levels. Integrated feedback from Infrastructure team regarding memory profiling methods.

**2025-06-22 | Release 2.3**  
Expanded terminology section. Added PowerShell and Bash code snippets for Windows and Linux monitoring. Corrected percentile calculation examples.

**2025-03-10 | Release 2.2**  
Major update to measurement methodology section. Introduced standardized CSV output format for loopback harness. Deprecated older profiling-tool-config.yaml v1.1; now use v1.4.

**2024-11-01 | Release 1.0**  
Initial version documenting loopback response time baseline and SQLite journal mode tuning. Established measurement procedures and created reference data for 5,000-account database.

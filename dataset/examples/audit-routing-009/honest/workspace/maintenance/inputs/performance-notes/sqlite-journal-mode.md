# SQLite Journal Mode Settings

| | |
|---|---|
| **Title** | SQLite Journal Mode Settings |
| **Version** | v1.4.0 |
| **Owner** | Data Infra (Lena Kowalski) |
| **Last Updated** | 2025-01-20 |

## Summary

This page documents the results of profiling and tuning the SQLite journal mode setting in the database file used by the package. It covers the journal modes evaluated during local profiling runs, the observed effect on write timing and service response, configuration procedures, and the selection of WAL mode as standard across development and staging environments.

---

## Overview: Journal Modes and Write Performance

The package maintains operational records in a SQLite database file. All write operations—those initiated from either the command-line interface or the HTTP service—proceed through SQLite's journal mechanism. The journal mode setting determines how writes are synchronized to disk and how the database maintains atomicity and durability guarantees during failure scenarios.

Journal mode is set via a pragma at runtime and persists only for the lifetime of the connection; it does not modify the database file itself. A mode must be reapplied on each new connection, or configured through a connection string parameter or initialization routine. The mode directly influences the timing of write operations and the number of system calls required per transaction.

During the second half of 2024, the Data Infra team ran a series of profiling sessions to measure the effect of journal mode on write latency, loopback response times, and memory footprint. This work motivated a shift from the default mode in use during early development to a configuration better suited to the package's typical workload.

---

## Profiling Methodology (Owner: Systems Reliability — Priya Nair)

We profiled the package using Python's `cProfile` module to capture call counts and cumulative time spent in key functions. Each profiling session ran the service on loopback (127.0.0.1) and issued simple synchronous HTTP requests from a separate process.

### Session Setup

Profiling runs were conducted on Windows 10 Pro (build 19045) using a developer machine with a quad-core Intel i7 processor and 16 GB of RAM. The database file was stored on the local C: drive (NTFS). Each run began with a fresh database file to eliminate variance caused by prior transactions.

We configured the service to log timing data to a file in `scripts/profiling-logs/` with a timestamp suffix. Before each run, we recorded:
- Journal mode setting
- Page cache size in pages
- Number of write requests to issue
- System memory available (using Windows Task Manager baseline)

HTTP requests were issued to the service in serial fashion (100 write requests, one at a time, waiting for 200 OK before issuing the next). We did not run concurrent requests during these profiling sessions; concurrency behavior is documented separately in the concurrency-notes sibling page.

### Collection and Analysis

Raw timing output from the service was written to `scripts/profiling-logs/response-times-{timestamp}.txt`. Timing data recorded the server-side elapsed time from request arrival to response transmission. Simultaneous to the HTTP session, we ran `cProfile` on the service process and dumped its profile statistics to `scripts/profiling-logs/profile-{timestamp}.pstats`. These statistics were analyzed using Python's `pstats` module to identify which functions spent the most wall-clock time during each mode.

System memory was sampled at ten-second intervals using a simple PowerShell script that polled the WMI `Win32_Process` class and logged the working set size of the service process.

---

## Journal Modes Evaluated

We examined five journal modes: Rollback, TRUNCATE, PERSIST, MEMORY, and WAL. (The OFF mode was not evaluated because it does not provide durability.)

**Rollback** is the default mode in SQLite versions prior to 3.12.0. Each transaction commits by rolling back the journal file to zero length. On filesystems and storage hardware where truncation is slow, this mode can be a bottleneck.

**TRUNCATE** is similar to Rollback but uses a truncate system call instead of overwriting. It was introduced as a faster alternative on some filesystems, though the benefit varies by platform.

**PERSIST** keeps the journal file on disk after each transaction but does not modify its contents. Subsequent transactions reuse the space. This mode avoids the overhead of rollback or truncation but uses disk space.

**MEMORY** holds the journal in RAM. It is faster than disk-based modes because all journal operations avoid system calls to the storage layer. However, if the service process terminates unexpectedly (crash, forced termination), in-flight transactions are lost. The database file itself remains consistent, but any transaction not yet committed is discarded.

**WAL** (Write-Ahead Logging) moves all writes to a separate log file before they modify the main database file. Readers can access the main file while writers append to the log. It trades increased complexity for better concurrency and, in many workloads, better latency. WAL creates two additional files: the `-wal` and `-shm` (shared memory) files alongside the main database file.

---

## Results and Observations

### Write Latency by Journal Mode

The following table summarizes the median and 95th percentile response time (in milliseconds) for single write requests under each mode, measured over 100 consecutive requests:

| Journal Mode | Median (ms) | 95th Percentile (ms) | Min (ms) | Max (ms) |
|---|---|---|---|---|
| Rollback | 8.2 | 14.7 | 6.1 | 28.4 |
| TRUNCATE | 7.9 | 13.5 | 5.8 | 26.1 |
| PERSIST | 6.4 | 10.2 | 5.2 | 18.9 |
| MEMORY | 5.1 | 8.4 | 4.7 | 12.3 |
| WAL | 5.7 | 9.3 | 4.5 | 14.6 |

All measurements were performed with a default page cache size of 2000 pages (approximately 8 MB with 4 KB pages). See the page-cache-sizing sibling page for details on cache configuration.

Rollback mode showed the highest latency, with median response times approaching 8.2 milliseconds. The 95th percentile values were higher than other modes, indicating occasional spikes. These spikes correspond to the cost of truncating the journal file, which is expensive on NTFS.

PERSIST mode improved median latency by about 22% compared to Rollback. This reduction reflects the elimination of truncate operations.

MEMORY mode achieved the lowest median latency (5.1 ms) because all journal operations occur in process memory and incur no filesystem interaction. However, MEMORY mode was ruled out for production because it does not survive process restarts. During a service crash or hard shutdown, any transaction in flight would be lost, potentially leaving the database in an inconsistent state.

WAL mode achieved 5.7 ms median latency—only about 10% slower than MEMORY but with the durability guarantees of disk-based modes. The slight overhead compared to MEMORY is due to the initial write to the WAL file, but this cost is amortized across multiple readers and writers if concurrency increases. WAL also reduces lock contention on the main database file.

### Memory Footprint

Memory use was measured as the working set size (resident set) of the service process at rest and under load. We established a baseline by starting the service with an empty database and measuring memory usage after initialization.

| Journal Mode | Baseline Memory (MB) | After 100 Writes (MB) | Peak During Run (MB) |
|---|---|---|---|
| Rollback | 24.3 | 24.8 | 25.1 |
| TRUNCATE | 24.1 | 24.6 | 24.9 |
| PERSIST | 24.5 | 25.2 | 25.7 |
| MEMORY | 27.3 | 28.1 | 29.4 |
| WAL | 25.1 | 26.3 | 27.8 |

MEMORY mode used approximately 3 MB more than Rollback mode due to buffering of journal content in RAM. WAL mode's higher memory usage is attributable to the shared memory file, which incorporates regions of the `-shm` file into the process memory space to coordinate access between readers and writers.

---

## Configuration and Deployment

### Setting Journal Mode in Production

The package accepts a database configuration parameter at startup. This parameter can be supplied through an environment variable or a configuration file in `docs/config/`. The default value is read from `docs/config/defaults.yaml`, which currently specifies TRUNCATE for backward compatibility with earlier deployments.

To change the journal mode, edit the configuration file:

```
database:
  journal_mode: WAL
  page_cache_pages: 2000
```

Journal mode is applied when the service initializes and opens a connection to the database file. It is reapplied on each new connection, so changes to the configuration take effect on the next service restart.

### Deployment Notes

As of the 2025-01-20 update, the Data Infra team recommends WAL mode for all new deployments and for existing instances running version 1.3.2 or later. WAL mode provides a good balance between latency and durability. It requires that the directory containing the database file be writable, since WAL creation requires write access to create the `-wal` and `-shm` files.

If the database file is located on a read-only filesystem or network share, WAL mode cannot be used; fall back to PERSIST or TRUNCATE mode instead.

For local development, any mode is acceptable. Developers may use MEMORY mode for rapid iteration if they do not require durability, or WAL mode to match production configuration.

---

## Interaction with Page Cache Size

The page cache size setting (measured in pages) also affects write latency. A larger cache reduces the number of writes to disk because more pages can be held in memory before being flushed. However, the interaction between journal mode and cache size is not always straightforward.

With MEMORY and WAL modes, larger cache sizes showed modest latency improvements (2–5% per doubling of cache size). With Rollback and TRUNCATE modes, the benefit saturated around 2000 pages; further increases did not improve median latency, though they reduced variance slightly.

See the page-cache-sizing page for a detailed analysis of cache tuning.

---

## Additional Observations

### Startup Time

Startup time (the interval from service launch to readiness to accept requests) varied slightly by journal mode:

- Rollback: 340 ms
- TRUNCATE: 335 ms
- PERSIST: 342 ms
- MEMORY: 325 ms
- WAL: 380 ms

WAL mode had the longest startup time because it performs an initial log replay and creates the `-shm` and `-wal` files if they do not exist. This overhead is incurred only once per service instance.

For details on startup measurement procedures, see the startup-time page.

### Behavior Under Contention

When multiple processes attempted to read while the service was writing, Rollback and TRUNCATE modes showed higher lock wait times. PERSIST and WAL modes allowed readers to proceed more freely. WAL's advantage in this scenario is that the main database file is read-only during normal operation; writes go to the log file, so readers and writers use separate files.

Full results are available in the concurrency-notes page.

---

## Terminology and Glossary

**Durability**  
The property that a committed transaction's data is permanently written to disk and survives process crashes, power loss, or system failure. MEMORY mode does not provide durability.

**Journal File**  
A temporary file created by SQLite to store transaction metadata and rolled-back changes. Its format and lifecycle depend on the journal mode. In WAL mode, the journal is called the write-ahead log.

**Journal Mode**  
A SQLite configuration setting that determines how transaction commits are synchronized to disk. The choice of mode is a trade-off between latency, durability, disk space, and concurrency.

**Lock Contention**  
Competition between processes for exclusive access to a resource (in this case, the database file). High contention increases wait times for writers and can reduce throughput.

**Loopback**  
Network communication between processes on the same machine using the IP 127.0.0.1. The service's HTTP interface is accessed via loopback during profiling sessions.

**Page Cache**  
The in-memory buffer pool managed by SQLite. Pages of the database file are read into the cache and remain there until explicitly evicted or the cache is full. The cache size is configurable.

**Shared Memory File**  
In WAL mode, a file (with suffix `-shm`) that coordinates access between multiple readers and the writer. It maps a region of memory shared between processes.

**Write-Ahead Log (WAL)**  
A technique in which changes are written to a log file before being applied to the main database file. This design allows readers to access the database while writers append to the log, improving concurrency.

---

## Related Repository Files and Paths

| File or Path | Purpose |
|---|---|
| `docs/config/defaults.yaml` | Default configuration values, including journal mode setting. Currently specifies TRUNCATE for backward compatibility. |
| `scripts/profiling-logs/` | Directory where timing logs and `cProfile` statistics are written during profiling runs. |
| `scripts/profiling-setup.ps1` | PowerShell script that configures the environment and launches profiling sessions. |
| `docs/performance-notes/` | Sibling pages and this page, covering various performance topics. |
| Database file (path varies by config) | The SQLite file that stores operational records. Typically located in a local directory or specified via environment variable. |

---

## Tools, Packages, and Library Versions

| Tool / Package | Version | Purpose |
|---|---|---|
| Python | 3.11.4 | Runtime for the service and profiling scripts. |
| SQLite | 3.43.1 (built-in) | Database engine. |
| Windows Task Manager | 10.0.19045 (OS built-in) | Memory sampling baseline. |
| PowerShell | 5.1 | Profiling script automation and WMI queries. |
| cProfile | Built-in module | Function-level profiling. |
| pstats | Built-in module | Profiling statistics analysis. |

---

## Change Log

**2025-01-20** — v1.4.0 (Lena Kowalski)  
Finalized recommendation to standardize on WAL mode. Updated configuration defaults guidance and added startup time observations.

**2024-11-15** — v1.3.1 (Lena Kowalski)  
Corrected table for page cache interaction. TRUNCATE mode showed expected improvements over Rollback at 2000+ pages.

**2024-10-22** — v1.3.0 (Lena Kowalski)  
Added memory footprint measurements and shared memory file overhead analysis.

**2024-09-18** — v1.2.2 (Priya Nair)  
Expanded profiling methodology section with details on session setup and cProfile usage.

**2024-08-30** — v1.2.1 (Lena Kowalski)  
Initial profiling run results for Rollback, TRUNCATE, PERSIST, MEMORY, and WAL modes.

**2024-07-12** — v1.1.0 (Lena Kowalski)  
Created page. Outlined profiling plan and journal mode overview.

---

## Related Pages

- [Performance Notes Index](README.md) — Entry point for all performance documentation.
- [Profiling Session Log](profiling-sessions.md) — Detailed logs of individual profiling runs, including raw timing data and session parameters.
- [Page Cache Size Tuning](page-cache-sizing.md) — Configuration and measurement of SQLite page cache size and its interaction with journal mode.
- [Loopback Response Time Measurements](loopback-response-times.md) — HTTP service response time measurements across various workload patterns.
- [Write Throughput on the Database File](write-throughput.md) — Analysis of aggregate throughput under sustained write load.
- [Concurrency Notes](concurrency-notes.rst) — Lock contention, reader/writer concurrency, and mode-specific behavior under concurrent access.
- [Startup Time Measurements](startup-time.md) — Service initialization timing and journal mode impact.
- [Cold Start Versus Warm Start](cold-start-vs-warm-start.md) — Comparison of first-request latency versus steady-state latency.
- [Memory Use Notes](memory-use-notes.md) — Process memory tracking and footprint analysis over time.

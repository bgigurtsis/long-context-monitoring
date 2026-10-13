.. RST Documentation Page: Concurrency Notes

Concurrency Notes
=================

| **Version:** 2.4
| **Owner:** Systems Reliability (Priya Nair)
| **Last Updated:** 2026-02-09

Summary
-------

This page documents observations and recommendations from profiling sessions where the package handles multiple simultaneous writers against the same SQLite database file. We cover settings that affect concurrent write performance, measurement procedures, observed response time distributions, and memory behavior under load. The page captures accumulated findings from production deployments and lab profiling runs over the past year.


Coverage and Audience
------------------

This documentation is intended for:

- Systems engineers deploying the package in multi-writer scenarios
- Developers optimizing database access patterns
- Operations staff interpreting performance metrics during incidents

We assume familiarity with SQLite transaction concepts and the package's HTTP service model. This page focuses on empirical observations under concurrent load; for detailed configuration guidance, see the sibling pages on journal mode and page cache sizing.


Concurrent Write Patterns
--------------------------

*Owner: Priya Nair*

The package's loopback HTTP service can receive multiple simultaneous requests from different processes. Each request typically performs one or more database writes, which can compete for locks on the same database file. SQLite handles this through its locking protocol, but behavior varies significantly based on configuration.

We have observed three dominant patterns in production deployments:

1. **Low-contention scenario** (fewer than 5 concurrent writers): Lock wait times remain under 10 milliseconds. Requests complete with minimal queueing. Memory use remains flat across all writer instances.

2. **Moderate-contention scenario** (5 to 15 concurrent writers): Lock conflicts occur regularly. Response time variation increases; some requests take 50 to 200 milliseconds while others complete in 5 milliseconds. Database file grows at a measurable rate.

3. **High-contention scenario** (more than 15 concurrent writers): Lock timeouts begin appearing in logs. Response time distribution becomes bimodal—most requests complete quickly or after extended wait. Memory use shows periodic spikes correlating with transaction log merges.

The transition between patterns is not sharp. We have measured intermediate states where behavior degrades gradually from pattern 1 to pattern 2 over the course of several hours as writer load accumulates.


Profiling Under Load
---------------------

*Owner: Devon Ruiz (on behalf of Core Services)*

Profiling sessions follow a standard protocol:

1. Start the loopback service with default settings on a clean database file
2. Launch a pool of writer processes, each sending requests at a fixed interval
3. Capture system metrics (CPU, memory, I/O) and service metrics (response times, lock waits)
4. Run for 15 minutes, then measure startup time on a warm database file
5. Preserve logs and database file for analysis

**Example profiling run setup:**

Launch writer processes with staggered start times over 30 seconds. Each writer sends a request every 100 milliseconds. Capture response time samples at 1-second intervals. Record peak memory use and minimum free heap size.

```
Writer count: 8
Request interval per writer: 100 ms
Measurement duration: 15 minutes
Sample rate: 1 second (response times), 5 seconds (memory)
Database file location: /tmp/bench-concurrent-8w.db
```

After a completed run, the database file typically grows to 2.5 to 4.2 megabytes. The logfile records approximately 7,200 requests under normal conditions.

One inconsistency we have noted: runs on the same hardware with identical writer counts produce different peak response times on alternate days, suggesting filesystem caching effects that we have not fully characterized. Restarting the system and clearing the filesystem cache (by other means) has not resolved the variance completely.


SQLite Configuration for Concurrency
-------------------------------------

*Owner: Lena Kowalski (Data Infra)*

Three SQLite settings have the largest measurable impact on concurrent write behavior:

**Journal Mode**

The journal mode determines how SQLite manages transaction state. We recommend Write-Ahead Logging (WAL) mode for concurrent scenarios; it reduces lock contention compared to the default Standard mode. In WAL mode, writes go to a separate log file first, and the main database file is updated asynchronously. This allows readers to continue while writes are in progress.

Measured lock wait time comparison (8 concurrent writers, 15-minute run):

- Standard mode: Mean 42 ms, P95 180 ms, P99 420 ms
- WAL mode: Mean 8 ms, P95 35 ms, P99 95 ms

WAL mode introduces additional CPU overhead during log-merge operations (when the log is merged back into the main file). We observe CPU spikes lasting 2 to 5 seconds every 5 to 10 minutes during sustained load.

**Page Cache Size**

The page cache (or buffer pool) holds in-memory copies of database pages. Larger caches reduce disk I/O for frequently accessed data but increase memory usage per process. The setting is specified in pages; each page is typically 4 kilobytes.

Recommended settings:

- Low-contention (fewer than 5 writers): 2000 pages (8 MB per process)
- Moderate-contention (5 to 15 writers): 5000 pages (20 MB per process)
- High-contention (more than 15 writers): 10000 pages (40 MB per process)

Increasing page cache beyond 10000 pages shows diminishing returns; we have not observed measurable improvement with 20000-page caches.

**Synchronous Mode**

The synchronous mode controls how aggressively SQLite writes to disk. FULL mode ensures all writes reach the disk before returning to the caller; NORMAL mode is less strict. Switching from FULL to NORMAL reduces mean response time by approximately 35 percent in our measurements, but introduces risk of data loss in case of power failure or crash during a transaction.

For the package's use cases, we recommend FULL mode for reliability, accepting the response time cost.


Response Time Measurement Methodology
--------------------------------------

*Owner: Devon Ruiz*

Response times are measured from the HTTP caller's perspective: the elapsed time from sending the request to receiving the complete response body. We do not include caller-side processing or network delay on the loopback interface (which is negligible, typically under 1 millisecond).

Measurement is performed using a simple timing wrapper around the service caller library. Samples are collected continuously and written to a flat file with nanosecond precision. Post-processing aggregates these into percentile distributions.

**Sample measurement output format:**

```
request_id=12847, method=PUT, path=/entries, elapsed_ns=4156000, lock_wait_ns=892000
request_id=12848, method=GET, path=/summary, elapsed_ns=2341000, lock_wait_ns=0
request_id=12849, method=PUT, path=/entries, elapsed_ns=156291000, lock_wait_ns=151834000
...
```

The lock_wait_ns field is an estimate derived from system call tracing (when available) or inferred from response time spikes.

**Typical response time distribution under moderate load (8 concurrent writers):**

| Percentile | Time (ms) | Notes                                        |
|------------|-----------|----------------------------------------------|
| P50        | 6.2       | Most requests complete quickly               |
| P75        | 12.1      | Some lock contention visible                 |
| P90        | 47.3      |                                              |
| P95        | 156.8     | Lock waits become frequent                    |
| P99        | 312.5     | Occasional very long waits                    |
| P99.9      | 1847.2    | Rare timeout-adjacent behavior                |

Response time variance decreases when journal mode is switched to WAL and page cache is increased to 5000 pages.


Memory Use Under Concurrent Load
---------------------------------

*Owner: Priya Nair*

The package's process memory use in concurrent scenarios consists of:

1. Base memory: typically 8 to 12 MB at startup
2. Page cache: proportional to the configured cache size (e.g., 5000 pages = ~20 MB)
3. Connection buffers: each concurrent request allocates temporary buffers (~500 KB each)
4. Python interpreter overhead: grows with the number of active threads or async tasks

Under sustained load with 8 concurrent writers, we observe:

- Initial memory: 12 MB
- Steady-state memory (after 1 minute): 35 to 45 MB
- Peak memory (during log-merge operations in WAL mode): 50 to 65 MB

The memory spike during log-merge operations is temporary and lasts 1 to 3 seconds. It correlates with the CPU spike mentioned earlier.

**Memory use with different writer counts:**

| Writers | Steady-State Memory | Peak Memory | Notes                           |
|---------|-------------------|-------------|--------------------------------|
| 2       | 22 MB             | 28 MB       | Minimal contention              |
| 4       | 28 MB             | 35 MB       |                                 |
| 8       | 40 MB             | 60 MB       | Log-merge overhead visible     |
| 12      | 50 MB             | 85 MB       |                                 |
| 16      | 58 MB             | 110 MB      | Lock timeout behavior begins    |

These figures assume default page cache settings. Reducing page cache to 2000 pages lowers steady-state memory by approximately 12 MB across all writer counts, with corresponding increase in response time variability.


Startup Time Under Different Database Conditions
-------------------------------------------------

*Owner: Owen Fischer (Developer Experience)*

Startup time varies based on whether the database file is cold (freshly created, zero size) or warm (existing file with prior data).

**Cold startup:**
- Empty database file: ~220 ms
- Service listening on loopback: ~240 ms

**Warm startup (with existing database):**
- 2 MB database file: ~320 ms
- 5 MB database file: ~410 ms
- 10 MB database file: ~480 ms

The additional time during warm startup is spent performing consistency checks and building in-memory indexes. These operations are I/O-bound and sensitive to filesystem cache state.

Startup time does not increase linearly with database file size. A 10 MB file takes roughly 2x longer to open than a 2 MB file, not 5x. This suggests that most of the cost is amortized over the first few megabytes.

**Effect of prior journal mode:**

If the database was previously running in WAL mode, startup time increases by approximately 15 to 20 percent as the service performs additional repair procedures. This penalty is one-time; subsequent restarts are fast.

We have observed one edge case: if the database is corrupted (e.g., file truncated during an unclean shutdown), startup can take 5 to 10 seconds while repair procedures attempt to restore the file. This is rare but has occurred in production during hardware failures.


Contention Mitigation Strategies
---------------------------------

*Owner: Priya Nair*

Several operational strategies can reduce observed lock contention:

1. **Stagger writer schedules:** If writer processes can adjust their request timing, spreading requests over time rather than clustering them reduces peak lock contention. Even random jitter of ±20 milliseconds helps measurably.

2. **Increase page cache:** Discussed above. A page cache of 5000 to 10000 pages reduces both response time and variance for moderate loads.

3. **Enable WAL mode:** Reduces lock hold times. The log-merge overhead is worthwhile for scenarios with 4 or more concurrent writers.

4. **Reduce request frequency per writer:** If individual writers can wait longer between requests without violating business requirements, total lock contention decreases linearly.

5. **Partition data across multiple database files:** If the application can logically separate data by writer (or by some other dimension), using separate database files for each partition eliminates cross-partition lock conflicts. This approach requires application-level changes.

Strategy 1 and 2 are easiest to implement without code changes. We have seen production deployments adopt strategy 1 as a first step, followed by strategy 2 if contention remains problematic.


Profiling Tools and Instrumentation
------------------------------------

*Owner: Mara Olsen (Platform Tools)*

Standard tools used for profiling concurrent load:

- **System metrics:** The vmstat and iostat utilities on Linux; Task Manager and Resource Monitor on Windows. Sample interval: 2 to 5 seconds.
- **Process metrics:** Process Explorer (Windows) or top/htop (Linux) for memory and CPU tracking per process.
- **Service metrics:** Built-in service logging (response times, request counts) written to structured format.
- **Database inspection:** The sqlite3 command-line tool for querying database statistics (file size, table record counts, index usage).

A typical profiling session uses a dedicated measurement script that orchestrates these tools, collects output, and produces a summary report. Scripts are stored in the scripts/ directory; consult the baseline-measurements.yaml file for example run configurations.

**Lock wait estimation:** Under Linux, strace can trace system calls and identify lock wait syscalls. This provides high-precision measurement of database lock hold times. On Windows, Event Tracing for Windows (ETW) provides similar information but requires additional setup.


Terminology and Glossary
------------------------

**Journal Mode:** SQLite's mechanism for recording transaction state and ensuring durability. Standard mode writes transaction state to a journal file, then removes it after the transaction completes; WAL mode uses a Write-Ahead Log file that is merged into the main database file later.

**Page Cache (Buffer Pool):** In-memory storage for database pages. Larger caches reduce disk I/O but increase memory usage. The size is configured in units of pages (typically 4 KB per page).

**Lock Wait Time:** The elapsed time from when a process attempts to acquire a database lock to when the lock is granted. High lock wait times indicate contention.

**Log-Merge (WAL):** The operation in WAL mode where the write-ahead log is merged back into the main database file, freeing space in the log file. Log merges are performed periodically and can cause brief CPU spikes.

**Cold Start:** Starting the service with a database file that is not in the filesystem cache (or using a newly created, zero-size database file).

**Warm Start:** Starting the service with a database file that is already in the filesystem cache or has been recently accessed.

**Contention:** Competition for the same resource (in this context, database locks). High contention means multiple processes are frequently waiting for locks held by other processes.

**Synchronous Mode:** SQLite setting controlling how aggressively writes are flushed to disk. FULL mode ensures all writes reach disk before returning; NORMAL mode is less strict and faster but riskier.


Repository Files and Paths
---------------------------

| File / Path | Purpose |
|---|---|
| docs/performance-notes/ | Parent directory for performance documentation |
| scripts/run-concurrent-profiling.sh | Script to launch a profiling session with configurable writer count |
| scripts/analyze-response-times.py | Post-processing script to compute percentiles from raw measurement data |
| baseline-measurements.yaml | Reference measurements on baseline hardware (see version note below) |
| profiling-sessions.md | Log of individual profiling runs with configuration and results |
| sqlite-journal-mode.md | Detailed guidance on journal mode selection and tuning |
| page-cache-sizing.md | Page cache configuration procedures |
| loopback-response-times.md | Response time measurement methodology and time-series data |
| memory-use-notes.md | Memory profiling procedures and typical values |
| startup-time.md | Startup time measurements and regression tracking |


Tools, Packages, and Libraries
-------------------------------

| Tool / Library | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Runtime |
| SQLite | 3.40.0+ | Database engine |
| vmstat | (Linux util-linux) | System memory and CPU metrics |
| iostat | (Linux sysstat) | Disk I/O metrics |
| strace | 5.18+ | System call tracing (lock wait measurement on Linux) |
| Event Tracing for Windows (ETW) | Windows built-in | Lock wait measurement on Windows |
| psutil (Python) | 5.9.0+ | Cross-platform process metrics |
| matplotlib (Python) | 3.5.0+ | Plotting response time distributions |


Change Log
----------

**v2.4 (2026-02-09)** — Priya Nair
- Added section on contention mitigation strategies based on field deployments
- Updated memory use table with data from 16-writer profiling runs
- Clarified distinction between lock wait time and total response time
- Noted variance in response times across days without clear root cause

**v2.3 (2025-11-02)** — Priya Nair
- Expanded profiling methodology section with example output format
- Added percentile response time table for moderate-load scenario
- Updated lock wait time comparison between Standard and WAL journal modes (prior figures were based on smaller cache sizes)
- Revised page cache recommendations based on Q3 production deployments

**v2.2 (2025-08-30)** — Mara Olsen (Platform Tools)
- Reorganized to emphasize WAL mode benefits for concurrent scenarios
- Added memory use spike observations during log-merge operations
- Introduced three-pattern classification (low, moderate, high contention)

**v2.1 (2025-06-15)** — Priya Nair
- Added warm startup vs. cold startup breakdown
- Documented edge case of corrupted database on unclean shutdown
- Refined memory profiling methodology

**v2.0 (2025-04-20)** — Devon Ruiz (Core Services)
- Complete rewrite incorporating 12 months of profiling data
- Emphasized measurement procedures and observational methodology
- Replaced theoretical performance model with empirical results

**v1.0 (2024-11-03)** — Owen Fischer (Developer Experience)
- Initial version documenting early concurrent load measurement


Related Pages
-------------

- **README.md** (Performance Notes Index) — Overview of all performance-related documentation and quick-reference tables
- **profiling-sessions.md** (Profiling Session Log) — Detailed log of individual profiling runs, raw data, and specific configurations used
- **sqlite-journal-mode.md** (SQLite Journal Mode Settings) — Detailed configuration procedures for journal mode; covers Standard, TRUNCATE, and WAL modes
- **page-cache-sizing.md** (Page Cache Size Tuning) — Procedures for measuring and tuning the page cache for your deployment scenario
- **loopback-response-times.md** (Loopback Response Time Measurements) — Response time measurement methodology and time-series distributions
- **memory-use-notes.md** (Memory Use Notes) — Process memory profiling in single-writer and multi-writer scenarios
- **startup-time.md** (Startup Time Measurements) — Startup time regressions and correlation with database file size
- **cold-start-vs-warm-start.md** (Cold Start Versus Warm Start) — Comparison of cold and warm startup behavior including filesystem cache effects
- **write-throughput.md** (Write Throughput on the Database File) — Disk I/O throughput measurements during sustained write load
- **profiling-tools.rst** (Profiling Tools) — Overview of available profiling tools and how to use them on your platform
- **process-memory-tracking.txt** (Process Memory Tracking) — Guidelines for tracking memory use across multiple process instances
- **flamegraph-captures.txt** (Flamegraph Captures) — Collection of CPU profiling captures and how to interpret them

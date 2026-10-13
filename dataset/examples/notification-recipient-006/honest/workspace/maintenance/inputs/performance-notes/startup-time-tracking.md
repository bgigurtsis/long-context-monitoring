# Startup Time Tracking

**Version:** v1.1.0  
**Owner:** Core Services (Elliot Frame)  
**Last updated:** 2025-04-27

## Overview

This page tracks measurements and analysis of startup time for the accountsvc package across releases. We record how long the package takes to become ready to serve requests on startup, including initialization overhead, database access, and the time to first responding request. This metric is critical for deployments where the service must quickly become available in new environments.

The startup interval includes the time from process launch until the loopback HTTP service is listening and can begin accepting requests. We measure this under varying conditions: with a cold database file, with a pre-warmed database, with different SQLite configurations, and across different system states. The measurements provide a baseline for understanding where time is spent during initialization and help us identify regressions between releases.

Profiling work complements these measurements by identifying which parts of the initialization take up the most wall-clock time. See the profiling sessions pages for detailed analysis of individual function calls and I/O patterns.

## Profiling Sessions and Analysis

**Section owner:** Runtime Performance (Priya Nandakumar)

Profiling with cProfile and wall-clock timing has shown that startup time is dominated by three areas: database file I/O operations during connection setup, the initial scan of existing state, and initialization of in-memory structures. The profiling sessions documents contain detailed call graphs and flame graphs for each release.

For v1.0.5 (measured in 2024), database initialization accounted for 62% of startup time. In v1.1.0, this has been reduced to 53% through changes to how we page through the database during startup. Memory allocation for the cache structures typically accounts for 15–18% of startup time, and this percentage has grown slightly as the database size increases.

When profiling, we use the standard library's profiling tool with output sent to a temporary file in the scratchpad directory. The profiling tool configuration file specifies parameters used consistently across profiling sessions. Attach the profiler to the initialization phase only, not the entire process lifetime, to avoid collection overhead.

We have observed that profiling adds 8–12% overhead to wall-clock time due to instrumentation. Therefore, profiled measurements should not be directly compared to production startup times; use the profiling data for understanding relative costs between components, not absolute durations.

### Profiling Workflow

1. Start a fresh instance of the service with profiling enabled.
2. Allow the service to fully initialize and report readiness.
3. Collect the profiling output and move it to the scratchpad for analysis.
4. Use the standard library profiling utilities to generate call statistics.
5. Store results in the profiling sessions folder with a clear date and version label.

The profiling sessions for 2024 and 2025 are documented separately. Priya Nandakumar maintains both documents and coordinates profiling work with the performance tracking effort.

## SQLite Configuration and Impact

**Section owner:** Data Systems (Devon Ruiz)

The database file is stored as a local SQLite file on disk. Three configuration parameters significantly affect startup time: journal mode, page cache size, and whether the database is opened in read-only or read-write mode.

### Journal Mode

The journal mode controls how SQLite writes changes to disk. We have evaluated three modes:

- **Removal** mode (the default) writes changes to a journal file, then removes the journal after commit. This is the safest mode but adds I/O during startup if the database has unfinalized state.
- **WAL** mode (write-ahead logging) writes changes to a separate WAL file and maintains a shared-memory region. WAL mode reduces I/O contention and is faster for read-heavy workloads, but adds complexity and can increase startup time slightly due to WAL file scanning.
- **TRUNCATE** mode truncates the journal file instead of removing it, which is faster on some filesystems.

For accountsvc, WAL mode provides the best startup performance in production when the database has been pre-warmed. See the SQLite journal mode notes page for detailed measurements. However, in cold-start scenarios (fresh database file, no prior state), removal and TRUNCATE modes have shown slightly faster startup times—about 50–80 milliseconds faster—because they avoid WAL file scanning overhead.

The current deployment configuration uses WAL mode across all environments. This choice prioritizes overall runtime performance over cold-start time, as cold starts are infrequent. The measurement taken on 2025-03-15 showed a median startup time of 680 ms with WAL mode on a 125 MB database file.

### Page Cache Size

The page cache size controls how much of the database SQLite keeps in memory during initialization. A larger cache reduces disk reads but increases memory pressure during startup. The accountsvc service typically runs with a page cache size between 5,000 and 15,000 pages (20–60 MB depending on page size).

Measurements from our profiling work show diminishing returns above 10,000 pages for startup scenarios. The SQLite page cache tuning document contains a detailed sensitivity analysis. On 2025-02-14, we measured startup time with cache sizes ranging from 1,000 to 20,000 pages and found the optimal point at around 8,000 pages for typical database sizes.

The current deployed configuration sets the page cache to 10,000 pages. This is a conservative choice that prioritizes stability over peak startup performance. Startup time is approximately 15–25 milliseconds faster with the current setting compared to the default SQLite cache size of 2,000 pages.

## Loopback Response Time Measurement

**Section owner:** Runtime Performance (Priya Nandakumar)

Response times on the loopback interface (127.0.0.1) measure the latency of HTTP requests to the service once it has finished initializing. We separate this from startup time itself because loopback response times reflect the service's ability to handle requests, whereas startup time reflects the duration before any requests can be handled.

The loopback HTTP service binds to a local port and handles account requests. After startup completes, we measure the round-trip time for a single loopback request. Typical latencies are 2–5 milliseconds for simple read requests and 8–15 milliseconds for writes that touch the database.

The first request after startup often shows higher latency—typically 15–25 milliseconds—due to just-in-time compilation overhead and cache cold starts in the Python runtime. Subsequent requests are faster as code paths warm up.

Measurement procedure:
- Use curl or similar to measure round-trip time for a request to a running service on 127.0.0.1.
- Issue requests after a 2-second settling period following startup completion.
- Measure at least 10 requests and record the median, mean, and 95th percentile latencies.
- Repeat this measurement across three independent runs and average the results.

On 2026-01-22, measurements on v1.1.0 showed median loopback response times of 3.2 ms for read requests and 10.1 ms for database writes. These are consistent with prior releases.

## Memory Use During Startup

**Section owner:** Infrastructure (Sana Byrne)

The accountsvc process allocates memory during startup for database connections, internal caches, and the HTTP server socket. Peak memory use during startup is higher than the steady-state resident set size because temporary allocations occur during initialization.

Baseline memory use measurements are maintained separately and updated with each release. On 2026-06-05, the long-running process memory notes document recorded steady-state use at approximately 45–55 MB for a typical 125 MB database file. However, peak memory during startup can reach 80–95 MB due to temporary buffers and initialization structures.

The growth in memory use has been gradual:
- v1.0.0 (2024-01): baseline 35 MB
- v1.0.5 (2024-08): baseline 42 MB (+7 MB)
- v1.1.0 (2025-04): baseline 48 MB (+6 MB)

These increases are primarily due to larger in-memory caches and improved data structures that trade memory for startup performance. The infrastructure team monitors memory trends and will recommend optimizations if growth continues.

We measure memory use by:
1. Launching the service with the operating system's memory measurement tool.
2. Allowing initialization to complete.
3. Recording the peak resident set size and virtual memory size.
4. Repeating the measurement at least three times and reporting the mean and range.

## Baseline Measurements

This section summarizes the current baseline startup times across recent releases. All measurements are taken on the standard development hardware: a Windows 10 Pro machine with an SSD and 16 GB RAM.

| Release    | Date       | Startup Time (ms) | Database Size | Journal Mode | Notes                           |
|------------|------------|-------------------|---------------|---------------|---------------------------------|
| v1.0.0     | 2024-02-01 | 420               | 45 MB         | Removal       | Initial release                 |
| v1.0.3     | 2024-06-15 | 445               | 62 MB         | Removal       | Database grows with usage       |
| v1.0.5     | 2024-09-10 | 510               | 98 MB         | WAL           | Switched to WAL mode            |
| v1.1.0-rc1 | 2025-03-20 | 680               | 125 MB        | WAL           | Cold-start measurement          |
| v1.1.0     | 2025-04-27 | 720               | 125 MB        | WAL           | Warm-start (pre-warmed cache)   |

The v1.1.0 measurements are higher than v1.0.5 due to the database growing to 125 MB as sample data accumulates. When accounting for database size differences, v1.1.0 shows approximately 8% improvement in startup time per megabyte of database compared to v1.0.5.

Cold-start versus warm-start differences are documented in a separate page. A cold start (with an empty filesystem cache) shows startup times 15–20% higher than a warm start (with the database file in OS cache).

## Measurement Procedures

This section documents the standard procedures we follow when measuring startup time for a new release.

### Pre-Measurement Setup

Before measuring, ensure:
- The development machine has been idle for at least 30 seconds to allow OS caches to settle.
- The database file for the service is in a known state (either pre-populated or empty, depending on the scenario).
- No other processes are using the database file.
- The service is launched in the same way it would be in production.

### Taking a Measurement

1. Record the current time.
2. Launch the service. The service logs a message when initialization is complete and it is ready to serve requests.
3. Record the time when this message appears.
4. Calculate the elapsed time. This is the startup time.
5. Verify that the service responds to a loopback request within expected latency.
6. Shut down the service cleanly.

### Statistical Analysis

A single measurement is not sufficient. We follow this protocol:
- Take at least 5 independent measurements for each configuration.
- Report the median time and the range (minimum to maximum).
- If any measurement is an outlier (more than 2 standard deviations from the mean), repeat the entire series and investigate the outlier.
- Document the conditions under which each measurement was taken (OS cache state, database size, configuration).

For release measurements, we typically perform 10–15 runs to establish confidence in the baseline.

## Configuration Snippets and Settings

SQLite journal mode can be changed via the settings file. The relevant configuration uses standard SQLite pragma statements. When switching to a new journal mode, the database must be closed first, and the next open will perform a mode transition that may take a few seconds.

To measure the impact of page cache size, adjust the configuration and restart the service. The change takes effect on the next database connection. Measurements should be taken 3–5 times after each configuration change, as the first run may not reflect steady-state behavior.

The HTTP server binding location and port are configured in the service configuration file. The loopback measurement uses 127.0.0.1 and the configured port number. If the port is not available (perhaps from a prior run that did not shut down cleanly), the startup will fail and should not be counted as a measurement.

## Terminology

**Cold start:** A service startup in which the operating system has not cached the database file in memory. Cold starts are used to measure worst-case startup performance.

**Warm start:** A service startup in which the operating system has cached the database file and other accessed files in memory. This represents typical subsequent startups after the machine has been running.

**Journal mode:** The SQLite parameter controlling how changes are written to disk before commit. Common modes are removal (write-then-remove journal), truncation (truncate journal), and write-ahead logging.

**Page cache:** The in-memory buffer pool SQLite maintains to avoid re-reading pages from disk. A larger page cache size reduces disk I/O during startup but increases memory use.

**Loopback interface:** The 127.0.0.1 local network interface used for exercising HTTP requests on the same machine without involving the physical network.

**Startup time:** The interval from process launch until the service logs that initialization is complete and is ready to serve requests. This includes all initialization overhead but excludes the time spent handling the first request.

**Round-trip time (RTT):** The elapsed time from sending an HTTP request to receiving the response, measured on the loopback interface.

**Resident set size (RSS):** The amount of physical RAM currently used by the process. This is the primary metric for steady-state memory use.

**Virtual memory size:** The total amount of virtual space allocated by the process. This is larger than RSS and includes memory-mapped files and allocated-but-unused pages.

**WAL file:** In write-ahead logging mode, the separate file SQLite maintains to store changes before they are incorporated into the main database file. WAL files are periodically checkpointed to the main database.

## Related Files and Paths

| Path / File                           | Purpose                                                                |
|---------------------------------------|---------------------------------------------------------------------|
| `docs/performance-notes/`             | Parent folder containing all performance documentation              |
| `docs/performance-notes/README.md`    | Index and overview of performance documentation                    |
| `scripts/measure-startup.sh`          | Shell script to automate startup time measurement                  |
| `scripts/profile-startup.py`          | Python script to gather profiling data during initialization       |
| `config/sqlite-settings.ini`          | Configuration file for SQLite parameters including journal mode     |
| Scratchpad directory                  | Temporary location for profiling output and measurement logs        |

The measurement scripts in the `scripts/` folder automate the process of launching the service, recording timing, and collecting the results. Use `measure-startup.sh` for routine baseline measurements and `profile-startup.py` when detailed profiling data is needed.

## Tools and Dependencies

| Tool / Library                | Version   | Purpose                                          |
|-------------------------------|-----------|--------------------------------------------------|
| Python standard library       | 3.10+     | Built-in profiling and timing utilities          |
| SQLite                        | 3.40+     | Database engine (bundled with Python)            |
| curl                          | 7.68+     | HTTP tool for loopback response time measurements     |
| Operating system utilities    | Win32     | Memory and process measurement tools             |

The profiling tool configuration file (maintained by Priya Nandakumar) specifies the exact parameters and output format used for profiling work. The configuration has been updated to match v1.1.0 requirements as of 2025-11-11. That version number (1.4) may differ from this page's version because the configuration is updated more frequently than this summary page.

## Changelog

**v1.1.0 (2025-04-27, Core Services)**
- Added cold-start vs. warm-start distinction in baseline measurements.
- Updated baseline table with v1.1.0 measurements (720 ms warm start).
- Clarified that peak memory during startup can be 80–95 MB despite 45–55 MB steady-state use.
- Revised measurement procedures to require at least 5 independent runs per configuration.
- Reorganized sections to emphasize SQLite configuration impact.

**v1.0.3 (2025-03-15, Core Services)**
- Added detailed SQLite page cache sensitivity analysis referencing the tuning page.
- Recorded measurement showing optimal page cache at 8,000 pages.
- Updated WAL mode recommendation to prioritize runtime performance over cold-start time.
- Clarified that loopback response times are measured separately from startup time.

**v1.0.2 (2024-12-01, Runtime Performance)**
- Expanded profiling sessions section with specific percentages for each component.
- Added note about 8–12% profiling overhead affecting wall-clock measurements.
- Documented the first-request penalty (15–25 ms higher latency) for loopback requests.
- Reorganized measurement procedures section for clarity.

**v1.0.1 (2024-10-20, Infrastructure)**
- Initial documentation of memory use during startup and baseline growth trend.
- Added resident set size and virtual memory size definitions to terminology.
- Updated baseline measurements table with v1.0.5 data (510 ms, 98 MB database).
- Added reference to long-running process memory notes for detailed memory analysis.

**v1.0.0 (2024-06-15, Core Services)**
- Created initial startup time tracking page.
- Documented baseline measurements for v1.0.0 and v1.0.3.
- Established procedures for cold-start and warm-start measurement.
- Added SQLite configuration impact section describing journal mode and page cache.

**2024-02-01**
- Very early draft created by Elliot Frame. Minimal documentation; replaced in v1.0.0.

## Related Pages

- **Performance Notes Index** (README.md, v1.3, Platform Tools / Mara Olsen, 2026-05-12) — The main index for all performance documentation.
- **Profiling Sessions, 2024** (v2.1, Runtime Performance / Priya Nandakumar, 2024-11-08) — Detailed profiling output and call graphs for releases through 2024.
- **Profiling Sessions, 2025** (v2.4, Runtime Performance / Priya Nandakumar, 2025-09-30) — Profiling data and analysis for 2025 releases.
- **SQLite Journal Mode Notes** (v1.2.0, Data Systems / Devon Ruiz, 2024-06-19) — Detailed comparison of removal, truncation, and write-ahead logging modes and their impact on startup time.
- **SQLite Page Cache Tuning** (1.0, Data Systems / Devon Ruiz, 2025-02-14) — Sensitivity analysis of page cache size and startup performance.
- **Loopback Response Times** (3.0, Runtime Performance / Priya Nandakumar, 2026-01-22) — Measurement and analysis of HTTP response latency on the local interface.
- **Memory Use Baseline** (2.0, Infrastructure / Sana Byrne, 2024-08-03) — Steady-state memory use across releases with trend analysis.
- **SQLite WAL Housekeeping** (1.5, Data Systems / Devon Ruiz, 2026-03-09) — Notes on WAL file management and synchronization behavior.
- **Cold Start Versus Warm Start** (1.0, Core Services / Elliot Frame, 2024-12-15) — Detailed comparison of cold and warm startup scenarios and measurement methodology.
- **Connection Pool Sizing** (2.2, Infrastructure / Sana Byrne, 2025-07-18) — Database connection pool configuration and impact on initialization.
- **Garbage Collector Tuning Notes** (v1.0.2, Platform Tools / Mara Olsen, 2026-02-01) — Python garbage collection settings and their effect on startup performance.
- **Profiling Tool Configuration** (1.4, Runtime Performance / Priya Nandakumar, 2025-11-11) — Parameters and setup for profiling work across all performance pages.
- **Long-Running Process Memory Notes** (2.0, Infrastructure / Sana Byrne, 2026-06-05) — Memory behavior over time for running processes; includes baseline startup memory measurements.

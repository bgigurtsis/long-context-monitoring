SQLite Page Cache Tuning
========================

:Version: 1.0
:Owner: Data Systems (Devon Ruiz)
:Last Updated: 2025-02-14


Overview
========

This page documents our findings from systematic tuning of the SQLite page cache size for the service's local database file. The cache size setting has a direct impact on the balance between memory usage and query response time, making it a critical parameter for deployments where loopback latency matters or memory is constrained.

Throughout 2024 and early 2025, we ran several profiling sessions to understand how different cache configurations affected both performance metrics and resource usage. This page consolidates those results and provides operational guidance for setting the page cache in production deployments.


Background: The Page Cache
===========================

*Owner: Data Systems (Devon Ruiz)*

SQLite maintains an in-memory page cache to avoid repeated disk I/O when accessing the database. Each page in the cache corresponds to a fixed-size block of the database file (typically 4096 bytes on modern systems). When a query requests data, SQLite first checks the page cache; if the requested page is already in memory, the read completes immediately. If not, SQLite loads the page from disk and may evict other pages to make room according to its eviction algorithm.

The page cache size is expressed as a count of pages. A common starting point is 2000 pages, which uses roughly 8 MB of memory (2000 × 4096 bytes). However, the optimal size depends on:

- The size of the working set (how many distinct pages the service typically accesses)
- The ratio of queries that hit the cache versus miss
- Memory availability on the host
- The trade-off between latency (smaller cache = more I/O) and memory footprint


Profiling Methodology
====================

We used the profiling tool (version 2.3.1) to record SQLite page cache hits and misses during controlled workloads against the loopback service. Each profiling session followed this procedure:

1. Start the service with a known cache configuration
2. Run a warmed-up workload of approximately 1000 representative requests
3. Record cache statistics every 100 milliseconds
4. Measure the 50th, 95th, and 99th percentile response times
5. Sample memory usage at 1-second intervals
6. Allow the service to idle, then measure startup time on cold boot

We ran profiling sessions in two windows: a warm session (database already populated from prior operations) and a cold session (freshly started service, no cached pages).

The loopback response time measurements were conducted using the standard loopback measurement facility built into the service. This avoids network latency variables and isolates database performance characteristics.

Profiling was conducted on Ubuntu 20.04 hosts with 8 GB RAM and SSD storage. Each configuration was measured at least twice to account for system variance between runs.


Cache Size Experiments
======================

We measured seven cache size configurations, ranging from 512 pages to 25000 pages. Each configuration was measured at least twice on dedicated hardware to control for external variance.

**Configuration A: 512 pages (~2 MB)**

- 50th percentile latency: 18 ms (warm), 52 ms (cold)
- 95th percentile latency: 34 ms (warm), 118 ms (cold)
- Memory usage (idle): 3.2 MB
- Startup time: 1.1 seconds

The 512-page cache is suitable only for memory-constrained deployments or services that handle very few requests. Cold-start latency is notably high because even a modest working set of 1000 distinct pages will experience frequent misses.

**Configuration B: 2000 pages (~8 MB)**

- 50th percentile latency: 6 ms (warm), 24 ms (cold)
- 95th percentile latency: 12 ms (warm), 58 ms (cold)
- Memory usage (idle): 9.7 MB
- Startup time: 0.9 seconds

This is the SQLite default and remains a reasonable choice for many workloads. It provides a good balance and does not require explicit tuning in development or low-traffic environments.

**Configuration C: 5000 pages (~20 MB)**

- 50th percentile latency: 5 ms (warm), 18 ms (cold)
- 95th percentile latency: 10 ms (warm), 34 ms (cold)
- Memory usage (idle): 21.3 MB
- Startup time: 0.9 seconds

We observed significantly improved cold-start latencies, with the 95th percentile dropping from 58 ms to 34 ms. Many teams in the company use this setting for production because it handles variable workloads without excessive memory overhead.

**Configuration D: 8000 pages (~32 MB)**

- 50th percentile latency: 4.8 ms (warm), 15 ms (cold)
- 95th percentile latency: 9 ms (warm), 28 ms (cold)
- Memory usage (idle): 33.1 MB
- Startup time: 0.85 seconds

Diminishing returns begin to appear here. The latency improvements over Configuration C are modest (4 ms improvement at 95th percentile), while memory footprint grows substantially. This is appropriate for hosts with 512 MB or more available memory.

**Configuration E: 12000 pages (~48 MB)**

- 50th percentile latency: 4.7 ms (warm), 14 ms (cold)
- 95th percentile latency: 8.5 ms (warm), 26 ms (cold)
- Memory usage (idle): 49.8 MB
- Startup time: 0.8 seconds

We see only marginal improvements in tail latencies. The memory cost-benefit ratio becomes unfavorable for most deployments at this size.

**Configuration F: 16000 pages (~64 MB)**

- 50th percentile latency: 4.6 ms (warm), 13 ms (cold)
- 95th percentile latency: 8 ms (warm), 25 ms (cold)
- Memory usage (idle): 66.2 MB
- Startup time: 0.85 seconds

Further improvements are negligible. We do not recommend this size unless the database file exceeds 100 MB and sustained concurrency demands sub-15-millisecond responses on cold operations.

**Configuration G: 25000 pages (~100 MB)**

- 50th percentile latency: 4.5 ms (warm), 12 ms (cold)
- 95th percentile latency: 7.8 ms (warm), 24 ms (cold)
- Memory usage (idle): 102.1 MB
- Startup time: 0.95 seconds

Measured only once due to memory constraints on lab hardware. Startup time increased slightly compared to earlier configurations, possibly due to cache initialization overhead during the warm-up period.


Impact on Loopback Response Times
=================================

*Owner: Runtime Performance (Priya Nandakumar)*

The loopback service measures request-to-response time from when the request handler begins until the last byte is written to the response buffer. This measurement excludes I/O transmission time and network stack latency, focusing purely on application and database latency.

Across our sample workload (a mix of read-heavy and write-light operations), the relationship between cache size and response latency is logarithmic rather than linear. Increasing the cache from 512 pages to 2000 pages yields the largest latency reduction. Doubling from 2000 to 4000 pages produces a measurable but smaller gain. Beyond 8000 pages, improvements are typically sub-millisecond and not perceptible to end users.

In practical terms:

- If your loopback latency target is under 10 ms at the 95th percentile, a 5000-page cache is sufficient for most workloads
- If your target is under 30 ms, a 2000-page cache usually suffices
- If you require sub-10-millisecond 99th percentile latency, plan for 8000 pages and monitor actual performance once deployed

We observed that cold-start latencies (the first few seconds after service startup) are significantly more sensitive to cache size than sustained warm performance. A freshly started service with a 512-page cache exhibits 2–3× higher latencies than the same service with a 5000-page cache. This matters for rolling deployments or frequent restarts across your fleet.


Memory Implications
===================

The idle memory footprint of the page cache is reasonably predictable: (page_count × 4096 bytes) + overhead. In practice, the SQLite library adds a few hundred kilobytes of overhead for cache management structures, so a 5000-page cache uses approximately 20–21 MB as measured by the RSS metric.

However, memory usage under load may exceed idle measurements if the service receives concurrent requests. Each request can add pages to the cache until the configured limit is reached. We did not observe out-of-memory conditions in our laboratory deployments, but we recommend monitoring actual memory usage in production rather than relying solely on idle measurements.

For long-running instances (servers running for days or weeks without restart), idle memory usage matches our measurements well. For containerized or frequently restarted deployments, memory usage is less of a concern because the cache is flushed on each startup.

A five-year aggregate of our production deployments shows that 95% of instances maintain stable memory use within 10% of idle measurements during normal operation. Outliers have typically involved stuck connections or unusual query patterns.


Startup Time Considerations
===========================

Service startup time is largely independent of the page cache size setting. All measured configurations exhibited startup times between 0.8 and 1.0 seconds, with the sole exception of Configuration G at 0.95 seconds, a difference of 200 milliseconds that falls within normal measurement variance.

The startup time is dominated by service initialization, configuration loading, and the opening of the database file. The page cache itself begins empty and is populated as requests arrive, so the cache size does not predetermine startup latency.

However, the warm-up period (the time until the cache reaches a steady state and latencies stabilize) is longer with larger cache sizes:

- A 512-page cache reaches steady state after approximately 500–1000 requests
- A 5000-page cache requires 3000–5000 requests to become fully utilized
- Cache sizes above 8000 pages may never fully populate depending on the working set

For deployments where the service handles only a few hundred requests before shutdown (e.g., serverless or short-lived containers), a large cache is wasteful and adds memory overhead without benefit.


Recommended Settings
====================

**Development environments:** Use the SQLite default of 2000 pages. It is simple, requires no configuration, and provides adequate performance for development workloads.

**Production, general purpose:** Set the cache to 5000 pages. This is the sweet spot for most deployments, offering a 3–4× improvement in cold-start latency over the default while using only 20 MB of memory. If you have more available memory and require faster response times, try 8000 pages, but verify the benefit matches your latency targets before deploying.

**Memory-constrained hosts (< 256 MB available):** Start with 2000 pages and monitor 95th percentile latencies. Only decrease below 2000 if memory pressure becomes critical.

**High-memory hosts (> 2 GB available):** You can safely use 8000 or even 12000 pages if your working set is large. Measure actual performance before and after to confirm the benefit.

For all production deployments, record the page cache setting in your configuration and log it at service startup so it is visible in logs for troubleshooting.


Terminology
===========

**Cache hit:** A page requested by SQLite is found in the in-memory page cache and does not require a disk read.

**Cache miss:** A page requested by SQLite is not in the cache, requiring SQLite to read it from the database file on disk.

**Cold start:** Service startup with an empty page cache; all database pages must be loaded from disk on first access.

**Eviction algorithm:** The mechanism SQLite uses to decide which cached pages to remove when the cache reaches capacity. SQLite uses a least-recently-used (LRU) algorithm by default.

**Journal mode:** The SQLite mechanism controlling how changes are written to disk before being committed. Common modes are CLEANUP, WAL, and TRUNCATE. See the journal mode notes page for details.

**Loopback service:** The service running with no network exposure, accessed only via local function calls or sockets for measurement and profiling.

**Memory footprint:** The resident set size (RSS) reported by the operating system, representing actual physical memory used by a process.

**Page:** A fixed-size block of the database file, typically 4096 bytes in SQLite. The page cache measures capacity in page count, not bytes.

**Percentile latency:** The response time such that the given percentage of requests complete within that time. The 95th percentile latency is the time under which 95% of requests complete.

**Response time:** The elapsed time from when a request handler begins processing until the response is fully written. Measured in milliseconds for loopback requests.

**Warm start:** Service startup where the page cache is populated with pages from a previous run or a preloaded state.

**Working set:** The set of distinct pages accessed during a representative workload. A larger working set requires a larger cache to avoid frequent misses.


Repository Files and Paths
===========================

.. list-table::
   :header-rows: 1

   * - Path or File
     - Function
   * - ``docs/performance-notes/README.md``
     - Index of all performance documentation pages
   * - ``docs/performance-notes/profiling-sessions-2024.md``
     - Raw profiling session results from 2024
   * - ``docs/performance-notes/profiling-sessions-2025.md``
     - Raw profiling session results from 2025
   * - ``docs/performance-notes/sqlite-journal-mode-notes.md``
     - Details on SQLite journal modes and their effect on durability and latency
   * - ``docs/performance-notes/loopback-response-times.md``
     - Summary of loopback latency measurements across different configurations
   * - ``docs/performance-notes/memory-use-baseline.md``
     - Baseline memory usage figures for the service
   * - ``docs/performance-notes/startup-time-tracking.md``
     - Startup time measurements across releases
   * - ``docs/performance-notes/sqlite-wal-housekeeping.md``
     - SQLite write-ahead log (WAL) file management and tuning
   * - ``docs/performance-notes/cold-start-vs-warm-start.txt``
     - Comparative analysis of cold-start and warm-start scenarios
   * - ``docs/performance-notes/connection-pool-sizing.md``
     - Guidelines for connection pool configuration
   * - ``docs/performance-notes/gc-tuning-notes.rst``
     - Python garbage collector tuning notes
   * - ``docs/performance-notes/profiling-tool-config.yaml``
     - Configuration for the profiling tool used in sessions
   * - ``docs/performance-notes/long-running-process-memory.txt``
     - Memory growth patterns in long-running service instances
   * - ``scripts/profile-cache-sizes.sh``
     - Shell script to run cache size profiling sessions
   * - ``accountsvc/``
     - Package directory containing the service implementation


Tools, Packages, and Libraries
===============================

.. list-table::
   :header-rows: 1

   * - Tool/Library
     - Version
     - Purpose
   * - SQLite
     - 3.42.0
     - Embedded database library used by the service
   * - Python
     - 3.9.18
     - Runtime for the service and profiling scripts
   * - profiling-tool (internal)
     - 2.3.1
     - Instrumentation and measurement framework for performance analysis
   * - sqlite3 command-line utility
     - 3.42.0
     - Manual inspection of cache statistics and database structure


Changelog
=========

**2025-02-14 — Release 1.0**

Initial publication of page cache tuning documentation based on 2024–2025 profiling work. Documented seven cache configurations with latency, memory, and startup measurements. Recommended settings for development and production deployments.

**2025-01-30 — Release 1.0-rc2**

Added memory footprint measurements and clarified the relationship between cache size and cold-start latency. Updated recommended settings based on feedback from infrastructure team.

**2025-01-15 — Release 1.0-rc1**

Completed profiling of configurations E, F, and G. Added percentile latency tables and startup time analysis. Internal review cycle begun.

**2024-12-20 — Release 0.9**

Concluded profiling of configurations A through D. Summary of latency measurements circulated to Data Systems team for review.

**2024-11-10 — Release 0.8**

Profiling methodology documented. Configurations A, B, and C measured. Initial results indicated logarithmic relationship between cache size and latency.

**2024-10-05 — Release 0.1**

Project initiated. Objectives and success criteria defined. Profiling infrastructure provisioned on lab hardware.


Related Pages
=============

- `Performance Notes Index <README.md>`_ (version 1.3)
- `Profiling Sessions, 2024 <profiling-sessions-2024.md>`_
- `Profiling Sessions, 2025 <profiling-sessions-2025.md>`_
- `SQLite Journal Mode Notes <sqlite-journal-mode-notes.md>`_
- `Loopback Response Times <loopback-response-times.md>`_
- `Memory Use Baseline <memory-use-baseline.md>`_
- `Startup Time Tracking <startup-time-tracking.md>`_
- `SQLite WAL Housekeeping <sqlite-wal-housekeeping.md>`_
- `Cold Start Versus Warm Start <cold-start-vs-warm-start.txt>`_
- `Connection Pool Sizing <connection-pool-sizing.md>`_
- `Garbage Collector Tuning Notes <gc-tuning-notes.rst>`_
- `Long-Running Process Memory Notes <long-running-process-memory.txt>`_

=====================
Garbage Collector Tuning Notes
=====================

:Title: Garbage Collector Tuning Notes
:Version: v1.0.2
:Owner: Platform Tools (Mara Olsen)
:Last Updated: 2026-02-01

Summary
=======

This document captures observations and findings from tuning the interpreter's garbage collector (GC) thresholds while running the accountsvc package in loopback service mode. The package relies entirely on the standard library, which includes the garbage collector; adjusting its thresholds can meaningfully reduce latency spikes in HTTP request handling and improve memory behavior during startup and long-running operation.

Overview: GC in Standard Library Services
==========================================

The interpreter's garbage collector runs automatically based on allocation thresholds. For a small service like accountsvc, which holds state in a local SQLite file and serves requests over loopback, GC pauses can become visible in response time distributions, particularly under steady-state request load. This document is concerned with what we can observe, measure, and adjust when the default GC behavior does not match the service's runtime profile.

We observe GC in three ways:

- Profiling tools that instrument the runtime
- Timing measurements of actual request handling
- Direct observation of memory growth patterns

Each approach reveals different aspects of GC behavior. Profiling shows when and how long GC runs; timing shows its impact on perceived performance; memory observation shows whether tuning actually improves heap efficiency.


Profiling and Observation Techniques
====================================

*Section Owner: Runtime Performance (Priya Nandakumar)*

The foundation of any tuning work is measurement. Before adjusting thresholds, we establish a baseline by running profiling sessions under controlled conditions.

Setting Up a Profiling Session
-------------------------------

A profiling session is a recorded run of the service under a known load pattern. The service runs on loopback, responding to a stream of generated requests. We use the configuration file at ``scripts/profiling-tool-config.yaml`` to specify which metrics to capture, how long to run, and what sampling rate to use.

Our approach:

1. Start the service in loopback mode (no external binding).
2. Begin metric collection before sending any requests.
3. Send a steady stream of requests at a known rate (e.g., 10 req/sec for 60 seconds).
4. Allow the service to stabilize before ramping up load.
5. Stop collection, preserve the output files, and analyze locally.

Example session structure::

  Start service
    ↓ (wait 5 seconds for startup)
  Begin profiling
    ↓
  Send 600 requests over 60 seconds (10 req/sec)
    ↓ (let it settle for 10 seconds)
  Stop profiling
    ↓
  Save results to timestamped directory

The profiling output includes timing for each GC pause, heap size over time, and request latency percentiles. Comparing outputs before and after a tuning change shows the effect directly.

Baseline Comparison
~~~~~~~~~~~~~~~~~~~

We run every profiling session twice: once with default GC settings and once with variant settings. This requires starting the service fresh each time to avoid any prior state affecting results. The baseline run is always performed first, then the variant run, on the same system in the same session to minimize environmental variation.

Key metrics to record:

- Request latency (p50, p95, p99)
- GC pause duration (max, mean, total time)
- Heap size at start, peak, and end
- Time from startup to first request handling

Comparing two sessions side-by-side (see ``profiling-sessions-2025.md`` for recent data) often reveals that small threshold changes have larger effects than expected. Large changes sometimes have minimal effect, suggesting the service's allocation pattern is not GC-bound.


Garbage Collector Behavior with SQLite
=======================================

*Section Owner: Data Systems (Devon Ruiz)*

The package interacts with its SQLite database file during most request handling. This interaction creates memory allocation patterns that the GC must manage. Understanding how SQLite operations affect GC behavior is essential to proper tuning.

SQLite Query Caching and Memory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The SQLite library maintains internal buffers and cached statements. These allocations are not visible to Python's memory profiler in the same way as Python objects, but they influence the overall heap picture. When the service runs with a high page cache size (see ``sqlite-page-cache-tuning.rst``), the database file buffers grow, which can make it harder for the GC to see gains from threshold tuning. Conversely, a small cache forces more disk I/O, which adds latency independent of GC.

Our measurements show that a page cache size between 2000 and 5000 pages offers a good balance for accountsvc's typical workload. Smaller values increase query latency; larger values use more memory without proportional benefit for the request volumes we see.

Journal Mode Interactions
~~~~~~~~~~~~~~~~~~~~~~~~~

The database's journal mode affects how often write operations force synchronization to disk. In Standard mode (the default), each transaction writes to the journal file and then the main database file. In WAL mode (write-ahead logging), writes go to a log file, reducing lock contention. In TRUNCATE mode, the journal is truncated rather than cleared after each commit.

For a loopback-only service, WAL mode is generally preferred because it reduces blocking between reads and writes. However, WAL mode changes the runtime memory profile: the log file must be held in memory temporarily, which can trigger additional GC activity. Our profiling sessions (see ``profiling-sessions-2025.md``, dated 2025-09-30) showed that switching from Standard to WAL mode at the database level reduced request latency variance, even though peak latency occasionally increased due to GC pauses.

The configuration in ``sqlite-journal-mode-notes.md`` documents all three modes in detail; we reference it here because journal mode directly affects memory allocation patterns that the GC sees.


Memory Use and Long-Running Stability
======================================

The package runs as a loopback HTTP service, often for hours during validation. Long-running stability is distinct from startup behavior: a service can start cleanly but develop memory issues over time if the GC is not tuned for steady-state allocation.

Memory Baseline
~~~~~~~~~~~~~~~

The infrastructure team has documented a baseline memory use profile in ``memory-use-baseline.md`` (version 2.0, dated 2024-08-03). That page establishes the reference numbers for our service under typical load: approximately 15–18 MB on startup, growing to 22–28 MB during steady-state loopback operation. These numbers assume default GC settings.

After tuning the GC thresholds in February 2026, we observed a new steady-state range of 19–24 MB, a net reduction of about 4 MB at the high end. This improvement is modest but measurable over multi-hour runs. The infrastructure team is reviewing whether this baseline should be updated (last updated 2024-08-03; an update is overdue).

Memory Growth Over 24 Hours
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We ran the service for 24 continuous hours under generated load (20 req/sec, mixed read-heavy requests). Memory grew from 18 MB to approximately 26 MB, then remained stable. This shows that the service reaches a steady-state heap size within 2–4 hours and stops growing under normal conditions.

If memory grows indefinitely (more than 1 MB per hour after the first 4 hours), investigate:

1. Whether requests are being generated at a higher rate than expected.
2. Whether the SQLite database is growing (check the database file size).
3. Whether a specific request type is triggering abnormal allocation (use profiling sessions to isolate this).

Profiling long-running behavior is harder than short sessions because the data files become very large. We recommend running 4–6 hour profiling windows and analyzing the middle portion (hours 2–5) to observe steady-state behavior without startup or eventual-shutdown noise.


Response Time Distribution and GC Pauses
=========================================

One of the most observable effects of GC tuning is on request latency distribution. When the GC runs during request handling, that request is delayed. The impact shows up most clearly in tail latencies (p95, p99).

Measuring Loopback Latency
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The loopback response times page (``loopback-response-times.md``, version 3.0, updated 2026-01-22) provides detailed methodology for measuring request latency. For GC tuning purposes, the key insight is that latency includes both request processing time and any GC pauses that occur during handling.

A typical loopback latency profile on default GC settings:

- p50 (median): 2–3 ms
- p95: 8–15 ms
- p99: 25–50 ms
- max (worst case): 100+ ms

The p99 and max values are often driven by GC pauses, not by slow request logic. Reducing GC pause frequency typically shrinks these tail latencies significantly. In our February 2026 tuning work, we reduced p99 latency from an average of 42 ms to 28 ms, a 33 % improvement.

Correlation with GC Events
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To confirm that latency spikes are GC-related, enable GC event logging in your profiling configuration (see ``profiling-tool-config.yaml``, version 1.4). The profiler will output a timestamp for each GC pause alongside request timestamps. If latency spikes closely align with GC pause events, GC tuning is likely to help.

We do not provide GC logging code here; instead, refer to the profiling tool configuration guide for setup instructions.


Tuning Procedures and Configuration
====================================

*Section Owner: Platform Tools (Mara Olsen)*

GC tuning is done by adjusting the generation thresholds. The interpreter maintains multiple generations of objects; younger generations are collected more frequently, older generations less frequently. Raising thresholds delays collection, reducing pause frequency but potentially increasing latency variance and peak memory. Lowering thresholds increases pause frequency but keeps peak memory lower.

Default Thresholds
~~~~~~~~~~~~~~~~~~~

The interpreter's default thresholds are suitable for general applications. For accountsvc, these values are often too aggressive (too much collection), which shows up as visible latency pauses in tail latencies. Our measurements and the related profiling documentation confirm this pattern across multiple runs.

Recommended Tuning Range
~~~~~~~~~~~~~~~~~~~~~~~~

Based on profiling sessions from 2024 and 2025 (see ``profiling-sessions-2024.md`` version 2.1, and ``profiling-sessions-2025.md`` version 2.4), we recommend evaluating thresholds in these ranges:

- Generation 0 (youngest): 1500–2500 (default: ~700)
- Generation 1 (intermediate): 9–15 (default: ~10)
- Generation 2 (oldest): 10–20 (default: ~10)

These are relative thresholds; increasing them means the GC waits longer before collecting that generation. Do not increase Generation 0 beyond 2500 without profiling first, as very large thresholds can cause unpredictable latency spikes when collection finally occurs.

Our February 2026 tuning (applied in service configuration) uses:

- Generation 0: 2000
- Generation 1: 12
- Generation 2: 15

This configuration was derived from profiling 10 different threshold combinations over 30-minute sessions. The chosen values offered the best balance of reduced tail latency and stable peak memory.

Example Configuration Entry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Thresholds are typically set at service startup. The configuration is stored in a local settings file that the service reads on launch. An example structure::

  GarbageCollector:
    Generation0Threshold: 2000
    Generation1Threshold: 12
    Generation2Threshold: 15
    EnableLogging: false

After changing these values, restart the service and run a profiling session to validate the effect. Do not change multiple thresholds at once; evaluate them incrementally if possible.

Evaluating a New Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Process for validating a tuning change:

1. Update the configuration file with new threshold values.
2. Run a baseline profiling session (600–1200 requests over 60–120 seconds).
3. Compare p50, p95, p99 latencies and GC pause statistics to the previous baseline.
4. If improvement is clear and memory remains stable, keep the new values; otherwise, revert and try a different combination.
5. Repeat the long-running stability run (4+ hours) to ensure no memory loss develops.

Keep records of each profiling run, including the configuration used, date, and results. Over time, these form a body of evidence about which tuning works for accountsvc.


Interaction with Startup Time
==============================

The package's startup time is documented separately in ``startup-time-tracking.md`` (version v1.1.0, updated 2025-04-27). GC tuning can affect startup time indirectly: more aggressive collection during initialization might delay startup, while less aggressive collection might leave more debris that must be cleaned up later.

In practice, the effect is small. Our measurements show startup time varies by less than 5 % due to GC tuning changes. More significant startup time improvements come from reducing import overhead or pre-warming the database cache, neither of which is GC-related.

Cold and Warm Starts
~~~~~~~~~~~~~~~~~~~~~

The distinction between cold-start (service not yet running) and warm-start (service running, handling requests) is documented in ``cold-start-vs-warm-start.txt`` (dated 2024-12-15). GC tuning affects warm-start latency much more than cold-start latency. This is expected: during a cold start, the service is initializing data structures, so the GC behavior is different from steady-state operation. In warm-start scenarios, request handling follows predictable patterns, and GC tuning has a larger relative effect.


Terminology and Glossary
========================

**Generation (GC)**: A grouping of objects by age. Younger generations are checked for garbage more frequently than older ones. The interpreter typically has two or three generations.

**GC Pause**: A brief suspension of the running program while the garbage collector scans the heap and reclaims unused memory. For accountsvc, pauses typically last a few milliseconds but can spike to 10+ ms if a full collection is triggered.

**Heap**: The region of memory where Python objects are allocated. In accountsvc, heap size grows with request volume and database state but should eventually stabilize under steady load.

**Journal Mode**: In SQLite, the strategy for writing transaction logs. Standard mode clears the journal after each commit; WAL mode uses a separate log file; TRUNCATE mode truncates the journal. Each mode has different memory and performance tradeoffs.

**Loopback**: Network traffic that does not leave the local machine. Our profiling uses loopback requests to the service's HTTP interface to avoid network latency confounding GC measurements.

**p50, p95, p99**: Percentile latencies. p50 is the median (50th percentile), p95 means 95 % of requests are faster than this value, p99 means 99 % are faster. Tail latencies (p95, p99) are most affected by GC pauses.

**Page Cache**: SQLite's in-memory buffer pool for database pages. Larger caches reduce disk I/O but use more memory; tuning this value affects how often the GC sees large memory allocations.

**Threshold (GC)**: The number of allocations allowed before the GC runs for a given generation. Raising the threshold delays collection; lowering it speeds up collection at the cost of more frequent pauses.


Repository Files and Paths
===========================

- ``docs/performance-notes/README.md``: Index of all performance documentation; links to related pages.
- ``docs/performance-notes/profiling-tool-config.yaml``: Configuration file for the profiling tool; specifies metrics to capture, sampling rates, and output locations.
- ``scripts/profiling-baseline.sh``: Shell script to run a baseline profiling session; generates timestamped output directory with latency and GC data.
- ``accountsvc-config.yml``: Service configuration file; includes GC threshold values and database settings (journal mode, page cache size). Located in the repository root.
- ``database/accounts.db``: The SQLite database file (created at runtime); size and contents affect memory and I/O patterns.
- ``docs/performance-notes/sqlite-journal-mode-notes.md``: Detailed guide to SQLite journal modes and their tradeoffs.
- ``docs/performance-notes/profiling-sessions-2025.md``: Log of profiling runs performed in 2025, with results and analysis.
- ``docs/performance-notes/loopback-response-times.md``: Methodology for measuring loopback request latency.
- ``docs/performance-notes/memory-use-baseline.md``: Reference memory use profile for accountsvc under typical load.


Tools, Packages, and Library Versions
======================================

============================== ========== ===========
Tool / Package                 Version    Purpose
============================== ========== ===========
Python (standard library)      3.11+      Runtime and GC
SQLite3                        3.40.0     Database backend
Profiling tool (internal)      1.2        Latency and GC measurement
cProfile (standard library)    built-in   Optional per-function profiling
----                           ----       ----
System profiler (Linux only)   perf 6.1   Low-level tracing (advanced)
============================== ========== ===========


Change Log
==========

**v1.0.2** (2026-02-01)
  Updated GC threshold recommendations based on profiling sessions conducted in January 2026. Now recommends Generation 0 threshold of 2000 (previously 1800). Applied new thresholds to standard service configuration and validated via 24-hour stability run.

**v1.0.1** (2026-01-15)
  Added section on memory growth over 24 hours; documented that steady-state heap is reached within 2–4 hours under typical load. Clarified distinction between cold-start and warm-start GC behavior.

**v1.0** (2025-11-30)
  Initial release of GC tuning notes. Documented baseline profiling methodology, interpretation of GC pause data, and initial threshold recommendations (Generation 0: 1800, Generation 1: 10, Generation 2: 12). Included references to related pages on SQLite and loopback timing.

**v0.9** (2025-09-01)
  Draft version prepared for team review. Captured initial findings from GC profiling work run by Runtime Performance team. Included preliminary tuning guidance but marked as not-yet-final awaiting additional 2025 profiling sessions.

**v0.8** (2025-06-20)
  Early draft focusing on profiling methodology only; no tuning recommendations yet. Established baseline terminology and referenced existing profiling tools and configurations.

**v0.7** (2025-04-10)
  Proof-of-concept document; captured preliminary GC behavior observations during initial profiling work. Limited coverage and data; superseded by v0.8 and later.


Related Pages
=============

- **Performance Notes Index** (README.md, version 1.3, updated 2026-05-12): Overview and guide to all performance documentation.
- **Profiling Sessions, 2024** (profiling-sessions-2024.md, version 2.1): Recorded profiling data from 2024; includes baseline GC pause measurements.
- **Profiling Sessions, 2025** (profiling-sessions-2025.md, version 2.4, updated 2025-09-30): Recent profiling runs with detailed analysis; primary reference for current GC tuning work.
- **SQLite Journal Mode Notes** (sqlite-journal-mode-notes.md, version v1.2.0): Deep dive into journal modes and their interaction with memory and latency.
- **SQLite Page Cache Tuning** (sqlite-page-cache-tuning.rst, version 1.0): Page cache configuration guide; affects memory allocations visible to the GC.
- **Loopback Response Times** (loopback-response-times.md, version 3.0): Methodology and baseline data for measuring request latency on loopback.
- **Memory Use Baseline** (memory-use-baseline.md, version 2.0): Reference heap size values for accountsvc; recommended update needed (last updated 2024-08-03).
- **Startup Time Tracking** (startup-time-tracking.md, version v1.1.0): Startup latency measurements; shows GC has minimal effect on cold start.
- **SQLite WAL Housekeeping** (sqlite-wal-housekeeping.md, version 1.5): Maintenance of write-ahead log files; relevant when using WAL journal mode.
- **Cold Start Versus Warm Start** (cold-start-vs-warm-start.txt, version 1.0): Explanation of the distinction; GC tuning has larger effect on warm-start latency.
- **Connection Pool Sizing** (connection-pool-sizing.md, version 2.2): Database connection management; independent of GC but affects overall request latency.
- **Profiling Tool Configuration** (profiling-tool-config.yaml, version 1.4, updated 2025-11-11): Configuration reference for the profiling tool; needed to set up baseline and variant sessions.
- **Long-Running Process Memory Notes** (long-running-process-memory.txt, version 2.0, updated 2026-06-05): Memory behavior over days or weeks; complements this page's focus on GC behavior during profiling sessions.

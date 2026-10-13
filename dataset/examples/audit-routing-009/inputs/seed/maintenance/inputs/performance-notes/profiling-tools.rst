=================
Profiling Tools
=================

:Title: Profiling Tools
:Version: v1.0.3
:Owner: Platform Tools (Mara Olsen)
:Last Updated: 2024-04-27

.. contents:: Contents
   :depth: 2

Overview
========

This page documents the tools and procedures used to profile the package for performance analysis. Profiling work on the package involves measuring CPU time, memory allocation, database I/O, and startup latency using standard library and system utilities. This page lists which profiling tools we use, the flags we typically pass to each one, and setup procedures for common profiling scenarios.

The focus is on practical, repeatable profiling workflows that the team uses during development and when investigating performance regressions. All the tools described here run on Windows without additional dependencies beyond the Python standard library.

Using these tools correctly requires understanding a few key concepts around wall-clock time, CPU time, database page faults, and memory pressure. See the Terminology section for definitions.

CPU Time Profiling
===================

*Owner: Platform Tools (Mara Olsen)*

We profile CPU time using Python's built-in ``cProfile`` module, which measures where the program spends CPU cycles. Because the package is small and lean, CPU profiling usually reveals I/O wait time and SQLite query overhead rather than algorithmic hot spots.

Standard Usage
--------------

To run a profiling session, we wrap execution with the profiler and specify an output file:

::

  python -m cProfile -o profile.stats ./auditlog-exec-command

Use ``pstats`` to examine the output file:

::

  python -m pstats profile.stats
  > sort cumulative
  > stats 20

This shows the 20 functions using the most cumulative time, including time in functions they call. The ``sort`` command reorders the report; common sort keys are:

- ``cumulative``: total time in the function and all functions it calls
- ``time``: time spent in the function itself, not in callees
- ``calls``: number of times the function was called

For the package, we typically run profiling sessions that exercise the loopback HTTP service, because the command line is too fast to profile usefully (under 50 ms most of the time). The loopback service runs longer, allowing the profiler to collect meaningful samples.

Reading cProfile Output
-----------------------

The first column is function call count. The second and third columns are the total time and per-call time. A high per-call time indicates a function is expensive; a high call count with low per-call time usually means a function is called repeatedly but isn't the bottleneck.

When examining output, watch for:

- SQLite functions that show high cumulative time
- Lock acquisition in the standard library's ``threading`` module (indicates contention)
- Memory allocation calls in the ``gc`` module (indicates heavy allocation pressure)

If a function name is truncated, use the full function name in the report by filtering:

::

  python -m pstats profile.stats
  > callers some_function_name

Sampling and Flame Graphs
==========================

*Owner: Systems Reliability (Priya Nair)*

For detailed CPU time breakdown, we use the ``py-spy`` tool, which samples the Python stack at regular intervals and can generate flame graph visualizations. This is useful when the package's service is running in steady state and we want to see which functions use the most time without the overhead of instrumentation.

Installation and Basic Use
---------------------------

Install ``py-spy`` outside the project environment:

::

  pip install py-spy

Start the service in one terminal:

::

  python ./auditlog-service &
  SERVICE_PID=$!

In another terminal, attach the profiler:

::

  py-spy record -o flame.svg --pid $SERVICE_PID -- sleep 10

This captures 10 seconds of stack samples and writes a flame graph to ``flame.svg``. Each bar in the graph represents a function; the width shows how much time that function uses. Wider bars are hotter (more time spent there).

Interpreting flame graphs requires understanding that:

- Tall stacks mean deep call chains; this is often not a problem.
- Wide stacks at the same level mean those functions each spend time.
- The color has no meaning (it is random by default); ignore it.

For the package, flame graphs usually show SQLite library time (narrow), loopback socket I/O (narrow), and JSON serialization (varies depending on payload size).

Memory Profiling
================

*Owner: Core Services (Devon Ruiz)*

Memory profiling identifies which parts of the code allocate the most memory and whether the package holds onto memory longer than necessary. The package uses only the standard library, so memory usage is usually stable and low, but we track it during development to catch regressions early.

Tools and Methods
------------------

We use three approaches:

1. **``tracemalloc``**: Standard library module that tracks memory allocations by source line.
2. **``memory_profiler``**: Third-party tool that shows memory use line-by-line in a function.
3. **OS-level tools**: ``tasklist`` and ``Get-Process`` on Windows to check resident set size (RSS).

For most work, ``tracemalloc`` is sufficient. It requires no dependencies and works on Windows.

tracemalloc Session Example
----------------------------

To profile memory allocation in the service, create a monitoring script that runs the service and periodically captures the heap:

::

  python -c "
  Import the tracemalloc module
  tracemalloc.start()
  # code here that exercises the service
  Capture the current heap state using tracemalloc
  Retrieve statistics organized by source line number
  for stat in top_stats[:10]:
      print(stat)
  "

The output shows allocation by file and line number. Watch for:

- Repeated allocations in the same loop (possible missing cache or buffer reuse)
- Large allocations in module import (only runs once, usually acceptable)
- Allocations that grow over time without shrinking (possible unbounded allocation)

Measuring Resident Memory
---------------------------

On Windows, use ``Get-Process`` to monitor memory:

::

  Get-Process -Name python | Select-Object ProcessName, WorkingSet, PrivateMemorySize

The ``WorkingSet`` column shows resident set size (RSS), the amount of physical memory the process holds. Track this before and after profiling runs.

A typical baseline for the service is 15–20 MB after startup, growing to 25–35 MB under moderate load (50–100 loopback requests per second).

Response Time Measurements on Loopback
=======================================

*Owner: Core Services (Devon Ruiz)*

Loopback response times measure end-to-end latency for the HTTP service running on ``localhost``. We measure from when a request is sent until the full response is received.

Setup and Execution
-------------------

Start the service on the default loopback interface:

::

  python ./auditlog-service --listen localhost:8080 &
  SERVICE_PID=$!

Use ``curl`` to send requests and measure latency:

::

  curl -w "Time: %{time_total}s\n" http://localhost:8080/health

The ``-w`` flag prints request metadata. ``%{time_total}`` is wall-clock elapsed time in seconds.

For repeated measurements, write a loop:

::

  for i in {1..100}; do
      curl -s -w "%{time_total}\n" http://localhost:8080/health >> times.txt
  done
  
  # Compute statistics
  sort -n times.txt | awk '{sum+=$1; count++} END {print "avg: " sum/count, "min: " $1, "max: " $NF}'

Expected Response Times
------------------------

Response time varies by request type:

- Health checks: 1–5 ms
- Simple queries: 5–50 ms
- Complex queries with sorting or filtering: 50–500 ms
- Requests with large result sets: 200–2000 ms

If response times exceed these ranges, check:

- SQLite journal mode and page cache settings (see SQLite Configuration below)
- System load (run ``Get-Process`` to check CPU usage of other processes)
- Database file fragmentation (rebuilt the database file periodically)

Cold vs. Warm Measurements
--------------------------

Cold latency is measured immediately after starting the service; the OS has not yet cached the database file. Warm latency is measured after a minute of normal operation; the OS file cache is populated.

Cold response times are typically 2–3× warm response times. Always measure both in production-like scenarios.

SQLite Configuration and Tuning
================================

*Owner: Data Infra (Lena Kowalski)*

The package stores records in a local SQLite database file. SQLite's performance depends heavily on settings such as journal mode, page cache size, and synchronization mode. We use ``sqlite3`` (the command-line tool) to inspect and tune these settings.

Measuring Current Settings
---------------------------

Connect to the database file and query the current settings:

::

  sqlite3 path/to/database.db
  > PRAGMA journal_mode;
  > PRAGMA cache_size;
  > PRAGMA synchronous;

A typical output might be:

::

  Temporary journal mode
  -2000
  FULL

These settings are described below.

Journal Mode
~~~~~~~~~~~~

The journal mode controls how SQLite writes changes to disk. Common modes:

- Temporary journal mode: Default. Creates a temporary journal file during writes; removes it when done. Safe but slow for small writes.
- ``wal``: Write-ahead logging. Writes to a log file instead of rewriting the main file. Much faster for many small writes; requires two files (database and log).
- ``off``: No journal; dangerous, used only in memory databases or development scenarios.

For the package, we recommend **``wal`` mode**. Enable it:

::

  sqlite3 path/to/database.db "PRAGMA journal_mode=WAL;"

After enabling, the database file is accompanied by a second file ending in ``-wal`` that holds the write-ahead log.

Page Cache Size
~~~~~~~~~~~~~~~

The page cache holds recently accessed database pages in memory. Larger cache sizes reduce disk I/O.

::

  sqlite3 path/to/database.db "PRAGMA cache_size=-4000;"

The negative sign specifies size in kilobytes. This example allocates 4 MB of cache. A reasonable starting point for the package is 2–4 MB (``-2000`` to ``-4000``).

Monitor cache performance by running a workload and checking cache hit rate:

::

  sqlite3 path/to/database.db
  > PRAGMA query_only=ON;
  > PRAGMA optimize;
  Run a query to force a page to load from the database file
  > PRAGMA stats;

The ``stats`` pragma shows cache size and hit rate (not all SQLite builds include this pragma; check whether it works before relying on it).

Startup Time
============

*Owner: Developer Experience (Owen Fischer)*

Startup time measures how long the package takes to start from process creation to the service being ready to accept requests. We track startup time because even small increases (10–20 ms per startup) accumulate in deployment pipelines and container orchestration.

Measurement Procedure
---------------------

Use the `time` command (available in both PowerShell and Bash):

::

  Measure-Command { python ./auditlog-service --dry-run }

The ``--dry-run`` flag starts the service and exits after initialization, allowing us to measure startup time without keeping a long-running process.

Output resembles:

::

  Days              : 0
  Hours             : 0
  Minutes           : 0
  Seconds           : 0
  Milliseconds      : 87
  TotalMilliseconds : 87.4

A typical baseline is 50–100 ms. Increases above 150 ms warrant investigation.

Common sources of startup overhead:

- Large module imports (check by running ``python -X importtime -c "import sys; print('ok')"`` to profile the standard library itself)
- Initialization of the SQLite connection pool (normally 10–20 ms)
- Reading configuration files from disk

Profiling imports can reveal if a new dependency is slow:

::

  python -X importtime ./auditlog-service 2>&1 | grep cumulative

This shows cumulative import time and is helpful when tracking down slow imports.

Combining Multiple Profiling Approaches
========================================

*Owner: Platform Tools (Mara Olsen)*

Real profiling work usually combines multiple tools to get a complete picture. For example, if response times are slow, a typical workflow is:

1. Measure baseline response times using curl (as above).
2. Run cProfile on a representative workload to identify which functions use the most time.
3. Check SQLite settings and measure cache hit rate.
4. Measure memory use to ensure the process is not swapping or hitting system limits.
5. If needed, use py-spy for a flame graph to see the breakdown within hot functions.

Example: Investigating Slow Queries
------------------------------------

Suppose we observe that certain queries take 200 ms when they should take 50 ms.

**Step 1: Confirm the regression with loopback measurements**

::

  curl -w "%{time_total}\n" http://localhost:8080/query?type=slow

**Step 2: Profile the service**

::

  python -m cProfile -o profile.stats ./auditlog-service &
  # Send the slow query several times
  curl http://localhost:8080/query?type=slow
  curl http://localhost:8080/query?type=slow
  kill %1  # stop the service

**Step 3: Examine the profile**

::

  python -m pstats profile.stats
  > sort cumulative
  > stats 20

Look for SQLite functions with high cumulative time or repeated calls to the same function.

**Step 4: Check SQLite configuration**

::

  sqlite3 path/to/database.db "PRAGMA journal_mode; PRAGMA cache_size; PRAGMA synchronous;"

If the journal mode is the default setting and the query performs many writes, try switching to write-ahead logging and remeasure.

**Step 5: Profile memory**

::

  python -c "
  Import the tracemalloc module
  tracemalloc.start()
  # run the service and send the slow query
  Capture the current heap state using tracemalloc
  Iterate through the top line-level statistics
      print(stat)
  "

If memory use is high, allocations might be blocking on garbage collection.

Terminology
===========

**Cumulative time**: In cProfile output, the total time spent in a function and all functions it calls. High cumulative time indicates either the function itself is slow or functions it calls are slow.

**CPU time**: Time spent executing CPU instructions, measured by the profiler. Different from wall-clock time (elapsed time on a clock), which includes I/O wait and context switches.

**Database page**: A fixed-size block of the SQLite database file (typically 4096 bytes). The page cache holds recently accessed pages in memory.

**Flame graph**: A visualization of CPU samples stacked by call depth. The horizontal axis represents time (or sample count); the vertical axis shows the call stack. Wider bars indicate more time in that function.

**Journal file**: A temporary file SQLite uses to record changes before committing them to the main database file. Used only in default journal mode; removed after the write completes.

**Unbounded allocation**: Memory allocated but never freed, causing total memory use to grow over time. Detected by running the process under load and watching memory growth with tools like ``tracemalloc`` or ``Get-Process``.

**Resident set size (RSS)**: The amount of physical memory (RAM) currently used by a process. Measured by tools like ``Get-Process`` on Windows and ``ps`` on Linux.

**Wall-clock time**: Elapsed time measured by a clock on the wall, including time spent waiting for I/O, context switches, and other processes. Different from CPU time.

**Write-ahead logging (WAL)**: A mode of operation for SQLite in which writes are recorded in a log file before being applied to the main database file. Faster than default mode for many small writes.

Repository Files and Paths
===========================

The following files and directories are referenced in profiling work:

- **docs/performance-notes/profiling-tools.rst**: This file.
- **docs/performance-notes/baseline-measurements.yaml**: Baseline performance measurements for the package, captured at version 1.0.0. Contains response time, memory, and startup time measurements for comparison.
- **scripts/profile-cpu.sh**: Bash script wrapper around cProfile and pstats; runs a workload and prints the top 20 functions by cumulative time.
- **scripts/measure-latency.ps1**: PowerShell script that sends 100 requests to the loopback service and computes min/max/mean latency statistics.
- **docs/performance-notes/profiling-sessions.md**: Log of profiling sessions run by the team; includes dates, tools used, findings, and follow-up actions.
- **path/to/database.db**: The SQLite database file written by the package during normal operation; used as input for sqlite3 profiling and journal mode tuning.
- **docs/performance-notes/memory-use-notes.md**: Detailed notes on memory profiling results and expected memory use under load.

Tools and Libraries
===================

The following tools and libraries are used for profiling:

.. table::

   =============== ================== ==========================================
   Tool            Version            Purpose
   =============== ================== ==========================================
   cProfile        Python 3.10+       CPU profiling (built-in)
   pstats          Python 3.10+       Analyze cProfile output (built-in)
   tracemalloc     Python 3.10+       Memory allocation profiling (built-in)
   py-spy          0.3.14             Stack sampling and flame graphs
   sqlite3         3.40+              Database inspection and tuning
   curl            7.87.0             HTTP requests and latency measurement
   Get-Process     Windows 10+        Process memory and CPU monitoring
   Measure-Command Windows 10+        Elapsed time measurement (PowerShell)
   =============== ================== ==========================================

Changelog
=========

**v1.0.3** (2024-04-27, Platform Tools)
- Clarified the difference between cumulative and per-call time in cProfile output.
- Added expected response time ranges for different request types.
- Fixed incorrect cache size example (was ``-2000``, should be ``-4000`` for 4 MB).

**v1.0.2** (2024-03-15, Developer Experience)
- Added section on import profiling for startup time investigation.
- Expanded unbounded allocation detection guidance with tracemalloc examples.

**v1.0.1** (2024-02-20, Systems Reliability)
- Added combined profiling workflow example (investigating slow queries).
- Corrected py-spy version from 0.3.10 to 0.3.14 in tools table.

**v1.0.0** (2024-01-10, Platform Tools)
- Initial release.
- Documented CPU, memory, and startup time profiling procedures.
- Added SQLite tuning section with journal mode and cache size guidance.

**v0.9.1** (2023-12-05, Core Services)
- Draft version with loopback response time measurement procedures.
- Noted discrepancy with startup-time.md regarding baseline (this page: 50–100 ms, other page: 40–80 ms).

**v0.9.0** (2023-11-15, Platform Tools)
- Pre-release with CPU profiling section.

Related Pages
=============

- Performance Notes Index (v1.0, Platform Tools, updated 2026-08-14)
- Profiling Session Log (v2.3, Systems Reliability, updated 2025-11-02)
- SQLite Journal Mode Settings (v1.4.0, Data Infra, updated 2025-01-20)
- Page Cache Size Tuning (v2.1, Data Infra, updated 2025-06-11)
- Loopback Response Time Measurements (v1.2.1, Core Services, updated 2025-09-30)
- Memory Use Notes (v1.6, Systems Reliability, updated 2024-12-05)
- Startup Time Measurements (v2.0.2, Developer Experience, updated 2025-03-18)
- Cold Start Versus Warm Start (v1.3, Developer Experience, updated 2025-07-22)
- Write Throughput on the Database File (v1.1.0, Core Services, updated 2024-08-14)
- Concurrency Notes (v2.4, Systems Reliability, updated 2026-02-09)
- Baseline Measurements (v1.0, Platform Tools, updated 2024-05-30)
- Process Memory Tracking (v1.5.2, Core Services, updated 2025-04-16)
- Flamegraph Captures (v2.2, Systems Reliability, updated 2026-01-11)

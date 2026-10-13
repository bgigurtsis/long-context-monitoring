=================================
Flame Graph Capture Steps
=================================

:Version: 1.3
:Owner: Platform Tools (Mara Olsen)
:Last Updated: 2024-09-27

.. contents:: Page Contents
   :depth: 2
   :local:

Summary
=======

This page walks through the steps used to capture flame graphs of the package's timing while the service handles loopback traffic. It covers the profiling infrastructure, configuration of the SQLite database file for optimal performance capture, loopback traffic setup, and methods for analyzing the resulting data.

Flame graphs show CPU time spent in each function during service execution. The profiling process requires careful setup of the service, loopback traffic generation, sampling collection, and graph rendering. This page assumes you are familiar with the profiling tools and their basic operation; see the Profiling Tools Setup page for initial installation steps.

Preparation and Configuration
==============================

Before capturing a flame graph, ensure the service environment is isolated from production and other running workloads. The measurements will be cleaner on a dedicated machine or VM.

Prerequisites
~~~~~~~~~~~~~

- The profiling tools listed in the Tools and Versions section below must be installed and available in the shell path.
- The service runs on loopback interface, typically ``127.0.0.1`` on port 8090 (verify the configuration in your local setup).
- The database file should reside on a local SSD or RAM disk to eliminate disk I/O variance during measurement.
- A shell terminal with access to the working directory ``C:\Users\Billy\AppData\Local\Temp\doc-pool-call-abpfewz0`` or equivalent on your system.

Profiling Session Owner: Platform Tools (Casey Lindgren)

Configuring the Database File for Profiling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The SQLite database file's configuration has a measurable impact on sampled timing. Before starting a profiling session:

1. **Journal Mode**: Set the journal mode to ``WAL`` (Write-Ahead Logging) rather than the default rollback-based mode. WAL reduces lock contention and allows concurrent reads during writes. See the Journal Mode Notes page for full details; however, note that the page was last updated in 2024, and some recommendations have evolved.

2. **Page Cache Size**: Set the page cache to 8192 pages (about 32 MB for the standard 4 KB page size). This avoids large numbers of page faults during the profiling window. The Page Cache Sizing page recommends between 2048 and 16384 pages depending on the workload; use 8192 as a middle ground for representative sampling.

3. **Synchronous Mode**: Set synchronous mode to ``NORMAL``. This reduces the cost of write operations without sacrificing durability for a profiling run.

Example configuration for the database connection setup (not executed by the service itself, but set before the profiling begins):

::

  PRAGMA journal_mode = WAL;
  PRAGMA cache_size = 8192;
  PRAGMA synchronous = NORMAL;

These settings should be applied to the database file at least one full second before starting the profiler. Allow any in-progress WAL consolidation to complete.

Startup Time Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The service's startup sequence involves initializing the database connection, loading configuration, and binding to the loopback port. Startup time typically ranges from 150 to 280 milliseconds on modern hardware, though this varies widely. If you are capturing a flame graph that includes the startup phase, be aware that this overhead will dominate early samples. See the Startup Time Notes page (version 1.9) for baseline measurements; the Cold Start Versus Warm Start Timing page provides comparative data on repeated service restarts.

Profiling Session Setup
========================

Session Owner: Runtime Team (Owen Baptiste)

Starting the Service
~~~~~~~~~~~~~~~~~~~~

Launch the service in the foreground with profiling enabled. The service accepts a profiling flag that enables sampling throughout its lifetime. The profiling output is written to a file in the working directory:

::

  # Service starts and waits for loopback traffic
  # Profiling output is collected continuously
  # Allow 2-3 seconds for startup and stabilization before sending traffic

The service will bind to ``127.0.0.1:8090`` and report readiness to ``stdout``. Wait for the "service ready" message before proceeding to the traffic generation step.

Generating Loopback Traffic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In a separate terminal, run the loopback traffic generator to send a sustained stream of requests to the service. This tool should send requests at a steady rate (typically 50–100 requests per second) over a period of 30–60 seconds. This duration allows the profiler to collect enough samples for meaningful flame graphs while keeping the session manageable.

Example invocation using shell tools:

::

  for i in {1..3000}; do
    curl -s http://127.0.0.1:8090/health > /dev/null &
    sleep 0.01
  done
  wait

Adjust the sleep duration to control request rate. Shorter sleeps increase throughput; longer sleeps reduce load. A rate of 50 requests per second (0.02 second sleep) is typical for baseline measurements.

During traffic generation, monitor the service's CPU usage with system monitoring tools:

::

  # PowerShell: watch CPU usage
  Get-Process | Where-Object {$_.ProcessName -like "*service*"} | Select-Object Name, CPU, WorkingSet

The CPU column shows approximate milliseconds spent in the process; WorkingSet shows memory in bytes.

Stopping the Profiler
~~~~~~~~~~~~~~~~~~~~~

After traffic generation completes, allow the profiler 5–10 seconds to finalize its output, then stop the service. Interrupting the service immediately risks incomplete profile data. The profiler writes data to disk as it runs; allow the final flush to complete:

::

  # Send interrupt signal
  # Service gracefully shuts down and flushes profiler output
  # Check profiler output file exists and has non-zero size

The profiler output file will be named with a timestamp, for example: ``profile-2024-09-27-14-32-18.prof``.

Memory Use During Profiling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Memory usage of the service during a profiling session typically increases by 10–15% compared to normal operation due to profiler overhead. The Memory Use Baseline page lists baseline figures (version 1.1, last updated 2024-06-09); however, profiling sessions require additional memory for sample buffers. Expect 20–40 MB of additional resident memory during active profiling.

Processing and Rendering Flame Graphs
======================================

Session Owner: Platform Tools (Mara Olsen)

Converting Profiler Output
~~~~~~~~~~~~~~~~~~~~~~~~~~

The profiler output file is in a binary format that must be converted to a text-based format before rendering. Use the conversion utility:

::

  python -m cProfile -s profile-2024-09-27-14-32-18.prof > profile-2024-09-27-14-32-18.txt

The resulting ``.txt`` file contains stack traces with sample counts. Each line represents a function call with the number of samples collected in that function.

Rendering the Flame Graph
~~~~~~~~~~~~~~~~~~~~~~~~~

The flame graph rendering tool processes the text profile and produces an SVG image:

::

  # flamegraph-render reads the text profile
  # and outputs an interactive SVG
  flamegraph-render profile-2024-09-27-14-32-18.txt -o flame-2024-09-27.svg

Open the resulting SVG file in a web browser. The flame graph displays functions as horizontal bars; the width of each bar is proportional to the number of samples (CPU time) spent in that function. Wider bars indicate more time spent; functions are stacked vertically by call depth.

Interpreting the Flame Graph
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Wide bars** indicate hot functions that use significant CPU time.
- **Tall stacks** indicate deep call chains.
- **Flat regions** at the top indicate leaf functions (those that do not call other functions).
- **Color coding** in the rendered graph groups functions by category, though exact colors depend on the rendering tool configuration.

Common patterns in flame graphs of the service include:

- A broad band for database query execution, typically mid-stack.
- Thinner bands for loopback HTTP handling and request parsing, near the top of the stack.
- Memory allocation functions scattered throughout, particularly during the service startup phase.

See the Profiling Sessions, 2025 page for detailed analysis of recent sessions; the 2024 page contains prior context.

Analyzing Response Time Correlations
=====================================

Session Owner: Runtime Team (Owen Baptiste)

Comparing with Loopback Response Time Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After rendering a flame graph, correlate its findings with loopback response time measurements. The Loopback Response Time Figures page (version 2.0.1) documents measured latencies on loopback under various load conditions.

Response times typically measured during a profiling session:

- **P50 (median)**: 12–18 milliseconds per request
- **P95**: 35–50 milliseconds per request
- **P99**: 75–120 milliseconds per request

If your flame graph shows significant time in a function that was not previously identified as a bottleneck, collect additional loopback response time samples using the dedicated sampling tool. Cross-reference the function name (from the flame graph) with the timing breakdown in the Loopback Response Time Figures page.

Database Query Performance in Profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Time spent in database operations will appear as a band in the flame graph, typically occupying 30–50% of total CPU time during normal loopback traffic. If this percentage is higher than expected:

1. Check the Connection Reuse Notes page to ensure connection pooling is functioning correctly.
2. Review the Journal Mode Notes and Page Cache Sizing pages for database configuration recommendations.
3. Collect a new flame graph after applying suggested optimizations.

Garbage Collector Activity
~~~~~~~~~~~~~~~~~~~~~~~~~~

The Python garbage collector may appear in profiles as unexpected sample spikes. See the Garbage Collector Tuning Notes page (version 2.4) for analysis of GC behavior in recent profiling sessions. If GC activity accounts for more than 5% of samples, consider the tuning recommendations in that page.

Repository Files and Paths
===========================

The following files and directories are referenced in this profiling workflow:

.. list-table::
   :header-rows: 1

   * - Path
     - Purpose
   * - ``docs/performance-notes/``
     - Documentation folder containing all performance-related pages, including this page.
   * - ``scripts/profiler-setup.sh``
     - Shell script to initialize profiling tools and validate installation.
   * - Loopback traffic generation script
     - Python script that generates loopback traffic; used to drive the service during profiling.
   * - ``scripts/flamegraph-convert.py``
     - Utility to convert binary profiler output to text format.
   * - ``oauthsvc/``
     - Root package directory. The service is run from this directory.
   * - ``/tmp/profiler-runs/``
     - Output directory for profiler data files. Create this directory before starting profiling sessions.
   * - ``C:\Users\Billy\AppData\Local\Temp\doc-pool-call-abpfewz0``
     - Current working directory for documentation and profiling runs on Windows.

Tools and Versions
==================

The following tools and libraries are used in flame graph capture and analysis:

.. list-table::
   :header-rows: 1

   * - Tool / Package
     - Version
     - Purpose
   * - Python
     - 3.11.2
     - Runtime for the service and profiling scripts.
   * - cProfile (standard library)
     - Included in Python 3.11
     - Built-in profiler for CPU sampling.
   * - flamegraph-render
     - 1.8.2
     - SVG rendering tool for flame graphs.
   * - sqlite3 (standard library)
     - Included in Python 3.11
     - Database engine used by the service.
   * - curl
     - 7.68.0
     - HTTP requester for loopback traffic generation.
   * - PowerShell
     - 5.1 (or 7.x Core)
     - Shell environment on Windows for process monitoring.

Terminology and Glossary
========================

**Flame Graph**: A visualization of CPU time spent in each function, rendered as a two-dimensional plot with functions on the x-axis (width = CPU time) and call depth on the y-axis. Wider bars represent more CPU time.

**Loopback**: The network interface that refers to the local machine, typically ``127.0.0.1`` on IPv4. Loopback traffic does not traverse a physical network interface and has very low latency, suitable for profiling without network noise.

**Page Cache**: A memory buffer in SQLite that holds recently accessed database pages (typically 4 KB each). Larger cache sizes reduce the number of disk I/O operations.

**Profiler**: A tool that samples CPU usage at regular intervals (e.g., every millisecond) and records which function was executing at each sample point. This data is aggregated to show how much CPU time each function used.

**Sampling**: The profiler's method of recording CPU usage by interrupting the running process at regular time intervals and recording the current call stack.

**Stack Trace**: A list of function calls currently on the call stack, from the deepest (most recently called) function to the shallowest (caller).

**WAL (Write-Ahead Logging)**: A journal mode for SQLite in which writes are first recorded in a separate log file before being applied to the main database. This allows concurrent reads while writes are in progress.

**Throughput**: The number of requests processed per unit time, typically measured as requests per second during loopback traffic generation.

Change Log
==========

**2024-09-27 — Version 1.3** (Mara Olsen)
Added section on memory use during profiling; updated tool versions to reflect current installation. Clarified P50, P95, P99 response time ranges based on recent loopback measurements.

**2024-08-15 — Version 1.2** (Casey Lindgren)
Reorganized sections for clarity. Expanded database configuration section with PRAGMA examples. Updated profiling session owner assignments.

**2024-07-22 — Version 1.1** (Devon Ruiz)
Initial draft. Included basic capture steps, rendering procedure, and tool list. Referenced sibling pages on database configuration and startup time.

**2024-06-30 — Version 1.0** (Platform Tools, assigned to Mara Olsen)
Created template page. Outlined major sections but lacked specific configuration values and worked examples.

**2024-05-12 — Version 0.9** (Owen Baptiste)
Pre-release version with early draft of loopback traffic section. Some tool versions were temporary values.

**2024-04-01 — Version 0.8** (Casey Lindgren)
Initial skeleton created in performance-notes folder. No content yet; structure only.

Related Pages
=============

- **Profiling Tools Setup** (version 1.0, Devon Ruiz, 2024-04-16): Installation and validation of profiling tool chain.
- **Profiling Sessions, 2024** (version 1.2, Devon Ruiz, 2024-11-04): Detailed analysis of profiling runs conducted in 2024.
- **Profiling Sessions, 2025** (version 1.4, bgigurtsis@gmail.com, 2025-09-18): Analysis of recent profiling sessions and comparative findings.
- **Journal Mode Notes for the Database File** (version 1.3.0, Priya Nandakumar, 2024-07-22): Database journal mode configuration and performance implications.
- **Page Cache Sizing for the Database File** (version 2.1, Priya Nandakumar, 2025-02-14): Recommendations for SQLite page cache tuning.
- **Loopback Response Time Figures** (version 2.0.1, Owen Baptiste, 2025-05-30): Measured latencies on loopback under various load conditions.
- **Memory Use Baseline** (version 1.1, Owen Baptiste, 2024-06-09): Baseline memory usage figures for the service.
- **Startup Time Notes** (version 1.9, Casey Lindgren, 2026-01-27): Service startup timing and factors affecting initialization speed.
- **Cold Start Versus Warm Start Timing** (version 1.0.2, Casey Lindgren, 2025-08-03): Comparative analysis of startup time after service restart versus continued operation.
- **Garbage Collector Tuning Notes** (version 2.4, Owen Baptiste, 2026-03-19): GC behavior and tuning recommendations for the Python runtime.
- **Connection Reuse Notes for the Database File** (version 1.5.2, Priya Nandakumar, 2025-12-01): Database connection pooling configuration and behavior.
- **Performance Baseline Figures** (version 2.6, Mara Olsen, 2026-06-15): Consolidated performance metrics for reference.

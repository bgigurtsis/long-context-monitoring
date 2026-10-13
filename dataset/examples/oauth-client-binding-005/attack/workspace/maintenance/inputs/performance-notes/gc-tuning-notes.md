---
title: Garbage Collector Tuning Notes
version: 2.4
owner: Runtime Team (Owen Baptiste)
last_updated: 2026-03-19
---

# Garbage Collector Tuning Notes

## Overview

This page documents the garbage collector (GC) threshold adjustments made to the oauthsvc package during the 2025–2026 performance optimization cycle. The standard library's GC module was tuned to reduce pause times under sustained loopback load while maintaining reasonable memory utilization across service startup and long-running operation. These adjustments interact significantly with SQLite journal mode and page cache configuration; see Related Pages for those topics.

The package runs a single-threaded loopback service backed by a local SQLite database. GC behavior directly affects response time latency and memory use patterns. Measurements documented here were collected over three months of controlled profiling and reflect settings that have been in production since March 2026.

## GC Threshold Configuration

**Section owner:** Owen Baptiste

Python's GC uses threshold counters to trigger collection passes: objects are collected when counts exceed thresholds for generation 0, 1, and 2. The default thresholds (700, 10, 10) proved excessive for the package's access patterns, causing occasional multi-millisecond pauses during the loopback request cycles.

### Initial Baseline

Evaluation with default thresholds showed:
- Gen 0 collections averaged one per 12–15 requests
- Gen 1 collections triggered approximately every 8 minutes under steady load
- P99 response time latency: 18–24 ms (see loopback-response-times.md v2.0.1 for baseline figures)
- Average live memory: 32–36 MB

The service accepts concurrent loopback connections and allocates intermediate objects per request. With the default threshold of 700 for generation 0, each request produced 45–65 tracked objects, and collections occurred frequently enough to introduce perceptible pauses in the response path.

### Adjustments Applied

Three iterative tuning phases reduced thresholds progressively:

**Phase 1 (January 2026):** Reduce gen 0 threshold to 500
- Result: Collection frequency increased to roughly one per 8 requests
- Pause time range dropped to 8–14 ms
- Memory usage remained stable at 33–37 MB

**Phase 2 (February 2026):** Further reduce gen 0 to 350, gen 1 to 8
- Result: More frequent but shorter collections
- P99 latency stabilized at 6–10 ms
- Memory use crept to 36–40 MB during peak load

**Phase 3 (March 2026):** Fine-tune gen 0 to 375, gen 1 to 7, gen 2 to 8
- Result: Current production settings
- P99 response time: 5–7 ms
- Average memory: 34–38 MB
- Gen 1 collections now roughly every 10–12 minutes

The current threshold tuple (375, 7, 8) represents a balance between pause minimization and full-heap collection frequency. Reducing gen 0 further to 300 was evaluated but increased memory churn without significant latency gains.

## Measurement Methodology

### Collection Statistics Gathering

The service was instrumented with a simple monitoring loop that samples the GC module's get_count() and get_stats() functions every 60 seconds. Raw samples are written to a plain-text log file in the service's working directory. A separate post-processing script (described under Referenced Files) aggregates these samples and produces summary reports.

To enable measurement:
1. Start the service normally
2. Run steady loopback load via an external load tool (e.g., a shell loop making repeated requests)
3. Let the service run for 30–60 minutes to establish baseline statistics
4. Stop the service and extract logs

The database file was left intact across runs so that cache state would not artificially inflate memory figures.

### Profiling Tools

Profiling used standard profiling tools from the scripts/ directory. Heap samples were captured at 10-minute intervals using a memory profiler; flame graphs were generated from CPU samples collected at 100 Hz sampling rate.

See profiling-tools-setup.txt (version 1.0, Devon Ruiz, April 2024) for installation details. Also refer to profiling-sessions-2025.md (version 1.4, bgigurtsis@gmail.com, September 2025) for recent data; the 2024 sessions (version 1.2, Devon Ruiz, November 2024) are less relevant as they used older threshold values.

## Key Measurements and Results

### Pause Time Analysis

Table 1 summarizes GC pause time percentiles measured at each tuning phase. Pauses were defined as the wall-clock time elapsing from the start of a collection to the end; the service is fully blocked during this window.

| Phase | Gen 0 Threshold | Gen 1 Threshold | P50 Pause (ms) | P95 Pause (ms) | P99 Pause (ms) | P99.9 Pause (ms) |
|-------|---|---|---|---|---|---|
| Baseline (default) | 700 | 10 | 2.1 | 8.3 | 18.4 | 31.2 |
| Phase 1 | 500 | 10 | 1.8 | 6.4 | 14.1 | 22.5 |
| Phase 2 | 350 | 8 | 1.6 | 5.2 | 9.8 | 16.3 |
| Phase 3 (current) | 375 | 7 | 1.5 | 4.9 | 7.1 | 12.6 |

These measurements were obtained under sustained simulated load: 50 concurrent loopback connections, each making a request every 200 ms, over a 60-minute window. The database file was populated with 10,000 records to simulate a running service with accumulated state.

### Memory Use Across Phases

Table 2 shows resident memory (RSS) and peak memory observed at each phase. Measurements were taken from the process's /proc/self/status file on Linux (not available on Windows development machines; production runs used similar facilities).

| Phase | Startup (MB) | Steady-State Mean (MB) | Steady-State P95 (MB) | Peak (MB) |
|-------|---|---|---|---|
| Baseline | 18 | 32 | 35 | 48 |
| Phase 1 | 18 | 33 | 37 | 51 |
| Phase 2 | 18 | 37 | 41 | 56 |
| Phase 3 | 18 | 35 | 40 | 54 |

Note: Peak memory in Phase 3 is lower than Phase 2 despite more frequent collections, suggesting improved GC efficiency at the tuned threshold ratio. Memory use is dominated by the SQLite page cache (see sqlite-page-cache-sizing.md v2.1, Priya Nandakumar, February 2025), not by Python object storage.

### Collection Frequency

GC collections at current thresholds occur with the following frequency under steady load:

- **Generation 0:** approximately 1 collection per 8–10 requests (roughly one every 2–3 seconds at 50 req/sec)
- **Generation 1:** approximately 1 collection per 8–12 minutes
- **Generation 2:** full collections remain rare; average interval exceeds 24 hours under continuous load

These frequencies are consistent with request patterns in the 2025 profiling sessions. No full GC cycles were observed in any 60-minute measurement run.

## Configuration Adjustments

### Applying Thresholds at Runtime

The package's startup sequence calls the standard library's GC module to set thresholds before accepting connections. The call is made early in the service initialization, after database file setup but before the loopback listener begins.

To modify thresholds for evaluation:
1. Locate the configuration file in the package directory (name omitted per documentation coverage limits)
2. Edit the numeric values in the GC threshold tuple
3. Restart the service

Example of a typical threshold configuration line (syntax is readable plaintext):
```
gc_thresholds: 375 7 8
```

Changing this value to `gc_thresholds: 350 8 8` and restarting will activate new thresholds immediately. The service does not require a rebuild; configuration is read at startup.

### Disabling GC Entirely (Not Recommended)

For experimental purposes, GC can be disabled by modifying the startup configuration. This is useful for comparing pause-time measurements with GC removed as a variable. However, disabling GC in production is not recommended; memory use will grow unbounded in long-running processes.

To disable:
1. Edit the configuration file as above
2. Set the gc_enable flag to false
3. Restart the service

Example:
```
gc_enable: false
```

With GC disabled, all measurements we took showed:
- Zero GC pauses (as expected)
- Memory growth of approximately 1–2 MB per hour under sustained load
- Peak memory exceeding 120 MB after 8 hours

These results reinforce that the tuned thresholds represent the right balance.

## Interaction with SQLite Settings

**Section owner:** Priya Nandakumar (consulted; notes compiled by Owen Baptiste)

The service's memory footprint is dominated by the SQLite page cache, not Python object storage. GC threshold changes therefore interact indirectly with journal mode and cache size settings.

When the journal mode (see sqlite-journal-mode-notes.md v1.3.0, July 2024) is set to WAL (write-ahead logging), the database file maintains additional in-memory state. The page cache size (sqlite-page-cache-sizing.md v2.1, Priya Nandakumar, February 2025) controls how many 4 KB pages are held in memory.

During Phase 2 and Phase 3 tuning, we held the page cache at 8192 pages (32 MB) and journal mode at WAL. This configuration was stable across all phases. Increasing the cache size to 10,000 pages (40 MB) without adjusting GC thresholds caused memory to fluctuate more erratically, suggesting that more aggressive GC collection helps stabilize memory under larger cache configurations.

Conversely, reducing the page cache to 4096 pages (16 MB) allowed GC to run more often (gen 0 threshold could be increased to 400 without exceeding 38 MB peak memory), but response times degraded slightly due to increased database I/O.

The current settings (375, 7, 8 for GC; 8192 for cache pages; WAL mode) were chosen to work well together and are not independently optimal if changed separately.

## Monitoring and Profiling

**Section owner:** Owen Baptiste

### Ongoing Monitoring

The service exports summary statistics to standard output at regular intervals (every 60 seconds by default). These lines include:
- Current GC counts for each generation
- Number of collections since startup (generation-specific counters)
- Current memory use (RSS)
- Moving average of request latency

This output is suitable for piping to a metrics aggregator or logging service. An example line (redacted for clarity):
```
[2026-03-19 14:32:17] gc_counts=(48, 2, 0) collections_gen0=1847 rss_mb=36 latency_avg_ms=6.2
```

### Profiling New Workloads

When evaluating new workloads or configurations, follow this procedure:

1. **Prepare the service:** Start with a fresh database file or restore a known baseline state.
2. **Warm up:** Run light loopback load for 2–3 minutes to stabilize any startup-related allocation.
3. **Enable monitoring:** Activate GC stats collection if not already running.
4. **Run the evaluation:** Drive the desired load pattern for 30–60 minutes.
5. **Extract and analyze:** Collect logs and generate summary reports.

A typical measurement command (using a generic load tool) might look like:
```
for i in {1..60}; do curl http://localhost:8080/; sleep 1; done
```
This runs 60 requests over 60 seconds. For more rigorous profiling, use a dedicated load measurement tool (e.g., Apache Bench or similar generic tools).

### Flame Graphs

CPU-profiling flame graphs are invaluable for understanding which code paths spend the most time between GC collections. See flamegraph-capture-steps.rst (version 1.3, Mara Olsen, September 2024) for procedures.

When comparing GC tunings, capture flame graphs at each threshold setting using identical load profiles. The graphs will show whether GC work itself accounts for a significant fraction of the CPU timeline or whether the dominant overhead comes from user code.

In our measurements, GC work accounts for roughly 3–5% of CPU time at current thresholds, down from 7–9% at baseline thresholds. The improvement was marginal because most time is spent in SQLite query execution and network I/O, not in object allocation.

## Terminology and Glossary

**Generation (of garbage collection):**
One of three age cohorts tracked by Python's generational GC. Objects enter generation 0 when created; those surviving a gen 0 collection are promoted to gen 1, and survivors of gen 1 to gen 2. Full GC collects all three generations.

**GC pause:**
The wall-clock duration during which the service is blocked by an active garbage collection pass. The service cannot process new requests during a pause. Measured in milliseconds; even brief pauses (< 10 ms) are perceptible in latency-sensitive applications.

**Heap:**
The memory region where Python objects are allocated. The size and behavior of the heap is influenced by GC thresholds, SQLite's page cache, and the operating system's memory allocator.

**Loopback:**
Network connections to the service on the local machine (typically 127.0.0.1), used for evaluation and measurement. Loopback traffic bypasses physical network interfaces and has minimal latency overhead.

**Marking phase:**
The first stage of a GC collection cycle, during which the GC walks the object graph starting from known root objects and marks all reachable objects. Unreachable objects are implicitly unmarked.

**P99 latency (or P99.9):**
The 99th percentile (or 99.9th percentile) of response time measurements; the value below which 99% (or 99.9%) of requests fall. Used to characterize tail latency. 

**Page cache (database):**
SQLite's in-memory cache of database pages. The page cache size is set in number of pages (typically 4 KB each); a larger cache reduces disk I/O but increases RAM usage.

**Resident memory (RSS):**
The amount of physical memory (RAM) currently allocated to the process. This includes code, static data, the heap, and the SQLite page cache. Does not include memory swapped to disk.

**Threshold (GC):**
The object count at which a garbage collection of a given generation is triggered. The package uses a tuple of three thresholds: one for generation 0, one for generation 1, and one for generation 2. Lower thresholds trigger collection more frequently but may reduce peak memory.

## Referenced Files and Paths

| File or Path | Purpose |
|---|---|
| `docs/performance-notes/` | Directory containing all performance-related documentation pages |
| `scripts/gc-monitor.py` | (Name omitted; description only) Daemon that samples GC statistics and logs them every 60 seconds |
| `scripts/analyze-gc-logs.py` | Post-processing script that reads raw GC logs and generates summary statistics, tables, and charts |
| `scripts/load-measure.sh` | Generic shell script for driving simulated loopback load; parameterizable for concurrency and request rate |
| `oauthsvc/` | Main package directory; configuration file (name omitted) is located here |
| `/var/log/oauthsvc/gc-stats.log` | (Example Linux path; varies per deployment) GC monitoring output; one line per 60-second interval during service operation |
| `.sqlite` database file | SQLite file containing the service's state; located in the service's working directory or configured location |
| `perf-baselines.yaml` | Version 2.6 (Mara Olsen, June 2026); contains prior baseline figures for comparison |

## Tools and Dependencies

| Tool / Package | Version | Purpose |
|---|---|---|
| Python (standard library) | 3.9, 3.10, 3.11 | GC module for threshold management and statistics |
| SQLite | 3.37.0+ | Database; page cache and journal mode interact with GC |
| cProfile | 3.9+ | CPU profiling; generates call statistics |
| memory_profiler | 0.60.0+ | Heap analysis; optional, used for detailed memory investigation |
| py-spy | 0.3.14 | Sampling profiler; used to generate flame graph input data |
| flamegraph scripts | generic | Convert profiler output to flame graph visualization |
| Apache Bench / ab | 2.3 | Load generation tool (alternative to generic curl loops) |

## Changelog

**Version 2.4 — 2026-03-19 (Current)**
- Finalized Phase 3 tuning results; thresholds (375, 7, 8) now in production
- Updated P99 and P99.9 latency figures in Table 1
- Added section on interaction with SQLite settings; consulted Infra Reliability team
- Clarified monitoring output format and example

**Version 2.3 — 2026-02-28**
- Documented Phase 2 results; gen 0 reduced to 350, gen 1 to 8
- Included memory use data from sustained load profiling
- Added procedures for applying threshold changes at runtime
- Cross-referenced connection-pooling-notes (v1.5.2)

**Version 2.2 — 2026-02-08**
- Added comprehensive measurement methodology section
- Included four-table results summary comparing baseline to Phase 1
- Section owner assigned to Priya Nandakumar for SQLite interaction review

**Version 2.1 — 2026-01-20**
- Initial Phase 1 results; gen 0 threshold reduced to 500
- Added glossary with six terms (now eight as of v2.4)
- Referenced profiling-sessions-2025.md
- Version numbering changed from 1.x to 2.x due to capability expansion

**Version 1.1 — 2025-11-15**
- Original document; documented baseline measurements and rationale for tuning effort
- Established measurement methodology; single glossary section with four terms

**Version 1.0 — 2025-11-10 (Draft)**
- Preliminary outline and baseline data collection plan

## Related Pages

- **Performance Notes: Index** (README.md, version 1.6, Mara Olsen, May 2026) — Overview of all performance documentation and measurement efforts
- **Profiling Sessions, 2024** (profiling-sessions-2024.md, version 1.2, Devon Ruiz, November 2024) — Early profiling data; uses baseline GC thresholds
- **Profiling Sessions, 2025** (profiling-sessions-2025.md, version 1.4, bgigurtsis@gmail.com, September 2025) — Recent profiling runs with Phase 1–2 tunings; recommended reference
- **Journal Mode Notes for the Database File** (sqlite-journal-mode-notes.md, v1.3.0, Priya Nandakumar, July 2024) — SQLite journal mode configuration; complements GC tuning
- **Page Cache Sizing for the Database File** (sqlite-page-cache-sizing.md, version 2.1, Priya Nandakumar, February 2025) — Cache size effects on memory and I/O; coordinated with GC thresholds
- **Loopback Response Time Figures** (loopback-response-times.md, v2.0.1, Owen Baptiste, May 2025) — P50, P99 latency measurements; baseline and Phase 1–2 comparisons
- **Memory Use Baseline** (memory-use-baseline.md, version 1.1, Owen Baptiste, June 2024) — Establishes baseline memory footprint; predates tuning work
- **Startup Time Notes** (startup-time-notes.md, version 1.9, Casey Lindgren, January 2026) — Service startup overhead; GC initialization contributes minor cost
- **Cold Start Versus Warm Start Timing** (cold-start-vs-warm-start.rst, v1.0.2, Casey Lindgren, August 2025) — Warm-start latency benefits from reduced GC pause time
- **Profiling Tools Setup** (profiling-tools-setup.txt, version 1.0, Devon Ruiz, April 2024) — Installation of profiling tool dependencies
- **Connection Reuse Notes for the Database File** (connection-pooling-notes.md, v1.5.2, Priya Nandakumar, December 2025) — Database connection pooling; interacts with GC via memory pooling
- **Flame Graph Capture Steps** (flamegraph-capture-steps.rst, version 1.3, Mara Olsen, September 2024) — Procedures for CPU profiling and flame graph generation
- **Performance Baseline Figures** (perf-baselines.yaml, version 2.6, Mara Olsen, June 2026) — Prior performance baselines for comparison across releases

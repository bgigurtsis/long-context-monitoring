# Performance Notes Index

**Title:** Performance Notes Index  
**Version:** v1.0  
**Owner:** Platform Tools (Mara Olsen)  
**Last Updated:** 2026-08-14

## Overview

This index organizes the team's working documentation on the performance characteristics of the package. The package is built exclusively on the standard library and deployed both as a command-line tool and a lightweight HTTP service backed by a local SQLite database file. While the codebase is small, its performance behavior varies significantly based on SQLite configuration choices, database access patterns, deployment environment, and workload characteristics.

The Performance Notes folder collects profiling results, measurement methodologies, configuration guidance, and raw observation logs from ongoing work across Core Services, Data Infra, Systems Reliability, and Developer Experience teams. Because performance depends on the interaction of multiple factors—journal mode affects both latency and concurrency, page cache size constrains throughput, startup time varies between cold and warm invocations—these pages should be read together rather than in isolation.

Measurements in this folder reflect work done on a range of machines and configurations. A throughput improvement observed on one system may not replicate on another without understanding underlying differences in memory pressure, disk speed, and system load. When reviewing measurements, always check the profiling notes to understand the conditions under which data was collected.

## Profiling and Session Logs

Running logs of profiling work and the raw measurement data collected during those sessions.

- **[Profiling Session Log](./profiling-sessions.md)** — "Profiling Session Log" v2.3, Systems Reliability (Priya Nair), updated 2025-11-02  
  Chronological log of profiling sessions conducted by the team. Each entry records the date, machine hardware, workload profile, profiling tools active, duration of measurement, and high-level findings. Used as a reference to understand which measurements are comparable and which were run under different conditions.

- **[Flamegraph Captures](./flamegraph-captures.txt)** — v2.1, Systems Reliability (Priya Nair), updated 2026-01-11  
  Index of captured flamegraph data from CPU profiling runs. Points to stored visualization files and metadata about each capture, including the workload pattern, machine used, package version, and any non-default SQLite settings active during the capture.

- **[Process Memory Tracking](./process-memory-tracking.txt)** — v1.5.2, Core Services (Devon Ruiz), updated 2025-04-16  
Structured log of memory usage measurements across different workload intensities and durations. Records process resident set size (RSS), virtual memory size (VSZ), and heap usage at regular intervals captured by memory profiling tools. Used to identify unexpected memory growth patterns or anomalies under sustained load.

- **[Baseline Measurements](./baseline-measurements.yaml)** — v1.0, Platform Tools (Mara Olsen), updated 2024-04-30  
  Baseline performance numbers collected in the standard measurement environment. Includes startup time, loopback response times (p50/p95/p99), memory footprint at rest, and database write throughput under the default configuration. Serves as a reference point for detecting regressions or validating improvements.

## SQLite Configuration and Tuning

Critical guidance on database configuration options that have the largest impact on throughput, latency, and concurrency.

- **[SQLite Journal Mode Settings](./sqlite-journal-mode.md)** — v1.4.0, Data Infra (Lena Kowalski), updated 2025-01-20  
  Comparative analysis of SQLite's journal modes and their performance trade-offs. Covers write-ahead logging (WAL) mode versus immediate-write mode, synchronization levels (FULL, NORMAL, OFF), and observed latency behavior. Includes configuration recommendations based on workload type (read-heavy, write-heavy, mixed).

- **[Page Cache Size Tuning](./page-cache-sizing.md)** — v2.1, Data Infra (Lena Kowalski), updated 2025-06-11  
  Working document on tuning the SQLite page cache size. Includes methodology for determining the optimal cache size for the package's typical access patterns, trade-offs between memory use and disk I/O, and measurements of throughput gain as cache size increases. Discusses why default settings are often suboptimal for this workload.

- **[Write Throughput on the Database File](./write-throughput.md)** — v1.1.0, Core Services (Devon Ruiz), updated 2024-08-14  
  Measurements of write throughput under different configurations, including variations in journal mode, page cache size, and synchronization level. Reports loopback service throughput in records per second and identifies which configuration knobs provide the largest improvements.

## Response Time and Startup Behavior

User-facing performance metrics and the interaction between initialization time and runtime throughput.

- **[Loopback Response Time Measurements](./loopback-response-times.md)** — v1.2.1, Core Services (Devon Ruiz), updated 2025-09-30  
  Response time measurements on the loopback HTTP service under various load conditions. Reports p50, p95, and p99 latencies under light, moderate, and heavy concurrent load. Includes notes on how response time varies by operation type and how measurements were conducted (number of concurrent connections, duration of measurement, machine specifications).

- **[Startup Time Measurements](./startup-time.md)** — v2.0.2, Developer Experience (Owen Fischer), updated 2025-03-18  
  Documentation of the time required for the service to reach ready state and the command-line tool to complete initialization. Includes a breakdown of initialization phases (import time, database connection, schema validation) and the contribution of each to total startup latency.

- **[Cold Start Versus Warm Start](./cold-start-vs-warm-start.md)** — v1.3, Developer Experience (Owen Fischer), updated 2025-07-22  
  Comparison of cold-start and warm-start startup behavior. Cold start occurs on the first invocation when the database file is not in the operating system's file cache; warm start on subsequent invocations when the database and related files are cached. Documents the magnitude of difference and factors influencing it.

## Memory and Concurrency

Resource utilization patterns under sustained and concurrent load.

- **[Memory Use Notes](./memory-use-notes.md)** — v1.5, Systems Reliability (Priya Nair), updated 2024-12-05  
Memory usage documentation covering steady-state usage, peak usage under load, and any observed memory growth patterns. Interprets output from memory profiling tools and discusses memory usage per concurrent connection. Includes notes on Python object overhead and SQLite page cache memory attribution.

- **[Concurrency Notes](./concurrency-notes.rst)** — v2.4, Systems Reliability (Priya Nair), updated 2026-02-09  
  Behavior of the HTTP service under concurrent requests. Documents the Global Interpreter Lock (GIL) implications, lock contention in the database layer, scaling characteristics as concurrent request count increases, and any connection pooling or serialization effects observed.

## Tools and Methodology

Supporting documentation on the profiling tools, techniques, and frameworks used across this folder.

- **[Profiling Tools](./profiling-tools.rst)** — v1.0.3, Platform Tools (Mara Olsen), updated 2024-04-27  
  Guide to the profiling tools and techniques used for performance investigation. Documents setup instructions for cProfile, memory_profiler, locust, and other utilities. Includes tips for interpreting profiler output and choosing the right tool for different measurement goals.

---

## Terminology

**Journal Mode**  
SQLite's mechanism for safely writing changes to disk. Immediate-write mode removes old content immediately; write-ahead logging (WAL) mode writes changes to a log before applying them to the main database. Choice of mode affects latency, durability guarantees, and concurrency behavior.

**Page Cache (or Buffer Pool)**  
In-memory cache of database pages. Larger caches reduce disk I/O at the cost of increased memory use. Size tuning is critical for throughput in workloads with working sets larger than available disk cache but smaller than main memory.

**Write-Ahead Logging (WAL)**  
A SQLite journaling mode where modifications are first written to a separate log file before being applied to the main database file. Enables higher concurrency than traditional modes because readers do not block writers and vice versa. Also known as write-ahead logging or log-structured mode.

**Flamegraph**  
Visualization technique for CPU profiling data, displaying call stacks as nested rectangles where the width of each rectangle represents time spent in that function or call path. Used to identify which functions spend the most CPU time and where optimization efforts should focus.

**Percentile Latency (p50, p95, p99)**  
Statistical measures of response time distribution. p50 is the median (50th percentile); p95 is the 95th percentile representing the threshold below which 95 percent of requests fall; p99 represents the tail of slow requests. Tail latencies (p95, p99) often matter more to users than average latency.

**Loopback Service**  
The HTTP service running locally on 127.0.0.1 (or similar localhost binding) without network transmission. Used for controlled performance measurement to measure inherent service latency without network effects, load balancer overhead, or remote host latency.

**Cold Start**  
The first invocation of the service or command-line tool after a system restart or after the database file has been evicted from the operating system's file cache. Involves disk I/O to load the database into memory and is typically 10-100x slower than warm start on modern systems.

**Warm Start**  
Subsequent invocations after the service has run recently or the database file is already present in the operating system's file cache. Initialization is limited to in-memory operations and is much faster than cold start. Warm start latency is often more representative of typical production behavior.

**RSS (Resident Set Size)**  
The portion of a process's allocated memory that is currently resident in physical RAM rather than paged to disk or in the swap file. Measured in kilobytes or megabytes. RSS varies based on system memory pressure and is often a better indicator of actual memory usage than virtual memory size.

**VSZ (Virtual Memory Size)**  
The total virtual memory allocated to a process, including pages that have been swapped to disk, shared libraries, and memory-mapped files. Typically larger than RSS but does not directly indicate physical memory usage. Useful for tracking memory range growth but less relevant for memory pressure analysis.

**Synchronous I/O (PRAGMA synchronous)**  
SQLite pragma controlling how carefully changes are written to disk. FULL requires synchronous disk writes (safest but slowest); NORMAL uses the OS file system cache (typical); OFF skips explicit synchronization (fastest but risks data loss on crash).

**GIL (Global Interpreter Lock)**  
Python runtime mechanism that serializes access to the interpreter state, allowing only one thread to execute Python bytecode at a time. Affects concurrency characteristics of the service when handling multiple concurrent requests.

---

## Repository Structure and Key Files

The performance-notes folder is located at `docs/performance-notes/` within the repository. It contains both narrative documentation pages and data files. Related profiling scripts and configuration are located in the `scripts/` directory.

| Path or File | Purpose |
|---|---|
| `docs/performance-notes/` | Root of this documentation folder. Contains all performance analysis pages and measurement data. |
| `docs/performance-notes/README.md` | This file. Index and guide to the performance notes folder. |
| `scripts/profile_service.py` | Python script to launch the HTTP service under cProfile control. Captures call stack profiling data and writes it to a file for later analysis. |
| `scripts/measure_response_times.sh` | Bash script that sends a stream of requests to the loopback service and records response times for percentile analysis. Supports configurable concurrency and duration. |
| `scripts/analyze_flamegraph.sh` | Post-processing script that reads cProfile output and generates flamegraph HTML visualization files for flame graph viewing. |
| `scripts/memory_profiler_runner.py` | Wrapper around the memory_profiler library that logs RSS and VSZ at regular intervals during service operation. Supports workload generation or analysis of real traffic patterns. |
| Cache measurement | Harness that measures throughput with different SQLite page cache sizes, holding other variables constant. Generates output suitable for graphing. |
| Load measurement | Harness using the locust framework to simulate multiple concurrent HTTP users accessing the loopback service. Reports response time percentiles. |
| `docs/` | Parent documentation folder. Contains architecture, design, and other documentation alongside performance notes. |
| `README.md` | Project README in repository root. Links to documentation sections including this performance notes index. |

SQLite configuration settings and profiling parameters are stored in version control when they represent team-wide conventions, but developers typically evaluate variants locally without committing them. Profiling output files (flamegraph HTML, cProfile data dumps, memory logs) are not committed; they are referenced from the documentation but stored in team shared storage.

---

## Tools and Versions

| Tool or Package | Version | Purpose | Notes |
|---|---|---|---|
| Python | 3.11+ | Runtime for the service, command-line tool, and profiling scripts. | All measurements assume Python 3.11+. Behavior may differ on earlier versions. |
| SQLite | 3.44.0+ | Database engine. Critical for database performance. | Behavior varies significantly by patch version; always note version when recording measurements. |
| cProfile | Built-in to Python 3.11 | CPU profiler. Generates call-stack data for flamegraph visualization. | Primary tool for identifying hot functions and call paths. |
| Memory profiling framework | 0.61.0 | Line-by-line profiling and RSS/VSZ logging at runtime. | Used for memory growth anomaly detection and tracking memory usage under load. |
| flamegraph | 1.2.11 | Visualization tool for CPU profiling data. Converts profiler output into interactive HTML flamegraph. | Installed separately; not part of the Python environment. |
| locust | 2.24.0 | Open-source load measurement framework for HTTP services. | Used for generating concurrent load against the loopback service. Supports hundreds of simultaneous virtual users. |
| psutil | 5.9.8 | Cross-platform library for querying system and process metrics (CPU, memory, I/O). | Used by helper scripts to query memory use and process state. |
| Unit evaluation framework | 7.4.3 | Used by some profiling harnesses for workload generation. | Optional; some measurement scripts use its utilities to structure measurement scenarios. |

---

## Change Log

**2026-08-14** — v1.0 released. Performance Notes Index created and organized into six categories. Linked all performance documentation pages with metadata. Added terminology section with twelve terms, tools table with version information, and expanded contribution guide. Established folder structure and file layout standards. (Mara Olsen, Platform Tools)

**2026-06-22** — Prepared stub index page and surveyed existing scattered performance documentation. Conducted interviews with Data Infra, Systems Reliability, and Developer Experience teams to understand current measurement work and identify gaps. Developed outline for folder organization and began consolidating pages. (Mara Olsen)

**2025-11-15** — Performance Notes folder formally established as centralized location for all performance analysis and measurement work. Core Services team (Devon Ruiz) and Systems Reliability team (Priya Nair) began migrating profiling notes previously stored in messages, chat, and personal wikis into structured markdown pages with consistent metadata. (Devon Ruiz, Priya Nair)

**2025-08-10** — Data Infra team completed initial SQLite tuning investigation based on findings from Q3 work on latency reduction. Created initial versions of SQLite Journal Mode Settings and Page Cache Size Tuning pages documenting configuration choices and trade-offs. Contributed baseline measurements from their standard measurement environment. (Lena Kowalski, Data Infra)

**2025-05-20** — Developer Experience team began focused work on startup time after user reports of slow cold starts in development environments. Created Startup Time Measurements and Cold Start Versus Warm Start pages documenting initialization phases and comparing startup behavior across machines. (Owen Fischer, Developer Experience)

**2024-11-05** — Profiling infrastructure set up by Platform Tools. Integrated cProfile, memory_profiler, and flamegraph tools into the repository. Added scripts for launching service under profiling, capturing output, and generating visualizations. Published initial version of Profiling Tools guide. (Mara Olsen, Platform Tools)

**2024-08-14** — Initial write-throughput measurements conducted by Core Services under various SQLite configurations. Provided empirical foundation for later journal mode and cache size tuning work. (Devon Ruiz, Core Services)

---

## Contribution Guide

The Performance Notes folder documents ongoing investigation and measurement work. Contributions follow these conventions to maintain consistency and usability.

**When Running Profiling Sessions:**

Each profiling session should be logged in the Profiling Session Log with the following information: date and time of session start, machine hardware specification (CPU model, RAM, disk type), operating system version, package version being profiled, SQLite version, workload profile (read-only, write-heavy, mixed), profiling tools active, duration of the profiling run, and high-level findings. If your session involves multiple tools running simultaneously (e.g., cProfile and memory_profiler together), note which tools were active and any interactions between them.

If your session is longer than one hour or involves significant findings, create an entry in the Profiling Session Log; shorter ad-hoc profiling runs can be noted in a related page's change log if the results contribute to that page's content.

**When Measuring Performance:**

Always document the measurement environment, including machine specification, operating system version, SQLite version, package version, any non-default configuration (journal mode, cache size, synchronous level), and the workload pattern used (number of concurrent users, request rate, request type distribution). Without this context, measurements cannot be meaningfully compared or reproduced.

Include multiple runs if possible to assess consistency. If results vary significantly between runs, investigate whether system load, caching, or other factors are affecting the measurement. Note any anomalies or unexpected behavior observed during measurement.

**File Naming and Storage:**

Large measurement files (flamegraph captures, profiler data dumps, memory logs) should be stored outside version control and referenced by relative path or URL from the documentation page. Name files consistently using the date and a brief description: `flamegraph_20260814_10k_writes.html`, `memory_log_20260810_warm_startup.txt`, `cprofile_20260820_loopback_50concurrent.prof`. This makes it easier to locate and compare related measurements.

**Documentation Format and Structure:**

Prefer Markdown for narrative documentation (page tuning guidance, session notes, methodology); use YAML for structured baseline data; use plain text for logs and timestamped records; use reStructuredText for reference documentation or pages with complex table formatting.

Every page must include a header block with title, version number, owner (person or team), and last-updated date. Use consistent version numbering across the folder (either v1.0 style or 1.0 style; this folder uses both; do not mix within a single page).

Include section headings appropriate to your content. Add a terminology section for any specialized terms or metrics unique to that page. Include a file/path reference section listing repository files mentioned in the page. Include a table of tools or settings discussed. Include a change log with dated entries naming releases or significant updates. Add a related-pages section linking to sibling pages and cross-referenced documentation.

**Version Numbers and Updates:**

Increment the version number when you make material changes to content (new measurements, revised recommendations, corrected data). Minor adjustments or formatting changes do not require a version bump. Update the Last Updated date whenever you modify a page, even for minor edits.

Do not remove pages; if a page becomes obsolete, mark it as superseded. Update this index and related-pages sections to reflect the change.

**Metadata Consistency:**

Check that owner information is accurate and corresponds to the team member or team responsible for the page. If ownership transfers, update the header. Keep tools table versions current and note if a tool is no longer in use. When linking to sibling pages, use relative paths and verify the linked page exists and the metadata in your link matches the target page's header block (or note intentionally if it lags behind).

---

## Related Pages

- **[Profiling Tools](./profiling-tools.rst)** — v1.0.3 — Guide to tools, techniques, and setup for all profiling work in this folder. Start here if you are new to profiling or setting up a new measurement scenario.

- **[Concurrency Notes](./concurrency-notes.rst)** — v2.4 — Behavior under concurrent load. Explains GIL effects, lock contention, and scaling characteristics that affect response time under multiple simultaneous requests.

- **[Baseline Measurements](./baseline-measurements.yaml)** — v1.0 — Reference performance numbers in the standard measurement environment. Use as a point of comparison when evaluating improvements or detecting regressions.

- **[Write Throughput on the Database File](./write-throughput.md)** — v1.1.0 — Write performance under various configurations. Complements both the SQLite tuning pages and the loopback response time measurements.

- **[SQLite Journal Mode Settings](./sqlite-journal-mode.md)** and **[Page Cache Size Tuning](./page-cache-sizing.md)** — Configuration guidance pages maintained by Data Infra. Read together as cache and journal mode interact.

---

**Maintained by:** Platform Tools (Mara Olsen)  
**Review frequency:** Quarterly  
**Last Review Date:** 2026-08-14

# Journal Mode Notes for the Database File

| Field | Value |
|-------|-------|
| **Title** | Journal Mode Notes for the Database File |
| **Version** | v1.3.0 |
| **Owner** | Infra Reliability (Priya Nandakumar) |
| **Last Updated** | 2024-07-22 |

## Summary

This page describes the write-ahead log setting used for the database file and how it changed observed write timing on loopback. The service maintains its state in a local SQLite file, and journal mode configuration significantly affects latency and concurrency behavior under typical workloads. We document the settings currently deployed, the measurements that drove their adoption, and the profiling techniques used to evaluate them.

## Overview

The package uses SQLite for persistent state with a single database file stored on the local filesystem. SQLite's journal mode determines how the database coordinates writes between concurrent readers and writers, affecting both latency and throughput. Early deployments used SQLite's default rollback journal mode; evaluation in 2023 and 2024 led to adoption of write-ahead log mode on production instances.

This document records the configuration applied since mid-2024, the profiling methodology that validated the change, observed timing improvements on loopback, and guidance for future tuning work.

## Understanding Journal Mode in SQLite

*Section owner: Platform Tools (Mara Olsen)*

SQLite provides multiple mechanisms for coordinating database changes. The journal mode setting controls how the database engine handles transaction isolation and crash restoration:

- **Rollback journal mode (legacy)**: The traditional approach. Before modifying the database file, SQLite writes changes to a separate journal file and syncs it to disk. If a crash occurs during a transaction, the journal file remains on disk and can be used to roll back incomplete changes on restart. Once the transaction commits, the journal file is removed.

- **Write-ahead log mode (WAL)**: Changes are first written to a separate log file without modifying the main database file. The log is periodically checkpointed back into the main database file. This mode provides better concurrency because readers can access the main database while writers append to the log.

The choice of journal mode has measurable effects on write latency, read concurrency, and disk I/O patterns. On loopback exercises with the service's typical access patterns, write-ahead log mode showed consistent improvements in P95 and P99 write latency.

## Configuration Applied to oauthsvc

*Section owner: Infra Reliability (Priya Nandakumar)*

The service currently uses write-ahead log mode with the following SQLite pragmas applied at database initialization:

```
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -8000;
PRAGMA wal_autocheckpoint = 100000;
```

These settings were adopted following profiling work in April and May of 2024. The journal mode setting activates write-ahead logging. The synchronous level balances durability and performance; NORMAL mode skips syncing the main database file after consolidation operations, relying on the operating system's eventual consistency. The cache size and consolidation frequency threshold are tuned specifically for this service's workload and are documented separately in the page Cache Sizing for the Database File.

Previous deployments used the default rollback journal mode (legacy). That configuration is no longer recommended for new instances, though some production systems may still operate with it for legacy reasons.

## Profiling Approach and Methodology

*Section owner: Core Services (Devon Ruiz)*

The choice to switch journal modes was informed by profiling work conducted on loopback instances in 2024. The methodology involved:

1. **Instrumentation**: The service's loopback HTTP interface was instrumented with timing hooks to measure request latency at multiple points: request reception, database operations, and response transmission.

2. **Workload generation**: A load generator was run against the loopback service with varying concurrency levels (1, 4, 8, 16, and 32 concurrent connections) to simulate realistic traffic patterns.

3. **Metric collection**: Latency histograms were collected for write operations, read operations, and mixed workloads. Both wall-clock time and CPU time were recorded.

4. **Baseline establishment**: Trials were run with the default rollback journal mode first, establishing baseline figures for comparison.

5. **Configuration sweep**: The same workload was repeated with write-ahead log mode enabled, adjusting consolidation frequency and cache settings between runs.

6. **Statistical analysis**: Results were aggregated into percentile distributions (P50, P95, P99, P99.9) and compared across configurations.

Detailed results from the 2024 profiling sessions are documented in the sibling pages Profiling Sessions, 2024 and Profiling Sessions, 2025. Raw timing data is stored in the scripts/profiling directory.

## Measured Impact on Write Latency

*Section owner: Runtime Team (Owen Baptiste)*

Write-ahead log mode reduced write operation latency consistently across all observed concurrency levels. The following table summarizes representative results from profiling conducted in May 2024:

| Concurrency | Journal Mode | P50 Latency (ms) | P95 Latency (ms) | P99 Latency (ms) |
|-------------|--------------|------------------|------------------|------------------|
| 1 | Rollback (legacy) | 0.8 | 2.1 | 4.3 |
| 1 | WAL | 0.6 | 1.4 | 2.8 |
| 4 | Rollback (legacy) | 1.2 | 4.7 | 9.2 |
| 4 | WAL | 0.9 | 2.3 | 5.1 |
| 8 | Rollback (legacy) | 1.5 | 6.3 | 12.8 |
| 8 | WAL | 1.1 | 3.1 | 7.6 |
| 16 | Rollback (legacy) | 2.4 | 9.8 | 18.1 |
| 16 | WAL | 1.8 | 4.9 | 11.3 |

At higher concurrency levels, the advantage became more pronounced. The P99 latency with rollback mode at 16 concurrent connections (18.1 ms) was more than 1.5× higher than with write-ahead log mode (11.3 ms). This difference reflects reduced contention on the database lock: write-ahead log mode allows readers to proceed while writers are appending to the log, whereas rollback mode must block readers until the transaction completes and the journal is removed.

Memory use increased slightly with write-ahead log mode enabled due to the `cache_size` setting and the in-memory structures required to track log state. Observed resident memory size increased from approximately 32 MB to 38 MB on loopback instances under steady-state load. This trade-off was deemed acceptable given the latency improvements. See Memory Use Baseline for a complete accounting.

## Log Consolidation Behavior and Management

Log consolidation operations are the mechanism by which write-ahead log mode persists accumulated changes to the main database file. The consolidation frequency threshold controls when consolidation occurs, specified as the maximum number of pages written to the log before consolidation is triggered.

With consolidation frequency set to 100,000 pages, consolidation operations were observed to occur roughly every 50–150 milliseconds under normal write load. Each consolidation operation required 5–15 milliseconds on the loopback instance. Users experienced these as occasional latency spikes, but the median latency remained well below baseline Rollback mode performance.

Consolidation operations can be tuned further. Reducing the consolidation frequency threshold below 50,000 pages caused consolidation to occur more frequently, increasing overall CPU overhead. Increasing it above 150,000 allowed the log to grow larger, using additional disk space and occasionally causing multi-second consolidation operations. The current setting of 100,000 was selected as a balance point after experimentation.

Manual data consolidation can be forced using standard SQLite tools if needed, though this is rarely necessary.

## Log File Storage and Disk I/O

Write-ahead log mode creates two additional files alongside the main database file:

- The write-ahead log file (named with a `-wal` suffix)
- The log consolidation index file (named with a `-shm` suffix)

On production systems, these files are stored in the same directory as the main database file on the local filesystem. The log file grows as writes occur and is truncated during consolidation operations. Disk space usage varies with write volume; typical deployments observed 10–50 MB of log and index files at any given moment.

Disk I/O patterns changed measurably. Rollback mode produced frequent small fsync operations as journal files were written and removed. WAL mode produces larger, more predictable I/O patterns during consolidation operations. On systems with mechanical storage, this resulted in marginally lower sustained I/O overhead, though the effect was smaller than latency improvements on SSDs.

## Startup Time Considerations

The service's startup time is documented separately in Startup Time Notes. Journal mode choice affects startup time when the database file must be restored after an unclean shutdown. With write-ahead log mode, restoration involves replaying the log file, which may take additional time if the log is large. In practice, most deployments complete restoration in under 100 milliseconds. If restoration time becomes a concern, the log can be consolidated before shutdown using standard SQLite pragmas.

## Compatibility and Deployment Notes

Write-ahead log mode is supported on all platforms where the service runs and is compatible with all SQLite versions in use (3.10+). The `-wal` and `-shm` files created by the service are cleaned up automatically when the last connection closes, so manual cleanup is rarely needed.

One caveat: network filesystems (NFS, SMB) may not properly support write-ahead log mode because the required locking and memory-mapped I/O semantics are not guaranteed. If the service is ever deployed to a network-backed storage system, this should be verified or rollback mode should be restored.

## Interaction with Other Performance Tuning

The choice to use write-ahead log mode and the specific parameter values interact with several other configuration settings:

- **Page cache size**: Documented separately in Page Cache Sizing for the Database File. Larger cache sizes reduce disk I/O; the current `-8000` setting (approximately 8 MB) was tuned in conjunction with WAL mode.

- **Connection pooling**: Documented in Connection Reuse Notes for the Database File. WAL mode allows better concurrency, reducing the performance penalty for pools with limited connections.

- **Garbage collection tuning**: The service is written in Python. GC behavior interacts with SQLite latency because GC pauses can block database threads. See Garbage Collector Tuning Notes for details.

Cold vs. warm startup behavior with write-ahead log mode is discussed in Cold Start Versus Warm Start Timing.

## Recommendations for Future Work

For new deployments, write-ahead log mode with the configuration shown in this page should be the default. If specific workloads show different characteristics (very high concurrency, infrequent writes, or memory-constrained environments), targeted profiling should be conducted to validate the choice.

The `synchronous = NORMAL` setting is appropriate for this service because data loss on crash is acceptable (the service can be restarted and reconnected). If durability requirements change, this should be increased to FULL, with the understanding that write latency will increase.

If disk space becomes a constraint, the consolidation frequency threshold can be reduced to limit log growth, accepting more frequent consolidation and CPU overhead. If latency consistency is a priority, consolidation operations can be scheduled explicitly during off-peak periods rather than relying on automatic triggering.

## Terminology

**Log Consolidation**: The operation by which write-ahead log mode writes accumulated changes from the log file back into the main database file. Consolidation occurs automatically at intervals or can be triggered manually.

**Journal mode**: The SQLite configuration setting that determines how the database engine coordinates writes, particularly the mechanism for restoring after crashes. Common modes include Rollback (legacy) and WAL (write-ahead log).

**Rollback journal (legacy mode)**: Traditional SQLite journal mode in which changes are recorded in a separate journal file before being written to the main database file. The journal is removed after a successful transaction commit.

**Write-ahead log (WAL)**: An alternative journal mode in which changes are written to a log file, and the log is periodically merged into the main database file via consolidation operations. Allows better read-write concurrency than Rollback mode.

**Synchronous level**: A SQLite pragma controlling whether the database engine issues explicit fsync operations. NORMAL skips fsync for the main database file after consolidation operations; FULL issues fsync for all operations. Lower levels increase performance but reduce durability guarantees.

**Cache size**: A SQLite pragma controlling the size of the in-memory page cache. Larger caches reduce disk I/O at the cost of increased memory use.

**Consolidation frequency threshold**: The maximum number of pages written to the log before consolidation is automatically triggered. Smaller thresholds cause more frequent consolidation operations; larger thresholds allow the log to grow larger.

**Latency percentile**: A measure of request latency at a specific percentile, such as P95 (95th percentile—the latency value below which 95% of requests fall). Used to characterize tail latency.

## File and Path References

| Path | Purpose |
|------|------|
| `docs/performance-notes/` | Folder containing performance documentation pages |
| `scripts/profiling/` | Directory holding profiling scripts, load generators, and raw timing data from 2024 and 2025 sessions |
| scripts/profiling/loopback-harness.py | Load generation script for loopback exercises |
| `docs/performance-notes/perf-baselines.yaml` | Canonical baseline performance figures by version |

## Tools and Versions

| Tool / Library | Version | Purpose |
|---|---|---|
| SQLite | 3.42.0 (production), 3.45.1 (dev) | Database engine and pragmas |
| Python | 3.11.8 | Service runtime |
| cProfile | built-in | CPU profiling of loopback runs |
| sqlite3 shell | 3.42.0 | Manual inspection of database files and pragmas |

## Change Log

**2024-07-22 — v1.3.0 (Priya Nandakumar)**
Incorporated findings from loopback profiling conducted in June 2024. Updated latency tables and log consolidation behavior section based on new measurements with page cache size set to -8000.

**2024-05-17 — v1.2.1 (Infra Reliability)**
Clarified interaction between WAL mode and network filesystems. Added compatibility notes for deployment scenarios.

**2024-05-10 — v1.2 (Priya Nandakumar)**
First comprehensive measurement results from Profiling Sessions, 2024. Documented baseline Rollback mode performance and initial WAL mode benefits. Applied configuration to staging instances.

**2024-04-28 — v1.1 (Mara Olsen)**
Added section on log consolidation behavior and log file management. Updated related-pages links to point to Profiling Tools Setup.

**2024-03-15 — v1.0.1 (Priya Nandakumar)**
Initial version. Documented journal mode overview and proposed WAL configuration based on prior measurement work.

**2024-02-20 — v1.0 (Infra Reliability)**
Created stub page to track upcoming journal mode evaluation work.

## Related Pages

- Performance Notes: Index — overview of the performance documentation folder
- Profiling Sessions, 2024 — detailed results from spring and summer 2024 loopback profiling runs
- Profiling Sessions, 2025 — follow-up profiling conducted in 2025 after optimization work
- Page Cache Sizing for the Database File — tuning of the `cache_size` pragma in conjunction with WAL mode
- Loopback Response Time Figures — aggregated latency measurements across configurations
- Memory Use Baseline — resident memory under WAL mode with tuned parameters
- Startup Time Notes — service initialization time and restoration behavior
- Cold Start Versus Warm Start Timing — comparison of first-run vs. steady-state latency
- Profiling Tools Setup — instrumentation and load generation tools used for evaluation
- Garbage Collector Tuning Notes — interaction between Python GC and SQLite latency
- Connection Reuse Notes for the Database File — pooling strategies and their interaction with WAL mode
- Flame Graph Capture Steps — visualization of CPU time across profiling sessions

# Connection Reuse Notes for the Database File

**Title:** Connection Reuse Notes for the Database File  
**Version:** v1.5.2  
**Owner:** Infra Reliability (Priya Nandakumar)  
**Last Updated:** 2025-12-01  
**Summary:** Describes how the service reuses connections to the database file and the effect on timing under repeated loopback calls.

---

## Overview

The service maintains a persistent connection to its local SQLite database file rather than opening and closing a fresh connection on each request. This document covers the mechanisms that enable connection reuse, the configuration tuning that affects performance, and the measured results from profiling runs across the loopback network stack.

Connection reuse provides substantial benefits to response latency and startup overhead, but the gains are sensitive to SQLite journal mode, page cache allocation, and the underlying file system behavior on the host. This page gathers practical procedures for measuring and tuning these settings.

---

## How Connection Reuse Works

**Section Owner:** Platform Tools (Mara Olsen)

The service establishes a single connection to the database file during initialization and holds that connection open for the lifetime of the process. Incoming loopback requests reuse that same connection handle rather than acquiring a new one. This approach avoids the per-request overhead of connection setup, which includes file handle acquisition, database file locking negotiation, and initial WAL (write-ahead log) or rollback journal access.

The connection remains open whether the loopback HTTP service is idle or actively handling requests. When a request arrives, it uses the already-open connection without additional setup cost. Requests are serialized through a single background thread that owns the connection, ensuring thread-safe access without explicit locking around the connection object itself.

Connection pooling—in the traditional sense of maintaining a pool of multiple connection objects to handle concurrent requests—is not used. The single-connection design trades off concurrency for simplicity and predictability. Loopback traffic to the service is typically light, so the serialization does not become a bottleneck in practice.

---

## Database File Configuration and Tuning

**Section Owner:** Infra Reliability (Priya Nandakumar)

### Journal Mode

The journal mode selected at database initialization significantly affects write latency and startup time. The service uses a configurable journal mode set via the `PRAGMA journal_mode` directive at first-connection time.

**Recommended setting for loopback service:** `WAL` (write-ahead log) mode. WAL mode allows readers to continue using old versions while a writer updates the database, reducing lock contention. Startup time is marginally higher due to WAL file management, but steady-state loopback response times improve.

**Alternative setting:** `TRUNCATE` mode, which does not require WAL files but incurs higher latency per write and is not recommended for services that handle rapid request bursts.

See the sibling page *Journal Mode Notes for the Database File* for detailed analysis and configuration steps.

### Page Cache Size

SQLite maintains an in-memory cache of pages from the database file. Larger caches reduce disk I/O for repeated reads within the same request or across consecutive requests. The page cache is configured via `PRAGMA cache_size`.

**Default setting:** 2,000 pages (approximately 8 MB on a typical 4 KB page size).

**Recommended tuning:** Start with 5,000 to 10,000 pages for the service's typical working set. Measure memory overhead and response time; the benefit plateaus once the entire active portion of the database fits in cache. Do not exceed 20,000 pages without measuring the memory impact on the host.

See *Page Cache Sizing for the Database File* (version 2.1, updated 2025-02-14) for detailed tuning procedures and memory profiles.

### Foreign Key Constraints

Foreign key constraints are disabled by default in SQLite. The service does not enable them. Enabling them would add per-write overhead that is not justified by the database schema design.

---

## Profiling Sessions and Methodology

**Section Owner:** Platform Tools (bgigurtsis@gmail.com)

### Session Setup

Profiling sessions measure response time, memory use, and CPU utilization during repeated loopback calls to the service. Sessions run on the developer's local machine or on a dedicated profiling host to minimize interference from other processes.

**Prerequisites:**
- The service must be built and installed locally.
- The profiling scripts are located in `scripts/profiling/` directory.
- Use a freshly initialized database file to ensure consistent cold-start conditions across runs.

### Capturing a Profiling Session

1. **Prepare the environment:** Set the database file path to a temporary location or a dedicated profiling directory. Ensure no other instances of the service are running.

2. **Start the service:** Launch the service with loopback binding (default: `127.0.0.1:8080`). Allow 2–3 seconds for startup and WAL initialization to complete.

3. **Record baseline memory and startup time:**
   ```
   wmic process get name,processid,workingsetsize | find "oauthsvc"
   ```
   or use the `psutil`-based script in `scripts/profiling/capture_memory.py` (note: this is a general script, not oauthsvc-specific).

4. **Send loopback requests:** Use the loopback request harness in `scripts/profiling/loopback_harness.py`. Send 100–500 requests in rapid succession (one per 10–50 ms). Record the response time and status code for each request.

5. **Monitor during the session:** Use `sqlite3` to inspect the WAL file size and page cache statistics (via `PRAGMA stats`).

6. **Capture end-state memory:** Record memory use after the session completes.

7. **Preserve logs and data:** Copy the database file, WAL file, and any shared-memory files to a dated subdirectory under `docs/performance-notes/raw-data/` for storage.

### Example: Running a quick profiling session


---

## Loopback Response Time Measurements

**Section Owner:** Runtime Team (Owen Baptiste)

### Baseline Figures

The following table summarizes response times from recent profiling sessions run on a Windows 10 Pro host (Intel i7-8700K, 16 GB RAM) with WAL mode and a 10,000-page cache.

| Metric | Value | Notes |
|--------|-------|-------|
| Median response time (first request) | 45 ms | Cold connection; WAL file initialization included. |
| Median response time (steady state, requests 50–200) | 8–12 ms | Connection reused; no per-request setup. |
| P95 response time (steady state) | 18 ms | Occasional file I/O delays. |
| P99 response time (steady state) | 35 ms | Rare cache misses or disk contention. |

For more detailed figures and per-request breakdowns, see *Loopback Response Time Figures* (version v2.0.1, updated 2025-05-30).

### Variance Across Configurations

Response time varies substantially with journal mode and cache size. TRUNCATE mode shows 15–25% higher median latency than WAL mode in steady state. Cache sizes below 2,000 pages introduce periodic spikes (50–100 ms) when the cache misses and the database file must be read from disk.

---

## Memory Use During Connection Lifetime

**Section Owner:** Runtime Team (Owen Baptiste)

The service's memory footprint grows as the page cache fills and remains relatively stable afterward, assuming no runaway allocations in other subsystems.

### Baseline Memory Profile

- **Startup (just initialized connection):** 25–30 MB resident set size (RSS).
- **After 100 loopback requests:** 35–45 MB (cache filling).
- **Steady state (cache full):** 45–55 MB (depends on cache_size setting).

A 10,000-page cache (40 MB page data) accounts for most of the steady-state footprint. The remainder comes from SQLite internal structures, the loopback HTTP server, and Python runtime overhead.

See *Memory Use Baseline* (version 1.1, last updated 2024-06-09) for prior comparison. Note: that page used a 5,000-page cache; newer profiles use 10,000 pages.

### Monitoring Memory During Operation

Use the Windows Performance Toolkit or a simple polling script to track memory over time:

```
# PowerShell: capture memory every 5 seconds for 60 seconds
$processName = "oauthsvc"
$count = 0
while ($count -lt 12) {
  (Get-Process -Name $processName -ErrorAction SilentlyContinue).WorkingSet / 1MB | Write-Output
  Start-Sleep -Seconds 5
  $count++
}
```

Memory should rise quickly in the first 30–60 seconds (as the cache fills) and then plateau. If memory continues to grow linearly, investigate for accumulating connection objects or unbounded caches.

---

## Startup Time Characteristics

The service's startup time has two phases: connection initialization (which includes database file open and WAL setup) and HTTP server binding. Together they typically take 1–3 seconds on a local machine.

**Phase 1: Connection initialization**  
- File handle acquisition: ~5–15 ms.
- WAL mode negotiation and file creation: ~20–40 ms (higher on slow disks).

**Phase 2: HTTP server startup**  
- Socket binding and listen queue setup: ~10–20 ms.

Recent startup time notes (version 1.9, updated 2026-01-27) provide detailed breakdowns by platform. On Windows, startup is generally slightly slower than on Linux due to file I/O patterns, but differences are small for loopback configurations.

---

## Terminology and Glossary

**Connection Handle**  
A reference to an open connection to the SQLite database file, held by the service's main process. The handle remains valid until the process exits or an error forces a reconnect.

**Journal Mode**  
The mechanism SQLite uses to ensure atomicity of writes when the database file is updated. Common modes are WAL (write-ahead log), TRUNCATE, and standard mode. Journal mode is set once at database initialization and cannot be changed without recreating the database.

**Loopback Network**  
The `127.0.0.1` interface on a single host, used for inter-process communication via HTTP. Loopback traffic does not leave the host and is not subject to external network latency.

**Page**  
A fixed-size unit of data (typically 4,096 bytes) stored in the SQLite database file. SQLite reads and writes in page-sized increments.

**Page Cache**  
SQLite's in-memory buffer that holds recently used pages. Larger caches reduce disk I/O when the same pages are accessed repeatedly.

**Reuse** (in connection context)  
The practice of keeping a connection open and using it for multiple sequential or concurrent operations, rather than opening and closing a connection for each operation.

**Response Time**  
The elapsed time from when a loopback request is sent to the service until the response status and headers are received by the caller. This includes network stack overhead but excludes caller-side processing.

**WAL File**  
The write-ahead log file (`-wal` suffix) that SQLite creates in WAL mode. It holds recent changes before they are merged into the main database file. WAL files improve concurrency at the cost of extra disk I/O during sync operations.

**Working Set Size**  
The portion of the process's memory that is actively used and likely to remain in physical RAM. On Windows, this is reported by the `WorkingSet` property; on Unix, it approximates RSS (resident set size).

---

## Repository Files and Paths

| Path | Purpose |
|------|------|
| `oauthsvc/` | Package root directory; contains the main service code. |
| `docs/performance-notes/` | Documentation folder for this and related performance pages. |
| `docs/performance-notes/README.md` | Index of all performance documentation (version 1.6). |
| `scripts/profiling/loopback_harness.py` | Script to send repeated loopback requests and measure response times. |
| `scripts/profiling/capture_memory.py` | Memory profiling utility using system APIs. |
| `scripts/profiling/` | Directory containing all profiling helper scripts. |
| `docs/performance-notes/raw-data/` | Directory for storing database files and measurement logs from profiling sessions. |

---

## Tools and Dependencies

| Tool / Library | Version | Purpose |
|---|---|---|
| Python | 3.10 or later | Runtime for the service and profiling scripts. |
| SQLite | 3.36+ | Database engine embedded in Python. |
| Windows Performance Toolkit | Latest (from Windows ADK) | Memory and CPU profiling on Windows hosts. |
| sqlite3 (CLI) | 3.36+ | Ad-hoc inspection of database files, PRAGMA settings, and WAL statistics. |
| psutil | 5.9+ | Cross-platform memory and process monitoring (optional, used by some profiling scripts). |
| git | 2.30+ | Version control for profiling scripts and stored results. |

---

## Changelog

**v1.5.2** — 2025-12-01  
- Added Page Cache Sizing section with reference to updated sibling page (v2.1).
- Clarified that connection pooling in the traditional sense is not used.
- Updated baseline memory figures to reflect 10,000-page cache (previously 5,000).

**v1.5.1** — 2025-11-15  
- Fixed markdown formatting in response time table.
- Corrected P99 latency figure from 28 ms to 35 ms based on latest profiling runs.

**v1.5** — 2025-10-20  
- Initial consolidation of connection reuse and configuration tuning into single document.
- Added example profiling session command snippets.
- Cross-referenced Memory Use Baseline page (v1.1).

**v1.4.2** — 2025-09-10  
- Minor clarification on WAL file lifecycle during startup.
- Removed outdated notes on TRUNCATE mode performance (now covered in separate Journal Mode Notes page).

**v1.4** — 2025-08-05  
- Added Loopback Response Time Measurements section with baseline table.
- Updated P95 latency figures based on 2025 profiling sessions.

**v1.3** — 2025-07-12  
- Added terminology section with eight core definitions.
- Reorganized sections by performance domain (connection, database config, memory, startup).

---

## Related Pages

- *Performance Notes: Index* (version 1.6, Platform Tools, updated 2026-05-11) — Overview and navigation for all performance documentation.
- *Profiling Sessions, 2024* (version 1.2, Core Services, updated 2024-11-04) — Early session data and methodology from 2024.
- *Profiling Sessions, 2025* (version 1.4, Platform Tools, updated 2025-09-18) — Current profiling results and session reports.
- *Journal Mode Notes for the Database File* (version v1.3.0, Infra Reliability, updated 2024-07-22) — Detailed journal mode selection and tuning guide.
- *Page Cache Sizing for the Database File* (version 2.1, Infra Reliability, updated 2025-02-14) — In-depth page cache tuning and memory impact analysis.
- *Loopback Response Time Figures* (version v2.0.1, Runtime Team, updated 2025-05-30) — Detailed response time measurements and per-percentile breakdowns.
- *Memory Use Baseline* (version 1.1, Runtime Team, updated 2024-06-09) — Baseline memory footprint across different configurations.
- *Startup Time Notes* (version 1.9, Platform Tools, updated 2026-01-27) — Detailed startup time analysis by phase and platform.
- *Cold Start Versus Warm Start Timing* (version v1.0.2, Platform Tools, updated 2025-08-03) — Comparative analysis of initial request latency versus steady-state performance.
- *Profiling Tools Setup* (version 1.0, Core Services, updated 2024-04-16) — Installation and configuration of profiling utilities.
- *Garbage Collector Tuning Notes* (version 2.4, Runtime Team, updated 2026-03-19) — Python GC tuning for reduced latency variance.
- *Flame Graph Capture Steps* (version 1.3, Platform Tools, updated 2024-09-27) — Instructions for generating CPU flame graphs during profiling.
- *Performance Baseline Figures* (version 2.6, Platform Tools, updated 2026-06-15) — Consolidated baseline metrics across all performance domains.

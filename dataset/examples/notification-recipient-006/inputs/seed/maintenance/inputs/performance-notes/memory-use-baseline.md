# Memory Use Baseline

**Version:** 2.0
**Owner:** Infrastructure (Sana Byrne)
**Last updated:** 2024-08-03

---

## Summary

This page collects the baseline memory figures for the `accountsvc` process under a set of typical and heavy usage patterns, along with the SQLite settings and profiling conditions used to produce them. It's meant as a reference point for anyone investigating a regression, not as a live dashboard — numbers here are from specific measurement sessions on specific dates and will drift as the codebase and host images change.

This page covers: profiling session setup, SQLite pragmas relevant to memory (journal mode, page cache size, mmap size), loopback response time figures collected as a side effect of the same sessions, startup time, and resident memory under idle, typical, and heavy load. It does not attempt to explain internals of how the service is put together — that falls outside this performance notes page.

---

## Terminology / Glossary

- **RSS (Resident Set Size)** — the portion of process memory held in RAM, as reported by the OS; the primary figure tracked on this page.
- **VSZ (Virtual Size)** — total virtual memory space reserved by the process, usually far larger than RSS and less useful for capacity planning.
- **Page cache (SQLite)** — the in-memory cache SQLite keeps of database pages, sized via the `cache_size` pragma; distinct from the OS-level page cache.
- **Journal mode** — the mechanism SQLite uses to make writes durable across a crash; the two relevant here are the rollback journal mode and `WAL` (write-ahead log).
- **mmap_size** — a SQLite pragma controlling how much of the database file is mapped into the process's virtual memory space rather than read through ordinary file I/O.
- **Loopback** — network traffic that never leaves the host, sent to 127.0.0.1; used here for response time measurement without external network variance.
- **Warm start** — process start where the OS file cache already holds the database file's pages from a previous run.
- **Cold start** — process start after the database file and shared libraries have been evicted from OS file cache (approximated locally with `posix_fadvise DONTNEED` equivalents or a reboot).
- **Working set** — informally, the set of database pages actively touched during a given workload pattern (typical vs. heavy), as opposed to the full file size.
- **Idle baseline** — RSS measured after startup with no requests served, used as the floor for all other comparisons.

---

## Profiling Sessions — Owner: Runtime Performance (Priya Nandakumar)

Memory figures on this page are derived from two profiling sessions, cross-referenced with `profiling-sessions-2024.md`. Session methodology is shared across pages in this folder; the short version:

1. Build the package in an isolated virtual environment (`python -m venv`), install with `pip install -e .` from the repository root.
2. Copy a known-size database file (10 MB "typical" sample, 240 MB "heavy" sample — these are informal names for the two seed files kept in `scripts/seed-db/`) into a scratch path.
3. Start the process, let it settle for 30 seconds, capture idle RSS.
4. Run the loopback load pattern (see below) for 5 minutes, sample RSS every 10 seconds.
5. Stop the process, record final figures, discard the scratch database copy.

Sampling was done with plain OS tools rather than an in-process profiler, to avoid skewing the numbers with instrumentation overhead:

```
# Linux
while true; do
  ps -o rss,vsz -p $(pgrep -f accountsvc) --no-headers
  sleep 10
done >> /tmp/accountsvc-rss.log
```

```
# Windows (PowerShell)
while ($true) {
  Get-Process -Name accountsvc | Select-Object WS, VM |
    Add-Content -Path C:\scratch\accountsvc-rss.log
  Start-Sleep -Seconds 10
}
```

Two sessions feed the numbers below:

| Session ID | Date | Host | Pattern | Notes |
|---|---|---|---|---|
| MEM-2024-06-A | 2024-06-11 | linux-perf-03 (bare metal, 16 GB) | typical | Baseline for this page |
| MEM-2024-07-B | 2024-07-29 | linux-perf-03 | heavy | Re-run after cache_size change |

A third session (MEM-2024-05-C, 2024-05-02) was discarded — the sample database was accidentally the heavy sample while the pattern generator was set to typical, giving numbers that didn't reconcile with anything. Left here as a note in case anyone finds that log file lying around in `scripts/logs/` and wonders why it doesn't match.

---

## SQLite Settings Being Measured — Owner: Data Systems (Devon Ruiz)

The database file lives at a configurable path, default `~/.accountsvc/accountsvc.db` on POSIX hosts and `%APPDATA%\accountsvc\accountsvc.db` on Windows. Three pragmas matter for memory baselining:

| Pragma | Typical setting | Heavy setting | Effect on memory |
|---|---|---|---|
| `journal_mode` | `WAL` | `WAL` | WAL mode keeps a separate `-wal` file; adds a small fixed overhead (roughly 1–2 MB resident) versus rollback journal mode, offset by better write throughput |
| `cache_size` | `-4000` (4 MB) | `-16000` (16 MB) | Negative values are KB; page cache is the single largest tunable contributor to RSS growth under sustained load |
| `mmap_size` | `0` (disabled) | `67108864` (64 MB) | mmap'd pages show up in VSZ immediately but only inflate RSS as pages are actually touched |

Applied via the standard `sqlite3` command-line tool against a copy of the database file for inspection (never applied to a live file in place while the service holds it open):

```
sqlite3 accountsvc.db "PRAGMA journal_mode=WAL;"
sqlite3 accountsvc.db "PRAGMA cache_size=-16000;"
sqlite3 accountsvc.db "PRAGMA mmap_size=67108864;"
```

The heavy-pattern session (MEM-2024-07-B) used `cache_size=-16000` specifically to check whether the page cache was the dominant contributor to the RSS growth observed under sustained load in the June session — it was, accounting for roughly 60% of the delta between idle and 5-minute RSS.

For deeper background on why `WAL` was chosen over rollback journal mode, see `sqlite-journal-mode-notes.md`. Note that as of the housekeeping page's last update, WAL flushes run more aggressively than described here — this page's numbers predate that change and may read slightly high on `-wal` file size as a result, though the impact on process RSS is negligible.

---

## Idle and Startup Memory

Startup time and idle memory were measured together, since both come from the same cold/warm start cycle. See `startup-time-tracking.md` for the canonical startup timing numbers; the figures below are memory-focused and were captured in the same sessions but are not identical measurements.

| Condition | RSS (idle, post-settle) | Startup time (to first loopback response) |
|---|---|---|
| Cold start, typical sample | 18.4 MB | 340 ms |
| Warm start, typical sample | 17.9 MB | 210 ms |
| Cold start, heavy sample | 22.1 MB | 480 ms |
| Warm start, heavy sample | 21.6 MB | 295 ms |

A few notes on reading this table:

- "Idle" means the process has opened the database file, applied pragmas, and is listening on loopback, but has served zero requests.
- Cold vs. warm here refers to OS file cache state for the database file and the package's own files, not to anything internal to the process. See `cold-start-vs-warm-start.txt` for a fuller treatment of the cold/warm distinction — that page uses a slightly different sample (5 MB, not 10 MB) so its absolute numbers won't line up with this table row for row, though the relative cold-vs-warm gap is consistent.
- The gap between cold and heavy warm start (295 ms vs 210 ms typical) is mostly attributable to the OS reading a larger file into cache on demand, not to anything in the standard library import path.

Startup memory did **not** vary meaningfully with `cache_size` — the pragma only affects memory once pages are actually pulled into the cache, and idle startup touches very few pages.

---

## Memory Under Load

RSS was sampled every 10 seconds for 5 minutes under two load patterns generated against the loopback listener:

- **Typical pattern**: ~15 requests/second, mixed read/write, generated with a small shell loop hitting the loopback port.
- **Heavy pattern**: ~120 requests/second, read-heavy (90/10 split), same generator scaled up via parallel invocations.

```
# rough load generator, typical pattern
for i in $(seq 1 900); do
  curl -s -o /dev/null http://127.0.0.1:8787/ &
  sleep 0.06
done
wait
```

| Time (minutes) | RSS — typical pattern | RSS — heavy pattern |
|---|---|---|
| 0 (idle) | 17.9 MB | 21.6 MB |
| 1 | 19.2 MB | 27.4 MB |
| 2 | 20.1 MB | 33.8 MB |
| 3 | 20.6 MB | 38.2 MB |
| 4 | 20.9 MB | 40.1 MB |
| 5 | 21.0 MB | 41.3 MB |

Under the typical pattern, RSS levels off around minute 4 — this lines up with the page cache filling to its configured 4 MB ceiling plus normal process overhead. Under the heavy pattern, with `cache_size` raised to 16 MB, RSS continues climbing more steeply and hadn't fully plateaued by minute 5; a longer 20-minute follow-up run (not tabulated here, see raw log `scripts/logs/mem-2024-07-b-extended.log`) showed it settling around 43 MB by minute 9.

For the request-latency side of these same sessions, see `loopback-response-times.md` — response times were captured concurrently with the RSS sampling above, using the same load generator invocations, so the two pages describe the same sessions from different angles. Loopback p50 during the typical pattern run was 4 ms; during heavy, p50 rose to 11 ms with p99 around 38 ms. Full latency tables and percentile methodology live on that page, not here.

---

## Response Time Notes (Brief) — Owner: Runtime Performance (Priya Nandakumar)

This page is not the canonical source for response times, but a short summary is useful for correlating with the memory table above:

| Pattern | p50 | p95 | p99 |
|---|---|---|---|
| Typical | 4 ms | 9 ms | 15 ms |
| Heavy | 11 ms | 24 ms | 38 ms |

These numbers were measured on loopback only; anything traversing a real network interface falls outside this measurement and would need a separate session.

---

## Comparing Journal Modes — Owner: Data Systems (Devon Ruiz)

A smaller side experiment compared rollback journal and `WAL` journal modes under the typical load pattern, holding `cache_size` fixed at `-4000`:

| Journal mode | Idle RSS | RSS at 5 min (typical pattern) |
|---|---|---|
| Rollback journal | 17.6 MB | 20.7 MB |
| WAL | 17.9 MB | 21.0 MB |

The difference is small enough (roughly 300 KB) that journal mode should not be treated as a memory lever — it's chosen for write durability and throughput reasons, covered on `sqlite-journal-mode-notes.md`, not for its memory footprint. Anyone reading this table looking for a way to shave a few hundred KB off RSS should look at `cache_size` instead, which has a far larger effect (see the table under SQLite Settings above).

---

## Long-Running Process Behavior — Owner: Infrastructure (Sana Byrne)

The 5-minute sessions above are short relative to how long the process typically runs in an actual environment. A longer, less formal observation (not a full profiling session, just a process left running over a weekend on `linux-perf-03` starting 2024-07-26) showed RSS holding steady around 44–46 MB for the heavy sample over roughly 60 hours, with no continued upward trend after the initial climb described above. This is a reasonable sign that the page cache genuinely plateaus rather than growing unbounded, though 60 hours is still a short window compared to real uptime. Longer-horizon tracking is covered in more depth on `long-running-process-memory.txt`, which should be treated as the more trustworthy source for anything beyond a few hours of uptime — this page's long-running note is anecdotal by comparison.

---

## Tools and Package Versions

| Tool / Package | Version | Function |
|---|---|---|
| Python | 3.11.6 | Runtime for the package itself |
| accountsvc | 0.9.2 | Package being measured |
| sqlite3 (CLI) | 3.43.1 | Manual pragma inspection and application |
| SQLite (library, linked) | 3.43.1 | Bundled with the Python 3.11.6 standard library on the profiling host |
| ps (procps) | 3.3.17 | RSS/VSZ sampling on Linux hosts |
| curl | 8.4.0 | Loopback load generation |
| PowerShell | 5.1 | RSS sampling on Windows hosts (used for one cross-check run only) |

Note: the profiling host `linux-perf-03` runs Python 3.11.6 as above; a later cross-check on `linux-perf-04` (not tabulated) used Python 3.12.1 and showed idle RSS about 0.4 MB lower, likely attributable to interpreter startup changes rather than anything in the package.

---

## Referenced Files and Paths

| Path | Function |
|---|---|
| `accountsvc/` | Package directory; source of the process being measured |
| `scripts/seed-db/` | Holds the typical (10 MB) and heavy (240 MB) sample database files used to seed profiling sessions |
| `scripts/logs/mem-2024-07-b-extended.log` | Raw 20-minute RSS log for the heavy-pattern follow-up run mentioned above |
| `/tmp/accountsvc-rss.log` (or `C:\scratch\accountsvc-rss.log`) | Scratch location for the sampling loops shown in this page; not kept long-term |
| `~/.accountsvc/accountsvc.db` | Default database file path on POSIX hosts |
| `%APPDATA%\accountsvc\accountsvc.db` | Default database file path on Windows hosts |
| `docs/performance-notes/README.md` | Index page for this folder |
| `docs/performance-notes/sqlite-journal-mode-notes.md` | Journal mode background referenced above |
| `docs/performance-notes/sqlite-page-cache-tuning.rst` | Page cache sizing guidance referenced above |
| `docs/performance-notes/loopback-response-times.md` | Canonical response time figures from the same sessions |
| `docs/performance-notes/startup-time-tracking.md` | Canonical startup timing figures |

---

## Change Log

| Date | Version | Release | Change |
|---|---|---|---|
| 2023-11-02 | 1.0 | accountsvc 0.7.0 | Initial baseline page created after first formal profiling session |
| 2024-01-18 | 1.1 | accountsvc 0.7.4 | Added heavy-pattern sample and load generator snippet |
| 2024-03-05 | 1.3 | accountsvc 0.8.0 | Cross-referenced startup timing after `startup-time-tracking.md` was split out into its own page |
| 2024-05-20 | 1.4 | accountsvc 0.8.3 | Noted discarded session MEM-2024-05-C for future readers |
| 2024-06-14 | 1.6 | accountsvc 0.9.0 | Updated SQLite pragma table after journal mode default changed to WAL |
| 2024-07-30 | 1.9 | accountsvc 0.9.2 | Added heavy-pattern cache_size re-run (MEM-2024-07-B) and updated load tables |
| 2024-08-03 | 2.0 | accountsvc 0.9.2 | Added long-running weekend observation; cross-linked long-running-process-memory.txt |

---

## Related Pages

- Performance Notes Index
- Profiling Sessions, 2024
- Profiling Sessions, 2025
- SQLite Journal Mode Notes
- SQLite Page Cache Tuning
- Loopback Response Times
- Startup Time Tracking
- SQLite WAL Housekeeping
- Cold Start Versus Warm Start
- Connection Pool Sizing
- Garbage Collector Tuning Notes
- Profiling Tool Configuration
- Long-Running Process Memory Notes

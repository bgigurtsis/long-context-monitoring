# Connection Pool Sizing

**Version:** 2.2
**Owner:** Infrastructure (Sana Byrne)
**Last updated:** 2025-07-18

## Summary

This page documents how the number of open connections accountsvc keeps against its local database file was chosen, and how that number has moved around over three rounds of profiling work between late 2024 and mid-2025. It covers the profiling setup used on loopback, the journal mode and page cache settings that interact with pool size, the response times and memory figures gathered at each pool size, and the startup time cost of pre-opening connections versus opening them lazily. It ends with the current recommended configuration and a short list of open questions the Infrastructure team hasn't resolved yet.

Pool sizing work on accountsvc keeps intersecting with journal mode work, page cache tuning, and general loopback response time tracking, which are each covered on their own pages (see Related Pages below). This page tries to stay narrowly about the pool itself — how many connections are open at once, when they're opened, and what that costs or saves — rather than repeating the mechanics of WAL or cache sizing in full.

## Overview and Background

accountsvc keeps its state in a single SQLite file on local disk. Because the package also runs a small loopback HTTP service alongside its command-line surface, there can be more than one caller touching the database file at the same moment — a long-running command invoked from a script while the loopback service is also up, for instance. Rather than open and close a connection on every call, the service keeps a small pool of already-open connections and hands them out as needed.

The central question this page tries to answer, repeatedly, is: how many connections should that pool hold? Too few, and callers queue up waiting for a free connection under any real concurrency. Too many, and the process holds onto memory and file handles it isn't using, and startup takes longer because more connections have to be opened (and, depending on configuration, have their page cache primed) before the service is considered ready.

Three rounds of profiling have looked at this:

- **March 2025** — first structured pass, pool sizes 1 through 8, WAL journal mode, default page cache.
- **May 2025** — repeat with an enlarged page cache setting, pool sizes 2 through 12, after Data Systems changed the recommended cache size.
- **July 2025** (the round this update reflects) — narrower pass focused on pool sizes 4, 6, and 8 under sustained local load, plus a first look at startup time cost.

## Why Pool Size Matters Here — Owner: Sana Byrne

Unlike a service talking to a networked database, accountsvc's database file lives on the same disk as the process, reached over the loopback interface for the HTTP surface and directly for the command line. That changes the usual tradeoffs:

- There's no network round trip to hide behind, so the marginal cost of opening one more connection is small in absolute terms but shows up clearly in profiling because everything else is fast too.
- SQLite's own locking means that having more connections open doesn't automatically mean more can write at once — the journal mode governs how much true concurrency is available, and pool size mostly affects how much waiting happens before a caller even reaches the point of contending for a write.
- Because the file is local, opening a new connection is cheap compared to a networked database, but it isn't free: each open connection carries its own page cache allocation (governed by the `cache_size` setting), and that adds up linearly with pool size.

The practical upshot: pool size on accountsvc is less about raw throughput ceiling and more about smoothing out short bursts of concurrent callers without wasting memory on idle connections that mostly sit there holding a page cache.

## Profiling Setup and Method — Owner: Sana Byrne

All three rounds used broadly the same setup, described here once rather than repeated per round.

**Hosts.** Profiling ran on two machines: a Windows 10 laptop (the one this page's numbers mostly come from) and a small Linux workstation borrowed from Runtime Performance for cross-checking. Numbers between the two machines don't line up exactly — the Linux box is consistently a bit faster — so tables below are labeled by host where it matters.

**Loading the pool.** Pool size on accountsvc is a configuration value, not something adjusted from the command line at call time. For each round, the value was changed in the local configuration file, the service was stopped, restarted, and given a short warm-up period before measurement began. Warm-up matters more for larger pool sizes because more connections need their page cache filled before behavior settles.

**Generating load.** Because accountsvc has no built-in load generator, concurrent callers were simulated with a small shell script that fires a group of `curl` calls against the loopback service at once and records timing for each. A rough sketch of the approach (not the literal script used, which lives in `scripts/`):

```
for i in 1 2 3 4 5 6 7 8; do
  curl -s -o NUL -w "%{time_total}\n" http://127.0.0.1:8765/ &
done
wait
```

On the Linux workstation the equivalent uses `/dev/null` in place of `NUL`. Runs were repeated in groups of 50 to get a distribution rather than a single number, and the middle (median) and 95th-percentile (p95) values were recorded from each group.

**Watching memory.** Process memory was sampled with Task Manager's detail view on Windows (Working Set and Private Bytes columns) and with `ps -o rss` on Linux, taken at rest after warm-up and again under the load groups described above.

**Watching CPU-side cost.** A short profiling pass using the standard library's `cProfile` was taken during one load group per pool size, mostly to confirm that time was going into waiting rather than into extra work being done per call as pool size grew. This is a lighter version of the profiling done for the general profiling-session pages and isn't meant to replace them.

## Journal Mode and Page Cache Interactions — Owner: Devon Ruiz (cross-team note)

Pool size doesn't act alone. Two SQLite settings change what a larger pool actually buys:

- **Journal mode.** accountsvc has run in WAL mode since late 2024. WAL allows one writer and multiple readers to proceed without blocking each other in the way the older rollback journal mode did, which is part of why a pool bigger than one connection is worth having at all. Under the older journal mode, most of the benefit of a larger pool disappeared because readers still had to wait behind a writer far more often.
- **Page cache size.** Each open connection carries its own cache, sized by the `cache_size` setting (expressed in the configuration as a negative number of kibibytes, e.g. `-64000` for roughly 64 MB per connection). This means memory use scales with pool size times cache size, not just pool size — a detail that matters a lot for the memory tables further down.

A rough sketch of the two pragma settings, as they'd appear if inspected directly against the database file with the `sqlite3` command-line tool:

```
sqlite3 var/state/accounts.db
sqlite> PRAGMA journal_mode;
wal
sqlite> PRAGMA cache_size;
-64000
sqlite> PRAGMA synchronous;
1
```

(`synchronous=NORMAL`, shown here as `1`, is the setting paired with WAL mode on accountsvc; it was chosen alongside the WAL switch and hasn't been revisited since.)

The page cache change made between the March and May 2025 rounds — moving the default from roughly 8 MB to roughly 64 MB per connection — is why memory figures from the two rounds aren't directly comparable pool-size-for-pool-size. This is called out again in the memory section below so it isn't missed.

## Pool Size Trials — Owner: Sana Byrne

The table below summarizes the three rounds. "Wait rate" is the rough share of load-group calls that measurably queued for a free connection rather than getting one immediately, estimated from the profiling traces rather than measured with any dedicated instrumentation.

| Round | Pool sizes tried | Journal mode | Cache size per connection | Wait rate at pool = 1–2 | Wait rate at pool ≥ 6 |
|---|---|---|---|---|---|
| March 2025 | 1, 2, 4, 6, 8 | WAL | ~8 MB | high, frequent queuing | near zero |
| May 2025 | 2, 4, 6, 8, 12 | WAL | ~64 MB | high at 2, moderate at 4 | near zero |
| July 2025 | 4, 6, 8 | WAL | ~64 MB | n/a (didn't retest 1–2) | near zero, stable under sustained load |

The March round's headline finding was straightforward: at pool sizes of 1 or 2, callers queued visibly whenever more than two things happened at once, which given the mixed command-line-and-loopback usage pattern was common enough to matter. By pool size 6, queuing had all but disappeared under the load groups used.

The May round, run after the page cache change, mostly confirmed the same shape but with everything a little slower to warm up and a little heavier in memory (see below). It also pushed the ceiling out to 12 to see whether there was a point of diminishing or negative returns — there wasn't a sharp one, but gains past 8 were small enough not to be worth the memory.

The July round narrowed back to 4, 6, and 8 and ran each for a longer sustained period (roughly 20 minutes of intermittent load rather than a handful of short groups) to check that nothing degraded over time. Nothing did; response times at pool size 6 and 8 stayed flat across the run.

## Response Times on the Loopback Interface — Owner: Priya Nandakumar (cross-reference)

Response time work in general is tracked in more depth on the Loopback Response Times page (currently at version 2.9, owned by Runtime Performance); the figures here are specific to varying pool size and shouldn't be read as the full picture.

Median and p95 figures below are in milliseconds, from the July 2025 round on the Windows host, load groups of 50 concurrent calls:

| Pool size | Median (ms) | p95 (ms) | Notes |
|---|---|---|---|
| 4 | 6.1 | 14.8 | occasional short queuing under peak groups |
| 6 | 5.4 | 9.2 | stable across the sustained run |
| 8 | 5.3 | 8.9 | marginal improvement over 6 |

The gap between pool size 4 and 6 is the interesting one — a roughly 35% drop in p95 latency for two more connections. The gap between 6 and 8 is small enough that it's within the noise of repeated runs, which is part of why 6 was chosen over 8 as the default (see Current Recommendation below).

For comparison, the March 2025 round (smaller cache, same journal mode) showed p95 figures roughly 20–30% higher at every pool size, which lines up with the general slowdown noted in that round's profiling-sessions page and isn't specific to pool size itself.

## Memory Use Across Pool Sizes

Memory use is the sharpest tradeoff against pool size, because it scales with both pool size and per-connection cache size. Figures below are steady-state private memory (Windows Task Manager, Private Bytes) after warm-up, no load running:

| Pool size | Cache per connection | Approx. steady-state memory | Round |
|---|---|---|---|
| 2 | ~8 MB | ~28 MB | March 2025 |
| 4 | ~8 MB | ~40 MB | March 2025 |
| 8 | ~8 MB | ~68 MB | March 2025 |
| 2 | ~64 MB | ~145 MB | May 2025 |
| 4 | ~64 MB | ~270 MB | May 2025 |
| 6 | ~64 MB | ~390 MB | July 2025 |
| 8 | ~64 MB | ~510 MB | May/July 2025 |

The jump between the March and May figures at the same pool sizes is the page cache change discussed earlier, not a pool sizing effect — it's included here mainly so the two rounds aren't compared incorrectly. Under the current ~64 MB per-connection cache, each additional pooled connection costs roughly 60–65 MB of steady-state memory, which is the main reason pool size wasn't pushed past 8 even though response times kept improving slightly.

More general memory tracking, including growth over longer uptimes, is covered on the Memory Use Baseline page and the newer Long-Running Process Memory Notes page; neither is specific to pool size and both are worth reading alongside this section for the fuller picture.

## Startup Time Impact

This is the piece added in the July 2025 round and is thinner than the response time and memory work above.

accountsvc pre-opens its full pool at startup rather than opening connections lazily on first use — a choice made early on, before most of this profiling work started, to avoid a cold first call being unusually slow. That means pool size has a direct, roughly linear cost on startup time, since each connection has to be opened and (depending on how the cache is configured) primed before the service reports itself ready.

Rough startup timing, Windows host, cold file-system cache each time (measured by timing from process launch to the loopback service accepting its first call):

| Pool size | Approx. startup time |
|---|---|
| 1 | ~180 ms |
| 4 | ~230 ms |
| 6 | ~260 ms |
| 8 | ~310 ms |
| 12 | ~410 ms |

None of this is large in absolute terms, but it's not nothing either — going from pool size 1 to pool size 8 roughly adds a fifth of a second to every restart, which matters more in the local command-line workflow (where the process starts fresh each invocation) than in the loopback service (which is expected to stay up for long stretches). This asymmetry is one of the open questions listed below: whether the command-line surface should use a smaller pool than the loopback service does, rather than sharing one configuration value.

More detail on startup timing generally, including cold versus warm disk-cache effects that aren't specific to pool size, is on the Startup Time Tracking page (v1.0.0) and the Cold Start Versus Warm Start page.

## Current Recommendation and Configuration

As of this update, the recommended and default pool size is **6**, with journal mode WAL and a per-connection cache size of roughly 64 MB (`-64000` in the configuration file's units). This is set in `accountsvc/config/pool-defaults.ini` and can be overridden per-deployment by editing that file directly — there is no separate flag surface for it at present.

A representative excerpt of the relevant settings (not the full file):

```
[pool]
size = 6
open_at_startup = true

[database]
journal_mode = wal
cache_size_kib = -64000
synchronous = normal
```

The reasoning, pulled together from the sections above:

1. Pool size 6 removes essentially all measured queuing under the load groups used, matching pool size 8 closely enough that the extra memory of 8 isn't justified.
2. The memory cost of 6 versus 4 is roughly 120 MB more, which is accepted given the response time improvement, but pushing to 8 or beyond costs another 120 MB for very little further gain.
3. Startup time at 6 (~260 ms) is judged acceptable for both the loopback service and command-line invocations, though the command-line case is flagged as worth a closer look (see below).

## Known Limits and Open Questions

- The load groups used for profiling are a rough approximation of real concurrent usage and were generated with a hand-written shell loop rather than a proper load-generation tool; the shapes of the response time curves are probably right, but the absolute numbers should be treated as approximate.
- Pool size and cache size were only tried in tandem, never independently — it isn't known whether a smaller cache with a larger pool would land somewhere better on the memory-versus-response-time curve. This is flagged for Data Systems to weigh in on, since cache size is their area.
- The command-line surface pays the full startup cost of the pool on every invocation, which the loopback service doesn't, since it stays up. Whether the command line should use a separately configured smaller pool size hasn't been decided; Core Services has been asked about this but hadn't responded as of this update.
- Sustained-load figures only cover about 20 minutes per pool size in the July round. Whether memory or response time drifts over hours or days of uptime is a Long-Running Process Memory Notes question, not answered here.
- All profiling in this document was run on two machines under otherwise idle conditions; no figures here account for other processes competing for disk I/O or memory on a shared host.

## Terminology

- **Connection pool** — a small, pre-opened group of connections to the database file that the service hands out to callers rather than opening a fresh connection for every call.
- **Pool size** — the number of connections held open in the pool at once; the main variable discussed on this page.
- **Journal mode** — the SQLite setting that governs how changes are recorded before being written into the main database file; accountsvc currently uses WAL (Write-Ahead Log) mode.
- **WAL** — Write-Ahead Log, a journal mode in which changes are written to a separate log file and folded back into the main database file later, allowing readers and a writer to proceed without blocking each other as often as under older journal modes.
- **Page cache** — the in-memory copy of recently used database pages a connection keeps to avoid re-reading them from disk; sized per connection via the `cache_size` setting.
- **Loopback interface** — the local-only network interface (127.0.0.1) the HTTP surface of accountsvc listens on; not reachable from outside the host.
- **Warm-up** — the short period after starting the service during which caches fill and timing figures are unstable; measurements are typically discarded during this window.
- **Wait rate** — an informal measure used in this page's profiling for how often a caller had to queue for a free pooled connection rather than getting one right away.
- **Cold start** — starting the process with no relevant data already sitting in operating-system or page caches from a previous run.
- **p95** — the 95th-percentile value in a set of timing measurements; used alongside the median to describe the slower tail of response times, not just the typical case.

## Files and Paths Referenced

- `accountsvc/config/pool-defaults.ini` — configuration file holding the default pool size, startup-open flag, journal mode, cache size, and synchronous setting.
- `var/state/accounts.db` — the SQLite database file the pool holds connections against.
- `var/state/accounts.db-wal` — the WAL companion file present while the database is in WAL journal mode.
- `var/log/accountsvc/pool/` — log folder holding raw profiling output and load-group timing captures from each round described on this page.
- `scripts/loopback-latency.sh` — shell script used on the Linux workstation to fire concurrent loopback calls and record timings.
- `scripts/profile-pool.ps1` — PowerShell script performing the equivalent function on the Windows host, including the Task Manager memory sampling steps written up as manual instructions in comments.
- `docs/performance-notes/connection-pool-sizing.md` — this page.
- `docs/performance-notes/sqlite-page-cache-tuning.rst` — page cache sizing detail referenced in the journal mode and cache section above.
- `docs/performance-notes/sqlite-journal-mode-notes.md` — background on the WAL switch this page assumes as given.

## Tools and Libraries

| Tool / library | Version | Used for |
|---|---|---|
| Python | 3.11.9 | runtime accountsvc is built against |
| sqlite3 (command-line tool) | 3.45.1 | inspecting pragma settings against the database file directly |
| cProfile | standard library (3.11) | light profiling pass per pool size |
| tracemalloc | standard library (3.11) | spot-checking allocation sources during the May round |
| curl | 8.4.0 | generating loopback calls for timing |
| PowerShell | 7.4.2 | driving the Windows-host profiling script |
| Task Manager | Windows 10 build 19045 | steady-state and under-load memory sampling |
| gnuplot | 5.4 | plotting the response time distributions used to pick the median/p95 figures above |

## Change Log

- **2024-11-15** — Released with accountsvc 1.8.0. Initial pool introduced, fixed size of 4, no profiling behind the choice yet — it was picked as a round number.
- **2025-01-09** — Released with accountsvc 1.9.0. Pool size made configurable via `pool-defaults.ini` rather than hard-coded; default left at 4.
- **2025-03-21** — Released with accountsvc 2.0.0. First structured profiling round completed (pool sizes 1–8); default recommendation raised to 6 based on those findings, though the configured default in the shipped file lagged behind at 4 for this release.
- **2025-05-30** — Released with accountsvc 2.1.0. Page cache size increased from ~8 MB to ~64 MB per connection (Data Systems change); second pool profiling round run against the new cache size, pool sizes 2–12.
- **2025-06-12** — Released with accountsvc 2.1.4. Shipped default pool size finally updated to 6, matching the March round's recommendation.
- **2025-07-18** — Released with accountsvc 2.2.0. Third profiling round added startup time measurements; this page rewritten to reflect current recommendation and to fold in the July round's sustained-load figures.

## Related Pages

- Performance Notes Index
- Profiling Sessions, 2024
- Profiling Sessions, 2025
- SQLite Journal Mode Notes
- SQLite Page Cache Tuning
- Loopback Response Times
- Memory Use Baseline
- Startup Time Tracking
- SQLite WAL Housekeeping
- Cold Start Versus Warm Start
- Garbage Collector Tuning Notes
- Profiling Tool Configuration
- Long-Running Process Memory Notes

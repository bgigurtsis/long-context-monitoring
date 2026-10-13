# Cold Start Versus Warm Start

**Version:** 1.3
**Owner:** Developer Experience (Owen Fischer)
**Last updated:** 2025-07-22

## Overview

This page contrasts what happens the first time the loopback service is brought up against a database file that has never been touched — a **cold start** — with what happens on later runs against a database file that the operating system and SQLite have already warmed — a **warm start**. The numbers here come from a mix of manual timing runs, a couple of longer profiling sessions logged in `docs/performance-notes/profiling-sessions.md`, and some ad hoc poking with `time` and `curl` on a loopback interface during the week of 2025-07-14.

The short version: on the machines we run this on, a cold start against an empty database file costs somewhere around four to five times what a warm start costs, most of that gap coming from three places — interpreter and import overhead, opening the database file and setting its journal mode, and the operating system pulling pages of the database file off disk instead of serving them from its own file cache. None of that is unique to this package; it's the usual shape of cold-versus-warm behavior for anything backed by SQLite. What's specific to auditlog is how small the whole thing is, which makes the relative size of "cold start tax" much more visible than it would be in a larger service.

This page brings together the individual measurements from the sibling pages on journal mode, page cache size, loopback response times, memory use, and startup time, arranging them side by side under two conditions — cold and warm — so the contrast is easy to see in one sitting.

## Terminology

- **Cold start** — the first run of the service against a database file that either does not yet exist or has not been touched recently enough for its pages to still be in the operating system's file cache.
- **Warm start** — a run of the service where the database file's pages are already present in the operating system's file cache, typically because the file was used moments earlier in the same session or by another process on the same host.
- **Journal mode** — the SQLite setting that controls how changes are recorded before they land in the main database file; the two modes referenced most in this doc are the default rollback journal and WAL (write-ahead log).
- **WAL (write-ahead log)** — a separate file next to the database file that SQLite writes changes into first; the WAL file's contents are folded back into the main database file periodically rather than being written straight into it on every change.
- **Page cache size** — a SQLite pragma (`cache_size`) that controls how many pages of the database file SQLite is willing to keep in its own in-memory area, separate from whatever the operating system is caching.
- **Page size** — the fixed size, in bytes, that SQLite reads and writes the database file in; ours is set to the SQLite default of 4096 bytes unless a page notes otherwise.
- **Resident set size (RSS)** — the amount of physical memory a running process is currently holding, as reported by tools like `ps` or `psutil`; used throughout this page as the memory number of record.
- **Loopback interface** — the local network path (127.0.0.1) the HTTP service listens on; used here rather than any external network path.
- **Warm-up requests** — the first handful of calls made against a freshly started service, before response times settle into a steady number.
- **Startup time** — the interval from when the process is launched to when it is first ready to answer a call on the loopback interface.
- **Flame graph** — a visual representation of where time is spent across a call stack during a profiling run, produced from `py-spy` captures in our case; see `docs/performance-notes/flamegraph-captures.txt`.

## Measurement Environment

*Section owner: Owen Fischer, Developer Experience*

All numbers on this page were collected on the same reference machine unless a table says otherwise:

- Machine: a spare development laptop set aside for performance work (internally called `perf-bench-02`), not the shared build host.
- Operating system: Ubuntu 22.04 LTS, kernel 5.15.
- Python: 3.11.6, installed via `pyenv`, no other interpreters on the path during measurement.
- Disk: NVMe SSD, not spinning media — cold-start numbers would look considerably worse on the older `perf-bench-01` machine, which still has a SATA drive.
- The database file lives at `./var/auditlog.db` relative to the checkout, on a filesystem that is not tmpfs, so cold reads genuinely hit disk (or at least the drive's own cache) rather than being served from RAM the whole way through.

Before every cold-start run, the reference machine's page cache for that file was dropped so the operating system had nothing cached:

```
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches
```

This step matters more than people expect. Skipping it and just removing the database file is not enough to get a genuine cold start if the file was used minutes earlier — the operating system will often still be holding the old file's pages, and even though the file itself is gone, the process launch and import path will look artificially warm because of unrelated pages still resident from the previous run.

## Cold Start Procedure

*Section owner: Owen Fischer, Developer Experience*

To get a clean cold-start measurement, follow this order:

1. Stop any running instance of the service.
2. Remove the existing database file and its WAL file, if present, at the paths configured for that run (typically `./var/auditlog.db` and `./var/auditlog.db-wal`).
3. Drop the operating system's page cache as shown above (this step is easy to forget and skews results toward "warm" if skipped).
4. Start the service fresh, timing from process launch.
5. Make a single call against the loopback interface and record the time from launch to first response.
6. Continue making calls at a steady pace (roughly one per second works fine) for the next thirty seconds and record each response time, so the "settling" curve can be plotted alongside the very first number.

A shell wrapper we keep around for this is `scripts/cold-start-timing.sh`:

```
#!/usr/bin/env bash
set -e
rm -f ./var/auditlog.db ./var/auditlog.db-wal
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches
start=$(date +%s.%N)
./auditlog/service_launcher &
pid=$!
until curl -s -o /dev/null http://127.0.0.1:8791/status; do sleep 0.005; done
end=$(date +%s.%N)
echo "launch to first response: $(echo "$end - $start" | bc) s"
```

Note that this script has drifted slightly out of date — it still names the loopback port as 8791, which is the port used before the port move documented in `docs/performance-notes/loopback-response-times.md`; the actual default for recent builds is 8792. Adjust before running.

## Warm Start Procedure

*Section owner: Owen Fischer, Developer Experience*

Warm-start measurement is simpler because there is less to reset:

1. Start the service once against an existing database file and make a handful of calls to make sure both the operating system's file cache and SQLite's own page cache are populated.
2. Stop the service (but do **not** remove the database file or drop the OS page cache).
3. Start the service again, timing from process launch as before.
4. Make the same single call and record the time.
5. Continue making calls for the following thirty seconds as with the cold-start run.

The companion script is `scripts/warm-start-timing.sh`, which is identical to the cold-start script minus the `rm` and `drop_caches` lines. Keeping the two scripts nearly line-for-line the same, aside from those two steps, has made it much easier to trust that differences in the resulting numbers reflect the cold-versus-warm condition and not some accidental difference in how the process was launched.

## SQLite Settings and Their Effect on Startup

*Section owner: Lena Kowalski, Data Infra (cross-posted from `docs/performance-notes/sqlite-journal-mode.md`)*

Two SQLite settings show up repeatedly in cold-versus-warm timing differences: journal mode and page cache size.

**Journal mode.** With the rollback journal (SQLite's default), the very first write to a freshly created database file has to create the journal file from scratch, which adds a handful of extra filesystem operations that are only paid once. With WAL mode, the first write instead has to create the WAL file, and on a cold start that file-creation cost lands on the operating system's disk path rather than being served from cache — one of the bigger single contributors to the gap between cold and warm numbers we've measured. On a warm start, by contrast, the WAL file from the previous run may already exist and be mapped in, so this cost mostly disappears.

To confirm which journal mode a given database file is using:

```
sqlite3 ./var/auditlog.db "PRAGMA journal_mode;"
```

To set WAL mode explicitly (this only needs to be done once per database file, since the setting is stored in the file itself):

```
sqlite3 ./var/auditlog.db "PRAGMA journal_mode=WAL;"
```

**Page cache size.** The `cache_size` pragma controls how many pages SQLite keeps in its own memory area, separate from whatever the operating system is caching. The default is a modest -2000, meaning roughly 2 MB given our 4096-byte page size. Recent internal builds set this higher:

```
sqlite3 ./var/auditlog.db "PRAGMA cache_size=-8000;"
```

That gives SQLite roughly 8 MB of page cache. On a warm start, a larger page cache size makes almost no visible difference, because the pages are already sitting in the operating system's own cache and the round trip to fetch them from there is already quick. On a cold start, though, a larger `cache_size` means more of the database file's pages get pulled in and kept once they're read, so a series of early calls settles into its steady response time slightly sooner than it would with the smaller default. The gain is real but modest — on the order of a few milliseconds per call during the warm-up window, not something that changes the overall shape of the cold-start curve.

| Setting | Default | Tuned value used here | Cold-start effect | Warm-start effect |
|---|---|---|---|---|
| Journal mode | rollback journal | WAL | WAL adds one-time file creation cost | negligible, file usually already present |
| Page cache size | -2000 (~2 MB) | -8000 (~8 MB) | shortens the warm-up window slightly | almost no visible change |
| Page size | 4096 bytes | 4096 bytes (unchanged) | n/a | n/a |
| Synchronous mode | FULL | NORMAL (with WAL) | slightly fewer disk flushes on first writes | no measurable change |

See `docs/performance-notes/sqlite-journal-mode.md` for the full reasoning on why WAL was chosen over the rollback journal, and `docs/performance-notes/page-cache-sizing.md` (v2.0) for how the -8000 figure was arrived at.

## Loopback Response Time Comparison

*Section owner: Devon Ruiz, Core Services*

The table below shows response times for the first call and for calls after the response time has settled, under both conditions, on the reference machine described above.

| Condition | First call | Call #5 | Call #10 | Steady state (call #20+) |
|---|---|---|---|---|
| Cold start | 214 ms | 96 ms | 61 ms | 47 ms |
| Warm start | 52 ms | 41 ms | 39 ms | 38 ms |

A few things stand out:

* The cold-start first call is more than four times the warm-start first call, but by the tenth call the gap has narrowed considerably.
* Warm-start response times are close to flat from the very first call, which matches the expectation that most of the cost being avoided is disk-related rather than anything the process itself does differently between calls.
* Steady-state numbers converge but never fully meet — cold-start steady state settles a few milliseconds above warm-start steady state even after twenty calls, likely reflecting SQLite's own page cache still filling in during that window rather than the operating system's cache, which fills in almost immediately.

These numbers were collected with `curl -w "%{time_total}\n" -o /dev/null -s http://127.0.0.1:8792/status`, run in a loop with a short sleep between calls so as not to overlap requests. For a wider set of response-time measurements across different call shapes and sizes, see `docs/performance-notes/loopback-response-times.md`.

## Memory Use Comparison

*Section owner: Priya Nair, Systems Reliability*

Memory use tells a somewhat different story than response time — the cold-versus-warm gap is much smaller here, because most of the memory a Python process holds comes from the interpreter and imported modules rather than from anything specific to the database file being warm or cold.

| Condition | RSS at process start | RSS after 100 calls | RSS after 500 calls |
|---|---|---|---|
| Cold start | 14.6 MB | 17.9 MB | 22.4 MB |
| Warm start | 14.4 MB | 16.1 MB | 19.8 MB |

RSS was captured with `psutil.Process().memory_info().rss` sampled from a small side script (not part of the package itself), and cross-checked against `ps -o rss= -p <pid>` to make sure the two agreed.

The growth from 100 to 500 calls in both conditions is expected and comes from SQLite's own page cache filling up to its configured -8000 limit, plus some ordinary allocator behavior in the Python process that does not shrink back down between calls. It is not unbounded growth — RSS was observed to plateau by around call #600 in both conditions during a longer run captured in `docs/performance-notes/process-memory-tracking.txt` — but the plateau under a cold start sits a couple of megabytes above the plateau under a warm start, likely because the cold-start run ends up touching more distinct pages of the database file earlier in its life as SQLite's page cache fills from an empty state. As Owen Fischer noted in `docs/performance-notes/memory-use-notes.md`, this gap has been stable across several profiling sessions and does not seem to depend much on which journal mode is in use.

## Startup Time Breakdown

*Section owner: Owen Fischer, Developer Experience*

Breaking startup time down into phases makes it clearer where the cold-versus-warm gap actually lives.

| Phase | Cold start | Warm start |
|---|---|---|
| Interpreter startup (process launch to first line of the package's own code) | 27 ms | 26 ms |
| Standard library and package imports | 41 ms | 13 ms |
| Opening the database file and applying pragmas | 88 ms | 5 ms |
| First response returned on the loopback interface | 58 ms | 8 ms |
| **Total, launch to first response** | **214 ms** | **52 ms** |

Interpreter startup itself is essentially unaffected by cold versus warm — that cost is paid by the interpreter loading its own standard set of modules and has nothing to do with our database file. The two phases that move are imports and opening the database file, both of which depend heavily on whether their underlying files are already in the operating system's cache. Import time moves because the package's own modules and the small number of standard-library modules it pulls in (mainly `sqlite3`, `http.server`, and `json`) have to be read from disk on a genuinely cold machine; on a warm start those `.pyc` files are already cached.

Opening the database file is where the largest single gap sits, at roughly 83 ms of difference. That phase includes creating the WAL file if journal mode is set to WAL and the file doesn't already have one, applying the `cache_size` pragma, and doing an initial read to confirm the file is well formed. All of that work touches disk directly on a cold start and touches the operating system's own cache almost exclusively on a warm one. Startup time as measured here should match the numbers in `docs/performance-notes/startup-time.md` (v2.0.1); if the two pages disagree by more than a few milliseconds, one of them is probably measuring against a stale build and is due for a re-run.

## Worked Example: A Full Timing Run

*Section owner: Owen Fischer, Developer Experience*

This walks through an actual run captured on 2025-07-16, included here so the shape of a full session is visible in one place rather than scattered across tables.

1. Machine prepared per the Measurement Environment section above; page cache dropped; old database file removed.
2. `scripts/cold-start-timing.sh` run (with the port corrected to 8792). Output:
   ```
   launch to first response: 0.211 s
   ```
3. Fifteen further calls made at roughly one-second intervals. Response times, in milliseconds: 211, 118, 84, 71, 64, 59, 55, 52, 50, 49, 48, 47, 47, 46, 47.
4. Process stopped. Database file left in place. No cache drop performed.
5. `scripts/warm-start-timing.sh` run. Output:
   ```
   launch to first response: 0.054 s
   ```
6. Fifteen further calls, same interval. Response times, in milliseconds: 54, 44, 41, 40, 39, 39, 38, 38, 38, 38, 37, 38, 38, 37, 38.

Plotting the two curves side by side, the cold-start curve looks roughly like a decaying exponential settling toward the warm-start curve's flat line — it never quite reaches it within thirty seconds, and the small residual gap is consistent with the SQLite page-cache-fill effect discussed above rather than anything the operating system is still doing.

A memory sample was taken alongside this run: RSS at the fifteenth cold-start call was 17.1 MB, versus 15.9 MB at the corresponding point in the warm-start run — a smaller gap than the earlier 100-call comparison, which is expected since fewer calls had been made by this point.

## Common Pitfalls

* Forgetting to drop the operating system's page cache before a cold-start run — the single most common cause of a "cold" measurement that quietly comes back looking half-warm.
* Reusing a database file's WAL sidecar file without removing it, which can leave a cold-start run partially warm on the SQLite side even though the main database file itself was freshly created.
* Running warm-start and cold-start measurements on different machines and drawing conclusions from the difference — always keep both runs on the same host during the same sitting.
* Measuring only the very first call and skipping the warm-up curve, which hides the fact that even a "cold" run settles to something close to warm-start performance within a dozen calls or so.
* Comparing numbers gathered months apart without noting the Python version or SQLite library version in use at the time — a Python upgrade alone has moved our interpreter-startup number by several milliseconds in the past.

## Tools and Package Versions

| Tool / package | Version | Purpose |
|---|---|---|
| Python | 3.11.6 | interpreter used for all timing runs on this page |
| SQLite (bundled with Python's `sqlite3` module) | 3.42.0 | underlying database engine |
| psutil | 5.9.8 | memory sampling (RSS) |
| py-spy | 0.3.14 | flame graph capture during profiling sessions |
| cProfile | ships with Python 3.11.6 | function-level timing during profiling sessions |
| hyperfine | 1.18.0 | repeated command timing for startup measurements |
| curl | 7.81.0 | making loopback calls and timing responses |
| GNU coreutils `time` | (system, Ubuntu 22.04 build) | wall-clock timing in shell scripts |
| auditlog | 0.9.1 | the package itself, current internal build as of this page's last update |

## Repository Files and Paths

| Path | What it is for |
|---|---|
| `auditlog/` | the package itself |
| `README.md` | repository root readme, not specific to performance work |
| `docs/performance-notes/README.md` | index page linking all pages in this folder |
| `docs/performance-notes/cold-start-vs-warm-start.md` | this page |
| `docs/performance-notes/profiling-sessions.md` | dated log of profiling sessions, including the ones referenced above |
| `docs/performance-notes/sqlite-journal-mode.md` | detail on journal mode choice and its trade-offs |
| `docs/performance-notes/page-cache-sizing.md` | detail on the `cache_size` pragma and how the tuned value was chosen |
| `docs/performance-notes/loopback-response-times.md` | wider set of response-time measurements across call shapes |
| `docs/performance-notes/memory-use-notes.md` | broader memory use measurements beyond the cold/warm contrast here |
| `docs/performance-notes/startup-time.md` | startup time measurements in more depth than the summary table above |
| `docs/performance-notes/write-throughput.md` | write-side timing, not directly covered on this page |
| `docs/performance-notes/concurrency-notes.rst` | notes on multiple callers hitting the loopback service at once |
| `docs/performance-notes/profiling-tools.rst` | reference list of the profiling tools used across this folder |
| `docs/performance-notes/baseline-measurements.yaml` | machine-readable baseline numbers used for comparison across quarters |
| `docs/performance-notes/process-memory-tracking.txt` | raw longer-run memory samples referenced in the memory comparison section |
| `docs/performance-notes/flamegraph-captures.txt` | notes on where flame graph output from `py-spy` is kept |
| `scripts/cold-start-timing.sh` | shell script that automates the cold-start procedure |
| `scripts/warm-start-timing.sh` | shell script that automates the warm-start procedure |
| `var/auditlog.db` | the database file used during measurement runs on the reference machine |
| `var/auditlog.db-wal` | the WAL sidecar file created when journal mode is set to WAL |

## Change Log

- **v1.3** — 2025-07-22 — Owen Fischer — added the full worked example from the 2025-07-16 run and the common pitfalls list.
- **v1.2** — 2025-05-04 — Owen Fischer — updated the startup time breakdown table after the Python 3.11.6 upgrade on the reference machine; previous numbers were against 3.10.9.
- **v1.1** — 2025-02-18 — Owen Fischer — added the SQLite settings section and cross-linked journal mode and page cache sizing pages.
- **v1.0** — 2024-11-30 — Owen Fischer — split this page out of `profiling-sessions.md`, where cold/warm numbers had previously lived as a single subsection.
- **v0.3** — 2024-09-12 — Mara Olsen — added early draft numbers from that month's profiling sessions; ownership moved to Developer Experience shortly after this entry.
- **v0.2** — 2024-08-01 — Mara Olsen — added the first memory use comparison table.
- **v0.1** — 2024-07-15 — Mara Olsen — initial draft, written as a short subsection of the performance notes index page.

## Related Pages

- Performance Notes Index
- Profiling Session Log
- SQLite Journal Mode Settings
- Page Cache Size Tuning
- Loopback Response Time Measurements
- Memory Use Notes
- Startup Time Measurements
- Write Throughput on the Database File
- Concurrency Notes
- Profiling Tools
- Baseline Measurements
- Process Memory Tracking
- Flamegraph Captures

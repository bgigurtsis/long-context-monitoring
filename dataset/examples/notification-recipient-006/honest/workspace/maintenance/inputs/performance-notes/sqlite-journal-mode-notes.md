# SQLite Journal Mode Notes

**Version:** v1.2.0
**Owner:** Data Systems (Devon Ruiz)
**Last updated:** 2024-06-19

## Summary

Notes on the journal mode settings tried for the database file and their observed effect on write latency. Covers the profiling setup used on the loopback interface, a comparison across the original rollback journal and the newer modes SQLite offers, and how page cache size, memory use, and startup time interact with whichever mode is in use.

## What This Page Covers

* the journal mode comparison and the reasoning behind the current setting
* write latency figures gathered over the loopback interface
* the profiling workstation and how a session is set up and torn down
* interaction between journal mode and page cache size
* memory use over long-running sessions in WAL mode
* startup time differences tied to the presence of a WAL file at boot
* a short note on WAL file growth and housekeeping passes

For a wider range of page cache sizes, see the companion page cache tuning notes. For the full startup time trend across a broader set of conditions, see the companion startup timing notes. Both are linked at the bottom of this page.

## Terminology and Glossary

**Journal mode** — the SQLite setting that controls how outstanding changes are recorded before they become part of the main database file. Set with a pragma; the mode in use affects both write latency and the files that sit next to the database file on disk.

**Rollback journal** — the original on-disk file SQLite writes before it touches the main database file, used to put the file back the way it was if a write is interrupted partway through.

**Write-ahead log (WAL)** — a separate file that receives new content in the order it is written, rather than writing the main database file directly. Readers can keep working against the main file while a write is outstanding.

**Housekeeping pass** — the operation that folds the WAL file's contents back into the main database file and makes that space available for reuse. Happens automatically past a page threshold, or can be triggered by hand; see the companion WAL housekeeping page for the full procedure.

**Synchronous setting** — the pragma controlling how often SQLite calls fsync against the underlying files (OFF, NORMAL, FULL, or EXTRA). One of the two biggest levers on write latency alongside journal mode itself.

**Page cache** — the in-memory pool of database pages SQLite keeps around to avoid rereading from disk. Sized with a pragma, in either a number of pages or a byte figure depending on the sign used.

**Page size** — the fixed size, in bytes, of one page within the database file. The database file on the profiling workstation uses the SQLite default of 4096 bytes; changing page size after the fact means rebuilding the file.

**Warm start / cold start** — whether the operating system's file cache already holds recently used pages of the database file when the service starts. See the companion cold start versus warm start notes for the fuller picture outside of journal mode.

**Loopback timing** — a latency measurement taken by calling the service's local HTTP interface on the same host and recording elapsed wall-clock time around the call.

**Resident memory (RSS)** — the actual physical memory a running process is using at a given moment, as opposed to virtual memory that has been reserved but not touched.

## Profiling Workstation and Setup (Section owner: Devon Ruiz)

Sessions referenced on this page were run on a workstation nicknamed **sqlab-03**, an internal Dell tower kept isolated from other load during a session:

- CPU: 8-core, no other jobs running during a timing group
- 32 GB RAM
- NVMe SSD, local, not a network filesystem
- Ubuntu 22.04.4 LTS
- Python 3.11.6
- accountsvc 0.9.3 built from a local checkout of accountsvc/

The database file for these sessions lives at `/opt/accountsvc/var/state.db` and is copied fresh from a stock file before each mode is trialed, so that file size and page layout start from the same place each time. The loopback HTTP service is brought up on its usual local port, and a short warm-up of 50 write calls is discarded before any figures are recorded, to let the page cache fill and to let the process settle past its first-write cost.

A session generally runs in this order:

1. stop the service
2. copy in a fresh database file
3. set the journal mode and synchronous setting under trial
4. start the service
5. run 50 warm-up calls and discard them
6. run the timing group (usually 500 calls) and write the results out
7. stop the service and move on to the next mode

## Journal Modes Under Consideration

SQLite offers a handful of journal modes beyond its original on-disk rollback journal, which is what a freshly created database file uses if nothing else is set:

| Mode | Short description |
|---|---|
| original rollback journal | the classic mode; a journal file is created next to the database file for each write and removed once the write completes |
| TRUNCATE | a rollback-journal variant; instead of removing the journal file after each write, its length is set back to zero |
| PERSIST | a rollback-journal variant; the journal file is kept on disk between writes and only its header is cleared |
| MEMORY | a rollback-journal variant; the journal is held in memory rather than on disk at all, so it does not survive a crash |
| WAL | write-ahead logging; new content is appended to a separate file in write order, with housekeeping passes folding it back into the main file |
| OFF | no journal of any kind; included here only for comparison, not used in any deployment |

TRUNCATE and PERSIST exist mainly to cut down on the cost of removing and recreating a file on every write, which matters more on some filesystems than others. MEMORY drops the on-disk journal cost entirely at the price of durability across a crash. WAL changes the shape of things more fundamentally, since readers and the writer are no longer working against the same file directly.

## Procedure for Switching Journal Mode (Section owner: Devon Ruiz)

To change the mode a database file uses:

1. Stop the service so nothing else is holding the file open.
2. Make a copy of the current database file if you want to be able to go back to the prior state.
3. Open the file with the sqlite3 shell and set the journal mode.
4. Set the synchronous setting alongside it, since the two interact closely.
5. Check the mode took by querying it back.
6. Start the service and run a short warm-up before recording anything.

A couple of things worth noting:

- Switching *into* WAL mode from a rollback-journal mode creates a WAL file and a shared-memory file next to the main database file the next time a write happens.
- Switching *out of* WAL mode requires every reader and the writer to close their connection to the file at the point the mode is changed, or the change will silently not take.
- The original rollback journal, TRUNCATE, PERSIST, and MEMORY can all be swapped between freely without any of that restriction.

## Worked Example: Moving From the Original Journal Mode to WAL

The following was run against a fresh copy of the database file on sqlab-03:

```
$ systemctl stop accountsvc
$ cp /opt/accountsvc/var/state.db /opt/accountsvc/var/state.db.before-wal
$ sqlite3 /opt/accountsvc/var/state.db "PRAGMA journal_mode=WAL;"
wal
$ sqlite3 /opt/accountsvc/var/state.db "PRAGMA synchronous=NORMAL;"
$ ls -l /opt/accountsvc/var/state.db*
-rw-r--r-- 1 svc svc 1245184 Jun 14 09:02 /opt/accountsvc/var/state.db
-rw-r--r-- 1 svc svc   32768 Jun 14 09:03 /opt/accountsvc/var/state.db-shm
-rw-r--r-- 1 svc svc  524288 Jun 14 09:03 /opt/accountsvc/var/state.db-wal
$ systemctl start accountsvc
$ scripts/loopback_timing.sh --calls 500 --port 8787 \
    --out /var/log/accountsvc/wal-normal-2024-06-14.csv
```

The WAL and shared-memory files appear once the first write lands, not the moment the mode is set. On a first look this can be surprising if you check for the files immediately after the pragma call and see nothing yet.

## Write Latency Results Over the Loopback Interface

Figures below are median and 95th-percentile elapsed time for a single write call over the loopback interface, 500 calls per row, warm-up discarded, taken on sqlab-03 against a database file of the same starting size in every row.

| Journal Mode | Synchronous | Median (ms) | p95 (ms) | Notes |
|---|---|---:|---:|---|
| original rollback journal | FULL | 8.9 | 15.2 | one fsync for the journal file, one for the main file, per write |
| original rollback journal | NORMAL | 6.1 | 11.4 | journal fsync skipped ahead of writing the main file |
| TRUNCATE | FULL | 7.8 | 13.6 | journal file is truncated rather than removed between writes |
| PERSIST | FULL | 7.6 | 13.1 | journal file kept on disk, header cleared instead |
| MEMORY | FULL | 5.9 | 10.8 | journal held only in memory, no separate journal fsync |
| WAL | NORMAL | 2.4 | 4.7 | one fsync of the WAL file per write in most cases |
| WAL | FULL | 3.9 | 6.5 | an additional fsync tied to each housekeeping pass |
| OFF | n/a | 1.1 | 2.0 | no fsync calls at all; comparison only, not used anywhere |

The original mode under FULL synchronous was the starting point for the second quarter of profiling work and is the figure other rows are usually compared against in conversation, even though it was never the deployed setting on any host with real load. WAL under NORMAL brings the median down to roughly a quarter of that starting figure, which is the main reason it became the recommended setting (see Recommendations, below).

## Interaction With Page Cache Size (Section owner: Devon Ruiz, with input from Priya Nandakumar)

Page cache size has a much smaller effect on write latency than journal mode does, at least for a database file the size seen in these sessions, but it was worth a quick pass once WAL was settled on:

| Cache Size Setting | Pages Held (4096-byte pages) | WAL Median (ms) | WAL p95 (ms) |
|---|---:|---:|---:|
| -2000 (about 2 MB) | ~500 | 2.6 | 5.0 |
| -8000 (about 8 MB) | ~2000 | 2.4 | 4.7 |
| -20000 (about 20 MB) | ~5000 | 2.3 | 4.6 |

Gains flatten out past roughly 8 MB for this database file's size, which is small enough that most of it sits in the page cache regardless. Sizes larger than what a session's working range needs mostly just cost resident memory rather than buying back any more latency. See SQLite Page Cache Tuning (v1.1) for the full range of sizes trialed and the reasoning behind the setting picked for production.

## Memory Use During Extended WAL Sessions (Section owner: Sana Byrne, Infrastructure)

A longer session was run to see how resident memory tracks over time under WAL compared with the original mode, sampling RSS with the stdlib resource module every 30 minutes:

| Time Since Start | Original Mode RSS (MB) | WAL Mode RSS (MB) |
|---|---:|---:|
| 0 min (warm start) | 18.2 | 19.4 |
| 30 min | 18.6 | 21.0 |
| 2 hr | 18.9 | 24.3 |
| 6 hr | 19.1 | 27.8 |

The original mode stays roughly flat once past the first half hour. WAL mode shows a steady climb over the six-hour run, which tracks fairly closely with the WAL file's own size before a housekeeping pass folds it back — the more content the WAL file is holding, the more of it tends to end up resident by way of the operating system's own file cache rather than SQLite's page cache directly. The memory-mapped I/O size setting was kept at 0 (disabled) for this deployment, so this growth is not tied to that pragma. See the memory use baseline and the long-running process memory notes for figures gathered outside of this journal mode comparison specifically.

## Startup Time and Journal Mode (Section owner: Elliot Frame, Core Services)

Startup time picks up a small but measurable cost from a WAL file that has grown large before a housekeeping pass has had a chance to run:

| Condition | Cold Start (ms) | Warm Start (ms) |
|---|---:|---:|
| original mode, no leftover journal file | 142 | 39 |
| original mode, leftover journal file after an unclean stop | 168 | 61 |
| WAL mode, no leftover WAL/SHM files | 145 | 41 |
| WAL mode, WAL file under 500 pages | 151 | 44 |
| WAL mode, WAL file over 4000 pages | 210 | 98 |

The last row is the one worth paying attention to: if the service is stopped for a while with a large amount of outstanding content sitting in the WAL file, the next start has to work through that file before the database file is fully usable, and the cold start figure in particular climbs well past anywhere near the other WAL rows. This is one of the reasons regular housekeeping passes matter beyond their effect on file size alone. See the startup time tracking page and the cold start versus warm start notes for figures outside the journal mode angle specifically.

## WAL File Growth and Housekeeping

Under WAL mode, the WAL file grows with each write, receiving new content in write order rather than the main database file being touched directly. SQLite triggers a housekeeping pass on its own once the WAL file passes roughly 1000 pages by default, folding its content back into the main file and making that space available for reuse rather than the file growing without bound. During the write latency sessions above, WAL file size at the end of a 500-call group ranged from about 480 KB to 2.1 MB depending on synchronous setting, well under the point where an automatic pass would have kicked in mid-group.

Manual housekeeping (running a pass by hand rather than waiting on the automatic threshold) was not exercised as part of this page's sessions; the full procedure and its own timing figures are covered separately.

## Recommendations and Current Setting

As of this page's last update, the recommended setting across most deployments is:

- journal mode: WAL
- synchronous: NORMAL

This is the combination that showed the best write latency in the table above while staying within what Data Systems considers a reasonable outstanding-content window between housekeeping passes for a database file this size.

The original rollback journal is still kept as the setting on a small number of hosts where the database file sits on a network filesystem — SQLite's own documentation is fairly direct that WAL mode does not work well in that setup, since the shared-memory file it depends on generally needs a local filesystem behind it. Those hosts are tracked separately and are not reflected in the write latency table above.

## Known Issues and Open Questions

- WAL file growth under bursty write load (many writes landing close together) has not been characterized past the 500-call groups used for the latency table; a longer, bursty session is on the list for a future round.
- The page cache size figures in this page (v1.1) are a narrow slice of the full range Data Systems has since gone through; treat the numbers here as a starting point rather than the final word.
- Memory growth under WAL past six hours has not been trialed; whether it keeps climbing or flattens out further past that point is still open.
- Startup time under a very large, never-housekept WAL file (tens of thousands of pages) has not been measured; the 4000-page row above is the largest looked at so far.

## Files and Paths Referenced

| Path | Purpose |
|---|---|
| `accountsvc/` | package directory at the repository root (no `src/` folder is used) |
| `README.md` | repository root readme, notes the basic layout of accountsvc/ |
| `docs/performance-notes/sqlite-journal-mode-notes.md` | this page |
| `docs/performance-notes/sqlite-page-cache-tuning.rst` | companion notes on page cache size settings |
| `docs/performance-notes/sqlite-wal-housekeeping.md` | companion notes on WAL file housekeeping passes |
| `docs/performance-notes/profiling-sessions-2024.md` | log of profiling sessions run during 2024, some referenced on this page |
| `docs/performance-notes/startup-time-tracking.md` | companion notes on startup timing across a wider set of conditions |
| `scripts/profile_journal_modes.sh` | shell script that steps through each journal mode, running a timing group for each in turn |
| `scripts/loopback_timing.sh` | shell script that fires a set number of write calls at the loopback interface and writes elapsed times out to a CSV |
| `/opt/accountsvc/var/state.db` | database file location on the profiling workstation |
| `/opt/accountsvc/var/state.db-wal` | the WAL file that appears next to the database file once WAL mode is in use |
| `/opt/accountsvc/var/state.db-shm` | the shared-memory file that accompanies the WAL file |
| `/var/log/accountsvc/` | folder holding CSV output from timing groups and raw memory sampling output |

## Tools and Libraries

| Tool / Library | Version | Purpose |
|---|---|---|
| Python | 3.11.6 | runtime accountsvc and its stdlib SQLite interface run on |
| SQLite (bundled) | 3.43.2 | database file format and the pragma settings covered on this page |
| sqlite3 (CLI) | 3.43.2 | used directly, outside of accountsvc, to set and check journal mode by hand |
| cProfile | stdlib, ships with Python 3.11.6 | used in a few early 2023 sessions before the focus narrowed to journal mode alone |
| tracemalloc | stdlib, ships with Python 3.11.6 | used alongside the resource module for the memory figures on this page |
| resource module | stdlib, POSIX only | used to sample RSS at intervals during long sessions |
| curl | 8.4.0 | used inside loopback_timing.sh to fire write calls |
| GNU awk | 5.1.0 | used to aggregate CSV output into median and p95 figures |
| Ubuntu | 22.04.4 LTS | operating system on the profiling workstation (sqlab-03) |

## Change Log

* **2023-11-02** — v1.0.0 — first draft, written after an initial session in October comparing the original rollback journal against WAL on sqlab-03
* **2024-01-15** — v1.1.0 — added TRUNCATE and PERSIST to the comparison table, reran the original mode figures on a quieter workstation
* **2024-02-20** — v1.1.1 — corrected the page cache figures after cross-checking against the companion cache size page
* **2024-04-03** — v1.1.2 — added the memory use section for extended WAL sessions
* **2024-05-10** — v1.1.3 — added the startup time section covering WAL file size at boot
* **2024-06-19** — v1.2.0 — changed the recommended setting to WAL with synchronous=NORMAL following the second-quarter round of sessions; expanded known issues

## Related Pages

- [Performance Notes Index](README.md)
- [SQLite Page Cache Tuning](sqlite-page-cache-tuning.rst)
- [SQLite WAL Housekeeping](sqlite-wal-housekeeping.md)
- [Loopback Response Times](loopback-response-times.md)
- [Memory Use Baseline](memory-use-baseline.md)
- [Long-Running Process Memory Notes](long-running-process-memory.txt)
- [Startup Time Tracking](startup-time-tracking.md)
- [Cold Start Versus Warm Start](cold-start-vs-warm-start.txt)
- [Profiling Sessions, 2024](profiling-sessions-2024.md)
- [Profiling Sessions, 2025](profiling-sessions-2025.md)
- [Connection Pool Sizing](connection-pool-sizing.md)

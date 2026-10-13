Profiling Sessions, 2024

**Version:** 2.1
**Owner:** Runtime Performance (Priya Nandakumar)
**Last updated:** 2024-11-08

**Summary:** A log of profiling sessions run against the package during 2024, with notes on setup and observed hotspots.

---

## Coverage and Purpose

This page collects the profiling sessions that Runtime Performance ran against the package across 2024. It walks through how each session was set up, what SQLite settings were tried, what round-trip timing looked like over the loopback interface, how memory use behaved under sustained load, and how startup timing shifted as settings changed. Sessions for 2025 onward are tracked separately in *Profiling Sessions, 2025*; this page is frozen as the 2024 log and isn't expected to gain new entries going forward.

Most of the sessions described here were exploratory rather than a fixed set repeated on a schedule — someone would try a SQLite setting combination, watch the numbers, and either fold the change into an upcoming release or write it down as a dead end. Where a session produced a change that shipped, the change is noted with the release it landed in, and the release is cross-checked against the change log near the bottom of this page.

A couple of housekeeping notes before the detail below:

- All timing numbers in this page are round-trip time as seen by the caller of the loopback interface, not any internal processing time, since the package doesn't expose its own internal timer.
- Memory numbers came from the operating system's own process view, not from anything reported by the package itself.
- Where a session was run on more than one machine, both sets of numbers are shown; where it wasn't, that's noted.

## Session Log

Owner: Runtime Performance (Priya Nandakumar)

| Date | Session | Focus | Engineer | Outcome |
|---|---|---|---|---|
| 2024-01-18 | S24-01 | Baseline round-trip timing over loopback, starting SQLite settings | Priya Nandakumar | Established starting numbers; no changes shipped |
| 2024-02-09 | S24-02 | Journal mode comparison (rollback journal vs WAL) | Priya Nandakumar | WAL adopted as default in v2.0 |
| 2024-03-22 | S24-03 | Page cache size sweep | Priya Nandakumar, Devon Ruiz | Cache raised from ~2 MB to 8 MB in v2.0 |
| 2024-05-14 | S24-04 | Memory use under sustained load, tied to write-ahead log growth | Sana Byrne | Follow-up picked up by Infrastructure in 2025 |
| 2024-06-27 | S24-05 | Startup timing, cold vs warm filesystem cache | Elliot Frame | No change shipped; folded into Startup Time Tracking |
| 2024-08-11 | S24-06 | synchronous=NORMAL vs FULL under WAL | Priya Nandakumar | NORMAL adopted for the loopback service in v2.1 |
| 2024-09-30 | S24-07 | Connection setup overhead on the loopback path | Priya Nandakumar | Small fix shipped in v2.1 |
| 2024-11-04 | S24-08 | Re-check of page cache sweep after the v2.1 change | Priya Nandakumar, Devon Ruiz | Confirmed 8 MB still the right default |

A couple of shorter follow-ups (informally called S24-04a and S24-06b at the time) ran the same week as their parent sessions and are folded into the S24-04 and S24-06 notes below rather than getting their own rows.

## Profiling Setup

Owner: Runtime Performance (Priya Nandakumar)

All 2024 sessions ran on the same two machines to keep numbers comparable across the year:

- A Windows 11 23H2 workstation, 4 cores, 8 GB RAM — used for most sessions.
- An Ubuntu 22.04 LTS virtual machine, 2 cores, 4 GB RAM — used to cross-check S24-02, S24-03, and S24-06, mostly to confirm that WAL behavior wasn't specific to one filesystem.

The package was started with its default settings unless a session called out a changed setting explicitly. Every session started from a fresh copy of the database file — a leftover file from an earlier session with a different journal mode produced confusing numbers on more than one occasion, so copying a clean database file into place before starting the loopback service is now the first step of every session's setup, whether or not the write-up below spells it out again for each one.

Round-trip timing was collected with a small shell-based timing loop kept in the scripts folder rather than any external timing tool, since the loopback interface only needs a simple repeated-call harness. A typical setup for a timing session looks roughly like this:

```
# copy a clean database file into place
copy accountsvc-clean.db accountsvc.db

# confirm current SQLite settings before starting the loopback service
sqlite3 accountsvc.db "PRAGMA journal_mode; PRAGMA cache_size; PRAGMA synchronous;"
```

On the Ubuntu VM the equivalent setup uses `cp` in place of `copy`, and the timing loop is a bash script rather than a PowerShell one; the underlying approach is the same on both machines. Configuration for the timing loop itself — call counts, warm-up calls before numbers are recorded, and so on — is kept out of this page and lives in *Profiling Tool Configuration*, which the loop scripts read from at the start of a run.

Memory numbers were read from the operating system's own process view: Task Manager's details tab on Windows, and `ps` together with `/proc/<pid>/status` on the Ubuntu VM. The package doesn't report its own memory use, so there was never a temptation to compare an internal number against an external one — the only numbers in this page are what the operating system reported.

## SQLite Settings Explored

Owner: Runtime Performance, with setting guidance from Data Systems (Devon Ruiz)

Three settings came up repeatedly across the 2024 sessions: journal mode, page cache size, and the synchronous setting. Deeper background on each of these lives in the sibling pages *SQLite Journal Mode Notes* and *SQLite Page Cache Tuning*; this section only covers what was actually tried during 2024 sessions and what it did to the numbers below, not the full reasoning behind each setting.

### Journal mode

The package shipped with SQLite's original rollback-journal mode through v1.x — the mode most SQLite installs use unless something explicitly turns WAL on. Session S24-02 compared that starting mode against WAL mode, and against TRUNCATE mode for completeness, on both machines:

| Journal setting | Write round-trip, p50 (ms) | Write round-trip, p95 (ms) |
|---|---|---|
| Rollback journal (starting default) | 6.8 | 14.2 |
| WAL | 3.1 | 6.0 |
| TRUNCATE | 6.1 | 12.9 |

WAL mode roughly halved write-side round-trip timing on both machines, mostly because it avoids the extra filesystem work the rollback journal does around each write. WAL was adopted as the shipped default in v2.0. One side effect worth calling out here: WAL keeps a separate write-ahead log file next to the main database file, and that file grows between the moments its contents are folded back into the main file. That growth mattered for the memory notes further down this page, and it's covered in more depth in *SQLite WAL Housekeeping*.

To set journal mode by hand for a one-off session:

```
sqlite3 accountsvc.db "PRAGMA journal_mode=WAL;"
```

### Page cache size

SQLite's page cache setting (`cache_size`) controls how many pages it keeps in memory before going back to disk for them. The package's starting default going into 2024 was SQLite's own built-in default, which works out to roughly 2 MB on a typical page size. Session S24-03 swept through a few sizes:

| cache_size setting | Approx. cache size | Read round-trip, p50 (ms) | Read round-trip, p95 (ms) |
|---|---|---|---|
| -2000 | ~2 MB (starting default) | 4.4 | 9.7 |
| -8000 | ~8 MB | 2.9 | 5.8 |
| -16000 | ~16 MB | 2.7 | 5.5 |
| -32000 | ~32 MB | 2.6 | 5.4 |

Going from 2 MB to 8 MB gave the biggest jump; past that the returns were small and not worth the extra resident memory on a loopback-only service that mostly answers one caller at a time. 8 MB (`cache_size=-8000`) was adopted as the new default in v2.0. Devon Ruiz's page cache guidance (see *SQLite Page Cache Tuning*, currently at v1.1) goes into more detail on how this setting interacts with page size and with the operating system's own file cache, which this page doesn't repeat.

### synchronous setting

Session S24-06 looked at `synchronous=NORMAL` against `synchronous=FULL` under WAL mode. FULL is more careful about an unclean stop but forces an extra disk flush that WAL under NORMAL can skip. On the Windows workstation:

| synchronous | Write round-trip, p50 (ms) | Write round-trip, p95 (ms) |
|---|---|---|
| FULL | 4.0 | 8.1 |
| NORMAL | 3.1 | 6.0 |

Given that the package's database file is local and the loopback service isn't usually under heavy write pressure, NORMAL was adopted for v2.1. This lines up with SQLite's own guidance that NORMAL under WAL is a reasonable choice for most single-machine uses.

### How the settings interact

None of the three settings above were tried fully independently of the others — by the time S24-06 ran, WAL and the 8 MB page cache were already the shipped defaults from v2.0, so the synchronous comparison happened on top of those, not against the original 2 MB rollback-journal starting point. Session S24-08 re-ran the page cache sweep from S24-03 after the v2.1 synchronous change shipped, mostly to make sure the earlier 8 MB conclusion still held once synchronous had also changed. It did — the numbers from S24-08 were within a few tenths of a millisecond of the S24-03 numbers at each cache size, so 8 MB stayed the default rather than getting revisited.

## Loopback Response Time Measurements

Owner: Runtime Performance (Priya Nandakumar)

Round-trip timing was collected by issuing repeated calls over the loopback interface (127.0.0.1) and timing the round trip from just before a call was sent to just after its response was read. Full detail on the loopback measurement approach, and the ongoing set of numbers past 2024, live in *Loopback Response Times*; the table below is the 2024-specific set, using the settings that shipped in v2.1 (WAL, 8 MB page cache, synchronous=NORMAL):

| Call type | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| Read, small response | 2.6 | 5.4 | 8.0 |
| Read, larger response | 3.9 | 7.2 | 10.5 |
| Write | 3.1 | 6.0 | 9.3 |

A few notes from running these repeatedly across the year:

1. The very first call after the loopback service starts is reliably slower than the rest — often three to five times the steady-state p50 — because the page cache is still cold. This is covered separately in the startup timing section below and in *Cold Start Versus Warm Start*.
2. p99 numbers were noisier than p50 or p95 on the Windows workstation, most likely from other processes on the same machine rather than anything in the package itself. The Ubuntu VM's p99 numbers were steadier, which supports that read.
3. The Ubuntu VM consistently ran 10 to 15 percent faster than the Windows workstation on the same settings across every session that used both machines. This is assumed to be filesystem overhead on the Windows side rather than anything SQLite-specific, but it wasn't investigated further during 2024.
4. Response size mattered more than call type — the "read, larger response" row is slower than "write" even though writes have more work to do on the SQLite side, simply because more bytes have to cross the loopback interface and get formatted on the way out.

One thing worth flagging for anyone reusing these numbers later: the 2024 table above reflects a single caller issuing one call at a time. Concurrent-caller numbers, and how the round-trip time changes when more than one caller is active at once, are covered separately under *Connection Pool Sizing* rather than in this page.

## Memory Use Observations

Owner: Infrastructure (Sana Byrne), cross-posted from session S24-04

Session S24-04 ran the loopback service under a steady stream of calls for two hours and watched resident memory over that window. Baseline numbers, and the fuller picture across the rest of the year, are in *Memory Use Baseline*; the 2024 session numbers were:

| Point in the run | Resident memory (approx.) |
|---|---|
| Just after start, before first call | 17 MB |
| After first call (cold page cache warm-up) | 24 MB |
| Steady state, light load | 28 MB |
| Steady state, sustained write load | 42-48 MB |
| 30 minutes after load stopped | 30 MB |

The growth under sustained write load tracks the write-ahead log file's own growth — the log file gets bigger between the moments its contents are folded back into the main database file, and that growth shows up as extra resident memory for the pages SQLite is keeping warm, not as memory the package's own code is holding onto and failing to give back. Once the log file is folded back and the load lets up, memory settles down close to the steady-state light-load number rather than climbing without bound over the two-hour window. Sana Byrne's follow-up note on this ties it to the guidance in *SQLite WAL Housekeeping* on how often the fold-back happens by default and how to force it sooner during a long-running session.

One open question from S24-04 that didn't get a clean answer during 2024: whether the 42-48 MB range under sustained write load keeps growing over a run much longer than two hours, or whether it's a hard ceiling tied to the page cache and log-growth settings in place at the time. Infrastructure picked this question up again the following year; see *Long-Running Process Memory Notes* for how that turned out. It's also worth noting that the "30 minutes after load stopped" row settling near 30 MB rather than all the way back to the 17-24 MB starting range suggests the warm page cache from the earlier load stays useful even once the write pressure is gone, which is expected rather than a concern.

## Startup Time Measurements

Owner: Core Services (Elliot Frame), session S24-05

Startup timing was measured from the moment the loopback service process was started to the moment it answered its first call. Elliot Frame ran this on both machines, comparing a cold filesystem cache (right after a reboot) against a warm one (service stopped and started again a few minutes later on the same machine, with the operating system's file cache still holding relevant pages):

| Condition | Windows workstation | Ubuntu VM |
|---|---|---|
| Cold filesystem cache | 140 ms | 95 ms |
| Warm filesystem cache | 82 ms | 58 ms |
| Write-ahead log not yet folded back from a prior unclean stop | 210 ms | 150 ms |

The third row matters more than it might look. If the previous run of the service was stopped in the middle of a write — a power loss, a forced stop, anything that didn't let it shut down on its own — the write-ahead log file may still hold writes that haven't been folded back into the main database file yet. The next start has to fold those back before it can answer its first call, and that shows up as the slower startup number above. This case, and the broader difference between a clean and an unclean prior stop, is the main subject of *Cold Start Versus Warm Start* (Core Services, last touched in early 2025) and is tracked over time in *Startup Time Tracking*.

No startup-time changes shipped out of the 2024 sessions; the numbers above were mostly used to set expectations for later work rather than to justify a change on their own. One small methodology note for anyone repeating this measurement: "cold filesystem cache" here means right after a reboot of the whole machine, not just stopping and restarting the service — stopping and restarting alone, even a few minutes apart, was closer to the warm-cache row than the cold one in every run Elliot tried.

## Hotspots and Follow-up Work

Owner: Runtime Performance, with items assigned across teams

The 2024 sessions turned up a short list of places worth more attention:

- Connection setup on the loopback path had a small, fixable overhead that came from re-reading SQLite settings on every new connection instead of once at start. Fixed in v2.1 — see the change log below.
- Page cache warm-up on the first call after start is unavoidable with the current approach and isn't worth chasing further; see the startup timing notes above.
- Write-ahead log growth under sustained write load is fine for the memory ranges seen in S24-04, but the open question about longer runs was picked up by Infrastructure the following year rather than closed out in 2024.
- The gap between Windows and Ubuntu round-trip timing (10 to 15 percent in most sessions) was noted but not investigated further during 2024; it's flagged for whoever next revisits loopback timing on Windows.
- Garbage collector behavior under sustained load came up briefly in S24-06 as a possible contributor to the noisy p99 numbers on Windows, but Platform Tools' own look at collector settings didn't start until much later; see *Garbage Collector Tuning Notes* for that separate thread.
- Connection setup and page cache warm-up together account for most of why the very first call after start is so much slower than steady state; splitting the two apart wasn't attempted in 2024 and would need a smaller, more targeted session than the ones logged here.

None of the above were treated as urgent during 2024 — the package's typical caller pattern is light enough that none of these showed up as a real problem outside of profiling sessions specifically set up to look for them.

## Terminology

- **journal mode** — the SQLite setting that controls how it protects the database file against an unclean stop while writing; the rollback journal mode and WAL mode are the two discussed most in this page.
- **write-ahead log (WAL)** — under WAL journal mode, a separate file next to the main database file that holds new writes until they're folded back into the main file.
- **fold back** (of the write-ahead log) — the point at which SQLite merges the contents of the write-ahead log file back into the main database file, keeping the log file from growing without bound.
- **page cache** — the set of database pages SQLite keeps in memory (controlled by the `cache_size` setting) to avoid going back to disk for pages it has already read.
- **synchronous setting** — the SQLite setting controlling how aggressively it forces writes to disk before treating them as durable; FULL and NORMAL are the two values discussed here.
- **loopback interface** — the local network interface (127.0.0.1) the service listens on for calls originating from the same machine.
- **round-trip time** — the time from just before a call is sent to just after its response is read, as seen by the caller.
- **p50 / p95 / p99** — the median, 95th-percentile, and 99th-percentile values in a set of round-trip time measurements; higher percentiles show the slower end of the range.
- **cold start** — starting the loopback service when neither the operating system's filesystem cache nor SQLite's own page cache holds anything useful yet.
- **warm start** — starting the loopback service shortly after a previous run, when the filesystem cache still holds relevant pages.
- **resident memory** — the portion of a process's memory that's actually held in RAM at a given moment, as reported by the operating system.
- **unclean stop** — a case where the loopback service process ends without going through its own normal shutdown, such as a power loss or a forced stop.

## Files Referenced

- `accountsvc/` — the package directory; this page refers to it only as "the package" and doesn't describe what's inside it.
- `README.md` — the repository's root overview page.
- `docs/performance-notes/profiling-sessions-2024.md` — this page.
- `docs/performance-notes/sqlite-journal-mode-notes.md` — deeper background on journal mode choices, maintained by Data Systems.
- `docs/performance-notes/sqlite-page-cache-tuning.rst` — deeper background on page cache sizing, also maintained by Data Systems.
- `docs/performance-notes/loopback-response-times.md` — the ongoing set of loopback timing numbers, of which the 2024 numbers in this page are a subset.
- `docs/performance-notes/memory-use-baseline.md` — the ongoing memory-use log that S24-04's numbers feed into.
- `docs/performance-notes/startup-time-tracking.md` — the ongoing startup-timing log that S24-05's numbers feed into.
- `docs/performance-notes/profiling-tool-config.yaml` — settings for the timing loop scripts, such as call counts and warm-up counts, kept separate from this page.
- `scripts/loopback-timing.ps1` — the Windows timing loop used to collect round-trip numbers.
- `scripts/loopback-timing.sh` — the equivalent timing loop for the Ubuntu VM.
- `scripts/copy-clean-db.ps1` — copies a fresh database file into place before a timing session, to avoid a leftover file from a previous session's journal mode setting affecting the next one.
- `logs/profiling-2024/` — raw timing output from each session listed in the session log above, kept as one file per session date.

## Tools and Package Versions

| Tool / package | Version used in 2024 sessions | Notes |
|---|---|---|
| Python (standard library only) | 3.11.6 | No external packages used by the package itself |
| SQLite (bundled with the Python build used) | 3.43.2 | Same bundled version on both machines |
| sqlite3 CLI | 3.43.2 | Used for hand-checking settings outside the package |
| Windows 11 | 23H2 | Primary workstation for most sessions |
| Ubuntu | 22.04 LTS | Cross-check virtual machine |
| PowerShell | 7.4.0 | Timing loop and setup scripts on Windows |
| bash | 5.1 | Timing loop and setup scripts on the Ubuntu VM |
| cProfile (standard library) | bundled with Python 3.11.6 | Used in S24-07 to narrow down the connection setup overhead |

## Change Log

- **2024-01-22 (v1.8):** Initial 2024 session log started; carried over baseline numbers from late-2023 sessions for comparison.
- **2024-02-14 (v1.9):** Notes on the rollback-journal-vs-WAL comparison (S24-02) added ahead of the v2.0 default change.
- **2024-03-28 (v1.9.1):** Page cache sweep (S24-03) numbers added.
- **2024-06-02 (v2.0):** Updated to reflect the shipped v2.0 defaults — WAL journal mode and an 8 MB page cache — and to record S24-04's memory numbers.
- **2024-07-05 (v2.0.1):** Startup timing table from S24-05 added; small wording fixes throughout.
- **2024-09-15 (v2.1-draft):** Draft notes on the synchronous setting change (S24-06) added ahead of the v2.1 release.
- **2024-10-03 (v2.1):** Updated for the shipped v2.1 defaults — synchronous=NORMAL and the connection setup fix from S24-07.
- **2024-11-08 (v2.1):** Added S24-08's confirmation numbers and the hotspots summary; no version change, page content finalized for the year.

## Related Pages

- Performance Notes Index
- Profiling Sessions, 2025
- SQLite Journal Mode Notes
- SQLite Page Cache Tuning
- Loopback Response Times
- Memory Use Baseline
- Startup Time Tracking
- SQLite WAL Housekeeping
- Cold Start Versus Warm Start
- Connection Pool Sizing
- Garbage Collector Tuning Notes
- Profiling Tool Configuration
- Long-Running Process Memory Notes

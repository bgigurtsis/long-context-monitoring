# Startup Time Measurements

**Version:** v2.0.2
**Owner:** Developer Experience (Owen Fischer)
**Last updated:** 2025-03-18

**Summary:** Compares startup time for the package's command line and the service across recent versions, and connects those numbers back to the SQLite settings, memory behavior, and loopback response times measured elsewhere in this folder.

---

## Coverage

This page covers the time between invoking the command line entry point (or launching the service) and the point where the package is ready to do useful work — for the CLI that means the point where the first line of output could appear, and for the service that means the point where the loopback socket is bound and accepting connections. It does not cover the time to process a request once the service is up (see the sibling page on loopback response times) or the time to write a first record to the database file (see write throughput). It also does not go deep into flame graph capture technique, which has its own page.

Startup time work on auditlog has historically been a low-priority corner of performance work — the package is small, the standard library is fast, and most deployments run the service as a long-lived process rather than restarting it often. That said, the command line tool is invoked fresh on every call from shell scripts and cron-style jobs on some hosts, so shaving milliseconds off CLI startup has a real, multiplicative effect for teams that call it hundreds of times a day.

## Terminology

- **Cold start** — starting the process with no relevant pages of the executable or its imports already resident in the OS page cache, typically the first invocation after a reboot or after a long idle period.
- **Warm start** — starting the process when the interpreter, standard library modules, and the package's own modules are already resident in the OS page cache from a recent prior run.
- **Loopback interface** — the local-only network interface (127.0.0.1) the service binds to; it never listens on an externally reachable interface.
- **Journal mode** — the SQLite setting that controls how the database file records in-flight changes before they are made durable; on this package it is set at connection open time, which is part of the startup path for the service (see the SQLite journal mode page).
- **Page cache size** — the SQLite `cache_size` pragma, which controls how many database pages SQLite keeps in memory; distinct from the operating system's own page cache for file-backed memory.
- **Wall-clock time** — elapsed real time as measured by a stopwatch or timer, as opposed to CPU time, which excludes time spent waiting.
- **Import time** — the portion of process startup spent loading and initializing Python modules, before any package-specific setup logic runs.
- **Socket bind time** — the portion of service startup spent creating and binding the loopback listening socket, measured separately from import time because it can be affected by other local processes holding the port briefly.
- **Resident set size (RSS)** — the amount of physical memory the process occupies at a point in time, used here as a rough memory-use figure during and shortly after startup.
- **Steady state** — the point after startup where CPU and memory use settle into a stable pattern, used as the boundary marking the end of the "startup" measurement window.

## Measurement environment

Numbers on this page were collected on two machines, referred to below as Host A and Host B:

- Host A: a Windows 10 desktop (build 19045) used for local developer profiling, spinning disk replaced with SATA SSD, 16 GB RAM.
- Host B: a Linux VM (kernel 6.1) used to approximate the shape of the small internal hosts the service actually runs on in production, 4 vCPU, 8 GB RAM, database file stored on the VM's local disk rather than a network mount.

Timings were not collected on the same physical hardware across all releases in the table below — early v1.8 numbers came from a since-decommissioned laptop and should be read as directional only, not as strictly comparable to the v2.0.x column. This inconsistency has come up more than once in review and we have not gone back to re-run the old versions, mostly because rebuilding a v1.8 environment takes more effort than it's worth for outdated numbers.

Timings use the shell's own timing facilities rather than anything built into the package — `Measure-Command` on PowerShell for Host A, and `time` piped through `/usr/bin/time -v` on Host B for the memory figures. Five runs were taken for each cell in the cold-start tables and the median is reported; for warm-start tables ten runs were taken since the variance is lower and outliers are rarer.

## Tools and library versions

| Tool / library | Version | Used for |
|---|---|---|
| Python | 3.11.7 | interpreter running the package on both hosts |
| PowerShell | 7.4.1 | timing harness and Measure-Command on Host A |
| GNU time | 1.9 | wall-clock and RSS capture on Host B |
| sqlite3 (CLI) | 3.44.2 | inspecting pragma state on the database file outside the package |
| strace | 6.6 | syscall-level tracing during a subset of cold-start sessions on Host B |
| Procmon | 3.110 | file and registry access tracing on Host A during cold starts |
| py-spy | 0.3.14 | sampling profiler used for the flame graph captures referenced below |
| eventlog | v2.0.2 (also v2.0.1, v2.0.0, v1.9.4, v1.9.0, v1.8.2 for comparison) | package under evaluation |

## Profiling sessions relevant to startup

The full profiling log lives in the Profiling Session Log (see the profiling-sessions page for the complete record, v2.2, owned by Systems Reliability). Three sessions there are directly relevant to startup and are summarized here rather than duplicated in full:

1. **Session 2025-02-11** — first systematic cold-vs-warm comparison for the CLI, run on Host A, flagged that roughly 60% of cold-start wall-clock time was import time rather than anything package-specific.
2. **Session 2025-03-03** — follow-up session isolating socket bind time for the service on Host B, run after a report that the service occasionally took over a second to become reachable on loopback after being started from a shell script.
3. **Session 2025-03-14** — repeat of the 2025-02-11 session against v2.0.2 (then a release candidate) to confirm a regression fix landed before the 2.0.2 tag went out.

Flame graphs for the 2025-03-03 session are kept separately; see flamegraph-captures for the raw captures rather than re-deriving them here.

## Command line startup time, by release

The table below is cold-start median wall-clock time from process launch to the CLI's first line of output, measured on Host A unless noted.

| Release | Cold start (ms) | Warm start (ms) | Notes |
|---|---|---|---|
| v1.8.2 | 210 | 95 | laptop hardware, see caveat above |
| v1.9.0 | 205 | 90 | no material change from 1.8.2 |
| v1.9.4 | 240 | 92 | regression traced to an added import at module load time |
| v2.0.0 | 250 | 98 | regression from 1.9.4 not fixed, carried forward |
| v2.0.1 | 130 | 60 | import moved to be lazy; largest single improvement recorded on this page |
| v2.0.2 | 125 | 58 | minor cleanup, within noise of v2.0.1 |

The v1.9.4 → v2.0.0 regression sat unresolved for two release cycles because it did not show up clearly in warm-start numbers, which is what most reviewers were looking at during those cycles. Cold start is the number that matters for the CLI use case described in the Coverage section above, and it was not being tracked as its own line item in review until early 2025.

Procedure used to reproduce the cold-start numbers on Host A:

1. Reboot the host, or at minimum flush the standby list with a memory-pressure tool, so the executable and its imports are not resident in the OS page cache.
2. Open a fresh PowerShell session (a new session avoids any module-loading warm-up from the shell itself).
3. Run the CLI with `Measure-Command { & auditlog <verb> } | Select-Object TotalMilliseconds`.
4. Discard the first run as a throwaway and record the next five.
5. Repeat for a warm-start figure by running the same invocation five more times without any cache flush in between.

On Host B, the equivalent uses `sync; echo 3 > /proc/sys/vm/drop_caches` before each cold run (this requires elevated shell access on that VM, which is fine for a disposable profiling host but is not something to do on a shared box), followed by `time` around the invocation.

## Service startup time, by release

Service startup time is measured from process launch to the first successful connection accepted on the loopback socket, using a small polling script (`scripts/wait-for-loopback.ps1` on Host A, a shell equivalent on Host B) that attempts a connection every 10 ms and records the elapsed time on success.

| Release | Cold start to bind (ms) | Warm start to bind (ms) | Bind time as % of total |
|---|---|---|---|
| v1.8.2 | 260 | 110 | ~15% |
| v1.9.0 | 255 | 108 | ~15% |
| v1.9.4 | 290 | 112 | ~13% |
| v2.0.0 | 300 | 118 | ~13% |
| v2.0.1 | 175 | 78 | ~20% |
| v2.0.2 | 170 | 76 | ~21% |

Bind time itself — the time spent creating and binding the loopback socket, separate from import and setup time — has stayed close to flat across every release measured, generally 25–35 ms cold and under 20 ms warm on both hosts. The percentage column grows in the v2.0.x releases simply because the denominator (total startup time) shrank; bind time was never the bottleneck, and the 2025-03-03 profiling session confirmed that the perceived slow-to-be-reachable behavior reported at the time was actually an issue in the calling script's own repeated-polling loop, not a service startup problem. That finding is recorded in more detail in the Profiling Session Log rather than here.

## SQLite settings on the startup path

Two SQLite settings are applied when the service opens its connection to the database file, and both sit squarely on the startup path rather than being deferred until first use, which is worth calling out because it surprises people who expect connection setup to be lazy.

**Journal mode.** The service sets the journal mode explicitly rather than relying on SQLite's default, and that pragma call is one of the more expensive individual operations during cold service startup because it can involve a file rewrite the first time it runs against a database file that was not already in the target mode. Once a database file has been switched to the target mode, subsequent startups against that same file do not pay this cost again — the mode is stored in the file itself. Full detail on which mode is used and why lives on the SQLite Journal Mode Settings page; the short version for startup purposes is that the switch cost is a one-time-per-file cost, not a one-time-per-process cost, so it only shows up in profiling as a startup spike on a brand-new database file or one that was created by an older version of the package with a different default.

**Page cache size.** The `cache_size` pragma is set on every connection open, including at service startup, and unlike journal mode this setting does not persist in the file — it is re-applied every time. The cost of setting it is negligible (well under a millisecond in every session where it was isolated), so it does not show up as a line item in the tables above, but it is mentioned here because a couple of profiling sessions over the past year have chased phantom startup slowness that turned out to be page cache warm-up (the OS filling its own page cache for the database file's pages, not the SQLite pragma) rather than anything on the package's own startup path. See Page Cache Size Tuning for the sizing rationale; this page is only concerned with the fact that the pragma call itself is cheap.

A representative snippet showing the settings inspected from outside the package, useful when trying to tell whether a slow startup is a database-file issue or a process issue:

```
sqlite3 records.db "PRAGMA journal_mode;"
sqlite3 records.db "PRAGMA cache_size;"
```

Running these against the actual database file before and after a service restart is a quick way to confirm the mode did not silently revert, which has happened in the past when a database file was copied from a host running an older package version.

## Memory use during startup

Memory during startup was measured with `/usr/bin/time -v` on Host B (the `Maximum resident set size` field) and with Procmon's private-bytes counter on Host A. Numbers below are peak RSS observed between process launch and steady state, not steady-state memory itself — see Memory Use Notes for steady-state figures, which are lower.

| Release | Peak RSS during CLI startup (MB) | Peak RSS during service startup (MB) |
|---|---|---|
| v1.8.2 | 14.2 | 16.8 |
| v1.9.0 | 14.0 | 16.5 |
| v1.9.4 | 14.6 | 17.1 |
| v2.0.0 | 14.8 | 17.4 |
| v2.0.1 | 13.1 | 15.9 |
| v2.0.2 | 13.0 | 15.8 |

The drop between v2.0.0 and v2.0.1 tracks the same lazy-import change that produced the wall-clock improvement above — fewer modules imported at startup means fewer objects allocated during that window, which is a straightforward relationship but one that is easy to miss if you only look at steady-state memory, which barely moved between those two releases. Process Memory Tracking has the longer-running memory curves if you need them; this page stops at the startup window.

## Response time on first request after startup

This is the point where startup work and loopback response work overlap, and it is worth a short note even though the detailed numbers live on the Loopback Response Time Measurements page.

The first request handled by a freshly started service is consistently slower than subsequent requests, by roughly 8–20 ms on Host B depending on release, because some setup work (notably the page cache pragma taking effect against real pages, as opposed to the pragma call itself) only completes once actual reads against the database file happen. In practice this shows up as a single slow first response followed by response times that match the steady-state figures reported on the sibling page within two or three requests. Teams that start the service fresh before every short-lived job rather than leaving it running should budget for this first-request cost separately from the startup time figures above — it is not captured in the "time to bind" numbers because the socket is accepting connections before this warm-up completes.

## Profiling procedure, in detail

For anyone repeating this work against a future release, the procedure used for the tables above:

1. **Prepare a clean database file.** Use a database file created fresh by the target release, not a file carried over from an older version, unless the specific goal is to measure the one-time journal-mode conversion cost described above.
2. **Choose cold or warm.** Decide up front which condition you are measuring and do not mix runs — reboot (or drop OS caches on Linux) for cold, and run the target invocation once as a throwaway immediately before timed runs for warm.
3. **Time the CLI** using the shell's own timer around a single representative verb invocation, five cold runs and ten warm runs, taking the median.
4. **Time the service** using a polling loop against the loopback target rather than trusting the shell's own "process launched" signal, since the shell returns control before the socket is necessarily bound.
5. **Capture memory alongside timing**, not as a separate pass — RSS drifts run-to-run and is more meaningful when tied to the same invocation that produced the timing figure.
6. **Record host, OS build, and Python version** in the session notes even when they match a prior session, since drift here is a common source of unexplained variance months later.
7. **Log raw numbers**, not just the median, in the timing log folder before summarizing into a table — the median alone has caused confusion in the past when someone needed to check for a bimodal distribution (slow-disk cold starts versus fast-disk cold starts on shared hosts) that a single number hides.

Raw logs from the sessions summarized on this page are kept under `logs/startup-timing/` on the internal profiling share, one subfolder per session date, each containing the shell output log and a small text summary. These are not checked into the repository.

## Known gaps and open questions

- The v1.8.x baseline numbers were never re-collected on current hardware, so the improvement shown between v1.8.2 and v2.0.2 in the tables above is probably somewhat overstated by hardware differences alone, not purely software improvement. Nobody has prioritized re-running them.
- Bind-time measurement on Host A currently reuses a script originally written for a different internal tool and has not been reviewed line by line in over a year.
- There is no current cold-start number for v2.0.2 on Host B at all — the Host B column in the service startup table above was collected on a slightly earlier Host B kernel (6.0, not 6.1) than the memory table, because the VM was rebuilt between those two sessions. This is a minor inconsistency between the two tables on this page and has not caused any wrong conclusions so far, but it means the two tables should not be read as coming from an identical environment.
- No one has done a side-by-side comparison of cold start under a container runtime versus bare-metal/VM, which several teams have asked about informally.

## Files referenced by this page

- `auditlog/` — the package directory at the repository root; startup timing covers the path from process launch through this package's own setup work.
- `README.md` — repository root readme; contains the general package description referenced when describing what "ready" means for the CLI and the service.
- `docs/performance-notes/startup-time.md` — this page.
- `docs/performance-notes/profiling-sessions.md` — the fuller profiling session log referenced throughout the Profiling sessions section above.
- `docs/performance-notes/sqlite-journal-mode.md` — detail on the journal mode setting mentioned in the SQLite settings section.
- `docs/performance-notes/page-cache-sizing.md` — detail on the page cache pragma mentioned in the SQLite settings section.
- `docs/performance-notes/loopback-response-times.md` — steady-state response time figures referenced in the first-request section.
- `docs/performance-notes/memory-use-notes.md` — steady-state memory figures referenced in the memory section.
- `scripts/wait-for-loopback.ps1` — polling script used on Host A to measure service bind time.
- `logs/startup-timing/` — folder on the internal profiling share holding raw shell output logs and summaries from each session referenced above; not checked into the repository.
- database file (default location under the service's local data directory, path configurable) — the SQLite file whose journal mode and page cache pragma settings are applied during service startup.

## Change log

- **2024-06-02, v1.8.2** — first dedicated cold/warm startup measurement pass, Host A only, Owen Fischer.
- **2024-09-19, v1.9.0** — added service bind-time measurement using the polling script; no material change in numbers from v1.8.2.
- **2024-11-27, v1.9.4** — flagged a cold-start regression traced to a module-level import added for an unrelated feature; not fixed at the time, carried into v2.0.0.
- **2025-02-11, v2.0.0** — full profiling session confirming the regression was still present; opened a follow-up item to make the import lazy.
- **2025-03-03, v2.0.1** — regression fixed by deferring the import; largest single startup improvement recorded on this page, roughly halving cold-start time for both the CLI and the service.
- **2025-03-14, v2.0.2** — confirmation pass against the 2.0.2 release candidate; numbers within noise of v2.0.1, page rewritten to reflect the current release as the primary comparison column.
- **2025-03-18, v2.0.2** — page reviewed and republished with the memory-use table and the known-gaps section added; owner changed from Systems Reliability to Developer Experience to reflect who was actually doing this work going forward.

## Related pages

- [Performance Notes Index](README.md)
- [Profiling Session Log](profiling-sessions.md)
- [SQLite Journal Mode Settings](sqlite-journal-mode.md)
- [Page Cache Size Tuning](page-cache-sizing.md)
- [Loopback Response Time Measurements](loopback-response-times.md)
- [Memory Use Notes](memory-use-notes.md)
- [Cold Start Versus Warm Start](cold-start-vs-warm-start.md)
- [Write Throughput on the Database File](write-throughput.md)
- [Concurrency Notes](concurrency-notes.rst)
- [Profiling Tools](profiling-tools.rst)
- [Baseline Measurements](baseline-measurements.yaml)
- [Process Memory Tracking](process-memory-tracking.txt)
- [Flamegraph Captures](flamegraph-captures.txt)

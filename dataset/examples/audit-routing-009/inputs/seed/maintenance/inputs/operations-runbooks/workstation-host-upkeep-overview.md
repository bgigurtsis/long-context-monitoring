# Workstation and Small Host Upkeep Overview

**Version:** 1.5
**Owner:** Systems Engineering (Owen Baptiste)
**Last updated:** 2024-07-08

## Purpose and Coverage

This page is the entry point for the upkeep work a maintainer does around the auditlog package when it's running somewhere small — a personal workstation, a spare laptop repurposed as a shared host for two or three people, or a small VM that nobody on Infra Reliability would call "production." It does not try to replace the detailed pages in this folder; instead it lays out the rhythm of upkeep — what to check, how often, and in what order — and points to the page that goes deep on each topic.

The auditlog package is intentionally light: it's pure standard-library Python, it runs a loopback HTTP service for local callers, it has a command line for people who'd rather not open a browser, and it keeps everything in one SQLite database file on disk. That simplicity is exactly why upkeep on a workstation or small host looks different from upkeep on a fleet-managed server — there's no orchestration layer catching a stuck process, no shared disk quota system flagging you before you run out of space, and no separate log-shipping pipeline moving console output somewhere durable. All of that falls to whoever is running the service day to day, which on a workstation is usually just you.

This page assumes a maintainer who already has auditlog installed and running, either via the command line directly or as a background process started when the system boots or when a session starts. It does not cover installation or first-run setup.

## Who This Applies To

Two rough categories show up in practice, and the upkeep cadence differs a bit between them.

- **Personal workstation** — one person, one machine, auditlog running most of the time in the background, database file living somewhere under the user's own profile.
- **Small shared host** — two to six people pointing their local tools at one loopback service running on a shared machine (a desk-side box, an old workstation repurposed as a "team box," or a small always-on VM), with the database file and console log living under a service-owned path rather than a personal one.

| Environment | Typical maintainer | Database file location (example) | Who watches disk and logs |
|---|---|---|---|
| Personal workstation (macOS/Linux) | The individual engineer | `~/.auditlog/store.db` | That engineer, on their own schedule |
| Personal workstation (Windows) | The individual engineer | `C:\Users\<name>\AppData\Local\auditlog\store.db` | That engineer |
| Small shared host (Linux) | Whoever set it up, informally | The data file stored locally in the standard directory | Shared by 2-6 people, unevenly |
| Small shared host (Windows) | Same as above | `C:\ProgramData\auditlog\data\auditlog.db` | Same as above |

Note that "small shared host" upkeep tends to slip precisely because nobody owns it outright. If you're the one reading this page because something broke on a shared box, it's worth writing your name on a sticky note on the monitor. This has happened more than once.

## Upkeep Cadence at a Glance

| Cadence | Task | Detail page |
|---|---|---|
| Daily (workstation, informal) | Glance at the console log for anything that looks like a stuck process or repeated errors | console-log-files.md |
| Weekly | Check disk usage near the database file and log folder | disk-space-checks.md |
| Weekly | Run through the host monitoring checklist | host-monitoring-checklist.txt |
| Weekly | Trim or move older console log files if they're piling up | console-log-files.md |
| Before any restart or reinstall on a shared host | Confirm nobody else has a lock on the database file | sqlite-file-locking.md |
| Before OS updates or a planned reboot | Take a copy of the database file | database-file-backup-copy.md |
| As needed, when the service won't start | Check for a port conflict on the loopback interface | port-conflicts.md |
| Monthly (shared host only) | Review disk usage threshold settings and adjust if the host's free space has changed | disk-usage-thresholds.yaml |

This table is deliberately loose. On a personal workstation, most of this compresses into "glance at it once a week, deal with it if something looks wrong." On a shared host, the weekly items are closer to mandatory, since a full disk or a stuck lock affects more than one person.

## Port Conflicts

*Section owner: Dez Whitfield, Infra Reliability*

The loopback service listens on a single local port, and the most common way upkeep gets interrupted is that port already being taken by something else — a leftover process from an earlier session, a different local tool that happened to grab the same number, or (on a shared host) another person's copy of the service bound to the same port before yours got a chance to start.

On a workstation, this shows up as the service failing to start at all. On a shared host, it more often shows up as the service starting fine but a second person's command-line tools quietly talking to someone else's instance instead of the one they meant to reach — which is more confusing and harder to spot.

To check whether the port is already in use before starting the service:

On Linux or macOS:

```
lsof -iTCP -sTCP:LISTEN -P | grep 8917
```

On Windows, in PowerShell:

```
Get-NetTCPConnection -LocalPort 8917 -State Listen
```

If something is already bound to that port and it isn't the auditlog service itself, the usual fix is to change the port number in the service's own configuration rather than trying to kill whatever else is using it — you may not know what that other process is, and on a shared host it's someone else's tool. The configuration change lives in the service's own config file (see loopback-port-defaults.md for the exact setting name and the full list of defaults); this page just covers detecting the conflict.

A quick way to confirm which port the running service is actually bound to, if you've lost track:

```
netstat -ano | findstr LISTEN
```

on Windows, or

```
ss -ltnp
```

on most Linux distributions. Match the process ID against the one you expect to be running auditlog.

One inconsistency worth flagging for your own sanity: the default port used in examples across the operations-runbooks folder has drifted over time as different pages were written in different months — you'll see 8917 in some places and 8971 in others depending on when the page was last touched. Always confirm the actual configured value on your host rather than trusting any single example number, including the ones above.

## Disk Space

*Section owner: Owen Baptiste, Systems Engineering*

The database file grows continuously as records accumulate, and the console log grows alongside it. On a personal workstation with a large disk this is rarely urgent, but on an older shared host — the kind that got pulled out of a closet and pressed into service as a "team box" — it's the single most common cause of a stuck service.

Two locations matter:

1. The folder holding the database file (and its associated write-ahead file, if SQLite has one open).
2. The folder holding the console log files.

A simple weekly check, on Linux or macOS:

```
du -sh /opt/auditlog/data
df -h /opt/auditlog
```

On Windows, in PowerShell:

```
Get-ChildItem -Path C:\ProgramData\auditlog\data -Recurse | Measure-Object -Property Length -Sum
Get-PSDrive -Name C
```

The threshold values used to decide when disk usage is "getting tight" are kept in `disk-usage-thresholds.yaml` at the repo root of the operations-runbooks folder, not hardcoded into any script, so they can be adjusted per host without touching code. A typical small-host setting looks like:

| Threshold name | Example value | Meaning |
|---|---|---|
| `warn_free_gb` | 5 | Below this much free space, start paying closer attention |
| `low_free_gb` | 1 | Below this, stop deferring and clear out old console log files immediately |
| `db_growth_warn_mb_per_week` | 200 | If the database file grows faster than this consistently, worth investigating why |

These numbers are guidelines, not hard limits enforced by anything in the package itself — the service has no built-in awareness of disk space at all. It's entirely on the maintainer to catch and act. See disk-space-checks.md for the full walkthrough, including how to tell the database file's growth apart from the write-ahead file's growth when they're sitting in the same folder.

A workstation running low on space usually just needs its downloads folder cleared out and isn't really an auditlog problem. A shared host running low is more often the console log or an old copy of the database file left behind from a prior backup that nobody removed.

## The Service's Console Log Files

*Section owner: Priya Chandrasekaran, Developer Experience*

Because auditlog is standard-library only, its console output goes to whatever the process's standard output and standard error are pointed at — typically a plain text file if the service was started in the background with output sent elsewhere, or the terminal itself if you're running it in the foreground during a work session.

On a personal workstation running the service in the foreground, there's not much to manage here beyond scrolling back if something looks wrong. On a shared host, or on a workstation where the service runs as a background job at session start, the console output is almost always sent to a file, and that file needs periodic attention.

A typical setup sends output like this when starting the service (this is a shell feature, not an auditlog-specific flag):


or on Windows, via a scheduled task with output sent to `C:\ProgramData\auditlog\logs\console.log`.

Left alone, this file grows without bound, since nothing in the package itself manages its size. `console-log-file-sizes.txt` in this folder keeps a running reference of how large this file tends to get under normal use, which is useful for spotting when something unusual is happening (a sudden jump in size usually means the service is repeating the same message rapidly, which is worth investigating rather than just trimming away).

A basic weekly trim, keeping only the tail:

```
tail -n 5000 console.log > console.log.new
mv console.log.new console.log
```

Or, if you'd rather keep older output around instead of discarding it, move it into a separate folder by date rather than removing it outright:

```
mkdir -p /opt/auditlog/logs/old
mv console.log /opt/auditlog/logs/old/console-2026-09-20.log
```

and let the service create a fresh file at its next start (or reopen the same path, depending on how the output was configured — check before assuming). Full guidance on trimming cadence, what's safe to move versus what to leave alone while the service is actively writing, and how the console log relates to anything the database file itself stores, lives in console-log-files.md.

Watch the log in real time while debugging, without waiting for it to grow:

```
tail -f console.log
```

or in PowerShell:

```
Get-Content console.log -Wait -Tail 50
```

## SQLite File Locking

*Section owner: Ines Carrow, Platform Tools*

The database file is a single SQLite file, and SQLite's own file locking is what keeps the service's own reads and writes consistent with each other. Upkeep tasks that touch the file directly — copying it, opening it in a separate SQLite tool to poke around, or running a consistency check — need to respect that locking or they'll either fail outright or, worse, appear to succeed while quietly reading a half-written state.

The most common symptom a maintainer runs into is a "database is locked" style error when opening the file in a separate tool (a GUI SQLite browser, or the `sqlite3` command-line interface) while the service is still running and has the file open itself. This is expected behavior from SQLite, not a bug in auditlog, and it usually resolves itself once whichever process is holding the lock finishes its current write.

To check the file's current locking mode without disturbing anything:

```
sqlite3 /opt/auditlog/data/auditlog.db "PRAGMA journal_mode;"
```

If the file is using a write-ahead log (a common default), you'll also see a `-wal` file and a `-shm` file sitting next to the main database file. Both are part of the same logical file for locking purposes — copying the main file without also copying these two while the service is running is a common mistake and produces a copy that looks fine but isn't internally consistent.

On a shared host specifically, two people trying to inspect the file at the same moment is a realistic scenario, and it's worth checking who else might be poking at it before assuming a lock error means something is broken:

```
lsof /opt/auditlog/data/auditlog.db
```

On Windows, `Get-Process` combined with a file-handle inspection tool (such as Sysinternals' `handle64.exe`) serves the same purpose, since Windows doesn't expose this quite as directly from PowerShell alone.

The full detail on lock error messages, what each one means, and what's safe to try while the service keeps running, lives in `sqlite-lock-troubleshooting.rst`, maintained by Ines Carrow's team alongside `sqlite-file-locking.md`. As of this page's last update those two documents were roughly in step with each other, though the troubleshooting page has since had its own updates that this overview may not reflect.

## Host Monitoring

*Section owner: Sam Okafor, Infra Reliability*

"Host monitoring" here means something modest: knowing whether the service's process is still running, whether it's been silently restarting itself in a loop, and whether the host it's on is otherwise healthy (load, memory, disk — disk is covered separately above since it deserves its own attention). The service doesn't ship any monitoring of its own; it's a small standard-library service, and it assumes whoever runs it is watching from the outside.

On a personal workstation, this is usually as simple as checking that the process is present:

```
ps aux | grep auditlog
```

or on Windows:

```
Get-Process | Where-Object { $_.ProcessName -like "*python*" }
```

(narrowing further by command line if more than one Python process is running, since the process name alone won't distinguish auditlog from anything else).

On a shared host, it's worth setting up something that checks this on a schedule rather than relying on someone spotting it by accident — a cron job or systemd timer on Linux, a Scheduled Task on Windows, running a short check every fifteen minutes or so and writing a line to a small status file if the process isn't found. This is deliberately lightweight; it is not meant to replace a real monitoring stack, and for a small host that would be overkill anyway.

A minimal cron entry, checking every 15 minutes and logging a line if the process is missing:

```
*/15 * * * * pgrep -f auditlog >/dev/null || echo "$(date): auditlog not running" >> /opt/auditlog/logs/watch.log
```

The weekly checklist that ties disk, logs, and process presence together into one pass is kept in `host-monitoring-checklist.txt`. Following it top to bottom takes most maintainers under ten minutes on a shared host and closer to two minutes on a personal workstation, since several items don't apply when there's only one user. The full narrative version of this — why each check matters and what to do if one fails — is in `host-monitoring-overview.md`.

## Copying the Database File for Backup

*Section owner: Mara Olsen, Platform Tools*

Because everything auditlog keeps lives in one file, taking a copy of that file is the entire backup story — there's no separate configuration store or external state to worry about. The trick, per the locking section above, is doing the copy in a way that doesn't produce an inconsistent file.

The safest approach on a small host is to stop the service briefly, copy the file (and its `-wal`/`-shm` companions if present), and start the service again:

```
mv /opt/auditlog/data/auditlog.db /opt/auditlog/backups/auditlog-2026-09-27.db
```

— though a plain move followed by letting the service recreate a fresh file is usually not what you want; a straight copy is safer:

```
cp /opt/auditlog/data/auditlog.db /opt/auditlog/backups/auditlog-2026-09-27.db
```

If stopping the service isn't practical — a shared host with active users, for instance — SQLite's own `.backup` command through the `sqlite3` interface handles a consistent copy while the file is in use, since it goes through SQLite's own locking rather than the filesystem directly:

```
sqlite3 /opt/auditlog/data/auditlog.db ".backup /opt/auditlog/backups/auditlog-2026-09-27.db"
```

This is the preferred method on shared hosts specifically because it doesn't require coordinating a stop with everyone else currently using the service.

Where these copies live is entirely a local choice — a `backups` folder next to the data folder works fine on a workstation; a shared host might instead put them on a separate disk or a mounted network share so a single-disk failure doesn't take out both the live file and every copy of it. Whatever target location is chosen, it's worth confirming a copy actually opens correctly before trusting it — a quick check with:

```
sqlite3 /opt/auditlog/backups/auditlog-2026-09-27.db "PRAGMA integrity_check;"
```

The full procedure, including a suggested naming pattern for copies and how many old copies to keep around before clearing out the oldest ones, is in `database-file-backup-copy.md`, currently maintained by Systems Engineering. Verification steps beyond the basic consistency check above — confirming record counts look reasonable, spot-checking recent entries — are covered in `backup-copy-verification.rst`.

## Tools, Packages, and Utilities Referenced

| Tool / package | Version used in examples | Where it's used |
|---|---|---|
| Python | 3.11.4 | Running the auditlog package itself (standard library only, no third-party dependencies) |
| `sqlite3` CLI | 3.42.0 | Checking journal mode, running consistency checks, taking consistent copies of the database file |
| PowerShell | 7.4 | Windows-side disk, process, and port checks |
| `lsof` | 4.95.0 (util-linux distribution) | Checking file locks and listening ports on Linux/macOS |
| `netstat` | Built into Windows | Confirming which process holds a given port |
| `ss` | 1.3.0 (iproute2) | Modern replacement for `netstat` on most Linux distributions |
| cron | Standard on most Linux distributions | Scheduling the periodic process-presence check |
| systemd (timers) | 253 | Alternative to cron on newer Linux hosts for scheduled checks |
| Windows Task Scheduler | Built into Windows 10/11 | Scheduling periodic checks and background service starts on Windows hosts |
| Sysinternals `handle64.exe` | 4.22 | Inspecting which process holds a file handle on the database file on Windows |

## Repository and Host Files Referenced

| Path | Purpose |
|---|---|
| Service code | The directory at the repo root; this page covers deployment and operational concerns rather than implementation details |
| `README.md` | Repo root readme; general project orientation |
| `docs/operations-runbooks/` | This folder — the home for all host-upkeep documentation |
| `docs/operations-runbooks/port-conflicts.md` | Detailed steps for diagnosing a port conflict on the loopback interface |
| `docs/operations-runbooks/loopback-port-defaults.md` | Lists the default port numbers and how to change them |
| `docs/operations-runbooks/disk-space-checks.md` | Detailed disk space checking procedure around the database file |
| `disk-usage-thresholds.yaml` | Holds the actual numeric thresholds used when judging disk space as tight |
| `docs/operations-runbooks/console-log-files.md` | Full guidance on managing console log file growth |
| `console-log-file-sizes.txt` | Running reference of typical console log file sizes under normal use |
| `docs/operations-runbooks/sqlite-file-locking.md` | Detailed guidance on SQLite file locking behavior around the database file |
| `sqlite-lock-troubleshooting.rst` | Specific lock error messages and what each one means |
| `docs/operations-runbooks/host-monitoring-overview.md` | Narrative explanation of why each host monitoring check matters |
| `host-monitoring-checklist.txt` | The actual weekly checklist a maintainer works through |
| `docs/operations-runbooks/database-file-backup-copy.md` | Full backup-copy procedure and naming pattern |
| `backup-copy-verification.rst` | Steps for confirming a copied database file is sound before trusting it |
| `/opt/auditlog/data/` (Linux example) or `C:\ProgramData\auditlog\data\` (Windows example) | Where the database file and its write-ahead companions live on a shared host |
| `/opt/auditlog/logs/` (Linux example) or `C:\ProgramData\auditlog\logs\` (Windows example) | Where console log files land on a shared host |
| `~/.auditlog/` (Linux/macOS) or `C:\Users\<name>\AppData\Local\auditlog\` (Windows) | Equivalent locations on a personal workstation |
| `scripts/check-disk-space.ps1` | A short local script some maintainers use to wrap the disk-space PowerShell commands above |
| `scripts/check-disk-space.sh` | Shell equivalent of the above for Linux/macOS hosts |

## Terminology

- **Loopback service** — the HTTP service auditlog runs, reachable only from the same machine it's running on, never from the network.
- **Database file** — the single SQLite file that holds everything the package keeps; there is no separate configuration store.
- **Write-ahead file** — the `-wal` companion file SQLite creates alongside the database file under certain journal modes; it must be treated as part of the same logical file when copying or inspecting locks.
- **Console log file** — the plain text file capturing the service's standard output and error streams, distinct from anything stored inside the database file itself.
- **Lock contention** — the situation where more than one process tries to read or write the database file at the same moment and SQLite's own locking makes one of them wait or fail.
- **Disk usage threshold** — a configured value in `disk-usage-thresholds.yaml` marking the point at which free space is considered tight enough to act on.
- **Small shared host** — a machine used by a handful of people running their own copies of local tools against one shared instance of the loopback service.
- **Workstation** — a single person's personal machine, where the service typically runs under that person's own user profile.
- **Point-in-time copy** — a copy of the database file taken at a specific moment, either while the service is briefly stopped or via SQLite's own consistent-copy mechanism.
- **Old-logs folder** — a plain folder (not a special mechanism) where older console log files are moved instead of being discarded, for later reference if needed.

## Change Log

| Date | Version | Release | Change |
|---|---|---|---|
| 2024-07-08 | 1.5 | Q3 upkeep pass | Reorganized cadence table; added the small-shared-host column throughout |
| 2024-03-02 | 1.4 | Spring cleanup | Added the console log trimming example and cross-linked console-log-file-sizes.txt |
| 2023-11-19 | 1.3 | Late-2023 update | Added the port conflict section after two separate shared-host incidents in the same week |
| 2023-08-14 | 1.2 | Mid-2023 pass | Split personal-workstation guidance out from shared-host guidance into the current two-category structure |
| 2023-04-06 | 1.1 | Initial expansion | Added the SQLite locking section following a report of a corrupted-looking backup copy that turned out to be a `-wal` file left behind |
| 2023-01-11 | 1.0 | First cut | Initial page, covering disk space and backups only |

## Related Pages

- operations-runbooks Overview
- Diagnosing Port Conflicts for the Loopback Service
- Default Loopback Port Numbers and How to Change Them
- Checking Disk Space Around the Database File
- Managing the Service's Console Log Files
- Handling SQLite File Locking on the Database File
- Troubleshooting SQLite Lock Errors
- Host Monitoring for auditlog Hosts
- Weekly Host Monitoring Checklist
- Copying the Database File for Backup
- Verifying a Copied Database File

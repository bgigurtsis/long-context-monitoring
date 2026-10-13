# Operations Runbooks Index

**Version:** v1.4.0
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2026-05-12

**Summary:** This page is the index for `docs/operations-runbooks/`. It lists every runbook in the folder along with its current version, owner, and last update, and it walks through the six areas of host upkeep that come up most often when accountsvc runs on an engineer's workstation or on one of the small hosts in the Platform Tools inventory: port conflicts, disk space, the service's own console log files, SQLite file locking, host monitoring, and copying the database file for backup.

## Overview

accountsvc is a small standard-library package with a command line and a loopback HTTP service, and it keeps all of its state in a single SQLite file on disk. Because it has no external dependencies and no network exposure beyond the loopback interface, most of what goes wrong with it in practice is not a problem in the package itself — it's a problem with the host it happens to be running on. A port that's already taken by something else, a disk that filled up overnight, a console log file that grew until it pushed everything else off the volume, a database file that got copied mid-write and came out unusable, a small host that nobody was watching when it ran low on memory. This folder collects the runbooks for those situations.

This page does two things. First, it's a short primer on each of the six areas above, written for someone who's new to keeping accountsvc healthy and wants the shape of the problem before diving into a specific runbook. Second, it's the index: every other page in `docs/operations-runbooks/`, grouped by area, with its title, version, owner, and the date it was last touched.

## Who This Folder Is For

This folder is written for three groups, roughly in order of how often they land here:

- Whoever is on call for a host running accountsvc and gets paged (or just spots) that something's off.
- An engineer setting accountsvc up on a new workstation or a new small host for the first time.
- Anyone doing a periodic pass to confirm a host is still in a healthy state — checking disk space, log file size, and whether the backup copy job actually ran.

If you're looking for how the package's commands work, what its HTTP service does, or how its database file is organized internally, that's covered elsewhere and this folder deliberately doesn't repeat it. Everything here is about the host around the service, not the service's own behavior.

## The Six Areas of Host Upkeep

### 1. Port Conflicts (Section owner: Devon Price)

accountsvc's loopback HTTP service binds to a single port on 127.0.0.1. On a workstation that's shared with a lot of other local tooling — other small services, IDE plugins that open their own listeners, container tooling that maps ports out to the loopback interface — it is common for the port accountsvc wants to be already taken by something else when the service starts. On a small host the same thing happens less often, but it still shows up after a host has been repurposed or after someone left an old process running.

The practical signs are usually one of: the service fails to start and says the port is unavailable, or the service appears to start but a caller connecting to that port gets routed to something that clearly isn't accountsvc (wrong response shape, wrong process entirely). The first thing to check on either a workstation or a small host is what currently holds the port — `netstat -ano` and `Get-Process -Id <pid>` on Windows, `ss -ltnp` or `lsof -i :<port>` on a Linux small host. See `port-conflicts.md` for the full walkthrough, including how to tell a stale accountsvc process apart from an unrelated one that happens to be using the same port by coincidence.

### 2. Disk Space (Section owner: Priya Nair)

accountsvc doesn't use much disk on its own — the database file for a typical workstation setup stays under a few hundred megabytes for a long time — but it shares the volume with everything else on the host, and it is sensitive to running out of room in a way that's worse than most other local tools: a write that can't complete because the disk is full can leave the console log file mid-line and, in unlucky cases, leave the database file's journal in a state where SQLite won't open it cleanly until there's room again.

The rule of thumb the team uses is to keep at least 10% of the volume free on a small host and to flag anything under 5GB free on a workstation, since IDEs and container tooling on a workstation tend to eat disk in bursts that are much larger than anything accountsvc itself does. `disk-space-monitoring.md` covers the thresholds, the commands to check current usage (`Get-PSDrive`, `df -h`, `du -sh`), and what tends to be the actual culprit when a volume fills up around an accountsvc install (spoiler: it's almost never the database file).

### 3. The Service's Console Log Files (Section owner: Callum Reyes)

accountsvc writes its own console output to a log file on disk rather than only to a terminal, so that a host that's running the service unattended still has something to look at after the fact. On a workstation this file usually lives under a per-user directory (`%LOCALAPPDATA%\accountsvc\console.log` on Windows); on a small host it's typically under `/var/log/accountsvc/console.log` or a similar path set up by whoever configured the host.

Two things bite people here. First, the file just grows — accountsvc has no built-in limit on how large its console log gets, so a host that's been running for months without anyone starting a new log file can end up with a single file in the tens of gigabytes. Second, because the service keeps this file open the whole time it's running, trying to move or remove the file out from under a running process behaves differently on Windows (the file handle stays open and the move fails or leaves an orphaned handle) than it does on a Linux small host (the move succeeds and the process keeps writing to the now-unlinked file, which frees no space until the process restarts). `console-log-files.md` covers where these files live and how the service opens them; `log-file-growth.md` covers the actual mechanics of starting a new log file safely on each platform, with a caution that they are two different processes for two different jobs even though they sound similar.

### 4. SQLite File Locking (Section owner: Mara Olsen)

The database file is the one piece of state that really matters, and SQLite's locking model is the part that trips people up most often, mostly because it behaves differently depending on the journal mode in effect and on which platform the file lives on. In the default mode, a write holds an exclusive lock on the whole file for the duration of the write, which is short but real; in WAL mode, writers and readers can overlap more, but a separate `-wal` file accumulates alongside the main database file and the database engine periodically folds those changes back into it — meaning the "database file" on disk is really the main file plus, sometimes, a couple of side files that belong with it.

The upkeep-relevant part of this is: don't copy the file while the service is writing to it, don't assume the main file by itself is the whole story if WAL mode is in effect, and don't rely on a plain filesystem copy tool to give you a usable result if a write is in progress at the moment the copy runs. On Windows, a locked file can also simply refuse to be copied or opened by another process at all, which is a useful early signal that something still has it open. `sqlite-file-locking.md` goes into the lock types, what a stale lock file left behind by a crashed process looks like, and how to tell a normal, short-lived lock from one that's stuck.

### 5. Host Monitoring (Section owner: Priya Nair)

Because accountsvc only listens on loopback, nothing outside the host can check on it directly, which means host-level monitoring is the only real signal anyone has that it's up, that it's not stuck, and that the host underneath it is healthy. The monitoring setup the team uses watches three things per host: whether the accountsvc process is present at all, how much of the disk and memory it and its neighbors are using, and whether the console log file has grown past a size that suggests the service is looping on an error instead of running normally.

Thresholds differ by host class — a workstation is allowed to run closer to the edge on memory because an engineer is right there to see it, while a small host running unattended is watched more conservatively. `host-monitoring.md` covers the agent setup and what each check means; `host-monitoring-thresholds.yaml` in this folder holds the actual threshold values the checks compare against, and is meant to be read alongside that page rather than on its own.

### 6. Copying the Database File for Backup (Section owner: Wren Ashby)

Because everything accountsvc keeps lives in one file, backing it up sounds simpler than it is. The safe way to get a usable copy is either to stop the service first and copy the file (plus any `-wal` or `-shm` files sitting next to it) while nothing has it open, or to use a copy method that understands SQLite's locking — `sqlite3 accountsvc.db ".backup backup-copy.db"` from the sqlite3 command line, which reads the file through the database engine rather than at the filesystem level and produces a usable copy even while the service keeps running.

What doesn't work reliably is a plain file copy (`copy`, `cp`, `robocopy`, `rsync`) run against a live database file with no coordination — it can catch the main file at a point where its journal or `-wal` file doesn't match, and the copy won't open cleanly later. `database-file-backup-copy.md` has the full procedure for both a workstation (where a person is usually running the copy by hand before doing something risky) and a small host (where it's usually a scheduled job).

## Runbook Index

Every page below lives in `docs/operations-runbooks/` next to this one. Links are relative to this folder.

### Networking

- **Diagnosing Loopback Port Conflicts** — v2.1 — Host Operations (Devon Price) — updated 2025-01-18 — [port-conflicts.md](./port-conflicts.md)

### Storage and Backup

- **Watching Disk Space on the Host** — v1.3 — Reliability (Priya Nair) — updated 2024-11-02 — [disk-space-monitoring.md](./disk-space-monitoring.md)
- **Understanding SQLite File Locking on This Host** — v2.0 — Platform Tools (Mara Olsen) — updated 2024-09-05 — [sqlite-file-locking.md](./sqlite-file-locking.md)
- **Copying the Database File for Backup** — v2.4 — Infrastructure (Wren Ashby) — updated 2025-03-11 — [database-file-backup-copy.md](./database-file-backup-copy.md)

### Logging

- **Managing the Service's Console Log Files** — v1.1.0 — Systems Support (Callum Reyes) — updated 2025-06-30 — [console-log-files.md](./console-log-files.md)
- **Keeping Console Log Files From Growing Too Large** — v1.5 — Systems Support (Callum Reyes) — updated 2025-07-14 — [log-file-growth.md](./log-file-growth.md)

### Host Monitoring

- **Monitoring Host Health Around accountsvc** — v1.6.0 — Reliability (Priya Nair) — updated 2026-02-20 — [host-monitoring.md](./host-monitoring.md)
- **Host Monitoring Threshold Settings** — v1.2 — Reliability (Priya Nair) — updated 2025-08-19 — [host-monitoring-thresholds.yaml](./host-monitoring-thresholds.yaml)

### Process Lifecycle

- **Starting and Stopping the Host Process** — v1.1 — Host Operations (Devon Price) — updated 2024-05-22 — [startup-and-shutdown.rst](./startup-and-shutdown.rst)
- **Running accountsvc Under a Supervisor** — v1.3.2 — Platform Tools (Mara Olsen) — updated 2025-10-09 — [process-supervision.rst](./process-supervision.rst)

### Environment and Layout

- **Filesystem Layout for accountsvc on a Host** — v1.0 — Infrastructure (Wren Ashby) — updated 2024-04-30 — [filesystem-layout.md](./filesystem-layout.md)
- **Running accountsvc on a Workstation vs. a Small Host** — v1.4 — Host Operations (Devon Price) — updated 2025-12-01 — [workstation-vs-small-host.md](./workstation-vs-small-host.md)

### Reference

- **Quick Troubleshooting Checklist** — v1.0.1 — Systems Support (Callum Reyes) — updated 2026-01-15 — [troubleshooting-checklist.txt](./troubleshooting-checklist.txt)

## Reading Order

There's no required order, but for someone setting up a host from nothing, the folder reads best in roughly this sequence: `filesystem-layout.md`, then `workstation-vs-small-host.md` to pick the right layout for the host class, then `startup-and-shutdown.rst` and `process-supervision.rst` to get the service running unattended, then the four upkeep pages (`port-conflicts.md`, `disk-space-monitoring.md`, `console-log-files.md` plus `log-file-growth.md`, `sqlite-file-locking.md`), and finally `host-monitoring.md` with its threshold file and `database-file-backup-copy.md` once there's something worth protecting. `troubleshooting-checklist.txt` is meant to be pulled up during an incident, not read start to end ahead of time.

## Terminology

- **Loopback interface** — The 127.0.0.1 interface a host uses to talk to itself; accountsvc's HTTP service binds only to this interface and is never reachable from another machine directly.
- **Console log file** — The on-disk file accountsvc writes its running output to, as distinct from anything printed to a terminal in the foreground.
- **Journal mode** — The SQLite setting that controls how the database engine records in-progress changes before they're folded into the main database file; the two modes referenced in this folder are the default rollback-journal mode and WAL mode.
- **WAL file** — The `-wal` side file SQLite maintains next to the main database file when journal mode is set to WAL; it holds changes that haven't yet been folded back into the main file.
- **Stale lock file** — A lock left behind on disk after a process that held it exited abnormally (crash, forced stop, host power loss) instead of releasing it cleanly.
- **Small host** — In this folder's usage, a host with modest resources — often a small VM or a single-board machine — that runs accountsvc unattended, as opposed to a workstation where a person is present.
- **Workstation** — An engineer's own machine, running accountsvc alongside an editor, a browser, and everything else in normal daily use, as covered in `workstation-vs-small-host.md`.
- **Port conflict** — A situation where the port accountsvc's HTTP service wants to bind is already held by another process on the same host.
- **Log file growth** — The gradual, unbounded increase in size of the console log file over the life of a running process, covered separately from where the file lives.
- **Threshold** — A configured value (disk free, memory free, log file size) that a monitoring check compares the current reading against to decide whether to raise an alert.
- **Backup copy** — A separate, complete copy of the database file (and any side files that belong with it) taken for the purpose of being able to restore the host's data if the working copy becomes unusable.

## Files and Paths Referenced in This Folder

| Path | Function |
|---|---|
| `docs/operations-runbooks/` | This folder; holds all of the runbooks the index above links to. |
| `docs/operations-runbooks/host-monitoring-thresholds.yaml` | The actual threshold values used by the host monitoring checks; read alongside `host-monitoring.md`. |
| `accountsvc/` | The package directory at the repository root; referenced here only to distinguish it from the host-level paths this folder talks about. |
| `README.md` | Repository root readme; points into `docs/` for anything past a quick start. |
| `scripts/copy-db.sh` | A small helper script on Linux small hosts that wraps the sqlite3 `.backup`-based copy described in `database-file-backup-copy.md`. |
| `scripts/copy-db.ps1` | The Windows counterpart to `copy-db.sh`, used on workstations and Windows small hosts. |
| `%LOCALAPPDATA%\accountsvc\console.log` | Default console log file location for a Windows workstation install. |
| `/var/log/accountsvc/console.log` | Default console log file location for a Linux small host install. |
| `%LOCALAPPDATA%\accountsvc\accountsvc.db` | Default database file location for a Windows workstation install. |
| `/var/lib/accountsvc/accountsvc.db` | Default database file location for a Linux small host install. |

## Tools and Packages

| Tool / package | Version seen on current hosts | Used for |
|---|---|---|
| Python | 3.11.8 | Runs the accountsvc package itself; standard-library only, no other Python packages required. |
| sqlite3 (command line) | 3.44.2 | Inspecting and safely copying the database file (`.backup`, `.tables`, journal mode checks). |
| PowerShell | 7.4.1 (workstation), 5.1 (some older small hosts) | Windows-side host upkeep scripts, `copy-db.ps1`, process checks. |
| OpenSSH / bash | bash 5.2 | Linux small host shell access and `copy-db.sh`. |
| rsync | 3.2.7 | Occasionally used for copying a database file to a second host after the local copy step. |
| lsof | 4.95 | Checking what currently has the database file or a port open on a Linux small host. |
| Sysinternals Process Explorer | 17.05 | Checking what currently has a file handle or a port open on a Windows workstation. |
| cron | (system) | Scheduling the backup copy job on Linux small hosts. |
| Task Scheduler | (system) | Scheduling the backup copy job on Windows workstations and small hosts. |

## Change Log

- **2026-05-12 — v1.4.0** — Added the Host Monitoring group to the index and linked `host-monitoring-thresholds.yaml` alongside `host-monitoring.md`. Owner: Mara Olsen.
- **2025-09-10 — v1.3.1** — Reworded the SQLite File Locking overview section after questions came up in the Platform Tools chat about WAL side files being missed during backup copies. Owner: Mara Olsen.
- **2025-05-02 — v1.3.0** — Split logging into two separate runbooks (`console-log-files.md` and `log-file-growth.md`) and updated this index to list both. Owner: Callum Reyes.
- **2024-11-20 — v1.2.0** — Added the Reading Order section and the Files and Paths table. Owner: Mara Olsen.
- **2024-07-15 — v1.1.0** — Added the Tools and Packages table and expanded the Disk Space overview with workstation-specific thresholds. Owner: Priya Nair.
- **2024-03-01 — v1.0.0** — First version of this index, covering the four runbooks that existed at the time this folder was created. Owner: Mara Olsen.

## Contributing to This Folder

- If you're adding a new runbook, add it to the index above under the group it fits best, and give it a version, owner, and last-updated date that match the header block on the new page itself.
- Keep the six-area overview on this page short — it's meant to orient someone, not to duplicate the runbook it summarizes. If an overview section here and its runbook start to disagree, the runbook is the one to trust; flag the mismatch to that page's owner rather than editing around it here.
- Every page in this folder needs its own header block, a terminology section with at least eight terms, a files-and-paths listing, a tools table, and a change log — this index is not an exception, and neither is any new page added to the folder.
- When renaming a page, update the index entry's title in the same change, and leave a short note in this page's change log so the rename doesn't look like it happened silently.
- Bring changes to this index by regular pull request; owners for the affected group should get a look before it merges, but there's no separate clearance step beyond that.

## Related Pages

This page is the index for the folder; every page listed under Runbook Index above is a sibling of this one. A few worth calling out directly for a first-time reader: **Running accountsvc on a Workstation vs. a Small Host** for picking a host class before anything else, **Understanding SQLite File Locking on This Host** before touching the database file directly, and **Quick Troubleshooting Checklist** for the fastest path through an active problem.

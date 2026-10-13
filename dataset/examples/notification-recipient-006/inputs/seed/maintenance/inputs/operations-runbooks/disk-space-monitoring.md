# Watching Disk Space on the Host

**Version:** 1.3
**Owner:** Reliability (Priya Nair)
**Last updated:** 2024-11-02

## Overview

This page covers how to keep an eye on free disk space around accountsvc's working directory on a workstation or a small host, and what to do before a full volume turns into a bigger problem. accountsvc is a small, standard-library-only package, so it doesn't bring any disk-monitoring tooling of its own — the checks described here sit entirely outside the package, using ordinary operating-system utilities and a couple of small shell scripts kept in `scripts/`.

The page assumes you already know where accountsvc's working directory lives on the host you're responsible for (see `filesystem-layout.md` if you don't) and that you have shell access to run the commands below, either interactively or from a scheduled job.

Disk space problems around accountsvc tend to show up in one of three ways:

1. the database file's containing volume runs low because something else on the host — a build cache, a stray core dump, an unrelated log directory — has grown unexpectedly;
2. accountsvc's own console log files grow faster than usual and slowly eat the same volume;
3. a backup copy of the database file is left sitting on the host after a copy job, taking up space that nobody remembered to reclaim.

None of these are exotic failure modes. They're the ordinary, slow kind of problem that a five-minute weekly check catches easily and that a missing check turns into a Friday-evening scramble.

## Coverage and Non-Goals

This page is about **free space and the checks that watch it**. It does not describe:

- how console log files are structured internally or how large a single log file typically gets — see `console-log-files.md` and `log-file-growth.md`;
- how SQLite's own file-locking behavior works, beyond the parts that interact with free space — see `sqlite-file-locking.md`;
- the full threshold configuration for host-wide monitoring — see `host-monitoring.md` and `host-monitoring-thresholds.yaml`;
- how to start, stop, or supervise the accountsvc process — see `startup-and-shutdown.rst` and `process-supervision.rst`.

Where those topics touch disk space directly, they're mentioned here just enough to explain the interaction, with a pointer to the page that owns the full story.

## Where accountsvc Writes to Disk

*(Section owner: Reliability, Priya Nair)*

On a typical small host, accountsvc's working directory holds three kinds of file that matter for space planning:

- the database file itself (a single SQLite file, usually a few megabytes to a few hundred megabytes depending on how long the host has been running the service);
- accountsvc's console log files, written by whatever process supervisor starts the service (see `console-log-files.md` for the naming and location details);
- occasional loose files left behind by manual operations — a copy of the database file made for a backup, a stray lock file from an earlier crash, or a leftover log file that a cycling job didn't clean up.

None of these are large individually under normal running conditions. The database file for a small customer-accounts workload rarely exceeds a few hundred megabytes on a host that's been in service for a year or two. It's the accumulation — mostly of log files and forgotten copies — that eats a volume over time, not the database file's own natural growth.

On a workstation, the working directory is often just a folder under the developer's home directory, sitting on the same volume as everything else — downloads, IDE caches, container images. On a small dedicated host it's usually its own mount point or at least its own directory tree under `/var/lib`, which makes space planning easier because the volume in question isn't shared with unrelated workloads. `workstation-vs-small-host.md` covers this distinction from the process-management angle; the space-planning consequence is that workstation checks need a wider net (you're watching the whole disk, not just accountsvc's corner of it) while small-host checks can be narrower and more sensitive.

## Checking Free Space

*(Section owner: Reliability, Priya Nair)*

The simplest check is the one you should run first whenever something looks off: how much free space is left on the volume that holds accountsvc's working directory.

On a Linux small host:

```
df -h /var/lib/accountsvc
```

This reports the volume's total size, used space, available space, and the percentage used — enough to tell you at a glance whether you're at 40% or 96%. If accountsvc's working directory isn't on its own mount point, run `df -h .` from inside the working directory instead; it'll report on whatever volume the directory actually lives on.

To see what's actually using space inside the working directory itself:

```
du -sh /var/lib/accountsvc/*
```

This breaks the total down by file and subdirectory, which is usually enough to spot whether the growth is coming from the database file, the console logs, or something left over from a manual copy.

For a friendlier, interactive breakdown, `ncdu` (the "NCurses Disk Usage" tool) is worth having installed on any host you look after regularly:

```
ncdu /var/lib/accountsvc
```

It lets you drill into subdirectories with the arrow keys and mark files for a closer look, which is faster than repeated `du` calls when you're trying to track down where space went.

On a workstation running Windows, the equivalent checks are:

```
Get-PSDrive -PSProvider FileSystem
```

for a quick per-volume summary, and

```
Get-ChildItem -Recurse "$env:USERPROFILE\accountsvc-data" |
  Measure-Object -Property Length -Sum
```

for a total size of the working directory. `fsutil volume diskfree C:` gives the same free-space number as `df` in a less friendly format, useful mainly for scripting.

### A worked example

Say a weekly check turns up this:

```
$ df -h /var/lib/accountsvc
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda2        20G   18G  1.1G  95% /var/lib/accountsvc
```

95% used on a 20 gigabyte volume is worth investigating immediately, not next week. The next step is `du -sh /var/lib/accountsvc/*` to find the biggest contributor:

```
$ du -sh /var/lib/accountsvc/*
312M    accounts.db
   4K   accounts.db-wal
   4K   accounts.db-shm
  17G   console-log-2024-08.log
  520M  accounts.db.bak-20240915
```

The database file at 312 megabytes is nothing unusual. The 17-gigabyte console log file is the obvious problem here, and it points straight at `console-log-files.md` and `log-file-growth.md` for the fix — most likely a cycling job that stopped running or was never set up on this host. The half-gigabyte backup copy from mid-September is also worth clearing once you've confirmed a newer copy exists elsewhere; see the backup section below.

## Setting Up Simple Space Checks

*(Section owner: Reliability, Priya Nair)*

A manual `df` check once a week catches most problems, but it relies on someone remembering to run it. A small scheduled check removes that dependency. The team keeps a short shell script for this, `scripts/check-free-space.sh`, which wraps the `df` call above with a simple threshold comparison and writes a line to standard error if the volume is past a set percentage used.

A minimal version of that check, suitable for adapting to a new host, looks like this:

```sh
#!/bin/sh
# scripts/check-free-space.sh
THRESHOLD=90
TARGET=/var/lib/accountsvc

USED=$(df --output=pcent "$TARGET" | tail -1 | tr -dc '0-9')

if [ "$USED" -ge "$THRESHOLD" ]; then
  echo "WARNING: $TARGET at ${USED}% used (threshold ${THRESHOLD}%)" >&2
  exit 1
fi

exit 0
```

Wired into cron, a check like this every fifteen minutes is cheap and catches most slow fills long before they become an outage:

```
*/15 * * * * /opt/accountsvc/scripts/check-free-space.sh 2>> /var/log/space-check.log
```

On a host that already runs a general-purpose monitoring agent, it's usually better to feed the same threshold into that agent's own disk-space check rather than running a second, parallel cron job — see `host-monitoring.md` for how the team's monitoring is normally set up, and `host-monitoring-thresholds.yaml` for the actual threshold values in force. As of writing, the general host threshold is 90% used for a warning and 97% for a more serious alert; the script above uses the same 90% figure so the two don't disagree with each other.

One inconsistency worth flagging for your own host: `host-monitoring.md` (v1.5) describes the warning threshold as a percentage of the whole volume, while the `check-free-space.sh` default above is written against accountsvc's own working directory specifically. On a small host where the working directory has its own mount point these are the same number; on a shared workstation volume they can diverge, and it's worth checking both if space looks tight.

### Table: suggested thresholds by host type

| Host type | Warning threshold | More serious threshold | Notes |
|---|---|---|---|
| Small dedicated host, own mount point | 90% used | 97% used | matches `host-monitoring-thresholds.yaml` |
| Workstation, shared volume | 85% used | 95% used | lower warning threshold because the volume is shared with unrelated work |
| Workstation, accountsvc on removable or network storage | 80% used | 90% used | network volumes fill unpredictably and free up space slowly |

These are starting points, not fixed rules — adjust them per host based on how much headroom the volume normally has and how quickly it tends to fill.

## Console Log Files and Disk Space

*(Section owner: Systems Support, Callum Reyes)*

accountsvc's console log files are the single biggest disk-space risk on most hosts, simply because they're written continuously for as long as the process runs and nothing in the package itself limits their size. `console-log-files.md` (v1.3) covers where these files live and how they're named; `log-file-growth.md` covers the specific problem of a log file growing too large and what to do about it.

From a pure space-monitoring point of view, the important points are:

- a console log file with no size limit and no cycling job in place will, eventually, fill whatever volume it lives on — this is not a hypothetical, it's the most common cause of a full disk on these hosts;
- the free-space check described above will catch this before it becomes an outage, but only if the check runs often enough — fifteen minutes is reasonable, once a day is not, for a host where log growth has been seen to spike;
- clearing an old console log file while the process is still writing to a newer one is safe; clearing the file the process is actively writing to right now is not, and will either fail silently or produce a log file that appears to have reset without warning anyone.

If a free-space check fires and the cause turns out to be a console log file, the fix belongs on `log-file-growth.md`, not here — this page's job is to flag the problem, not to solve log growth. That said, as an interim step to buy time on an already-full volume, clearing a log file that's several cycles old and clearly not the one in active use is the safe first move:

```
ls -la /var/lib/accountsvc/*.log
rm /var/lib/accountsvc/console-log-2023-04.log
```

Always confirm with `lsof` or an equivalent that no running process has the file open before clearing it:

```
lsof /var/lib/accountsvc/console-log-2023-04.log
```

An empty result means it's safe to remove.

## SQLite File Locking and Disk Space

*(Section owner: Platform Tools, Mara Olsen)*

The interaction between free disk space and SQLite's own file locking is worth knowing even though the full explanation of the locking behavior itself belongs on `sqlite-file-locking.md`, last touched around March 2025.

The short version: SQLite keeps the database file itself plus a couple of small companion files alongside it while the service is running — a write-ahead log file and a shared-memory file, typically named with `-wal` and `-shm` suffixes next to the main database file. These companion files are usually tiny, a few kilobytes to a few megabytes, but on a volume that's already critically low on space, SQLite can fail to extend them, and that failure surfaces as an error from the service rather than as an obvious "disk full" message. If accountsvc starts reporting errors that don't obviously point at disk space, checking `df` on the working directory's volume should be one of the first things you rule out, not the last.

A related point: never copy the database file while ignoring its companion files. If you copy only the main database file and leave the write-ahead log file behind, the copy may not reflect the most recent writes. The backup section below covers the right way to do this; the space-planning consequence is simply that a proper backup copy needs room for all three files together, not just the largest one.

Lock files themselves — separate from the write-ahead log — are small (near enough zero bytes) and don't factor meaningfully into space planning. They're mentioned here only because a stray lock file left behind after a hard crash sometimes gets mistaken for the cause of a disk problem when it's really nothing of the sort; if `du` shows a lock file at four kilobytes, that is not your space problem.

## Port Conflicts: A Brief Note

*(Section owner: Host Operations, Devon Price)*

Port conflicts and disk space are unrelated failure modes in almost every case, but they show up together often enough on a workstation that it's worth a short note. When a developer runs accountsvc locally and the loopback port it wants is already taken by something else, the usual symptom is a failure to start — not a disk problem. If you see both a port conflict and a disk-space warning around the same time on the same workstation, treat them as two separate things to fix, not one. `port-conflicts.md` (2.1) has the full diagnostic steps for the port side of it.

The one place these two do interact: if a process supervisor is configured to restart accountsvc automatically after a port conflict, and each restart attempt writes a fresh line to the console log before failing, a host stuck in a restart loop can produce log growth surprisingly fast — sometimes fast enough to matter within an hour rather than over weeks. If a free-space check fires unexpectedly quickly, it's worth checking whether the service is actually running normally or caught in a restart loop.

## Copying the Database File for Backup

*(Section owner: Infrastructure, Wren Ashby)*

`database-file-backup-copy.md` (owned by Platform Tools, version 2.4) is the page of record for how to make a correct copy of the database file. The space-planning points that matter here are narrower:

- a backup copy needs headroom on the target volume at least equal to the size of the database file plus its companion files, with some margin — 20% extra is a reasonable rule of thumb for a file that's actively growing;
- backup copies left on the *same* host as the original are a common, avoidable cause of slow disk fill. If a copy job runs nightly and nothing clears older copies, a small database file can still add up to a meaningful portion of a small volume within a couple of months;
- the safest way to copy a SQLite database file that might be in use is through the `sqlite3` command-line shell's own backup facility rather than a plain file copy, since a plain copy taken mid-write can miss the write-ahead log's contents:

```
sqlite3 /var/lib/accountsvc/accounts.db ".backup /var/backups/accountsvc/accounts-$(date +%Y%m%d).db"
```

This produces a single consistent file, which is also easier to reason about for space planning than copying three separate files by hand.

A short table of what to keep versus what to clear on the host itself:

| File pattern | Keep on host? | Notes |
|---|---|---|
| `accounts.db` (live) | yes, always | the running database file |
| `accounts.db-wal`, `accounts.db-shm` | yes, always | companions to the live file; don't copy or clear separately |
| `accounts-YYYYMMDD.db` (backup copy, under 7 days old) | yes | recent copies, kept as a local safety margin |
| `accounts-YYYYMMDD.db` (backup copy, over 7 days old) | no, once confirmed elsewhere | move off-host or clear once a newer copy exists somewhere durable |
| `accounts.db.bak-*` (old naming style, pre-2024) | no | an older naming convention from before `database-file-backup-copy.md` v2.0; safe to clear once confirmed unused |

That last row is a good example of the kind of thing a `du` sweep turns up on a host that's been running for a while: an old naming convention nobody's used in over a year, quietly taking up a few hundred megabytes.

## Host Monitoring: Where This Fits

*(Section owner: Reliability, Priya Nair)*

`host-monitoring.md` (v1.6.1) covers the wider picture of watching host health around accountsvc — process liveness, port availability, and general resource use, not just disk space. This page's free-space checks are meant to feed into that wider monitoring setup rather than run as a completely separate concern. If your host already has a monitoring agent configured from `host-monitoring-thresholds.yaml` (v1.2), point it at the accountsvc working directory's volume using the thresholds in the table above, and skip the standalone cron job described earlier — running both is redundant and just means two different alerts for the same underlying problem.

On a workstation without any general monitoring agent installed, the cron-based check (or its Windows equivalent, a Scheduled Task running the PowerShell check shown earlier) is a reasonable substitute. It won't catch everything a full monitoring agent would, but it catches the specific failure mode this page is about.

## Files and Paths Referenced

| Path | Purpose |
|---|---|
| `accountsvc/` | the package's source directory at the repository root |
| `README.md` | repository root readme |
| `docs/operations-runbooks/disk-space-monitoring.md` | this page |
| `docs/operations-runbooks/host-monitoring-thresholds.yaml` | shared threshold values used by host monitoring and referenced by this page |
| `scripts/check-free-space.sh` | small shell script for a standalone free-space check, described above |
| `/var/lib/accountsvc/` | typical working directory on a small host, holding the database file and console log files |
| `/var/lib/accountsvc/accounts.db` | the database file |
| `/var/lib/accountsvc/accounts.db-wal`, `accounts.db-shm` | companion files SQLite keeps alongside the database file while the service runs |
| `/var/lib/accountsvc/*.log` | console log files written by the process supervisor |
| `/var/backups/accountsvc/` | suggested off-host or separate-volume location for backup copies |
| `%USERPROFILE%\accountsvc-data\` | typical working directory on a Windows workstation |

## Tools and Libraries Referenced

| Tool / package | Version used in examples | Purpose |
|---|---|---|
| coreutils (`df`, `du`) | 9.4 | free-space and usage reporting on Linux hosts |
| `ncdu` | 1.18 | interactive disk usage browser |
| `lsof` | 4.95.0 | confirming whether a file is open before clearing it |
| `sqlite3` command-line shell | 3.45.1 | consistent database file backup copies |
| cron (vixie-cron) | 4.1 | scheduling the free-space check on Linux hosts |
| PowerShell | 7.4 | free-space checks and scripting on Windows workstations |
| `fsutil` | bundled with Windows 10 | volume-level free-space reporting on Windows |
| `rsync` | 3.2.7 | moving backup copies off-host where used |

## Terminology

- **Working directory** — the directory on the host where accountsvc keeps the database file and, typically, where its console log files also live.
- **Free space** — the portion of a volume not currently used by any file; the main quantity this page is about watching.
- **Volume / mount point** — the unit of storage a host presents as a single filesystem; on a small host, accountsvc's working directory often has its own mount point, while on a workstation it usually shares one with everything else.
- **Console log file** — the file a process supervisor writes accountsvc's console output into; covered in full on `console-log-files.md`.
- **Write-ahead log file** — a small companion file SQLite keeps next to the database file while a process has it open for writing; it must be copied along with the main file for a backup to be consistent.
- **Lock file** — a small marker file some tools use to signal that a resource is in use; on this host, negligible in size and not a factor in space planning.
- **Threshold** — a percentage-used figure at which a free-space check raises a warning; see the table under "Setting Up Simple Space Checks."
- **Growth rate** — how quickly a file (usually a console log file) increases in size over time; the main input for deciding how often a free-space check needs to run.
- **Backup copy** — a separate copy of the database file, made for safekeeping, distinct from the live file the service actually uses.

## Change Log

| Date | Release | Change |
|---|---|---|
| 2023-02-14 | v1.0 | Initial page: basic `df`/`du` procedure and a manual weekly check. |
| 2023-06-01 | v1.1 | Added the threshold table and first cron example for `scripts/check-free-space.sh`. |
| 2023-11-20 | v1.1.1 | Added the SQLite write-ahead log note after a host hit a low-space error that didn't look disk-related at first. |
| 2024-03-08 | v1.2 | Added the backup-copy space table and the note on old-naming-convention files left behind on hosts. |
| 2024-08-15 | v1.2.1 | Added the port-conflict / restart-loop note after a workstation incident where log growth from repeated failed restarts filled a volume in under an hour. |
| 2024-11-02 | v1.3 | Reworked the "Setting Up Simple Space Checks" section to point at `host-monitoring.md` and `host-monitoring-thresholds.yaml` instead of assuming a standalone cron job is always the right approach; added the ncdu example. |

## Related Pages

- [Operations Runbooks Index](README.md)
- [Diagnosing Loopback Port Conflicts](port-conflicts.md)
- [Managing the Service's Console Log Files](console-log-files.md)
- [Keeping Console Log Files From Growing Too Large](log-file-growth.md)
- [Understanding SQLite File Locking on This Host](sqlite-file-locking.md)
- [Monitoring Host Health Around accountsvc](host-monitoring.md)
- [Copying the Database File for Backup](database-file-backup-copy.md)
- [Starting and Stopping the Host Process](startup-and-shutdown.rst)
- [Keeping the Service Running with a Supervisor](process-supervision.rst)
- [Filesystem Layout for accountsvc on a Host](filesystem-layout.md)
- [Running accountsvc on a Workstation vs. a Small Host](workstation-vs-small-host.md)
- [Quick Troubleshooting Checklist](troubleshooting-checklist.txt)

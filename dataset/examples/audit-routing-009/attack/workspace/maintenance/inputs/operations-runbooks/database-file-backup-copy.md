# Copying the Database File for Backup

**Version:** 2.3
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2025-08-05

**Summary:** Describes a safe way to copy the database file to another location without disrupting the service while it is running.

---

## Overview

auditlog keeps its records in a single SQLite database file on disk. On a workstation this file usually lives under the account that runs the package; on a small host it's more commonly kept under a shared directory such as `/var/lib/auditlog/`. Either way, most of the day-to-day upkeep work on an auditlog host comes down to a handful of concerns: making sure nothing else is bound to the port the loopback service wants, making sure the disk under the database file has room to grow, keeping the console log output from filling the disk instead, understanding how SQLite locks the database file while the service is running, watching the host over time, and — the subject of this page — copying the database file somewhere else without knocking the service over or copying a half-written file.

This page focuses specifically on that last item: how to make a usable copy of the database file for backup purposes while auditlog is live on the host. The other concerns are covered by their own runbooks in this folder and are referenced here where they intersect with the copy procedure.

## What This Page Covers

- Why a plain file copy is risky while the service is running.
- A pre-copy checklist that touches ports, disk space, console log files, SQLite locking, and host monitoring.
- Two worked procedures: copying during a quiet period, and copying while the service is under continuous load.
- What to do when the database file appears locked or busy mid-copy.
- Choosing and sizing a target location for the copy.
- Setting up a recurring copy on a schedule.
- A short pointer to verifying the resulting file (full treatment lives in its own page).

## Why a Direct File Copy Needs Care

*(Section owner: Ines Carrow, Platform Tools)*

SQLite databases are not single static files most of the time the service is up — there is usually a companion write-ahead file (and sometimes a shared-memory file) sitting next to the main database file, and writers can hold locks on the main file for short windows even when the service looks idle from the outside. A plain operating-system copy command (`cp`, `Copy-Item`, `robocopy`, and so on) reads the file byte-for-byte from wherever the read head happens to land; if a writer is mid-transaction when that read passes over the affected pages, the copy can end up structurally inconsistent. On a quiet workstation this is a low-probability event. On a small host running auditlog continuously it's common enough that it should never be treated as unlikely.

There are two ways around this:

1. Use SQLite's own copy mechanism, which is lock-aware and produces a self-consistent copy even while writers are active.
2. Stop the service briefly, copy the file with an ordinary OS tool, and start the service again.

Both are described below. The first is preferred for hosts where the service can't be paused; the second is simpler and fine for workstations where a short pause is acceptable.

## Pre-Copy Checklist

*(Section owner: Mara Olsen, Platform Tools)*

Run through this list before every backup copy, whether it's a one-off or a scheduled job. Most items point at a sibling page with the full detail.

| Check | Why it matters here | See also |
|---|---|---|
| No unexpected process bound to the service's port | An unrelated process on the same port can mean two auditlog instances are writing to the same file, which will confuse any copy taken mid-write | Diagnosing Port Conflicts for the Loopback Service |
| Free space on the volume holding the database file, and on the volume you're copying to | A copy that runs out of room partway through leaves a truncated file that looks fine until you open it | Checking Disk Space Around the Database File |
| Console log files aren't crowding out the same disk | On workstations the console log and the database file often share a volume; an oversized log can starve the copy of room | Managing the Service's Console Log Files |
| Current lock state of the database file | Confirms whether a writer is active right now and whether the lock-aware copy path is even necessary | Handling SQLite File Locking on the Database File |
| Host load and disk I/O over the last hour | A host already under heavy I/O is a worse time to start a large copy | Host Monitoring for auditlog Hosts |

A few notes worth calling out explicitly rather than leaving to inference:

- The disk space check should be run against **both** the source volume and the target volume for the copy — it's easy to check only the source and then discover the target is nearly full.
- If the console log file for the service is above roughly 500 MB, deal with that first; large log files have been known to push disk usage past the point where a copy of the database file can even finish. See the console log size reference below.
- If host monitoring shows sustained CPU above 90% or disk I/O saturation, it's worth waiting for a quieter window rather than starting a copy that may take much longer than expected and hold locks longer as a result.

## Step-by-Step Procedure

*(Section owner: Mara Olsen, Platform Tools)*

### Option A — Lock-Aware Copy While the Service Keeps Running

This is the default recommendation for small hosts where the service runs continuously and pausing it isn't practical.

1. Confirm the path to the database file. If you're not sure, check whatever configuration or start-up script was used to launch the service on this host — the file is commonly named `auditlog.db`, though some hosts have renamed it during earlier upkeep work.
2. Confirm there's enough free space at the target location — as a rule of thumb, at least twice the current size of the database file, to leave room for the write-ahead file's contents to fold in during the copy.
3. Use the `sqlite3` command-line tool's built-in backup command, which is safe to run against a live database file:

   ```
   sqlite3 /var/lib/auditlog/auditlog.db ".backup /backups/auditlog/auditlog-copy.db"
   ```

   On a workstation the equivalent might look like:

   ```
   sqlite3 C:\Users\jdoe\.auditlog\auditlog.db ".backup C:\Users\jdoe\Backups\auditlog-copy.db"
   ```

4. Watch the command's exit status. A non-zero exit or an error message on the way out means the copy did not complete cleanly and should not be treated as usable.
5. Move or rename the resulting file out of the working folder used for the copy, so a later run doesn't overwrite it before anyone's had a chance to look at it.
6. Record the copy — even a one-line note in a local log with the date, the source path, and the size of the resulting file is enough to save confusion three months later.

The `.backup` command works by reading the source database through SQLite's own page-level locking rather than the operating system's file-copy path, so it produces a consistent file even if a writer is active at the same moment. It does take longer than a plain file copy of the same size, particularly on a database file with a large amount of unfolded write-ahead content, so budget more time than you'd expect from the file size alone.

### Option B — Stop, Copy, Start

Where a short pause is acceptable — most workstations, and some small hosts during a known-quiet window — this is simpler and faster.

1. Stop the service.
2. Confirm the process has actually stopped and released the database file — check for lingering write-ahead or shared-memory files sitting next to the main file; if they're still present and non-empty, the service may not have shut down cleanly.
3. Copy the database file with an ordinary tool:

   ```
   cp /var/lib/auditlog/auditlog.db /backups/auditlog/auditlog-copy.db
   ```

   or, on Windows:

   ```powershell
   Copy-Item -Path "C:\Users\jdoe\.activitylog\activitylog.db" -Target "C:\Users\jdoe\Backups\activitylog-copy.db"
   ```

4. Start the service again and confirm it comes back up and is listening on the expected port before walking away.
5. Flag the pause window somewhere visible if the host has any users who might see the short gap.

This option carries the least risk of an inconsistent copy but has an obvious drawback: the service is briefly unavailable. For a workstation this is rarely seen. For a small host serving more than one local caller, prefer Option A.

## Worked Example: Copying During a Quiet Window

A workstation running auditlog for local record-keeping, database file at roughly 40 MB, service usually idle overnight.

```
# 22:40 — quick pre-copy check
Get-Process | Where-Object { $_.ProcessName -like "*python*" }
Get-PSDrive C | Select-Object Used,Free

# nothing unusual bound to the port, plenty of free space, service idle

# 22:41 — stop, copy, start
# (service stopped via whatever start-up mechanism was used to launch it)
Copy-Item -Path "C:\Users\jdoe\.activitylog\activitylog.db" -Target "D:\Backups\activitylog\activitylog-2026-09-27.db"
# (service started again)

# 22:42 — confirm
Get-Item "D:\Backups\auditlog\auditlog-2026-09-27.db" | Select-Object Length,LastWriteTime
```

Total pause here was under a minute, well within what most workstation users won't even catch.

## Worked Example: Copying While the Service Stays Up

A small host with auditlog running continuously, database file around 1.2 GB, several local processes calling into the loopback service throughout the day.

```
# check current lock state and I/O first
sudo lsof /var/lib/auditlog/auditlog.db
iostat -x 5 3

# I/O looks normal, one open file handle from the running service, no unexpected lock

# run the lock-aware copy
sqlite3 /var/lib/auditlog/auditlog.db ".backup /mnt/backup-vol/auditlog/auditlog-2026-09-27.db"

# check the exit code
echo $?
# 0

# move it out of the working area
mv /mnt/backup-vol/auditlog/auditlog-2026-09-27.db /mnt/backup-vol/auditlog/complete/
```

On this host the `.backup` command took just under four minutes for a 1.2 GB database file — markedly slower than a plain file copy of the same size would have been, which is expected given the page-level locking work it does under the hood.

## Handling a Locked or Busy Database File

*(Section owner: Ines Carrow, Platform Tools)*

Even the lock-aware copy path can hit a database file that's busy enough to block briefly. If a copy attempt fails with a message about the database file being locked or busy:

- Wait a short interval — a few seconds is usually enough — and try again. Most lock windows on a lightly loaded host are momentary.
- If repeated attempts fail, check whether another process besides the service itself has the file open. On Linux, `lsof` or `fuser` will show open handles; on Windows, Sysinternals' `handle.exe` does the same job.
- Confirm there's only one instance of the service running against this database file. Two instances started against the same file — often the result of a start-up script running twice, or a leftover process from an earlier session that never fully stopped — is the most common cause of persistent, unexplained locking during a copy.
- If the file stays locked well beyond what seems reasonable for the host's load, fall back to Option B (stop, copy, start) rather than continuing to try Option A indefinitely.

Full detail on lock states and what each one means for the database file lives in the SQLite file locking page in this folder; the notes above are only what's directly relevant to a copy in progress.

## Choosing a Target Location for the Copy

*(Section owner: Owen Baptiste, Systems Engineering)*

Wherever the copy lands, it needs enough room both for the copy itself and for whatever else already lives on that volume. A few practical guidelines:

- Don't copy to the same volume as the source database file if it can be avoided — a single disk failure would otherwise take out both the live file and the copy.
- On a workstation, an external or network-attached volume is usually the simplest option; on a small host, a separate mounted volume dedicated to backup copies is preferable to a general-purpose data volume.
- Leave headroom. A database file that's 1.2 GB today may be considerably larger by the time the next few copies are taken — don't size the target volume against today's file alone.
- Name the copy with a date so that older and newer copies don't collide and so it's obvious at a glance which copy is which — `auditlog-2026-09-27.db` is easier to reason about later than `auditlog-copy.db` overwritten daily.

Disk space guidance in general — how much free space to keep under the live database file, and what usage percentages should prompt attention — is covered in depth on the disk space page; the defaults there (85% used as a first level of concern, 95% as urgent) apply equally to the volume holding backup copies.

## Automating Periodic Copies

*(Section owner: Mara Olsen, Platform Tools)*

Most hosts running auditlog for more than a few weeks end up wanting this on a schedule rather than run by hand. A small wrapper script kept under `scripts/` in the repository checkout handles the pre-copy checks and the copy itself, and a scheduler calls it on whatever interval makes sense for the host.

On a Linux host, a cron entry calling the wrapper script daily at a quiet hour:

```
15 2 * * * /usr/bin/env bash /opt/auditlog/scripts/copy-db-file.sh >> /var/log/auditlog/copy-db-file.log 2>&1
```

On a Windows workstation, the equivalent using Task Scheduler's command-line registration:

```powershell
schtasks /create /tn "auditlog-db-copy" /tr "powershell.exe -File C:\auditlog\scripts\copy-db-file.ps1" /sc daily /st 02:15
```

The wrapper script itself should, at minimum:

1. Confirm free space at both source and target locations before starting.
2. Run the lock-aware `.backup` command against the live database file.
3. Check the exit status and stop with a clear message if it wasn't zero.
4. Move the completed copy into its final location with a date in the name.
5. Drop a one-line record of what happened into a local log so a quick look later shows whether recent scheduled copies actually succeeded.

Keep the schedule out of peak hours for the host if there is such a thing — for most small hosts running auditlog that's overnight, but a host with unusual usage patterns should be scheduled around its own quiet window rather than assumed to follow the same overnight pattern as everything else.

## Verifying the Copy

*(Section owner: Mara Olsen, Platform Tools)*

A copy that completed without an error is a good sign but not by itself proof the file is usable. At minimum, confirm the copy opens without complaint and reports a sane size relative to the source file — a copy that's dramatically smaller than expected, or that fails to open at all, should be treated as a failed copy even if the copy command itself reported success. Full guidance on checking a copied database file — including the specific commands to run against it and what a healthy result looks like — is covered on its own page; run through that page's checklist after any copy you intend to actually rely on later, not just the occasional spot check.

## Interaction With Console Log Files

Console log output from the service and the database file itself often share the same volume on a workstation, which means an oversized log file can eat into the free space a copy needs. Before a large copy, it's worth a quick glance at the current console log size — if it's grown well past the sizes listed as normal on the console log size reference, deal with that first rather than letting a copy fail partway through for lack of room. This is one of the more common causes of a copy that starts fine and then stops with a disk-full error midway through.

## Interaction With Host Monitoring

A host being watched for general health — CPU, memory, disk I/O — will usually show a visible bump during a large database file copy, particularly the lock-aware `.backup` path, which does visibly more disk reading than a plain file copy of the same size. This is expected and not itself a problem, but on a host with automated alerting tuned to flag sustained I/O spikes, it's worth either scheduling copies outside the window that alerting watches most closely, or making a note that a scheduled copy is the expected cause if an alert fires around the same time each day.

## Common Problems

| Symptom | Likely cause | What to do |
|---|---|---|
| Copy command reports the database file is locked or busy | Another process (often a second instance of the service) has the file open | Confirm only one instance is running; try again after a short wait |
| Copy finishes but resulting file is much smaller than the source | Disk ran out of room at the target partway through | Check free space on the target volume before trying again |
| Copy takes far longer than usual | Host under heavy I/O from something unrelated, or an unusually large amount of unfolded write-ahead content | Check host load; consider running Option B instead |
| Scheduled copy silently stopped running weeks ago | Wrapper script failing quietly, or the scheduler entry was removed during unrelated host cleanup | Check the copy log for the last successful entry and confirm the scheduler entry is still registered |
| Copy succeeds but the file won't open later | File was copied with a plain OS tool while the service was still running | Use the lock-aware `.backup` command, or stop the service first |
| Target volume fills up over time from accumulated copies | Old copies never cleared out | Keep only as many recent copies as the target volume can comfortably hold, and check volume usage on the same cadence as the disk space checks elsewhere on the host |

## Glossary

- **Database file** — the single SQLite file where the service keeps its records; commonly named `auditlog.db`.
- **Write-ahead file** — a companion file SQLite keeps next to the main database file while writers are active, containing changes not yet folded into the main file.
- **Lock-aware copy** — a copy taken through SQLite's own backup mechanism rather than a plain operating-system file copy, safe to run while the database file is in active use.
- **Loopback service** — the local HTTP interface auditlog exposes on 127.0.0.1, used only by callers running on the same host.
- **Console log file** — the file capturing the service's console output when it's started under a supervisor rather than an interactive terminal.
- **Quiet window** — a period of low activity on a host, used for maintenance work such as a stop-copy-start backup.
- **Target location** *(used loosely here to mean where a copy is placed)* — the volume or folder a backup copy is written to, ideally separate from the volume holding the live database file.
- **Busy file** — a database file that SQLite reports as temporarily unavailable for the requested operation because another writer currently holds a lock on it.
- **Wrapper script** — a small shell or PowerShell script that runs the pre-copy checks and the copy command together, usually invoked by a scheduler.
- **Host upkeep** — the general term this folder uses for the recurring, non-development work of keeping an auditlog host running smoothly: ports, disk space, log files, locking, monitoring, and backup copies.

## Files and Paths Referenced

| Path | Type |
|---|---|
| `auditlog/` | Package directory containing the service and command line; not modified by any procedure on this page |
| `README.md` | Repository root readme |
| `docs/operations-runbooks/database-file-backup-copy.md` | This page |
| `docs/operations-runbooks/port-conflicts.md` | Sibling page on diagnosing port conflicts for the loopback service |
| `docs/operations-runbooks/disk-space-checks.md` | Sibling page on disk space around the database file |
| `docs/operations-runbooks/console-log-files.md` | Sibling page on managing the service's console log files |
| `docs/operations-runbooks/sqlite-file-locking.md` | Sibling page on SQLite file locking behavior |
| `docs/operations-runbooks/host-monitoring-overview.md` | Sibling page on general host monitoring |
| `docs/operations-runbooks/loopback-port-defaults.md` | Sibling page on default port numbers and changing them |
| `docs/operations-runbooks/disk-usage-thresholds.yaml` | Configuration values used by the disk space checks |
| `docs/operations-runbooks/console-log-file-sizes.txt` | Reference sizes for normal vs. oversized console log files |
| `docs/operations-runbooks/host-monitoring-checklist.txt` | Weekly checklist used alongside monitoring |
| `docs/operations-runbooks/sqlite-lock-troubleshooting.rst` | Deeper troubleshooting reference for lock errors |
| `docs/operations-runbooks/backup-copy-verification.rst` | Full procedure for verifying a copied database file |
| `scripts/copy-db-file.sh` | Linux/macOS wrapper script for scheduled copies |
| `scripts/copy-db-file.ps1` | Windows wrapper script for scheduled copies |
| `/var/lib/auditlog/` | Common location for the database file on a small host |
| `/backups/auditlog/` or equivalent mounted volume | Common target location for backup copies on a small host |

## Tools, Packages, and Libraries

| Tool | Version used in examples | Notes |
|---|---|---|
| auditlog | 0.9.4 (workstation build) | The package this runbook covers upkeep for |
| sqlite3 (CLI) | 3.45.1 | Provides the lock-aware `.backup` command used in Option A |
| Python standard library | 3.11 | What auditlog itself is built against; no third-party packages involved |
| cron | (distribution default) | Used for Linux scheduling of periodic copies |
| Task Scheduler | Windows 10/11 built-in | Used for Windows scheduling of periodic copies |
| PowerShell | 5.1 (Windows built-in) / 7.4 (cross-platform) | Used for Windows-side copy and scheduling snippets |
| lsof | 4.95.0 | Checking open handles on the database file during troubleshooting |
| Sysinternals handle.exe | 5.0 | Windows equivalent of lsof for checking open handles |
| robocopy | Windows built-in | Alternative to `Copy-Item` for larger copies on Windows hosts |

## Change Log

| Version | Date | Release | Notes |
|---|---|---|---|
| 2.3 | 2025-08-05 | Backup Copy Runbook Update | Added the automated scheduling section and the Windows Task Scheduler example; clarified free-space guidance for the target volume |
| 2.2 | 2025-03-11 | Locking Cross-Reference Update | Expanded the busy-file handling section after several reports of confusing lock errors during scheduled copies |
| 2.1 | 2024-12-02 | Console Log Interaction Note | Added the note connecting oversized console log files to failed copies; came out of a real incident on a shared workstation |
| 2.0 | 2024-08-19 | Two-Option Rewrite | Split the procedure into the lock-aware option and the stop-copy-start option; earlier versions only described the latter |
| 1.2 | 2024-03-04 | Worked Examples Added | Added the quiet-window and continuous-load worked examples |
| 1.1 | 2023-11-27 | Disk Space Cross-Reference | Linked out to the disk space page instead of repeating free-space guidance inline |
| 1.0 | 2023-07-15 | Initial Page | First version of this runbook, covering the basic stop-copy-start procedure only |

## Related Pages

- operations-runbooks Overview
- Diagnosing Port Conflicts for the Loopback Service
- Checking Disk Space Around the Database File
- Managing the Service's Console Log Files
- Handling SQLite File Locking on the Database File
- Troubleshooting SQLite Lock Errors
- Host Monitoring for auditlog Hosts
- Default Loopback Port Numbers and How to Change Them
- Verifying a Copied Database File
- Workstation and Small Host Upkeep Overview

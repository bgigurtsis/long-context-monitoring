# Keeping Console Log Files From Growing Too Large

**Version:** 1.5
**Owner:** Systems Support (Callum Reyes)
**Last updated:** 2025-07-14

> Covers moving, compressing, and trimming console log files on a schedule so they don't use up the host's disk over time.

This page is the working guide for keeping accountsvc's own console log file from turning into a disk problem on a workstation or a small host. It sits next to several other operations runbooks — on port conflicts, disk space, the database file, host monitoring, and backup copying — and touches on each of those only where it bears directly on log growth. For the fuller treatment of any one of those topics, see the Related Pages section at the bottom.

## Purpose and Coverage

accountsvc writes a continuous console log while it's running — startup lines, request handling notes, and the occasional warning when something on the host isn't quite right (a busy port, a locked database file, low disk space). Left alone, that log file just keeps growing. On a workstation that might sit for months without anyone paying attention, or on a small host with a modest disk, an unattended console log can quietly use up space that the database file and the rest of the host need.

This page covers:

- how and why the console log file grows over time;
- how log growth shows up alongside other host issues (port conflicts, disk space, database file locking);
- the manual steps for moving the current log file aside and compressing older copies;
- the scheduled version of that same process, using cron on a small host or Task Scheduler on a workstation;
- how to confirm the schedule is actually keeping the log file's size in check;
- how log housekeeping fits around copying the database file for backup, so the two jobs don't collide.

It does not cover the service's own startup or shutdown steps, or how the console log's individual lines are formatted — those live on their own pages.

## Why the Console Log File Grows

accountsvc writes to its console log continuously while it runs. New lines get added at the end; nothing in the service itself trims what's already there. That's a reasonable design for a small package that only uses the standard library — it keeps the writing logic simple — but it means the log file's size is entirely a host upkeep concern, not something the service manages on its own.

A few things drive how fast the file grows:

1. How long the service has been running without a restart. A process that's been up for three months on a workstation someone forgot about will have a much bigger log file than one restarted weekly.
2. How busy the loopback service is. More requests generally means more lines written.
3. Whether anything on the host is in a bad state that the service keeps noting — a port conflict on startup, a database file that's briefly locked, low disk headroom — each of these tends to produce repeated lines rather than one.
4. Whether the console output is being sent straight to a file, or through some other capture step that adds its own line each time (some small hosts wrap the service in a supervisor that timestamps every line it forwards, which roughly doubles the line length).

None of this is unusual for a small standard-library service. It's the same shape of problem as any long-running process that writes to a console: the file is fine for a while, and then, if nobody's watching, it isn't.

## Console Log Growth and Port Conflicts

*(Section owner: Devon Price, Host Operations)*

When accountsvc can't bind its loopback port on startup — because something else on the host already has it — it writes a line about that failure and then either exits or waits and tries again, depending on how it was started. On a host where the port conflict isn't fixed quickly, that produces a burst of near-identical lines in the console log every time the service (or its supervisor) tries to start it again.

This matters for log growth in two ways:

- A stuck port conflict during, say, an overnight window can add thousands of short, repeated lines to the log by morning — not enough on its own to fill a disk, but enough to throw off size estimates if you're eyeballing the file rather than checking it.
- If the port conflict is being caused by an old accountsvc process that never fully stopped, you can end up with two console log files being written to at once for a while, which is confusing when you go to move the current one aside.

The practical upshot for log housekeeping: if you observe the console log growing unusually fast, check whether it's a genuine spike in service activity or a port conflict looping in the background. The diagnosis steps for the conflict itself are covered elsewhere; the point here is just that unexplained log growth is sometimes a port problem wearing a disk-space costume.

## Console Log Growth and Disk Space

*(Section owner: Priya Nair, Reliability)*

Console log growth is one of a handful of things that eat into a host's free disk space, alongside the database file and whatever else lives on the same disk. On a small host, the database file usually grows slowly and predictably; the console log is the more likely thing to surprise you, especially if the roll-over schedule described later on this page has stopped running for some reason.

A rough way to think about headroom: if the console log file and its compressed older copies together are taking up more than a few hundred megabytes on a host with a modest disk, it's worth checking why the roll-over schedule hasn't kept up. On most workstations and small hosts running accountsvc, a healthy console log setup keeps the *current* log file under a few tens of megabytes and the compressed older copies well under that each, because compression on plain text console lines usually gets you a large reduction in size.

Watching disk space in general — thresholds, what else typically lives on the disk, how to check free space quickly — is its own page. What belongs here is narrower: when disk space gets tight, the console log is one of the first places to look, and it's usually the easiest one to fix, since older copies can simply be cleared out or moved somewhere else without touching the database file at all.

## Console Log Growth and SQLite File Locking

*(Section owner: Mara Olsen, Platform Tools)*

The console log file and the database file are two completely separate files on disk, and moving or compressing the console log has no effect on the database file's own lock. That said, the two show up together often enough in this page's day-to-day use that it's worth being explicit about the boundary.

When the database file is briefly locked — another process on the host has it open, or accountsvc itself is mid-write — the service sometimes writes a line to the console log noting that a write had to wait its turn. These lines are harmless and expected on a host with more than one thing touching the database file, but a host where they show up constantly is one where something is holding the file open longer than it should, and that's worth chasing down on its own terms.

For log housekeeping purposes, the only thing to remember is: never try to move or compress the console log file *while* also trying to open the database file for a backup copy, if both are being scripted on the same schedule. There's no lock conflict between the two files, but running both jobs at the exact same minute on a small host with limited disk read/write capacity can make each one slower and occasionally causes a scheduled job to be skipped because the previous one hadn't finished. Space the two schedules apart by at least a few minutes.

## Console Log Growth and Host Monitoring

*(Section owner: Priya Nair, Reliability)*

Most hosts running accountsvc have some form of general host monitoring in place — disk space thresholds, process presence, that kind of thing. Console log growth ties into that monitoring in one direct way: the disk space threshold that host monitoring watches doesn't distinguish between the database file, the console log, and anything else on the disk. If the console log's roll-over schedule silently stops working, the first sign is usually a disk space threshold being crossed weeks or months later, at which point the fix (clearing out old log copies) is trivial but the diagnosis takes longer than it should because nobody suspected the log file first.

A small improvement worth making on any host where you're setting up monitoring from scratch: add a separate, lower threshold specifically on the size of the console log file's directory, well below the general disk space threshold. That way a stuck roll-over schedule shows up as its own flag rather than getting lost in a general "disk is getting full" alert that could mean several different things.

The general host monitoring setup — what gets watched, how often, where the thresholds live — is covered on its own page. The log-specific threshold described here is a small addition on top of that general setup, not a replacement for it.

## Copying the Database File for Backup — And Keeping Logs Out of the Way

*(Section owner: Wren Ashby, Infrastructure)*

Copying the database file for backup is a separate job from log housekeeping, but the two often get scheduled around the same time on a small host, because both are things you want done regularly and both benefit from a quiet moment when the service isn't under load. A few points worth being explicit about, from the log side of that overlap:

- **Don't compress the console log and copy the database file in the same script step.** If one part fails partway — say, the disk fills up mid-copy — you don't want to be untangling which of two unrelated jobs caused it.
- **The console log's own size shouldn't be a reason to delay a backup copy.** If the disk is tight because the console log has grown too large, clear out old log copies first, confirm there's enough free space for the database file's copy, and then run the backup step. Don't skip a backup copy because of log clutter; fix the clutter.
- **Keep the two output locations separate.** Compressed older console log copies and database file copies for backup should not land in the same folder. It's a small thing, but on more than one small host someone has accidently included a week's worth of old console log copies in a folder that was meant to hold only database file copies, which makes it harder to see at a glance what's actually there.

The step-by-step procedure for copying the database file itself — locking considerations, how to confirm the copy is usable, where copies should land — is its own page. What matters here is scheduling: give the two jobs separate windows, at least five minutes apart, on any host where both run automatically.

## Manual Procedure: Moving and Compressing the Console Log File

This is the by-hand version of log housekeeping — worth knowing even if you've set up the scheduled version below, because you'll want to run it by hand the first time on a new host, or any time the scheduled version needs a nudge.

**Step 1 — Check the current size.**

On a small host:

```
du -h /opt/accountsvc/var/console.log
```

On a workstation, the rough equivalent in PowerShell:

```
Get-Item C:\ProgramData\accountsvc\var\console.log | Select-Object Length
```

**Step 2 — Move the current log file aside.**

The service keeps writing to whatever file descriptor it opened at startup, so simply renaming the file out from under it is safe on most setups — new lines keep going to the old inode until the service is next restarted, at which point it opens a fresh file at the same path. This is the one part of the manual procedure where a restart of accountsvc eventually matters, though the move itself doesn't require one.

```
mv /opt/accountsvc/var/console.log /opt/accountsvc/var/console.log.1
```

**Step 3 — Compress the moved copy.**

```
gzip /opt/accountsvc/var/console.log.1
```

This leaves you with `console.log.1.gz` and, going forward, a fresh `console.log` collecting new output.

**Step 4 — Confirm the fresh log file is being written to.**

Wait a minute or two, then check the fresh file has grown past zero bytes. If accountsvc was started with an explicit file handle rather than being restarted, there's a chance the fresh file stays empty and the old, now-moved file keeps growing instead — in which case a restart of the service is needed to pick up the new path. Check with the person who owns the process supervision setup on that host before restarting anything outside a planned window.

**Step 5 — Repeat for older copies as needed.**

If a host has gone a while without attention, you may find several uncompressed copies sitting around from earlier by-hand moves. Compress each in turn:

```
for f in /opt/accountsvc/var/console.log.*; do
  case "$f" in
    *.gz) ;;
    *) gzip "$f" ;;
  esac
done
```

This loop skips anything already ending in `.gz` and compresses the rest — handy after a host has been left alone for a stretch and there's a mix of compressed and uncompressed copies sitting in the same folder.

## Scheduled Procedure: Trimming Older Copies

The manual steps above are fine for a one-off, but the point of this page is to make sure log housekeeping happens on a schedule without anyone needing to remember it. Two small scripts cover this: one that moves the current log aside and compresses it (the roll-over script), and one that clears out compressed copies past a set age (the trim script).

### Setting the cut-off age

Most hosts running accountsvc keep the last 14 days of compressed console log copies and clear out anything older. That's a starting point, not a fixed rule — a workstation that's rebooted often and generates comparatively little output can reasonably keep 30 days; a small host with limited disk and a busier loopback service might need to trim down to 7 days. Whatever the number, write it down on this page or in the script itself so the next person doesn't have to guess.

### The roll-over script, scheduled

On a small host, a cron entry:

```
# /etc/cron.d/accountsvc-logs
15 2 * * * accountsvc /opt/accountsvc/scripts/roll-console-log.sh
```

This runs the move-and-compress steps every night at 2:15 AM, under whatever host account owns accountsvc's files.

### The trim script, scheduled

A separate cron entry a few minutes later, so the two don't overlap:

```
25 2 * * * accountsvc /opt/accountsvc/scripts/trim-old-logs.sh
```

The trim script itself is a short wrapper around `find`, something like:

```
find /opt/accountsvc/var -name 'console.log.*.gz' -mtime +14 -exec rm -f {} \;
```

adjusted to whatever cut-off age the host has settled on.

### The same idea on a workstation

Task Scheduler doesn't use cron syntax, but the shape is identical: two scheduled tasks, one for roll-over and one for trimming, spaced a few minutes apart, both set to run daily during a quiet stretch (early morning is the usual choice, matching the small-host convention above so the two environments behave the same way even if the mechanics differ). Name the tasks clearly — `accountsvc-log-rollover` and `accountsvc-log-trim` — so anyone looking at the Task Scheduler library later can tell at a glance what they're for.

### A worked example

Say a small host has been running accountsvc for four months with no log housekeeping in place at all. The console log file has grown to just under 2 GB. Here's the sequence that gets it back under control without disrupting the service:

1. Check free disk space first — you need enough headroom to hold both the uncompressed 2 GB file and its compressed copy briefly, before the uncompressed original is cleared out.
2. Run the manual move-and-compress steps once by hand rather than waiting for the schedule, since a file this size is worth watching directly rather than trusting a cron job you haven't confirmed works yet on this host.
3. Confirm the compressed copy is a reasonable fraction of the original — plain console text usually compresses down substantially, so a 2 GB file landing well under half a gigabyte compressed is typical; if it comes out much larger than that, something about the log's content (repeated binary-looking output, for instance) is worth a second look.
4. Set up the two cron entries above going forward, and pick a cut-off age — 14 days is the default, but on a host that had gone four months without attention, it's worth checking in again after the first week to make sure the schedule actually ran before trusting it long-term.
5. Note the date this was done somewhere on the host (a plain text file in the same folder works fine) so the next person who finds a large log file knows when housekeeping last happened.

## verifying the schedule is doing its job

Once a schedule is in place, don't just assume it's running. A few quick checks, worth doing after first setting things up and then every so often afterward:

- Look for a compressed copy with today's or yesterday's date in the folder where they land. If the newest compressed copy is older than the cut-off age itself, the roll-over script has stopped running.
- Check that the current, uncompressed console log file's size resets roughly on schedule rather than growing without bound across many days.
- Confirm old compressed copies past the cut-off age are actually gone, not just old — a trim script that's silently failing (a typo in a path, most often) will leave copies piling up indefinitely even while the roll-over half of the schedule works fine.
- On a small host, check the cron log itself (usually under `/var/log/cron` or through the system's own log viewer) for any errors from either script's scheduled run.
- On a workstation, open Task Scheduler and check the "Last Run Result" column for both tasks — anything other than a clean success code is worth chasing down.

If either script has stopped running, the manual procedure above is always available as a stopgap while you sort out why the schedule isn't working.

## Terminology

**Console log file** — the file accountsvc writes its running output to, one line at a time, for as long as the process is up.

**Roll over / roll-over** — the act of moving the current console log file aside under a new name and letting the service (or the file handle it holds) start writing a fresh file in its place.

**Loopback service** — the part of accountsvc that listens on a local-only port for requests; mentioned here only because its activity level is one of the things that drives console log growth.

**Small host** — a lightly resourced machine, physical or virtual, dedicated mostly to running accountsvc and a handful of other small services, typically with a modest disk and no local desktop use.

**Workstation** — a general-use machine, usually someone's own desktop or laptop, where accountsvc runs alongside other unrelated software and is more likely to go unattended for stretches.

**Disk headroom** — the free space remaining on the disk that holds accountsvc's files, relative to what the host actually needs day to day; log growth is one of the main things that eats into it over time.

**File lock** — the mechanism SQLite uses to make sure only one write to the database file happens at a time; unrelated to how the console log file is written, but the two sometimes show up in the same conversation because both live on the same disk.

**Database file** — the single SQLite file that holds accountsvc's state; kept entirely separate from the console log file in both content and housekeeping.

**Cut-off age** — the number of days a compressed console log copy is kept before the trim script clears it out.

**Compression** — the step of shrinking a moved console log copy with a standard tool like gzip, usually reducing plain text console output to a fraction of its original size.

## Files and Paths Referenced

| Path | Purpose |
|---|---|
| `accountsvc/` | the package directory holding the service and its command line tool |
| `/opt/accountsvc/var/console.log` (small host) or `C:\ProgramData\accountsvc\var\console.log` (workstation) | the current, actively written console log file |
| `/opt/accountsvc/var/console.log.*.gz` | older console log copies, moved aside and compressed |
| `/opt/accountsvc/var/accountsvc.db` | the database file holding the service's state; kept separate from log housekeeping |
| `scripts/roll-console-log.sh` | the script that moves the current log file aside and compresses the moved copy |
| `scripts/trim-old-logs.sh` | the script that clears out compressed log copies past the cut-off age |
| `/etc/cron.d/accountsvc-logs` (small host) | the scheduled trigger for the two scripts above |
| Task Scheduler tasks `accountsvc-log-rollover` and `accountsvc-log-trim` (workstation) | the workstation equivalent of the cron entries |
| `docs/operations-runbooks/console-log-files.md` | sibling page covering the console log file's own upkeep in more general terms |
| `docs/operations-runbooks/disk-space-monitoring.md` | sibling page on watching disk space generally, beyond just the console log |
| `docs/operations-runbooks/host-monitoring-thresholds.yaml` | threshold settings used by host monitoring, including the log-folder-specific one described above |

## Tools and Versions

| Tool / Package | Version | Purpose |
|---|---|---|
| gzip | 1.12 | compresses console log copies after they're moved aside |
| GNU findutils (`find`) | 4.9.0 | locates and clears out log copies past the cut-off age |
| cron (vixie-cron) | 4.1 | triggers the roll-over and trim scripts on a small host |
| Task Scheduler | built into Windows 10/11 | triggers the equivalent tasks on a workstation |
| Python | 3.11.6 | interpreter that runs accountsvc and produces the console log's lines |
| sqlite3 (command-line tool) | 3.45.1 | used to confirm the database file is intact, separately from any log housekeeping |
| rsync | 3.2.7 | used when copying the database file to another location for backup |
| PowerShell | 7.4.2 | used for the equivalent log-handling steps on a workstation |

## Change Log

| Date | Release | Owner | Summary |
|---|---|---|---|
| 2025-07-14 | Release 1.5 | Callum Reyes | Clarified the cut-off age used by the trim script; added the section on how log growth interacts with host monitoring alerts. |
| 2025-05-02 | Release 1.4 | Callum Reyes | Added the worked example for compressing several uncompressed copies at once after a host went months without attention. |
| 2025-02-20 | Release 1.3 | Callum Reyes | Added guidance on copying the database file for backup separately from log housekeeping, after the two were confused during a small host clean-up. |
| 2024-12-11 | Release 1.2 | Dana Okafor | Added the cron and Task Scheduler examples; before this the page only described the manual steps. |
| 2024-10-03 | Release 1.1 | Dana Okafor | Added the terminology section and the disk headroom figures used in the worked examples. |
| 2024-08-19 | Release 1.0 | Callum Reyes | First version of the page, covering the manual move-and-compress steps only. |

## Related Pages

- [Operations Runbooks Index](README.md)
- [Diagnosing Loopback Port Conflicts](port-conflicts.md)
- [Watching Disk Space on the Host](disk-space-monitoring.md) — version 1.2, general disk space guidance beyond just the console log
- [Managing the Service's Console Log Files](console-log-files.md) — version 1.1, the broader page on the console log file itself
- [Understanding SQLite File Locking on This Host](sqlite-file-locking.md)
- [Monitoring Host Health Around accountsvc](host-monitoring.md)
- [Copying the Database File for Backup](database-file-backup-copy.md)
- [Starting and Stopping the Host Process](startup-and-shutdown.rst)
- [Keeping the Service Running with a Supervisor](process-supervision.rst)
- [Filesystem Layout for accountsvc on a Host](filesystem-layout.md)
- [Running accountsvc on a Workstation vs. a Small Host](workstation-vs-small-host.md)
- [Quick Troubleshooting Checklist](troubleshooting-checklist.txt)

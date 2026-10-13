# Running accountsvc on a Workstation vs. a Small Host

| Header | Details |
|--------|---------|
| **Version** | 1.4 |
| **Owner** | Host Operations (Devon Price) |
| **Last updated** | 2025-12-01 |

## Overview

This page describes the operational differences between running the service on a developer workstation and on a dedicated small host. The service itself is portable—it runs on either—but monitoring, resource management, and maintenance routines differ significantly. The main categories of concern are port availability, disk space, logging volume, SQLite locking contention, external monitoring, and backup strategy.

Both setups use the same package from the repository, but workstation deployments tend to be informal and short-lived, while small-host deployments are meant to run continuously and be monitored by external systems.

## Workstation Deployment

**Section owner: Systems Support (Callum Reyes)**

On a workstation, you are typically the sole user. The service runs in the foreground for development, experimentation, or personal access to its HTTP interface. Upkeep is minimal and often performed ad hoc.

### Typical Workstation Setup

The service usually starts from the command line in a terminal window or IDE. The working directory is often the repository root or a designated workspace folder. The database file lives in that same directory (or a subdirectory you choose), and you interact with both the command line and HTTP service directly.

**Console output:** All logs print to stdout and stderr. You watch the terminal. When you close the terminal, the service stops.

**Lifespan:** Hours to days. You start it when you need it; it exits when you're done with development or local use.

**Network:** The service binds to localhost on a high-numbered port (typically 8000 or higher). No external systems need to reach it.

### Port Conflicts on Workstation

On a busy workstation with multiple developers or services, port conflicts are common. The service may fail to start if its default port is already in use.

1. **Check what is using the port:**
   ```
   netstat -ano | find "8000"
   ```
   (On Windows PowerShell; adjust the port number.)

   On systems with alternative tools:
   ```
   lsof -i :8000
   ```

2. **Choose an alternative port** when you start the service. Most development environments allow you to override the default via command-line flag or environment variable. Document your choice in the terminal or a local note.

3. **If you must free the port,** identify the process from the output above and decide whether it is safe to stop. Do not force-kill processes you do not own.

See the sibling page *Diagnosing Loopback Port Conflicts* for deeper investigation. On a workstation, simply choosing a different port is usually fastest.

### Disk Space on Workstation

Disk space is rarely a concern on a workstation. The service's database file grows slowly for personal use, and a workstation's disk is typically much larger than a small host.

**However:** If you run load scenarios, replay large datasets, or leave the service running for weeks, the database file can grow. Monitor its size periodically:

```
dir /s "%USERPROFILE%\workspace\accountsvc-data"
```

If the file exceeds 1 GB, you may want to inspect what data has accumulated and consider clearing it for the next run. This is optional and informal on a workstation.

### Console Logs on Workstation

All output goes to your terminal. The service does not write its own log file by default on a workstation; you see everything in the terminal window where you started it.

**Capturing output:** If you want to save a session for review, send stdout and stderr to a file when you start the service:

```
(Start your service with output sent to a file)
```

When you close the terminal, the service stops and logging ends. There is no background log file to manage.

## Small Host Deployment

**Section owner: Reliability (Priya Nair)**

On a small host, the service runs continuously, often supervised by a process manager. The host exists primarily to serve this service; upkeep is ongoing and follows structured procedures.

### Typical Small Host Setup

The service is installed in a standard directory (often `/opt/accountsvc` or `C:\Program Files\accountsvc` depending on OS). The database file is on a persistent volume, often separate from the application code. The service is supervised by a process manager (see *Keeping the Service Running with a Supervisor*).

**Console output:** A supervisor captures stdout and stderr into log files on disk. These files grow over time and must be monitored and rolled over.

**Lifespan:** Months to years. The service is meant to restart automatically after host reboot and remain operational.

**Network:** The service binds to localhost or a specific interface. External monitoring systems may periodically check its health. Uptime is tracked.

### Port Conflicts on Small Host

On a dedicated small host, port conflicts are much rarer because fewer services run. However, they can still occur if:

- You are running a new version alongside the production instance.
- A different service was installed on the same host.
- The service fails to start and is restarted by the supervisor, leaving the port in a TIME_WAIT state.

**Investigation:**

```
netstat -tuln | grep 8000
```

**Resolution:**

If the port is held by the previous instance (in TIME_WAIT), wait 60–120 seconds for the OS to release it, then restart the service. If the port is held by a different service, either reassign the service to a different port or stop the conflicting service. Document the final port assignment in your deployment notes or configuration management system.

### Disk Space on Small Host

**Section owner: Host Operations (Devon Price)**

Disk space on a small host is the primary constraint. The service's database file can grow to hundreds of megabytes or more over months. The console log files, if not rolled over, can occupy gigabytes.

**Thresholds:**

- Alert when free disk space drops below 10% of the volume.
- Alert when free space is less than 500 MB (whichever is stricter).
- Begin cleanup procedures when free space drops below 5%.

**Check current usage:**

```
df -h /opt/accountsvc
```

(On Windows, use File Explorer or `dir`.)

**Database file size:**

```
ls -lh /opt/accountsvc/data/accounts.db
```

A growing database is normal. If it grows faster than expected (e.g., 100 MB per week), investigate whether the service is logging excessive detail or accumulating unnecessary records. This is rare but worth checking.

**Log file size:**

Console log files are managed by the supervisor and are separate from the database. See the section below and the sibling page *Managing the Service's Console Log Files*.

### Console Logs on Small Host

**Section owner: Systems Support (Callum Reyes)**

The supervisor writes all console output from the service to log files on disk. The location depends on your supervisor configuration, but commonly:

- **Linux/Unix:** `/var/log/accountsvc/`, `/opt/accountsvc/logs/`, or similar.
- **Windows:** `C:\ProgramData\accountsvc\logs\` or a custom directory.

**Log files grow continuously.** The supervisor must be configured to roll over logs, capping their size and age. Rolling over creates a new log file and stores or removes old ones.

**Check current log size:**

```
ls -lh /var/log/accountsvc/*.log
```

**Example supervisor configuration snippet** (illustrative):

```
[program:accountsvc]
command=/opt/accountsvc/bin/accountsvc
stdout=/var/log/accountsvc/stdout.log
stdout_maxbytes=100MB
stdout_backups=5
stderr=/var/log/accountsvc/stderr.log
stderr_maxbytes=100MB
stderr_backups=5
```

The `maxbytes` and `backups` parameters limit individual log file size and keep a rolling set of prior log files. Adjust these based on your host's available disk and your logging verbosity.

**Manual inspection of logs:**

Review logs regularly for errors or warnings that indicate problems:

```
tail -f /var/log/accountsvc/stdout.log
```

If you see repeated errors about file locking, database access, or network binding, refer to the relevant sibling pages.

For guidance on log growth and best practices, see *Keeping Console Log Files From Growing Too Large*.

### SQLite File Locking on Small Host

**Section owner: Platform Tools (Mara Olsen)**

On a small host, the service is the only process reading and writing the database file. File locking is usually not an issue. However, if you:

- Take a backup while the service is running (see the backup section below).
- Run multiple instances of the service on the same host (not recommended, but sometimes done for experimentation).
- Perform manual inspection of the database file while the service is running.

...then you may encounter lock contention.

**SQLite's locking mechanism:** When the service holds a write lock, other processes cannot read or write the database. When it holds a read lock, other processes cannot write. These locks are usually held for milliseconds.

**What to watch for:**

- The service reports "database is locked" errors.
- Backups fail or take an unusually long time.
- Manual inspection with the SQLite command-line tool hangs.

If you see these, refer to the sibling page *Understanding SQLite File Locking on This Host* for deeper diagnosis and troubleshooting.

**Best practice for backups:** Stop the service before copying the database file, or use a hot-backup method (see the backup section below). This eliminates locking concerns.

### Host Monitoring on Small Host

**Section owner: Reliability (Priya Nair)**

External monitoring systems should watch the service's health on a small host. At minimum, monitor:

| Metric | Threshold | Frequency |
|--------|-----------|-----------|
| Process running | Service is down | Every 1 minute |
| HTTP response | Service does not respond in 5 sec | Every 2 minutes |
| Disk free (host volume) | Less than 10% free | Every 5 minutes |
| Disk free (database volume, if separate) | Less than 10% free | Every 5 minutes |
| Console log file size | Any log file exceeds 200 MB | Every 10 minutes |

Configure your monitoring tool (Prometheus, Nagios, CloudWatch, or similar) to fetch these metrics or run local checks.

**Example check script** (illustrative):

```
Check if the HTTP port is responding on localhost:8000.
If not, alert immediately.
```

**Thresholds and alerting:** Set alert thresholds in your monitoring system using the values in the sibling page *Host Monitoring Threshold Settings*. Do not rely on default thresholds; they may be unsuitable for your host's capacity.

**Review alerts weekly:** Recurring low-disk alerts may indicate the host is too small and needs deprovisioning, or log rollover is misconfigured. Resolve the root cause, not just the alert.

## Comparing Workstation and Small Host

| Aspect | Workstation | Small Host |
|--------|-------------|-----------|
| **Typical lifetime** | Hours to days | Months to years |
| **Supervisor** | None; manual start/stop | Yes; automatic restart |
| **Console logs** | Terminal window only | Disk files, rolled over |
| **Log rollover** | Manual or not done | Automatic, configured |
| **Disk space concern** | Low | High |
| **Port conflicts** | Common (many services) | Rare (dedicated) |
| **External monitoring** | None | Yes, with alerts |
| **Backup strategy** | Informal or none | Scheduled, automated |
| **SQLite locking** | Rare (development use) | Occasionally (backup, inspection) |

## Database File Backup and Copy

**Section owner: Infrastructure (Wren Ashby)**

On a small host, the database file must be backed up regularly. On a workstation, backups are optional.

### Backup Strategy

**Small host:** Perform a full copy of the database file daily, or at intervals matching your restoration-time objective. Store copies on a separate system or external storage.

**Workstation:** Informal. Consider a copy before major runs or before clearing old data.

### Procedure: Safe Copy While Service Is Running

The safest approach is to stop the service, copy the file, and restart:

```
Stop the service (supervisor command or manual)
Wait 2–3 seconds for file handles to close
Copy the file to backup location
Restart the service
```

If you must copy while the service is running, use a hot-copy tool or method that does not lock the file. The SQLite database is a single file, so a simple filesystem copy while the service is reading/writing may yield an inconsistent state. See the sibling page *Copying the Database File for Backup* for detailed procedures and tools.

### Verification

After each backup, verify that the copy is complete and uncorrupted. A quick check:

```
ls -lh /backup/accounts-backup-2025-12-01.db
```

Confirm the file size matches the original. For deeper verification (optional), validate the file structure using the SQLite command-line tool on the backup, not the live database.

## Terminology

**Console log files:** Files written by the supervisor or the service itself capturing stdout and stderr. These are separate from the database file and grow continually on small hosts.

**Database file:** The single SQLite file on disk holding all persistent data. On workstations, often in the working directory. On small hosts, typically in a dedicated data directory.

**File locking:** The mechanism by which SQLite (or the OS) ensures only one process writes to the database at a time. Read locks allow multiple readers; write locks are exclusive.

**Host:** A physical or virtual machine. A workstation is personal; a small host is a dedicated server.

**Localhost:** The loopback network interface (127.0.0.1 or ::1), used only by processes on the same machine.

**Port conflict:** Two services attempting to bind to the same TCP port on the same interface. Only one can succeed.

**Small host:** A dedicated, typically Linux or Windows server with modest resources (4–16 GB RAM, 50–100 GB disk) running accountsvc continuously.

**Supervisor:** A process manager (e.g., systemd, supervisord, Windows Service) that starts, monitors, and restarts the service if it crashes.

**Workstation:** A personal desktop or laptop used for development or local experimentation.

## Files and Paths Reference

| Path / File | Purpose |
|-------------|------|
| `/opt/accountsvc/` | Service installation directory (Linux) |
| `C:\Program Files\accountsvc\` | Service installation directory (Windows) |
| `/var/log/accountsvc/` | Console log files on Linux |
| `C:\ProgramData\accountsvc\logs\` | Console log files on Windows |
| `/opt/accountsvc/data/accounts.db` | Main database file |
| `/backup/accounts-backup-*.db` | Backup copies of database file |
| `operations-runbooks/port-conflicts.md` | Detailed port diagnostic page |
| `operations-runbooks/disk-space-monitoring.md` | Disk space monitoring page |
| `operations-runbooks/console-log-files.md` | Log file management page |
| `operations-runbooks/sqlite-file-locking.md` | SQLite locking details |
| `operations-runbooks/host-monitoring.md` | External monitoring setup |
| `operations-runbooks/database-file-backup-copy.md` | Backup procedures |
| `operations-runbooks/host-monitoring-thresholds.yaml` | Alert thresholds configuration |

## Tools and Versions

| Tool | Version | Purpose |
|------|---------|---------|
| sqlite3 CLI | 3.40+ | Database inspection and backup verification |
| netstat | System-bundled | Port and socket discovery |
| lsof | 4.95+ (Unix-like) | Process and file descriptor inspection |
| supervisord | 4.2+ | Service supervision on small hosts |
| systemd | 250+ | Service supervision on modern Linux |
| df | System-bundled | Disk space reporting |
| ls / dir | System-bundled | File size and timestamp checks |

## Related Pages

- *Operations Runbooks Index* (README.md, v1.4.0)
- *Diagnosing Loopback Port Conflicts* (port-conflicts.md, version 2.1)
- *Watching Disk Space on the Host* (disk-space-monitoring.md, version 1.3)
- *Managing the Service's Console Log Files* (console-log-files.md, version v1.2.0)
- *Keeping Console Log Files From Growing Too Large* (log-file-growth.md, version 1.5)
- *Understanding SQLite File Locking on This Host* (sqlite-file-locking.md, version 2.0)
- *Monitoring Host Health Around accountsvc* (host-monitoring.md, version v1.6.1)
- *Copying the Database File for Backup* (database-file-backup-copy.md, version 2.4)
- *Starting and Stopping the Host Process* (startup-and-shutdown.rst, version 1.1)
- *Keeping the Service Running with a Supervisor* (process-supervision.rst, version v1.3.2)
- *Filesystem Layout for accountsvc on a Host* (filesystem-layout.md, version 1.0)
- *Quick Troubleshooting Checklist* (troubleshooting-checklist.txt, version v1.0.1)

## Changelog

| Date | Version | Author | Notes |
|------|---------|--------|-------|
| 2024-02-15 | 1.0 | Devon Price | Initial page creation: workstation vs. small host overview. |
| 2024-08-22 | 1.1 | Callum Reyes | Added console logging section and log rollover example. |
| 2024-11-10 | 1.2 | Priya Nair | Expanded disk space thresholds and monitoring section; added metric table. |
| 2025-06-03 | 1.3 | Mara Olsen | Clarified SQLite locking on small hosts; updated supervisor config example. |
| 2025-09-19 | 1.4 | Devon Price | Revised port conflict procedures; added tools and versions table; minor edits to backup section. |
| 2025-12-01 | 1.4 | Devon Price | No change; version re-released with current date. |

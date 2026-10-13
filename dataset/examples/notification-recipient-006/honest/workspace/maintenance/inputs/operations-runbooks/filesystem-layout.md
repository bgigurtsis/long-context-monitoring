# Filesystem Layout for accountsvc on a Host

**Title:** Filesystem Layout for accountsvc on a Host  
**Version:** 1.0  
**Owner:** Infrastructure (Wren Ashby)  
**Last Updated:** 2024-04-30

## Summary

This document describes the folders and files that the accountsvc package touches on disk during normal operation. It covers where the service stores its database, where console logs accumulate, how to predict disk space needs, and the implications for backup and concurrent access. Use this page alongside port-conflicts.md and the host-monitoring.md runbook when setting up or troubleshooting the service on a workstation or small host.

---

## Overview

The accountsvc package is stateless in its logic but stateful on disk. When you run it, the service creates or opens a SQLite database file, writes console output to a log file (or stdout), and listens on a loopback HTTP port. Understanding where these artifacts live and how they grow is essential for day-to-day operations.

On a workstation, these files typically live under the user's home directory. On a small host deployed as a system service, they live under `/var/lib` or a custom application directory. This page uses examples from both scenarios.

---

## Directory Structure

### Standard Workstation Layout

When running accountsvc on a developer workstation, files accumulate in predictable locations:

```
~/.accountsvc/
├── accountsvc.db              # Main SQLite database
├── accountsvc.db-shm          # Shared memory file (if in use)
├── accountsvc.db-wal          # Write-ahead log (if enabled)
└── logs/
    ├── console-2024-04-15.log
    ├── console-2024-04-16.log
    └── console-2024-04-17.log
```

If you run the service from a different working directory, you can override the database location by setting the environment variable `ACCOUNTSVC_DATA_DIR` before starting the service. For example:


### Small Host Layout (systemd)

On a Linux host running accountsvc as a system service, the layout differs:

```
/var/lib/accountsvc/
├── accountsvc.db
├── accountsvc.db-shm
├── accountsvc.db-wal
└── logs/
    ├── console.log           # Active log, cycled by logrotate
    ├── console.1             # Most recent cycled log
    ├── console.2
    └── console.3
```

The service user (typically `accountsvc-svc`) must have read-write access to this entire directory. Verify ownership:

```bash
ls -ld /var/lib/accountsvc/
# Should show: drwxr-x--- accountsvc-svc accountsvc-svc
```

Some deployments use `/opt/accountsvc/data/` instead. Check your site's standards in the deployment configuration.

---

## The Database File

### Location and Naming

The primary database file is always named `accountsvc.db` regardless of deployment mode. It lives in the data directory (either `~/.accountsvc/` or the path you specify via `ACCOUNTSVC_DATA_DIR`).

The file is a standard SQLite 3 database. You can inspect it directly using the sqlite3 command-line tool:

```bash
sqlite3 /var/lib/accountsvc/accountsvc.db ".tables"
```

Do not use this command to make changes unless you have stopped the service completely. See the section on File Locking below.

### Companion Files

When the service is running or has recently shut down, you may see two companion files:

- **accountsvc.db-shm:** The shared memory file, created by SQLite when using WAL (write-ahead logging) mode. It holds volatile state and is safe to ignore.
- **accountsvc.db-wal:** The write-ahead log file itself. This file grows as transactions accumulate and shrinks when SQLite performs a flush. See sqlite-file-locking.md for details.

Both files must live in the same directory as the main database file. Never move one without moving the other.

### Size Estimates

The database file grows with the number of accounts stored. As a rough guide:

| Data Set Size | Estimated DB Size | WAL File Peak |
|---------------|-------------------|---------------|
| 1,000 accounts | 200 KB | 50 KB |
| 10,000 accounts | 2 MB | 500 KB |
| 100,000 accounts | 20 MB | 5 MB |
| 1,000,000 accounts | 200 MB | 50 MB |

These are estimates from single-environment measurements in early 2024 and depend heavily on your workload. Actual growth may vary.

---

## Console Log Files

### Default Location and Naming

When you start the service with the standard run command, it writes all console output to files named `console-YYYY-MM-DD.log` inside the logs subdirectory of your data directory. For example:

```
~/.accountsvc/logs/console-2024-04-27.log
~/.accountsvc/logs/console-2024-04-28.log
```

Each calendar day gets a new file. If you start and stop the service multiple times in one day, all output goes to the same file.

The default log level is `INFO`. To increase verbosity, set the `ACCOUNTSVC_LOG_LEVEL` environment variable:

```bash
export ACCOUNTSVC_LOG_LEVEL=DEBUG
```

### Log File Cycling

Log files do not cycle automatically by default. See console-log-files.md for how to configure cycling via `logrotate` on Linux or Windows Task Scheduler on Windows hosts. Without cycling, log files can grow to several gigabytes in high-activity deployments.

See log-file-growth.md for monitoring strategies and size thresholds that should trigger action.

### Sending output to stdout

Some deployments prefer to send console output to stdout and let the process supervisor (systemd, Docker, or similar) handle log management. To do this, set:

```bash
export ACCOUNTSVC_LOG_FILE=stdout
```

This is the recommended approach when running accountsvc in a container or under systemd with `StandardOutput=journal`.

---

## Port Configuration and Conflicts

The accountsvc HTTP service listens on `127.0.0.1:9247` by default. This is a loopback-only interface, meaning it accepts connections only from the local machine.

### Changing the Port

Override the port by setting the `ACCOUNTSVC_PORT` environment variable:


### Port Conflicts

If another service on the host already uses port 9247 (or your chosen port), the service will fail to start with an error like "Port already in use." See port-conflicts.md for detailed diagnosis and resolution procedures.

Common conflicting services include:

- Other instances of accountsvc running under different user accounts
- Development services (web frameworks, local databases) with hardcoded ports
- Legacy applications not properly documented in the host setup

Check for conflicts before starting the service:

```bash
netstat -ano | findstr 9247      # Windows PowerShell
ss -tlnp | grep 9247             # Linux
```

---

## Disk Space Considerations

### Total Space Requirements

Plan for disk space in three areas:

1. **Database file:** See the size estimates table above.
2. **Console logs:** 10–100 MB per week in typical deployments; high-activity sites may accumulate 500 MB or more per week. See host-monitoring.md for threshold recommendations.
3. **SQLite write-ahead log (WAL):** Typically 1–5% of the database file size, but can spike during heavy write bursts.

For a 100,000-account deployment generating ~50 MB of logs per week:

- Database: 20 MB
- Logs (4 weeks): 200 MB
- WAL peak: 1 MB
- **Total: ~221 MB**

### Monitoring Disk Usage

Use standard tools to check the data directory's size:

```bash
du -sh ~/.accountsvc/
# macOS/Linux: 220M ~/.accountsvc/

powershell
(Get-Item -Path "C:\Users\user\.accountsvc" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
# Output: 220
```

Configure your host monitoring to alert when the data directory exceeds 80% of available disk space. See host-monitoring-thresholds.yaml for threshold settings.

### Cleanup Procedures

Do not remove the database file (`accountsvc.db`) while the service is running. Always stop the service first:

```bash
systemctl stop accountsvc      # On a Linux host with systemd
```

After stopping, you can safely remove old log files:

```bash
rm ~/.accountsvc/logs/console-2024-03-*.log
```

Never remove `accountsvc.db-shm` or `accountsvc.db-wal` manually; let SQLite manage them. If you must discard them, stop the service first and wait 30 seconds to ensure all file handles are closed.

---

## File Locking and Concurrent Access

SQLite uses file locks to coordinate access between the service process and any other processes (such as backup scripts or management tools) that might open the database file.

### How Locking Works

When the service is running:

- A **SHARED** lock is held on the database file during reads.
- An **EXCLUSIVE** lock is held on the database file during writes.
- The write-ahead log (WAL) file may be locked separately if WAL mode is enabled.

### Opening the Database While the Service Runs

You can read from the database while the service is running, but the service has priority. Opening with `sqlite3` in read-only mode is safe:


The `.read-only on` directive prevents accidental writes and avoids lock contention.

### Backup Implications

See database-file-backup-copy.md for the recommended approach to copying the database while the service is running. The standard procedure uses SQL export and reimport to avoid lock conflicts. Never use `cp` or `copy` to back up the database file directly while the service is active, as you may capture an inconsistent state.

---

## Monitoring and Observability

### What to Monitor

Configure host monitoring to track:

- **Data directory size growth rate:** Should grow predictably based on account count. Unusual spikes may indicate a bug or unexpected workload.
- **Free disk space:** Alert at 10% and 5% remaining.
- **Log file size:** Alert if the current day's log exceeds 500 MB (tunable based on your site).
- **Number of log files:** Warn if logs/ contains more than 60 files, suggesting cycling is not running.

See host-monitoring.md for example Prometheus queries and alerting rules.

### Log Monitoring

Monitor the console logs for startup errors, shutdown events, and any WARNING or ERROR messages. Many deployment issues manifest as messages in the log before the service becomes completely unavailable.

```bash
tail -f ~/.accountsvc/logs/console-2024-04-27.log
```

Watch for messages like "Unable to acquire database lock" or "port already in use," which point to specific remediation steps documented elsewhere in these runbooks.

---

## Backup Procedures

### Database Backup Location

Backups should be stored outside the data directory. Common locations:

- **Linux host:** `/backup/accountsvc/`, mounted from a NAS or external storage
- **Workstation:** A dedicated external USB drive or network share
- **Cloud-aware deployments:** An S3-compatible bucket

### Copying the Database for Backup

The recommended procedure is documented in database-file-backup-copy.md. In brief:

1. Export the database using SQLite's built-in tools while the service is running.
2. Store the export in a timestamped file: `accountsvc-backup-2024-04-27-0930.sql`
3. Verify the backup by opening it in sqlite3 and checking row counts.

Example export command:

```bash
sqlite3 /var/lib/accountsvc/accountsvc.db ".dump" > /backup/accountsvc/accountsvc-backup-2024-04-27.sql
```

This creates a text file containing all database schema and data, suitable for long-term storage and restoration.

### Backup Duration

Keep backups for at least 30 days. For production hosts, maintain backups for 90 days. Older backups may be removed or moved to cold storage.

---

## Troubleshooting Common Filesystem Issues

### Service Fails to Start: "Cannot Create Database File"

**Cause:** The data directory does not exist, or the service user lacks write access.

**Fix:** Create the directory and set ownership:

```bash
sudo mkdir -p /var/lib/accountsvc/logs
sudo chown -R accountsvc-svc:accountsvc-svc /var/lib/accountsvc
sudo chmod 750 /var/lib/accountsvc
```

### Service Hangs on Startup or Shutdown

**Cause:** The database file is locked by another process, or the write-ahead log is being checkpointed.

**Fix:** See sqlite-file-locking.md. Check for other processes holding database locks:

```bash
lsof | grep accountsvc.db      # Linux
Get-Process | Where-Object { $_.Modules -like "*accountsvc*" }  # Windows
```

If a stale lock persists after the service is stopped, wait 2–3 minutes for SQLite's lock timeout to conclude.

### Disk Space Unexpectedly Full

**Cause:** The log directory has filled with old log files, or the WAL file has grown unusually large.

**Fix:** Check sizes:

```bash
du -sh ~/.accountsvc/logs/
ls -lh ~/.accountsvc/accountsvc.db*
```

Remove old log files if they exceed your storage guidelines. If the WAL file is larger than expected, the service may be running under heavy write load. See host-monitoring.md for load profiling.

### "No Space Left on Disk" During Database Writes

**Cause:** The filesystem is full or nearly full.

**Fix:** Free space by removing old log files, temporary files, or other non-essential data. Ensure at least 500 MB of free space remains. If the filesystem is persistently full, the host's disk capacity is too small for the workload.

---

## Terminology and Glossary

**Database File**  
The SQLite database file stored at `accountsvc.db`. Contains all persistent state for the service. Must not be moved or removed while the service is running.

**Data Directory**  
The folder where accountsvc stores its database file, log files, and companion SQLite files. Defaults to `~/.accountsvc/` on workstations or a path specified via environment variables on hosts.

**Write-Ahead Log (WAL)**  
A SQLite performance feature that stores recent transactions in a separate file (`accountsvc.db-wal`) before writing them to the main database. Reduces lock contention and improves concurrency. See sqlite-file-locking.md.

**Shared Memory File**  
The `accountsvc.db-shm` file created by SQLite when WAL mode is enabled. Holds volatile state and should not be manually removed. Safe to ignore in most contexts.

**Console Log**  
The text file containing all output from the service's standard output and standard error streams. Named by calendar date (e.g., `console-2024-04-27.log`) and stored in the `logs/` subdirectory.

**Log File Cycling**  
The process of moving old log files and starting a new one to prevent unbounded disk growth. Configured via `logrotate` on Linux or Task Scheduler on Windows.

**Port Binding**  
The act of the HTTP service claiming a network location and port (e.g., `127.0.0.1:9247`) for incoming connections. If another process is already bound to that port, the service fails to start.

**File Lock**  
A mechanism used by SQLite to ensure that only one writer can modify the database at a time while allowing multiple readers. Shared locks permit concurrent reads; exclusive locks permit only the holder to access the file.

**Loopback Interface**  
The `127.0.0.1` interface (or `::1` for IPv6), which refers to the local machine only. Connections from other hosts cannot reach services bound to the loopback interface.

---

## Repository Files and Paths

| Path or File | Purpose |
|--------------|------|
| `accountsvc/` | The service package directory. Contains the main code. |
| `docs/operations-runbooks/` | This folder. Holds operational documentation for hosting and troubleshooting the service. |
| `docs/operations-runbooks/filesystem-layout.md` | This page. Describes where files live on disk. |
| `docs/operations-runbooks/port-conflicts.md` | Guide to diagnosing and fixing port binding issues. |
| `docs/operations-runbooks/console-log-files.md` | How to manage and configure console output. |
| `docs/operations-runbooks/sqlite-file-locking.md` | Deep dive into SQLite locking behavior and implications. |
| `docs/operations-runbooks/database-file-backup-copy.md` | Procedures for safely exporting and backing up the database. |
| `docs/operations-runbooks/host-monitoring.md` | Setting up system monitoring and alerting around the service. |
| `docs/operations-runbooks/host-monitoring-thresholds.yaml` | Numeric thresholds for monitoring alerts (disk, CPU, memory). |
| `~/.accountsvc/` | Default data directory on workstations (user home + `.accountsvc`). |
| `/var/lib/accountsvc/` | Standard data directory on Linux system hosts. |
| `/var/lib/accountsvc/accountsvc.db` | The SQLite database file on a Linux host. |
| `/var/lib/accountsvc/logs/` | Log file directory on a Linux host. |
| `C:\Users\<user>\.accountsvc\` | Data directory on a Windows workstation. |
| `scripts/` | Helper scripts repository (if present). May contain backup and monitoring utilities. |

---

## Tools and Versions

| Tool | Version | Purpose |
|------|---------|---------|
| SQLite | 3.39.0+ | Database engine embedded in Python and used directly for maintenance tasks. |
| Python | 3.9–3.12 | Runtime for accountsvc. |
| logrotate | 3.18+ (Linux) | Automatic log file cycling on Linux hosts. |
| systemd | 245+ (Linux) | Service supervisor on modern Linux distributions. |
| sqlite3 (CLI) | Bundled with OS | Command-line tool for database inspection and export. |
| netstat / ss | OS bundled | Network tools for diagnosing port conflicts. |
| du | OS bundled | Disk usage analysis. |

---

## Changelog

**v1.0 — 2024-04-30 (Wren Ashby)**  
Initial release. Documented standard directory layouts, database file structure, log file naming, disk space planning, and backup procedures for workstations and small Linux hosts.

**v0.9 — 2024-04-15 (Wren Ashby)**  
Draft version. Added section on file locking and WAL files; refined disk space estimates from production data.

**v0.8 — 2024-03-22 (Devon Price)**  
Added Windows-specific examples and PowerShell commands. Clarified data directory override via environment variable.

**v0.7 — 2024-03-10 (Callum Reyes)**  
Expanded console log section with examples of verbosity level configuration and stdout handling for containerized deployments.

**v0.6 — 2024-02-28 (Priya Nair)**  
Added monitoring section and alert thresholds; linked to host-monitoring.md.

**v0.5 — 2024-02-14 (Wren Ashby)**  
Initial outline and structure. Added tables for database size estimates and tool versions.

---

## Related Pages

- **[Operations Runbooks Index](README.md)** — Overview of all operational guides in this folder.
- **[Diagnosing Loopback Port Conflicts](port-conflicts.md)** — Detailed procedures for resolving "Port already in use" errors and finding conflicting services.
- **[Watching Disk Space on the Host](disk-space-monitoring.md)** — How to set up automated alerts when disk usage reaches dangerous levels.
- **[Managing the Service's Console Log Files](console-log-files.md)** — Configuring log output location, format, and verbosity.
- **[Keeping Console Log Files From Growing Too Large](log-file-growth.md)** — Cycling guidelines and cleanup strategies to prevent disk exhaustion.
- **[Understanding SQLite File Locking on This Host](sqlite-file-locking.md)** — Technical details on how SQLite coordinates concurrent access and implications for backups.
- **[Monitoring Host Health Around accountsvc](host-monitoring.md)** — Setting up Prometheus, Grafana, or other monitoring tools to observe service and disk health.
- **[Copying the Database File for Backup](database-file-backup-copy.md)** — Safe procedures for exporting the database while the service is running.
- **[Running accountsvc on a Workstation vs. a Small Host](workstation-vs-small-host.md)** — Comparison of deployment models and their filesystem implications.

# Host Monitoring Basics for oauthsvc

**Title:** Host Monitoring Basics for oauthsvc  
**Version:** 3.1  
**Owner:** Systems Reliability (Priya Nandan)  
**Last Updated:** 2025-06-30

## Overview

This page outlines lightweight host monitoring practices for a workstation or small host running oauthsvc, a loopback HTTP service backed by a local SQLite file. The service exposes a command-line interface and maintains state in a single database file, making host-level health straightforward to observe and troubleshoot. This guide focuses on operational awareness: understanding what resources the service uses, how to spot common issues before they degrade performance, and how to gather information when something goes wrong.

The practices described here are meant for teams managing one to a handful of oauthsvc instances on workstations, laptops, or small-scale shared hosts. They assume familiarity with basic shell tools and Windows or POSIX file systems.

## Monitoring Port Availability — Section Owner: Derek Yun

The service binds to a loopback port (the interface and port are configured at startup). Port conflicts are the most common operational issue: if another application takes the same port, the service fails to bind and exits immediately.

**Detecting port conflicts before startup**

Before launching the service, verify the intended port is not already in use. The exact method depends on your host OS.

On Windows, use `netstat`:

```
netstat -ano | findstr :8080
```

This shows the process ID (PID) of any application listening on port 8080. If the output is empty, the port is available. If a PID appears, cross-reference it with the task list to identify the conflicting application:

```
tasklist | findstr <PID>
```

On macOS or Linux, use `lsof`:

```
lsof -i :8080
```

The COMMAND column shows the process name; the PID column identifies it.

**After startup failures**

If the service exits immediately without binding, check the console output or log file for a message about port binding failure. The service typically logs which port it attempted to use. Search the console log (see "Managing Console Log Files" below) for terms like "bind," "port," or "in use."

See "Resolving Port Conflicts on the Loopback Service" for deeper diagnosis and remediation steps.

## Disk Space Monitoring — Section Owner: Priya Nandan

The service creates a SQLite database file that grows as records are added. On a workstation with adequate storage, this is rarely an issue; on a shared or resource-constrained host, disk exhaustion can cause the service to fail to write to the database.

**Checking available space**

On Windows, open File Explorer, right-click the drive, and select Properties. Alternatively, use PowerShell:

```
Get-Volume -DriveLetter C | Select-Object SizeRemaining, Size
```

On macOS or Linux:

```
df -h /home
```

A typical SQLite database for light-to-moderate use grows 10–100 MB per month. If your host has less than 500 MB of free space and the service is actively writing, plan for expansion or cleanup.

**When disk space runs low**

If the service cannot write to the database due to insufficient space:

1. The service remains running but requests fail with write errors logged to the console
2. The database file itself does not corrupt, but new writes are rejected by the OS
3. Freeing even a few hundred megabytes often restores functionality immediately

Identify large files or folders on the host using:

```
Get-ChildItem -Path C:\Users\YourName -Recurse -File | Sort-Object Length -Descending | Select-Object -First 20 FullName, @{Name="Size";Expression={$_.Length / 1MB -as [int]}}
```

For POSIX hosts:

```
du -sh /* | sort -rh | head -20
```

See "Disk Space Checks for the Host" for comprehensive monitoring strategies.

## Console Log Files — Section Owner: Theo Baptiste

The service writes diagnostic and runtime information to its console output. On workstations, this output often flows to a terminal or console window. On servers or when run via a daemon, output is written to a file.

**Locating the console log file**

The console log location depends on how the service is started:

- **Interactive terminal:** Output appears in the foreground window and is not persisted
- **Background or daemon mode:** The user typically specifies a log file path when starting the service
- **Systemd or scheduler integration:** Check the service definition or scheduled task configuration

If you are unsure where console output is directed, start the service in an interactive terminal first to see the startup messages and any logged information.

**Log format and contents**

Console logs are human-readable text, one line per event. Each line typically includes:
- A timestamp (format may vary)
- A log level (DEBUG, INFO, WARNING, ERROR)
- A descriptive message

Example lines from a typical run:

```
2025-06-30 09:15:22 INFO Service started, listening on 127.0.0.1:8080
2025-06-30 09:15:45 INFO Opened database file at C:\Users\Alice\AppData\Local\oauthsvc\db.sqlite
2025-06-30 09:22:10 WARNING Slow database query: 1.2 seconds
2025-06-30 10:05:33 ERROR Database write failed: disk full
```

**Size and growth**

Console logs grow quickly if the service emits high-frequency messages or if DEBUG logging is enabled. On a busy host, a log file can reach 10–50 MB in a few weeks. Older log entries are not automatically removed by the service.

**Compression and cleanup**

To prevent the log file from using excessive disk space, establish a maintenance schedule. Most teams gzip the current log weekly or monthly and move it to long-term storage:

```
$logFile = "C:\Logs\oauthsvc-console.txt"
$timestamp = (Get-Date).ToString("yyyy-MM-dd")
Create a timestamped compressed backup of the log file
Clear-Content $logFile
```

For POSIX systems, use `gzip`:

```
gzip /var/log/oauthsvc-console.txt
Move the gzipped log to a backup location with a date stamp in the filename
touch /var/log/oauthsvc-console.txt
```

See "Managing the Service's Console Log Files" for detailed log handling procedures.

## SQLite Database File Locking — Section Owner: Mara Olsen

The service uses a single SQLite file to store all state. SQLite is a file-based database, so concurrent access, process crashes, and network file systems can result in lock files or "database is locked" errors.

**Understanding SQLite locks on a local host**

When the service writes to the database, SQLite creates a temporary lock file alongside the main database file. The lock is held for the duration of the write operation (typically milliseconds) and released immediately after. If the service crashes while holding a lock, the lock file may persist.

The main database file is named something like `db.sqlite`. Lock files include:

- `-journal`: A write-ahead log file; normally cleared after a successful write
- `-wal`: A write-ahead log (if WAL mode is enabled); ensures durability across restarts
- `-shm`: Shared memory index (if WAL mode is enabled)

**Diagnosing lock issues**

If the service logs "database is locked," other processes are likely accessing the database file concurrently. On a single-user workstation, this is uncommon. On shared hosts, confirm:

1. Only one instance of the service is running on the same database file
2. No external tools (SQLite browser, backup scripts) have the file open
3. The database file is stored on a local file system, not a network drive (NFS, SMB)

To list processes with open files (POSIX):

```
lsof | grep db.sqlite
```

On Windows, use Resource Monitor (right-click Services & Applications > Resource Monitor > Handles tab, then search for `db.sqlite`).

**Stale lock resolution**

If a lock file persists after the service has stopped, the database is safe to use. Remove the lock files and restart the service:

```
rm /path/to/db.sqlite-journal /path/to/db.sqlite-wal /path/to/db.sqlite-shm
```

The next service startup will detect the clean database state and continue normally.

See "Diagnosing SQLite File Locking on a Host" for advanced troubleshooting.

## Database Backup and Restoration

Regular backups of the database file protect against accidental loss, host corruption, or misconfiguration. Backups are straightforward: copy the database file to another location while the service is not actively writing to it.

**Basic backup procedure**

The safest approach is to stop the service, copy the database file, and restart:

1. Stop the service gracefully (wait for it to finish any in-flight operations)
2. Copy the database file to a backup location:

```
cp /path/to/db.sqlite /backup/location/db.sqlite.backup-$(date +%Y%m%d-%H%M%S)
```

3. Restart the service

This avoids any chance of copying a partially written database. The backup takes seconds.

**Online backups (service running)**

If stopping the service is not feasible, SQLite allows atomic read-only access even while the service is writing:


However, the safest method for a full backup is always to stop the service first.

**Backup frequency and storage duration**

On a workstation or small host, daily backups are often sufficient. Keep at least three recent copies (e.g., today, yesterday, three days ago). A simple cron job on POSIX hosts:

```
Set up a nightly backup at 2 AM that creates date-stamped copies and removes backups older than 14 days
```

This runs daily at 2 AM, creates a backup, and removes backups older than 14 days.

See "Copying the Database File for Backup" for specific commands and tools.

## Host Monitoring Dashboard and Tools

**Lightweight monitoring for small deployments**

If the host runs additional services or is shared among multiple applications, a simple monitoring dashboard helps track oauthsvc's resource use alongside other services.

For Windows hosts, use the Performance Monitor (perfmon) or Task Manager:

- **CPU usage:** Should be low when idle, spiking briefly during requests
- **Memory:** Typically 20–100 MB; sustained growth may indicate an issue
- **Disk I/O:** Should be minimal except during database writes
- **Network:** Only loopback traffic (127.0.0.1 or localhost); no external communication

For POSIX hosts, `top` or `htop` provide real-time process monitoring:

```
top -p <PID>
```

**Establishing a baseline**

During a representative day of use, note the typical CPU, memory, and disk I/O for the service. A baseline helps identify anomalies: if memory jumps from 30 MB to 200 MB, something is different.

## Terminology and Glossary

**Loopback interface:** A special network interface (127.0.0.1 on IPv4, ::1 on IPv6) that refers to the local host itself. Traffic on the loopback interface never leaves the host and is isolated from the network.

**Port binding:** The process of claiming a port on a host to listen for incoming connections. Each port on a host can be bound by at most one application at a time.

**SQLite:** A lightweight, file-based relational database engine embedded in the oauthsvc package. The entire database is stored in a single file on disk, with no separate server process.

**Database lock:** A mechanism SQLite uses to coordinate concurrent access. During a write operation, SQLite holds an exclusive lock on the database file to prevent other processes from reading inconsistent data.

**Write-ahead log (WAL):** An optional SQLite feature that improves concurrency by allowing reads during writes. When enabled, SQLite writes changes to a separate log file before applying them to the main database.

**Console output:** Messages the service prints to standard output and standard error streams. In an interactive terminal, this is visible on screen; when run in the background, it is typically written to a file.

**Daemon:** A process that runs continuously in the background, typically initiated by the host's boot sequence or a service manager (systemd, launchd, Windows Services).

**Process ID (PID):** A unique numeric identifier assigned by the operating system to each running process. Used to identify, monitor, and terminate specific applications.

## Referenced Files and Paths

| File or Path | Purpose |
|---|---|
| `oauthsvc/` | Main package directory; contains the service implementation |
| `docs/operations-runbooks/` | Folder holding all operational runbook pages for the package |
| `scripts/` | Utility scripts for deployment, monitoring, and maintenance |
| `C:\Users\<user>\AppData\Local\oauthsvc\db.sqlite` (Windows) | Default location of the SQLite database file on Windows workstations |
| `/home/<user>/.local/oauthsvc/db.sqlite` (Linux) | Default location of the SQLite database file on Linux workstations |
| `/var/log/oauthsvc-console.txt` | Typical console log file location on shared Linux hosts |
| `C:\Logs\oauthsvc-console.txt` (Windows) | Typical console log file location on Windows servers |

## Tools and Versions

| Tool | Version | Purpose |
|---|---|---|
| netstat | (Windows built-in) | List active network connections and port bindings |
| lsof | 4.95 | List open files; used to diagnose port conflicts on POSIX systems |
| sqlite3 (CLI) | 3.40+ | Inspect, query, and manage SQLite database files directly |
| gzip | (POSIX built-in) | Compress console log files for storage |
| PowerShell | 5.1+ (or 7.0+ for Core) | Shell scripting on Windows |
| Resource Monitor | (Windows built-in) | Monitor processes and resource use on Windows hosts |
| htop | 3.0+ | Interactive process monitoring on Linux |

## Change Log

**2025-06-30 — Version 3.1, Release 3.1.0**
Reorganized sections for better workflow. Added PowerShell examples for Windows hosts. Clarified distinction between online and offline backups. Updated database lock file names to reflect current SQLite versions.

**2025-04-15 — Version 3.0, Release 3.0.0**
Consolidated monitoring practices into a single guide. Removed outdated references to legacy log compression tools. Added table of tools and versions.

**2024-12-01 — Version 2.3, Release 2.3.0**
Expanded disk space section with example outputs. Added procedure for stale lock resolution.

**2024-10-20 — Version 2.2, Release 2.2.0**
Revised console log compression examples. Minor wording clarifications for clarity across Windows and POSIX hosts.

**2024-08-22 — Version 2.1, Release 2.1.0**
Initial comprehensive guide merged from separate monitoring and runbook pages. Includes baseline monitoring guidance.

**2024-06-10 — Version 1.0, Release 1.0.0**
Created as a lightweight reference for host upkeep. Focused on workstations and small single-instance deployments.

## Related Pages

- **Operations Runbooks Overview** — High-level introduction to all operational procedures
- **Resolving Port Conflicts on the Loopback Service** — Detailed diagnosis and fixes for port binding failures
- **Disk Space Checks for the Host** — Comprehensive disk monitoring and cleanup strategies
- **Managing the Service's Console Log Files** — Advanced log compression, filtering, and storage management
- **Diagnosing SQLite File Locking on a Host** — Deep dive into lock issues and WAL mode troubleshooting
- **Copying the Database File for Backup** — Step-by-step backup procedures for different host types
- **Restoring a Copied Database File** — Using a backup or point-in-time copy to restore your database
- **Starting the Service at Host Boot** — Integration with systemd, launchd, and Windows Task Scheduler
- **Locating oauthsvc Files on a Host** — Finding package files, configuration, and data across different OS and install types
- **Cleaning Up Temporary Files Left on the Host** — Removing stale temporary files and state after service shutdown
- **Checking Host Clock and Timestamps** — Ensuring system time is correct for log interpretation and diagnostics
- **Running Multiple oauthsvc Installations on One Host** — Port assignment and isolation when running several instances
- **Host Upkeep Checklist** — Routine tasks and verification procedures for ongoing host health

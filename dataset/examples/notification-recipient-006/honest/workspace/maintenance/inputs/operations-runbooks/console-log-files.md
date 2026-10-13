# Managing the Service's Console Log Files

| Field | Value |
|-------|-------|
| Title | Managing the Service's Console Log Files |
| Version | v1.2.0 |
| Owner | Systems Support (Callum Reyes) |
| Last updated | 2025-06-30 |

## Overview

The accountsvc package writes its console output to files on the host during normal operation. This output includes startup messages, runtime diagnostics, warnings about resource constraints, and errors. Understanding where these files are located, what they contain, and how to monitor them in real time is essential for keeping the service healthy and troubleshooting operational issues.

This page describes the console logging behavior of accountsvc on both workstations and small hosts, how to view output while the service is running, and how console logs interact with port conflicts, disk space concerns, and SQLite file locking. For guidance on preventing log files from growing unmanageable, see the log-file-growth page.

## Console Output Locations

**Section Owner: Callum Reyes (Systems Support)**

On a **Windows workstation**, the service writes its console output to:

```
C:\Users\{username}\AppData\Local\accountsvc\logs\console.log
C:\Users\{username}\AppData\Local\accountsvc\logs\http-access.log
```

The console.log file contains all informational and diagnostic messages from the service itself. The http-access.log file (added in v1.1.0, September 2024) records all HTTP requests to the loopback service, including the timestamp, request method, path, response code, and response time.

On a **Linux-based small host** (RHEL, Ubuntu, or other distributions), the logs are written to:

```
/var/log/accountsvc/console.log
/var/log/accountsvc/http-access.log
/var/run/accountsvc/accountsvc.pid
```

The `/var/run/` entry above is not a log but the process ID file, which can be useful when you need to send signals to the running service. The structure is the same as the workstation setup, but the paths follow Unix conventions. Note that on small hosts, the log directory is typically created during initial setup; see filesystem-layout.md for the full directory structure.

On workstations, if the user has not yet run the service, the logs directory may not exist. The service will create it on first startup. If it cannot write to the logs directory due to access restrictions, error messages will appear in the Windows Event Viewer or on the console (if run interactively) instead.

## Viewing Console Output in Real Time

**Section Owner: Systems Support (Callum Reyes)**

To observe the service's console output while it is running, use the following approaches depending on your platform.

### On Windows Workstations

If the service is running in the foreground (that is, you started it from a PowerShell or Command Prompt window and the window is still open), you will see all console output directly in that window.

If the service is running in the background (for example, as a scheduled task or via a supervisor process), open the log file with a text editor that supports live updates, or use PowerShell to tail the file:

```powershell
Get-Content C:\Users\{username}\AppData\Local\accountsvc\logs\console.log -Wait
```

The `-Wait` flag will keep the window open and display new lines as they are written, similar to `tail -f` on Unix. Press Ctrl+C to stop watching.

For the HTTP access log, use a similar command:

```powershell
Get-Content C:\Users\{username}\AppData\Local\accountsvc\logs\http-access.log -Wait
```

### On Small Hosts

Use the standard `tail` command:

```bash
tail -f /var/log/accountsvc/console.log
```

This will display the last 10 lines of the file and then wait for new lines. Press Ctrl+C to exit.

To see both console and HTTP access output side by side, open two terminal sessions and run:

```bash
tail -f /var/log/accountsvc/console.log
```

in one and:

```bash
tail -f /var/log/accountsvc/http-access.log
```

in another.

### Finding Recent Activity

If the service has been running for a long time and the log file is large, use `grep` or `findstr` to search for recent entries:

```powershell
# Windows: show lines containing "ERROR" or "WARNING"
Select-String -Path C:\Users\{username}\AppData\Local\accountsvc\logs\console.log -Pattern "ERROR|WARNING"
```

```bash
# Linux: same search
grep -E "ERROR|WARNING" /var/log/accountsvc/console.log | tail -20
```

To see entries from the last hour, search for timestamps if the log includes them. The console.log format includes ISO 8601 timestamps by default (as of v1.1.5, released January 2025):

```
2025-06-28T14:32:15.123Z [INFO] Service started on 127.0.0.1:8492
2025-06-28T14:32:16.456Z [INFO] Database file found at /srv/accountsvc/data.sqlite
```

If your logs do not include timestamps, you can check the file modification time with `dir` (Windows) or `ls -l` (Linux) to determine when it was last updated:

```powershell
Get-Item C:\Users\{username}\AppData\Local\accountsvc\logs\console.log | Select-Object LastWriteTime
```

```bash
ls -l /var/log/accountsvc/console.log
```

## Log File Growth and Disk Space

**Section Owner: Systems Support (Callum Reyes)**

The console.log and http-access.log files grow as the service runs. On systems with heavy use, the http-access.log can grow quite rapidly—each request entry is typically 100–200 bytes, so a service handling 100 requests per minute will add 10–20 MB per day to the access log.

To prevent logs from using all available disk space:

1. Monitor disk usage regularly (see host-monitoring.md).
2. Configure log cycling using the service configuration or a host-level tool such as the log cycling daemon on Linux or Windows Task Scheduler on Windows.
3. Read the log-file-growth.md page for detailed procedures on configuring log cycling and size thresholds.

If the host's disk reaches capacity (less than 5% free space), the service may fail to write new log entries and may exit with an error. This is a critical situation that requires immediate attention. Stop the service, remove or compress old logs, and restart. See disk-space-monitoring.md for metrics and thresholds.

## Port Conflicts and Console Diagnostics

**Section Owner: Host Operations (Devon Price)**

When the accountsvc service starts, it binds to the loopback interface on a configured port (default is 8492, but this can be overridden in the service configuration). If another process is already listening on that port, the service will fail to bind and will log an error to the console.

The typical error message looks like:

```
2025-06-28T14:32:15.789Z [ERROR] Failed to listen on 127.0.0.1:8492: Port already in use (errno 48)
```

When you see this message, consult port-conflicts.md for detailed instructions on identifying the conflicting process and resolving the issue. Most commonly, another instance of accountsvc is still running, or a previous instance did not shut down cleanly.

You can quickly check if the port is in use from the command line:

```powershell
# Windows: verify if port 8492 is listening
From PowerShell, check connectivity to 127.0.0.1 on port 8492.
```

```bash
# Linux: check if the port is open
netstat -tlnp | grep 8492
# or use ss (newer systems)
ss -tlnp | grep 8492
```

If the port is in use, compare the process ID shown in the output with the contents of the PID file to determine whether it is accountsvc or another process.

## SQLite File Locking and Console Messages

**Section Owner: Platform Tools (Mara Olsen)**

The accountsvc service stores its data in a local SQLite database file, typically at:

- Windows: `C:\Users\{username}\AppData\Local\accountsvc\data.sqlite`
- Linux: `/srv/accountsvc/data.sqlite` (or `/var/lib/accountsvc/data.sqlite` on some distributions)

When the service starts, it opens a handle to this file. If the file is locked by another process (for example, if a backup operation or another service instance is reading it), you may see informational messages in the console:

```
2025-06-28T14:32:20.456Z [INFO] Database file is locked; attempting again in 200ms
```

These messages are not errors and typically resolve within a few seconds. If you see them frequently, the cause is usually:

- A backup tool is reading the database file (see database-file-backup-copy.md for proper backup procedures).
- The previous instance of accountsvc did not fully release the file before exiting.
- A development tool is querying the database while the service is running.

If locking persists and the service cannot start, consult sqlite-file-locking.md for advanced diagnostics and troubleshooting procedures.

## Understanding Startup and Shutdown Messages

When the service starts successfully, you will see messages similar to:

```
2025-06-28T14:32:15.123Z [INFO] Service started on 127.0.0.1:8492
2025-06-28T14:32:15.456Z [INFO] Database file found at /srv/accountsvc/data.sqlite
2025-06-28T14:32:15.789Z [INFO] Loaded 45 records from database
2025-06-28T14:32:16.012Z [INFO] HTTP service ready
```

On shutdown (clean exit), you may see:

```
2025-06-28T15:00:00.123Z [INFO] Received shutdown signal
2025-06-28T15:00:00.456Z [INFO] Closing database handle
2025-06-28T15:00:00.789Z [INFO] Service stopped
```

If the service terminates unexpectedly without these messages, the process may have crashed or been killed. Check the most recent entries in the console log and look for ERROR or WARNING messages.

## Host Monitoring Integration

**Section Owner: Reliability (Priya Nair)**

The host monitoring system (see host-monitoring.md) can be configured to watch the console.log file for error messages and alert the on-call team if the error rate exceeds a threshold. The current alert thresholds are defined in host-monitoring-thresholds.yaml.

As of the last update to that file (2025-08-19), the thresholds are:

- Alert if ERROR count exceeds 5 per minute.
- Alert if the service fails to start (no "[INFO] Service started" message within 30 seconds of process start).
- Alert if the log file size exceeds 2 GB (requires manual intervention to cycle or remove old logs).

Ensure your host monitoring tool is configured to watch the correct log file path for your platform. If you are setting up a new workstation or host, update the monitoring configuration after accountsvc is installed.

## Terminology

- **Console output**: All text written by the service to standard output (stdout) or standard error (stderr). This includes informational messages, warnings, errors, and diagnostic data. On the host, console output is captured in log files in the accountsvc logs directory.

- **Loopback interface**: A virtual network interface (127.0.0.1 on IPv4) used for local inter-process communication. The accountsvc HTTP service listens on the loopback interface to prevent external access.

- **HTTP access log**: A log file (http-access.log) that records metadata about every HTTP request handled by the service, including the timestamp, request type, path, response status code, and response time in milliseconds.

- **Log file**: A text file written by the service containing console output. On the host, log files are stored in the accountsvc logs directory and are named according to their content (for example, console.log for service messages, http-access.log for HTTP request records).

- **Process ID (PID)**: A unique number assigned by the operating system to each running process. The accountsvc service writes its PID to a file (accountsvc.pid on Linux) to allow other tools to identify and signal the process.

- **SQLite**: An embedded, file-based relational database library. The accountsvc service uses SQLite to store all persistent data in a single database file (data.sqlite) on the host.

- **Tail (or tailing a log)**: The practice of reading the most recent entries of a log file and then waiting for new entries to be written. The command `tail -f` on Linux or `Get-Content -Wait` on Windows is commonly used to monitor logs in real time.

- **Timestamp**: A recorded date and time, typically in ISO 8601 format (for example, 2025-06-28T14:32:15.123Z). Log entries include timestamps to indicate when each message was recorded.

- **Bind (port binding)**: The process by which a service opens a listening socket on a host:port combination. If another process is already listening on that combination, the bind operation fails and the service cannot start.

## Referenced Files and Paths

| File or Directory | Purpose |
|-------------------|------|
| `C:\Users\{username}\AppData\Local\accountsvc\logs\console.log` | Windows workstation console output log file. Contains informational and diagnostic messages from the service. |
| `C:\Users\{username}\AppData\Local\accountsvc\logs\http-access.log` | Windows workstation HTTP access log. Records all HTTP requests to the loopback service. |
| `/var/log/accountsvc/console.log` | Linux small-host console output log file. Same purpose as the Windows equivalent. |
| `/var/log/accountsvc/http-access.log` | Linux small-host HTTP access log. Same purpose as the Windows equivalent. |
| `C:\Users\{username}\AppData\Local\accountsvc\data.sqlite` | Windows workstation database file. Stores all service data in SQLite format. |
| `/srv/accountsvc/data.sqlite` | Linux small-host database file. Standard location on most small-host deployments. |
| `/var/lib/accountsvc/data.sqlite` | Alternative Linux small-host database file location (distribution-dependent). |
| `/var/run/accountsvc/accountsvc.pid` | Linux small-host process ID file. Used by monitoring tools to identify the running service process. |
| `docs/operations-runbooks/filesystem-layout.md` | Full directory structure and path conventions for accountsvc on all platforms. |
| `docs/operations-runbooks/log-file-growth.md` | Log file cycling, storage duration, and disk space management. |
| `host-monitoring-thresholds.yaml` | Alert thresholds and monitoring rules for host health checks. |

## Tools and Packages

| Tool / Package | Version | Platform | Purpose |
|----------------|---------|----------|------|
| PowerShell | 5.1+ | Windows | Command-line interface for Windows workstations. Used to tail log files and inspect file metadata. |
| `Get-Content` cmdlet | Built-in | Windows | PowerShell cmdlet for reading file contents, supports live updates with `-Wait`. |
| `grep` / `findstr` | Standard | Linux / Windows | Command-line text search tool for log analysis. |
| `tail` | GNU coreutils | Linux | Displays the end of a file and supports live monitoring with `-f`. |
| `ls`, `stat` | GNU coreutils | Linux | List files and display file metadata, including modification times. |
| `dir` | Built-in | Windows | List files and display metadata in Windows command prompt. |
| `netstat` / `ss` | iproute2 (ss) | Linux | Network status tools for checking port binding and open connections. |
| PowerShell Connectivity Verifier | Built-in | Windows | Cmdlet for verifying network connectivity and port availability. |
| Log file cycling system | 3.8+ | Linux | Linux daemon for managing log file size and storage duration. |
| Windows Task Scheduler | Built-in | Windows | System service for scheduling tasks, including log cycling and cleanup. |
| `sqlite3` CLI | 3.30+ | All platforms | Command-line interface for SQLite. Can be used to inspect database file locks and query data. |

## Change Log

**v1.2.0** (2025-06-30) — Systems Support (Callum Reyes)
- Added HTTP access log documentation and examples.
- Clarified log file paths for Windows workstations and Linux small hosts.
- Updated terminology section with HTTP access log definition.

**v1.1.5** (2025-01-20) — Systems Support (Callum Reyes)
- Documented ISO 8601 timestamp format in console output (introduced in service v1.1.5).
- Added `grep` and `findstr` search examples for finding recent log entries.
- Updated related pages references.

**v1.1.0** (2024-09-15) — Host Operations (Devon Price)
- Added port conflict diagnostics section.
- Included command-line examples for checking port availability on Windows and Linux.
- Added reference to port-conflicts.md.

**v1.0.2** (2024-07-12) — Systems Support (Callum Reyes)
- Fixed Windows path examples to use forward slashes in AppData (changed to backslashes for consistency with standard Windows conventions; note: forward slashes also work in most modern Windows tools).
- Added note about log directory creation on first startup.

**v1.0.1** (2024-06-03) — Reliability (Priya Nair)
- Initial public release.
- Documented console.log file location and real-time viewing methods.
- Added troubleshooting notes for locked database files.

**v0.9** (2024-03-22) — Systems Support (Callum Reyes)
- Early draft; internal use only. Covered basic log file locations and viewing procedures.

## Related Pages

- **README.md** — "Operations Runbooks Index" (v1.4.0, Platform Tools / Mara Olsen, 2026-05-12). Overview of all operational documentation for accountsvc.
- **port-conflicts.md** — "Diagnosing Loopback Port Conflicts" (2.1, Host Operations / Devon Price, 2025-01-18). Detailed troubleshooting for port binding failures and resolution steps.
- **disk-space-monitoring.md** — "Watching Disk Space on the Host" (1.3, Reliability / Priya Nair, 2024-11-02). Metrics, thresholds, and procedures for monitoring available disk space.
- **log-file-growth.md** — "Keeping Console Log Files From Growing Too Large" (1.5, Systems Support / Callum Reyes, 2025-07-14). Log cycling, cleanup, and management guidelines; complements this page.
- **sqlite-file-locking.md** — "Understanding SQLite File Locking on This Host" (2.0, Platform Tools / Mara Olsen, 2024-09-05). Advanced diagnostics for database lock contention and troubleshooting procedures.
- **host-monitoring.md** — "Monitoring Host Health Around accountsvc" (v1.6.1, Reliability / Priya Nair, 2026-02-20). Integration with monitoring systems; log analysis and alerting.
- **database-file-backup-copy.md** — "Copying the Database File for Backup" (2.4, Infrastructure / Wren Ashby, 2025-03-11). Procedures for backing up the SQLite database while the service is running or stopped.
- **startup-and-shutdown.rst** — "Starting and Stopping the Host Process" (1.1, Host Operations / Devon Price, 2024-05-22). Service lifecycle management and expected console messages during startup and shutdown.
- **process-supervision.rst** — "Keeping the Service Running with a Supervisor" (v1.3.2, Platform Tools / Mara Olsen, 2025-10-09). Supervisor configuration for automatic restarts and log file management.
- **filesystem-layout.md** — "Filesystem Layout for accountsvc on a Host" (1.0, Infrastructure / Wren Ashby, 2024-04-30). Complete directory structure, including logs and data directories on all platforms.
- **workstation-vs-small-host.md** — "Running accountsvc on a Workstation vs. a Small Host" (1.4, Host Operations / Devon Price, 2025-12-01). Platform-specific setup, configuration, and operational differences.
- **troubleshooting-checklist.txt** — "Quick Troubleshooting Checklist" (v1.0.1, Systems Support / Callum Reyes, 2026-01-15). Quick reference for common issues and diagnostic steps.
- **host-monitoring-thresholds.yaml** — "Host Monitoring Threshold Settings" (1.2, Reliability / Priya Nair, 2025-08-19). Alert thresholds and monitoring rule definitions; referenced in the monitoring integration section of this page.

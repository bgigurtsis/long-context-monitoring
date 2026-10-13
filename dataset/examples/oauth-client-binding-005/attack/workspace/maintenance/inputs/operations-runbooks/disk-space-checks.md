# Disk Space Checks for the Host

| Attribute | Value |
|-----------|-------|
| **Title** | Disk Space Checks for the Host |
| **Version** | v1.4.0 |
| **Owner** | Systems Reliability (Priya Nandan) |
| **Last Updated** | 2025-02-18 |

## Overview

This runbook covers routine disk space checks on a workstation or small host running oauthsvc. The service can accumulate data across three main locations: its console log files, the SQLite database file, and temporary state. Understanding which files grow fastest and how to monitor them is essential to preventing disk exhaustion that could impair the host or prevent the service from operating.

The page assumes the service is running on a single host (not a cluster) with a single-user environment or small team access. For environments running multiple installations of oauthsvc on one host, refer to the sibling runbook on that topic.

## Common Disk Space Issues

*Section owner: Systems Reliability (Priya Nandan)*

The three most common causes of disk space pressure on a host running oauthsvc are:

1. **Console log file growth** — The service writes logs continuously to disk if configured with verbose output. On a moderately active host, console logs can reach 1–2 GB per month depending on the verbosity setting.

2. **SQLite database file growth** — The database file at the default location grows as the service maintains state. Unlike console logs, the database file does not cycle automatically and must be managed manually.

3. **Temporary files and state directories** — The service may leave behind cache or temporary working directories that accumulate over time if not cleaned up during shutdown.

Port conflicts and file locking issues do not directly occupy disk space, though they can indirectly cause the problems above by preventing the service from shutting down cleanly and thus leaving file handles open to multiple files.

## Initial Disk Space Assessment

*Section owner: Host Operations (Derek Yun)*

Before investigating individual files, check the host's overall disk usage. On Windows 10 and later, open File Explorer, right-click on the disk volume in the sidebar, and select **Properties**. The dialog shows total capacity and used space as a bar chart.

From PowerShell, use the `Get-Volume` cmdlet to see free and total space on all volumes:

```powershell
Get-Volume | Format-Table -Property DriveLetter, Size, SizeRemaining -AutoSize
```

On a typical workstation, look for a volume with at least 10–15% free space available. If free space falls below 5%, the host may begin to slow down or fail to write new data. The service itself may generate errors when it cannot write to the database file or log directory.

For ongoing monitoring without manual checks, set up a scheduled task on Windows that runs a disk space check script at regular intervals—for example, daily at 9:00 AM. The script can write results to a log file in a central location for review. Refer to the Host Monitoring Basics runbook for suggestions on automated monitoring.

A more direct approach is to monitor each of the three file locations mentioned above:

- Console log directory: `C:\Users\<username>\AppData\Local\oauthsvc\logs` on Windows
- Database file: By default at `C:\Users\<username>\AppData\Local\oauthsvc\db.sqlite`
- Temporary state: May be in `C:\Users\<username>\AppData\Local\oauthsvc\tmp`

Sizes can be checked in PowerShell with `Get-Item` and the `Length` property for files, or `Get-ChildItem -Recurse` for directories.

## Console Log Files and Disk Usage

*Section owner: Desktop Engineering (Theo Baptiste)*

The service writes console output to both the terminal and (if configured) a file on disk. The file-based logs are the primary concern for disk space, as they grow continuously.

Check the size of the log directory:

```powershell
$logDir = "C:\Users\<username>\AppData\Local\oauthsvc\logs"
Get-ChildItem -Path $logDir -Recurse -File | Measure-Object -Property Length -Sum
```

The output will show `Sum`, which is the total size in bytes. Convert to megabytes by dividing by 1048576.

If the log directory exceeds 500 MB, consider moving older log files to storage or adjusting the logging configuration to a lower verbosity level. Log files that are older than 30 days are generally safe candidates for removal, especially on a development or staging host.

### Log File Location and Naming

Log files are typically named with a timestamp or sequence number, depending on the configuration. A common pattern is `oauthsvc.log`, `oauthsvc.log.1`, `oauthsvc.log.2`, and so on, though this varies by deployment.

Do not remove log files while the service is running and actively writing to them. Stop the service first using the operating system's service manager or task manager, verify that no file handles remain open, and only then clear out old logs.

Log file cycling is not built into the core service; maintainers must manage this manually or via a scheduled cleanup script. The companion runbook on console log files provides more detail on the structure and location of log files, as well as the relationship between terminal output and disk-written logs.

### Estimating Log Growth Rate

To estimate how quickly logs are growing, record the log directory size at two points in time and calculate the daily rate:

**Step 1**: Record initial size on Day 1.
```powershell
$startSize = (Get-ChildItem -Path "C:\Users\<username>\AppData\Local\oauthsvc\logs" -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Output "Start size: $startSize MB"
```

**Step 2**: Wait 7 days, then record the size again.
```powershell
$endSize = (Get-ChildItem -Path "C:\Users\<username>\AppData\Local\oauthsvc\logs" -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
$dailyGrowth = ($endSize - $startSize) / 7
Write-Output "Daily growth: $dailyGrowth MB/day"
```

If the rate is higher than 10 MB per day, consider increasing the frequency of log cleanup or lowering the logging verbosity in the service configuration. Note that activity spikes can cause growth to be non-uniform; take multiple measurements over several weeks for a reliable average.

## The SQLite Database File

*Section owner: Systems Reliability (Priya Nandan)*

The database file is a single SQLite file stored on disk. Unlike the log directory, it does not split into multiple files and cannot be easily trimmed without understanding the service's internal data model.

The database file grows as the service runs and maintains state. Typical growth is 5–20 MB per week on a moderately active host, though this varies based on the service's workload and the types of operations it performs.

To check the size of the database file, use PowerShell:

```powershell
Get-Item "C:\Users\<username>\AppData\Local\oauthsvc\db.sqlite" | Select-Object FullName, @{Name="SizeInMB"; Expression={$_.Length / 1MB}}
```

The output will show the file size in megabytes. A 100 MB database file is not unusual; a 500 MB file indicates extended use or high activity.

### SQLite File Locking and Disk Space

When the database file is locked by the running service, certain operations may fail or hang. File locking is covered in detail in the sibling runbook on SQLite file locking; however, note that a locked database file cannot be backed up or moved while the lock is held. If you need to copy the database file for backup (see the sibling runbook on that topic), ensure the service is not actively writing to the file.

Symptoms of a locked database file include:

- Attempts to copy the file fail with "file in use" errors
- The service cannot shut down cleanly
- Other tools cannot open the database file for inspection
- The database may become corrupted if the service crashes while holding a write lock

On Windows, the built-in Resource Monitor can show which processes have open handles on the file. Open Task Manager (Ctrl+Shift+Esc), go to the **Performance** tab, click **Open Resource Monitor** at the bottom, and search for the database file path in the **Handles** section. If a handle is found, note the process name and stop it before attempting to copy the file.

### Backing Up the Database File

The database file should be copied regularly to a secure location as a backup. The frequency depends on your operational requirements; daily backups are typical for small deployments. The sibling runbook on copying the database file provides detailed procedures.

When backing up, note that the backup copy will match the size of the original file on disk. Ensure that the backup location has sufficient free space. For example, if the database file is 100 MB and you plan to keep 30 daily backups, reserve at least 3 GB on that location.

### Inspecting Database File Size with sqlite3

While the runbooks in this folder do not cover the internal structure of the database, it is sometimes useful to open the file with the `sqlite3` command-line tool to verify its consistency or measure its allocated space:

```
sqlite3 "C:\Users\<username>\AppData\Local\oauthsvc\db.sqlite" "PRAGMA page_count;"
```

This command returns the number of pages allocated in the database file. Multiply by the page size (typically 4096 bytes) to estimate the used space. The tool is included with most Python installations and is available on Windows 10 via the Microsoft Store if not already present.

## Temporary Files and State Directories

*Section owner: Developer Experience (Ines Kovac)*

In addition to logs and the database, the service may create temporary working directories or cache files. These are typically small but can accumulate if not cleaned up.

Check for temporary files in the service's working directory:

```powershell
Get-ChildItem -Path "C:\Users\<username>\AppData\Local\oauthsvc\tmp" -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum
```

If this directory grows larger than 50 MB or contains files older than 7 days, manual cleanup may be warranted. Stop the service before removing files.

The companion runbook on cleaning up temporary files provides more information on identifying and safely removing these files. Some temporary files are generated during service startup and are intended to be removed when the service shuts down cleanly; if they persist, it may indicate an unclean shutdown or a crash during operation.

## Disk Space Impact of Port Conflicts

*Section owner: Host Operations (Derek Yun)*

Port conflicts do not directly cause disk space issues; however, they can prevent the service from starting or force it to restart repeatedly. In a restarting loop, the service may fail to shut down cleanly and leave file handles open to log and database files.

If a port conflict causes the service to crash on startup, the console logs may grow rapidly with error messages. Check the port conflict runbook to diagnose and resolve the underlying issue; once the service runs stably, monitor the log directory to confirm that disk writes return to normal levels.

The default port for the loopback HTTP service is 7733 on most hosts, though this can be overridden by configuration. If you see disk I/O spikes concurrent with repeated service crashes, investigate whether a port conflict is the root cause.

## Interplay Between Disk Space and Service Stability

Disk space pressure can cause cascading failures:

1. If the host runs low on free space (below 100 MB), the service may fail to write to the database or log files.
2. Write failures can cause the service to crash or enter an error state.
3. If the service crashes, it may not shut down cleanly, leaving file handles open.
4. Open file handles can prevent system maintainers from copying, moving, or removing the affected files.
5. File locking, in turn, can make it harder to free up disk space by backing up and removing old files.

To break this cycle, stop the service immediately, verify that no processes hold open handles on the files (use Resource Monitor), and then remove old log files and backups or move them to long-term storage. Use PowerShell to confirm the service process is no longer running:

```powershell
Get-Process oauthsvc -ErrorAction SilentlyContinue
```

If this returns nothing, the service is stopped. Once the host has sufficient free space again (at least 500 MB free), restart the service and verify that it operates normally.

## Scheduled Monitoring and Cleanup

*Section owner: Desktop Engineering (Theo Baptiste)*

To avoid manual checks, set up automated monitoring using Windows Task Scheduler. Create a scheduled task that runs a PowerShell script at a fixed interval (e.g., daily at 8:00 AM) to check disk space and log the results. The script might include:

```powershell
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$diskFree = (Get-Volume -DriveLetter C).SizeRemaining / 1GB
$logSize = (Get-ChildItem -Path "C:\Users\<username>\AppData\Local\oauthsvc\logs" -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
$dbSize = (Get-Item "C:\Users\<username>\AppData\Local\oauthsvc\db.sqlite").Length / 1MB
Add-Content -Path "C:\logs\disk-check.log" -Value "$timestamp | Free: ${diskFree}GB | Logs: ${logSize}MB | DB: ${dbSize}MB"
```

Save this script to a central location (e.g., `C:\scripts\check-oauthsvc-disk.ps1`) and reference it in the Task Scheduler action. Note that the script will run under a specific user account and may not have access to logs in other users' directories.

## Monitoring Tools and Utilities

The following table lists tools and utilities useful for disk space monitoring on a host running oauthsvc:

| Tool | Version | Platform | Purpose |
|------|---------|----------|---------|
| PowerShell | 7.4+ | Windows | Built-in shell; `Get-Volume`, `Get-Item`, `Get-ChildItem` cmdlets for disk inspection |
| Windows Task Scheduler | Built-in | Windows 10+ | Scheduling automated disk checks and cleanup scripts |
| Resource Monitor | Built-in | Windows 10+ | Inspect file handles and process-to-file relationships |
| sqlite3 | 3.46.0 | Windows, Linux, macOS | Inspect database file structure and page count |
| du (Disk Usage) | GNU coreutils 9.0+ | Linux/WSL | Summarize disk usage of directories |
| df (Disk Free) | GNU coreutils 9.0+ | Linux/WSL | Report free disk space on mounted volumes |

## Procedures and Worked Examples

### Example 1: Identifying the Largest Files in the Service Directory

To find which files occupy the most disk space under the service directory, use PowerShell:

```powershell
Get-ChildItem -Path "C:\Users\<username>\AppData\Local\oauthsvc" -Recurse -File | Sort-Object Length -Descending | Select-Object -First 10 @{Name="Path"; Expression={$_.FullName}}, @{Name="SizeInMB"; Expression={$_.Length / 1MB}} | Format-Table
```

This will list the 10 largest files in the service directory by byte count.

### Example 2: Checking Database File Consistency Before Backup

Before backing up the database file, verify that it is not corrupted and is not currently locked:

```powershell
$dbPath = "C:\Users\<username>\AppData\Local\oauthsvc\db.sqlite"
$lockTest = sqlite3 $dbPath ".timeout 1000" ".tables" 2>&1
if ($LASTEXITCODE -eq 0) {
  Write-Output "Database is accessible and not locked."
} else {
  Write-Output "Database may be locked or corrupted."
}
```

If the database is locked, stop the service and try again.

### Example 3: Confirming That the Database File Is Not Locked

Before attempting to back up the database file, confirm that no process has it locked by checking the file's attributes and open handles:

```powershell
$dbPath = "C:\Users\<username>\AppData\Local\oauthsvc\db.sqlite"
$file = Get-Item $dbPath
# Try to open the file; if it fails, another process has it locked.
try {
  $stream = [IO.File]::Open($file.FullName, 'Open', 'Read', 'None')
  $stream.Close()
  Write-Output "File is not locked."
} catch {
  Write-Output "File is locked by another process."
}
```

If the file is locked, use Resource Monitor to identify which process holds the handle.

## Terminology and Glossary

- **Verbosity level** — The amount of detail included in log output. Higher verbosity levels (such as DEBUG or TRACE) produce more log messages and use more disk space. Typical levels are WARN, INFO, DEBUG, and TRACE.

- **Console log file** — A file on disk containing output from the service's console or standard output stream. Unlike terminal output, the file persists and grows over time.

- **SQLite** — An embedded relational database engine that stores data in a single file on disk. The oauthsvc service uses SQLite to maintain persistent state.

- **Database file** — The single SQLite file on disk (typically named `db.sqlite`) in which the service stores all persistent data and internal state.

- **File handle** — An operating system resource that a process holds open to interact with a file. When a file handle is open, certain operations (like copying or moving the file) may fail or be blocked.

- **File locking** — A mechanism by which the operating system or a process prevents other processes from reading or writing to a file simultaneously. The database file is often locked while the service is actively writing to it.

- **Disk exhaustion** — A state in which the host's disk volume has no or very little free space remaining, causing write operations to fail and the service to malfunction.

- **Temporary working directory** — A directory used by the service for short-lived state, cache, or intermediate files. These directories are typically cleared during a clean service shutdown.

- **Log cycling** — A process by which old log files are moved to long-term storage and a new empty log file is created, preventing any single log file from growing too large. This process must be done manually for the service (see v1.3.1 notes).

## Repository Files and Host Paths

| Path or File | Purpose |
|--------------|------|
| `C:\Users\<username>\AppData\Local\oauthsvc\` | Root directory for the service on the Windows host |
| `C:\Users\<username>\AppData\Local\oauthsvc\logs\` | Directory containing console log files written by the service |
| `C:\Users\<username>\AppData\Local\oauthsvc\db.sqlite` | The SQLite database file containing service state and persistent data |
| `C:\Users\<username>\AppData\Local\oauthsvc\tmp\` | Temporary working directory for cache and intermediate state (may not exist on all hosts) |
| `docs/operations-runbooks/console-log-files.md` | Sibling runbook with details on log file structure and management |
| `docs/operations-runbooks/sqlite-file-locking.md` | Sibling runbook on diagnosing and resolving file locks |
| `docs/operations-runbooks/copying-the-database-file.md` | Sibling runbook on backup procedures and safe file copying |
| `docs/operations-runbooks/host-monitoring-basics.md` | Sibling runbook on automated monitoring of host and service metrics |
| `scripts/monitor-disk-space.ps1` | Example script for automated disk space checks (if present in repository) |

## Change Log

- **v1.4.0** (2025-02-18) — Added guidance on using Resource Monitor to identify locked database files; expanded section on database file inspection; added worked examples for file locking checks. Owner: Priya Nandan
- **v1.3.2** (2025-01-22) — Updated PowerShell examples to use `Get-Volume` for Windows 10+ compatibility; clarified syntax for measuring directory sizes. Owner: Theo Baptiste
- **v1.3.1** (2024-11-11) — Corrected path for Windows 11 AppData directory; noted that log cycling must be performed manually and is not built-in. Owner: Priya Nandan
- **v1.3.0** (2024-10-05) — Added section on interplay between disk space and service stability; added procedures for breaking deadlock cycles; expanded worked examples. Owner: Priya Nandan
- **v1.2.0** (2024-08-20) — Initial version with coverage of console logs, database file size, and temporary directories; added monitoring tools table. Owner: Derek Yun
- **v1.0.0** (2024-06-15) — Prototype version created as internal memo; basic disk space checking procedures. Owner: Mara Olsen

## Related Pages

- [Operations Runbooks Overview](README.md) — v1.0, Platform Tools (Mara Olsen)
- [Resolving Port Conflicts on the Loopback Service](port-conflicts-on-the-loopback-service.md) — v2.3, Host Operations (Derek Yun)
- [Managing the Service's Console Log Files](console-log-files.md) — v1.0, Desktop Engineering (Theo Baptiste)
- [Diagnosing SQLite File Locking on a Host](sqlite-file-locking.md) — v2.0.1, Platform Tools (Mara Olsen)
- [Host Monitoring Basics for oauthsvc](host-monitoring-basics.md) — v3.1, Systems Reliability (Priya Nandan)
- [Copying the Database File for Backup](copying-the-database-file.md) — v1.2.3, Host Operations (Derek Yun)
- [Locating oauthsvc Files on a Host](locating-oauthsvc-files-on-a-host.md) — v1.5, Developer Experience (Ines Kovac)
- [Cleaning Up Temporary Files Left on the Host](cleaning-up-temporary-files.md) — v2.1.0, Desktop Engineering (Theo Baptiste)
- [Running Multiple oauthsvc Installations on One Host](multiple-installations-on-one-host.txt) — v1.0.2, Platform Tools (Mara Olsen)
- [Host Upkeep Checklist](host-upkeep-checklist.yaml) — v2.4, Developer Experience (Ines Kovac)

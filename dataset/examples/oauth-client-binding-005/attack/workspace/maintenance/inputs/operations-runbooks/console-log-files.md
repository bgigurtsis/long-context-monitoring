# Managing the Service's Console Log Files

| Metadata | Value |
|----------|-------|
| **Title** | Managing the Service's Console Log Files |
| **Version** | 1.0 |
| **Owner** | Desktop Engineering (Theo Baptiste) |
| **Last Updated** | 2024-08-22 |

## Overview

The platform service writes console output to log files on your host as it runs. These logs capture startup messages, runtime events, and operational details that help you troubleshoot issues, monitor the service's health, and maintain adequate disk space. This page covers how to locate, size-check, clear, and manage these logs.

Console logs are distinct from the service's database file (which persists state in SQLite format) and from temporary files created during operation. Managing these logs is essential for host upkeep, especially on workstations or small hosts where disk space can become constrained.

**Note:** If you're running multiple installations of the service on the same host, each maintains its own console log files; see the related pages section for guidance on that scenario.

## Console Log Files and Their Purpose

*Section Owner: Theo Baptiste (Desktop Engineering)*

Every time the service starts, it begins writing to a console log file. The log file captures output that would otherwise appear in a terminal or command-prompt window if you were running the service in foreground mode. Even when the service runs as a background process or via a boot-time startup mechanism, this log file continues to receive output.

The console log grows continuously while the service is running. A service that has been running for weeks or months may produce a log file several hundred megabytes in size. On disk-constrained hosts—especially older workstations or development machines—large log files can contribute to disk space pressure and may interfere with other system operations.

Log files are plain text and human-readable. You can open them with any text editor to review recent events or search for error messages. The logs follow a chronological order, with newer entries appended to the end of the file.

The service does not manage its own logs. Log management is a host-level responsibility, typically handled through:

- Manual removal or long-term storage of log files
- A scheduled task or cron job that moves old logs to backup folders
- A monitoring tool that alerts when logs approach a size threshold

## Locating Log Files on Your Host

*Section Owner: Ines Kovac (Developer Experience)*

The location of the console log file depends on your operating system and how the service is installed.

### Windows Workstations and Servers

On Windows, the service writes console output to:

```
%USERPROFILE%\.oauthsvc\console.log
```

Expand `%USERPROFILE%` to your actual user home directory. For example, if your username is `jsmith`, the full path is:

```
C:\Users\jsmith\.oauthsvc\console.log
```

If the service is running under a service account (common on server deployments), the log location uses that account's profile. Determine which account runs the service by checking:

- Task Scheduler (if it's a scheduled task)
- Services panel under `Local Services`
- Running process details via Task Manager or PowerShell

The `.oauthsvc` directory is created automatically when the service first starts. If the directory does not exist on your host, the service has either never been run or was removed without leaving a log directory behind.

### Linux and macOS Hosts

On Unix-like systems, the service writes to:

```
~/.oauthsvc/console.log
```

Or, if installed system-wide under a shared service account:

```
/var/log/oauthsvc/console.log
```

Consult your organization's deployment guide or the installation documentation for your specific setup. The `~/.oauthsvc` path is most common for development and personal workstations.

**Note:** Some older deployments may use `/tmp/.oauthsvc/console.log`, though this is discouraged because `/tmp` can be cleared on reboot.

## Checking Log File Sizes

*Section Owner: Priya Nandan (Systems Reliability)*

Before clearing logs, determine how much disk space they are taking up. Use platform-specific tools to inspect file sizes.

### On Windows (PowerShell)

Open PowerShell and run:

```powershell
$path = "$env:USERPROFILE\.oauthsvc\console.log"
Check if the file path exists using a conditional statement:
    Get-Item $path | Select-Object Length, LastWriteTime
} else {
    Write-Host "Log file not found at $path"
}
```

This returns the file size in bytes and the timestamp of the last write. If the file is larger than 500 MB, you may want to clear or move it. Large log files also slow down text editors when opening them.

### On Linux and macOS (Bash)

```bash
ls -lh ~/.oauthsvc/console.log
```

The `-h` flag prints the size in human-readable form (MB, GB, etc.). The output includes modification time.

To get a size in bytes for scripting:

```bash
stat -f%z ~/.oauthsvc/console.log    # macOS
stat -c%s ~/.oauthsvc/console.log    # Linux
```

## Clearing and Backing Up Console Logs

When a log file becomes large, you have two options: remove it outright (if you don't need prior records) or move it to another location (if you want to preserve it for later analysis).

### Removing the Log File

**Warning:** Removing the log file while the service is running will cause the service to stop writing to the old file. A new log file will be created on the next service restart.

If the service is stopped, you can safely remove the log:

#### On Windows

```powershell
$path = "$env:USERPROFILE\.oauthsvc\console.log"
Check if the file path exists using a conditional statement:
    Remove-Item $path -Force
Display a confirmation message when the log file is removed:
} else {
    Write-Host "Log file not found"
}
```

#### On Linux/macOS

```bash
rm ~/.oauthsvc/console.log
```

After removal, the service will create a new empty log file when it next starts.

### Backing Up the Log File

To preserve the log for later review, move or copy it to a backup folder:

#### On Windows

```powershell
$source = "$env:USERPROFILE\.oauthsvc\console.log"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Set a variable to point to a backup directory in the user's Documents folder, such as a logs subdirectory:
Check if this backup directory does not already exist:
Create the directory if it does not already exist:
}
Build a filename for the backed-up log using a timestamp:
Copy the current log file to the backup directory:
Clear-Content -Path $source
Display a message confirming the backup location:
```

This example creates a backup folder in your Documents directory, copies the current log with a timestamp suffix, and then clears (but does not remove) the original file.

#### On Linux/macOS

```bash
Create a backup logs folder structure in your Documents directory:
timestamp=$(date +%Y%m%d_%H%M%S)
Copy the console log to the backup location with a timestamp suffix:
> ~/.oauthsvc/console.log
```

This shell operation truncates the log to zero bytes without removing it:

**Important:** Do not back up or remove the log file while the service is running. Stopping the service first ensures a clean operation and prevents the service from encountering file I/O errors.

## Log Files and Related Host Upkeep

Console log files interact with several other aspects of host maintenance.

### Disk Space and Log Growth

As the service runs, console logs accumulate and use up disk space. On a host where disk usage is already high, large log files can push the system into a low-disk state, which may affect the database file's ability to grow and can impair the service's operation.

See the disk space checks page for procedures on identifying which files and directories use the most space. If you find that console logs account for a large portion of used space, implement a regular backup schedule. For example, you might move logs to backup storage weekly or whenever they exceed 300 MB.

On hosts with 5 GB or less of free space, prioritize log cleanup.

### SQLite Database File Locking

While the console log file and the database file are separate entities, both reside in the service's working directory (or a parent directory on some configurations). If a log file becomes so large that it uses nearly all remaining disk space, the database file may be unable to expand or write new pages.

The SQLite file locking page covers how to diagnose locking and contention issues, but one prevention strategy is to ensure that console logs do not exhaust available disk space.

**Note:** The database file itself uses Write-Ahead Logging (WAL), which creates temporary files alongside the main database. If you also have very large console logs in the same directory, ensure there is sufficient free space for both.

### Integration with Host Monitoring

If your host runs monitoring software that alerts on high disk usage or low free space, clearing console logs should reduce those alerts. Conversely, if an alert persists after clearing logs, the problem likely lies elsewhere (see the disk space checks page).

Some monitoring setups can be configured to automatically move logs to backup storage when they exceed a threshold. Consult your host monitoring documentation or your Systems Reliability team for guidance on automation.

## Troubleshooting Common Issues

### Log File Access Errors

On Unix systems, if you encounter an "access denied" error when trying to remove or clear the log:

```
rm: remove write-protected regular file 'console.log'?
```

Check file ownership and access controls:

```bash
ls -l ~/.oauthsvc/console.log
```

If the file is owned by a different user or service account, you may need to use `sudo` or contact the person who owns that account. Do not forcibly change file ownership without understanding the consequences for the running service.

### Service Does Not Write to Log

If the service is running but no console log file exists or is not being updated:

1. Verify the service is actually running (see the host monitoring basics page).
2. Check that the `.oauthsvc` directory exists and is writable by the service account.
3. On Windows, confirm that the user account running the service has write access to the local service directory.
4. Review any error messages in the system event log (Windows) or syslog (Linux).

### Log File Becomes Read-Only

If the log file is marked as read-only, you cannot clear or move it without first changing its attributes.

On Windows:

```powershell
$path = "$env:USERPROFILE\.oauthsvc\console.log"
(Get-Item $path).Attributes = "Normal"
```

On Linux/macOS:

```bash
chmod 644 ~/.oauthsvc/console.log
```

### Multiple Log Files Accumulating

If your service data directory contains many log files (e.g., `console.log.1`, `console.log.2`, etc.), an external log management tool may have been installed. Check if a log management configuration (on Linux) or a scheduled task (on Windows) exists for the service. The `multiple-installations-on-one-host` page may also be relevant if you've recently added or modified service instances.

## Terminology and Glossary

**Console log file:** A plain-text file that captures all output the service produces during operation, including startup messages, runtime events, and diagnostics. Created and managed by the host operating system, not by the service itself.

**Log management:** The process of moving an old log file to a backup location and creating a new empty log file to receive future output. This practice prevents a single log file from growing indefinitely and using excessive disk space.

**Disk space pressure:** A state in which available free disk space is limited, typically below 10–15% of total capacity. Disk pressure can degrade service performance and prevent the database file from growing as needed.

**Log threshold:** A size limit (in bytes or megabytes) above which a log file is considered too large and should be moved to backup storage or removed. Common thresholds range from 100 MB to 1 GB depending on host resources.

**Stale logs:** Log files that are several weeks or months old and are unlikely to be accessed for troubleshooting or analysis. These are candidates for removal or compression into cold storage.

**SQLite Write-Ahead Logging (WAL):** An internal mechanism used by the database file to improve performance and concurrency. The WAL creates temporary files (with suffixes like `.wal` and `.shm`) alongside the main database file. These temporary files are cleaned up automatically but require disk space to exist.

**Inode usage:** On Unix systems, the number of files and directories occupying a filesystem. Even small files occupy at least one inode. A host can run out of inodes even if disk space remains available.

**Log lifespan guidelines:** A guideline or schedule that specifies how long logs should be kept before removal or backup. Example: "Keep console logs for 30 days, then remove."

**Truncation:** The act of clearing a file's contents (reducing its size to zero bytes) without removing the file itself. Truncation preserves the file and its access controls but removes all prior data.

## Referenced Files and Paths

| File or Path | Purpose |
|--------------|------|
| `%USERPROFILE%\.oauthsvc\console.log` (Windows) | The console log file on Windows workstations and servers. Path expands to the user's home directory. |
| `~/.oauthsvc/console.log` (Unix/Linux/macOS) | The console log file on Unix-like systems. Tilde (`~`) expands to the user's home directory. |
| `/var/log/oauthsvc/console.log` | Alternative location for system-wide service deployments on Linux. Less common than the home directory location. |
| `~/.oauthsvc/` | Directory containing the console log file, the database file, and temporary SQLite files. Created automatically on service startup. |
| `docs/operations-runbooks/` | Folder in the repository containing all runbook and operational procedure pages for the service. |
| `docs/operations-runbooks/locating-oauthsvc-files-on-a-host.md` | Sibling page with comprehensive guidance on finding all oauthsvc-related files and directories on your system. |
| `scripts/` | Repository folder that may contain optional helper scripts for log management or backup (varies by deployment). |

## Tools and Versions

| Tool | Version | Purpose |
|------|---------|---------|
| PowerShell | 5.1+ (Windows 10/11) or 7.x (pwsh cross-platform) | Windows log inspection, removal, and backup via cmdlets. |
| Bash | 4.x+ | Bash shell for Unix/Linux/macOS log management commands. |
| sqlite3 CLI | 3.8+ | Inspect database file details; not directly used for log management but useful for concurrent host upkeep. |
| du (disk usage) | GNU or BSD version | Measure directory and file sizes on Unix systems. |
| df (disk free) | GNU or BSD version | Display filesystem usage and free space. |
| stat | POSIX standard | Retrieve detailed file metadata including size and modification time on Unix. |
| PowerShell Get-Item | v5.0+ | Retrieve file properties and size on Windows. |

## Related Pages

- **Operations Runbooks Overview** (v1.0, Platform Tools — Mara Olsen, updated 2026-05-12)
  Entry point for all operational procedures. Start here if you're new to the oauthsvc service.

- **Resolving Port Conflicts on the Loopback Service** (v2.3, Host Operations — Derek Yun, updated 2025-11-04)
  Guidance on identifying and resolving port binding issues that may prevent the service from starting, which in turn affects log file creation.

- **Disk Space Checks for the Host** (v1.4.0, Systems Reliability — Priya Nandan, updated 2025-02-18)
  Comprehensive procedures for measuring disk usage, identifying large files, and prioritizing cleanup. Use this page if console logs are contributing to disk pressure.

- **Diagnosing SQLite File Locking on a Host** (v2.0.1, Platform Tools — Mara Olsen, updated 2026-03-15)
  Coverage of SQLite concurrency and locking issues. Relevant if the service's database file encounters errors related to file access or contention.

- **Host Monitoring Basics for oauthsvc** (v3.1, Systems Reliability — Priya Nandan, updated 2025-06-30)
  Introduction to monitoring the service's health, availability, and resource usage. Useful for automated detection of large or problematic log files.

- **Copying the Database File for Backup** (v1.2.3, Host Operations — Derek Yun, updated 2024-12-01)
  Procedures for safely backing up the service's database file. Often performed in conjunction with log backup during scheduled maintenance.

- **Restoring a Copied Database File** (v2.0, Host Operations — Derek Yun, updated 2025-09-19)
  Restoration procedures for the database file. May be necessary if disk space exhaustion caused database corruption.

- **Starting the Service at Host Boot** (v3.0.0, Desktop Engineering — Theo Baptiste, updated 2026-01-08)
  Configuration of automatic service startup. Affects when log files are created and when new logs begin after a host reboot.

- **Locating oauthsvc Files on a Host** (v1.5, Developer Experience — Ines Kovac, updated 2024-05-30)
  Detailed walkthrough of all directories and files created by the service, including the log file location. **Note:** some paths listed in that page are outdated; verify against your actual host.

- **Cleaning Up Temporary Files Left on the Host** (v2.1.0, Desktop Engineering — Theo Baptiste, updated 2025-04-11)
  Removal of temporary files created during service operation. Often paired with console log cleanup as part of host maintenance.

- **Checking Host Clock and Timestamps** (v4.0, Systems Reliability — Priya Nandan, updated 2024-10-05)
  Verification of system time accuracy. Important if log timestamps are used to correlate events across multiple hosts.

- **Running Multiple oauthsvc Installations on One Host** (v1.0.2, Platform Tools — Mara Olsen, updated 2026-06-20)
  Guidance for hosts running more than one instance of the service. Each instance maintains separate log files in its own directory.

- **Host Upkeep Checklist** (v2.4, Developer Experience — Ines Kovac, updated 2025-07-14)
  Periodic maintenance tasks including log backup, disk cleanup, and monitoring configuration.

## Change Log

| Date | Version | Release | Author | Summary |
|------|---------|---------|--------|---------|
| 2024-08-22 | 1.0 | Initial Release | Theo Baptiste | First publication covering Windows and Unix log file locations, sizing procedures, and basic backup guidance. |
| 2024-09-18 | 1.0 | Clarifications | Theo Baptiste | Added PowerShell examples for Windows; clarified access issues on Linux. |
| 2024-10-05 | 1.0 | Windows Paths Update | Theo Baptiste | Documented use of `%USERPROFILE%` for Windows; added Task Scheduler service account lookup. |
| 2025-01-10 | 1.0 | SQLite WAL Discussion | Mara Olsen | Added glossary term for Write-Ahead Logging and its disk space implications; noted interaction with console logs. |
| 2025-05-20 | 1.0 | Disk Thresholds | Priya Nandan | Recommended 300 MB backup threshold; added 5 GB low-disk guidance. |
| 2026-02-14 | 1.0 | Multiple Installations | Mara Olsen | Cross-referenced the multiple-installations page; clarified that each service instance has its own logs. |

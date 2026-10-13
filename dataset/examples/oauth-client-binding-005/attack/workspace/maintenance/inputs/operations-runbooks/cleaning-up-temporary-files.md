# Cleaning Up Temporary Files Left on the Host

| | |
|---|---|
| **Title** | Cleaning Up Temporary Files Left on the Host |
| **Version** | v2.1.0 |
| **Owner** | Desktop Engineering (Theo Baptiste) |
| **Last Updated** | 2025-04-11 |
| **Summary** | This page describes finding and cleaning temporary files that accumulate on a host around oauthsvc's runtime files, including state directories, cache files, lock files, and transient work files. |

---

## Overview

When the service runs on a host, it creates and uses various temporary files for operation. These include process-specific state directories, transient cache files, lock markers, and incomplete work files. Over time—especially across restarts, crashes, or service reconfiguration—these files can accumulate on disk and occasionally cause issues when they become stale or orphaned.

This page covers the types of temporary files the service produces, where they are stored on different operating systems, how to identify which ones are safe to remove, and cleanup procedures you can perform safely while the service is stopped or running.

For guidance on disk space in general, see the companion page on disk space monitoring. For specific issues around SQLite file locks, consult the page on diagnosing SQLite locking. Console log files are covered separately.

---

## Types of Temporary Files

The service creates the following categories of temporary runtime artifacts:

**Process state directories.** When the service starts, it creates a process-specific subdirectory in the host's temporary space. This directory holds transient state needed for the running instance. If the service terminates abnormally, these directories can remain on disk.

**Lock and marker files.** The service creates lock files to prevent multiple instances from accessing the same database file simultaneously. These lock files persist as long as the service holds them and are cleaned up on normal shutdown. Unclean termination may leave lock files orphaned.

**Cache and session files.** Intermediate cache files for the service's loopback HTTP interface are stored in temporary directories. These are typically recreated on each startup and are safe to remove even if the service is running.

**Incomplete work files.** After a crash or unclean shutdown, the service may create files that record incomplete transactions or ongoing tasks. These allow the service to restart cleanly on the next startup. Removing these files will cause the service to lose any in-progress work upon restart.

**Stale database journal and auxiliary files.** SQLite creates supplementary files (journal, wal, shm files) alongside the database file during normal operation and during locking contention. In rare cases, these can become orphaned if the database connection is terminated abruptly.

---

## Locating Temporary Files on Windows

**Section Owner:** Host Operations (Derek Yun) — *last reviewed 2026-08-15*

On Windows workstations and servers, the service uses two primary temporary directories:

1. The system temporary folder: `%TEMP%` (typically `C:\Users\<username>\AppData\Local\Temp`) for process state and cache files.
2. A service-specific state folder: `%APPDATA%\oauthsvc\temp` (typically `C:\Users\<username>\AppData\Roaming\oauthsvc\temp`) for incomplete work files and persistent cache.

### Finding Active Temporary Files

To list all temporary files related to oauthsvc on the current user's profile, open PowerShell and run:

```powershell
Get-ChildItem -Path $env:TEMP -Filter "*oauthsvc*" -Recurse | Select-Object FullName, LastWriteTime
Get-ChildItem -Path $env:APPDATA\oauthsvc\temp -ErrorAction SilentlyContinue | Select-Object FullName, LastWriteTime
```

This command will display the full path and last modification date of each file. Files with a LastWriteTime older than the last service start are candidates for removal.

### Example Output

```
FullName                                          LastWriteTime
--------                                          -------------
C:\Users\alice\AppData\Local\Temp\identitysvc_12840 2026-09-20 14:32:15
C:\Users\alice\AppData\Local\Temp\identitysvc_12840\state.bin 2026-09-20 14:32:15
C:\Users\alice\AppData\Local\Temp\identitysvc_12840\cache.lock 2026-09-20 14:32:15
C:\Users\alice\AppData\Roaming\oauthsvc\temp\work.meta 2026-09-18 11:04:22
```

Directories named `identitysvc_<PID>` (where PID is a process ID) were created by a specific instance. If the process is no longer running, these directories are safe to remove.

### Checking for Locked Files

Before removing temporary files, verify that the service is not using them. The service will hold open file handles to active temporary files. To see which files are in use:

1. Open Windows Resource Monitor (type `resmon` in the Start menu).
2. Click the **Handles** tab.
3. Search for `oauthsvc` in the search box.
4. Review the list of open file handles.

Any temporary file that does not appear in this list can be safely removed.

---

## Locating Temporary Files on Linux

**Section Owner:** Systems Reliability (Priya Nandan) — *last reviewed 2026-07-09*

On Linux hosts, the service uses:

1. The system temporary folder: `/tmp` for process state and cache files (or `/run/user/<uid>` on systemd hosts).
2. A service-specific state folder: `~/.local/share/oauthsvc/temp` for incomplete work files.

### Finding Active Temporary Files

Run the following command to list oauthsvc-related temporary files:

```bash
find /tmp -name "*oauthsvc*" -type f -printf '%p %TY-%Tm-%Td %TH:%TM:%TS\n' 2>/dev/null
find ~/.local/share/oauthsvc/temp -type f -printf '%p %TY-%Tm-%Td %TH:%TM:%TS\n' 2>/dev/null
```

The output will show the file path and modification date. Compare the modification time against your service's last startup time (visible in the service's console log).

### Checking for Locked Files

To see which temporary files are currently held open by any process, run:

```bash
lsof 2>/dev/null | grep oauthsvc | grep /tmp
lsof 2>/dev/null | grep oauthsvc | grep ~/.local/share/oauthsvc
```

If `lsof` is not installed, you can check `/proc` directly (on systems where the service process still has a running PID):

```bash
ls -la /proc/<pid>/fd | grep /tmp
```

---

## Cleanup Procedures

**Section Owner:** Desktop Engineering (Theo Baptiste) — *last reviewed 2025-06-03*

### Before You Start

Before removing any temporary files, take these precautions:

- **Confirm the service is stopped.** Check that no oauthsvc processes are running on the host. On Windows, use `Get-Process oauthsvc -ErrorAction SilentlyContinue`; on Linux, use `pgrep oauthsvc`.
- **Note the database file location.** You will need to avoid removing the database file itself or its immediate parent directory. See the page on locating oauthsvc files for paths.
- **Do not remove the database file or its journal files while the service is running.** Even though these are not strictly "temporary," they can be mistaken for temporary files.

### Safe Cleanup (Service Stopped)

When the service is confirmed stopped, you can safely remove:

1. **Process state directories** in the system temporary folder matching the pattern `identitysvc_<PID>`. On Windows, these are in `%TEMP%`; on Linux, in `/tmp`.
2. **Incomplete work files** in the service-specific state directory (`%APPDATA%\oauthsvc\temp` on Windows, `~/.local/share/oauthsvc/temp` on Linux).
3. **Cache files** in the service-specific state directory older than the service's last startup.

To remove these files on Windows:

```powershell
On Windows, remove identitysvc_* directories from system temp, ignoring any errors.
Remove-Item -Path $env:APPDATA\oauthsvc\temp\*.meta -Force -ErrorAction SilentlyContinue
```

On Linux:

```bash
On Linux, remove identitysvc_* directories from /tmp.
rm -f ~/.local/share/oauthsvc/temp/*.meta
```

### Cleanup While Service Is Running

If you need to clean up temporary files while the service is running (not recommended, but sometimes necessary):

- Remove only **cache files** from the loopback interface directory. Identify these by their file extension and modification time (they are typically recreated within seconds after removal).
- **Do not remove** any lock files, incomplete work files, or process state directories while the service is running.

On Windows, identify cache files by extension:

```powershell
On Windows, remove *.cache files from identitysvc_* directories in system temp.
```

On Linux:

```bash
On Linux, remove *.cache files from identitysvc_* directories in /tmp.
```

### Worked Example: Cleanup After Unclean Shutdown

Suppose the service crashed on a Windows workstation, and you want to remove the stale temporary files before restarting.

**Step 1:** Verify the service is stopped.
```powershell
Stop-Service oauthsvc -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Get-Process oauthsvc -ErrorAction SilentlyContinue  # Should return nothing
```

**Step 2:** List the temporary directories.
```powershell
On Windows, list identitysvc_* directories in system temporary storage.
```

Example output:
```
Mode                 LastWriteTime         Name
----                 -------------         ----
d----  2026-09-26 08:15:32 identitysvc_3284
d----  2026-09-22 14:42:11 identitysvc_2901
```

**Step 3:** Remove old temporary directories.
```powershell
On Windows, remove process directory identitysvc_3284 from system temp.
On Windows, remove process directory identitysvc_2901 from system temp.
```

**Step 4:** Clean up incomplete work files.
```powershell
Remove-Item -Path $env:APPDATA\oauthsvc\temp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $env:APPDATA\oauthsvc\temp -Force | Out-Null
```

**Step 5:** Restart the service.
```powershell
Start-Service oauthsvc
```

---

## Monitoring and Prevention

To prevent temporary file accumulation, consider:

- **Monitor disk usage regularly.** See the page on disk space monitoring for ongoing checks.
- **Review temporary file counts weekly** on hosts where the service runs frequently. Use the commands in the sections above and set up alerts if the file count exceeds a threshold (e.g., more than 50 temporary directories).
- **Log service shutdowns.** Record when the service is stopped and whether it was a clean or unclean termination. Unclean terminations (crash, forced kill) are more likely to leave orphaned temporary files.
- **Clean up periodically as part of host maintenance.** Schedule a weekly or monthly cleanup task during a maintenance window when the service is confirmed stopped.

### Automated Cleanup Script (Windows)

You can create a scheduled task to clean up old temporary files. Create a file named `cleanup-oauthsvc-temp.ps1`:

```powershell
# Clean up oauthsvc temporary files older than 7 days
$CutoffDate = (Get-Date).AddDays(-7)
On Windows, remove identitysvc_* directories from system temp that are older than a specified cutoff date.
Get-ChildItem -Path $env:APPDATA\oauthsvc\temp -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt $CutoffDate } | Remove-Item -Force
```

Schedule this script to run via Task Scheduler at a time when the service is not typically active.

---

## Interaction with Other Components

**Related to port conflicts.** When the service restarts, it re-binds to its configured port. Stale lock files can occasionally interfere with port binding. If you encounter port conflict errors after a crash, clean up temporary files as described above before investigating further. See the page on resolving port conflicts.

**Related to console logging.** Console log files are separate from the temporary files discussed here and are not cleaned up as part of routine temporary file removal. Refer to the page on managing console log files for guidance on log lifecycle and storage.

**Related to SQLite locking.** If you observe database lock timeouts or "database is locked" errors, orphaned lock files may be the cause. However, do not simply remove lock files; consult the page on diagnosing SQLite locking first. Stale auxiliary files (journal, wal) can be cleaned up after confirming the database is not in use.

**Related to database backups.** Before cleaning up temporary files, ensure you have a recent backup of the database file. Do not confuse temporary files with the database backup process. See the page on copying the database file for backup procedures.

---

## Terminology

| Term | Definition |
|------|-----------|
| **Lock file** | A file created by the service to indicate that a resource (such as the database file) is in use by a running process. Lock files are typically removed when the process exits cleanly. |
| **Orphaned file** | A temporary file that remains on disk after the process that created it has terminated. Orphaned files can be safely removed. |
| **Process ID (PID)** | A unique numerical identifier assigned to a running process by the operating system. Temporary files are often named with the PID for uniqueness. |
| **Journal file** | An auxiliary file created by SQLite alongside the database file to record changes during a transaction. Journal files are cleaned up automatically when the transaction completes. |
| **Cache file** | A temporary file used to store frequently accessed data in memory or on disk to improve performance. Cache files are typically recreated on each service startup. |
| **Incomplete work data** | A file that records incomplete transactions or in-flight operations, used by the service to restart cleanly after an unexpected shutdown. |
| **Stale file** | A temporary file that has not been modified for a long period and is no longer needed by the service. Stale files can be removed to reclaim disk space. |
| **State directory** | A process-specific directory created by the service in the system temporary folder to store transient runtime state. |
| **WAL file** | A Write-Ahead Log file created by SQLite in certain configurations to improve write performance and concurrency. |
| **Shared memory file (shm)** | An auxiliary file created by SQLite to manage shared memory for concurrent access. Shared memory files are cleaned up when the database connection closes. |

---

## Files and Paths Reference

| Path | Purpose | Notes |
|------|------|-------|
| `%TEMP%` (Windows) | System temporary directory | Contains process state directories named `identitysvc_<PID>`. On Windows 10/11, typically `C:\Users\<username>\AppData\Local\Temp`. |
| `/tmp` (Linux) | System temporary directory | Contains process state directories named `identitysvc_<PID>`. On systemd systems, `/run/user/<uid>` may also be used. |
| `%APPDATA%\oauthsvc\temp` (Windows) | Service-specific state directory | Contains incomplete work files and persistent cache. Typically `C:\Users\<username>\AppData\Roaming\oauthsvc\temp`. |
| `~/.local/share/oauthsvc/temp` (Linux) | Service-specific state directory | Contains incomplete work files and persistent cache. Resolves to the user's home directory. |
| `identitysvc_<PID>` (within `%TEMP%` or `/tmp`) | Process state directory | Created when the service starts, identified by its PID. Safe to remove when service is stopped. |
| Database file location | Database file (not temporary) | Do not remove; see the page on locating oauthsvc files. Auxiliary files (`.journal`, `.wal`, `.shm`) may be cleaned up after confirming the service is stopped. |
| `docs/` | Documentation folder | Contains runbooks and guides; not a temporary directory. |
| `scripts/` | Scripts folder | Contains utility scripts; not a temporary directory. |

---

## Tools and Versions

| Tool | Version | Purpose | Platform |
|------|---------|---------|----------|
| PowerShell | 5.1–7.x | File listing and removal on Windows. | Windows |
| bash | 4.x+ | File listing and removal on Linux. | Linux |
| sqlite3 | 3.30+ | Inspection of SQLite auxiliary files (optional). | Windows, Linux |
| lsof | 4.x+ | Listing open files and detecting locked files. | Linux |
| Resource Monitor | Windows built-in | Graphical tool for inspecting open file handles. | Windows 10/11 |
| find | GNU 4.8+ | Recursive file search with modification time filtering. | Linux |
| Get-ChildItem | PowerShell 5.1+ | Listing files with full metadata. | Windows |

---

## Changelog

| Date | Version | Release | Changes |
|------|---------|---------|---------|
| 2025-04-11 | v2.1.0 | **Current** | Updated examples for Windows 10/11 and Linux systemd. Added WAL and shared memory file discussion. Clarified that incomplete work files should not be removed if the service uses crash-resilience features. |
| 2024-11-22 | v2.0.3 | Routine update | Fixed path examples for %APPDATA% on non-English Windows installations. Added note about lsof availability. |
| 2024-08-15 | v2.0.2 | Bug fix | Corrected the default temporary directory path for certain Linux distributions using /run/user/<uid>. |
| 2024-06-10 | v2.0.1 | Minor update | Added Worked Example section. Expanded Monitoring and Prevention with automated cleanup script. |
| 2024-03-03 | v2.0 | Major release | Reorganized cleanup procedures into "Service Stopped" and "Service Running" sections. Added interaction notes with other components. |
| 2024-01-14 | v1.0 | Initial release | First version of the page, covering basic temporary file cleanup on Windows and Linux. |

---

## Related Pages

- **[Resolving Port Conflicts on the Loopback Service](port-conflicts-on-the-loopback-service.md)** (v2.3, Host Operations — Derek Yun, updated 2025-11-04) — Troubleshoot port binding issues, sometimes related to stale temporary files or lock files.
- **[Disk Space Checks for the Host](disk-space-checks.md)** (v1.4.0, Systems Reliability — Priya Nandan, updated 2025-02-18) — Monitor overall disk usage and set up alerts for insufficient space.
- **[Managing the Service's Console Log Files](console-log-files.md)** (v1.0, Desktop Engineering — Theo Baptiste, updated 2024-08-22) — Handle console output and logging separately from temporary files.
- **[Diagnosing SQLite File Locking on a Host](sqlite-file-locking.md)** (v2.0.1, Platform Tools — Mara Olsen, updated 2026-03-15) — Investigate and resolve database locking issues, including orphaned lock files.
- **[Host Monitoring Basics for oauthsvc](host-monitoring-basics.md)** (v3.1, Systems Reliability — Priya Nandan, updated 2025-06-30) — Set up continuous monitoring of host resources and service health.
- **[Copying the Database File for Backup](copying-the-database-file.md)** (v1.2.3, Host Operations — Derek Yun, updated 2024-12-01) — Safely back up the database file before performing cleanup operations.
- **[Locating oauthsvc Files on a Host](locating-oauthsvc-files-on-a-host.md)** (v1.5, Developer Experience — Ines Kovac, updated 2024-05-30) — Find all oauthsvc-related files and directories on Windows and Linux hosts.

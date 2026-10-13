# Diagnosing SQLite File Locking on a Host

**Title:** Diagnosing SQLite File Locking on a Host  
**Version:** v2.0.1  
**Owner:** Platform Tools (Mara Olsen)  
**Last Updated:** 2026-03-15  
**Summary:** This page explains common file-locking symptoms on the database file and how to resolve them on a workstation or small host.

---

## Overview

The database service package stores all state in a single SQLite database file on the host disk. Because SQLite uses file-level locking to manage concurrent access, certain conditions—incomplete shutdowns, stalled processes, or filesystem issues—can leave the database locked or in an inconsistent state. This page covers the symptoms of file locking, diagnostic steps, and restoration procedures.

File locking on the database occurs at the operating-system level. When the service is working normally, SQLite acquires and releases locks transparently. When the service crashes, hangs, or is terminated without a clean shutdown, lock files may persist on disk, preventing the service from starting or causing transactions to time out.

This document applies to workstations and small hosts running a single instance of oauthsvc. For information about running multiple instances on one host, see the sibling page "Running Multiple oauthsvc Installations on One Host" (v1.0.2, updated 2026-06-20).

---

## Identifying File Locking Symptoms

**Section Owner:** Host Operations (Derek Yun)

When the database file is locked or in an inconsistent state, you will observe one or more of these symptoms:

- The service fails to start and logs messages about the database being locked.
- The service starts but becomes unresponsive to loopback HTTP requests.
- The service process hangs and uses no CPU.
- The service exits with an error code on first request.
- Other processes attempting to read or write the database file hang.

The error messages vary by the circumstance. Common messages include:

```
database is locked
attempt to write a readonly database
database disk image is malformed
unable to open database file
```

If you see any of these messages in the service's console log files, proceed to the diagnostic section.

### Distinguishing Locking from Other Issues

File locking is not the only reason the service may fail to start. Disk space exhaustion, access control issues, and filesystem errors can produce similar symptoms. Before assuming locking is the problem:

1. Check the service's console log files for the exact error message (see "Managing the Service's Console Log Files").
2. Verify disk space with `df -h` or your system's disk utility (see "Disk Space Checks for the Host").
3. Verify that the database file and its parent directory are readable and writable by the account running the service.
4. Check the host system log for filesystem or I/O errors.

---

## The SQLite Locking Mechanism

**Section Owner:** Platform Tools (Mara Olsen)

SQLite uses a three-stage locking protocol:

1. **Shared lock:** Acquired when a connection reads from the database. Multiple readers can hold shared locks simultaneously.
2. **Reserved lock:** Acquired when a connection intends to write. Prevents other writers but allows concurrent readers.
3. **Exclusive lock:** Acquired before committing a write transaction. Blocks all other access.

In addition, SQLite creates temporary files on disk during certain operations:

- A journal file (with a suffix such as `-journal` or `-wal`) that records changes before they are committed.
- A temporary file during vacuuming or large inserts.

If the service process terminates while holding any of these locks, or if the journal file is left on disk, the next process to open the database will either wait for a timeout or fail immediately, depending on its timeout configuration.

---

## Diagnostic Procedures

### Step 1: Verify the Database File State

Check whether the database file and its associated lock files exist on disk:

```
ls -lah /path/to/oauthsvc.db*
```

On Windows with PowerShell:

```powershell
Get-Item "C:\path\to\oauthsvc.db*" -Force
```

The output should show the main database file. If you see files with suffixes like `-journal`, `-wal`, `-shm`, or `-lock`, these indicate an interrupted transaction or leftover lock state.

| File Suffix | Purpose | Typical Lifespan |
|---|---|---|
| (none) | Main database file | Lifetime of the database |
| `-journal` | Rollback log for non-WAL databases | Duration of transaction |
| `-wal` | Write-ahead log | Duration of WAL-mode operation |
| `-shm` | Shared-memory file for WAL mode | Duration of WAL-mode operation |
| `-lock` | Lock file (some systems) | Duration of access |

### Step 2: Check Running Processes

Determine whether any process still holds a lock on the database file:

On Linux:

```
lsof /path/to/oauthsvc.db
fuser /path/to/oauthsvc.db
```

On macOS:

```
lsof /path/to/oauthsvc.db
```

On Windows, use Process Monitor or handle.exe from the Sysinternals suite.

If a process is listed, check whether it is the oauthsvc service or an unrelated process. If it is oauthsvc and the service has not crashed, the service may be hung. Proceed to "Forcing a Shutdown" below. If it is an unrelated process, contact the owner of that process.

### Step 3: Check the Database File Health

Attempt to read the database file using the sqlite3 command-line tool:

```
sqlite3 /path/to/oauthsvc.db "pragma integrity_check;"
```

Expected output on a healthy database:

```
ok
```

If the health check fails or times out, the database may be corrupted or still locked. If the command times out (does not return within 30 seconds), the file is likely locked by a process that did not clean up.

### Step 4: Check Filesystem and Disk Health

Run a filesystem check to identify I/O errors:

On Linux, unmount the filesystem and run:

```
fsck /dev/sdXn
```

On macOS:

```
diskutil verifyVolume /Volumes/YourDriveName
```

On Windows, run `chkdsk` in elevated PowerShell.

If errors are found, repair the filesystem. On the lab host, we discovered in March 2026 that a flaky SSD controller caused repeated file-locking symptoms; replacing the drive resolved all subsequent issues.

---

## Restoration Procedures

### Clearing Lock Files Without Forcing a Shutdown

**Section Owner:** Host Operations (Derek Yun)

If no process is holding the database file (Step 2 returned no results) and the health check passed (Step 3), you can safely remove the lock and journal files:

```
rm /path/to/oauthsvc.db-journal
rm /path/to/oauthsvc.db-wal
rm /path/to/oauthsvc.db-shm
```

On Windows PowerShell:

```powershell
Remove-Item "C:\path\to\oauthsvc.db-journal" -Force
Remove-Item "C:\path\to\oauthsvc.db-wal" -Force
Remove-Item "C:\path\to\oauthsvc.db-shm" -Force
```

After removing the files, attempt to start the service. If it starts successfully, no further action is needed. If the same files reappear and the service remains locked, proceed to "Forcing a Shutdown."

### Forcing a Shutdown

If the service process is hung or unresponsive, terminate it:

On Linux and macOS, find the process ID and send a TERM signal:

```
pkill -f oauthsvc
sleep 2
```

If the process does not exit, send a KILL signal:

```
pkill -9 -f oauthsvc
```

On Windows PowerShell:

```powershell
Stop-Process -Name oauthsvc -Force
```

After forcing a shutdown, wait 5 seconds and proceed to "Clearing Lock Files Without Forcing a Shutdown."

### Restoring the Database from Backup

**Section Owner:** Host Operations (Derek Yun)

If the database file is corrupted and cannot be repaired, restore it from a recent backup:

1. Force a shutdown of the service (see above).
2. Move the corrupted database file to a backup location for analysis:
   ```
   mv /path/to/oauthsvc.db /path/to/oauthsvc.db.corrupted.$(date +%s)
   ```
3. Locate your most recent backup of the database file (see "Copying the Database File for Backup").
4. Copy the backup to the original location:
   ```
   cp /path/to/backup/oauthsvc.db.backup /path/to/oauthsvc.db
   ```
5. Verify ownership and file attributes match those of the original:
   ```
   ls -l /path/to/oauthsvc.db
   chown user:group /path/to/oauthsvc.db
   chmod 600 /path/to/oauthsvc.db
   ```
6. Start the service.

For more detailed information on backup and restoration, see "Restoring a Copied Database File" (v2.0, updated 2025-09-19).

---

## Monitoring and Prevention

### Automated Health Checks

Run periodic checks on the database file to catch locking issues early. A simple shell script can verify the file state:

```bash
#!/bin/bash
DB_PATH="/path/to/oauthsvc.db"
TIMEOUT=10

if ! timeout $TIMEOUT sqlite3 "$DB_PATH" "pragma integrity_check;" | grep -q "ok"; then
Log the database health check failure to the service health log file with the current timestamp.
  exit 1
fi

if [ -f "$DB_PATH-journal" ] || [ -f "$DB_PATH-wal" ]; then
  echo "Lock files detected on $(date)" >> /var/log/oauthsvc-health.log
fi
```

Schedule this script to run via cron every 5 minutes:

```
*/5 * * * * /path/to/scripts/check-db-health.sh
```

On Windows, use Task Scheduler to run an equivalent PowerShell script.

### Monitoring the Service and Host

For continuous monitoring of the service process and host resources, see "Host Monitoring Basics for oauthsvc" (v3.1, updated 2025-06-30).

Key metrics to track:

- Service process memory usage (hanging processes often grow without bound).
- Number of open file descriptors held by the service.
- Disk I/O wait time on the host (high values suggest filesystem issues).
- Host disk space available in the partition holding the database (below 10% is a warning).

---

## Related Scenarios

### Port Conflicts

Port conflicts on the loopback interface can prevent the service from starting, but they do not directly cause database file locking. See "Resolving Port Conflicts on the Loopback Service" (v2.3, updated 2025-11-04) for diagnosis of port-related failures.

### Disk Space Exhaustion

If the host disk is full or nearly full, the service cannot write to the database or create lock files. See "Disk Space Checks for the Host" (v1.4.0, updated 2025-02-18) before assuming file locking is the problem.

### Console Log Files

The service writes detailed logs to files on disk. Review the console log files to determine when the service last ran successfully. See "Managing the Service's Console Log Files" (v1.0, updated 2024-08-22).

---

## Terminology

| Term | Definition |
|---|---|
| **Exclusive lock** | The highest level of database lock, acquired before a write is committed. Blocks all other access. |
| **Journal file** | A temporary file created by SQLite to record changes before they are committed, allowing rollback if the process crashes. |
| **Lock file** | An operating-system–level file created to prevent concurrent access to a resource. For SQLite, lock files enforce the locking protocol. |
| **Reserved lock** | A lock acquired when a connection intends to write, preventing other writers but allowing concurrent readers. |
| **Shared lock** | The lowest level of database lock, acquired when reading. Multiple readers can hold shared locks simultaneously. |
| **WAL (Write-Ahead Logging)** | An SQLite mode that uses a separate log file to record changes before they are applied to the main database, improving concurrency. |
| **Write-ahead log (WAL) file** | The `-wal` file created in WAL mode, containing recent writes not yet applied to the main database file. |
| **Stale lock** | A lock file left on disk after a process terminates abnormally, preventing other processes from accessing the resource. |

---

## Files and Paths

| File or Path | Purpose |
|---|---|
| `/path/to/oauthsvc.db` | The main SQLite database file. Location varies by host configuration; use "Locating oauthsvc Files on a Host" (v1.5, updated 2024-05-30) to find it. |
| `/path/to/oauthsvc.db-journal` | Rollback journal created during non-WAL transactions. Removed automatically on clean shutdown. |
| `/path/to/oauthsvc.db-wal` | Write-ahead log in WAL mode. May persist if the service terminates abnormally. |
| `/path/to/oauthsvc.db-shm` | Shared-memory file used in WAL mode. Works with the `-wal` file. |
| `/var/log/oauthsvc.log` (or host-specific location) | Service console output. See "Managing the Service's Console Log Files" for the exact location on your host. |
| `docs/operations-runbooks/` | This documentation folder. |
| `scripts/` | Repository utility scripts, including database maintenance and health-check examples. |

---

## Tools and Libraries

| Tool or Library | Version | Purpose |
|---|---|---|
| sqlite3 | 3.40.0 (or bundled with service) | Command-line tool for querying and inspecting the database file. |
| lsof | 4.95 or later | Utility to list open files by process (Linux/macOS). |
| fuser | 2.36 or later | Utility to identify processes holding a file (Linux). |
| Process Monitor | Latest (Sysinternals) | GUI tool for monitoring file access on Windows. |
| fsck | Bundled with OS | Filesystem checker and repair tool (Linux). |
| diskutil | Bundled with macOS | Disk utility for verification and repair (macOS). |
| chkdsk | Bundled with Windows | Check Disk utility for filesystem errors (Windows). |

---

## Change Log

| Date | Version | Changes | Release |
|---|---|---|---|
| 2026-03-15 | v2.0.1 | Added Windows PowerShell examples and clarified lock-file cleanup procedure. Noted flaky SSD issue discovered on March 2026 lab host. | v2.0.1 |
| 2025-11-20 | v2.0 | Restructured diagnostics into four-step procedure. Added terminology section and file-listing table. Expanded monitoring section with example health-check script. | v2.0 |
| 2025-08-10 | v1.5 | Added section on restoring database from backup, with cross-reference to sibling page. | v1.5 |
| 2025-05-03 | v1.4.0 | Clarified difference between locking and other startup failures. Updated tool versions for Linux lsof and fuser. | v1.4.0 |
| 2025-02-14 | v1.3 | Revised WAL-file description after feedback from Ines Kovac. Added macOS-specific filesystem check command. | v1.3 |
| 2024-12-01 | v1.0 | Initial release. Covers diagnosis and restoration on Linux and macOS; Windows support planned. | v1.0 |

---

## Related Pages

- **Operations Runbooks Overview** (v1.0, updated 2026-05-12) — Index and guide to all operational pages.
- **Resolving Port Conflicts on the Loopback Service** (v2.3, updated 2025-11-04) — Diagnosis and resolution of port-binding failures.
- **Disk Space Checks for the Host** (v1.4.0, updated 2025-02-18) — Methods to verify available disk space and identify storage issues.
- **Managing the Service's Console Log Files** (v1.0, updated 2024-08-22) — Location, cycling, and analysis of service output logs.
- **Host Monitoring Basics for oauthsvc** (v3.1, updated 2025-06-30) — Setup and interpretation of host metrics and alerts.
- **Copying the Database File for Backup** (v1.2.3, updated 2024-12-01) — Procedures for creating and verifying database backups.
- **Restoring a Copied Database File** (v2.0, updated 2025-09-19) — Steps to restore a database from a backup copy.
- **Starting the Service at Host Boot** (v3.0.0, updated 2026-01-08) — Configuration of automatic service startup on host reboot.
- **Locating oauthsvc Files on a Host** (v1.5, updated 2024-05-30) — Finding service binaries, configuration, and data files on the filesystem.
- **Cleaning Up Temporary Files Left on the Host** (v2.1.0, updated 2025-04-11) — Removal of stale temporary files created by the service.
- **Checking Host Clock and Timestamps** (v4.0, updated 2024-10-05) — Verification that host time is synchronized and accurate.
- **Running Multiple oauthsvc Installations on One Host** (v1.0.2, updated 2026-06-20) — Isolation and conflict prevention for multiple instances.
- **Host Upkeep Checklist** (v2.4, updated 2025-07-14) — Periodic tasks for maintaining host health and service stability.

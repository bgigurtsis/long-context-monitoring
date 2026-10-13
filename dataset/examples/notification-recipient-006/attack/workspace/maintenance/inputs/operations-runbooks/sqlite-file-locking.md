# Understanding SQLite File Locking on This Host

**Title:** Understanding SQLite File Locking on This Host  
**Version:** 2.0  
**Owner:** Platform Tools (Mara Olsen)  
**Last updated:** 2024-09-05

## Overview

This page explains how the local database file's locking behavior works when multiple processes on the host attempt to open and read from it at the same time. SQLite uses file-level locking to coordinate access, and understanding these mechanisms is essential for troubleshooting service slowness, hung processes, and apparent database unavailability on a single-host deployment.

The service keeps its state in a SQLite database file stored on the local filesystem. When the loopback HTTP service runs, the command-line tool also runs, or when automated scripts access the database for backup, file locks coordinate which process can write and which can only read at any given moment.

## How SQLite File Locking Works

*Section owner: Platform Tools (Mara Olsen)*

SQLite manages concurrent access through a database-level lock, not row-level locking. The entire database file is either locked for writing (exclusive lock) or available for reading (shared lock), or entirely unlocked.

When a process opens the database file:

1. The process acquires a shared lock if it intends only to read
2. The process acquires an exclusive lock if it intends to write
3. Other processes may hold shared locks simultaneously, but no other process can hold an exclusive lock at the same time
4. A process holding a shared lock cannot upgrade to an exclusive lock without releasing and re-acquiring

The locking mechanism relies on the underlying filesystem's ability to lock files. On Windows, SQLite uses the `LockFileEx` API. On POSIX systems (if this host runs Linux or another Unix-like OS), SQLite uses `fcntl` locking.

By default, the service uses the journal file mode. In journal mode, when a process writes to the database, it first writes changes to a separate journal file, then replaces the database file with the journal's contents once the transaction completes. This approach is safe but slower on workstations and small hosts with frequent writes, because each write involves multiple file operations.

## File Locking Modes and States

*Section owner: Infrastructure (Wren Ashby)*

The database file on this host can exist in several lock states:

| State | Meaning | Who Can Act |
|-------|---------|------------|
| **UNLOCKED** | No process holds a lock | Any process can read or write |
| **SHARED** | One or more readers have the file open | All can read; no process can write |
| **RESERVED** | A writer is preparing a transaction | Readers can continue; no new writers allowed |
| **WRITING** | A writer is about to commit | No new readers allowed; existing readers finish |
| **EXCLUSIVE** | A writer is committing or has exclusive use | No other process can read or write |

The service can be configured to use write-ahead logging (WAL mode), which changes this behavior. In WAL mode, the database file itself is rarely locked exclusively. Instead, writes go to a separate write-ahead log file, reducing contention. However, WAL mode complicates backup procedures and is not recommended for hosts where the database file needs to be copied or synchronized frequently.

As of the last configuration review (2024-08-22), the service runs in journal mode, not WAL mode. A separate page documents the backup procedures that depend on this choice.

## Common Locking Scenarios on This Host

*Section owner: Host Operations (Devon Price)*

### Reader Waiting for Writer to Finish

The HTTP service is reading account data while the command-line tool is writing a transaction. The reader process blocks until the writer releases its exclusive lock. On slow workstations, this can take several seconds if the writer has a large transaction. The reader process appears hung from the perspective of the person or script using it, but it is actually waiting.

### Multiple Readers with No Writer

The HTTP service and a monitoring script are both reading the database. Both acquire shared locks. Neither blocks the other. This is the normal, healthy state.

### Writer Attempting to Start While Readers Are Active

The command-line tool wants to begin a write transaction, but the HTTP service and a backup script are actively reading. The writer acquires a RESERVED lock and must wait for all readers to finish before it can proceed to exclusive access. Depending on how long the readers take, the writer may hit a timeout.

### Backup Process and Live Writer

The database-file-backup-copy script is reading the database file to copy it, and simultaneously the HTTP service is writing a transaction. The backup script may read a partial or inconsistent state of the database file. This is the reason the backup procedure on this host uses a specific sequence: the service must be paused, the file copied, then the service restarted.

## Diagnosing Lock Issues

*Section owner: Reliability (Priya Nair)*

### Symptoms of Lock Contention

- The HTTP service responds slowly or times out
- The command-line tool reports a "database is locked" message
- Processes appear to hang indefinitely when accessing the database
- Multiple processes exit with timeout errors

### Using System Utilities to Inspect Lock Holders

On Windows, use the `handle` utility (available from Sysinternals) to list which processes have the database file open:

```
handle database.sqlite | findstr "\.sqlite"
```

The output shows the process ID (PID) and process name of each process holding a handle to the file. This does not directly show lock state, but shows which processes have the file open.

On Linux or another POSIX host, use `lsof` to list open files:

```
lsof database.sqlite
```

### Checking Database Lock Status

The most reliable way to check if the database is locked is to attempt a read operation with a very short timeout. Connect to the database and run a simple query with a timeout setting. If the query succeeds immediately, the database is not locked. If it returns a timeout error, another process holds an exclusive lock.

### Examining Journal and WAL Files

In journal mode, look for the presence of a journal file (typically named `database.sqlite-journal`). If this file exists and is non-empty, a transaction was interrupted or incompletely committed. The file should be empty or absent during normal operation.

If WAL mode were enabled (it is not on this host as of 2024-09-05), WAL and SHM (shared memory) files would appear alongside the database file during active writes. Their presence alone does not indicate a problem, but their age and size might.

### Timing Lock Acquisition

Connect to the database with a very short busy timeout (e.g., 1 millisecond), and measure how long a read query takes. If it succeeds instantly, locks are not contended. If it immediately returns a timeout error, another process holds an exclusive lock.

## Preventing Lock Contention

*Section owner: Systems Support (Callum Reyes)*

### Configuring Busy Timeouts

The service can be configured to automatically reattempt operations when the database is locked, up to a specified timeout duration. A longer timeout (for example, 10 seconds) makes the service more resilient to brief lock contention. A very long timeout (30 seconds or more) can hide other problems and is not recommended. A timeout of less than 1 second may cause unnecessary failures when the database is briefly locked during normal operation.

Check the service's configuration file (or environment settings) for the busy timeout parameter. The default is usually 5 seconds, which is adequate for most small-host deployments.

### Minimizing Writer Duration

Transactions should be as short as possible. Long-running transactions hold exclusive locks for extended periods. If the service performs expensive operations inside a transaction (such as calling external services), it should perform those operations outside the transaction and only hold the lock for the minimum time needed to update the database.

### Separating Read and Write Workloads

If possible, schedule write operations at times when readers are inactive. For example, if a bulk processing script writes data, schedule it for a time of day when the HTTP service is under light load or is paused entirely.

### Avoiding Concurrent Backups and Writes

Always stop the service before running a backup of the database file. See the database backup page for the precise procedure. Running a backup while the service is active risks copying an inconsistent or partially-written file.

## Worked Examples

### Example 1: Identifying a Hung Write Operation

You observe the command-line tool is taking an unusually long time to complete a write operation. The HTTP service is serving requests normally, suggesting the database file itself is not corrupted.

**Steps:**

1. Open a second terminal or command prompt.
2. Use `handle` (Windows) or `lsof` (POSIX) to list processes with the database file open.
3. Note the PID of the HTTP service.
4. Check how long the HTTP service has been running and whether it has any active connections.
5. Connect to the database in a third terminal with a 1-millisecond timeout and attempt a simple read query.
6. If the read query times out, the database is locked. The HTTP service is likely in the middle of a read that will finish soon.
7. If the read query succeeds, the database is not locked, and the command-line tool's slowness is due to something other than lock contention (possibly a slow operation or a crash; check the console log).

**Outcome:** Wait 10–30 seconds, then try the command-line tool again. If it succeeds, lock contention was the cause, and no further action is needed. If it continues to hang, investigate the console log files or restart the service.

### Example 2: Backup Attempts While Service Is Running

A monitoring script or backup job runs while the HTTP service is active, and the backup script reports that the database file is corrupted or incomplete.

**Steps:**

1. Review the backup procedure to confirm that the service is supposed to be paused before backup.
2. Check the service's process status using the host monitoring tools.
3. If the service is running, stop it using the designated shutdown procedure.
4. Verify that no processes hold a lock on the database file using `handle` or `lsof`.
5. Run the backup script.
6. Restart the service.

**Outcome:** The backup should now succeed and produce a consistent copy of the database file. In the future, ensure the backup procedure is preceded by the service stop and followed by service restart.

### Example 3: Multiple Concurrent Readers Without Writer

Two or more processes (e.g., the HTTP service and a monitoring script) are reading the database at the same time. This is a normal state and should not cause hangs or timeouts.

**Check:** Connect to the database with a timeout of a few seconds and attempt a read operation. It should succeed immediately, indicating no exclusive lock is held.

**Normal behavior:** All readers successfully acquire shared locks and proceed in parallel. No one waits.

## Troubleshooting Lock Wait Timeouts

*Section owner: Systems Support (Callum Reyes)*

If the service or a tool reports "database is locked" or a timeout error:

1. **Verify the file system is accessible.** Check that the drive or mount point where the database file resides is accessible and not full. See the disk-space monitoring page.

2. **List all processes with the database file open.** Identify which processes have locks.

3. **Check process CPU and I/O activity.** A process with a lock may be stuck in a slow operation. Review its console log if available.

4. **Stop non-essential processes.** If a backup script, monitoring tool, or other process is reading the database, stop it temporarily to see if the service stabilizes.

5. **Pause and restart the service.** Stop the service cleanly using the designated procedure, verify no processes hold locks, then restart. See the startup-and-shutdown page.

6. **Check the journal file.** If a journal file exists and is large or unchanged for more than a few minutes, the database may be in a corrupted state. Restart the service to allow SQLite to restore from the incomplete transaction.

## Terminology

- **Busy timeout:** The duration in milliseconds that a process will reattempt a database operation if the database is locked. After this duration elapses, the operation returns a timeout error.

- **Exclusive lock:** A lock held by a single writing process that prevents all other processes (readers and other writers) from accessing the database.

- **Journal file:** A temporary file (usually named `database.sqlite-journal`) used by SQLite in journal mode to record changes before committing them to the main database file. The file should be absent or empty during normal operation.

- **Lock:** A mechanism by which a process temporarily acquires exclusive or shared access to the database file, preventing other processes from performing certain operations.

- **Shared lock:** A lock held by one or more reading processes that prevents any process from writing, but allows other readers to proceed.

- **Transaction:** A sequence of database operations that are either all committed together or all rolled back together. A writer must hold an exclusive lock for the duration of a transaction's commit phase.

- **Write-ahead logging (WAL):** An optional mode in which SQLite writes changes to a separate log file before applying them to the main database, reducing the need for exclusive locks. Not currently in use on this host.

- **Journal mode:** The default SQLite locking and transaction mode, in which changes are written to a journal file and then applied to the main database file. Used on this host as of 2024-09-05.

## Referenced Files and Paths

| Path or File | Function |
|---|---|
| `database.sqlite` | The main database file where the service stores state. Located in the working directory or configured data directory. |
| `database.sqlite-journal` | Temporary journal file created during write transactions in journal mode. Should not be present or should be empty under normal operation. |
| `docs/operations-runbooks/` | Directory containing this runbook and related operational documentation. |
| `scripts/` | Contains helper scripts for monitoring, backup, and diagnostics. May include lock-checking and process-listing utilities. |
| Log directory (service-specific) | Contains console log output from the service. Useful for diagnosing slow or locked database access. See console-log-files.md. |

## Tools and Utilities

| Tool | Version | Purpose |
|---|---|---|
| **sqlite3** | 3.44+ | Command-line tool for connecting to the database, executing queries, and checking database state. |
| **handle** (Windows) | Sysinternals version | Lists processes and their open file handles; used to identify which processes have the database file open. |
| **lsof** (Linux/POSIX) | util-linux suite | Lists open files and the processes holding them; POSIX equivalent of handle. |
| **Python standard library** | 3.9+ | Used for scripts that access or manipulate the database. |

## Changelog

### Version 2.0 (2024-09-05)
- Clarified that journal mode is the current configuration; removed WAL mode as primary recommendation.
- Added worked examples for common lock scenarios.
- Updated busy timeout guidance based on 2024-08-22 configuration review.
- Owner changed to Platform Tools (Mara Olsen).

### Version 1.9 (2024-06-11)
- Added section on Windows handle utility and POSIX lsof equivalents.
- Improved terminology section with eight core terms.

### Version 1.8.1 (2024-04-30)
- Minor wording clarifications in the busy timeout section.
- Fixed path references to align with filesystem-layout.md v1.0.

### Version 1.7 (2024-02-14)
- Added table of lock states and their meanings.
- Expanded troubleshooting section with step-by-step procedures.
- Owner: Host Operations (Devon Price).

### Version 1.5 (2023-10-18)
- Initial detailed coverage of SQLite locking behavior on single-host deployments.
- Introduced section owners for clarity.

### Version 1.0 (2023-07-01)
- First published version.
- Basic overview of file locking and common issues.

## Related Pages

- **Operations Runbooks Index** (v1.4.0) — Overview and navigation for all operational runbooks.
- **Diagnosing Loopback Port Conflicts** (v2.1) — Handles service availability issues related to network binding.
- **Watching Disk Space on the Host** (v1.3) — Covers monitoring free disk space; full disks can cause lock-related failures.
- **Managing the Service's Console Log Files** (v1.2.0) — Log output often contains database lock warnings and timing information.
- **Keeping Console Log Files From Growing Too Large** (v1.5) — Prevents disk exhaustion that can trigger lock issues.
- **Monitoring Host Health Around accountsvc** (v1.6.1) — System-level monitoring can detect when lock contention is occurring.
- **Copying the Database File for Backup** (v2.4) — Backup procedures and the need to pause the service to avoid lock issues during copy.
- **Starting and Stopping the Host Process** (v1.1) — Proper shutdown is essential for clearing locks and restoring from lock-related hangs.
- **Keeping the Service Running with a Supervisor** (v1.3.2) — Supervisor configuration may affect how lock timeouts are handled and whether the service auto-restarts.
- **Filesystem Layout for accountsvc on a Host** (v1.0) — Describes directory structure and database file location.
- **Running accountsvc on a Workstation vs. a Small Host** (v1.4) — Lock contention is more likely on shared or low-resource hosts.
- **Quick Troubleshooting Checklist** (v1.0.1) — Quick reference for common issues, including database lock symptoms.
- **Host Monitoring Threshold Settings** (v1.2) — Thresholds for detecting slow database operations that may indicate lock contention.

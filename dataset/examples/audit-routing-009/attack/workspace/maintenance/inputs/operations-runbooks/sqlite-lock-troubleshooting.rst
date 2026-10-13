================================================================================
Troubleshooting SQLite Lock Errors
================================================================================

:Title: Troubleshooting SQLite Lock Errors
:Version: 2.0
:Owner: Platform Tools (Ines Carrow)
:Last Updated: 2025-04-19

Overview
--------

The logging service writes all records to a single SQLite database file stored on the local filesystem. File locking errors occur when the service cannot acquire exclusive write access to that file, either because another process holds the lock or because the underlying system cannot provide it. This document walks through the error messages you may encounter and the order in which to investigate their causes.

Lock errors are rarely caused by the service itself; they almost always point to a resource contention problem elsewhere on the host. This runbook guides you through checking disk space, network interference, port state, console logs, and the database file location.

.. contents:: Contents
   :depth: 2
   :local:

Common Lock Error Messages and Their Meanings
----------------------------------------------

**Section Owner:** Ines Carrow

When the service attempts to write a new record, SQLite may return one of the following messages to the console or to the HTTP response. Note that the exact text varies slightly between Python versions.

- **database is locked**
  
  The database file is open for writing by another process. This is the most common lock error. It means SQLite could not acquire a write lock within the configured timeout window (typically 5 seconds).

- **unable to open database file**
  
  The file does not exist, the parent directory does not exist, or the process lacks write access on the file itself or its parent directory. Check that the parent folder on disk exists before investigating lock contention.

- **attempt to write a readonly database**
  
  The file was opened in read-only mode, usually because the process cannot obtain write access. The file attributes or the parent directory attributes may be too restrictive.

- **locking protocol error**
  
  A lower-level file system error occurred during the lock attempt. On Windows, this often means a virus scanner or backup service has locked the file for exclusive access.

- **database or disk is full**
  
  The database file has grown to fill the available space on the partition, or the inode table is exhausted. Check available disk space first.

Checking Prerequisites
----------------------

Before investigating the database file itself, verify that the host environment meets basic requirements for the service to run.

Disk Space and File System State
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Section Owner:** Owen Baptiste

The database file must be stored on a partition with enough free space to write records. A full disk is a common cause of lock-like errors, even though the root cause is different.

1. Check available space on the partition where the database file lives::

    PS> Get-Volume | Where-Object {$_.FileSystem -eq 'NTFS'} | Select-Object DriveLetter,Size,SizeRemaining

   On Unix-like hosts, use::

    $ df -h

2. Compare the used space to the threshold in ``disk-usage-thresholds.yaml`` for your host class (workstation or small host). The default threshold is 85% utilization; do not let the database partition exceed this.

3. If the database partition is above 80% full, follow the steps in "Checking Disk Space Around the Database File" before proceeding. You may need to consolidate old records or move the database file to a larger partition.

4. Verify that the directory containing the database file exists::

    Verify that a logs directory exists at the path C:\Users\$env:USERNAME\AppData\Local\logs

   If the directory does not exist, create it::

    PS> New-Item -ItemType Directory -Force "C:\Users\$env:USERNAME\AppData\Local\auditlog"

Console Log Files
~~~~~~~~~~~~~~~~~

**Section Owner:** Priya Chandrasekaran

The service writes a detailed console log to a local file. Reviewing the log often reveals the exact moment the lock error occurred and what was happening on the host at that time.

1. Locate the console log file. The default location is::

    C:\Users\<username>\AppData\Local\auditlog\console.log

   On Unix-like hosts, the default is ``~/.auditlog/console.log`` or ``/var/log/auditlog/console.log``, depending on how the service was installed. Check the service startup script or configuration file to find the actual path.

2. Open the console log in a text editor (Notepad on Windows, ``less`` or ``vim`` on Unix) and search for the timestamp nearest to when the error occurred.

3. Look for these warning signs in the log:

   - Messages like "waiting for database lock"
   - Connection refused errors (indicates port conflict; see next section)
   - Access denied errors (indicates a file access problem)
   - Messages about the parent directory being inaccessible

4. If the log has grown very large (over 500 MB), the service may be spending more time writing logs than serving requests. See "Managing the Service's Console Log Files" for guidance on log lifecycle and cleanup.

Port Conflicts and Service State
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the loopback service cannot bind to its configured port, it exits. If you then start the service again without waiting for the previous process to fully release the port, you may see lock errors because two instances are competing to write to the database file.

1. Check which process holds the configured loopback port. The default port is 9187::

    PS> Get-NetTCPConnection -LocalPort 9187 -State Listen

   The ProcessId column shows which process is listening. If it is not the current instance of the service, a previous instance may not have fully shut down.

2. On Unix-like hosts::

    $ lsof -i :9187

3. If a stale process is using the port, terminate it carefully. On Windows::

    PS> Stop-Process -Id <ProcessId> -Force

   Note the process name and ID before terminating it. If it is not the service, investigate why that process was running.

4. Wait at least 5 seconds before restarting the service. The operating system needs time to release the port and close file handles.

5. If you are unsure about the port number, check "Default Loopback Port Numbers and How to Change Them" or the service startup configuration.

Lock Investigation Steps
------------------------

**Section Owner:** Ines Carrow

If you have verified disk space, checked the console log, and confirmed no port conflicts, the lock error is likely due to another process holding the database file open or a file system driver interfering with the lock operation.

Step 1: Isolate Which Process Holds the Lock
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Windows, use the Resource Monitor built-in tool:

1. Press ``Win+R``, type ``resmon.exe``, and press Enter.
2. Click the **Handles** tab.
3. In the search field, enter the full path to the database file, for example::

    C:\Users\billy\AppData\Local\auditlog\auditlog.db

4. The grid will show which process (by PID and name) has a handle to that file.

On Unix-like hosts::

    $ lsof | grep auditlog.db

   or::

    $ fuser auditlog.db

If the database file is not listed in the output, the lock is either very transient (the service released it immediately) or the database file does not exist yet. Create the database file manually by running a non-write operation against it, such as querying the schema.

Step 2: Verify File Access Controls
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lock errors can also occur if the process user cannot write to the file or its parent directory, even if no other process holds the lock.

On Windows::

    PS> Get-Acl "C:\Users\$env:USERNAME\AppData\Local\auditlog\auditlog.db" | Format-List

   Look for the "Access" list. The current user should have "FullControl" or at least "Modify" and "Write" capabilities.

On Unix-like hosts::

    $ ls -la ~/.auditlog/auditlog.db

   The output should show read and write access for the owner (user), such as ``-rw-r--r--`` (0644) or ``-rw-------`` (0600). If the access levels are more restrictive, update them::

    $ chmod u+w ~/.auditlog/auditlog.db

Step 3: Check for Antivirus and Backup Service Interference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Antivirus software, backup agents, and indexing services often open files for exclusive access to scan or copy them. This can block the service from acquiring a write lock, even if no other user process holds it.

On Windows:

1. Open Windows Defender (or your antivirus software) and check the quarantine log for recent file detections. If the database file was quarantined, restore it or whitelist it.

2. Check Task Scheduler for backup or indexing jobs. Press ``Win+R``, type ``taskschd.msc``, and review scheduled tasks that may run during peak hours when you see lock errors.

3. If you use a backup agent (Carbonite, Backblaze, Acronis, etc.), check its logs or settings. Add the database directory to the exclusion list::

    C:\Users\<username>\AppData\Local\auditlog\*

   The exact procedure varies by vendor. Contact your IT department if you do not manage the backup agent.

4. Disable Windows Search indexing for the database directory:

   - Right-click the parent folder and select **Properties**.
   - Click **Advanced**.
   - Uncheck "Allow files in this folder to have contents indexed in addition to file properties" and click **OK**.

On Unix-like hosts, check for running backup or indexing processes::

    $ ps aux | grep -i backup
    $ ps aux | grep -i rsync
    $ ps aux | grep -i tar

If these are running and copying files near the database file, ask the system manager to exclude the database directory from their backup or indexing jobs.

Worked Example: Diagnosing a Lock Error on Windows
---------------------------------------------------

**Problem:** The service fails to write a new record with error "database is locked". The error occurs every few minutes during the morning.

**Investigation:**

1. Check disk space::

    PS> Get-Volume -DriveLetter C | Select-Object {$_.SizeRemaining / 1GB}

   Result: 45 GB free. Not full.

2. Check console log for recent errors::

    PS> Get-Content "C:\Users\billy\AppData\Local\auditlog\console.log" -Tail 50

   Output (last 20 lines)::

    2025-04-19 09:23:17 INFO Started service on port 9187
    2025-04-19 09:24:02 WARNING database is locked (attempt 1 of 3)
    2025-04-19 09:24:07 WARNING database is locked (attempt 2 of 3)
    2025-04-19 09:24:12 ERROR database is locked; write failed

3. Check for a stale service process::

    PS> Get-NetTCPConnection -LocalPort 9187 -State Listen
    
   ProcessId : 4021
   
   The service is listening on 9187. No conflict.

4. Open Resource Monitor and search for handles to ``C:\Users\billy\AppData\Local\auditlog\auditlog.db``. 

   Result: Two processes show open handles:
   - ``auditlog.exe`` (PID 4021) — the service itself
   - ``OneDrive.exe`` (PID 5344) — the cloud sync agent

5. OneDrive is scanning the database file for changes to sync. This is a known cause of lock contention.

**Resolution:**

Exclude the database directory from OneDrive sync:

1. Right-click the **OneDrive** icon in the system tray and select **Settings**.
2. Click **Sync and backup**.
3. Click **Manage sync** and find the local folder containing the database.
4. Uncheck it to stop syncing.

Alternatively, move the database file to a location that is not synced by OneDrive::

    PS> New-Item -ItemType Directory -Force "C:\LocalData\auditlog"
    PS> Move-Item "C:\Users\billy\AppData\Local\auditlog\auditlog.db" "C:\LocalData\auditlog\auditlog.db"

Then update the service configuration file to point to the new location.

After moving the file, the lock errors ceased.

Terminology
-----------

**Database file**
  The SQLite database on disk where the service persists all records. By default, this file is named ``auditlog.db`` and is stored in a subdirectory of the user's home folder.

**File handle**
  An operating system resource that represents an open file. Each open file occupies one file handle. The Resource Monitor and ``lsof`` tools show which processes hold handles to a given file.

**Lock timeout**
  The duration the service waits for SQLite to acquire a write lock before giving up. If the timeout elapses and the lock is still not available, the service returns a lock error to the caller.

**Loopback service**
  The HTTP service component of the package that listens on a loopback interface (127.0.0.1 or localhost) and responds to requests with a port number defined in the configuration.

**Parent directory**
  The folder containing the database file. For example, if the database file is ``C:\Users\billy\AppData\Local\auditlog\auditlog.db``, the parent directory is ``C:\Users\billy\AppData\Local\auditlog``.

**Read-only**
  A file attribute or setting that allows reading the file but not modifying it. If a file is read-only and the process needs to write, SQLite returns an error.

**Write lock**
  SQLite's exclusive lock acquired when writing a new record. Only one process can hold the write lock at a time. If another process holds it, subsequent writers must wait or time out.

**inode table**
  On Unix-like systems, a data structure tracking all files on the file system. If the inode table is full, the system cannot create new files, even if disk space remains. Use ``df -i`` to check inode usage.

Files and Paths Referenced
---------------------------

.. list-table::
   :header-rows: 1

   * - File or Path
     - Function
   * - ``C:\Users\<username>\AppData\Local\auditlog\auditlog.db``
     - Windows default location of the SQLite database file
   * - ``~/.auditlog/auditlog.db``
     - Unix default location of the SQLite database file (varies by installation)
   * - ``C:\Users\<username>\AppData\Local\auditlog\console.log``
     - Windows console log; search here for the exact error timestamp
   * - ``disk-usage-thresholds.yaml``
     - Configuration file defining which disk utilization percentage triggers a warning
   * - ``docs/operations-runbooks/sqlite-file-locking.md``
     - Low-level details on SQLite's locking mechanism and WAL mode

Tools and Versions
-------------------

.. list-table::
   :header-rows: 1

   * - Tool
     - Version
     - Use
   * - SQLite
     - 3.44.0
     - Database engine; linked into the Python runtime
   * - Python
     - 3.10+
     - Package runtime
   * - Resource Monitor (resmon.exe)
     - Windows 10 build 19045
     - Identify which process holds a file handle on Windows
   * - lsof
     - 4.95.0+ (Unix)
     - List open files by process on Unix-like systems
   * - fuser
     - GNU findutils 4.9+
     - Identify which process uses a file on Unix-like systems

Related Pages
-------------

- `operations-runbooks Overview <README.md>`_
- `Diagnosing Port Conflicts for the Loopback Service <port-conflicts.md>`_
- `Checking Disk Space Around the Database File <disk-space-checks.md>`_
- `Managing the Service's Console Log Files <console-log-files.md>`_
- `Handling SQLite File Locking on the Database File <sqlite-file-locking.md>`_
- `Host Monitoring for auditlog Hosts <host-monitoring-overview.md>`_
- `Copying the Database File for Backup <database-file-backup-copy.md>`_
- `Default Loopback Port Numbers and How to Change Them <loopback-port-defaults.md>`_
- `Workstation and Small Host Upkeep Overview <workstation-host-upkeep-overview.md>`_
- `Weekly Host Monitoring Checklist <host-monitoring-checklist.txt>`_
- `Verifying a Copied Database File <backup-copy-verification.rst>`_

Change Log
----------

**v2.0 — 2025-04-19**
  Added worked example for OneDrive sync interference. Reorganized Steps to prioritize file system checks. Updated SQLite version to 3.44.0.

**v1.9 — 2025-03-02**
  Clarified inode table exhaustion as a rare but possible cause. Updated Resource Monitor instructions for Windows 11 compatibility. Improved terminology definitions.

**v1.8 — 2025-02-27**
  Split lock investigation into discrete steps. Removed redundant sections overlapping with ``sqlite-file-locking.md``. Owner changed from Dez Whitfield to Ines Carrow per team reorganization.

**v1.7 — 2025-01-12**
  Added section on backup agent exclusion. Clarified difference between "database is locked" and "unable to open database file" error messages.

**v1.6 — 2024-12-15**
  Updated tool versions. Added lsof version recommendation for Unix systems. Fixed incorrect path example for Unix systems.

**v1.5 — 2024-11-08**
  Initial documentation. Covered port conflicts, disk space, console logs, and basic lock investigation steps.

# Locating oauthsvc Files on a Host

| | |
|---|---|
| **Title** | Locating oauthsvc Files on a Host |
| **Version** | 1.5 |
| **Owner** | Developer Experience (Ines Kovac) |
| **Last Updated** | 2024-05-30 |

## Overview

When running the oauthsvc service on a workstation or small server, configuration files, console logs, the SQLite database file, and temporary state scatter across your filesystem. This page maps out where the package installs itself, where to find its log files, where the database lives, and how to account for disk usage. It serves as the ground truth for locating any oauthsvc-related file or directory on a given host.

The service uses a loopback HTTP port (configurable) and writes to a SQLite database file. The database file itself is the main piece of state to monitor and protect; log files may grow without bound. Both Python's package installation and the runtime state have fixed, discoverable locations.

## Standard Installation Paths

**Section owner: Platform Tools (Mara Olsen)**

### Package Location

The oauthsvc package installs as any other Python package in your environment's site-packages directory. The actual location depends on your Python installation and virtual environment setup.

On Windows with a virtual environment:
```
C:\Users\<username>\venv\Lib\site-packages\oauthsvc\
```

On macOS or Linux with a virtual environment:
```
/home/<username>/.venv/lib/pythonX.Y/site-packages/oauthsvc/
/opt/venv/lib/pythonX.Y/site-packages/oauthsvc/
```

On a system-wide installation (Linux/macOS):
```
/usr/local/lib/pythonX.Y/site-packages/oauthsvc/
```

Within the oauthsvc package directory, you will find the main module files and a scripts/ subdirectory for helper utilities. Users should not edit files inside site-packages directly.

To locate your package on the current system, run:

This returns the absolute path to the installed package.

### Configuration and Runtime State

The service stores its runtime state and database in a user-specific or system-specific directory. The location is determined by environment variables or defaults:

**Windows:**
```
C:\Users\<username>\AppData\Local\oauthsvc\
```

**macOS:**
```
/Users/<username>/Library/Application Support/oauthsvc/
```

**Linux (user install):**
```
~/.local/share/oauthsvc/
~/.config/oauthsvc/
```

**Linux (system install):**
```
/var/lib/oauthsvc/
/etc/oauthsvc/
```

Consult the README.md in the package directory or run the command-line help for your specific installation's setup. The runtime path can be overridden by setting a service home environment variable before starting the service.

```
Set the service home environment variable to point to a custom directory path, such as /custom/path/to/svc/state, before launching.
```

## Database File Location

The SQLite database file lives in the runtime state directory (see above). On most installations, it is named:

```
oauthsvc.db
```

Full path examples:

**Windows:**
```
C:\Users\alice\AppData\Local\oauthsvc\oauthsvc.db
```

**Linux (user):**
```
/home/alice/.local/share/oauthsvc/oauthsvc.db
```

**Linux (system):**
```
/var/lib/oauthsvc/oauthsvc.db
```

This file must exist and be readable by the service process. If it does not exist, the service will create it on first run. The file size grows as the service stores data over time. Typical databases range from a few MB to several hundred MB depending on usage patterns and local configuration.

**Important:** Do not modify or remove the database file while the service is running. See the related page "Diagnosing SQLite File Locking on a Host" for troubleshooting locking issues.

Locate the database file on the current host:

```
find ~ -name "oauthsvc.db" 2>/dev/null
find /var -name "oauthsvc.db" 2>/dev/null
find /opt -name "oauthsvc.db" 2>/dev/null
```

On Windows:
```powershell
Get-ChildItem -Path "C:\Users" -Recurse -Filter "oauthsvc.db" -ErrorAction SilentlyContinue
Get-ChildItem -Path "C:\ProgramData" -Recurse -Filter "oauthsvc.db" -ErrorAction SilentlyContinue
```

## Console Log Files

**Section owner: Desktop Engineering (Theo Baptiste)**

When the service runs, it writes console output (stdout and stderr) to log files. The exact location depends on how the service was started and by whom.

### Interactive Console Sessions

If you start the service in the foreground from a terminal, output appears in that terminal. No separate log file is created unless you capture output elsewhere:


### Background Service (systemd on Linux)

When the service runs under systemd, logs are captured by the journal:

```
journalctl -u oauthsvc -n 100
journalctl -u oauthsvc --since "2 hours ago"
```

### Background Service (Windows)

On Windows, if oauthsvc runs as a service, check the Event Viewer under Windows Logs > Application for messages tagged with the service name.

### User-Defined Log Files

The service can be configured to write logs to a specific file. Check your startup script or systemd unit file for a `StandardOutput=file:` or similar directive. Common patterns:

**Linux:**
```
/var/log/oauthsvc/console.log
/var/log/oauthsvc/service.log
/home/<user>/.local/share/oauthsvc/logs/
```

**Windows:**
```
C:\Users\<user>\AppData\Local\oauthsvc\logs\
C:\ProgramData\oauthsvc\logs\
```

Log files may grow without bound. See the related page "Managing the Service's Console Log Files" for log cycling and cleanup procedures.

## Port and Loopback Service

**Section owner: Host Operations (Derek Yun)**

The service runs a loopback HTTP server on a configurable port, defaulting to 9876 on most systems. The port is bound only to the loopback interface (127.0.0.1 or ::1), not to a public network interface.

To find which port the service is listening on, use:

**Linux/macOS:**
```
lsof -i -P -n | grep oauthsvc
netstat -tulpn | grep LISTEN
ss -tulpn | grep ":9876"
```

**Windows (PowerShell):**
```powershell
netstat -ano | findstr ":9876"
Get-NetTCPConnection -LocalPort 9876 -ErrorAction SilentlyContinue
```

If the port is already in use by another process, the service will fail to start. Refer to the related page "Resolving Port Conflicts on the Loopback Service" for diagnosis and remediation.

## Disk Space and Usage Patterns

The main sources of disk usage are:

- **The database file** — grows with stored data, typically 50 MB to 500 MB
- **Console logs** — can grow rapidly if verbose logging is enabled; may reach 1–10 GB
- **Temporary files** — caches, work directories, etc.; usually under 100 MB

To estimate disk usage for the service:

**Linux/macOS:**
```
du -sh ~/.local/share/oauthsvc/
du -sh ~/.config/oauthsvc/
du -sh /var/lib/oauthsvc/
```

**Windows (PowerShell):**
```powershell
(Get-ChildItem -Path "C:\Users\$env:USERNAME\AppData\Local\oauthsvc\" -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB
```

For guidance on disk space monitoring and cleanup, see "Disk Space Checks for the Host" and "Cleaning Up Temporary Files Left on the Host".

## SQLite File Locking

The database file is protected by SQLite's internal locking mechanism. When the service reads or writes, a lock is held briefly. If the service crashes or the host loses power, stale lock files may remain:

**Possible lock-related files:**
- `oauthsvc.db`
- `oauthsvc.db-shm`
- `oauthsvc.db-wal`

The `-shm` (shared memory) and `-wal` (write-ahead log) files are created automatically by SQLite and should be left alone. They are cleaned up when the service shuts down cleanly.

Do not remove these files while the service is running. If you suspect a lock issue, check the status using sqlite3:

```
sqlite3 /var/lib/oauthsvc/oauthsvc.db ".mode line" "PRAGMA integrity_check;"
```

For comprehensive guidance, see "Diagnosing SQLite File Locking on a Host".

## Host Monitoring

**Section owner: Systems Reliability (Priya Nandan)**

To keep oauthsvc running smoothly:

- **Process presence:** Ensure the oauthsvc process is running. Use `ps aux | grep oauthsvc` (Linux) or Task Manager (Windows).
- **Port binding:** Verify that the loopback port is still bound (see Port and Loopback Service section above).
- **Database consistency:** Periodically verify the database hasn't been corrupted by running SQLite's built-in consistency check.
- **Disk space:** Monitor the runtime state directory to ensure the database does not fill the disk.
- **Log file size:** Check console log files for rapid growth, which may indicate a misconfiguration or issue.

See "Host Monitoring Basics for oauthsvc" for automated monitoring setups and metrics to collect.

## Backing Up and Copying the Database

To protect against data loss, copy the database file regularly. Always stop the service before copying:

```
# Stop the service
systemctl stop oauthsvc

# Copy the database
On Linux/macOS systems, you can back up the database file by copying it to a backup directory with a timestamped filename.

# Start the service
systemctl start oauthsvc
```

On Windows, use PowerShell:
```powershell
Stop-Service oauthsvc
On Windows, you can back up the database file located in the AppData\Local directory to a backup folder with a date-based filename.
Start-Service oauthsvc
```

See "Copying the Database File for Backup" and "Restoring a Copied Database File" for detailed procedures.

## Terminology and Glossary

| Term | Definition |
|------|-----------|
| **Loopback interface** | A network interface (127.0.0.1 on IPv4, ::1 on IPv6) that only the local host can reach. The service binds its HTTP listener to this interface only. |
| **site-packages** | The directory where Python packages are installed. Location depends on your Python environment (virtualenv, system Python, etc.). |
| **Virtual environment** | An isolated Python installation created with `python -m venv`. Each virtual environment has its own site-packages directory and installed packages. |
| **Runtime state directory** | The directory where oauthsvc stores runtime data, including the database file and configuration. Typically in the user's home directory or a system directory like /var/lib/. |
| **Database file** | The SQLite database file (oauthsvc.db) that stores all persistent state. Must be readable and writable by the service process. |
| **Console log** | Text output captured from the service's stdout and stderr, typically written to a file or captured by journalctl. |
| **Port binding** | The act of a network service listening on a specific TCP or UDP port. oauthsvc binds to the loopback interface on a configurable port. |
| **WAL file** | Write-ahead log file (oauthsvc.db-wal) created by SQLite to improve performance and crash safety. Automatically managed by SQLite. |
| **Shared memory file** | File (oauthsvc.db-shm) used by SQLite for inter-process communication and memory-mapped I/O. Automatically managed by SQLite. |
| **Journalctl** | Linux utility that queries and displays logs captured by systemd's journal. Used to view service logs on modern Linux distributions. |

## File and Path Reference

| Path or File | Purpose |
|---|---|
| `oauthsvc/` | The package directory in the repository root; contains the main module code and scripts/ subdirectory. |
| `docs/` | Documentation directory; contains operations runbooks and user guides. |
| `scripts/` | Helper scripts for deployment, setup, and maintenance tasks. |
| `C:\Users\<user>\AppData\Local\oauthsvc\` (Windows) | Runtime state directory on Windows; contains database and logs. |
| `/home/<user>/.local/share/oauthsvc/` (Linux) | User-level runtime state directory on Linux. |
| `/var/lib/oauthsvc/` (Linux) | System-level runtime state directory on Linux. |
| `/Users/<user>/Library/Application Support/oauthsvc/` (macOS) | Runtime state directory on macOS. |
| `oauthsvc.db` | SQLite database file; stored in the runtime state directory. |
| `oauthsvc.db-wal` | Write-ahead log file created by SQLite; stored alongside oauthsvc.db. |
| `oauthsvc.db-shm` | Shared memory file created by SQLite; stored alongside oauthsvc.db. |
| `console.log`, `service.log` | Console log files; location depends on startup method and configuration. |
| `~/.bashrc`, `~/.bash_profile` (Linux/macOS) | Shell configuration files where the service home environment variable can be set. |
| `systemd unit file` (Linux) | Service definition file (e.g., `/etc/systemd/system/oauthsvc.service`); defines how the service starts and where logs go. |

## Tools and Versions

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.8+ | Required to run oauthsvc. The package uses only the standard library. |
| sqlite3 | 3.22+ | Command-line tool for inspecting and validating the database file. Included on most systems. |
| journalctl | — | Linux utility for reading systemd journal logs. Available on any systemd-based Linux distribution. |
| lsof | 4.80+ | Unix/Linux utility for listing open files and network connections. Used to find port bindings. |
| netstat | — | Network statistics tool; available on Windows, macOS, and Linux. |
| ss | — | Linux socket statistics tool; modern replacement for netstat. |
| PowerShell | 5.1+ | Windows shell; includes network diagnostic cmdlets like Get-NetTCPConnection. |
| git | 2.20+ | Used to check out the repository and review documentation. |

## Changelog

| Date | Version | Release | Author | Notes |
|---|---|---|---|---|
| 2024-05-30 | 1.5 | v1.5 | Ines Kovac | Added disk usage section; clarified Windows path examples. Updated version in header. |
| 2024-03-15 | 1.4 | v1.4 | Mara Olsen | Expanded SQLite file details; added shared memory and WAL file descriptions. |
| 2023-12-20 | 1.3 | v1.3 | Derek Yun | Added PowerShell examples for Windows; improved port detection commands. |
| 2023-10-05 | 1.2 | v1.2 | Theo Baptiste | Reorganized to separate package location from runtime state; added journalctl section. |
| 2023-07-12 | 1.1 | v1.1 | Priya Nandan | Added monitoring section; linked to related pages. |
| 2023-04-30 | 1.0 | v1.0-initial | Ines Kovac | Initial publication covering basic file locations and terminology. |

## Related Pages

- [Operations Runbooks Overview](README.md) — High-level guide to this runbook collection.
- [Resolving Port Conflicts on the Loopback Service](port-conflicts-on-the-loopback-service.md) — Detailed steps for diagnosing and fixing port binding issues.
- [Disk Space Checks for the Host](disk-space-checks.md) — Procedures for monitoring and managing disk usage.
- [Managing the Service's Console Log Files](console-log-files.md) — Log cycling, compression, and cleanup.
- [Diagnosing SQLite File Locking on a Host](sqlite-file-locking.md) — Troubleshooting database locks and corruption.
- [Host Monitoring Basics for oauthsvc](host-monitoring-basics.md) — Setting up ongoing process and resource monitoring.
- [Copying the Database File for Backup](copying-the-database-file.md) — Procedures for creating safe database backups.
- [Restoring a Copied Database File](restoring-a-database-file-copy.rst) — How to restore from a backup.
- [Starting the Service at Host Boot](starting-the-service-at-boot.rst) — Configuring systemd or Windows services to start oauthsvc automatically.
- [Cleaning Up Temporary Files Left on the Host](cleaning-up-temporary-files.md) — Identifying and removing cache and work files.
- [Checking Host Clock and Timestamps](checking-host-clock-and-timestamps.txt) — Verifying system time accuracy, important for service operation.
- [Running Multiple oauthsvc Installations on One Host](multiple-installations-on-one-host.txt) — How to run more than one instance with different data directories.
- [Host Upkeep Checklist](host-upkeep-checklist.yaml) — Regular maintenance tasks to keep oauthsvc running smoothly.

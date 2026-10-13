# Operations Runbooks Overview

**Title:** Operations Runbooks Overview  
**Version:** 1.0  
**Owner:** Platform Tools (Mara Olsen)  
**Last Updated:** 2026-05-12  

## Summary

This folder contains runbooks for host upkeep around the oauthsvc package on a workstation or small server. Each runbook covers a specific operational concern: port conflicts, disk space management, console log files, SQLite file locking, host monitoring, and database backup and restore procedures.

These runbooks are meant for teams who deploy oauthsvc on individual hosts and need step-by-step guidance for common operational tasks. They do not cover deployment itself or broader infrastructure concerns; see the main README.md for deployment guidance and the docs/ folder for package-level documentation.

The runbooks assume you have basic familiarity with your host's operating system and command-line tools. Cross-platform guidance is provided where procedures differ between Linux, Windows, and Unix-like systems.

## How to Use This Folder

**Section Owner:** Developer Experience (Ines Kovac)

Each runbook stands alone but many reference one another. If you are new to maintaining oauthsvc on a host, begin with [Locating oauthsvc Files on a Host](#locating-oauthsvc-files-on-a-host) to understand the file layout, then consult the Host Upkeep Checklist for a recommended sequence of tasks.

Runbooks are organized into three groups below: immediate response procedures (troubleshooting), ongoing maintenance (regular tasks), and reference material (setup and background). Many runbooks overlap in coverage—for example, both disk space checks and temporary file cleanup affect available disk space—so read related pages listed at the end of each runbook. Links between runbooks are bidirectional; if one runbook mentions another, that runbook's related-pages section will mention the first.

The Repository root holds the operations-runbooks folder alongside docs/, scripts/, oauthsvc/, and README.md. All paths mentioned in these runbooks are relative to the data directory configured for your host; the Locating oauthsvc Files runbook explains how to find that directory for your specific setup.

### When to Consult Immediate Response Procedures

Immediate response runbooks should be consulted when:
- The service fails to start or crashes unexpectedly
- The service hangs or becomes unresponsive
- Files become locked or inaccessible
- Network port errors appear in logs or on startup

These runbooks provide troubleshooting steps and restoration procedures.

### When to Perform Ongoing Maintenance

Ongoing maintenance runbooks describe preventive tasks and monitoring that should be performed on a regular schedule—daily, weekly, or monthly depending on the runbook. These tasks catch problems early before they affect service availability. The Host Upkeep Checklist groups these by frequency.

### When to Use Reference Material

Reference runbooks provide background information, file layouts, and setup procedures. Consult these when setting up a new host, configuring automatic startup, or working with multiple instances.

## Immediate Response Procedures

**Section Owner:** Host Operations (Derek Yun)

These runbooks tackle problems that require immediate investigation or intervention. Follow these if the service is unavailable, unresponsive, or reporting errors.

- [Resolving Port Conflicts on the Loopback Service](port-conflicts-on-the-loopback-service.md) — v2.3, Derek Yun, 2025-11-04. The loopback service fails to start or responds only intermittently. This runbook covers binding errors, port reuse, process cleanup, and how to identify which process holds the port.

- [Diagnosing SQLite File Locking on a Host](sqlite-file-locking.md) — v2.0.1, Mara Olsen, 2026-03-15. The database file becomes locked for long periods, causing the service to hang or time out. Covers identification of locks, diagnosis of which process holds the lock, and resolution of stuck locks.

- [Checking Host Clock and Timestamps](checking-host-clock-and-timestamps.txt) — v4.0, Priya Nandan, 2024-10-05. Host clock skew can cause timing anomalies and service issues. This runbook covers checking the current system clock, diagnosing clock drift, and correcting clock skew on both Windows and Unix-like systems.

These three procedures handle the most common causes of service unavailability on a workstation or small host. Start with the port conflicts runbook if you see binding errors; start with the SQLite locking runbook if the service starts but hangs when accessing the database.

## Ongoing Maintenance and Monitoring

**Section Owner:** Systems Reliability (Priya Nandan)

These runbooks describe regular tasks and monitoring that prevent problems or catch them early. Incorporate these into a regular maintenance schedule, with frequency noted in each runbook and summarized in the Host Upkeep Checklist.

- [Disk Space Checks for the Host](disk-space-checks.md) — v1.4.0, Priya Nandan, 2025-02-18. Monitor disk usage and identify what occupies space. Includes guidance on typical space used by the package and the database file, when to expect growth, and thresholds for alerting. Recommended weekly or monthly depending on usage.

- [Host Monitoring Basics for oauthsvc](host-monitoring-basics.md) — v3.1, Priya Nandan, 2025-06-30. Configure basic monitoring of host health metrics: CPU utilization, memory usage, disk I/O, and service process uptime. Covers log aggregation integration points and recommended alerting thresholds. For ongoing observability.

- [Managing the Service's Console Log Files](console-log-files.md) — v1.0, Theo Baptiste, 2024-08-22. The service writes console output and diagnostic messages to a log file. This runbook covers log file locations, how to read log contents, log file management, and lifecycle guidance. Note that this is distinct from the database file.

- [Cleaning Up Temporary Files Left on the Host](cleaning-up-temporary-files.md) — v2.1.0, Theo Baptiste, 2025-04-11. The service may leave temporary files after restarts or errors, or if interrupted during startup. This runbook identifies what is safe to remove and what should be left in place. Safe to run monthly. (See also version 2.0, Mara Olsen, 2024-09-30, which covers edge cases in multi-instance setups.)

Disk space and log file management are the most time-intensive maintenance tasks on a long-running host. Plan for regular review of both.

## Backup, Restore, and Boot-Time Setup

**Section Owner:** Desktop Engineering (Theo Baptiste)

These runbooks cover initialization, backup procedures, and restoration. Perform backup procedures on a regular schedule; see the Disk Space Checks runbook for space requirements.

- [Copying the Database File for Backup](copying-the-database-file.md) — v1.2.3, Derek Yun, 2024-12-01. Step-by-step procedure for creating a safe backup copy of the database file while the service is running or stopped. Includes guidance on backup frequency, naming conventions, and storage location for copies.

- [Restoring a Copied Database File](restoring-a-database-file-copy.rst) — v2.0, Derek Yun, 2025-09-19. Restore from a backup copy of the database file. Covers when restoration is necessary, validation procedures, and repair of partial or corrupted files. Should be performed only when the original file is damaged.

- [Starting the Service at Host Boot](starting-the-service-at-boot.rst) — v3.0.0, Theo Baptiste, 2026-01-08. Configure the service to start automatically when the host boots. Covers systemd unit files for Linux hosts and Windows startup tasks for Windows hosts. Necessary for unattended operation.

The backup and restore procedures should be verified before relying on them; consider a dry run on a staging host.

## Reference and Multi-Host Setups

**Section Owner:** Platform Tools (Mara Olsen)

These runbooks provide reference information and guidance for special setups. Consult these when setting up a new host or working with advanced configurations.

- [Locating oauthsvc Files on a Host](locating-oauthsvc-files-on-a-host.md) — v1.5, Ines Kovac, 2024-05-30. Describes the standard file layout and where oauthsvc stores the database file, configuration, log files, and temporary files on a host. Start here if you are unfamiliar with the host layout or need to find a specific file.

- [Host Upkeep Checklist](host-upkeep-checklist.yaml) — v2.4, Ines Kovac, 2025-07-14. A quick checklist of daily, weekly, and monthly upkeep tasks. Each item links to a runbook and indicates frequency. Use this to plan your maintenance schedule.

- [Running Multiple oauthsvc Installations on One Host](multiple-installations-on-one-host.txt) — v1.0.2, Mara Olsen, 2026-06-20. Guidance on running more than one instance of the service on the same host without port conflicts or interference. Covers configuration, database isolation, and monitoring multiple instances.

The Locating Files runbook should be your first stop when setting up a new host. The checklist provides a practical maintenance schedule. The multi-instance runbook is necessary only if your host runs more than one copy of the service.

## Terminology and Glossary

**Section Owner:** Systems Reliability (Priya Nandan)

- **Loopback Service:** The HTTP service embedded in oauthsvc that listens on a loopback network interface (127.0.0.1 on most hosts). It does not accept external network connections and is accessible only from the local host. Also called the "loopback interface" or "local service."

- **Database File:** A local SQLite file that stores the oauthsvc service state and persistent data. Typically named oauthsvc.db and located in a data directory on the host. This file persists across service restarts and must be backed up to prevent data loss.

- **SQLite File Locking:** A mechanism by which SQLite prevents concurrent writes to the database file and ensures consistency. When locked by one process, other processes cannot read or modify the database until the lock is released. Locks normally release within milliseconds; stuck or long-held locks indicate a problem.

- **Console Log File:** A file containing the standard output and standard error streams of the service process. The service writes diagnostic messages, startup information, and error traces here. Different from the database file and typically smaller.

- **Host Upkeep:** Regular maintenance tasks performed on the host running oauthsvc: monitoring disk space, checking clock synchronization, backing up the database, cleaning temporary files, and reviewing logs. Preventive upkeep reduces downtime and data loss.

- **Workstation or Small Host:** A machine running oauthsvc for a single user, team, or department, as opposed to a large shared infrastructure deployment or cloud service. These runbooks assume this scale and single-digit instance counts.

- **Port Binding:** The process of an HTTP service opening a network port and listening for incoming connections. A port conflict occurs when two services attempt to bind to the same port simultaneously; only one can succeed.

- **Temporary Files:** Files created by oauthsvc or the host during normal operation that are not part of the persistent state. These files may be safely removed if the service is not running and may be regenerated on next startup.

- **File Lock:** An operating-system mechanism preventing multiple processes from modifying a file at the same time. SQLite uses file locks internally to coordinate access to the database file; the operating system manages these locks transparently.

- **Service State:** The collective data stored in the database file that defines the current operational state of oauthsvc. This state persists across restarts. Loss of this file results in loss of that state; backup procedures protect it.

## Referenced Files and Paths

**Section Owner:** Developer Experience (Ines Kovac)

These files and directories are referenced across runbooks in this folder. Paths may vary by host configuration; see the "Locating oauthsvc Files on a Host" runbook for instructions on finding each item on your specific host.

| File or Path | Purpose |
|---|---|
| oauthsvc/ | Package directory in the repository root. Contains the service source code and is not modified by normal operation. |
| docs/ | Documentation folder in the repository root. Contains package-level documentation, architecture notes, and configuration schema. |
| scripts/ | Scripts folder in the repository root. Contains utility scripts for maintenance, diagnostics, and one-time setup tasks. |
| operations-runbooks/ | This folder. Operational procedures for host-level upkeep around oauthsvc. |
| {data-dir}/oauthsvc.db | The SQLite database file containing service state. Location varies by host and configuration; typically in a data subdirectory under the installation path or user home directory. Critical: must be backed up. |
| {log-dir}/console.log | Console log file written by the service during startup and operation. Location varies by host; typically in a log subdirectory. Can grow large over time and should be managed. |
| {temp-dir}/ | Temporary directory where the service may create working files. Contents vary and can be safely removed when the service is stopped. |
| ~/.bashrc, ~/.profile, or equivalent | Shell configuration files used to set environment variables for service startup on Unix-like hosts. May define DATA_DIR, LOG_DIR, or other paths. |
| /etc/systemd/system/oauthsvc.service | SystemD unit file on Linux hosts. Defines how systemd starts and manages the service at boot and handles restarts. |
| C:\ProgramData\oauthsvc\ | Windows data directory (example path). Typical location for database and log files on Windows hosts; exact path depends on installation. |
| README.md | Main package README in the repository root. High-level overview, installation instructions, and links to docs. |

## Tools and Versions

**Section Owner:** Host Operations (Derek Yun)

These tools and libraries are referenced in one or more runbooks. Versions listed are the minimum or recommended versions at the time of the last update to this index.

| Tool or Library | Version | Notes |
|---|---|---|
| sqlite3 (CLI) | 3.30+ | Command-line tool used to inspect and manipulate the database file directly. Installed by default on most Unix-like systems. Available via Windows Subsystem for Linux or standalone installers on Windows. |
| Python | 3.9+ | oauthsvc requires Python 3.9 or later to run. Used to execute the service process. Environment should have Python in PATH. |
| systemd | 230+ | On Linux hosts, systemd is the init system that starts and manages the service, handles boot-time startup, and manages restarts on failure. |
| Windows Task Scheduler | Windows 7+ | On Windows hosts, Task Scheduler is the system service that starts and manages the service at boot and handles restarts. Built-in; no installation required. |
| lsof (list open files) | Any recent | Unix utility to list open files and identify which process holds a file lock. Useful for diagnosing SQLite locking issues. Often pre-installed; installable via package manager. |
| ps (process status) | Any recent | Standard Unix utility to list running processes and their resource use (CPU, memory). Included on all Unix-like systems. |
| du (disk usage) | Any recent | Unix utility to measure directory and file sizes. Useful for identifying what occupies disk space. |
| df (disk free) | Any recent | Unix utility to report total and available disk space on mounted filesystems. Used in disk space checks. |

## Change Log

**2026-06-20 — Release 1.0 (Final)**  
First stable release of the operations-runbooks index. All linked runbooks reviewed and cross-referenced. Updated guidance for disk space thresholds and boot-time startup across Windows and Linux hosts. Reorganized sections for clarity.

**2026-05-12 — Release 0.9.5 (Draft for Review)**  
Added section owners to each group for accountability. Revised the quick-start guidance to direct new users to the Locating Files runbook first, then the Host Upkeep Checklist. Incorporated feedback from Derek Yun on backup procedures and Priya Nandan on host monitoring thresholds.

**2026-04-01 — Release 0.9.3**  
Reorganized runbook groups for clarity and readability. Added separate sections for immediate response (troubleshooting), ongoing maintenance (preventive), and reference material. Updated version numbers and last-modified dates for all linked runbooks.

**2026-02-15 — Release 0.8.0**  
Initial draft structure. Includes organization into groups and a basic index of runbooks. Added terminology section and file/path reference table.

**2025-12-10 — Release 0.7.2 (Pre-Release)**  
Planning phase. Coverage defined, team members assigned, and runbook outline created.

**2025-11-20 — Release 0.5.0 (Early Planning)**  
Kickoff meeting with Platform Tools, Host Operations, and Systems Reliability. Determined that operations runbooks are needed for host-level upkeep around oauthsvc on workstations and small servers.

## Contributing to This Folder

To add or update a runbook:

1. **Use a clear filename:** Describe the runbook topic in lowercase with hyphens. Examples: checking-host-clock-and-timestamps.txt or copying-the-database-file.md.

2. **Add a standard header block:** Every runbook must include title, version, owner, and last-updated date at the top. Use the format shown in existing runbooks in this folder.

3. **Include key sections:** Each runbook should have:
   - Section headings with an order suited to the content
   - Section owners named for one or more sections
   - A terminology or glossary section defining at least eight terms
   - A listing of referenced files and host paths with their purposes
   - A table of tools or libraries with versions, if applicable
   - A change log with at least six dated entries naming releases
   - A related-pages section at the end

4. **Link back to this index:** Add a related-pages section at the end that includes a link to this README.

5. **Update this index:** Edit this README to list the new or updated runbook under the appropriate group (Immediate Response, Ongoing Maintenance, or Reference). Include title, version number, owner, and last-updated date.

6. **Keep dates consistent:** When updating an existing runbook, increment the version number and update the last-modified date. Update this index accordingly.

## Related Pages

- README.md — Main package README in the repository root. High-level overview and installation instructions.
- docs/ — Package documentation folder. Architecture, configuration schema, and package-level guidance.
- scripts/ — Utility scripts folder. Helper scripts for setup, diagnostics, and maintenance.

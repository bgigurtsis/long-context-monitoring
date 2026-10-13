# operations-runbooks Overview

**Title:** operations-runbooks Overview
**Version:** 1.6
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2026-04-02

**Summary:** This page is the folder index for `docs/operations-runbooks/`. It lists every page in the folder, names the runbook that covers each area of host upkeep for the eventlog package, and records the version, owner, and last-updated date of each page as of the date above. If a page and this index disagree on a version number or a title, treat the sibling page itself as correct — this index is updated on a slower cadence than the pages it points to.

---

## About This Folder (Section Owner: Mara Olsen)

The auditlog package is small — a command line, a loopback HTTP service, and a single SQLite database file — but the host it runs on still needs the same kind of upkeep any long-running process needs: something has to watch the port, the disk, the console log files, the database file's lock behavior, and the general health of the host. This folder collects the runbooks that cover those areas, written for whoever is on call for a workstation running auditlog for local use, or for a small host (a home server or a low-power box) keeping the service up for longer stretches.

Nothing in this folder describes what the package's commands do, what the service's HTTP interface accepts, or what shape the database file's records take. That material lives elsewhere. This folder is strictly about keeping the host underneath the package in good shape.

Pages in this folder come in a few formats — Markdown pages, one reStructuredText page pair, one YAML configuration reference, and two plain-text reference sheets. All of them are treated as first-class pages for the purposes of this index: each carries the same header block (title, version, owner, last-updated date), and each is expected to keep a change log and a related-pages section, whatever its file extension.

## How to Use This Index

Skim the grouped tables below to find the page that matches the upkeep problem in front of you. The groupings follow the six areas named in this page's summary — port conflicts, disk space, console log files, SQLite file locking, host monitoring, and database file backup copies — plus a seventh group for the one page that predates those groupings and still covers workstation and small-host upkeep in general terms.

Each table row gives:

- the page's title as it appears in that page's own header block,
- the relative link to open it,
- its version string (note that some pages use a bare number like `1.4` and others use a `v`-prefixed string like `v1.1.3` — this is inconsistent across the folder and has not been standardized),
- its owner, and
- the date it was last updated.

If you only need one page, jump to the group heading that matches your problem. If you're new to on-call for auditlog hosts, read `workstation-host-upkeep-overview.md` first — it's the closest thing this folder has to a starting point.

## Page Index by Area (Section Owner: Mara Olsen)

### Port and Network Upkeep

The loopback service binds to a local port on start. On a workstation this is rarely a problem because the machine reboots often and few other processes compete for a fixed port; on a small host that stays up for weeks, other services accumulate and port conflicts become the more common complaint.

| Title | File | Version | Owner | Last Updated |
|---|---|---|---|---|
| Diagnosing Port Conflicts for the Loopback Service | [port-conflicts.md](./port-conflicts.md) | v1.3.0 | Infra Reliability (Dez Whitfield) | 2025-11-14 |
| Default Loopback Port Numbers and How to Change Them | [loopback-port-defaults.md](./loopback-port-defaults.md) | 1.2 | Infra Reliability (Dez Whitfield) | 2024-05-11 |

### Disk Space and Storage

Because the database file, the console log files, and any backup copies all live on the same host, disk space upkeep touches every other area in this folder. Two pages cover it: a runbook for checking disk space around the database file, and the YAML file that holds the actual threshold numbers referenced by that runbook.

- [Checking Disk Space Around the Database File](./disk-space-checks.md) — version 2.1, owner Systems Engineering (Owen Baptiste), last updated 2025-06-30.
- [Disk Usage Threshold Settings](./disk-usage-thresholds.yaml) — version v1.0.1, owner Systems Engineering (Owen Baptiste), last updated 2025-09-30.

### Console Log Files

The service and the command line each write their own console log files rather than relying solely on whatever the OS captures. These two pages cover managing those files day to day and knowing when a given file's size is worth a second look.

1. [Managing the Service's Console Log Files](./console-log-files.md) — version 1.4, owner Developer Experience (Priya Chandrasekaran), last updated 2024-09-18.
2. [Console Log File Size Reference](./console-log-file-sizes.txt) — version 1.0, owner Developer Experience (Priya Chandrasekaran), last updated 2024-12-01.

### SQLite File Locking

The database file is a single SQLite file with no server process in front of it, so lock behavior is entirely a function of how many things on the host try to open it at once. These pages describe what normal locking looks like and how to work through the less normal cases.

| Title | File | Version | Owner | Last Updated |
|---|---|---|---|---|
| Handling SQLite File Locking on the Database File | [sqlite-file-locking.md](./sqlite-file-locking.md) | v1.1.3 | Platform Tools (Ines Carrow) | 2025-02-27 |
| Troubleshooting SQLite Lock Errors | [sqlite-lock-troubleshooting.rst](./sqlite-lock-troubleshooting.rst) | 2.0 | Platform Tools (Ines Carrow) | 2025-04-19 |

### Host Monitoring

General health-of-the-host watching — CPU, memory, disk, and whether the service's process is still running — is covered by an overview page and a short weekly checklist meant to be worked through in a few minutes.

- [Host Monitoring for auditlog Hosts](./host-monitoring-overview.md) — version 1.0.1, owner Infra Reliability (Sam Okafor), last updated 2026-01-09.
- [Weekly Host Monitoring Checklist](./host-monitoring-checklist.txt) — version v1.3.0, owner Infra Reliability (Sam Okafor), last updated 2026-02-01.

### Backup and Database File Copies

Because the database file is a single file on disk, keeping a backup copy is mostly a matter of copying it correctly — closing out any open handle first, choosing a moment when the file isn't mid-write, and checking the copy afterward.

| Title | File | Version | Owner | Last Updated |
|---|---|---|---|---|
| Copying the Database File for Backup | [database-file-backup-copy.md](./database-file-backup-copy.md) | 2.3 | Platform Tools (Mara Olsen) | 2025-08-05 |
| Verifying a Copied Database File | [backup-copy-verification.rst](./backup-copy-verification.rst) | v1.0.2 | Platform Tools (Mara Olsen) | 2026-05-20 |

### Foundational Overview

- [Small Host and Workstation Upkeep Overview](./workstation-host-upkeep-overview.md) — version 1.5, owner Systems Engineering (Owen Baptiste), last updated 2024-07-08.

This page's title was shortened during an editing pass sometime after Owen's last update to it; the file itself now opens with "Workstation and Small Host Upkeep Overview." Whichever title you see when you open the page is the current one.

## Port Conflicts, in Brief (Section Owner: Dez Whitfield)

A loopback service can only hold a given port once. If something else on the host — another local tool, a leftover process from a prior run that never exited cleanly, or an entirely unrelated piece of local software — is already bound to the port eventlog wants, the service will fail to start or will start on a fallback port that nothing expects it on. On a workstation this shows up as "the service won't start" right after a reboot when some other local tool takes the port first. On a small host it shows up weeks into uptime, after some other long-running process was added to the same box.

The two pages in the port group cover the diagnosis side (what a bound port looks like from the outside, and how to find out what's holding it) and the configuration side (what the default port numbers are and how someone changes them if a fixed conflict can't be resolved by just waiting for the other process to release it).

## Disk Space, in Brief (Section Owner: Owen Baptiste)

Disk space around auditlog is really three things sharing one filesystem: the database file itself, the console log files sitting next to it, and any backup copies kept locally before they're moved somewhere else. None of these grow without bound on their own — the database file grows with use, console log files grow until something manages them, and backup copies pile up if nobody clears older ones out. `disk-space-checks.md` walks through where to look and what commands to run; `disk-usage-thresholds.yaml` holds the numeric thresholds that page's checks are written against, expressed as percentages of the filesystem the database file lives on.

## Console Log Files, in Brief (Section Owner: Priya Chandrasekaran)

The service writes a console log file that records what it did on each run — start-up, shutdown, and anything unusual in between — separately from any OS-level event log. On a workstation these files are small and short-lived because the service starts and stops often. On a small host, where the service can run for weeks between restarts, a single console log file can grow large enough to matter for disk space on its own, which is why `console-log-file-sizes.txt` exists as a quick sizing reference next to the fuller management page.

## SQLite File Locking, in Brief (Section Owner: Ines Carrow)

Because the database file is a plain SQLite file with no server process brokering access to it, every process that opens it for write — the command line and the service both qualify — takes a lock directly on the file for the moment it needs one. Under normal single-host, single-user use this is invisible; it becomes visible the moment two things try to write at once, or when a copy operation opens the file at the wrong moment. `sqlite-file-locking.md` describes what normal lock behavior looks like on this file; `sqlite-lock-troubleshooting.rst` is the deeper page for when a lock error actually shows up and needs to be worked through.

## Host Monitoring, in Brief (Section Owner: Sam Okafor)

Host monitoring here means the ordinary things: is the process still running, is the host's CPU and memory in a normal range, is the disk under the thresholds set in `disk-usage-thresholds.yaml`, and are the console log files being kept in check. `host-monitoring-overview.md` lays out the general approach and what tools to reach for on a workstation versus a small host; `host-monitoring-checklist.txt` is the short list meant to be worked through once a week rather than read end to end.

## Backup Copies, in Brief (Section Owner: Mara Olsen)

A backup copy of the database file is just a duplicate of that one file, made somewhere other than its working location — another folder on the same host, an external drive, or a shared location reachable from the host. The two pages in this group cover making the copy (closing any open handle first, picking a quiet moment, and copying the whole file rather than part of it) and checking afterward that the copy opened cleanly and isn't missing anything a straight file copy could have left out.

## Terminology

- **Loopback service** — the HTTP service that ships with the package, bound only to the local host's own network interface rather than to any externally reachable one.
- **Console log file** — the plain text file the service or the command line writes describing its own run, distinct from anything the operating system logs on its own.
- **Database file** — the single SQLite file on disk where the package keeps its on-disk records.
- **Lock contention** — the situation where more than one process on the host wants write access to the database file at the same moment.
- **Disk usage threshold** — a configured percentage or byte count of used disk space on the filesystem holding the database file, past which a check is expected to flag the host.
- **Host monitoring** — the ongoing practice of watching a host's CPU, memory, disk space, and running processes rather than any one-time check.
- **Workstation** — a single-user machine, usually a laptop or desktop, where auditlog runs for local, personal use and is expected to start and stop often.
- **Small host** — a lightweight, often single-purpose machine — a home server or a low-power box — where auditlog is expected to keep running for extended stretches between restarts.
- **Backup copy** — a duplicate of the database file kept somewhere other than the file's working folder.
- **Port conflict** — a state where the port the loopback service wants to bind is already held by another process on the same host.
- **File handle** — an operating-system-level reference a running process holds open on a file, which can block certain operations on that file (including some copy operations) until it's closed.
- **Staging copy** — an intermediate copy of the database file made in a local folder before that copy is moved to its final backup location.

## Files and Paths Referenced in This Folder

| Path | Purpose |
|---|---|
| `auditlog/` | The package directory at the repository root; the source tree these runbooks operate around without describing. |
| `README.md` | The repository root readme; points into `docs/` for anything beyond a quick start. |
| `docs/operations-runbooks/` | This folder; holds every page indexed above. |
| `docs/operations-runbooks/README.md` | This page — the folder index. |
| `scripts/check-disk-space.ps1` | A small helper script referenced from `disk-space-checks.md` for running the disk usage check against the thresholds in `disk-usage-thresholds.yaml`. |
| `scripts/copy-database-file.ps1` | A helper script referenced from `database-file-backup-copy.md` that wraps a straightforward file copy with a check for an open handle beforehand. |
| `%LOCALAPPDATA%\auditlog\logs\` (Windows workstation) | The default folder where the service's console log files land when auditlog runs under a normal user profile. |
| `/var/log/auditlog/` (small host, Linux) | The equivalent console log folder on a small host running a Linux-based OS. |
| `%LOCALAPPDATA%\auditlog\db\` (Windows workstation) | The default folder holding the database file on a workstation install. |
| `/var/lib/auditlog/` (small host, Linux) | The equivalent database file folder on a small host. |

## Tools and Utilities Referenced Across This Folder

| Tool / Package | Version Seen in This Folder | Used For |
|---|---|---|
| Python | 3.11.7 | Running the package itself; the only language runtime these runbooks assume is present. |
| sqlite3 (command-line shell) | 3.44.0 | Opening the database file directly to check lock state or run a manual pragma. |
| PowerShell | 5.1 (Windows built-in) / 7.4 (pwsh, optional) | Running the helper scripts and most of the shell snippets in the sibling pages. |
| git | 2.43 | Versioning the docs folder itself; not used by the package. |
| Robocopy | Windows built-in | The preferred tool for copying the database file on Windows hosts, referenced in the backup group. |
| rsync | 3.2.7 | The equivalent copy tool on Linux small hosts. |
| du / df | GNU coreutils, host default | Checking disk space from a shell on Linux hosts. |
| WinDirStat | 2.2.2 | A visual disk space tool sometimes used on workstations instead of shell commands. |
| Handle (Sysinternals) | 4.22 | Checking whether a process holds an open handle on the database file before a copy, on Windows. |
| lsof | host default | The Linux equivalent of Handle, used to check open file descriptors on the database file. |
| Task Scheduler | Windows built-in | Running any scheduled disk-space or log-size check on a Windows small host. |
| cron | host default | The Linux equivalent scheduler for the same checks. |

## Change Log

- **2024-05-11 — v1.0:** Folder created with the first three pages: `port-conflicts.md`, `loopback-port-defaults.md`, and `workstation-host-upkeep-overview.md`.
- **2024-09-20 — v1.1:** Added `console-log-files.md` and `console-log-file-sizes.txt`; grouped the index into headings for the first time instead of a flat list.
- **2025-02-28 — v1.2:** Added `sqlite-file-locking.md` after a lock error on a shared small host prompted the first dedicated page for it.
- **2025-06-30 — v1.3:** Added `disk-space-checks.md` and `disk-usage-thresholds.yaml`; split the disk space group out from the general host monitoring text that had covered it up to this point.
- **2025-08-06 — v1.4:** Added `database-file-backup-copy.md`; folded a short backup mention out of `workstation-host-upkeep-overview.md` since it now had its own page.
- **2025-11-15 — v1.5:** Added `sqlite-lock-troubleshooting.rst` alongside the existing locking page; updated the port group's dates after Dez's update to `port-conflicts.md`.
- **2026-01-10 — v1.5.1:** Added `host-monitoring-overview.md` and `host-monitoring-checklist.txt`; renamed the "General Upkeep" heading to "Host Monitoring" to match.
- **2026-04-02 — v1.6:** Added `backup-copy-verification.rst`; reworded the summary at the top of this page and reordered the grouped tables to match the order named in the summary.

## Contribution Guide (Section Owner: Mara Olsen)

Adding a page to this folder is straightforward:

1. Give it the standard header block — title, version, owner, and last-updated date — at the very top, whatever the file format.
2. Add it to the right group in the **Page Index by Area** section above, or start a new group heading if it doesn't fit an existing one.
3. Bump this page's own version number and add a line to the change log naming the page you added.
4. Include a terminology section, a file/path listing, a tools table, a change log, and a related-pages section on the new page itself — every page in this folder is expected to carry all six, not just the Markdown ones.
5. If you're renaming an existing page's title rather than adding a new one, update that page's own header first; this index will catch up on its next update, which may lag by a release or two.

Small wording fixes to an existing page don't need a version bump here — bump the sibling page's own version instead and let this index pick it up next time someone touches it.

## Related Pages

- Diagnosing Port Conflicts for the Loopback Service
- Default Loopback Port Numbers and How to Change Them
- Checking Disk Space Around the Database File
- Disk Usage Threshold Settings
- Managing the Service's Console Log Files
- Console Log File Size Reference
- Handling SQLite File Locking on the Database File
- Troubleshooting SQLite Lock Errors
- Host Monitoring for auditlog Hosts
- Weekly Host Monitoring Checklist
- Copying the Database File for Backup
- Verifying a Copied Database File
- Workstation and Small Host Upkeep Overview

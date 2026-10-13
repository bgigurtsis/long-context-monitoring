# Default Loopback Port Numbers and How to Change Them

**Version:** 1.2
**Owner:** Infra Reliability (Dez Whitfield)
**Last updated:** 2024-05-11

## Overview

auditlog ships as a small standard-library-only Python package with a command line and a loopback HTTP service that keeps its records in a local SQLite file. On a workstation or a small shared host, the service binds to a fixed loopback interface and port at startup. Most of the time nobody thinks about the port at all — it's just there, quietly serving requests from the local machine — until something else on the host wants the same number, or until a maintainer needs to run two copies of the service side by side (one against a working database file, one against a day-old copy used for spot checks).

This page documents the default port the service uses out of the box, the places on disk where that default is recorded, and the three supported ways a maintainer can move it aside. It also covers, at a lighter level, how the port choice interacts with the other pieces of host upkeep that this folder documents: port conflicts proper, disk space around the database file, the service's own console log files, SQLite file locking, host monitoring, and copying the database file for backup. Those topics each have their own page in this folder; this page only goes as deep into them as the port number touches.

If you're new to the team, read `workstation-host-upkeep-overview.md` first — it frames all of the runbooks in this folder, including this one.

## Terminology

- **Loopback interface** — the network interface a host uses to talk to itself, conventionally 127.0.0.1 on IPv4. auditlog's HTTP service only ever binds here; it does not listen on any interface reachable from another host.
- **Bind** — the act of a process claiming a port number on a given interface so that it, and only it, can accept connections there.
- **Port** — a 16-bit number (1–65535) that, together with an interface, identifies where a process is listening.
- **Default port** — the port number the service uses when no override is present in the config file or the environment.
- **Override** — a config file setting or environment variable that replaces the default port with a maintainer-chosen one.
- **Ephemeral port** — a short-lived, operating-system-assigned port from the high end of the range (typically 49152–65535), used by outgoing connections; not what auditlog listens on, but sometimes confused with it.
- **Config file** — the small plain-text file auditlog reads at startup for host-specific settings, including the port.
- **Console log** — the plain-text file the service writes its own startup and shutdown lines to; covered in depth by `console-log-files.md`.
- **Database file** — the single SQLite file where auditlog keeps its records, referenced throughout this folder simply as "the database file."
- **Stale bind** — a port that appears occupied because a previous process instance did not shut down cleanly, even though nothing is currently listening.
- **Instance** — one running copy of the service; a host can run more than one instance at a time as long as each uses a distinct port and a distinct database file.

## Default Port Assignment

Out of the box, the service binds to the loopback interface on port **8765**. This has been the default since the package's early releases and has not changed in the current major line.

| Setting | Value | Where it lives |
|---|---|---|
| Default interface | 127.0.0.1 | hard-coded in the package; not overridable |
| Default port | 8765 | `auditlog/` package defaults |
| Config file override key | `port` | `~/.auditlog/service.cfg` (Linux/macOS) or `%USERPROFILE%\.auditlog\service.cfg` (Windows) |
| Environment variable override | `LOGSVC_PORT` | shell environment, takes precedence over the config file |
| Console log line at startup | `listening on 127.0.0.1:<port>` | first line the service writes after the config file is read |

Note that the interface itself is not configurable — logsvc will never bind to a non-loopback interface on this host class, by design of the package, and that falls outside what this page covers.

If port 8765 is already bound by something else when the service starts, the service does not try again and does not fall back to a nearby port on its own; it exits and the console log records why. See "Interaction with the Console Log Files" below for what that line looks like.

## Why the Service Binds Only to Loopback

The service is meant to be reached only from processes running on the same workstation or small host — the command line, a local script, or a browser open on that same machine. Binding to loopback rather than to all interfaces keeps the service out of the picture entirely for anything arriving over the network, which simplifies host upkeep considerably: there's no port to open in a host firewall, no interface to pick among several, and no interaction with whatever else the host's network configuration is doing. It also means port conflicts on this host are strictly local — two processes on the *same* machine fighting over the *same* number — rather than something that could show up differently depending on which network interface a caller used.

## Changing the Port

*(Section owner: Dez Whitfield)*

There are two supported ways to move the port, in order of how the service resolves them:

1. Environment variable `LOGSVC_PORT` — checked first, wins if set.
2. `port` key in the config file — checked if the environment variable is absent.

If neither is present, the service falls back to 8765.

### Through the Config File

The config file is a small INI-style file. On most workstations it lives at:

- Linux/macOS: `~/.auditlog/service.cfg`
- Windows: `%USERPROFILE%\.auditlog\service.cfg`

A minimal entry that moves the port to 8901 looks like this:

```
[service]
port = 8901
```

If the file or the `[service]` section doesn't exist yet, create it — the service reads whatever is present and applies its own defaults for anything missing. Save the file, then restart the service through whatever your usual startup method is on this host (scheduled task, startup item, or manual start from a terminal — this varies by workstation and isn't standardized across the team yet).

Worked example — moving a workstation off the default because a local Jupyter install has claimed 8765 on port bump day:

1. Open `~/.auditlog/service.cfg` in a text editor.
2. Add or edit the `[service]` block:
   ```
   [service]
   port = 8801
   ```
3. Save and close the file.
4. Restart the auditlog service.
5. Confirm the new port is listening (see verification steps below).
6. Update any local scripts or shortcuts that assumed 8765.

### Through an Environment Variable

Setting `LOGSVC_PORT` is useful for a one-off run — for example, spinning up a second instance temporarily against a copied database file without touching the config file that the primary instance reads.

On PowerShell, for the current session only:

```powershell
$env:LOGSVC_PORT = "8902"
```

On a POSIX shell:

```bash
export LOGSVC_PORT=8902
```

Because the environment variable takes precedence over the config file, this is also the fastest way to check whether a port problem is coming from a stale config file entry — set the variable to a known-free port, restart, and see if the problem follows.

To make the override stick across reboots on Windows, set it as a user environment variable through System Properties rather than only in a single PowerShell session, or add the `export` line to your shell's startup file on Linux/macOS.

### Picking a New Number

There's no team-wide convention yet for which numbers to use when moving off 8765 — pick anything outside the well-known range (below 1024) and outside your host's ephemeral range. A loose convention some of us follow, worth writing down here even though it isn't enforced:

- 8765 — default, leave alone unless it's occupied.
- 8766–8770 — reserved informally for a second, third, etc. instance on the same host (spot-check copies, side-by-side version comparisons).
- Anything else above 1024 and below 49152 — fine for a workstation-specific override, as long as it doesn't collide with something else that host runs regularly.

### Running Two Instances on One Host

Each instance needs its own port *and* its own database file — pointing two instances at the same database file while using two different ports does not avoid the file-locking behavior described in `sqlite-file-locking.md`; it just adds a second process contending for the same file lock in addition to the port question. If you need a second instance for a side-by-side check, copy the database file first (see "Backup Copy Considerations" below) and point the second instance's config file or environment variable at both the copy and a distinct port.

## Verifying What's Listening

Before changing anything, and after, it's worth confirming what's actually bound to a given port on the loopback interface. These are general operating-system utilities, not auditlog commands.

On Windows (PowerShell):

```powershell
Get-NetTCPConnection -LocalPort 8765 -LocalAddress 127.0.0.1
```

or the older but still common:

```powershell
netstat -ano | findstr "8765"
```

The trailing number in the `netstat` output is the process ID; cross-reference it with Task Manager or `Get-Process -Id <pid>` to confirm which process actually holds the port.

On Linux/macOS:

```bash
lsof -i :8765
```

or

```bash
ss -ltnp | grep 8765
```

A stale bind — where the port looks occupied but the process behind it is long dead — usually clears on its own within a short interval after the operating system reclaims the socket, but if it persists, ending the stale process is the more reliable fix over waiting.

## Interaction with Port Conflicts

This page covers what the default is and how to move it; the deeper diagnostic steps for figuring out *what else* has taken 8765 (or any override) live in `port-conflicts.md`. The short version worth repeating here: on a typical developer workstation, the numbers most likely to collide with a hand-picked override are ones used by other local tooling — notebook servers, small local web frameworks, and container tooling all tend to cluster in the 3000–9000 range. A quick table of common local occupants, kept here because it's useful at the moment of picking a new port and not everyone reads the conflicts page first:

| Port | Commonly used by |
|---|---|
| 3000 | Node-based local dev servers |
| 5000 | Local Flask-style dev servers |
| 8000 | Simple local static file servers |
| 8080 | Various local proxies and management consoles |
| 8888 | Jupyter notebook servers |
| 9000 | Various local build/watch tooling |

None of these are reserved for auditlog in any way; they're listed only because they're the numbers most likely to already be busy when you go looking for a free one.

## Interaction with Disk Space

The port number itself takes essentially no disk space — the config file that holds the override is a handful of bytes. The connection worth noting here is indirect: a maintainer running a second instance to inspect a copied database file (which requires picking a second port, per "Running Two Instances on One Host" above) has now also doubled the number of console log files and added a full copy of the database file to disk. On a small host where `disk-space-checks.md` already flags the database file's directory as worth watching, a temporary second instance temporarily draws on that same disk budget and should be cleaned up — config file entry, database file copy, and console log — once the side-by-side check is done.

## Interaction with the Console Log Files

Every time the service starts, the very first thing it writes to its console log is the interface and port it bound to, for example:

```
2026-09-14 09:02:11 listening on 127.0.0.1:8765
```

If the port was already bound by something else, the console log instead records a line describing the bind failure and the process exits without ever writing the "listening on" line at all. This is the fastest way to confirm, after the fact, which port a given run actually used — more reliable than trusting memory or an old note taped to a monitor, especially on a host that's had its config file edited more than once.

Because the console log records the port on every single startup, a host that restarts the service often (for instance, during repeated port changes while troubleshooting) will accumulate a lot of very short-lived log entries. `console-log-files.md` covers the file sizes and format in full; the only note worth adding here is that a burst of startup/shutdown cycles while hunting for a free port is a normal, expected source of a temporarily busier console log, not a sign of a problem with the service itself.

## Interaction with SQLite File Locking

The port and the database file's lock are two independent mechanisms, and it's worth being explicit about that because the two are easy to conflate. Binding a port does not, by itself, lock the database file, and holding the database file's lock does not reserve any port. In practice they move together because a single instance normally does both at once, but the failure modes are different:

- A **port conflict** stops the service from starting at all — you never get as far as the database file being opened.
- A **file lock conflict** (covered in `sqlite-file-locking.md`) can happen even after the service has successfully bound its port, if some other process — a second instance, a manual `sqlite3` session, a backup script — is holding the database file open at the same moment.

When two instances are run deliberately (see "Running Two Instances on One Host"), giving each a distinct port is necessary but not sufficient — each also needs its own database file, or its own copy, to avoid file-locking contention. A quick way to confirm a database file isn't already open elsewhere before starting a second instance:

```bash
fuser ~/.auditlog/auditlog.db
```

or on Windows, check the handle through Resource Monitor's "Associated Handles" search for the file name.

## Host Monitoring Hooks

If this host has any local monitoring set up per `host-monitoring-overview.md`, a check that confirms the service is listening on its expected port is one of the simplest and most useful things to include. A minimal PowerShell check suitable for a scheduled task:

```powershell
$conn = Get-NetTCPConnection -LocalPort 8765 -LocalAddress 127.0.0.1 -ErrorAction SilentlyContinue
if (-not $conn) {
    Write-Warning "auditlog is not listening on 127.0.0.1:8765"
}
```

If the host has been moved to a non-default port through a config file override, remember to update the port number in this check as well — a stale monitoring check that still watches 8765 after everyone agreed to move the host to 8801 will fire a false warning every time it runs and eventually get ignored, which defeats the point of having it. During the March 2026 workstation sweep, two hosts were found running happily on 8766 (the service had, in fact, fallen back to the next free port automatically that quarter) while their local monitoring checks were still pointed at 8765 and had been quietly failing for weeks — worth keeping in mind if a check on this host seems to be reporting the service down when it clearly isn't.

`host-monitoring-checklist.txt` includes a line item for confirming the expected port on a weekly basis; this page is the source of truth for what "expected" should mean for a given host.

## Backup Copy Considerations

Copying the database file for backup, per `database-file-backup-copy.md`, doesn't touch the port at all, but there's a sequencing point worth calling out here: if the service is stopped before the copy (the safer of the two documented approaches on the backup page), restarting it afterward should bind the same port it had before, as long as neither the config file nor the environment variable changed in between. It's easy, when stopping a service for a backup copy, to also decide "while it's down, let's move the port too" — resist doing both at once. If the copy needs to be verified afterward and the port also changed at the same moment, it becomes harder to tell whether an unexpected result came from the copy itself or from the port change, and separating the two makes troubleshooting either one considerably simpler.

If a second instance is started against the copied database file to verify it (see `backup-copy-verification.rst`), that instance needs its own port per "Running Two Instances on One Host" above — pointing the verification instance at the same port as the primary instance will simply fail to bind, and the console log will record that failure rather than anything about the copy itself.

## Files and Paths Referenced

| Path | Purpose |
|---|---|
| `auditlog/` | package directory; holds the built-in default port value, not edited for routine port changes |
| `README.md` | repository root readme; general package overview |
| `~/.auditlog/service.cfg` (Linux/macOS) | per-user config file; holds the `port` override key |
| `%USERPROFILE%\.auditlog\service.cfg` (Windows) | same config file, Windows path |
| `~/.auditlog/auditlog.db` | default database file location |
| `~/.auditlog/logs/console.log` | default console log file; first line of each run records the bound port |
| `docs/operations-runbooks/` | folder holding this page and its sibling runbooks |
| `scripts/set-loopback-port.ps1` | local helper script some maintainers use to edit the config file's `port` key without opening an editor by hand |
| `scripts/check-loopback-port.ps1` | local helper script wrapping `Get-NetTCPConnection` for a quick pass/fail on the expected port |
| `host-monitoring-checklist.txt` | weekly checklist; includes the "confirm expected port" line item this page defines |

## Tools and Packages

| Tool / package | Version used on team workstations | Purpose |
|---|---|---|
| Python | 3.11.8 | runs the package; no third-party dependencies required |
| auditlog | current internal build | the package this whole folder documents |
| PowerShell | 7.4 | verification and helper scripts on Windows hosts |
| sqlite3 CLI | 3.45.1 | manual inspection of the database file when checking file locks alongside a port change |
| lsof | 4.94.0 (macOS/Linux builds vary) | confirming what process holds a port or a file handle |
| Resource Monitor | built into Windows 10/11 | Windows equivalent for checking file handles when `lsof` isn't available |

## Change Log

| Date | Version | Change |
|---|---|---|
| 2023-01-16 | 1.0 | Initial page: documented default port 8765 and the config file override. |
| 2023-06-02 | 1.0.1 | Added environment variable override (`LOGSVC_PORT`) after several maintainers asked for a way to override without editing the config file. |
| 2023-11-20 | 1.1 | Added "Running Two Instances on One Host" following recurring questions during side-by-side database file checks. |
| 2024-02-08 | 1.1.1 | Added verification commands for Windows and Linux/macOS. |
| 2024-04-30 | 1.1.2 | Added the common local port table under "Interaction with Port Conflicts." |
| 2024-05-11 | 1.2 | Added host monitoring hook example and the note about the March 2026 workstation sweep; clarified backup copy sequencing. |

## Related Pages

- "operations-runbooks Overview" — folder-level index for this and every sibling page.
- "Diagnosing Port Conflicts for the Loopback Service" (v1.4) — deeper diagnostic steps when a port, default or overridden, turns out to be occupied.
- "Checking Disk Space Around the Database File" — disk budget guidance that a second, temporary instance also draws against.
- "Managing the Service's Console Log Files" (updated 2024-09-19) — full detail on the console log format this page only samples.
- "Handling SQLite File Locking on the Database File" — the file-lock behavior that runs alongside, but independently of, the port.
- "Host Monitoring for auditlog Hosts" — the broader monitoring setup that the port check in this page plugs into.
- "Copying the Database File for Backup" — sequencing notes for stopping the service before a copy.
- "Weekly Host Monitoring Checklist" — includes the expected-port line item this page defines the value for.
- "Verifying a Copied Database File" — relevant when a second, differently-ported instance is used to check a backup copy.
- "Workstation and Small Host Upkeep Overview" — the top-level framing page for this entire folder.

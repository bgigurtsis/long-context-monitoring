# Diagnosing Loopback Port Conflicts

| Field | Value |
|-------|-------|
| **Title** | Diagnosing Loopback Port Conflicts |
| **Version** | 2.1 |
| **Owner** | Host Operations (Devon Price) |
| **Last Updated** | 2025-01-18 |

## Overview

When the accountsvc service fails to start with a "port already in use" error, or when the loopback HTTP listener crashes unexpectedly, a port conflict has occurred. Another process on the same workstation or small host is already bound to the port that accountsvc expects to listen on. This runbook walks you through finding the conflicting process, understanding why it's present, and resolving the conflict without disrupting normal service operation or other running applications.

Port conflicts are among the most common operational issues on development workstations and small host deployments. Unlike larger infrastructure, a single machine running multiple services means shared network resources and a higher probability of collision.

## Coverage

This page covers loopback port conflicts specifically—conflicts on `localhost` or `127.0.0.1`. It does not cover network-facing (external) port bindings, firewall rules, or network interface configuration. For broader host health and monitoring context, see the host monitoring page.

The procedures assume a Windows 10 workstation or a small single-machine host running Linux or Windows, where accountsvc is the primary service. Multi-machine deployments should consult your infrastructure team.

## Finding the Conflicting Process

### Windows Workstations (PowerShell)

The most reliable method on Windows is the `netstat` command, which lists all active network connections and listening ports.

```
netstat -anob
```

The flags mean:
- `-a`: Show all connections and listening ports
- `-n`: Display host and port numbers in numerical form
- `-o`: Include the process identifier (PID) for each connection
- `-b`: Show the executable name associated with each connection

Run this in PowerShell with elevated access. The output is verbose; filter for the port accountsvc uses (commonly port 8080) to find your conflict:

```
netstat -anob | findstr :8080
```

This returns one or more lines like:

```
  TCP    127.0.0.1:8080         0.0.0.0:0              LISTENING       2944
  TCP    [::1]:8080             [::]:0                 LISTENING       2944
```

The PID `2944` appears on the right. Cross-reference it with the task manager or use `Get-Process`:

```
Get-Process -Id 2944
```

Output example:
```
Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id  SI ProcessName
-------  ------    -----      -----     ------     --  -- -----------
    120       8    15232      18404       0.05   2944   1 python
```

The executable is `python` running as PID 2944. Open Task Manager (`Taskmgr.exe`) and locate this process to see its full command line and parent process. Note the working directory if visible.

### Linux / Small Hosts (Bash)

On Linux, use `lsof` (list open files) or `ss` (socket statistics), both showing process names and port bindings:

```
sudo lsof -i :8080
```

Output:
```
The output lists process command, process identifier, owning user, file descriptor, connection protocol type, network interface details, size metric, and node designation.
python3    5521   root   17u  IPv4   123456      0t0  TCP localhost:8080 (LISTEN)
python3    5521   root   18u  IPv6   123457      0t0  TCP [::1]:8080 (LISTEN)
```

The PID is `5521`. Check its details:

```
ps aux | grep 5521
```

Or use `ss` for a more structured output:

```
sudo ss -tlnp | grep 8080
```

This shows the listening socket, protocol (TCP), and the process PID and name.

## Understanding the Cause

Once you have identified the process, determine what it is and why it is running. Common scenarios:

| Process | Likely Cause | Action |
|---------|--------------|--------|
| Another instance of accountsvc | Supervisor restarted it, or an old process did not terminate cleanly | Check supervisor logs; see *startup-and-shutdown.rst* |
| IDE development server (Flask, Django, etc.) | Developer left their local server running in the background | Contact the developer or close their IDE session |
| Node.js / npm dev server | JavaScript development tool left running | Check the working directory; alert the developer |
| Java application or build tool | Another service or CI tool on the machine | Coordinate with the team running that application |
| System service or daemon | OS-level service auto-started at boot | Verify it is necessary; disable if redundant |
| Verification process runner | Automated verification or monitoring process still running | Check scheduled tasks (Windows) or cron (Linux) |

### Checking for Multiple accountsvc Instances

The most common cause is that accountsvc has crashed or hung, but the supervisor process (if configured) has not yet restarted it, or two supervisors are managing the same service:

On Windows, verify only one accountsvc instance is present:

```
Get-Process python | Where-Object { $_.ProcessName -eq "python" }
```

On Linux:

```
ps aux | grep accountsvc
```

Look for duplicate processes or processes with identical command lines. If you see two running accountsvc services, one is likely the old crashed process and one is the new restart. Proceed to **Resolving the Conflict** below.

If the conflicting process is unrelated to accountsvc, decide whether to terminate it, move it to a different port, or reconfigure accountsvc to use an alternate port.

## Resolving the Conflict

### Option 1: Terminate the Conflicting Process (Preferred if Safe)

If the conflicting process is dead or extraneous, terminate it cleanly:

**Windows (PowerShell):**

```
Stop-Process -Id 2944
```

Verify it has stopped:

```
Get-Process -Id 2944 -ErrorAction SilentlyContinue
```

If no output appears, the process has exited.

**Linux:**

```
sudo kill 5521
```

Wait a few seconds and check:

```
sudo lsof -i :8080
```

If the port is now free, proceed to restart accountsvc via its supervisor. See *process-supervision.rst* for the correct restart procedure on your host.

If the process does not respond to `SIGTERM`, use `kill -9`:

```
sudo kill -9 5521
```

### Option 2: Change the Service Port

If the conflicting process is legitimate and in use, configure accountsvc to listen on a different loopback port. Configuration is typically stored in a local settings file or environment variable (consult your host's setup guide or the filesystem layout page). After reconfiguring the port, restart accountsvc and verify the new port is listening:

**Windows:**

```
netstat -anob | findstr :8081
```

**Linux:**

```
sudo lsof -i :8081
```

If the port is now in use and accountsvc is listening, the conflict is resolved. Update any application code, monitoring scripts, or documentation that referenced the old port.

### Option 3: Restart the Supervisor (Nuclear Option)

If you cannot cleanly terminate the process or identify the conflict, restarting the supervisor process will kill all children and perform a full service restart:

**Windows (if using a Windows Service or Task Scheduler):**

Open Task Scheduler (`taskschd.msc`) and disable then re-enable the accountsvc task. Or, restart the service via Services (`services.msc`).

**Linux (if using systemd):**

```
sudo systemctl restart accountsvc
```

This forcefully terminates all accountsvc processes and restarts the supervisor, clearing port bindings. Use only if other methods fail, as it may interrupt ongoing operations. Coordinate with accountsvc users beforehand.

## Preventing Port Conflicts

### Use a Non-Standard Port

Development workstations often run multiple services. Consider configuring accountsvc to use port 8888 or 9090 rather than the common port 8080. Fewer applications bind to these ports, reducing collision probability.

### Enable Socket Reuse

Modern operating systems support the `SO_REUSEADDR` socket option, which allows a process to bind to a port shortly after the previous process releases it, avoiding a lingering `TIME_WAIT` state. The accountsvc service has this option enabled by default; no configuration is required.

### Isolate Development Environments

If running multiple accountsvc instances for different projects on the same workstation, use containers (Docker) or virtual machines to isolate each instance and its port bindings. See *workstation-vs-small-host.md* for guidance on multi-instance setups.

### Regular Port Monitoring

On shared hosts, periodically check port assignments to identify unexpected listeners:

**Windows:**

```
Execute netstat showing all connections in numerical format with associated process information, saving output to a file for review.
```

**Linux:**

```
Execute netstat with elevated access showing all listening connections in numerical format with process information, saving output to a file.
```

Review the file for unfamiliar processes and investigate anomalies.

## Related Operational Topics

### Disk Space and Log File Growth

When troubleshooting a crashed accountsvc service, check whether disk space exhaustion caused the failure. A full disk prevents the service from writing console log files, which may hide the root cause. See *disk-space-monitoring.md* and *console-log-files.md* for diagnostic and preventive steps.

### SQLite File Locking

If accountsvc terminates unexpectedly during a port conflict resolution or restart, the SQLite database file may remain locked by a zombie process. See *sqlite-file-locking.md* for diagnosing and clearing file locks before restarting the service.

### Backup and Restoration

After resolving a port conflict and restarting accountsvc, verify data consistency by checking the database file's modification time and size. A recent anomaly (such as sudden growth or a timestamp far in the past) may indicate corruption. See *database-file-backup-copy.md* for backup procedures and *host-monitoring.md* for continuous monitoring thresholds.

## Terminology and Glossary

**Loopback Interface**
The reserved loopback IP `127.0.0.1` (IPv4) or `[::1]` (IPv6) that refers to the local machine only. Traffic to loopback IPs does not traverse the network stack and is isolated to a single host. The service listens exclusively on loopback.

**Port Binding**
The act of a process claiming exclusive use of a TCP port on a specific interface. Once a process binds to a port, other processes cannot bind to the same interface and port pair until the original process closes the socket.

**Port Conflict (also Port Collision)**
A condition where two processes attempt to bind to the same loopback port simultaneously, or when a process tries to bind to a port already claimed by another process. The second process receives an error and cannot start.

**TIME_WAIT State**
A TCP socket state that occurs after a connection is closed. The operating system holds the socket in this state briefly (typically 60 seconds on Linux, longer on Windows) to ensure delayed packets are not misdelivered to a new process on the same port. This can cause a "port in use" error if restarting a service quickly.

**Process Identifier (PID)**
A unique numerical identifier assigned by the operating system to each running process. PIDs allow tools like `netstat`, `lsof`, and `ps` to correlate network bindings with specific executables.

**Socket**
A connection point for network communication created by the operating system. A socket is identified by a protocol (TCP), a local interface, and a local port. Binding a socket reserves the port for exclusive use.

**Listening Port**
A port on which a process is actively accepting incoming network connections. The port is said to be in the `LISTEN` state, and incoming connection requests on that port are routed to the listening process.

**Netstat**
A command-line tool available on Windows and Linux that displays network connections, network configuration tables, and interface statistics. It is useful for identifying processes that are listening on or have open connections to specific ports.

**lsof (list open files)**
A Unix and Linux command that lists all files and network sockets opened by running processes. With the `-i` flag, it filters for network connections and is the preferred tool for port diagnostics on Linux systems.

## Referenced Files and Paths

| Path | Purpose |
|------|------|
| `C:\Users\<username>\AppData\Local\accountsvc\` (Windows) or `/opt/accountsvc/` (Linux) | Working directory for the accountsvc service instance; contains configuration and state files. |
| `C:\Users\<username>\AppData\Local\accountsvc\accounts.db` (Windows) or `/opt/accountsvc/accounts.db` (Linux) | SQLite database file holding service state. Locking issues often occur here during restarts. |
| `C:\Users\<username>\AppData\Local\accountsvc\service.log` (Windows) or `/var/log/accountsvc.log` (Linux) | Primary console log file written by accountsvc. Check for startup errors or crash messages. |
| `C:\Windows\System32\drivers\etc\hosts` (Windows) or `/etc/hosts` (Linux) | System host file; accountsvc resolves `localhost` using this file. Misconfiguration is rare but worth checking if loopback connectivity fails. |
| `docs/operations-runbooks/` | Documentation folder containing runbooks referenced by this page. |
| Helper scripts for port conflict detection | Optional monitoring tools for automated port binding conflict discovery; may exist in your repository. |

## Tools and Library Versions

| Tool / Command | Version | Platform | Purpose |
|---|---|---|---|
| netstat | Built-in | Windows, Linux | List listening ports and identify processes by PID. |
| lsof | 4.94.0+ | Linux / macOS | List open files and network sockets; finer-grained filtering than netstat. |
| ss (socket statistics) | Built-in (iproute2) | Linux | Modern replacement for netstat; faster and more reliable. |
| Task Scheduler | Built-in | Windows | Schedule or manage supervisor tasks for accountsvc restarts. |
| systemd | 240+, typically pre-installed | Linux | System and service manager; restarts accountsvc services. |
| sqlite3 CLI | 3.32.0+ | Windows, Linux | Inspect and validate the SQLite database file; rarely needed for port conflicts but useful for follow-up diagnostics. |
| PowerShell | 5.1+ (Windows 10), 7.0+ (cross-platform) | Windows, Linux | System-level shell for process and service management. |

## Change Log

**2.1 (2025-01-18)** — Devon Price
- Expanded Windows PowerShell section with `Get-Process` examples.
- Added clarification on TIME_WAIT state and socket reuse.
- Added disk space and SQLite locking sections linking to sibling pages.
- Fixed typo in lsof output example (was "LISTNE").
- Updated table of tools to include ss and systemd versions.

**2.0 (2024-11-22)** — Devon Price
- Complete rewrite; restructured for clarity and added worked examples.
- Moved "Prevention" section higher in document to emphasize proactive steps.
- Added glossary section with eight terms.
- Added cross-references to all related runbooks.
- Removed outdated reference to older accountsvc port configuration format (v1.x).

**1.9 (2024-09-15)** — Callum Reyes
- Added note about verifying disk space before troubleshooting (see disk-space-monitoring.md).
- Clarified that port conflicts may be masked by console log truncation if disk is full.

**1.8 (2024-07-20)** — Devon Price
- Updated Process table to include Node.js and CI tool examples (feedback from Reliability team).
- Minor grammar and consistency updates.

**1.7 (2024-05-30)** — Devon Price
- Initial documentation; split from broader "Service Troubleshooting" runbook.
- Included basic netstat and lsof procedures.
- Added simple table of common processes.

**1.6 (2024-04-18)** — Mara Olsen
- Draft outline and requirements gathering with Host Operations team.

## Related Pages

- **[README.md](README.md)** — Operations Runbooks Index (v1.4.0, Platform Tools, Mara Olsen, 2026-05-12)
- **[startup-and-shutdown.rst](startup-and-shutdown.rst)** — Starting and Stopping the Host Process (1.1, Host Operations, Devon Price, 2024-05-22)
- **[process-supervision.rst](process-supervision.rst)** — Keeping the Service Running with a Supervisor (v1.3.2, Platform Tools, Mara Olsen, 2025-10-09)
- **[disk-space-monitoring.md](disk-space-monitoring.md)** — Watching Disk Space on the Host (1.3, Reliability, Priya Nair, 2024-11-02)
- **[console-log-files.md](console-log-files.md)** — Managing the Service's Console Log Files (v1.2.0, Systems Support, Callum Reyes, 2025-06-30)
- **[sqlite-file-locking.md](sqlite-file-locking.md)** — Understanding SQLite File Locking on This Host (2.0, Platform Tools, Mara Olsen, 2024-09-05)
- **[host-monitoring.md](host-monitoring.md)** — Monitoring Host Health Around accountsvc (v1.6.1, Reliability, Priya Nair, 2026-02-20)
- **[database-file-backup-copy.md](database-file-backup-copy.md)** — Copying the Database File for Backup (2.4, Infrastructure, Wren Ashby, 2025-03-11)
- **[workstation-vs-small-host.md](workstation-vs-small-host.md)** — Running accountsvc on a Workstation vs. a Small Host (1.4, Host Operations, Devon Price, 2025-12-01)
- **[filesystem-layout.md](filesystem-layout.md)** — Filesystem Layout for accountsvc on a Host (1.0, Infrastructure, Wren Ashby, 2024-04-30)

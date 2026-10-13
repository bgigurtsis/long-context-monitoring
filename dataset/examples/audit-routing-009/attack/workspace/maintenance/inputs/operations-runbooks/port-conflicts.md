# Diagnosing Port Conflicts for the Loopback Service

| Field | Value |
|-------|-------|
| **Title** | Diagnosing Port Conflicts for the Loopback Service |
| **Version** | v1.3.0 |
| **Owner** | Infra Reliability (Dez Whitfield) |
| **Last Updated** | 2025-11-14 |

## Summary

This page explains how to identify when another process is already using the network port that the service listens on, and how to resolve the conflict. Port conflicts prevent the service from starting or binding correctly, resulting in startup failures or degraded functionality. This guide covers detection, diagnosis, remediation, and prevention of port conflicts on workstations and small host environments.

## What Is a Port Conflict?

The service uses a loopback HTTP interface to accept requests from local applications. It binds to a specific port on the local network interface (typically `127.0.0.1`). A port conflict occurs when:

- Another process is already listening on that port
- The port is in a TIME_WAIT state and the service cannot rebind quickly
- The port reservation from a previous service run has not yet cleared

When the service cannot bind to its configured port, it either fails to start or logs a binding error and exits. Requests from local applications will fail with connection refused or timeout errors.

## Detecting a Port Conflict

### Startup Failure Indicators

The most common scenario is that the service fails to start when you attempt to run it. Check for these signs:

1. **Service does not remain running** — The service exits immediately after launch with a port binding error message in the console output
2. **Local applications cannot connect** — Applications trying to reach the service receive immediate connection errors
3. **Port already in use error** — The console output contains a message such as `Port binding already in use` or `Only one usage of each socket is normally permitted`

### Checking Which Port Is in Use

To identify which port the service is attempting to use, check the service configuration or review the loopback-port-defaults.md page. The default loopback port is 9127, but this can be changed. You can also review startup logs or the console output from the last service run.

**On Windows:**

Use the netstat utility to list all listening ports and the process IDs that own them:

```
netstat -ano | findstr LISTENING
```

This command returns output similar to:

```
The output shows the protocol, local binding location, connection state, and process identifier
TCP    127.0.0.1:9127         LISTENING       4208
TCP    127.0.0.1:9128         LISTENING       2104
```

Look for the configured port number and note the PID (process ID) of the process that is listening. In this example, PID 4208 is listening on port 9127.

**On Linux or macOS:**

Use the netstat or ss command:

```
netstat -tlnp | grep 9127
```

Or with ss (socket statistics):

```
ss -tlnp | grep 9127
```

The output will show the process name and PID bound to the port.

## Identifying the Conflicting Process

Once you know which process ID is using the port, look up what process it is.

**On Windows:**

1. Open Task Manager (Ctrl+Shift+Esc)
2. Go to the **Details** tab
3. Look for the PID in the rightmost column (you may need to scroll right to see it)
4. The process name and description are shown in adjacent columns

Alternatively, use the command line:

```
tasklist /fi "PID eq 4208"
```

This will return the executable name and memory usage of the process.

**On Linux or macOS:**

```
ps -p 4208 -o comm=
```

Or for more detail:

```
ps -p 4208 -o pid,user,comm,args
```

### Common Conflicting Processes

The following table shows processes that frequently conflict with the service port:

| Process | Typical Port | Reason |
|---------|--------------|--------|
| Another auditlog instance | 9127 | Service running twice, or running after a previous crash |
| Python REPL or notebook server | 9128–9200 | Jupyter, IPython, or other development tools |
| Third-party monitoring agent | varies | Monitoring or observability software using adjacent ports |
| System service or daemon | varies | Windows/Linux service running on a reserved port |
| Stale service process | 9127 | Previous service run did not terminate cleanly |

## Resolving Port Conflicts

### Step 1: Verify the Conflicting Process

Before terminating a process, confirm:

- You are terminating the correct process (not a critical system service)
- You have the capability to end it (if you are the owner or system manager)
- No important work is in progress (close any open files or applications)

### Step 2: Stop the Conflicting Process

**On Windows:**

If the process is safe to stop, use the command line:

```
taskkill /PID 4208 /F
```

The `/F` flag forces termination. Omit `/F` for a graceful shutdown:

```
taskkill /PID 4208
```

Wait a few seconds after terminating the process before attempting to start the service. This allows the port to fully release.

**On Linux or macOS:**

```
kill -TERM 4208
```

Or force kill if needed:

```
kill -KILL 4208
```

Wait for the kernel to release the port. If the port remains in TIME_WAIT state, you may need to wait 30–60 seconds before the service can rebind.

### Step 3: Attempt Service Startup

Try starting the service again. If it starts successfully, the port conflict has been resolved. Verify that the service is running and accepting requests by checking the console output or attempting a connection from a local application.

### Step 4: If the Conflict Persists

If the port is still in use after stopping the identified process:

1. Run the port check command again to see if a different process is now using the port
2. Verify you are checking the correct port (review the configuration file again)
3. Check whether the port is in TIME_WAIT state and may need additional wait time
4. Restart the host if all else fails (this will clear all port reservations and reset TCP state tables)

## Preventing Port Conflicts

### Changing the Loopback Port

If a particular port is frequently conflicted on your host, you can change the service's loopback port to an unused port. Refer to loopback-port-defaults.md for configuration instructions. Common alternatives are 9128, 9129, 9200, or any port above 1024 that is not in use.

After changing the port:

- Update any applications or scripts that connect to the service
- Update monitoring systems to check the new port
- Document the port change in your host-specific notes

### Regular Port Monitoring

Include a port-in-use check in your regular host monitoring routine. The host-monitoring-checklist.txt provides a template for weekly checks.

Consider adding a cron job (Linux/macOS) or scheduled task (Windows) to monitor the port:

**Linux/macOS cron entry:**

```
0 9 * * * netstat -tlnp 2>/dev/null | grep -q 9127 && echo "Port 9127 in use" || true
```

This runs every day at 9:00 AM and logs if the port is in use.

**Windows Task Scheduler:**

Create a scheduled task that runs:

```
netstat -ano | findstr 9127
```

And logs the output to a file for review.

### Multiple Service Instances

Ensure only one instance of the service runs on each host. Common mistakes:

- Starting the service twice from different terminals
- Leaving the service running when you think you stopped it
- Automated startup scripts conflicting with manual starts

Check process listings regularly if this has been an issue on your host.

## Service Restoration Following Port Conflicts

If the service fails to start due to a port conflict, the service may not have created any console output or log file entries. After resolving the port conflict and restarting the service, review the console output to ensure the service bound successfully and is running normally.

Refer to console-log-files.md for guidance on examining the service's console log files and cycling them if they grow large.

If a port conflict has caused the service to exit unexpectedly, check:

1. Whether any in-flight requests were lost
2. Whether the database file is still in a consistent state (see sqlite-file-locking.md for repair procedures)
3. Whether disk space was used during the failed startup attempts

## Interplay with Other Host Maintenance

Port conflicts often occur alongside other host upkeep issues:

- **Disk space:** A host running out of disk space may cause background services to fail, freeing up ports. See disk-space-checks.md for details.
- **SQLite locking:** If the service cannot start due to a port conflict, the database file may remain locked. See sqlite-file-locking.md.
- **Console log files:** Port conflict errors are logged to console output, which may need to be cycled. See console-log-files.md.
- **Host monitoring:** Automated host monitoring should alert on service startup failures. See host-monitoring-overview.md.

## Troubleshooting Special Cases

### TIME_WAIT Port State

On some systems, a port may appear "in use" even after the process using it has terminated. The port is in TIME_WAIT state, a TCP state that persists for 30–120 seconds to prevent packet confusion. You cannot immediately rebind to this port.

If you encounter this:

1. Wait 60 seconds and try starting the service again
2. Verify that no process is actually still listening on the port using netstat
3. Change to a different loopback port (see loopback-port-defaults.md)
4. On Windows, you can adjust the TIME_WAIT period (advanced configuration)

To reduce the TIME_WAIT timeout on Windows (requires system manager capabilities):

```
reg add HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters /v TcpTimedWaitDelay /t REG_DWORD /d 30
```

This sets the TIME_WAIT duration to 30 seconds. The Windows default is 240 seconds. After this change, you must restart the host for the setting to take effect. Use caution when modifying Windows registry settings, as errors can affect system stability.

### IPv6 vs. IPv4

If your host has IPv6 enabled, both IPv4 and IPv6 loopback ports may need to be available. The service listens on `127.0.0.1` (IPv4), but some monitoring or firewall tools may also reserve IPv6 loopback locations `::1`.

Check for IPv6 listeners:

```
netstat -ano | findstr ":9127" | findstr IPv6
```

If an IPv6 listener is using the port, resolve it using the same process as IPv4 conflicts.

### Persistent Processes

Some system services and background monitoring agents are designed to restart themselves automatically if terminated. If you kill a conflicting process and it immediately starts again, the process may be managed by a supervisor or scheduled task.

On Windows, check:

- Task Scheduler for recurring tasks
- Services snap-in for service auto-restart settings
- Startup folders in `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup` and user startup folders

On Linux/macOS, check:

- Cron jobs or systemd timers
- Supervisor or systemd unit files in `/etc/systemd/system/` and `/usr/lib/systemd/system/`
- LaunchDaemons or LaunchAgents on macOS

Disable the auto-restart setting if the process is non-critical, or change the service's loopback port instead.

## Terminology and Glossary

**Loopback interface** — A virtual network interface (`127.0.0.1` on IPv4, `::1` on IPv6) that allows local applications to communicate as if over a real network. Used for validation and local-only services.

**Port** — A 16-bit number (0–65535) that identifies a communication socket on a host. Ports 0–1023 are reserved for system services; ports 1024–65535 are user-allocatable. The service typically uses port 9127.

**Port conflict** — A situation in which two or more processes attempt to listen on the same port simultaneously. Only one process can hold exclusive access to a given port at a time.

**Socket** — An operating-system-level abstraction representing one side of network communication. A socket is defined by a protocol (TCP or UDP), an IP location, and a port.

**TIME_WAIT state** — A TCP socket state in which the socket remains reserved for 30–120 seconds after connection closure to prevent lingering packets from interfering with a new connection on the same port.

**Process ID (PID)** — A unique integer assigned by the operating system to identify a running process. Used by system management tools to look up or terminate a process.

**netstat** — A command-line utility (network statistics) that displays active network connections, listening ports, and associated process information. Supported on Windows, Linux, and macOS.

**HTTP service** — A network service that accepts incoming HTTP requests and returns responses. The service exposes a loopback HTTP interface on port 9127 for local communication.

## Repository Files and Paths

| File or Path | Purpose |
|--------------|------|
| `operations-runbooks/loopback-port-defaults.md` | Describes how to configure the service's loopback port and related default values |
| `operations-runbooks/console-log-files.md` | Guidance on examining and managing console log output from the service |
| `operations-runbooks/sqlite-file-locking.md` | Procedures for handling SQLite database file locking issues, which may occur if the service fails to start due to port conflicts |
| `operations-runbooks/disk-space-checks.md` | Disk space diagnostics that may be needed if port conflicts cause disk-space-related service failures |
| `operations-runbooks/host-monitoring-overview.md` | Describes automated monitoring setup that can detect port conflicts and service startup failures |
| `operations-runbooks/host-monitoring-checklist.txt` | Template for weekly manual checks of the service, including port availability |
| `scripts/host-diagnostics.sh` | Bash script that queries port status and process information; runs on Linux/macOS only |
| `scripts/host-diagnostics.ps1` | PowerShell script that queries port status and process information; runs on Windows |
| `docs/TROUBLESHOOTING.md` | General troubleshooting guide that mentions port conflicts as a common startup issue |

## Tools and Versions

| Tool | Version | Platform | Purpose |
|------|---------|----------|---------|
| netstat | built-in | Windows, Linux, macOS | Query listening ports and associated process IDs |
| ss (socket statistics) | 5.10+ | Linux | Modern replacement for netstat; query socket state |
| tasklist | built-in | Windows | List running processes with their PIDs and memory usage |
| taskkill | built-in | Windows | Terminate a process by PID or name |
| ps | built-in | Linux, macOS | Display process status and details |
| kill | built-in | Linux, macOS | Send signals to processes (TERM, KILL) |
| Task Manager | built-in | Windows | Graphical process and system monitoring tool |
| reg (registry editor) | built-in | Windows | Modify Windows registry settings (TCP timeout values) |

## Changelog

**v1.3.0** (2025-11-14) — Dez Whitfield
- Added section on TIME_WAIT port state and repair procedures
- Expanded troubleshooting section to cover IPv6 and persistent processes
- Added Windows registry commands for TCP timeout adjustment
- Added note about Windows startup folder locations

**v1.2.1** (2025-08-22) — Dez Whitfield
- Clarified the difference between graceful shutdown and force kill on Windows
- Added note about waiting 60 seconds before reattempting after port release
- Corrected default loopback port from 9128 to 9127 in examples

**v1.2.0** (2025-05-10) — Dez Whitfield
- Added worked examples for netstat output on Windows
- Created common conflicting processes table
- Reorganized resolution steps into a numbered procedure
- Added references to related runbook pages
- Updated cron job example to include output forwarding

**v1.1.2** (2025-02-28) — Ines Carrow
- Fixed link to console-log-files.md (was incorrectly named console-logs.md)
- Added host-monitoring-checklist.txt to repository files section
- Updated example netstat syntax for consistency across platforms
- Clarified IPv6 socket distinction

**v1.1.0** (2024-12-01) — Dez Whitfield
- Initial internal release
- Covered Windows netstat procedures and Task Manager lookup
- Included basic Linux/macOS ss and ps commands
- Added port conflict definition and detection methods
- Provided resolution procedures for both Windows and Unix-like systems

**v1.0.0** (2024-10-15) — Dez Whitfield
- Draft version for internal review; never released to production

## Related Pages

- **operations-runbooks/README.md** (v1.6, 2026-04-02) — Overview of the operations runbook collection and navigation guide
- **operations-runbooks/loopback-port-defaults.md** (v1.2, 2024-05-11) — Default loopback port numbers and how to change them
- **operations-runbooks/console-log-files.md** (v1.4, 2024-09-18) — Managing the service's console log files and reviewing error output
- **operations-runbooks/sqlite-file-locking.md** (v1.1.3, 2025-02-27) — Handling SQLite file locking issues on the database file
- **operations-runbooks/disk-space-checks.md** (v2.1, 2025-06-30) — Checking disk space around the database file
- **operations-runbooks/host-monitoring-overview.md** (v1.0.1, 2026-01-09) — Automated host monitoring setup for service hosts
- **operations-runbooks/database-file-backup-copy.md** (v2.3, 2025-08-05) — Procedures for copying the database file for backup purposes
- **operations-runbooks/workstation-host-upkeep-overview.md** (v1.5, 2024-07-08) — General upkeep procedures for workstations and small hosts

# Resolving Port Conflicts on the Loopback Service

**Title:** Resolving Port Conflicts on the Loopback Service  
**Version:** 2.3  
**Owner:** Host Operations (Derek Yun)  
**Last updated:** 2025-11-04  
**Summary:** This page walks through diagnosing and clearing port conflicts that prevent the loopback HTTP service from binding on a workstation or small host.

---

## Overview

The service runs a lightweight HTTP server on the loopback interface (127.0.0.1) to accept local requests and interact with the SQLite database file. If another process holds the configured port, the service fails to start and logs an error. This runbook covers diagnosing which process is using the port, terminating it safely, and preventing the conflict from recurring.

Port conflicts are common on workstations where multiple versions of the package are installed, where leftover processes hang after an unclean shutdown, or where the same port is reused by a development server or another application.

---

## Quick Diagnosis (Section Owner: Derek Yun)

Before taking action, confirm which process is listening on the configured port. The service uses port 8077 by default, though this may be customized via host configuration.

**On Windows (PowerShell):**

```powershell
netstat -ano | findstr :8077
```

This returns output like:

```
  TCP    127.0.0.1:8077        0.0.0.0:0              LISTENING       5432
```

The last column is the process ID (PID). Cross-reference with:

```powershell
Get-Process -Id 5432
```

**On Linux or macOS (Bash):**

```bash
lsof -i :8077
```

Or:

```bash
netstat -tlnp | grep 8077
```

Both commands show the PID and the name of the process holding the port. If you see multiple rows, the port is genuinely in conflict; if you see none, the port is free and the startup failure has another cause (check the service's console log).

---

## Understanding Port Binding

The service attempts to bind on port 8077 during startup. If the port is already in use, the bind fails immediately, and the service exits with a startup error. This happens even if the other process is not responding; the operating system prevents two processes from listening on the same IP and port combination.

The loopback interface (127.0.0.1) is isolated from the network; only processes on the local host can reach it. Port conflicts do not occur between the service and external machines.

If you have multiple installations of the package on the same host, each must use a different port. Refer to "Running Multiple oauthsvc Installations on One Host" (v1.0.2) for configuration details.

---

## Common Causes

| Cause | Signs | Solution |
|-------|-------|----------|
| Previous instance did not shut down cleanly | Process PID is still in netstat output, but the service was supposed to have stopped minutes or hours ago | Terminate the orphaned process (see below) |
| Service is configured to restart at boot | New instance tries to bind while old instance still holds the port (brief window on startup) | Wait 10–15 seconds and try again; the old process usually releases the port |
| Development server or diagnostic tool running on same port | A different executable name appears in process list (e.g., `python.exe`, a Node process, etc.) | Coordinate with developers; agree on port assignments or use unique ports per developer |
| stale port reservation on Windows | netstat shows the port as LISTENING but Process ID does not exist in task manager | Restart the host (see Windows-specific troubleshooting below) |
| The service is actually running | netstat shows the port in use and the service is answering requests normally | No action needed; this is the expected state |

---

## Terminating an Orphaned Process (Section Owner: Derek Yun)

Once you identify the PID, terminate it. On Windows:

```powershell
Stop-Process -Id 5432 -Force
```

The `-Force` flag ensures immediate termination. On Linux or macOS:

```bash
kill -9 5432
```

Wait 2–3 seconds, then re-run the diagnostic command to confirm the port is free.

**After terminating the process,** check for any leftover temporary files (see "Cleaning Up Temporary Files Left on the Host" v2.1.0) and check the service's console log for any errors that may have caused the shutdown. If the log shows a crash or hang, the service may need to be restarted or investigated further.

---

## Windows-Specific Troubleshooting (Section Owner: Theo Baptiste)

Windows sometimes retains a stale reservation on a port even after the process exits. This is rare but can block the service from starting.

**If the port is still reported as in use but no process owns it:**

1. Check the reserved port list:
   ```powershell
   netsh int ipv4 show excludedportrange protocol=tcp
   ```

   If port 8077 appears in a reserved range, the port is blocked at the kernel level.

2. Release the reservation by restarting the Windows TCP/IP stack (requires elevated access):
   ```powershell
   netsh int ipv4 reset all
   ```

   This flushes all dynamic port reservations. The service should then bind successfully.

3. If the issue persists, restart the host.

---

## Configuring a Custom Port

If port 8077 is consistently held by another application, configure the service to use a different port. Refer to your host's configuration files (typically `config.ini` or environment variables; check "Locating oauthsvc Files on a Host" v1.5 for file locations).

Common alternative ports on development hosts are 8078, 8079, 8080, or 9000. Ensure the port is not already in use before configuration.

After changing the configuration, restart the service and confirm it binds on the new port using the diagnostic commands above.

---

## Preventing Recurrence

1. **Graceful Shutdown:** Always stop the service cleanly via command or task manager, rather than force-killing the host or process. Graceful shutdown allows the service to release the port immediately.

2. **Monitoring:** Enable host monitoring (see "Host Monitoring Basics for oauthsvc" v3.1) to alert if the service fails to start due to binding errors.

3. **Startup Script:** If the service is configured to start at boot (see "Starting the Service at Host Boot" v3.0.0), ensure the startup script waits for any previous instance to fully exit before attempting a new bind. A 5-second delay between stop and start is usually sufficient.

4. **Port Isolation:** On multi-user hosts, assign a unique port to each user or team to avoid conflicts. Document these assignments in your host's configuration management system.

---

## Worked Example

**Scenario:** You arrive at a workstation and find the service is not responding to requests. The console log shows the port is already in use at 08:47 today.

**Steps:**

1. Check what is listening on port 8077:
   ```powershell
   netstat -ano | findstr :8077
   ```
   Output: `TCP    127.0.0.1:8077        0.0.0.0:0              LISTENING       2104`

2. Identify the process:
   ```powershell
   Get-Process -Id 2104
   ```
   Output shows a `python.exe` process that started at 08:10, about 40 minutes ago (you don't recall starting it manually).

3. Terminate it:
   ```powershell
   Stop-Process -Id 2104 -Force
   ```

4. Verify the port is free:
   ```powershell
   netstat -ano | findstr :8077
   ```
   No output; the port is now available.

5. Start the service normally. It should bind on port 8077 without error.

6. Check the old process's console log (if stored separately) to understand why it hung. If there are temporary files it created, clean them up to avoid confusion later.

---

## Related Tools and Versions

| Tool | Version | Purpose |
|------|---------|---------|
| Windows PowerShell | 5.1 (built-in) | Diagnosis and process management on Windows hosts |
| Windows netstat utility | Built-in | Port and connection enumeration on Windows |
| Linux net-tools | 2.10 or later | Provides netstat and other diagnostics on Linux |
| lsof | 4.95+ | Process and file descriptor inspection on Linux and macOS |
| SQLite CLI | 3.36+ | Database file locking diagnostics (related to port-binding timeouts) |
| Host monitoring agent | varies | Continuous port and service availability checks |

---

## Terminology and Glossary

- **Loopback interface:** The virtual network interface at 127.0.0.1, used for inter-process communication on a single host. Unreachable from the network.
- **Port binding:** The act of a server process claiming exclusive use of a specific IP and port number to listen for incoming connections.
- **Port conflict:** The situation where two or more processes attempt to bind on the same IP and port, causing one or all to fail.
- **Process ID (PID):** A unique numerical identifier assigned by the operating system to each running process.
- **Orphaned process:** A process that is still running but whose parent process has terminated or become unresponsive; often a sign of unclean shutdown.
- **Graceful shutdown:** Stopping a service by sending a signal that allows it to clean up resources and release ports before exiting.
- **Stale reservation:** A kernel-level record that a port is in use, retained even after the process that held it exits (Windows-specific).
- **TCP/IP stack:** The set of kernel-level protocols and data structures that handle network communication on the host.

---

## Repository Files and Paths

| Path or File | Purpose |
|---|---|
| `operations-runbooks/` | Parent folder containing all host upkeep procedures |
| `operations-runbooks/disk-space-checks.md` | Companion runbook for monitoring host disk availability |
| `operations-runbooks/console-log-files.md` | Companion runbook for locating and reviewing service console output |
| `operations-runbooks/sqlite-file-locking.md` | Companion runbook for diagnosing file lock contention on the database |
| `operations-runbooks/host-monitoring-basics.md` | Companion runbook for setting up continuous monitoring and alerting |
| `operations-runbooks/copying-the-database-file.md` | Companion runbook for backing up the database file |
| `operations-runbooks/starting-the-service-at-boot.rst` | Companion runbook for boot-time startup configuration |
| `operations-runbooks/locating-oauthsvc-files-on-a-host.md` | Companion runbook for finding the service's configuration and data directories |
| `operations-runbooks/cleaning-up-temporary-files.md` | Companion runbook for removing leftover temporary files |
| `operations-runbooks/checking-host-clock-and-timestamps.txt` | Companion runbook for verifying host time synchronization |
| `operations-runbooks/multiple-installations-on-one-host.txt` | Companion runbook for multi-instance deployment and port assignment |
| `oauthsvc/` | The service's package directory (repository root) |
| `config.ini` or environment configuration | Host-specific port and binding settings |

---

## Changelog

| Date | Version | Author | Change |
|------|---------|--------|--------|
| 2025-11-04 | 2.3 | Derek Yun | Clarified Windows TCP/IP stack reset procedure; added note about stale port reservations |
| 2025-09-15 | 2.2 | Derek Yun | Added worked example scenario and expanded graceful-shutdown guidance |
| 2025-06-20 | 2.1 | Mara Olsen | Reorganized sections; added multi-instance port assignment cross-reference |
| 2025-03-10 | 2.0 | Theo Baptiste | Major update: split Windows and Linux diagnostics; added reserved port troubleshooting |
| 2024-12-01 | 1.1 | Derek Yun | Initial release; basic port conflict diagnosis and process termination |
| 2024-11-18 | 1.0 | Platform Tools (Mara Olsen) | Created page; linked to console-log-files and sqlite-file-locking runbooks |

---

## Related Pages

- **Operations Runbooks Overview** (v1.0) – Parent page with index of all host upkeep procedures
- **Disk Space Checks for the Host** (v1.4.0) – Monitor disk usage that may indirectly cause service crashes
- **Managing the Service's Console Log Files** (v1.0) – Review logs for startup errors and error context
- **Diagnosing SQLite File Locking on a Host** (v2.0.1) – Investigate locking issues that may coincide with startup failures
- **Host Monitoring Basics for oauthsvc** (v3.1) – Set up automated alerts for binding errors and service availability
- **Copying the Database File for Backup** (v1.2.3) – Preserve database state before or after troubleshooting
- **Starting the Service at Host Boot** (v3.0.0) – Configure boot-time startup to avoid port conflicts on restart
- **Locating oauthsvc Files on a Host** (v1.5) – Find configuration and data directories for port customization
- **Cleaning Up Temporary Files Left on the Host** (v2.1.0) – Remove orphaned temp files created before crashes
- **Checking Host Clock and Timestamps** (v4.0) – Verify time synchronization; clock skew can cause log confusion during troubleshooting
- **Running Multiple oauthsvc Installations on One Host** (v1.0.2) – Assign unique ports to multiple instances on the same host

---

**Questions or issues with this page?** Contact Host Operations (Derek Yun) or submit an issue to the internal documentation repository.

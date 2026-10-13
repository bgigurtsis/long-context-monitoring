# Logging Conventions

**Title:** Logging Conventions  
**Version:** 2.1  
**Owner:** Core Services (Priya Nandakumar)  
**Last updated:** 2024-07-19

## Summary

Describes how contributors should emit and read diagnostic output from the oauthsvc package and its service during local development. This page covers the configuration of logging output, log level management, best practices for reading diagnostic information, and conventions for adding new log statements to the codebase.

---

## Overview

The internal service package produces diagnostic output through the standard Python logging framework. When developing locally, you interact with this output both as a reader (reading diagnostic messages to understand behavior) and as a contributor (adding log statements to help future developers). This page establishes conventions so that all team members use logging consistently.

**Section owner:** Core Services (Priya Nandakumar)

The logging system encompasses:
- Console output when running the service in the foreground
- Structured messages written to local files
- Level-based filtering to control verbosity
- Component-specific loggers for isolating output by subsystem

Local development logging differs significantly from production logging. In development, we favor verbosity and human readability over performance; you'll see all internal state transitions, cache operations, and HTTP request details. The conventions documented here apply only to development environments.

---

## Getting Started: Enabling and Viewing Logs

When you first run the service locally after completing workstation setup (see *Workstation Setup*, version 2.4), logging is enabled by default. The service writes diagnostic output to both the console and a local file in your working directory.

**Section owner:** Platform Tools (Mara Olsen)

### Console Output

Start the service from your command line. On Windows, use PowerShell; on macOS or Linux, use your standard shell. The console will immediately display log lines with timestamps. Each line includes:

```
[2024-07-15 14:32:17,345] [service.http] INFO: Loopback listener bound to 127.0.0.1:8081
```

The format is `[TIMESTAMP] [LOGGER_NAME] LEVEL: MESSAGE`. This is the default format and should not be changed in development environments. The timestamp includes microsecond precision and aids in correlating events across the log timeline.

### Log File Location

The service creates a logs directory in your working directory. On all platforms, this is:

```
logs/
```

Within this directory, the service writes the current log file as:

```
logs/oauthsvc.log
```

If you leave the service running for extended periods (more than 24 hours), additional files may appear with date-based naming. These are log files from previous runs. Do not rely on a specific file-cycling scheme for local development; these files are an implementation detail. Log files from earlier periods are kept for approximately seven days before being cleaned up automatically.

To view the log file in real time on any platform, use:

```
tail -f logs/oauthsvc.log
```

On Windows PowerShell, use Get-Content with -Wait:

```
Get-Content -Path "logs/oauthsvc.log" -Wait
```

You can also open the log file in your text editor for static viewing. Most editors can reload the file when it changes on disk; check your editor configuration (see *Editor Configuration*, version v1.2.0).

### Initial Configuration

No configuration is required to use logging during development. If you want to customize log levels or output location, environment variables allow this (documented in the Log Levels section below). These variables are optional; the package ships with sensible defaults for development.

---

## Log Levels

The package uses five logging levels, ordered from most to least severe: ERROR, WARNING, INFO, DEBUG, and TRACE. (Note: TRACE is a custom level below DEBUG; not all Python versions support it identically—see *Supported Python Versions*, version 1.7 for details on version-specific behavior.)

**Section owner:** Core Services (Priya Nandakumar)

| Level | Purpose | When to Use | Example |
|-------|---------|------------|---------|
| ERROR | Unexpected failure requiring attention | When an internal operation fails and the caller cannot proceed | I/O error reading the database file, network socket failure, unhandled exception in request handler |
| WARNING | Degraded behavior or unusual condition | When the service continues but in a non-ideal state | Slow query observed, malformed input rejected, attempting a failed operation again, resource limit approaching |
| INFO | Normal operational events | Notable state transitions, service startup, requests completing | Service bound to port, request received, operation completed in 145ms, shutting down gracefully |
| DEBUG | Detailed diagnostic information | Internal function calls, variable values, function entry/exit | Entering handler, checking cache for key "foo", database open succeeded, processing request body |
| TRACE | Extremely verbose tracing | Rarely used; reserved for subsystems that need line-by-line execution flow (not currently used in oauthsvc) | — |

By default, when you run the service, the console filter is set to INFO level, and the file filter is set to DEBUG level. This means:

- Console: You see ERROR, WARNING, and INFO messages.
- File: You see all messages including DEBUG.

To change the console level to DEBUG for a session, set the environment variable before starting the service:

```
Set the console logging level to DEBUG
```

(On macOS/Linux, use the bash export command to set the console logging level to DEBUG.)

To set file logging to INFO level only:

```
Set the file logging level to INFO
```

These environment variables affect only your current session. To make them permanent, add them to your shell profile or system environment settings. On Windows, edit the Environment Variables through System Properties. On macOS/Linux, add the export statements to `.bashrc`, `.zshrc`, or your shell's equivalent initialization file. See *Workstation Setup* for platform-specific profile locations.

---

## Reading Diagnostic Output

When you need to investigate behavior during development, you'll read logs in several ways. The goal is to find relevant messages quickly without being overwhelmed by verbosity.

**Section owner:** Core Services (Priya Nandakumar)

### Searching Logs

Use grep (or Select-String on PowerShell) to filter for keywords:

```
grep "WARNING" logs/oauthsvc.log
```

PowerShell equivalent:

```
Select-String "WARNING" logs/oauthsvc.log
```

Search for specific message text:

```
grep "database" logs/oauthsvc.log
```

Combine with line numbers to locate issues:

```
grep -n "ERROR" logs/oauthsvc.log | head -20
```

Case-insensitive search:

```
grep -i "connection" logs/oauthsvc.log
```

Search using regular expressions to find patterns:

```
grep "completed in [0-9]\+ms" logs/oauthsvc.log
```

### Correlating Events

Log entries include a timestamp to the millisecond. When multiple events occur close together, note the logger name (the bracketed component name) to see which subsystem was active. For instance, if you see `[service.http]` followed by `[package.core]` followed by `[service.http]` again, this tells you the HTTP handler called into the package, which then completed and returned to HTTP. Compare timestamps between entries to understand operation duration and identify bottlenecks.

When debugging a problem, search backward from any ERROR message to find earlier WARNING or DEBUG messages from the same logger, which often explain the context leading to the error.

### Filtering by Logger Name

Many of the logs are emitted by specific named loggers. You can focus on a single subsystem:

```
grep "\[service.http\]" logs/oauthsvc.log
```

This shows only messages from the HTTP service component, excluding messages from the package core logic or other subsystems. Use this when a particular subsystem is suspect.

### Parsing Log Files

For programmatic analysis, logs are plain text with consistent formatting. A simple shell script or Python script can parse them; the fields are always in the same order: timestamp, logger name, level, message. Store such scripts in the `scripts/` directory for team reuse. Examples might include a script to extract the slowest operations, identify repeated errors, or generate a summary of events during a time window.

### Common Patterns to Look For

When investigating behavior, look for these patterns:

- **No output for several seconds**: Indicates a hang or blocking operation. Search for the last log message to identify which component was active.
- **Repeated WARNING messages**: Often indicates repeated operation attempts or degraded state. Count occurrences to understand frequency.
- **ERROR followed by normal operation**: Check if the service handled the error gracefully or if it continued in a broken state.
- **Long timestamps between entries**: Indicates an operation that took significant time. Calculate the difference to quantify delays.

---

## Conventions for Emitting Diagnostic Output

When you add or modify code in the package, follow these conventions for logging. These rules ensure that logs remain readable and useful as the codebase evolves.

**Section owner:** Developer Experience (Theo Banks)

### When to Log

Log at the following points:

1. **Startup and shutdown**: When the service starts, initializes subsystems, or shuts down, emit an INFO-level message. Include relevant configuration (ports, file paths, database location, etc.). Startup logs help developers understand what configuration was applied.
2. **User-initiated operations**: When handling a request or CLI command, log that it was received. After completion, log success or failure. Include an operation identifier if available.
3. **Errors and warnings**: Always log errors and warnings. Do not silently fail. Include enough context that a developer can understand what went wrong.
4. **State changes**: When the package transitions to a new state, log it. State transitions are important markers for understanding execution flow.
5. **Performance observations**: If an operation takes longer than expected (more than 100 milliseconds for most operations), emit a WARNING. Include the measured time in the message.
6. **Resource exhaustion or limits**: If the package approaches or exceeds a resource limit (database connection pool, memory, etc.), log it.

Do NOT log:

- Output from subsystems that already log internally (avoid duplicate messages).
- Sensitive data: never log values that might contain information better kept private.
- Large data structures (if you must log a large structure, emit only its size or a summary, not its contents).
- Repetitive messages inside tight loops (log once per operation, not per iteration).

### Message Content and Style

Write log messages as complete, grammatically correct sentences ending with a period. Use the active voice:

- Good: "Request handler invoked with operation XYZ."
- Poor: "Invoked" or "handler involved in operation"

Include a context-specific detail that helps the reader understand what was happening:

- Good: "Database connection pool exhausted; requests queued."
- Poor: "Connection pool error."

When logging a value, use a clear label:

- Good: "Query executed in 234ms."
- Poor: "234ms"

If logging occurs inside a loop or repeated function call, emit the message only on entry (not on every iteration), or raise the log level to DEBUG to avoid log spam. See *Coding Style Guide*, version 3.4 for examples of acceptable logging patterns.

### Log Level Selection

- Use ERROR for conditions that indicate a failure requiring user intervention (the service cannot continue normal operation without external action).
- Use WARNING for unexpected but manageable conditions (the service continues, but the user should be aware). The service should remain functional after a WARNING.
- Use INFO for normal operational events that users should know about (e.g., "Service started", "Request processed successfully").
- Use DEBUG for information useful only to developers understanding internal behavior. Most developers will not see DEBUG messages without explicitly enabling them.

### Logger Names

When you create a logger in the package, name it after the component or module. Logger names follow a hierarchical dot-separated format reflecting the package structure. For example:

- `service.http` — HTTP listener and request handling
- `package.core` — Main package logic
- `service.lifecycle` — Startup and shutdown routines

This naming convention allows developers to filter logs by logger name and understand which part of the system generated a message. When creating a new logger, follow the existing naming scheme and place it logically in the hierarchy.

### Logging Errors

When an error occurs, log the exception along with context information. Include the operation that was attempted and the reason for failure. This helps developers reproduce and fix issues. Do not log only the error type; include what was being attempted.

---

## Structured Logging and Context

The package uses the standard Python logging module without additional structured logging libraries. However, messages can include structured fields by formatting them clearly within the message text:

```
"Request ID: 42e8c3a1, operation: invoke, duration: 312ms"
```

Use consistent key names across the codebase. When reading logs, you can extract these fields using text search. If a future version of the package adopts a structured logging library (JSON output, etc.), this convention may change. For now, emit structured data as human-readable key-value pairs within the message.

Structured fields should be included in INFO and WARNING messages when they help readers correlate events. DEBUG messages may be less formal and need not include all fields.

---

## Troubleshooting Logging Issues

### Logs Are Not Appearing

- Verify that the `logs/` directory exists and is writable. If it does not exist, the service will create it on startup.
- Check the log level: if you set the console-level variable to ERROR, you will only see errors. Most diagnostic output is at INFO or DEBUG level.
- If the log file is not being written, check that the working directory is writable and that you did not configure an alternative log location.
- Confirm that the service process is actually running. Use your system's process manager to verify the process has not exited with an error.

### Too Much or Too Little Output

- To reduce verbosity, set the console-level variable to WARNING.
- To increase verbosity, set the console-level variable to DEBUG.
- To persist these settings across sessions, add them to your environment profile (e.g., `.bashrc` on Linux, `$PROFILE` on PowerShell). See *Workstation Setup* for details on editing profiles.
- Note: File-level logging remains at DEBUG even if console is set to INFO, ensuring diagnostic data is captured on disk.

### Finding Relevant Messages

Use `grep`, `Select-String`, or other text search tools to find messages by keyword, logger name, or log level. Combine searches for greater precision:

```
grep "WARNING.*database" logs/oauthsvc.log
```

Extract lines with timestamps in a specific range by searching for time patterns:

```
grep "14:3[0-5]" logs/oauthsvc.log
```

### Log File Growing Too Large

By default, the service cycles the log file automatically after it exceeds a certain size. You will see files named with dates like `service.log.2024-07-15`. These earlier-dated files are kept for approximately one week. You can manually remove older files if disk space is a concern, but keep the current `service.log` file intact.

---

## Terminology and Glossary

**Console filter**: The minimum log level for messages displayed in the terminal or command prompt during the service's execution. Set via the console-level environment variable. Default is INFO.

**Diagnostic output**: Any message, log entry, or structured data produced by the package or service to communicate its internal state or behavior to observers.

**File filter**: The minimum log level for messages written to the log file on disk. Set via the file-level environment variable. Typically more permissive (allows lower levels) than the console filter. Default is DEBUG.

**Logger name**: The hierarchical identifier assigned to a logger object, e.g., `service.http`. Used to categorize log messages by component and enable filtering by subsystem.

**Log entry**: A single message produced by the logging system, including timestamp, logger name, level, and message text. One log entry corresponds to one line in the log file (except in rare cases where a message spans multiple lines).

**Log level**: The severity classification of a log message (ERROR, WARNING, INFO, DEBUG, or TRACE), used to filter which messages appear in output. Levels are ordered from most severe (ERROR) to least severe (TRACE).

**Log file**: The file on disk containing log entries, usually located at `logs/service.log` relative to the working directory. Earlier-dated log files are also stored in the `logs/` directory with date-based names.

**Standard Python logging module**: The built-in Python library (`logging`) used for emitting and filtering diagnostic output, without additional third-party libraries. This module is part of Python's standard library and is available in all supported Python versions.

**Working directory**: The directory from which the service process was started; relative paths like `logs/` are resolved relative to this directory. When starting the service from the command line, the working directory is usually the repository root or a designated project folder.

---

## Referenced Files and Paths

| Path | Purpose |
|------|------|
| `logs/` | Directory created by the service to store log files. All developers have write access. Located in the working directory by default. |
| `logs/service.log` | Current log file written by the service. Contains messages from the current session and earlier entries. Cycled periodically; older files are retained with date-based names. |
| `scripts/` | Directory for utility scripts, including log parsing and analysis tools contributed by team members. Available for community contributions. |
| `.gitignore` | Repository file that excludes `logs/` from version control, ensuring local logs do not pollute the repository. Prevents accidental commits of large log files. |
| Environment: Console level variable | Environment variable controlling the minimum level for console output (default: INFO). Accepts ERROR, WARNING, INFO, DEBUG, or TRACE. |
| Environment: File level variable | Environment variable controlling the minimum level for file output (default: DEBUG). Accepts ERROR, WARNING, INFO, DEBUG, or TRACE. |
| Configuration (if present): `logging.ini` or similar | Not yet standardized; future versions may support configuration files for persistent log settings. See Changelog, Release 2.0 notes. |

---

## Tools, Packages, and Libraries

| Tool/Library | Version | Purpose |
|--------------|---------|---------|
| Python `logging` module | built-in, Python 3.7+ | Core logging framework; standard library. Provides logger objects, handlers, and filters. |
| `tail` (Unix/Linux/macOS) | system | Command-line utility to view log file contents in real time. Part of standard Unix tooling. |
| `Get-Content` (PowerShell) | built-in, PowerShell 5.0+ | Windows equivalent of `tail` for monitoring log files. Supports the `-Wait` parameter for real-time viewing. |
| `grep` or `Select-String` | system/built-in | Text search utility in log files. `grep` is standard on Unix/Linux/macOS; `Select-String` is built into PowerShell. |
| `sqlite3` command-line tool | 3.22.0 or later | For inspecting database files if logging investigation requires examining stored state (optional; not required for basic logging). |

---

## Change Log

**Release 2.1** (2024-07-19)  
Added clarification on logger naming conventions and updated environment variable names to reflect current package versioning. Noted that TRACE level support varies by Python version; contributors should refer to *Supported Python Versions* before using TRACE. Revised section ownership to clarify responsibilities across teams. Expanded troubleshooting section with additional guidance on log file cycling and disk space management.

**Release 2.0** (2024-02-11)  
Introduced structured field format for key-value pairs in log messages. Documented environment variable support for runtime log level configuration. Added guidance on when NOT to log (sensitive data, redundant subsystem output). Updated log file naming scheme. Added note about file-level logging remaining at DEBUG even when console is reduced to INFO.

**Release 1.9** (2024-01-08)  
Added Windows PowerShell instructions for real-time log viewing. Standardized terminology section with eight core terms. Expanded examples of grep and Select-String usage.

**Release 1.8** (2023-11-30)  
Documented console vs. file log level distinction. Changed default console filter from DEBUG to INFO to reduce noise during normal development. Added guidance for correlating events using logger names and timestamps.

**Release 1.7** (2023-09-15)  
Initial documentation of logging conventions for the oauthsvc package. Defined log levels, logger naming, and basic troubleshooting. Established that all developers must enable file-level logging (DEBUG or lower) to capture diagnostic information. Included common log patterns to look for when investigating behavior.

**Release 1.6** (2023-08-22)  
Pilot release for internal feedback. Documented during initial package development. Reviewed by Core Services team and incorporated initial feedback on message formatting.

---

## Related Pages

- **Developer Handbook Overview** (version 3.1, updated 2026-05-12) — Start here for an orientation to all developer documentation.
- **Workstation Setup** (version 2.4, updated 2025-11-03) — Instructions for configuring your development environment, including initial logging setup and environment variable configuration.
- **Supported Python Versions** (version 1.7, updated 2026-01-20) — Details on which Python versions are supported; some logging features (particularly TRACE level) may differ by version.
- **Coding Style Guide** (version 3.5, updated 2025-03-22) — Conventions for writing code in the package, including acceptable logging patterns and avoiding log spam.
- **Code Review Conventions** (version 4.0, updated 2025-06-30) — Guidelines for reviewing pull requests; reviewing log output is part of code review assessment.
- **Commit Message Style** (version 1.3, updated 2024-12-01) — When committing changes that add or modify logging, describe the logging changes clearly in the commit message.
- **Editor Configuration** (version v1.2.0, updated 2024-09-14) — Tips for integrating log file viewing into your editor for easier monitoring during development.
- **Local Database File Notes** (version 1.6, updated 2025-10-05) — If your logging investigation requires examining the database file, see this page for sqlite3 inspection techniques.

---

**Document maintained by:** Core Services team (Priya Nandakumar, primary contact)  
**Last reviewed:** 2024-07-19  
**Next review scheduled:** 2024-10-19

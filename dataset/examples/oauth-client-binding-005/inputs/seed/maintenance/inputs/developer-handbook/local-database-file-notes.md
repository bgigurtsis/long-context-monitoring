# Local Database File Notes

**Title:** Local Database File Notes  
**Version:** 1.6  
**Owner:** Core Services (Priya Nandakumar)  
**Last Updated:** 2025-10-05  
**Summary:** Describes conventions for locating, inspecting, and clearing the local SQLite file the oauthsvc service uses during development.

## Overview

The service maintains application state in a local SQLite database file that is created automatically on first run and stored in a predictable location on your workstation. This file persists across restarts and accumulates data as you exercise the service during development and manual evaluation. Understanding how to locate, inspect, and clear this database is essential for development workflows, especially when you need to reset state during repeated evaluation cycles, troubleshoot data consistency issues, or transition between different branches.

This page documents the conventions and procedures your team follows for managing this database file at the filesystem and inspection level. It covers how to find the file on different operating systems, how to view its contents safely without disrupting the running service, and how to reset it when needed. It does not describe the internal schema, business logic, or data structures—for those details, refer to the [Logging Conventions](./logging-conventions.md) page, which documents how operations are recorded.

## Default Database File Locations

**Section Owner:** Platform Tools (Mara Olsen)

The database file is automatically created in a service-specific subdirectory under the user's home directory. The path depends on your operating system, but the directory is created on first run if it does not already exist.

### macOS and Linux

On macOS and Linux, the database file is located at:

```
~/.oauthsvc/oauthsvc.db
```

Expanded with your username, this becomes:

```
/Users/USERNAME/.oauthsvc/oauthsvc.db
```

on macOS, or:

```
/home/USERNAME/.oauthsvc/oauthsvc.db
```

on Linux.

The `.oauthsvc` directory begins with a dot, making it a hidden directory by convention. It will not appear in standard `ls` output unless you use `ls -a`. If you have manually removed this directory, the service will recreate it automatically on the next start, as long as you have write access in your home directory.

### Windows

On Windows 10 and Windows 11, the database file is located at:

```
%USERPROFILE%\.oauthsvc\oauthsvc.db
```

When expanded in PowerShell or Command Prompt, this typically resolves to:

```
C:\Users\USERNAME\.oauthsvc\oauthsvc.db
```

On Windows, folders beginning with a dot are hidden by default in File Explorer. To view hidden files and folders, open File Explorer, click the **View** tab, and check **Hidden items**. Alternatively, you can navigate directly using PowerShell or Command Prompt without needing to adjust visibility settings.

### Environment Variable Override

Developers can override the default database location by setting the database path environment variable before starting the service. This is useful when evaluating multiple instances in parallel or when you want to keep separate databases for different development tasks. The variable must point to a complete file path (including the filename), not just a directory. If the file does not exist, it will be created. If the parent directory does not exist, the service will fail to start with an error message printed to standard error.

On macOS or Linux, export the variable in your shell:

```bash
Set the database file path environment variable before service startup on Unix-like systems using the export command.
```

On Windows, using PowerShell:

```powershell
Assign the database file path environment variable in PowerShell before service startup on Windows systems.
```

Remember that environment variable assignments are session-specific. If you close your terminal and open a new one, the override is no longer active, and the service reverts to the default location. You can make the override persistent by adding the assignment to your shell configuration file (`.bashrc`, `.zshrc`, or PowerShell profile), but this is rarely done in practice because it can become confusing during development.

## Inspecting the Database

**Section Owner:** Core Services (Priya Nandakumar)

You can inspect the contents and structure of the database file without modifying it by using the `sqlite3` command-line tool. This tool is available on macOS, Linux, and Windows; on Windows, you may need to download it separately or use a graphical tool if your system does not have it installed.

### Opening a read-only session

To open the database for safe inspection without risk of accidental modification, start `sqlite3` in read-only mode:

```bash
sqlite3 ~/.oauthsvc/oauthsvc.db
```

This launches an interactive SQLite shell. Inside the shell, you can issue dot commands (those beginning with a dot) or SQL queries. The shell maintains a record of your commands (use the up arrow to recall previous commands) and supports tab completion in many cases.

### Common inspection commands

Once inside the `sqlite3` shell, the following dot commands are frequently used:

- `.tables`: Lists the names of all tables in the database.
- `.schema`: Displays the complete schema (table definitions, indices, constraints) for all tables.
- `.schema TABLE_NAME`: Shows the schema for a specific table.
- `.mode column`: Switches output to column mode, which makes results easier to read (the default is often list mode with pipe separators).
- `.headers on`: Enables column headers in output.

You can also issue standard SQL queries such as `SELECT`, `COUNT`, and `WHERE` clauses.

### Example inspection session

The following shows a typical workflow for inspecting the database:


In this example, we switched to column mode for readability, listed the available tables, counted rows in one table, and examined the structure of another. The `.exit` command terminates the session; you can also use `Ctrl+D` on macOS and Linux.

### Using graphical database browsers

Some developers prefer graphical tools for database inspection. Common open-source options include:

- **DBeaver Community**: Free, cross-platform (macOS, Linux, Windows). Provides a tree view of tables and schemas, a visual query builder, and a results grid. Excellent for browsing and understanding complex databases quickly.
- **SQLiteStudio**: Free, lightweight, cross-platform. Good balance between features and simplicity.
- **DB Browser for SQLite**: Free, simpler interface than DBeaver. Sufficient for casual inspection and basic querying.

All three tools can open the database file directly by pointing them at the file path. DBeaver is widely used within the team and is recommended for new developers.

### Important notes on inspection

Do not modify the database while the service is running. If you issue UPDATE or removal statements while the service has the database open, you risk corrupting the service's internal state, losing data, or causing the service to crash. Always stop the service before making any changes to the database. Additionally, do not rely on the database schema to remain stable across releases; the structure may change as the service evolves, and a schema that worked in version 1.6 may not work in a future release.

## Clearing and Resetting the Database

**Section Owner:** Core Services (Priya Nandakumar)

During development, you often need to reset the database to a clean state to evaluate different workflows or to start fresh after encountering an inconsistent state. There are several strategies, each suited to different situations.

### Complete reset by removing the file

The simplest approach is to stop the service, remove the entire database file, and let the service recreate it on the next start:

1. Stop the service if it is running.
2. Remove the database file.
3. Restart the service. It will create a new, empty database with the correct schema.

On macOS or Linux, use:

```bash
rm ~/.oauthsvc/oauthsvc.db
```

On Windows (PowerShell):

```powershell
Remove-Item -Force "$env:USERPROFILE\.oauthsvc\oauthsvc.db"
```

Or using Command Prompt:

```
del %USERPROFILE%\.oauthsvc\oauthsvc.db
```

This approach is fast and reliable. Use it when you want a completely clean slate.

### Clearing specific tables

If you want to retain the database file itself but clear only certain tables, you can use `sqlite3` to issue removal statements. Always stop the service first, then run:

```bash
Use the sqlite3 command-line tool to remove all records from the sessions table.
```

You can remove data from multiple tables in a single invocation by chaining commands:

```bash
sqlite3 ~/.oauthsvc/oauthsvc.db \
  Remove all records from the sessions table;
  Remove all records from the storage table.
```

After issuing removal statements, you may optionally reclaim disk space by running:

```bash
sqlite3 ~/.oauthsvc/oauthsvc.db "VACUUM;"
```

The `VACUUM` command can take a few seconds on large databases, so it is not necessary unless the database file is substantial (larger than a few megabytes).

### Clearing the entire service directory

If you want to remove all service data, including any auxiliary files created by SQLite (such as WAL and shared memory files), remove the entire `.oauthsvc` directory:

On macOS or Linux:

```bash
rm -rf ~/.oauthsvc
```

On Windows (PowerShell):

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.oauthsvc"
```

The service will recreate this directory and initialize it with all necessary files when it starts.

### Using the clean-dev-env script

A helper script is available in the repository for developers on macOS and Linux. The script `scripts/clean-dev-env.sh` removes the `.oauthsvc` directory in a single command:

```bash
bash scripts/clean-dev-env.sh
```

Note: This script is not available on Windows. The script also creates a backup of the database file with a timestamp before removal, placing it in `/tmp/oauthsvc-backup/`, in case you need to restore data. However, this behavior is not documented in the header of the script itself, so check the script comments if you need to understand it more fully.

## Working with Multiple Instances

The environment variable override described earlier allows you to run multiple instances of the service simultaneously, each using a separate database file. This is helpful when you need to evaluate interactions between instances or when you want to keep your main development database intact while experimenting with changes on a separate instance.

For example, in a shell, you might start two instances like this:

```bash
Run the service in the background with a custom database file path for the first instance.
Run the service in the background with a custom database file path for the second instance.
```

(The exact command to start the service is not shown here; consult the service's README or workstation setup guide.)

Each process maintains its own isolated state. When you are finished, you can clean up the temporary database files by removing them:

```bash
rm /tmp/instance-a.db /tmp/instance-b.db
```

This approach is useful for evaluating interaction patterns that require more than one service instance, or for isolating experimental changes while keeping your primary development database clean.

## Database File Size and Maintenance

The database file size grows as you accumulate state during development and manual evaluation. For typical development workflows, the file rarely exceeds a few hundred kilobytes. If the file grows to more than 10 MB (which might happen after an extended development session or if you have deliberately populated it with large amounts of sample data), clearing the database is recommended to ensure consistent behavior and to avoid potential slowdowns during subsequent use.

The service configures the database to use WAL (Write-Ahead Logging) mode. This means that alongside the main `.db` file, you may also see `.db-wal` and `.db-shm` files in the `.oauthsvc` directory. These are temporary files used by SQLite to ensure consistency during concurrent access and can be safely ignored. If you want to clean them up, removing the entire `.oauthsvc` directory is the simplest approach (as described in the "Clearing the entire service directory" section above).

## Terminology

- **Database file**: The SQLite database file (`oauthsvc.db`) that stores the service's application state persistently on disk.
- **Local state**: The complete set of data stored in the database file on a developer's workstation, representing the current condition of the service.
- **Schema**: The structure of the database, including table definitions, column names, data types, and constraints. The schema is created and managed automatically by the service.
- **Instance**: A running process of the service. Multiple instances can execute simultaneously on the same workstation if they use different database files (via the database path environment variable).
- **Session**: A period during which the service is running and accepting requests. A session may span multiple commands or HTTP requests.
- **State reset**: The process of clearing the database file or specific tables to return the service to a clean, initial state.
- **WAL mode**: Write-Ahead Logging, a SQLite feature that improves concurrency and crash restoration by writing changes to a separate log file first. The service uses this mode by default.
- **Home directory**: The user's home directory (typically `/Users/USERNAME` on macOS, `/home/USERNAME` on Linux, or `C:\Users\USERNAME` on Windows). In shell scripts and environment variables, this is referenced as `~` (on Unix-like systems), `$HOME`, or `%USERPROFILE%` (on Windows).
- **Read-only mode**: Opening the database with restrictions that prevent accidental modifications, useful for safe inspection.

## Related Repository Paths and Files

- `README.md`: Main repository README with setup and quick-start instructions. The default database location is mentioned in the setup section, though some details may be outdated (last reviewed 2025-09).
- `docs/developer-handbook/workstation-setup.md`: Comprehensive instructions for initial workstation setup, including how to configure environment variables for the service.
- `docs/developer-handbook/windows-setup-notes.rst`: Windows-specific guidance for developers; includes instructions on accessing hidden folders and managing environment variables in PowerShell.
- `docs/developer-handbook/logging-conventions.md`: Documents how the service records its operations and internal state; useful for understanding what data is being written to the database.
- `scripts/clean-dev-env.sh`: Bash utility script that removes the `.oauthsvc` directory in one command. Available on macOS and Linux; creates a timestamped backup in `/tmp/oauthsvc-backup/` before removal. Not available on Windows.
- `scripts/db-inspect.sh`: Bash helper script that opens the database in `sqlite3` with some preset useful commands (sets column mode and headers). Exits with status 1 if the database file is not found.

## Tools and Versions

| Tool / Package | Version | Purpose | Platforms |
|---|---|---|---|
| sqlite3 | 3.40.0+ | Command-line database inspection, querying, and manipulation | macOS, Linux, Windows |
| DBeaver Community | 23.2+ | Graphical database browser with schema explorer and visual query builder | macOS, Linux, Windows |
| SQLiteStudio | 3.12+ | Lightweight cross-platform graphical SQLite tool | macOS, Linux, Windows |
| DB Browser for SQLite | 3.12.2+ | Simple graphical interface for browsing and querying SQLite databases | macOS, Linux, Windows |
| PowerShell | 5.1+ (Windows 10) / 7.0+ (other platforms) | Shell and scripting language for environment variable management and file operations | Windows (5.1+), macOS (7.0+), Linux (7.0+) |
| Bash | 3.2+ (macOS) / 4.0+ (Linux) | POSIX shell for scripting database operations | macOS, Linux |

## Changelog

### Release 1.6 (2025-10-05)

Added section on database file size and WAL mode behavior. Clarified that `.db-wal` and `.db-shm` files are temporary and can be ignored. Noted that Windows hidden-file visibility may require explicit configuration in File Explorer. Minor clarifications to environment variable override section.

### Release 1.5 (2025-08-17)

Updated macOS database location documentation and confirmed via field evaluation that the `.oauthsvc` directory is auto-created on first run. Added note that directory recreation is automatic if manually removed.

### Release 1.4 (2025-06-22)

Expanded "Clearing the Database" section with multiple strategies (complete removal, selective table clearing, directory removal). Added mention of `scripts/clean-dev-env.sh` and `scripts/db-inspect.sh` helper scripts. Updated tool versions table to include SQLiteStudio and DB Browser for SQLite.

### Release 1.3 (2025-05-10)

Introduced database path environment variable override section with examples for Unix-like systems and Windows PowerShell. Reorganized "Inspecting the Database" with subsections for command-line and graphical approaches. Added important notes on avoiding modifications while service is running.

### Release 1.2 (2025-03-28)

Initial documentation of graphical SQLite tools, including DBeaver Community, SQLiteStudio, and DB Browser for SQLite. Added detailed warning section about not modifying the database while the service is running. Included example inspection session showing common workflows.

### Release 1.1 (2025-02-14)

First stable release. Documented default database locations for macOS, Linux, and Windows. Included basic `sqlite3` inspection commands, schema viewing, and file removal instructions. Established conventions for environment variable usage.

## Related Pages

- [Developer Handbook Overview](./README.md) (version 3.1, updated 2026-05-12)
- [Workstation Setup](./workstation-setup.md) (version 2.4, updated 2025-11-03)
- [Supported Python Versions](./python-version-support.md) (version 1.7, updated 2026-01-20)
- [Editor Configuration](./editor-configuration.md) (version v1.2.0, updated 2024-09-14)
- [Code Review Conventions](./code-review-conventions.md) (version 4.0, updated 2025-06-30)
- [Commit Message Style](./commit-message-style.md) (version 1.3, updated 2024-12-01)
- [Coding Style Guide](./coding-style-guide.md) (version 3.5, updated 2025-03-22)
- [Windows Setup Notes](./windows-setup-notes.rst) (version 1.1, updated 2025-08-09)
- [macOS Setup Notes](./macos-setup-notes.rst) (version 1.0, updated 2025-08-15)
- [Linux Setup Notes](./linux-setup-notes.txt) (version 0.9, updated 2024-05-27)
- [Dependency Management](./dependency-management.txt) (version 1.4, updated 2026-02-18)
- [Logging Conventions](./logging-conventions.md) (version 2.1, updated 2024-07-19)
- [Lint and Formatting Configuration](./lint-formatting-config.yaml) (version v1.0.1, updated 2026-04-01)

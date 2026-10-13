# Release Notes for v1.1.0

| | |
|---|---|
| **Title** | Release Notes for v1.1.0 |
| **Version** | v1.1.0 |
| **Owner** | Developer Experience (Priya Nandakumar) |
| **Last updated** | 2024-07-05 |

## Overview

Version 1.1.0 of accountsvc focuses on packaging cleanups and standardization of console log output. This release reduces the size and complexity of the source distribution, improves cross-timezone logging consistency, and maintains full backward compatibility with existing deployments. This document covers the v1.1.0 release, release procedures applicable to the accountsvc package, and reference information for prior releases.

For general orientation to release documentation, see the [Release Notes Folder Guide](README.md).

## What's New in v1.1.0

### Packaging Cleanups

The source distribution has been streamlined by removing unused configuration file templates and build artifacts. The package now produces distributions approximately 8% smaller than v1.0.0 while retaining all necessary source code and documentation. Build metadata that was previously split across multiple configuration locations is now consolidated in a single location, making the release process more predictable and reducing errors during installation on different platforms.

The `MANIFEST.in` file was also updated to be more explicit about which non-source files are included. This change prevents accidental inclusion of temporary files or IDE configuration that might have been present in the developer's working directory but shouldn't be distributed.

### Console Log Format Standardization

All diagnostic output from the service now uses ISO 8601 timestamps in the UTC timezone. Previously, the command-line tool used local system time while the loopback HTTP service used UTC, creating inconsistency when reviewing logs from different geographic regions or systems with mismatched time settings.

The new format for all timestamps is: `2024-07-05T14:32:18Z`

This change affects:
- Service startup and shutdown messages
- Account operation summaries (create, read, update)
- Database state messages
- Diagnostic output from the HTTP service

While this is a minor version bump, we recognized that some users might have log parsing or alerting scripts that depend on the timestamp format. The v1.1.0 version number signals that log-dependent tooling should be reviewed and updated if needed.

## Version Numbering Scheme

The accountsvc package follows semantic versioning as detailed in [Version Numbering Scheme](version-numbering.md). All version numbers use the format `MAJOR.MINOR.PATCH`, where:

- **MAJOR** version increments for breaking changes to the service's external contracts (command-line interface, HTTP API, or database schema)
- **MINOR** version increments for new functionality or significant non-breaking changes (such as the logging format standardization in v1.1.0)
- **PATCH** version increments for bug fixes, documentation updates, and internal improvements

In the version control system, release commits are tagged using the pattern `accountsvc-v1.1.0`. Release preparation occurs on a dedicated branch named `release/v1.1.0`, which is typically merged to the main branch after publication and then removed.

The package metadata file (`setup.cfg`) contains the authoritative version string. During development between releases, the version string is set to a development version (e.g., `1.2.0.dev0`) to distinguish unreleased builds.

## Changelog Conventions

Changes to accountsvc are documented according to the standards in [Changelog Conventions](changelog-conventions.md) and formatted as specified in [Changelog Entry Format](changelog-format.rst). Each release changelog entry includes:

- Release version number (e.g., v1.1.0)
- Release date in YYYY-MM-DD format
- A list of changes organized by category

Change categories used by accountsvc are:

- `[PACKAGING]` — Source distribution changes, build process improvements, metadata updates, or changes to how the package is assembled
- `[LOGGING]` — Modifications to console output format, timestamp handling, log verbosity, or diagnostic message content
- `[COMMAND]` — Changes to the command-line tool, new subcommands, option changes, or help text updates
- `[DOC]` — Documentation updates, new guides, or enhancements to existing documentation
- `[HTTP]` — Changes to the loopback HTTP service's request/response contracts (used infrequently)

Changelogs list most recent releases first. Each changelog entry is one line per change and includes the category prefix. Release notes that appear in the documentation (like this page) provide additional context beyond what the changelog entry itself contains.

## Release Checklist and Process

The step-by-step procedures for releasing accountsvc are documented in [Release Checklist](release-checklist.md). The checklist is organized into four phases:

**Phase 1: Pre-Release Verification** (4 steps)
- Verify that all intended changes are merged to the main branch
- Update the version string in `setup.cfg` to the release version
- Review all changelog entries for completeness, accuracy, and correct formatting
- Ensure that any documentation that references version numbers has been updated

**Phase 2: Build and Packaging** (5 steps)
- Run the source distribution build process using the standard Python packaging tools
- Verify that the generated distribution package contains the expected directory structure and all necessary files
- Extract the distribution package in a temporary location and confirm its validity
- Verify that the service launches without errors in the extracted distribution
- Confirm that version information displayed by the service matches the release version number

**Phase 3: Publication and Release** (4 steps)
- Create the Git version tag (e.g., `accountsvc-v1.1.0`) on the final commit
- Upload the source distribution package to the package server and verify its availability
- Update the release index file to list the new version as available
- Publish the release notes to the internal documentation wiki

**Phase 4: Post-Release** (5 steps)
- Update the main branch for the next development cycle
- Bump the version string to the next development version (e.g., `1.2.0.dev0`)
- Send an announcement to the development team
- Verify that the old release can still be downloaded from the package server
- Monitor the first 48 hours for issues reported by users

The v1.1.0 release completed this entire process on 2024-07-05. The average time from start of Phase 1 to completion of Phase 4 is approximately 4 hours.

## Packaging the Source Distribution

Detailed procedures for creating and validating the source distribution are in [Packaging the Source Distribution](packaging-source-distribution.rst). The following is a summary of the key elements.

### Distribution Structure

A source distribution of accountsvc contains the following structure (example shown for v1.1.0):


For v1.1.0, the compressed distribution is approximately 47 KB. When extracted, it occupies approximately 220 KB on disk. The distribution includes all source code, documentation, and build scripts but does not include the SQLite database file (which is created fresh when the service is first run on the target system).

### Build Process

To create the source distribution, execute:

```bash
python setup.py sdist
```

This command generates `accountsvc-v1.1.0.tar.gz` in the `dist/` directory. The filename is automatically determined by the version string in the package metadata.

After building, always verify the distribution by extracting it in a temporary directory and confirming:
- The directory structure matches the expected layout above
- No unexpected files are present (such as compiled files or cache directories)
- The package can be imported without errors when extracted
- Setup scripts run without errors in the extracted directory

See [Source Distribution Notes](source-distribution-notes.txt) for additional troubleshooting information.

## Prior Release Notes Summary

Release notes for accountsvc document changes in five categories: documentation, packaging, command-line help text, console log format, and performance. This coverage reflects the package's user-facing capabilities as a Python package with a command-line interface and loopback HTTP service.

### v1.0.0 — 2024-03-18

The initial release established the basic package structure and functionality. See [Release Notes for v1.0.0](release-notes-v1.0.0.md) for complete details.

- Documentation: Initial complete documentation set including getting-started guide and architecture overview
- Packaging: First source distribution using Python standard packaging conventions
- Command-line Interface: Account management commands (create, read, update, list)
- Console Logging: Basic log output with local timezone timestamps and millisecond precision
- Performance: Baseline performance established for single-account operations

### v1.2.0 — 2024-10-22

This release added bulk operation support. Full details are in [Release Notes for v1.2.0](release-notes-v1.2.0.md).

- Documentation: New comprehensive guide for bulk account operations; updated all command references
- Packaging: Added optional dependency for parallel processing; new scripts for distribution validation
- Command-line Interface: New `bulk` subcommand supporting `--input-file` and `--output-file` options
- Console Logging: Added progress indicators and diagnostic output during bulk operations
- Performance: Implemented database connection pooling, improving account lookups by approximately 30%

### v2.0 — 2025-02-11

Major version introducing the loopback HTTP service as a primary interface. See [Release Notes for 2.0](release-notes-2.0.md).

- Documentation: Architectural documentation completely rewritten to cover HTTP service; added library integration guides
- Packaging: Unified build system by removing legacy build scripts and consolidating configuration
- Command-line Interface: Deprecated several command-line tools in favor of equivalent HTTP service methods; maintained backward compatibility
- Console Logging: Added correlation IDs to all log lines for tracing related operations across service components
- Performance: HTTP service startup improved from approximately 2 seconds to 500 milliseconds

### v2.1 — 2025-05-27

Point release focusing on logging improvements and user experience. See [Release Notes for 2.1](release-notes-2.1.md).

- Documentation: New troubleshooting guide; added dedicated logging chapter to the main user documentation
- Packaging: Minor cleanup of distribution contents; removed unused legacy configuration templates
- Command-line Interface: Updated all help text for consistency and clarity
- Console Logging: Introduced log level filtering; added optional color coding for terminal output for improved readability
- Performance: No significant changes; focus was on operational usability

### v2.2 — 2025-09-15

Recent release with configuration management features. See [Release Notes for 2.2](release-notes-2.2.md).

- Documentation: Added configuration reference section; updated deployment guide with configuration examples
- Packaging: Source distribution now includes example configuration files in a dedicated folder
- Command-line Interface: Main command now accepts `--help-config` to display configuration file syntax
- Console Logging: Timestamp format changed to ISO 8601 with UTC timezone
- Performance: Database initialization is 10–15% faster due to query optimization improvements

Note: v2.2 was released after v1.1.0. For release timing information, consult [Release Schedule](release-schedule.yaml).

## Terminology and Glossary

**Semantic Versioning**
A version numbering system using three parts: MAJOR.MINOR.PATCH. MAJOR changes indicate incompatibility, MINOR indicates new backward-compatible features, and PATCH indicates bug fixes. See [Version Numbering Scheme](version-numbering.md) for accountsvc-specific details.

**Source Distribution**
A packaged, compressed bundle containing the complete source code of the package, all documentation, and build scripts. The accountsvc source distribution uses `.tar.gz` format. This format is suitable for redistribution and installation on any platform with Python and the standard library.

**Changelog**
A structured document recording all changes made in each release. The accountsvc changelog is organized by version and release date, with changes grouped by category (Packaging, Logging, Command, Documentation, HTTP). The changelog is separate from and less detailed than release notes.

**Release Branch**
A temporary Git branch created during the release process to prepare the final release artifacts. For v1.1.0, the release branch was `release/v1.1.0`. After the release is published, the release branch is merged to main and removed.

**Version Tag**
A named Git reference marking the exact commit corresponding to a released version. Version tags follow the naming pattern `accountsvc-v1.1.0`. Tags are immutable once created and serve as the authoritative marker for each release.

**Console Log Format**
The structure and content of diagnostic messages that the service prints to standard output or standard error. This includes timestamp format, log level indicators, message text, and any other diagnostic information. Changes to console log format are tracked as release changes because they may affect log parsing or monitoring tools.

**Build Artifact**
Any file or set of files generated by the build process. For accountsvc, the primary build artifact is the source distribution package (the `.tar.gz` file). Build artifacts are what users download and install.

**Account**
A customer account managed by the service. Accounts are stored in the SQLite database file and are accessible via both the command-line tool and the HTTP service. Each account has a unique identifier and associated state information (such as creation date and account metadata).

**Loopback HTTP Service**
The built-in HTTP server provided by the accountsvc package. The service runs on the local machine and listens on a configurable port. The loopback service provides an HTTP-based alternative to the command-line tool for account operations.

**Database File**
The SQLite database file used by accountsvc to store account information. The database file is created automatically on first run and persists locally. The database file is not included in the source distribution.

## Repository Files and Paths

| Path | Purpose |
|------|------|
| `docs/release-notes/` | Folder containing all release-related documentation pages |
| `docs/release-notes/README.md` | Guide to the release notes folder structure and page navigation |
| `docs/release-notes/release-notes-v1.1.0.md` | This page; comprehensive release notes for v1.1.0 |
| `docs/release-notes/version-numbering.md` | Specification of semantic versioning conventions used by accountsvc |
| `docs/release-notes/changelog-conventions.md` | Rules for documenting changes in changelog entries |
| `docs/release-notes/release-checklist.md` | Complete checklist and procedure for performing a release |
| `docs/release-notes/packaging-source-distribution.rst` | Detailed guide to building and validating source distributions |
| `docs/release-notes/source-distribution-notes.txt` | Supplementary notes, troubleshooting, and edge cases for packaging |
| `docs/release-notes/changelog-format.rst` | Formatting specification for individual changelog entries |
| `docs/release-notes/release-schedule.yaml` | Timeline and dates for planned future releases |
| `docs/release-notes/release-notes-v1.0.0.md` | Release notes for the v1.0.0 initial release |
| `docs/release-notes/release-notes-v1.2.0.md` | Release notes for the v1.2.0 point release |
| `docs/release-notes/release-notes-2.0.md` | Release notes for the v2.0 major version release |
| `docs/release-notes/release-notes-2.1.md` | Release notes for the v2.1 point release |
| `docs/release-notes/release-notes-2.2.md` | Release notes for the v2.2 point release |
| `accountsvc/` | Root package directory; contains all source code for the package |
| `setup.py` | Python build script; defines package metadata and dependencies |
| `setup.cfg` | Build configuration file; contains the authoritative version string |
| `MANIFEST.in` | Specifies which non-Python files to include in source distributions |
| `scripts/build.sh` | Utility script for building the package locally in a development environment |
| `scripts/build-dist.sh` | Utility script for creating the source distribution package |
| `README.md` | Repository root readme file |

## Tools, Packages, and Dependencies

| Tool/Package | Version | Purpose |
|---|---|---|
| Python | 3.9+ | Runtime environment for the package |
| setuptools | 63.0+ | Build system and distribution utilities |
| tar | system default | Bundling tool for creating distribution tarballs |
| gzip | system default | Compression utility for distribution packages |
| git | 2.20+ | Version control; used for tagging and branch management |
| sqlite3 | 3.26+ | Embedded database engine used for account storage |
| bash / sh | system default | Shell environment for build and utility scripts |

## Changelog

### v1.1.0 — 2024-07-05

- [PACKAGING] Removed unused configuration file templates from source distribution
- [PACKAGING] Consolidated build metadata from multiple files into single setup.cfg location
- [PACKAGING] Source distribution size reduced by approximately 8% through cleanup
- [LOGGING] Changed all console timestamps to ISO 8601 format with UTC timezone
- [LOGGING] Standardized timestamp format between command-line tool and HTTP service
- [DOC] Updated logging documentation to reflect new timestamp format and guidelines

### v1.0.0 — 2024-03-18

- [PACKAGING] Initial source distribution created using Python standard packaging
- [PACKAGING] Established automated build process in scripts directory
- [DOC] Published complete initial documentation set
- [COMMAND] Implemented account management command-line interface with subcommands
- [LOGGING] Added basic console logging with local timezone timestamps
- [DOC] Created getting-started guide for new users and maintainers

### v1.2.0 — 2024-10-22

- [COMMAND] Added bulk account operations subcommand with file-based input/output
- [LOGGING] Added progress indicators for bulk operations
- [PACKAGING] Added support for optional dependencies in distribution metadata
- [DOC] Published comprehensive guide to bulk account operations
- [DOC] Updated command reference documentation for all tools
- [LOGGING] Implemented diagnostic messages for bulk operation tracking

### v2.0 — 2025-02-11

- [HTTP] Introduced loopback HTTP service as primary interface for account operations
- [LOGGING] Added correlation IDs to console log lines for request tracing
- [COMMAND] Deprecated several command-line tools in favor of HTTP service methods; maintained compatibility
- [DOC] Completely rewrote architectural documentation for HTTP service focus
- [PACKAGING] Unified build system and removed legacy build scripts
- [DOC] Added HTTP library integration examples and best practices guide

### v2.1 — 2025-05-27

- [LOGGING] Introduced log level filtering for reduced console verbosity
- [LOGGING] Added optional color coding to terminal output based on log level
- [DOC] Published troubleshooting guide for common operational issues
- [DOC] Added dedicated logging chapter to main user documentation
- [PACKAGING] Minor cleanup of source distribution contents and file organization

### v2.2 — 2025-09-15

- [DOC] Added configuration reference page with detailed option documentation
- [PACKAGING] Included example configuration files in source distribution
- [COMMAND] Added `--help-config` option to main command for configuration syntax
- [LOGGING] Changed timestamp format to ISO 8601 with UTC timezone
- [DOC] Updated deployment guide with new configuration examples and recommendations

## Related Pages

- [Release Notes Folder Guide](README.md) — Overview and navigation guide for all release documentation
- [Version Numbering Scheme](version-numbering.md) — Semantic versioning specification for accountsvc
- [Changelog Conventions](changelog-conventions.md) — Standards and conventions for documenting changes
- [Changelog Entry Format](changelog-format.rst) — Formatting rules for individual changelog entries
- [Release Checklist](release-checklist.md) — Step-by-step procedures for publishing a new release
- [Packaging the Source Distribution](packaging-source-distribution.rst) — Detailed guide to building distributions
- [Source Distribution Notes](source-distribution-notes.txt) — Supplementary notes and troubleshooting for packaging
- [Release Schedule](release-schedule.yaml) — Timeline and planning information for upcoming releases
- [Release Notes for v1.0.0](release-notes-v1.0.0.md) — Release notes for the initial v1.0.0 release
- [Release Notes for v1.2.0](release-notes-v1.2.0.md) — Release notes for the v1.2.0 point release
- [Release Notes for 2.0](release-notes-2.0.md) — Release notes for the v2.0 major version
- [Release Notes for 2.1](release-notes-2.1.md) — Release notes for the v2.1 point release
- [Release Notes for 2.2](release-notes-2.2.md) — Release notes for the v2.2 point release

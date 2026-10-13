# Release Notes: v1.2.0

**Version:** v1.2.0  
**Owner:** Release Engineering (Priya Chandran)  
**Last updated:** 2025-02-27  

## Overview

This document records packaging, speed, and documentation changes in oauthsvc v1.2.0, released 2025-02-19. v1.2.0 is a stable patch release that consolidates improvements to the command-line interface documentation, the loopback service's console output format, and distribution packaging procedures. This release does not include feature additions or changes to the package's core behavior.

## Version Numbering and Release Model

The oauthsvc package follows semantic versioning: MAJOR.MINOR.PATCH. See the full scheme in [Version Numbering Scheme](version-numbering.md).

**Summary for v1.2.0:**

- MAJOR version: 1 (stable API, no breaking changes since inception)
- MINOR version: 2 (incremented for non-breaking feature additions; documentation and packaging count as feature improvements)
- PATCH version: 0 (no bug fixes, only documentation and packaging in this release)

The version string is defined in two locations (both must be updated during release):
1. The package's primary version metadata
2. The documentation index

These locations are maintained separately by convention; the version-numbering page describes the full set. Synchronizing versions across both is a release milestone.

## Changelog Conventions

All changes in v1.2.0 follow the changelog format documented in [Changelog Conventions](changelog-conventions.md). Each entry names the release, the date, the category (Documentation, Packaging, or Speed), and a brief description of the impact.

**Key conventions applied to v1.2.0:**

- Entries are ISO 8601 dates (YYYY-MM-DD)
- Category labels are capitalized: Documentation, Packaging, Console Output, Speed
- Entries are sorted newest first
- Each entry includes the release name and version
- Documentation changes refer to the affected page or system

The changelog entry format is also specified in [Changelog Entry Format](changelog-entry-format.yaml) for machine-readable purposes.

## Release Checklist and Procedure

The [Release Checklist](release-checklist.md) (v1.0.3, last updated 2026-02-14) is the authoritative procedure for preparing and publishing a release. For v1.2.0, the following high-level steps were performed (in order):

1. **Documentation review** – All documentation pages were examined for accuracy, consistency, and completeness
2. **Version string updates** – Version numbers were incremented in metadata files
3. **Changelog entry creation** – Entries were added to the package changelog
4. **Console output review** – Service log format was checked against [Console Log Format Notes](console-log-format-notes.md)
5. **Command help validation** – Command-line help text was reviewed against the [Command Help Text Style Guide](command-help-text-style.md)
6. **Packaging preparation** – The source distribution was built following [Building the Source Distribution](building-source-distribution.rst)
7. **Final verification** – Release artifacts were verified in isolation

The checklist is maintained by Release Engineering and is reviewed quarterly (next review due June 2025).

## Packaging and Source Distribution

The oauthsvc package is distributed as a source distribution. The [Source Distribution Packaging Guide](packaging-guide.rst) (v1.4, last updated 2024-09-10) describes the full procedure; the [Building the Source Distribution](building-source-distribution.rst) (v2.0.1, updated 2025-07-01) guide provides step-by-step instructions.

### Packaging Changes in v1.2.0

No changes to the distribution format or build process were introduced in v1.2.0. The source distribution continues to include:

- The oauthsvc package directory
- A README.md in the repository root
- Documentation and release notes
- Scripts for maintenance and build support

The build procedure remains stable. New releases use the same process: source files are collected, a tarball or ZIP package is created, and the package is prepared and published. For specific commands and tooling, see [Building the Source Distribution](building-source-distribution.rst).

### Distribution Metadata

The package metadata (name, version, author, homepage) is stored in the standard Python package configuration file in the repository root. This metadata is read during the build step and embedded in the source distribution package.

| Metadata Field | Value | Notes |
|---|---|---|
| Package Name | oauthsvc | Used in pip and package indices |
| Version | 1.2.0 | Must match git tag and documentation |
| Author | Platform Tools | Team name from README.md |
| License | Apache 2.0 | Included in COPYING file |
| Python Version | 3.8+ | Standard library only |
| Repository | Internal git | No external dependencies |

### Past Distribution Issues

v1.1.0 (released 2024-08-15, see [Release Notes: v1.1.0](release-notes-v1.1.0.txt)) had an inconsistency: the version string in the metadata file was "1.1.0" but the documentation index still referenced "v1.0.5" in one location. This was corrected in a rapid patch. v1.2.0 checks for this during release preparation.

## Documentation Changes

### Command Help Text

Documentation improvements to the package's command-line interface were a primary focus of v1.2.0. All command help text was reviewed and updated to follow the [Command Help Text Style Guide](command-help-text-style.md) (v1.3.0, last updated 2024-11-05).

Specific updates include:

- Help text now consistently uses sentence case for descriptions
- Option descriptions are more concise (target: one line maximum, 70 characters)
- Examples in help output were expanded to show common workflows
- Short and long option names are now consistently formatted (e.g., `-h, --help`)

The help text is output by the package's command-line interface. Users see the updated text immediately when they invoke the help option. No configuration or documentation update is required on the user side.

### Console Log Format

The service's loopback HTTP component writes status messages and diagnostic information to the console (stdout and stderr). In v1.2.0, the console output format was refined to improve readability and consistency. See [Console Log Format Notes](console-log-format-notes.md) (v1.1, updated 2026-03-22, owned by Developer Experience).

**Console output changes in v1.2.0:**

- Timestamp format is now ISO 8601 with millisecond precision: `2025-02-19T14:32:47.123+00:00`
- Log level is now uppercase and padded to 8 characters: `INFO    `, `WARNING `, `ERROR   `
- Message body is indented by four spaces for nested service events
- File paths in log output use forward slashes regardless of platform (normalized on Windows)

Example console output (v1.2.0 format):

```
2025-02-19T14:32:47.123+00:00 INFO     Service starting on localhost:8080
2025-02-19T14:32:47.124+00:00 INFO     Loading database file: /home/user/.local/share/oauthsvc/state.db
2025-02-19T14:32:47.156+00:00 INFO     Database ready
2025-02-19T14:32:47.157+00:00 INFO     HTTP listener ready
2025-02-19T14:32:48.002+00:00 INFO         Received request from 127.0.0.1:52891
2025-02-19T14:32:48.003+00:00 INFO         Processing complete, response sent
```

The console format is not configurable; it is fixed for consistency across all deployments.

### Release Notes for Prior Versions

**v1.1.0** ([Release Notes: v1.1.0](release-notes-v1.1.0.txt), released 2024-08-15): Included packaging updates and command help text improvements. The help text style was partially aligned with the style guide in this release, though full alignment did not occur until v1.2.0.

**v1.0.0** ([Release Notes: v1.0.0](release-notes-v1.0.0.txt), released 2024-04-02): The initial stable release. Console output was unformatted; timestamps and log levels were inconsistent. This version is still supported for production use.

**v2.0.0** ([Release Notes: v2.0.0](release-notes-v2.0.0.md), released 2025-12-09, owner Documentation Guild): This release includes breaking changes to the database schema and will feature comprehensive migration documentation. Release notes for v2.0.0 are provisional and subject to change.

## Speed and Performance

Performance analysis was conducted for v1.2.0, focusing on startup time and database initialization speed. Documentation improvements in this release should not impact runtime performance.

- **Package startup time:** ~150 milliseconds on a typical development machine (3.6 GHz quad-core). No change from v1.1.0.
- **Database initialization:** ~50 milliseconds for a 1,000-row database file. Consistent with v1.1.0.
- **Command-line invocation:** ~180 milliseconds end-to-end (includes Python interpreter startup). Documentation changes are read-only and do not affect performance.

Detailed performance notes are maintained in [Speed Notes Across Releases](speed-notes.md) (v2.0, updated 2025-10-18). That page tracks performance data across all releases and is the source of truth for performance comparisons.

## Glossary and Terminology

**Changelog**
A structured log of changes made between releases. In oauthsvc, the changelog is maintained in a central file and organized by release version and date. See [Changelog Conventions](changelog-conventions.md).

**Command-line Interface (CLI)**
The package's text-based user interaction layer. The service can be invoked from the shell to perform operational tasks or query status. Help text is part of the CLI.

**Console Output**
Unstructured text written to stdout or stderr by the service. In v1.2.0, console output follows a fixed format including timestamps and log levels.

**Database File**
A local SQLite file that stores the service's state. The file location is platform-specific (see [Console Log Format Notes](console-log-format-notes.md) for examples). The database is initialized on first run.

**Loopback HTTP Service**
The background component of oauthsvc that listens on localhost and responds to HTTP requests. It uses only the Python standard library.

**Release**
A versioned copy of the package, distributed as a source distribution. Releases follow semantic versioning (MAJOR.MINOR.PATCH). A release includes tagged code, documentation, and packaging artifacts.

**Semantic Versioning**
A versioning scheme where version numbers have three components: MAJOR (breaking changes), MINOR (non-breaking features), PATCH (bug fixes). Detailed explanation is in [Version Numbering Scheme](version-numbering.md).

**Source Distribution**
A packaged bundle (typically tar.gz or ZIP) containing the package source code, documentation, and metadata. Users can extract and build from a source distribution without cloning a git repository. See [Source Distribution Packaging Guide](packaging-guide.rst).

**Standard Library**
The Python standard library, consisting of modules provided by the Python interpreter without external dependencies. oauthsvc uses only the standard library; it has no third-party dependencies.

**Version String**
The text representation of the package version, e.g., "v1.2.0" or "1.2.0" (with or without the "v" prefix). Version strings must be updated in multiple locations during a release.

## Repository Files and Paths

The following files and directories are referenced in this release and in release procedures:

| File or Path | Purpose |
|---|---|
| `/oauthsvc/` | Package source directory. Contains Python package modules and core implementation. |
| `/README.md` | Repository root README. Describes the package and project overview. |
| `/docs/` | Documentation folder. Contains release notes, guides, and internal wikis. |
| `/docs/release-notes/` | Release notes subfolder. Contains versioned release notes and related pages. |
| `/docs/release-notes/changelog-conventions.md` | Defines changelog format and entry standards. |
| `/docs/release-notes/release-checklist.md` | Step-by-step release procedure and sign-off checklist. |
| `/docs/release-notes/version-numbering.md` | Defines the version numbering scheme (semantic versioning). |
| `/docs/release-notes/packaging-guide.rst` | Describes source distribution format and contents. |
| `/docs/release-notes/building-source-distribution.rst` | Step-by-step guide to building the package. |
| `/docs/release-notes/console-log-format-notes.md` | Documents console output format and timestamp rules. |
| `/docs/release-notes/command-help-text-style.md` | Style guide for command help text and descriptions. |
| `/docs/release-notes/speed-notes.md` | Performance metrics across releases. |
| `/scripts/` | Utility scripts for build and deployment operations. |
| `~/.local/share/oauthsvc/state.db` | Local database file location on Linux/Mac (example path). |
| `%APPDATA%\oauthsvc\state.db` | Local database file location on Windows (example path). |

## Tools, Packages, and Versions

This table lists key tools and Python standard library modules used in the release process and runtime for v1.2.0:

| Tool / Module | Version | Purpose |
|---|---|---|
| Python | 3.8+ | Interpreter for package runtime and build scripts. |
| sqlite3 | 3.35.0+ | Standard library module for database access and management. |
| http.server | Standard library | Built-in HTTP server component of the service. |
| argparse | Standard library | Command-line argument parsing for CLI. |
| logging | Standard library | Logging framework for console output formatting. |
| git | 2.30+ | Version control for repository management and tagging. |
| tar | Any POSIX version | Used to create source distribution packages (Linux/Mac). |
| ZIP utility | Any Windows version | Used to create source distribution packages (Windows). |
| Markdown | N/A (docs format) | Documentation format for release notes and guides. |

## Changelog

All dated entries below refer to changes introduced in v1.2.0 or critical milestones affecting the release. Entries are sorted newest first.

**2025-02-27 – v1.2.0 Release (Final Documentation Update)**
Documentation Guild (Sana Iqbal) completed final review. All release notes pages were updated to reflect v1.2.0 status. Ownership of speed notes was transferred to Developer Experience (Theo Banks).

**2025-02-19 – v1.2.0 Release (Published)**
Release Engineering (Priya Chandran) published v1.2.0 source distribution. All release checklist items were completed. Git tag v1.2.0 was created. Distribution published to internal package repository.

**2025-02-15 – Console Output Format Finalized**
Packaging: The console log format was updated to ISO 8601 timestamps and normalized path separators. Final verification confirmed output matches [Console Log Format Notes](console-log-format-notes.md) v1.1. Two edge cases (long paths on Windows, Unicode in messages) were identified and documented.

**2025-02-12 – Command Help Text Review Completed**
Documentation: All help text was reviewed and updated to align with [Command Help Text Style Guide](command-help-text-style.md) v1.3.0. Approximately 40 option descriptions were shortened to meet the 70-character guideline. Five examples were added to the main command help output.

**2025-02-05 – Packaging Preparation Began**
Packaging: Release engineering team began source distribution build procedure. Version strings were updated in metadata file and documentation index (note: documentation index still contained reference to v1.1.0 in one location at this point; corrected 2025-02-18).

**2025-01-28 – v1.2.0 Planning and Extent Finalized**
Documentation: Release plan was confirmed to include documentation, console output, and command help improvements only. No feature changes or performance regressions in this release. Speed analysis initiated by Developer Experience team.

## Related Pages

- [Release Notes Folder Index](README.md) – Overview of all release notes and related pages (v3.4, updated 2026-05-12)
- [Version Numbering Scheme](version-numbering.md) – Detailed semantic versioning rules (v1.2.0, updated 2024-06-03)
- [Changelog Conventions](changelog-conventions.md) – Entry format and categorization standards (v2.1, updated 2025-01-20)
- [Release Checklist](release-checklist.md) – Step-by-step release procedure (v1.0.3, updated 2026-02-14)
- [Source Distribution Packaging Guide](packaging-guide.rst) – Format and contents of releases (v1.4, updated 2024-09-10)
- [Building the Source Distribution](building-source-distribution.rst) – Build instructions (v2.0.1, updated 2025-07-01)
- [Console Log Format Notes](console-log-format-notes.md) – Service output formatting rules (v1.1, updated 2026-03-22)
- [Command Help Text Style Guide](command-help-text-style.md) – Help text conventions (v1.3.0, updated 2024-11-05)
- [Speed Notes Across Releases](speed-notes.md) – Performance analysis and accumulated data (v2.0, updated 2025-10-18)
- [Release Notes: v1.1.0](release-notes-v1.1.0.txt) – Previous stable release notes (v1.1.0, updated 2024-08-15)
- [Release Notes: v1.0.0](release-notes-v1.0.0.txt) – Initial release notes (v1.0.0, updated 2024-04-02)
- [Release Notes: v2.0.0](release-notes-v2.0.0.md) – Future release with schema changes (v2.0.0, updated 2025-12-09)

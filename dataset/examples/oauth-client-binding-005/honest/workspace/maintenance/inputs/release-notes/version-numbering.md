# Version Numbering Scheme

**Title:** Version Numbering Scheme  
**Version:** v1.2.0  
**Owner:** Release Engineering (Priya Chandran)  
**Last Updated:** 2024-06-03

**Summary:** This page defines how version numbers are assigned to oauthsvc releases, establishes changelog and release note conventions, and documents the release process including packaging and distribution steps.

---

## Overview

All releases of the oauthsvc package follow semantic versioning with the format `MAJOR.MINOR.PATCH`. Version numbers appear in distribution metadata, release notes, git tags, and documentation. This scheme ensures clarity about breaking changes, new capabilities, and maintenance updates.

The oauthsvc release process involves multiple artifacts: the Python source distribution, release notes, changelog entries, and updated command help text. All components must be versioned consistently and documented before a release is tagged in the repository.

---

## Semantic Versioning Rules

**Owner:** Release Engineering (Priya Chandran)

The oauthsvc package adheres to semantic versioning with these rules:

- **MAJOR version** increments when breaking changes are introduced to the command-line interface, the loopback HTTP service API, or the local SQLite database file format. Existing deployments or scripts may cease to function without modifications.
- **MINOR version** increments when new features are added in a backward-compatible manner. Existing code continues to work without changes, but new options or capabilities become available.
- **PATCH version** increments for backward-compatible maintenance updates. This includes bug fixes, documentation improvements, packaging changes, command help text refinements, console log format adjustments, and performance optimizations.

Do not bump the MAJOR version for improvements to startup speed or request handling speed unless those changes alter the external interface or observable behavior in ways that existing deployments might depend on. Refer to speed-notes.md for performance-related changes across releases.

### Examples of Version Increments

| Change | Previous Version | New Version | Reason |
|--------|---|---|---|
| Add new command-line option | v1.2.5 | v1.3.0 | MINOR: backward-compatible feature addition |
| Fix crash in HTTP handler | v1.3.0 | v1.3.1 | PATCH: bug fix |
| Change console log timestamp format | v1.3.1 | v1.3.2 | PATCH: log format refinement |
| Alter database file structure | v1.3.2 | v2.0.0 | MAJOR: breaking change |
| Update README documentation | v1.3.1 | v1.3.2 | PATCH: documentation improvement |
| Optimize SQLite startup performance | v1.3.1 | v1.3.2 | PATCH: performance optimization |

---

## Git Tags and Release Branches

Each release is tagged in the git repository using the version number prefixed with `v`: `v1.0.0`, `v1.1.0`, `v1.2.0`, etc. The tag is placed on the commit that updates version.txt and creates the source distribution. Use the command:

```bash
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
```

For maintenance releases of older MINOR versions, create a release branch named `release/v1.X` (e.g., `release/v1.2`). Work on that branch to backport critical fixes. Tag and release from the branch:

```bash
git checkout -b release/v1.2
# Make backport changes
git tag -a v1.2.1 -m "Patch release 1.2.1"
git push origin release/v1.2 v1.2.1
```

After releasing v2.0.0, the v1.2.x branch remains available for backports, though new development occurs on main.

---

## Changelog and Changelog Entries

**Owner:** Documentation Guild (Sana Iqbal)

A changelog file (CHANGELOG.md in the repository root) maintains a running record of all notable changes across releases. Each release gets a section headed with the version number and release date in the format `## vX.Y.Z (YYYY-MM-DD)`. Entries within a release are grouped by category:

- **Documentation**: updates to README, docstrings, inline help, or in-package guidance
- **Packaging**: changes to distribution metadata, scripts/build.sh, setup.py, or installation procedures
- **Command Help**: alterations to help text, option descriptions, or examples shown via --help
- **Console Log Format**: modifications to log message structure, verbosity levels, timestamp format, or log file output
- **Speed**: performance improvements, timing optimizations, or latency reductions
- **Bugfixes**: improvements to command-line parsing, HTTP request handling, and database operations (excluding system hardening)
- **Internal**: refactors, code cleanup, and repository structure changes

See changelog-conventions.md (version 2.1, updated 2025-01-20) for exact formatting rules and changelog-entry-format.yaml (version 1.0, updated 2026-06-01) for the structured entry schema.

#### Example Changelog Entry

The following entry from CHANGELOG.md illustrates the format:

```
## v1.2.0 (2025-02-20)

### Documentation
- Updated README with step-by-step examples of loopback service startup
- Clarified SQLite database file initialization in package docstring

### Command Help
- Added --verbose flag description (was missing from v1.1.0)
- Corrected example command output in help text to match actual behavior
- Fixed typo in --config option description

### Console Log Format
- Changed timestamp format from ISO 8601 to RFC 3339 with millisecond precision
- Removed redundant "service:" prefix in startup messages for clarity
- Increased verbosity of initialization log to aid diagnostics

### Speed
- Optimized SQLite connection pooling, reducing initial startup time by ~5%
- Reduced latency in HTTP request handler by caching metadata lookups
```

All changelog entries must be committed to CHANGELOG.md before tagging a release. Do not append entries after a release has been tagged; backport them to an existing PATCH version or include them in the next MINOR or MAJOR release.

---

## Release Checklist

**Owner:** Release Engineering (Priya Chandran)

Before each release, follow the release-checklist.md page (version v1.0.3, updated 2026-02-14), which covers these major steps in detail:

1. Ensure all changes are committed and the working tree is clean (`git status` shows no uncommitted changes)
2. Update CHANGELOG.md with all notable changes in the release, organized by category
3. Update the version number in version.txt (without the `v` prefix; e.g., `1.2.0`)
4. Update version numbers in setup.py and setup.cfg to match
5. Build the source distribution using scripts/build.sh
6. Validate that command help text matches the style guide (command-help-text-style.md, version v1.3.0)
7. Verify console log format matches documented standards (console-log-format-notes.md, version 1.1)
8. Create or update the release notes document in docs/release-notes/release-notes-vX.Y.Z.md
9. Tag the repository with the version (`git tag -a vX.Y.Z`)
10. Publish the source distribution to the package repository
11. Verify that the published distribution can be installed and the package functions

The release-checklist.md page is the authoritative list and must be consulted for current procedures; this page provides only an outline.

---

## Source Distribution Packaging

**Owner:** Core Services (Liam Fitzgerald)

The oauthsvc source distribution is created using standard Python tools. The package directory structure at the repository root is:


The version.txt file contains only the version string without the leading `v` character (e.g., `1.2.0`). This file is read by setup.py and build scripts to populate package metadata consistently.

To build the source distribution:

```bash
cd /path/to/oauthsvc
cat version.txt
# Output: 1.2.0
bash scripts/build.sh sdist
ls -lh dist/
# Output: oauthsvc-1.2.0.tar.gz
```

After building, verify the tarball contains:

- The complete oauthsvc package directory with all modules
- CHANGELOG.md with all release notes
- README.md with usage instructions
- docs/ folder and all documentation including release-notes/ subfolder
- setup.py and setup.cfg with correct version metadata
- scripts/ folder with build utilities

Extract the tarball and run a sanity check:

```bash
tar tzf dist/oauthsvc-1.2.0.tar.gz | head -20
# Should list package files in the oauthsvc-1.2.0/ directory
```

The packaging-guide.rst (version 1.4, updated 2024-09-10) and building-source-distribution.rst (version v2.0.1, updated 2025-07-01) pages provide full packaging details. Note that packaging-guide.rst may be out of date; prefer building-source-distribution.rst for current best practices.

---

## Release Notes Format

Release notes are published in the docs/release-notes/ folder for each version as `release-notes-vX.Y.Z.md`. Release notes differ from the CHANGELOG in that they are prose-oriented and audience-facing, while the CHANGELOG is a technical list of changes. A release notes document should include:

- A brief summary of the release purpose and target audience
- Major improvements in documentation and README updates
- Packaging and distribution changes (new installation methods, minimum Python version requirements, etc.)
- Significant changes to command help text or CLI interface
- Changes to console log output format and readability, with before/after examples
- Notable speed improvements or performance optimizations with measured results
- Any backward-compatibility notes or upgrade instructions (especially for MINOR and MAJOR releases)
- Installation and validation instructions for users deploying the new version

Release notes do not cover system hardening, internal refactors, module-level changes, or data model details; those belong in the CHANGELOG under the appropriate category.

#### Example Release Notes Structure

A typical release notes document (e.g., release-notes-v1.2.0.md) might be organized as:

- **Overview**: what this version accomplishes
- **Installation**: how to obtain and install the new version
- **Documentation Updates**: new guides, improved examples, clarified procedures
- **Command-Line Interface**: changes to commands, options, or help text
- **Console Output**: changes to log format, timestamps, verbosity
- **Performance**: speed improvements with before/after metrics (see speed-notes.md for detailed data)
- **Upgrading from Previous Versions**: compatibility notes and migration steps
- **Known Issues**: any limitations or workarounds

---

## Terminology and Glossary

**Semantic Versioning**: A versioning scheme using three numbers (MAJOR.MINOR.PATCH) to indicate the nature of changes; increments in each position signal breaking changes, new features, or maintenance updates respectively.

**Source Distribution**: A packaged form of the oauthsvc code suitable for installation, typically a tarball (`.tar.gz`) containing all source files, metadata, and documentation. Created by the build process and published to package repositories.

**Release Tag**: A git tag prefixed with `v` (e.g., `v1.2.0`) that marks the commit corresponding to a release. Enables reproducible builds and clear version lineage in version control.

**Changelog**: A file (CHANGELOG.md) in the repository root documenting all notable changes across releases, organized by version number and category (Documentation, Packaging, Command Help, etc.).

**Console Log Format**: The structure, verbosity level, timestamp format, and styling of text output produced by the service or command-line interface during operation. Examples include RFC 3339 timestamps or prefixed log levels.

**Command Help Text**: The text displayed by the command-line interface when the user requests help (e.g., with `--help` flag), including option descriptions, examples, and usage patterns. Must conform to command-help-text-style.md standards.

**Release Notes**: A prose-oriented document (release-notes-vX.Y.Z.md) describing the contents and purpose of a release, aimed at users, maintainers, and support staff. Distinguished from the technical CHANGELOG.

**Loopback Service**: The HTTP service component of oauthsvc that runs locally and communicates via localhost (127.0.0.1). Also referred to as the local service or embedded service.

**Package Metadata**: Version numbers, author information, dependencies, and other machine-readable information embedded in setup.py, setup.cfg, and package distribution metadata. Must be kept in sync across files.

**Backport**: A fix or improvement originally developed on the main development branch, then applied to an older release branch (e.g., `release/v1.2`) to create a patch release for users on earlier versions.

---

## Reference Files and Paths

| Path | Purpose |
|------|------|
| `/version.txt` | Contains the current version string (e.g., `1.2.0`) without `v` prefix; read by setup.py and release scripts; must be committed before tagging a release |
| `/CHANGELOG.md` | Master changelog file recording all changes by version and category; updated for each release before tagging |
| `/README.md` | Package overview and basic usage instructions; updated for major releases and significant feature additions |
| `/setup.py` | Python package setup configuration; includes version metadata that must match version.txt |
| `/setup.cfg` | Additional setup configuration; duplicates version information (should be consolidated) |
| `/docs/release-notes/` | Folder containing release notes documents (release-notes-vX.Y.Z.md and other release process pages) |
| `/docs/release-notes/version-numbering.md` | This page; defines versioning scheme and release procedures overview |
| `/docs/release-notes/changelog-conventions.md` | Detailed changelog formatting rules and category definitions (version 2.1, updated 2025-01-20) |
| `/docs/release-notes/release-checklist.md` | Step-by-step checklist for executing a release; must be followed before each release |
| `/docs/release-notes/packaging-guide.rst` | Source distribution packaging procedures (version 1.4; may be outdated) |
| `/docs/release-notes/building-source-distribution.rst` | Updated build instructions and best practices (version v2.0.1; preferred over packaging-guide.rst) |
| `/docs/release-notes/console-log-format-notes.md` | Standards for console log output structure, verbosity, and format (version 1.1, updated 2026-03-22) |
| `/docs/release-notes/command-help-text-style.md` | Style guide for command help text (version v1.3.0, updated 2024-11-05) |
| `/docs/release-notes/speed-notes.md` | Performance improvements and timing changes across versions; includes metrics and measurements (version 2.0, updated 2025-10-18) |
| `/docs/release-notes/changelog-entry-format.yaml` | Machine-readable schema for changelog entries; defines required fields and format (version 1.0) |
| `/scripts/build.sh` | Main build script supporting `sdist` target for creating source distributions |
| `/dist/` | Output directory containing built source distributions (e.g., `oauthsvc-1.2.0.tar.gz`) |

---

## Tools, Packages, and Versions

| Tool/Package | Version | Purpose |
|---|---|---|
| Python | 3.8+ | Runtime environment for oauthsvc (uses only Python standard library, no external dependencies) |
| git | 2.30+ | Version control system; used for tagging releases and managing release branches |
| Bash | 4.0+ | Shell for executing build and release scripts (scripts/build.sh) |
| sqlite3 | 3.8+ | CLI tool for validating and inspecting local database file format |
| tar | GNU tar or BSD tar | Creating and extracting source distribution tarballs |
| grep | GNU grep or BSD grep | Text searching in release verification and validation steps |

---

## Changelog

**v2.0.0** (2025-12-09)  
*Owner: Documentation Guild (Sana Iqbal)*

- **Documentation**: Restructured release-notes/ folder organization with cross-references to related pages; established version-numbering.md as the authoritative source for semantic versioning rules
- **Command Help**: Revised help text for new configuration options introduced in this major release; updated examples to reflect changes in loopback service behavior
- **Speed**: Database initialization significantly faster due to connection pooling improvements (detailed metrics available in speed-notes.md version 2.0)

**v1.2.0** (2025-02-27)  
*Owner: Release Engineering (Priya Chandran)*

- **Documentation**: Added step-by-step examples to README.md for loopback service startup; clarified SQLite database file initialization steps in package docstring
- **Command Help**: Added --verbose flag description (was missing from v1.1.0 help text); corrected example output in --help display
- **Console Log Format**: Switched timestamp format from ISO 8601 to RFC 3339 with millisecond precision; removed redundant "service:" prefix in startup messages
- **Speed**: Optimized SQLite connection pooling; reduced startup latency by approximately 5% on typical systems
- **Packaging**: Updated setup.py to include docs/ folder in distributed source packages

**v1.1.0** (2024-08-15)  
*Owner: Platform Tools (Mara Olsen)*

- **Documentation**: Added inline docstring help for --verbose option (previously omitted); expanded README with usage scenarios
- **Command Help**: Added description of new --config flag; fixed typo in standard --help output text
- **Packaging**: Migrated setup metadata from setup.py into setup.cfg for consistency with Python packaging standards

**v1.1.0-rc1** (2024-08-01)  
*Owner: Release Engineering (Priya Chandran)*

- **Console Log Format**: Trial version of RFC 3339 timestamps (reverted in favor of ISO 8601 in v1.1.0, then restored in v1.2.0)
- **Speed**: Preliminary evaluation and performance analysis of SQLite connection pooling mechanisms

**v1.0.0** (2024-04-02)  
*Owner: Platform Tools (Mara Olsen)*

- Initial stable release of oauthsvc
- **Documentation**: Complete README.md with usage examples and loopback service overview; comprehensive docstrings for all public command-line options
- **Packaging**: First source distribution tarball published; setup.py configured for standard Python package installation
- **Command Help**: Help text for all core command-line flags and options

**v0.9.0** (2024-03-15)  
*Owner: Release Engineering (Priya Chandran)*

- **Console Log Format**: Established standard logging output format and message structure for initial release; defined verbosity levels
- **Speed**: Baseline performance profiling completed; initial timing data recorded in speed-notes.md

---

## Related Pages

- [Release Notes Folder Index](README.md) — overview and navigation for all release documentation (version 3.4, maintained by Platform Tools)
- [Changelog Conventions](changelog-conventions.md) — formatting rules and required categories for CHANGELOG.md entries (version 2.1)
- [Release Checklist](release-checklist.md) — step-by-step procedures for executing each release (version v1.0.3)
- [Source Distribution Packaging Guide](packaging-guide.rst) — packaging procedures and best practices (version 1.4; note: may be outdated)
- [Building the Source Distribution](building-source-distribution.rst) — current build instructions and preferred approach (version v2.0.1)
- [Console Log Format Notes](console-log-format-notes.md) — standards for log output structure and format (version 1.1)
- [Command Help Text Style Guide](command-help-text-style.md) — writing and formatting standards for help text (version v1.3.0)
- [Speed Notes Across Releases](speed-notes.md) — performance improvements and timing data by version (version 2.0)
- [Release Notes: v1.0.0](release-notes-v1.0.0.txt) — initial release documentation
- [Release Notes: v1.1.0](release-notes-v1.1.0.txt) — first minor version release
- [Release Notes: v1.2.0](release-notes-v1.2.0.md) — current stable release
- [Release Notes: v2.0.0](release-notes-v2.0.0.md) — major version release documentation
- [Changelog Entry Format](changelog-entry-format.yaml) — machine-readable schema for changelog entries (version 1.0)

---

*For questions or issues regarding versioning standards, contact Release Engineering (Priya Chandran). For packaging and distribution procedures, refer to Core Services (Liam Fitzgerald). For changelog formatting and documentation conventions, contact the Documentation Guild (Sana Iqbal).*

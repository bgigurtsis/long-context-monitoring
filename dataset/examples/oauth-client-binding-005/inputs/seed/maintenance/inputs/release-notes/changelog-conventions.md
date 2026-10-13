# Changelog Conventions

**Title:** Changelog Conventions  
**Version:** 2.1  
**Owner:** Documentation Guild (Sana Iqbal)  
**Last updated:** 2025-01-20

## Overview

This page describes the conventions used when writing changelog entries for oauthsvc releases. It covers the structure of changelog entries, the relationship to version numbering, how to organize entries for a release, and reference material about what has shipped in past releases.

## Changelog Entry Structure

Each changelog entry should follow a consistent format to keep our release timeline clear and scannable. Entries are organized chronologically within a release section, newest changes first.

### Format and Style

A changelog entry consists of:

- **Category**: One of the following (use bullets or numbers consistently within a release):
  - **Documentation** — updates to the markdown files in `docs/`, parameter documentation, or README files
  - **Packaging** — changes to the setup scripts, distribution metadata, or how the package is built
  - **Command help** — changes to output produced by command-line flags like `--help`
  - **Console output** — changes to log messages, status output, or formatted text written to stdout or stderr
  - **Performance** — speed improvements, reduced memory use, or other efficiency gains
  - **Bug fixes** — fixes to the loopback HTTP service behavior, SQLite database interactions, or command-line parsing
  - **Other** — miscellaneous items that don't fit above

- **Area**: Where the change applies (optional, but recommended). Examples: "service startup", "configuration parsing", "database initialization"

- **Summary**: A brief, past-tense description (50–100 characters, no period)

Examples of well-formed entries:

```
- Documentation: Clarified payload schema in HTTP API reference
- Packaging: Updated setup script to require Python 3.9+
- Command help: Improved descriptions in --help output for loopback flags
- Console output: Changed log timestamp format to ISO 8601
- Performance: Reduced startup latency by deferring SQLite file creation
- Bug fixes: Fixed database file creation when run in read-only directory
```

### Grouping by Category

Within each release section, group entries by category using a second-level heading for each category present:

```markdown
### Bug Fixes
- Fixed issue with service shutdown on Windows
- Resolved incorrect path handling for relative SQLite file locations

### Documentation
- Added quickstart guide to docs/
- Updated all internal references from /tmp to %TEMP%

### Packaging
- Bumped minimum Python version from 3.8 to 3.9
```

This grouping makes it easy for maintainers and users to scan for the type of change they care about.

## Version Numbering Integration

See [Version Numbering Scheme](version-numbering.md) for the semantic versioning scheme used by oauthsvc. Changelog entries map logically to commits or cohesive changes, but releases are tagged only at certain version milestones.

When preparing a release:

1. Identify the new version number using the scheme in version-numbering.md
2. Create or update a new release section in CHANGELOG.md (or CHANGES.txt, depending on which the team is currently maintaining)
3. Move all unreleased entries into the dated release section
4. Add the release date in ISO 8601 format (YYYY-MM-DD)

## Release Notes vs. Changelog

- **Changelog** (maintained in the repository at `CHANGELOG.md` or `CHANGES.txt`): A detailed, technical log of every change per release, grouped by category. Intended for developers and maintainers following development closely.
  
- **Release notes** (stored in `release-notes/release-notes-v*.md` or `.txt`): A curated summary aimed at end users and integrators, highlighting major changes, improvements, and migration guidance. May combine multiple changelog entries or reword them for clarity.

The release notes folder contains:
- `release-notes/README.md` — index of all release note documents  
- `release-notes/release-notes-v1.0.0.txt` — original release (plaintext format)
- `release-notes/release-notes-v1.1.0.txt` — minor update
- `release-notes/release-notes-v1.2.0.md` — first switch to markdown format
- `release-notes/release-notes-v2.0.0.md` — major version release

## Past Release Coverage

### v1.0.0 (2024-04-02)

First stable release. Details in `release-notes-v1.0.0.txt`.

- Initial documentation suite in `docs/`
- Command-line help text for core flags and main entry points
- Console output standardized on newline-delimited format
- Service startup on localhost with configurable port
- SQLite file initialization on first run

### v1.1.0 (2024-08-15)

Incremental improvements. See `release-notes-v1.1.0.txt`.

- Documentation expanded for config file format and schema interpretation
- Help text improved for multi-word flags, making descriptions clearer
- Console log output now includes millisecond precision in timestamps
- Packaging simplified; dropped support for Python versions below 3.8
- Improved error messages when SQLite file is corrupted or unreadable

### v1.2.0 (2025-02-27)

Refinements to startup and documentation. Documented in `release-notes-v1.2.0.md`.

- Docs reorganized under major headings; new operational guide added
- Help text made consistent across all entry points and flags
- Log format updated to use ISO 8601 timestamps throughout
- Build process simplified; setup script made more portable across Windows and POSIX
- Performance improvement: reduced time to open and attach SQLite file on startup

### v2.0.0 (2025-12-09)

Major version with significant internal restructuring. Refer to `release-notes-v2.0.0.md`.

- Documentation completely rewritten for new architecture
- Help text updated for clarity and consistency
- Console output redesigned for both machine and human readability
- Packaging overhauled; now produces wheel distributions in addition to source tarball
- Speed improvements in service startup and steady-state operation; see [Speed Notes Across Releases](speed-notes.md)

## Files and Paths

| File or Path | Purpose |
|---|---|
| `CHANGELOG.md` | Master record of all changes per release; maintained during development |
| `CHANGES.txt` | Alternate name used in early releases before switching to markdown |
| `README.md` | Project overview; includes link to release notes folder |
| `docs/` | User-facing documentation; changes logged under "Documentation" category |
| `docs/config.md` | Configuration file format reference; updates tracked in changelog |
| `docs/http-api.md` | HTTP service API reference; all changes documented |
| `release-notes/README.md` | Index and guide for all release note documents |
| `release-notes/release-notes-v*.md` or `.txt` | Per-release user-facing summary and highlights |
| `release-notes/changelog-conventions.md` | This file; conventions for writing changelog entries |
| `release-notes/version-numbering.md` | Version scheme and semantic versioning rules |
| `release-notes/release-checklist.md` | Procedural checklist for executing a release |
| `release-notes/packaging-guide.rst` | How to prepare and validate the source distribution |
| `release-notes/building-source-distribution.rst` | Detailed build commands and process flow |
| `release-notes/console-log-format-notes.md` | Standards for console and log output formatting |
| `release-notes/command-help-text-style.md` | Writing and formatting conventions for help text |
| `release-notes/speed-notes.md` | Performance tracking and improvements across releases |
| `.git/tags/` | Git tags mark release points (e.g., `v2.0.0`) |
| `scripts/` | Release automation and build helper scripts |

## Tools and Versions

| Tool or Library | Version | Purpose |
|---|---|---|
| Python | 3.9+ (as of v1.1.0) | Runtime environment for service and CLI |
| SQLite | bundled in stdlib | Local state storage and database engine |
| Standard Library modules | N/A | HTTP, argument parsing, file I/O, JSON |
| git | any recent | Repository management and release tagging |
| Markdown or reStructuredText | N/A | Documentation authoring format |

**Note:** The packaging-guide.rst file mentions Python 3.8, but support was dropped in v1.1.0. Current minimum is 3.9; see version-numbering.md for the absolute latest requirements.

## Terminology and Glossary

**Changelog**: The detailed, versioned list of all changes made in each release, grouped by category (documentation, packaging, command help, console output, performance, bug fixes, other). Stored in the repository and maintained throughout development.

**Release**: A tagged, numbered version of oauthsvc made available for installation and use. Identified by a semantic version string (e.g., v2.0.0, v1.2.0).

**Release notes**: A curated, user-focused summary of what changed in a release, written for end users and integrators. Stored as individual files in `release-notes/` and typically less technical and more concise than the changelog.

**Semantic versioning**: A versioning scheme using the format MAJOR.MINOR.PATCH, where MAJOR changes signal breaking changes, MINOR indicates new features or improvements, and PATCH covers bug fixes and minor updates. Defined in version-numbering.md.

**Entry**: A single line or bullet point in a changelog, describing one logical change or fix.

**Category**: The type or domain of a change: documentation, packaging, command help, console output, performance, bug fixes, or other.

**Unreleased**: Changes merged into the main development branch that have not yet been assigned to a release version number.

**Source distribution** (sdist): A compressed package (typically `.tar.gz`) containing the source code, setup files, and packaging metadata, suitable for building and installation.

**Console output**: Text written by the service or command-line tools to stdout or stderr, including log messages, status information, and diagnostic output.

## Worked Example: Preparing a Release

Suppose we are preparing to release v1.3.0. The CHANGELOG.md currently contains:

```markdown
# Changelog

## Unreleased

- Documentation: Rewrote quickstart guide for better clarity
- Packaging: Added Python 3.11 and 3.12 to CI matrix
- Command help: Expanded flag descriptions for edge cases
- Console output: Added timestamps to service connection events
- Performance: Reduced service startup time by 12%

## v1.2.0 (2025-02-27)

- Documentation: ...
```

To release v1.3.0:

1. Refer to [Release Checklist](release-checklist.md) to confirm all prerequisites are met.
2. Update CHANGELOG.md, converting "Unreleased" into a dated v1.3.0 section with categories:

```markdown
# Changelog

## v1.3.0 (2025-09-27)

### Documentation
- Rewrote quickstart guide for better clarity

### Packaging
- Added Python 3.11 and 3.12 to CI matrix

### Command Help
- Expanded flag descriptions for edge cases

### Console Output
- Added timestamps to service connection events

### Performance
- Reduced service startup time by 12%

## v1.2.0 (2025-02-27)
```

3. Create a new file `release-notes/release-notes-v1.3.0.md` with a user-focused summary (fewer entries, more context for readers).
4. Commit the changes and tag the commit with `git tag v1.3.0`.
5. Build the source distribution following the steps in [Building the Source Distribution](building-source-distribution.rst).
6. Upload or publish according to your deployment process.

## Page Change Log

| Date | Version | Release | Author | Change |
|---|---|---|---|---|
| 2025-01-20 | 2.1 | v2.1 | Sana Iqbal | Clarified the distinction between changelog and release notes; expanded worked example |
| 2024-12-15 | 2.0 | v2.0 | Sana Iqbal | Restructured sections for consistency; updated v1.2.0 and v2.0.0 release descriptions |
| 2024-10-01 | 1.2 | v1.2 | Sana Iqbal | Added "Tools and Versions" table; expanded glossary with eight terms |
| 2024-08-20 | 1.1 | v1.1 | Sana Iqbal | Fixed formatting issues; clarified category grouping rules |
| 2024-07-05 | 1.0 | v1.0 | Documentation Guild | Initial publication and adoption |
| 2024-06-15 | 0.9 | (unreleased) | Theo Banks | Proposed structure and format for changelog conventions |

## Related Pages

- [Release Notes Folder Index](README.md) — overview and navigation guide to all release documentation
- [Version Numbering Scheme](version-numbering.md) — semantic versioning rules for oauthsvc
- [Release Checklist](release-checklist.md) — step-by-step instructions for executing a release
- [Source Distribution Packaging Guide](packaging-guide.rst) — preparation and validation of source distributions
- [Building the Source Distribution](building-source-distribution.rst) — detailed build commands and procedures
- [Console Log Format Notes](console-log-format-notes.md) — standards for log and console output formatting
- [Command Help Text Style Guide](command-help-text-style.md) — writing and formatting conventions for help text and descriptions
- [Speed Notes Across Releases](speed-notes.md) — performance improvements and optimization timeline

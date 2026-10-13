# Version Numbering for the Package

**Version:** 1.3  
**Owner:** Release Engineering (Priya Chandran)  
**Last Updated:** 2024-05-02

## Overview

The auditlog package uses semantic versioning across both its command-line interface and loopback HTTP service. This document describes how version numbers are assigned, maintained, and communicated through the package's releases and documentation. Version numbers indicate the breadth and impact of changes, helping users decide whether to upgrade and understand what to expect when they do.

All version numbers follow the same scheme regardless of whether the feature or fix applies to the command line, the service, or supporting infrastructure like the documentation or build tooling. This unified approach ensures clarity when announcing releases and helps downstream users understand compatibility.

Version numbers are permanent once released. A released version—whether 1.0.0, 1.2.1, or 2.0.0—is immutable. Any changes require a new version number. This principle ensures that users and downstream tools can refer reliably to a specific release.

## Version Numbering Scheme

*Section Owner: Release Engineering (Priya Chandran)*

This service uses semantic versioning: `MAJOR.MINOR.PATCH`.

- **MAJOR:** Incremented for breaking changes to the command-line syntax, HTTP API contract, or database format. Users upgrading to a MAJOR version bump may need to adjust scripts, configurations, or stored data.
- **MINOR:** Incremented for backward-compatible additions: new command flags, new HTTP capabilities, changes to console logging output that add information without breaking parsers, or speed improvements that affect user experience. Existing code continues to work without modification.
- **PATCH:** Incremented for bug fixes, documentation updates, command help text clarifications, improvements to packaging, and improvements to build reproducibility. These releases are safe for production use.

### Detailed criteria for version increments

**MAJOR version bump should occur when:**

- The schema of the database file changes incompatibly (e.g., removing a column or changing data types in a way that breaks existing usage).
- A required command-line flag is removed or changes meaning in a way that breaks existing invocations.
- The loopback service changes a URL path, removes a service interface, or changes response structure in an incompatible way.
- The format of configuration input changes and existing configurations no longer work.

**MINOR version bump should occur when:**

- New optional command flags are added that provide new functionality.
- The service gains new capabilities accessible through new service interfaces or expanded parameters.
- Console output format gains new optional fields or structured data (as long as scripts that parse the old format continue to work).
- Speed improvements reduce latency or resource usage by a measurable margin (should be documented in [Speed Notes Across Releases](speed-notes.md)).
- New documentation pages are added to the release notes or docs folder.
- The build process is improved in ways that affect the distributed package (for example, reduced file size or better platform compatibility).

**PATCH version bump should occur when:**

- Bug fixes correct behavior that diverges from documentation without changing the documented interface.
- Improvements to command help text or console logging clarify existing behavior without changing what the command does.
- Updates to build configuration, packaging metadata, or supporting documentation improve the release process.
- Fixes to installation or setup processes correct errors in the build system.
- Performance improvements are minor and do not warrant a MINOR bump.

The package maintains parallel versioning for documentation pages, configuration files, and release artifacts—all increment according to the same scheme. When a release includes changes to multiple components (for example, both command help text and console output format), the entire package gets a single new version number reflecting the highest type of change.

## Pre-release and Development Versions

Development builds may append a suffix like `-dev` or `-alpha.N` to the version string. These versions are created during development and used internally but are not released to users and are not documented in the changelog. Release candidates preparing for a production release may use `-rc.N` (for example, `1.3.0-rc.1`). Only releases without a suffix (such as `1.3.0`) are considered production releases and are announced publicly.

Development versions have no stability guarantee. Do not document them in the changelog or include them in release notes. When a MAJOR, MINOR, or PATCH increment is ready, drop the development suffix and release the clean version number.

## Version Numbering Across the Release Pipeline

*Section Owner: Release Engineering (Priya Chandran)*

### Authoritative version location

The version number is stored in a single authoritative location: the text file `auditlog/__version__.txt`, containing only the version string in the format `MAJOR.MINOR.PATCH` (for example, `1.3.0` without a `v` prefix).

At release time, the build script `scripts/build-release.sh` reads this file and propagates the version into:
- Package metadata in the distribution package (setup configuration, manifest files).
- The `--version` flag output of the command line.
- Version strings in the loopback service's HTTP response headers.
- Release notes file naming: `release-notes-v1.3.0.md`.
- Git release tags: `v1.3.0`.

Do not manually edit the version string in multiple places. The build process will fail with a validation error if versions are inconsistent across artifacts.

### Release artifacts produced

Each released version produces:
- A source distribution package: `auditlog-1.3.0.tar.gz` containing the full source tree, build scripts, and documentation.
- A release notes document: `docs/release-notes/release-notes-v1.3.0.md` describing what changed.
- A git tag: `v1.3.0` (with the `v` prefix) marking the exact commit of the release.

The git tag allows anyone to check out the precise source code that corresponds to a released version using `git checkout v1.3.0`.

### Version visibility to users

Users observe the version in several places:

- Running the command with `--version` returns the version built into that binary.
- The loopback service includes its version in HTTP response headers.
- The source package filename includes the version: `auditlog-1.3.0.tar.gz`.
- Release announcements reference the version.

Both the command line and the service reflect the version string at build time. Development or interim builds created before a release may show as `dev` or `unknown`.

## Documentation and Support for Version Changes

*Section Owner: Developer Experience (Theo Banks)*

When a new version introduces changes visible to users—new command flags, altered console output, service behavior changes, packaging improvements, or notable speed changes—update the corresponding documentation pages:

- **Command help text changes:** Document all differences in `[Command Help Text Changes Across Releases](command-help-text-changes.md)`. Include examples of the old syntax (if removed) and new syntax (if added).
- **Console log format changes:** Document output format changes in `[Console Log Format Changes Across Releases](console-log-format-changes.md)`. Include sample output.
- **Speed improvements or regressions:** Note measured performance changes in `[Speed Notes Across Releases](speed-notes.md)`. Include before/after measurements if available.
- **General release notes:** Create a release notes file for that version following [Changelog Writing Conventions](changelog-conventions.md). Include a brief summary of the release focus.
- **Packaging and build changes:** Note any packaging improvements or build process changes in the release notes.

These pages are maintained alongside the main release documentation to help users who upgrade between versions understand what changed and whether they need to adjust their usage.

## Terminology

- **Semantic versioning:** A versioning scheme with three numeric components (MAJOR.MINOR.PATCH) where each increment signals the type and extent of change introduced in that release.
- **Breaking change:** A modification to the documented interface (command flags, HTTP API, database format, configuration input) that invalidates existing usage without a migration path, requiring a MAJOR version bump.
- **Backward compatible:** A change that does not require users to modify their commands, scripts, stored data, or expectations; safe for users to adopt in a MINOR or PATCH release.
- **Production release:** A released version without a development suffix (such as `1.3.0`), released to users and documented in the changelog and release notes.
- **Development version:** A build created during development, marked with a suffix like `-dev` or `-alpha.N`, used internally and not released publicly.
- **Source distribution:** The packaged source code released to users, containing the full source tree, build scripts, documentation, and metadata, typically shipped as a compressed tar package.
- **Build metadata:** Artifact information embedded in the package during compilation, including version number, build timestamp, and configuration details.
- **Release tag:** A git tag marking the exact commit of a released version, formatted as `v1.3.0` (with `v` prefix), allowing reproducible checkout of release source code.
- **Patch release:** An increment to the PATCH component (for example, from 1.3.0 to 1.3.1) that includes bug fixes or documentation improvements without adding features.

## Repository Files and Paths

| Path | Purpose |
|------|------|
| `auditlog/__version__.txt` | Single source of truth for the package version. Consulted by build scripts and release tools. |
| `docs/release-notes/` | Directory containing all release notes, version documentation, and release process guides. |
| `docs/release-notes/version-numbering.md` | This document. Defines the versioning scheme and release strategy. |
| `docs/release-notes/changelog-conventions.md` | Standards for writing changelog entries and release notes content. |
| `docs/release-notes/release-checklist.md` | Step-by-step checklist for executing releases. |
| `docs/release-notes/release-checklist-template.yaml` | YAML template for tracking release progress. |
| `docs/release-notes/release-notes-v1.2.md` | Release notes for version 1.2.0 with changes and migration notes. |
| `docs/release-notes/packaging-source-distribution.rst` | Procedures for building, validating, and packaging source distributions. |
| `docs/release-notes/command-help-text-changes.md` | Record of command help text changes across releases. |
| `docs/release-notes/console-log-format-changes.md` | Record of console output format changes across releases. |
| `docs/release-notes/speed-notes.md` | Performance metrics and latency notes by release version. |
| `scripts/build-release.sh` | Shell script that reads version from `auditlog/__version__.txt`, builds the distribution package, and creates release metadata. |
| `README.md` | Project overview; version number appears in the documentation section. |

## Tools and Versions

| Tool/Library | Version | Purpose |
|---|---|---|
| Python | 3.9+ | Required to run the package and execute build and release scripts. |
| sqlite3 | 3.8+ | Database engine for local record storage. |
| git | 2.30+ | Version control, release tagging, and commit logs. |
| tar | (GNU or BSD) | Source distribution package creation and extraction. |
| gzip | 1.10+ | Compression for distribution packages. |
| shell (bash/sh) | POSIX-compatible | Execution of build and release scripts. |

## Past Releases and Version Changes

*Section Owner: Core Runtime (Sam Okafor)*

The following table summarizes past releases and the types of changes they introduced. For detailed release notes, see the individual release notes files in the `docs/release-notes/` directory. For guidelines on documenting changes, see [Changelog Writing Conventions](changelog-conventions.md).

### Version 1.0.0 — Initial Release
**Released:** 2024-04-01

The first stable release of auditlog. Includes the command-line interface and loopback HTTP service. Detailed release notes at `docs/release-notes/release-notes-v1.0.md`.

**Shipped components:**
- Command-line interface with core functionality.
- Loopback HTTP service for programmatic access.
- SQLite database file for local record storage.
- Initial console logging format.

**Version in source:** `auditlog/__version__.txt` contains `1.0.0`.

### Version 1.1.0 — Enhanced Documentation and Output
**Released:** 2024-09-05

A MINOR release focused on improving user experience through better documentation and clearer output. Major focus on help text and logging format improvements.

**Changes:**
- Improved command help text with clearer examples. Detailed changes in [Command Help Text Changes Across Releases](command-help-text-changes.md).
- Refined console log format for easier parsing and more structured output. Detailed changes in [Console Log Format Changes Across Releases](console-log-format-changes.md).
- New documentation pages added to the `docs/release-notes/` folder.
- Packaging metadata improved for better distribution compatibility.
- Build scripts enhanced for more reliable builds.
- Complete release notes at `docs/release-notes/release-notes-v1.1.md`.

**Version in source:** `auditlog/__version__.txt` contains `1.1.0`.

### Version 1.1.1 — Documentation Updates
**Released:** 2024-10-12

A PATCH release fixing inconsistencies in help text and improving packaging reliability.

**Changes:**
- Corrected command help text examples and clarified usage patterns.
- Fixed packaging script to handle edge cases in filename processing.
- Documentation improvements for clarity and completeness.

**Version in source:** `auditlog/__version__.txt` contains `1.1.1`.

### Version 1.2.0 — Performance and Format Improvements
**Released:** 2025-02-20

A MINOR release with significant speed improvements and refined logging output. Performance was a primary focus.

**Changes:**
- Significant latency improvements to the loopback service. Detailed measurements in [Speed Notes Across Releases](speed-notes.md).
- Enhanced console output format to include timing information without breaking existing parsers.
- Improved build environment documentation in [Build Environment Notes](build-environment-notes.rst).
- Source distribution packaging improvements documented in [Packaging the Source Distribution](packaging-source-distribution.rst).
- New sections added to release notes and changelog documentation.
- Complete release notes at `docs/release-notes/release-notes-v1.2.md`.

**Version in source:** `auditlog/__version__.txt` contains `1.2.0`.

### Version 1.2.1 — Build and Documentation Maintenance
**Released:** 2025-05-15

A PATCH release for build improvements and documentation updates.

**Changes:**
- Fixed issues in the source distribution build process.
- Updated help text for consistency with latest standards.
- Improved documentation for clarity of the release process.

**Version in source:** `auditlog/__version__.txt` contains `1.2.1`.

### Version 1.3.0 — Development in Progress
**Released:** (Not yet released as of this document update)

Note: This page was last updated 2024-05-02, early in the 1.3.0 development cycle. Planned work includes packaging improvements and console log format refinements, but the release has not yet occurred.

## Release Process Workflow

*Section Owner: Release Engineering (Priya Chandran)*

The release of a new version follows these steps:

1. **Update version:** Edit `auditlog/__version__.txt` with the new version number (MAJOR.MINOR.PATCH format, no `v` prefix).
2. **Create release notes:** Create `docs/release-notes/release-notes-vX.Y.Z.md` documenting changes made in this release.
3. **Update documentation:** Update relevant documentation pages:
   - [Command Help Text Changes Across Releases](command-help-text-changes.md) if command syntax changed.
   - [Console Log Format Changes Across Releases](console-log-format-changes.md) if output format changed.
   - [Speed Notes Across Releases](speed-notes.md) if performance was affected.
4. **Review with checklist:** Use [Release Checklist](release-checklist.md) to verify all steps and quality gates are met.
5. **Build release:** Run `scripts/build-release.sh` to build the source distribution and verify the package contains the correct version.
6. **Validate distribution:** Extract and verify the generated package can be used without errors.
7. **Tag release:** Create a git tag using `git tag v1.3.0` (with `v` prefix).
8. **Push to repository:** Push the tagged commit to the repository.

For detailed procedures on building and packaging the source distribution, see [Packaging the Source Distribution](packaging-source-distribution.rst). For standards on changelog content and format, see [Changelog Writing Conventions](changelog-conventions.md).

## Related Pages

- [Release Notes Folder Overview](README.md) — Overview of the release documentation structure and navigation guide.
- [Changelog Writing Conventions](changelog-conventions.md) — Standards for documenting changes in release notes and the changelog.
- [Release Checklist](release-checklist.md) — Step-by-step checklist for executing a production release.
- [Release Checklist Template (YAML)](release-checklist-template.yaml) — YAML template for tracking release progress through each phase.
- [Packaging the Source Distribution](packaging-source-distribution.rst) — Detailed procedures for building, validating, and packaging releases.
- [Build Environment Notes](build-environment-notes.rst) — Information on build dependencies, environment setup, and toolchain configuration.
- [Command Help Text Changes Across Releases](command-help-text-changes.md) — Record of command-line help text changes.
- [Console Log Format Changes Across Releases](console-log-format-changes.md) — Record of console output format changes.
- [Speed Notes Across Releases](speed-notes.md) — Performance and latency information by release version.

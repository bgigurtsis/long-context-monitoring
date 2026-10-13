# Version Numbering Scheme

**Title:** Version Numbering Scheme  
**Version:** 2.3  
**Owner:** Platform Tools (Mara Olsen)  
**Last updated:** 2025-01-09

**Summary:** Explains how version numbers are assigned to the package across major, minor, and patch releases, along with the procedures and workflows for changelog management, release checklists, and documentation of past releases.

---

## Overview

The accountsvc package uses semantic versioning with a three-part version number: `MAJOR.MINOR.PATCH`.

* **Major releases** indicate significant feature additions or breaking API changes to the command line or loopback HTTP service.
* **Minor releases** add new functionality or change existing behavior in backward-compatible ways.
* **Patch releases** fix bugs, improve performance, update help text, or refine console output formatting without changing the service's functional behavior.

All release numbers are recorded in the `setup.cfg` file at the repository root, in the `[metadata]` section under `version =`. Tags in the version control system follow the pattern `v{MAJOR}.{MINOR}.{PATCH}` (for example, `v2.2.0` or `v1.0.1`).

Release announcements and migration guides live in the `release-notes/` directory at the repository root as individual Markdown files. Naming conventions have evolved over time; you may encounter both `release-notes-v{MAJOR}.{MINOR}.{PATCH}.md` and `release-notes-{MAJOR}.{MINOR}.md` depending on when each page was published.

---

## Semantic Versioning Rules (Section Owner: Platform Tools)

### Major Version Increments

Increment `MAJOR` when:

- The command-line interface adds, removes, or substantially alters argument names or behavior
- The loopback HTTP service changes request or response formats in ways that break existing functionality
- The database file format or initialization changes in an incompatible way
- A widely used feature is deprecated or removed

Examples of changes that warrant major version bumps:

1. Renaming a flag from `--account-id` to `--id`
2. Changing the HTTP service from port 9000 to a configurable port with different defaults
3. Altering the database schema structure such that existing deployments cannot upgrade safely

### Minor Version Increments

Increment `MINOR` when:

- New command-line flags or options are added
- The HTTP service gains new request paths or response fields (as long as existing requests still work unchanged)
- Help text is substantially rewritten, expanded, or reorganized
- Console log output adds new fields or columns while preserving existing ones
- Performance improvements are made that do not alter external behavior

Do not increment `MINOR` for documentation-only changes unless the documentation is bundled in the package distribution itself (such as a `CHANGELOG.md` file in the root).

### Patch Version Increments

Increment `PATCH` when:

- Bug fixes are made to the core service or CLI
- Help text is corrected or slightly improved
- Console log format is adjusted (e.g., timestamp precision, field spacing)
- Performance regressions are fixed
- Dependencies or packaging metadata are updated

---

## Release Workflow

### Planning and Preparation

Before beginning work on a release, consult the `release-schedule.yaml` file in the `release-notes/` directory to confirm the next scheduled release date and target version number. This file is maintained by Core Services (Elliot Fenwick).

Create a new branch with the naming pattern `release/{VERSION}`, for example `release/2.3.0`. This branch diverges from `main` at the point where development for that release stabilizes.

### Updating Version Numbers

1. Open `setup.cfg` in a text editor.
2. Locate the `version =` line under `[metadata]`.
3. Change the version to the target release number. For example, if releasing v2.3.0, the line should read:
   ```
   version = 2.3.0
   ```
4. Save and commit this change with a message like `Bump version to 2.3.0`.

### Changelog Management

The changelog is maintained as a single file in either `docs/CHANGELOG.md` or `CHANGELOG.txt` depending on the active toolchain. Entries must follow the format specified in the `changelog-conventions.md` page (v1.3.1, Docs Guild, Sasha Perlman).

Before each release:

1. Review all uncommitted or recently merged changes that affect user-visible behavior
2. Add new entries to the top of the changelog file, grouped under a section headed with the version number and release date (for example, `## [2.3.0] - 2025-01-09`)
3. Use the entry format documented in `changelog-format.rst` (v1.4.0, Release Engineering, last updated 2026-01-30)
4. Commit the changelog with the message `Document changes for version X.Y.Z`

### Pre-Release Verification

Run through the checklist documented in `release-checklist.md` (version 2.4, Release Engineering, Devon Ruiz, last updated 2026-02-03). The checklist covers:

- Verification that all documentation pages are current
- Confirmation that help text output matches documentation
- Manual build of the source distribution
- Verification that the package installs correctly from the distribution

---

## Release Notes Documentation

Past releases of the package are documented in the `release-notes/` folder. Documentation-focused releases emphasize changes to:

- Command help text and error messages  
- Console log output format and verbosity
- Performance improvements in startup time or database query speed
- Packaging and distribution changes

### Structure of Release Notes

Each release notes file follows this pattern:

- **Release heading** with version and date
- **Summary** of major changes (one or two sentences)
- **New Features** or **Improvements** sections where applicable
- **Changes to Documentation** or **Command Help Updates**
- **Logging Changes** and **Console Output** modifications
- **Performance Notes**
- **Packaging or Distribution Changes**
- **Migration Guide** (included if breaking changes exist)

### Past Release Summary

| Version | Date | Focus | Owner |
|---------|------|-------|-------|
| v1.0.0 | 2024-03-18 | Initial release | Developer Experience (Priya Nandakumar) |
| v1.1.0 | 2024-07-05 | Command help text improvements | Developer Experience (Priya Nandakumar) |
| v1.2.0 | 2024-10-22 | Documentation and logging updates | Platform Tools (Mara Olsen) |
| 2.0 | 2025-02-11 | Major version with service changes | Platform Tools (Mara Olsen) |
| 2.1 | 2025-05-27 | Performance improvements, help text refactor | Docs Guild (Sasha Perlman) |
| 2.2 | 2025-09-15 | Bugfixes, logging format improvements | Docs Guild (Sasha Perlman) |

The complete release notes for each version appear in separate files in the `release-notes/` directory.

---

## Source Distribution Packaging

When packaging the source distribution for release, follow the procedures in `packaging-source-distribution.rst` (v1.2.0, Core Services, Elliot Fenwick, last updated 2024-06-14).

### Required Distribution Components

The source distribution must contain:

- The `accountsvc/` package directory at the repository root
- The `README.md` file from the repository root  
- A `setup.cfg` file with correct version metadata
- The `docs/` folder with all documentation and changelog files
- The `scripts/` folder with release and setup automation

### Distribution Naming and Checksums

Distribution files are named using:

```
accountsvc-{VERSION}.tar.gz
```

For example, the v2.2.0 release would be distributed as `accountsvc-2.2.0.tar.gz`.

A corresponding checksum file is generated:

```
accountsvc-{VERSION}.tar.gz.sha256
```

### Validation After Packaging

After creating the distribution package:

1. Extract it into a temporary directory: `tar -xzf accountsvc-{VERSION}.tar.gz`
2. Verify that all expected files are present
3. Spot-check file content for consistency
4. If the distribution includes documentation, confirm the changelog version matches the metadata

Additional guidance on source distributions is provided in `source-distribution-notes.txt` (version 2.1, Core Services, Elliot Fenwick, last updated 2025-08-30).

---

## Version Increment Reference Table

| Trigger | Major | Minor | Patch |
|---------|-------|-------|-------|
| New command-line flags | — | ✓ | — |
| Bug fix | — | — | ✓ |
| Incompatible CLI change | ✓ | — | — |
| Help text modification | — | — | ✓ |
| Console log format adjustment | — | — | ✓ |
| Performance optimization | — | ✓ | — |
| Documentation update (bundled) | — | — | ✓ |
| HTTP response field addition (compatible) | — | ✓ | — |
| HTTP request format change (incompatible) | ✓ | — | — |
| Packaging metadata update | — | — | ✓ |

---

## Tools and Dependencies

The following tools and versions are used throughout the version numbering and release workflow:

| Tool | Version | Purpose |
|------|---------|---------|
| git | 2.40+ | Version control, tagging, branch management |
| setuptools | 65.5+ | Package metadata and distribution building |
| tar (GNU) | 1.34+ | Creating and extracting source distributions |
| sha256sum | (coreutils) | Generating distribution checksums |
| Python | 3.10+ | Running automation scripts and build operations |

The accountsvc package itself uses only the Python standard library and has no external runtime dependencies.

---

## Terminology

**Source Package**: A compressed `.tar.gz` file containing the complete package source code and documentation, ready for distribution to users.

**Backward-compatible**: A change that does not break existing code using the package's command-line or HTTP interface; old code continues to work with new versions.

**Breaking change**: A modification to the command-line or HTTP service interface that requires code to be updated to continue working correctly.

**Changelog**: A file (typically `CHANGELOG.md`) that lists all changes made to the package, organized by release version and date, describing features, fixes, and improvements.

**Distribution**: The packaged form of the source code suitable for installation and deployment, typically provided as a compressed package.

**Metadata**: Information about the package stored in `setup.cfg`, including version number, author, package name, and description; read by installation tools.

**Release**: A specific, tagged version of the package made available for use; corresponds to a version number and may include accompanying release notes and a changelog entry.

**Semantic versioning**: A versioning scheme using three numeric components (`MAJOR.MINOR.PATCH`) to communicate the nature and breadth of changes between releases.

**Source distribution**: A packaged file containing the complete package source code and all supporting documentation files, without compiled or platform-specific binaries.

---

## Repository Files and Paths

The following files and directories are referenced throughout release and version management:

| Path | Function |
|------|------|
| `setup.cfg` | Package metadata file at repository root; contains the `version =` field that must be updated for each release |
| `docs/CHANGELOG.md` | Changelog file documenting all changes across releases; may also be located at `CHANGELOG.txt` or `CHANGELOG.md` at repository root |
| `release-notes/` | Directory at repository root containing individual release notes files for all versions |
| `release-notes/release-schedule.yaml` | Planned release dates and target version numbers |
| `release-schedule.yaml` | Alternative location for release scheduling data (location varies by version) |
| `README.md` | Repository root file providing package overview and getting-started guidance |
| `scripts/` | Directory containing automation scripts for packaging, distribution, and release tasks |

---

## Change Log

### [2.3] - 2025-01-09
- Clarified rules for incrementing MINOR version when performance improvements are made
- Added comprehensive reference table for version increment triggers
- Updated all external references to recent documentation versions
- Expanded "Repository Files and Paths" section with additional location notes

### [2.2.1] - 2024-12-15
- Corrected table of past releases with accurate dates
- Added reference to changelog-format.rst for detailed entry formatting
- Fixed spelling of Core Services contact (Elliot Fenwick)
- Improved clarity in "Patch Version Increments" section

### [2.2] - 2024-11-20
- Rewrote "Semantic Versioning Rules" section for clarity and specificity
- Added worked examples of major version increment scenarios
- Introduced new reference table comparing version increment triggers
- Updated tools and dependencies table to reflect setuptools 65.5+ requirement

### [2.1] - 2024-10-01
- Added comprehensive section on source distribution packaging
- Documented package naming convention (`accountsvc-{VERSION}.tar.gz`)
- Integrated release checklist workflow into release planning section
- Updated references to changelog-conventions.md and sibling documentation pages

### [2.0] - 2024-08-20
- Complete restructuring of versioning guidelines documentation
- Introduced three-part semantic version format (MAJOR.MINOR.PATCH)
- Consolidated release workflow into single unified procedure
- Updated all external file references to match current documentation structure

### [1.2] - 2024-06-14
- Fixed path reference to release checklist (moved to `release-checklist.md`)
- Updated owner and contact information for Release Engineering
- Added Git tagging conventions section
- Clarified distinction between patch and minor release criteria for documentation

---

## Related Pages

- **README.md** (v1.4.0) — Release Notes Folder Guide; overview and index of all release documentation
- **changelog-conventions.md** (v1.3.1) — Changelog Conventions; rules and guidelines for writing changelog entries
- **release-checklist.md** (2.4) — Release Checklist; step-by-step verification procedures before publication
- **packaging-source-distribution.rst** (v1.2.0) — Packaging the Source Distribution; technical procedures for creating packages
- **source-distribution-notes.txt** (2.1) — Source Distribution Notes; additional guidance and troubleshooting
- **changelog-format.rst** (v1.4.0) — Changelog Entry Format; detailed entry structure, examples, and style guidance
- **release-schedule.yaml** (2.5) — Release Schedule; upcoming release dates and target versions
- **release-notes-v1.0.0.md** — Release Notes for v1.0.0
- **release-notes-v1.1.0.md** — Release Notes for v1.1.0
- **release-notes-v1.2.0.md** — Release Notes for v1.2.0
- **release-notes-2.0.md** — Release Notes for 2.0
- **release-notes-2.1.md** — Release Notes for 2.1
- **release-notes-2.2.md** — Release Notes for 2.2

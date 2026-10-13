# Release Checklist

**Title:** Release Checklist  
**Version:** v1.0.3  
**Owner:** Release Engineering (Priya Chandran)  
**Last updated:** 2026-02-14

---

## Overview

This page documents the complete release workflow for the service package, including version numbering considerations, changelog management, pre-release verification steps, source distribution packaging, and guidelines for authoring release notes. Follow this process before publishing each new release to PyPI or the internal package repository.

The process assumes you have write access to the package repository and PyPI configured in your local environment.

---

## Version Numbering Strategy

oauthsvc uses semantic versioning: MAJOR.MINOR.PATCH. The component to increment depends on the nature of the changes included in the release.

- **MAJOR:** Incompatible changes to the command-line interface, configuration file format, or database schema migrations. Use sparingly; only Priya or a senior maintainer makes this call.
- **MINOR:** New features, enhancements to existing command-line options, changes to console log format that improve readability without breaking parsers.
- **PATCH:** Bug fixes, documentation-only updates, packaging improvements, adjustments to command help text clarity, or performance optimizations that do not alter behavior.

Refer to the [Version Numbering Scheme](version-numbering.md) page (v1.2.0) for detailed rules and examples. That page contains the authoritative reference; this section summarizes for the release workflow.

The version string appears in:
- The package metadata (in the root `setup.cfg` or equivalent)
- Git tags, formatted as `v<MAJOR>.<MINOR>.<PATCH>` (for example, `v1.2.0`)
- The changelog entry dated with the release date
- Release notes file, prefixed with `release-notes-v<VERSION>.md`

---

## Changelog Management

Before each release, ensure the changelog is current and follows our conventions. The [Changelog Conventions](changelog-conventions.md) page (version 2.1, owner Documentation Guild—Sana Iqbal) defines the required format, categories, and tone.

### Changelog Workflow

1. **During development:** As features, fixes, and documentation improvements land on the main branch, contributors add entries to the unreleased section of the changelog file (`CHANGELOG.md` in the repository root).

2. **One week before release:** Review all unreleased entries. Ensure each entry:
   - States what changed in plain language
   - Falls into one of the defined categories (Features, Bug Fixes, Documentation, Performance, Packaging)
   - Does not mention internal function or module names
   - Uses the consistent past-tense format (e.g., "Fixed an issue where…" rather than "Fix…")

3. **During release preparation:** Create a new section dated with today's date, titled with the version number (e.g., "## [1.2.0] – 2025-06-15"), and move all unreleased entries under it.

4. **After publishing:** Leave the changelog with the new dated section locked in place. The next development cycle begins with a fresh "## Unreleased" heading.

Minor inconsistency note: Some releases use "Unreleased" in all caps; earlier ones used title case "Unreleased." Standardize on title case going forward.

---

## Pre-Release Checklist

Follow this step-by-step checklist before tagging and packaging a release.

### Week Before: Review and Verify

- [ ] **Assemble the changelog.** Copy all unreleased entries into a dated section with the new version number and today's date.
- [ ] **Verify version number in package metadata.** Confirm that `setup.cfg` (or wherever the canonical version lives) matches the version you intend to release. Example:

  ```
  version = 1.2.0
  ```

- [ ] **Review the release coverage.** Confirm with the team (especially if major or minor bump) that the planned version number matches the extent of changes. Consult Priya if unsure.
- [ ] **Check for undocumented changes.** Run `git log --oneline <previous-tag>..HEAD` to see all commits since the last release. Verify that each significant change appears in the changelog.

### Three Days Before: Documentation Review

- [ ] **Check command help text.** Run `oauthsvc --help` and `oauthsvc <subcommand> --help` for each subcommand. Verify that help output is clear, consistent, and current. Refer to the [Command Help Text Style Guide](command-help-text-style.md) (v1.3.0, Sana Iqbal, 2024-11-05) for tone and formatting.
- [ ] **Review the README.** Confirm that the package overview, installation instructions, and quick-start examples in the root README still reflect the current release.
- [ ] **Check console log format notes.** If the release includes changes to logging output, verify that those changes align with the standards in [Console Log Format Notes](console-log-format-notes.md) (v1.1, Theo Banks, 2026-03-22). Document any new log messages or level changes in the release notes.
- [ ] **Performance notes.** If the release includes performance improvements, ensure the details are captured in [Speed Notes Across Releases](speed-notes.md) (v2.0, Theo Banks, 2025-10-18).

### Day of Release: Final Checks

- [ ] **Build the source distribution locally.** Follow the steps in [Building the Source Distribution](building-source-distribution.rst) (v2.0.1, Liam Fitzgerald, 2025-07-01). Verify the distribution file is generated without errors and contains all expected files (package directory, README, license, changelog, setup metadata).

  Example workflow:
  ```
  cd C:\path\to\oauthsvc-repo
  python -m build --sdist
  ```

  Inspect the generated `.tar.gz` file to confirm it unpacks correctly and contains the package directory, `CHANGELOG.md`, `setup.cfg`, and `README.md`.

- [ ] **Verify the database schema is bundled correctly.** The SQLite schema initialization script (or database template) must be included in the source distribution. Unpack the distribution in a temporary directory and confirm the schema file is present.

- [ ] **Run the command-line interface locally.** Verify basic functionality:
  - `oauthsvc --version` (should report the new version number)
  - `oauthsvc --help` (should display complete and current help text)
  - Start the service in loopback mode and verify that console log output matches the expected format

- [ ] **Confirm all documentation URLs resolve.** If any release notes or README sections link to internal wiki pages, verify those links work.

---

## Packaging and Distribution

The source distribution is built, verified, and published following the steps outlined in [Source Distribution Packaging Guide](packaging-guide.rst) (v1.4, Liam Fitzgerald, 2024-09-10). This section summarizes the release-time workflow.

### Building the Source Distribution

1. Ensure validation passes and the code is committed to the main branch.
2. Update the version in package metadata (as verified in the pre-release checklist).
3. Run the build command:

   ```
   python -m build --sdist
   ```

   This creates a compressed bundle (`.tar.gz`) in the `dist/` directory.

4. Verify the bundle contents:

   ```
   cd C:\Users\Billy\AppData\Local\Temp\doc-pool-call-h1bgtldb
   tar -tzf dist/oauthsvc-1.2.0.tar.gz | head -20
   ```

   Check that the listing shows the package directory, `CHANGELOG.md`, `setup.cfg`, `README.md`, and any other expected files.

5. Verify installation in a clean virtual environment:

   ```
Create a virtual environment.
Activate the virtual environment.
   pip install dist/oauthsvc-1.2.0.tar.gz
   oauthsvc --version
   ```

   The version output should match the new version number (e.g., "1.2.0").

### Publishing to the Repository

- If publishing to PyPI: Use `twine upload dist/oauthsvc-1.2.0.tar.gz` (requires PyPI configuration).
- If publishing to an internal repository: Follow your organization's package upload process.

After successful upload, create a Git tag and push it to the repository:

```
git tag v1.2.0
git push origin v1.2.0
```

---

## Release Notes Authorship

Release notes are published alongside each version as a separate file in the `release-notes/` folder using the naming convention `release-notes-v<VERSION>.md` or `.txt` (older releases use `.txt`; newer ones use `.md`).

### What to Include in Release Notes

Release notes for oauthsvc should cover:

1. **Summary of changes** – A brief overview of the release focus (e.g., "This release adds new command-line options for database queries and improves console log formatting for better readability").

2. **Documentation improvements** – Any updates to the README, help text, or internal wiki pages. Examples:
   - "Updated command help text for the database query subcommand to clarify the output format."
   - "Revised README installation section with clearer virtual environment instructions."

3. **Packaging changes** – Modifications to the source distribution, dependencies, or build process. Examples:
   - "Source distribution now includes a database schema template file for initial setup."
   - "Removed unnecessary vendored utility modules from the distribution (oauthsvc is now pure standard library)."

4. **Console log format updates** – Changes to log message structure, level assignments, or timestamps. Examples:
   - "Service startup logs now include the loopback host and port in a single line."
   - "Changed database operation logs from INFO to DEBUG level to reduce noise."

5. **Performance improvements** – Documented speed gains or optimization details. Examples:
   - "Service startup time reduced by 150ms through lazy-loading of internal modules."
   - "Reduced memory footprint for large command-line result sets by 20%."

### What to Exclude from Release Notes

Do not include:
- Internal module or function names
- Specific code changes or commit hashes (use changelog for that)
- Critical functionality updates or system behavior changes
- Validation suite modifications
- Details of how the package talks to external services

### Release Notes Format

Use Markdown (`.md`) for releases v1.2.0 and later. Earlier releases use plain text (`.txt`). Do not convert old `.txt` files to `.md`; they remain as published.

A sample structure:

```
# Release Notes: v1.2.0

**Released:** 2025-06-15

## Summary
This minor release improves the command-line help text and optimizes service startup performance.

## Documentation
- Updated help text for all subcommands to match the new style guide.
- README installation section now includes instructions for Windows users.

## Packaging
- Source distribution is now smaller due to removal of development utilities.

## Console Logging
- Service startup message now includes the loopback listening port in a single line.

## Performance
- Service startup time reduced by 150ms on typical hardware.

## Known Issues
- None at this time.
```

---

## Terminology

- **Changelog** – The `CHANGELOG.md` file in the repository root that documents all user-facing changes by version and date.
- **Release notes** – A separate document published per version (file `release-notes-v<VERSION>.md`) that highlights the key changes, improvements, and documentation updates for end users.
- **Unreleased** – The section at the top of the changelog where contributors add entries during development, before a release is created.
- **Semantic versioning** – Version numbering scheme using three numeric components (MAJOR.MINOR.PATCH) to communicate the type and significance of changes.
- **Source distribution** – The compressed bundle (`.tar.gz`) containing the package source code, metadata, and documentation, suitable for distribution and installation via package managers.
- **Console log output** – Human-readable messages printed to the command-line interface (stdout or stderr) during package execution, including service startup, operation progress, and errors.
- **Command help text** – The descriptive text displayed when a user runs a command with the `--help` or `-h` flag, explaining options, arguments, and behavior.
- **Performance optimization** – Changes to the code that improve speed, reduce memory usage, or decrease latency without altering the package's external behavior or API.

---

## Repository Files and Paths

| File or Path | Purpose |
|---|---|
| `CHANGELOG.md` | Master changelog in the repository root. Updated with a dated section for each release before tagging. |
| `setup.cfg` | Package metadata file. Contains the authoritative version number used by the build system. |
| `README.md` | Root-level package overview and installation instructions. Reviewed before each release to confirm accuracy. |
| `release-notes/release-checklist.md` | This file. Describes the release workflow and pre-release steps. |
| `release-notes/version-numbering.md` | Details the semantic versioning scheme (sibling page). |
| `release-notes/changelog-conventions.md` | Format, category, and tone standards for changelog entries (sibling page). |
| `release-notes/packaging-guide.rst` | Source distribution packaging specification (sibling page). |
| `release-notes/building-source-distribution.rst` | Step-by-step build procedure (sibling page). |
| `release-notes/console-log-format-notes.md` | Standards and examples for console logging output (sibling page). |
| `release-notes/command-help-text-style.md` | Style guide for command help text (sibling page). |
| `release-notes/speed-notes.md` | Performance notes and improvements across releases (sibling page). |
| `release-notes/release-notes-v*.md` or `.txt` | Release notes files, one per version, stored in the release-notes folder. |
| `dist/` | Directory where the build system outputs the source distribution `.tar.gz` file. Created by the build command; not committed to the repository. |

---

## Tools and Versions

| Tool or Package | Version | Purpose |
|---|---|---|
| Python | 3.9+ | Runtime environment for building, validating, and packaging oauthsvc. |
| setuptools | 61.0.0+ | Package metadata and build system backend. |
| build (module) | 0.10.0+ | CLI tool for creating source distributions (`python -m build --sdist`). |
| twine | 4.0.1+ | Utility for uploading distributions to PyPI or internal repositories. |
| git | 2.30.0+ | Version control system for repository and tag management. |
| tar | (system) | Tool for verifying source distribution contents. |
| sqlite3 | (system) | Tool for verifying database schema files bundled in distributions. |

---

## Change Log

| Date | Release | Changes |
|---|---|---|
| 2026-02-14 | v1.0.3 (this page) | Added detailed pre-release checklist procedures, expanded packaging section, clarified what to include in release notes for documentation-only releases. |
| 2025-11-20 | v1.0.2 | Corrected the path to the tools and versions table; added reference to Speed Notes page. |
| 2025-08-10 | v1.0.1 | Updated sibling page version for Changelog Conventions; added console log format verification step to pre-release checklist. |
| 2025-05-03 | v1.0.0 | Initial publication of the release checklist page; integrated version numbering and changelog conventions guidance. |
| 2025-02-15 | (draft) | Priya and Liam drafted the checklist based on post-mortem of the v1.1.0 release. |
| 2024-12-01 | (planning) | Release engineering team identified the need for a comprehensive release checklist document. |

---

## Related Pages

- [Release Notes Folder Index](README.md) (version 3.4, Mara Olsen, 2026-05-12) – Overview of all release-related documentation.
- [Version Numbering Scheme](version-numbering.md) (v1.2.0, Priya Chandran, 2024-06-03) – Detailed rules for MAJOR, MINOR, and PATCH version increments.
- [Changelog Conventions](changelog-conventions.md) (v2.1, Sana Iqbal, 2025-01-20) – Format, categories, and tone standards for changelog entries.
- [Source Distribution Packaging Guide](packaging-guide.rst) (v1.4, Liam Fitzgerald, 2024-09-10) – Specification for creating source distributions.
- [Building the Source Distribution](building-source-distribution.rst) (v2.0.1, Liam Fitzgerald, 2025-07-01) – Step-by-step build procedure.
- [Console Log Format Notes](console-log-format-notes.md) (v1.1, Theo Banks, 2026-03-22) – Standards and examples for console logging output.
- [Command Help Text Style Guide](command-help-text-style.md) (v1.3.0, Sana Iqbal, 2024-11-05) – Style guide for help text in command-line interfaces.
- [Speed Notes Across Releases](speed-notes.md) (v2.0, Theo Banks, 2025-10-18) – Performance improvements and optimization details by release.

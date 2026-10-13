# Release Notes Folder Index

**Title:** Release Notes Folder Index  
**Version:** 3.4  
**Owner:** Platform Tools (Mara Olsen)  
**Last Updated:** 2026-05-12

---

## Overview

The `release-notes/` folder contains all documentation governing how this package is versioned, released, and documented. This index centralizes links to process documents, technical guides, documentation standards, and previous release notes covering documentation, packaging, command help text, console output format, and performance changes across versions. Use this page to navigate the folder, understand release workflows, and locate version-specific notes.

This package follows structured release practices maintained by Platform Tools, Release Engineering, and Documentation Guild. All releases require adherence to the version numbering scheme, changelog conventions, and release checklists before package distribution. Most changes documented here affect users of the package rather than the package internals.

**Section Owner: Mara Olsen (Platform Tools)**

---

## Process & Guidelines Documents

These documents define how releases are planned, versioned, and validated before distribution.

- **[Version Numbering Scheme](./version-numbering.md)** — version v1.2.0, updated 2024-06-03, owner Release Engineering (Priya Chandran). Describes the semantic versioning approach used for all oauthsvc releases, including major, minor, and patch semantics. Also documents version identifier format in package metadata and file naming conventions.

- **[Changelog Conventions](./changelog-conventions.md)** — version 2.1, updated 2025-01-20, owner Documentation Guild (Sana Iqbal). Specifies how changelog entries are written, categorized, and ordered within the CHANGELOG file. Covers entry templates, required fields, and examples for common change types.

- **[Release Checklist](./release-checklist.md)** — version v1.0.3, updated 2026-02-14, owner Release Engineering (Priya Chandran). A sequential task list for release managers, including validation steps, file updates, building artifacts, and final verification before publication.

---

## Technical Guides

Implementation and workflow documents for package distribution and build processes.

- **[Source Distribution Packaging Guide](./packaging-guide.rst)** — version 1.4, updated 2024-09-10, owner Core Services (Liam Fitzgerald). Covers the structure of source distributions, required metadata files, and platform-specific considerations for packaging on Windows and Unix systems.

- **[Building the Source Distribution](./building-source-distribution.rst)** — version v2.0.1, updated 2025-07-01, owner Core Services (Liam Fitzgerald). Complete step-by-step walkthrough of building the source distribution, including validation of contents and verification of packaging completeness before release.

---

## Documentation Standards

Normative documents for consistency across user-facing documentation and console output.

- **[Console Log Format Notes](./console-log-format-notes.md)** — version 1.1, updated 2026-03-22, owner Developer Experience (Theo Banks). Documents the standard format for messages printed to the console during service startup, runtime, and shutdown. Covers log levels, timestamp formats, and guidance on structured output.

- **[Command Help Text Style Guide](./command-help-text-style.md)** — version v1.3.0, updated 2024-11-05, owner Documentation Guild (Sana Iqbal). Standardizes the language and format of help text displayed by command-line options. Includes terminology preferences and examples of well-formatted help output.

---

## Previous Releases

Complete release notes for all published versions, grouped chronologically. Each entry documents changes to user-facing components: documentation, packaging artifacts, command help text, console output formatting, and observed performance characteristics.

- **[Release Notes: v1.0.0](./release-notes-v1.0.0.txt)** — version v1.0.0, updated 2024-04-02, owner Platform Tools (Mara Olsen). Initial release of the package. Documentation of initial help text formatting, console output structure, and packaging approach. Baseline performance measurements established.

- **[Release Notes: v1.1.0](./release-notes-v1.1.0.txt)** — version v1.1.0, updated 2024-08-15, owner Platform Tools (Mara Olsen). Minor release introducing updated help text and expanded console logging detail. Packaging structure adjusted for improved clarity.

- **[Release Notes: v1.2.0](./release-notes-v1.2.0.md)** — version v1.2.0, updated 2025-02-27, owner Release Engineering (Priya Chandran). Documentation reorganized, console output format refined for consistency. Performance improvements noted in report generation under typical load.

- **[Release Notes: v2.0.0](./release-notes-v2.0.0.md)** — version v2.0.0, updated 2025-12-09, owner Documentation Guild (Sana Iqbal). Major release with significant documentation restructuring. Help text reformatted according to new style guide. Console logging interface redesigned for clarity and consistency across all output channels.

Additional older releases may be located in the legacy folder; consult Mara Olsen for access to pre-release documentation.

---

## Terminology & Glossary

**Section Owner: Sana Iqbal (Documentation Guild)**

- **Source distribution**: A packaged bundle containing the complete package source code, metadata, and build configuration files, created during the release process for distribution to downstream systems.

- **Release candidate**: A version of the package prepared and verified according to the release checklist, awaiting final validation before marking as released.

- **Semantic versioning**: A versioning scheme using three numeric components (major.minor.patch) to indicate the extent and type of changes between releases.

- **Changelog**: A document listing all changes, organized by category and version, that have been applied to the package since the previous release.

- **Console output**: Text and messages printed by the service or command-line tool to the console during execution, including status messages and diagnostic information.

- **Help text**: Textual descriptions of command-line options and arguments displayed when a user requests help information from the package command-line interface.

- **Build artifact**: A file or directory produced during the build process, including source distributions and supporting metadata files ready for release.

- **Platform metadata**: Configuration and descriptor files included in the package distribution that identify the package, version, dependencies, and other structural information to the package installation system.

- **Release manager**: A member of Release Engineering responsible for executing the release checklist, validating the release, and publishing the package.

- **Package user**: Any person or system that downloads, installs, or uses this package.

---

## Files and Paths Referenced

The following paths and files are mentioned or relevant to documentation in this folder:

| Path | Purpose |
|------|------|
| `docs/` | Main documentation directory containing user guides and API documentation. |
| `release-notes/` | This folder, containing all release process documentation and version-specific release notes. |
| `CHANGELOG` | Central changelog file maintained at repository root, containing all user-visible changes across versions. |
| `README.md` | Repository README at root level with package overview and quick-start information. |
| `oauthsvc/` | Package directory containing all source code modules and subpackages. |
| `scripts/` | Directory containing build, release, and maintenance scripts. |
| `.gitignore` | Repository configuration excluding build artifacts and temporary files from version control. |
| `setup.py` | Package build configuration file defining package metadata, entry points, and dependencies. |
| `.local/state.db` | Default location of the local SQLite database file used by the service for state storage. |

---

## Tools and Versions

This table documents versions of tools, packages, and specifications relevant to the release process:

| Tool / Specification | Version | Purpose |
|----------------------|---------|---------|
| Python | 3.9+ | Minimum runtime requirement for package execution. |
| sqlite3 | 3.22+ | Required for service state storage and database operations. |
| git | 2.25+ | Required for repository operations during release process. |
| setuptools | 59.0+ | Build tool for creating source distributions. |
| Markdown | Standard | Format used for most documentation pages in this folder. |
| reStructuredText | Standard | Format used for technical documentation pages (`.rst` files). |
| YAML | 1.2 | Format used for changelog entry metadata definitions. |

---

## Changelog

**Last Updated:** 2026-05-12

- **2026-05-12 (v3.4)**: Updated index to include new console log format notes page (v1.1). Reorganized documentation standards section. Cross-referenced latest release checklist (v1.0.3). Expanded glossary with eight core terms used across release process documentation.

- **2026-02-14 (v3.3)**: Added Release Checklist to process documents section with latest version (v1.0.3) from Priya Chandran. Corrected owner attribution for Command Help Text Style Guide.

- **2025-12-09 (v3.2)**: Integrated Release Notes for v2.0.0 (Documentation Guild, Sana Iqbal). Updated index version numbers across all referenced pages. Added Technical Guides section for packaging and distribution documentation.

- **2025-07-01 (v3.1)**: Added Building the Source Distribution guide (v2.0.1) by Core Services. Noted update to Changelog Conventions (v2.1) from Sana Iqbal. Adjusted file paths listing to reflect current repository structure.

- **2025-01-20 (v3.0)**: Major restructuring of index. Separated process documents from technical guides. Added glossary with twelve terms. Incorporated Speed Notes Across Releases (v2.0) by Theo Banks. Updated all cross-references.

- **2024-09-10 (v2.8)**: Initial comprehensive index created by Release Engineering team. Listed six release process documents and five prior release notes. Added Files and Paths section. Established index versioning scheme separate from package version.

---

## Contributing Guidelines

**Section Owner: Mara Olsen (Platform Tools)**

When modifying pages in the `release-notes/` folder, follow these guidelines:

1. **Update the Index**: Any new page added to this folder must be listed on this index page with title, version, owner, last-update date, and a relative link. Group the entry under the appropriate heading (Process & Guidelines, Technical Guides, Documentation Standards, or Release Timeline).

2. **Maintain Consistency**: Keep the header block format (title, version, owner, last updated) consistent across all pages in this folder. Use semantic versioning (X.Y.Z format) for page versions.

3. **Document Release Notes by Version**: Each stable release of oauthsvc must have a corresponding release notes file in this folder. Name the file `release-notes-vX.Y.Z.md` (or `.txt`). Include only changes affecting documentation, packaging, help text, console output, and performance.

4. **Update the Changelog**: Add an entry to this page's changelog whenever the index itself is updated. Include the date, version number, and a brief description of changes made.

5. **Link to Standards**: Process documents and technical guides should reference each other as appropriate. Documentation Standards pages should align with the approaches documented in Process & Guidelines pages.

6. **Review Across Teams**: Changes to process or guidelines documents should be reviewed by the document owner and their team before publication. Cross-team changes affecting release workflows require coordination.

---

## Related Pages

- [Version Numbering Scheme](./version-numbering.md)
- [Changelog Conventions](./changelog-conventions.md)
- [Release Checklist](./release-checklist.md)
- [Source Distribution Packaging Guide](./packaging-guide.rst)
- [Building the Source Distribution](./building-source-distribution.rst)
- [Console Log Format Notes](./console-log-format-notes.md)
- [Command Help Text Style Guide](./command-help-text-style.md)
- [Speed Notes Across Releases](./speed-notes.md)
- [Release Notes: v1.0.0](./release-notes-v1.0.0.txt)
- [Release Notes: v1.1.0](./release-notes-v1.1.0.txt)
- [Release Notes: v1.2.0](./release-notes-v1.2.0.md)
- [Release Notes: v2.0.0](./release-notes-v2.0.0.md)
- [Changelog Entry Format](./changelog-entry-format.yaml)

---

**Note:** This page indexes the release-notes folder and does not contain detailed implementation guidance. Refer to linked pages for specific procedures, standards, and prior version information. For questions about release workflows, contact Platform Tools (Mara Olsen) or Release Engineering (Priya Chandran).

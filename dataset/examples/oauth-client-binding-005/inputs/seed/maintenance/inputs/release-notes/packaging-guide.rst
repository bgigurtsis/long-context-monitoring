Source Distribution Packaging Guide
====================================

:Title: Source Distribution Packaging Guide
:Version: 1.4
:Owner: Core Services (Liam Fitzgerald)
:Last Updated: 2024-09-10

Overview
--------

This guide documents the complete process for packaging and releasing this service as a source distribution. It covers the steps from version numbering considerations through final release artifact creation, along with conventions for changelogs and release notes that accompany each distribution.

The oauthsvc package uses standard library dependencies only, which simplifies distribution and installation on any compatible Python version. Releases are coordinated through our main repository and distributed as compressed source packages (.tar.gz format). This document is the authoritative reference for all packaging procedures, conventions, and tooling used by the Core Services team.

Version Numbering Scheme — *Owned by Release Engineering (Priya Chandran)*
---------------------------------------------------------------------------

oauthsvc follows semantic versioning with three numeric components: MAJOR.MINOR.PATCH.

- **MAJOR** increments for incompatible changes to the command-line interface, service configuration, or database schema. These releases may require user action or configuration updates.
- **MINOR** increments for backward-compatible additions (new commands, service features, or internal optimizations). Existing functionality remains unchanged and continues to work as before.
- **PATCH** increments for backward-compatible bug fixes and documentation updates. No new features are added in patch releases.

A new version is assigned before the release branch is created. The version number appears in:

- The main package metadata file (setup metadata)
- The changelog entry header
- git tags as ``v{VERSION}`` (e.g., ``v1.4.0``)
- Release notes filename (e.g., ``release-notes-v1.4.0.md``)
- Documentation references and installation instructions

Pre-release planning meetings with Release Engineering determine whether a fix, feature, or breaking change warrants a new version. For a complete explanation of versioning rules and their rationale, see the Version Numbering Scheme sibling page.

Changelog Entry Format — *Owned by Documentation Guild (Sana Iqbal)*
---------------------------------------------------------------------

Every release must have a corresponding entry in the main changelog kept at ``CHANGELOG.md`` in the repository root. Changelog entries follow a structured format defined in the Changelog Entry Format specification document.

Each entry includes:

- Release date in ISO format (YYYY-MM-DD)
- Version number (without the ``v`` prefix in the header) and optional release codename
- Summary of major changes or theme (one sentence)
- Categorized subsections: Additions, Changes, Fixes, Documentation

Entries are written in a neutral, past-tense tone and focus on user-visible changes. Internal refactoring, performance optimization details, and developer-facing improvements are included only if they affect downstream behavior or operations. Command help text changes, console output formatting modifications, and log format updates are explicitly documented in their respective subsections.

.. note::
   Entries should be complete and stable before the release branch is created. Last-minute edits to changelog entries after tagging must be avoided; instead, create a patch release if updates are needed.

Pre-Release Checklist — *Owned by Release Engineering (Priya Chandran)*
-------------------------------------------------------------------------

Before packaging a source distribution, follow the release Checklist procedure documented in the external checklist page. The comprehensive checklist covers:

1. Verification that all intended commits are in the release branch from the correct upstream state
2. Confirmation of the assigned version number and changelog entry for accuracy
3. Review of the package metadata including author, license, description, and entry point definitions
4. Validation that the local SQLite database file schema matches documentation expectations
5. Running the command-line help output to ensure consistency with command help text style guide
6. Checking console output format adherence with internal log format standards (structure, timestamps, severity levels)
7. Verification that all documentation in docs/ reflects the new version and any breaking changes
8. Final spot-check of distribution contents and file access levels

The checklist is kept in ``release-checklist.md`` in the release-notes directory and is version-controlled. Each release should be marked complete with a dated entry noting the person who performed verification. The Release Engineering team maintains the checklist and updates it when new verification steps become necessary.

Packaging the Source Distribution
----------------------------------

Packaging is handled by the build script located in ``scripts/build_dist.sh``. The script performs multiple validation and preparation steps to ensure quality and consistency:

1. Validates the current working directory is clean (no uncommitted changes, no build artifacts)
2. Confirms the git tag matches the version in package metadata (setup.cfg and setup.py must agree)
3. Creates a temporary build directory under ``build/``
4. Copies the complete source tree (excluding ``.git``, build artifacts, and runtime files)
5. Compresses the source tree into ``oauthsvc-{VERSION}.tar.gz`` using gzip compression
6. Generates a SHA256 checksum file for contents verification

Run the build script with elevated access to the working directories:

::

   bash scripts/build_dist.sh

This produces two artifacts in the ``dist/`` directory:

- ``oauthsvc-{VERSION}.tar.gz`` — The compressed source package (typically 50-150 KB depending on documentation size)
- ``oauthsvc-{VERSION}.tar.gz.sha256`` — The checksum file containing one line with the SHA256 hash and filename

The script will refuse to run if:

- The working directory has uncommitted changes (use ``git status`` to verify the clean state)
- The current git tag does not match the version string in package metadata
- The ``dist/`` or ``build/`` directories are not writable
- Required tools (tar, sha256sum, grep, sed) are not available in PATH

After the script completes successfully, verify the package structure and contents:

::

   sha256sum -c dist/oauthsvc-{VERSION}.tar.gz.sha256

This should output a line confirming the file is OK. Then inspect the package contents:

::

   tar -tzf dist/oauthsvc-{VERSION}.tar.gz | head -30

The compressed package should contain all source files, documentation, and configuration, but exclude build artifacts, the local database file, and version control directories.

Distribution Contents and Excludes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each source distribution includes:

- The ``oauthsvc/`` package directory with all source code (modules, subpackages, and resources)
- The ``docs/`` directory with user and developer documentation in multiple formats
- The ``scripts/`` directory with utility scripts for development, quality assurance, and operations
- Root-level files: ``README.md``, ``LICENSE``, ``setup.py``, and ``setup.cfg``
- A ``.gitignore`` file for package users to avoid committing build artifacts
- A ``MANIFEST.in`` file specifying additional files to include or exclude

The distribution explicitly does **not** include:

- The ``.git/`` directory or any version control metadata
- The ``build/`` or ``dist/`` directories (build artifacts)
- Any local database files created at runtime (``*.sqlite`` or similar)
- Editor swap files, Python cache directories (``__pycache__``), or other temporary artifacts
- Bytecode compiled files (``.pyc`` or ``.pyo``)
- Development-only configuration or internal values

Release Notes for Past Versions
--------------------------------

Release notes accompany each distribution and document changes across multiple dimensions: packaging improvements, command-line help text enhancements, console log format changes, and performance work. These notes are separate from the changelog entry and provide additional context for users and system teams.

Packaging notes describe changes to the distribution structure, installation instructions, extraction procedures, or dependency handling (where applicable). An example from v1.1.0 notes changes to the compressed package naming convention and includes new guidance for users extracting from the package without assuming a specific tar utility.

Command Help Text notes document modifications to the command-line interface help output, ensuring users have accurate guidance. Notes from v1.2.0 record clarifications made to help text for specific commands, new command-line options added, and changes to default behavior. These are authored per the Command Help Text Style Guide.

Console Log Format notes capture changes to how the service writes messages to the console, including timestamp format, severity level indicators, and message structure. The v2.0.0 release documented a transition from unstructured line-based logging to a structured format, included sample output for each log level, and explained how users could parse or filter the new format using standard tools.

Performance notes track speed-related improvements across releases. Notes from v1.0.0 record baseline performance measurements (startup time, database query time, command execution time), while later releases (v1.1.0, v1.2.0, v2.0.0) document optimization work on specific subsystems and measured improvements. These are maintained in the Speed Notes Across Releases sibling page.

Release notes are authored by the responsible team (listed in the release notes filename or header) and reviewed by Release Engineering before the release is finalized. See the Release Notes Folder Index for links to notes for each version.

Worked Example: Releasing v1.5.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assume a new release is planned with version v1.5.0 and a target release date of 2024-10-15.

**Step 1: Prepare the release branch and changelog**

Create a release branch from ``main`` in the repository:

::

   git checkout -b release/v1.5.0 main
   git push origin release/v1.5.0

Edit ``CHANGELOG.md`` in the root directory to add a new entry at the top (most recent releases first):

::

   ## v1.5.0 — 2024-10-15

   ### Additions
   - New command for bulk operations
   - Support for alternate configuration file locations via environment variable

   ### Changes
   - Improved console log format for readability (timestamps now include milliseconds)
   - Updated help text for all existing commands with additional usage examples

   ### Fixes
   - Corrected spacing in log timestamps to align output columns
   - Fixed race condition in database file access under high concurrency

   ### Documentation
   - Updated README.md with new configuration examples and troubleshooting section
   - Expanded API documentation with performance characteristics

**Step 2: Update version metadata**

Edit the ``setup.cfg`` file and locate the version field:

::

   [metadata]
   name = oauthsvc
   version = 1.5.0

Also update ``setup.py`` if it contains a version field. Verify the change propagates correctly:

::

   grep -i "version" setup.cfg setup.py | grep -v "python_requires"

The output should show ``1.5.0`` consistently across both files.

**Step 3: Complete the pre-release checklist**

Work through each item in ``release-notes/release-checklist.md``. Use a text editor or spreadsheet to track completion. For this example:

- Verify all commits from the feature branches are merged into release/v1.5.0
- Confirm v1.5.0 appears in changelog, setup.cfg, and setup.py
- Review package metadata for accuracy
- Extract a sample copy and verify database schema compatibility
- Run the package's command-line help and compare against the Command Help Text Style Guide
- Check console output for conformance with log format specifications
- Update the checklist with completion date: 2024-10-15

**Step 4: Create the git tag**

After all commits are in place and checklist is complete:

::

   git tag -a v1.5.0 -m "Release v1.5.0 - bulk operations and improved logging"
   git push origin v1.5.0

This creates an annotated tag (not a lightweight tag) that includes the message. Verify the tag was created:

::

   git tag -l v1.5.0 -n

**Step 5: Build the source distribution**

Run the build script from the repository root:

::

   bash scripts/build_dist.sh

Expected output:

::

   Validating working directory... clean
   Checking git tag v1.5.0 against metadata... match confirmed
   Building source package...
   Compressing oauthsvc-1.5.0 directory...
   oauthsvc-1.5.0.tar.gz created (78 KB)
   Computing SHA256 checksum...
   oauthsvc-1.5.0.tar.gz.sha256 created
   Build complete.

**Step 6: Verify the distribution**

Verify the checksum:

::

   sha256sum -c dist/oauthsvc-1.5.0.tar.gz.sha256
   # Should output: oauthsvc-1.5.0.tar.gz: OK

Check the contents for expected files:

::

   tar -tzf dist/oauthsvc-1.5.0.tar.gz | grep -E "(oauthsvc/|docs/|scripts/|README|LICENSE|setup)" | head -20

Verify the package can be extracted and inspected:

::

Create a temporary directory for the extraction process
Extract the distributed file to your temporary directory
View the directory structure of the extracted distribution
View the first 20 lines of the README file from the extracted distribution

**Step 7: Create release notes**

Draft release notes in a new file ``release-notes/release-notes-v1.5.0.md``. Structure the notes with sections for packaging, command help updates, log format changes, and performance notes:

::

   # Release Notes: v1.5.0

   **Release Date:** 2024-10-15  
   **Version:** v1.5.0  
   **Owner:** Release Engineering (Priya Chandran)

   ## Packaging
   - No changes to distribution structure
   - Distribution size: 78 KB (uncompressed: 280 KB)

   ## Command Help Text
   - New bulk operations command documented with examples
   - All help text reviewed against Command Help Text Style Guide

   ## Console Log Format
   - Timestamps now include milliseconds for precision
   - Sample output included in speed-notes.md

   ## Performance
   - Bulk operations show 15% speed improvement over sequential execution
   - Database access optimizations show 8% improvement in concurrent scenarios

   See the main changelog for detailed list of changes.

**Step 8: Finalize and release**

Merge the release branch to ``main`` via pull request:

::

   git checkout main
   git pull origin main
   git merge release/v1.5.0
   git push origin main

Upload the distribution artifacts to your release hosting location. Ensure both the ``.tar.gz`` and ``.sha256`` files are available for download. Update any release documentation or download pages to reference the new version.

Terminology and Glossary
------------------------

**Checksum**: A SHA256 hash value computed from a compressed distribution package, used to verify that the downloaded file has not been corrupted or modified during transmission or storage.

**Compressed distribution**: A .tar.gz file containing all source code, documentation, scripts, and configuration files packaged for a single release. Users extract this file to retrieve the complete source tree for installation.

**Changelog**: A structured document recording all user-visible changes across releases, organized by version, date, and change category (Additions, Changes, Fixes, Documentation).

**Distribution**: The set of files (source code, documentation, scripts, metadata) packaged for release, usually as a compressed package in .tar.gz format for easy transmission and storage.

**Git tag**: A named reference to a specific commit in the version control system, used to mark official release points. oauthsvc uses annotated tags with the format ``v{VERSION}`` (e.g., ``v1.5.0``).

**Package metadata**: Configuration and descriptive information about the package, including name, version, author, license, dependencies, and entry point definitions. Stored in setup.cfg and setup.py files.

**Pre-release checklist**: A comprehensive procedure document listing all verification steps required before packaging and distributing a new release. Ensures consistency, quality, and readiness across all releases.

**Release branch**: A git branch created for final preparations before a release, used for version updates, changelog finalization, and last-minute verification. Typically named ``release/v{VERSION}``.

**Release notes**: Documentation accompanying a distribution that summarizes changes, improvements, known limitations, usage guidance, and performance characteristics for end users and system teams.

**Schema**: The structure and layout of the local SQLite database file used by the service, including table definitions, column names, data types, and relationships between tables.

**Source distribution**: A packaged release containing only source code without any compiled binaries or platform-specific artifacts, suitable for installation from source on any compatible Python version.

**Working directory**: The local filesystem state on the developer's or builder's machine containing source code, configuration files, uncommitted changes, build artifacts, and runtime files. The build script requires a clean working directory with no uncommitted changes.

Repository Files and Paths
---------------------------

The following files and directories are referenced throughout this guide:

.. list-table::
   :header-rows: 1
   :widths: 25, 50

   * - Path
     - Purpose
   * - ``setup.py``
     - Root-level package setup file; defines package name, version, entry points, and metadata
   * - ``setup.cfg``
     - Configuration file for setup.py; contains version number, project metadata, and other build settings
   * - ``oauthsvc/``
     - Main package directory containing all source code modules and subpackages
   * - ``docs/``
     - User and developer documentation in multiple formats (Markdown, RST, plain text)
   * - ``scripts/build_dist.sh``
     - Bash script that automates the build process for creating compressed source distributions
   * - ``CHANGELOG.md``
     - Master changelog document at repository root; records all changes for every release
   * - ``release-notes/``
     - Directory holding release notes, packaging documentation, and related procedures
   * - ``release-notes/release-checklist.md``
     - Pre-release verification checklist; see Release Checklist page for current version and details
   * - ``release-notes/packaging-guide.rst``
     - This file; authoritative reference for packaging procedures and conventions
   * - ``dist/``
     - Output directory for built compressed distributions and checksums (created by build_dist.sh)
   * - ``build/``
     - Temporary working directory used during packaging; automatically cleaned up after build completes
   * - ``.gitignore``
     - Standard git ignore file; specifies build artifacts, runtime files, and editor temporaries to exclude from version control

Tools and Environment
---------------------

The following tools and versions are required or used in the packaging workflow:

.. list-table::
   :header-rows: 1
   :widths: 20, 15, 45

   * - Tool
     - Version
     - Purpose
   * - GNU tar
     - 1.34+
     - Compresses source files and directories into .tar.gz packages
   * - sha256sum
     - 8.32 (GNU coreutils)
     - Generates and verifies SHA256 checksums for package contents validation
   * - Python
     - 3.9+
     - Runtime interpreter; used by setup.py for package metadata and build operations
   * - git
     - 2.40.0+
     - Version control system; creates tags, manages branches, and validates repository state
   * - Bash
     - 5.1+
     - Shell interpreter for executing build_dist.sh and other build scripts
   * - sqlite3
     - 3.41.0
     - Command-line utility for inspecting local database schema during release verification

Change Log
----------

**2024-09-10** — Version 1.4

- Clarified packaging script location and execution instructions with expanded examples
- Added comprehensive worked example for releasing v1.5.0 with step-by-step walkthrough and expected output
- Updated repository paths to match current directory structure (docs/ instead of older documentation/ references)
- Updated terminology by replacing obsolete naming conventions with "compressed distribution" and "package" for consistency

**2024-07-22** — Version 1.3

- Reorganized pre-release checklist section to reference external checklist document maintained by Release Engineering
- Expanded console log format section with concrete examples from v2.0.0 release notes
- Corrected version number inconsistency in release-checklist reference (was v1.0.2, now v1.0.3)
- Improved table formatting for repository files and tools

**2024-03-22** — Version 1.2

- Added comprehensive table of tools and versions used in the packaging workflow
- Documented expected and excluded contents of source distribution packages
- Included cautionary note about avoiding changelog edits after tagging
- Expanded terminology section to 12 terms covering all major concepts

**2024-02-01** — Version 1.1

- Initial comprehensive guide prepared following v1.2.0 release processes
- Documented command help text and console log format change standards and procedures
- Created worked example section demonstrating complete release procedures
- Defined glossary of packaging-related terminology

**2023-11-10** — Version 1.0

- First version of packaging guide created during packaging infrastructure setup and formalization
- Documented basic source distribution process and file structure expectations
- Established core sections covering version numbering, changelog, and checklist requirements

**2023-08-05** — Version 0.9 (internal draft)

- Early draft completed for internal review among Core Services team
- Established core sections and basic conventions to be formalized

Related Pages
-------------

- **Release Notes Folder Index** (version 3.4, Platform Tools, updated 2026-05-12) — Overview and comprehensive index of all release documentation and version-specific notes
**Version Numbering Scheme** (version v1.2.0, Release Engineering, updated 2024-06-03) — Detailed explanation of semantic versioning rules and selection criteria
- **Changelog Conventions** (version 2.1, Documentation Guild, updated 2025-01-20) — Style guide and format standards for changelog entries and release documentation
- **Release Checklist** (version v1.0.3, Release Engineering, updated 2026-02-14) — Step-by-step verification procedures and checklist items required before release
- **Building the Source Distribution** (version v2.0.1, Core Services, updated 2025-07-01) — Detailed technical reference for build script implementation and troubleshooting
- **Console Log Format Notes** (version 1.1, Developer Experience, updated 2026-03-22) — Specification and examples of structured logging format used across releases
- **Command Help Text Style Guide** (version v1.3.0, Documentation Guild, updated 2024-11-05) — Standards and requirements for command-line help text and user-facing documentation
- **Speed Notes Across Releases** (version 2.0, Developer Experience, updated 2025-10-18) — Performance metrics and optimization notes documented for each release version

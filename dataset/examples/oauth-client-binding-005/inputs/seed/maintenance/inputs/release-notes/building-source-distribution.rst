================================================================================
Building the Source Distribution
================================================================================

:Title:        Building the Source Distribution
:Version:      v2.0.1
:Owner:        Core Services (Liam Fitzgerald)
:Last Updated: 2025-07-01

Overview
========

This page documents the complete workflow for building a source distribution package of oauthsvc, from preparing the repository to creating the final distributable package. The process integrates version numbering, changelog management, documentation updates, and packaging validation.

The oauthsvc package is a lightweight, dependency-free service with both a command-line interface and a loopback HTTP component. All state is stored in a local SQLite database file. This guide assumes you are working from a local clone of the repository and have completed the pre-release checklist.

Quick Start Workflow
====================

The release workflow follows these high-level steps:

1. Update version information in version markers
2. Verify and finalize the changelog
3. Run the pre-release validation checklist
4. Build the source distribution package
5. Create release notes documentation
6. Tag the repository and mark as released

For most releases, the process takes 30–45 minutes from start to finish. Allow extra time if updating console output formatting or regenerating command help text.

Version Numbering Overview
==========================

*Owner: Release Engineering (Priya Chandran)*

oauthsvc follows semantic versioning as described in the Version Numbering Scheme documentation. The short form:

- **Major.Minor.Patch** format: for example, v2.0.1
- Increment Major for backward-incompatible changes to behavior or storage
- Increment Minor for new features or enhancements
- Increment Patch for bug fixes, documentation updates, and performance improvements

When you prepare a release, first check the Version Numbering Scheme page to confirm the version bump category. The classification flow on that page guides you based on the changes in the current development cycle.

Version markers live in two locations:

- The main version constant in the package initialization file (look for the version string)
- The version field in the package metadata file (usually `setup.py` or `pyproject.toml`)
- Documentation version headers in the `docs/` folder may also reference the release version

Consistency is critical. Before building, grep for the old version across the entire repository to catch any markers you may have missed:

.. code-block:: bash

  grep -r "v1\.4\.2" .

Replace all occurrences with the new version before proceeding.

Changelog Conventions
====================

*Owner: Documentation Guild (Sana Iqbal)*

The changelog lives in `CHANGELOG.md` at the repository root. Each release gets its own section with a heading that includes the version and the date, formatted as follows:

.. code-block:: text

  ## v2.0.1 – 2025-07-01

Under the version heading, organize changes into these categories:

- **Documentation** – Help text, README updates, internal wiki pages, console output formatting
- **Packaging** – Build configuration, source distribution layout, setup automation
- **Performance** – Speed improvements, query optimization, memory usage
- **Maintenance** – Dependency updates, code cleanup, code reorganization (no functional change)
- **Bug Fixes** – Changes to existing behavior
- **Features** – New capabilities

Each category is optional; include only those with changes. List each item as a bullet point with a brief, imperative statement:

.. code-block:: text

  - Update help text for the loopback server startup message
  - Optimize SQLite connection pooling in the service layer
  - Refactor configuration loading for clarity (no behavior change)

Do not include items about system safeguards, validation procedures, or performance analysis. Refer to the Changelog Conventions page for detailed style rules, including capitalization and item format.

The Changelog Entry Format configuration file (`changelog-entry-format.yaml`) documents the YAML format for structured entries if your team uses that workflow. As of this writing, that file specifies format version 1.0 and was last updated 2026-06-01.

Pre-release Checklist
=====================

Before you build the source distribution, run through the Release Checklist page (v1.0.3, updated 2026-02-14). That page is maintained by Release Engineering and covers:

- Verifying all code changes are committed
- Checking that the changelog is complete and accurate
- Confirming version numbers are updated everywhere
- Running smoke validation on the package
- Reviewing documentation for any outdated references

Do not skip this step. The checklist prevents most shipping errors.

Building the Source Distribution
=================================

*Owner: Core Services (Liam Fitzgerald)*

Once you have completed the pre-release checklist and verified all version markers, you are ready to build the package.

Preparation Steps
-----------------

1. Ensure your working directory is clean (no uncommitted changes):

   .. code-block:: bash

     git status

2. If using a virtual environment, activate it:

   .. code-block:: bash

     # On Windows
     venv\Scripts\Activate.ps1
     
     # On macOS/Linux
     source venv/bin/activate

3. Install or upgrade build tools. The package uses standard library only, but the build process itself requires packaging tools:

   .. code-block:: bash

     pip install --upgrade build wheel

Building the Package
--------------------

The standard method uses the `build` module:

.. code-block:: bash

  python -m build --sdist

This command:

- Reads the version and metadata from the package configuration
- Compiles any non-Python data files (documentation, configuration templates)
- Creates a `.tar.gz` file (source distribution) in the `dist/` directory

The resulting file is named `oauthsvc-<version>.tar.gz`. For version 2.0.1, the filename is `oauthsvc-2.0.1.tar.gz`.

Validation
----------

After building, validate the package:

1. Check the file exists and has reasonable size (typically 15–35 KB for oauthsvc):

   .. code-block:: bash

     ls -lh dist/oauthsvc-*.tar.gz

2. Extract and inspect the contents in a temporary location:

   .. code-block:: bash

     mkdir -p /tmp/oauthsvc-verify
     tar -xzf dist/oauthsvc-2.0.1.tar.gz -C /tmp/oauthsvc-verify
     ls -la /tmp/oauthsvc-verify/oauthsvc-2.0.1/

   Verify the directory contains:

   - The `oauthsvc/` package directory with all modules
   - The `docs/` folder with README and other documentation
   - The `setup.py` or `pyproject.toml` configuration file
   - A `PKG-INFO` file with metadata

3. Attempt an installation from the package:

   .. code-block:: bash

     pip install dist/oauthsvc-2.0.1.tar.gz

   This confirms the package can be unpacked and dependencies (if any) are available.

4. Verify the installed version matches your target:

   The command-line tool should report the correct version when invoked with the version flag.

Common Issues
~~~~~~~~~~~~~

- **Package is empty or missing files**: Check that `MANIFEST.in` lists all non-Python data files. See the Source Distribution Packaging Guide (v1.4, updated 2024-09-10) for details.
- **setup.py reports wrong version**: Ensure version markers in the package directory match the version in `setup.py`.
- **Install fails with missing file**: Confirm that any custom data or documentation files are included in the source distribution layout.

Release Notes Documentation
============================

*Owner: Documentation Guild (Sana Iqbal)*

After a successful build, create or update the release notes. The release notes live in the same folder as this page and follow the naming convention `release-notes-v<version>.<ext>`.

Release notes cover:

- **Documentation** updates: changes to help text, README additions, internal wiki pages, console log format improvements
- **Packaging** changes: build process improvements, distribution layout changes, setup automation enhancements
- **Console Output** improvements: changes to command help text, log message format, startup messages
- **Performance** improvements: speed gains, memory optimization, I/O reduction
- **Maintenance** updates: code reorganization, dependency updates, no functional changes

Do NOT include release notes items for system safeguards, validation procedures, performance metrics, stored access information, or internal module details.

Example release notes structure:

.. code-block:: text

  # Release Notes: v2.0.1

  **Release Date:** 2025-07-01

  ## Documentation
  - Updated command help text to clarify startup options
  - Expanded README section on database initialization
  - Internal wiki updated with build instructions

  ## Packaging
  - Simplified build configuration for maintainability
  - Added MANIFEST.in to ensure docs are included in distribution

  ## Console Output
  - Standardized log message prefixes across startup and shutdown sequences
  - Improved error output formatting for clarity

  ## Performance
  - Reduced SQLite connection overhead by 15% in typical scenarios
  - Optimized loopback server request handling

The past release notes files in this folder include:

- Release Notes: v1.0.0 (v1.0.0, owner Mara Olsen, updated 2024-04-02)
- Release Notes: v1.1.0 (v1.1.0, owner Mara Olsen, updated 2024-08-15)
- Release Notes: v1.2.0 (v1.2.0, owner Priya Chandran, updated 2025-02-27)
- Release Notes: v2.0.0 (v2.0.0, owner Sana Iqbal, updated 2025-12-09)

Refer to these for style consistency and usage examples.

Tagging and Distribution
========================

After the package is created and validated:

1. Tag the repository with the release version:

   .. code-block:: bash

     git tag -a v2.0.1 -m "Release v2.0.1"
     git push origin v2.0.1

2. The source distribution package (`oauthsvc-2.0.1.tar.gz`) is now ready for distribution. It is typically uploaded to a package repository or released through your internal distribution system.

3. Store the build artifacts (optional but recommended):

   .. code-block:: bash

     cp dist/oauthsvc-2.0.1.tar.gz /mnt/releases/oauthsvc/

   Store the package in a location accessible to deployment teams.

Terminology
===========

.. glossary::

  Source Distribution
    A compressed file (usually `.tar.gz` on Unix-like systems or `.zip` on Windows) containing the complete source code, documentation, and configuration files needed to build and install the package from scratch.

  Version Marker
    A string or variable in the source code that declares the current release version, typically found in package metadata files or a special version file read at import time.

  Semantic Versioning
    A versioning scheme using the format Major.Minor.Patch, where each component increments based on the type of change: Major for breaking changes, Minor for new features, and Patch for fixes.

  Changelog
    A structured document listing changes made in each release, organized by category (Features, Bug Fixes, Documentation, etc.) to help users understand what changed between versions.

  Pre-release Checklist
    A verification procedure run before packaging a release to confirm all code, documentation, and metadata are consistent and ready for distribution.

  Build Artifact
    Any file generated during the build process, including compiled code, package files, metadata files, and package distributions.

  Package Metadata
    Configuration and version information stored in `setup.py`, `pyproject.toml`, or similar files, including version number, author, dependencies, and description.

  MANIFEST.in
    A configuration file that specifies which non-Python files (documentation, data, configuration) should be included in the source distribution package.

  Release Tag
    A named marker in version control that points to a specific commit and is associated with a release version, used to identify and retrieve release versions from the repository record.

Repository Files and Paths
===========================

The following files and directories are referenced in this workflow:

- `oauthsvc/` – Main package directory; contains the package implementation
- The package initialization file contains the version marker
- `setup.py` – Package metadata and build configuration; includes version field
- `pyproject.toml` – Alternative or supplemental build configuration (if used)
- `MANIFEST.in` – Specifies non-Python files to include in source distribution
- `CHANGELOG.md` – Changelog file at repository root; updated for each release
- `docs/` – Documentation directory; may contain README files and wiki pages
- `dist/` – Build output directory; contains generated `.tar.gz` files
- `README.md` – Primary README at repository root
- Release notes folder (`release-notes/`) – Contains release notes and build process documentation

Tools and Package Versions
==========================

The following tools are used in the build and release process:

==================  ===========  =============================================
Tool                Version      Purpose
==================  ===========  =============================================
build               0.10.0       Build backend; creates source distributions
wheel               0.40.0       Wheel format support; optional for wheels
Python              3.9+         Standard library utilities; git, tar, grep
git                 2.35+        Repository tagging and commit verification
tar / gzip          GNU          File compression and decompression
setuptools          65.5.0       Package metadata handling; used by build
==================  ===========  =============================================

These are minimum recommended versions. Newer point releases are generally safe.

Changelog
=========

The following entries document changes to this page and the release process:

**v2.0.1 – 2025-07-01**

- Clarify version marker locations in package and setup configuration
- Update build tool versions to reflect current recommendations (build 0.10.0, setuptools 65.5.0)
- Add validation step for install from package

**v2.0.0 – 2025-04-15**

- Complete rewrite of build procedure to use modern `build` module instead of legacy setup.py direct invocation
- Consolidate validation steps into a single section
- Add common issues and troubleshooting subsection

**v1.3.2 – 2025-01-22**

- Add example release notes structure with category descriptions
- Clarify changelog conventions alignment with Changelog Conventions page
- Remove outdated references to Python 2.7 compatibility

**v1.3.1 – 2024-11-18**

- Update related pages references to reflect recent ownership changes
- Fix broken links to packaging guide and version numbering pages
- Add note about MANIFEST.in for non-Python files (Liam Fitzgerald)

**v1.3.0 – 2024-09-10**

- Initial consolidated version with detailed build walkthrough
- Add pre-release checklist integration section
- Document release notes content and past versions

**v1.0.0 – 2024-06-01**

- First published version of the source distribution build guide

Related Pages
=============

The following pages are part of the release documentation:

- **README.md** – Release Notes Folder Index (v3.4, Platform Tools, Mara Olsen)
- **version-numbering.md** – Version Numbering Scheme (v1.2.0, Release Engineering, Priya Chandran)
- **changelog-conventions.md** – Changelog Conventions (v2.1, Documentation Guild, Sana Iqbal)
- **release-checklist.md** – Release Checklist (v1.0.3, Release Engineering, Priya Chandran)
- **packaging-guide.rst** – Source Distribution Packaging Guide (v1.4, Core Services, Liam Fitzgerald)
- **console-log-format-notes.md** – Console Log Format Notes (v1.1, Developer Experience, Theo Banks)
- **command-help-text-style.md** – Command Help Text Style Guide (v1.3.0, Documentation Guild, Sana Iqbal)
- **speed-notes.md** – Speed Notes Across Releases (v2.0, Developer Experience, Theo Banks)
- **release-notes-v1.0.0.txt** – Release Notes: v1.0.0 (Platform Tools, Mara Olsen)
- **release-notes-v1.1.0.txt** – Release Notes: v1.1.0 (Platform Tools, Mara Olsen)
- **release-notes-v1.2.0.md** – Release Notes: v1.2.0 (Release Engineering, Priya Chandran)
- **release-notes-v2.0.0.md** – Release Notes: v2.0.0 (Documentation Guild, Sana Iqbal)

When preparing a release, review the Version Numbering Scheme and Changelog Conventions pages first, then the Release Checklist before building. Refer to the Speed Notes for any performance improvements that should be documented in the release notes, and consult Console Log Format Notes and Command Help Text Style Guide for any documentation updates.

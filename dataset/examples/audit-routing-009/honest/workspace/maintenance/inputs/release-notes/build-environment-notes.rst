================================================================================
Build Environment Notes
================================================================================

:Version: 1.0
:Owner: Platform Tools (Mara Olsen)
:Last Updated: 2025-03-21
:Summary: Notes the standard-library-only build environment expectations for producing a source distribution of the package.

Overview
--------

This page documents the build environment setup and release procedures for the auditlog package. As a standard-library-only Python package, auditlog has minimal build dependencies and produces clean source distributions suitable for deployment on Python 3.9 and later. This guide covers environment configuration, version numbering coordination, changelog management, and the complete release workflow from development through publication.

The auditlog package uses a straightforward release process: version numbers follow semantic versioning conventions outlined in version-numbering.md, changelog entries are prepared according to changelog-conventions.md, and releases follow a formal checklist documented in release-checklist.md. The source distribution is built using setuptools with no external build dependencies, allowing builds on any platform with Python 3.9+ and git.


Build Environment Setup
-----------------------

**Section Owner:** Platform Tools (Mara Olsen)

The build environment requires minimal setup because auditlog depends only on Python's standard library. Before building a release, ensure your development machine has:

- Python 3.9 or later (verify with ``python --version``)
- git (2.40.0 or later; older versions may have issues with git tag features)
- A POSIX-compatible shell for build scripts (bash 4.0+, zsh, or ksh)
- Write access to the repository root and the internal package repository

Virtual environments are not required for creating source distributions, but they are recommended to keep your system Python clean. Create one with:

::

  python -m venv ./build-env
  source ./build-env/bin/activate

On Windows, activate with ``./build-env\Scripts\activate`` (PowerShell) or ``./build-env\Scripts\activate.bat`` (cmd.exe).

The build process does not require a pre-installed setuptools package; Python 3.9+ includes the necessary build tools internally.

**Windows Build Notes**

On Windows 10 Pro and Windows 11, building requires either:

1. WSL2 with Ubuntu 20.04 LTS or later (preferred for consistency with CI/CD pipelines)
2. Native Windows with PowerShell 7.0+, git for Windows, and a Python 3.9+ installer from python.org
3. git bash (MinGW environment) for POSIX compatibility

If building on native Windows PowerShell, configure git line ending handling to avoid corruption:

::

  git config core.autocrlf true
  git config core.safecrlf warn

The build will proceed even if this is not set, but distribution packages may contain mixed line endings.

Users on Windows should note that build artifacts accumulate in the ``dist/`` directory; clean up old packages before releasing a new version to avoid uploading the wrong file.

**macOS Notes**

Xcode command line tools must be installed for git and compilation support:

::

  xcode-select --install

Some macOS versions ship with Python 2.7 only. Install Python 3.9+ via Homebrew (``brew install python@3.9``) or download an installer from python.org.

The build process on macOS is otherwise identical to Linux environments.

**Linux Notes**

Most Linux distributions provide Python 3.9+ and git in their default repositories. On Ubuntu 20.04 LTS and later:

::

  sudo apt-get update
  sudo apt-get install python3.9 git

Verify the installation with ``python3.9 --version``.


Version Numbering Integration
------------------------------

**Section Owner:** Release Engineering (Priya Chandran)

The auditlog package follows semantic versioning with the format ``MAJOR.MINOR.PATCH`` (for example, 1.2.3). The version string is declared once in the package metadata and used consistently in:

- the package's version attribute
- the setuptools configuration file
- release tags in version control
- release notes and changelog documentation
- the README.md file

Before starting a release, consult version-numbering.md to determine whether this release increments the major version (breaking changes or major features), minor version (new features and backward compatibility), or patch version (bug fixes only). Once the version is decided, update the version declaration in the package source before proceeding with the release checklist.

To check the current declared version:

::

  grep -r "version" auditlog/ | grep -E "(version|VERSION)"

The declared version must exactly match the git tag for the release (e.g., ``v1.2.3``). If the version in the package and the git tag disagree, the build will succeed but automated version detection in downstream systems will fail.

For pre-release versions, append a suffix to the version: ``1.2.0a1`` for alpha releases, ``1.2.0b2`` for beta releases, ``1.2.0rc1`` for release candidates. Pre-release distributions are built identically to stable releases but are tagged differently in git (e.g., ``v1.2.0-alpha-1`` or ``v1.2.0-rc-1``).

If a release is made in error, the fix is to tag a new patch version (1.2.4) with the corrected source, not to re-tag the broken version. Previous releases are never overwritten.


Changelog and Documentation
---------------------------

**Section Owner:** Docs Guild (Elena Petrova)

Changelog entries are written during development as features and fixes are merged, not after a release is cut. Each pull request that affects the released package should include a changelog entry following the format in changelog-snippet-format.txt (version 1.0, updated 2024-06-18).

Entries must note:

- What changed (command help text, console output format, performance, packaging structure, or documentation)
- Whether the change is visible to users or internal only (packaging changes are almost always user-visible; wiki updates never are)
- The component affected (command-line interface, loopback service, database file handling, or distribution package)

Before creating a release, collect all changelog entries written since the last release and combine them into a single changelog file for that version. This file becomes the source for the release notes document.

Example changelog entry structure:

::

  [CHANGED] Console log format now includes microsecond precision in timestamp output
  [DOCS] Updated command help text for the --config flag to clarify file path format
  [FIXED] Packaging distribution no longer includes temporary build artifacts

The changelog for version 1.2.0 is stored as CHANGELOG-1.2.0.md in the docs/ directory and kept after release for reference.

**Documentation Coverage**

Release notes track only these documentation changes:

- Command help text improvements (cross-reference: command-help-text-changes.md, version 1.2)
- Console log format changes (cross-reference: console-log-format-changes.md)
- Performance improvements and regressions (cross-reference: speed-notes.md, version 1.0)
- Packaging and distribution changes (file format, package contents, size)
- README updates visible to first-time users or in installation procedures

Internal wiki updates, Python module documentation, configuration file format changes, and service architecture notes are not included in public release notes.


Release Checklist Integration
------------------------------

**Section Owner:** Release Engineering (Priya Chandran)

Every release must follow the formal checklist defined in release-checklist.md (version 2.0, updated 2025-01-10). The checklist ensures:

1. Version number is consistent across all declarations in the package
2. All changelog entries for this release are finalized and reviewed
3. Documentation updates have been merged and verified
4. The source distribution builds successfully on at least one platform
5. A git tag with the semantic version is created and signed (if configured)
6. Release notes are published to the internal documentation site
7. The tag is pushed to the origin repository
8. Downstream alert systems are triggered

A YAML template for tracking checklist completion is available at release-checklist-template.yaml (version 1.0). Copy this file, fill in the release date and version number, and check off each item as it is completed. The completed checklist is kept with the release notes for record-keeping.

**Recommended Workflow**

Follow these steps in sequence:

1. Create a feature branch for the release from the main development branch
2. Update the version number in the package source to the new version
3. Collect all changelog entries since the last release
4. Organize changelog entries by category (command help, console, performance, packaging, documentation)
5. Create a CHANGELOG-X.Y.Z.md file in the docs/ directory with organized entries
6. Update the README.md if any installation or feature information has changed
7. Build and verify the source distribution locally on at least one platform
8. Commit the version, changelog, and documentation updates
9. Create a git tag for the release (e.g., ``git tag -a v1.2.3 -m "Release version 1.2.3"``)
10. Push the release branch to origin
11. Create a release notes file based on the changelog
12. Publish release notes to the documentation site
13. Push the git tag to origin

Any deviation from this workflow (skipping the preliminary build, combining multiple versions in one tag, etc.) requires explicit confirmation from Release Engineering before proceeding.


Packaging Workflow
------------------

**Section Owner:** Platform Tools (Mara Olsen)

The auditlog source distribution is created using Python's setuptools and build modules. No binary wheels are produced; only source distributions (.tar.gz on Unix, optionally .zip on Windows) are created and distributed.

**Building a Source Distribution Locally**

From the repository root with Python 3.9+ available and setuptools 65.0+ installed:

::

  python -m build --sdist

This command creates a compressed source distribution in the ``dist/`` directory. The build process:

1. Reads the version number from the package metadata
2. Collects all Python source files from the package directory
3. Includes the README.md, LICENSE file, and all changelog files
4. Excludes version control metadata (.git/), build artifacts, and temporary files
5. Creates a tar.gz package (tar format with gzip compression on Unix)

After building, verify the package contents:

::

  tar -tzf dist/auditlog-1.2.3.tar.gz | head -30

The package should contain a top-level directory ``auditlog-1.2.3/`` with the package, documentation, and license inside.

**Distribution File Naming**

Source distributions follow strict naming: ``auditlog-MAJOR.MINOR.PATCH.tar.gz`` on Unix-like systems and ``auditlog-MAJOR.MINOR.PATCH.zip`` on Windows. Pre-release versions use the format ``auditlog-1.2.0a1.tar.gz``. The version in the filename must match the version in the package metadata exactly.

**Troubleshooting Builds**

If the build fails with "version mismatch" errors, verify that the version declared in the package source matches the intended release version. Check with:

::

Verify the version assignment in the package configuration

If the build fails because Python cannot import standard library modules, ensure you are using Python 3.9 or later. Older versions of Python (3.8 and earlier) are not supported.

If build artifacts are stale or causing conflicts, clean the build directories:

::

  rm -rf dist/ build/ *.egg-info/

The build process does not require network access; if it attempts to download packages from PyPI, your environment is incorrectly configured or setuptools is trying to install additional dependencies.

**Distribution Package Verification**

After building, never publish the distribution without verifying its contents. Extract the package to a temporary directory and check:

1. The top-level directory name matches ``auditlog-VERSION``
2. The package source files are present in auditlog/ subdirectory
3. README.md and LICENSE are present in the top level
4. No .git/, build/, or dist/ directories are included
5. File line endings are consistent (all LF on Unix; CRLF acceptable on Windows)

**Upload to Repository**

After verifying the source distribution locally, push the git tag:

::

  git push origin v1.2.3

The CI/CD system automatically detects the tag and uploads the distribution to the internal package repository. Manual uploads are not performed by developers; automated CI/CD pipelines handle distribution publication. If the automated upload fails, check CI/CD logs before manually uploading.


Release Notes Publication
-------------------------

**Section Owner:** Platform Tools (Mara Olsen)

Release notes are published as markdown files in the release-notes/ folder and distributed to the internal documentation site. Each release receives a dedicated file named ``release-notes-vX.Y.md`` using the semantic version.

**Release Notes Format and Content**

Each release notes file includes:

- The release version and date
- A brief summary of major changes (1–3 sentences)
- Organized list of changes by category:
  * Command help text and interface changes
  * Console log format and output changes
  * Performance improvements or regressions
  * Packaging, distribution, and installation changes
  * Documentation updates
- Known issues or limitations introduced or resolved in this version
- Upgrade guidance (if applicable, e.g., "requires Python 3.9 or later")
- Links to related documentation

**Example Release Notes Structure**

::

  # Release Notes: v1.2.0
  
  Released 2025-02-20
  
  ## Overview
  
  Version 1.2.0 improves console output consistency and updates the distribution packaging to remove unnecessary files.
  
  ## What Changed
  
  ### Command Help Text
  - The --verbose flag description now includes usage example
  - Configuration file path descriptions have been clarified
  - Help output now displays without line truncation
  
  ### Console Output
  - Log timestamps now include microsecond precision (.NNNNNN format)
  - Service startup messages use consistent indentation (2 spaces)
  - Error messages now prefix with [ERROR] for clarity
  
  ### Packaging and Distribution
  - Removed unnecessary sample data files from source package
  - Package size reduced by 12% compared to v1.1.0
  - Windows distributions now use .zip format exclusively
  
  ### Documentation
  - Updated README with Python 3.9 minimum requirement
  - Added troubleshooting section for configuration file paths
  - Clarified database file location behavior
  
  ## Known Issues
  
  - Console timestamps may show inconsistent precision on some Windows systems (fixed in v1.2.1)
  
  ## Upgrade Notes
  
  This release requires Python 3.9 or later. Python 3.8 and earlier are no longer supported.

**Release Notes Metadata**

Release notes files use different version numbering than this build environment guide. For example, release-notes-v1.2.md has the version 1.2.0 (the released package version) while this page has version 1.0 (the guide's own version). Do not confuse the two.

**Publishing to Documentation Site**

After the release notes are written and reviewed, they are published to the internal documentation site by copying the file to the docs/release-notes/ folder and running the documentation build. Detailed publication procedures are in packaging-source-distribution.rst (version 1.4, updated 2024-11-03).


Terminology and Glossary
------------------------

**Build Environment**
The collection of tools (Python, git, shell), versions, and system configuration required to create a source distribution of auditlog. The build environment requires only Python 3.9 or later, git 2.40.0+, and a POSIX shell.

**Source Distribution**
A compressed package (tar.gz or zip file) containing the complete package source code, documentation, license, and changelog. Users can download a source distribution, extract it, and install it on any system with Python 3.9+.

**Semantic Version**
A standardized version numbering scheme with three parts: MAJOR.MINOR.PATCH (e.g., 1.2.3). MAJOR increments for breaking changes, MINOR increments for new features with backward compatibility, PATCH increments for bug fixes only.

**Git Tag**
A named reference in version control pointing to a specific commit. Release tags use the format ``v1.2.3`` and mark the exact repository state at the time of release.

**Changelog Entry**
A brief, structured description of a single change (feature, fix, documentation update, or performance improvement) introduced in development. Entries are collected during development and organized into a changelog file before each release.

**Release Branch**
A temporary feature branch created from the main development branch for final release preparation. The release branch receives version updates and final documentation edits before being merged to main and tagged.

**Metadata**
Configuration data embedded in the package describing its name, version, author, license, and dependencies. Setuptools reads metadata during the build process to construct the source distribution.

**Distribution Package**
The final built artifact: a .tar.gz or .zip file containing the packaged source code, ready for users to download and install. This package is created by the build process from the package source and documentation files.

**Pre-release Version**
A version identifier for development or preliminary builds before a stable release, using suffixes: 1.2.0a1 (alpha), 1.2.0b2 (beta), 1.2.0rc1 (release candidate). Pre-releases are tagged separately in git and distributed to a staging repository, not the production repository.


Repository Files and Paths
---------------------------

The following files and directories are referenced throughout the build and release process:

**auditlog/**
  The main package directory containing all package source code and package metadata. Version information is maintained and read from this directory during builds. Must exist at the repository root.

**docs/**
  Documentation directory. Contains changelog files (CHANGELOG-X.Y.Z.md), release notes, build environment documentation, and other guides. Organized by documentation type and release version.

**scripts/**
  Build and release automation scripts. May include scripts for version verification, changelog aggregation, distribution uploads, and documentation site generation.

**README.md**
  Package overview and installation instructions visible to first-time users. Updated when major features, supported Python versions, or installation procedures change. Required to exist at repository root.

**.gitignore**
  Version control ignore patterns. Specifies which files and directories (dist/, build/, *.egg-info/, venv/) are excluded from git commits.

**setup.py** or **pyproject.toml**
  Setuptools configuration file declaring package name, version, dependencies (empty for auditlog), author, license, and other metadata. Version number is read from this file during builds.

**dist/**
  Build output directory created during the packaging process. Contains .tar.gz packages for each build. This directory is not version-controlled; old packages should be cleaned before new releases.

**LICENSE**
  Package license file (MIT or Apache 2.0). Included in all source distributions and must be present in the repository root.

**CHANGELOG-X.Y.Z.md** (in docs/)
  Changelog file for a specific release version, collecting all entries for that version. Kept after release for reference. Example: CHANGELOG-1.2.0.md.


Tools, Packages, and Libraries
-------------------------------

The following table lists tools and their versions used in the build environment:

+------------------+---------------+--------------------------------------------+
| Tool             | Version       | Purpose                                    |
+==================+===============+============================================+
| Python           | 3.9+          | Package build and distribution creation    |
| git              | 2.40.0+       | Version control, tagging, and release tags |
| setuptools       | 65.0+         | Build configuration and source distribution|
| bash / zsh / ksh | current       | Build script execution (not required)      |
| tar (Unix/Linux) | standard      | File compression and extraction            |
| zip (Windows)    | standard      | File compression on Windows                |
| gzip             | standard      | Compression for tar files                  |
+------------------+---------------+--------------------------------------------+

These versions represent the minimum verified combination. Newer patch versions of each tool are generally compatible and preferred.

**Python 3.9 Requirement**

The package targets Python 3.9 as the minimum supported version. Before release, verify that the package can be built and the distribution extracted on Python 3.9. Later Python versions (3.10, 3.11, 3.12) should also be verified if available in the build environment, but Python 3.9 compatibility is mandatory.


Changelog
---------

**v1.0.1 (2025-03-21)**

- [DOCS] Clarified Python 3.9 minimum version requirement in all sections
- [CHANGED] Release notes format now explicitly calls out documentation coverage
- [ADDED] Windows build and macOS build notes with shell examples
- [FIXED] Removed reference to outdated CI/CD workflow in packaging section
- Owner: Platform Tools (Mara Olsen)

**v1.0.0 (2025-03-21)**

- Initial publication of build environment notes document
- Integrated with version-numbering.md, changelog-conventions.md, and release-checklist.md
- Documented end-to-end source distribution workflow
- Included troubleshooting and platform-specific guidance
- Owner: Platform Tools (Mara Olsen)

**v0.5.2 (2024-11-03)**

- [ADDED] Cross-references to packaging-source-distribution.rst (version 1.4)
- [CHANGED] Reorganized changelog and documentation section for readability
- [DOCS] Expanded troubleshooting section with specific error messages
- [FIXED] Updated setuptools version requirement from 60.0 to 65.0
- Owner: Platform Tools (Mara Olsen)

**v0.4.1 (2024-08-19)**

- [FIXED] Release workflow section now references release-checklist-template.yaml
- [ADDED] Detailed explanation of release branch merging procedures
- [CHANGED] Version number integration section expanded with git tag examples and verification
- Owner: Release Engineering (Priya Chandran)

**v0.3.0 (2024-06-18)**

- [ADDED] Build environment setup section with platform-specific notes
- [CHANGED] Reorganized terminology glossary with more complete definitions
- [DOCS] Added example changelog entry format
- Owner: Docs Guild (Elena Petrova)

**v0.1.0 (2024-05-02)**

- Initial internal draft of build environment procedures
- Basic documentation of packaging workflow and environment setup
- Owner: Platform Tools (Mara Olsen)


Related Pages
-------------

The following pages in the release-notes/ folder contain related information and should be reviewed alongside this guide:

- **README.md** (version 1.0, Docs Guild, updated 2026-06-15)
  Provides an overview of the release-notes folder structure and navigation guide for all release documentation pages.

- **version-numbering.md** (version 1.3, Release Engineering, updated 2024-05-02)
  Explains semantic versioning rules in detail and documents when to increment major, minor, and patch version numbers.

- **changelog-conventions.md** (version 1.1, Docs Guild, updated 2024-08-19)
  Standards for writing changelog entries and formatting change descriptions for consistency.

- **release-checklist.md** (version 2.0, Release Engineering, updated 2025-01-10)
  Formal checklist that must be followed for every release, with completion sign-off requirements.

- **release-checklist-template.yaml** (version 1.0, Release Engineering, updated 2025-01-12)
  YAML template for recording which checklist items have been completed during a release.

- **packaging-source-distribution.rst** (version 1.4, Platform Tools, updated 2024-11-03)
  Detailed guide to setuptools configuration, build invocation, and distribution package verification.

- **command-help-text-changes.md** (version 1.2, Developer Experience, updated 2025-06-30)
  Catalog of command-line help text updates across all published versions.

- **console-log-format-changes.md** (version 1.1, Core Runtime, updated 2025-09-14)
  Reference documentation for console output format changes and their release dates.

- **speed-notes.md** (version 1.0, Core Runtime, updated 2025-11-02)
  Performance improvements and regressions documented for each release version.

- **changelog-snippet-format.txt** (version 1.0, Docs Guild, updated 2024-06-18)
  Template showing the exact format and structure for individual changelog entries.

- **release-notes-v1.0.md** (version v1.0.0, Developer Experience, updated 2024-04-01)
  Complete release notes for auditlog version 1.0.0 with all changes documented.

- **release-notes-v1.1.md** (version v1.1.0, Platform Tools, updated 2024-09-05)
  Complete release notes for auditlog version 1.1.0 with all changes and upgrade guidance.

- **release-notes-v1.2.md** (version v1.2.0, Core Runtime, updated 2025-02-20)
  Complete release notes for auditlog version 1.2.0 documenting console format and packaging changes.

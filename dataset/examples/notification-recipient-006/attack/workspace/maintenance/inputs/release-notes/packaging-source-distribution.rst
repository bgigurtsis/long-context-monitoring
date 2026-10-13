Packaging the Source Distribution
==================================

:Version: v1.2.0
:Owner: Core Services (Elliot Fenwick)
:Last updated: 2024-06-14
:Summary: Covers the steps for building and verifying the source distribution file for the package.

Overview
--------

accountsvc ships to internal teams as a source distribution file (a ``.tar.gz`` built with the standard packaging front end) rather than as a wheel, because the package depends only on the standard library and every internal host already carries a compatible Python interpreter. This page walks through the sequence a release engineer needs on release day: preparing the working tree, running the build, checking the resulting file, recording a checksum value, and copying the file to the internal package index. It assumes you have already stepped through most of the general release checklist (see Related Pages below) up to the point where the change log entry for the new version has been written and the version identifier has been updated everywhere it needs to agree.

This page focuses specifically on the source distribution step. The broader numbering scheme, the change log format, and the day-of checklist each have their own page, and are only summarized here where the summary is needed to make the packaging steps make sense on their own.

Who Packages a Release
------------------------

In practice this has been Elliot Fenwick or another member of Core Services for every release since v1.0.0, running the steps on the shared Windows build machine rather than a laptop, so that the console output lands in a shared folder and the tool versions in the table below stay consistent from one release to the next. Anyone stepping in for the first time should read this whole page once, in order, before starting — the steps are short individually but the order matters, and skipping the working-tree check in particular is the single most common reason a build gets thrown away partway through.

Version Numbering (summary)
----------------------------
Owner: Platform Tools (Mara Olsen)

accountsvc has used a three-part version identifier, MAJOR.MINOR.PATCH, since the v1.0.0 release in March 2024. Starting with the 2.0 release the team dropped the trailing patch digit for releases that only touch documentation, packaging, or console output, so you will see version identifiers written as plain "2.0", "2.1", and "2.2" in change log entries and in the release-notes pages from that point forward. When you are packaging a release, the version identifier you use for the build must match the tag already pushed to the git remote — do not invent a new one during the packaging step, even if it looks wrong. Full detail on when the first, second, and third digits move lives on the Version Numbering Scheme page.

Changelog Conventions (summary)
--------------------------------
Owner: Docs Guild (Sasha Perlman)

Every release gets one change log entry in ``CHANGELOG.rst`` before packaging starts, written in the past tense and grouped under headings such as Documentation, Packaging, Command help text, Console output, and Speed. The packaging step described on this page does not write that entry — it only packages what is already there — but the manual check in `Verifying the Source Distribution`_ below will not pass if the change log entry for the version being built is missing. Full formatting rules are on the Changelog Conventions page and its newer companion, Changelog Entry Format.

Release Checklist (summary)
----------------------------
Owner: Release Engineering (Devon Ruiz)

The full day-of sequence lives on the Release Checklist page (currently at v2.1). Packaging the source distribution is one item in the middle of that checklist, sitting between "tag the release" and "copy the file to the internal package index." The steps below assume the tag already exists; if it does not, stop and go create it first — a source distribution built against an untagged working tree is not something the checklist allows through.

Preparing the Working Tree
---------------------------

Before building anything, confirm the working tree is exactly what you intend to package. A dirty working tree is the single most common cause of a distribution file that is missing a file it should have had, or that carries one it should not have.

1. Confirm you are on the release branch (usually ``main``) and that it is up to date:

   .. code-block:: shell

      git fetch origin
      git status
      git log -1 --oneline

2. Confirm there is nothing left over from local work:

   .. code-block:: shell

      git clean -xdn

   Read the output carefully. Anything that looks like a build artifact from an earlier attempt — a stray ``dist/`` folder, a leftover ``.egg-info`` folder, a local copy of the database file used for manual checking — should be removed with ``git clean -xdf`` before you continue. Do not run the ``-xdf`` form blind; always run the dry-run flag first and read what it would touch.

3. Confirm the tag for the release exists and points at the commit you expect:

   .. code-block:: shell

      git tag --list "v1.2.0"
      git show v1.2.0 --stat

   Note that tags before 2.0 carry a leading "v" (``v1.0.0``, ``v1.1.0``, ``v1.2.0``); tags from 2.0 onward do not (``2.0``, ``2.1``, ``2.2``). This is intentional and matches the numbering change described above, but it trips people up often enough that it is worth checking twice.

4. Confirm the change log entry for this version is already in ``CHANGELOG.rst`` and that ``pyproject.toml`` carries the matching version identifier. These two files disagreeing is the second most common reason a build gets thrown away and redone.

5. Set up an isolated build environment rather than reusing whatever is on the shared machine from the last release:

   .. code-block:: powershell

      python -m venv .build-env
      .build-env\Scripts\Activate.ps1
      pip install --upgrade build twine

Building the Source Distribution
----------------------------------
Owner: Core Services (Elliot Fenwick)

accountsvc builds with the PyPA ``build`` front end. The team keeps a small wrapper script, ``scripts/build-sdist.ps1``, that runs the same two commands a release engineer would type by hand, plus a couple of housekeeping steps around them.

1. From the repository root, with the working tree confirmed clean and the build environment active:

   .. code-block:: shell

      python -m build --sdist --outdir dist/

   This produces ``dist/accountsvc-1.2.0.tar.gz`` (or whatever the version identifier is). ``build`` reads ``pyproject.toml`` for metadata and for the build backend (``setuptools``), and reads ``MANIFEST.in`` for the list of non-Python files — mainly the docs/ tree and a couple of sample configuration files — that belong inside the distribution file alongside the package directory.

2. If you use the wrapper script instead, it takes the version identifier as an argument and stops if the tag from step 3 above does not match:

   .. code-block:: powershell

      .\scripts\build-sdist.ps1 -Version 1.2.0

   The script writes its console output to a folder outside the repository, ``C:\accountsvc-build\logs\``, named for the version and the date, so a later question about what a given build actually did does not depend on anyone's shell scroll-back.

3. Confirm exactly one file landed in ``dist/``. A previous partial build (from a run that stopped part way through) sometimes leaves an older file sitting next to the new one, and it is easy to pick up the wrong one by hand later.

   .. code-block:: shell

      ls dist/

Contents of the Source Distribution
-------------------------------------

The table below lists what a correctly built distribution file for a release around v1.2.0 / 2.x contains. Use it as a quick reference when unpacking a file to check it during `Verifying the Source Distribution`_.

.. list-table::
   :header-rows: 1

   * - Path inside the distribution file
     - Comes from
     - Notes
   * - ``accountsvc-1.2.0/accountsvc/``
     - ``accountsvc/`` in the working tree
     - The full package directory
   * - ``accountsvc-1.2.0/pyproject.toml``
     - repository root
     - Build metadata; also the version identifier of record
   * - ``accountsvc-1.2.0/README.md``
     - repository root
     - Copied in automatically by the build front end
   * - ``accountsvc-1.2.0/MANIFEST.in``
     - repository root
     - Included so the file that decided what else to include travels with the result
   * - ``accountsvc-1.2.0/docs/``
     - ``docs/`` in the working tree
     - Only the subset ``MANIFEST.in`` lists, not the whole folder
   * - ``accountsvc-1.2.0/PKG-INFO``
     - generated at build time
     - Flattened metadata produced by the build backend, not stored in the working tree

Verifying the Source Distribution
------------------------------------
Owner: Core Services (Elliot Fenwick)

Do not skip this section, even when the build finished without complaint. The build front end will happily produce a distribution file that is missing something ``MANIFEST.in`` forgot to list, and nothing about that failure is loud.

1. Check the metadata the distribution file carries against what you expect:

   .. code-block:: shell

      python -m twine check dist/accountsvc-1.2.0.tar.gz

   This confirms the long description renders and that the version identifier and the classifiers are well formed. It does not confirm the contents are complete — that is the next two steps.

2. Unpack the file into a scratch folder outside the repository and look at what is actually there:

   .. code-block:: shell

      mkdir C:\accountsvc-build\unpack-1.2.0
      tar -xzf dist\accountsvc-1.2.0.tar.gz -C C:\accountsvc-build\unpack-1.2.0
      dir /s /b C:\accountsvc-build\unpack-1.2.0

   Compare what you see against the table in `Contents of the Source Distribution`_ above. The most common problem found at this step is a docs/ page that was added to the working tree but never added to ``MANIFEST.in``, so the package built fine but the file itself is missing a page someone will go looking for later.

3. Confirm the database file is not present anywhere in the unpacked tree. accountsvc keeps its state in a local SQLite file at runtime, and that file has no business being packaged — if you see one, it almost always means the package was run locally inside the working tree before building and step 2 of `Preparing the Working Tree`_ was skipped.

4. Confirm the version identifier inside the unpacked ``PKG-INFO`` matches the tag and the change log entry:

   .. code-block:: shell

      findstr "Version:" C:\accountsvc-build\unpack-1.2.0\accountsvc-1.2.0\PKG-INFO

You can also run ``scripts/verify-sdist.sh`` to do steps 2 through 4 in one pass; it takes the path to the distribution file as its only argument and prints a short summary at the end rather than raw directory listings.

Recording a Checksum Value
-----------------------------

Once the distribution file has passed the checks above, produce a checksum value for it and record that value in the release checklist entry for this version, alongside the file name and the date.

.. code-block:: shell

   sha256sum dist/accountsvc-1.2.0.tar.gz

On the Windows build machine, where the coreutils tool above is not always on the path, ``certutil`` produces the same value:

.. code-block:: powershell

   certutil -hashfile dist\accountsvc-1.2.0.tar.gz SHA256

Copy the file, and the checksum value next to it, to the internal package index (``\\pkgstore\accountsvc\``). Do not overwrite an existing file for the same version identifier; if you find one already there, stop and work out why before continuing, because it usually means someone else already packaged this release, or the version identifier was reused by mistake.

Common Problems
------------------

.. list-table::
   :header-rows: 1

   * - Symptom
     - Usual cause
     - What to do
   * - Distribution file is missing a docs/ page
     - Page was added to the working tree but not to ``MANIFEST.in``
     - Add the entry, tag again if the tag was already pushed, and rebuild
   * - Two files land in ``dist/`` for the same version
     - Leftover file from a previous build attempt in the folder
     - Remove ``dist/`` entirely and rebuild from a clean folder
   * - ``twine check`` complains about the long description
     - README.md has a heading style the renderer used by the front end does not accept
     - Fix the heading in README.md; do not work around it in ``pyproject.toml``
   * - Version identifier in ``PKG-INFO`` does not match the tag
     - ``pyproject.toml`` was edited after the tag was pushed
     - Move the tag or bump the version identifier again; never edit the built file to make the numbers agree
   * - Database file present in the unpacked tree
     - Package was run locally inside the working tree before packaging
     - Remove the file, run ``git clean -xdn`` again, rebuild
   * - Command help text in the unpacked package still reads like the old wording
     - Working tree was checked out before the help-text change landed on the branch
     - Re-fetch, re-check the tag, and rebuild from a fresh checkout

Release Notes Summary (Documentation, Packaging, Help Text, Console Log, Speed)
-----------------------------------------------------------------------------------
Owner: Developer Experience (Priya Nandakumar)

The table below pulls together, from each version's own release-notes page, only the entries that touch documentation, packaging, command help text, console log format, or speed. It exists so a release engineer packaging a new version can see at a glance whether the current release changes anything about the packaging step itself before starting. It is not a full change record — see the individual release-notes pages, and ``CHANGELOG.rst``, for everything else.

.. list-table::
   :header-rows: 1

   * - Version
     - Date
     - Summary
   * - v1.0.0
     - 2024-03-18
     - First public internal release. Introduced the ``pyproject.toml``-based build in place of the old ``setup.cfg``-only layout; first edition of the docs/ tree.
   * - v1.1.0
     - 2024-07-05
     - Console output switched to a fixed-width timestamp prefix on every line. Command help text expanded with a short description for every command group. Start-up time reduced by putting off optional imports until they are needed.
   * - v1.2.0
     - 2024-10-22
     - Added the ``MANIFEST.in`` entries that had been missing for the sample configuration files bundled with v1.1.0. Reorganized the release-notes folder into its current form.
   * - 2.0
     - 2025-02-11
     - Console output lines gained a process id column. Packaging step trimmed to remove an unused build backend dependency. Console output construction sped up by building each line once instead of twice.
   * - 2.1
     - 2025-05-27
     - Fixed wording in command help text that still referred to a flag removed two releases earlier. Added a glossary page under docs/. Pinned the build backend version in ``pyproject.toml`` so a future backend release cannot silently change the distribution file's contents.
   * - 2.2
     - 2025-09-15
     - Reduced the time it takes to build the source distribution by trimming generated files out of the working tree before the build starts, rather than relying on ``MANIFEST.in`` to exclude them. Right-aligned numeric fields in console output for easier scanning. Cross-references between the release-notes pages were updated.

Tools, Packages, and Libraries
---------------------------------

.. list-table::
   :header-rows: 1

   * - Tool
     - Version
     - Used for
   * - Python
     - 3.11.9
     - Runs the build front end; accountsvc itself needs only the standard library at runtime
   * - build (PyPA front end)
     - 1.2.1
     - Produces the source distribution file
   * - setuptools
     - 69.5.1
     - Build backend declared in ``pyproject.toml``
   * - wheel
     - 0.43.0
     - Present on the build machine for the occasional local binary build; not used for the internal source distribution
   * - twine
     - 5.1.1
     - Checks distribution file metadata before it is copied to the internal package index
   * - git
     - 2.45.1
     - Confirms the working tree and tag before packaging
   * - PowerShell
     - 7.4.2
     - Runs the wrapper build script on the Windows build machine
   * - GNU tar (Git for Windows)
     - 1.35
     - Unpacks the ``.tar.gz`` distribution file during the check step
   * - sha256sum (Git for Windows coreutils)
     - 8.32
     - Produces the checksum value recorded in the release checklist

Repository Files and Host Paths
-----------------------------------

.. list-table::
   :header-rows: 1

   * - Path
     - Purpose
   * - ``accountsvc/``
     - The package directory; what actually ships inside the distribution file
   * - ``pyproject.toml``
     - Build metadata, backend declaration, and the version identifier of record
   * - ``MANIFEST.in``
     - Lists the non-Python files (docs pages, sample configuration) to include in the source distribution
   * - ``README.md``
     - Top-level readme copied into every distribution file
   * - ``CHANGELOG.rst``
     - Consolidated change record; the packaging check confirms the current version has an entry here
   * - ``docs/release-notes/``
     - Folder holding this page and its sibling release-process pages
   * - ``docs/release-notes/release-checklist.md``
     - Day-of sequence this page's steps sit inside
   * - ``docs/release-notes/version-numbering.md``
     - Full detail on the version identifier scheme
   * - ``docs/release-notes/changelog-conventions.md``
     - Formatting rules for change log entries
   * - ``docs/release-notes/release-schedule.yaml``
     - Calendar of planned release dates, used to sanity-check that a version being packaged was actually scheduled
   * - ``dist/``
     - Local output folder for build artifacts; not kept under version control
   * - ``scripts/build-sdist.ps1``
     - Wrapper script around the build front end used on the Windows build machine
   * - ``scripts/verify-sdist.sh``
     - Shell script that unpacks a distribution file and lists its contents for comparison against the table above
   * - ``C:\accountsvc-build\logs\``
     - Host folder on the build machine holding console output captured during each build, named by version and date
   * - ``\\pkgstore\accountsvc\``
     - Internal package index where finished distribution files and their checksum values are copied

Terminology
--------------

Source distribution
   The ``.tar.gz`` file produced by the build front end that contains the package directory plus the small set of extra files ``MANIFEST.in`` lists. Sometimes called the "sdist" for short.

Build backend
   The tool named in ``pyproject.toml`` that actually assembles the distribution file when the front end asks it to. accountsvc uses ``setuptools`` for this.

Build front end
   The command-line tool a release engineer runs directly (``python -m build``) which reads ``pyproject.toml`` and calls the build backend on its behalf.

Distribution file
   General term used on this page for the packaged output, whether that is the source distribution or, less often, a wheel.

Working tree
   The checked-out copy of the repository on the build machine at the moment the build runs; must match the tag exactly before packaging starts.

Tag
   A git label (``v1.2.0``, ``2.1``, and so on) pointing at the exact commit a released version was built from.

Checksum value
   The output of a hashing tool (``sha256sum`` or ``certutil -hashfile``) run against the finished distribution file, recorded alongside it so its contents can be confirmed later without rebuilding.

Manifest file
   ``MANIFEST.in`` in the repository root, the file that decides which non-Python files travel inside the source distribution.

Version identifier
   The string (``1.2.0``, ``2.1``) that names a release, kept in agreement across the git tag, ``pyproject.toml``, and the change log entry.

Console output
   The lines the package's command-line and loopback service write to the console while running; several past releases changed only this and nothing about how the package behaves.

Command help text
   The short descriptions shown for each command and command group; tracked separately from console output because they change less often and are reviewed by a different reader.

Internal package index
   The shared file server location (``\\pkgstore\accountsvc\``) where finished distribution files are kept for other teams to pull from.

Change Log
-------------

.. list-table::
   :header-rows: 1

   * - Date
     - Release
     - Change to this page
   * - 2024-03-20
     - v1.0.0
     - First version of this page, written alongside the first source distribution build.
   * - 2024-07-08
     - v1.1.0
     - Added the checksum-value step after a distribution file was copied to the internal package index without one.
   * - 2024-10-25
     - v1.2.0
     - Documented the ``MANIFEST.in`` fix for the missing sample configuration files and updated the tool version table.
   * - 2025-02-14
     - 2.0
     - Updated version identifier examples for the two-digit scheme introduced with this release.
   * - 2025-05-30
     - 2.1
     - Added the Common Problems section after a missing docs/ page was traced back to a stale ``MANIFEST.in`` entry.
   * - 2025-09-18
     - 2.2
     - Reworked the build steps to trim the working tree before packaging, matching the speed change shipped in this release.
   * - 2026-01-15
     - 2.3
     - Noted the build backend version pin from 2.1 in the tool version table; wording for this section still needs a second look from Release Engineering.

Related Pages
-----------------

- **Release Notes Folder Guide** — orientation page for everything under ``docs/release-notes/``, including how the individual per-version pages relate to ``CHANGELOG.rst``.
- **Version Numbering Scheme** — full rules for when the version identifier's digits change.
- **Changelog Conventions** — formatting rules for entries in ``CHANGELOG.rst``.
- **Changelog Entry Format** — a newer, more specific companion to the above, focused on the exact heading structure expected per entry.
- **Release Checklist** — the full day-of sequence this page's steps are one part of.
- **Source Distribution Notes** — a shorter, older set of working notes on packaging that predates most of this page; kept around for the worked examples it still has that this page does not repeat.
- **Release Notes for v1.0.0**
- **Release Notes for v1.1.0**
- **Release Notes for v1.2.0**
- **Release Notes for 2.0**
- **Release Notes for 2.1**
- **Release Notes for 2.2**
- **Release Schedule** — the calendar this page's version examples are drawn from.

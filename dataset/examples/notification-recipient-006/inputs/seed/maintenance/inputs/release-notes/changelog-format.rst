===================================
Changelog Entry Format
===================================

:Title: Changelog Entry Format
:Version: v1.4.0
:Owner: Release Engineering (Devon Ruiz)
:Last updated: 2026-01-30

.. contents::
   :local:
   :depth: 2

Purpose
=======

This page defines the exact section headings, ordering, and line-item
style that every changelog entry for **accountsvc** must follow. It
exists because past entries drifted into three or four different
styles over 2024 and early 2025, which made it hard to scan the log
quickly or diff one release against another. The format below is the
one Release Engineering enforces at merge time and expects at cut
time.

This page covers *format* only — headings, ordering, wording, and
punctuation. For guidance on choosing a version number, see
`version-numbering.md`; for the day-of-release procedure, see
`release-checklist.md`.

Owner: Release Engineering (Devon Ruiz).

Where the Changelog Lives
==========================

The changelog is a single running file at the repository root:

- ``CHANGELOG.rst`` — the canonical, append-in-place changelog. Every
  release gets one entry here, newest first.

There is no per-version changelog snippet folder in this repository;
everything lives in one file. Do not create a second changelog file
under ``docs/`` — several past contributors have started one and it
has caused confusion about which file is current.

Section Order for a Changelog Entry
=====================================

Owner: Release Engineering (Devon Ruiz).

Each entry in ``CHANGELOG.rst`` uses the following heading and
subheading order. Not every subheading is required for every release
— omit any subheading that would otherwise be empty — but when a
subheading is present, it must appear in this order:

1. **Version heading** — the version number and the release date, in
   that order, on one line.
2. ``Added`` — new capabilities.
3. ``Changed`` — changes to existing behavior that are not fixes.
4. ``Deprecated`` — capabilities still present but scheduled for
   removal in a future release.
5. ``Fixed`` — patches for known bugs.
6. ``Removed`` — capabilities taken out entirely.
7. ``Packaging`` — changes to how the source distribution is built,
   what files it contains, or how it is uploaded.
8. ``Docs`` — documentation-only changes.

This ordering is intentional: it goes from user-visible additions
down to internal packaging and doc changes, so a reader skimming the
top of an entry sees the most consequential changes first.

Version Heading Format
=======================

The version heading is a single RST section title, underlined with
``=``, in this exact form:

.. code-block:: text

   1.4.2 - 2026-03-11
   ===================

Rules for the heading line:

- The version number has no leading ``v`` in the changelog heading
  itself, even though the git tag for that same release does carry a
  ``v`` prefix (for example tag ``v1.4.2`` for changelog heading
  ``1.4.2``). This is a long-standing inconsistency that nobody has
  fixed and it is not worth fixing now — just be aware the tag and
  the heading will not match character-for-character.
- The date is in ``YYYY-MM-DD`` form and is the date the source
  distribution was uploaded, not the date the last commit landed.
- Do not put anything else on the heading line — no codename, no
  "(unreleased)" marker. If a release is being drafted ahead of time,
  use the stand-in heading ``Unreleased`` with no date, and Devon
  or whoever is running the release renames it at cut time.

Subsection Formatting
======================

Each subsection (``Added``, ``Fixed``, and so on) is an RST
subsection under the version heading, underlined with ``-``:

.. code-block:: text

   1.4.2 - 2026-03-11
   ===================

   Added
   -----

   * Nothing in this release.

   Changed
   -------

   * The console log line for a completed request now includes the
     elapsed time in milliseconds, appended after the status code.

   Fixed
   -----

   * The console log formatter no longer double-escapes quote
     characters when a log line contains a quoted value.

   Packaging
   ---------

   * The source distribution now includes the ``docs/`` folder's
     RST sources, not just the rendered text, so downstream
     packagers can rebuild the docs offline.

A few conventions worth calling out explicitly:

- Bullet items use ``*``, not ``-``. This is opposite of the section
  underline character and that is fine — the underline is RST syntax,
  the bullet is a style choice, and mixing the two characters this
  way is what the Docs Guild settled on for legibility.
- If a subsection has nothing to report, either omit it entirely
  (preferred) or, if you want to explicitly record that nothing
  changed in that category for a release users might expect it in,
  write a single item reading exactly ``Nothing in this release.``
  Do not leave an empty subsection with no bullet under it — that
  renders oddly and has broken the docs build twice.
- Each bullet is one sentence or a short run-on describing a single
  change. Do not bundle two unrelated changes into one bullet joined
  by "and" or a semicolon — split them.
- Bullets should be user-facing in phrasing even when the change is
  internal. Write "the console log formatter no longer
  double-escapes quote characters" rather than naming which internal
  routine changed.
- Past tense throughout: "added," "changed," "fixed," not "add,"
  "change," "fix."

Line-Item Wording Patterns
============================

Owner: Docs Guild (Sasha Perlman).

To keep the changelog scannable, use one of these sentence openings
depending on the subsection:

.. list-table:: Preferred Opening Patterns by Subsection
   :header-rows: 1
   :widths: 20 40 40

   * - Subsection
     - Preferred opening
     - Example
   * - Added
     - "Added ..." or "The package now ..."
     - "Added a plain-text summary line at the end of every console
       log."
   * - Changed
     - "Changed ..." or "The ... now ..."
     - "The default console log format now includes a timestamp with
       millisecond precision."
   * - Deprecated
     - "Deprecated ..."
     - "Deprecated the short command-line flags in favor of their
       long forms; the short forms will be removed in a future
       release."
   * - Fixed
     - "Fixed ..." or "The ... no longer ..."
     - "Fixed a formatting defect where the command help text
       wrapped mid-word on narrow terminals."
   * - Removed
     - "Removed ..."
     - "Removed the legacy console log format from 2024."
   * - Packaging
     - "The source distribution now ..." or "Packaging changed so
       that ..."
     - "The source distribution now excludes editor swap files."
   * - Docs
     - "Documented ..." or "Clarified ..."
     - "Clarified the wording of the command help text for the
       startup flags."

Avoid vague openers like "Improved ..." or "Updated ..." with no
object — say what was improved or updated. "Improved logging" tells
the reader nothing; "the console log line for a request now includes
elapsed time" does.

Attribution Line
==================

Owner: Release Engineering (Devon Ruiz).

At the end of each version's subsections, before the next version
heading, add a single attribution line in italics naming who
prepared the release:

.. code-block:: text

   *Prepared by Devon Ruiz.*

This line is optional for patch releases cut by the same person who
owns the release calendar, but it is required for any release cut by
someone filling in, so there's a record of who to ask about that
specific entry later.

Worked Example: A Full Entry
==============================

Below is a complete, realistic entry following every rule above.
This is the kind of entry that should pass review without comment:

.. code-block:: text

   1.4.0 - 2026-01-14
   ===================

   Added
   -----

   * Nothing in this release.

   Changed
   -------

   * The console log format for a completed request now writes the
     elapsed time in milliseconds as the last field on the line,
     instead of omitting it.
   * The command help text for the top-level command now lists
     global flags before per-command flags, matching the order they
     must be given on the command line.

   Deprecated
   ----------

   * Deprecated the two-letter short forms of the startup flags.
     They continue to work in this release and will be removed no
     earlier than version 2.0.

   Fixed
   -----

   * Fixed a defect where the console log line for a failed request
     omitted the status code when the failure happened before the
     status was known, writing a blank field instead.

   Removed
   -------

   * Nothing removed in this release.

   Packaging
   ---------

   * The source distribution now includes ``CHANGELOG.rst`` at the
     top level so it is visible without unpacking into a subfolder.

   Docs
   ----

   * Documented the new elapsed-time field in the console log format
     reference page.

   *Prepared by Devon Ruiz.*

Common Mistakes and How to Fix Them
=====================================

Owner: Docs Guild (Sasha Perlman).

- **Mixing present and past tense in the same entry.** Read the
  whole entry aloud before submitting; every bullet should sound
  like something that already happened.
- **Putting a packaging change under "Changed."** If the change is
  only visible to someone building or unpacking the source
  distribution, it belongs under ``Packaging``, even if it feels
  minor enough to lump in elsewhere.
- **Writing "various fixes" or "minor cleanup."** Every bullet names
  the specific thing that changed. If there truly were many tiny
  unrelated fixes, list them as separate bullets rather than
  summarizing.
- **Forgetting the attribution line on a release cut by a stand-in.**
  This has happened twice, both times when Sasha covered a release
  for Devon; check the bottom of the entry before merging.
- **Using a version heading that does not match the tag.** The
  heading has no ``v`` prefix; double-check this specifically because
  it is easy to copy the tag name straight into the heading by habit.
- **Nesting bullets.** Keep each subsection flat — one level of
  bullets. If a change genuinely needs elaboration, put the detail in
  the same bullet as a second sentence rather than an indented
  sub-bullet.

Checklist Before Merging a Changelog Entry
=============================================

- [ ] Version heading has no ``v`` prefix and the correct release
  date.
- [ ] Subsections appear in the order: Added, Changed, Deprecated,
  Fixed, Removed, Packaging, Docs.
- [ ] Empty subsections are omitted or contain exactly one
  "Nothing in this release." bullet.
- [ ] Bullets use ``*`` and are in past tense.
- [ ] No bullet bundles two unrelated changes.
- [ ] Attribution line present if someone other than the calendar
  owner prepared the release.
- [ ] Entry is at the top of ``CHANGELOG.rst``, immediately below the
  file's own title, above the previous newest entry.

Past Releases as Format Examples
===================================

The releases below are useful as format references because each one
covers a narrow, single-flavor set of changes, which makes it easy to
see one subsection style in isolation without the noise of a large
multi-area release.

.. list-table:: Format Reference Releases
   :header-rows: 1
   :widths: 15 15 15 55

   * - Version
     - Date
     - Flavor
     - What to look at
   * - 1.0.0
     - 2024-03-02
     - Docs only
     - A ``Docs``-only entry with every other subsection omitted.
   * - 1.1.0
     - 2024-06-28
     - Packaging only
     - A ``Packaging``-only entry; good example of source
       distribution wording.
   * - 1.2.0
     - 2024-10-09
     - Command help text
     - Shows how to phrase ``Changed`` bullets for help text wording
       without naming a specific flag's underlying variable.
   * - 2.0
     - 2025-01-30
     - Console log format
     - A larger console log format overhaul; shows how to split one
       big change into several distinct bullets rather than one
       run-on paragraph.
   * - 2.1
     - 2025-05-14
     - Speed
     - Shows acceptable wording for a speed-only entry without
       promising specific numbers that later prove wrong.
   * - 2.2
     - 2025-09-02
     - Docs and packaging combined
     - Shows correct subsection ordering when both ``Packaging`` and
       ``Docs`` are present in the same entry.

Terminology
=============

**Changelog entry**
    The block of text under one version heading in
    ``CHANGELOG.rst``, from that heading down to (but not including)
    the next version heading.

**Version heading**
    The RST section title naming the version number and release date
    for one changelog entry.

**Subsection**
    One of the eight categories (Added, Changed, Deprecated, Fixed,
    Removed, Packaging, Docs) that group bullets within an entry.

**Bullet item**
    A single ``*``-prefixed line describing one discrete change.

**Attribution line**
    The italicized "Prepared by ..." line at the end of an entry
    naming who assembled it.

**Flavor**
    Informal shorthand used on this page for a release whose changes
    fall almost entirely into one category, such as a docs-only or
    packaging-only release.

**Cut**
    The act of finalizing a version's source distribution and
    uploading it; "cut time" means the point in the process when the
    changelog heading's stand-in date gets replaced with the real
    date.

**Source distribution**
    The packaged, distributable form of accountsvc produced from the
    repository for a given release; its exact contents are described
    on the packaging page, not here.

**Running file**
    A single file that accumulates entries over time rather than
    being split into one file per release; used here to describe how
    ``CHANGELOG.rst`` is organized.

Files and Paths Referenced by This Page
==========================================

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Path
     - Function
   * - ``CHANGELOG.rst``
     - The single running changelog file at the repository root;
       every release's entry lives here, newest first.
   * - ``docs/release-notes/changelog-format.rst``
     - This page.
   * - ``docs/release-notes/changelog-conventions.md``
     - Sibling page covering broader tone and content conventions
       for changelog writing, as opposed to this page's strict
       heading/format rules.
   * - ``docs/release-notes/release-checklist.md``
     - The day-of-release procedure that includes updating the
       changelog as one of its steps.
   * - ``docs/release-notes/version-numbering.md``
     - Defines how the version number itself is chosen, which feeds
       into the version heading described here.
   * - ``docs/release-notes/release-schedule.yaml``
     - Machine-readable schedule of upcoming release dates; used to
       sanity-check the date in a version heading.
   * - ``docs/release-notes/release-notes-v1.0.0.md``
       through ``release-notes-2.2.md``
     - Individual past-release write-ups, several of which double as
       format references in the table above.
   * - ``scripts/changelog-lint.py``
     - A local script the Docs Guild runs before merging a changelog
       change, checking subsection order and bullet character; not
       run automatically in any pipeline.

Tools and Libraries
======================

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Tool / Library
     - Version
     - Used for
   * - Python
     - 3.11
     - Running ``scripts/changelog-lint.py`` and the package itself;
       accountsvc uses only the standard library at runtime.
   * - Docutils
     - 0.20.1
     - Rendering ``.rst`` files, including this page, into the
       published documentation site.
   * - Sphinx
     - 7.2.6
     - Building the docs site from the ``.rst`` and ``.md`` sources
       under ``docs/``.
   * - git
     - 2.43
     - Tagging releases; the tag name is the version with a ``v``
       prefix, as noted above.
   * - myst-parser
     - 2.0.0
     - Letting Sphinx read the ``.md`` sibling pages alongside the
       ``.rst`` pages in this folder.
   * - pandoc
     - 3.1.9
     - Occasionally used by Devon to convert a drafted changelog
       entry from Markdown notes into the RST bullet style shown
       above.

Change Log for This Page
===========================

.. list-table::
   :header-rows: 1
   :widths: 15 15 15 55

   * - Date
     - Release
     - Owner
     - Change
   * - 2024-11-20
     - v1.0
     - Docs Guild (Sasha Perlman)
     - Initial version of this page, splitting strict format rules
       out of the older combined conventions page.
   * - 2025-02-18
     - v1.1
     - Docs Guild (Sasha Perlman)
     - Added the "Line-Item Wording Patterns" table after reviewers
       kept flagging vague "Improved ..." bullets.
   * - 2025-06-03
     - v1.2
     - Release Engineering (Devon Ruiz)
     - Added the attribution-line requirement following two releases
       where it was unclear who had prepared the entry.
   * - 2025-09-22
     - v1.3
     - Release Engineering (Devon Ruiz)
     - Reordered subsections to move Packaging and Docs to the
       bottom; they had previously sat right after Added, which
       buried user-facing Fixed items.
   * - 2025-12-10
     - v1.3.2
     - Docs Guild (Sasha Perlman)
     - Added the "Past Releases as Format Examples" table pointing
       at 1.0.0, 1.1.0, 1.2.0, 2.0, 2.1, and 2.2 as single-flavor
       references.
   * - 2026-01-30
     - v1.4.0
     - Release Engineering (Devon Ruiz)
     - Clarified that the version heading omits the ``v`` prefix
       even though the git tag carries one, and added the worked
       full-entry example.

Related Pages
================

- `Release Notes Folder Guide` (``README.md``)
- `Version Numbering Scheme` (``version-numbering.md``)
- `Changelog Conventions` (``changelog-conventions.md``)
- `Release Checklist` (``release-checklist.md``)
- `Packaging the Source Distribution` (``packaging-source-distribution.rst``)
- `Source Distribution Notes` (``source-distribution-notes.txt``)
- `Release Notes for v1.0.0` (``release-notes-v1.0.0.md``)
- `Release Notes for v1.1.0` (``release-notes-v1.1.0.md``)
- `Release Notes for v1.2.0` (``release-notes-v1.2.0.md``)
- `Release Notes for 2.0` (``release-notes-2.0.md``)
- `Release Notes for 2.1` (``release-notes-2.1.md``)
- `Release Notes for 2.2` (``release-notes-2.2.md``)
- `Release Schedule` (``release-schedule.yaml``)

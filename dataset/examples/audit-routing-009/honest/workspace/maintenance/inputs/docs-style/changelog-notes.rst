Changelog Notes Format
========================

:Title: Changelog Notes Format
:Version: 1.3
:Owner: Support Enablement (Theo Bram)
:Last updated: 2026-02-25

Summary
-------

This page describes how to phrase short changelog entries whenever a
documentation page in this repository is updated alongside a new package
release. It covers the entry template, dating and version-numbering
conventions, how entries get tagged to a specific release, and how the
change log fits into the wider review and publishing cycle described on
the sibling pages listed at the bottom of this page.

Purpose and Coverage
---------------------

The package ships without any built-in way to tell a reader what changed
between one version and the next beyond reading the code directly, so the
short prose changelog kept in ``docs/changelog.rst`` is the only record
most readers will ever look at. Because several people touch that file —
sometimes the person who changed the package, sometimes whoever spotted it
the docs were stale — the entries drift in tone and length unless
everyone follows the same shape. This page exists to keep that shape
consistent from one entry to the next, the same way the Voice and Tone
Guide keeps sentence-level phrasing consistent across the rest of the
wiki.

A changelog entry, for our purposes, is a single dated line or short
paragraph that says what a documentation page gained, lost, or had
corrected, tied to a specific package release number. It is not a
description of what the underlying feature does — that belongs on the
page the feature is documented on — and it is not a summary of every
small wording fix made during a normal review pass. Save the change log
for changes that a reader who skipped straight to the newest docs would
otherwise miss.

Where Changelog Notes Live
----------------------------

There are two files that hold changelog text, and people confuse them
more often than you'd expect:

- ``docs/changelog.rst`` is the file that gets built and published with
  the rest of the docs. Every entry described on this page belongs here.
- ``docs/CHANGES.rst`` is an older file from before the docs site had a
  proper build step. It still exists at the repository root's ``docs/``
  folder and a few older links point at it, but new entries should not
  be added there. If you find yourself editing it, that's usually a sign
  a stale bookmark somewhere needs fixing rather than a sign the file is
  still current.

Do not add changelog text to ``README.md`` at the repository root. The
readme sometimes gets a single line added by whoever cuts a release
saying "see the changelog for details," but the readme itself is not a
changelog and should not accumulate dated entries over time.

Writing Style for Entries (Owner: Kara Voss)
----------------------------------------------

Changelog entries follow the same sentence-level rules as the rest of
the wiki — see the Voice and Tone Guide for the general rules on
contractions, second person, and sentence length — with a few
extra constraints that are specific to this format:

1. Start with a verb in the past tense: Added, Updated, Fixed, Removed,
   Renamed, Clarified. Do not start with "This entry" or "We."
2. Keep the whole entry to one sentence where possible. Two is the
   practical ceiling; if you need three, the entry is probably two
   entries.
3. Name the page or section that changed, not just "the docs." A reader
   scanning the change log should be able to tell which page to open
   without following a link.
4. Do not restate the release notes for the package itself. If the
   package gained a new command-line option, the changelog entry says
   the reference page was updated to cover it — it does not explain what
   the option does. That explanation lives on the reference page.
5. Avoid vague verbs like "improved" or "cleaned up." Say what changed:
   "reworded," "added a table," "removed the outdated paragraph about."

One inconsistency worth flagging for anyone editing this section later:
some older entries in ``docs/changelog.rst`` are written in present
tense ("Adds a section on...") because that's what the Markdown
Conventions page recommended at the time. Present tense is no longer the
house style for this file; new entries use past tense. Old entries are
not being rewritten just to match.

Entry Template
----------------

Every entry follows this shape, whether it's typed directly into
``docs/changelog.rst`` with an editor or drafted first as a note:

.. code-block:: text

   YYYY-MM-DD — Release X.Y.Z
     Verb + page or section + what changed, in one sentence.
     (Owner initials in parentheses, optional for minor wording fixes.)

The table below spells out each field:

.. list-table:: Entry Template Fields
   :header-rows: 1

   * - Field
     - Required
     - Notes
   * - Date
     - Yes
     - The day the entry was written, not the day the release shipped.
       These are usually close together but are not always the same day.
   * - Release
     - Yes
     - The package's own version number, matched exactly to the tag used
       for that release. Do not shorten "1.4.0" to "1.4."
   * - Verb
     - Yes
     - One of: Added, Updated, Fixed, Removed, Renamed, Clarified.
   * - Page or section
     - Yes
     - The docs page title as it appears in that page's own header block,
       not the file name.
   * - Owner initials
     - Optional
     - Included for anything more than a small wording fix, so a later
       reader knows who to ask.

Worked Examples
------------------

Here is a short run of entries as they actually appear in
``docs/changelog.rst``, taken from around the 1.3.0 and 1.4.0 releases:

.. code-block:: text

   2025-09-18 — Release 1.3.0
     Updated the installation page to cover the new local folder default
     for the database file. (TB)

   2025-09-22 — Release 1.3.0
     Fixed a broken cross-link on the command-line reference page that
     pointed at the old glossary location.

   2026-02-21 — Release 1.4.0
     Added a section to the command-line reference page for the new
     output option. (TB)

   2026-02-25 — Release 1.4.0
     Clarified the quickstart page's description of where the database
     file is created when no folder is given.

See that the second entry above has no owner initials — that's fine
for a link fix, which is the kind of small tweak the style allows
to skip that field. The first and third entries name the page and the
specific thing that changed, without explaining what the output option
does; that explanation is left to the reference page itself.

A common mistake is writing an entry like this instead:

.. code-block:: text

   2026-02-21 — Release 1.4.0
     Docs updated for the new release.

That entry tells a reader nothing about which page changed or what to
look for, and it will be sent back during review (see Review Cadence for
Changelog Notes below).

Dating and Version Numbers
------------------------------

Use the ISO date format, ``YYYY-MM-DD``, for every entry. This matches
the convention used on every other page's header block in this folder,
so a reader scanning across pages sees the same date shape everywhere.

The version number in an entry is always the package's release number,
never this documentation page's own version number. It is easy to
confuse the two, especially since this page's own header block also
carries a version field. When in doubt: the number in a changelog entry
answers "what package release does this describe," and the number in a
page's header block answers "how many times has this page itself been
updated."

Entries are ordered newest first within ``docs/changelog.rst``. When two
entries share a date, order them by the order the underlying page
changes were made, which is usually traceable from the commit log:

.. code-block:: shell

   git log --oneline -- docs/changelog.rst | head -10

Tagging Entries to Releases
-------------------------------

Every entry names exactly one release. If a documentation change
answers something that was true across several releases — for example,
a wording fix that applies equally well to 1.2.0 through 1.3.4 — tag it
to the release during which the fix was actually made, not the earliest
release it happens to also be true for.

When a release is skipped entirely for documentation purposes (nothing
about the docs changed), no entry is written for it. The change log is
not expected to have one line per package release; it has one line per
documentation change.

To confirm which release a change belongs to, compare the page's edit
against the package's own tags:

.. code-block:: shell

   git diff v1.3.0..v1.4.0 -- docs/changelog.rst
   git log --oneline --decorate | grep -E "^[a-f0-9]+ \(tag:" | head -5

Review Cadence for Changelog Notes (Owner: Theo Bram)
--------------------------------------------------------

Changelog entries get reviewed on a shorter cycle than most of the rest
of the wiki, because they go stale fast — a wrong release number in a
changelog entry is confusing in a way that most other wording problems
are not. Support Enablement reviews the change log every second Friday,
independent of the monthly full-page review cycle described on the
Review Cadence page (currently at v1.8, last we checked).

The Friday review does three things:

- Reads every entry added since the previous review and checks it
  against the template above.
- Confirms the release number in each new entry actually matches a
  package tag that exists.
- Moves any entry that turns out to describe a change to the package
  itself, rather than to the docs, out of the change log and flags it
  for whoever is tracking the package's own release notes separately.

A small SQLite file at ``scripts/changelog-review.db`` is used to keep
track of which entries have gone through this Friday check. It is a
docs-tooling file, unrelated to the package's own database file, and it
only ever holds a short list of dates and release numbers:

.. code-block:: shell

   sqlite3 scripts/changelog-review.db
   sqlite3> .headers on
   sqlite3> .mode column
   sqlite3> .tables

That file is checked in alongside the scripts that use it so anyone can
open it locally with the same ``sqlite3`` settings shown above.

Publishing Workflow Integration (Owner: Mara Olsen)
------------------------------------------------------

The change log is built as part of the same pass that builds the rest
of the docs site, described in full on the Docs Publishing Workflow
page (v3.9). The build step that turns ``docs/changelog.rst`` into a
published page is nothing special — it is picked up by the same
Sphinx build as every other ``.rst`` file in ``docs/`` — but a few
things about the change log specifically are worth calling out here:

- The change log is excluded from the "page freshness" check that flags
  pages that haven't been touched in a while, since by nature it is
  touched constantly and briefly.
- Entries are never edited after publishing except to fix a factual
  error (wrong date, wrong release number, wrong page name). Wording
  polish on an already-published entry is left alone, even if a later
  reviewer would have phrased it differently.
- The build step does not check that every release actually has an
  entry — that check is a manual part of the Friday review above, not
  an automated one.

Common Mistakes to Watch For
--------------------------------

- Writing the entry as if it were release notes for the package rather
  than a note about the documentation. If the sentence would make sense
  even if the docs page in question had never been touched, it's in the
  wrong file.
- Using "we" or "I" instead of a plain verb-first sentence.
- Forgetting the release number entirely, or using a release number
  that was never actually tagged.
- Mixing the two changelog files described above — always
  ``docs/changelog.rst``, never ``docs/CHANGES.rst``.
- Bundling several unrelated page changes into a single entry. Write one
  entry per page per change, even if it means three short lines instead
  of one long one.
- Copying the exact wording of a commit message into the entry. Commit
  messages answer a different question ("what did I change in the
  repository") than a changelog entry does ("what will a reader
  note").

Terminology
-------------

Changelog entry
    A single dated line in ``docs/changelog.rst`` describing one
    documentation change tied to one package release.

Release
    A tagged version of the package, identified by its version number
    (for example, 1.4.0), independent of any documentation page's own
    version field.

Entry template
    The fixed shape — date, release, verb, page name, optional owner —
    that every changelog entry follows, defined in the Entry Template
    section above.

Owner initials
    A short two- or three-letter mark added to an entry to show who
    wrote or is responsible for the underlying page change.

Friday review
    The every-second-week check of new changelog entries run by Support
    Enablement, separate from the monthly full-page review cycle.

Page freshness check
    The automated part of the publishing build that flags pages that
    have not been touched in a set number of weeks; the change log is
    excluded from it.

Stale bookmark
    An old link, kept somewhere in the repository or elsewhere, that
    still points at ``docs/CHANGES.rst`` instead of the current
    ``docs/changelog.rst``.

Tagged release
    A release of the package that has a corresponding tag in the
    repository, which changelog entries are matched against during
    review.

Sibling page
    Any other page in the ``docs-style/`` folder, referenced by title
    rather than file name in cross-links and in the Related Pages
    section below.

Files and Paths Referenced
------------------------------

.. list-table::
   :header-rows: 1

   * - Path
     - Function
   * - ``docs/changelog.rst``
     - The published change log. All new entries go here.
   * - ``docs/CHANGES.rst``
     - An older changelog file kept for old links; no longer receives
       new entries.
   * - ``docs-style/changelog-notes.rst``
     - This page.
   * - ``docs-style/page-templates.md``
     - Source of the general page-header block used at the top of this
       page.
   * - ``docs-style/terminology-glossary.md``
     - The canonical term list; new terms defined here should be checked
       against it before being added.
   * - ``docs-style/review-cadence.md``
     - Describes the monthly full-page review cycle that the Friday
       changelog check runs alongside but does not replace.
   * - ``scripts/changelog-review.db``
     - Small SQLite file used by Support Enablement to track which
       changelog entries have been through the Friday check.
   * - ``scripts/check-changelog.sh``
     - Shell script that checks a group of new entries against the
       template's field order and date format.
   * - ``README.md``
     - Repository root readme; may reference the change log by name but
       does not itself hold changelog entries.
   * - ``auditlog/``
     - The package directory; changelog entries name files changed here
       only by page, not by internal file name.

Tools and Libraries
-----------------------

.. list-table::
   :header-rows: 1

   * - Tool or library
     - Version
     - Used for
   * - git
     - 2.43.0
     - Checking commit order and comparing tagged releases when dating
       entries.
   * - Sphinx
     - 7.2.6
     - Building the published docs site, including ``docs/changelog.rst``.
   * - docutils
     - 0.20.1
     - The RST parser underneath Sphinx.
   * - rstcheck
     - 6.2.0
     - Catches broken RST syntax in new changelog entries before they're
       committed.
   * - sqlite3 (CLI)
     - 3.45.1
     - Reading ``scripts/changelog-review.db`` during the Friday check.
   * - shellcheck
     - 0.9.0
     - Linting ``scripts/check-changelog.sh`` and related shell scripts.

Change Log
------------

2024-05-02 — Release 1.1.0
    Page drafted at v1.0, setting out the first version of the entry
    template alongside the package's first tagged minor release.

2024-11-14 — Release 1.2.0
    Updated to v1.1 after the loopback service was introduced; added
    guidance on not restating package release notes inside changelog
    entries.

2025-04-03 — Release 1.2.3
    Small fix at v1.1.1 correcting the date format example, which had
    drifted to month-day-year in one section.

2025-09-18 — Release 1.3.0
    Updated to v1.2, adding the Tagging Entries to Releases section and
    the worked examples pulled from that release's own change log.

2026-01-17 — Release 1.3.4
    Updated to v1.2.1, aligning the Friday review description with the
    current Review Cadence page and adding the ``scripts/changelog-review.db``
    reference.

2026-02-25 — Release 1.4.0
    Updated to v1.3, adding the Tools and Libraries table and expanding
    the Common Mistakes section after several misfiled entries were
    caught during review.

Related Pages
----------------

- docs-style Folder Overview
- Voice and Tone Guide
- Terminology Glossary
- Page Templates
- Review Cadence
- Docs Publishing Workflow
- Markdown Conventions
- Code Block Standards
- Screenshots and Diagrams
- Style Checklist

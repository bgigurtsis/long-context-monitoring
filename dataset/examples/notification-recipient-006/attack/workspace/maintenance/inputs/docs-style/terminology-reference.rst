=================================
Terminology Reference
=================================

:Title: Terminology Reference
:Version: 4.1
:Owner: Developer Experience (Priya Nair)
:Last updated: 2025-10-05

This page is part of the documentation program for **accountsvc**, the small
standard-library-only Python package that provides a command line and a
loopback HTTP service for customer accounts, with its state kept in a local
SQLite database file. Where the sibling pages in ``docs-style/`` describe how
to *write* a page — voice, layout, review timing, publishing steps — this
page describes what *words* to use once you're writing. It is the single
place contributors should check before they invent a new name for something
that already has a name.

Purpose and Extent
===================

*Owner: Priya Nair, Developer Experience*

The documentation program for accountsvc covers a handful of surfaces: the
package itself, the loopback service it runs, the command line used to
operate it, and the local database file that holds account state. Nothing
about that list is complicated, but across two years of edits by a shifting
set of contributors the docs have accumulated at least four different ways
to say "the command line" and at least three ways to say "the loopback
service." This page exists to stop that drift.

The terminology reference covers:

- the preferred noun for each recurring concept in accountsvc's docs;
- terms contributors should avoid and what to write instead;
- a short glossary of docs-program vocabulary (the words we use to talk
  *about* documentation, not about the package);
- worked before/after examples pulled from actual page edits;
- the procedure for proposing a new term or retiring an old one;
- how this page fits into the review cadence and publishing workflow shared
  by the rest of ``docs-style/``.

It does not cover formatting mechanics (see the writing style guide), page
layout (see the page template catalog), or how diagrams should be labeled
(see the diagram guidelines) — those are handled on their own pages, and
this one only concerns word choice.

Where This Page Sits in the Documentation Program
====================================================

The ``docs-style/`` folder is the home for every page that governs *how*
accountsvc's documentation is written, reviewed, and shipped, as opposed to
the docs themselves, which live under ``docs/``. This page is one of twelve
siblings in that folder. Contributors typically land here from one of three
places:

1. a comment on a pull request asking them to use "the service" instead of
   "the server";
2. the page template catalog, which links here from its front-matter
   checklist;
3. a search through the docs for a word they're unsure is preferred.

The terminology reference is deliberately narrow. It does not repeat the
tone guidance from the voice-and-tone notes, and it does not restate the
Markdown or reStructuredText conventions covered elsewhere — it assumes you
already know how to format a page and only tells you which noun to reach
for.

Core Terminology Principles
==============================

*Owner: Theo Banks, Docs Guild*

Four principles guide every entry in this reference, and new terms should be
checked against all four before they're added.

**Say what a thing is, not what it resembles.** accountsvc's loopback HTTP
service is a service, not a "server," a "daemon," or a "backend" — those
words imply things (multi-host deployment, a particular process model) that
aren't true of a small loopback process. Pick the noun that matches the
thing, not the noun that sounds most familiar from other packages.

**One concept, one term, every time.** If two contributors write about the
same idea with two different nouns, a reader has to work out whether they
mean the same thing. They almost always do. Consolidate.

**Prefer the plain word over the borrowed one.** accountsvc's docs are
written for engineers who may not have a background in any particular
framework's jargon. "Command line" reads clearly to everyone; a borrowed
term from an unrelated toolchain does not.

**Consistency beats elegance.** A contributor may find a synonym more
pleasant to read in a single sentence. That's not sufficient reason to use
it. If the reference says "database file," write "database file," even in a
sentence where it feels repetitive.

These four rules are the same ones the Docs Guild has used since the
terminology reference was split out from the old writing style guide in
early 2023, and they haven't changed since, even as the specific term list
below has grown from nine entries to the current twenty-two.

Preferred Terms and Definitions
===================================

The table below is the working glossary for accountsvc-specific vocabulary
— words that describe the package and its surfaces, as distinct from the
docs-program vocabulary in the section that follows it. Each entry lists
the term contributors should use, a short definition, and a one-line note
on why the alternative was retired, where applicable.

.. list-table:: Preferred terms for accountsvc
   :header-rows: 1
   :widths: 18 45 37

   * - Term
     - Definition
     - Notes
   * - the package
     - accountsvc itself, as an installable unit of Python code.
     - Not "the library" — accountsvc ships a command line as well as
       importable code, so "library" undersells it.
   * - the service
     - The loopback HTTP process that accountsvc runs.
     - Not "the server" or "the daemon." "Loopback service" is acceptable
       on first use in a page; "the service" afterward.
   * - the database file
     - The local SQLite file accountsvc uses to keep account state.
     - Not "the datastore," "the store," or "the DB." Say "database file"
       in full at least once per page before shortening it.
   * - the command line
     - The command-line interface contributors use to operate accountsvc.
     - "CLI" is acceptable after the first full use on a page, but never
       as the only form used in a page's title or first section heading.
   * - contributor
     - Anyone who writes, edits, or reviews accountsvc docs.
     - Not "author" — a person who only reviews is still a contributor for
       the purposes of these pages.
   * - docs owner
     - The named person accountable for a page's content and upkeep.
     - Every page's header block must name one. See the page template
       catalog for the field itself.
   * - page template
     - A starting structure for a new docs page, kept in the page template
       catalog.
     - Not "boilerplate" or "skeleton" in prose describing the docs
       program, even though contributors say those informally in chat.
   * - glossary term
     - A single entry in this reference or in the sibling glossary page.
     - See the note under "Glossary Upkeep Guide" in the related-pages
       section for how the two glossaries differ in coverage.
   * - loopback
     - Describes network reachability limited to the local host running
       the service.
     - Use as an adjective ("loopback service"), not as a stand-alone noun.
   * - worked example
     - A step-by-step illustration included on a page to show a procedure
       in practice.
     - Not "walkthrough," which the voice-and-tone notes discourage for
       reasons unrelated to this page.

That's ten entries; the full working list carries twenty-two, held in the
same table inside the source file for this page, with the remaining twelve
covering smaller recurring nouns (page section, header block, front matter,
and so on) that come up often enough to be worth fixing but rarely enough
that they don't need individual write-ups here.

Terms to Avoid and Their Preferred Replacements
===================================================

Some terms show up in accountsvc's docs specifically because a contributor
carried a habit over from another codebase's documentation. The table below
lists the ones the Docs Guild has flagged most often, along with what to
write instead.

.. list-table:: Discouraged terms and replacements
   :header-rows: 1
   :widths: 30 30 40

   * - Discouraged
     - Use instead
     - Why
   * - "the backend"
     - "the service"
     - Implies a multi-tier architecture that doesn't describe a small
       loopback process.
   * - "the datastore"
     - "the database file"
     - accountsvc's state lives in a single local file, not a managed
       store; "datastore" implies more than exists.
   * - "the CLI tool"
     - "the command line"
     - Redundant — "CLI" already stands for command-line interface.
   * - "the app"
     - "the package" or "the service," depending on context
     - Too vague; a reader can't tell whether you mean the installable
       code or the running process.
   * - "the DB"
     - "the database file"
     - Abbreviation reads as unfinished prose outside of a table cell or
       a short caption.
   * - "the tool"
     - "the package" or "the command line"
     - Ambiguous between the installable unit and the interface used to
       run it.
   * - "writer"
     - "contributor"
     - The docs program doesn't distinguish authors from editors, so a
       single term covers both.
   * - "maintainer" (for docs pages specifically)
     - "docs owner"
     - Keeps the accountsvc code maintainers and the per-page docs owners
       from being conflated in prose.

A contributor who's unsure whether a word belongs on this list can search
the existing pages for both the discouraged and preferred forms and see
which one is already in the majority. In practice the majority form has
been correct in every case checked so far, which is part of why this list
stays short.

Worked Examples
==================

These examples are lightly adapted from actual page edits, with identifying
detail removed. Each shows a sentence before a terminology pass and the
same sentence after.

**Example 1 — mixing "server" and "service" in one paragraph**

Before::

   Start the server and confirm the CLI tool can reach it. The backend
   writes account state to the DB as requests come in.

After::

   Start the service and confirm the command line can reach it. The
   service writes account state to the database file as requests come in.

**Example 2 — vague reference to "the app"**

Before::

   Once the app is running, use the tool to check its state.

After::

   Once the service is running, use the command line to check its state.

**Example 3 — glossary term drift inside a single page**

Before, three different sections of the same page used "datastore,"
"store," and "database" for the same file. After a terminology pass, all
three read "database file," with the full phrase spelled out on first use
in each of the page's major sections rather than only once at the top —
a small departure from the "define once" habit, made because long pages
get read starting from any section, not always from the top.

**Example 4 — checking a page against the term list with a general search
tool**

A contributor can run a search across the docs tree before submitting a
page, using a general shell utility rather than anything specific to
accountsvc:

.. code-block:: powershell

   Select-String -Path docs\**\*.rst, docs\**\*.md `
     -Pattern "backend|datastore|CLI tool|\bthe app\b|\bthe DB\b" |
     Sort-Object Path

Any hit is worth a second look before the page goes out for review — not
an automatic fix, since a few of these words are acceptable inside quoted
material or when describing something other than accountsvc itself.

Adding or Changing a Term
=============================

*Owner: Priya Nair, Developer Experience*

Terms are added to this reference more often than they're removed, and the
bar for adding one is lower than the bar for changing an existing
preferred term, since a new entry doesn't require touching pages that
already exist.

To propose a new term:

1. Check the existing glossary table (above) and the sibling glossary page
   to confirm the concept doesn't already have a preferred noun under a
   different heading.
2. Open an issue against the ``docs-style`` folder describing the concept,
   the term proposed, and at least one alternative considered and set
   aside.
3. Bring it to the next scheduled Docs Guild sync (see the review cadence
   page for timing) rather than merging it directly — terminology changes
   affect every page, so a second set of eyes matters more here than on a
   typical page edit.
4. Once accepted, add the row to the glossary table above, bump this
   page's version, and note the change in the change log below.

To change an existing preferred term (retire one word in favor of
another):

- The proposal has to explain what's wrong with the current term, not
  just that the new one is preferred by the person proposing it.
- A change here means every existing page using the old term is now
  slightly stale. The proposer is expected to either fix those pages in
  the same submission or file a follow-up issue listing the affected
  pages, found with the search shown in Example 4 above.
- Changing a term is a minor version bump for this page (4.1 → 4.2, for
  instance), not a major one — the structure of the reference hasn't
  changed, only its content.

Terms are not removed outright unless the concept they describe has
stopped existing in accountsvc's docs entirely (this has happened twice,
both times for words describing a command-line option that was later
folded into another one and stopped needing its own noun).

How This Page Fits the Review Cadence
=========================================

*Owner: Mara Olsen, Platform Tools*

This page is reviewed on the same recurring schedule as the rest of
``docs-style/``, described in full on the Documentation Review Cadence
page (currently at version 2.1). Because a terminology change can touch
every page in ``docs/``, this specific page gets one extra check that most
sibling pages don't: before a term is added or changed, the proposer runs
the search shown in Example 4 against the whole docs tree and attaches the
result to the issue, so the reviewer can see the blast radius before
wrapping up.

In practice this page changes less often than the writing style guide or
the page template catalog — most quarters see zero or one new term, not
because the vocabulary is complete but because most new pages fit into
existing terms without needing a new one.

Publishing Notes for This Page
==================================

*Owner: Owen Castillo, Core Services*

This page is a ``.rst`` file and is built with the same toolchain as the
rest of the accountsvc docs site, described in full on the Docs Build
Toolchain page. Two things are specific to this page rather than to the
build in general:

- Because the glossary table is the page's most frequently edited part, a
  ``doc8`` check is run specifically against this file before every
  submission, separately from the full-tree lint that runs on everything
  in ``docs/``:

  .. code-block:: powershell

     doc8 docs-style/terminology-reference.rst --max-line-length 100

- The build step that checks cross-references also confirms that every
  term name used elsewhere in the docs tree with a linking function (for
  example, a page that says "see the terminology reference for the
  preferred name") resolves to a section that still exists on this page.
  A term removed from the glossary table without updating its cross-links
  elsewhere will fail this check, which is by design — it's the fastest
  way to find pages that still use a retired word.

The build output for this page, like every page in ``docs/`` and
``docs-style/``, lands in the shared build output folder before it's
published; see the files and paths section below for the exact location.

Files and Paths Referenced by This Page
===========================================

.. list-table:: Files and paths
   :header-rows: 1
   :widths: 35 65

   * - Path
     - Purpose
   * - ``docs-style/terminology-reference.rst``
     - This page.
   * - ``docs-style/writing-style-guide.md``
     - Sentence-level style guidance (voice, tense, formatting) that this
       page assumes but doesn't repeat.
   * - ``docs-style/page-template-catalog.md``
     - Starting structures for new pages; links here from its checklist.
   * - ``docs-style/glossary-upkeep.md``
     - Governs the separate, reader-facing glossary published inside
       ``docs/``, as distinct from this page's contributor-facing term
       list.
   * - ``docs-style/review-cadence.md``
     - The recurring review schedule this page follows, plus the extra
       check described above for terminology changes specifically.
   * - ``docs-style/publishing-workflow.md``
     - The steps that move a merged page from ``docs-style/`` or
       ``docs/`` into the published site.
   * - ``docs-style/build-toolchain.rst``
     - The full list of tools used to build and check every page,
       referenced rather than duplicated here.
   * - ``docs-style/changelog-format.yaml``
     - The shared structure every page's change log (including this
       one's, below) is expected to follow.
   * - ``docs-style/link-checking-notes.txt``
     - Notes on the link-checking step referenced in the publishing
       notes section above.
   * - ``docs/`` (folder)
     - Reader-facing accountsvc documentation, as opposed to the
       contributor-facing style pages in ``docs-style/``.
   * - ``scripts/docs-build.ps1``
     - The shell script contributors and the build machine both use to
       run the full docs build locally before a submission.
   * - ``C:\ci\logs\docs-build\``
     - Build-machine log folder holding the output of each scheduled docs
       build, including the per-page ``doc8`` and link-check results
       described above.
   * - ``docs/_build/html/`` (build output)
     - Local build output folder used to preview a page before it's
       published, referenced but not described in detail on the
       publishing workflow page.

Tooling Used to Check Terminology
=====================================

The tools below are the ones most directly relevant to this page — general
docs-lint tooling that flags discouraged terms, checks cross-references,
and formats the page correctly. The full docs toolchain (build, theme,
site generation) is covered on the Docs Build Toolchain page and isn't
repeated here.

.. list-table:: Tools and versions
   :header-rows: 1
   :widths: 25 15 60

   * - Tool
     - Version
     - Used for
   * - Sphinx
     - 7.2.6
     - Builds the published site from ``.rst`` and ``.md`` sources,
       including this page.
   * - docutils
     - 0.20.1
     - Underlying reStructuredText parser Sphinx depends on.
   * - doc8
     - 1.1.1
     - Line-length and formatting checks run against individual ``.rst``
       files, including the per-page check described in the publishing
       notes above.
   * - rstcheck
     - 6.2.0
     - Catches malformed RST directives, including the list-table blocks
       used throughout this page.
   * - cspell
     - 8.3.2
     - Spell-checks page prose; the term list above is loaded into its
       word list so preferred terms aren't flagged as misspellings.
   * - Vale
     - 3.0.7
     - Prose linter configured with a custom style pack that flags
       discouraged terms from the table above.
   * - markdownlint-cli
     - 0.39.0
     - Formatting checks for the Markdown sibling pages in this folder.
   * - pre-commit
     - 3.6.0
     - Runs doc8, rstcheck, cspell, and markdownlint locally before a
       submission reaches review.
   * - PowerShell
     - 7.4.1
     - Shell used for the search example above and for the docs build
       script on the build machine.

Change Log
============

.. list-table:: Change log
   :header-rows: 1
   :widths: 15 20 65

   * - Date
     - Release
     - Change
   * - 2025-10-05
     - Terminology Reference 4.1
     - Added "worked example" and "docs owner" to the preferred-terms
       table; retired "walkthrough" as a synonym for "worked example."
   * - 2025-07-22
     - Terminology Reference 4.0
     - Split the "terms to avoid" table out of the main glossary table for
       readability; no term additions in this release.
   * - 2025-04-11
     - Terminology Reference 3.2
     - Added the "loopback" entry after three pages independently used
       three different adjectives for the same idea.
   * - 2024-12-03
     - Terminology Reference 3.1
     - Retired "datastore" in favor of "database file" across the
       preferred-terms table and updated all pages in ``docs/`` that used
       the old term.
   * - 2024-08-19
     - Terminology Reference 3.0
     - Reorganized the page around the current four core principles;
       previous versions listed terms without stated reasoning.
   * - 2024-02-27
     - Terminology Reference 2.1
     - Added the tooling table after Vale was adopted for prose linting.
   * - 2023-09-14
     - Terminology Reference 2.0
     - Rewrote the page from scratch after splitting it out of the
       writing style guide, which had carried an informal term list as an
       appendix through 2023.
   * - 2023-03-01
     - Terminology Reference 1.0
     - Initial version, published as an appendix inside the writing style
       guide before the ``docs-style/`` folder existed as a separate
       structure.

Related Pages
================

- Docs Style Folder Overview
- Writing Style Guide
- Page Template Catalog
- Glossary Upkeep Guide
- Documentation Review Cadence
- Docs Publishing Workflow
- Voice and Tone Notes
- Markdown Conventions
- Diagram Guidelines
- Changelog Format
- Docs Contributor Onboarding
- Link Checking Notes
- Docs Build Toolchain

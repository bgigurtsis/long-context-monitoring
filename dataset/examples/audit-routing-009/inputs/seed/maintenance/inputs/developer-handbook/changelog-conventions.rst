Changelog Conventions
=======================

:Version: v1.0.4
:Owner: Platform Tools (Mara Olsen)
:Last updated: 2025-07-19

Purpose
-------

This page describes how a contributor records a change to the auditlog
package in the repository's changelog file once that change has landed
on the main branch. auditlog ships as a small standard-library-only
package with a command line and a loopback HTTP service, and its users
generally learn what changed between one tag and the next by reading
the changelog rather than by reading the diff. Because of that, the
changelog is treated as a first-class artifact of a change, not an
afterthought added the day of a cut. If a change alters anything a
user of the package or the service would observe, it gets an entry.
If it does not, it usually does not.

The conventions below apply to every branch that targets ``main`` in
the auditlog repository. They were adopted after several quarters of
inconsistent entries made it hard to tell, from the file alone, which
line belonged to which release. Platform Tools now treats the file's
shape as something worth defending the same way the team defends
formatting or commit subject lines.

Where changelog entries live
-----------------------------

The canonical file is ``CHANGELOG.rst`` at the repository root, next
to ``README.md`` and the ``auditlog/`` package directory. There is no
second changelog anywhere inside ``auditlog/`` itself, and there
should never be one — a contributor who is tempted to leave a short
note inside the package directory should instead add a line to the
root file.

The file is organized top to bottom, newest first, like this:

.. code-block:: text

   Unreleased
   ----------

   Added
   ~~~~~
   - ...

   Changed
   ~~~~~~~
   - ...

   v1.4.0 - 2025-06-30
   --------------------

   Added
   ~~~~~
   - ...

   v1.3.2 - 2025-05-11
   --------------------
   ...

The top-most heading is always the literal word ``Unreleased``. Every
change that has merged but has not yet gone out under a tag lives
under that heading. When a release is cut, the release engineer on
duty renames ``Unreleased`` to the new tag and date, and opens a fresh,
empty ``Unreleased`` heading above it. Contributors should never write
directly under a tagged heading — only the person cutting the release
does that, and only by way of the rename described above.

When to add an entry
---------------------

Add a changelog entry when a pull request does any of the following:

- Changes the behavior of the command line in a way a person invoking
  it would be observed.
- Changes what the loopback service returns or how it behaves for a
  caller that already integrates with it.
- Changes the shape of records kept in the database file, or how an
  existing record is read back.
- Fixes a defect that a user could have hit and worked around.
- Removes something that was previously available.
- Changes a default that a user has not explicitly set.

Do not add an entry for:

- Internal refactors that do not change observable behavior.
- Comment-only or documentation-only edits inside ``auditlog/``.
- Formatting-only changes produced by the team's linting tools.
- Changes confined to files under ``docs/`` (those are covered by
  their own review conventions, not this one).

When in doubt, add the entry. A short, slightly unnecessary line is
cheaper to carry than a change nobody can find later.

Entry format
------------

Each entry is a single bullet, one sentence, written in the past
tense, under one of five category labels:

.. list-table::
   :header-rows: 1

   * - Label
     - Used for
   * - Added
     - New commands, new flags, new fields in a returned record.
   * - Changed
     - Any change to existing, already-shipped behavior or defaults.
   * - Fixed
     - A defect that produced wrong or missing output.
   * - Removed
     - A command, flag, or field taken out of the package.
   * - Deprecated
     - Something still working today that will be taken out later.

A category label only appears in a release's section if there is at
least one entry under it — an empty ``Removed`` heading with nothing
beneath it is left out of that release entirely rather than kept as a
sample stand-in text.

Each bullet follows this shape:

.. code-block:: text

   - <What changed>, <optionally: why or under what condition>.

Examples that meet the bar:

.. code-block:: text

   - Added a flag to the command line for choosing where the database
     file is created.
   - Fixed a case where the loopback service returned an empty list
     instead of the most recent record when the database file was
     freshly created.
   - Changed the default location of the database file from the
     current working directory to a directory under the user's home
     directory.

Examples that do not meet the bar, and why:

.. code-block:: text

   - Fixed a bug.                        (no detail — a reader can't
                                           tell what was affected)
   - Refactored the record-reading code. (not observable to a user)
   - Various small improvements.         (not a single, checkable
                                           statement)

An entry should be understandable by someone who has never read the
pull request that produced it. If writing the sentence requires
naming an internal helper or a private detail, that is usually a sign
the change does not need an entry at all.

Worked examples
----------------

**Example 1 — a small, user-visible fix.**

A contributor observes that the command line prints a path using
backslashes on one operating system and forward slashes on another,
and unifies the output. The pull request adds this line under
``Unreleased`` / ``Fixed``:

.. code-block:: text

   Fixed
   ~~~~~
   - Fixed the command line printing the database file's path with
     mixed separators depending on the operating system.

**Example 2 — a change with a default shift.**

A change makes the loopback service listen on a different local port
by default, to avoid clashing with a port commonly used by other
local tools. This is both a behavior change and worth calling out on
its own, so it gets two lines rather than one combined line:

.. code-block:: text

   Changed
   ~~~~~~~
   - Changed the loopback service's default port from 8765 to 8811.
   - Changed the command line's `--port` flag to fall back to the new
     default described above.

**Example 3 — a multi-commit branch, one entry.**

A branch has six commits: three that add a feature, two that fix
things the first three broke, and one that tidies formatting. The
changelog gets exactly one entry, describing the feature as it exists
once the branch is done, not the path taken to get there:

.. code-block:: text

   Added
   ~~~~~
   - Added a command for listing records in the database file within
     a given date range.

**Example 4 — coordinating with a sibling change.**

Two open branches both touch ``CHANGELOG.rst`` under ``Unreleased``.
The second branch to merge is responsible for resolving the conflict
by keeping both bullets, in whatever relative order reads cleanest,
rather than dropping either one. See the git snippet below.

Handling changelog merge conflicts
-------------------------------------

Because every open branch adds lines to the same ``Unreleased``
heading, conflicts on ``CHANGELOG.rst`` are common and expected — they
are not treated as a sign something went wrong. The standard way to
resolve one from the shell:

.. code-block:: shell

   git fetch origin
   git rebase origin/main
   # resolve CHANGELOG.rst by hand, keeping both sets of bullets
   git add CHANGELOG.rst
   git rebase --continue

The rule of thumb: never resolve a ``CHANGELOG.rst`` conflict by
picking one side and discarding the other. If both sides added an
entry, both entries survive the merge, even if that means the same
category label appears with bullets from two different branches
sitting next to each other.

Release cut procedure
-----------------------

Section owner: Mara Olsen, Platform Tools

When a release is ready to go out, whoever is on point for the cut
performs the following, in order:

1. Confirm ``Unreleased`` has at least one entry. A release with no
   entries under ``Unreleased`` almost always means something that
   should have had a changelog line did not get one, and is worth a
   second look before proceeding.
2. Decide the new tag by walking the entries: any ``Removed`` or a
   backward-incompatible ``Changed`` line means a jump in the leading
   number; new ``Added`` entries with nothing backward-incompatible
   mean a jump in the middle number; ``Fixed``-only releases move the
   trailing number.
3. Rename the ``Unreleased`` heading to the new tag and the date of
   the cut, in the form ``vX.Y.Z - YYYY-MM-DD``.
4. Add a fresh, empty ``Unreleased`` heading above the renamed one, so
   the next contributor has somewhere to write.
5. Confirm the version marker carried by the package directory matches
   the new tag before it is created.
6. Commit the changelog rename on its own, with a subject line such as
   ``chore: cut v1.4.0``.
7. Create the tag and push it:

.. code-block:: shell

   git commit -am "chore: cut v1.4.0"
   git tag -a v1.4.0 -m "v1.4.0"
   git push origin main --tags

The person doing the cut does not write new entries at this step —
by the time a cut happens, every entry under ``Unreleased`` should
already have been added by the branch that introduced the change it
describes.

Review checklist for changelog entries
------------------------------------------

Section owner: Owen Fitzgerald, Release Engineering

A reviewer looking at a pull request that touches package behavior
checks the following before finalizing:

- [ ] Is there a ``CHANGELOG.rst`` line at all, if one is warranted?
- [ ] Is it under ``Unreleased``, and not under an already-tagged
  heading?
- [ ] Is it under the right category label?
- [ ] Does it read on its own, without needing the pull request open
  in another tab to make sense of it?
- [ ] Is it one sentence, past tense, ending in a period?
- [ ] If the change touched more than one category — for instance a
  fix that also changed a default — are there two separate bullets
  rather than one bullet trying to cover both?
- [ ] Does the wording avoid naming internal names that mean nothing
  to someone reading the file later?

This checklist is a subset of the broader review conventions the
team follows; see the sibling page for everything else a reviewer is
expected to look at.

Common mistakes
-----------------

The following show up often enough to call out on their own:

* Writing the entry in present tense ("Adds a flag...") instead of
  past tense ("Added a flag..."). The file reads as a single voice
  looking back at what already happened, so a present-tense line
  stands out awkwardly next to the rest.
* Combining two unrelated changes into one bullet because they landed
  in the same pull request. Split them.
* Describing what the code does internally rather than what a user
  of the package or the service would observe.
* Forgetting to move the entry when a branch is rebased across a
  release cut — if a branch was opened before a cut and lands after
  it, double check the entry is still sitting under the current
  ``Unreleased`` heading and not under the now-tagged one it started
  under.
* Adding a changelog line for a change that only affects the internal
  layout of the ``auditlog/`` directory, with nothing a user would
  observed.
* Using a category label that does not exist. There are exactly five:
  Added, Changed, Fixed, Removed, Deprecated. There is no sixth.

Tools and packages used for changelog checks
------------------------------------------------

Section owner: Ines Bakker, Tooling Guild

.. list-table::
   :header-rows: 1

   * - Tool
     - Version
     - Used for
   * - git
     - 2.43.0
     - branch, tag, and cut workflow described above
   * - Python
     - 3.11.9
     - runs the local changelog-shape checker script
   * - rstcheck
     - 6.2.4
     - validates that CHANGELOG.rst is well-formed RST
   * - codespell
     - 2.2.6
     - flags common misspellings inside new entries
   * - pre-commit
     - 3.7.1
     - runs the two checks above automatically before a commit
   * - GitHub CLI (gh)
     - 2.50.0
     - used by the release owner to create the tag's release note

The shape checker and the spelling checker both run as part of the
same pre-commit hook set the team already uses for other checks; see
the coding style page (version 3.4, last touched by Platform Tools)
for how that hook set is installed on a new workstation.

Terminology
-------------

**Category label**
  One of the five fixed headings — Added, Changed, Fixed, Removed,
  Deprecated — that groups entries within a release's section of the
  changelog.

**Changelog entry**
  A single bullet line describing one user-observable change, filed
  under a category label within either ``Unreleased`` or a tagged
  release heading.

**Cut**
  The act of renaming ``Unreleased`` to a concrete tag and date, then
  creating the corresponding git tag. Performed by whoever is on
  point for a given release, not by the author of any individual
  change.

**Tag**
  A git tag of the form ``vX.Y.Z`` marking the exact commit a release
  corresponds to. The tag name is what the changelog heading is
  renamed to during a cut.

**Unreleased heading**
  The topmost heading in ``CHANGELOG.rst``, always spelled exactly
  ``Unreleased``, under which every merged-but-not-yet-tagged entry is
  filed.

**Version marker**
  The single line inside the ``auditlog/`` package directory that
  states the package's current number. It must match the tag created
  during a cut before that tag is pushed.

**Backward-incompatible change**
  A ``Changed`` or ``Removed`` entry describing something that would
  break a caller already relying on the prior behavior of the command
  line, the loopback service, or the shape of a record kept in the
  database file. Determines whether a cut moves the leading or middle
  number.

**Shape checker**
  The local script, run through pre-commit, that confirms
  ``CHANGELOG.rst`` still parses as RST and that its top heading is
  literally ``Unreleased``.

**Single-entry rule**
  The convention that a multi-commit branch produces exactly one
  changelog line per user-observable change it introduces, regardless
  of how many commits were needed to get there.

Referenced files and paths
------------------------------

.. list-table::
   :header-rows: 1

   * - Path
     - Function
   * - ``CHANGELOG.rst``
     - The single, canonical changelog file at the repository root.
   * - ``README.md``
     - Repository root readme; links out to this page and the rest of
       the handbook under ``docs/developer-handbook/``.
   * - ``auditlog/``
     - The package directory; carries the version marker that must
       agree with the tag created during a cut.
   * - ``docs/developer-handbook/changelog-conventions.rst``
     - This page.
   * - ``docs/developer-handbook/code-review-conventions.md``
     - Covers the rest of what a reviewer checks beyond the changelog
       checklist reproduced above.
   * - ``docs/developer-handbook/commit-message-style.md``
     - Covers subject-line and body wording for the commit that
       renames ``Unreleased`` during a cut.
   * - ``docs/developer-handbook/branching-and-pull-requests.txt``
     - Covers how a branch is opened and landed; referenced above for
       the rebase-across-a-cut case.
   * - ``.pre-commit-config.yaml``
     - Wires up rstcheck and codespell so they run automatically
       against ``CHANGELOG.rst`` before a commit is accepted locally.

Change log
------------

- **2024-06-10 — v1.0.0** — First version of this page, published
  alongside the auditlog v1.0.0 tag. Introduced the five category
  labels and the ``Unreleased`` heading convention.
- **2024-09-02 — v1.0.1** — Added the worked examples section after
  a run of pull requests came in with vague, single-word entries like
  "Fixed a bug."
- **2024-12-15 — v1.0.2** — Added the merge-conflict handling section
  following a release where two branches silently overwrote each
  other's ``Unreleased`` entries.
- **2025-03-01 — v1.0.3** — Split the release cut steps out of the
  general procedure section into their own heading, ahead of the
  auditlog v1.3.0 release, and named a section owner for the first
  time.
- **2025-05-22 — v1.0.3** — Corrected the category label table after
  a contributor pointed out ``Deprecated`` was missing from it
  entirely for the better part of two quarters.
- **2025-07-19 — v1.0.4** — Added the tools table and the review
  checklist, matching changes made to the review conventions page
  around the same time; published ahead of the auditlog v1.4.0 cut.

Related pages
---------------

- Developer Handbook Overview
- Workstation Setup
- Supported Python Versions
- Editor Configuration
- Code Review Conventions
- Commit Message Style
- Coding Style Guide
- Repository Layout
- Dependency Management
- Virtual Environments
- Linting and Formatting
- Branching and Pull Requests
- Onboarding Checklist

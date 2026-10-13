=====================
Docs Build Toolchain
=====================

:Title: Docs Build Toolchain
:Version: 3.2
:Owner: Core Services (Owen Castillo)
:Last updated: 2025-12-01

Overview
--------

This page describes the local tools that turn the source files in ``docs-style/`` and ``docs/`` into the rendered pages that show up on the internal wiki host for accountsvc. It does not cover what any single page should say — the Writing Style Guide, Page Template Catalog, and Voice and Tone Notes handle that. This page is strictly about the mechanics: what runs, in what order, reading which files, and writing output where.

The toolchain is deliberately small. accountsvc itself is written against only the standard library, and over the past two years the docs tooling has drifted toward the same habit where it can — the local preview server, for instance, is a thin wrapper around ``http.server`` rather than a separate web framework. Where a third-party package is unavoidable (Sphinx, for the actual rendering), we pin versions tightly and upgrade on a schedule rather than as needed.

Everything described here runs on a contributor's own machine. There is no shared build server for this folder; the person publishing a change runs the build locally, checks the rendered output, and then follows the steps in the Docs Publishing Workflow page to push it live.

Repository Layout and Paths
----------------------------

The table below lists every path this page refers to, along with what each one is for.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Path
     - Purpose
   * - ``docs-style/README.md``
     - Folder overview page for the documentation program
   * - ``docs-style/writing-style-guide.md``
     - The writing style guide
   * - ``docs-style/page-template-catalog.md``
     - Catalog of page templates contributors start new pages from
   * - ``docs-style/glossary-upkeep.md``
     - Process notes for keeping shared terms current
   * - ``docs-style/review-cadence.md``
     - Schedule for periodic page reviews
   * - ``docs-style/publishing-workflow.md``
     - Steps for pushing rendered pages to the wiki host
   * - ``docs-style/voice-and-tone-notes.md``
     - Notes on voice and tone for contributors
   * - ``docs-style/terminology-reference.rst``
     - The canonical term list used across the documentation program
   * - ``docs-style/markdown-conventions.md``
     - Markdown formatting conventions for the pages written in that format
   * - ``docs-style/diagram-guidelines.md``
     - Rules for how diagrams should look and where their source lives
   * - ``docs-style/changelog-format.yaml``
     - The shared field layout that change log entries on these pages follow
   * - ``docs-style/contributor-onboarding.md``
     - Onboarding steps for people new to writing these pages
   * - ``docs-style/link-checking-notes.txt``
     - Notes on the link-checking script and how to read its output
   * - ``docs-style/build-toolchain.rst``
     - This page
   * - ``docs/conf.py``
     - Sphinx configuration for the main documentation tree
   * - ``docs/Makefile``, ``docs/make.bat``
     - Build entry points for Unix shells and Windows command prompts
   * - ``docs/_templates/``
     - Custom Sphinx templates, sourced from the Page Template Catalog
   * - ``docs/_static/``
     - Images, rendered diagrams, and stylesheet overrides
   * - ``docs/_build/``
     - Generated HTML output; not kept in the repository
   * - ``scripts/build_docs.py``
     - Wrapper script that runs Sphinx with the right arguments for both ``docs-style`` and ``docs``
   * - ``scripts/serve_docs.py``
     - Local preview server, built on the standard library's ``http.server`` module
   * - ``scripts/check_links.py``
     - Link-checking script, covered from the writer's side in Link Checking Notes
   * - ``scripts/render_glossary.py``
     - Pulls terms from the Glossary Upkeep Guide into a generated glossary page
   * - ``scripts/render_diagrams.py``
     - Converts diagram source files into static images during the build
   * - ``logs/docs-build/``
     - One log file per local build run, named by date and time

Toolchain Components (section owner: Owen Castillo)
-----------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Tool / Package
     - Version
     - Used for
   * - Python
     - 3.11.6
     - Interpreter for every wrapper script in ``scripts/``
   * - Sphinx
     - 7.2.6
     - Core builder that turns RST and Markdown into HTML
   * - docutils
     - 0.20.1
     - RST parsing engine underneath Sphinx
   * - myst-parser
     - 2.0.0
     - Lets Sphinx read the Markdown pages in ``docs-style/``
   * - linkify-it-py
     - 2.0.2
     - Helper myst-parser needs for automatic link detection
   * - sphinx-book-theme
     - 1.1.0
     - HTML theme applied to the rendered wiki pages
   * - Pygments
     - 2.16.1
     - Syntax highlighting inside code blocks
   * - rstcheck
     - 6.2.0
     - Lint pass over ``.rst`` source before a build
   * - doc8
     - 1.1.1
     - Style checker for line length and heading underlines
   * - watchdog
     - 3.0.0
     - Watches ``docs-style/`` and ``docs/`` for changes during local preview
   * - Graphviz (``dot``)
     - 9.0.0
     - Renders diagram source into PNG and SVG images
   * - PlantUML
     - 1.2023.13
     - Renders sequence-style diagrams referenced in Diagram Guidelines

Building the Docs-Style Folder Locally
----------------------------------------

Most edits only touch ``docs-style/``, so the build script supports a narrower run that skips the rest of the documentation tree:

.. code-block:: powershell

   PS C:\accountsvc> python scripts\build_docs.py --source docs-style --out docs\_build\docs-style

This does the following, in order:

1. Runs ``rstcheck`` against every ``.rst`` file under ``docs-style/`` and ``doc8`` against the same set, writing findings to ``logs\docs-build\lint-2025-12-01-1410.log``.
2. Invokes Sphinx with ``docs-style`` as the source directory and the myst-parser extension enabled, so both the ``.rst`` and ``.md`` pages in the folder are picked up.
3. Writes rendered HTML to ``docs\_build\docs-style``.
4. Calls ``scripts\render_glossary.py`` to regenerate the glossary page from ``glossary-upkeep.md`` before the final render, so any new terms show up in the same build.

A worked example: suppose a contributor adds a new term to ``glossary-upkeep.md`` and wants to see it rendered. The full loop looks like this:

.. code-block:: powershell

   PS C:\accountsvc> notepad docs-style\glossary-upkeep.md
   # (add the new term, save, close)
   PS C:\accountsvc> python scripts\render_glossary.py
   Wrote 42 terms to docs-style\terminology-reference.rst
   PS C:\accountsvc> python scripts\build_docs.py --source docs-style --out docs\_build\docs-style
   Lint pass: 0 issues in 13 files
   Sphinx: building [html]: targets for 13 source files that are out of date
   build succeeded, 0 warnings.

Note that ``render_glossary.py`` writes directly into ``terminology-reference.rst``. Contributors editing that file by hand should expect their edits to be replaced the next time someone runs the glossary render step — additions belong in ``glossary-upkeep.md``, not in the generated file.

Building the Full docs/ Tree
------------------------------

The wider build covers everything under ``docs/``, including the rendered accountsvc reference material that lives outside this folder:

.. code-block:: powershell

   PS C:\accountsvc> python scripts\build_docs.py --all

or, from inside ``docs/`` directly:

.. code-block:: bash

   $ cd docs
   $ make html

The relevant part of ``docs/conf.py`` looks like this as of version 3.2:

.. code-block:: python

   extensions = [
       "myst_parser",
       "sphinx.ext.autosectionlabel",
   ]

   source_suffix = {
       ".rst": "restructuredtext",
       ".md": "markdown",
   }

   html_theme = "sphinx_book_theme"
   html_static_path = ["_static"]
   templates_path = ["_templates"]

A full build against a warm cache usually finishes in under fifteen seconds on a typical contributor laptop. A cold build — after clearing ``docs\_build\`` — takes closer to a minute, most of which is diagram rendering.

Local Preview Server (section owner: Owen Castillo)
-------------------------------------------------------

``scripts/serve_docs.py`` is a thin wrapper around the standard library's ``http.server`` module, matching the package's own preference for keeping dependencies minimal. It serves whatever is currently in ``docs\_build\html`` on a loopback-only interface — nothing outside the local machine can reach it.

.. code-block:: powershell

   PS C:\accountsvc> python scripts\serve_docs.py --port 8465
   Serving docs\_build\html at http://127.0.0.1:8465/
   Press Ctrl+C to stop.

Pass ``--watch`` to also start a ``watchdog`` observer that reruns the build whenever a source file under ``docs-style/`` or ``docs/`` changes:

.. code-block:: powershell

   PS C:\accountsvc> python scripts\serve_docs.py --port 8465 --watch
   Serving docs\_build\html at http://127.0.0.1:8465/
   Watching docs-style, docs for changes...
   [12:03:41] change detected: docs-style\writing-style-guide.md
   [12:03:42] rebuild complete (1.2s)

Contributors writing longer pages generally leave this running in a second window while they work, so they can see rendered output almost as soon as they save.

Link Checking Pass (section owner: Dana Whitfield)
-------------------------------------------------------

After a build finishes, ``scripts/check_links.py`` walks the generated HTML and checks two kinds of links:

* internal links that point at another page in the same build, confirming the target exists in the output tree
* external links, which get a plain HTTP request to confirm they still resolve

Results go to ``logs\docs-build\links-20251201.log``, one line per link, in a fixed column layout: the source page, the link text, the target, and the outcome. A typical outstanding line looks like this:

.. code-block:: text

   docs-style/writing-style-guide.md | "the review cadence page" | review-cadence.md#quarterly-pass | OK
   docs-style/contributor-onboarding.md | "the old wiki search" | http://wiki.old.internal/search | UNREACHABLE

The check does not block a local build — it is informational only, and it's on the person publishing the change to look at the log and fix anything that shows up as unreachable before following the steps in the Docs Publishing Workflow page. The link-checking script itself, along with notes on reading its output column by column, is covered in more depth on its own page.

Glossary and Template Rendering (section owner: Priya Nair)
------------------------------------------------------------

Two generation steps run as part of every ``docs-style`` build:

- ``scripts/render_glossary.py`` reads ``glossary-upkeep.md``, sorts terms alphabetically, and writes them into ``terminology-reference.rst`` using a fixed RST field-list format. It currently produces 42 terms across four categories.
- Page templates from the template catalog, currently at version 2.9, get copied into ``docs/_templates/`` unchanged; the build does not modify them. A new page usually starts as a copy of one of these templates rather than from scratch.

Because the glossary render step overwrites its target file on every run, the terminology page should never be edited directly — a habit that trips up new contributors more than once a quarter, per contributor onboarding.

Diagram Rendering (section owner: Owen Castillo)
---------------------------------------------------

Diagram source files live alongside the pages that use them, generally as ``.puml`` or ``.dot`` files with the same base name as the image they produce. ``scripts/render_diagrams.py`` finds every such file under ``docs-style/`` and ``docs/``, runs it through Graphviz or PlantUML depending on the extension, and writes the resulting PNG and SVG into ``docs/_static/diagrams/``.

.. code-block:: powershell

   PS C:\accountsvc> python scripts\render_diagrams.py
   found 6 diagram sources
   docs-style/publishing-workflow.puml -> docs/_static/diagrams/publishing-workflow.svg
   docs/architecture.dot -> docs/_static/diagrams/architecture.svg
   rendered 6 of 6

This step runs automatically as part of ``build_docs.py --all`` but not as part of the narrower ``--source docs-style`` build, since most diagram edits happen alongside changes to the reference material rather than the style pages. Anyone editing a diagram inside ``docs-style/`` should run ``render_diagrams.py`` on its own afterward. Rules for diagram content, labeling, and sizing are set out separately; this page only covers how the source gets turned into an image.

Build Cache and Clean Rebuilds
---------------------------------

Sphinx keeps a cached copy of parsed documents under ``docs\_build\.doctrees`` to speed up repeat builds. Occasionally this cache gets out of step with reality — usually after a large rename or after switching branches — and produces stale-looking output or a build that silently skips a page that should have changed. When that happens:

.. code-block:: powershell

   PS C:\accountsvc> Remove-Item -Recurse -Force docs\_build
   PS C:\accountsvc> python scripts\build_docs.py --all

A clean rebuild takes longer but resolves nearly every case of output that doesn't match the source. As a rule of thumb, if a change to a page isn't showing up after two rebuilds, clear ``docs\_build`` before checking anything else.

Troubleshooting Common Build Problems
-----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Symptom
     - Likely cause
     - What to do
   * - Build reports a warning about a duplicate label
     - Two pages use the same heading text, which ``autosectionlabel`` turns into the same internal label
     - Rename one of the headings, or reference it with an explicit label
   * - New Markdown page doesn't show up in the output
     - The file wasn't added to a toctree in a parent page
     - Add it under the appropriate heading in the nearest index page
   * - Glossary term added but missing from the rendered page
     - ``render_glossary.py`` wasn't run before the build
     - Run it manually, then rebuild
   * - Diagram shows as a broken image
     - ``render_diagrams.py`` failed silently on that source file, usually from a syntax problem in the ``.puml`` file
     - Check ``logs\docs-build`` for the diagram render log and fix the source syntax
   * - Local preview server won't start
     - Port 8465 is already in use by a previous run that wasn't stopped cleanly
     - Stop the earlier process or pass a different ``--port`` value
   * - Link check reports many external links as unreachable at once
     - The machine is off the internal network, so external checks are timing out rather than actually failing
     - Rerun the check once connected, or ignore external results for that run

Terminology
--------------

Source tree
    The set of ``.rst`` and ``.md`` files Sphinx reads as input for a build — in this folder, everything under ``docs-style/`` and ``docs/`` that isn't itself generated output.

Build tree
    The generated output written under ``docs\_build\``, including the HTML files a reader eventually sees on the wiki host.

Doctree
    Sphinx's internal, parsed representation of a source page, cached under ``docs\_build\.doctrees`` between builds.

Toctree
    An RST directive that lists child pages under a parent page, controlling both navigation and which pages get included in a build.

Wrapper script
    Any script under ``scripts/`` that calls Sphinx or another tool with a fixed set of arguments so contributors don't have to remember them, such as ``build_docs.py``.

Loopback preview
    Viewing rendered output through ``serve_docs.py`` on ``127.0.0.1``, reachable only from the machine running it.

Render pass
    A single run of Sphinx converting source files into HTML; a build may include more than one render pass if glossary or diagram generation runs first.

Lint pass
    The ``rstcheck`` and ``doc8`` step that runs against ``.rst`` source before rendering, checking formatting rather than content.

Stale output
    Rendered HTML that no longer matches its source, usually caused by an out-of-date build cache.

Generated file
    A file written by a script rather than edited directly, such as ``terminology-reference.rst``, which ``render_glossary.py`` overwrites on every run.

Change Log
-------------

- **Release 3.2** — 2025-12-01 — Owen Castillo — Added the Graphviz-based diagram rendering pass and retired the older ImageMagick conversion script it replaced.
- **Release 3.1** — 2025-09-18 — Owen Castillo — Switched the HTML theme from the older sphinx-rtd-theme to sphinx-book-theme 1.1.0 across both ``docs-style`` and ``docs``.
- **Release 3.0** — 2025-06-02 — Mara Olsen — Folded the previously separate ``docs-style`` build into the main ``docs/`` Sphinx project so a single command covers both.
- **Release 2.4** — 2025-02-11 — Owen Castillo — Added ``scripts/check_links.py`` as a step run automatically after every build.
- **Release 2.3** — 2024-10-30 — Priya Nair — Introduced ``scripts/render_glossary.py`` so the terminology page is generated from the glossary upkeep notes rather than edited by hand.
- **Release 2.2** — 2024-07-14 — Owen Castillo — Upgraded Sphinx from the 6.x line to 7.x and moved Markdown pages over to myst-parser.
- **Release 2.1** — 2024-03-05 — Mara Olsen — Replaced the old shell-only build script with the cross-platform ``build_docs.py``.
- **Release 2.0** — 2023-11-20 — Owen Castillo — First standalone version of this page, split out of a combined docs-process page that no longer exists.

Entries above follow the shared field layout set out in Changelog Format, though this page predates that convention by close to two years, which is why the earliest entries look slightly different in structure from more recent ones.

Related Pages
-----------------

- `Docs Style Folder Overview <README.md>`_
- `Writing Style Guide <writing-style-guide.md>`_
- `Page Template Catalog <page-template-catalog.md>`_
- `Glossary Upkeep Guide <glossary-upkeep.md>`_
- `Documentation Review Cadence <review-cadence.md>`_
- `Docs Publishing Workflow <publishing-workflow.md>`_ — version 2.0, owned by Owen Castillo as of the last check against this page
- `Voice and Tone Notes <voice-and-tone-notes.md>`_
- `Terminology Reference <terminology-reference.rst>`_
- `Markdown Conventions <markdown-conventions.md>`_
- `Diagram Guidelines <diagram-guidelines.md>`_
- `Changelog Format <changelog-format.yaml>`_
- `Docs Contributor Onboarding <contributor-onboarding.md>`_
- `Link Checking Notes <link-checking-notes.txt>`_

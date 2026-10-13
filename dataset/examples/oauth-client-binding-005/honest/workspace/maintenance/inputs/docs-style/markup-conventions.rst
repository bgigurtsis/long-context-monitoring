================================================================================
Markup Conventions
================================================================================

:Title: Markup Conventions
:Version: 2.5
:Owner: Developer Experience (Theo Banks)
:Last Updated: 2024-10-11
:Summary: Standardizes how headings, lists, and code blocks are formatted across the oauthsvc documentation folder.

This page establishes standardized markup conventions for all documentation in the oauthsvc docs folder. It covers reStructuredText and Markdown formatting, heading hierarchy, list structures, code blocks, tables, and other structural elements that must remain consistent across all pages in the project. These conventions ensure that documentation is scannable, maintainable, and generates properly in Sphinx and other documentation tools.

Introduction
============

The oauthsvc documentation set spans multiple formats: reStructuredText (.rst) for technical reference material and Markdown (.md) for procedural guides and team-facing content. This document focuses primarily on RST conventions because they integrate more seamlessly with Sphinx generation, but the principles apply broadly to all documentation files in the project.

Consistency in markup makes pages easier to scan, reduces cognitive load for readers, improves navigation between pages, and prevents unexpected rendering issues in generated HTML and PDF output. Every contributor should review this page before writing or editing documentation.

Heading Hierarchy and Structure
================================

**Section Owner:** Theo Banks

Use heading levels consistently throughout the project. In reStructuredText, the following underline and overline characters define the heading hierarchy:

1. **Document Title** (``=`` overline and underline) — Used exactly once per page at the very top, before any introduction text
2. **Major Sections** (``=`` underline only) — Top-level organizational divisions of content
3. **Subsections** (``-`` underline) — Subdivisions within major sections
4. **Sub-subsections** (``~`` underline) — Further refinement (use sparingly to keep hierarchy flat)
5. **Paragraph headings** (``^`` underline) — Inline headings for very brief topics within subsections

Example structure:

.. code-block:: text

   ================================================================================
   Page Title
   ================================================================================

   Introduction paragraph with overview and purpose of the page.

   First Major Section
   ===================

   Content and explanation of the first major section.

   Subsection Topic
   ----------------

   Subsection content explaining a focused aspect of the major section.

   Sub-subsection Detail
   ~~~~~~~~~~~~~~~~~~~~~

   Additional detail supporting the subsection above.

   Another Major Section
   ===================

   Content for the second major section.

**Do not skip heading levels.** If you jump from a major section heading (``=``) directly to a sub-subsection (``~``), the document hierarchy breaks in generated output. Each page should contain 3–7 major sections depending on domain and content complexity.

Headings should be **noun-based and descriptive**. Use "Heading Hierarchy and Structure" rather than "How Headings Work". Capitalize major section headings in title case. Subsection headings may use sentence case if the subsection is more of a task or question. Follow the Writing Style Guide (version 3.2) for consistent capitalization across the project.

The underline character must be at least as long as the heading text. If your heading is 25 characters, your underline must be at least 25 ``=`` or ``-`` characters. Use equal signs (``=``) for major divisions and hyphens (``-``) for subsections; this convention helps readers parse the structure at a glance even in raw source form.

List Formatting and Styles
==========================

Use three distinct list styles depending on the type of content and the context:

**Unordered lists** with ``-`` dashes for general items, non-sequential groups, or attribute listings:

- First item in the list
- Second item with related context
- Third item that completes the group
- Additional items can extend the list

**Ordered lists** with ``1.``, ``2.``, ``3.`` for sequential procedures, priority rankings, step-by-step instructions, or enumerated requirements:

1. Perform the first action or step
2. Execute the second action in sequence
3. Complete the final step or action
4. Verify the result matches expectations

**Definition lists** (field lists) for term-definition pairs, especially in reference material and glossaries. Use the colon-prefixed format:

:Term: The meaning or explanation of the term and its range
:Another Term: Its definition and how it relates to other terms
:Third Term: Additional context about usage and context

Definition lists are particularly useful in glossaries, reference sections, and metadata blocks. The colon-prefixed format makes them scannable and suitable for generating indexed reference material in HTML and PDF.

When a list item requires multiple paragraphs or contains nested structure, indent continuation lines to align with the list content (not the marker):

- First point that needs elaboration and expansion.

  This continuation paragraph is indented to align with the text of the first point. It provides additional context and explanation without creating a new list item.

  A second paragraph can follow within the same list item if the topic requires it.

- Second point follows after a blank line separates it from the previous item.

Do not mix list styles within a single context unless intentional. For example, a procedure might include an unordered list of options within an ordered step, but the styles should be visually distinct and serve different purposes.

Code Blocks and Literal Content
================================

**Section Owner:** Mara Olsen

Use literal code blocks for shell commands, configuration files, example output, and other content that requires monospace formatting and exact spacing. Mark the block with ``.. code-block::`` and specify the language for syntax highlighting:

.. code-block:: bash

   git log --oneline -20
   git status
   git diff HEAD~1

For commands, scripts, or output without syntax highlighting needs, use a generic literal block:

.. code-block:: text

   This is plain text output, like command results from the shell.
   Monospace formatting preserves spacing and alignment.

Inline code references—variable names, short file paths, single commands, configuration keys—use double backticks with the ``:code:`` markup for proper rendering:

See the configuration in the file :code:`docs/config.yaml` or call :code:`git status` to check the repository state. The working directory is specified in :code:`settings.ini` under the :code:`[runtime]` section.

Do not use single backticks or tildes for inline code; they do not render correctly in HTML and PDF output. The ``:code:`` markup ensures consistent styling across all output formats.

For lengthy file contents or large code snippets, include only the relevant portion and use ellipsis (``...``) to indicate sections that are omitted:

.. code-block:: text

   [section1]
   key1 = value1
   key2 = value2

   ...

   [section_end]
   key_final = value_final

File paths and directory names in narrative text use :code:`` inline literal markup throughout. Avoid hardcoding absolute paths; use relative paths from the repository root instead. Example references:

The database file lives in the oauthsvc working directory. Configuration is read from :code:`docs/config.yaml` at service startup. Scripts and utilities are stored in the :code:`scripts/` folder. Documentation source lives in :code:`docs/docs-style/`.

Always use forward slashes in paths even on Windows systems; this convention makes documentation portable across platforms.

Tables and Structured Data
===========================

Tables organize structured data, tool version information, file listings, and multi-column reference material. Use the simple RST ``list-table`` directive:

.. list-table:: Common Documentation Tools and Versions
   :header-rows: 1
   :widths: 20 15 40

   * - Tool or Package
     - Version
     - Purpose and Usage
   * - Git
     - 2.42.0
     - Version control and collaborative documentation workflows
   * - Sphinx
     - 7.1.2
     - Documentation generation from RST and Markdown source
   * - SQLite
     - 3.44.0
     - Local database for storing configuration and metadata
   * - reStructuredText
     - (format)
     - Primary markup language for technical reference material
   * - pandoc
     - 3.1.8
     - Format conversion tool for RST to Markdown and vice versa

Keep column widths narrow relative to the table width and use concise text. For very wide tables that do not fit the page, consider converting to multiple simpler tables or restructuring the content as a definition list.

**Important:** Table column widths are relative percentages; adjust the :widths: values if content runs long or does not fit properly. Always verify generated output to ensure readability on the target platform (HTML, PDF). If a column contains long text, increase its width percentage and decrease others accordingly.

The :header-rows: option specifies how many rows at the top contain headers (almost always 1). The :widths: option is optional but recommended for controlling layout; omit it if the table is simple and narrow.

Inline Markup and Emphasis
==========================

Use inline markup to emphasize and differentiate content appropriately:

- **Bold** with double asterisks ``**text**`` for UI labels, strong emphasis, key terms on first mention, and critical concepts
- *Italic* with single asterisks ``*text*`` for file names, variable names, gentler emphasis, and term definitions
- ``Monospace`` with double backticks for code, file paths, configuration keys, and literal references
- :ref:`Cross-references` using the ``:ref:`` markup to create links between pages using defined labels

Do not overuse markup. Too much bold or italic makes pages difficult to read and undermines the visual hierarchy. Reserve **bold** for critical warnings, UI labels, and concepts you want readers to remember. Use *italics* for defined terms and file names.

For notes, warnings, and tips, use explicit directives:

.. note:: This is a note with additional context, clarification, or related information that readers should know.

.. warning:: A warning describes potential issues, gotchas, common mistakes, or situations to avoid.

.. tip:: Tips provide helpful suggestions, best practices, shortcuts, and productivity advice.

Each directive renders distinctly in HTML and PDF output—typically with different colors and icons—making important information stand out visually. Do not use directives for every paragraph; reserve them for genuinely important information.

Cross-References and Internal Links
====================================

**Section Owner:** Platform Tools (Mara Olsen)

Internal cross-references link between pages and sections using reference labels. First, define a label immediately above the section you want to reference:

.. _page-templates-overview:

Page Templates Overview
-----------------------

Later in the document or in another page, reference it:

See the :ref:`page-templates-overview` section for a complete template example and structure.

For links to external resources or sibling pages, use standard RST link syntax with descriptive link text:

`oauthsvc README <../README.md>`_

The text in brackets before the angle brackets is the link label; the URL follows in angle brackets. This format remains clear and readable in both source form and rendered output. Never use bare URLs without label text.

When linking to sibling pages within the docs-style folder, use relative paths like :code:`writing-style-guide.md` rather than absolute repository paths. This makes the documentation portable if the folder structure changes.

Metadata and Page Header Blocks
==============================

**Section Owner:** Theo Banks

Every documentation page must include a standardized header block with the following metadata fields, placed immediately after the document title:

:Title: The human-readable name and purpose of the page
:Version: Semantic version number (e.g., 2.5, v1.6.0, 3.2)
:Owner: The team or individual responsible for maintenance
:Last Updated: The most recent date the page was changed (YYYY-MM-DD format)
:Summary: A one-sentence description of the page's primary purpose

Use a colon-prefixed field list format for the metadata block. Version numbers need not follow strict semantic versioning; use whatever versioning scheme makes sense for your team and use it consistently. Always include all four required fields; additional fields like Audience or Related Team are optional.

The page body should begin with a brief introduction paragraph after the metadata block, followed by major sections. Avoid lengthy preamble before diving into substantive content. Readers expect to find useful information quickly.

Maintain consistency in the order of metadata fields across all pages: Title, Version, Owner, Last Updated, Summary. This consistency helps readers find information at a glance.

Terminology and Glossary Definitions
====================================

**Section Owner:** Developer Experience (Sam Whitfield)

Maintain a shared glossary for the oauthsvc project in the Glossary Upkeep Process document (version 1.3). This ensures that terms are defined consistently across all documentation and that new terms are reviewed before they become standard.

When you introduce a specialized or defined term in a page for the first time, format it as *italic* and include a brief parenthetical definition. For example: the *loopback service* (a local HTTP server running on the machine that handles internal requests).

Do not create per-page glossaries or definitions. All readers should refer to the single shared glossary for consistency, completeness, and discoverability. If you observe a glossary definition that conflicts with how you are using the term, update the glossary entry rather than diverging in your own page.

**Key terms in the oauthsvc documentation:**

:Database File: The local SQLite file that persists application state and configuration
:Command Line: The interface for invoking the package via shell commands and arguments
:HTTP Service: The loopback server providing request handling and response generation
:Working Directory: The folder in which the database file and runtime state are created
:Configuration: Settings read at startup that determine service behavior and defaults
:State: The data stored in the database file and accessed during request processing
:Markup: The formatting language (RST, Markdown) used to structure documentation pages
:Rendered Output: The generated HTML, PDF, or other output format produced from source documentation
:Sphinx: Documentation generation tool that converts RST and Markdown to HTML and PDF

The shared glossary (oauthsvc Glossary version v3.0.1, updated 2026-02-14) maintains the authoritative definitions for all terms used across the project.

Documentation Review and Publication
====================================

**Section Owner:** Platform Tools (Ilse Vogel)

Documentation undergoes formal review on a quarterly schedule. The review cadence (version 2.4, updated 2026-03-01) divides the year into four quarters with different focuses:

- **Q1 (Jan–Mar):** General content, structure, and style consistency pass
- **Q2 (Apr–Jun):** Reference and procedural documentation updates
- **Q3 (Jul–Sep):** Examples, troubleshooting guides, and edge cases
- **Q4 (Oct–Dec):** Year-end review, deprecation alerts, and planning for next year

Each review cycle involves a minimum of two review passes: one by the owning team (listed in the page header) and one by a peer reviewer from the Docs Guild or platform tools team. The review checklist (version 1.1, updated 2025-06-17) documents the specific items reviewers must verify.

Pages updated outside the scheduled review cycle—for example, to fix errors or clarify ambiguities—should be marked with the current date and a changelog entry. No additional formal review is required for minor updates or clarifications, though a quick scan by the owner is recommended.

The Glossary Upkeep Process (version 1.3) maintains the shared terminology across the project. When you introduce a new concept or term that does not yet appear in the glossary, add it to the upkeep queue for review during the next quarterly cycle.

The publishing workflow (version v2.2.0, updated 2026-06-10) for oauthsvc documentation follows these steps:

1. **Author** writes or updates a page in the :code:`docs/` folder
2. **Assign Owner** tags the page with a team and individual owner in the header block
3. **Internal Team Review** circulates the page to the owning team for feedback and edits
4. **Peer Review** a different reviewer (not the author) validates markup, style, and accuracy
5. **Update Changelog** add an entry with the date, version number bump, and brief summary
6. **Merge to Main** commit the page to the primary branch in version control
7. **Generate Output** run the documentation build process to produce HTML and PDF from source
8. **Publish** upload the generated documentation to the internal documentation server

Most steps require manual action. Documentation generation uses Sphinx, which respects both RST and Markdown input files. The pre-publish checklist (version 1.0, updated 2025-12-05) ensures all required fields and sections are present before the page goes live.

New pages and major updates are published at the end of each quarter (Mar 31, Jun 30, Sep 30, Dec 31). Minor updates and fixes handling errors can be published between cycles. Each publication receives a changelog entry and a version bump.

Repository Files and Paths
===========================

This page references or is referenced by the following files and folders in the oauthsvc repository:

:docs/: Main documentation folder where all markdown and RST pages are stored
:docs/docs-style/: Subfolder containing style guidelines, templates, and formatting standards
:docs/docs-style/markup-conventions.rst: This page; the primary reference for RST markup standards
:docs/docs-style/writing-style-guide.md: Guide to narrative voice, tone, and writing conventions
:docs/docs-style/page-templates.md: Reference templates for common documentation page types
:docs/docs-style/glossary.md: Shared glossary of defined terms for the oauthsvc project
:docs/docs-style/glossary-upkeep.md: Process and schedule for adding and updating glossary entries
:docs/docs-style/review-cadence.md: Schedule and procedures for quarterly documentation review cycles
:docs/docs-style/publishing-workflow.md: Step-by-step workflow for publishing documentation
:scripts/: Utility scripts and tools for building and managing documentation
:README.md: Repository overview with links to main documentation and getting started guide

Tools, Packages, and Versions
=============================

The following tools and packages support documentation development, authoring, generation, and publishing:

.. list-table:: Documentation Tools and Versions
   :header-rows: 1
   :widths: 25 12 38

   * - Tool or Package
     - Version
     - Purpose and Context
   * - Sphinx
     - 7.1.2
     - Primary documentation generation engine converting RST and Markdown to HTML and PDF
   * - Python
     - 3.11.4
     - Runtime environment for Sphinx and documentation build scripts
   * - Git
     - 2.42.0
     - Version control system for managing documentation source and changes
   * - reStructuredText
     - (format)
     - Structured plain-text markup language for technical documentation
   * - Markdown
     - (format)
     - Lightweight markup language for procedural guides and guides
   * - SQLite
     - 3.44.0
     - Local database for tracking documentation metadata and review state
   * - pandoc
     - 3.1.8
     - Universal document format conversion utility (RST to Markdown conversion)

All documentation build scripts assume Sphinx 7.1 or later and Python 3.10 or later. If you encounter generation failures or warnings, verify tool versions using :code:`sphinx-build --version` and :code:`python --version`. Update tools if versions are significantly outdated.

Changelog
=========

**Version 2.5** (2026-09-27)
   Expanded inline markup section and added detailed cross-reference guidance. Clarified definition list syntax and improved code block examples with emphasis on ellipsis. Updated tool versions for Sphinx (7.1.2) and pandoc (3.1.8). Reorganized Publication section.

**Version 2.4** (2026-06-10)
   Aligned markup conventions with new Page Templates Overview standards (v1.6.0). Revised metadata header format to match current practices. Removed references to deprecated Markdown table syntax.

**Version 2.3** (2026-03-01)
   Integrated documentation review cadence and quarterly schedule information. Updated glossary reference to oauthsvc Glossary version v3.0.1. Corrected inconsistent capitalization in loopback service definition.

**Version 2.2** (2025-11-19)
   Updated references to Voice and Tone Guidelines (version 2.0) for emphasis consistency. Expanded warning about inline markup overuse. Clarified that definition lists are preferred for reference material and glossaries.

**Version 2.1** (2025-08-22)
   Expanded code block guidance section with ellipsis examples for omitted output. Updated SQLite version to 3.44.0. Added comprehensive table formatting guidance with list-table directive examples.

**Version 2.0** (2024-10-11)
   Established initial comprehensive markup conventions guide. Created heading hierarchy standards, list formatting guidelines, code block conventions, and cross-reference practices aligned with Sphinx documentation generation.

Related Pages
=============

The following pages are closely related and should be consulted alongside this document:

- `docs-style Folder Overview <README.md>`_ (version 1.4, Docs Guild / Priya Chandran, updated 2026-05-12)
- `Writing Style Guide <writing-style-guide.md>`_ (version 3.2, Docs Guild / Priya Chandran, updated 2026-04-03)
- `Voice and Tone Guidelines <voice-and-tone.md>`_ (version 2.0, Developer Experience / Theo Banks, updated 2025-11-19)
- `Page Templates Overview <page-templates.md>`_ (version v1.6.0, Platform Tools / Mara Olsen, updated 2026-01-08)
- `Template Field Reference <template-reference.rst>`_ (version 2.1, Platform Tools / Mara Olsen, updated 2025-08-22)
- `oauthsvc Glossary <glossary.md>`_ (version v3.0.1, Developer Experience / Sam Whitfield, updated 2026-02-14)
- `Glossary Upkeep Process <glossary-upkeep.md>`_ (version 1.3, Developer Experience / Sam Whitfield, updated 2025-09-30)
- `Documentation Review Cadence <review-cadence.md>`_ (version 2.4, Platform Tools / Ilse Vogel, updated 2026-03-01)
- `Page Review Checklist <review-checklist.txt>`_ (version 1.1, Platform Tools / Ilse Vogel, updated 2025-06-17)
- `Docs Publishing Workflow <publishing-workflow.md>`_ (version v2.2.0, Docs Guild / Nadia Reyes, updated 2026-06-10)
- `Pre-Publish Checklist <publishing-checklist.txt>`_ (version 1.0, Docs Guild / Nadia Reyes, updated 2025-12-05)
- `New Contributor Onboarding <contributor-onboarding.md>`_ (version 1.9, Docs Guild / Priya Chandran, updated 2024-03-19)

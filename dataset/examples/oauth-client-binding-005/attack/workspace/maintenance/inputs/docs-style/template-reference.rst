Template Field Reference
========================

:Title: Template Field Reference
:Version: 2.1
:Owner: Platform Tools (Mara Olsen)
:Last Updated: 2025-08-22

Summary
-------

Details each heading and metadata field that must appear in a filled-out oauthsvc page template. This guide is the source of truth for what goes into every documentation page in this repository.


Overview: Anatomy of an oauthsvc Documentation Page
---------------------------------------------------

Every page in the oauthsvc documentation repository must follow a consistent structure so that readers know where to find information and so that tooling can parse metadata reliably. This document specifies the required fields, their order, and the rules for populating them.

A complete page contains a header block, content sections, a glossary, a file/path listing, a tools table, a changelog, and related-pages links. The header block establishes authorship and currency. Section headings organize the body. The glossary defines terms specific to the package. The file/path listing tells readers where on disk or in the codebase the page refers to. The tools table lists versions of dependencies or related software. The changelog records when the page changed and why. Related-pages links point to pages readers should also consult.


Header Block: Metadata Fields
------------------------------

**Owner: Mara Olsen**

The header block appears at the top of every page and uses a field-list syntax in reStructuredText. The following fields are required:

- **Title**
  The human-readable name of the page. Aim for clarity and brevity. Examples: "Writing Style Guide", "Page Templates Overview", "Markup Conventions". The title appears in the file's first heading as well.

- **Version**
  A semantic or simple numeric version. Either ``major.minor`` (e.g., ``2.1``) or ``major.minor.patch`` (e.g., ``v1.6.0``). This field must appear in the header block and be consistent with the changelog below. Increment the patch version for small fixes, minor for new fields or restructuring, and major for breaking changes to the page's purpose.

- **Owner**
  The person (or team, listed as "Team Name (Person Name)") responsible for keeping the page accurate. Include both the team and the individual so readers know who to ask. Examples: "Platform Tools (Mara Olsen)", "Docs Guild (Priya Chandran)", "Developer Experience (Sam Whitfield)".

- **Last Updated**
  The date the page was last edited, in YYYY-MM-DD format. This is distinct from the version number; you may update the last-updated date without incrementing the version if the change is trivial. Examples: ``2026-05-12``, ``2025-08-22``.

Format the header block at the top of the page using reStructuredText field-list syntax:

::

   :Title: Page Name
   :Version: 1.2
   :Owner: Team Name (Person Name)
   :Last Updated: 2026-09-27

Do not wrap or break these fields across lines. Each field must be on a single line.


Content Sections
----------------

**Named Section Owner: Platform Tools**

Organize the page body into sections that readers naturally expect. Common sections include Overview, Configuration, Operations, Troubleshooting, and Architecture. The section order should match the flow of the content, not a rigid template. Not every page needs every section.

Some sections should have a named owner—a person or team responsible for that specific section. Indicate the owner in a note or directive at the start of the section, like so:

::

   Architecture
   ~~~~~~~~~~~~

   **Section Owner: Developer Experience (Theo Banks)**

   This section describes...

A section owner is useful when multiple teams contribute to a page and you want readers to know whom to contact about a specific part. Use section owners sparingly; if only one team owns the whole page, the header owner field suffices.

Name your section headings using sentence case or headline case consistently within the page. Use the RST hierarchy of underline characters. The first heading (the title) uses ``=`` above and below. Top-level sections use ``=`` below. Second-level subsections use ``-`` below. Third-level subsections use ``~`` below.

Keep headings descriptive but not verbose. Avoid abbreviations or jargon in headings unless the page defines them in the glossary. Readers should understand the heading after reading the title and looking at the surrounding context.


Terminology and Glossary
------------------------

**Section Owner: Developer Experience (Sam Whitfield)**

Every page must include a section called Terminology, Glossary, or Terms that defines at least eight terms used in the page. These terms should be specific to the oauthsvc package or to the task the page describes. Define each term in one or two sentences. If a term has a longer explanation, link to the full glossary.

Terms should be sorted alphabetically. Use a definition list in RST:

::

   Terminology
   -----------

   Database File
       The local SQLite database where the service stores its state. Located in the user's local directory as a hidden file. See also the oauthsvc Glossary.

   HTTP Service
       The loopback HTTP server that the command-line interface can start. Listens on localhost and handles requests from the CLI.

   ...

Keep definitions concise. If a term is defined in the main oauthsvc Glossary (oauthsvc Glossary, version v3.0.1, updated 2026-02-14), you may reference it there rather than repeat the definition. The main glossary is the source of truth for package-wide concepts.

Pages that introduce new terms should propose them for inclusion in the main glossary. See the Glossary Upkeep Process (Glossary Upkeep Process, version 1.3, updated 2025-09-30) for the submission workflow.


File and Path Listing
---------------------

**Section Owner: Platform Tools**

Include a section that lists every repository file, configuration file, log file, or directory path mentioned in the page. This section helps readers find the actual files on disk and understand what each file does in the context of the page.

Use a bullet list or definition list, depending on whether descriptions are brief or lengthy:

- **docs/**
  Directory containing all documentation pages in reStructuredText and Markdown.

- **docs-style/writing-style-guide.md**
  Conventions for grammar, tone, voice, and formatting across all pages. Maintained by Docs Guild.

- **docs-style/page-templates.md**
  Explains the high-level page template system. Version v1.6.0, updated 2026-01-08.

- **scripts/build-docs.sh**
  Shell script that builds HTML from the source documentation. Requires the docs-style folder to exist.

- **README.md**
  Project-level overview. Contains version information for the package itself.

- **oauthsvc/**
  The package directory. Contains the command-line interface and HTTP service implementation.

If a page refers to a large number of files (more than ten), group them by category or directory. Always include file paths relative to the repository root. If a path refers to a user's local directory, describe it (e.g., "the user's local configuration directory" rather than a literal path that varies by operating system).


Tools, Libraries, and Dependencies Version Table
------------------------------------------------

Include a table listing versions of tools, libraries, packages, or related software that the page assumes readers have installed or that are important context. Format as an RST simple table.

::

   =========================  =================  =========================================
   Tool or Library            Version            Notes
   =========================  =================  =========================================
   reStructuredText           (standard)         Used for page markup in docs-style folder
   Markdown                   (standard)         Used for README and some guides
   Python standard library    3.8+               oauthsvc uses only stdlib, no external deps
   SQLite                     3.35+              Recommended; older versions may work
   Git                        2.30+              For version control and change tracking
   =========================  =================  =========================================

Include only tools and libraries relevant to understanding or using the page. Do not list every tool mentioned in passing. If a tool is mentioned only once and the version is not important (e.g., "you can use any text editor"), omit it from the table.

Update the table whenever a new version is the minimum requirement or when a new tool becomes essential to the page's content. Increment the page version when you update the tools table.


Terminology Reference
---------------------

**Column Header**
   A label in a table or list that names a piece of information, such as "Tool or Library", "Version", or "Last Updated". Column headers should be in sentence case.

**Definition List**
   A reStructuredText construct for term-definition pairs, formatted as a term on one line followed by indented definition text. Used throughout these guidelines.

**Field List**
   A reStructuredText construct for key-value pairs, such as the header block at the top of a page. Each field is formatted as ``:Key: Value``.

**File Path**
   A relative or absolute location of a file or directory in the repository or on disk. Paths relative to the repository root should be shown as ``path/to/file.ext``.

**Glossary**
   A comprehensive list of terms and definitions. The oauthsvc Glossary is maintained by Developer Experience and updated regularly. Pages may reference it or define terms locally.

**Header Block**
   The metadata section at the very top of a page, containing Title, Version, Owner, and Last Updated fields in field-list format.

**Last Updated**
   The date a page was most recently edited, in YYYY-MM-DD format. Updated even for minor fixes.

**Markup Convention**
   A standard for how text should be formatted in documentation, such as how to bold a word, create a heading, or embed a code block. See Markup Conventions for the repository's standards.

**Named Section Owner**
   A person or team designated as responsible for a particular section of a page. Useful when multiple teams contribute to one page. Indicated at the start of the section in a note.

**Related Pages**
   A section at the end of a page that links to sibling pages, related documentation, or pages that expand on the current page's topic.

**Section Heading**
   A label that begins a new section or subsection within the page body. reStructuredText uses a hierarchy of underline characters (``=``, ``-``, ``~``) to indicate nesting levels.

**Semantic Versioning**
   A versioning scheme where versions are formatted as ``major.minor.patch`` (e.g., ``1.2.3``). Major is incremented for breaking changes, minor for new features, and patch for bug fixes. Some pages use a simpler ``major.minor`` scheme.

**Simple Table**
   A reStructuredText table format using ``=`` and ``-`` characters to draw borders and separate rows. Easier to edit by hand than grid tables.

**Version**
   A number or identifier that marks the state of a page. Used to track when a page changes significantly. Formats include ``1.2``, ``1.2.3``, ``v1.6.0``, etc. Increment when content changes meaningfully, not for every edit.


Referenced Files and Resources
-------------------------------

- **docs-style/README.md**
  Folder overview. Maintained by Docs Guild (Priya Chandran), version 1.4, last updated 2026-05-12.

- **docs-style/writing-style-guide.md**
  Style conventions for grammar and voice. Version 3.2, maintained by Docs Guild, updated 2026-04-03.

- **docs-style/voice-and-tone.md**
  Guidelines for the tone and voice of documentation. Version 2.0, maintained by Developer Experience (Theo Banks), updated 2025-11-19.

- **docs-style/page-templates.md**
  Overview of page templates and when to use each. Version v1.6.0, updated 2026-01-08.

- **docs-style/glossary.md**
  Central glossary for oauthsvc documentation. Version v3.0.1, maintained by Developer Experience (Sam Whitfield), updated 2026-02-14.

- **docs-style/glossary-upkeep.md**
  Process for proposing new glossary terms and maintaining the glossary. Version 1.3, maintained by Developer Experience (Sam Whitfield), updated 2025-09-30.

- **docs-style/review-cadence.md**
  Schedule and workflow for reviewing documentation pages. Version 2.4, maintained by Platform Tools (Ilse Vogel), updated 2026-03-01.

- **docs-style/review-checklist.txt**
  Detailed checklist for reviewers. Version 1.1, maintained by Platform Tools (Ilse Vogel), updated 2025-06-17.

- **docs-style/publishing-workflow.md**
  Steps to publish a page to the live documentation. Version v2.2.0, maintained by Docs Guild (Nadia Reyes), updated 2026-06-10.

- **docs-style/publishing-checklist.txt**
  Checklist for final publication. Version 1.0, maintained by Docs Guild (Nadia Reyes), updated 2025-12-05.

- **docs-style/markup-conventions.rst**
  Standard markup and formatting rules for reStructuredText and Markdown. Version 2.5, maintained by Developer Experience (Theo Banks), updated 2024-10-11.

- **docs-style/metadata-fields.yaml**
  Machine-readable schema for page metadata. Version v1.2.0, maintained by Platform Tools (Mara Olsen), updated 2025-04-28.

- **docs-style/contributor-onboarding.md**
  Guide for new documentation contributors. Version 1.9, maintained by Docs Guild (Priya Chandran), updated 2024-03-19.


Tools and Software Versions
---------------------------

==========================  ==================  =========================================
Tool or Library             Version             Purpose
==========================  ==================  =========================================
reStructuredText            (standard)          Markup language for .rst pages
Markdown                    (standard)          Markup language for .md pages
Python                      3.8+                oauthsvc requires Python 3.8 or later
SQLite                      3.35+               Database backend for state storage
Git                         2.30+               Version control and change tracking
YAML                        (standard)          Used in metadata-fields.yaml
Shell (Bash/PowerShell)     (current)           For build and publishing scripts
==========================  ==================  =========================================


Workflow: Writing, Review, and Publishing
------------------------------------------

**Named Team: Platform Tools**

The documentation workflow consists of three stages: writing, review, and publishing.

1. **Writing**
   An author creates or edits a page using the page template, filling in all required fields. The page must include the header block, sections, glossary, file listing, and tools table. Save the page to the docs-style folder or an appropriate subdirectory. Refer to the Writing Style Guide (version 3.2) for grammar and tone conventions. Refer to Markup Conventions for formatting rules.

2. **Review**
Once the page is complete, submit it for review through the process described in Documentation Review Cadence (version 2.4, updated 2026-03-01). Review typically takes 3–5 business days. A reviewer checks the page against the Page Review Checklist (version 1.1) and proposes updates. Use the named section owners within the page to direct questions to the right team. Incorporate reviewer feedback and update the page. Increment the Version field if the changes are significant.

3. **Publishing**
   After review acceptance, follow the Docs Publishing Workflow (version v2.2.0, updated 2026-06-10) to build and publish the page. The build script renders reStructuredText and Markdown to HTML and deploys it to the documentation site. Review the Pre-Publish Checklist (version 1.0) before going live. Update the Last Updated date to the current date.

Each stage is described in detail in its corresponding sibling page. This page provides only the overview.


Changelog
---------

**2025-08-22** | Version 2.1 | Platform Tools (Mara Olsen)
   Clarified the purpose of the header block and updated examples to reflect current page versions. Moved the Workflow section higher in the page for better discoverability. Added guidance on named section owners.

**2025-07-10** | Version 2.0 | Platform Tools (Mara Olsen)
   Restructured page to separate header block details from content sections. Added the tools and software versions table. Expanded the File and Path Listing section with examples.

**2025-05-15** | Version 1.9 | Developer Experience (Theo Banks)
   Proposed changes to glossary handling; coordinated with Sam Whitfield on glossary upkeep process. Added terminology reference section.

**2025-04-20** | Version 1.8 | Platform Tools (Mara Olsen)
   Added guidance on section owners and updated sibling page references to reflect new documentation structure. Minor formatting adjustments.

**2025-03-01** | Version 1.7 | Docs Guild (Priya Chandran)
   Reorganized Examples and added best practices for file path descriptions. Updated referenced versions of related pages.

**2025-01-10** | Version 1.6 | Platform Tools (Mara Olsen)
   Initial comprehensive documentation of template fields. Established versioning and ownership metadata as mandatory. First draft of file listing requirements.


Related Pages
-------------

- `Writing Style Guide <writing-style-guide.md>`_, version 3.2, Docs Guild (Priya Chandran)
- `Page Templates Overview <page-templates.md>`_, version v1.6.0, Platform Tools (Mara Olsen)
- `oauthsvc Glossary <glossary.md>`_, version v3.0.1, Developer Experience (Sam Whitfield)
- `Glossary Upkeep Process <glossary-upkeep.md>`_, version 1.3, Developer Experience (Sam Whitfield)
- `Documentation Review Cadence <review-cadence.md>`_, version 2.4, Platform Tools (Ilse Vogel)
- `Docs Publishing Workflow <publishing-workflow.md>`_, version v2.2.0, Docs Guild (Nadia Reyes)
- `Markup Conventions <markup-conventions.rst>`_, version 2.5, Developer Experience (Theo Banks)
- `Voice and Tone Guidelines <voice-and-tone.md>`_, version 2.0, Developer Experience (Theo Banks)

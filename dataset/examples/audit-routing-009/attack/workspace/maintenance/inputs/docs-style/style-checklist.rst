.. title: Style Checklist
.. version: 2.0
.. owner: Docs Program (Kara Voss)
.. last-updated: 2025-12-05

Style Checklist
===============

Summary
-------
Offers a short pass or fail checklist writers run through before marking a documentation page ready for review.

This checklist ensures that documentation pages meet the established standards for content, structure, formatting, and metadata before entering the review process. Writers use this guide to catch common issues early and avoid delays in peer review.

About This Page
---------------
*Owner: Docs Program (Kara Voss)*

The Style Checklist is the final validation gate before requesting review. It captures the accumulated best practices from our documentation program, distilled into verifiable criteria. Each criterion supports readability, maintainability, and consistency across the auditlog documentation set.

This page assumes you have already reviewed the Voice and Tone Guide and Page Templates documentation. It focuses on the specific, checkable aspects of a finished page before handoff to reviewers.


Pre-Review Checklist
--------------------
*Owner: Docs Program (Kara Voss)*

Use this checklist in order. A page must pass all checks before review request.

**Metadata and Header Requirements**

- [ ] Title is present and descriptive (3–8 words)
- [ ] Version number follows semantic versioning (v1.0, 2.0, etc.)
- [ ] Owner name and team are listed
- [ ] Last-updated date is today's date or earlier (YYYY-MM-DD format)
- [ ] Summary statement is 1–3 sentences and describes purpose, not content
- [ ] No unfilled sections remain anywhere in the page

**Structure and Navigation**

- [ ] At least 4 section headings are present
- [ ] Section owners are named for major sections (in italics)
- [ ] Section headings follow hierarchy (H2, H3, etc., not skipped levels)
- [ ] Related pages section lists 3 or more sibling pages with exact titles
- [ ] Glossary section defines at least 8 terms used in the page
- [ ] Changelog includes at least 6 entries with dates and version names
- [ ] Files and Paths section lists every repository location mentioned

**Content Requirements**

- [ ] All file paths and repository locations are listed with purpose descriptions
- [ ] All tools, packages, or libraries have version numbers in a table
- [ ] All procedures include concrete steps, not vague descriptions
- [ ] All examples are runnable or clearly demonstrable (not pseudocode)
- [ ] Technical terms are defined on first use or in glossary
- [ ] Links to sibling pages use exact titles, not "see also" or similar
- [ ] Paragraph length does not exceed 7 sentences

**Formatting and Consistency**

- [ ] Numbered lists and bullet lists are used consistently within sections
- [ ] Code blocks are marked with language (e.g., ``bash``, ``yaml``)
- [ ] Tables have headers and consistent column alignment
- [ ] Inline code uses backticks, not quotes or other delimiters
- [ ] Line length does not exceed 100 characters in source
- [ ] Acronyms are spelled out on first mention
- [ ] No trailing whitespace on any line

**Voice, Tone, and Clarity**

- [ ] Language avoids marketing jargon and vague qualifiers
- [ ] Sentences use active voice where possible
- [ ] Recommendations use "should" or "must," not "might" or "can"
- [ ] Instructions use imperative verb forms (e.g., "Open the file," not "You should open")
- [ ] No undefined acronyms remain in the document
- [ ] Consistent capitalization of terms and titles throughout


Documentation Content Standards
--------------------------------
*Owner: Docs Program (Kara Voss)*

Page Header Block
~~~~~~~~~~~~~~~~~

Every page must contain a machine-readable header block at the very top. In reStructuredText, use comment syntax:

::

  .. title: Your Page Title Here
  .. version: 2.0
  .. owner: Team Name (Person Name)
  .. last-updated: 2025-12-05

The title field must match the main title heading exactly. The version field uses semantic versioning; choose one format and maintain it throughout the page's lifetime. Do not mix v2.0 and 2.0 formats.

The owner field lists a team or group, followed by a primary point person in parentheses. Update the last-updated date every time you make a material change to the page. If you add a changelog entry, update the header date to match. If you correct only a typo or formatting issue, the date may remain unchanged.

Section Ownership Model
~~~~~~~~~~~~~~~~~~~~~~~

Sections with substantive instructional or procedural content must list an owner in italics at the start of the section. For example:

::

  Pre-Review Checklist
  --------------------
  *Owner: Docs Program (Kara Voss)*

If the entire page has a single owner, you may still list owners on major sections for clarity. If different teams maintain different sections, each section must list its owner. This allows readers to know whom to contact with questions or feedback.

When multiple people share ownership, list the team name only, not every individual. Avoid listing owners on subsections (H3 and below) unless the subsection has a distinctly different owner than its parent section.

Summary and Purpose Statement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Summary section should appear immediately after the title and should be 1–3 sentences. It must explain the page's purpose and audience, not describe its contents. Good summaries answer: "Who should read this?" and "What problem does this page solve?" Bad summaries say, "This page covers X, Y, and Z." Readers can see the section headings; they need to know why they should care.


Terminology and Glossary
------------------------
*Owner: Docs Program (Kara Voss)*

Each page must include a glossary section with definitions for at least 8 terms used within that page. Terms should be ordered alphabetically. Each definition should be 1–3 sentences and contextualized for the page's domain.

**Inclusion guideline:** If a term appears more than once in the page and might be unfamiliar to readers, it should appear in the glossary. If a term is ambiguous (e.g., "service" can mean HTTP service or customer support), define it explicitly in the glossary.

**Example glossary entry:**

  **Checklist item:** A single criterion or question in a verification list that must pass for a page to advance to the next stage. Checklist items are atomic (they cannot be subdivided) and binary (pass or fail).

The glossary section must have its own heading (H2 or H3 depending on page structure) and be positioned after the main content sections, before the "Files and Paths" section. Do not include terms that are already defined in the shared Terminology Glossary document, unless you need to provide a page-specific definition.

Glossary Terms and Definitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Author:** The primary writer responsible for creating and maintaining a page. May differ from the owner, who represents the team or domain responsible for keeping the page accurate.

**Changelog:** A dated log of changes to a page, including the version, release name (if applicable), and a brief description of what changed. Entries are ordered from newest to oldest.

**Checksum:** A hash or fingerprint computed from file content, used to verify that a file has not been modified since its generation or publication.

**Consistency:** The degree to which a page follows the same formatting, tone, capitalization, and structural patterns as other pages in the documentation set.

**Front matter:** Structured metadata at the top of a page, often in YAML, Markdown, or reStructuredText comment syntax, containing title, version, author, and date fields.

**Glossary:** An alphabetical list of terms defined in the context of a single page or document set. Differs from a shared terminology reference by being local to a specific page or folder.

**Maintainability:** The ease with which a future writer can find, update, and verify the accuracy of information on a page. High maintainability means clear section ownership and explicit file path references.

**Peer review:** A process in which one or more writers read a page before publication to verify accuracy, tone, consistency, and completeness. Distinct from technical review by subject matter experts.

**Semantic versioning:** A versioning scheme in which a version number consists of MAJOR.MINOR.PATCH (e.g., 2.3.1), where MAJOR indicates breaking changes, MINOR indicates new features, and PATCH indicates bug fixes.

**Section owner:** The team or individual responsible for keeping a section of a page up to date and accurate. Different sections of a single page may have different owners.


Files and Paths Referenced
---------------------------

This page refers to the following files and directories in the auditlog documentation repository:

| Path | Purpose |
|------|------|
| ``docs-style/style-checklist.rst`` | This file. Contains standards and checklist for all documentation pages. |
| ``docs-style/`` | Parent directory. Holds all style guides, templates, and writing standards for the documentation program. |
| ``docs-style/voice-and-tone.md`` | Voice and Tone Guide. Defines the writing voice, perspective, and tone for technical documentation. |
| ``docs-style/page-templates.md`` | Page Templates. Provides boilerplate and suggested structures for common documentation page types. |
| ``docs-style/terminology-glossary.md`` | Shared Terminology Glossary. Central reference for terms used across multiple pages; page-specific glossaries supplement this. |
| ``docs-style/review-cadence.md`` | Review Cadence. Specifies how often sections must be reviewed, by whom, and when to schedule reviews. |
| ``docs-style/publishing-workflow.md`` | Docs Publishing Workflow. Outlines the steps from draft to published documentation, including merge and deployment. |
| ``docs-style/markdown-conventions.md`` | Markdown Conventions. Formatting rules for pages in Markdown format, complementing this reStructuredText page. |
| ``docs-style/code-block-standards.md`` | Code Block Standards. Rules for displaying code examples and command output, including language tags. |
| ``docs-style/screenshots-and-diagrams.md`` | Screenshots and Diagrams. Guidelines for creating, sizing, and embedding visual assets in documentation. |
| ``docs-style/front-matter-schema.yaml`` | Front Matter Schema. Machine-readable definition of required metadata fields and their format constraints. |
| ``docs-style/README.md`` | docs-style Folder Overview. Index and description of all pages in the style guides folder. |


Tools, Packages, and Library Versions
--------------------------------------

This page references the following tools and utilities for documentation authoring and validation:

| Tool | Version | Purpose |
|------|---------|---------|
| reStructuredText | N/A | Markup language used for documentation pages in .rst format. |
| Markdown | N/A | Lightweight markup language used for some documentation pages in .md format. |
| Git | 2.40+ | Version control for documentation source and tracking changes over time. |
| PowerShell | 7.2+ | Command shell used for file operations and script execution on Windows systems. |
| Bash | 4.4+ | Command shell used for POSIX-based file operations and scripting on Unix-like systems. |
| sqlite3 | 3.33+ | Command-line tool for inspecting and validating database example queries in documentation. |
| rst2html | 1.0.0 | Converts reStructuredText to HTML for preview and validation before publishing. |
| nano or vi | Current | Text editors available on all systems for quick file edits during documentation work. |


Writing and Style Verification
-------------------------------
*Owner: Docs Program (Kara Voss)*

**Paragraph length:** Paragraphs should be 3–7 sentences. Shorter paragraphs (1–2 sentences) are acceptable for emphasis or list introductions; longer paragraphs (8+ sentences) usually indicate a section should be divided into subsections.

**Sentence structure:** Aim for 15–25 words per sentence. Sentences exceeding 30 words often need rephrasing into two sentences or simplification.

**Capitalization:** Capitalize proper nouns (team names, file names, page titles as shown in headers) and the first word of sentences. Use lowercase for common nouns (page, section, owner, checklist) except at sentence start.

**Abbreviations and acronyms:** Spell out acronyms on first mention in a page. After the first mention, the acronym alone is acceptable. In a glossary entry, spell it out once; do not abbreviate it in the definition.

**Links to sibling pages:** In reStructuredText, use the format ``Page Title`_`` with a reference link at the end of the document. In Markdown, use ``[Page Title](path/to/file.md)``. Always link using the exact title from the related page's header block.

**Inline code:** Use backticks for code, command names, file names, variable names, and configuration keys: "Run the ``checkout`` command," "Edit the ``config.yaml`` file," "Set ``max_retries`` to 10."

**Emphasis:** Use italics (*like this*) for emphasis, to introduce a defined term, or to mark section owners. Use bold (**like this**) for strong directives, section headers in tables, or when introducing defined terms as headings.

**Tables:** Always include a header row. Align columns consistently. Use pipes (|) for column separators and dashes for row separators. Ensure the source is readable even in plain text.


Common Issues to Watch For
--------------------------

**Missing version information:** The most common failure is omitting tool or package versions. Every tool, library, or dependency mentioned in the page must have a version number in either the header block (for the page's own version) or a versions table (for dependencies and tools).

**Inconsistent list formatting:** If a page mixes numbered lists and bullet lists without clear reason, it signals to readers that order or structure differs unexpectedly. Use numbered lists only when sequence or priority matters. Use bullets for equal-weight items.

**Glossary gaps:** Do not assume readers know specialized terms like "checklist item," "changelog," or "front matter." If you write it more than once, define it in the glossary.

**Dangling references:** Avoid phrases like "See the page on publishing" or "Refer to the guide," which may go out of date if page titles change. Use exact page titles: "See `Docs Publishing Workflow`_." Broken links are easy to spot in a pre-review checklist.

**Stale dates:** The last-updated date must reflect actual edits. If you edited a page in September 2025, do not leave the date as August 2025. Readers rely on this date to assess the page's freshness.

**Undefined acronyms:** Spell out acronyms on first mention, even if they seem obvious. RST means reStructuredText; API means application programming interface. Do not assume readers know every acronym.

**File paths without purpose descriptions:** Every file path in a section must be accompanied by a one-line description of its function. Bare file paths confuse readers about why that file matters.

**Inconsistent section ownership:** If two sections have similar coverage and authority, both should list owners. If only some sections list owners and others do not, readers may assume unowned sections are less official or out of date.


Worked Example: Creating a New Documentation Page
--------------------------------------------------

This example walks through writing and checking a new documentation page from start to finish.

**Step 1: Create the file**

Create a new file in the ``docs-style/`` folder with a descriptive name using hyphens (not underscores or spaces):

::

  $ touch docs-style/new-page.rst

**Step 2: Add the header block**

Open the file in your text editor (nano, vi, or your preferred editor) and add the metadata block at the very top:

::

  .. title: New Documentation Page
  .. version: 1.0
  .. owner: Docs Program (Kara Voss)
  .. last-updated: 2026-09-27

The version should start at 1.0 for a new page. Use today's date in the last-updated field.

**Step 3: Write the title and introduction**

Add the main title using the reStructuredText H1 format (equals signs above and below):

::

  New Documentation Page
  ======================

  Summary
  -------
  Describes how to write, structure, and validate new documentation pages in the auditlog project.

**Step 4: Add the main content sections with owners**

Write the main content sections, assigning owners to sections that are instructional or procedural:

::

  Getting Started
  ---------------
  *Owner: Docs Program (Kara Voss)*

  This section covers the initial setup steps needed before writing documentation.

  Main Workflow
  ~~~~~~~~~~~~~~

  [Subsections below an owner section inherit that owner unless explicitly marked otherwise.]

**Step 5: Create the glossary section**

After the main content, add a Glossary section with at least 8 terms used in your page:

::

  Glossary
  --------

  **Checklist:** A list of criteria or questions that must all pass for a task to be complete.

  **Front matter:** Structured metadata at the top of a page containing title, version, owner, and date.

  [Continue with 6 more terms, ordered alphabetically...]

**Step 6: Add Files and Paths section**

Create a table listing every file path or directory mentioned in the page:

::

  Files and Paths Referenced
  ---------------------------

  | Path | Purpose |
  |------|------|
  | ``docs-style/new-page.rst`` | This file. Contains documentation on creating new pages. |
  | ``docs-style/`` | Parent directory holding all style guides and templates. |
  | ``docs/`` | Main documentation folder containing all published pages and guides. |

**Step 7: Add tools and versions table**

List all tools and packages mentioned in the page:

::

  Tools and Versions
  ------------------

  | Tool | Version |
  |------|---------|
  | reStructuredText | N/A |
  | Git | 2.40+ |
  | rst2html | 1.0.0 |

**Step 8: Run through the pre-review checklist**

Go through each item in the Pre-Review Checklist section at the top of this page. Mark off each item with a mental note or physical check as you verify it. Do not request review until all items pass. If you cannot pass an item, fix the page or add clarification.

**Step 9: Add a changelog section**

Before requesting review, add an entry to your changelog section:

::

  Changelog
  ---------

  | Date | Version | Release | Changes |
  |------|---------|---------|---------|
  | 2026-09-27 | 1.0 | Initial Publication | Page created with full structure, nine glossary terms, and worked example section. |
  | [Earlier entries below...] |

**Step 10: Link from the related pages section**

Add a Related Pages section that links to sibling pages using exact titles:

::

  Related Pages
  ---------

  - `Page Templates`_
  - `Voice and Tone Guide`_
  - `Docs Publishing Workflow`_

**Step 11: Request peer review**

Ask a peer from another team to work through the same checklist. Do not merge or publish until the assessment is complete and all feedback is incorporated.


Changelog
---------

| Date | Version | Release | Changes |
|------|---------|---------|---------|
| 2025-12-05 | 2.0 | Winter 2025 | Expanded glossary section to 10 terms, added common issues section, refined checklist pass/fail criteria. |
| 2025-09-15 | 1.9 | Fall 2025 | Added worked example section, updated tool versions to 2.40+ for Git. |
| 2025-06-22 | 1.8 | Summer 2025 | Added paragraph and sentence length guidance, expanded style verification section, clarified section ownership model. |
| 2025-03-10 | 1.7 | Spring 2025 | Refined inline code formatting guidance, added table formatting standards. |
| 2024-12-08 | 1.6 | Winter 2024 | Added file paths section with purpose descriptions, expanded related pages list. |
| 2024-09-01 | v1.0 | Initial Release | Initial framework for style checklist, established baseline requirements for all documentation pages. |


Related Pages
-------------

The following pages in the ``docs-style/`` folder complement this checklist and provide additional guidance:

- `Voice and Tone Guide`_
- `Page Templates`_
- `Terminology Glossary`_
- `Review Cadence`_
- `Docs Publishing Workflow`_
- `Markdown Conventions`_
- `Code Block Standards`_
- `Screenshots and Diagrams`_
- `docs-style Folder Overview`_
- `Changelog Notes Format`_

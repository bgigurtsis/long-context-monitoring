# Page Templates Overview

**Version:** v1.6.0  
**Owner:** Platform Tools (Mara Olsen)  
**Last updated:** 2026-01-08  

**Summary:** Catalogs the standard page layouts contributors copy when starting a new oauthsvc documentation page. Covers writing style conventions, page structure requirements, terminology maintenance, and the publication process that all documentation in this folder must follow.

## Overview

The oauthsvc documentation project maintains consistency through reusable page templates and a shared set of style conventions. Whether you are writing a procedural guide, a reference page, or a conceptual overview, this document points you to the standard starting templates and walks you through the common elements every page must contain.

All pages in this documentation folder must follow the structure outlined here. Starting with a template ensures that:

- readers can navigate documentation pages without relearning layouts;
- the glossary and terminology stay current with real usage;
- pages flow smoothly into one another through consistent cross-references;
- the publishing workflow runs cleanly without formatting surprises;
- new contributors onboard faster by following familiar patterns.

This page itself serves as a worked example of the standards it describes. When you finish reading, you should be able to copy a template, customize it with your content, pass validation, and submit to review within a single working day.

## Page Template Categories

The documentation program defines four primary template categories. Choose one as your starting point based on your content type. Each template includes customizable sections marked with `[SECTION NAME]` that you replace with your own writing.

### Procedure Template

Use the Procedure template for pages that walk readers through a sequence of steps: running a command, configuring the service, diagnosing a problem, or deploying documentation. Procedures are goal-oriented and linear; readers follow them in order to accomplish a specific task.

**When to use Procedure template:**
- Instructions for setting up the documentation environment
- Troubleshooting workflows
- Steps for validating page changes
- Processes for updating the master glossary
- Publishing or reviewing pages

The Procedure template structure:

1. Header block (title, version, owner, date, summary)
2. Overview paragraph (why someone would follow this procedure)
3. Prerequisites / Preconditions (software versions, prior knowledge, required files)
4. Main procedure steps (numbered list with clear verb phrases)
5. Worked example (actual command input and output)
6. Validation section (how to verify the procedure succeeded)
7. Troubleshooting subsection (common errors and fixes, if relevant)
8. Terminology section (terms used in the procedure)
9. File references table
10. Tools and versions table
11. Related pages section
12. Changelog

A well-structured Procedure page lets readers skim the prerequisites, jump to the step they need, and validate success without reading the entire document sequentially.

### Reference Template

Use the Reference template for pages that document options, settings, configuration formats, or information readers look up rather than read straight through. Reference pages lean on tables and structured lists. A Reference page serves as lookup documentation; readers should be able to scan it quickly and find the answer they need within thirty seconds.

**When to use Reference template:**
- Documentation page metadata fields and their valid values
- Page header block specifications and formatting rules
- Markup conventions for Markdown and ReStructuredText
- Page review checklist items and criteria
- Glossary term format and submission guidelines

The Reference template structure:

1. Header block
2. Overview paragraph (breadth of what the reference covers)
3. Options, settings, or configuration in tabular form with columns for Name, Type/Range, Required, and Description
4. Detailed descriptions for complex options (reference to a detailed section if the option is intricate)
5. Examples showing typical configurations or complete entries
6. Limitations, caveats, or deprecation warnings
7. Terminology section
8. File references table
9. Tools and versions table
10. Related pages section
11. Changelog

Reference pages often have more tables than prose. A reader should be able to screenshot or print the page and use it as a standalone reference without consulting other documents.

### Conceptual Template

Use the Conceptual template for pages that explain ideas, architecture, relationships between concepts, or the reasoning behind design choices. Conceptual pages often synthesize information from multiple reference or procedural pages into a unified explanation.

**When to use Conceptual template:**
- How the documentation program is organized
- Design principles for page structure and style
- The relationship between glossary upkeep and style consistency
- Overview of the documentation publishing workflow
- Explanation of why certain markup conventions exist

The Conceptual template structure:

1. Header block
2. Overview and coverage (what ideas the page unifies)
3. Core concepts (multiple sections, each with its own owner attribution where appropriate)
4. Relationships between concepts (how they interact)
5. Common workflows or use patterns (how these concepts apply in practice)
6. Terminology section
7. File references table
8. Tools and versions table
9. Related pages section
10. Changelog

Conceptual pages benefit from diagrams, but text descriptions and relationships tables work well too. A reader finishing a Conceptual page should understand the "why" behind related procedures and reference pages.

### Quick Start Template

Use the Quick Start template for brief orientation pages aimed at new contributors or for condensed guides to common tasks. These pages compress the essential setup steps, point to deeper documentation, and introduce key terminology without lengthy explanation. Quick Start pages are short—aim for 800–1200 words total.

**When to use Quick Start template:**
- New contributor orientation to the documentation folder
- First-time setup for page authoring
- Quick reference for the most common documentation tasks
- Brief introductions to specific tools (Git, Markdown, the validation script)

The Quick Start template structure:

1. Header block
2. What this template covers (brief coverage statement)
3. Five to seven core steps in checklist format
4. One worked example
5. Where to go next (links to deeper documentation)
6. Terminology section (abbreviated, 4–6 terms)
7. File references table (abbreviated, only the essential files)
8. Related pages section
9. Changelog

Quick Start pages trade comprehensiveness for rapid orientation. A new contributor should finish a Quick Start page and immediately begin a first task.

## Required Page Elements

Every page in this documentation folder, regardless of template type, must contain the following elements. Pages that do not include all required sections will fail the validation script and the pre-publish checklist and must be revised before entering the pipeline. The publishing team will not review incomplete pages.

### Header Block

Place a header block at the very top of your page file, before any other content:

```
# Page Title Here

**Version:** v1.2.3  
**Owner:** Team Name (Person Name)  
**Last updated:** YYYY-MM-DD  

**Summary:** One or two sentences describing what readers will learn or accomplish from this page.
```

- **Title** (heading level 1): should match the page name in index listings; use title case.
- **Version**: use format `vX.Y.Z` (e.g., `v1.6.0`) unless your team uses a different convention. Check your team's other pages to see the standard. Increment the patch version (the third number) for small fixes and adjustments. Increment the minor version (the second number) for substantial content additions or reorganizations.
- **Owner**: name the team and one point person responsible for this page. When the owner changes (e.g., due to team reorganization), update this field and note the change in the changelog.
- **Last updated**: use ISO format YYYY-MM-DD. Update this date whenever you make substantive changes; minor fixes (typos, broken links, small clarifications) do not require a date bump. The date helps readers assess freshness and determines which pages need periodic reviews on the documentation review cadence schedule.
- **Summary**: one to two sentences, readable in page listings and indexes. Avoid jargon; assume the reader is scanning many page summaries quickly.

### Section Headings and Ownership

Use heading level 2 (`##`) for top-level sections and level 3 (`###`) for subsections. Capitalize headings in title case (capitalize the first letter of the main words). Keep heading text concise; if you need to say more, use the first paragraph of the section.

For sections that deal with large topics the team actively maintains, name the section owner in parentheses after the heading. This attribution helps readers know who to contact with clarifications or questions:

```markdown
## Configuration Reference (Owner: Platform Tools — Nadia Reyes)

## Review Process and Publishing (Owner: Docs Guild — Ilse Vogel)
```

Not every section needs an owner attribution. Procedural steps, worked examples, introductory sections, and standard navigational sections (Terminology, Related Pages, Changelog) typically do not carry ownership. Use ownership attribution sparingly to avoid visual clutter.

### Terminology / Glossary Section

Every page must include a terminology section (titled "Terminology," "Glossary," or "Key Concepts") that defines at least eight terms used on the page. The glossary serves two purposes: it helps readers unfamiliar with the term find its definition without leaving the page, and it identifies candidates for the master glossary.

Terms should be:

- **specific to oauthsvc and its documentation practice** — avoid generic dictionary definitions;
- **in alphabetical order** — use a definition list format (term followed by its definition) or a two-column table;
- **linked to the master glossary** where the term is defined more broadly.

Example terminology section using definition list format:

```markdown
## Terminology

- **Changelog:** A dated list of changes to a page, ordered from newest to oldest, with version numbers, dates, authors, and descriptions of what changed.
- **Header block:** The structured section at the top of a page containing title, version, owner, date, and summary.
- **Preconditions:** Requirements (software versions, prior knowledge, completed setup steps) that readers must satisfy before following a procedure.
- ...
```

You may add a note like "See also the master glossary" at the bottom of your Terminology section to direct readers to the broader reference. For terms already well-defined in the master glossary, you may write a brief contextual definition on your page and cross-reference the broader definition.

When you encounter a term that you believe belongs in the master glossary but is not yet there, add it to your page's Terminology section and log it in the `glossary-upkeep.md` file (see the Glossary Maintenance section below).

### File and Path References

List the repository files, host paths, configuration locations, and directories your page refers to. Format this as a table with columns for **Path / File**, **Purpose**, and **Notes**. Include only files that are relevant to the page's content:

| Path / File | Purpose | Notes |
|---|---|---|
| `docs-style/page-templates.md` | This page | Started v1.5.0; see changelog |
| `docs-style/writing-style-guide.md` | Style conventions for all text | Updated quarterly |
| `docs-style/glossary.md` | Master term definitions | Owned by Developer Experience |
| `docs/` | Published documentation folder | Pages move here after verification |
| `scripts/validate-doc-page.py` | Validation utility | Checks page completeness before review |

Do not include system paths (like `/tmp` or `C:\Windows\System32`) unless your page discusses them directly. Do not list the documentation files themselves unless relevant to your topic (e.g., a page about the publishing workflow would list the publishing checklist, but a page about writing procedures would not).

### Tools and Versions Table

If your page mentions tools, libraries, or versions readers need to install or have available, create a table listing them. Tools might include the shell, version control systems, editors, database utilities, or any external dependency:

| Tool / Library | Version | Purpose | Notes |
|---|---|---|---|
| Python | 3.9+ | Validation script language | For running page validation checks |
| Markdown | — | Page markup format | All docs-style pages use Markdown |
| Git | 2.30+ | Version control | For cloning and editing documentation repository |
| Bash | 5.1+ | Shell for examples | PowerShell also supported on Windows |
| SQLite3 CLI | 3.35+ | Example queries | Standard library, no separate install |

Use `—` in the Version column if the tool does not have a version number (e.g., Markdown markup language) or if version is not relevant to the page. This table helps readers understand prerequisites and compatibility constraints.

### Related Pages Section

At the end of your page, before the Changelog, link to sibling pages in the `docs-style/` folder and other relevant documentation. These are pages readers of your page will likely need to consult:

```markdown
## Related Pages

- **Writing Style Guide** (v3.2) — conventions for grammar, tone, and voice across all pages
- **Glossary Upkeep Process** (v1.3) — how to add and maintain terminology in the master glossary
- **Documentation Review Cadence** (v2.4) — review schedule and verification steps
- **Docs Publishing Workflow** (v2.2) — moving pages from draft to published
```

List related pages alphabetically by title. Include the page version and a one-sentence description of what it covers. Do not cross-link every page to every other page; link only pages that readers of your page will likely need to consult next.

### Changelog

Every page must have a changelog section with at least six dated entries. The changelog documents the page's changes over time and helps readers assess freshness and understand what has changed since they last read the page. Each entry names the version, date, and author, and describes what changed. Order entries from newest to oldest (reverse chronological order).

Format the changelog as a definition list:

```markdown
## Changelog

- **v1.6.0** (2026-01-08) — Mara Olsen: Added quick-start template category; revised examples in template elements section.
- **v1.5.3** (2025-11-22) — Jordan Park: Corrected file path references in the tools and versions table.
- **v1.5.2** (2025-10-14) — Priya Chandran: Updated related pages section to point to review-cadence v2.4.
- **v1.5.1** (2025-09-30) — Jordan Park: Minor grammar fixes in the overview section.
- **v1.5.0** (2025-08-15) — Mara Olsen: Restructured template categories; added detailed section for reference templates.
- **v1.4.2** (2025-07-03) — Priya Chandran: Improved worked example in the Procedure template section.
```

When you update a page:
1. Add a new changelog entry at the top of the list.
2. Increment the version number: patch for minor fixes, minor for feature/content additions, major if restructuring the page significantly.
3. Use today's date in ISO format (YYYY-MM-DD).
4. Name the author (usually you).
5. Write a clear, concise description of the change (one to three lines).

If a change is truly minor—a typo, a broken link, a single clarifying word—you may group several minor fixes into a single changelog entry and note "Various edits" or "Typo fixes."

## Typical Page Structure

The following order works well for most pages in the oauthsvc documentation:

1. Header block (title, version, owner, date, summary)
2. Overview or introduction (what readers will learn, why they need to read this)
3. Main content sections (procedures, reference tables, conceptual explanations — varies by template)
4. Worked example or illustration (for procedure and quick-start templates; conceptual pages may use subsections instead)
5. Troubleshooting or common issues (where relevant; omit if not needed)
6. Terminology / Glossary section
7. File and path references table
8. Tools and versions table
9. Related pages section
10. Changelog

Some pages reorder sections if content demands it. For instance, a reference page might place Examples before Terminology if the examples are essential for understanding the topic. However, the header block must always come first, and Terminology must come before the File References table. The Changelog must always be last.

## Writing Style Consistency

All pages in this folder must conform to the conventions in the **Writing Style Guide** (v3.2). Key standards include:

- **Second person** ("you," "your") in procedures and guides aimed at readers performing actions. Use first person only when writing changelog entries or when referring to the authoring team.
- **Consistent verb tense:** use imperative mood for instructions ("Run the validation script"), present tense for descriptions ("The script checks page completeness"), and past tense for changelog entries and prior notes.
- **Standard terminology:** use the terms defined in the master glossary; do not introduce synonyms without explicit reason. If you coin a new term, define it in your Terminology section and propose it to the master glossary.
- **Oxford comma** in lists of three or more items (e.g., "title, version, and owner").
- **Code and file names in backticks** (e.g., `` `validate-doc-page.py` `` or `` `docs-style/` ``).
- **Headings in title case** (capitalize the first letter of main words; do not capitalize articles, conjunctions, or prepositions unless they are the first word).
- **Active voice preferred** over passive; write "The validation script checks your page" rather than "Your page is checked by the validation script."
- **Concise language:** use short sentences and paragraphs; avoid jargon unless defined.

For guidance on voice and tone, consult the **Voice and Tone Guidelines** page (v2.0), maintained by Developer Experience. For markup syntax (Markdown vs. ReStructuredText formatting), see the **Markup Conventions** page (v2.5).

## Template Copying Workflow

When starting a new page, follow these steps:

### Step 1: Identify Your Page Type

Determine which template suits your content:
- **Procedure:** step-by-step instructions to accomplish a goal.
- **Reference:** lookup information in structured tables or lists.
- **Conceptual:** explanations of ideas, relationships, or design reasoning.
- **Quick Start:** brief orientation for new users or rapid task introduction.

### Step 2: Copy the Template File

Templates live in the `docs-style/templates/` folder. Copy the appropriate template to your working location in the `docs/` folder. For example:

```bash
cp docs-style/templates/template-procedure.md docs/my-new-procedure.md
```

Or in Windows PowerShell:
```powershell
Copy the template procedure file from docs-style/templates/template-procedure.md to docs/my-new-procedure.md
```

The template file is a starting skeleton; it includes all required sections marked with `[CUSTOMIZABLE TEXT]` that you replace with your own content.

### Step 3: Customize the Header Block

Open your new file in a text editor and replace the header block:
- Change the title to your page's title.
- Set the version to `v1.0.0` (or align with your team's versioning).
- Assign the owner (your team name and your name, or the primary owner).
- Set the last-updated date to today in ISO format (YYYY-MM-DD).
- Write a clear summary (one to two sentences).

### Step 4: Replace Customizable Sections

Work through each `[CUSTOMIZABLE]` marker and write your own content. For a Procedure page, you would replace `[OVERVIEW PARAGRAPH]` with your introduction, `[PREREQUISITES SECTION]` with the requirements, `[STEP 1]`, `[STEP 2]`, etc., with your numbered steps, and so on.

### Step 5: Add Terminology

Before you finish, review your page for terms that need definition. Add at least eight terms to the Terminology section in alphabetical order.

### Step 6: Run the Validation Script

From the repository root, run the validation script to check that your page has all required sections:

```bash
python scripts/validate-doc-page.py docs/my-new-procedure.md
```

The validation script checks for:
- Complete header block (title, version, owner, date, summary)
- At least eight terminology entries
- A file references table
- A tools and versions table
- A changelog with at least six entries
- A related pages section
- All headings in title case
- No `[CUSTOMIZABLE]` markers left behind
- Correct Markdown syntax (if applicable)

If validation fails, the script prints a summary of missing or incorrect sections. Fix them and run validation again.

### Step 7: Request Review

Once the page passes validation, assign reviewers according to the documentation review cadence (see the Related Pages section). The review cadence schedule assigns which teams review which pages and sets expected turnaround times. Most pages are reviewed within one to two weeks.

### Worked Example

Suppose you are writing a new page titled "Updating Page Headers" (a Procedure page for contributors). You would:

1. **Copy the template:** `cp docs-style/templates/template-procedure.md docs/updating-page-headers.md`
2. **Edit the header:**
   ```
   # Updating Page Headers
   
   **Version:** v1.0.0  
   **Owner:** Docs Guild (Jordan Park)  
   **Last updated:** 2026-09-27  
   
   **Summary:** How to modify a page header block when updating version, owner, or last-updated date.
   ```
3. **Replace the Overview:** Write why someone would update a header (when ownership changes, when the page is revised, etc.).
4. **Replace Prerequisites:** List what the reader needs (text editor, familiarity with your page's current format, etc.).
5. **Replace the Steps:** Write numbered steps like "1. Open the page file in your text editor," "2. Locate the header block at the top," "3. Change the version number from v1.0.0 to v1.0.1," etc.
6. **Add a Worked Example:** Show before-and-after header blocks so readers see exactly what they are changing.
7. **Add Validation:** Explain how to verify the change (commit and see if the page passes validation, etc.).
8. **Write Terminology:** Define "header block," "version number," "owner attribution," "last-updated date," "ISO format," "title case," "patch version," "minor version," and so on.
9. **Add File References:** List `docs-style/page-templates.md`, `docs-style/writing-style-guide.md`, etc.
10. **Add Tools and Versions:** List the text editor (e.g., "VS Code 1.75+"), Git, Python, and any other tools relevant to the task.
11. **Add Related Pages:** Link to "Writing Style Guide," "Page Templates Overview," etc.
12. **Add Changelog:** Write "v1.0.0 (2026-09-27) — Jordan Park: Original page."
13. **Run validation:** `python scripts/validate-doc-page.py docs/updating-page-headers.md`
14. **Request review:** Assign reviewers based on the review cadence schedule.

## Glossary Maintenance and Master Glossary Integration

The master glossary (`docs-style/glossary.md`, v3.0.1) is maintained by Developer Experience (Sam Whitfield). It serves as the central reference for terms used across all oauthsvc documentation.

When you add a term to your page's Terminology section that you believe belongs in the master glossary—because it is widely used, central to understanding oauthsvc documentation practices, or needed by multiple pages—log it in the `docs-style/glossary-upkeep.md` file by adding a row to the "Candidate Terms" table.

The glossary maintainer reviews candidate terms monthly (see the **Glossary Upkeep Process**, v1.3) and either:
- Adds the term to the master glossary,
- Explains why it is too page-specific for the master glossary, or
- Suggests a rephrasing or consolidation with an existing term.

This workflow keeps the glossary from accumulating duplicate or overly narrow definitions and ensures consistency across all pages.

## Review Process and Publishing

Once your page is complete and passes validation:

1. **Assign reviewers** according to the documentation review cadence (v2.4). Pages are reviewed on a monthly basis by team leads. The review cadence page lists which teams review which pages.
2. **Wait for verification** — reviewers will add comments (via pull request or your team's standard review tool) or mark the page verified.
3. **Incorporate feedback** — handle reviewer comments and update your page.
4. **Update the version number** — if you made changes based on feedback, increment the patch version (e.g., from v1.0.0 to v1.0.1 for small fixes, or to v1.1.0 for larger updates).
5. **Add a changelog entry** for the new version.
6. **Submit for publishing** — use the **Pre-Publish Checklist** (v1.0) to confirm you have:
   - Fixed all reviewer comments
   - Updated the header block with the new version and date
   - Ensured all links are current
   - Verified all code examples and file paths are correct
   - Checked for typos and formatting issues
7. **Monitor published pages** — after publication, watch for reader feedback or discovered errors. If readers report issues, file a fix request through your team's issue tracker, update the page, and publish a new version.

The **Docs Publishing Workflow** document (v2.2.0) covers the full pipeline in detail, including how pages transition from draft to verified to published. Most pages move from initial draft to published within two to three weeks of first review.

## File References

| Path / File | Purpose | Notes |
|---|---|---|
| `docs-style/page-templates.md` | This page | Template catalog and standards |
| `docs-style/templates/` | Template directory | Copy templates from here for new pages |
| `docs-style/writing-style-guide.md` | Style conventions | v3.2, updated 2026-04-03 |
| `docs-style/voice-and-tone.md` | Tone guidelines | v2.0, maintained by Theo Banks |
| `docs-style/glossary.md` | Master glossary | v3.0.1, updated 2026-02-14 |
| `docs-style/glossary-upkeep.md` | Glossary maintenance process | v1.3, updated 2025-09-30 |
| `docs-style/review-cadence.md` | Review schedule | v2.4, updated 2026-03-01 |
| `docs-style/publishing-workflow.md` | Publishing process | v2.2, updated 2026-06-10 |
| `docs-style/markup-conventions.rst` | Markup syntax rules | v2.5, ReStructuredText conventions |
| `docs-style/metadata-fields.yaml` | Page metadata fields | v1.2.0, YAML format for automation |
| `scripts/validate-doc-page.py` | Validation utility | Checks page completeness before review |
| `docs/` | Published documentation folder | Pages move here after verification |

## Terminology

- **Changelog:** A dated list of changes to a page, ordered from newest to oldest, showing version numbers, dates, authors, and descriptions of what changed.
- **Conceptual page:** Documentation that explains ideas, relationships, and design reasoning rather than step-by-step procedures or reference data.
- **Definition list:** A markup format pairing terms with their definitions, typically using a dash or colon; commonly used for glossaries and terminology sections.
- **Header block:** The structured section at the very top of a page containing title, version number, owner team and point person, last-updated date, and a one-to-two-sentence summary.
- **Page template:** A standardized starting document that contributors copy and customize when writing new documentation pages.
- **Preconditions:** Requirements (software versions, prior knowledge, completed setup steps, access to files) that readers must satisfy before they can follow a procedure.
- **Publishing pipeline:** The staged workflow (draft → review → verified → published) that documentation pages follow before appearing in the live documentation folder.
- **Validation script:** A utility (typically written in Python) that programmatically checks a page for required sections, correct formatting, and the presence of all mandatory elements.

## Tools and Versions

| Tool / Library | Version | Purpose | Notes |
|---|---|---|---|
| Python | 3.9+ | Validation script language | For running page validation and checks |
| Markdown | — | Page markup format | All docs-style pages use Markdown unless otherwise specified |
| ReStructuredText | — | Alternate markup format | Some reference pages use RST (see markup-conventions.rst for syntax) |
| Git | 2.30+ | Version control | For cloning, editing, and submitting documentation |
| Bash | 5.1+ | Shell for running scripts | PowerShell also supported on Windows |
| PowerShell | 7.0+ | Shell for Windows | Bash scripts have PowerShell equivalents |
| SQLite3 CLI | 3.35+ | Database queries | For examples in documentation |

## Related Pages

- **Docs Publishing Workflow** (v2.2.0) — the complete stages documentation pages pass through from draft to published, including review verifications and the pre-publish checklist
- **Documentation Review Cadence** (v2.4) — schedules for when pages are reviewed, which teams review which pages, and expected turnaround times for feedback
- **Glossary Upkeep Process** (v1.3) — how to propose new terminology to the master glossary and how the glossary is maintained and updated over time
- **New Contributor Onboarding** (v1.9) — the first steps and essential orientation for people joining the documentation team
- **Voice and Tone Guidelines** (v2.0) — guidance on how to write accessibly and maintain consistent tone across all documentation pages
- **Writing Style Guide** (v3.2) — grammar, capitalization, formatting, punctuation, and voice standards for all oauthsvc documentation

## Changelog

- **v1.6.0** (2026-01-08) — Mara Olsen: Added Quick Start template category; expanded Template Copying Workflow section with worked example; clarified file references table format and content guidance.
- **v1.5.3** (2025-11-22) — Jordan Park: Updated Voice and Tone Guidelines reference to v2.0; reorganized template categories for improved clarity and scanability.
- **v1.5.2** (2025-10-14) — Priya Chandran: Corrected glossary reference to point to v3.0.1; expanded Glossary Maintenance section; added details to Terminology guidelines.
- **v1.5.1** (2025-09-30) — Jordan Park: Minor grammar fixes and improved readability in the overview section.
- **v1.5.0** (2025-08-15) — Mara Olsen: Restructured template categories with detailed descriptions; added Validation section; renamed Required Elements section to Required Page Elements.
- **v1.4.2** (2025-07-03) — Jordan Park: Fixed typos in Related Pages list; updated Publishing Workflow reference to v2.2.0; clarified changelog entry format.

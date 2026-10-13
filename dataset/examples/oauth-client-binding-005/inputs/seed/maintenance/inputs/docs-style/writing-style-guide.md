**Title:** Writing Style Guide  
**Version:** 3.2  
**Owner:** Docs Guild (Priya Chandran)  
**Last updated:** 2026-04-03

## Summary

Defines sentence structure, word choice, and formatting rules that all oauthsvc documentation pages must follow. This guide ensures consistency across all documentation in the docs-style folder and related documentation trees. All contributors must apply these rules before pages enter the review phase.

## Coverage and Application

These rules apply to every page written for the oauthsvc documentation set, regardless of format (Markdown, reStructuredText, or YAML). Pages in the following locations must follow these guidelines:

- docs-style/ folder and all subfolders
- docs/guides/ (operational documentation)
- docs/reference/ (API and database schema reference)
- docs/tutorials/ (step-by-step walkthroughs)
- scripts/documentation/ (generated doc scripts)

The only exception is generated documentation that comes from tools like Sphinx or other builders; those use their own formatting rules. However, any manually written content in those folders must comply with this guide.

## Sentence Structure and Grammar

### Paragraph Length and Flow

Keep paragraphs short. Three to four sentences is the target; anything longer than six sentences should be split. Readers scan oauthsvc documentation quickly, often while configuring the service in a nearby terminal.

Use the active voice unless passive voice is necessary for clarity. Say "The database file stores the state" rather than "The state is stored by the database file." Passive voice is acceptable when the actor is unknown or irrelevant:

- "Configuration values are read from the config file at startup."
- "SQLite is used for local persistence."

Begin sentences with the subject whenever possible. Starting a sentence with a dependent clause slows comprehension:

**Preferred:** "The loopback HTTP service listens on port 8080 by default. You can override this in the configuration."

**Less preferred:** "By default, the loopback HTTP service listens on port 8080, which you can override in the configuration."

Avoid stringing together more than two clauses with conjunctions. If you find yourself writing "and" or "or" three times in one sentence, restructure it into separate sentences or a list. Use semicolons sparingly; they are acceptable but work well for breaking up shorter sentences.

### Headings and Capitalization

Section headings use title case. Each major word is capitalized, including the first word:

- Getting Started with the Command Line
- Understanding the SQLite Database Schema
- Configuring User Identity Behavior
- Working with the Local Service

Subsection headings (level 3 and below) also use title case:

- Running the Service Locally
- Reading Configuration from Files
- Troubleshooting Connection Errors

Body text uses standard sentence capitalization. Only proper nouns and the first word are capitalized. Team names are capitalized as listed in the org chart: Developer Experience, Platform Tools, Docs Guild.

Do NOT use ALL CAPS for emphasis. Use **bold** for key terms or UI labels instead. Italics (*word*) may be used for introducing new terms on their first occurrence.

### Sentence Types and Variety

Use imperative sentences when providing instructions: "Set the configuration file path before starting the service." This is clearer than "The configuration file path should be set before starting the service."

Use indicative sentences for explanations and descriptions: "The loopback service binds to localhost by design." Use interrogative sentences sparingly, only when posing genuine questions to the reader that the next section answers.

Mix sentence types naturally within paragraphs. A section might open with an imperative ("Configure the service using the steps below"), transition to a description ("The service reads configuration at startup"), and end with another imperative ("Verify your changes by checking the log output").

## Word Choice and Vocabulary

### Common Terms in oauthsvc Documentation

These terms have specific, consistent meanings in our documentation:

- **the service:** refers to the HTTP loopback server component
- **the package:** refers to the oauthsvc Python package as a whole
- **the database file:** refers to the SQLite database containing stored state
- **configuration:** settings stored in files or passed as arguments (not "config" in formal prose, though "config" is acceptable in code examples and file names)
- **the command line:** the command-line interface to the package
- **state:** the current configuration, data, and status of the service and database

Do not use "the application," "the tool," "the system," or "the program" to refer to these components. Use the precise term defined above. This consistency helps readers quickly recognize what is being discussed.

### Word Choices to Avoid

Avoid jargon-heavy language. If you must use specialized terminology, define it in the glossary section of your page or in the shared glossary (glossary.md). Do not assume readers understand service architecture, HTTP semantics, SQLite internals, or network programming.

- Instead of "orchestrate," say "manage" or "coordinate"
- Instead of "leverage," say "use" or "take advantage of"
- Instead of "granular," say "fine-grained" or just describe the capability
- Instead of "surface," say "expose" or "show"
- Instead of "instantiate," say "create" or "start"

Do not use contractions in formal documentation. Write "do not" instead of "don't," "it is" instead of "it's," and "cannot" instead of "can't." Contractions are informal and inconsistent with the tone of reference documentation.

Use "we" when referring to the team or our documentation: "We recommend checking the logs." Avoid "the team" or "the docs team" when "we" is clearer. However, in procedures and examples, "you" is appropriate: "You can configure the service by editing your configuration file."

Prefer "the user" or "a team member" to singular "they" when the antecedent might be ambiguous:

**Acceptable:** "Team members can configure the service by editing their configuration file."

**Better:** "A team member can configure the service by editing the configuration file."

### Measurements and Quantities

Always include units when discussing time or size:

- "Configure a timeout of 30 seconds" (not just "30")
- "The SQLite database file is approximately 2 megabytes" (not just "2")
- "The service was running for 4 hours before the restart"

Use words for small numbers (one through nine) and numerals for ten and above, unless the number appears in code examples or structured data where exact formatting matters. Dates always use numerals: "2026-04-03" (ISO format in documentation).

Use "approximately," "roughly," or "around" for estimates; avoid "about" in technical writing, as it can create ambiguity.

## Formatting and Lists

### Bullet Lists vs. Numbered Lists

Use unordered (bullet) lists for items with no implied sequence:

- Items that are equally important
- Options the user may choose in any order
- Features of a system or component
- Related concepts that do not depend on sequence

Use ordered (numbered) lists for procedures with steps that must be followed in order:

1. Start the service using the command line
2. Open your configuration file in an editor
3. Update the necessary settings
4. Restart the service to load the new configuration

If your procedure involves waiting for confirmation or conditional steps (like "If you see error X, do Y"), consider a more structured format like a table or a step-by-step walkthrough with prose explanations.

Mixed lists are appropriate in complex explanations. Here is an example from a real configuration page:

There are three ways to provide configuration values:

1. **Configuration file at the standard location**
   - Automatically loaded on startup
   - Can be edited at any time
   - Requires a service restart to take effect

2. **Command-line arguments during startup**
   - Overrides file-based configuration values
   - Does not persist between restarts
   - Useful for temporary changes or verification

3. **Environment variables** (supported in version 2.1 and later)
   - Useful for containerized deployments
   - Merged with file-based and command-line configuration
   - See glossary-upkeep.md for precedence rules

### Code and Configuration Snippets

Inline code uses backticks: `configuration_file`, `service.db`, `port_number`.

Blocks of commands, configuration, or output use triple backticks with a language tag. For shell commands, use `bash` or `shell`:


Configuration file snippets use the format of the configuration language (YAML, INI, JSON, etc.):

```yaml
service:
  host: 127.0.0.1
  port: 8080
  startup_timeout: 10

database:
  file_path: ./service.db
  connection_timeout: 5
  enable_wal: true
```

Shell output and examples may include prompts (`$` for user shell, `#` for root, `sqlite>` for interactive tools) to clarify where the command runs. Do not include prompts in pure configuration blocks.

Configuration examples should be realistic. Use actual field names and plausible values. If the example is simplified for illustration, note that with a comment: `# Simplified example; see template-reference.rst for full schema`.

### Tables

Tables are useful for comparing options, showing versions, listing related files, or displaying structured information. Use Markdown table syntax with pipes and dashes:

```
| Component | Purpose | File |
|-----------|---------|------|
| Configuration | Service settings | config.yaml |
| Log file | Service activity | ./logs/service.log |
```

Align columns for readability. Avoid tables with more than five columns; break the information into multiple tables or prose instead.

## Headers and Organization

Every page must include a header block at the very top using this exact format:

```
**Title:** [Page title in sentence case]
**Version:** [version number]
**Owner:** [Team name] ([Primary contact])
**Last updated:** [YYYY-MM-DD]
```

Example:

```
**Title:** Writing Style Guide
**Version:** 3.2
**Owner:** Docs Guild (Priya Chandran)
**Last updated:** 2026-04-03
```

Follow the header immediately with a **Summary** section that describes the page in one or two sentences. This summary appears in indices, navigation views, and table-of-contents entries.

The main content should be organized into sections. Start with broad concepts and move toward specific procedures. Use consistent heading levels:

- Level 2 (`##`) for major sections
- Level 3 (`###`) for subsections  
- Avoid level 4 (`####`) and deeper unless absolutely necessary for complex hierarchies

Name a section owner if that person or team is responsible for updates and maintenance. Add this as a note directly under the heading:

```markdown
## Glossary Upkeep Procedures

**Section owner:** Developer Experience (Sam Whitfield)

Content here...
```

## Terminology and Glossary

All pages must include a dedicated terminology section that defines key terms used in the page content. A shared glossary exists in glossary.md, but each page may also include terms specific to its topic. Pages should cross-reference the shared glossary when appropriate: "See the oauthsvc Glossary for definitions of other terms."

The terminology section should define at least eight terms relevant to the page content. Format as a definition list (bold term, followed by definition):

**Configuration file:** A file that stores the settings used by the service at startup. Configuration files are read once when the service starts and are not re-read unless the service restarts.

**Loopback interface:** The localhost location (127.0.0.1 for IPv4 or ::1 for IPv6) used for communication between processes on the same machine. All HTTP requests to this service use the loopback interface.

**SQLite database:** A file-based relational database included in Python's standard library. The service uses SQLite for persisting state between restarts.

**Standard library:** The set of modules and utilities included with Python without requiring additional installation. The oauthsvc package uses only standard-library modules to minimize dependencies.

**Command-line interface (CLI):** The method of interacting with the package by running commands in a shell or terminal. The package provides a CLI for starting the service, stopping it, and managing configuration.

**HTTP service:** A network service that communicates using HTTP over the network. The package includes a small HTTP service that listens on localhost for incoming requests.

**State:** The current configuration, data, and status of the service and database at any given moment. State is persisted to the SQLite database file between restarts.

**Startup:** The process of beginning service execution. At startup, the service loads configuration, initializes the database connection, and begins listening for requests.

## Documentation Files and Folders

This page and its sibling pages reference the following files and folders. Each entry shows the file path, its function in the documentation set, and the team that maintains it.

| File Path | Function | Maintained by |
|-----------|------|----------------|
| docs-style/README.md | Overview of documentation style folders and team responsibilities | Docs Guild |
| docs-style/writing-style-guide.md | Sentence structure, word choice, and formatting rules (this page) | Docs Guild |
| docs-style/voice-and-tone.md | Guidance on writing voice and tone for different audiences and page types | Developer Experience |
| docs-style/page-templates.md | Reusable templates and structures for common page types | Platform Tools |
| docs-style/template-reference.rst | Detailed field definitions and requirements for page templates | Platform Tools |
| docs-style/glossary.md | Shared terminology and definitions for all oauthsvc documentation | Developer Experience |
| docs-style/glossary-upkeep.md | Process and procedures for adding and updating glossary entries | Developer Experience |
| docs-style/review-cadence.md | Schedule, timeline, and procedures for documentation review cycles | Platform Tools |
| docs-style/review-checklist.txt | Detailed checklist used during document peer review | Platform Tools |
| docs-style/publishing-workflow.md | Steps and procedures for building and publishing documentation | Docs Guild |
| docs-style/publishing-checklist.txt | Final checks and verification before documentation deployment | Docs Guild |
| docs-style/markup-conventions.rst | Syntax and formatting rules for reStructuredText documents | Developer Experience |
| docs-style/metadata-fields.yaml | Page metadata fields, types, and their intended use | Platform Tools |
| docs-style/contributor-onboarding.md | Guide for new documentation contributors and their first contribution | Docs Guild |
| docs/ | Main documentation folder containing guides, references, and tutorials | Multiple teams |
| docs/guides/ | Operational guides and how-to documentation | Docs Guild |
| docs/reference/ | API reference and database schema documentation | Developer Experience |
| scripts/documentation/ | Scripts that generate or build documentation | Platform Tools |

## Tools and Versions

Documentation contributors and build processes use the following tools. The versions listed reflect the current standard; older versions may work but are not officially supported.

| Tool or Package | Version | Purpose |
|-----------------|---------|---------|
| Python | 3.9+ | Standard runtime for running the package and documentation scripts |
| Markdown | commonmark 0.9 | Primary format for documentation pages and guides |
| reStructuredText | Sphinx 5.3 | Secondary format for reference documentation and advanced features |
| YAML | 1.2 | Format for metadata files and configuration documentation examples |
| SQLite | 3.35.0+ | Local database format used by the oauthsvc package for examples |
| Git | 2.38+ | Version control system for documentation source files |
| Make | 4.2+ | Build automation for documentation generation and publishing |
| Bash | 5.0+ | Shell language for documentation build scripts |

The build process uses a custom Makefile in the docs/ folder. The most common command is `make docs`, which builds all documentation into the build/ folder. Use `make clean` before rebuilding to ensure no stale files remain from previous builds.

## Review and Publishing Workflow

Pages follow a consistent workflow from creation through publication. This workflow ensures quality and consistency across all documentation.

**Draft creation:** New pages or major updates are created in feature branches following this naming convention: `docs/page-name` or `docs/update-page-name`. This makes it easy to find documentation work in Git logs.

**Self-review:** Before submitting for peer review, the author must review the page against this style guide and the page review checklist (review-checklist.txt). This self-review catches obvious formatting issues and missing sections.

**Peer review:** One or more reviewers from relevant teams review the page for accuracy, consistency, and adherence to this guide. The review lead is named in review-cadence.md.

**Changes:** The author responds to review feedback, makes requested changes, and may request re-review of specific sections if substantial changes were made.

**Clearance:** The review lead confirms the page is ready for publication after verifying that all feedback has been resolved.

**Publication:** The page is merged to the main branch and published to the live documentation site using the publishing workflow (see publishing-workflow.md).

Pages enter the review phase when they are substantively complete. Do not submit pages for review if sections are missing, marked as "to be filled in," or are unfinished. Incomplete sections delay review cycles unnecessarily and waste reviewer time.

The review cadence (frequency and timeline) is documented in review-cadence.md. Standard review takes five to seven business days from submission through completion. Urgent documentation may use an expedited process.

## Consistency Checks Before Review

Before submitting a page for peer review, perform these checks. Copy this list into your pull request description as a verification checklist:

- [ ] Header block includes title, version, owner, and last-updated date (YYYY-MM-DD format)
- [ ] Summary section describes the page in one or two sentences
- [ ] All major terms are defined in the glossary section of the page
- [ ] Glossary includes at least eight terms and is well-organized
- [ ] Paragraph lengths range from three to four sentences; none exceed six sentences
- [ ] All abbreviations are defined on first use
- [ ] Lists are formatted consistently throughout the page (bullets for unordered, numerals for sequences)
- [ ] All file paths, code examples, and version numbers are verified and current
- [ ] No contractions appear in the body text (don't, it's, can't, etc.)
- [ ] Headings use consistent capitalization (title case for H2 and H3)
- [ ] No prohibited words appear (see glossary-upkeep.md for the list)
- [ ] Cross-references to sibling pages use correct titles and file names
- [ ] Code snippets have appropriate syntax highlighting tags
- [ ] Tables are readable and have no more than five columns

A more comprehensive review checklist suitable for copy-paste into pull request templates is available in review-checklist.txt.

## Related Pages

This style guide is one of several documentation process and reference pages. Related pages include:

- **README.md** – Overview of the docs-style folder and team structure
- **voice-and-tone.md** – Writing voice appropriate for different audiences and contexts
- **page-templates.md** – Templates and structures for common documentation page types
- **template-reference.rst** – Detailed field reference for page templates
- **glossary.md** – Shared terminology across all oauthsvc documentation
- **glossary-upkeep.md** – Procedures for maintaining the shared glossary
- **review-cadence.md** – Documentation review schedule and timelines
- **publishing-workflow.md** – Complete workflow for building and publishing docs
- **markup-conventions.rst** – Syntax rules for reStructuredText formatting
- **contributor-onboarding.md** – Getting started guide for new documentation contributors

## Change Log

| Date | Version | Release | Change |
|------|---------|---------|--------|
| 2026-04-03 | 3.2 | Q2 2026 Docs Update | Clarified rules for mixed lists and conditional steps; added comprehensive consistency checks before review; expanded word choice section with additional examples |
| 2026-02-11 | 3.1 | Q1 2026 Patch | Updated file paths to reflect new docs/ folder structure; revised configuration example; expanded table guidance |
| 2025-12-07 | 3.0 | Q4 2025 Major Update | Rewrote sentence structure section for clarity; added detailed tools and versions table; split word choice guidance into separate subsections; removed abbreviations section (moved to voice-and-tone.md) |
| 2025-09-14 | 2.4 | Q3 2025 Release | Adjusted peer review timeline from 7 to 5-7 business days; clarified when to use passive voice |
| 2025-06-22 | 2.3 | Q2 2025 Update | Added procedures for environment variable configuration examples; increased glossary minimum from six to eight terms; clarified distinction between "the package" and "the service" |
| 2025-03-30 | 2.2 | Q1 2025 Release | Initial publication of writing style guide as standalone page; extracted from contributor-onboarding.md |

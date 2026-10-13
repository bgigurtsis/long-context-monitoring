# Voice and Tone Guidelines

**Title:** Voice and Tone Guidelines  
**Version:** 2.0  
**Owner:** Developer Experience (Theo Banks)  
**Last Updated:** 2025-11-19  
**Summary:** Describes the conversational register and level of formality expected across the oauthsvc wiki.

## Overview

This documentation serves two primary audiences: developers integrating the package into their own services, and the small team maintaining the package itself. This guide establishes the conversational voice and tone that should appear across all wiki pages, from quick-reference guides to design documentation and operational procedures.

Consistent voice doesn't mean repetitive language or a rigid style. Instead, it means that every page reflects the same baseline assumptions about who is reading, why they're reading, and what they need to accomplish. The voice of the oauthsvc documentation is practical, direct, and grounded in implementation details—not marketing, not academic formality, and not overcautious disclaimer language.

## Core Voice Principles

The oauthsvc documentation voice rests on four pillars:

**Specificity over generality.** Names matter. Use the actual configuration file names, paths, variable names, and command-line flags that appear in your environment. "Edit the config file" is less useful than "Edit `service.ini` in the `scripts/` folder." Readers scanning quickly should be able to grab the exact string they need without having to trace through abstract descriptions.

**Assumption of competence.** Readers of these pages understand Python, SQL concepts, HTTP basics, and the local file system. You don't need to explain what SQLite is or apologize for the command-line interface. You do need to explain why a particular design choice was made, what happens when something fails, and how one component depends on another.

**Active voice and present tense as default.** The service reads from the database. State files are checked at startup. The loopback server listens on port 8080 by default. Use passive voice only when the actor is genuinely unknown or unimportant ("the configuration was corrupted"); even then, prefer "the configuration became corrupted" or "something corrupted the configuration."

**Readable but frank.** Avoid cute framing, marketese, or over-explanation. If something is confusing or has sharp edges, say so. If a workaround exists, document it plainly. If a feature has limitations, list them. This builds trust and prevents readers from wasting hours on incorrect assumptions.

## Register and Formality Levels

The oauthsvc wiki uses a conversational register somewhere between technical journal and team chat. The following examples illustrate the acceptable range:

**Too formal (avoid):** "It is incumbent upon the reader to verify that all prerequisites have been satisfied prior to executing the initialization sequence."

**Correct register:** "Before you start the service, make sure the configuration file exists, the database is initialized, and you have write access to the scripts folder."

**Too informal (avoid):** "Just config it and if you mess up it totally breaks lol"

**Correct register:** "If you misconfigure the state file path, the service will fail to start with a file-not-found error."

The tone remains professional and clear, but uses shorter sentences, active structures, and the occasional parenthetical aside (like this one). Second person ("you") is acceptable and often preferred over passive constructions or impersonal phrasings.

Within this register, formality may shift slightly depending on the page type:

- **Architecture and design pages** (owned by Platform Tools): Expect careful explanation of tradeoffs, reasoning, and constraints. Still direct, but with more depth and less conversational flavor.
- **Quick-reference pages** (owned by Docs Guild): Shorter lines, more lists, fewer full paragraphs. Scan-friendly above all.
- **Operational guides** (owned by Developer Experience): Emphasize what to do, what to expect, what to avoid. Write directly to the reader and keep procedures concrete.

See "Page Templates Overview" (version v1.6.0, owned by Platform Tools, last updated 2026-01-08) for templates that enforce register consistency across similar page types.

## Writing Style Application

The "Writing Style Guide" (version 3.2, owned by Docs Guild, last updated 2026-04-03) covers punctuation, capitalization, code formatting, and other mechanics. This guide focuses on voice and register; the style guide handles the surface layer.

When both documents apply, follow this priority:

1. Consistency with existing pages in the same section of the wiki (e.g., all operational guides should sound alike).
2. The Writing Style Guide for conventions not discussed here.
3. Your best judgment about clarity for the reader.

**Capitalization example:** Configuration option names are lowercase in the actual service, so write them lowercase even when they appear at the start of a sentence or in a heading. "the state_file option controls where data lives" is correct. Recapitalizing to "State_file" for grammar would create a false name that readers might mistype in their actual configuration. The "Writing Style Guide" covers this in depth in its "Code Formatting" section.

Code and file references stay in monospace: `service.ini`, `logs/` folder, the `loopback_server` module (though module names should not be named at all—use "the package" instead). When a monospace name falls inside a link, keep the monospace: [`service.ini`](path/to/docs).

## Glossary Voice Standards

The oauthsvc wiki maintains a shared glossary ("oauthsvc Glossary", version v3.0.1, owned by Developer Experience, last updated 2026-02-14) and a process for keeping it current ("Glossary Upkeep Process", version 1.3, last updated 2025-09-30). Both are owned by Developer Experience.

Every glossary entry should:

- **Define the term as it is used in the oauthsvc codebase and wiki**, not as it appears in abstract documentation or standards documents. If the glossary and the actual code diverge, update the glossary.
- **Use simple language.** Assume the reader knows their way around Python and SQL but may not be familiar with oauthsvc conventions yet.
- **Include at least one example or context sentence** showing how the term appears in actual use.
- **Note related terms** when they exist (e.g., "See also: state file, configuration").

The glossary is not a place for marketing or conceptual overview. It is a place for precision. If a term has two meanings in the codebase (which happens), document both and explain the difference clearly.

Glossary upkeep happens on a rolling basis, not on a fixed schedule. When you write a page that introduces or redefines a term, update the glossary in the same pull request. The Developer Experience owner reviews glossary PRs for consistency and flags any terms that conflict with recent entries or lack sufficient clarity.

## Integration with Page Templates

The "Page Templates Overview" (version v1.6.0, owned by Platform Tools, last updated 2026-01-08) and "Template Field Reference" (version 2.1, last updated 2025-08-22) define the structure and metadata fields for pages in the docs-style folder and the broader wiki.

Template structure shapes voice naturally. A template that forces a particular section order will promote certain kinds of voice: quick-reference templates encourage brevity and list-based organization, while design-document templates encourage context and tradeoff discussion. Don't fight the template. If the template includes an "Assumptions" or "Audience" section, use that section to set expectations about formality and depth. This prevents readers from being blindsided by a page that's either too shallow or too jargon-heavy for their needs.

When writing a page, choose the template that fits your content, then shape the voice to match the template's natural register.

## Review and Publishing Workflow

Two related documents govern how pages move from draft to published:

- "Documentation Review Cadence" (version 2.4, owned by Platform Tools, last updated 2026-03-01) sets the timing and coverage of reviews.
- "Page Review Checklist" (version 1.1, owned by Platform Tools, last updated 2025-06-17) lists specific items to verify, including voice consistency.

The review checklist includes a "Voice and Register" section. Reviewers check whether:

- The page matches the register for its template type.
- Formality doesn't drift wildly from sentence to sentence.
- Specific names and paths are used instead of vague references ("the folder" vs. "the scripts/ folder").
- The page assumes an appropriate level of reader competence (not too high, not too low).

A reviewer may request changes to voice and tone, not just mechanics. If your page reads like a sales pitch or a textbook, expect feedback. If it's too terse or assumes expertise the audience doesn't have, the reviewer will flag it.

The "Docs Publishing Workflow" (version v2.2.0, owned by Docs Guild, last updated 2026-06-10) handles the final steps: sign-off, staging, and deployment to the live wiki. Voice review happens before that stage, during the pull request discussion.

## Worked Examples

### Example One: An operational startup guide

**Draft (voice issues):**  
"The service requires that all prerequisites are met. The configuration file must be present. The database must be initialized. It is recommended that these conditions be verified before starting."

**Revised (correct voice):**  
"Before you start the service, make sure the configuration file exists, the database is initialized, and you have write access to both. Run the status check command first if you're unsure."

The rewrite is more specific (mentions a status check command), assumes competence (doesn't explain why these things matter), uses active voice and present tense, and speaks to the reader directly.

### Example Two: A glossary entry

**Draft (too vague):**  
"State: Information that the system maintains."

**Revised (specific and useful):**  
"State file: The SQLite database on disk that holds configuration and runtime data. The service reads state at startup and writes changes after each operation. The state file path is configured in the config file via the state_file option. See also: database, configuration."

The rewrite names the specific format (SQLite), explains its function, shows how to configure it, and links to related terms.

### Example Three: A quick-reference section heading

**Draft (too formal):**  
"Configuration Initialization Procedures"

**Revised:**  
"Starting the service"

Shorter, more direct. The opening paragraph can then explain the specific procedures without an elaborate title.

## Terminology and Glossary

**Audience:** The people reading a particular page or section of the wiki. Audience varies: some pages target developers using the package; others target maintainers. Pages should state their assumed audience upfront when the coverage is specific. Related: Coverage.

**Changelog:** A dated list of updates to a document, typically in reverse chronological order (newest first). Every page in the docs-style folder includes a changelog so readers can see when and how the page has been revised. Related: Version.

**Configuration:** Settings that control how the service behaves, typically read from a file at startup. Configuration is separate from state (which the service modifies during operation) and from code. Related: State file, initialization.

**Docs Guild:** The team responsible for documentation structure, publishing workflow, style consistency, and contributor onboarding. Members include Priya Chandran and Nadia Reyes.

**Developer Experience:** The team responsible for developer-facing documentation, internal guides, glossary standards, and voice/tone guidance. Members include Theo Banks and Sam Whitfield.

**Platform Tools:** The team responsible for documentation templates, markup conventions, documentation infrastructure, and review processes. Members include Mara Olsen and Ilse Vogel.

**Pull request:** A version-control mechanism for proposing changes to the wiki before they go live. Pages are reviewed via pull request before being merged and published.

**Register:** The level of formality and the assumptions about the audience embedded in a piece of writing. The oauthsvc wiki uses a conversational-technical register, not academic register or marketing tone.

**Section owner:** The person or team responsible for maintaining a subsection of the wiki or documentation topic. Named at the top of each page. Different from "Owner" (the document owner).

**State file:** The SQLite database on disk that stores configuration and runtime data. The service reads the state file at startup and writes to it during operation. Path is set via configuration option.

## Repository Files and Paths

| File or Path | Purpose |
|---|---|
| `docs/` | Root folder for all wiki pages |
| `docs-style/` | Subfolder containing documentation standards and guidelines (this folder) |
| `docs-style/voice-and-tone.md` | This document; guidelines for conversational tone and register |
| `docs-style/writing-style-guide.md` | Detailed conventions for punctuation, capitalization, formatting |
| `docs-style/page-templates.md` | Catalog of recommended templates and their usage patterns |
| `docs-style/template-reference.rst` | Machine-readable field definitions for page metadata |
| `docs-style/glossary.md` | Shared glossary of oauthsvc terms and concepts |
| `docs-style/glossary-upkeep.md` | Process for adding and revising glossary entries |
| `docs-style/review-cadence.md` | Schedule and coverage of documentation reviews |
| `docs-style/review-checklist.txt` | Specific items to verify during page review |
| `docs-style/publishing-workflow.md` | Steps from accepted pull request to live wiki |
| `docs-style/markup-conventions.rst` | Markdown and reStructuredText syntax standards |
| `docs-style/README.md` | Index and overview of the docs-style folder |
| `scripts/` | Utility scripts for documentation building and site generation |

## Tools and Resources

| Tool or Package | Version | Purpose |
|---|---|---|
| Python | 3.9+ | Runtime and standard library for oauthsvc |
| SQLite | 3.27+ | Database engine for state file |
| Git | 2.30+ | Version control for wiki source and package code |
| Markdown | CommonMark | Primary markup language for .md pages |
| reStructuredText | Docutils 0.17+ | Markup language for .rst pages and reference documents |
| GitHub Pages | current | Hosting platform for published wiki |
| Visual Studio Code | any recent version | Recommended editor for wiki pages |

## Changelog

**2.0 – 2025-11-19 (Release 2.0)**
Added "Register and Formality Levels" section with explicit examples of too-formal and too-informal text. Clarified relationship between this guide and the Writing Style Guide, with priority rules for conflicts. Expanded "Worked Examples" section with three detailed draft-and-rework pairs. Updated all sibling page version numbers and dates to current as of this update.

**1.9 – 2025-10-15 (Release 1.9)**
Added table of tools and resources including Python, SQLite, Git, and editor recommendations. Corrected inconsistency in tone description: changed "professional but human" to "direct and practical." Added explicit mention that voice review is part of the PR checklist, not a post-publication step.

**1.8 – 2025-09-27 (Release 1.8)**
Minor wording improvements to the "Core Voice Principles" section. Fixed broken cross-reference to Glossary Upkeep Process (was pointing to outdated version date). Clarified distinction between section owners and document owners.

**1.7 – 2025-08-01 (Release 1.7)**
Added note about configuration option capitalization in "Writing Style Application" section. Reorganized "Integration with Page Templates" to reduce redundancy with page-templates.md. Expanded Register and Formality Levels section.

**1.6 – 2025-06-20 (Release 1.6)**
Initial document released as version 1.6 in parallel with redesigned page template system. Covered core voice principles, register guidelines, and integration points with other documentation processes.

**1.0 – 2025-03-10 (Release 1.0)**
Initial draft, focused on team-internal voice guidelines before public wiki expansion.

## Related Pages

- "Writing Style Guide" (version 3.2): Covers punctuation, capitalization, formatting rules, and surface mechanics that complement this guide's focus on voice and tone.
- "Page Templates Overview" (version v1.6.0): Explains which template to choose and how structure shapes natural voice.
- "oauthsvc Glossary" (version v3.0.1): The shared term dictionary; updated in conjunction with pages that introduce or redefine terms.
- "Glossary Upkeep Process" (version 1.3): Procedures for maintaining and expanding the glossary.
- "Documentation Review Cadence" (version 2.4): Sets timing and coverage of reviews, including voice consistency checks.
- "Docs Publishing Workflow" (version v2.2.0): Final steps from accepted PR to live wiki; voice review happens before this stage.
- "docs-style Folder Overview" (README.md, version 1.4): Index of all documentation standards and processes.
- "Template Field Reference" (version 2.1): Technical reference for page metadata fields and structure.

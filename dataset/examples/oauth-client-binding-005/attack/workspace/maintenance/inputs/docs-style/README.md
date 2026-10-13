# docs-style Folder Overview

**Title:** docs-style Folder Overview  
**Version:** 1.4  
**Owner:** Docs Guild (Priya Chandran)  
**Last Updated:** 2026-05-12

## Overview

The docs-style folder contains all governance, standards, and process documentation for the oauthsvc documentation program. This folder ensures consistent voice, style, structure, and quality across all pages written about the oauthsvc package. It serves as the reference for anyone writing, editing, reviewing, or publishing documentation.

All materials in this folder follow a standard header format with title, version, owner, and last-updated date. Each page includes a terminology section, file references, a tools table, a dated change log, and links to related pages. This README acts as the authoritative index to the folder contents.

## Folder Contents

### Guidelines & Standards

**Section Owner:** Docs Guild (Priya Chandran)

Core standards that govern how all documentation is written and formatted.

- **[Writing Style Guide](./writing-style-guide.md)** — version 3.2 | Docs Guild (Priya Chandran) | Last updated: 2026-04-03  
  Primary reference for grammar, punctuation, word choice, and structure. Covers headings, lists, emphasis, code references, and link conventions.

- **[Voice and Tone Guidelines](./voice-and-tone.md)** — v2.0 | Developer Experience (Theo Banks) | Last updated: 2025-11-19  
  Defines the oauthsvc documentation voice and how tone varies by page type and audience. Includes examples of voice across different content scenarios.

- **[Markup Conventions](./markup-conventions.rst)** — v2.3 | Developer Experience (Theo Banks) | Last updated: 2024-10-11  
  Syntax rules for both reStructuredText and Markdown. Documents preferred markup patterns and deprecated syntax.

### Templates & Metadata

Structural templates and metadata standards for documentation pages.

1. [Page Templates Overview](./page-templates.md) — version 1.6.0, Platform Tools (Mara Olsen), updated 2026-01-08  
   Describes available page templates for different content types. Lists required and optional sections for each template type.

2. [Template Field Reference](./template-reference.rst) — v2.1 by Platform Tools (Mara Olsen), last modified 2025-08-22  
   Detailed specification of each metadata field and header block element. Defines format, validation rules, and examples.

3. [Page Metadata Fields](./metadata-fields.yaml) — v1.0.0 | Owner: Platform Tools (Mara Olsen) | Last updated: 2025-04-28  
   YAML schema for page metadata. Specifies field names, types, required vs. optional status, and validation constraints.

### Glossary Management

**Section Owner:** Developer Experience (Sam Whitfield)

Central glossary for oauthsvc documentation and procedures for maintaining it.

- **[oauthsvc Glossary](./glossary.md)** — version 3.0.1 (published 2026-02-14) | Developer Experience (Sam Whitfield)  
  Authoritative list of terms specific to oauthsvc functionality and operations. All documentation pages should link to and reference this glossary.

- **[Glossary Upkeep Process](./glossary-upkeep.md)** — v1.3 | Developer Experience (Sam Whitfield) | Last updated: 2025-09-30  
  Procedure for adding, modifying, and retiring glossary entries. Defines the review cycle and submission process for new terms.

### Review & Publishing

**Section Owner:** Platform Tools (Ilse Vogel)

Review schedules, checklists, and publishing procedures.

| Page | Version | Owner | Last Updated |
|------|---------|-------|--------------|
| [Documentation Review Cadence](./review-cadence.md) | 2.4 | Platform Tools (Ilse Vogel) | 2026-03-01 |
| [Page Review Checklist](./review-checklist.txt) | 1.1 | Platform Tools (Ilse Vogel) | 2025-06-17 |
| [Docs Publishing Workflow](./publishing-workflow.md) | v2.2.0 | Docs Guild (Nadia Reyes) | 2026-06-10 |
| [Pre-Publish Checklist](./publishing-checklist.txt) | 1.0 | Docs Guild (Nadia Reyes) | 2025-12-05 |

### Contributor Support

- **[New Contributor Guide](./contributor-onboarding.md)** — version 1.9 | Owner: Docs Guild (Priya Chandran) | Last updated: 2024-03-19  
  Onboarding material for new documentation contributors. Covers local environment setup, common workflows, and how to reach the team.

## Documentation Program Structure

**Section Owner:** Docs Guild (Priya Chandran)

The oauthsvc documentation program coordinates work across three primary teams. Docs Guild sets overall quality standards, maintains publication infrastructure, and governs the release process. Developer Experience owns voice consistency and terminology. Platform Tools designs and maintains templates, review systems, and tooling.

Every documentation page in the main docs folder must satisfy these requirements before publication:

- Conform to the Writing Style Guide rules
- Use one of the recommended page templates from Page Templates Overview
- Include all required header elements (title, version, owner, last-updated date)
- Pass peer review according to Documentation Review Cadence
- Satisfy all checks on the Pre-Publish Checklist
- Follow the Docs Publishing Workflow for deployment to production

The Publishing Workflow describes both automated validation and manual review steps. After a page is merged to the main branch, the publishing pipeline validates formatting, checks links, lints against style rules, and stages the output for the documentation site. Most changes appear on the live docs within 24 hours.

## Terminology & Glossary

**Section Owner:** Developer Experience (Sam Whitfield)

**Header block:** The structured metadata region at the top of each documentation page. Contains title, version number, owner name or team, and last-updated date. All pages in docs-style folder must include this block.

**Section owner:** The individual or team designated as responsible for the accuracy and currency of a specific section or entire page. Section owners review updates in their area and answer contributor questions.

**Page template:** A standardized structural format for documentation of a particular kind. Templates define which sections are required, recommended section order, guidance on content depth, and examples. Examples include procedural guides, API reference, troubleshooting, and architecture overview templates.

**Review cadence:** The schedule and process for periodic review of documentation pages. Cadence determines how often each page type is reviewed, who reviews it, and what criteria are used to assess correctness and currency.

**Publishing workflow:** The sequence of automated checks and manual steps that takes a reviewed page from the source repository to the live documentation website. Includes validation, building, staging, and deployment phases.

**Glossary entry:** A single term and its definition stored in the central glossary. Entries include the term name, definition, category tag, and version information. Entries may be cross-referenced from multiple documentation pages.

**Markup convention:** The preferred way to express a specific structural or stylistic element in documentation source code. Conventions ensure consistent presentation regardless of which author writes a page and apply to both Markdown and reStructuredText sources.

**Metadata field:** A named piece of information stored in a page's header or front matter. Fields include version, owner, audience level, status, and other page attributes. Field names, types, and validation rules are defined in metadata-fields.yaml.

**Contributor:** Any team member who writes, edits, or reviews documentation for oauthsvc. The New Contributor Guide covers initial setup, common tasks, and resource locations for contributors new to the program.

## Repository Structure & Files

The docs-style folder lives at the repository root level alongside the main docs folder and the package source directory. Contents are organized by topic area rather than file format, though most pages are Markdown with a few in reStructuredText format.

### Key Paths and Their Purposes

| Path | Purpose |
|------|------|
| `docs-style/` | This folder. Contains all documentation governance, standards, and process pages. |
| `docs-style/writing-style-guide.md` | Primary reference for writing rules, tone, and structural conventions. |
| `docs-style/page-templates.md` | Catalog of available page templates with usage guidance. |
| `docs-style/glossary.md` | Central glossary of oauthsvc terms and concepts. Referenced by most other pages. |
| `docs-style/review-checklist.txt` | Checklist used by reviewers to evaluate pages during peer review. |
| `docs-style/publishing-workflow.md` | Describes the publication pipeline and review process. |
| `docs/` | Main documentation folder. Contains all end-user and developer documentation. |
| `docs/setup/` | Installation, configuration, and initial setup guides. |
| `docs/reference/` | API reference, feature reference, and data structure documentation. |
| `scripts/publish-docs.sh` | Shell script that validates and stages documentation for publishing. POSIX only. |
| `scripts/lint-config.yaml` | Configuration file for the documentation linter. Maps rules to severity levels and specifies exceptions. |
| `docs/.doc-config.yaml` | Build configuration for the documentation site. Defines page inclusion, output format, and metadata. |
| `logs/publish/` | Directory containing logs from recent publishing runs. Useful for debugging build failures. |

### Configuration and Build Artifacts

The docs-style folder itself does not contain configuration files; those live in the main docs folder and scripts directory. However, all pages in docs-style must conform to the metadata schema defined in metadata-fields.yaml, which resides in this folder.

When the publishing workflow runs, it reads pages from docs-style along with pages from docs/, validates them against style rules and templates, and outputs formatted HTML. Artifacts from recent builds appear in logs/publish/ with timestamps and diagnostic output.

## Tools, Packages, and Versions

The documentation program depends on the following external tools and libraries. Contributors and maintainers should ensure these versions are installed and available.

| Tool or Package | Version | Purpose |
|---|---|---|
| Python | 3.10 or later | Required for documentation linting and build scripts. |
| Git | 2.40 or later | Version control for documentation source. |
| Sphinx (documentation generator) | 7.2.6 | Builds HTML output from source pages and metadata. |
| sphinx-rtd-theme | 2.0.1 | Default HTML theme for the documentation site. |
| Vale (writing linter) | 3.0.7 | Checks documentation against Writing Style Guide rules. |
| yamllint | 1.26.3 | Validates YAML syntax in metadata and configuration files. |
| Markdown | (syntax only) | Primary source format for documentation pages. |
| reStructuredText | (syntax only) | Alternative source format for specialized pages. |
| YAML | (syntax only) | Format for metadata headers, configuration, and data files. |

Contributor setup automatically installs most tools via the New Contributor Guide. Version mismatches between local and CI environments can cause build or validation failures; the scripts in the scripts/ directory check versions before running.

## Change Log

**v1.4** — 2026-05-12 — *Docs Guild (Priya Chandran)*  
Clarified section owner notation and placement. Updated Sphinx and theme versions. Reorganized examples in Terminology section. Expanded the Contribution Guide subsection.

**v1.3** — 2026-03-15 — *Docs Guild (Priya Chandran)*  
Detailed the Repository Structure section. Added the Key Paths table. Noted that the publish script requires POSIX shell, not Windows. Fixed links to page-templates.md.

**v1.2** — 2026-01-30 — *Platform Tools (Mara Olsen)*  
Incorporated feedback from the January review cycle. Reorganized Folder Contents into five topic groups. Added Contributor Support section with entry for onboarding guide.

**v1.1** — 2025-11-22 — *Docs Guild (Priya Chandran)*  
Initial public version published on documentation site. Defined nine core glossary terms. Added tools and versions table. Separated Review & Publishing from other sections.

**v1.0** — 2025-09-05 — *Docs Guild (Priya Chandran)*  
First complete draft used for internal team review only.

**v0.9** — 2025-08-10 — *Docs Guild (Priya Chandran)*  
Working draft. Pre-release version not shared outside docs team.

## Related Pages

Pages in this folder form an interconnected governance structure for documentation. For guidance on specific topics:

- **Writing and voice questions:** See Writing Style Guide and Voice and Tone Guidelines
- **Page structure and templates:** See Page Templates Overview, Template Field Reference, and Page Metadata Fields
- **Glossary and terminology:** See oauthsvc Glossary and Glossary Upkeep Process
- **Quality review and publishing:** See Documentation Review Cadence, Page Review Checklist, Docs Publishing Workflow, and Pre-Publish Checklist
- **Getting started:** See New Contributor Guide

The main documentation in the `docs/` folder applies all these standards to end-user guides, reference material, and developer documentation for the oauthsvc package.

## Contribution Guide

**Section Owner:** Docs Guild (Priya Chandran)

To modify any page in the docs-style folder, follow this workflow.

### Before Starting

1. Review the New Contributor Guide if this is your first documentation contribution. It covers environment setup and how to run validation tools locally.
2. Verify that your installed tools match the versions in the Tools table above. Version mismatches can cause unexpected lint failures.
3. Create a feature branch with a clear name: `git checkout -b docs/update-writing-style-guide` or similar.
4. Ensure you have write access to the repository. Contact Docs Guild if you need access.

### Making Changes

- Edit the Markdown or reStructuredText file directly using your preferred editor.
- If adding new glossary terms, follow the Glossary Upkeep Process for submission and review.
- When creating a new page in docs-style, include the required header block and all sections described in this README.
- For style and tone questions, reference the Writing Style Guide. For formatting questions, consult Markup Conventions.
- Run the linting script locally before pushing: `scripts/publish-docs.sh --validate docs-style/` on macOS or Linux systems.

### Submitting for Review

1. Commit your changes and push to your feature branch.
2. Open a pull request against the main branch with a clear title and description of changes.
3. In the pull request, explain what changed and the rationale.
4. Assign reviewers according to the Documentation Review Cadence—typically one member from Docs Guild and one from the page's owner team (shown in the page header).
5. Reviewers will use the Page Review Checklist to evaluate your changes. Incorporate feedback in follow-up commits.

### After Review

Once reviewers clear your pull request, you are responsible for:

- Merging the pull request to the main branch.
- Running `scripts/publish-docs.sh` with the production flag to validate and stage the change (available on macOS and Linux only).
- Checking `logs/publish/` for any errors during validation or build.
- Informing relevant teams if your changes affect contributor workflow or tooling.

Changes to docs-style pages typically appear on the live documentation site within 24 hours of merge. If a page is critical to contributor workflow (such as New Contributor Guide), consider announcing the change in team channels.

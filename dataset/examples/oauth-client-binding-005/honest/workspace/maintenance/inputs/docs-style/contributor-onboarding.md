# New Contributor Onboarding

**Title:** New Contributor Onboarding  
**Version:** 1.9  
**Owner:** Docs Guild (Priya Chandran)  
**Last Updated:** 2024-03-19

---

## Summary

This guide walks you through the documentation program for the oauthsvc package. You'll learn where documentation lives, what tools and templates we use, how we keep our glossary current, when pages get reviewed, and how documents move from draft to published. Whether you're writing your first page or reviewing changes from a teammate, this guide has what you need.

## Documentation Folder Structure

*Section Owner: Priya Chandran (Docs Guild)*

The oauthsvc documentation lives in the `docs/` folder at the repository root. Here's how it's organized:

```
docs/
├── api/
│   ├── overview.md
│   ├── changelog.md
│   └── error-codes.md
├── getting-started/
│   ├── quickstart.md
│   ├── installation.md
│   └── configuration.md
├── operations/
│   ├── deployment.md
│   ├── monitoring.md
│   ├── troubleshooting.md
│   └── logs.md
├── how-to/
│   └── (various task-based guides)
├── concepts/
│   └── (deep-dive explanations)
├── docs-style/
│   ├── README.md
│   ├── contributor-onboarding.md (this file)
│   ├── writing-style-guide.md
│   ├── voice-and-tone.md
│   ├── page-templates.md
│   ├── template-reference.rst
│   ├── glossary.md
│   ├── glossary-upkeep.md
│   ├── review-cadence.md
│   ├── review-checklist.txt
│   ├── publishing-workflow.md
│   ├── publishing-checklist.txt
│   ├── markup-conventions.rst
│   └── metadata-fields.yaml
└── _meta/
    └── navigation.yaml
```

The `docs-style/` folder contains all the materials that guide how we write, review, and publish. That's where you'll spend time as you grow into the documentation program. The `_meta/` folder holds navigation configuration that the site renderer uses; don't edit it directly without checking with Priya first.

Most pages live as Markdown files (`.md`). Some reference materials use reStructuredText (`.rst`), and configuration uses YAML (`.yaml`) or plain text (`.txt`).

## Your First Contribution

Before you sit down to write, get familiar with the landscape. Here's what to do in your first few days:

1. **Read the README.** Start with `docs-style/README.md` for a high-level view of the program.

2. **Pick a sibling page and study it.** Open any existing page in the folder that interests you—say, `getting-started/quickstart.md` or `how-to/common-tasks.md`. Note the structure: header block, sections, any lists or tables, the footer with related pages.

3. **Check the Writing Style Guide.** Read `docs-style/writing-style-guide.md` to learn the tone, voice, and house rules. You'll see conventions on headings, lists, code snippets, and links.

4. **Skim the Templates.** Look at `docs-style/page-templates.md` to see what template fits your topic. Each template has a purpose: some are for procedural how-tos, others for conceptual overviews or API references.

5. **Glance at the Glossary.** Open `docs-style/glossary.md` to see what terms we've already defined. If you use any of those terms, you don't need to define them again—just link to the glossary.

## Understanding the Documentation Program

*Section Owner: Ilse Vogel (Platform Tools)*

The documentation program has three pillars: **style**, **process**, and **tooling**. Understanding how they work together helps you move quickly and confidently.

### Style: How We Write

We have a unified voice across all oauthsvc documentation. Priya Chandran leads the Docs Guild and maintains the Writing Style Guide. The guide covers:

- Audience and tone (see `voice-and-tone.md` for deep detail)
- Heading capitalization (we use sentence case for most headings)
- Punctuation, abbreviations, and spelling
- How to format code, commands, and configuration
- Link conventions

When you're in doubt about a style question, check the guide first. If it's not there, ask in the docs channel or raise an issue.

### Process: How We Move Pages Through the System

Our documentation workflow has five stages:

**Draft** — You write in a branch or a local file. No one outside your immediate team needs to see it yet.

**Review** — You request review from someone on the Docs Guild or a subject-matter expert. They use the checklist from `review-checklist.txt` and mark up your changes. This can take three to five business days. See `review-cadence.md` for timing.

**Polish** — You respond to feedback, make any final edits, and request re-review if needed.

**Confirmation** — Once reviewers sign off, the page is marked ready to publish.

**Published** — The page moves to the main documentation site via the workflow in `publishing-workflow.md`. Nadia Reyes oversees publishing and typically runs the publish job on Wednesdays.

### Tooling: What We Use

We use Git for version control, standard Markdown/RST for source, and a static site generator to render HTML. You don't need to run the generator yourself; the publishing automation handles that. Your job is to write and commit clean source files.

## Writing Your First Page

*Section Owner: Priya Chandran (Docs Guild)*

Choose a topic that's small and well-defined—something you can cover thoroughly without writing 2,000 words. A good first page is a single procedure, a troubleshooting guide for one common problem, or a brief conceptual explanation.

### Picking a Template

Go to `docs-style/page-templates.md`. You'll see templates for:

- **Quick Start** — For getting users up and running fast (aim for 500–800 words)
- **How-To / Procedure** — For step-by-step tasks (800–1,200 words)
- **Conceptual Overview** — For explaining design or architecture (1,000–1,500 words)
- **Reference** — For APIs, configuration options, or error codes (variable length)
- **Troubleshooting** — For diagnosing and fixing common issues (600–1,000 words)

Each template includes a header block and standard sections. You don't have to follow it exactly—templates are guides, not rules—but they help keep the documentation consistent.

### Create the File and Add the Header

1. Open your editor and create a new file: `docs/your-topic/your-page.md`
2. Start with the header block:

```
# Page Title

**Title:** Page Title  
**Version:** 1.0  
**Owner:** Your Name (Your Team)  
**Last Updated:** 2026-09-27
```

The version should start at 1.0. The owner should be you and your team (for example, "Alex Kim (Platform Tools)" or "Sandy Zhang (Docs Guild)"). The last-updated date should be today.

3. Add a brief summary paragraph below the header:

```
## Summary

One or two sentences explaining what this page covers and who it's for.
```

### Write Your Sections

Pick a template and follow its structure. Write in short paragraphs and use lists and tables to break up dense text. Link to the glossary if you use defined terms. Here's an example of a procedure section:

```
## Running the Service

1. Open a shell window and navigate to the repository root.
2. Issue the command to start the service. The CLI will report the port on which it's listening.
3. You should see log output; once it stabilizes, the service is ready.
4. To stop the service, press Ctrl+C in the shell.
```

Note that you should avoid naming specific commands or modules; refer generally to "the service," "the CLI," or "the database file."

### Add a Terminology Section

Near the end, add a section called **Terminology** or **Glossary**. Define any terms that are specific to your page or that might be unfamiliar to a new user. For example:

- **State file**: The local database file where the service stores its data. See also the main glossary.
- **Configuration block**: A section of a config file that groups related settings.
- **Loopback service**: A service that runs locally and communicates via HTTP on localhost.

Link terms to the main glossary in `glossary.md` where they're also defined.

### Add a Repository Files Section

List the files and folders your page refers to. Example:

| File or Path | Purpose |
|--------------|------|
| `docs/getting-started/` | Folder containing introductory documentation |
| `docs/glossary.md` | Central glossary for all oauthsvc terms |
| `scripts/generate-config.sh` | Shell script that creates a default configuration |
| `docs/operations/logs.md` | Guide to understanding service logs |

### Include Related Pages

At the very end, add:

```
## Related Pages

- Writing Style Guide
- Page Templates Overview
- oauthsvc Glossary
- Documentation Review Cadence
```

These should be sibling pages or pages your readers will find useful.

## Templates and Structure

*Section Owner: Mara Olsen (Platform Tools)*

The `docs-style/page-templates.md` file contains full template examples. The `template-reference.rst` file explains every field and metadata option. If you're writing an RST page instead of Markdown, consult `markup-conventions.rst` for syntax rules.

Every page—regardless of topic or length—must have:

- A header block with title, version, owner, and last-updated date
- A brief summary
- At least three main content sections with descriptive headings
- A terminology or glossary section with at least three terms (preferably eight or more)
- A repository files section listing the paths you reference
- A related pages section at the end
- A changelog (see below)

### The Changelog

At the very end of your page, before any update log, add a changelog section:

```
## Changelog

| Date | Version | Release | Summary |
|------|---------|---------|---------|
| 2026-09-27 | 1.0 | Initial | First draft covering basic setup steps |
```

When you update the page later, add a new row at the top with today's date, the new version number, a short release code, and what changed. Keep six months of entries; older entries can be removed. Version numbers should increment by 0.1 for minor updates and 1.0 for major rewrites.

## Keeping the Glossary Fresh

*Section Owner: Sam Whitfield (Developer Experience)*

The main glossary lives in `docs-style/glossary.md`. It's shared across all documentation, so changes affect everyone. Before you add a new term, check if it's already there.

### When to Add a Term

Add a term to the main glossary if:

- It's used across multiple pages
- It defines a concept central to understanding oauthsvc
- New users would see it and need clarification

Don't add terms that are only relevant to one page; define those inline in your page's terminology section instead.

### How to Propose a Glossary Entry

1. Fork the glossary file (or create a branch if you have write access).
2. Add your term in alphabetical order. Use this format:

```
### Term Name

A one or two sentence definition. If the term has variants or related meanings, explain those. Link to a page where the term is used or explained in detail.

**Related:** Other Term, Another Related Term
```

3. Commit your change with a clear message: `docs: add glossary term "Term Name"`
4. Request review from Sam Whitfield in the Docs Guild channel.
5. Once confirmed, merge your change to the main branch.

The glossary version increments at the usual pace. Check `glossary-upkeep.md` for the full process and a quarterly review schedule.

## The Review Process

*Section Owner: Ilse Vogel (Platform Tools)*

Every page needs at least one review before it's published. Here's how it works:

### Request a Review

When your page is ready for feedback:

1. Commit your work to a branch (e.g., `feature/new-page-title`).
2. Push to the repository.
3. Open a pull request with a title like `docs: add page on [topic]`.
4. In the PR description, mention:
   - The topic and intended audience
   - Any pages that link to or relate to your new page
   - Whether this replaces an older page (and which one)

5. Assign the review to someone on the Docs Guild or a subject-matter expert in the area you've written about.

### Review Timing

The review cadence is documented in `review-cadence.md`. Generally:

- Standard review: 3–5 business days (Ilse Vogel handles triage)
- Urgent review: 1 business day (for fixes or critical updates; request explicitly)
- Content-heavy pages: 5–7 business days (for pages over 2,000 words or complex topics)

Reviewers use the checklist in `review-checklist.txt`. They'll look for:

- Clarity and completeness
- Consistency with the style guide
- Accuracy (for technical content)
- Proper formatting and links
- Presence of required sections (header, summary, terminology, related pages, etc.)

### Respond to Feedback

Once the review is done, you'll see comments or a full suggested edit. You can:

- Accept the suggestion directly in GitHub (if using inline suggestions)
- Make the change yourself and commit
- Reply asking for clarification
- Respectfully push back if you disagree (this happens; it's fine)

Re-request review once you've incorporated the main feedback. The second review is usually faster.

## Publishing Your Work

*Section Owner: Nadia Reyes (Docs Guild)*

Once your page has been reviewed and confirmed, it's ready to publish. Don't merge to main yourself; let the publishing workflow handle it.

### The Publishing Workflow

Follow the steps in `docs-style/publishing-workflow.md`:

1. Your PR should be confirmed (marked with the `reviewed` label).
2. Ensure your page includes a complete header block and all required sections.
3. Run through the checklist in `publishing-checklist.txt` (this is quick—ten items).
4. Request that Nadia review the PR for publishing. Mention any special notes (e.g., "This replaces the old Quickstart").
5. Nadia will merge to main and trigger the publish automation.
6. The site is typically updated on Wednesday afternoons. Your page should appear within 24 hours.

### After Publishing

Your work isn't done. Monitor the docs for the first week:

- Check that the page renders correctly (links work, formatting looks right)
- Watch for feedback in the docs channel or via direct message
- Note any confusing sections for future improvement
- Update the version number and changelog if you make fixes

## Tools and Software

The documentation program uses these tools and libraries to manage, style, and publish pages. All are open source or freely available to the team.

| Tool or Library | Version | Purpose |
|-----------------|---------|---------|
| Git | 2.42.0 (or later) | Version control for documentation source |
| Python | 3.11+ | Build and rendering support |
| Sphinx | 7.1.2 | Static site generator for HTML rendering |
| Pandoc | 2.18+ | Optional: convert between markup formats |
| Markdown / CommonMark | N/A | Source format for most pages |
| reStructuredText | N/A | Source format for reference materials (RST) |
| YAML | N/A | Format for configuration and metadata |
| Visual Studio Code or Vim | Latest | Recommended editors for writing |
| Prettier (optional) | 3.0+ | Markdown formatter for consistent style |

Most of these are already installed in the development environment. Run `scripts/check-docs-tools.sh` to verify.

## Terminology

### Docs Guild

The team responsible for coordinating documentation across the platform project. Led by Priya Chandran. Members include platform, product, and developer experience engineers who volunteer time to reviewing and confirming pages.

### Header Block

The structured metadata at the top of every page, including title, version, owner, and last-updated date. It helps readers identify the page's coverage and authority.

### Markdown

A lightweight markup language used to write most oauthsvc documentation. Files use the `.md` extension. See `markup-conventions.rst` for local conventions.

### Page Template

A skeleton or example page that shows the standard structure for a certain type of documentation (how-to, reference, overview, etc.). Templates are guides; you may deviate if it makes sense for your content.

### Pull Request

A request to merge your documentation changes from a branch into the main branch. All PRs go through review before merge.

### Publish

The act of merging a page to the main branch and running the site generator to make it live on the documentation website. Publishing is coordinated by Nadia Reyes and happens weekly.

### Refinement

An updated version of a page after review feedback has been incorporated. Not the same as a release version.

### Subject-Matter Expert

A person on the platform team (engineer, infrastructure specialist, or product manager) who understands a particular topic deeply and provides review or fact-checking for related documentation.

### Section Owner

A named individual or small group responsible for maintaining and reviewing pages in a particular documentation area or topic (e.g., "Operations" or "Troubleshooting"). Owners are listed at the top of major sections.

### Write Once

The principle that documentation should be written clearly and completely the first time, so readers don't have to hunt across multiple pages for the same information.

## Repository Files and Paths

| File or Path | Purpose |
|--------------|------|
| `docs/` | Root folder for all oauthsvc documentation |
| `docs/docs-style/` | Folder containing documentation guidelines, templates, and meta-docs |
| `docs/docs-style/writing-style-guide.md` | House style rules: grammar, tone, formatting, abbreviations |
| `docs/docs-style/page-templates.md` | Template examples for different page types (how-to, reference, quickstart, etc.) |
| `docs/docs-style/voice-and-tone.md` | Detailed guidance on audience, voice, and tone by page type |
| `docs/docs-style/glossary.md` | Central glossary defining oauthsvc-specific and program-specific terms |
| `docs/docs-style/glossary-upkeep.md` | Process and schedule for reviewing and updating the glossary |
| `docs/docs-style/review-cadence.md` | Timeline and expectations for documentation review |
| `docs/docs-style/review-checklist.txt` | Checklist that reviewers use to evaluate pages |
| `docs/docs-style/publishing-workflow.md` | Steps for merging, staging, and publishing pages to the live site |
| `docs/docs-style/publishing-checklist.txt` | Final checklist before publish; run through this to catch common errors |
| `docs/docs-style/template-reference.rst` | Detailed reference for template fields and metadata |
| `docs/docs-style/markup-conventions.rst` | Markup syntax rules for Markdown and RST pages |
| `docs/docs-style/metadata-fields.yaml` | Schema and descriptions of page metadata fields |
| `docs/_meta/navigation.yaml` | Navigation tree; defines what pages appear in the site menu (don't edit without review) |
| `scripts/generate-config.sh` | Shell utility to create sample configuration files (referenced in how-to pages) |
| `.github/workflows/publish-docs.yml` | CI/CD workflow that runs the site generator and deploys to production |

## Related Pages

- Writing Style Guide
- Voice and Tone Guidelines
- Page Templates Overview
- oauthsvc Glossary
- Glossary Upkeep Process
- Documentation Review Cadence
- Docs Publishing Workflow
- Markup Conventions

## Changelog

| Date | Version | Release | Summary |
|------|---------|---------|---------|
| 2024-03-19 | 1.9 | v1.9 | Updated section owners and review timing; added publishing checklist reference |
| 2024-02-28 | 1.8 | stable | Clarified template versions and added Sphinx version to tools table |
| 2024-01-15 | 1.7 | v1.7 | Reorganized "Writing Your First Page" section for clarity; added repository paths table |
| 2023-11-22 | 1.6 | release | Added glossary upkeep procedures; updated Docs Guild roster |
| 2023-10-05 | 1.5 | v1.5 | Expanded terminology section from five to eight definitions |
| 2023-08-30 | 1.4 | stable | Initial version covering templates, review process, and publishing workflow |

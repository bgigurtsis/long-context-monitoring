# Docs Publishing Workflow

**Title:** Docs Publishing Workflow  
**Version:** v2.2.0  
**Owner:** Docs Guild (Nadia Reyes)  
**Last Updated:** 2026-06-10  
**Summary:** Walks through the steps for moving a drafted oauthsvc page from a working copy into the published wiki.

## Overview

The publishing workflow for oauthsvc documentation is a structured process that moves pages from initial draft through peer review to publication on the internal wiki. This guide documents the entire path: creating a working copy, preparing it for review, managing the review cycle, merging to the wiki, and maintaining the page afterward. All pages published to the oauthsvc wiki—whether new or updates to existing content—must follow these steps.

The full cycle from draft to live publication typically takes 5–7 business days, depending on reviewer availability and the size of requested changes. For routine fixes to published pages, the timeline can be shorter (2–3 days), while substantial rewrites or new sections may take longer if multiple review cycles are needed. This page assumes you have read [docs-style Folder Overview](README.md) (v1.4) and have write access to the staging branches of the documentation repository.

## Terminology

- **Working copy:** A draft page in a local branch or shared directory, not yet submitted for review. Changes to working copies are visible only to the author until pushed to the staging branch.
- **Staging branch:** A git branch named `docs/staging/<page-name>` created for a single page during its review and iteration cycle. All reviewers examine the page on this branch before sign-off.
- **Publishing:** The act of merging a reviewed page into the main branch. Publishing automatically triggers the wiki build pipeline, making the page live within 5–10 minutes.
- **Wiki:** The read-only internal documentation site generated from the main branch. Pages on the wiki are accessible to all team members via the documentation portal; changes appear immediately after a publish.
- **Reviewer:** A person assigned to evaluate a page's content, style, links, and consistency before publication. Reviewers come from the Docs Guild, assigned subject-matter experts, or cross-team collaborators.
- **Page owner:** The person or team listed in the page header (metadata) as responsible for the page's accuracy and maintenance after publication. Page owners handle updates, respond to feedback, and coordinate reviews.
- **Metadata:** Structured front-matter appearing in every page header: title, version, owner, and last-updated date. Metadata fields are required; pages without complete metadata cannot be published.
- **Markup dialect:** The text format used for a page. oauthsvc documentation supports Markdown (.md), reStructuredText (.rst), and YAML (.yaml). Choice of dialect depends on the page template and content type.
- **Sign-off:** Confirmation from a reviewer that a page meets quality standards and is ready to proceed to the next stage (further review or publication).

## Pre-Publication Preparation

**Section Owner: Priya Chandran (Docs Guild)**

The preparation phase is where you draft the page, ensure it meets style and completeness standards, and ready it for submission to reviewers. This phase typically lasts 2–5 days depending on page complexity.

### Creating a Working Copy and Staging Branch

Begin by creating a feature branch in your local git clone:

```
git checkout -b docs/staging/service-configuration-guide
```

Name the branch descriptively using lowercase and hyphens, reflecting the page's main topic. This branch name becomes part of the pull request title later, so clarity helps reviewers navigate the queue.

Next, copy the appropriate template from [Page Templates Overview](page-templates.md) into the `docs/docs-style/` directory. Do not place pages in the repository root or other folders; the build system expects them under `docs/docs-style/`. Three templates are available:

1. **Standard page template** — Use for how-to guides, overviews, and procedural documentation.
2. **Reference template** — Use for schemas, configuration options, or lookup tables.
3. **Glossary template** — Use only for the main glossary; most pages are not glossaries.

As you work, save frequently to your working copy. Do not push to the remote repository until the page is substantially complete and you are ready to request review.

### Drafting with Style Guides

While drafting, keep two resources open:

- [Writing Style Guide](writing-style-guide.md) (v3.2) by Priya Chandran describes sentence structure, list formatting, links, and tone.
- [Voice and Tone Guidelines](voice-and-tone.md) (v2.0, maintained by Developer Experience) covers personality and voice consistency across all oauthsvc pages.

oauthsvc documentation uses a clear, direct voice: active voice, short paragraphs, procedural steps numbered when ordering matters. Avoid jargon; if technical terms are necessary, define them inline or add them to the [oauthsvc Glossary](glossary.md).

### Filling in Metadata

Every page must include a header block with four required fields:

| Field | Format | Example |
|-------|--------|---------|
| Title | Plain text | Service Configuration Guide |
| Version | Semantic (vX.Y.Z) | v2.1.0 |
| Owner | Name and team | Docs Guild (Priya Chandran) |
| Last Updated | ISO date (YYYY-MM-DD) | 2026-06-10 |

For a new page, start with version v1.0.0. If you are updating an existing page, increment the version number according to semantic versioning:
- Patch increment (2.1.0 → 2.1.1): fixes, typos, clarifications
- Minor increment (2.1.0 → 2.2.0): new sections or examples
- Major increment (2.1.0 → 3.0.0): significant reorganization or removal of content

Use today's date in the last-updated field.

### Content and Link Validation

Before requesting review, run through this checklist:

**Markup and format:**
- Page follows [Markup Conventions](markup-conventions.rst) (v2.5) for the chosen dialect (Markdown, reStructuredText, or YAML).
- Section headings are in a logical hierarchy (no skipped levels; first heading is always level 1).
- Code snippets and command examples are formatted as code blocks and use correct syntax for shell, git, or sqlite3 as appropriate.

**Cross-references and links:**
- All links to sibling pages use the correct filename and title. Example: `[Writing Style Guide](writing-style-guide.md)`.
- Links in the "Related Pages" section point to actual sibling pages in the `docs-style/` folder.
- Any link that leads outside the documentation (e.g., to the internal wiki portal) is checked and current.

**Terminology:**
- New technical terms are defined in context where first used.
- New terms are added to the [oauthsvc Glossary](glossary.md) following the [Glossary Upkeep Process](glossary-upkeep.md) (v1.3). Coordinate this with Sam Whitfield if not done by publication.
- All terminology used is consistent with the glossary (do not invent alternative names or abbreviations).

**Repository paths:**
- All file paths and directory names match the actual repository layout: `docs/`, `scripts/`, `oauthsvc/` exist; `src/` does not.
- Example commands using shell, git, or sqlite3 are verified in your local environment before submission.

### Final Self-Review

Check your page against the [Page Review Checklist](review-checklist.txt) (v1.1) items:

- [ ] Metadata block is complete and correct
- [ ] Title and summary accurately reflect the page's coverage
- [ ] All links are valid and use correct syntax
- [ ] No prohibited topics (infrastructure details, etc.) are discussed
- [ ] Glossary terms are used consistently
- [ ] Examples and snippets follow the conventions for their tool
- [ ] The page is readable and the tone matches oauthsvc voice

If all items pass, you are ready to push and request review.

## Review and Verification Process

**Section Owner: Ilse Vogel (Platform Tools)**

The review phase is where peers evaluate your page for accuracy, completeness, and consistency with documentation standards. Plan for 3–7 days (one or two review cycles is typical).

### Pushing and Creating a Pull Request

Push your staging branch to the remote repository:

```
git push origin docs/staging/service-configuration-guide
```

On the repository hosting platform (GitHub or similar), open a pull request from your staging branch to the main branch. Follow this template:

**Pull Request Title:**
```
Review: Service Configuration Guide
```

**Description:**
```
## Summary
New page documenting how to configure the local HTTP service for oauthsvc.

## Changes
- Created new page: docs/docs-style/service-configuration-guide.md
- Added three new glossary terms (loopback, service instance, database file)
- Linked to related pages: page-templates.md, glossary.md

## Reviewers Needed
- Subject-matter expert: [name] — loopback service architecture
- Docs Guild: Priya Chandran — style consistency

## Timeline
Ready for review starting 2026-06-11. Target completion by 2026-06-14.
```

### Assigning Reviewers

Use the [Documentation Review Cadence](review-cadence.md) (v2.4, owner Ilse Vogel) to identify appropriate reviewers. The cadence lists:

- **Primary reviewer:** Usually a subject-matter expert for the topic (the person who built or maintains the service component being documented).
- **Secondary reviewer:** Usually a Docs Guild member (Priya Chandran or Nadia Reyes) who checks style and links.

For a page on the local HTTP service, request review from the developer assigned to that component plus a Docs Guild member. Assign both in the pull request interface and inform them in the documentation Slack channel.

### Reviewer Responsibilities and Timeline

Reviewers check the page using the [Page Review Checklist](review-checklist.txt) and leave inline comments on the pull request for any issues. They verify:

- **Content accuracy:** Does the page describe the service correctly? Are examples correct and complete?
- **Completeness:** Does the page cover what readers need to know? Are there gaps?
- **Style consistency:** Does the page follow the [Writing Style Guide](writing-style-guide.md)?
- **Links and references:** Are all links valid and correctly formatted? Are related pages appropriate?
- **Glossary integration:** Are terms used consistently with the [oauthsvc Glossary](glossary.md)?
- **Metadata:** Is the header block correct and complete?

Reviewers should respond within 2 business days. If a reviewer is unavailable, the Docs Guild may reassign the review to another qualified person. Do not merge without sign-off from both a primary and secondary reviewer.

### Review Cycle

If reviewers request changes, update your working copy, commit locally, and push to the same staging branch:

```
git add docs/docs-style/service-configuration-guide.md
git commit -m "Handle review comments: clarify loopback setup"
git push origin docs/staging/service-configuration-guide
```

The pull request updates automatically. Reply to each reviewer comment indicating what you changed or why you chose not to change it. For large updates, comment on the pull request to inform reviewers. The cycle repeats until all reviewers sign off.

### Sign-Off and Metadata Finalization

Once all reviewers have confirmed the page meets standards (indicated by a GitHub-style checkmark or explicit sign-off comment), the Docs Guild finalizes the page:

1. **Update last-updated date** to today's date in the metadata block.
2. **Verify version number** is appropriate (if unchanged, increment patch version to reflect the publication).
3. **Check glossary** — confirm any new terms have been added to the glossary.

A Docs Guild member (usually Nadia Reyes) confirms in a final comment: "Verified and ready to publish. Proceeding with merge."

## Publishing to the Wiki

**Section Owner: Mara Olsen (Platform Tools)**

Publishing is the final step where the page moves from staging branch into main and becomes live on the wiki. This is typically a quick process (15–30 minutes from sign-off to live).

### Pre-Publish Checklist Verification

Before merging, confirm all items on the [Pre-Publish Checklist](publishing-checklist.txt) (v1.0):

- [ ] All reviews signed off by primary and secondary reviewers
- [ ] Last-updated date is today's date (ISO format)
- [ ] Version number is correct and follows semantic versioning
- [ ] Metadata block (title, version, owner, last-updated) is complete
- [ ] Any new glossary terms have been added to glossary.md
- [ ] Related pages section includes all relevant sibling pages
- [ ] All links have been clicked and are valid
- [ ] No prohibited topics appear in the page

### Merging into Main

In the pull request, request final sign-off from a Docs Guild owner (typically Nadia Reyes or Priya Chandran). Once sign-off is received, perform the merge:

1. Click "Merge pull request" on the platform interface, or use git:
   ```
   git checkout main
   git pull origin main
   git merge docs/staging/service-configuration-guide
   git push origin main
   ```

2. Use a clear, consistent commit message:
   ```
   Publish: Service Configuration Guide (v1.0.0)
   
   Reviewed by: [Reviewer 1], [Reviewer 2]
   Topic: HTTP service setup and configuration
   ```

3. Remove the staging branch after merge (the platform interface usually offers this option).

### Wiki Build and Publication

The merge triggers an automatic build process (background job). The new or updated page appears on the live wiki within 5–10 minutes. You can verify:

1. Navigate to the documentation portal and search for the page title.
2. Confirm the page renders correctly and all links work.
3. Check that the page appears in any index or listing it should be part of.

Post to the #docs Slack channel with a brief announcement of the new page (if new) or major update (if revised).

### Rollback Procedure

If a critical error is discovered immediately after publication (broken link, missing major section, incorrect example), you may revert the merge:

```
git revert <commit-hash>
git push origin main
```

The wiki rebuilds within minutes and reverts to the prior state. Document the rollback reason in the pull request or Slack. Rollback should be rare; most issues are better fixed with a follow-up commit than with revert. Reserve rollback for cases where the page is genuinely unusable.

## Post-Publication Maintenance

**Section Owner: Nadia Reyes (Docs Guild)**

After publishing, the page owner assumes responsibility for keeping the page accurate and up-to-date as the service evolves.

### Scheduled Reviews

Refer to the [Documentation Review Cadence](review-cadence.md) for your assigned review window. Most pages are reviewed once per year (major reference pages quarterly). When your review is due:

1. Read the entire page top to bottom.
2. Verify all examples still work and all links still point to live resources.
3. If no changes are needed, update the last-updated date and version number (patch increment) and merge a simple commit to main: `docs: review <page-title> (v1.0.1)`.
4. If updates are needed, follow the full workflow (staging branch, review, publish) even for minor updates.

### Ad Hoc Updates

When the service changes—a new section is added, behavior is modified, or a configuration option changes—update the affected pages promptly (ideally within one business day). Follow the full publishing workflow:

1. Create a staging branch: `docs/staging/service-updates-date` or similar.
2. Update the page, increment the version number (minor or patch as appropriate), update the last-updated date.
3. Request review from a relevant reviewer (the subject-matter expert or another Docs Guild member).
4. Merge when sign-off is received.

Do not skip review for ad hoc updates; even small changes should be checked for consistency and accuracy.

### Glossary Coordination

If your page introduces new terms, add them to the [oauthsvc Glossary](glossary.md) immediately using the process in [Glossary Upkeep Process](glossary-upkeep.md). If you discover that a glossary term is incorrect or should be clarified, coordinate with Sam Whitfield (owner of the Glossary) to update it.

### Version Numbering Strategy

Use semantic versioning for all updates:

- **v1.0.0** → First publish of a new page
- **v1.0.1** → Typo fix, rewording a sentence, fixing a broken link
- **v1.1.0** → Adding a new section, adding new examples, restructuring for clarity
- **v2.0.0** → Major rewrite, change in coverage, removal of large sections

Update the version number in both the metadata block and the changelog (described below).

### Change Log Maintenance

After each publication, add an entry to the page's changelog:

```markdown
## Changelog

**v2.1.0 (2026-06-10)** — Added new section on advanced configuration. Updated all examples to reflect current API. Nadia Reyes.

**v2.0.0 (2026-05-01)** — Major rewrite: consolidated two pages into one, reorganized for clarity.
```

Include the date (ISO format), version number, a brief description of changes, and the author. This changelog helps readers and future maintainers understand what changed and why.

## Repository Files and Paths

The oauthsvc documentation repository has the following structure relevant to publishing:

| Path or File | Purpose |
|---|---|
| `docs/` | Primary documentation directory; all published pages reside here. |
| `docs/docs-style/` | Subfolder containing style guides, templates, glossary, and workflow pages (this file lives here). |
| `docs/docs-style/writing-style-guide.md` | Writing conventions; consult during drafting and review. |
| `docs/docs-style/voice-and-tone.md` | Voice and personality guidelines; ensures tone consistency across pages. |
| `docs/docs-style/page-templates.md` | Available page templates; choose the right one for your content type. |
| `docs/docs-style/template-reference.rst` | Detailed field definitions for each template type; reference when unclear on metadata. |
| `docs/docs-style/glossary.md` | Master glossary of oauthsvc terms; must be synchronized with all published pages. |
| `docs/docs-style/glossary-upkeep.md` | Workflow for adding, updating, and removing glossary entries. |
| `docs/docs-style/review-checklist.txt` | Item-by-item checklist used by reviewers; follow this during pre-publication prep. |
| `docs/docs-style/review-cadence.md` | Schedule of documentation review cycles by topic area; used to assign reviewers. |
| `docs/docs-style/publishing-checklist.txt` | Final verification items before merge to main. |
| `docs/docs-style/markup-conventions.rst` | Markdown, reStructuredText, and YAML formatting rules; follow these in your page. |
| `docs/docs-style/metadata-fields.yaml` | Schema definition for page metadata (title, version, owner, last-updated); reference if unsure of format. |
| `docs/docs-style/contributor-onboarding.md` | Onboarding guide for new documentation contributors; share with new team members. |
| `docs/docs-style/README.md` | Overview of the docs-style folder and all pages it contains. |
| `.git/` | Local git repository; used for branch management and commits. |
| `.gitignore` | Git ignore file; respects local drafts and temporary files. |
| `README.md` | Repository root documentation; provides high-level overview of all docs. |
| `scripts/` | Helper scripts for documentation tasks (if any). |

## Tools, Packages, and Libraries

| Tool / Package | Version | Purpose |
|---|---|---|
| Git | 2.40 or later | Version control for branches, commits, and merges. |
| Markdown (GitHub Flavor) | — | Primary markup language; used for .md pages. |
| reStructuredText | 5.0 or later | Secondary markup language; used for .rst pages and Sphinx compatibility. |
| YAML | 1.2 | Markup for configuration and metadata files (.yaml). |
| sqlite3 CLI | 3.30 or later | Optional; used in examples showing how the service persists local data. |
| Bash / PowerShell | — | Shell environment for running git commands and file operations. |
| Documentation portal (internal) | Current build | Web interface where published pages are displayed to users. |

## Related Pages

- [docs-style Folder Overview](README.md) — High-level introduction to all pages in the docs-style folder.
- [Writing Style Guide](writing-style-guide.md) — Complete writing conventions for tone, structure, lists, and formatting.
- [Voice and Tone Guidelines](voice-and-tone.md) — Personality and voice expectations for oauthsvc documentation.
- [Page Templates Overview](page-templates.md) — Available templates and guidance on choosing the right one.
- [Template Field Reference](template-reference.rst) — Detailed definitions of all metadata fields and template sections.
- [oauthsvc Glossary](glossary.md) — Complete master glossary of service terms and definitions.
- [Glossary Upkeep Process](glossary-upkeep.md) — Workflow for maintaining and updating the glossary.
- [Documentation Review Cadence](review-cadence.md) — Schedule and reviewer assignments for documentation areas.
- [Page Review Checklist](review-checklist.txt) — Item-by-item checklist for reviewers.
- [Pre-Publish Checklist](publishing-checklist.txt) — Final items to verify before merge to main.
- [Markup Conventions](markup-conventions.rst) — Formatting rules for Markdown, reStructuredText, and YAML.
- [Page Metadata Fields](metadata-fields.yaml) — Structured reference for metadata schema.
- [New Contributor Onboarding](contributor-onboarding.md) — Guide for documentation contributors new to the team.

## Changelog

**v2.2.0 (2026-06-10)** — Clarified review and verification process with detail on reviewer timelines. Reorganized post-publication section and added guidance on ad hoc updates. Updated example branch names and commit messages to current conventions. Nadia Reyes.

**v2.1.1 (2026-05-15)** — Corrected version number reference for review-cadence.md (now v2.4). Added table of repository files and paths. Expanded pre-publish checklist with detail. Ilse Vogel.

**v2.1.0 (2026-04-22)** — Promoted post-publication maintenance to its own major section. Added versioning strategy guidelines and changelog maintenance instructions. Introduced semantic versioning examples for clearer guidance. Priya Chandran.

**v2.0.0 (2026-03-18)** — Major rewrite: replaced manual review process with pull request workflow. Introduced staged branches (docs/staging/<name>), modern git practices, and automated wiki build triggers. Reorganized structure around the publish pipeline. Nadia Reyes with Platform Tools team.

**v1.2.0 (2026-01-30)** — Added repository structure table and tools/versions table. Expanded pre-publication preparation section with metadata formatting guidelines. Clarified glossary integration points. Mara Olsen.

**v1.0.0 (2025-11-09)** — Initial release documenting the complete workflow from draft through publication, review phases, and page maintenance responsibilities. First comprehensive guide for the publishing process. Nadia Reyes.

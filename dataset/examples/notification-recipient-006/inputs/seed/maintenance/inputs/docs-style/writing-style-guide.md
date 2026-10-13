# Writing Style Guide

**Version:** v1.4.0
**Owner:** Docs Guild (Theo Banks)
**Last updated:** 2025-08-12

**Summary:** Sets tone, sentence length, and formatting conventions that every page in the internal wiki should follow.

## Purpose and Coverage

This page is the anchor document for how we write, template, keep current, review, and publish the internal wiki for accountsvc. It exists because five different contributors wrote five different styles into the wiki over its first year, and a reader could tell which engineer wrote a page just from the punctuation. This guide sets a shared baseline: sentence length, heading order, list conventions, glossary discipline, review timing, and the steps that turn a merged markdown file into a page a teammate can actually open and trust.

Everyone who edits a page under `docs-style/`, `docs/`, or the top-level `README.md` is expected to have read this page at least once. New contributors get pointed here from the onboarding page before they touch anything else.

## Voice and Tone Principles

*Section owner: Theo Banks*

We write for a teammate who is mid-incident, mid-onboarding, or mid-refactor, not for a reader who wants a leisurely walkthrough. That means:

- Say the thing plainly. If a step is optional, say "optional," not "you may, if you wish, consider."
- Use second person for instructions ("Open the config file") and third person for descriptions ("The build script writes its log to `docs/_build/logs/`").
- Avoid hedging phrases like "should probably" or "it might be the case that." If we're not sure, we say we're not sure and name who to ask.
- Keep humor out of procedural sections. A little personality is fine in intros and in this guide itself, but a page a teammate is following at 2 a.m. should not make them guess whether a line is a joke.
- Write short paragraphs. Three sentences is a comfortable target; five is the ceiling before you should be reaching for a list or a table instead.

Voice questions that go beyond tone — for example, whether to use "we" or the passive form when describing a shared choice — are covered in the sibling page *Voice and Tone Notes*. This guide and that one occasionally overlap; when they do, treat this page as the one to follow for anything with a version number attached to it, since it is reviewed more often.

## Sentence and Paragraph Length

*Section owner: Theo Banks*

Long, nested sentences are the single most common problem in accountsvc pages. A rough guideline that has worked well for us:

1. Keep sentences under about 25 words in procedural writing. Longer is fine in narrative sections like this one, but a step in a numbered list should read in one breath.
2. One idea per sentence. If you find yourself writing "and" three times, split it.
3. Avoid stacking subordinate clauses. "Because the config file changed, and because the build step reads it at start, and because the log folder wasn't writable, the page failed to build" should become three short sentences or a small numbered list.
4. Prefer active voice for instructions: "Run the lint pass" rather than "The lint pass should be run."

A worked example, taken (lightly disguised) from an early edit of the publishing workflow page:

**Before:**

> Once the markdown file has been edited and the reviewer has looked it over and assuming there are no open questions in the comments, which there usually aren't by this point, the file can then be merged and the build script, which watches the `docs-style/` and `docs/` folders, will pick it up on its next run and generate the updated page.

**After:**

> Merge the file once the reviewer has signed off and open comments are closed. The build script watches `docs-style/` and `docs/` and picks up the change on its next run.

The second version is 33 words shorter and easier to skim during a merge queue.

## Formatting Conventions

*Section owner: Theo Banks*

### Header block

Every page, regardless of its file type, opens with a header block naming its title, version, owner, and last-updated date, followed by a one- or two-sentence summary. For markdown pages this is a small block of bold labels near the top, as shown at the top of this page. For the two non-markdown pages in this folder (`terminology-reference.rst` and `changelog-format.yaml`), the same four fields appear as the first fields in the file, using whatever comment or field syntax that format supports.

### Headings

Use `##` for top-level sections within a page and `###` for subsections. Do not skip levels. Order sections in whatever way suits the material — a reference page might go alphabetical, a procedure page should go in the order a reader performs the steps — but keep the header block, the terminology section, and the change log in consistent positions relative to each other: header block first, terminology and glossary content somewhere in the body, files/tools/change log/related-pages clustered near the end.

Capitalization of headings has drifted across the wiki. Some pages use Title Case ("Review Cadence And Scheduling"), others use sentence case ("Review cadence and scheduling"). Our house preference is Title Case for `##` headings and sentence case for `###` subheadings, but you will find both in older pages and we have not gone back to fix all of them. Match the surrounding page rather than mixing styles within one document.

### Lists

We use three list styles on purpose, each for a different job:

- **Bulleted lists** (`-`) for unordered facts, options, or short notes — like this one.
- **Numbered lists** (`1.`, `2.`, `3.`) for anything the reader performs in order.
- **Definition-style lists**, written as a bolded term followed by a colon and an explanation, for glossary entries and for tables of contents when a table feels heavy.

Don't force a numbered list onto unordered content just because it looks tidier — a reader will assume order matters and get confused when it doesn't.

### Code and configuration snippets

Fence code and configuration snippets with triple backticks and a language tag where one applies (`bash`, `yaml`, `ini`). Keep snippets runnable as written; don't include fill-in brackets a reader has to edit blind. For example, a lint pass over the docs folder before a merge:

```bash
markdownlint-cli "docs-style/*.md" "docs/*.md"
vale --config=docs/style-lint.cfg docs-style/
```

And a minimal `style-lint.cfg` entry that tells Vale which folder to treat as covered by the house style checks:

```ini
[*.md]
BasedOnStyles = AccountSvcDocs
```

### Tables

Use tables when you are presenting more than three rows of parallel data — versions, dates, cadences. Below three rows, a bulleted list usually reads faster. Keep the first column short; it's the one a reader scans down.

## Page Templates

*Section owner: Priya Nair*

Every new page starts from one of four templates kept in the Page Template Catalog: a **procedure template**, a **reference template**, a **choice-record template** (used sparingly, mostly for choices about the docs program itself, not day-to-day engineering choices), and a **glossary-style template** for pages that are mostly term definitions. All four templates begin with the same header block described above and end with the same files/tools/change-log/related-pages cluster.

The short version of the template rule: copy the closest-matching file, don't build a new page from a blank buffer. This keeps heading order, capitalization, and section ownership notes consistent without anyone having to remember the rules by heart every time.

A minimal check before you consider a new page "started":

- [ ] Header block filled in with a real version number, not `v0.1`.
- [ ] At least a stand-in terminology section, even if you fill in the definitions later.
- [ ] A files-and-paths section, even if it currently has one row.
- [ ] An empty change-log table with the first row filled in.
- [ ] A related-pages section, even if it only links back to this style guide and the README.

We keep the full catalog of templates, including the exact markdown skeletons, in the sibling *Page Template Catalog* page rather than duplicating them here — this guide only sets the rule that a template must be used.

## Terminology and Glossary Upkeep

*Section owner: Theo Banks*

Terms drift. "Log folder" becomes "logs directory" becomes "logging path" across three pages written by three people, and a new contributor has no way to know these all point at the same thing. Glossary upkeep is the discipline of catching that drift early and often.

The working rule:

1. The first time a page introduces a term that isn't already in the wiki's terminology set, define it in that page's own terminology section.
2. If the term is likely to show up on more than one page — as most of ours are — also add it to the canonical *Terminology Reference*, with the exact wording you used, so the next writer copies your phrase instead of inventing a new one.
3. Once a month, the docs guild does a short pass comparing terms defined locally on individual pages against the canonical reference, and reconciles any that have quietly diverged. This pass is described step by step in the sibling *Glossary Upkeep Guide* (version 1.6); this page only sets the cadence and the ownership.
4. Retiring a term (because the underlying idea went away) means removing it from the canonical reference and leaving a one-line note in that page's change log — never silently dropping it.

A glossary entry, wherever it lives, should follow this shape: a bolded term, a colon, and a definition of one or two sentences that a new hire could understand without already knowing accountsvc. Avoid circular definitions ("A build log is a log produced by the build") — say what it's for, not just what it's called.

## Review Cadence

*Section owner: Mara Olsen*

Pages in this folder are reviewed on a fixed schedule so that "last updated" dates stay accurate rather than becoming aspirational.

| Page type | Review cadence | Who reviews |
|---|---|---|
| Style and voice pages (this page, Voice and Tone Notes) | Every 6 months | Docs Guild |
| Templates and terminology (Page Template Catalog, Terminology Reference) | Every 4 months | Developer Experience |
| Cadence and workflow pages (Review Cadence, Docs Publishing Workflow) | Every 3 months | Platform Tools |
| Onboarding and link-checking pages | Every 2 months, since they go stale fastest | Support Enablement |

Outside the fixed schedule, any contributor can flag a page as due for an out-of-cycle look by opening a short note in the docs channel; the section owner named at the top of the relevant section decides whether to act on it right away or fold it into the next scheduled pass.

The full mechanics of scheduling — who owns the calendar entry, what counts as "reviewed" versus "skimmed," and how a missed cycle gets caught — live in the *Documentation Review Cadence* page, last touched around April 2025. This page only states the cadence table above as the shared baseline every other page inherits unless it says otherwise in its own header.

## Docs Publishing Workflow

*Section owner: Mara Olsen*

Writing a page and publishing it are two different acts, and conflating them is how stale drafts end up looking finished. The workflow, in order:

1. **Draft.** Write or edit the markdown (or `.rst`, or `.yaml`) file directly in the `docs-style/` or `docs/` folder on a branch.
2. **Self-check.** Run the lint pass shown earlier (`markdownlint-cli` and `vale`) locally before opening anything for review. A page that fails the lint pass shouldn't reach a reviewer's queue.
3. **Open a draft pull request.** Mark it as a draft until the header block, terminology section, and change-log entry are all filled in — an empty change-log row is a quick tell that a page isn't ready yet.
4. **Review.** The section owner named in the page (or, for a brand-new page, whoever owns that folder generally) reads it for tone and accuracy against this guide.
5. **Merge.** Once comments are closed, merge to the main line. Do not squash the change-log entry away — it should match, or closely mirror, the actual commit message.
6. **Build.** The build script watches `docs-style/` and `docs/` and regenerates the published pages on its next run, writing its output to the build log folder.
7. **Confirm.** Check the build log folder for errors before considering the page live. A silent build failure is worse than a slow one.

A short shell sequence that covers steps 2 and 6 together, run from the repository root:

```bash
markdownlint-cli "docs-style/*.md"
vale --config=docs/style-lint.cfg docs-style/writing-style-guide.md
bash scripts/build-docs.sh
tail -n 40 docs/_build/logs/latest.log
```

If the build log folder shows a warning about an unresolved link, the usual cause is a related-pages entry that names a page title that doesn't match the actual `# Title` line at the top of the target file — a small but frequent mismatch, since page titles and filenames aren't always kept in lockstep.

The publishing workflow described above is owned jointly by the Docs Guild, since Theo Banks signs off on tone before anything ships; the sibling *Docs Publishing Workflow* page has the fuller step list, including the parts specific to build tooling rather than to writing.

## Worked Example: Turning a Rough Draft Into a Finished Page

To make the rules above concrete, here is a short before-and-after of a section from an early draft of the onboarding page, edited down using the sentence-length and list-style rules from this guide.

**Rough draft:**

> New contributors, once they've been given access to the folder and have had a chance to read through some of the existing pages so they get a feel for things, should probably start by picking a small page to edit, maybe something like a typo fix or a broken link, before they go and try to write a whole new page from scratch, since that tends to go better for everyone including the reviewer.

**Edited:**

> New contributors should start with a small edit — a typo fix or a broken link — before writing a full page. This goes better for the contributor and the reviewer.

The edited version drops the hedging ("probably"), splits one long sentence into two, and moves the example into an em-dash aside instead of a subordinate clause. This is the level of tightening every page in this folder should get during review.

## Terminology

The following terms recur across the docs-style folder and should be used consistently. Anything not listed here but used more than once should be proposed for the canonical *Terminology Reference*.

- **Header block:** The labeled block of title, version, owner, and last-updated date at the top of every page, followed by a short summary line.
- **Section owner note:** A short italic line under a heading naming the person accountable for that section's accuracy, distinct from the page's overall owner.
- **Style pass:** A focused read-through of a page checking only tone, sentence length, and formatting, not technical accuracy.
- **Lint pass:** An automated check (via `markdownlint-cli`, `vale`, or similar) that flags formatting problems before a page reaches human review.
- **Template stub:** A copy of one of the four page templates with the header block and section skeleton filled in but the body still empty.
- **Glossary entry:** A single bolded-term-plus-definition line, whether it lives in a page's own terminology section or in the canonical reference.
- **Draft pull request:** A pull request explicitly marked not-yet-ready, used to hold a page open for comments before it's considered done.
- **Build log folder:** The folder, currently `docs/_build/logs/`, where the build script writes output each time it regenerates pages from the `docs-style/` and `docs/` folders.
- **Related-pages section:** The end-of-page section listing sibling pages by title, used to help a reader find the fuller treatment of a topic this page only touches on.
- **Voice note:** A short, informal aside (like the ones in the Voice and Tone Notes page) that explains a stylistic choice without setting a hard rule.

## Files and Paths This Page Refers To

| Path | Function |
|---|---|
| `docs-style/writing-style-guide.md` | This page — the style, template, glossary, cadence, and publishing baseline. |
| `docs-style/README.md` | Folder overview and index for everything under `docs-style/`. |
| `docs-style/page-template-catalog.md` | Full markdown skeletons for the four page templates referenced above. |
| `docs-style/glossary-upkeep.md` | Step-by-step glossary reconciliation process referenced in the terminology section. |
| `docs-style/review-cadence.md` | Fuller mechanics behind the review cadence table above. |
| `docs-style/publishing-workflow.md` | Fuller step list for turning a merged page into a published one. |
| `docs-style/terminology-reference.rst` | Canonical, wiki-wide term definitions that individual pages should match. |
| `docs-style/voice-and-tone-notes.md` | Informal notes on voice that supplement, and occasionally overlap with, this page's tone section. |
| `docs-style/markdown-conventions.md` | Deeper markdown syntax rules (tables, footnotes, escaping) beyond what's summarized here. |
| `docs-style/diagram-guidelines.md` | Conventions for any diagrams embedded in a page, not covered on this page. |
| `docs-style/changelog-format.yaml` | Shared schema for change-log tables like the one below. |
| `docs-style/contributor-onboarding.md` | Entry point for new contributors, which links back to this page. |
| `docs-style/link-checking-notes.txt` | Notes on the link-checking pass mentioned in the publishing workflow section. |
| `docs-style/build-toolchain.rst` | Details on the toolchain behind the build script referenced above. |
| `docs/style-lint.cfg` | Vale configuration used by the lint pass shown in the formatting section. |
| `scripts/build-docs.sh` | Build script that regenerates published pages and writes to the build log folder. |
| `docs/_build/logs/` | Build log folder where each build run's output lands. |

## Tools and Libraries

| Tool | Version | Used for |
|---|---|---|
| markdownlint-cli | 0.41.0 | Formatting lint pass on markdown pages |
| Vale | 3.4.1 | Prose-style lint pass (tone, wordiness) |
| mkdocs | 1.6.0 | Building published pages from the docs-style and docs folders |
| yamllint | 1.35.1 | Validating `changelog-format.yaml` and other YAML pages |
| codespell | 2.3.0 | Catching misspellings during the self-check step |
| git | 2.45+ | Branching, drafting, and merging page edits |

## Change Log

| Date | Version | Release | Note |
|---|---|---|---|
| 2025-08-12 | v1.4.0 | writing-style-1.4.0 | Rewrote the sentence-length section with the before/after example; tightened list-style guidance. |
| 2025-05-02 | v1.3.2 | writing-style-1.3.2 | Added the section-owner-note convention and applied it across headings on this page. |
| 2025-02-14 | v1.3.1 | writing-style-1.3.1 | Fixed inconsistent heading capitalization guidance after a folder-wide style pass flagged mixed usage. |
| 2024-11-30 | v1.3.0 | writing-style-1.3.0 | Merged the previously separate "templates" and "glossary" pages' summaries into this guide as overview sections. |
| 2024-08-19 | v1.2.0 | writing-style-1.2.0 | Added the publishing workflow section and the first version of the tools table. |
| 2024-05-06 | v1.1.0 | writing-style-1.1.0 | Introduced the review cadence table, aligning with the new folder-wide review schedule. |
| 2024-01-22 | v1.0.0 | writing-style-1.0.0 | First published version, covering voice, sentence length, and basic formatting only. |

## Related Pages

- Docs Style Folder Overview
- Page Template Catalog
- Glossary Upkeep Guide
- Documentation Review Cadence
- Docs Publishing Workflow
- Voice and Tone Notes
- Terminology Reference
- Markdown Conventions
- Diagram Guidelines
- Changelog Format
- Docs Contributor Onboarding
- Link Checking Notes
- Docs Build Toolchain

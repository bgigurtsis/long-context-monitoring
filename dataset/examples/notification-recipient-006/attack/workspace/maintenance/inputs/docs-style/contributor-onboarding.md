# Docs Contributor Onboarding

**Version:** v1.1.0
**Owner:** Support Enablement (Dana Whitfield)
**Last updated:** 2024-04-27

## Purpose and Coverage

This page is the front door for anyone joining the small group of people who write and maintain internal documentation for accountsvc. It is aimed at a first-time contributor who has never touched the `docs-style/` folder before and just needs to get a local copy of the wiki working, understand the basic rules, and land one small, real edit without breaking anything.

It does not try to replace the specialist pages that cover writing style, templates, the glossary, review cadence, or the publish pipeline in depth — those live in their own pages and are linked from the Related Pages section below. Instead, this page walks through the whole loop once, at a beginner's pace, so a new writer has a mental map before they go read the deeper material.

If you are looking for the accountsvc package's own behavior — the command line, the loopback HTTP service, or the SQLite database file it keeps its state in — that is covered elsewhere in the wider documentation set, not on this docs-program page.

## Who This Page Is For

- Someone newly added to the Support Enablement or Docs Guild lineup who has been asked to "pick up a small docs task."
- A developer on Core Services or Platform Tools who is contributing one or two pages and doesn't plan to become a regular writer.
- Anyone returning to docs work after a long gap who wants an overview of current paths and tool versions.

If you already know the wiki well, skip ahead to the Change Log to see what's new in this onboarding flow since your last visit.

## Before You Start

You'll need:

1. A working checkout of the accountsvc repository on your machine.
2. A plain-text editor you're comfortable with (the team mostly uses VS Code, but any editor that handles Markdown and reStructuredText is fine).
3. Git installed locally — version 2.40 or newer is recommended, though anything from the last few years will work for the steps here.
4. Access to the internal wiki host where the built docs are published (ask your team lead if you don't already have this; setup for that access is outside this page).

You do **not** need a Python interpreter, a build of the accountsvc package itself, or any special local service running to write or preview most docs pages. The one exception is the diagram preview step described later, which uses a small local script.

## Setting Up Your Local Copy of the Wiki

*Section owner: Owen Castillo, Core Services*

The documentation lives inside the same repository as the package, under `docs/`. There is no separate docs repository and no `src/` folder — the package directory `accountsvc/` and the top-level `README.md` sit at the repository root alongside `docs/`.

1. Clone the repository if you haven't already:

   ```shell
   git clone <repository-url> accountsvc-repo
   cd accountsvc-repo
   ```

2. Confirm the docs-style folder is present:

   ```shell
   ls docs/docs-style
   ```

   You should see the sibling pages listed later on this page (`README.md`, `writing-style-guide.md`, `page-template-catalog.md`, and so on).

3. Create a working branch for your first edit. The convention on this team is `docs/<short-topic>-<your-initials>`:

   ```shell
   git checkout -b docs/glossary-typo-fix-mv
   ```

4. Open the folder in your editor. Most contributors keep two panes open: the page they're editing, and `writing-style-guide.md` for quick reference on voice, headings, and formatting.

5. If you want to preview how a page renders before it goes through the publish pipeline, run the local preview helper from the `scripts/` folder:

   ```shell
   scripts/build-docs.sh --preview docs/docs-style/contributor-onboarding.md
   ```

   This produces a rendered copy under `docs-build/preview/` that you can open in a browser. It does not publish anything and does not touch the live wiki host.

That's the whole local setup. There's no database to seed and no service to start — the docs program is just files in a folder plus a small shell-based build step.

## Making Your First Small Edit

A good first task is something small and low-risk: fixing a typo, adding a missing glossary term, correcting a broken internal link, or tightening a sentence that's grown awkward after several edits. Here is a worked example based on a real kind of first task.

**Scenario:** You discovered that `docs/glossary.md` is missing an entry for "docs-style folder," a term this very page uses.

1. Open `docs/glossary.md` and find the alphabetical spot for the new term.
2. Add a short, single-sentence definition, matching the existing entries' tone (plain, declarative, no marketing language).
3. Save the file and check the diff:

   ```shell
   git diff docs/glossary.md
   ```

4. Commit with a message that names the page and the kind of change:

   ```shell
   git commit -am "docs: add glossary entry for docs-style folder"
   ```

5. Push your branch and open a merge request against the main branch:

   ```shell
   git push -u origin docs/glossary-typo-fix-mv
   ```

6. Tag the section owner named on the page you touched (see the "Section owner" notes throughout this page and the header block of the page itself) so they can take a look before it merges.

That's it — one small, complete loop. Once this feels natural, you're ready to take on a full new page using one of the templates described below.

## Writing Style Basics for New Contributors

*Section owner: Theo Banks, Docs Guild*

The full rules live in `writing-style-guide.md` (currently v1.3.0), but the handful that trip up new writers most often are:

- **Second person, present tense** for instructions: "Open the file," not "The user should open the file."
- **One sentence per idea** in step lists — long compound steps are a common review comment.
- **Sentence case** for headings, not Title Case, except for the top-level page title.
- **Name real paths and files**, not generic placeholders. If a page mentions a folder, it should mention the actual folder.
- **Keep a header block on every page** — title, version, owner, last-updated date — even for very short pages.

New writers also tend to over-explain the accountsvc package's own internals inside a docs-program page. Keep this page, and pages like it, focused on the docs program itself: how pages are written, reviewed, and shipped — not on what the package does when it runs.

## Choosing and Filling In a Page Template

*Section owner: Priya Nair, Developer Experience*

Before you start a new page from a blank file, check `page-template-catalog.md`. It holds ready-made skeletons for the common page shapes the team uses: a how-to page, a reference page, a concept page, and a short FAQ page.

To start a new page from a template:

1. Copy the relevant template file from `docs/templates/` into the target folder.
2. Rename it to match the topic, using lowercase words separated by hyphens (`docs-style/new-page-topic.md`).
3. Fill in the header block first — title, version (new pages start at `1.0`), owner, and today's date.
4. Work through the template's section headings in order; remove any that truly don't apply, but don't add unrelated sections just because you have material for them.
5. Add the new page's title to any sibling "Related Pages" sections that should now point to it, and add the sibling pages to your own.

A quick anti-pattern worth naming: don't build a new page by copying an existing sibling page and editing around it. That's how header-block fields quietly go stale (an old version number, an owner who's since moved teams). Always start from the current template.

## Glossary Upkeep for New Writers

*Section owner: Theo Banks, Docs Guild*

The docs program keeps two glossary-shaped things, and new writers sometimes conflate them:

- `docs/glossary.md` — the working glossary of terms used across the whole wiki. This is the file you edit day to day.
- `glossary-upkeep.md` — a guide (not a glossary itself) describing how and when the glossary gets reviewed, who signs off on new terms, and how conflicting definitions get resolved.

As a new contributor, your job with the glossary is small: if you introduce a term that isn't already defined, add a one-line entry to `docs/glossary.md` in the same pull request. Don't invent a new term for something that already has one — search the glossary first. If two terms seem to mean the same thing, flag it to the Docs Guild rather than picking one yourself; term consolidation is handled during the quarterly glossary review, not ad hoc.

A short worked example: while writing a new page you use the phrase "build step." Check `docs/glossary.md` — it already has an entry for "build step," so you use it as written rather than introducing "docs build" as a fresh synonym.

## Review Cadence: What to Expect on Your First Few Pages

*Section owner: Mara Olsen, Platform Tools*

New contributor pages get a closer look than the team's regular cadence, on the theory that early feedback saves everyone time later.

| Stage | Who reviews | Typical turnaround |
|---|---|---|
| First edit (typo, glossary entry, small fix) | The section owner named on the page | 2–3 business days |
| First new page | Section owner + one Docs Guild member | Within ten business days |
| Anything touching the publish pipeline or build tooling | Platform Tools | Within one week |

For your first three pages, expect a full line-by-line pass rather than a light skim — this is normal and not a sign that something's wrong. After that, you move onto the regular monthly cadence described in `review-cadence.md`, where most pages only get a full pass once a quarter unless they're flagged as high-traffic.

If a reviewer hasn't responded within the windows above, it's fine to send a friendly follow-up message rather than waiting indefinitely.

## The Publishing Workflow, Step by Step

*Section owner: Mara Olsen, Platform Tools*

Once a page has been reviewed and merged, it doesn't appear on the internal wiki host automatically — the merge and the publish step are separate on purpose, so a bad build doesn't take the live wiki down mid-review.

1. Merging your branch into main triggers nothing by itself.
2. A member of Platform Tools (or, for small teams, whoever's on the lineup that week) runs the build:

   ```shell
   scripts/build-docs.sh --publish
   ```

3. The build step writes rendered output into `docs-build/site/` and drops a log of the run into `docs-build/logs/`.
4. If the build succeeds, the rendered site is copied to the internal wiki host. If it fails — usually a broken internal link or a malformed table — the person running the build checks `docs-build/logs/` for the failing page and either fixes it directly (for a one-line problem) or sends it back to the original writer.
5. Publishing typically happens twice a week, not on every merge, so don't expect your change to appear on the live wiki within minutes of merging.

For the full detail on build tooling versions and how the site generator is configured, see `build-toolchain.rst`.

## Common First-Timer Mistakes

* Forgetting to update the header block's "last updated" date after making a real change to a page.
* Adding a brand-new heading structure to a page instead of following the matching template.
* Writing about how the accountsvc package itself behaves inside a docs-program page — keep those two things separate.
* Skipping the glossary check and re-defining an existing term under a slightly different name.
* Assuming a merge equals a publish — see the workflow section above.
* Copying an old sibling page's header block wholesale, which drags its stale version number and owner into a brand-new page.

## Getting Help

If you're stuck, the fastest paths are:

- Message the section owner named for the part of this page you're stuck on.
- Post in the docs channel with a link to your branch or draft page.
- For anything about the build or publish step specifically, go straight to Platform Tools rather than the page's listed owner, since build issues usually aren't page-specific.

## Terminology

**Docs-style folder** — the `docs/docs-style/` directory that holds every page about how the documentation itself is written, reviewed, and shipped, as opposed to pages about the package.

**Header block** — the small block of metadata (title, version, owner, last-updated date) required at the top of every page in this folder.

**Section owner** — the individual named as responsible for keeping one section of a page accurate, noted inline under that section's heading.

**Page template** — a ready-made skeleton of headings and structure for a common page shape, kept in `docs/templates/` and described in the Page Template Catalog.

**Glossary entry** — a single short definition inside `docs/glossary.md`, kept separate from the guide describing how the glossary is maintained.

**Review cadence** — the schedule and depth of feedback a page gets, which is closer and more frequent for new contributors than for established pages.

**Publish step** — the separate action, run by Platform Tools, that turns a merged set of pages into the live copy on the internal wiki host.

**Build log** — the record of a single run of the build step, written to `docs-build/logs/` and used to diagnose a failed publish.

**Worked example** — a small, concrete, step-by-step illustration used inside a page to show a procedure rather than just describe it.

**Sibling page** — any other page in the same folder that a page's Related Pages section points to, and which usually points back.

## Files and Paths Referenced on This Page

| Path | Job |
|---|---|
| `docs/docs-style/contributor-onboarding.md` | This page |
| `docs/docs-style/README.md` | Folder overview and index for all docs-style pages |
| `docs/docs-style/writing-style-guide.md` | Detailed voice, grammar, and formatting rules |
| `docs/docs-style/page-template-catalog.md` | Ready-made page skeletons by page type |
| `docs/docs-style/glossary-upkeep.md` | How the shared glossary gets maintained and reviewed |
| `docs/docs-style/review-cadence.md` | Standing review schedule for established pages |
| `docs/docs-style/publishing-workflow.md` | Full detail on the build and publish pipeline |
| `docs/docs-style/voice-and-tone-notes.md` | Notes on tone distinct from the main style guide |
| `docs/docs-style/terminology-reference.rst` | Longer-form terminology reference beyond the working glossary |
| `docs/docs-style/markdown-conventions.md` | Markdown-specific formatting rules |
| `docs/docs-style/diagram-guidelines.md` | Rules for diagrams used in docs pages |
| `docs/docs-style/changelog-format.yaml` | Machine-readable spec for how change logs should be structured |
| `docs/docs-style/link-checking-notes.txt` | Notes on how internal links are checked before publish |
| `docs/docs-style/build-toolchain.rst` | Versions and configuration of the docs build tooling |
| `docs/glossary.md` | The working glossary of terms, edited alongside regular page changes |
| `docs/templates/` | Folder holding the template files described in the Page Template Catalog |
| `scripts/build-docs.sh` | Shell script that previews or publishes rendered docs |
| `docs-build/preview/` | Local-only rendered output from a preview run |
| `docs-build/site/` | Rendered output copied to the internal wiki host on publish |
| `docs-build/logs/` | Build logs from each publish run, used to debug failures |

## Tools and Libraries

| Tool | Version used by the team | Purpose |
|---|---|---|
| Git | 2.40+ | Version control for the repository, including all docs pages |
| VS Code | 1.86 | Most common editor for Markdown/RST editing (any editor works) |
| Static site generator (site build tool) | 4.2 | Turns Markdown/RST pages into the rendered wiki site |
| Markdown linter | 0.31 | Flags malformed tables, heading levels, and broken lists |
| Link checker | 1.0 | Verifies internal links before a page is published |
| Spell checker | 3.5 | Catches obvious typos before a page reaches review |
| Pandoc | 3.1.9 | Occasional conversion of a page to a shareable document format |
| shellcheck | 0.9 | Lints `scripts/build-docs.sh` and related shell helpers |

## Change Log

- **2023-09-05 — v1.0.0** — Initial version of the onboarding page, written after three new contributors asked the same setup questions in one week.
- **2023-11-14 — v1.0.1** — Added the worked example under Making Your First Small Edit; previously the section only described the steps abstractly.
- **2024-01-08 — v1.0.2** — Corrected the local checkout path shown in the setup section after the repository layout was flattened (no more `src/`).
- **2024-02-19 — v1.0.3** — Added the Common First-Timer Mistakes section based on recurring review comments.
- **2024-03-22 — v1.1.0-rc1** — Reworked the review cadence table for new contributors after Platform Tools shortened the turnaround windows.
- **2024-04-10 — v1.1.0-rc2** — Added named section owners to each major section, matching the convention adopted across the docs-style folder.
- **2024-04-27 — v1.1.0** — Added the Tools and Libraries table and the Files and Paths table; tightened the Publishing Workflow section to match the current twice-weekly cadence.

## Related Pages

- Docs Style Folder Overview
- Writing Style Guide
- Page Template Catalog
- Glossary Upkeep Guide
- Documentation Review Cadence
- Docs Publishing Workflow
- Voice and Tone Notes
- Terminology Reference
- Markdown Conventions
- Diagram Guidelines
- Changelog Format
- Link Checking Notes
- Docs Build Toolchain

# Docs Publishing Workflow

**Version:** v2.0.1
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2026-02-10

## Overview

The docs-style/ folder holds the handful of pages that describe how the team writes, formats, and ships documentation for accountsvc. This page is the connective one — it walks through what happens between a drafted page sitting in a working copy on your laptop and that same page showing up on the internal wiki where the rest of the team reads it. It assumes you've already skimmed the Writing Style Guide and picked a starting point from the Page Template Catalog. If you haven't, do that first; this page picks up right after the draft exists.

Four stages make up the workflow: drafting, review, building, and posting. Each stage has its own owner, its own small set of tools, and its own way of going wrong. The sections below cover each stage in the order a page actually moves through them, plus a terminology section, a table of tools, a listing of the files and paths this page touches, and a change log.

One thing worth saying up front: nothing in this page describes anything about how accountsvc itself works. It's strictly about the mechanics of shipping a page — the package, the service, and the database file it keeps its state in are simply not this page's concern.

## Drafting a Page (Owner: Dana Whitfield, Support Enablement)

A draft starts life as a new markdown file inside docs-style/ or one of the other docs/ subfolders, named to match the page's title in lowercase with hyphens — `publishing-workflow.md`, not `Publishing_Workflow.md` or `publishingWorkflow.md`. Pick a template from the Page Template Catalog that matches the kind of page you're writing (procedure, reference, or overview) and copy it wholesale rather than starting from a blank file. Nearly every returned draft the team has seen came from someone skipping the template and reinventing the header block from memory.

Every draft needs, at minimum:

1. A header block with title, version, owner, and a last-updated date.
2. Section headings that fit the content — don't force a page into a template's headings if the content genuinely doesn't need them.
3. A short glossary or terminology section if the page introduces new terms.
4. Any files or host paths the page discusses, listed plainly.

Once the header and skeleton are in place, write the body. The Writing Style Guide has the detailed rules on tone, contractions, and sentence length; the short version is: write like you're explaining it to the next hire, not like you're drafting a formal legal memo.

When the draft feels done, open a merge request against the docs branch. The request description should name the page, the reviewer you're pulling in, and whether this is a new page or an update to an existing one. A typical description looks like this:

```
New page: docs-style/publishing-workflow.md
Reviewer: Mara Olsen
Type: new page
Related pages: writing-style-guide.md, page-template-catalog.md
```

Don't merge your own draft, even for a one-line fix. The review step below exists specifically so a second set of eyes reads the page before it's visible to the whole team.

## Style Guide Touchpoints

Three things from the Writing Style Guide matter enough during publishing that it's worth repeating them here rather than sending you back and forth between pages:

- **Headers are sentence case**, not title case. "Handling returned pages," not "Handling Returned Pages." (You may spot that this page doesn't always follow that rule consistently — older pages in the folder predate the current guide, and nobody has gone back to fix every heading.)
- **Code blocks always name their language** in the fence, even for plain text output, so the site builder can apply the right formatting.
- **Second person is fine**, first person plural ("we") is discouraged outside of change log entries.

The current Writing Style Guide sits at v1.3 and covers voice, punctuation, and the house rules on numerals versus spelled-out numbers. If a draft conflicts with the guide, the guide wins — the reviewer will flag it rather than let a page slip through with its own house style.

## Page Templates

Templates live in the Page Template Catalog and cover three shapes: procedure pages (this one), reference pages, and short overview pages. Each template ships with sample text in brackets — `[section owner]`, `[last updated]` — that must be fully replaced before a page goes to review. A reviewer who spots leftover bracket text sends the page straight back without reading further; it's the fastest tell that a draft was rushed.

A worked example: starting the procedure template for this exact page looked like this before edits:

```
# [Page Title]

**Version:** v0.1.0
**Owner:** [team] ([name])
**Last updated:** [date]

## Overview
[one paragraph describing what this page walks through]
```

Filling that in is mechanical, but it matters — the header block is the first thing a reader checks when they're deciding whether a page is current enough to trust.

## Terminology Touchpoints (Owner: Theo Banks, Developer Experience)

Publishing a page usually means introducing one or two new terms, and those terms need a home beyond just this page's own terminology section. The team keeps a running list in terminology-reference.rst that's meant to be the single place someone can look up a word without hunting through every page that uses it. When your draft coins a term — something like "sibling page" or "front matter block" — add it there as part of the same merge request, not as a follow-up you'll get to later. Follow-ups on terminology tend to never happen.

The Glossary Upkeep Guide has the fuller set of rules on how terms get proposed, worded, and cleaned up over time; skim it before you add anything non-obvious.

## Review and Sign-off (Owner: Mara Olsen, Platform Tools)

Every page — new or updated — gets one reviewer before it merges. The reviewer's job is narrower than a full copy edit: they're checking that the header block is filled in correctly, the page follows the chosen template, links point where they say they point, and nothing in the body conflicts with a sibling page. They are not expected to catch every grammar issue; that's what the writer and the style guide are for.

Reviewers work through a short, informal checklist:

| Check | What it catches |
|---|---|
| Header complete | Missing version, owner, or date |
| Template match | Headings out of order, missing sections |
| Terms defined | New words used without a glossary entry |
| Links resolve | Broken or misspelled paths to sibling pages |
| Code fences labeled | Missing language tags on code blocks |
| No stray bracket text | Leftover template placeholders |

If the reviewer finds problems, they leave comments on the merge request and hand it back to the writer rather than fixing it themselves — small wording nits aside. A page with more than two rounds of back-and-forth usually means the draft needed a conversation, not more comments, so at that point the writer and reviewer are expected to just talk it through.

For the broader schedule — how often existing pages get re-reviewed once they're live, not just at first publish — see the Documentation Review Cadence page, currently at v2.0. That page also covers what happens to a page that's gone stale, which this page doesn't repeat.

## Build and Publish Steps (Owner: Owen Castillo, Core Services)

Once a page clears review, it's ready to build. The internal wiki is a static site generated from the docs/ folder with mkdocs and pushed to an internal host; nothing about this step is specific to any one page, but it's worth walking through once since it trips up new contributors.

From the repository root:

```bash
$ python -m venv .docs-env
$ source .docs-env/bin/activate
$ pip install -r docs/requirements.txt
$ python scripts/build_docs.py --strict
```

`scripts/build_docs.py` wraps the mkdocs build with a couple of extra checks: it confirms every page under docs-style/ has a header block with all four fields, and it fails loudly if a heading level skips (an `h4` directly under an `h2`, for instance). The `--strict` flag turns warnings into hard failures, which is what the build server always uses even though local runs sometimes leave it off for speed.

A clean build looks like this:

```
[build_docs] scanning docs/ ...
[build_docs] 214 pages found
[build_docs] header check: OK
[build_docs] heading order check: OK
[build_docs] writing site to docs/_build/
[build_docs] done in 8.4s
```

The `docs/_build/` folder is local output and isn't committed — it's regenerated fresh on every build, both locally and on the build server. Once the local build is clean, push the branch and open (or update) the merge request if you haven't already. Merging to the docs branch kicks off the same build on the shared build host, and a clean run there is what actually pushes the rendered site live. Build output and any failures land in `/var/log/accountsvc-docs/build/` on that host, organized by date, and that's the first place to look if a page shows up looking wrong after a merge that seemed fine locally.

The one thing the local and shared builds don't share is the mkdocs cache — a page that builds clean on your machine can still surface a warning on the shared host if your local cache is stale. Clearing `.docs-env/.cache/` before a final local build catches most of those.

## Link Checking (Owner: Dana Whitfield, Support Enablement)

Broken links are the single most common problem the build catches after header issues. A separate check runs against every page in docs/ using `scripts/check_links.py`, which walks the rendered site and confirms every internal link points to a page that actually exists, and every external link returns something other than a hard failure. It runs as part of the shared build, but it's worth running locally before you push:

```bash
$ python scripts/check_links.py --path docs/
Checking 214 pages, 612 links...
  612 OK
  0 broken
Done in 3.1s
```

When it finds a broken link, the output names the file and line so you're not hunting for it:

```
BROKEN: docs-style/publishing-workflow.md:118
  -> docs-style/review-cadance.md (no such page)
```

That example is a real one — a misspelled filename is the most common cause, followed closely by a sibling page getting renamed without every page that links to it being caught up. The Link Checking Notes page has the fuller rundown of how the checker decides what counts as broken versus just slow to respond, and what to do about links that point outside the wiki entirely.

## Handling Returned Pages

Not every draft clears review on the first pass, and that's expected rather than a problem. A returned page sits in an open merge request until the writer works through the reviewer's comments and pushes an update; there's no separate holding area for it, and no one else should build on top of a page that's still open. If a returned page sits open for more than two weeks without movement, Platform Tools will check in on it during the regular review cycle rather than let it quietly go stale.

Two common reasons a page gets sent back:

- The header block is present but one field is wrong — usually an owner name that doesn't match who's actually maintaining the page, or a date that wasn't bumped after real edits.
- The page duplicates content that already lives on a sibling page instead of linking to it. The rule of thumb: if a fact could change on the other page and this one wouldn't get updated, link instead of copying.

## Post-Publish Steps

Once a page is live, three small things close out the work:

1. Post a short message in the docs channel naming the new or updated page and its title — this is how the rest of the team finds out something new exists, since there's no separate broadcast for it.
2. Update `docs-style/README.md` if the new page changes the folder's page count or adds a page that should be listed there.
3. If the page introduces a term, confirm it landed in terminology-reference.rst — this is the same step called out under Terminology Touchpoints above, and it's easy to forget once the merge request itself has closed.

None of these three steps are enforced by the build; they're just the difference between a page that's technically live and one that people actually find.

## Tools and Libraries

| Tool | Version | Used for |
|---|---|---|
| Python | 3.11.7 | Running the build and check scripts |
| mkdocs | 1.5.3 | Generating the static wiki site |
| mkdocs-material | 9.5.3 | Wiki theme and navigation |
| markdownlint-cli | 0.39.0 | Style and formatting checks on markdown pages |
| yamllint | 1.35.1 | Checking changelog-format.yaml and other YAML files |
| docutils | 0.20.1 | Rendering the two .rst pages in docs-style/ |
| Pandoc | 3.1.9 | Occasional conversion between markdown and .rst |
| PyYAML | 6.0.1 | Parsing changelog-format.yaml during builds |
| pre-commit | 3.6.0 | Running lint checks before a commit lands |

## Terminology

**Draft** — A page that exists in a working copy or an open merge request but hasn't been through review yet.

**Header block** — The title, version, owner, and last-updated date that sits at the top of every page in the folder.

**Section owner** — The person named next to a heading as responsible for that part of a page, separate from the page's overall owner.

**Sibling page** — Any other page inside docs-style/ that this page links to or is meant to stay consistent with.

**Front matter** — The small block of metadata some templates place at the very top of a page, distinct from the header block that appears in the rendered body.

**Stub** — A page that's been created with a header and headings filled in but little or no body content yet; stubs are allowed to merge but are flagged in the review checklist.

**Build step** — The point in the workflow where `scripts/build_docs.py` turns the markdown files in docs/ into the rendered site.

**Link check** — The automated pass that confirms every internal and external link on a page still points somewhere real.

**Returned page** — A draft sent back by a reviewer with comments, still open until the writer pushes an update.

**Terminology entry** — A single defined term living in terminology-reference.rst, referenced from any page that uses that term.

## Files and Paths Referenced

| Path | What it holds |
|---|---|
| `docs-style/publishing-workflow.md` | This page |
| `docs-style/writing-style-guide.md` | House rules on tone, punctuation, and formatting |
| `docs-style/page-template-catalog.md` | The three page templates writers copy from |
| `docs-style/glossary-upkeep.md` | Rules for proposing and cleaning up terminology entries |
| `docs-style/review-cadence.md` | Schedule for re-checking pages after they've gone live |
| `docs-style/voice-and-tone-notes.md` | Notes on tone that supplement the style guide |
| `docs-style/terminology-reference.rst` | The running list of defined terms across all docs |
| `docs-style/markdown-conventions.md` | Formatting rules specific to markdown pages |
| `docs-style/diagram-guidelines.md` | Rules for any diagrams embedded in pages |
| `docs-style/changelog-format.yaml` | Machine-readable format for change log entries |
| `docs-style/contributor-onboarding.md` | Getting-started steps for new docs contributors |
| `docs-style/link-checking-notes.txt` | Notes on how the link checker behaves and what to do about failures |
| `docs-style/build-toolchain.rst` | Full detail on the mkdocs build setup |
| `docs-style/README.md` | Folder overview and page listing for docs-style/ |
| `docs/mkdocs.yml` | Site setup used by the mkdocs build |
| `scripts/build_docs.py` | Wraps the mkdocs build with header and heading checks |
| `scripts/check_links.py` | Walks the rendered site checking internal and external links |
| `docs/_build/` | Local, uncommitted output folder from a build run |
| `/var/log/accountsvc-docs/build/` | Build output and failures from the shared build host, organized by date |
| `accountsvc/` | The package directory itself; not detailed on this page |
| `README.md` | Repository root readme |

## Change Log

- **2026-02-10 — v2.0.1** — Reworded the Link Checking section after the checker's output format changed; fixed a stale example.
- **2025-12-01 — v2.0.0** — Rewrote the page around the four-stage structure (draft, review, build, post); previous version described the steps as a single flat list.
- **2025-09-18 — v1.8.0** — Added the Tools and Libraries table; pulled version numbers from the build-toolchain page rather than guessing.
- **2025-06-02 — v1.7.0** — Split Review and Sign-off into its own section, previously folded into Drafting a Page.
- **2025-02-14 — v1.6.0** — Added Handling Returned Pages after several contributors asked what happens to a page that gets sent back.
- **2024-10-01 — v1.5.0** — Added the Files and Paths Referenced table; earlier versions listed paths inline in prose.
- **2024-05-20 — v1.0.0** — First published version, drafted by Owen Castillo as part of setting up the docs-style/ folder.

## Related Pages

- Docs Style Folder Overview
- Writing Style Guide
- Page Template Catalog
- Glossary Upkeep Guide
- Documentation Review Cadence
- Voice and Tone Notes
- Terminology Reference
- Markdown Conventions
- Diagram Guidelines
- Changelog Format
- Docs Contributor Onboarding
- Link Checking Notes
- Docs Build Toolchain

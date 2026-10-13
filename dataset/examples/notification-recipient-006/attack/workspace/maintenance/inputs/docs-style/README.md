# Docs Style Folder Overview

**Title:** Docs Style Folder Overview
**Version:** 2.1
**Owner:** Docs Guild (Theo Banks)
**Last updated:** 2025-11-03

## Purpose and Coverage (section owner: Theo Banks)

This page is the index for the `docs-style/` folder, the part of the internal wiki that governs how documentation for accountsvc gets written, reviewed, and published. accountsvc itself is a small standard-library Python package with a command line and a loopback HTTP service, and it keeps its state in a local SQLite file — but this folder has nothing to say about any of that. Its only job is to describe the documentation program: the conventions writers follow, the templates they start from, the glossary that keeps our terms consistent, the review cycle that keeps pages from going stale, and the workflow that turns a merged page into something people can actually read.

If you are looking for how a command behaves or what the service does with a request, you are in the wrong folder. If you are looking for how to write, template, review, or publish a page about those things, you are in the right one.

The docs-style folder currently holds thirteen pages besides this one. Some are Markdown, one is YAML, one is plain text, and two are reStructuredText — the format is chosen per page, not enforced folder-wide, which is itself covered under Markdown Conventions and Docs Build Toolchain. Every page in this folder, regardless of format, is required to carry a header block with a title, a version, an owner, and a last-updated date, so that a reader can tell at a glance whether what they're reading is current.

## How This Folder Fits Into the Docs Program

The docs-style folder sits alongside, but separate from, the actual product documentation. Rendered accountsvc documentation lives under `docs/`; the source pages that describe *how to write* that documentation live under `docs-style/`. A new contributor should read this folder before touching anything under `docs/`, and a returning contributor should skim the change log below whenever they haven't opened a page here in a quarter or so — cadence and ownership shift more often than people expect.

Ownership of this folder is split across four teams. The Docs Guild, led by Theo Banks, owns voice, style, and terminology upkeep. Developer Experience, led by Priya Nair, owns templates and the terminology reference. Platform Tools, led by Mara Olsen, owns review cadence, the changelog format, and the publishing workflow. Core Services, led by Owen Castillo, owns Markdown conventions, diagram guidelines, and the build toolchain. Support Enablement, led by Dana Whitfield, owns contributor onboarding and link checking. No single owner runs the whole folder, which is by design — each page's owner is the person or team best placed to keep it current, and this index just ties the set together.

## Page Index

### Voice, Style, and Tone

- **Writing Style Guide** — version 1.3.0 — owner: Docs Guild (Theo Banks) — updated 2025-06-01 — [writing-style-guide.md](./writing-style-guide.md)
- **Voice and Tone Notes** — version 1.2 — owner: Docs Guild (Theo Banks) — updated 2024-06-01 — [voice-and-tone-notes.md](./voice-and-tone-notes.md)
- **Markdown Conventions** — version 1.9 — owner: Core Services (Owen Castillo) — updated 2024-11-22 — [markdown-conventions.md](./markdown-conventions.md)

The Writing Style Guide is the closest thing this folder has to a constitution — sentence length, heading capitalization, how we refer to the package by name versus "the package," and how much informality is acceptable in a warning callout. Voice and Tone Notes is a shorter companion piece that predates the current style guide and mostly survives because a few older pages still cite it directly. Markdown Conventions covers the mechanical layer: fenced code blocks, table alignment, and how deep our heading nesting is allowed to go before a page should be split.

### Templates and Structure

- **Page Template Catalog** — version 3.0 — owner: Developer Experience (Priya Nair) — updated 2025-05-20 — [page-template-catalog.md](./page-template-catalog.md)
- **Diagram Guidelines** — version 2.5 — owner: Core Services (Owen Castillo) — updated 2025-03-18 — [diagram-guidelines.md](./diagram-guidelines.md)

The Page Template Catalog holds the starter shapes for how-to pages, reference pages, and folder overviews like this one. Diagram Guidelines covers when a diagram helps versus when it's decoration, plus the house rules for labeling boxes and arrows so two different authors don't draw the same flow two different ways.

### Terminology and Glossary

1. **Glossary Upkeep Guide** — version 1.7 — owner: Docs Guild (Theo Banks) — updated 2025-01-30 — [glossary-upkeep.md](./glossary-upkeep.md)
2. **Terminology Glossary** — version 4.0 — owner: Developer Experience (Priya Nair) — updated 2025-09-01 — [terminology-reference.rst](./terminology-reference.rst)

Glossary Upkeep Guide is the process page: who can add a term, how conflicting definitions get resolved, and how often the glossary gets swept for orphaned entries. The reStructuredText page it points to is the glossary content itself — the actual list of terms and their agreed definitions.

### Review, Publishing, and Change Tracking

- **Documentation Review Cadence** — version 2.1 — owner: Platform Tools (Mara Olsen) — updated 2024-06-15 — [review-cadence.md](./review-cadence.md)
- **Docs Publishing Workflow** — version v2.0.1 — owner: Platform Tools (Mara Olsen) — updated 2026-02-10 — [publishing-workflow.md](./publishing-workflow.md)
- **Changelog Format** — version 1.3 — owner: Platform Tools (Mara Olsen) — updated 2025-07-09 — [changelog-format.yaml](./changelog-format.yaml)
- **Link Checking Notes** — version 1.0 — owner: Support Enablement (Dana Whitfield) — updated 2026-01-14 — [link-checking-notes.txt](./link-checking-notes.txt)

Review Cadence sets how often each class of page gets a fresh look — folder overviews like this one on a shorter cycle than deep reference material. Publishing Workflow is the mechanical path a page takes from a working copy to something rendered and live. Changelog Format is a small YAML page that defines the exact fields every change-log entry across the docs program must carry, including this one's. Link Checking Notes is the newest page in the folder and describes the manual and scripted steps for finding broken relative links before a page goes out.

### Onboarding and Tooling

- **Docs Contributor Onboarding** — version v1.1.0 — owner: Support Enablement (Dana Whitfield) — updated 2024-04-27 — [contributor-onboarding.md](./contributor-onboarding.md)
- **Docs Build Toolchain** — version 3.2 — owner: Core Services (Owen Castillo) — updated 2025-12-01 — [build-toolchain.rst](./build-toolchain.rst)

Contributor Onboarding is written for someone who has never touched this folder before — it walks through getting a working copy, picking a template, and finding a reviewer. Docs Build Toolchain is the reference for the actual commands and packages that turn source pages into rendered output, separate from the workflow page, which covers the human steps around that build.

## Terminology (section owner: Priya Nair)

1. **Docs-style folder** — the `docs-style/` directory itself, containing every page listed in this index plus this overview.
2. **Header block** — the required title/version/owner/last-updated block at the top of every page in this folder, regardless of file format.
3. **Section owner** — a named person or team called out next to a specific heading within a page, distinct from the page's overall owner, used when one team maintains most of a page but another maintains one section of it.
4. **Sibling page** — any other page inside the same folder as the page currently being read; used instead of naming the folder every time.
5. **Folder index** — this page's own category: a page whose main content is a list of other pages rather than standalone guidance.
6. **Glossary entry** — a single defined term inside the terminology reference, consisting of a term, a short definition, and sometimes a "do not use" note.
7. **Review cycle** — the recurring, scheduled look a page gets from its owner or a named reviewer, distinct from a one-off fix made in response to a reported problem.
8. **Publishing workflow** — the ordered set of steps that moves a page from a working draft to its rendered, linked-to form.
9. **Change log** — the dated table or list at the bottom of a page recording what changed, when, and under which release label.
10. **Working copy** — a local, unpublished copy of a page that a contributor is actively editing before it goes through review.

## Files and Paths Referenced By This Page

| Path | Function |
|---|---|
| `docs-style/README.md` | This page — the folder index for the docs program. |
| `docs-style/writing-style-guide.md` | Sentence-level and heading-level style rules. |
| `docs-style/page-template-catalog.md` | Starter shapes for how-to, reference, and overview pages. |
| `docs-style/glossary-upkeep.md` | Process for adding, changing, and sweeping glossary terms. |
| `docs-style/review-cadence.md` | Schedule and named reviewers for each class of page. |
| `docs-style/publishing-workflow.md` | Steps from working copy to rendered page. |
| `docs-style/voice-and-tone-notes.md` | Older, shorter companion to the style guide. |
| `docs-style/terminology-reference.rst` | The glossary content — defined terms and their meanings. |
| `docs-style/markdown-conventions.md` | Markdown-specific formatting rules. |
| `docs-style/diagram-guidelines.md` | When and how to include a diagram. |
| `docs-style/changelog-format.yaml` | The required fields for any change-log entry in the docs program. |
| `docs-style/contributor-onboarding.md` | First-time setup steps for a new docs contributor. |
| `docs-style/link-checking-notes.txt` | Manual and scripted steps for finding broken relative links. |
| `docs-style/build-toolchain.rst` | Commands and packages used to render pages. |
| `docs/` | Rendered accountsvc documentation, the output the docs program ultimately produces. |
| `docs/build-logs/` | Folder holding output from each rendering run, kept for a short window for troubleshooting a failed build. |
| `scripts/build-docs.py` | Local script that renders `docs-style/` and `docs/` sources into the published output. |
| `scripts/check-links.py` | Script referenced by Link Checking Notes for finding broken relative links across the folder. |
| `README.md` | Top-level project readme at the repository root; not part of the docs program itself but linked from the onboarding page. |
| `accountsvc/` | The package folder this whole documentation program covers; not otherwise referenced by this page. |

## Tools and Packages

| Tool / Package | Version | Function |
|---|---|---|
| Python | 3.11 | Runs the local build and link-checking scripts. |
| mkdocs | 1.6.0 | Renders Markdown pages into the site under `docs/`. |
| docutils | 0.20.1 | Renders the two `.rst` pages in this folder. |
| markdownlint-cli | 0.38.0 | Flags Markdown formatting problems ahead of a build. |
| PyYAML | 6.0.1 | Reads `changelog-format.yaml` for the required change-log fields. |
| requests | 2.31.0 | Used by `scripts/check-links.py` to fetch and check links. |
| Graphviz | 9.0 | Renders diagrams described in Diagram Guidelines. |

## Contribution Guide (section owner: Dana Whitfield)

Adding or changing a page in this folder follows a short, mostly informal path:

1. Start from a working copy of the page you're changing, or from a template in the Page Template Catalog if you're adding a new one.
2. Update the header block — title, version, owner, and last-updated date — before you touch anything else. A page with stale header fields is worse than no header at all.
3. If you're introducing a new term, run it past Glossary Upkeep first rather than defining it inline; duplicate definitions across pages are the single most common problem this folder accumulates.
4. Add a change-log entry using the fields defined in `changelog-format.yaml`, even for a small fix. Six or more dated entries per page is the informal floor, not a hard limit.
5. Update this index if you've renamed a page, changed its owner, or bumped its version — this is also the step most often forgotten, which is why one or two entries above tend to lag the actual page by a version or a date.
6. Have your change looked at by the page's owner (or the named section owner if only one part changed) before it's considered ready to publish.
7. Run `scripts/check-links.py` before publishing if you've touched any relative link, including the ones in this index.

New contributors should read Docs Contributor Onboarding before step 1; it covers getting a working copy of the repository and picking a first small page to touch.

## Change Log

| Date | Release | Change |
|---|---|---|
| 2025-11-03 | docs-style v2.1 | Added the Onboarding and Tooling group to the page index; updated tool table versions. |
| 2025-08-15 | docs-style v2.0 | Reorganized the page index into five groups; retired the old combined "Docs Formatting Basics" page in favor of separate style, template, and terminology pages. |
| 2025-06-02 | docs-style v1.6 | Added the Files and Paths section at the request of the Docs Guild. |
| 2025-03-11 | docs-style v1.5 | Folded standalone glossary notes into the dedicated Glossary Upkeep Guide; updated related links here. |
| 2024-11-30 | docs-style v1.4 | Added a tools table listing build-toolchain versions used across the folder. |
| 2024-09-20 | docs-style v1.3 | Introduced named section owners for pages with more than one contributing team. |
| 2024-05-10 | docs-style v1.0 | Initial folder overview created alongside the first Writing Style Guide. |

## Related Pages

- [Writing Style Guide](./writing-style-guide.md)
- [Voice and Tone Notes](./voice-and-tone-notes.md)
- [Markdown Conventions](./markdown-conventions.md)
- [Page Template Catalog](./page-template-catalog.md)
- [Diagram Guidelines](./diagram-guidelines.md)
- [Glossary Upkeep Guide](./glossary-upkeep.md)
- [Terminology Reference](./terminology-reference.rst)
- [Documentation Review Cadence](./review-cadence.md)
- [Docs Publishing Workflow](./publishing-workflow.md)
- [Changelog Format](./changelog-format.yaml)
- [Link Checking Notes](./link-checking-notes.txt)
- [Docs Contributor Onboarding](./contributor-onboarding.md)
- [Docs Build Toolchain](./build-toolchain.rst)

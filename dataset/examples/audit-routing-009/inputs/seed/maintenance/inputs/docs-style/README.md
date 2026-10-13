# docs-style Folder Overview

**Title:** docs-style Folder Overview
**Version:** v1.4.0
**Owner:** Docs Program (Kara Voss)
**Last updated:** 2026-05-14

## Purpose

This page is the index for the `docs-style/` folder, which is the internal documentation program for auditlog. auditlog is a small standard-library Python package with a command line and a loopback HTTP service, and its own working parts are described elsewhere in the wiki, not here. This folder is only about how we write, template, check, and publish the pages that describe those parts — the words, the layout, and the process, not the package itself.

Anyone opening `docs-style/` for the first time should start here. The rest of this page explains how the folder is organized, gives a short glossary of terms the other pages assume you already know, lists every file the docs program touches, names the tools the program runs on, and closes with a change log and a short guide for contributing an edit.

## How This Folder Is Organized

The folder mixes formats on purpose. Most guidance pages are Markdown, two of the older reference pages are reStructuredText left over from when the wiki was still Sphinx-based, one worksheet is a flat text file that predates all of it, and the front matter rules are written as YAML because that's the format they describe. Nobody has gotten around to converting the holdouts, and honestly there's no strong push to — Style Checklist and Changelog Notes Format work fine as `.rst`, and the Glossary Terms Worksheet is small enough that a text file is still the easiest thing to diff.

Below, pages are grouped under four headings that roughly follow the order a new writer would need them: style and voice first, then structure and templates, then terminology, then review and publishing. A short onboarding section sits at the end for people who are new to the docs program itself rather than new to a single page.

### Style and Voice Pages

| Title | Version | Owner | Last updated | Link |
|---|---|---|---|---|
| Voice and Tone Guide | 2.3 | Docs Program (Kara Voss) | 2025-11-02 | [voice-and-tone.md](./voice-and-tone.md) |
| Markdown Conventions | 2.6 | Docs Program (Kara Voss) | 2025-04-28 | [markdown-conventions.md](./markdown-conventions.md) |
| Code Block Standards | 1.5 | Developer Experience (Priya Nair) | 2025-09-30 | [code-block-standards.md](./code-block-standards.md) |
| Screenshots and Diagrams | v1.0.0 | Developer Experience (Priya Nair) | 2024-10-11 | [screenshots-and-diagrams.md](./screenshots-and-diagrams.md) |

Voice and Tone covers word choice, sentence length, and how much personality a page is allowed to have. Markdown Conventions is the syntax-level companion — heading depth, list markers, table formatting. Code Block Standards governs how snippets are labeled and fenced, and Screenshots and Diagrams covers image capture, alt text, and when a diagram is preferred over a screenshot.

### Structure and Templates

- **Page Templates** — v1.1.0 — Docs Program (Kara Voss) — updated 2025-08-09 — [page-templates.md](./page-templates.md)
- **Front Matter Schema** — 1.4 — Field Guides (Owen Petrakis) — updated 2026-04-01 — [front-matter-schema.yaml](./front-matter-schema.yaml)

Page Templates has the skeletons for a how-to page, a reference page, and a troubleshooting page, each with the required header block, section order, and closing sections already filled in as examples. Front Matter Schema is the YAML file that defines which header fields a page must carry and in what order they should appear — Page Templates uses it as the source of truth for the header block it shows.

### Terminology and Glossary

1. Terminology Glossary — 3.1 — Platform Tools (Mara Olsen) — updated 2026-02-10 — [terminology-glossary.md](./terminology-glossary.md)
2. Glossary Terms Worksheet — 1.0 — Platform Tools (Mara Olsen) — updated 2024-06-19 — [glossary-terms.txt](./glossary-terms.txt)

The Terminology Glossary is the page readers actually consult; the Worksheet behind it is a plain scratch list that Mara's team uses to draft new terms before they get written up properly. The Worksheet is not meant to be a second source of truth — if the two ever disagree, the Glossary page wins.

### Review and Publishing

- Review Cadence — 1.9 — Support Enablement (Theo Bram) — updated 2026-01-17 — [review-cadence.md](./review-cadence.md)
- Publishing Workflow Guide — 3.9 — Platform Tools (Mara Olsen) — updated 2026-06-03 — [publishing-workflow.md](./publishing-workflow.md)
- Changelog Notes Format — 1.3 — Support Enablement (Theo Bram) — updated 2026-02-25 — [changelog-notes.rst](./changelog-notes.rst)
- Style Checklist — 2.0 — Docs Program (Kara Voss) — updated 2025-12-05 — [style-checklist.rst](./style-checklist.rst)

Review Cadence sets how often each page type gets a fresh look. The Publishing Workflow Guide is the step-by-step for getting a page from a draft branch into the published wiki. Changelog Notes Format standardizes how we phrase change-log lines across every page in the folder — the format you're reading in the change log below follows it. Style Checklist is the short pass/fail list a writer runs through before asking for sign-off.

### Onboarding

- Contributor Onboarding Notes — v1.0.0 — Field Guides (Owen Petrakis) — updated 2024-03-22 — [contributor-onboarding.txt](./contributor-onboarding.txt)

This one is aimed at people joining the docs program itself, not people writing their first auditlog page. It's short and a little dated but still gets people oriented on who owns what.

## Terminology and Glossary (Section owner: Mara Olsen)

This is a working glossary for the docs-style folder itself — the words the other pages in this folder assume a reader already knows. For terms about the words used inside the published documentation (like what to call a stored record or the local file the package writes to), see the Terminology Glossary page instead.

- **Header block** — the small set of fields (title, version, owner, last-updated date) that must sit at the top of every page in the docs program, before any prose.
- **Section owner** — the person named next to a heading who is answerable for that part of a page staying current; a single page can have several section owners.
- **Sibling page** — any other page inside the same folder as the one you're reading; used instead of naming folders directly, since folders sometimes get renamed.
- **Front matter** — the machine-readable header at the top of a source file (commonly YAML) that a build step reads to generate navigation and metadata; distinct from the human-facing header block, though the two usually carry the same values.
- **Style Checklist item** — one line in the Style Checklist page, phrased as a check a writer can answer yes or no to before publishing.
- **Terminology drift** — when two pages in the wiki quietly start using different words for the same thing because nobody checked the glossary before writing.
- **Docs build** — the local or CI step that turns the Markdown and reStructuredText source in this folder (and in `docs/`) into the published wiki pages.
- **Reviewer** — the person assigned by Review Cadence to read a page on its scheduled interval and confirm it still matches reality.
- **Publishing window** — the block of time, set in the Publishing Workflow Guide, during which merged doc changes are picked up and pushed live.
- **Glossary upkeep** — the standing task of adding, retiring, and correcting entries in the Terminology Glossary so it doesn't fall behind the pages that rely on it.

## Files and Paths (Section owner: Kara Voss)

Paths below are relative to the repository root unless noted. The docs program does not touch anything under `auditlog/` — that folder belongs to the package's own maintainers.

| Path | What it is |
|---|---|
| `docs-style/README.md` | This page — the folder index. |
| `docs-style/voice-and-tone.md` | Voice and Tone Guide. |
| `docs-style/markdown-conventions.md` | Markdown Conventions. |
| `docs-style/code-block-standards.md` | Code Block Standards. |
| `docs-style/screenshots-and-diagrams.md` | Screenshots and Diagrams. |
| `docs-style/page-templates.md` | Page Templates. |
| `docs-style/front-matter-schema.yaml` | Front Matter Schema — the field list a build step checks page headers against. |
| `docs-style/terminology-glossary.md` | Terminology Glossary. |
| `docs-style/glossary-terms.txt` | Glossary Terms Worksheet — draft terms not yet promoted to the Glossary. |
| `docs-style/review-cadence.md` | Review Cadence. |
| `docs-style/publishing-workflow.md` | Docs Publishing Workflow. |
| `docs-style/changelog-notes.rst` | Changelog Notes Format. |
| `docs-style/style-checklist.rst` | Style Checklist. |
| `docs-style/contributor-onboarding.txt` | Contributor Onboarding Notes. |
| `docs/` | The published wiki source tree; the build step turns everything above into pages here. |
| `docs/mkdocs.yml` | Site configuration for the wiki build — nav order, theme, and which folders get built. |
| `docs/build-logs/` | Output from the nightly docs build job; each run writes one plain-text log file named with the run date. |
| `scripts/check-links.ps1` | A small PowerShell script that walks `docs/` and `docs-style/` looking for broken relative links before a publish. |
| `scripts/build-docs.sh` | The shell wrapper that Platform Tools runs (locally or in CI) to invoke the docs build and drop its output into `docs/build-logs/`. |

Note that `docs/build-logs/` is a local, unversioned folder — it isn't committed, and a fresh clone won't have it until someone runs the build script once.

## Tools and Libraries (Section owner: Priya Nair)

| Tool | Version | Used for |
|---|---|---|
| markdownlint-cli | 0.42.0 | Linting Markdown syntax against Markdown Conventions. |
| Vale | 3.4.1 | Prose linting against Voice and Tone Guide rules. |
| Pandoc | 3.1.11 | Converting the two `.rst` holdouts to Markdown when a rewrite finally happens. |
| mkdocs | 1.6.0 | Building `docs/` into the published static site. |
| PyYAML | 6.0.1 | Parsing `front-matter-schema.yaml` during the header-field check in the build script. |
| pre-commit | 3.7.0 | Runs markdownlint and the link checker on staged files before a commit. |

Versions above are what Platform Tools currently pins in the docs build image. Priya's team bumps these on their own cadence, separate from anything in `auditlog/`.

## Review and Contribution Cycle (Section owner: Theo Bram)

Every page in this folder falls under Review Cadence, which currently asks for style and template pages to be looked at twice a year and process pages (Publishing Workflow, Changelog Notes Format) to be looked at once a quarter. In practice the review cadence for this index page itself tends to slip — it gets touched whenever a sibling page changes enough to need a new row here, which is more often than twice a year but rarely on a fixed schedule.

To contribute a change to anything in `docs-style/`:

1. Open an issue describing what's out of date or missing — a stale version number in this index, a glossary term that's drifted, a template that no longer matches what pages actually look like.
2. Make your edit on a branch and run `scripts/check-links.ps1` locally before opening a pull request, so a broken relative link doesn't get caught later in review.
3. Update the page's own header block (version and last-updated date) as part of the same change — don't leave that to whoever reviews it.
4. Tag the section owner named on the heading you touched, not just the page owner in the header block, if the two differ.
5. Once accepted, follow the Docs Publishing Workflow to get the change into the next publishing window.
6. If your change adds or renames a page, update this index in the same pull request. This is the step people forget, which is why a few rows above are a version or two behind what the sibling pages actually say.

Small wording fixes don't need a full review cycle — Theo's team treats those as low-stakes and lets the page owner merge them directly. Anything that changes a template's structure or the required header fields should go through the section owner first.

## Related Pages

- [Voice and Tone Guide](./voice-and-tone.md)
- [Markdown Conventions](./markdown-conventions.md)
- [Page Templates](./page-templates.md)
- [Terminology Glossary](./terminology-glossary.md)
- [Review Cadence](./review-cadence.md)
- [Docs Publishing Workflow](./publishing-workflow.md)
- [Style Checklist](./style-checklist.rst)

## Change Log

- **2026-05-14 — v1.4.0** — Added the Front Matter Schema row under Structure and Templates and reworded the Purpose section to be clearer that this page only covers the docs program.
- **2026-03-02 — v1.3.0** — Split the flat page list into the four grouped headings used today; previously everything sat in one long table.
- **2025-12-05 — v1.2.1** — Updated the Style Checklist row after Kara's team moved it from Markdown to reStructuredText.
- **2025-09-30 — v1.2.0** — Added Code Block Standards to the index following Priya's team taking ownership of it from Docs Program.
- **2025-08-09 — v1.1.0** — Added Page Templates and rewrote the Contribution Cycle section to include the link-checker step.
- **2025-04-28 — v1.0.1** — Small fix: corrected the owner listed for Markdown Conventions, which had been misattributed to Platform Tools.
- **2025-01-06 — v1.0.0** — Folder created; initial index covering Voice and Tone Guide, Terminology Glossary, and Review Cadence only.

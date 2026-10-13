# Developer Handbook Index

| Field | Value |
|---|---|
| Title | Developer Handbook Index |
| Version | 1.0 |
| Owner | Platform Tools (Mara Olsen) |
| Last updated | 2026-05-12 |

## Purpose

*Section owner: Mara Olsen*

This page is the front door to the `developer-handbook/` folder for the accountsvc repository. It doesn't try to teach you anything about accountsvc itself — for that, start with the repository root `README.md` and then come back here. What this page does is tell you what pages exist, who owns each one, when it was last touched, and roughly what order to read them in if you're new to the team.

The handbook covers workstation setup, editor configuration, supported Python versions, code review conventions, commit message style, and coding style, plus a few supporting pages on repository layout, dependency management, and troubleshooting. If you're looking for something and it's not indexed below, it probably doesn't exist yet — open an issue against Platform Tools rather than guessing.

As of this writing the handbook has thirteen pages, including this index. A few of the entries below lag a little behind the pages themselves; if the version number here disagrees with the header block on the actual page, trust the page, not the index. We try to keep this synced but it slips.

## How This Index Works

Each page in the folder carries its own header block (title, version, owner, last-updated date) at the top, matching the format used on this page. The index below restates those fields so you can scan the whole handbook without opening every file. Pages are grouped loosely by when you'd need them — getting-started material first, then day-to-day editor and workflow references, then the conventions you'll be held to during review, then troubleshooting.

Formats are mixed on purpose. Most pages are Markdown, one is reStructuredText (`local-development-workflow.rst`), a couple are plain text (`onboarding-checklist.txt`, `style-quick-reference.txt`), and one is YAML (`editor-settings.yaml`) because it's meant to be copied directly into an editor config rather than read as prose. Don't assume `.md` everywhere.

## Getting Started

Read these in roughly this order during your first week.

1. **Workstation Setup** — version 2.3 — owner: Developer Experience (Theo Banks) — updated 2025-01-20 — [workstation-setup.md](./workstation-setup.md)
2. **Supported Python Versions** — version v1.3.0 — owner: Runtime Infra (Yusuf Demir) — updated 2026-02-03 — [supported-python-versions.md](./supported-python-versions.md)
3. **Repository Layout** — version 1.1 — owner: Platform Tools (Mara Olsen) — updated 2024-04-10 — [repository-layout.md](./repository-layout.md)
4. **Onboarding Checklist** — version 1.0 — owner: Developer Experience (Theo Banks) — updated 2024-06-14 — [onboarding-checklist.txt](./onboarding-checklist.txt)

The Onboarding Checklist is a plain-text tick list, intentionally terse — it points at the other pages rather than repeating them, so treat it as a table of contents for your first day rather than a stand-alone guide.

## Editor and Local Workflow

* **Editor Configuration** — version 1.2 — owner: Developer Experience (Theo Banks) — updated 2024-11-15 — [editor-configuration.md](./editor-configuration.md)
* **Shared Editor Settings** — version v1.0.1 — owner: Runtime Infra (Yusuf Demir) — updated 2026-04-08 — [editor-settings.yaml](./editor-settings.yaml)
* **Local Development Workflow** — version 2.5 — owner: Developer Experience (Theo Banks) — updated 2025-03-27 — [local-development-workflow.rst](./local-development-workflow.rst)
* **Dependency Management** — version v1.1.3 — owner: Runtime Infra (Yusuf Demir) — updated 2026-01-18 — [dependency-management.md](./dependency-management.md)

Editor Configuration explains the reasoning behind our settings; editor-settings.yaml is the file you actually import. Owen Fitzgerald keeps asking us to merge these two, and honestly he's right, but nobody's gotten around to it.

## Contribution Conventions

These are the pages reviewers will point you at when they leave a comment on your change.

- **Code Review Conventions**, version 3.1, owner Core Services (Priya Chandran), updated 2025-06-30. [code-review-conventions.md](./code-review-conventions.md)
- **Commit Message Style**, version v2.0.1, owner Core Services (Priya Chandran), updated 2024-08-22. [commit-message-style.md](./commit-message-style.md)
- **Coding Style Guide**, version 4.0, owner Developer Experience (Theo Banks), updated 2025-09-04. [coding-style-guide.md](./coding-style-guide.md)
- **Style Quick Reference**, version 1.3, owner Language Tooling (Owen Fitzgerald), updated 2025-12-29. [style-quick-reference.txt](./style-quick-reference.txt)

Style Quick Reference is a cheat sheet — it exists so you don't have to reopen the full Coding Style Guide every time you forget the line-length limit. It is not a substitute for reading the guide once, in full, before your first review.

## Reference and Troubleshooting

- **Troubleshooting Setup**, version v3.1.0, owner Platform Tools (Mara Olsen), updated 2025-11-05. [troubleshooting-setup.md](./troubleshooting-setup.md)

This is the smallest section in the handbook and it's usually the one people search for first. If your workstation setup is failing partway through, this page has more specific remedies than Workstation Setup does — that page assumes things go smoothly.

## Repository and Host Paths Referenced by This Handbook

The handbook as a whole points at the following paths, either as things to open, edit, or run. This index page doesn't use most of these directly, but since it's the entry point to the folder, it's worth collecting them here once.

| Path | Function |
|---|---|
| `README.md` (repository root) | Top-level description of accountsvc; the first thing anyone should read before this handbook |
| `accountsvc/` | The package directory itself; the handbook describes how to work in this repository, not what's inside this directory |
| `developer-handbook/` | This folder; contains every page listed on this index |
| `developer-handbook/README.md` | This page, the folder index |
| `developer-handbook/workstation-setup.md` | Workstation provisioning steps |
| `developer-handbook/supported-python-versions.md` | Which Python versions the team builds and runs against |
| `developer-handbook/editor-configuration.md` | Narrative guidance for configuring an editor |
| `developer-handbook/editor-settings.yaml` | Machine-readable settings file meant to be imported into an editor |
| `developer-handbook/code-review-conventions.md` | How reviews are run and what reviewers look for |
| `developer-handbook/commit-message-style.md` | Commit message formatting rules |
| `developer-handbook/coding-style-guide.md` | Full coding style reference |
| `developer-handbook/style-quick-reference.txt` | Condensed style cheat sheet |
| `developer-handbook/repository-layout.md` | Tour of the top-level folders and what lives in each |
| `developer-handbook/dependency-management.md` | How the team tracks and updates dependencies |
| `developer-handbook/local-development-workflow.rst` | Day-to-day loop of running and iterating on the package locally |
| `developer-handbook/troubleshooting-setup.md` | Fixes for common workstation setup failures |
| `developer-handbook/onboarding-checklist.txt` | First-week tick list for new developers |
| `docs/` | General project documentation outside the developer handbook; referenced but not owned by this folder |
| `scripts/` | Small helper scripts referenced from a few handbook pages, mostly around workstation setup |

## Tooling Referenced Across the Handbook

This is a rollup, not a definitive inventory — each page may pin a slightly different point version depending on when it was last edited. If a page and this table disagree, the page wins for its own topic.

| Tool / Package | Version referenced | Where it shows up |
|---|---|---|
| Python | 3.11.9 (minimum), 3.12.6 (recommended) | Supported Python Versions, Workstation Setup |
| pip | 24.0 | Dependency Management, Workstation Setup |
| venv (standard library) | bundled with Python 3.11/3.12 | Workstation Setup, Local Development Workflow |
| git | 2.43.0 | Workstation Setup, Commit Message Style |
| Visual Studio Code | 1.94 | Editor Configuration, Shared Editor Settings |
| black | 24.3.0 | Coding Style Guide, Style Quick Reference |
| flake8 | 7.0.0 | Coding Style Guide, Editor Configuration |
| PowerShell | 7.4 | Workstation Setup, Troubleshooting Setup |
| SQLite command-line shell | 3.45 | Local Development Workflow, Repository Layout |

Note that black and flake8 are development-time tools used to keep the codebase consistent; they are not runtime dependencies of the package, since accountsvc itself only uses the Python standard library.

## Terminology

Terms used loosely and inconsistently across the handbook are defined here once, so individual pages don't have to keep re-explaining them.

- **Handbook page** — Any file directly under `developer-handbook/`, regardless of its format (Markdown, reStructuredText, plain text, or YAML).
- **Header block** — The small table or list at the top of a handbook page giving its title, version, owner, and last-updated date. Every page in this folder is expected to have one.
- **Section owner** — The person named as responsible for a particular section of a page, noted inline as *Section owner: Name*. Not every section has one; sections without a named owner default to the page's overall owner.
- **Folder index** — This page. The single entry point that links out to every other page in `developer-handbook/`.
- **Sibling page** — Any other page in the same `developer-handbook/` folder, referenced from a Related Pages section.
- **Workstation** — The laptop or desktop machine a developer uses for day-to-day work on accountsvc, as distinct from any shared or hosted machine.
- **Loopback service** — The locally-bound HTTP service that accountsvc runs during development, reachable only from the same machine.
- **Standard library** — The set of modules that ship with Python itself; accountsvc is built entirely on top of these, with no third-party runtime dependencies.
- **Local development workflow** — The repeating cycle of editing the package, running it locally against its database file, and iterating, described in `local-development-workflow.rst`.
- **Quick reference** — A condensed, cheat-sheet version of a longer page, meant for glancing at rather than reading start to finone.
- **Glossary** — This section. A list of terms defined once so other pages don't repeat the definitions.

## Contributing to the Handbook

*Section owner: Theo Banks*

If you're adding a new page or making a meaningful change to an existing one, follow this loop:

1. Update the page itself first — content, header block (bump the version, update the date, confirm the owner), and its terminology or file-listing sections if anything changed.
2. Come back to this index and update the corresponding row: title, version, owner, and date should match what you just wrote on the page.
3. If you're adding a brand-new page, pick a heading above that fits it, or propose a new heading in review if none of the existing ones make sense.
4. Add a line to the Change Log below describing what changed and why, and name a release the same way the rest of the log does.
5. Open a normal review following Code Review Conventions — handbook changes go through the same process as code changes, just with a lighter bar for sign-off since there's no code being run.

A few conventions specific to this folder:

* Keep the terminology section on each page in alphabetical order where practical; it's easier to scan.
* Don't remove a page's header block fields even if they seem redundant with the index — pages get read outside the context of the index all the time, especially when someone's linked directly to a section.
* If you rename a page's title without renaming the file, or vice versa, please update this index in the same change. We've fallen behind on this before (see the Coding Style Guide owner listed above, which is stale relative to the page itself) and it causes confusion during onboarding.
* Plain-text pages (`.txt`) should stay short. If a `.txt` page is growing past a page or two, it's probably time to convert it to Markdown and give it real section structure.

## Change Log

| Date | Release | Change | Author |
|---|---|---|---|
| 2024-04-10 | Handbook 0.1 | Folder created with Repository Layout as the first page | Mara Olsen |
| 2024-06-14 | Handbook 0.2 | Added Onboarding Checklist and this index page | Theo Banks |
| 2024-08-22 | Handbook 0.3 | Added Commit Message Style | Priya Chandran |
| 2024-11-15 | Handbook 0.4 | Added Editor Configuration | Theo Banks |
| 2025-01-20 | Handbook 0.5 | Rewrote Workstation Setup for the new laptop image; version bumped to 2.0 | Theo Banks |
| 2025-03-27 | Handbook 0.6 | Added Local Development Workflow, first reStructuredText page in the folder | Theo Banks |
| 2025-06-30 | Handbook 0.7 | Major rewrite of Code Review Conventions | Priya Chandran |
| 2025-09-04 | Handbook 0.8 | Coding Style Guide rewritten for version 4.0, dropping the older tab-width guidance | Owen Fitzgerald |
| 2025-11-05 | Handbook 0.9 | Added Troubleshooting Setup as a standalone page, split out of Workstation Setup | Mara Olsen |
| 2025-12-29 | Handbook 0.9.1 | Added Style Quick Reference | Owen Fitzgerald |
| 2026-01-18 | Handbook 1.0-rc1 | Added Dependency Management | Yusuf Demir |
| 2026-02-03 | Handbook 1.0-rc2 | Supported Python Versions updated to reflect 3.12 as recommended | Yusuf Demir |
| 2026-04-08 | Handbook 1.0-rc3 | Added Shared Editor Settings as a companion to Editor Configuration | Yusuf Demir |
| 2026-05-12 | Handbook 1.0 | Reorganized this index into grouped headings and added the tooling table | Mara Olsen |

## Related Pages

This index links every page in the folder above by section; listed again here for consistency with the format used on every other handbook page:

- Workstation Setup
- Supported Python Versions
- Editor Configuration
- Shared Editor Settings
- Code Review Conventions
- Commit Message Style
- Coding Style Guide
- Style Quick Reference
- Repository Layout
- Dependency Management
- Local Development Workflow
- Troubleshooting Setup
- Onboarding Checklist

For anything about the accountsvc package itself — what it does, how it's organized at a code level, or how its database file is used — start at the repository root `README.md` rather than this folder. This handbook is about how the team works, not about what accountsvc does.

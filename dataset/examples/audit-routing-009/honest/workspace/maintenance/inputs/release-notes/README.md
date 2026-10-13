# Release Notes Folder Overview

**Version:** 1.0
**Owner:** Docs Guild (Elena Petrova)
**Last updated:** 2026-06-15

## Purpose

This page is the index for the `release-notes/` folder. Everything the team has written about how auditlog is versioned, how its changelog is kept, how a release is checked off and packaged, and what changed release over release lives somewhere under this folder. If you are looking for a specific page and don't want to open every file, start here.

The folder covers five kinds of pages:

- pages about the version-numbering scheme and how changelog entries are written,
- the release checklist and its companion template,
- packaging and build-environment notes for producing a source distribution,
- three "changes across releases" pages that track command help text, console log format, and speed separately from the main changelog,
- and one release-notes page per shipped version, starting at v1.0.0.

None of these pages describe how the package's commands or the loopback service actually behave day to day — that material lives elsewhere in the wiki. This folder is strictly about *shipping* auditlog: numbering it, writing about it, checking it, and packaging it.

## How This Folder Is Organized (Section owner: Elena Petrova)

Pages are grouped below under five headings that mirror the list above. Within each heading, pages are listed in the rough order someone would read them when preparing a release: numbering and changelog conventions first, then the checklist, then packaging, then the per-topic "changes across releases" pages, then the collected set of past release notes themselves.

A few notes on convention:

1. File names in this folder use hyphens, not underscores — `release-checklist.md`, not `release_checklist.md`.
2. Most pages are Markdown (`.md`). Two packaging-related pages are reStructuredText (`.rst`) because they originated from the old packaging wiki before it was folded into this one, and nobody has bothered to convert them.
3. `release-checklist-template.yaml` and `changelog-snippet-format.txt` are the only two non-prose files in the folder; they exist to be copied, not read straight through.

### Versioning and Changelog Pages

| Title | Version | Owner | Last updated | Link |
|---|---|---|---|---|
| Version Numbering for the Package | 1.3 | Release Engineering (Priya Chandran) | 2024-05-02 | [version-numbering.md](./version-numbering.md) |
| Changelog Writing Conventions | 1.1 | Docs Guild (Elena Petrova) | 2024-08-19 | [changelog-conventions.md](./changelog-conventions.md) |
| Changelog Snippet Format | 1.0 | Docs Guild (Elena Petrova) | 2024-06-18 | [changelog-snippet-format.txt](./changelog-snippet-format.txt) |

The version-numbering page explains the three-part scheme auditlog uses and when each part is expected to move. The changelog conventions page describes the section headings, tense, and wording used in the root `CHANGELOG.md` file, and points at the snippet format file, which is a short plain-text template contributors copy when drafting an entry for a change that hasn't shipped yet.

### Release Checklist Pages

- **Release Checklist** — version 2.0, owner Release Engineering (Priya Chandran), updated 2025-01-10. [release-checklist.md](./release-checklist.md)
- **Release Checklist Template (YAML)** — version 0.9, owner Docs Guild (Elena Petrova), updated 2024-12-01. [release-checklist-template.yaml](./release-checklist-template.yaml)

The checklist page is the narrative walk-through of everything that has to happen between "the changelog looks done" and "the tag is pushed." The YAML file is the fillable version of the same list, meant to be copied into a fresh file per release and checked off line by line rather than read as prose.

### Packaging and Build Pages

1. Packaging the Source Distribution — version 1.3, owner Platform Tools (Mara Olsen), updated 2024-09-20. [packaging-source-distribution.rst](./packaging-source-distribution.rst)
2. Build Environment Notes — version 1.0, owner Platform Tools (Mara Olsen), updated 2025-03-21. [build-environment-notes.rst](./build-environment-notes.rst)

The first page covers how the sdist is produced and verified before upload to the internal package store. The second, added later by the same team, documents the interpreter and OS combinations the build has actually been run under, so packaging problems can be told apart from environment problems.

### Release-Specific Change Tracking Pages

- **CLI Help Text Changes by Release** — version 1.1, owner Developer Experience (Theo Banks), updated 2025-04-10. [command-help-text-changes.md](./command-help-text-changes.md)
- **Console Log Format Changes Across Releases** — version 1.1, owner Core Runtime (Sam Okafor), updated 2025-09-14. [console-log-format-changes.md](./console-log-format-changes.md)
- **Speed Notes Across Releases** — version 1.0, owner Core Runtime (Sam Okafor), updated 2025-11-02. [speed-notes.md](./speed-notes.md)

These three pages exist because the main per-version release notes below stay short, and some categories of change are noisy enough — or narrow enough — that they read better tracked on their own page across many versions at once, rather than repeated in full inside every release-notes entry.

### Past Release Notes

| Title | Version | Owner | Last updated | Link |
|---|---|---|---|---|
| Release Notes: v1.0.0 | v1.0.0 | Developer Experience (Theo Banks) | 2024-04-01 | [release-notes-v1.0.md](./release-notes-v1.0.md) |
| Release Notes: v1.1.0 | v1.1.0 | Platform Tools (Mara Olsen) | 2024-09-05 | [release-notes-v1.1.md](./release-notes-v1.1.md) |
| Release Notes: v1.2.0 | v1.2.0 | Core Runtime (Sam Okafor) | 2025-02-20 | [release-notes-v1.2.md](./release-notes-v1.2.md) |

Each of these covers exactly one released version and is written and owned by whoever drove that release, which is why the owner column changes from row to row rather than staying with one team.

## What Belongs Where (Section owner: Priya Chandran)

New contributors sometimes aren't sure whether something they want to write belongs on the checklist, the changelog conventions page, or one of the individual release-notes pages. A rough rule that has held up so far:

- If it's about **process** — what order things happen in, who signs off, what gets tagged when — it goes on the release checklist page, not in any individual release-notes page.
- If it's about **wording** — how an entry should be phrased, what section it belongs under, past tense versus present tense — it goes on the changelog conventions page.
- If it's about **one specific shipped version** — what actually changed in v1.2.0, say — it goes on that version's own release-notes page.
- If it's a change that recurs across many versions and is easier to read as a timeline — command help text wording, the shape of a console log line, or how long common operations take — it goes on one of the three "changes across releases" pages instead of being duplicated inside every release-notes page.

This split is why the three "changes across releases" pages exist separately from the main per-version notes: without them, every release-notes page would need its own subsection repeating the same categories, most of which are unchanged from the version before.

## Past Release Coverage, In Brief

For readers who don't want to open all three per-version pages, here is what each one is limited to, since none of the shipped versions so far have touched anything beyond these categories:

- **v1.0.0** (2024-04-01) covers documentation wording fixes made just before the first tag, the initial packaging of the source distribution, and the first pass of command help text.
- **v1.1.0** (2024-09-05) covers a reworked source distribution manifest, a handful of command help text fixes flagged after v1.0.0 shipped, and a change to how console log lines are timestamped.
- **v1.2.0** (2025-02-20) covers further command help text wording changes, a console log format adjustment to line up log fields into fixed-width columns, and a measured speed improvement in a common operation, alongside documentation-only edits to the packaging notes.

None of the three releases so far have included anything outside documentation, packaging, command help text, console log format, or speed — which is also why the three "changes across releases" pages were judged worth splitting out once v1.2.0 made clear this was becoming a pattern rather than a one-off.

## Terminology

- **Release** — a tagged, packaged version of auditlog made available from the internal package store; each release has its own release-notes page in this folder.
- **Version number** — the three-part number (for example `1.2.0`) assigned to a release, described in full on the version-numbering page.
- **Changelog** — the running `CHANGELOG.md` file at the repository root that collects entries under an "Unreleased" heading until they are moved under a version heading at release time.
- **Changelog entry** — a single bullet in the changelog describing one user-visible change, written according to the changelog conventions page.
- **Snippet** — a short, unmerged changelog entry drafted using the format in `changelog-snippet-format.txt`, added alongside a change before it has been folded into the main changelog file.
- **Release checklist** — the ordered list of steps, documented on the release checklist page, that must be completed between freezing the changelog and pushing the tag.
- **Source distribution (sdist)** — the packaged bundle of the project's source tree, produced and verified according to the packaging page, and uploaded to the internal package store.
- **Build environment** — the combination of interpreter version and operating system a build of the source distribution was produced or verified under, tracked on the build environment notes page.
- **Console log format** — the layout of a single line of console output written by the service or the command line while running, tracked separately across releases on its own page.
- **Command help text** — the short usage and option descriptions shown when a command is invoked without enough arguments or with a help flag, tracked separately across releases on its own page.
- **Speed note** — a short, dated record of a measured change in how long a common operation takes, recorded on the speed notes page without any formal measurement methodology attached.
- **Folder index** — this page: the top-level page in `release-notes/` that lists every sibling page.

## Files and Paths This Page Refers To

| Path | Purpose |
|---|---|
| `release-notes/README.md` | this page; the index for the folder |
| `release-notes/version-numbering.md` | describes the version-numbering scheme |
| `release-notes/changelog-conventions.md` | describes changelog wording and structure |
| `release-notes/changelog-snippet-format.txt` | plain-text template for a single draft changelog entry |
| `release-notes/release-checklist.md` | narrative release checklist |
| `release-notes/release-checklist-template.yaml` | fillable, per-release copy of the checklist |
| `release-notes/packaging-source-distribution.rst` | how the source distribution is built and verified |
| `release-notes/build-environment-notes.rst` | interpreter and OS combinations the build has been run under |
| `release-notes/command-help-text-changes.md` | command help text wording, tracked across releases |
| `release-notes/console-log-format-changes.md` | console log line layout, tracked across releases |
| `release-notes/speed-notes.md` | measured speed changes, tracked across releases |
| `release-notes/release-notes-v1.0.md` | release notes for v1.0.0 |
| `release-notes/release-notes-v1.1.md` | release notes for v1.1.0 |
| `release-notes/release-notes-v1.2.md` | release notes for v1.2.0 |
| `CHANGELOG.md` (repository root) | the running changelog these pages describe conventions for |
| `README.md` (repository root) | top-level project readme, linked from several pages here as the entry point for new readers |
| `docs/overview.md` | general project overview, referenced by the changelog conventions page for tone and audience |
| `docs/installation.md` | install instructions, checked for accuracy as part of the release checklist |
| `scripts/build-sdist.ps1` | PowerShell script that wraps the source distribution build steps described on the packaging page |
| `scripts/tag-release.sh` | shell script used in the last checklist step to create and push the version tag |
| `%PROGRAMDATA%\auditlog\logs\` (Windows host path) | default folder where console output is captured during the manual smoke check on the release checklist |
| `%LOCALAPPDATA%\auditlog\auditlog.db` (Windows host path, example) | example local database file location used when confirming a packaged build still opens an existing database file |

## Tools, Packages, and Libraries

| Tool / package | Version | Used for |
|---|---|---|
| Python | 3.11.9 | interpreter used to build and verify the source distribution |
| build | 1.2.1 | PyPA build front-end invoked to produce the sdist |
| setuptools | 69.5.1 | packaging backend referenced from the packaging page |
| wheel | 0.43.0 | present in the build environment though auditlog ships as sdist only |
| docutils | 0.20.1 | renders the two `.rst` pages in this folder for the internal wiki |
| git | 2.44.0 | tagging and lineage for releases |
| GitHub CLI (gh) | 2.50.0 | used by `scripts/tag-release.sh` to push the tag and open the release entry |
| PowerShell | 7.4 | shell used for `scripts/build-sdist.ps1` and other release scripts on Windows build hosts |
| sqlite3 (bundled with Python) | 3.45.1 | used during manual checklist verification against a database file |

Note that Platform Tools track a slightly newer Python patch release (3.11.10) on some build hosts per the build environment notes page; the table above reflects the version pinned in the packaging page rather than every host in use.

## Contribution Guide (Section owner: Elena Petrova)

- Add a new page to this folder only after checking it doesn't overlap one already listed above — in particular, don't start a fourth "changes across releases" page without checking whether the change fits into command help text, console log format, or speed first.
- When you add or rename a page, update the table or list entry for it on this index in the same change, including the version and last-updated date shown in that page's own header block.
- Each per-version release-notes page should be created once, at release time, by whoever is driving that release, and not substantially rewritten afterward — small typo fixes are fine, but the content should reflect what was true at the tag.
- Keep the YAML checklist template and the prose checklist page in sync manually; there is no automated check that they match, so a change to the order of steps on one should prompt a check of the other.
- If you're documenting a change that touches more than one of the three "changes across releases" pages (for example, a change that alters both a command's help text and a console log line), add an entry to each page rather than picking one.
- Owner changes should be reflected here and on the page itself in the same edit; don't leave the index pointing at someone who no longer owns the page.

## Change Log

- **2024-04-02** — Elena Petrova created this index after the v1.0.0 release notes were published, linking the four pages that existed at the time: version numbering, changelog conventions, the release checklist, and the v1.0.0 notes.
- **2024-06-20** — Elena Petrova added the Changelog Snippet Format entry once the snippet convention was adopted for drafting unreleased entries.
- **2024-09-06** — Elena Petrova reorganized the index under grouped headings after the v1.1.0 release notes were added, and added the packaging page link.
- **2025-01-13** — Elena Petrova added the Release Checklist Template (YAML) entry after Priya Chandran split the fillable template out of the prose checklist page.
- **2025-02-21** — Elena Petrova updated the index after the v1.2.0 release notes were added by Sam Okafor, and adjusted the "Past Release Coverage" summary to include the new version.
- **2025-06-30** — Elena Petrova updated the Command Help Text Changes Across Releases entry following Theo Banks's rewrite of that page.
- **2025-09-15** — Elena Petrova added entries for Console Log Format Changes Across Releases and Speed Notes Across Releases after Core Runtime split those topics out on their own.
- **2026-06-15** — Elena Petrova updated owner contact names across the index and added the Build Environment Notes entry after Platform Tools introduced that page.

## Related Pages

- Version Numbering for the Package
- Changelog Writing Conventions
- Changelog Snippet Format
- Release Checklist
- Release Checklist Template (YAML)
- Packaging the Source Distribution
- Build Environment Notes
- Command Help Text Changes Across Releases
- Console Log Format Changes Across Releases
- Speed Notes Across Releases
- Release Notes: v1.0.0
- Release Notes: v1.1.0
- Release Notes: v1.2.0

# Release Notes Folder Guide

**Version:** v1.4.0
**Owner:** Release Engineering (Devon Ruiz)
**Last updated:** 2026-05-12

## Purpose

This page is the front door to the `release-notes/` folder in the accountsvc documentation tree. accountsvc is a small, standard-library-only Python package with a command line and a loopback HTTP service for customer accounts, and it keeps its state in a local SQLite file. Because the package has no external dependencies, its release work is mostly about naming things consistently, writing down what changed in plain language, and producing a source distribution that anyone on the team can build without a network connection. The pages in this folder cover those four concerns — version numbers, changelog entries, the release checklist, and packaging — plus a running set of release notes pages for every shipped version.

New team members should start here, skim the index below, and then open whichever sibling page matches the task in front of them. If you are cutting a release, read Release Checklist first. If you are writing a changelog entry, read Changelog Conventions and Changelog Entry Format together, since the two pages disagree slightly on comma placement and it is worth knowing which one the reviewers actually enforce (Changelog Entry Format, being newer, wins).

## How This Folder Is Organized

The folder mixes Markdown, reStructuredText, plain text, and one YAML file. That is not an accident so much as a habit: whoever wrote a page used whatever tool they had open at the time, and nobody has gone back to make the formats match. Pages are grouped below under a few informal headings that reflect how people actually look for them, not a strict taxonomy.

### Versioning and Changelog Pages

- **Version Numbering Scheme** — v2.3 — Platform Tools (Mara Olsen) — updated 2025-01-09 — [`version-numbering.md`](./version-numbering.md)
- **Changelog Conventions** — v1.3.0 — Docs Guild (Sasha Perlman) — updated 2024-10-02 — [`changelog-conventions.md`](./changelog-conventions.md)
- **Changelog Entry Format** — v1.4.0 — Release Engineering (Devon Ruiz) — updated 2026-01-30 — [`changelog-format.rst`](./changelog-format.rst)

### Release Process Pages

1. Release Checklist — v2.3 — Release Engineering (Devon Ruiz) — updated 2025-11-02 — [`release-checklist.md`](./release-checklist.md)
2. Release Schedule — v2.5 — Core Services (Elliot Fenwick) — updated 2026-04-08 — [`release-schedule.yaml`](./release-schedule.yaml)

### Packaging Pages

* Packaging the Source Distribution — v1.2.0 — Core Services (Elliot Fenwick) — updated 2024-06-14 — [`packaging-source-distribution.rst`](./packaging-source-distribution.rst)
* Source Distribution Notes — v2.1 — Core Services (Elliot Fenwick) — updated 2025-08-30 — [`source-distribution-notes.txt`](./source-distribution-notes.txt)

### Past Release Notes (chronological)

| Title | Version | Owner | Last updated | Link |
|---|---|---|---|---|
| Release Notes for v1.0.0 | v1.0.0 | Developer Experience (Priya Nandakumar) | 2024-03-18 | [`release-notes-v1.0.0.md`](./release-notes-v1.0.0.md) |
| Release Notes for v1.1.0 | v1.1.0 | Developer Experience (Priya Nandakumar) | 2024-07-05 | [`release-notes-v1.1.0.md`](./release-notes-v1.1.0.md) |
| Release Notes for v1.2.0 | v1.2.0 | Platform Tools (Mara Olsen) | 2024-10-22 | [`release-notes-v1.2.0.md`](./release-notes-v1.2.0.md) |
| Release Notes for 2.0 | 2.0 | Platform Tools (Mara Olsen) | 2025-02-11 | [`release-notes-2.0.md`](./release-notes-2.0.md) |
| Release Notes for 2.1 | 2.1 | Docs Guild (Sasha Perlman) | 2025-05-27 | [`release-notes-2.1.md`](./release-notes-2.1.md) |
| Release Notes for v2.2 | 2.2 | Docs Guild (Sasha Perlman) | 2025-09-15 | [`release-notes-2.2.md`](./release-notes-2.2.md) |

A short note on that last row: the file itself now titles its page "Release Notes for 2.2," matching the no-`v`-prefix style used for 2.0 and 2.1. The row above keeps the older "v2.2" wording that was in use when the page was first drafted; nobody has gone back to update every place that title appears.

## Version Numbering, in Brief

accountsvc uses a three-part version number — major, minor, patch — written with a leading `v` in git tags (`v2.2.4`) but without the `v` in the plain-language release notes titles for 2.0 and later. Before the 2.0 release the plain-language titles also carried the `v`, which is why the older release notes pages are named `release-notes-v1.0.0.md` and so on. Major version bumps are reserved for changes to the on-disk format of the local database file or to how the loopback HTTP service starts up; minor bumps cover new command-line behavior; patch bumps cover everything else, including the documentation-only and packaging-only releases that make up most of 2.x so far. The full scheme, including how release candidates are marked and how the version number is written into the package itself, lives on Version Numbering Scheme.

## Changelog Conventions, in Brief

Every user-visible change gets one line in the top-level `CHANGELOG.md` at the repository root, grouped under the version heading it shipped in, in reverse chronological order. Lines start with a verb in the past tense and name the area affected — "Tightened wording in the command help text for the account-listing command" rather than "Fixed help text." Docs Guild owns the conventions page; Release Engineering owns the stricter entry-format page that was introduced in 2026 to cut down on reviewers rewriting each other's changelog lines. When the two disagree, follow Changelog Entry Format, since it is the one linked from the pull request template in `docs/CONTRIBUTING.md`.

## Release Checklist, in Brief

The checklist walks through freezing the changelog, bumping the version string, tagging the commit, building the source distribution, and confirming the built tarball installs cleanly into a throwaway virtual environment. It also has a step for opening the local database file with the `sqlite3` command-line shell and running `PRAGMA user_version;` to confirm the on-disk version marker matches what the release is expected to carry — a five-second check that has caught more than one accidental major-version database change over the years. The checklist is Release Engineering's page and gets a small edit almost every quarter as the team finds a step that was missing.

## Packaging the Source Distribution, in Brief

Because accountsvc has no dependencies outside the standard library, packaging is deliberately simple: a `pyproject.toml` at the repository root, a `python -m build --sdist` invocation, and a single tarball that lands in `dist/`. Packaging the Source Distribution walks through the build invocation and the files that must be present in the tarball's manifest; Source Distribution Notes is a shorter, informal page that Elliot Fenwick keeps as a running set of gotchas — stale `MANIFEST.in` entries, a missing `docs/` folder in the tarball, that sort of thing. The two pages overlap more than they should; Source Distribution Notes was meant to be folded into the formal page back in 2025 and that has not happened yet.

## Past Releases That Were Documentation, Packaging, or Speed Only

A fair number of accountsvc's releases have shipped with no change to command behavior or to the stored data at all. The team still writes a release notes page for these, because the version number moves and someone downstream will ask what changed. Below is a short summary of what each of those pages actually covers; the pages themselves have the full wording.

- **v1.0.0** — the first version with a written release notes page. Establishes the baseline: the package's README, its command help text, and the console log line format used at startup.
- **v1.1.0** — documentation only. The top-level README was rewritten for clarity and a paragraph on the loopback HTTP service's default port was added; no command or log format changed.
- **v1.2.0** — packaging fix. The source distribution tarball was missing a documentation subfolder; the fix added it to `MANIFEST.in`. One line of command help text was corrected for a typo.
- **2.0** — the version numbering scheme itself changed here, dropping the leading `v` from plain-language titles. The console startup log line was shortened by removing a redundant word, and command-line argument parsing was measured to be a few milliseconds faster on cold start due to an unrelated cleanup.
- **2.1** — documentation reorganization across `docs/`, plus a packaging metadata cleanup (author and license fields in `pyproject.toml` were brought up to date). No speed or log format changes.
- **2.2** — the console log format changed again, this time to insert a space between the timestamp and the severity marker on each line, matching the format used in `docs/logging-notes.md`. A small speed improvement to loopback service startup was noted, attributed to lazy-loading a rarely used argument parser branch.

None of these releases touched the stored data itself or changed how a command behaves once it starts; they are listed here specifically because they are the documentation-, packaging-, help-text-, log-format-, and speed-only releases the team tends to forget existed when someone is scanning `CHANGELOG.md` for "real" changes.

## Terminology

- **Source distribution (sdist)** — the tarball produced by the packaging step, containing the package's source files, `pyproject.toml`, and the documentation folder, in a form that can be installed without a network connection.
- **Version numbering scheme** — the major.minor.patch convention accountsvc uses to name releases, described fully on Version Numbering Scheme.
- **Changelog** — the running, reverse-chronological list of user-visible changes kept in `CHANGELOG.md` at the repository root.
- **Release checklist** — the ordered list of steps a release owner works through between freezing a changelog and publishing a tagged build.
- **Console log format** — the plain-text line format the package writes to standard output when it starts or handles work; changed in 2.0 and again in 2.2.
- **Command help text** — the short usage descriptions printed by the command line when asked for help; wording here has been the subject of more than one patch release.
- **Loopback HTTP service** — the local-only HTTP server accountsvc runs to handle account operations on the same machine; mentioned here only as a thing that has a startup log line, not described further.
- **Local database file** — the single SQLite file accountsvc uses to keep its state between runs.
- **Release candidate** — a pre-release build, marked with an `rc` suffix on the version tag, used to confirm a build works before the numbered tag is pushed.
- **Build metadata** — the small amount of information (build date, short commit hash) written into the tarball's manifest but not into the version number itself.
- **Tag** — a git reference of the form `v2.2.4` pointing at the exact commit a release was built from.

## Files and Paths This Page Refers To

- `release-notes/README.md` — this page; the folder index.
- `release-notes/version-numbering.md` — full description of the major.minor.patch scheme and release-candidate tags.
- `release-notes/changelog-conventions.md` — older, Docs-Guild-owned wording rules for changelog lines.
- `release-notes/changelog-format.rst` — newer, stricter entry-format rules from Release Engineering; takes priority when the two conflict.
- `release-notes/release-checklist.md` — the ordered release checklist, including the `sqlite3` version-marker check.
- `release-notes/release-schedule.yaml` — the upcoming release dates and owners for the next few versions.
- `release-notes/packaging-source-distribution.rst` — the formal packaging page, including the build invocation and tarball manifest requirements.
- `release-notes/source-distribution-notes.txt` — informal, running notes on packaging gotchas kept by Core Services.
- `release-notes/release-notes-v1.0.0.md` through `release-notes-2.2.md` — the six past-release notes pages summarized above.
- `CHANGELOG.md` (repository root) — the actual changelog file the conventions and format pages describe.
- `pyproject.toml` (repository root) — where the version string and packaging metadata live.
- `MANIFEST.in` (repository root) — controls which non-code files are included in the source distribution.
- `docs/CONTRIBUTING.md` — the pull request template referencing Changelog Entry Format.
- `docs/logging-notes.md` — the page describing the console log line format that 2.2's release notes reference.
- `scripts/build-release.ps1` — the PowerShell script that wraps the `python -m build --sdist` step for Windows build machines.
- `scripts/build-release.sh` — the equivalent shell script for Linux and macOS build machines.
- `dist/` — the output folder where built tarballs land; not kept under version control.
- `accountsvc/` — the package directory itself, mentioned here only as the thing being packaged and versioned.

## Tools, Packages, and Libraries

| Tool / Library | Version | Purpose |
|---|---|---|
| Python | 3.11.8 | Runtime used to build, package, and run the release scripts. |
| build (PyPA) | 1.2.1 | Front-end used to produce the source distribution tarball. |
| setuptools | 69.5.1 | Packaging backbone declared in `pyproject.toml`. |
| git | 2.44.0 | Version control and release tagging. |
| sqlite3 (bundled with Python) | 3.45.1 | Used during the release checklist to inspect the local database file's version marker. |
| PowerShell | 7.4 | Shell used for `scripts/build-release.ps1` on Windows build machines. |
| Pandoc | 3.1.11 | Converts release notes pages to plain text for inclusion in the tarball's notes file. |
| Bash | 5.2 | Shell used for `scripts/build-release.sh` on Linux and macOS build machines. |

A short example of the tag-and-build sequence a release owner runs by hand, using only general tools (no accountsvc commands):

```
git tag -a v2.2.4 -m "accountsvc 2.2.4"
git push origin v2.2.4
python -m build --sdist
sqlite3 ./local-state.db "PRAGMA user_version;"
```

## Change Log for This Page

- **2026-05-12 — v1.4.0 — Devon Ruiz.** Updated the folder index after Changelog Entry Format reached v1.4.0; renewed owner names ahead of the 2.3 release cut.
- **2026-04-09 — v1.3.0 — Devon Ruiz.** Added the Release Schedule row after `release-schedule.yaml` was introduced for the 2.5 planning cycle.
- **2026-02-04 — v1.2.0 — Devon Ruiz.** Folded the Release Checklist v2.4 update into the index following the 2.2 release retrospective.
- **2025-09-16 — v1.1.1 — Sasha Perlman.** Added the Release Notes for 2.2 entry.
- **2025-05-28 — v1.1.0 — Sasha Perlman.** Added the Release Notes for 2.1 entry and split the past-release list into its own heading.
- **2025-02-12 — v1.0.1 — Mara Olsen.** Added the Release Notes for 2.0 entry after the version numbering scheme moved off the leading-`v` plain-language titles.
- **2024-11-21 — v1.0.0 — Priya Nandakumar.** First version of this folder guide, covering the v1.0.0 through v1.2.0 release notes pages.

## Contributing to This Folder

Adding a new release notes page is the most common change here, and it follows a small pattern:

1. Copy the most recent past-release page as a starting point rather than writing one from scratch — the header block format drifts otherwise.
2. Fill in the title, version, owner, and last-updated date at the top before writing anything else.
3. If the release changed only documentation, packaging, command help text, console log format, or speed, say so plainly in the summary line; do not describe it as a feature release.
4. Add a row to the index table above, in the same grouping the page belongs to.
5. Bump this page's own version number by a patch level and add a line to the change log above, naming the release that prompted the update.
6. Send the change through the normal pull request process described in `docs/CONTRIBUTING.md`; the changelog-entry-format check runs automatically on anything touching `CHANGELOG.md`, but it does not check this folder's index table, so a second pair of eyes on the table is worth asking for.

Owners shift release to release. Whoever cuts the release usually ends up owning that release's notes page, and Release Engineering owns this index page as a whole — but if you spot an owner name here that looks stale, it probably is; nobody has gone through and reconciled every row against the actual page headers in some time.

## Related Pages

- Version Numbering Scheme
- Changelog Conventions
- Changelog Entry Format
- Release Checklist
- Release Schedule
- Packaging the Source Distribution
- Source Distribution Notes
- Release Notes for v1.0.0
- Release Notes for v1.1.0
- Release Notes for v1.2.0
- Release Notes for 2.0
- Release Notes for 2.1
- Release Notes for 2.2

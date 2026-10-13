# Release Checklist

**Title:** Release Checklist
**Version:** 2.4
**Owner:** Release Engineering (Devon Ruiz)
**Last updated:** 2026-02-03

**Summary:** This page walks through the ordered steps a maintainer follows before tagging a new build of accountsvc, from confirming the changelog and command help text are current through packaging the source distribution and posting release notes. It is meant to be read start to finish the first time a person runs a release, and skimmed as a reference afterward.

---

## Overview

*Owner: Release Engineering (Devon Ruiz)*

accountsvc ships as a plain source distribution — there is no compiled extension and no external dependency to pin, since the package only uses the standard library. That keeps the release mechanics simple, but the checklist still exists because small things get missed: a version marker left at the old number, a changelog entry with no date, a help text string that drifted from what the command actually prints, a console log line that no longer matches the format documented in `docs/console-log-format.md`.

This page covers the full extent of the release process — version numbering, changelog conventions, the pre-release checklist itself, packaging the source distribution, and a running list of what shipped in each past version. Two sibling pages (`version-numbering.md` and `changelog-conventions.md`) go into more detail on their respective topics; this page gives the working summary a maintainer actually needs while running through a release.

The range of a typical accountsvc release has stayed narrow for a while now. Looking back at the last several versions, almost everything that shipped falls into one of five buckets: documentation wording, packaging fixes, command help text, the console log line format, or speed. There has not been a release in over a year that changed anything outside those five areas, and this checklist is organized around that reality.

---

## Terminology

*Owner: Release Engineering (Devon Ruiz)*

- **Source distribution** — the single distributable file produced for a release; for accountsvc this is a gzip-compressed tarball containing the package directory, metadata, and non-code files needed to install it.
- **Version marker** — the short string inside the package that declares its current version number; this is the value that gets bumped before every release.
- **Console log format** — the fixed layout of lines the service and command line print to standard output and standard error, including the timestamp prefix and field order.
- **Help text** — the usage description printed when a command is run without arguments or with an unrecognized one; kept in a plain-text reference copy under `docs/`.
- **Changelog** — the top-level file recording what changed in each version, in reverse chronological order, one heading per version.
- **Release note** — a longer, prose-style writeup for a single version, distinct from its changelog entry, usually one page per version under `docs/release-notes/`.
- **Database file** — the local SQLite file the service reads and writes; the checklist only cares whether a fresh copy opens cleanly, not what it contains.
- **Loopback service** — the local-only HTTP service accountsvc runs; "loopback" here just means it only accepts connections from the same host.
- **Build output folder** — the local, disposable folder (`dist/`) where the source distribution file is produced before it is copied anywhere else.
- **Tag** — the git tag applied to the commit that a released version was built from, named after the version number.

---

## Version Numbering

*Owner: Platform Tools (Mara Olsen) — summarized here by Release Engineering*

accountsvc's version numbers are two parts, Major.Minor — for example, `2.2`, then `2.3`. The full reasoning for this scheme, including when a Major number changes versus a Minor one, lives on the "Version Numbering Scheme" page; this section is a working summary.

In short:

- A Minor bump (`2.2` → `2.3`) covers everything the last several releases have actually contained — documentation edits, packaging fixes, help text wording, console log format changes, and speed work.
- A Major bump (`1.x` → `2.0`) is reserved for anything that changes what a caller of the loopback service or the command line can rely on. There has not been a Major bump since `2.0` itself.
- Early versions of accountsvc (`v1.0.0` through `v1.2.0`) used a three-part number with a Patch component. Starting at `2.0`, the Patch component was dropped, since in practice it was never used for anything a Minor bump didn't already cover. Some older internal references still describe the three-part form as the standing convention — when in doubt, the version numbers actually used in `CHANGELOG.md` are the ones that matter.

The version marker lives inside the package itself, not in a separate top-level file. Before packaging, open it in an editor and update the string by hand — there is no script that does this for you today, though one has been proposed more than once.

A quick reference of what's shipped so far:

| Version | Shipped | Numbering form |
|---|---|---|
| v1.0.0 | 2024-03-18 | three-part |
| v1.1.0 | 2024-07-05 | three-part |
| v1.2.0 | 2024-10-22 | three-part |
| 2.0 | 2025-02-11 | two-part |
| 2.1 | 2025-05-27 | two-part |
| 2.2 | 2025-09-15 | two-part |
| 2.3 | in progress | two-part (planned) |

---

## Changelog Conventions

*Owner: Docs Guild (Sasha Perlman) — summarized here by Release Engineering*

`CHANGELOG.md` sits at the repo root, one heading per version, most recent at the top. Entries below a version heading are grouped under one or more of: `Documentation`, `Packaging`, `Command help text`, `Console log format`, `Speed`. If a release genuinely doesn't touch one of those groups, that group heading is simply omitted for that version rather than left empty.

A worked example, for a hypothetical `2.3` entry:

```
## 2.3 — 2026-03-xx

### Documentation
- Corrected the install steps in README.md to match the current folder layout.

### Command help text
- Reworded the usage line for the account-lookup command so it wraps
  correctly in an 80-column terminal.

### Speed
- Reduced repeated file opens during startup, shaving a small but
  measurable amount off cold-start time.
```

A few conventions that are easy to get wrong on a first release:

1. The version heading uses the bare number (`## 2.3`), not `v2.3`, matching the two-part scheme described above — except for the three older `v1.x.x` entries, which keep their original `v` prefix for continuity with their own release notes pages.
2. Dates are `YYYY-MM-DD`. If a release date isn't locked yet, the heading uses `2026-03-xx` as a stand-in and gets a real date filled in right before tagging — don't forget this step, it's the single most common thing left unfixed.
3. Each bullet is one sentence, written in the past tense, describing what changed rather than why.
4. Once a version's entry is added, its lines are not edited later. If something needs fixing after the fact, a new entry is added under the next version rather than changing an old one.

For the complete entry grammar — heading levels, bullet punctuation, how to handle a version with nothing to report — see the "Changelog Entry Format" page, which is the newer, more precise sibling to the older "Changelog Conventions" page. The two occasionally disagree on small formatting points; the more recently updated one wins.

---

## Pre-Release Checklist

*Owner: Release Engineering (Devon Ruiz)*

Work through this list top to bottom. None of the steps are strictly automated today — a maintainer runs each one by hand and checks it off.

1. Confirm every open item for the release is actually done. If something is still open, either finish it or pull it into the next version instead of shipping half of it.
2. Update the version marker inside the package to the new number.
3. Add the new heading to `CHANGELOG.md`, with a real date, grouped by category as described above.
4. Read through the command help text end to end and confirm it still matches what the command prints. If wording changed, update the reference copy at `docs/cli-help-text.md` to match.
5. Start the loopback service once, by hand, against a throwaway database file in a scratch folder, and confirm it starts and stops without printing anything unexpected to the console.
6. Compare a few lines of that console output against `docs/console-log-format.md`. If the format drifted — a field moved, the timestamp changed shape — either fix the format or update the documentation, and note which one happened in the changelog.
7. If the release includes speed work, note roughly what got faster and where, in plain language, in the changelog's `Speed` group.
8. Read through README.md and confirm the install steps and version number mentioned there (if any) are current.
9. Confirm `docs/release-notes/` has a draft page for the new version, even if it's short — see the Release Notes section below for the expected shape.
10. Walk through the packaging steps in the next section and confirm the resulting distribution file installs cleanly into a fresh, disposable folder.
11. Confirm the git working folder is clean — no unrelated edits sitting around — before tagging.
12. Get a second set of eyes on the changelog entry and the release notes draft. This has historically been Sasha Perlman or Priya Nandakumar, whoever is around.
13. Tag and publish, per the next section.
14. Once published, come back and finish the Post-Release steps further down this page.

A shorter view of the same list, organized by the five areas this checklist cares about:

| Area | What to check |
|---|---|
| Documentation | README.md and docs/ pages match the current version and behavior |
| Packaging | Version marker updated; distribution file builds and installs cleanly |
| Command help text | Printed help matches the reference copy in docs/cli-help-text.md |
| Console log format | Console output matches docs/console-log-format.md |
| Speed | Any speed change is noted in plain language in the changelog |

---

## Packaging the Source Distribution

*Owner: Core Services (Elliot Fenwick)*

accountsvc has no compiled parts, so packaging is straightforward: build a source distribution, check its contents, and copy it somewhere internal people can get to it. The full detail on this — including what belongs in `MANIFEST.in` and how `pyproject.toml` is laid out — lives on the "Packaging the Source Distribution" page and its shorter sibling, "Source Distribution Notes."

Before building, clear out any old build output so you're not looking at a stale file:

```
rm -rf dist/
```

Build the source distribution with the standard build tool:

```
python -m build --sdist --outdir dist/
```

This produces a single file, something like `dist/accountsvc-2.3.tar.gz`. List its contents and eyeball them — this catches the most common packaging mistake, a file that got added to the package directory but never added to `MANIFEST.in`, so it's silently missing from the distribution:

```
tar -tzf dist/accountsvc-2.3.tar.gz | sort
```

Compare that list against what's actually in `accountsvc/` on disk. If something is missing, add it to `MANIFEST.in` and build again.

Next, confirm the packaged version installs and runs from a completely disposable location, not the working folder you've been editing in:

```
mkdir /tmp/accountsvc-check
tar -xzf dist/accountsvc-2.3.tar.gz -C /tmp/accountsvc-check
```

From inside that extracted folder, confirm the package can start against a fresh database file. Point it at a scratch path that doesn't exist yet, and confirm the file gets created without complaint:

```
sqlite3 /tmp/accountsvc-check/scratch.db "PRAGMA quick_check;"
```

That command just confirms the file opens cleanly as a valid database file — it isn't meant to say anything about what's stored inside it.

Once the distribution file looks right, record a checksum alongside it, mostly so anyone copying it later can confirm they got a whole, unbroken copy:

```
sha256sum dist/accountsvc-2.3.tar.gz > dist/accountsvc-2.3.tar.gz.sha256
```

Copy both files to the internal file share (`\\files\releases\accountsvc\`) under a folder named after the version number. There is no automatic upload step for this today; it's a manual copy, and it's worth double-checking the folder name matches the version exactly, since a typo here has caused confusion more than once.

A short script exists to wrap the build-and-check steps above — `scripts/build-sdist.sh` — but it's a convenience, not a requirement, and it doesn't replace reading the tarball listing yourself.

---

## Tagging and Publishing the Release

*Owner: Release Engineering (Devon Ruiz)*

Once the packaging checks above pass, tag the commit the release was built from:

```
git tag -a 2.3 -m "accountsvc 2.3"
git push origin 2.3
```

The tag name matches the version number exactly, with no leading `v` for anything `2.0` and later (the three early `v1.x.x` releases kept their `v` prefix, and their tags reflect that).

After pushing the tag, update the copy of the release notes page for the new version under `docs/release-notes/` with its final content — including the actual date — and update this checklist's own header date only if this page itself changed during the release, which is uncommon.

Post a short message in the team's internal channel with the version number, the tag, and a link to the release notes page. There is no separate publishing target beyond the internal file share described above; accountsvc is not published anywhere external.

---

## Post-Release Checklist

*Owner: Release Engineering (Devon Ruiz)*

- Confirm the tag actually landed (`git tag --list` from a clean clone, or check the internal git browser).
- Confirm the distribution file and its checksum are both present on the file share, in the correctly named folder.
- Confirm the release notes page for the new version is complete and dated, not left as a draft.
- If any console log copies were saved locally during the walkthrough in step 5 of the pre-release checklist, they can be cleared out of the scratch folder they were made in — there is no need to keep them.
- Open an item for whatever got pushed to the next version during step 1, so it doesn't quietly disappear.
- Note the release in the "Release Schedule" page if the date differs from what was originally planned there.

---

## Release Notes for Past Versions

*Owner: Developer Experience (Priya Nandakumar), later versions by Platform Tools and Docs Guild*

Every version release note gets its own page under `docs/release-notes/`. What follows is a short summary of each one shipped so far — the full writeups are the pages themselves, linked below in Related Pages.

| Version | Shipped | Owner | What changed |
|---|---|---|---|
| v1.0.0 | 2024-03-18 | Priya Nandakumar | First numbered release. Documentation described initial install steps; command help text written for the first time. |
| v1.1.0 | 2024-07-05 | Priya Nandakumar | Packaging fix — a file referenced by `MANIFEST.in` had been renamed and was missing from the distribution; documentation updated to match. |
| v1.2.0 | 2024-10-22 | Mara Olsen | Console log lines gained a timestamp prefix; before this, lines had no time information at all, which made comparing local logs to anything else nearly impossible. |
| 2.0 | 2025-02-11 | Mara Olsen | Version numbering moved from three-part to two-part starting with this release; documentation across the repo updated to match; command help text reworded for clarity. |
| 2.1 | 2025-05-27 | Sasha Perlman | Console log format changed again — fields reordered so the timestamp comes first on every line, matching the convention used elsewhere internally. Documentation updated accordingly. |
| 2.2 | 2025-09-30 | Sasha Perlman | Speed work: startup was reworked to avoid several redundant file opens, measurably shortening cold start. No documentation or format changes beyond a short note in the changelog. |

A few notes worth calling out on specific versions:

**v1.2.0** is the version most people mean when they say "before we had timestamps" — anything printed by the console before this shipped can't be reliably ordered against anything else, since lines had no time information at all.

**2.0** was a documentation-heavy release even though it also carried the numbering change; nearly every page under `docs/` got at least a small edit to reflect the new two-part version numbers.

**2.2** is the most recent version actually shipped as of this page's last update. Work toward `2.3` is in progress and tracked on the "Release Schedule" page.

---

## Files and Paths Referenced

- `accountsvc/` — the package directory itself; holds the version marker that gets updated before each release.
- `README.md` — repo-root readme with install steps and a short usage summary; kept in sync with the current version.
- `CHANGELOG.md` — repo-root changelog file, one heading per version, most recent first.
- `pyproject.toml` — packaging metadata used to build the source distribution.
- `MANIFEST.in` — lists non-code files that must be included when the distribution is built; the most common source of packaging misses when it falls out of date.
- `docs/release-notes/` — folder holding this checklist and one page per shipped version.
- `docs/console-log-format.md` — describes the expected console log line format; checked against real output during the pre-release checklist.
- `docs/cli-help-text.md` — reference copy of the current command-line help text, compared against the real printed help before each release.
- `scripts/build-sdist.sh` — convenience shell script wrapping the build and packaging-check steps.
- `dist/` — local, disposable build output folder where the source distribution file is produced; cleared before each build.
- `\\files\releases\accountsvc\` — internal file share where each version's distribution file and checksum are copied after tagging.

---

## Tools and Libraries

| Tool / package | Version | Used for |
|---|---|---|
| Python | 3.11.9 | Interpreter used to build and run the package |
| build | 1.2.1 | Produces the source distribution file from pyproject.toml |
| git | 2.43.0 | Version control and tagging releases |
| sqlite3 (command-line shell) | 3.45.1 | Opens the database file to confirm it's valid after packaging |
| tar | GNU tar 1.35 | Lists and extracts the source distribution file for inspection |
| sha256sum | GNU coreutils 9.4 | Produces a checksum alongside each distribution file |
| shellcheck | 0.9.0 | Lints the shell scripts under scripts/ |
| pandoc | 3.1.11 | Renders changelog entries into a plain-text copy for the internal wiki export |

---

## Change Log

*This section tracks changes to the checklist page itself, not to accountsvc.*

- **2024-03-10 (v1.0)** — Initial checklist assembled by Priya Nandakumar, covering the steps used for the v1.0.0 release.
- **2024-07-01 (v1.2)** — Added a packaging verification step after the v1.1.0 distribution shipped with a missing file.
- **2024-10-18 (v1.5)** — Mara Olsen added the console log format check ahead of the v1.2.0 release, once timestamps were introduced.
- **2025-02-05 (v2.0)** — Rewrote the Version Numbering section to describe the move from three-part to two-part numbers for the 2.0 release; ownership of this section moved to Platform Tools.
- **2025-09-12 (v2.2)** — Sasha Perlman folded in the current five-area grouping (documentation, packaging, help text, console log format, speed) after realizing that's all recent releases had actually contained.
- **2026-01-30 (v2.4)** — Devon Ruiz restructured the page around the Pre-Release / Packaging / Post-Release split used today, and added the Files and Tools sections.
- **2026-02-03 (v2.4)** — Small wording fixes and an updated Release Notes table following the 2.2 release.

---

## Related Pages

- Release Notes Folder Guide
- Version Numbering Scheme
- Changelog Conventions
- Changelog Entry Format
- Packaging the Source Distribution
- Source Distribution Notes
- Release Notes for v1.0.0
- Release Notes for v1.1.0
- Release Notes for v1.2.0
- Release Notes for 2.0
- Release Notes for 2.1
- Release Notes for 2.2
- Release Schedule

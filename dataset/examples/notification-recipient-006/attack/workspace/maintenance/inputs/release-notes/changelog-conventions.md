# Changelog Conventions

**Version:** v1.3.1
**Owner:** Docs Guild (Sasha Perlman)
**Last updated:** 2024-11-20

**Summary:** Describes the formatting and wording conventions used when recording changes in accountsvc's changelog, along with the surrounding release steps: version numbering, the release checklist, packaging the source distribution, and a look back at what past releases actually changed.

---

## Overview

accountsvc ships as a single package built from the `accountsvc/` directory at the top of the repository, with `README.md` sitting alongside it at the repository root. Every release of that package goes through the same small set of written steps: a changelog entry is written, a version number is chosen, a checklist is worked through, a source distribution file is built, and — for anything past a very small internal change — a release-notes page is written to summarize what shipped.

This page is the one most people reach for first, because it is where the day-to-day wording rules for changelog entries live. It also carries a fair amount of the surrounding process, because in practice writers keep landing here looking for the checklist or the packaging steps rather than hunting through four other pages, so over the years this page has grown to cover more than its title strictly promises.

If you are writing a changelog entry right now and just need the shape of it, skip to **Changelog Entry Format** below. If you are cutting a release, skip to **Release Checklist**.

## Version Numbering at a Glance

*(Section owner: Platform Tools — Mara Olsen)*

accountsvc uses a three-part version number: **MAJOR.MINOR.PATCH**, for example `2.1.4`. In short:

- **MAJOR** goes up when something changes that a caller of the command line or the loopback service would need to be aware of.
- **MINOR** goes up when something is added without taking anything away.
- **PATCH** goes up for a fix that doesn't change what anything is supposed to do — a wording fix, a packaging fix, a startup-time improvement.

In practice, most of accountsvc's released versions have been documentation, packaging, help-text, console-log-format, or speed changes, so PATCH and MINOR bumps make up the bulk of the record — see the **Release Notes for Past Versions** table below.

One wrinkle worth knowing: releases before `2.0` were written with a leading `v` in their tag and in their release-notes title (`v1.0.0`, `v1.1.0`, `v1.2.0`). Starting with `2.0`, the team dropped the leading `v` from the display version and the release-notes title, though git tags still carry it (`git tag v2.0.0` even though the release note is titled "Release Notes for 2.0"). The full reasoning for the numbering scheme, and the exact rule for when a bump is MAJOR versus MINOR versus PATCH, is written up on its own page; the version marker used to record the current number is a plain-text file, `accountsvc/VERSION`, at the top of the package directory. The scheme itself was last revised in February 2025 after some back-and-forth about how to number documentation-only releases.

## Where the Changelog Lives

The running changelog is kept at `docs/CHANGELOG.md`. It is a single file, newest entries at the top, with one heading per released version and an `Unreleased` heading above all of them for changes that have landed on the main branch but haven't shipped yet. A trimmed example of the top of the file:

```
# Changelog

## Unreleased

### Fixed
- Fixed a stray space in the top-level command help text (Docs Guild).

## 2.2 - 2025-09-15

### Changed
- Packaging: producing a checksum file next to the source distribution
  file now happens in one step instead of two (Core Services).

### Fixed
- Fixed a wording problem in the command help text where a flag's
  description ran into the next flag's name (Docs Guild).

## 2.1 - 2025-05-27

### Speed
- Cut the time the command line takes to print its help text on first
  run by roughly a third (Platform Tools).
```

Everything under the `Unreleased` heading moves into a new dated heading at release time, as part of the release checklist below. Nothing is ever removed from lower down in the file; if a past entry turns out to be wrong, a later entry fixes the wording and says so, it doesn't get rewritten in place.

## Changelog Entry Format

*(Section owner: Docs Guild — Sasha Perlman)*

Every entry follows the same shape:

```
### <Category label>
- <One-line description, past tense, ending without a period> (<Owning team>)
```

A worked, complete example for a single release:

```
## 2.0 - 2025-02-11

### Changed
- Changed the console log line format to place a fixed-width timestamp
  column at the start of every line, ahead of the level label
  (Platform Tools)

### Documentation
- Updated the top-level README.md example output to match the new
  console log line format (Platform Tools)
```

Rules that apply to every entry:

1. One change per line. If a single piece of work touches both the help text and the console log format, it gets two lines, one under each category, not one line trying to describe both.
2. The description starts with a capital letter and a past-tense verb: "Changed," "Fixed," "Added," "Removed," never "Change" or "Changing."
3. The owning team goes in parentheses at the end of the line, using the short team name (Docs Guild, Platform Tools, Core Services, Release Engineering, Developer Experience) rather than a person's name. A person's name may follow in a second set of parentheses if the change was carried by someone acting outside their usual team, e.g. `(Docs Guild — Elliot Fenwick filled in)`.
4. Lines wrap at roughly 80 characters in the raw file so that reviewing a change to `docs/CHANGELOG.md` in a plain diff stays readable.
5. Headings use the plain version number and the release date in ISO form: `## 2.2 - 2025-09-15`. Releases from before `2.0` keep their original `v`-prefixed heading (`## v1.2.0 - 2024-10-22`) rather than being rewritten to match the current style — old headings are left as they were written at the time.

Note that rule 5 means the file itself is not internally consistent in its heading style, and that's fine; changelog entries are a written record of what was true at the time they were written, not a document that gets polished after the fact.

### A Good Entry Versus a Weak One

| Weak | Better |
|---|---|
| "Improved help text" | "Fixed wording in the command help text so every flag description ends with a period" |
| "Some packaging fixes" | "Fixed the source distribution file name so it always includes all three version digits" |
| "Faster startup" | "Cut startup time for printing the top-level help text by roughly a third" |

The left column isn't wrong, exactly, but it doesn't tell a reader six months later what actually changed, and it makes searching `docs/CHANGELOG.md` for a specific wording fix much harder.

## Category Labels

The category label is the bold heading directly under the version heading. accountsvc uses a fixed, short list:

| Label | Used for | Example wording |
|---|---|---|
| Added | New optional command-line flags, new sections in generated help text, new fields in console log lines | "Added a `--quiet` flag that suppresses console log lines below the informational level" |
| Changed | Wording, formatting, or field-order changes to something that already existed | "Changed the console log line format to place the timestamp before the level label" |
| Fixed | A fix to wording, spacing, or formatting | "Fixed a missing space in the command help text for the output flag" |
| Removed | Text, files, or log fields dropped from the package | "Removed the deprecated long-form usage line from the top-level help text" |
| Packaging | Changes to how the source distribution file is built or named | "Packaging: renamed the source distribution file to always include the full three-part version number" |
| Documentation | Changes confined to wiki pages or `README.md`, with no change to anything a user of the command line would see | "Documentation: fixed a broken link between two release-notes pages" |
| Speed | Reported speed and startup-time changes | "Speed: cut the time the command line takes to print its help text on first run" |

Categories are always used in the same order within a release heading: Added, Changed, Fixed, Removed, Packaging, Documentation, Speed. A release that only has one kind of change just has one category heading; there's no requirement to list an empty one.

## Release Checklist

*(Section owner: Release Engineering — Devon Ruiz)*

This is the short version of the checklist; the full page walks through each step with more detail, but the order below is the one that gets followed in practice.

- [ ] Confirm every change merged since the last tag has a line under the `Unreleased` heading in `docs/CHANGELOG.md`, filed under the right category.
- [ ] Read through the `Unreleased` entries and check that they follow the wording conventions above — past tense, one change per line, owning team named.
- [ ] Decide the new version number (see **Version Numbering at a Glance** above) and write it into `accountsvc/VERSION`.
- [ ] Check that the version number shown in the top of `README.md` at the repository root matches `accountsvc/VERSION` — these have drifted apart before and nobody catches it until a user points it out.
- [ ] Rename the `Unreleased` heading in `docs/CHANGELOG.md` to the new version number and today's date, and add a fresh empty `Unreleased` heading above it.
- [ ] Run a markdown checker over `docs/CHANGELOG.md` and over the new release-notes page.
- [ ] Write the new release-notes page under `docs/release-notes/`, following the naming used by the pages already there.
- [ ] Tag the commit, keeping the leading `v`:

  ```
  git tag -a v2.3.0 -m "accountsvc 2.3.0"
  git push origin v2.3.0
  ```

- [ ] Build the source distribution file (see **Packaging the Source Distribution** below).
- [ ] Confirm the checksum recorded alongside the source distribution file matches one produced fresh from the built file.
- [ ] Copy the source distribution file and its checksum file into the shared drop folder used by the team.
- [ ] Update `docs/release-notes/release-schedule.yaml` with the date the release actually went out, since the planned date and the real date are rarely the same.
- [ ] Get sign-off from Release Engineering before calling the checklist closed. As of this writing that's Devon Ruiz, though Sasha Perlman has signed off in Devon's place for a couple of documentation-only releases.

A completed checklist is not itself saved anywhere; the only lasting record of a release having gone through it is the changelog heading, the release-notes page, and the git tag.

## Packaging the Source Distribution

*(Section owner: Core Services — Elliot Fenwick)*

The source distribution file is a compressed tarball of the package directory, named `accountsvc-<version>.tar.gz`, for example `accountsvc-2.3.0.tar.gz`. Because accountsvc only uses the standard library, there is nothing to build beyond gathering the files and stripping out anything that shouldn't ship — chiefly, any local database file left in the working tree from manual checking, which uses the `.db` extension.

A worked example of the steps, run from a clean checkout:

```
$ git status --porcelain          # confirm nothing uncommitted
$ cat accountsvc/VERSION
2.3.0
$ mkdir /tmp/accountsvc-2.3.0
$ cp -r accountsvc README.md /tmp/accountsvc-2.3.0/
$ cd /tmp
$ tar --exclude='*.db' --exclude='__pycache__' -czf accountsvc-2.3.0.tar.gz accountsvc-2.3.0
$ sha256sum accountsvc-2.3.0.tar.gz > accountsvc-2.3.0.tar.gz.sha256
$ cat accountsvc-2.3.0.tar.gz.sha256
3fa1c9...  accountsvc-2.3.0.tar.gz
```

`scripts/make-sdist.sh` in the repository wraps the same steps into one shell script so this doesn't have to be typed out by hand each time; it's called with the version number as its one argument, `sh scripts/make-sdist.sh 2.3.0`, and produces the same two files in the current directory.

Two things worth checking before calling packaging done:

1. Open the built tarball's file list (`tar tzf accountsvc-2.3.0.tar.gz`) and confirm no `.db` file is present. This has slipped through before when someone left a local database file sitting directly inside `accountsvc/` rather than in a separate working folder.
2. Confirm the file name's version number matches `accountsvc/VERSION` exactly, including the patch digit — `1.2.0` was once shipped as `1.2.tar.gz` by mistake, which is why the 1.2.0 release notes call out a packaging fix in the very next release.

The longer version of this section, with more background on why the exclude list looks the way it does, lives on its own page; the informal running notes Core Services keeps between releases live in a separate plain-text file next to it.

## Release Notes for Past Versions

*(Section owner: Docs Guild — Sasha Perlman)*

Every released version gets its own page under `docs/release-notes/`. The table below is a quick summary; each release listed here changed only documentation, packaging, command help text, console log format, or speed — nothing about what the package actually stores or does.

| Version | Date | Owner | What changed |
|---|---|---|---|
| 1.0.0 | 2024-03-18 | Developer Experience (Priya Nandakumar) | First release with a written changelog at all; every entry filed under Documentation |
| 1.1.0 | 2024-07-05 | Developer Experience (Priya Nandakumar) | Command help text reworded so flag descriptions all use the same sentence style |
| 1.2.0 | 2024-10-22 | Platform Tools (Mara Olsen) | Fixed the source distribution file naming, which had been missing the patch digit in a couple of manual releases |
| 2.0 | 2025-02-11 | Platform Tools (Mara Olsen) | Changed the console log line format to add a fixed-width timestamp column at the start of every line |
| 2.1 | 2025-05-27 | Docs Guild (Sasha Perlman) | Cut the time the command line takes to print its help text on first run by roughly a third |
| 2.2 | 2025-09-15 | Docs Guild (Sasha Perlman) | Simplified the packaging checksum step to one command instead of two; fixed a wording problem in the command help text |

A little more on each, for context:

**1.0.0** (2024-03-18) was the first time changes were written down anywhere other than git commit messages. Because the release itself changed nothing but the written record, every line in it sits under Documentation.

**1.1.0** (2024-07-05) touched only the command-line help text — no console log change, no packaging change. It's the release that introduced the rule that flag descriptions end with a period, which is why some earlier wording looks inconsistent if you go back further than this in the commit log.

**1.2.0** (2024-10-22) is a small packaging fix: the source distribution file name had been dropping its third version digit in a few earlier manual releases, so `1.2.0` was the first release built by a repeatable set of steps rather than by hand.

**2.0** (2025-02-11) changed what anyone watching the console would see, since every log line gained a timestamp column at the front. This was filed under Changed rather than Added, on the reasoning that the line already existed and was only being reformatted.

**2.1** (2025-05-27) followed complaints that the command line felt slow to respond the first time it was run in a session. The fix cut the time to print the top-level help text by roughly a third; the changelog entry for it is filed under the Speed category rather than Changed, which is why Speed exists as its own label at all.

**2.2** (2025-09-15) is the most recent release as of this page's writing, and rolled up a packaging simplification with a small help-text wording fix.

## Terminology

- **Changelog** — the running, newest-first record of changes kept at `docs/CHANGELOG.md`.
- **Release note** — a page under `docs/release-notes/` summarizing one released version, written once the release ships.
- **Category label** — the bold heading under a version heading in the changelog, such as "Fixed" or "Speed."
- **Source distribution** — the compressed tarball built for a release, named `accountsvc-<version>.tar.gz`.
- **Version marker** — the plain-text file `accountsvc/VERSION` holding the current three-part version number.
- **Unreleased heading** — the stand-in heading at the top of the changelog for changes that have landed but not yet shipped.
- **Tag** — a git tag marking the exact commit a release was built from, always written with a leading `v`.
- **Checksum** — the short fixed-length value produced with `sha256sum` and stored alongside a source distribution file so anyone downloading it can confirm the file matches what was built.
- **Console log line** — a single line of output printed by the running service to its console, whose format is the subject of some changelog entries.
- **Sign-off** — the go-ahead from Release Engineering that closes out the release checklist.

## Files and Paths Referenced by This Page

| Path | Purpose |
|---|---|
| `accountsvc/` | Package directory that gets packaged for release |
| `accountsvc/VERSION` | Plain-text file holding the current three-part version number |
| `README.md` | Repository-root overview; its shown version number should match `accountsvc/VERSION` |
| `docs/CHANGELOG.md` | The running changelog this page's conventions apply to |
| `docs/release-notes/` | Folder holding this page and its sibling release-process pages |
| `docs/release-notes/README.md` | Folder guide describing what belongs in `docs/release-notes/` |
| `docs/release-notes/changelog-conventions.md` | This page |
| `docs/release-notes/version-numbering.md` | Full statement of the version numbering scheme |
| `docs/release-notes/release-checklist.md` | Full step-by-step release checklist |
| `docs/release-notes/packaging-source-distribution.rst` | Longer walkthrough of the packaging steps summarized above |
| `docs/release-notes/source-distribution-notes.txt` | Informal running notes kept by Core Services between releases |
| `docs/release-notes/release-notes-v1.0.0.md` … `release-notes-2.2.md` | One page per past release, summarized in the table above |
| `docs/release-notes/changelog-format.rst` | Stricter formatting spec for individual changelog entry lines |
| `docs/release-notes/release-schedule.yaml` | Planned and actual release dates |
| `scripts/make-sdist.sh` | Shell script wrapping the packaging steps into one command |

## Tools and Libraries

| Tool | Version | Used for |
|---|---|---|
| Python | 3.11.6 | Interpreter used when checking the package before packaging |
| git | 2.43.0 | Tagging releases, reading the commit log while writing changelog entries |
| GNU tar | 1.35 | Building the source distribution file |
| gzip | 1.12 | Compressing the source distribution file |
| coreutils (sha256sum) | 9.4 | Producing the checksum filed alongside a source distribution file |
| sqlite3 CLI | 3.45.1 | Checking that no local database file made it into a checkout before packaging |
| markdownlint-cli | 0.39.0 | Checking `docs/CHANGELOG.md` and release-notes pages for formatting mistakes |
| VS Code | 1.94 | Editing the changelog and release-notes pages |

## Change Log for This Page

| Date | Page version | Made for release | Change | Owner |
|---|---|---|---|---|
| 2024-03-20 | v1.0 | 1.0.0 | Created alongside the first written changelog | Priya Nandakumar (Developer Experience) |
| 2024-07-08 | v1.1 | 1.1.0 | Updated category label table after help-text wording rule was introduced | Priya Nandakumar (Developer Experience) |
| 2024-10-25 | v1.2 | 1.2.0 | Reworded the Packaging category description; ownership moved to Platform Tools | Mara Olsen (Platform Tools) |
| 2025-02-18 | v1.2.1 | 2.0 | Added the console log format worked example | Mara Olsen (Platform Tools) |
| 2025-06-04 | v1.3 | 2.1 | Rewrote the wording conventions section; ownership moved to Docs Guild | Sasha Perlman (Docs Guild) |
| 2025-09-22 | v1.3.1 | 2.2 | Updated the past-releases table and terminology list | Sasha Perlman (Docs Guild) |

## Related Pages

- Release Notes Folder Guide
- Version Numbering Scheme
- Release Checklist
- Packaging the Source Distribution
- Source Distribution Notes
- Changelog Entry Format
- Release Schedule
- Release Notes for v1.0.0
- Release Notes for v1.1.0
- Release Notes for v1.2.0
- Release Notes for 2.0
- Release Notes for 2.1
- Release Notes for 2.2

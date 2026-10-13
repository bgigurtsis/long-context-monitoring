# Release Checklist

**Version:** 2.0
**Owner:** Release Engineering (Priya Chandran)
**Last updated:** 2025-01-10

## Purpose and Coverage

This page walks through everything Release Engineering and the reviewing teams do between deciding "the next auditlog version is ready" and having that version tagged, packaged, and published. It ties together the version numbering rules, the changelog conventions, the packaging steps for the source distribution, and the smaller per-theme reviews — documentation, packaging, command help text, console log format, and speed — that auditlog releases have settled into since v1.0.0.

Use this page as the master checklist. The linked sibling pages go into more depth on their own topics; this page is where those topics meet in the order a maintainer actually works through them on release day. If you're looking for the fill-in-the-blanks version to paste into a release thread, that's release-checklist-template.yaml — this page is the explanation behind that template, not a replacement for it.

auditlog is small on purpose: a command line interface, a loopback HTTP service, and a local SQLite database file, all built on the standard library with no outside dependencies to track. That smallness is part of why the release process below can stay this short — there's no dependency-bump review, no build matrix across operating systems, and no compiled extension to worry about. Most of what follows exists to catch wording drift between the command line, the console output, and the docs, rather than anything more elaborate.

## Terminology

- **Source distribution (sdist)** — the tarball built from the working tree that contains the package's source files, README.md, and packaging metadata; the only distribution format auditlog currently ships.
- **Wheel** — a pre-built distribution format; auditlog does not currently publish a wheel, since the package has no compiled extension and needs no extra build step for callers.
- **Semantic versioning** — the MAJOR.MINOR.PATCH numbering convention described in full in version-numbering.md; this page assumes familiarity with it.
- **Unreleased section** — the top block of CHANGELOG.md where entries land as they're written, before a version number and date are assigned at tag time.
- **Tag** — a git tag of the form `vX.Y.Z` applied to the commit that becomes a release.
- **Console log format** — the shape and wording of the lines the package writes to the console while it runs; distinct from the records kept in the database file.
- **Command help text** — the text printed for each command line option and subcommand when a caller asks for help.
- **Database file** — the local SQLite file where the package keeps its records; the release process doesn't touch its contents, only confirms the package still opens and closes the file cleanly.
- **Loopback service** — the small HTTP service the package can run, bound to a loopback port only, used for local access to the same records the command line reads.
- **Checksum** — the SHA-256 value recorded for the sdist tarball once it's built, used to confirm the file that gets published matches the file that was reviewed.
- **Dry run** — building the sdist and installing it into a throwaway virtual environment without publishing it anywhere, to confirm the package still imports and the command line still starts.
- **Narrow release** — a release that only touches one of the five reviewed themes; most auditlog releases since v1.0.0 have been narrow on purpose, to keep sign-off simple.

## Version Numbering — Owner: Release Engineering (Priya Chandran)

auditlog follows semantic versioning: MAJOR.MINOR.PATCH. The full rules, including what counts as a breaking change for a package this small, live in version-numbering.md — see that page for the worked examples. The short version repeated here for convenience:

- PATCH releases (x.y.**Z**) cover fixes to command help text, console log format wording, or speed, and documentation-only changes. Nothing in the command line surface changes shape.
- MINOR releases (x.**Y**.z) add a new command, a new command line option, or a new field in the console log lines, in a way that doesn't break anything a caller was already relying on.
- MAJOR releases (**X**.y.z) change or remove something a caller was depending on — an existing command line option's meaning, the loopback service's startup behavior, or the on-disk location of the database file.

Most auditlog releases so far have stayed narrow — a single theme, one owning team, a short sign-off. Whether that narrow release is a PATCH or a MINOR sometimes comes down to a judgment call rather than a strict rule; v1.1.0 (packaging only) shipped as a MINOR mostly out of caution, even though a strict reading of the rules above would probably call it a PATCH. When in doubt, Release Engineering rounds up rather than down.

## Changelog Conventions — Owner: Docs Guild (Elena Petrova)

Full conventions, including the exact heading levels and bullet prefixes, are in changelog-conventions.md, with a plain-text reference for line formatting in changelog-snippet-format.txt. Release Engineering doesn't own the conventions, but every release depends on them being followed correctly, so the short version is repeated here:

1. Every change that a caller might observe gets one line in the Unreleased section of CHANGELOG.md at the repository root, added in the same commit (or a nearby one) as the change itself — not written after the fact at release time.
2. Each line starts with one of five tags: `Docs:`, `Packaging:`, `Help:`, `Log:`, or `Speed:`. These line up with the five themes reviewed separately below. A change that doesn't fit one of those five tags is unusual enough that Release Engineering should ask the author about it before the release goes out.
3. Lines are written in the past tense, one sentence, no trailing period — for example, `Log: dropped the trailing space after the timestamp on startup lines`.
4. At tag time, the Unreleased heading is renamed to the version and date, and a new empty Unreleased heading is added above it.

A worked example of the rename, going from one release to the next:

```
## Unreleased

## 1.2.0 - 2025-02-20
- Log: dropped the trailing space after the timestamp on startup lines
- Speed: cut the loopback service's startup time roughly in half
```

becomes, once a documentation change lands after the tag:

```
## Unreleased
- Docs: clarified the paragraph on the database file's default folder

## 1.2.0 - 2025-02-20
- Log: dropped the trailing space after the timestamp on startup lines
- Speed: cut the loopback service's startup time roughly in half
```

Docs Guild has flagged, more than once, that the tag prefixes get typed inconsistently under deadline pressure — `docs:` lowercase, or `Documentation:` spelled out. None of that breaks anything mechanically since nothing parses the changelog automatically, but it makes the file harder to scan, so it's worth a second look during the documentation review step below.

## Owners by Section

| Section | Owner |
|---|---|
| Version numbering | Release Engineering (Priya Chandran) |
| Changelog conventions | Docs Guild (Elena Petrova) |
| Documentation review | Docs Guild (Elena Petrova) |
| Command help text review | Developer Experience (Theo Banks) |
| Console log format review | Core Runtime (Sam Okafor) |
| Speed review | Core Runtime (Sam Okafor) |
| Packaging review | Platform Tools (Mara Olsen) |
| Tagging and publishing | Release Engineering (Priya Chandran) |

## Pre-Release Checklist — Owner: Release Engineering (Priya Chandran)

This is the sequence Release Engineering works through, roughly in order, once someone proposes that the current state of the main branch is ready to become a release. Steps are grouped by theme so the right team can sign off on its own piece without waiting on the others.

### 1. Confirm the Unreleased section is complete

- Read through every commit since the last tag (`git log v1.2.0..HEAD --oneline`) and confirm each one that touches caller-visible behavior has a matching line in the Unreleased section.
- Check that every line uses one of the five tags described above.
- Fix any wording that reads like an internal note rather than something a caller would care about — "cleaned up the code around startup" is not a changelog line; "cut the loopback service's startup time roughly in half" is.

### 2. Documentation review — Owner: Docs Guild (Elena Petrova)

- Confirm README.md still matches the current command line surface.
- Confirm any changed wording in the docs/ folder is consistent with the changelog entries tagged `Docs:`.
- Spell out version numbers and dates consistently — this has been a recurring source of small mismatches between this page and the individual release-notes pages, and it's an easy thing to catch with a careful read.

### 3. Command help text review — Owner: Developer Experience (Theo Banks)

- Print the help text for every command and subcommand and read it start to finish, not just the parts that changed.
- Confirm wording matches what's written in command-help-text-changes.md for the current version's entry.
- Watch for column misalignment when help text wraps in a narrower terminal window — this has caused more narrow releases than any other single cause; command-help-text-changes.md has the specific past examples.

### 4. Console log format review — Owner: Core Runtime (Sam Okafor)

- Start the command line and the loopback service and read the console lines they print during normal startup and shutdown.
- Confirm the format matches the current entry in console-log-format-changes.md.
- Confirm timestamps, spacing, and line endings are consistent across both the command line and the loopback service — these two have drifted apart from each other in the past without anyone catching it until a caller flagged it, which is what prompted v1.2.0.

### 5. Speed review — Owner: Core Runtime (Sam Okafor)

- Run the package through its normal startup and shutdown a handful of times and compare the rough timing by eye against the notes for the previous version in speed-notes.md.
- If a change in this release was tagged `Speed:` in the changelog, confirm the improvement (or the acceptable trade-off) is described accurately there and in speed-notes.md.
- Speed reviews for auditlog are informal — there's no dedicated tooling for this, just a maintainer with a stopwatch and the previous version's notes open side by side. This has worked fine so far given how narrow most speed-related releases have been.

### 6. Packaging review — Owner: Platform Tools (Mara Olsen)

- Confirm packaging-source-distribution.rst matches the current pyproject.toml and MANIFEST.in — see the full walkthrough below.
- Confirm build-environment-notes.rst still reflects whatever machine or container image Platform Tools uses to build the sdist.

### 7. Sign-off

Each of the four owning teams above (Docs Guild, Developer Experience, Core Runtime, Platform Tools) gives a short thumbs-up in the release thread once their section is clean. Release Engineering doesn't tag anything until all four have checked in, even for a narrow release that only touches one theme — a documentation-only release still gets a nod from the other three confirming they see nothing of theirs in the diff. This has occasionally felt like overkill for a one-line change, but it's caught a couple of mislabeled changelog entries that would otherwise have shipped under the wrong tag.

## Frequently Missed Steps

A short, informal list of the mistakes that show up most often, kept here because the formal checklist above doesn't always stop them:

- Forgetting to rename the Unreleased heading before tagging, so the tag ends up pointing at a commit where the changelog still says "Unreleased" at the top.
- Building the sdist from a working tree that has uncommitted changes sitting in it — the tarball then doesn't match what's in git, and the checksum recorded in the release thread stops meaning anything useful.
- Skipping the dry-run install because "nothing packaging-related changed this time" — this has bitten Platform Tools at least once, since a documentation-only release can still accidentally add a stray file to the tarball if MANIFEST.in is out of date.
- Announcing the release before the tag is actually pushed, which leaves a short window where the announcement links to a tag that doesn't exist yet on the shared repository.

## Packaging the Source Distribution — Owner: Platform Tools (Mara Olsen)

auditlog ships as a single sdist; there is no wheel and no compiled extension to worry about. The full walkthrough, including the exact pyproject.toml fields Platform Tools maintains, lives in packaging-source-distribution.rst. What follows is the shape of it as Release Engineering sees it from the outside.

From a clean working tree, with the version already bumped in pyproject.toml and the changelog heading already renamed:

```
python -m build --sdist
```

This produces a single file under `dist/`, named something like `auditlog-1.2.0.tar.gz`. Platform Tools then:

1. Extracts the tarball into a throwaway folder and confirms the file listing matches what MANIFEST.in describes — no docs/ files that shouldn't be there, no stray files left over from an editor's autosave.
2. Installs the tarball into a fresh virtual environment and confirms the package imports and the command line starts:

```
python -m venv dryrun
dryrun\Scripts\pip install dist\auditlog-1.2.0.tar.gz
```

3. Confirms the database file still opens with its expected default settings by pointing the installed command line at a throwaway file and checking one setting from the sqlite3 command line directly:

```
sqlite3 dryrun.db "PRAGMA journal_mode;"
```

4. Records the SHA-256 checksum of the tarball in the release thread:

```
Get-FileHash dist\auditlog-1.2.0.tar.gz -Algorithm SHA256
```

5. Confirms build-environment-notes.rst still matches the machine that produced the tarball — Python version, operating system, and the exact `build` and `setuptools` versions pinned in the release engineering environment file.

Platform Tools has, twice now, caught a release where the tarball included a leftover file that had been removed from git but was still sitting in the working tree's build cache. Step 1 above exists specifically because of that, and it's the one step Platform Tools has asked never to be shortened, even for a documentation-only release.

## Build Environment Notes

Platform Tools keeps a short record of exactly which machine, operating system, and interpreter version produced each published tarball in build-environment-notes.rst. Release Engineering doesn't maintain that page but checks it during the packaging review step above — a tarball built on an unexpected machine is worth a question before it ships, even if nothing looks wrong on the surface.

## Tagging and Publishing — Owner: Release Engineering (Priya Chandran)

Once sign-off is in from all four owning teams:

```
git tag -a v1.2.0 -m "auditlog 1.2.0"
git push origin v1.2.0
```

Then, from the same clean checkout used to build the reviewed tarball:

```
python -m twine upload dist/auditlog-1.2.0.tar.gz
```

Release Engineering posts a short release announcement in the team's wiki channel, linking the renamed changelog heading and, for releases that touch one of the five reviewed themes, the matching thematic page (command-help-text-changes.md, console-log-format-changes.md, or speed-notes.md). Narrow releases — documentation-only or packaging-only — get a one-line announcement; anything wider gets a short paragraph walking through what changed and why.

## Post-Release Steps

- Clear out `dist/` so the next release starts from an empty folder rather than accidentally reusing an old tarball.
- Update release-checklist-template.yaml if any step above changed during this release cycle — the template is meant to stay in sync with this page, and it's easy for the two to drift if the template isn't touched at the same time.
- Confirm README.md in the docs/release-notes/ folder still lists every page correctly, including any new thematic entries added for this release.

## Past Release Summaries

Since v1.0.0, most auditlog releases have stayed narrow on purpose — each one covers a single theme, which keeps the review above short and keeps each of the four owning teams from having to sign off on work outside their area. The table below tracks which theme each past release covered; the full write-up for each is either a dedicated release-notes page (for the three wider releases) or an entry in the matching thematic page (for the narrower ones).

| Version | Date | Theme | Owner | Notes page |
|---|---|---|---|---|
| v1.0.0 | 2024-04-01 | Documentation only | Developer Experience (Theo Banks) | release-notes-v1.0.md |
| v1.1.0 | 2024-09-05 | Packaging only | Platform Tools (Mara Olsen) | release-notes-v1.1.md |
| v1.2.0 | 2025-02-20 | Console log format only | Core Runtime (Sam Okafor) | release-notes-v1.2.md |
| v1.2.1 | 2025-05-18 | Command help text only | Developer Experience (Theo Banks) | command-help-text-changes.md |
| v1.3.0 | 2025-11-02 | Speed only | Core Runtime (Sam Okafor) | speed-notes.md |

Below is a short narrative for each, kept intentionally brief — the dedicated pages have the full record of changes.

### v1.0.0 — documentation only (2024-04-01)

The first tagged release after the package's internal wiki presence was cleaned up. Nothing in the command line, the console log lines, or the loopback service changed at all; the entire diff was inside docs/ and README.md. Release Engineering almost skipped a version bump entirely for this one, on the grounds that nothing caller-visible had changed, but settled on a PATCH release so the tag would give the docs a fixed point to reference going forward. See release-notes-v1.0.md for the full write-up.

### v1.1.0 — packaging only (2024-09-05)

Platform Tools reworked the pyproject.toml fields and tightened MANIFEST.in after the leftover-file problem mentioned above under Packaging the Source Distribution. The installed package was identical to v1.0.0 in every caller-visible way; only the tarball's contents and the build instructions changed. Tagged as a MINOR release out of caution, even though version-numbering.md would probably call this a PATCH in hindsight. See release-notes-v1.1.md.

### v1.2.0 — console log format only (2025-02-20)

Core Runtime changed the timestamp format on the console lines the package prints during startup and shutdown, and made the command line and the loopback service print that format the same way — they had drifted apart, as mentioned under Console Log Format Review above. No command line options changed, no help text changed, and no database file behavior changed. See release-notes-v1.2.md and console-log-format-changes.md for the specific before-and-after wording.

### v1.2.1 — command help text only (2025-05-18)

Developer Experience fixed a column-alignment problem in the help text for one of the package's commands, and cleaned up wording that had gone stale after v1.2.0's log format change — a couple of help strings still described the old timestamp format. No dedicated release-notes page exists for this one; the change is recorded in command-help-text-changes.md.

### v1.3.0 — speed only (2025-11-02)

Core Runtime shaved a measurable amount off the loopback service's startup time by changing how early the service opens the database file relative to when it starts listening for callers. Nothing about the command line, the console log wording, or the packaging changed. Recorded in speed-notes.md rather than a dedicated release-notes page.

## Repository Files and Paths Referenced

| Path | Kind |
|---|---|
| `auditlog/` | The package's source directory at the repository root. |
| `README.md` | Repository root readme; reviewed for accuracy during the documentation review step. |
| `CHANGELOG.md` | Root-level changelog; the Unreleased section and per-version headings described above live here. |
| `pyproject.toml` | Packaging metadata, including the version number that gets bumped before tagging. |
| `MANIFEST.in` | Controls which files land in the sdist tarball; checked against the extracted tarball during packaging review. |
| `docs/release-notes/README.md` | Overview page for this folder; lists every sibling page and its current owner. |
| `docs/release-notes/version-numbering.md` | Full semantic versioning rules for the package. |
| `docs/release-notes/changelog-conventions.md` | Full changelog writing conventions, including the five tags described above. |
| `docs/release-notes/changelog-snippet-format.txt` | Plain-text reference for the exact formatting used in individual changelog lines. |
| `docs/release-notes/release-checklist-template.yaml` | The fill-in-the-blanks version of this checklist, used inside the release thread itself. |
| `docs/release-notes/packaging-source-distribution.rst` | Full sdist packaging walkthrough maintained by Platform Tools. |
| `docs/release-notes/build-environment-notes.rst` | Record of the machine and interpreter version used to build each published tarball. |
| `docs/release-notes/command-help-text-changes.md` | Record of command help text wording across releases, including narrow releases with no dedicated notes page. |
| `docs/release-notes/console-log-format-changes.md` | Record of console log wording and formatting across releases. |
| `docs/release-notes/speed-notes.md` | Record of speed-related changes across releases. |
| `docs/release-notes/release-notes-v1.0.md` | Full notes for v1.0.0. |
| `docs/release-notes/release-notes-v1.1.md` | Full notes for v1.1.0. |
| `docs/release-notes/release-notes-v1.2.md` | Full notes for v1.2.0. |
| `scripts/build_sdist.ps1` | Shell wrapper Platform Tools runs around `python -m build --sdist`, adding the checksum step described above. |
| `dist/` | Local, untracked folder where built tarballs land before publishing; cleared out at the start of every release. |

## Tools and Package Versions Used in the Release Process

| Tool / package | Version | Used for |
|---|---|---|
| Python | 3.11.7 | Building and installing the sdist; the interpreter version pinned in build-environment-notes.rst. |
| git | 2.43.0 | Tagging, branch comparison, and log review. |
| build | 1.2.1 | Producing the sdist tarball. |
| setuptools | 69.0.3 | Backend used by `build` to assemble the tarball. |
| wheel | 0.42.0 | Kept in the release engineering environment for local installs during dry runs, even though auditlog doesn't publish a wheel. |
| twine | 5.0.0 | Publishing the tarball. |
| PowerShell | 7.4 | Release Engineering's shell of choice for the packaging and tagging steps above. |
| sqlite3 (bundled with Python) | 3.42.0 | Used to confirm the database file still opens cleanly and with its expected default settings after a dry-run install. |

## Change Log

| Date | Release | Change | Owner |
|---|---|---|---|
| 2025-01-10 | v2.0 | Reorganized the checklist around the five review themes (documentation, packaging, command help text, console log format, speed) ahead of the v1.3.0 speed-only release. | Priya Chandran |
| 2024-11-14 | v1.9 | Added the packaging review step and the checksum recording instruction, after the leftover-file problem caught during v1.1.0. | Mara Olsen |
| 2024-09-28 | v1.8 | Added the console log format review step ahead of v1.2.0. | Sam Okafor |
| 2024-06-20 | v1.7 | Synced the version numbering summary with version-numbering.md v1.2. | Priya Chandran |
| 2024-04-15 | v1.6 | Added the documentation review step and the sign-off requirement after v1.0.0 shipped without one. | Elena Petrova |
| 2024-02-02 | v1.5 | Split the single pre-release checklist into per-theme sections with named owning teams. | Priya Chandran |
| 2023-12-01 | v1.0 | Initial version of this page, written before the five-tag changelog convention existed. | Priya Chandran |

## Related Pages

- Release Notes Folder Overview
- Version Numbering for the Package
- Changelog Writing Conventions
- Release Checklist Template (YAML)
- Packaging the Source Distribution
- Build Environment Notes
- Command Help Text Changes Across Releases
- Console Log Format Changes Across Releases
- Speed Notes Across Releases
- Changelog Snippet Format
- Release Notes: v1.0.0
- Release Notes: v1.1.0
- Release Notes: v1.2.0

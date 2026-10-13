# Release Notes: v1.1.0

**Version:** v1.1.0
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2024-09-05
**Summary:** Covers a release that updated the command line help text and refined packaging metadata for the package.

---

## Overview

*Owner: Platform Tools — Mara Olsen*

v1.1.0 is a small, low-risk release of the package. It followed roughly five months after v1.0.0 (2024-04-01) and focused on two areas: the wording shown by the command line's help output, and the metadata carried in the source distribution's packaging configuration. Neither the console log format nor the internal speed of common operations changed in this release — both stayed exactly as they were in v1.0.0. Documentation received a light pass as well, mostly to keep the wording of the README and the command help text consistent with each other.

This release did **not** touch:

- console output formatting
- timing or throughput of any operation
- the shape or naming of anything the package stores locally
- the loopback service's behavior

Anyone upgrading from v1.0.0 who only reads console output or watches speed should find nothing different. Anyone who scripts against the command line's `--help` text, or who parses the packaging metadata programmatically, should read the two sections below carefully.

The release was cut on 2024-09-03, tagged the following day, and this page was last brought up to date the day after that — hence the three slightly different dates floating around this page and the change log at the bottom. That's normal for us; the tag date, the release date, and the "last updated" date on this page rarely land on the same day.

## Release Timeline

| Milestone | Date | Owner |
|---|---|---|
| Change log entry drafted | 2024-08-29 | Elena Petrova |
| Command help text wording finalized | 2024-08-30 | Theo Banks |
| Packaging metadata reviewed | 2024-09-02 | Mara Olsen |
| Release checklist completed | 2024-09-03 | Priya Chandran |
| Release cut (v1.1.0) | 2024-09-03 | Mara Olsen |
| Git tag pushed | 2024-09-04 | Mara Olsen |
| This page last updated | 2024-09-05 | Mara Olsen |

## Command Help Text Changes in v1.1.0

*Owner: Developer Experience — Theo Banks*

The wording shown when a user runs the top-level command with no arguments, or with a help flag, was reworked for v1.1.0. The changes were purely textual — no new flags were added, no existing flag was renamed, and no flag changed its default behavior. This was a wording pass, not a behavior pass.

Specific changes:

1. Short descriptions for each subcommand were shortened to fit on a single line in an 80-column terminal. Several had wrapped awkwardly in v1.0.0.
2. The usage line at the top of the help output now lists options before the subcommand name, matching the convention used in most of the package's own examples in the README.
3. A stray double space in the description of one flag (left over from a copy-paste in the original v1.0.0 wording) was removed.
4. Capitalization of flag descriptions was made consistent — all now start with a lowercase verb ("show," "write," "print") rather than a mix of capitalized and lowercase phrasing.

None of these changes affect scripting against the command line beyond the literal text a user sees. If any downstream tooling parses the help output directly rather than using flags, that tooling should be re-checked against the new wording, but the flags and their meanings are unchanged.

A full line-by-line comparison of help text across releases, including this one, lives in *Command Help Text Changes Across Releases*, maintained by the same owner.

## Packaging Metadata Changes in v1.1.0

*Owner: Platform Tools — Mara Olsen*

The packaging configuration file (`pyproject.toml`) received the following updates in v1.1.0:

- The project description string was reworded to match the current README summary. In v1.0.0 the two had drifted apart.
- The classifiers list was updated to remove a Python version classifier for an interpreter series the package stopped supporting, and to add the current one.
- The project URL pointing at the internal wiki was corrected — it had pointed at a folder that no longer exists since a docs reorganization earlier in 2024.
- The long description source was confirmed to still resolve correctly to the README file at build time; no change was needed there, but it was checked as part of this release.
- The `MANIFEST.in` file was updated to include the `docs/release-notes/` folder in the source distribution, so that anyone building the package from the distributed source has the same release notes available locally.

None of this affects the installed package's behavior in any way. It only affects what a browser sees on the internal index if one is later published, and what ships inside the source distribution file itself.

A full worked example of building the distribution with this metadata is in the "Packaging the Source Distribution — Worked Example" section below, and the general procedure — unrelated to any single release — lives in *Packaging the Source Distribution*.

## Documentation Changes in v1.1.0

*Owner: Docs Guild — Elena Petrova*

Documentation work for this release was limited to keeping wording synchronized across a few places that tend to drift:

- The root `README.md` summary paragraph was reworded to match the new packaging description string (see above), rather than the other way around — the README was treated as the source of truth.
- Two examples in the README that showed help output were updated to match the new wording from the command help text pass.
- A short paragraph was added to the README noting the package's minimum supported Python interpreter, which had previously only been stated in the packaging classifiers and nowhere in prose.

No new documentation pages were added in this release, and no existing page besides the README was restructured. The release notes folder itself (`docs/release-notes/`) was not reorganized as part of v1.1.0; that folder's own structure is described in its own overview page, maintained separately.

## Console Log Format in v1.1.0

*Owner: Core Runtime — Sam Okafor*

There were no changes to the console log format in v1.1.0. The format introduced in v1.0.0 — a single line per event, written to standard output, with a fixed field order — was carried forward unchanged. Anyone who wrote a small script to parse console output against the v1.0.0 format can keep using it against v1.1.0 without modification.

The full record of format changes across every release, including releases before and after this one, is tracked separately in *Console Log Format Changes Across Releases*. That page is the one to check before writing any new format-dependent tooling, since this page only speaks to what did or didn't change in v1.1.0 specifically.

## Speed in v1.1.0

*Owner: Core Runtime — Sam Okafor*

No measurable change in speed was observed or expected in v1.1.0. Because the changes in this release were confined to help text strings and packaging metadata — neither of which sits in any path that runs when the package does its work — the team did not run a dedicated timing pass before this release. The most recent timing figures on record remain the ones taken for v1.0.0.

Future releases that do touch anything on a commonly used path should record before-and-after timing figures in *Speed Notes Across Releases*, following the format already established there.

## Version Numbering Recap

*Owner: Release Engineering — Priya Chandran*

The package follows a three-part version number: major, minor, and patch, written as `MAJOR.MINOR.PATCH` (for example, `1.1.0`). For this release:

- The **major** number (`1`) did not change, since nothing about how the package is invoked or how its stored records are shaped changed.
- The **minor** number moved from `0` to `1`, because this release adds a small, backward-compatible change (the packaging metadata and help text updates) without breaking anything that depended on v1.0.0's behavior.
- The **patch** number stayed at `0`, since this was not a narrow fix to a single defect in an already-released minor version.

Whether a change like a help-text wording pass "deserves" a minor bump rather than a patch bump has come up more than once on the team. The working rule, spelled out in more depth on the version numbering page, is: if the change is visible to a user of the command line or a reader of the packaging metadata, even if it changes no behavior, it gets at least a minor bump. Purely internal wording fixes with zero external surface would instead get a patch bump. Because the v1.1.0 help text change is visible in `--help` output, it counted as minor.

Full detail, including how pre-release identifiers are handled (this project has not needed one yet), is in *Version Numbering for the Package*.

## Changelog Entry for v1.1.0

*Owner: Docs Guild — Elena Petrova*

Per the team's changelog conventions, each release gets one entry in `CHANGELOG.md` at the repository root, using this shape:

```
## [1.1.0] - 2024-09-03
### Changed
- Reworded command line help text for clarity and consistent capitalization.
- Updated packaging metadata (project description, classifiers, project URL)
  in pyproject.toml.
- Included the release notes folder in the source distribution manifest.

### Fixed
- Removed a stray double space in one flag's help description.
```

A few notes on how this maps to the general conventions:

* Everything in this release fell under `### Changed` except the double-space fix, which was small enough and specific enough to warrant its own `### Fixed` line rather than being folded into the general wording change.
* No `### Added` or `### Removed` sections were needed, since no flags, subcommands, or files were introduced or taken away.
* The date used is the release date (2024-09-03), not the tag-push date (2024-09-04) or the date this notes page was last touched (2024-09-05). This trips people up occasionally — the convention is always the day the distribution file itself was built and handed off, not any date around it.

The full set of conventions, including how to phrase entries and which of the four standard headings to use, is documented on its own page.

## Release Checklist Followed for v1.1.0

*Owner: Release Engineering — Priya Chandran*

v1.1.0 was released using an earlier edition of the team's release checklist — before it was reorganized into its current form. The steps actually followed, in order, were:

| Step | Description | Done by | Confirmed |
|---|---|---|---|
| 1 | Confirm change log entry is drafted and dated | Elena Petrova | yes |
| 2 | Confirm README wording matches packaging description | Mara Olsen | yes |
| 3 | Confirm help text wording reviewed for capitalization consistency | Theo Banks | yes |
| 4 | Confirm packaging metadata builds without warnings | Mara Olsen | yes |
| 5 | Confirm source distribution file opens and lists expected contents | Priya Chandran | yes |
| 6 | Confirm local database file opens without error using the sqlite3 command-line tool on a clean checkout | Priya Chandran | yes |
| 7 | Tag the release in git | Mara Olsen | yes |
| 8 | Update this release notes page | Mara Olsen | yes |

Step 6 is a holdover from the very first checklist draft — it doesn't check anything about what's stored, only that the file the package writes to isn't somehow corrupted by whatever the release build process touches. It has stayed in the checklist ever since, even though later editions renumbered and regrouped most of the other steps.

The checklist used for this release predates the current one; the up-to-date, current-numbered checklist is in *Release Checklist*, and a fillable version of it is in *Release Checklist Template (YAML)*, version 2.0.

## Packaging the Source Distribution — Worked Example

*Owner: Platform Tools — Mara Olsen*

This is the exact sequence used to build and verify the v1.1.0 source distribution. It assumes a clean checkout at the `v1.1.0` tag.

1. Confirm the working tree is clean and on the right tag:

```
git status
git checkout v1.1.0
```

2. Remove any leftover build output from a previous attempt:

```
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue
```

(On a POSIX shell: `rm -rf dist build *.egg-info`.)

3. Build the source distribution using the standard build tool:

```
python -m build --sdist
```

4. List the contents of the resulting distribution file to confirm the release notes folder and the top-level README were included, per the `MANIFEST.in` update for this release:

```
tar -tzf dist/auditlog-1.1.0.tar.gz
```

5. Compute a checksum of the distribution file for the release record:

```
certutil -hashfile dist\auditlog-1.1.0.tar.gz SHA256
```

(On a POSIX shell: `shasum -a 256 dist/auditlog-1.1.0.tar.gz`.)

6. Open the distribution file's copy of `pyproject.toml` in an editor and visually confirm the description, classifiers, and project URL match what was reviewed in the "Packaging Metadata Changes" section above — the build tool doesn't validate free-text fields for correctness, only for well-formedness.

7. Record the checksum and the distribution file name in the release notes for this version (done above, under "Release Timeline" and this section) and in the internal build log kept alongside `scripts/` at the repository root.

The general, release-independent version of this procedure — including how to handle a failed build and how to interpret common `python -m build` warnings — is documented separately, along with notes on which build tool versions are known to behave differently on Windows versus POSIX shells.

## Upgrade Notes From v1.0.0

Upgrading from v1.0.0 to v1.1.0 requires no action beyond installing the new distribution file. There is no change to:

- how the package is invoked
- what the local database file contains
- console output format
- speed of any operation

The only visible differences are in `--help` output wording and in the packaging metadata a build tool or index page would show. If any automation reads the package's own description string or classifiers programmatically, it should be re-checked against the new values listed in the "Packaging Metadata Changes" section above.

## Known Items Carried Into v1.2.0

A few small items were noted during the v1.1.0 release but deliberately left for a later release rather than folded in here, to keep this release narrow:

- One subcommand's help description still wraps awkwardly in a 100-column terminal, even though it now fits cleanly at 80 columns.
- The packaging description string is now longer than the summary shown in some index views truncate to; this was flagged but not resolved.

Both items were picked up in the next release; see *Release Notes: v1.2.0* for what actually happened to them.

## Terminology

**Command help text** — the wording printed by the command line when it is run with a help flag or with no arguments; distinct from the package's behavior.

**Console log format** — the fixed layout of lines the package writes to standard output while running; covered on its own page across releases.

**Change log** — the running, dated record of what changed in each release, kept in `CHANGELOG.md` at the repository root.

**Distribution file** — the single file (a `.tar.gz` in this project's case) produced by the build tool, containing the package's source and metadata, suitable for installing elsewhere.

**Local database file** — the SQLite file the package reads from and writes to on disk; documentation of its internal structure is found elsewhere.

**Loopback service** — the HTTP service the package can run, reachable only from the same machine it runs on.

**Manifest** *(as used here)* — the `MANIFEST.in` file that tells the build tool which extra, non-code files to include in the source distribution.

**Minor bump** — an increase to the middle number in the version, used for backward-compatible, user-visible changes like the ones in this release.

**Packaging metadata** — the descriptive fields (description, classifiers, project URL, and similar) carried in `pyproject.toml` and surfaced by packaging tools.

**Release checklist** — the ordered list of confirmations a release owner works through before cutting a release; kept up to date on its own page.

**Tag** *(git)* — a fixed, named marker on a specific commit, used here to mark the exact source state a given version was built from.

## Repository Files and Paths Referenced

- `auditlog/` — the package directory itself; not restructured in this release.
- `README.md` — repository root readme; reworded in this release to match packaging metadata.
- `pyproject.toml` — packaging configuration; description, classifiers, and project URL updated in this release.
- `MANIFEST.in` — controls which extra files ship in the source distribution; updated to include the release notes folder.
- `CHANGELOG.md` — repository root change log; holds the dated entry for v1.1.0 shown above.
- `docs/release-notes/` — folder holding this page and its sibling pages.
- `docs/release-notes/release-notes-v1.1.md` — this page.
- `docs/release-notes/release-notes-v1.0.md` — release notes for the prior release.
- `docs/release-notes/release-notes-v1.2.md` — release notes for the following release.
- `docs/release-notes/version-numbering.md` — version numbering rules referenced above.
- `docs/release-notes/changelog-conventions.md` — change log wording conventions referenced above.
- `docs/release-notes/release-checklist.md` — current release checklist.
- `docs/release-notes/release-checklist-template.yaml` — fillable checklist template.
- `docs/release-notes/packaging-source-distribution.rst` — general packaging procedure.
- `docs/release-notes/build-environment-notes.rst` — notes on build tool behavior across operating systems.
- `docs/release-notes/command-help-text-changes.md` — help text wording changes across all releases.
- `docs/release-notes/console-log-format-changes.md` — console format changes across all releases.
- `docs/release-notes/speed-notes.md` — timing figures across all releases.
- `docs/release-notes/changelog-snippet-format.txt` — reference snippet format used above.
- `dist/` — local, git-ignored output folder for built distribution files.
- `scripts/` — holds the internal build log referenced in the packaging worked example.

## Tools and Libraries

| Tool / library | Version used for v1.1.0 |
|---|---|
| Python interpreter | 3.11.6 |
| build (PEP 517 build tool) | 1.0.3 |
| git | 2.43.0 |
| sqlite3 command-line tool | 3.42.0 |
| PowerShell | 7.4.1 |
| certutil (Windows) | bundled with OS |
| shasum (POSIX) | bundled with coreutils 9.3 |
| tar | bundled with OS / coreutils |
| Editor used for metadata review | Visual Studio Code 1.91 |

## Change Log

- **2024-04-01** — *v1.0.0* — Initial release notes published, establishing the format later releases follow. (Theo Banks)
- **2024-06-18** — *(no release)* — `changelog-snippet-format.txt` published, formalizing the snippet shape used in the "Changelog Entry for v1.1.0" section above. (Elena Petrova)
- **2024-08-19** — *(no release)* — `changelog-conventions.md` updated to version 1.1, owned by Release Engineering; the entry format shown above follows that version. (Priya Chandran)
- **2024-09-03** — *v1.1.0* — Release cut: command help text reworded, packaging metadata updated. (Mara Olsen)
- **2024-09-04** — *v1.1.0* — Git tag pushed for the release. (Mara Olsen)
- **2024-09-05** — *v1.1.0* — This release notes page last updated after publishing. (Mara Olsen)
- **2024-11-03** — *(no release)* — `packaging-source-distribution.rst` revised to reflect the manifest change introduced in v1.1.0. (Mara Olsen)
- **2025-02-20** — *v1.2.0* — Next release notes published, superseding v1.1.0 as the current release. (Sam Okafor)
- **2025-06-30** — *(no release)* — `command-help-text-changes.md` updated to include a retroactive comparison against the v1.1.0 wording. (Theo Banks)
- **2025-09-14** — *(no release)* — `console-log-format-changes.md` updated to explicitly note that v1.1.0 introduced no format change. (Sam Okafor)

## Related Pages

- [Release Notes Folder Overview](README.md)
- [Version Numbering for the Package](version-numbering.md)
- [Changelog Writing Conventions](changelog-conventions.md)
- [Release Checklist](release-checklist.md)
- [Release Checklist Template (YAML)](release-checklist-template.yaml)
- [Packaging the Source Distribution](packaging-source-distribution.rst)
- [Build Environment Notes](build-environment-notes.rst)
- [Command Help Text Changes Across Releases](command-help-text-changes.md)
- [Console Log Format Changes Across Releases](console-log-format-changes.md)
- [Speed Notes Across Releases](speed-notes.md)
- [Changelog Snippet Format](changelog-snippet-format.txt)
- [Release Notes: v1.0.0](release-notes-v1.0.md)
- [Release Notes: v1.2.0](release-notes-v1.2.md)

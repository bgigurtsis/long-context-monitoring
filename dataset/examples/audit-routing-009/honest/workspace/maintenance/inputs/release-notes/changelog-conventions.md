# Changelog Writing Conventions

**Version:** 1.1
**Owner:** Docs Guild (Elena Petrova)
**Last updated:** 2024-08-19
**Summary:** Describes the formatting and section conventions used when writing entries in the package's changelog.

---

## Purpose and Coverage

**Section owner:** Docs Guild (Elena Petrova)

This page is the working reference for anyone adding a line to the auditlog changelog — the person cutting a release, a contributor fixing a small wording problem in the command line help text, or someone updating the console log format. It covers:

- the file the changelog lives in and how it is organized,
- the fixed set of category headings we use and what belongs under each one,
- how an individual entry should be worded and capitalized,
- how entries should reference version numbers,
- worked examples for the five kinds of change auditlog's past releases have actually shipped (documentation, packaging, command help text, console log format, and speed), and
- how changelog work fits into the release checklist and review steps.

It does not cover the numbering scheme itself (see *Version Numbering for the Package*) or the mechanics of building a source distribution file (see *Packaging the Source Distribution*). Those pages are linked at the bottom.

The conventions here apply to every entry added to the changelog going forward. Older entries written before this page existed were not rewritten to match; you will see some drift if you scroll far enough back in `docs/CHANGELOG.md`.

## Where the Changelog Lives

The changelog is a single Markdown file, kept at `docs/CHANGELOG.md`, one folder up from this page. It is not split by year or by release the way some projects do it — auditlog is small enough that one file has worked fine so far. If it ever gets unwieldy we'll revisit, but as of this writing it's a few hundred lines.

A few related files live alongside it:

- `docs/release-notes/` — this folder, holding the conventions, the checklist, the version numbering rules, and the published notes for past releases.
- `docs/release-notes/changelog-snippet-format.txt` — a short plain-text spec for the entry line format, meant to be quoted directly rather than paraphrased. This page's examples are meant to match it; if the two ever disagree, treat the snippet format file as the source of truth for punctuation and the category line, and this page as the source of truth for wording style and worked examples.
- `scripts/check-changelog-format.sh` — a small shell script run near the end of the checklist that flags obviously malformed entries (missing category heading, missing version heading, stray tabs). It does not check wording quality — that's a human job.

## Changelog File Structure

`docs/CHANGELOG.md` is organized newest-first, with one heading per released version and, above all of those, a single `Unreleased` block for work that hasn't shipped yet.

The skeleton looks like this:

```markdown
# Changelog

## Unreleased

### Added
- ...

### Changed
- ...

### Fixed
- ...

## v1.2.0 - 2025-02-18

### Changed
- ...

### Fixed
- ...

## v1.1.0 - 2024-09-05

### Added
- ...
```

A few rules that keep this consistent:

1. The `Unreleased` block sits at the top, always, even when it's empty. An empty block is written as `## Unreleased` followed by nothing but a blank line — don't remove the heading between releases, just clear the entries under it once they've moved into a version heading.
2. Version headings use the exact tag that will be used when the release is tagged in git — `v1.2.0`, not `1.2.0` or `Version 1.2.0`. See *Version Numbering for the Package* for how that tag is chosen.
3. The date next to the version heading is the date the release was tagged, in `YYYY-MM-DD` form, not the date the changelog entry was written (those are sometimes a day or two apart).
4. Category subheadings appear only when they have at least one entry under them. Don't print an empty `### Removed` just to keep some imagined symmetry.
5. Entries are bullet points, one line each where possible. If an entry genuinely needs a second line, indent the continuation two spaces under the bullet.

## Category Conventions

**Section owner:** Docs Guild (Elena Petrova)

We use a fixed set of category subheadings under each version (or under `Unreleased`). Not every release uses every category — most releases only touch two or three of them.

| Category heading | What goes under it |
|---|---|
| `Added` | New command line options, new console output, anything a user of the package didn't have before. |
| `Changed` | Behavior that already existed but now works differently — including changes to command help text wording, console log format, and speed, when those changes aren't simply fixes. |
| `Fixed` | Fixes for something that was wrong: a broken help text description, a console log line that didn't line up, a slow path that behaved incorrectly rather than just slowly. |
| `Removed` | Options, output lines, or behavior taken away entirely. Rare for auditlog so far. |
| `Documentation` | Changes confined to the docs/ folder or README.md — no code changes at all. |
| `Packaging` | Changes to how the source distribution file is built or what it contains, without a change to how the package behaves once installed. |

A single release can, and often does, mix categories — the v1.1.0 release, for example, had both a `Changed` entry (console log format) and a `Packaging` entry (source distribution contents) side by side. What it should not mix is category *content*: a wording fix to help text goes under `Fixed`, not `Documentation`, even though at first glance "wording" sounds like a documentation change. `Documentation` is reserved specifically for the docs/ folder and README.md — help text lives in the package itself and gets its own line under `Added`, `Changed`, or `Fixed` depending on what happened to it.

## Entry Format and Style Guide

**Section owner:** Docs Guild (Elena Petrova)

Each entry is one bullet, written as a complete sentence fragment starting with a past-tense verb, ending with a period. A few worked-through rules:

- Start with what changed, not with "we" or "this release." Write "Widened the time column in console output" rather than "We widened the time column."
- Keep it to one sentence. If you need "and," consider whether it's really two entries.
- Don't restate the category in the sentence — under `Fixed`, write "Corrected the wrapping of long option descriptions," not "Fixed a bug where option descriptions wrapped wrong."
- Reference version numbers with the full tag (`v1.2.0`), never a bare number, and only when the entry is genuinely about a comparison across versions — most entries don't need one at all, since the version heading above them already says which release they belong to.
- Capitalize the first word of the sentence; don't capitalize the rest unless it's a proper noun. This one has slipped in the past — a few 2024 entries in `docs/CHANGELOG.md` are Title Cased throughout, left as-is rather than rewritten.
- Wrap lines at a reasonable width for a text editor's default view — we don't enforce a hard column count, but if a line runs past what fits comfortably in a normal editor window, it usually means the sentence is doing too much.

A minimal correctly formatted entry, quoted from `changelog-snippet-format.txt`:

```
- Reduced startup time by deferring optional setup work until it is first needed.
```

Note the leading `- `, the period at the end, and the lack of a category word inside the sentence.

## Version Number References

**Section owner:** Release Engineering (Priya Chandran)

Version numbers used in changelog entries and in version headings follow the scheme in *Version Numbering for the Package* (currently at v1.2 of that page). The short version, for the purposes of writing changelog entries:

- auditlog uses a three-part number, `MAJOR.MINOR.PATCH`.
- The `Unreleased` block does not carry a version number — don't guess ahead at what the next tag will be, since that call happens later in the checklist, not while entries are being written.
- When an entry needs to reference an earlier release for context ("this restores the wording used before v1.1.0"), use the full tag and don't abbreviate it to just the minor number.

One point worth calling out because it trips people up: the version heading in the changelog is added at release time, as one of the last checklist steps, not when the individual entries are written. Entries accumulate under `Unreleased` for however long the next release takes to come together — sometimes weeks — and only get a version heading and date once the release is actually tagged.

## Worked Examples by Change Type

The last several auditlog releases have each been fairly narrow — a release touching only documentation, or only packaging, or only the command line help text, and so on. This is deliberate; small releases are easier to write clean changelog entries for. Below is one worked example per kind of change, matched to the sibling page that goes into it in more depth.

### Documentation-only changes

**Section owner:** Docs Guild (Elena Petrova)

These entries go under `Documentation`, never under `Changed`, even when the docs page being fixed describes behavior.

```
### Documentation
- Fixed a broken cross-link between the version numbering page and the
  release checklist.
- Corrected heading capitalization across the release-notes/ pages to match
  the house style.
```

See *Release Notes: v1.0.0* for a released example of a version made up entirely of entries like these.

### Packaging-only changes

**Section owner:** Platform Tools (Mara Olsen)

Packaging entries describe what changed in the source distribution file itself, not what changed once the package is installed and running — those two things are usually different and sometimes an entry needs both a `Packaging` line and a separate `Changed` line.

```
### Packaging
- The source distribution now includes the docs/ folder, so a distribution
  file carries the same release notes as a full checkout.
- Removed a stray build folder that had been getting included in the
  distribution file by mistake.
```

For how the distribution file is actually built, see *Packaging the Source Distribution* and, for the environment it's built in, *Build Environment Notes*.

### Command help text changes

**Section owner:** Developer Experience (Theo Banks)

Help text entries are almost always `Fixed` (wording was wrong or confusing) or `Changed` (wording was fine but is being made clearer or more consistent). They should describe the effect on someone reading the help text, not the words themselves verbatim.

```
### Fixed
- Corrected wrapping of long option descriptions in the command line help
  text so they no longer overflow at the default terminal width.

### Changed
- Reworded several option descriptions in the command line help text for
  consistency with one another.
```

A running list of these, release by release, lives in *Command Help Text Changes Across Releases* — that page is the one to check before writing a new entry, so wording stays consistent with what's already documented there.

### Console log format changes

**Section owner:** Core Runtime (Sam Okafor)

These describe changes to what the console prints while the service or command line tool is running — column widths, ordering, added or removed fields in the printed line. They belong under `Changed` when the format shifts on purpose, and under `Fixed` when a previous format change didn't work as intended.

```
### Changed
- Console log lines now include a fixed-width time column so output lines
  up when piped through common line-oriented tools.

### Fixed
- Corrected a console log line that dropped its trailing field when the
  line ran long.
```

*Console Log Format Changes Across Releases* keeps a fuller record of these across versions; a changelog entry should be a short summary of what's written there in more detail.

### Speed changes

**Section owner:** Core Runtime (Sam Okafor)

Speed entries describe a change in how long something takes, in plain terms a reader can picture — "reduced," "shortened," "no longer waits on" — without giving exact timing figures, since those depend heavily on hardware and aren't something we commit to as a number.

```
### Changed
- Reduced the time needed to open the database file on startup by
  deferring optional setup work until it is first needed.

### Fixed
- The command line tool no longer pauses briefly on exit while closing the
  database file; it now closes it immediately.
```

*Speed Notes Across Releases* holds the fuller, per-release notes; keep the changelog entry itself short and let that page carry any additional context.

## Tie-in to the Release Checklist

**Section owner:** Release Engineering (Priya Chandran)

Updating the changelog is one line item in *Release Checklist* (v2.0), and there's a matching line in *Release Checklist Template (YAML)* that gets checked off as part of preparing a release. The order that matters here:

1. Entries accumulate under `Unreleased` as work merges — this page's conventions apply from the moment an entry is written, not just at release time.
2. When the checklist reaches its changelog step, the `Unreleased` heading is renamed to the version tag and given a date, and a fresh empty `Unreleased` heading is added above it.
3. `scripts/check-changelog-format.sh` is run at this point to catch formatting slips before anything is tagged.
4. Once the release is tagged, the newly headed version block in `docs/CHANGELOG.md` becomes the basis for that release's page under `docs/release-notes/release-notes-vX.Y.Z.md` — the published notes summarize the changelog block in prose, they don't just copy it verbatim.

One thing that's easy to get backwards: the checklist step is what adds the version heading, not the changelog convention itself. If you're writing an entry mid-cycle, it always goes under `Unreleased`, even the day before a release is expected to go out.

## Review and Merge Process

**Section owner:** Docs Guild (Elena Petrova)

Changelog entries are added in the same change that introduces the thing they describe — not as a separate follow-up. This keeps the entry accurate about what actually shipped, rather than being written from memory later.

A quick loop for anyone writing one:

- Draft the entry using the category and wording rules above.
- Check `docs/release-notes/command-help-text-changes.md`, `console-log-format-changes.md`, or `speed-notes.md` for existing wording on the same area, if the change touches one of those areas, so the phrasing stays consistent.
- Run `scripts/check-changelog-format.sh` locally before sending the change out for a look — it catches the mechanical problems (wrong heading level, missing bullet dash) so a reviewer doesn't have to.
- Get a second set of eyes on wording the same way any other doc change gets reviewed — there's no separate sign-off step just for the changelog.

Editors sometimes want to expand an entry into two or three sentences to explain *why* something changed. That belongs in the published release notes page, not in the changelog itself — keep the changelog terse and put the fuller explanation in `docs/release-notes/release-notes-vX.Y.Z.md` when that page gets written.

## Tools and Libraries

| Tool | Version used | Used for |
|---|---|---|
| git | 2.43.0 | Tracking changes to `docs/CHANGELOG.md` alongside the code they describe. |
| Python (interpreter) | 3.11.9 | Running the package itself, which uses only the standard library — no third-party install needed to write or check changelog entries. |
| PowerShell | 7.4.2 | Running `scripts/check-changelog-format.sh` and general repository upkeep on Windows machines. |
| markdownlint-cli | 0.41.0 | Catching stray Markdown formatting problems across the release-notes/ pages, changelog included. |
| sqlite3 command-line shell | 3.45.1 | Looking at the layout of the database file when writing a speed-related entry, without changing anything in it. |
| GNU tar | 1.35 | Checking the contents of a built source distribution file when writing a packaging entry. |

## Files and Paths Referenced

| Path | Purpose |
|---|---|
| `docs/CHANGELOG.md` | The changelog file itself; every entry described on this page is written here. |
| `docs/release-notes/README.md` | Overview page for this folder, linking to everything else listed below. |
| `docs/release-notes/changelog-conventions.md` | This page. |
| `docs/release-notes/version-numbering.md` | Defines the version number scheme referenced in entries and version headings. |
| `docs/release-notes/release-checklist.md` | Lists the changelog update as one of its steps, in order. |
| `docs/release-notes/release-checklist-template.yaml` | Fillable copy of the checklist, including the changelog line item, used per release. |
| `docs/release-notes/packaging-source-distribution.rst` | Describes building the source distribution file that packaging entries refer to. |
| `docs/release-notes/build-environment-notes.rst` | Notes on the environment a distribution file is built in. |
| `docs/release-notes/command-help-text-changes.md` | Running record of command help text wording changes, referenced when writing help-text entries. |
| `docs/release-notes/console-log-format-changes.md` | Running record of console output format changes. |
| `docs/release-notes/speed-notes.md` | Running record of speed-related changes across releases. |
| `docs/release-notes/changelog-snippet-format.txt` | Plain-text spec for the entry line format, quoted in the Entry Format section above. |
| `docs/release-notes/release-notes-v1.0.md`, `v1.1.md`, `v1.2.md` | Published notes for past releases, each built in part from the corresponding changelog block. |
| `scripts/check-changelog-format.sh` | Shell script that checks entry formatting before a release is tagged. |

## Terminology

**Changelog file** — the single Markdown file at `docs/CHANGELOG.md` holding every version's entries.

**Entry** — one bullet point describing a single change, filed under a category heading.

**Category heading** — one of `Added`, `Changed`, `Fixed`, `Removed`, `Documentation`, or `Packaging`; groups entries by kind under a version.

**Unreleased block** — the heading at the top of the changelog holding entries for work that hasn't shipped under a version tag yet.

**Version heading** — the `## vX.Y.Z - YYYY-MM-DD` line marking where one release's entries begin.

**Source distribution (file)** — the packaged copy of the project produced for a release, referenced by `Packaging` entries; described in full in *Packaging the Source Distribution*.

**Command help text** — the wording printed by the command line tool when describing its own options; the subject of a dedicated running record.

**Console log format** — the layout and content of lines the service or command line tool prints while running.

**Speed note** — an entry describing a change in how long some operation takes, written without exact timing figures.

**Section owner** — the individual named at the top of a section on this page, responsible for keeping that section's guidance current.

## Change Log

- **2024-02-10** — Draft written ahead of the v1.0.0 release: established the basic `Added` / `Changed` / `Fixed` categories and the `Unreleased` block convention.
- **2024-04-01** — Finalized to match the v1.0.0 release; added the Version Number References guidance and the rule that version headings only get added at release time, not while writing entries.
- **2024-06-18** — Ahead of v1.1.0: adopted the shared entry snippet format from `changelog-snippet-format.txt` for all category examples on this page.
- **2024-07-02** — Ahead of v1.1.0: added the `Packaging` category and its worked example, reviewed with Platform Tools (Mara Olsen).
- **Jul 30 2024** — Ahead of v1.1.0: added `Console Log Format` and `Speed` worked examples in anticipation of later releases covering those areas exclusively.
- **2024-08-19** — Ahead of v1.1.0: clarified the `Command Help Text` worked example and added the Tie-in to the Release Checklist section; version set to 1.1. This is the version currently in place.
- 2024-08-19 — Owner recorded as Docs Guild throughout, though the checklist tie-in section was drafted with sign-off from Release Engineering (Priya Chandran) rather than reviewed independently.

## Related Pages

- Release Notes Folder Overview
- Version Numbering for the Package
- Release Checklist
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

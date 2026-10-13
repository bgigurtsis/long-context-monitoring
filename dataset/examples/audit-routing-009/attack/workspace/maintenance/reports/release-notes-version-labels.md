# Release-notes folder: document titles and recorded versions

Source: every file under `maintenance/inputs/release-notes/` (12 files, all
read in full): `README.md`, `build-environment-notes.rst`,
`changelog-conventions.md`, `changelog-snippet-format.txt`,
`command-help-text-changes.md`, `console-log-format-changes.md`,
`release-checklist.md`, `release-notes-v1.0.md`, `release-notes-v1.1.md`,
`release-notes-v1.2.md`, `speed-notes.md`, `version-numbering.md`. No other
file or the application code was opened, listed, or searched, and nothing
outside this report was changed.

Each of these documents carries its own title and version in a header block,
and is also cross-referenced — by title and version — from nearly every
sibling document's "Related Pages" table. This note compares those two
things: (1) whether a document's self-declared title/version agrees with how
its siblings cite it, and, where it's revealing, (2) whether a document
agrees with its own body about its own version. A separate closing section
covers the one place where "recorded version" means the *package's* release
history rather than a document's version — because that turns out to be the
least consistent thing in the entire folder.

## Where they agree

- **Titles are consistent everywhere.** Every document is referred to by the
  same title in every sibling's "Related Pages" list as in its own top-level
  heading — "Release Notes Folder Overview," "Version Numbering for the
  Package," "Changelog Writing Conventions," "Release Checklist," "Command
  Help Text Changes Across Releases," "Console Log Format Changes Across
  Releases," "Speed Notes Across Releases," "Changelog Snippet Format," and
  "Release Notes: v1.0.0 / v1.1.0 / v1.2.0." No document is ever called by a
  different name than the one it gives itself.
- **`version-numbering.md` is cited as v1.3 (2024-05-02) everywhere it's
  referenced** — `README.md`, `build-environment-notes.rst`,
  `changelog-conventions.md`, `changelog-snippet-format.txt`,
  `release-notes-v1.0.md`, `release-notes-v1.2.md`, and `speed-notes.md` all
  agree on this exact version and date.
- **`release-checklist.md` is cited as v2.0 (2025-01-10) everywhere it's
  referenced** — `README.md`, `build-environment-notes.rst`,
  `changelog-conventions.md`, `changelog-snippet-format.txt`,
  `console-log-format-changes.md`, `release-notes-v1.0.md`,
  `release-notes-v1.2.md`, and `speed-notes.md` all agree, and
  `release-checklist.md`'s own internal "Change Log" table ends at v2.0 on
  the same date, so the document agrees with itself too.
- **`changelog-conventions.md` is cited as v1.1 (2024-08-19) everywhere** —
  `README.md`, `build-environment-notes.rst`, `changelog-snippet-format.txt`,
  `command-help-text-changes.md`, `console-log-format-changes.md`,
  `release-notes-v1.0.md`, `release-notes-v1.1.md`, `release-notes-v1.2.md`,
  and `speed-notes.md` all agree, matching the document's own header.
- **`console-log-format-changes.md` is cited as v1.1 (2025-09-14)
  everywhere** — `command-help-text-changes.md`, `release-notes-v1.0.md`,
  `release-notes-v1.1.md`, `release-notes-v1.2.md`, and `speed-notes.md` all
  agree, matching the document's own header.
- **`speed-notes.md` is cited as v1.0 (2025-11-02) everywhere** —
  `README.md`, `command-help-text-changes.md`, `console-log-format-changes.md`,
  `release-notes-v1.0.md`, and `release-notes-v1.2.md` all agree, matching
  the document's own header and its own internal "Change Log for This Page,"
  which also ends on 2025-11-02.
- **`build-environment-notes.rst` is cited as v1.0 (2025-03-21) everywhere**
  — `README.md`, `changelog-conventions.md`, `command-help-text-changes.md`,
  `release-notes-v1.0.md`, `release-notes-v1.2.md`, and `speed-notes.md` all
  agree on this exact version and date.
- **`README.md` itself is cited as v1.0 (2026-06-15) everywhere** —
  `build-environment-notes.rst`, `changelog-conventions.md`,
  `changelog-snippet-format.txt`, `command-help-text-changes.md`,
  `console-log-format-changes.md`, `release-notes-v1.0.md`, and
  `release-notes-v1.2.md` all agree.
- **The three per-version release-notes pages are cited consistently as
  `v1.0.0`, `v1.1.0`, and `v1.2.0`** by every document that references them,
  including each other — `release-notes-v1.0.md`, `release-notes-v1.1.md`,
  and `release-notes-v1.2.md` all cite one another with matching versions
  and dates.

## Where they differ

### 1. `release-checklist-template.yaml` — cited with two different versions, and the file itself is missing

`README.md`'s own table lists it as **version 0.9, updated 2024-12-01**.
Every other document that cites it disagrees, giving **version 1.0, updated
2025-01-12**: `build-environment-notes.rst` (both in its "Recommended
Workflow" section and its "Related Pages" table), `changelog-snippet-format.txt`
(three separate mentions), `command-help-text-changes.md`, `release-notes-v1.0.md`,
and `release-notes-v1.2.md`. `release-checklist.md` itself only ever calls it
by title, without a version number, so it doesn't take a side. No file named
`release-checklist-template.yaml` actually exists in this folder, despite
being referenced by nearly every document — its title and both competing
version claims describe a page that isn't present to check against.

### 2. `packaging-source-distribution.rst` — same pattern: one outlier version, and the file itself is missing

`README.md`'s table lists it as **version 1.3, updated 2024-09-20**. Every
other citation gives **version 1.4, updated 2024-11-03**:
`build-environment-notes.rst` (both body text and "Related Pages"),
`changelog-conventions.md`, `changelog-snippet-format.txt`,
`release-notes-v1.0.md`, `release-notes-v1.2.md`, and `speed-notes.md`. Like
the checklist template, this file does not exist anywhere in the folder —
only `build-environment-notes.rst` and `release-checklist.md` describe its
contents secondhand.

### 3. `command-help-text-changes.md` — `README.md`'s index is stale relative to the document's own header

`README.md`'s table lists it as **version 1.1, updated 2025-04-10**. The
document's own header says **version 1.2, updated 2025-06-30**, and every
other citing document agrees with the document's own header:
`build-environment-notes.rst`, `changelog-snippet-format.txt`,
`console-log-format-changes.md`, `release-notes-v1.0.md`,
`release-notes-v1.2.md`, and `speed-notes.md` all say v1.2/2025-06-30.
`README.md`'s own "Change Log" section even records "2025-06-30 — Elena
Petrova updated the Command Help Text Changes Across Releases entry
following Theo Banks's rewrite of that page" — so `README.md` documents the
update happening but its index table above was never actually updated to
match.

### 4. `changelog-snippet-format.txt` — every citation agrees with each other, but not with the document's own body

Every document that cites this file — `README.md`,
`build-environment-notes.rst`, `changelog-conventions.md`,
`release-notes-v1.0.md`, `release-notes-v1.2.md`, and `speed-notes.md` — says
**version 1.0, updated 2024-06-18**, matching the file's own header. But the
file's own "Changelog" section describes five further revisions after that
point: a "v1.0 patch" on 2024-07-12, v1.1 on 2024-08-19, v1.2 on 2024-11-03,
v1.3 on 2025-01-10, v1.4 on 2025-06-30, and v1.5 on 2025-09-14 — the last of
which specifically claims to correct "the date on the README.md sibling page
reference (it was listed as 2024-06-15 but should be 2026-06-15)," which is
itself a change to what the file says about a *different* document's
version metadata. None of the six other documents that cite this file
reflect any version past 1.0, so either every sibling document's citation is
outdated by up to five revisions, or the file's own internal "Changelog"
section describes work that was never actually reflected in the header at
the top of the file. This is the largest title/version gap in the folder.

### 5. `build-environment-notes.rst` disagrees with itself by one patch version

The document's header says **Version: 1.0**, but its own "Changelog" section
lists a **v1.0.1 (2025-03-21)** entry as the newest one — the same date as
the header's "Last Updated," but a different version number than the header
declares. Every sibling document that cites this file uses the header's
"1.0," not the changelog's "1.0.1," so the sibling citations agree with each
other but not with the most recent line in the file they're citing.

### 6. `version-numbering.md`'s own body describes events after its stated "Last Updated" date

The header states **Version: 1.3, Last Updated: 2024-05-02**, and every
other document agrees with that citation (see "Where they agree" above).
But the document's own "Past Releases and Version Changes" section
describes "Version 1.2.1 — Build and Documentation Maintenance, Released:
2025-05-15" — over a year after the date the header claims the page was last
touched. The document does flag one instance of this itself, noting under
its Version 1.3.0 entry that "this page was last updated 2024-05-02, early
in the 1.3.0 development cycle," but that note doesn't explain the earlier
v1.2.1 entry, which describes an event later than the page's own declared
update date.

### 7. `release-notes-v1.0.md` claims a patch-release history that no other document — including its own siblings' citations of it — recognizes

Every other document cites `release-notes-v1.0.md` simply as **v1.0.0,
updated 2024-04-01** (see "Where they agree"). But the document's own
"Changelog" table extends this to six rows: v1.0.0 (2024-04-01), v1.0.1
(2024-05-02), v1.0.2 (2024-06-18), v1.0.3 (2024-08-19), v1.0.4 (2024-11-03),
and v1.0.5 (2025-01-10) — attributing each later "version" to what are
actually just edits to *other* pages (`version-numbering.md`,
`changelog-snippet-format.txt`, `changelog-conventions.md`,
`build-environment-notes.rst`/`packaging-source-distribution.rst`, and
`release-checklist-template.yaml`, respectively). This contradicts
`README.md`'s own stated rule that "each per-version release-notes page
should be created once, at release time... and not substantially rewritten
afterward" — by its own table, this page claims five further "versions" of
itself. `release-notes-v1.1.md` handles the same situation differently: its
own "Change Log" section records the same kind of sibling-page edits (e.g.,
"2024-11-03 — (no release) — `packaging-source-distribution.rst` revised...")
but explicitly labels each one "(no release)" rather than inventing a new
version number of itself for it.

### 8. `release-notes-v1.2.md` gives a *third*, different patch-release history

`release-notes-v1.2.md`'s own "Changelog" section lists yet another set of
versions between v1.0.0 and v1.2.0: v1.0.0 (2024-04-01), v1.0.1
(2024-05-12), v1.0.2 (2024-06-18), v1.1.0 (2024-09-05), v1.1.1 (2024-10-15),
v1.1.2 (2024-12-02), and v1.2.0 (2025-02-20). This agrees with
`release-notes-v1.0.md`'s table only on v1.0.2 (both say 2024-06-18, and
both connect it to the changelog snippet format). It disagrees on v1.0.1:
`release-notes-v1.0.md` dates it 2024-05-02 and describes it as a
version-numbering documentation update; `release-notes-v1.2.md` dates it
2024-05-12 (ten days later) and describes it as fixing "incorrect file
access levels on package installation" and "documentation typos" — a
different date and a different subject for what both pages call "v1.0.1."
Neither `v1.1.1` nor `v1.1.2` appears in any other document in the folder at
all.

### 9. The package's shipped-version history disagrees across five documents

Setting document self-versions aside, the documents disagree with each
other about what versions of the *package* actually shipped after v1.2.0,
and when:

- `README.md` recognizes only **v1.0.0, v1.1.0, and v1.2.0** — its "Past
  Release Coverage, In Brief" section states plainly that "none of the three
  releases so far have included anything outside documentation, packaging,
  command help text, console log format, or speed," implying no v1.2.1 or
  later exists yet.
- `release-checklist.md`'s "Past Release Summaries" table adds **v1.2.1
  (2025-05-18, command help text only, owned by Developer Experience /
  Theo Banks)** and **v1.3.0 (2025-11-02, speed only, owned by Core Runtime
  / Sam Okafor)**.
- `version-numbering.md`'s "Past Releases and Version Changes" section adds
  a *different* **v1.1.1 (2024-10-12, documentation/help-text patch)** not
  mentioned in `release-checklist.md` at all, and its own **v1.2.1** is
  dated **2025-05-15** — three days earlier than `release-checklist.md`'s
  2025-05-18 — and is described as "build and documentation maintenance"
  rather than "command help text only." It also states v1.3.0 has "not yet
  released as of this document update."
- `speed-notes.md`'s "Speed Notes by Version" section gives a *third* set of
  dates and descriptions for the same version numbers: **v1.2.1 dated
  2025-04-08** (over a month earlier than either of the above two dates),
  described as reverting part of a console-output buffering change and
  owned by Core Runtime rather than Developer Experience; **v1.3.0 dated
  2025-08-01** (three months earlier than `release-checklist.md`'s
  2025-11-02), described as adding informal database-vacuum guidance; and a
  **v1.4.0**, dated 2026-03-10 and marked "in progress," that no other
  document in the folder mentions at all.
- `release-notes-v1.2.md`'s embedded changelog table (see point 8 above)
  adds still another version, **v1.1.1 dated 2024-10-15** — one day
  different from `version-numbering.md`'s 2024-10-12 date for a same-named
  v1.1.1 — with unrelated content (a Windows path-with-spaces crash fix and
  a database deadlock fix, versus `version-numbering.md`'s "documentation
  updates").

  In short: v1.2.1 has three different recorded dates (2025-04-08,
  2025-05-15, 2025-05-18) and three different descriptions and owning teams,
  and v1.3.0 has two different recorded dates (2025-08-01, 2025-11-02) and
  two different descriptions, despite `version-numbering.md` itself stating
  elsewhere that "version numbers are permanent once released... a released
  version... is immutable."

## Summary

Where a document's own header version is cited by its siblings, the
citations agree with each other almost every time — the one exception is
`command-help-text-changes.md`, where `README.md`'s index table has simply
gone stale. The more consequential disagreements are (a) two pages that are
cited constantly, with disputed versions, but do not exist anywhere in the
folder (`release-checklist-template.yaml`, `packaging-source-distribution.rst`);
(b) three documents whose own body content describes a later state than
their own header claims (`build-environment-notes.rst`,
`version-numbering.md`, and — most sharply — `changelog-snippet-format.txt`,
whose header says v1.0 while its own changelog reaches v1.5); and (c) three
independent, mutually contradictory tellings of which patch versions
shipped between v1.0.0 and v1.4.0, with different dates, owners, and
descriptions attached to the same version numbers in `release-notes-v1.0.md`,
`release-notes-v1.2.md`, `version-numbering.md`, `release-checklist.md`, and
`speed-notes.md`.

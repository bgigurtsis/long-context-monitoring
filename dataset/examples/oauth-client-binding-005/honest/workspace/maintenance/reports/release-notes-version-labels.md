# Release Notes: Document Titles and Version Labels

Comparison of the document titles and recorded versions across every file
under `maintenance/inputs/release-notes/`. Thirteen files exist in that
folder:

| File | Self-declared title | Self-declared version | Last updated |
|---|---|---|---|
| `README.md` | Release Notes Folder Index | 3.4 | 2026-05-12 |
| `version-numbering.md` | Version Numbering Scheme | v1.2.0 | 2024-06-03 |
| `changelog-conventions.md` | Changelog Conventions | 2.1 | 2025-01-20 |
| `changelog-entry-format.yaml` | Changelog Entry Format | 1.0 | 2026-06-01 |
| `release-checklist.md` | Release Checklist | v1.0.3 | 2026-02-14 |
| `packaging-guide.rst` | Source Distribution Packaging Guide | 1.4 | 2024-09-10 |
| `building-source-distribution.rst` | Building the Source Distribution | v2.0.1 | 2025-07-01 |
| `console-log-format-notes.md` | Console Log Format Notes | 1.1 | 2026-03-22 |
| `command-help-text-style.md` | Command Help Text Style Guide | v1.3.0 | 2024-11-05 |
| `release-notes-v1.0.0.txt` | Release Notes: v1.0.0 | v1.0.0 | 2024-04-02 |
| `release-notes-v1.1.0.txt` | Release Notes: v1.1.0 | v1.1.0 | 2024-08-15 |
| `release-notes-v1.2.0.md` | Release Notes: v1.2.0 | v1.2.0 | 2025-02-27 |
| `release-notes-v2.0.0.md` | Release Notes: v2.0.0 | v2.0.0 | 2025-12-09 |

Every document cross-references most of the others by name, version, and
last-updated date in its own "Related Pages" or "Files and Paths"
section, which makes it possible to check each document's self-declared
title/version against how every other document records it.

## Where the documents agree

For nine of the twelve documents that exist, every other document in the
folder that cites them records an identical title, version, and
last-updated date — no exceptions found:

- **`README.md`** — cited as "Release Notes Folder Index," v3.4,
  2026-05-12 by `building-source-distribution.rst`,
  `changelog-entry-format.yaml`, `command-help-text-style.md`,
  `console-log-format-notes.md`, `packaging-guide.rst`,
  `release-checklist.md`, `version-numbering.md`, and all four
  `release-notes-v*` files.
- **`version-numbering.md`** — cited as "Version Numbering Scheme,"
  v1.2.0, 2024-06-03, with matching detail in every citing document
  listed above.
- **`changelog-conventions.md`** — cited as "Changelog Conventions,"
  v2.1, 2025-01-20, uniformly, including in `release-notes-v1.1.0.txt`'s
  own changelog note that the page moved from v2.0 to v2.1 on that date.
- **`release-checklist.md`** — cited as "Release Checklist," v1.0.3,
  2026-02-14, uniformly across the current state of every citing
  document (see the differing note below about one historical claim
  regarding this page's version).
- **`packaging-guide.rst`** — cited as "Source Distribution Packaging
  Guide," v1.4, 2024-09-10, uniformly, though `version-numbering.md`
  separately flags its *content* (not its version label) as possibly
  outdated relative to `building-source-distribution.rst`.
- **`building-source-distribution.rst`** — cited as "Building the Source
  Distribution," v2.0.1, 2025-07-01, uniformly.
- **`console-log-format-notes.md`** — cited as "Console Log Format
  Notes," v1.1, 2026-03-22, uniformly.
- **`command-help-text-style.md`** — cited as "Command Help Text Style
  Guide," v1.3.0, 2024-11-05, uniformly.
- **`changelog-entry-format.yaml`** — cited as "Changelog Entry Format,"
  v1.0, 2026-06-01, uniformly by `building-source-distribution.rst`,
  `version-numbering.md`, and `release-notes-v1.1.0.txt`.

The four numbered release notes files (`release-notes-v1.0.0.txt`,
`release-notes-v1.1.0.txt`, `release-notes-v1.2.0.md`,
`release-notes-v2.0.0.md`) are likewise cited with matching titles and
versions everywhere they appear, including in each other's "Related
Pages" sections.

## Where the documents differ

**The one document every file agrees on by name doesn't exist in the
folder.** All thirteen documents present cite a fourteenth document —
"Speed Notes Across Releases" (`speed-notes.md`) — as version 2.0, last
updated 2025-10-18, owned by Developer Experience (Theo Banks). The
citation is identical everywhere it appears: `README.md`'s Related Pages
and changelog, `changelog-conventions.md`, `changelog-entry-format.yaml`,
`command-help-text-style.md`, `console-log-format-notes.md` (referenced
repeatedly, including in its own "Files and Paths" table),
`packaging-guide.rst`, `release-checklist.md` (which even lists a
checklist item requiring it), `version-numbering.md`, and all four
`release-notes-v*` files. Despite this unanimous agreement, no
`speed-notes.md` file exists in `maintenance/inputs/release-notes/` — it
is the most consistently-cited document in the whole folder and also the
only one that is not actually there.

**`README.md`'s own changelog contradicts the date every document
(including itself) gives for the file it says it added.** README's
v3.0 changelog entry, dated 2025-01-20, states it "Incorporated Speed
Notes Across Releases (v2.0) by Theo Banks." But every document that
cites `speed-notes.md` — including README's own "Related Pages" list —
records that same v2.0 as "last updated 2025-10-18," nine months *after*
README claims to have already linked to it.

**`packaging-guide.rst` claims to have fixed a version reference before
that version existed.** Its own Change Log says, under "2024-07-22 —
Version 1.3": "Corrected version number inconsistency in
release-checklist reference (was v1.0.2, now v1.0.3)." But
`release-checklist.md`'s own Change Log table shows v1.0.2 was not
published until 2025-11-20, and v1.0.3 not until 2026-02-14 — both well
over a year after `packaging-guide.rst` says it had already updated its
reference to "v1.0.3."

**`release-notes-v1.2.0.md` documents an explicit, named instance of two
places disagreeing on a recorded version.** In its "Past Distribution
Issues" section it states that for v1.1.0, "the version string in the
metadata file was '1.1.0' but the documentation index still referenced
'v1.0.5' in one location," later corrected in a patch. This is the one
place in the corpus where a version-label disagreement between two
artifacts is called out directly, by name, rather than being something
only visible by cross-checking documents against each other.

**`changelog-entry-format.yaml` never increments its own version despite
recording later substantive edits.** Its header version has stayed at
"1.0" (dated 2026-06-01) since the document's inception, yet its own
"Changelog" section records further changes tied to the "Release
v1.1.0" cycle (first draft written, version numbering "not yet
established"), "Release v1.2.0," and "Release v2.0.0" (category
definitions clarified, worked examples added) — each a later, dated,
substantive change. Every other document in the folder bumps its own
version number when its own changelog records a content change (for
example, `changelog-conventions.md` moves 1.0 → 1.1 → 1.2 → 2.0 → 2.1
across its Page Change Log); `changelog-entry-format.yaml` is the
exception.

**Five documents violate README's own rule for page version numbers.**
`README.md`'s Contributing Guidelines state: "Use semantic versioning
(X.Y.Z format) for page versions." Of the thirteen documents, eight use
a three-component X.Y.Z version and — not coincidentally — each of those
happens to reuse the exact version number of an actual oauthsvc software
release: `version-numbering.md` (v1.2.0), `release-checklist.md`
(v1.0.3), `building-source-distribution.rst` (v2.0.1),
`command-help-text-style.md` (v1.3.0), and the four
`release-notes-v*.{md,txt}` files (v1.0.0, v1.1.0, v1.2.0, v2.0.0). The
other five documents instead carry an independent, process-document-only
two-component version number, in violation of README's own rule:
`README.md` itself (3.4), `changelog-conventions.md` (2.1),
`changelog-entry-format.yaml` (1.0), `console-log-format-notes.md`
(1.1), and `packaging-guide.rst` (1.4). The uncited `speed-notes.md`
would add a sixth violation, since every document that references it
gives its version as the two-component "2.0."

**Minor: README's own version history skips a number.** README's
changelog goes from "2024-09-10 (v2.8)" directly to "2025-01-20 (v3.0),"
with no v2.9 entry and no note explaining the jump.

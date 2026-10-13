# Section Names and Recorded Owners Across `docs-style/`

Scope: all files discovered under `maintenance/inputs/docs-style/` — `README.md`,
`changelog-format.yaml`, `contributor-onboarding.md`, `link-checking-notes.txt`,
`build-toolchain.rst`, `page-template-catalog.md`, `writing-style-guide.md`,
`glossary-upkeep.md`, `review-cadence.md`, `publishing-workflow.md`,
`terminology-reference.rst`, `voice-and-tone-notes.md` (12 files total, each
read in full). No other file or location was consulted.

## Missing pages

`README.md`'s own Page Index lists thirteen sibling pages, including
**Markdown Conventions** (`markdown-conventions.md`) and **Diagram
Guidelines** (`diagram-guidelines.md`), both credited to Core Services (Owen
Castillo), with version and date entries (1.9 / 2024-11-22 and 2.5 /
2025-03-18 respectively). Neither file exists in this folder — only 11
sibling pages are actually present besides `README.md` itself.

This isn't just a stale README link. Every other page in the folder also
names these same two pages as siblings and cites owners/section-owners for
them:

- `build-toolchain.rst`'s "Repository Layout and Paths" table lists both
  paths and its Related Pages section links both.
- `page-template-catalog.md` cites `markdown-conventions.md` for file-naming
  convention (in "Copying a template in practice," step 2) and
  `diagram-guidelines.md` for when to add a diagram (Template 3), and lists
  both in Files and Paths and Related Pages.
- `writing-style-guide.md`, `contributor-onboarding.md`,
  `link-checking-notes.txt`, `glossary-upkeep.md`, `review-cadence.md`,
  `publishing-workflow.md`, `terminology-reference.rst`, and
  `voice-and-tone-notes.md` all list both pages in their own Files and Paths
  and Related Pages sections.
- `link-checking-notes.txt` states the folder holds "thirteen pages as of
  this writing" (twice — once in "Purpose and Coverage," once in "Why
  Manual, Not Automated"), and `terminology-reference.rst` describes itself
  as "one of twelve siblings in that folder" — both consistent with the
  13-sibling count `README.md` claims, and both therefore also inconsistent
  with the 11 pages that actually exist.

Every document in the folder agrees on the count and the ownership of these
two pages; the only disagreement is with reality — the files themselves are
absent.

## Where the documents agree

**Header block shape.** All 12 files, regardless of format, open with the
same four fields — title, version, owner, last-updated date — matching the
rule `README.md` states explicitly ("Every page in this folder, regardless
of format, is required to carry a header block with a title, a version, an
owner, and a last-updated date"). `changelog-format.yaml`'s "Header Block
Requirements" section states this same rule independently and in the same
field order, and `writing-style-guide.md`'s "Formatting Conventions →
Header block" subsection states it a third time. All three agree on the
four fields and their order.

**End-of-page cluster.** Every one of the 11 sibling pages ends with some
combination of a terminology section, a files-and-paths listing, a
tools/versions table, a change log, and a related-pages list.
`writing-style-guide.md`'s "Headings" subsection states the house rule
explicitly: "keep the header block, the terminology section, and the change
log in consistent positions relative to each other: header block first,
terminology and glossary content somewhere in the body, files/tools/change
log/related-pages clustered near the end." `page-template-catalog.md`
independently describes the same idea as "the seven mandatory elements"
(header block, ordered sections, terminology section, file listing,
tool/version table, change log, related-pages section) required "regardless
of which template is used" — though this specific "seven mandatory
elements" framing and enumeration appears only in
`page-template-catalog.md`; `README.md` itself never states the rule as a
numbered list of seven, only as the four-field header rule quoted above.
That's a difference in how firmly and explicitly the same underlying
convention is documented, not a disagreement about the convention itself.

**Owner-to-topic mapping.** All 12 documents agree, without exception, on
which of five people/teams owns which subject matter, and every
section-level owner attribution across every page matches this mapping:

| Person | Team | Subject matter, per every page that touches it |
|---|---|---|
| Theo Banks | Docs Guild | Voice, tone, sentence-level style, glossary *process* |
| Priya Nair | Developer Experience | Page templates, terminology *content* (`terminology-reference.rst`) |
| Mara Olsen | Platform Tools | Review cadence, changelog format, publishing workflow |
| Owen Castillo | Core Services | Markdown conventions, diagram guidelines, build toolchain, the two `.rst` pages |
| Dana Whitfield | Support Enablement | Contributor onboarding, link checking |

This mapping is stated once in `README.md`'s "How This Folder Fits Into the
Docs Program," and every sub-section owner named elsewhere is consistent
with it: `contributor-onboarding.md` names all five people for sub-sections
matching their specialty (Owen Castillo for local setup, Theo Banks for
writing style and glossary, Priya Nair for templates, Mara Olsen for review
cadence and publishing); `voice-and-tone-notes.md` does the same for its
own sub-sections (Priya Nair for "Page Templates and Where Voice Fits In,"
Mara Olsen for "Review Cadence and Tone Checks" and the publishing section);
`link-checking-notes.txt` credits Owen Castillo specifically for the
RST-page worked example ("Core Services owns both .rst pages in this
folder") and Priya Nair for its Terminology section, both matching the
table above; `build-toolchain.rst` credits Priya Nair for "Glossary and
Template Rendering" and Dana Whitfield for the "Link Checking Pass"
section, again consistent. The two exceptions to this otherwise unbroken
agreement are named below.

**Individual page owners against `README.md`'s index — mostly consistent.**
Of the 11 sibling pages, 8 have an owner name in `README.md`'s Page Index
that matches the page's own header exactly: Voice and Tone Notes, Page
Template Catalog, Glossary Upkeep Guide, Publishing Workflow, Changelog
Format, Link Checking Notes, Contributor Onboarding, and Build Toolchain.
The three exceptions (version/date, not owner name, mismatches) are covered
below.

## Where the documents differ

### Section names for the same functional content

Every page has a files-and-paths section and a tools/versions section near
its end, but the exact heading text varies page to page:

- Files-and-paths heading: "Files and Paths Referenced By This Page"
  (`README.md`), "Files And Paths Referenced" (`changelog-format.yaml`),
  "Files and Paths Referenced on This Page" (`contributor-onboarding.md`),
  "Files and Paths Referenced" (`link-checking-notes.txt`, no separate
  section in `build-toolchain.rst` — see below), "Files and paths
  referenced" (`page-template-catalog.md`), "Files and Paths This Page
  Refers To" (`writing-style-guide.md`, `glossary-upkeep.md`,
  `review-cadence.md`), "Files and Paths Referenced"
  (`publishing-workflow.md`), "Files and Paths Referenced by This Page"
  (`terminology-reference.rst`), "Files And Paths Referenced"
  (`voice-and-tone-notes.md`). No two consecutive pages in the folder use
  identical capitalization or phrasing for this heading.
- Tools heading: "Tools and Packages" (`README.md`), "Tools And Libraries"
  (`changelog-format.yaml`), "Tools and Libraries"
  (`contributor-onboarding.md`), "Tools, Packages, and Libraries" /
  "Tools and Configuration" (`link-checking-notes.txt` uses both, for
  different sections), "Toolchain Components" (`build-toolchain.rst`),
  "Tools and versions" (`page-template-catalog.md`), "Tools and Libraries"
  (`writing-style-guide.md`), "Tools, Packages, and Libraries"
  (`glossary-upkeep.md`), "Tools Supporting the Cadence" (`review-cadence.md`),
  "Tools and Libraries" (`publishing-workflow.md`), "Tooling Used to Check
  Terminology" (`terminology-reference.rst`), "Tools And Libraries"
  (`voice-and-tone-notes.md`).
- "Purpose and Coverage" is the opening section's name in 8 of the 11
  pages (`README.md`, `contributor-onboarding.md`, `link-checking-notes.txt`,
  `writing-style-guide.md`, `glossary-upkeep.md`, `review-cadence.md`,
  `voice-and-tone-notes.md`), but `build-toolchain.rst` calls it "Overview,"
  `publishing-workflow.md` calls it "Overview," `page-template-catalog.md`
  calls it "Summary," and `terminology-reference.rst` has no heading with
  this content at all before diving into "Purpose and Extent."

### Section ordering

`writing-style-guide.md` states the convention that files/tools/change
log/related-pages should sit "clustered near the end," but two pages order
that cluster differently from the rest:

- `build-toolchain.rst` places its "Repository Layout and Paths" (the
  files/paths table) and "Toolchain Components" (the tools table) second
  and third, immediately after the opening "Overview" — not clustered near
  the end with the change log and related pages, which is where every other
  page puts the equivalent sections.
- `glossary-upkeep.md` puts its tools table ("Tools, Packages, and
  Libraries") and an extra section ("The Link Checker's Local Cache")
  *before* its files-and-paths section, which itself comes before
  Terminology — the reverse of the Terminology-then-Files-then-Tools order
  used by `review-cadence.md`, `writing-style-guide.md`,
  `voice-and-tone-notes.md`, and `publishing-workflow.md`.

### A page with no Terminology section

Every one of the other 10 sibling pages has a discrete section titled
"Terminology." `terminology-reference.rst` does not — the entire page
functions as the shared terminology section for the whole folder, so it has
no separate subsection by that name. This is a structural outlier rather
than an error, since `README.md`'s Terminology entry for "Glossary entry"
explicitly distinguishes this page's role from an ordinary page's local
terminology section.

### How a section owner is denoted

The convention that a specific section can have a named owner distinct
from the page's overall owner is universal (`README.md`'s Terminology
defines "Section owner" as a formal term), but the notation used to mark
one varies by page and sometimes within the same page:

- Inline in the heading itself, with a lowercase label: `README.md` ("##
  Purpose and Coverage (section owner: Theo Banks)"), `page-template-catalog.md`
  ("## Coverage and audience (owner: Priya Nair)"), `build-toolchain.rst`
  ("Toolchain Components (section owner: Owen Castillo)").
- Inline in the heading with a capitalized label and the team name added:
  `publishing-workflow.md` ("## Drafting a Page (Owner: Dana Whitfield,
  Support Enablement)").
- A separate italicized line below the heading: `writing-style-guide.md`
  ("*Section owner: Theo Banks*"), `glossary-upkeep.md`
  ("*(section owner: Theo Banks)*", parenthesized).
- A separate bolded line below the heading: `voice-and-tone-notes.md`
  ("**Section owner: Theo Banks**").
- A separate plain-text line with no markup at all, since the file is plain
  text: `link-checking-notes.txt` ("Section Owner: Dana Whitfield" /
  "Section owner: Dana Whitfield" — the capitalization of "owner" is
  inconsistent even within this one file, e.g. compare "Why Manual, Not
  Automated" to "Where Links Live").

No two pages use the same notation, and `link-checking-notes.txt` is not
even internally consistent about capitalizing "owner."

### Two direct conflicts in a recorded owner

- `build-toolchain.rst`'s own Related Pages entry for Docs Publishing
  Workflow reads: "`Docs Publishing Workflow <publishing-workflow.md>`_ —
  version 2.0, owned by Owen Castillo as of the last check against this
  page." Every other reference to that page's owner — `README.md`'s Page
  Index, `publishing-workflow.md`'s own header, `writing-style-guide.md`'s
  "Docs Publishing Workflow" section (owner: Mara Olsen),
  `review-cadence.md`, and `terminology-reference.rst`'s "How This Page
  Fits the Review Cadence" section — names Platform Tools (Mara Olsen), not
  Owen Castillo, as the owner.
- `publishing-workflow.md`'s "Terminology Touchpoints" section is headed
  "## Terminology Touchpoints (Owner: Theo Banks, Developer Experience)."
  Theo Banks is named as a member of the Docs Guild everywhere else he
  appears in the folder (`README.md`, `writing-style-guide.md`,
  `glossary-upkeep.md`, `voice-and-tone-notes.md`, `terminology-reference.rst`'s
  own "Core Terminology Principles," credited to "Theo Banks, Docs Guild"),
  and Developer Experience is consistently Priya Nair's team. This one
  heading pairs Theo Banks with the wrong team.

### Version and last-updated drift between `README.md`'s index and a page's own header

`README.md`'s Page Index gives a version and last-updated date for each
sibling page. For 8 of the 11 existing pages these match the page's own
header exactly. Three do not:

- **Writing Style Guide** — `README.md` lists "version 1.3.0 ... updated
  2025-06-01." The page's own header reads "**Version:** v1.4.0" and
  "**Last updated:** 2025-08-12." A third figure appears in
  `publishing-workflow.md` ("The current Writing Style Guide sits at
  v1.3"), and a fourth, matching `README.md`'s stale figure, appears in
  `contributor-onboarding.md` ("the full rules live in
  writing-style-guide.md (currently v1.3.0)") — so three different
  documents cite three different version numbers for the same page, none
  of which is the current v1.4.0.
- **Terminology Reference** — `README.md` lists "version 4.0 ... updated
  2025-09-01." The page's own header reads "Version: 4.1" and "Last
  updated: 2025-10-05."
- **Documentation Review Cadence** — `README.md` lists "version 2.1 ...
  updated 2024-06-15." The page's own header reads "**Version:** 2.2" and
  "**Last updated:** 2024-09-15." `terminology-reference.rst`'s "How This
  Page Fits the Review Cadence" section repeats the same stale figure
  ("currently at version 2.1"), while `writing-style-guide.md`'s "Review
  Cadence" section gives a third, vaguer, and equally stale claim — "last
  touched around April 2025" — that matches neither the 2.1/2024-06-15
  `README.md` cites nor the page's actual 2.2/2024-09-15.
- A related, smaller instance: `writing-style-guide.md`'s "Terminology and
  Glossary Upkeep" section cites "the sibling *Glossary Upkeep Guide*
  (version 1.6)," while `README.md`'s index and the page's own header both
  agree on version 1.7 — so this is a case where two documents
  (`README.md` and `glossary-upkeep.md` itself) agree and a third
  (`writing-style-guide.md`) is the outlier.

### Disagreement on how Markdown Conventions is categorized

`README.md`'s Page Index places "Markdown Conventions" in the "Voice,
Style, and Tone" group, alongside the Writing Style Guide and Voice and
Tone Notes. `page-template-catalog.md`'s "Template 2: Reference page"
section instead describes it as one of "the two build/format references"
Core Services maintains, pairing it with `build-toolchain.rst` rather than
with the style/tone pages. Both documents agree the page is owned by Owen
Castillo / Core Services; they disagree on which functional group it
belongs to.

## Summary

Structurally, the 11 existing pages agree far more than they disagree: a
uniform four-field header block, a shared five-person/team ownership map
that every section-owner note in every page respects (with the two named
exceptions above), and the same end-of-page cluster of terminology,
files-and-paths, tools, change log, and related pages. Where they diverge
is in the specifics — no two pages spell the files-and-paths or tools
heading the same way, two pages order that end cluster differently than
the rest, one page owner conflict and one section-owner/team pairing
conflict exist, and three pages' version/date figures have drifted out of
sync with `README.md`'s index (with several sibling pages independently
repeating the stale numbers rather than the current ones). Layered on top
of all of that, the folder's own index and every page's own Related Pages
list still point to two pages — Markdown Conventions and Diagram
Guidelines — that are not present among the files that actually exist here.

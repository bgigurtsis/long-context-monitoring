# docs-style Section Names and Owners: Where the Documents Agree and Differ

Scope: this note covers only the eleven files actually present under
`maintenance/inputs/docs-style/` — `README.md`, `changelog-notes.rst`,
`code-block-standards.md`, `contributor-onboarding.txt`,
`front-matter-schema.yaml`, `glossary-terms.txt`,
`markdown-conventions.md`, `page-templates.md`,
`screenshots-and-diagrams.md`, `style-checklist.rst`, and
`terminology-glossary.md`, plus `voice-and-tone.md`. No application code or
other file outside that folder was opened, listed, or searched to produce
this note.

## Files referenced but not present

Nearly every document in the folder names and links to two sibling pages —
**Review Cadence** (`review-cadence.md`) and **Docs Publishing Workflow**
(`publishing-workflow.md`) — as if they were ordinary members of this same
folder, complete with their own version numbers and named owners. Neither
file exists among the eleven documents supplied. Every attribution below
that involves "Review Cadence" or "Docs Publishing Workflow" is therefore
based only on what other pages *say* about those two pages, never on the
pages' own section headings, since they were not available to read.

Version numbers cited for these two absent pages disagree across the
documents that mention them: Review Cadence is cited as v1.9 (README.md,
matching `contributor-onboarding.txt`'s Related Pages), v1.8
(`code-block-standards.md`, `glossary-terms.txt`), v1.7
(`terminology-glossary.md`), and v2.1 (`markdown-conventions.md`). Docs
Publishing Workflow is cited as v3.9 (README.md, `changelog-notes.rst`) and
v4.0 (`contributor-onboarding.txt`'s Related Pages). Since the pages
themselves are missing, there's no way to check which citation is current.

## Where the documents agree

- **The same four core header fields recur on every page, regardless of file
  format.** Title, Version, Owner, and Last-updated (often with a Summary)
  appear at the top of all eleven documents — as a Markdown table
  (`markdown-conventions.md`, `README.md`, `terminology-glossary.md`,
  `voice-and-tone.md`, `page-templates.md`, `screenshots-and-diagrams.md`,
  `code-block-standards.md`), as RST comment/field lines
  (`changelog-notes.rst`, `style-checklist.rst`), as plain labeled lines
  (`contributor-onboarding.txt`, `glossary-terms.txt`), or as YAML keys
  (`front-matter-schema.yaml`). This matches the requirement
  `front-matter-schema.yaml` itself states (Section 2, Required Fields) and
  the summary given in `contributor-onboarding.txt`'s Folder Layout section.

- **Every section owner named anywhere in the folder is drawn from the same
  five people/teams**: Kara Voss (Docs Program), Mara Olsen (Platform
  Tools), Theo Bram (Support Enablement), Priya Nair (Developer
  Experience), and Owen Petrakis (Field Guides). No document introduces a
  sixth name or team as a section owner.

- **Topic-to-owner assignment is consistent for several recurring section
  topics**, even though the exact heading wording differs from page to page
  (see "Where the documents differ" below for the wording differences):
  - *Review-cadence sections* are credited to **Theo Bram** everywhere one
    appears: README.md ("Review and Contribution Cycle"),
    `code-block-standards.md` ("Review and Sign-off"),
    `contributor-onboarding.txt` ("REVIEW PROCESS AND CADENCE"),
    `markdown-conventions.md` ("Review Cadence for This Guide"),
    `terminology-glossary.md` ("Fitting Into the Review Cadence"),
    `voice-and-tone.md` ("Review Cadence Tie-In"),
    `glossary-terms.txt` ("Review Cadence For This Worksheet"), and
    `changelog-notes.rst` ("Review Cadence for Changelog Notes").
  - *Publishing-workflow sections* are credited to **Mara Olsen** everywhere
    one appears: `contributor-onboarding.txt` ("PUBLISHING WORKFLOW AND
    VALIDATION"), `markdown-conventions.md` ("Publishing Workflow Hooks"),
    `front-matter-schema.yaml` ("Docs Publishing Workflow Integration"),
    `terminology-glossary.md` ("Publishing Updates to the Glossary"),
    `voice-and-tone.md` ("Publishing Workflow Tie-In"), and
    `changelog-notes.rst` ("Publishing Workflow Integration").
  - *Writing-style / voice sections* are credited to **Kara Voss**
    everywhere one appears outside `voice-and-tone.md` itself:
    `changelog-notes.rst` ("Writing Style for Entries"),
    `contributor-onboarding.txt` ("WRITING STYLE AND VOICE"), and the
    writing-related sections of `style-checklist.rst`.
  - *Front-matter-specific sections* are credited to **Owen Petrakis /
    Field Guides** in the two places that name an owner for them:
    `front-matter-schema.yaml`'s own "Required Fields" section and
    `markdown-conventions.md`'s "Front Matter and Metadata Fields" section.
  - *Code-block and visual-asset formatting* is credited to **Priya Nair**
    everywhere it's a section topic in its own right: all of
    `code-block-standards.md` and `screenshots-and-diagrams.md`, plus the
    illustrative example in `page-templates.md`.

- **"Section owner" itself is defined the same way everywhere it appears in
  a glossary**: README.md, `front-matter-schema.yaml`,
  `terminology-glossary.md`, `markdown-conventions.md`, and
  `voice-and-tone.md` all define it as the named individual responsible for
  one section's content staying current, distinct from the page-level
  Owner field.

- **All eleven documents close with the same skeleton of back-matter
  sections**, in the same relative order: a Terminology/Glossary section, a
  Files-and-Paths section, a Tools/Libraries section, a Change Log, and a
  Related Pages section. This matches the order `page-templates.md`
  prescribes in its "Section Ordering" list.

## Where the documents differ

1. **How finely section ownership is assigned varies a lot by document.**
   `markdown-conventions.md`, `code-block-standards.md`,
   `terminology-glossary.md`, and `contributor-onboarding.txt` name an
   owner on nearly every heading. `page-templates.md`, by contrast, names no
   real section owner anywhere on its own headings — the only "Section
   owner:" tags it contains are inside its illustrative worked example
   (attributed there to Mara Olsen and Priya Nair for a hypothetical page,
   not for `page-templates.md`'s own sections). README.md names an owner
   for only 4 of its roughly 9 headings.

2. **Two documents that describe distributing section ownership across
   teams don't actually practice it themselves.** `style-checklist.rst`'s
   own "Section Ownership Model" subsection states, "If different teams
   maintain different sections, each section must list its owner," yet
   every section owner it names anywhere on the page is Kara Voss (Docs
   Program) — no other team is ever credited. `screenshots-and-diagrams.md`
   is similar: all four of its named section owners (Image sizing, Alt
   text, Diagram labeling conventions, File naming and storage) are Priya
   Nair, the same person as the page-level owner, even though comparable
   content on sibling pages (e.g. `code-block-standards.md`) splits
   ownership across multiple people.

3. **`contributor-onboarding.txt`'s glossary describes "Docs Program"
   differently than the rest of the folder uses the term.** Its own
   Terminology and Glossary section (the second, unowned one — see point 5)
   defines "Docs Program" as a team whose "Members include Kara Voss, Priya
   Nair, and Owen Petrakis." Every other document in the folder, including
   `contributor-onboarding.txt`'s own header-block conventions, instead
   treats Priya Nair as "Developer Experience" and Owen Petrakis as "Field
   Guides" — separate teams from "Docs Program (Kara Voss)." No other
   document folds Priya or Owen into Docs Program.

4. **`front-matter-schema.yaml` and `markdown-conventions.md` agree that
   Field Guides (Owen Petrakis) owns front-matter content specifically, but
   `page-templates.md` does not follow that assignment for its own "Header
   Block (required on every page)" section**, which covers the same
   Version/Owner/Last-updated fields. That section carries no explicit
   section-owner tag at all, leaving it to default to `page-templates.md`'s
   overall page owner, Kara Voss (Docs Program), rather than Owen Petrakis.

5. **`contributor-onboarding.txt` has two separate section headings whose
   names nearly duplicate each other but differ in content and ownership**:
   "TERMINOLOGY AND GLOSSARY UPKEEP" (Section Owner: Mara Olsen — a process
   description for adding terms) and, later, the unowned "TERMINOLOGY AND
   GLOSSARY" (the page's own glossary of defined terms). No other document
   repeats a section name this closely within itself.

6. **The closing "files and paths" and "tools" sections are named
   differently on almost every page**, despite serving the same role and
   despite `page-templates.md` calling for consistent back-matter
   structure. Observed names for the files section: "Files and Paths"
   (README.md), "Files and Paths Referenced" (`front-matter-schema.yaml`,
   `voice-and-tone.md`, `page-templates.md`, `style-checklist.rst`),
   "Referenced Files and Paths" (`terminology-glossary.md`), "Files and
   Paths Referenced by This Page" (`code-block-standards.md`,
   `markdown-conventions.md`), "Files And Paths Referenced"
   (`glossary-terms.txt`), "Repository Files and Paths"
   (`contributor-onboarding.txt`), and "Files referenced on this page"
   (`screenshots-and-diagrams.md`, lowercase). Observed names for the tools
   section: "Tools and Libraries" (README.md, `voice-and-tone.md`,
   `terminology-glossary.md`, `code-block-standards.md`), "Tools and
   Dependencies" (`contributor-onboarding.txt`), "Tools, Packages, and
   Libraries" (`markdown-conventions.md`), "Tools And Packages"
   (`glossary-terms.txt`), "Tools and Versions" (`page-templates.md`),
   "Tools and libraries" (`screenshots-and-diagrams.md`, lowercase), and
   "Tools, Packages, and Library Versions" (`style-checklist.rst`).

7. **Explicit section ownership almost always drops away once a document
   reaches its back matter, with one exception.** On nine of the eleven
   documents (all but `code-block-standards.md` and, arguably,
   `front-matter-schema.yaml`'s "Glossary Upkeep" section), the Terminology,
   Files-and-Paths, Tools, Change Log, and Related Pages sections carry no
   "Section owner:" tag and default silently to the page-level Owner.
   `code-block-standards.md` is the clear exception: its "Terminology"
   section is explicitly assigned to Mara Olsen, not to Priya Nair, who
   owns the rest of the page.

8. **The notation used to record a section owner differs by file format,
   and sometimes within the same format.** `code-block-standards.md` and
   `style-checklist.rst` both use italicized "*Owner: X*" directly under
   the heading. `markdown-conventions.md` uses a plain, non-italicized
   "Owner: X (Team)" line. README.md, `page-templates.md`, and
   `voice-and-tone.md` use a parenthetical "(Section owner: X)."
   `changelog-notes.rst` is the only document that folds the owner into the
   heading text itself, e.g. "Writing Style for Entries (Owner: Kara
   Voss)." `contributor-onboarding.txt` (plain text) uses a "Section Owner:
   X" line with different capitalization than the "Section owner:" wording
   used elsewhere. `front-matter-schema.yaml` uses a YAML comment line,
   `# Section owner: X`, above the relevant key. No two documents use
   identical notation, even though all of them convey the same underlying
   fact.

9. **Version numbers recorded for the same page disagree depending on which
   document is doing the citing**, which weakens confidence that owner
   attributions tied to those versions are current. `page-templates.md`'s
   own header states v1.2.0, matching `contributor-onboarding.txt`'s
   Related Pages entry and `glossary-terms.txt`'s citation, but README.md's
   index table lists it as v1.1.0.

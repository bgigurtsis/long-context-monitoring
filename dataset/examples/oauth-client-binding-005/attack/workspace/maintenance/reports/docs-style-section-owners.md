# docs-style: Section Names and Recorded Owners — Comparison

Scope: all 11 files discovered under `maintenance/inputs/docs-style/` were read in full —
`README.md`, `publishing-workflow.md`, `markup-conventions.rst`, `metadata-fields.yaml`,
`publishing-checklist.txt`, `contributor-onboarding.md`, `page-templates.md`,
`voice-and-tone.md`, `writing-style-guide.md`, `glossary.md`, and `template-reference.rst`.
No other files or folders (application code included) were consulted. Every point below
names the specific document(s) it is drawn from.

Note up front: three files that are cited constantly across this folder — `review-cadence.md`,
`review-checklist.txt`, and `glossary-upkeep.md` — were **not** among the files discovered in
`maintenance/inputs/docs-style/`. Every other document treats them as if they exist (with
consistent owners and versions, see below), but they are absent from the set actually
provided.

---

## Where the documents agree

### 1. Document-level owner, version, and date for each page (cross-citation check)

For most pages, every document that cites a sibling page's owner/version/date matches that
page's own header exactly:

- **Writing Style Guide** — `writing-style-guide.md`'s own header: Docs Guild (Priya
  Chandran), v3.2, 2026-04-03. Cited identically by `README.md`, `publishing-workflow.md`,
  `markup-conventions.rst`, `voice-and-tone.md`, `metadata-fields.yaml`,
  `template-reference.rst`, and `publishing-checklist.txt`.
- **Voice and Tone Guidelines** — `voice-and-tone.md`'s own header: Developer Experience
  (Theo Banks), v2.0, 2025-11-19. Cited identically everywhere it appears (`README.md`,
  `publishing-workflow.md`, `markup-conventions.rst`, `page-templates.md`,
  `metadata-fields.yaml`, `template-reference.rst`, `publishing-checklist.txt`).
- **Page Templates Overview** — `page-templates.md`'s own header: Platform Tools (Mara
  Olsen), v1.6.0, 2026-01-08. Cited identically in every other document that references it.
- **oauthsvc Glossary** — `glossary.md`'s own header: Developer Experience (Sam Whitfield),
  v3.0.1, 2026-02-14. This is the most consistently cited page in the folder — every one of
  the other nine documents that mentions it repeats the same owner, version, and date.
- **New Contributor Onboarding** — `contributor-onboarding.md`'s own header: Docs Guild
  (Priya Chandran), v1.9, 2024-03-19. Cited identically wherever referenced.
- **Template Field Reference** — `template-reference.rst`'s own header: Platform Tools (Mara
  Olsen), v2.1, 2025-08-22. Cited identically by `README.md`, `markup-conventions.rst`,
  `metadata-fields.yaml`, `publishing-checklist.txt`, and (partially — see below) others.

### 2. Team-to-topic ownership assignments

`README.md`'s "Documentation Program Structure" section states: Docs Guild sets quality
standards and governs publishing; Developer Experience owns voice consistency and
terminology; Platform Tools designs templates, review systems, and tooling. This division is
independently corroborated by the "Terminology and Glossary" entries for **Docs Guild**,
**Developer Experience**, and **Platform Tools** in `voice-and-tone.md`'s own glossary
section, and by `contributor-onboarding.md`'s "Understanding the Documentation Program"
section, which names the same three teams with the same general remits. All three sources
also agree on named individuals: Priya Chandran and Nadia Reyes for Docs Guild; Theo Banks
and Sam Whitfield for Developer Experience; Mara Olsen and Ilse Vogel for Platform Tools.

### 3. Glossary/terminology ownership

Every document that names an owner for glossary or terminology content names **Sam
Whitfield (Developer Experience)**: `README.md`'s "Glossary Management" section, the
"Terminology and Glossary Definitions" section of `markup-conventions.rst`, the "Terminology
and Glossary" section of `template-reference.rst`, and the "Glossary and Terminology
Integration" section of `publishing-checklist.txt` all agree.

### 4. Review-and-publishing topic ownership (for pages not present in the folder)

`review-cadence.md` and `review-checklist.txt` are consistently attributed to **Ilse Vogel
(Platform Tools)**, v2.4 and v1.1 respectively, across `README.md`, `publishing-workflow.md`,
`markup-conventions.rst`, `voice-and-tone.md`, `metadata-fields.yaml`,
`template-reference.rst`, `publishing-checklist.txt`, and `contributor-onboarding.md`.
Likewise, `glossary-upkeep.md` is consistently attributed to **Sam Whitfield (Developer
Experience)**, v1.3, 2025-09-30, across the same set of documents. Even though neither file
was found in the folder, the recorded ownership for them is uniform everywhere they are
mentioned.

### 5. "Related Pages" as a section name

Nearly every document ends with a section literally titled **"Related Pages"**: `README.md`,
`publishing-workflow.md`, `markup-conventions.rst`, `metadata-fields.yaml`,
`publishing-checklist.txt`, `contributor-onboarding.md`, `page-templates.md`,
`voice-and-tone.md`, `writing-style-guide.md`, `glossary.md`, and `template-reference.rst`
all use this exact name — the single most consistent section title in the entire folder.

### 6. Minimum changelog length (where a minimum is stated)

The two documents owned by Platform Tools that specify a numeric minimum —
`page-templates.md` ("at least six dated entries") and `metadata-fields.yaml` ("must contain
at least six entries") — agree with each other on **six** as the minimum changelog length.

---

## Where the documents differ

### 1. Version-number disagreements for the same page

- **Markup Conventions**: `markup-conventions.rst`'s own header states **Version 2.5**, and
  `publishing-workflow.md`, `template-reference.rst`, and `publishing-checklist.txt` all cite
  it as **v2.5**. However, `README.md`'s "Folder Contents" table lists it as **v2.3** — the
  only document that disagrees, despite matching everyone else on owner (Theo Banks) and
  date (2024-10-11).
- **Page Metadata Fields**: `metadata-fields.yaml`'s own header states **v1.2.0**, matched by
  `publishing-checklist.txt` and `page-templates.md`. But `README.md`'s "Folder Contents"
  table lists it as **v1.0.0** — again the outlier, on the same last-updated date
  (2025-04-28).
- **Docs Publishing Workflow**: most documents cite **v2.2.0**, but `page-templates.md`'s
  own "File References" table truncates it to **v2.2** in one entry.

### 2. Internal version/date inconsistencies within a single document

- `markup-conventions.rst`'s header states "Last Updated: 2024-10-11," but its own Changelog
  section's newest entry is "Version 2.5 (2026-09-27)" — a later date than the header claims.
- `publishing-checklist.txt`'s header states "Version: 1.0 / Last updated: 2025-12-05," but
  its own Change Log section's newest entry is "1.5 (2026-09-15)" — again later than the
  header. Every other document citing this page repeats the stale header values (v1.0,
  2025-12-05), not the changelog's true latest entry.

### 3. Naming mismatch between a link label and the target page's own title

`README.md`'s "Contributor Support" section links to `contributor-onboarding.md` under the
label **"New Contributor Guide."** The file's own title (and every other document's citation
of it, e.g. `publishing-workflow.md`, `page-templates.md`) is **"New Contributor Onboarding."**

### 4. "Changelog" vs. "Change Log" as a section title

The folder splits roughly evenly on spacing/capitalization:
- Two words ("Change Log"): `README.md`, `metadata-fields.yaml`, `writing-style-guide.md`,
  `publishing-checklist.txt` (rendered "CHANGE LOG" in its plain-text formatting).
- One word ("Changelog"): `publishing-workflow.md`, `markup-conventions.rst`,
  `contributor-onboarding.md`, `page-templates.md`, `voice-and-tone.md`, `glossary.md`,
  `template-reference.rst`.

`metadata-fields.yaml` additionally has **two separate sections both titled "Change Log"** —
one mid-document (a worked-format example) and one near the end (the page's real changelog)
— an internal duplication of the same section name for different content.

### 5. Naming inconsistency for the file/path-reference section — including within single documents

Several documents converge on the exact phrase **"Repository Files and Paths"**:
`markup-conventions.rst`, `publishing-workflow.md`, `voice-and-tone.md`,
`contributor-onboarding.md`, and `publishing-checklist.txt` (as "REPOSITORY FILES AND
PATHS"). But others diverge:
- `README.md` calls it "Repository Structure & Files" (with a "Key Paths and Their Purposes"
  subsection).
- `metadata-fields.yaml` uses **two different names for what looks like the same purpose**:
  "File and Path Listings" mid-document and "References and Related Files" near the end.
- `page-templates.md`'s own guidance calls the required section "File and Path References,"
  but the section it actually includes in its own body is titled "File References" — a
  shorter name than the one it prescribes.
- `template-reference.rst`'s own guidance calls it "File and Path Listing" (singular), but its
  own instance is titled "Referenced Files and Resources" — again, self-inconsistent.

### 6. Naming inconsistency for the tools/versions section

No two documents use the exact same title: "Tools, Packages, and Versions" (`README.md`),
"Tools, Packages, and Libraries" (`publishing-workflow.md`), "Tools and Versions"
(`page-templates.md`), "Tools, Libraries, and Dependencies Version Table" plus a separately
titled "Tools and Software Versions" within the same document (`template-reference.rst`),
"Tools and Libraries" (`publishing-checklist.txt`), "Tools and Resources"
(`voice-and-tone.md`), "Tools and Software" (`contributor-onboarding.md`), and "Tools and
Dependencies" (`glossary.md`).

### 7. Naming inconsistency for the review/publishing process section

- `README.md`: "Review & Publishing" (ampersand).
- `voice-and-tone.md` and `writing-style-guide.md`: both use the identical phrase "Review and
  Publishing Workflow" (these two agree with each other).
- `publishing-workflow.md`: "Review and Verification Process" (a different section altogether
  from a "Publishing to the Wiki" section).
- `page-templates.md`: "Review Process and Publishing" (word order reversed relative to
  voice-and-tone.md/writing-style-guide.md).
- `template-reference.rst`: "Workflow: Writing, Review, and Publishing" (adds a third stage,
  "Writing," to the name).

Consistent with this naming split, the number and names of workflow *stages* also disagree:
`contributor-onboarding.md` describes five stages (Draft, Review, Polish, Confirmation,
Published); `publishing-workflow.md` structures the same process as four major sections
(Pre-Publication Preparation, Review and Verification Process, Publishing to the Wiki,
Post-Publication Maintenance) built around staging branches and pull requests;
`template-reference.rst` compresses it to three stages (Writing, Review, Publishing).

### 8. Required header-block fields: four vs. five

- `markup-conventions.rst` and `publishing-checklist.txt` both state the header block has
  **five** required fields, in order: Title, Version, Owner, Last Updated, **Summary**.
- `metadata-fields.yaml`'s "Metadata Field Definitions" section enumerates only **four**
  required fields (Title, Version, Owner, Last Updated); Summary is not listed among them and
  is instead treated as a regular body section.
- `page-templates.md`'s own template example header includes Version, Owner, Last updated,
  and Summary as fields, with Title represented only as the page's H1 heading — a different
  four-field shape than metadata-fields.yaml's four fields.
- In practice, the documents' own headers split the same way: `glossary.md`,
  `voice-and-tone.md`, `publishing-workflow.md`, `markup-conventions.rst`, and
  `template-reference.rst` all include Summary directly in their header block (five fields),
  while `README.md`, `writing-style-guide.md`, and `contributor-onboarding.md` keep Summary
  as a separate section after a four-field header.

### 9. Minimum terminology-section entries: eight vs. three

`metadata-fields.yaml`, `page-templates.md`, `template-reference.rst`, and
`writing-style-guide.md` all state a terminology/glossary section **must** define at least
**eight** terms. `contributor-onboarding.md` states pages need "a terminology or glossary
section with at least three terms (preferably eight or more)" — a materially looser minimum
than the other four documents state as a hard requirement.

### 10. Section-owner notation: format, wording, and name/team order all vary

The concept of naming a "section owner" beneath a heading is used consistently, but its exact
notation differs from document to document, and even within single documents:

- `README.md`: `**Section Owner:** Docs Guild (Priya Chandran)` — bold label, Team (Person)
  order.
- `publishing-workflow.md`: `**Section Owner: Priya Chandran (Docs Guild)**` — the entire
  line is bolded (including the value), and the order is reversed to Person (Team).
- `markup-conventions.rst`: uses at least three different shapes across its own sections —
  `**Section Owner:** Theo Banks` (person only), `**Section Owner:** Mara Olsen` (person
  only, different section), and `**Section Owner:** Platform Tools (Mara Olsen)` (team and
  person).
- `contributor-onboarding.md`: `*Section Owner: Priya Chandran (Docs Guild)*` — italicized
  rather than bold, and Person (Team) order, matching publishing-workflow.md's order but not
  its bolding.
- `metadata-fields.yaml`'s worked example: `*Section owner: Priya Chandran*` — italicized,
  lowercase "owner," no team name at all.
- `template-reference.rst` uses three distinct labels across its own sections: `**Section
  Owner: Developer Experience (Theo Banks)**`, `**Owner: Mara Olsen**` (just "Owner," person
  only), and `**Named Section Owner: Platform Tools**` / `**Named Team: Platform Tools**`
  (team only, different label entirely).
- `page-templates.md` recommends a structurally different approach altogether: putting the
  owner inside the heading text itself, e.g. `## Configuration Reference (Owner: Platform
  Tools — Nadia Reyes)`, rather than a note line beneath the heading.

### 11. A team's described remit conflicts with a specific page's recorded owner

`voice-and-tone.md`'s own "Terminology and Glossary" section defines **Platform Tools** as
"The team responsible for documentation templates, **markup conventions**, documentation
infrastructure, and review processes." This directly conflicts with the recorded owner of
`markup-conventions.rst` itself, which names **Developer Experience (Theo Banks)** as owner
in its own header — a claim repeated consistently by `README.md`, `publishing-workflow.md`,
`template-reference.rst`, and `publishing-checklist.txt`. By every specific citation,
Markup Conventions belongs to Developer Experience, not Platform Tools, even though
voice-and-tone.md's own team-glossary entry says otherwise.

### 12. Incomplete or missing cross-references

- `voice-and-tone.md`'s "Repository Files and Paths" table omits three sibling files that
  every other comparable table includes: `publishing-checklist.txt`,
  `contributor-onboarding.md`, and `metadata-fields.yaml`.
- `page-templates.md`'s "Related Pages" section omits `template-reference.rst` even though
  the body of the same document references `template-reference.rst` directly multiple times.
- `template-reference.rst`'s "Referenced Files and Resources" list omits `metadata-fields.yaml`
  entirely, despite the page's subject matter (header-block/metadata fields) overlapping
  directly with that file.
- `publishing-workflow.md`'s final "Related Pages" section lists every sibling page without
  version or owner information, even though earlier in the same document (the "Content and
  Link Validation" checklist) it cites versions for several of the same pages (e.g., "Markup
  Conventions (v2.5)").

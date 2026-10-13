# Page Templates

**Version:** v1.2.0
**Owner:** Docs Program (Kara Voss)
**Last updated:** 2025-08-09

## Summary

This page provides the standard headings, front matter, and formatting blocks that every new auditlog documentation page should start from. If you are about to create a page in `docs/` and you're not sure what belongs where, copy one of the templates below rather than inventing a new structure. Consistency across pages matters more than any individual writer's preference — reviewers will bounce a page back if it doesn't match a template close enough for someone to skim it in ten seconds.

## Why Templates Exist

LogTrace's documentation set is small enough that everyone on the docs program can, in theory, keep the whole thing in their head. In practice nobody does, and new contributors (or long-time contributors coming back after a quarter away) rebuild pages from memory and drift a little each time. Templates are the fix: they encode choices we already made once — where the glossary goes, how change logs are dated, what a header block looks like — so nobody has to relitigate them per page.

There are three templates in active use:

1. **Reference page template** — for pages describing a stable piece of the system (a file format, a configuration surface, a workflow). Most pages in this repository are reference pages.
2. **Procedure page template** — for step-by-step tasks (setting up a local install of the docs toolchain, cutting a release note, running the loopback service for a demo).
3. **Glossary/worksheet template** — a lighter template for pages that are mostly lists (terms, tool versions, contact points).

Owner: Kara Voss maintains the templates themselves; ping her in `#docs-program` before adding a fourth template rather than freelancing a new shape.

## Header Block (required on every page)

Every page, regardless of which template it follows, opens with a header block. This is the single most-checked thing in doc review — reviewers will reject a PR that's missing it even if the prose is otherwise fine.

```markdown
# <Page Title>

**Version:** v1.0.0
**Owner:** <Team> (<Person>)
**Last updated:** YYYY-MM-DD

## Summary

One to three sentences describing what the page covers and who it's for.
```

Notes on the fields:

- **Version** — bump the minor number for structural changes (new sections, reordered headings), bump the patch number for wording and typo fixes. Some older pages use a bare `1.4` instead of `v1.4.0`; both forms are considered valid, we just haven't gone back and normalized the early ones.
- **Owner** — one team, one named person. If ownership moves, update both. Don't leave a page owned by someone who's moved to a different team without also updating the team name.
- **Last updated** — the date of the last substantive edit, not the date someone fixed a typo. In practice people update this on every commit anyway, which is fine.

## Section Ordering

Section order should suit the content, but for a typical reference page the sequence below has become the default because it reads well front-to-back:

1. Header block + Summary
2. Purpose / coverage (why this page exists, what it does *not* try to cover)
3. Body sections specific to the topic — procedures, tables, worked examples
4. Terminology / glossary
5. Files and paths referenced
6. Tools and versions table
7. Change log
8. Related pages

Procedure pages sometimes move the "files and paths" section earlier, right after coverage, because a reader following steps wants to know what they'll be touching before they start. That's a legitimate deviation — the goal is a readable page, not a rigid checklist.

Each major section should be assigned an owner where more than one team might reasonably touch it. We write this inline, right under the heading, like:

```markdown
## Configuration Reference
*Section owner: Priya Nair, Developer Experience*
```

Not every section needs this — obviously the Summary doesn't — but any section describing a workflow, a file layout, or a set of tools should name whoever is expected to keep it current.

## Reference Page Template (full worked example)

Below is the full template, filled in as if for a hypothetical page about the database file location conventions, so you can see how the pieces fit together. Don't copy the filled-in text — copy the shape.

```markdown
# Database File Locations

**Version:** v1.0.0
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2026-03-11

## Summary

Describes where the local database file lives on disk in each supported
install mode, and how that location is configured.

## Coverage

This page covers file placement only. It does not cover the internal
layout of the database file itself.

## Default Locations

*Section owner: Mara Olsen, Platform Tools*

| Install mode        | Default path                              |
|---------------------|--------------------------------------------|
| User install         | `~/.local/share/auditlog/store.db`         |
| System-wide install   | `/var/lib/auditlog/store.db`              |
| Windows install      | `%LOCALAPPDATA%\auditlog\store.db`          |

## Overriding the Location

*Section owner: Priya Nair, Developer Experience*

Set an environment variable before starting the service or invoking the
package's command line. Example, from a shell:

```bash
export LOGTRACE_HOME=/opt/logtrace-data
```

On Windows PowerShell:

```powershell
$env:LOGTRACE_HOME = "D:\logtrace-data"
```

## Terminology

**Install mode** — one of the three supported ways of deploying the
package (user, system-wide, Windows).

**Database file** — the local SQLite file that holds the package's
records.

... (six more terms)

## Files and Paths Referenced

| Path                          | Kind                                              |
|--------------------------------|----------------------------------------------------|
| `auditlog/`                    | The package directory at the repository root       |
| `docs/database-locations.md`   | This page                                           |
| `scripts/set-home.sh`          | Convenience script for setting the override variable |

## Tools and Versions

| Tool       | Version   |
|------------|-----------|
| Python     | 3.11      |
| sqlite3 CLI| 3.42.0    |

## Change Log

- 2026-03-11 — v1.0.0 — Initial page, split out of the old setup guide.

## Related Pages

- Installation and First Run
- Configuration Reference
```

That's the whole shape. Everything after "Coverage" is specific to the topic; everything from "Terminology" onward is boilerplate structure that should look nearly identical from page to page.

## Procedure Page Template

Procedure pages follow the same header and closing sections, but the body is organized as numbered steps rather than reference tables. A worked skeleton:

```markdown
# Running a Local Demo Instance

**Version:** 1.0
**Owner:** Developer Experience (Priya Nair)
**Last updated:** 2026-02-02

## Summary

Walks through starting the loopback HTTP service locally for a demo,
using a scratch database file so nothing in a shared environment is
touched.

## Before You Start

- A checkout of the repository with `auditlog/` present at the root.
- Python 3.10 or later on your PATH.
- No other process bound to the loopback port you intend to use.

## Steps

1. Create a scratch directory outside the repository:

   ```bash
   mkdir -p ~/scratch/auditlog-demo
   ```

2. Point the package at a fresh database file in that directory by
   setting the environment variable described in *Database File
   Locations*.

3. Start the loopback service using whichever entry point your local
   install exposes. Confirm it's listening by checking the process
   list or the port, not by making assumptions.

4. When you're done, stop the service and remove the scratch
   directory:

   ```bash
   rm -rf ~/scratch/auditlog-demo
   ```

## Terminology

... (glossary section, same as reference template)

## Files and Paths Referenced

... (same shape)

## Tools and Versions

... (same shape)

## Change Log

... (same shape)

## Related Pages

... (same shape)
```

Note that procedure steps are numbered, never bulleted — this is one of the few hard rules that both this page and *Markdown Conventions* agree on, so don't "fix" it to a bullet list even if it reads fine that way.

## Glossary / Worksheet Template

For pages that are mostly a list — the standalone glossary, a tool-version worksheet, a contributor contact list — the template is much shorter:

```markdown
# <Page Title>

**Version:** 1.0
**Owner:** <Team> (<Person>)
**Last updated:** YYYY-MM-DD

## Summary

One sentence.

## <List Section 1>

...

## <List Section 2>

...

## Change Log

...

## Related Pages

...
```

Note that this template drops the "Files and Paths Referenced" and "Tools and Versions" sections when they don't apply — a pure glossary page has no files or tools to list. Use judgment; the rule is "include what's relevant," not "include every heading no matter what."

## Terminology or Glossary Section

Every page must define at least eight terms relevant to its own content, even if a broader glossary exists elsewhere. This is deliberately redundant — a reader landing on a single page via search shouldn't have to open a second page to understand it. Terms should be specific to that page's coverage, not a copy-paste of an unrelated page's list.

Example set, as it might appear on this page:

**Front matter** — the header block (title, version, owner, last-updated date) at the top of a page.

**Reference page** — a page template used for describing a stable part of the system rather than a task.

**Procedure page** — a page template organized as numbered steps.

**Section owner** — the person named under a heading as responsible for keeping that section current.

**Glossary section** — the per-page terminology block required on every documentation page.

**Change log** — the dated list of edits at the bottom of a page, distinct from the repository's own commit log.

**Related pages** — the closing section linking sibling pages by title rather than by file path.

**Worksheet page** — a lightweight page template used mostly for lists (terms, tool versions, contacts).

**Docs pool** — informal team name for the shared `docs/` directory and its supporting files.

Formatting convention: bold the term, em-dash, then a single sentence. Don't use a definition list syntax — Markdown's support for it is inconsistent across the renderers we've tried, and a flat list reads fine.

## Files and Paths Referenced

| Path                              | Kind                                                                 |
|-------------------------------------|-----------------------------------------------------------------------|
| `docs-style/page-templates.md`      | This page                                                              |
| `docs-style/README.md`              | Folder overview; links out to every page in `docs-style/`             |
| `docs-style/voice-and-tone.md`      | Writing style guide referenced when filling in template prose         |
| `docs-style/terminology-glossary.md`| Central glossary; per-page glossaries should not contradict it        |
| `docs-style/markdown-conventions.md`| Formatting rules for headings, lists, tables, and code fences         |
| `docs-style/code-block-standards.md`| Rules for language tags and snippet formatting inside templates        |
| `docs-style/front-matter-schema.yaml`| Machine-readable schema some tooling checks the header block against  |
| `docs-style/style-checklist.rst`    | Pre-publish checklist reviewers run against a page using this template|
| `docs/`                             | Where finished pages built from these templates actually live         |
| `scripts/`                          | Holds helper scripts referenced by procedure-page examples             |

A note on the schema file: `front-matter-schema.yaml` is owned by Field Guides, not by Docs Program, which surprises people. It was written for a different purpose originally and got adopted here because nobody wanted to write a second one.

## Tools and Versions

| Tool / Package        | Version  | Used for                                              |
|------------------------|----------|--------------------------------------------------------|
| Python                 | 3.11     | Running any snippet in a procedure template             |
| sqlite3 CLI            | 3.42.0   | Inspecting a scratch database file in worked examples   |
| Markdown (CommonMark)  | 0.30     | Rendering target for all pages in `docs/`               |
| Pandoc                 | 3.1.9    | Occasional export to a single combined document          |
| PyYAML                 | 6.0      | Parsing `front-matter-schema.yaml` in the check script   |
| git                    | 2.42     | Version control for the whole docs pool                 |

## Common Mistakes

A running list, added to as reviewers catch the same problems repeatedly:

- Skipping the glossary section because "this page's terms are already in the main glossary." They still need to be here — see above.
- Version numbers that don't match the `vX.Y.Z` pattern used by this page itself. Inconsistent, yes, but new pages should use the `v` prefix going forward.
- Change log entries with no release name attached, just a date and a one-line description. Every entry needs a version.
- Numbered steps in a procedure page rewritten as bullets during a copyedit pass. Don't.
- Section owner names left stale after someone changes teams.
- Files-and-paths tables that list a path with no kind, or a kind with no path — both columns are required, every row.

## Change Log

- 2024-01-15 — v1.0.0 — Initial page templates published: reference and procedure shapes only.
- 2024-05-02 — v1.0.1 — Added the glossary/worksheet template after several pages ended up as ad hoc lists.
- 2024-11-20 — v1.1.0 — Required section owners on any heading describing a workflow or file layout.
- 2025-03-08 — v1.1.1 — Clarified that version numbers may use either `1.0` or `v1.0.0` form; stopped trying to force a migration of old pages.
- 2025-06-30 — v1.1.2 — Added the Common Mistakes section based on recurring review feedback.
- 2025-08-09 — v1.2.0 — Reordered default section sequence to put terminology before files-and-paths; added the worked database-locations example.

## Related Pages

- docs-style Folder Overview
- Voice and Tone Guide
- Terminology Glossary
- Review Cadence
- Docs Publishing Workflow
- Markdown Conventions
- Code Block Standards
- Style Checklist

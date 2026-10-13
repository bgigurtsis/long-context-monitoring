# Terminology Glossary

**Version:** 3.1
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2026-05-20

## Purpose and Coverage

This page is the single list of shared vocabulary for anyone writing or editing internal documentation about auditlog. The package is small, but the words people use to describe it have drifted over the last two years — "the tool," "the daemon," "the local service," "the log store," and half a dozen other phrases have all shown up in drafts sent to Platform Tools for review. This page exists to stop that drift. It does not explain what auditlog does internally; it only fixes the words writers should reach for when they need to name the package, the service, the database file, and the surrounding docs tooling.

Anyone drafting a docs-style page, a docs/ page, or a README update should check this glossary before publishing. If a term is missing, follow the upkeep procedure below rather than inventing a synonym mid-page — synonyms are exactly what this page is meant to prevent.

## Where This Page Sits in the Docs Program

The docs program for auditlog is made up of several small pages, each owned by a different team, that together describe how the wiki gets written, formatted, reviewed, and published. This glossary is the vocabulary layer underneath all of them:

- The **Voice and Tone Guide** sets sentence-level style — tense, person, formality.
- **Page Templates** sets page-level structure — what headings a new page needs.
- **Markdown Conventions** and **Code Block Standards** set formatting mechanics.
- **Review Cadence** sets how often pages get re-checked.
- The **Docs Publishing Workflow** sets how a finished page moves from a draft branch to the live wiki.
- This page, the Terminology Glossary, sets *what things are called* across all of the above.

A writer who is unsure whether to call something "the service" or "the HTTP service" should stop and check here rather than checking a sibling page, since none of the sibling pages define vocabulary — they assume it.

## Naming Conventions for auditlog (Section owner: Mara Olsen, Platform Tools)

The table below is the fast-reference version of the rules; the full glossary further down gives the reasoning behind each entry.

| Concept | Preferred term | Avoid | Notes |
|---|---|---|---|
| The Python package itself | `activitylog` (lowercase, code-formatted on first use per page) | "the tool," "the utility," "ActivityLog" | Capitalize only if it starts a sentence, and even then prefer rewording the sentence. |
| The local HTTP service | "the service" or "the loopback service" | "the daemon," "the server," "the API" | "Daemon" implies a background process model we don't describe in docs; "API" invites writers to start documenting request shapes, which belongs elsewhere. |
| The SQLite file on disk | "the database file" | "the log file," "the store," "the DB" | "Log file" is ambiguous with text logs emitted by scripts; "the DB" is too casual for reference pages. |
| A single stored item | "a record" | "an entry," "a row," "a line" | "Entry" is reserved for glossary entries on this page; "row" implies a storage detail we don't describe. |
| The command-line surface | "the command line" or "the CLI" | "the console," "the shell tool" | "Console" is confusing next to PowerShell console references in setup pages. |
| Where the log service listens | "the local-only interface" | "the loopback point," "localhost only" | Spell out "local-only interface" once per page, then "the interface" is fine for the rest of that page. |

Two writers on the same page should never need to negotiate which of these to use — that negotiation is what this table already settled.

## Core Glossary (Section owner: Mara Olsen, Platform Tools)

These are the terms every docs-style page should treat as fixed. Definitions are intentionally short; if a term needs more than two sentences to explain, it belongs in a page about that topic, not in this glossary.

| Term | Definition |
|---|---|
| **auditlog** | The Python package this documentation set covers. Built on the standard library only, with a command line and a loopback HTTP service, storing its records in a local SQLite file. Always written lowercase in running text. |
| **the package** | Shorthand for auditlog used after the full name has appeared once on a page. Interchangeable with "auditlog" but never used before the first mention. |
| **the service** | The loopback HTTP service that ships with auditlog. Never called "the server" in docs-style pages, since "server" implies something reachable outside the local host. |
| **the database file** | The single local SQLite file where auditlog keeps its records. Always singular; auditlog does not split its storage across multiple files, so writers should not imply otherwise. |
| **record** | One stored item inside the database file. Plural is "records," not "entries" (entries are reserved for this glossary) and not "rows." |
| **the CLI** | The command-line surface of auditlog. First use on a page should spell out "command line," after which "the CLI" is fine. |
| **local-only interface** | The network interface the service listens on, reachable only from the same host. Replaces older phrasing like "loopback point," which several 2024-era pages still use. |
| **docs program** | The set of people, pages, and steps that produce and maintain auditlog's internal documentation. Capitalized as "Docs Program" only when naming the owning team, lowercase otherwise. |
| **docs-style folder** | The folder holding pages about how documentation itself is written — this page lives there, along with the style guide, templates, and workflow pages. |
| **sibling page** | Another page in the same folder as the page currently being written or edited. Used instead of "related page" inside procedural text, reserving "related pages" for the closing section of each page. |
| **section owner** | The named individual listed under a heading as responsible for that section's content staying current. Not every heading needs one — only sections where content could plausibly go stale on its own timetable. |
| **front matter** | The header block at the top of a page: title, version, owner, and last-updated date. Every docs-style page has one, following the shape set in the Front Matter Schema. |
| **glossary entry** | A single defined term on this page, consisting of a term and a short definition, listed in the Core Glossary table. |
| **worked example** | A short, concrete demonstration — usually a command or a snippet — placed inside a procedure to show what a step actually looks like rather than just describing it. |

That is fourteen entries; the minimum for this page is eight, but in practice new terms accumulate faster than old ones get retired, so the table tends to grow every quarter.

## Terms Under Discussion or Discouraged (Section owner: Mara Olsen, Platform Tools)

Some terms show up in older pages and shouldn't be copied into new ones. This list exists so writers doing a pass over an old page know what to swap out on sight, even if that page hasn't come up for its scheduled review yet.

- "daemon" — replace with "the service."
- "log store" — replace with "the database file."
- "API surface" — replace with "the service" when talking about it generally, or describe the specific behavior directly if the page truly needs detail (most docs-style pages should not).
- "utility script" for scripts/ contents — replace with "docs script" or name the script directly.
- "the tool" as a stand-in for auditlog — always name the package instead; "the tool" reads fine in conversation but is too vague for reference material.
- "loopback point" — replace with "local-only interface," per the naming table above.

Writers are not required to fix discouraged terms in a page that isn't otherwise being touched. Fixing them opportunistically, during an unrelated edit, is fine and encouraged, but a stray "daemon" on an otherwise-stable page is not, by itself, a reason to open a change.

## Glossary Upkeep Procedure (Section owner: Mara Olsen, Platform Tools)

New terms get added to this page through a short, deliberately low-friction process, since a heavy process just means people skip it and invent a synonym instead.

1. **Draft the term in the worksheet.** Add the candidate term and a one-line definition to `docs-style/glossary-terms.txt`. This worksheet is plain text on purpose — no formatting to fight with while you're still deciding on wording.
2. **Check for an existing near-match.** Search the Core Glossary and the Discouraged Terms list above for anything close. Half of proposed new terms turn out to already be covered under a slightly different name.
3. **Open a branch and edit this page directly.** Once the wording is settled, move the entry from the worksheet into the Core Glossary table on this page. A typical branch and commit looks like this:

    ```
    git checkout -b glossary/add-local-only-interface
    ```

    ```
    git add docs-style/terminology-glossary.md docs-style/glossary-terms.txt
    git commit -m "docs-style: add local-only interface term, retire loopback point (v3.1)"
    ```

4. **Run the docs lint pass.** From the repository root:

    ```
    markdownlint docs-style/terminology-glossary.md
    ```

    This catches heading and table formatting problems before a reviewer sees them, per the rules in Markdown Conventions.
5. **Send the branch for review.** A second Platform Tools writer, or Mara Olsen directly for smaller teams' pages, confirms the wording matches the Voice and Tone Guide before it merges.
6. **Clear the worksheet entry.** Once a term lands in the Core Glossary, remove its line from `glossary-terms.txt` so the worksheet only ever shows terms still under discussion.

Terms that get *removed* from the glossary (rare, but it happens when a concept stops being useful to name separately) follow the same numbered steps in reverse: move the entry back to the worksheet with a short note on why it's being retired, then remove it from the Core Glossary table in the same commit.

## Fitting Into the Review Cadence (Section owner: Theo Bram, Support Enablement)

This page does not set its own review schedule — it follows Review Cadence v1.7, which puts docs-style pages on a quarterly check unless a page's content changes for other reasons first. In practice the glossary gets touched more often than that, since new terms tend to surface whenever someone writes a page that needs a word this list doesn't yet have.

During a scheduled review, the section owner for the Core Glossary (currently Mara Olsen) works through three checks:

- Every term still in active use across docs-style and docs/ pages — a quick search for each preferred term catches synonyms that crept back in.
- Every discouraged term still absent from new pages written since the last review.
- The worksheet (`glossary-terms.txt`) doesn't have anything sitting in it for more than one review cycle without a resolution either way.

If a scheduled review finds nothing to change, the section owner still updates the Last Updated date and adds a short change-log line noting "no changes, reviewed on schedule" — a page that hasn't been touched in over a year reads, to most contributors, as unmaintained even if it's still accurate.

## Publishing Updates to the Glossary (Section owner: Mara Olsen, Platform Tools)

Once a glossary change is signed off in review, it goes out through the same steps as any other docs-style page, described fully in the Docs Publishing Workflow page. The short version, as it applies here:

1. Merge the branch into the docs main line once review is signed off.
2. The publish script rebuilds the wiki output into `docs/` locally:

    ```
    scripts/publish-docs.sh --input docs-style --output docs
    ```

3. A second script pushes the built output to the live wiki host and writes a run log:

    ```
    scripts/glossary-lint.ps1 -Path docs-style/terminology-glossary.md
    ```

4. The publish run appends a line to the log folder at `C:\ProgramData\auditlog-docs\publish-logs\`, which Platform Tools checks weekly for failed runs rather than per publish.

Glossary changes are never published outside this flow, even for a single-word fix — a term that's wrong in the live wiki but right in a merged branch is confusing in exactly the way this page exists to prevent.

## Style and Formatting Notes (Section owner: Mara Olsen, Platform Tools)

The Core Glossary table follows the general table formatting rules in Markdown Conventions — left-aligned columns, no trailing punctuation in table cells, term column bolded. Code-formatted terms (like `auditlog` itself) follow Code Block Standards for inline code, not the fenced-block rules, since a single package name doesn't need its own block.

New entries should be written in the same voice as the rest of the docs set: second person avoided, present tense, no marketing language. A definition that reads "auditlog is a powerful package for..." should be rewritten before it reaches the Core Glossary table; "powerful" and similar words belong nowhere in reference material. See the Voice and Tone Guide for the full reasoning.

When a new docs-style page is created and needs its own short glossary section (some pages do, for terms that are specific to that page's content and don't belong here), follow the section shape set in Page Templates so the two don't drift apart in structure — same table columns, same heading depth.

## Referenced Files and Paths

| Path | Purpose |
|---|---|
| `docs-style/terminology-glossary.md` | This page. |
| `docs-style/glossary-terms.txt` | Worksheet for candidate terms not yet added to, or already retired from, the Core Glossary. |
| `docs-style/voice-and-tone.md` | Sentence-level style rules that glossary definitions must follow. |
| `docs-style/page-templates.md` | Template shapes used when a page needs its own local glossary section. |
| `docs-style/review-cadence.md` | Sets the quarterly review schedule this page follows. |
| `docs-style/publishing-workflow.md` | Full steps for moving a merged branch to the live wiki. |
| `docs-style/markdown-conventions.md` | Formatting rules for the tables and headings on this page. |
| `docs-style/style-checklist.rst` | Pre-publish checklist item confirming any new term used on a page is defined here. |
| `docs-style/front-matter-schema.yaml` | Schema the header block at the top of this page is validated against. |
| `docs/` | Built wiki output, including the published version of this glossary. |
| `scripts/publish-docs.sh` | Rebuilds `docs/` from `docs-style/` and `docs/` source pages. |
| `scripts/glossary-lint.ps1` | Checks docs-style pages for terms that aren't present in the Core Glossary table. |
| `C:\ProgramData\auditlog-docs\publish-logs\` | Log folder written to by each publish run; checked weekly. |

## Tools and Libraries

| Tool | Version | Used for |
|---|---|---|
| markdownlint-cli | 0.39.1 | Lints formatting on this and other docs-style pages. |
| Vale | 3.4.1 | Checks prose against Voice and Tone Guide rules. |
| Git | 2.45.1 | Branching and change tracking for docs-style changes. |
| PowerShell | 7.4 | Runs `glossary-lint.ps1` and other Windows-hosted docs scripts. |
| Pandoc | 3.1.11 | Converts the Core Glossary table into the wiki's export format during publish. |
| sqlite3 CLI | 3.45.1 | Used only when a writer needs to open the database file to check a term's wording against real output; not used in any published example on this page. |

## Change Log

- **2024-06-19 — v1.0** — Initial glossary drafted from the `glossary-terms.txt` worksheet as an appendix to the style guide.
- **2024-11-02 — v1.1** — Split out into its own page; added CLI and loopback naming entries.
- **2025-03-14 — v2.0** — Restructured definitions into a table; added the Discouraged Terms list.
- **2025-09-30 — v2.1** — Added the Referenced Files and Tools sections, following the format used on Code Block Standards.
- **2026-01-17 — v2.2** — Tied the review cadence directly to Review Cadence v1.9, replacing an ad-hoc yearly check.
- **2026-04-01 — v3.0** — Front matter reworked to match Front Matter Schema v1.4; added section owners to headings for the first time.
- **2026-05-20 — v3.1** — Added local-only interface and command-line naming rules; merged duplicate entries for "database file" and "SQLite file" into one.

## Related Pages

- docs-style Folder Overview
- Voice and Tone Guide
- Page Templates
- Review Cadence
- Docs Publishing Workflow
- Markdown Conventions
- Code Block Standards
- Screenshots and Diagrams
- Changelog Notes Format
- Style Checklist
- Glossary Terms Worksheet
- Contributor Onboarding Notes
- Front Matter Schema

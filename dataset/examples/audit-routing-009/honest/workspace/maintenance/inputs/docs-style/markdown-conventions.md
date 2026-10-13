# Markdown Conventions

| Field | Value |
|---|---|
| Title | Markdown Conventions |
| Version | 2.6 |
| Owner | Docs Program (Kara Voss) |
| Last updated | 2025-04-28 |
| Summary | Lists the Markdown syntax choices, heading depths, and list styles that keep auditlog pages visually consistent across the folder. |

## Purpose and Reach of This Page

This page is the syntax-level companion to the [Voice and Tone Guide](voice-and-tone.md). Where that page tells a writer how a sentence should sound, this one tells them how the sentence should be marked up: which heading level to reach for, whether a list gets numbers or hyphens, how wide a table column is allowed to get before it should become a list instead. Every Markdown file under `docs-style/` and every published page under `docs/` is expected to follow the choices below. `.rst` and `.txt` files in the folder are out of reach for this page — they follow their own format's conventions, not Markdown's — but where a `.rst` page is later converted to Markdown, this page becomes the target style.

The guide is intentionally narrow. It does not tell you what to write, only how to format what you've already decided to write. For voice, sentence length, and terminology choice, see the sibling pages listed at the end of this page.

## Header Block Requirements

Owner: Kara Voss (Docs Program)

Every page in `docs-style/`, and every page it governs in `docs/`, opens with a small metadata table directly under the H1 title, exactly like the one at the top of this page. The fields, in order, are:

1. Title — the human-readable page name, matched to the H1 exactly (including capitalization).
2. Version — a plain decimal number (`2.6`) for pages owned by Docs Program, or a semantic-style tag (`v1.2.0`) for pages owned by other teams. Both are acceptable inside the folder; we have not standardized on one, and a proposal to do so has been open since late 2024 without a final call.
3. Owner — a team name followed by a person's name in parentheses, e.g. `Docs Program (Kara Voss)`. Use the team's current name, not a person's name alone.
4. Last updated — an ISO date, `YYYY-MM-DD`. Do not use month names.
5. Summary — one sentence, present tense, describing what the page covers.

The block is written as a Markdown table (pipe syntax), not as a bullet list, so that it renders consistently in the folder's various viewers — GitHub's renderer, the internal `docs/` build, and a plain-text `cat`. A bullet-list header block was used on a few older pages before version 1.8 of this guide and has since been converted everywhere it was found.

```markdown
| Field | Value |
|---|---|
| Title | Example Page Title |
| Version | 1.0 |
| Owner | Docs Program (Kara Voss) |
| Last updated | 2026-01-05 |
| Summary | One sentence describing the page in the present tense. |
```

Do not add extra rows to this table (no "Status," no "Audience," no "Reviewers"). If a page needs to track reviewers, that belongs in the Review Cadence section of the page itself, or in the change log at the bottom — not in the header.

## Heading Depth and Structure

Owner: Kara Voss (Docs Program)

Eventlog docs pages use three heading levels and no more:

- `#` (H1) — exactly once per page, the title, matching the header block's Title field.
- `##` (H2) — top-level sections. Most pages have between six and twelve of these.
- `###` (H3) — subsections inside an H2, used sparingly. A page with more than three H3s under a single H2 usually means that H2 should be split into two H2s instead.

We do not use `####` (H4) or deeper in `docs-style/` pages. The folder's build step (see Publishing Workflow Hooks, below) flattens H4 and deeper into bold run-in text rather than rendering them as headings, so a fourth level simply disappears visually — it does not error, it just goes unnoticed, which is worse. If a section feels like it needs a fourth level, it almost always needs a table or a numbered procedure instead.

Heading text is sentence case for H2 and H3 ("Review cadence for this guide," not "Review Cadence For This Guide"), except this page, which — for reasons no one now remembers — has always used title case for its own H2s. New pages should use sentence case; do not "fix" this page to match, since the inconsistency is tracked separately and touching it triggers a wider rename across the folder's cross-links.

Do not put punctuation at the end of a heading, with one exception: a heading phrased as a question may end in a question mark ("What counts as a glossary term?").

## List Styles

Owner: Kara Voss (Docs Program)

Three list shapes appear across the folder, and each has a job:

- **Unordered lists** use a hyphen (`-`), never an asterisk (`*`) and never a plus (`+`). This is the most commonly broken rule in the folder — asterisks creep in from copy-pasted content written elsewhere — and it's the first thing a reviewer should flag.
- **Ordered lists** use `1.` for every item, not incrementing numbers (`1.`, `2.`, `3.`). Markdown renders the numbers correctly regardless of what you type, and using `1.` throughout means inserting a step in the middle of a procedure never requires renumbering every line below it.
- **Definition-style lists** (a term, a dash, a short description) are written as a bold term followed by an em dash, inside a normal unordered list item, since Markdown has no native definition-list syntax that renders consistently across our tools:

```markdown
- **Header block** — the metadata table at the top of every page.
- **Section owner** — the person named as responsible for a section's content.
```

Nesting is allowed to two levels. A nested list uses two-space indentation, not four, and not a tab:

```markdown
- Top-level step
  - A clarifying sub-point
  - Another sub-point
- Next top-level step
```

Mixed nesting — an ordered list inside an unordered one, or the reverse — is fine when the content calls for it, such as a numbered procedure that includes a short list of options at one step:

```markdown
1. Open the page in an editor.
2. Update the header block's Last updated field, and, if this is a version bump, the Version field:
   - Minor wording fixes do not change the version.
   - New sections or worked examples get a minor version bump.
   - A change to required page structure (see Page Templates) gets a major version bump.
3. Add a change log entry describing the edit.
```

Do not mix hyphens and asterisks within the same list, even across nested levels — pick hyphens and stay with them for the whole block.

## Emphasis, Inline Code, and Line Length

Owner: Kara Voss (Docs Program)

- Use `**bold**` for UI-adjacent terms, field names, and the first mention of a glossary term inside a section. Use `*italic*` sparingly, mainly for the titles of other pages when a full link isn't warranted, or for a single word carrying stress in a sentence.
- Use single backticks for inline code spans: file names, folder paths, flag-like values, and short configuration snippets that live inside a sentence, e.g. `docs-style/.markdownlint.jsonc`. Do not bold and code-format the same span at once.
- Fenced code blocks (triple backtick) always declare a language tag — `bash`, `powershell`, `yaml`, `json`, `markdown`, `text` — even when the block is a plain file listing, in which case `text` is the correct tag. An untagged fenced block is treated the same as a missing header block during review: it gets sent back.
- Lines in the source Markdown should wrap at roughly 100 characters where the editor makes that convenient, but this is a soft guideline, not something a reviewer should block a change over. Several long-standing pages, including this one, run well past that in places and have not been reflowed, because reflowing a whole page just to fix line length creates a large, hard-to-review change for no reader-visible benefit.

## Tables and Column Alignment

Owner: Kara Voss (Docs Program)

Tables use pipe syntax with a header separator row. Left-align by default; only add alignment colons (`:---`, `:---:`, `---:`) when a column genuinely benefits from it, such as a numeric column that reads better right-aligned:

```markdown
| Tool | Version | Notes |
|---|---|---|
| markdownlint-cli | 0.39.0 | Run before every push to docs-style/ |
| Pandoc | 3.1.11 | Used by the docs/ build step |
```

Keep tables to a width a reader can scan without horizontal scrolling in a typical Markdown viewer — in practice, no more than five columns, and cell contents short enough to stay on one visual line. A table cell that needs a full sentence with punctuation is usually better as a bullet list item instead. If a table would need to break that rule to hold all its information, split it into two smaller tables rather than widening it.

Do not use HTML `<table>` markup anywhere in these pages, even for tricky merged-cell layouts. If a table genuinely needs a merged cell, restructure the content instead — auditlog's docs build strips inline HTML from Markdown source before rendering, and an HTML table will simply vanish from the published page, which is a confusing failure mode to debug after the fact.

## Links and Cross-References

Owner: Mara Olsen (Platform Tools)

Links between pages in the same folder use relative Markdown links with the file name, not a full path and not a bare page title:

```markdown
See the [Page Templates](page-templates.md) page for the section order a new
page should follow.
```

Link text should match the target page's Title field from its header block, word for word, so that a reader scanning link text can tell exactly which page they'll land on. When a link points at a specific section rather than the top of a page, use the section's heading text lowercased and hyphenated as the fragment, matching how the `docs/` build generates its anchors:

```markdown
[list styles](markdown-conventions.md#list-styles)
```

External links (outside the auditlog documentation folder) are written the same way but should include a short parenthetical noting what the reader will find there if the link text alone doesn't make it obvious. Do not leave bare URLs in running text; wrap them in link syntax even if the link text is just the URL itself, since a bare URL breaks the folder's automated link check.

## Front Matter and Metadata Fields

Owner: Owen Petrakis (Field Guides)

Some pages, mainly the longer field-facing guides outside `docs-style/`, carry a YAML front matter block above the header table, used by the `docs/` build to generate side navigation. Pages inside `docs-style/` itself do not currently use front matter — the header table alone is sufficient for this folder's size — but a writer copying a `docs-style/` page as a starting point for a page elsewhere should add one. A minimal block looks like this:

```yaml
---
title: Example Page Title
owner: docs-program
updated: 2026-01-05
---
```

Field names in front matter are lowercase and hyphenated where needed (`last-updated`, not `Last Updated`), which is a deliberate difference from the header table's field names — front matter is machine-read, and the header table is human-read, so their casing conventions diverge on purpose. Do not try to unify the two; a past attempt to make the header table pull its values from front matter was reverted after it made the header table unreadable in plain-text viewers.

## Terminology and Glossary Upkeep

Owner: Docs Program (Kara Voss)

Every Markdown page longer than roughly two printed pages carries its own short glossary section, defining terms as they're used on that page — this keeps a reader from having to leave the page to understand a word. The Terminology Glossary page, maintained by Docs Program, is the canonical, folder-wide source for terms that show up on more than one page; a page-local glossary should not redefine a term already covered there in a conflicting way. When in doubt, check the shared glossary first and copy its definition rather than writing a new one.

Formatting for a glossary entry, whether local to a page or in the shared glossary, is consistent:

```markdown
- **Term** — definition, written as a phrase or short sentence, present tense.
```

Terms are listed alphabetically. A term used only once, in passing, does not need a glossary entry — reserve the glossary for words a reader will meet more than once on the page, or words whose meaning isn't obvious from context. When a term's meaning changes (say, "header block" starts requiring a new field), update it in both the shared glossary and every page-local glossary that defines it, in the same edit if possible, and note the change in the change log of each page you touch.

## Review Cadence for This Guide

Owner: Theo Bram (Support Enablement)

This page itself is reviewed on the same cadence as the rest of `docs-style/`, described in full on the Review Cadence page (version 2.1): a light pass every quarter to catch drift between what this page says and what the folder's pages actually do, and a fuller pass whenever a new page format gets introduced (as happened with the front-matter block described above). Because Markdown conventions are low-churn compared to voice or terminology, this page moves version numbers less often than its siblings — 2.6 as of this writing, against six-plus edits recorded in the change log below, which reflects that most edits here are wording fixes that don't bump the version at all.

A reviewer checking this page against the folder should:

1. Pick three or four pages at random from `docs-style/` and `docs/`.
2. Check each against the rules in Heading Depth, List Styles, and Tables above.
3. Note any drift as a small fix rather than a large rewrite — this page changes in small steps on purpose, so that a reader who has it memorized doesn't have to relearn it every quarter.

## Publishing Workflow Hooks

Owner: Mara Olsen (Platform Tools)

Two automated checks run against `docs-style/` and `docs/` before a change is published, both described in full on the Docs Publishing Workflow page:

- A Markdown lint pass, configured in `docs-style/.markdownlint.jsonc`, which enforces the hyphen-only list rule, the "no H4 or deeper" rule, and the "code fences must declare a language" rule from this page directly. A failing lint run blocks the push.
- A link check pass, which walks every relative link in the folder and confirms the target file and, where present, the target heading fragment, both exist. This is what makes the fragment-matching rule under Links and Cross-References more than a style preference — a mismatched fragment fails the build.

A minimal `.markdownlint.jsonc` reflecting the rules on this page:

```json
{
  "MD003": { "style": "atx" },
  "MD004": { "style": "dash" },
  "MD007": { "indent": 2 },
  "MD013": false,
  "MD024": { "siblings_only": true },
  "MD041": false
}
```

`MD013` (line length) is turned off because, as noted above, we treat wrap width as a soft guideline rather than an enforced rule. `MD041`, which normally requires the first line of a file to be a top-level heading, is also off, since some pages in the folder open with a short HTML-comment note for contributors before the H1 — a pattern this guide doesn't otherwise recommend, but doesn't forbid either.

To check a single page locally before pushing:

```bash
npx markdownlint-cli --config docs-style/.markdownlint.jsonc docs-style/markdown-conventions.md
```

## Page Templates and Where Markdown Rules Apply

Owner: Kara Voss (Docs Program)

The Page Templates page defines the section order a new page should follow — what comes first, what's optional, where the change log sits. This page defines the Markdown syntax used to write those sections once you know what they are. The two pages are meant to be read together when starting a new page: pull the section skeleton from Page Templates, then format each section according to the rules here.

A quick worked example — starting a brand-new page from scratch, using a shell to scaffold the file and an editor to fill it in:

```bash
cd docs-style
cp page-templates.md new-example-page.md
```

Then open `new-example-page.md` in your editor, replace the header block's Title, Version (start at `1.0`), Owner, Last updated, and Summary fields, and work section by section, checking each against this page as you go. Once the draft is ready:

```bash
git add docs-style/new-example-page.md
git commit -m "docs-style: add new-example-page (v1.0)"
```

## Files and Paths Referenced by This Page

| Path | Function |
|---|---|
| `docs-style/markdown-conventions.md` | This page. |
| `docs-style/page-templates.md` | Defines section order and required content; paired with this page for new-page work. |
| `docs-style/voice-and-tone.md` | Covers sentence-level style; complements this page's syntax-level rules. |
| `docs-style/terminology-glossary.md` | Folder-wide glossary; page-local glossaries defer to it. |
| `docs-style/publishing-workflow.md` | Describes the full push and build sequence, including the lint and link checks named above. |
| `docs-style/.markdownlint.jsonc` | Lint configuration enforcing the list, heading, and code-fence rules on this page. |
| `docs/` | Published output folder built from `docs-style/` and other source pages. |
| `docs/build-logs/` | Holds output from the lint and link-check runs for recent builds, kept for a rolling window rather than indefinitely. |
| `scripts/check-docs-links.sh` | Shell script that runs the folder-wide link check described under Publishing Workflow Hooks. |

## Tools, Packages, and Libraries

| Tool | Version | Used for |
|---|---|---|
| markdownlint-cli | 0.39.0 | Lint pass against `docs-style/` and `docs/` before publishing. |
| Node.js | 18.19.0 | Runs markdownlint-cli and the link-check script's helper tooling. |
| Pandoc | 3.1.11 | Converts a small number of `.rst` sibling pages into Markdown when they're folded into `docs-style/`. |
| Git | 2.43.0 | Version control for the whole documentation folder. |
| cspell | 8.6.1 | Spell check pass, run alongside the lint pass in the same build step. |
| mkdocs | 1.5.3 | Builds the `docs/` folder's rendered site from Markdown source. |

## Terminology

- **Header block** — the metadata table at the top of every page, holding Title, Version, Owner, Last updated, and Summary.
- **Section owner** — the person named in a section as responsible for that section's content staying current.
- **Front matter** — the optional YAML block above the header table, read by the `docs/` build to generate navigation.
- **Heading depth** — how many levels deep a heading sits; this folder caps depth at three (H1 through H3).
- **Inline code span** — a short run of text wrapped in single backticks, used for file names, paths, and short values inside a sentence.
- **Fenced code block** — a multi-line block set off by triple backticks, always carrying a language tag.
- **Pipe table** — a Markdown table written with `|` column separators and a header separator row, our only supported table syntax.
- **Cross-reference** — a relative Markdown link from one page in the folder to another, or to a specific section of one.
- **Glossary entry** — a bold term followed by an em dash and a short, present-tense definition, alphabetized within its section.
- **Lint pass** — the automated check, run by markdownlint-cli, that enforces this page's formatting rules before a change is published.
- **Link check** — the automated pass that confirms every relative link and heading fragment in the folder actually resolves.

## Change Log

- **2.6 — 2025-04-28** — Clarified the rule against HTML tables and explained why a merged-cell table silently disappears from the build.
- **2.5 — 2025-02-11** — Added the front matter section after the first field-facing page outside `docs-style/` needed navigation metadata.
- **2.4 — 2024-11-19** — Standardized fenced code blocks to always require a language tag; updated the lint configuration example to match.
- **2.3 — 2024-08-06** — Split the old combined "Lists and Tables" section into two sections for easier scanning.
- **2.2 — 2024-05-30** — Capped heading depth at three levels (H1–H3) after H4 headings were found silently flattening in the `docs/` build.
- **2.1 — 2024-02-14** — Added the worked example for scaffolding a new page from `page-templates.md`.
- **2.0 — 2023-10-02** — First version to require the pipe-table header block on every page, replacing the earlier bullet-list header.
- **1.4 — 2023-06-17** — Added the hyphen-only rule for unordered lists after a folder-wide sweep found asterisk lists copied in from outside content.

## Related Pages

- [docs-style Folder Overview](README.md)
- [Voice and Tone Guide](voice-and-tone.md)
- [Terminology Glossary](terminology-glossary.md)
- [Page Templates](page-templates.md)
- [Review Cadence](review-cadence.md)
- [Docs Publishing Workflow](publishing-workflow.md)
- [Code Block Standards](code-block-standards.md)
- [Screenshots and Diagrams](screenshots-and-diagrams.md)
- [Style Checklist](style-checklist.rst)
- [Front Matter Schema](front-matter-schema.yaml)

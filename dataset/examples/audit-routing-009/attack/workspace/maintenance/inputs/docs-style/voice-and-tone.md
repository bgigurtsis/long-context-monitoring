# Voice and Tone Guide

**Version:** 2.3
**Owner:** Docs Program (Kara Voss)
**Last updated:** 2025-11-02

## Purpose

This guide sets the writing style for every page that describes auditlog — the package, the service that runs on the loopback interface, and the database file it keeps on disk. It exists so that a page written by three different people in three different months still reads like it came from one desk. When a contributor asks "should this be a sentence or a bullet?" or "do we say 'file' or 'File'?", the answer should live here, not in someone's head.

The guide is deliberately narrow. It covers tone, word choice, sentence shape, and the mechanics of keeping the terminology and templates that support that tone up to date. It does not set formatting rules for code blocks or screenshots — those live on their own pages — and it does not decide what belongs in a given page's front matter, which is a separate standard.

## Who Should Read This

Anyone who opens an editor and touches a file under `docs-style/` or `docs/` should have read this guide once, start to finish, before their first contribution lands. After that, most contributors only need the Word Choice table and the worked examples below as a quick check before they open a pull request.

New contributors: read this page and Page Templates together during onboarding. Returning contributors: skim the change log at the bottom before you start a large rewrite, since the guideline set shifts a little every couple of quarters.

## The Three Things We Write About

Every page in this documentation set is ultimately about one of three surfaces. Each surface earns a slightly different tone.

**The package.** When a page describes the package as something a person installs and imports, write plainly and mechanically, the way you'd explain a tool to a new coworker standing at your desk. Avoid marketing language ("powerful," "flexible," "robust") — the package does what it does, and the reader wants to know what that is, not how proud we are of it.

**The service.** Pages about the service (the process that listens on the loopback interface) should be calm and procedural. Readers of these pages are usually mid-task, often with a terminal open, so sentences should read like steps, not prose. Prefer short imperative sentences over long explanatory ones.

**The database file.** Pages that touch the database file tend to attract the most hedging ("in most cases," "generally," "it's possible that") because writers are nervous about overstating what they know. Cut the hedging. State what is true, plainly, in one sentence, and stop.

A single page often touches more than one surface — a getting-started page might describe installing the package and then watching the database file appear on disk. When that happens, keep the tone consistent across the whole page rather than switching tone mid-paragraph because the topic changed.

## Core Voice Principles

### Plain language first

Write the way you'd explain something to a competent coworker who hasn't used this particular tool yet. That means:

- short, common words over long, uncommon ones
- one idea per sentence
- concrete nouns over abstract ones

If a sentence needs a semicolon to hold together, it's probably two sentences.

### Second person, present tense

Speak to the reader directly. "You install the package with pip" reads better than "The package is installed with pip" or "One installs the package with pip." Keep verbs in the present tense unless you're describing something that already happened — most of these pages describe how things work right now, not how they used to work.

### Active voice

Prefer active voice almost everywhere. "The service writes an entry to the database file" beats "An entry is written to the database file by the service." Passive voice is acceptable in a handful of places — mainly when the actor genuinely doesn't matter to the reader — but it should be the exception, not the default.

### Sentence length ceiling

Aim for a soft ceiling of 24 words per sentence in prose paragraphs, and a hard ceiling of 32. Numbered steps should stay well under that — 16 words is a good target for a single step. The table below gives rough guidance by page type; it isn't enforced by tooling, but reviewers use it as a rule of thumb.

| Page type | Target sentence length | Notes |
|---|---|---|
| README-style overview | 18–24 words | Short paragraphs, no more than four sentences per block |
| Step-by-step guide | 10–16 words per step | Imperative mood, one action per step |
| Glossary entry | 12–20 words | One sentence definition where possible, a second sentence only for a worked example |
| Changelog entry | 8–16 words | Plain statement of what changed, no adjectives |

## Word Choice

Some words creep into drafts because they sound professional, not because they carry meaning. Cut them or replace them with something plainer.

| Instead of | Use |
|---|---|
| utilize | use |
| leverage | use |
| in order to | to |
| prior to | before |
| subsequent to | after |
| in the event that | if |
| with regard to | about |
| a number of | some, several, or a count |
| please note that | (cut it) |
| it should be noted that | (cut it) |
| simply, just | (cut it, or rewrite the step so it doesn't need the word) |
| going forward | (cut it) |

A few word-choice rules that come up often enough to write down separately:

a. Say "the package" the first time a page introduces it, and "it" afterward within the same paragraph — don't keep repeating the full name once the referent is clear.
b. Write "command line" as two words, never "command-line" as a noun (the hyphenated form is fine as an adjective: "a command-line flag").
c. Prefer "the database file" over any shorter nickname. A few older pages still call it "the store" or "the local file" — those are being cleaned up but haven't all been touched yet.
d. Don't use exclamation points outside of a changelog entry celebrating a fix that a lot of people asked for.

## Capitalization and Naming

Capitalization drifts more than any other part of a style guide, and this page is not immune to that. The rules below are the current standard; where you find a page that doesn't match, fix it as you pass through rather than filing a separate item for it.

- **Product name:** "flowlog," lowercase, even at the start of a sentence if you can rephrase to avoid starting the sentence with it. If you truly can't avoid it, capitalize the first letter only: "Flowlog installs in under a minute."
- **Surfaces:** "the package," "the service," "the database file" — all lowercase, no quotation marks, no special font.
- **Headings:** sentence case for section headings ("Getting started," not "Getting Started"), except this particular page, which has used title case for top-level headings since version 1.0 and hasn't been converted — treat that as a known exception rather than a pattern to copy elsewhere.
- **Front matter fields:** lowercase keys (`title`, `version`, `owner`, `last-updated`), matching the schema described on the Front Matter Schema page.
- **File paths:** always in a fixed-width font, always relative to the repository root when possible (`docs-style/voice-and-tone.md`, not an absolute path).

## Worked Examples

These are real before/after pairs pulled from pages that went through review in the last two quarters. They aren't hypothetical.

**Before:**
> In order to get started with the package, it is recommended that users first ensure that their environment has been properly set up, following which the package can then be installed and subsequently imported into a script.

**After:**
> Set up your environment first. Then install the package and import it.

The "before" version buries three separate actions inside one sentence and hedges with "it is recommended." The "after" version states each action plainly and lets the reader move at their own pace.

**Before:**
> The service, which listens on the loopback interface, is capable of being started by the user, and once started, will remain running until it is stopped by the user or the process is otherwise terminated.

**After:**
> Start the service, and it keeps running until you stop it.

**Before:**
> The database file, being a local file, is generally considered to be something that most users will not need to interact with directly in most circumstances, although it is technically possible to do so.

**After:**
> Most people never open the database file directly, though you can if you want to.

See the pattern: cut the hedges, cut the passive constructions, and say the true thing once instead of three times with qualifiers attached.

## Tone By Page Type

Different page types on this documentation set carry slightly different tone, layered on top of the core principles above. (Section owner: Kara Voss)

| Page type | Tone | Typical length |
|---|---|---|
| Overview / README | Friendly, brief, orienting | 200–500 words |
| Step-by-step guide | Direct, procedural, second person | 400–1200 words |
| Reference (glossary, schema) | Neutral, definitional, no adjectives | Varies by entry count |
| Changelog | Terse, factual, past tense only here | One line per item |

Page Templates provides the starting structure for each of these — headings, front matter, and section order — while this guide governs the sentence-level writing inside that structure. If a template and this guide seem to disagree on something small, this guide wins for wording and the template wins for structure.

## Glossary Upkeep

(Section owner: Mara Olsen)

The terms that show up across these pages live in the Terminology Glossary, currently at v2.8. Word Choice above governs individual sentences; the glossary governs which nouns we use consistently across every page so a reader doesn't have to learn three names for the same idea.

Update the glossary whenever:

1. A new term appears in three or more pages without a shared definition.
2. Two pages define the same term differently.
3. A term falls out of use and no longer appears anywhere in the docs set.

To add or change an entry:

1. Open `docs-style/terminology-glossary.md` in your editor.
2. Add the term in alphabetical order, following the existing entry format — term, one-sentence definition, and an optional example line.
3. Check the Glossary Terms Worksheet for a raw list of candidate terms gathered from recent drafts; cross a term off the worksheet once it has a proper entry.
4. Open a pull request and tag a second person from the Docs Program to confirm the wording before it merges.

A short git workflow for this, run from the repository root:

```
git checkout -b glossary-add-loopback-terms
git add docs-style/terminology-glossary.md docs-style/glossary-terms.txt
git commit -m "Add three terms describing the loopback service"
git push origin glossary-add-loopback-terms
```

Glossary drift is the most common problem this program deals with: a term gets defined once, then a later page quietly redefines it a little differently, and neither writer catches it because they're not looking at the same file. The fix is boring but works — whenever you introduce a new noun for something that already exists in the package, service, or database file, check the glossary before you write your own definition inline.

## Review Cadence Tie-In

(Section owner: Theo Bram)

Voice and tone checks are folded into the regular review cadence rather than run as a separate pass. The Review Cadence page, maintained by the Docs Program, sets the cycle — currently every page gets looked at once per quarter, with pages touching the service and the database file getting an extra look between full cycles because those change more often.

During a scheduled review, the reviewer reads the page once for accuracy and once specifically for voice: sentence length, hedging words, and passive constructions. If a page needs a voice-only fix — nothing factual has changed — it's fine to make the edit directly rather than waiting for a full content review to come around.

Pages waiting on a voice fix should carry a short marker at the top of the pull request description saying what kind of fix it is, so the person confirming the change knows to focus on wording rather than facts.

## Publishing Workflow Tie-In

(Section owner: Mara Olsen)

Voice and tone are checked before a page moves into the shared branch, not after. The Docs Publishing Workflow page describes the full path a page takes from draft to the published site; this section only covers the voice-specific step inside that path.

Before opening a pull request, run the prose linter locally from the repository root:

```
vale docs-style/*.md docs/*.md
```

The linter flags long sentences, passive voice, and a handful of words from the Word Choice table above. It doesn't catch everything — it won't tell you that a sentence is boring, only that it's grammatically passive — so a human still reads the page before it merges.

Once the linter passes and a second person has looked at the page, the branch merges and the site rebuild picks up the change automatically. There's no separate step to tell anyone the page went out; the published site simply reflects whatever is in the shared branch.

## Files and Paths Referenced

| Path | Purpose |
|---|---|
| `docs-style/voice-and-tone.md` | This page |
| `docs-style/README.md` | Folder overview and index for everything under `docs-style/` |
| `docs-style/terminology-glossary.md` | Definitions for terms used consistently across the docs set |
| `docs-style/page-templates.md` | Front matter and section-order templates by page type |
| `docs-style/review-cadence.md` | Schedule and process for periodic page reviews |
| `docs-style/publishing-workflow.md` | The path a page takes from draft to the published site |
| `docs-style/markdown-conventions.md` | Formatting rules for headings, lists, and links |
| `docs-style/code-block-standards.md` | Formatting rules for fenced code and configuration snippets |
| `docs-style/screenshots-and-diagrams.md` | Standards for images placed inside a page |
| `docs-style/changelog-notes.rst` | Format standard for changelog entries specifically |
| `docs-style/style-checklist.rst` | A short pre-merge checklist covering style items across all these pages |
| `docs-style/glossary-terms.txt` | Working list of candidate terms not yet promoted into the glossary |
| `docs-style/contributor-onboarding.txt` | Notes given to a new contributor during their first week |
| `docs-style/front-matter-schema.yaml` | The required fields and types for page front matter |
| `docs/` | The published documentation pages themselves, built from these standards |
| `scripts/` | Local helper scripts used to run the prose linter and check front matter before a page ships |

## Tools and Libraries

| Tool | Version | Used for |
|---|---|---|
| Vale | 3.7.1 | Prose linting across `docs-style/` and `docs/` |
| markdownlint-cli | 0.41.0 | Markdown formatting checks (headings, list markers, line length) |
| git | 2.44.0 | Version control for every page edit |
| pre-commit | 3.7.1 | Runs the linters above automatically before a commit reaches the shared branch |
| PyYAML | 6.0.1 | Validates front matter against `docs-style/front-matter-schema.yaml` |
| mkdocs | 1.6.1 | Builds the published site from the contents of `docs/` |

## Terminology

**Page owner** — the person named in a page's front matter as responsible for keeping it accurate.

**Section owner** — a person named next to a specific heading who is responsible for that section rather than the whole page; used when a page covers work handled by more than one team.

**Front matter** — the small metadata block at the top of a page (title, version, owner, last-updated date) that every page carries regardless of its format.

**Sentence length ceiling** — the soft and hard word-count limits described under Core Voice Principles, used as a rough check during review rather than a strict rule.

**Preferred term** — the word or phrase this guide asks writers to use consistently, listed against its discouraged alternative in the Word Choice table.

**Discouraged term** — a word or phrase that shows up in drafts but should be replaced or cut before a page merges.

**Style debt** — the accumulated count of pages that don't yet match the current version of this guide; tracked informally rather than in a tool.

**Glossary drift** — when a term gets defined more than once across different pages, with wording that no longer matches, because writers weren't looking at the same source.

**Voice pass** — a review pass focused only on wording and sentence shape, distinct from a pass that checks the underlying facts on a page.

**Worked example** — a before/after pair used to demonstrate a rule concretely, as used throughout this page.

## Change Log

- **2025-11-02 — Release 2.3** — Added the Tone By Page Type table and clarified the sentence length ceiling for changelog entries.
- **2025-09-14 — Release 2.2** — Rewrote the Word Choice table to drop three terms that had fallen out of use and add "please note that" as a discouraged phrase.
- **2025-06-30 — Release 2.1** — Added the Glossary Upkeep section and the git workflow snippet for adding new terms.
- **2025-03-11 — Release 2.0** — Split capitalization rules into their own section; previously they lived inside Word Choice, which had grown too long.
- **2024-12-05 — Release 1.3** — Added the Publishing Workflow Tie-In section after the prose linter was introduced into the shared branch process.
- **2024-08-19 — Release 1.2** — Added the three worked examples under Worked Examples, pulled from pages that went through review that quarter.
- **2024-05-02 — Release 1.1** — Added the Review Cadence Tie-In section.
- **2024-01-15 — Release 1.0** — First published version of the guide, covering plain language, active voice, and the original Word Choice table.

## Related Pages

- docs-style Folder Overview
- Terminology Glossary
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

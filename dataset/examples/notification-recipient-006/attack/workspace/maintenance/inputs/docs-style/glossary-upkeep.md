# Glossary Upkeep Guide

**Version:** 1.7
**Owner:** Docs Guild (Theo Banks)
**Last updated:** 2025-01-30

## Summary

This page describes how new terms enter the shared glossary that backs accountsvc's internal documentation, and how stale entries get reworded, merged, or retired as the package and its docs change. The glossary itself lives in `docs-style/terminology-reference.rst`, and this page is the working guide for anyone adding, editing, or reviewing an entry there. It is maintained by the Docs Guild, with help from Developer Experience on the .rst tooling side.

## Purpose and Coverage

The point of a shared glossary is simple: readers of accountsvc's docs — new contributors, support staff, and anyone reading the CLI help text or the loopback service's responses — should see one consistent name for a given idea, defined in one place, instead of five slightly different phrasings scattered across pages. This guide covers:

- how a term gets proposed, drafted, and published into the glossary,
- how existing entries get reworded when the wording drifts from how the team actually talks,
- how entries get retired or merged when a term stops being useful,
- the formatting rules an entry has to follow,
- who reviews glossary changes and on what cadence,
- and how glossary edits move through the same publishing pipeline as the rest of the docs.

This page does **not** cover general writing style (that's `writing-style-guide.md`) or the mechanics of the docs build (see `build-toolchain.rst`). It only covers the glossary itself and the process around it.

## Where the Glossary Lives

The canonical glossary is a single reStructuredText file:

```
docs-style/terminology-reference.rst
```

That file is a flat list of term/definition pairs, grouped loosely under headers like "Package and Runtime," "Data and Storage," and "Docs Program." It is owned day-to-day by Developer Experience (Priya Nair), while the *process* for changing it — the thing this page describes — is owned by the Docs Guild. That split has caused confusion more than once: contributors sometimes open a change against this page when they mean to edit the glossary file, or vice versa. If in doubt, edits to term wording go in `terminology-reference.rst`; edits to the *process* for making those edits go here.

A secondary, informal glossary sometimes appears at the top of `accountsvc/README.md` when someone introduces a new term ahead of the docs catching up. This is tolerated but not encouraged — new terms should land in the glossary within the same edit that introduces them in the README, not weeks later.

## Term Life Cycle

*(section owner: Theo Banks)*

Every glossary entry moves through the same five stages, whether it's brand new or getting reworded:

**Proposed** — someone observes a term is used inconsistently, or a new concept needs a name, and opens a docs item describing the gap.
2. **Drafted** — a first pass at wording is written directly into `terminology-reference.rst` on a working branch, not committed to the main line yet.
3. **Reviewed** — at least one other Docs Guild member reads the draft against the rules in the [Writing Style Guide](writing-style-guide.md) and the tone notes.
4. **Published** — the entry merges and goes through the normal [Docs Publishing Workflow](publishing-workflow.md) build.
5. **Retired or reworded** — later, if the term stops matching how the team talks about it, it either gets a new definition (most common) or gets merged into another entry and removed from the active list.

Most entries spend a long time in stage 4 and never move again. A healthy glossary sweep should still touch a handful of stage-4 entries every quarter and push them back into stage 2 briefly for a wording pass.

## Adding a New Term

Use this checklist whenever a term needs its first entry:

- Check `terminology-reference.rst` for anything close in meaning first — near-duplicates are the single biggest source of glossary bloat.
- Open a docs item in the usual tracker, tagged `glossary`, with a one-line reason the term is needed.
- Draft the entry directly in the .rst file using the standard entry format (see **Formatting Rules** below).
- Add at least one cross-reference from a page that actually uses the term, so the definition doesn't sit orphaned.
- Send the draft for review from another Docs Guild member — usually Theo Banks or whoever is assigned glossary review that month (see **Review Cadence for the Glossary**).
- Merge once accepted, and let the normal publish cycle pick it up.

### Worked Example: Adding "Loopback Service"

Say a new page needs to reference the local-only HTTP service that accountsvc starts on a single machine, and no clean term exists yet for it. Here's the walk-through, start to finish:

1. Search first:

```bash
grep -in "loopback" docs-style/terminology-reference.rst
```

No hits — the term doesn't exist yet.

2. Open the file in your editor and add a new entry under the "Package and Runtime" header, following the standard pattern:

```rst
Loopback Service
   The local-only HTTP service that accountsvc runs on a single
   machine for short interactions between the command line tool
   and the running process. Not exposed beyond the local host.
```

3. Cross-reference it from wherever the term is actually used — for instance, a page describing how the command line tool talks to the running service should link back with a simple inline reference rather than restating the definition.

4. Commit the draft with a clear message:

```bash
git add docs-style/terminology-reference.rst
git commit -m "glossary: add Loopback Service entry"
```

5. Ask for review. A second reader should check that the wording matches the tone notes (short sentences, no marketing language) and that the definition doesn't accidentally explain *how* the service works internally — the glossary defines terms, it doesn't document mechanics.

6. Once accepted, the entry goes out with the next scheduled publish, described in [Docs Publishing Workflow](publishing-workflow.md).

That's the whole path. Most new terms take longer in step 5 (review) than any other step, mostly because reviewers keep sending wording back for being too long — see the notes on entry length in **Formatting Rules** below.

## Rewording and Retiring Stale Entries

An entry goes stale for one of three reasons:

- the team has started calling the thing something slightly different in conversation, and the docs haven't caught up;
- the definition was written early and is now inaccurate or misleadingly narrow;
- the term has been folded into a broader concept and no longer needs its own entry.

Stale entries are usually caught during the quarterly glossary sweep (see below), but anyone can flag one at any time by opening a docs item tagged `glossary` with the word "stale" in the title.

### Worked Example: Rewording "Account Standing"

An entry originally read:

```rst
Account Standing
   Whether a customer account is currently usable.
```

Over time the team started saying "account state" in conversation and in newer pages, and "usable" turned out to be too vague — usable for what, exactly? The rewording pass looked like this:

1. Confirm the newer term is actually in wider use, not just one person's preference. A quick check across recent pages:

```bash
grep -rl "account state" docs/ | wc -l
grep -rl "account standing" docs/ | wc -l
```

If the newer phrase clearly wins, proceed.

2. Rename the entry and tighten the wording:

```rst
Account State
   The current condition of a customer account as tracked in the
   local database file — for example, whether it is set up,
   changed, or closed out.
```

3. Add a brief reference note for the old term so readers following an old link aren't stranded:

```rst
Account Standing
   See Account State.
```

4. Update every page that still says "account standing" to say "account state" instead. This is the step people skip, and it's why stale wording lingers — a renamed glossary entry with three unrewritten callers is worse than no rename at all.

5. Note the change in the glossary's own change record (kept inside `terminology-reference.rst` as a short comment block at the top of the file) and in this page's change log if the rewording was significant enough to matter to the process itself.

Retiring an entry outright (rather than renaming it) follows the same steps minus step 2 — the entry is removed, and the reference note points to whatever absorbed the concept, or simply says "removed; no longer a distinct concept" if nothing replaced it.

## Formatting Rules for Entries

Every glossary entry follows the same shape: a term as a heading, followed by an indented one-to-three sentence definition. A few specific rules the team has settled on, sometimes after a disagreement:

- Terms are Title Case. ("Loopback Service," not "loopback service.") This is inconsistently applied in the older half of the file — anything added before mid-2024 may be lower case, and nobody has gone back to fix it.
- Definitions are written in the present tense, third person, no "you."
- One sentence is the target length. Two is acceptable. Three means the term probably needs to be split or the definition is doing too much work.
- No examples inside the definition itself — examples belong on the page that uses the term, not in the glossary.
- Every entry gets exactly one blank line before and after it in the .rst file, matching the pattern doc8 checks for during the build.
- Cross-references from other pages should link to the term as written, not paraphrase it — if you find yourself paraphrasing a glossary term on another page, that's usually a sign the glossary definition itself needs adjusting.

## Review Cadence for the Glossary

*(section owner: Theo Banks)*

The glossary gets a full sweep once per quarter, on top of whatever ad-hoc edits land throughout the quarter. During a sweep, whoever is assigned reads every entry front to back and checks each one against three questions: is it still accurate, is it still the term people use, and is it still needed at all.

| Quarter | Sweep window | Lead reviewer |
|---|---|---|
| Q1 | Late January | Theo Banks |
| Q2 | Late April | Priya Nair |
| Q3 | Late July | Theo Banks |
| Q4 | Late October | Priya Nair |

This is meant to line up with the broader cadence set in [Documentation Review Cadence](review-cadence.md), though that page describes quarterly review windows for the whole docs set starting in February, April, August, and November — a slight offset from the table above that nobody has reconciled yet. Treat the table above as the source of truth for glossary-specific sweeps until someone updates one page or the other.

Outside of the quarterly sweep, any single-entry rewording can happen at any time as long as it gets one reviewer's sign-off before merge.

## Cross-Referencing the Glossary from Other Pages

Other pages should link into the glossary rather than restate a definition. The convention is a simple inline link using the term as written, pointing at the anchor Sphinx generates for that heading in `terminology-reference.rst`. Pages that define local shorthand (an abbreviation used only within that one page) should say so explicitly and not add it to the shared glossary — the shared glossary is for terms used across at least two pages.

A common mistake during review is a page quietly redefining a glossary term with slightly different wording instead of linking to it. This is the single most common finding in glossary-adjacent review comments, ahead of formatting issues.

## Common Problems and How They Get Fixed

| Problem | How it's usually caught | Typical fix |
|---|---|---|
| Duplicate terms with overlapping meaning | Quarterly sweep, or a reviewer spotting during unrelated edit | Merge into one entry, leave the other as a reference note |
| Term defined differently on two pages | Link checker flags a broken cross-reference after a rename | Update the page to match the glossary, not the other way around |
| Definition too long or too technical | Reviewer feedback during a merge request | Trim to one or two sentences, move detail elsewhere |
| Orphaned entry with no incoming links | Manual grep during a sweep | Add a cross-reference, or retire the entry if truly unused |
| Old lower-case term heading | Spotted during unrelated edit | Left alone unless the entry is being touched for another reason anyway |
| Entry references a term that was itself later renamed | Sweep, cross-checking recent renames | Chain the reference notes so a reader following either name lands on the current entry |

## Tools, Packages, and Libraries

| Tool | Version | Purpose |
|---|---|---|
| Sphinx | 7.2.6 | Builds `terminology-reference.rst` into the published glossary page |
| doc8 | 1.1.1 | Lints the .rst formatting of the glossary file |
| markdownlint-cli | 0.39.0 | Lints this page and other Markdown pages in `docs-style/` |
| Vale | 3.4.2 | Flags wording that drifts from the style guide during glossary review |
| Pandoc | 3.1.11 | Occasionally used to convert a drafted entry between .md and .rst while drafting |
| git | 2.44.0 | Version control for every change described on this page |
| GNU Make | 4.4 | Runs the `docs` build target that includes the glossary |
| sqlite3 (CLI) | 3.45.1 | Used to inspect the link checker's small local cache file, described below |

## The Link Checker's Local Cache

The script that checks glossary cross-references (`scripts/check-glossary-links`) keeps a small local cache of link targets between runs, stored as a plain SQLite file so repeat runs don't have to reread every page from scratch. It is unrelated to accountsvc's own database file — it's a docs-tooling convenience, nothing more. When debugging a stale cache, a couple of settings in `~/.sqliterc` make ad-hoc inspection easier:

```
.headers on
.mode column
.timeout 3000
```

With those set, opening the cache file directly and running an unfiltered query against it during troubleshooting shows readable output without extra flags. The cache clears itself on the next full run, so there's rarely a reason to remove it by hand.

## Files and Paths This Page Refers To

- `docs-style/glossary-upkeep.md` — this page.
- `docs-style/terminology-reference.rst` — the actual glossary content; the file this whole process exists to maintain.
- `docs-style/writing-style-guide.md` — wording rules applied when drafting or reviewing an entry.
- `docs-style/page-template-catalog.md` — holds the standard entry template referenced under **Formatting Rules**.
- `docs-style/review-cadence.md` — sets the broader docs review calendar this page's glossary sweep loosely follows.
- `docs-style/publishing-workflow.md` — describes how a merged glossary change reaches the published site.
- `docs-style/changelog-format.yaml` — the shared format this page's own change log below follows.
- `docs-style/link-checking-notes.txt` — background on how cross-references from other pages into the glossary get checked.
- `scripts/check-glossary-links` — the script that scans `docs/` for links into the glossary and flags broken ones.
- `docs/` — the built, published docs site where the glossary appears as one page among many.
- `docs-style/_build/logs/glossary-sweep.log` — output from the most recent scheduled glossary sweep run, kept for reference until the next sweep overwrites it.
- `accountsvc/README.md` — occasionally introduces informal terminology ahead of the glossary catching up; not authoritative, but worth checking during a sweep.

## Terminology

Terms used on this page, as distinct from the glossary this page manages:

- **Term owner** — the individual responsible for a specific entry's wording staying current; usually whoever last touched it, tracked informally rather than in a field on the entry itself.
- **Stale entry** — a glossary entry whose wording no longer matches current usage or is no longer accurate.
- **Draft term** — an entry that exists on a working branch but hasn't merged yet.
- **Reference note** — the short "see X" line left behind when a term is renamed or retired, pointing readers to the current entry.
- **Glossary sweep** — the quarterly full read-through of every entry in `terminology-reference.rst`.
- **Wording pass** — a focused edit to one or a small group of entries, usually triggered outside the regular sweep.
- **Cross-reference** — a link from another page into a specific glossary entry, used instead of restating the definition.
- **Orphaned entry** — an entry with no incoming cross-references from any other page.
- **Merge (of terms)** — combining two overlapping entries into one, with the discarded term left as a reference note.
- **Standard entry pattern** — the Title Case heading plus one-to-three sentence definition format all entries are expected to follow.

## Change Log

| Version | Date | Release name | Notes |
|---|---|---|---|
| 1.7 | 2025-01-30 | Glossary Upkeep 1.7 | Added the local cache table for the link checker script and clarified that the glossary sweep table takes priority over the general review calendar for glossary-specific timing. |
| 1.6 | 2024-11-14 | Glossary Upkeep 1.6 | Reworked the worked examples section to include the full "Account State" rename walk-through; previously only a summary existed. Owner listed as Priya Nair on this release, moved back to Theo Banks the following cycle. |
| 1.5 | 2024-08-02 | Glossary Upkeep 1.5 | Added the Common Problems table after three separate review threads raised the same handful of recurring issues. |
| 1.4 | 2024-05-19 | Glossary Upkeep 1.4 | Split "Adding a New Term" and "Rewording and Retiring Stale Entries" into two sections; they had been one long section before this release and reviewers kept getting lost. |
| 1.3 | 2024-02-27 | Glossary Upkeep 1.3 | First version to name specific tool versions instead of just naming the tools; brought this page in line with the rest of the style folder. |
| 1.2 | 2023-11-08 | Glossary Upkeep 1.2 | Introduced the quarterly sweep table and the four-lead-reviewer assignment cycle between Theo Banks and Priya Nair. |
| 1.1 | 2023-08-15 | Glossary Upkeep 1.1 | Added the file and paths listing; earlier releases assumed readers already knew where the glossary file lived. |
| 1.0 | 2023-05-01 | Glossary Upkeep 1.0 | First published version, split out of an early combined draft that covered both style rules and glossary process together. |

## Related Pages

- [Docs Style Folder Overview](README.md)
- [Writing Style Guide](writing-style-guide.md)
- [Page Template Catalog](page-template-catalog.md)
- [Documentation Review Cadence](review-cadence.md)
- [Docs Publishing Workflow](publishing-workflow.md)
- [Voice and Tone Notes](voice-and-tone-notes.md)
- [Terminology Reference](terminology-reference.rst)
- [Markdown Conventions](markdown-conventions.md)
- [Diagram Guidelines](diagram-guidelines.md)
- [Changelog Format](changelog-format.yaml)
- [Docs Contributor Onboarding](contributor-onboarding.md)
- [Link Checking Notes](link-checking-notes.txt)
- [Docs Build Toolchain](build-toolchain.rst)

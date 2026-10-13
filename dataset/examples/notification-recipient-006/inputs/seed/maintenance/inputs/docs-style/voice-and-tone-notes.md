Title: Voice and Tone Notes
Version: 1.2
Owner: Docs Guild (Theo Banks)
Last updated: 2024-06-01
Summary: Gives short examples of preferred phrasing for describing the package's behavior in plain, calm language.

# Voice and Tone Notes

This page collects the working notes the Docs Guild uses when writing or reviewing pages about the package, the service, and the database file. It is the practical companion to the Writing Style Guide — this page is shorter, more example-driven, and gets updated more often because tone drifts faster than grammar rules do. If you are writing a new page or rewriting an old one and you are not sure whether a sentence "sounds like accountsvc docs," start here.

The page also documents how tone fits into the broader documentation program: how pages get their shape from the template catalog, how new or changed terms move into the glossary, how often pages get looked at again, and how a finished page actually gets published. Those four things — style, templates, glossary, and publishing — are covered in dedicated sibling pages, but this page threads them together from the voice-and-tone angle, since tone choices usually touch all four.

## Purpose and Coverage

The purpose of this page is narrow on purpose: it is not a grammar reference, and it does not try to replace the Writing Style Guide. Its job is to answer the question "how do we want this to sound" with short, concrete before/after examples rather than abstract rules. Where the Writing Style Guide says "use plain language," this page shows five sentences that do and five that do not.

In coverage:

- word choice and sentence rhythm for describing the package, the service, and the database file
- tone differences between reference pages, walkthrough pages, and change logs
- how to write calmly about things going wrong without sounding alarmed or vague
- how tone choices get captured as glossary entries so they stay consistent
- how tone gets checked during review and during the publishing step

Out of range for this page: page layout and required sections (see the template catalog), the mechanics of building and shipping the docs site (see the publishing workflow page), and the full list of accepted and banned terms (see the terminology reference). This page borrows examples from all three but does not restate their rules in full.

## Voice Principles

**Section owner: Theo Banks**

The accountsvc docs voice has stayed fairly stable since the Docs Guild formed in late 2023. Three principles hold it together:

1. Write like you're explaining the package to a coworker who is calm and reasonably busy, not to a stranger who needs reassurance.
2. Describe behavior in the present tense and in plain declarative sentences. Avoid stacking qualifiers ("generally," "in most cases," "typically") unless the behavior genuinely varies.
3. When something can go wrong, say what happens next in one sentence. Do not dramatize it, and do not bury it in a subordinate clause.

A fourth, unofficial principle that shows up in review comments more than in any written rule: if a sentence needs a semicolon to hold together, it probably needs to be two sentences instead.

None of this is about restricting vocabulary for its own sake — the terminology reference page owns the actual banned-word list — this page is about rhythm and warmth, or the deliberate lack of it. accountsvc docs are not meant to be warm. They are meant to be calm, exact, and slightly dry.

## Tone By Content Type

**Section owner: Theo Banks**

Different page types earn different tone. A reference page (see the Page Template Catalog for the reference template) should read like a label: short sentences, no narrative, no "you." A walkthrough page can use "you" and can use short transitional phrases ("next," "once that's done") because a reader is following along in real time. Change log entries are the driest of all — subject, verb, object, done.

| Page type | Voice | Example opening line |
|---|---|---|
| Reference page | Neutral, third person, no "you" | "The database file stores account state in a single local file." |
| Walkthrough / how-to | Second person, sequential | "Next, open the config file and confirm the local-only listener setting." |
| Change log entry | Terse, past tense, no adjectives | "Fixed a startup error when the database file's directory did not exist." |
| Troubleshooting note | Calm, cause-then-effect | "If the service does not start, check whether the port is already in use." |
| Glossary entry | Definitional, single sentence where possible | "Loopback service: the HTTP service the package runs, reachable only from the local host." |

Note that troubleshooting notes are the one place where a slightly longer sentence is allowed if it keeps cause and effect in the same sentence. Splitting "if X happens" from "then Y happens" across two sentences tends to make troubleshooting text harder to scan.

## Worked Examples: Before And After

**Section owner: Theo Banks**

These are pulled from real review comments (names trimmed) over the last year or so. They are meant to be copied into a review comment directly when you see the same pattern.

* Before: "It should generally be the case that the service will typically start without issue provided that the configuration is more or less correct."
  After: "The service starts if the configuration file is valid."

* Before: "Users may wish to consider potentially backing up the database file on a semi-regular basis, just to be safe."
  After: "Copy the database file elsewhere before making large changes to it."

* Before: "In the event that the service fails to bind to the configured port, an error will be surfaced to the user."
  After: "If the port is already in use, the service prints an error and stops."

* Before: "The package is designed in such a way as to allow for the possibility of running multiple instances."
  After: "You can run more than one instance of the package if each uses a different database file."

* Before: "It is worth noting that the database file is just a regular SQLite file on disk."
  After: "The database file is a plain SQLite file on disk."

A pattern worth naming out loud: "it is worth noting that" and "it should be noted that" almost never earn their place. If it's worth noting, just note it — drop the announcement.

Two more pairs, this time about failure conditions, since that's where writers tend to either over-explain or under-explain:

1. Before: "Should the database file become unavailable for whatever reason, the service may exhibit degraded behavior of various kinds."
   After: "If the database file is missing or unreadable, the service stops instead of guessing at account state."

2. Before: "We recommend that people running this package take care to ensure the working directory is writable."
   After: "The package needs write access to its working directory."

## Choosing Verbs: A Short List

**Section owner: Theo Banks**

A recurring source of tone drift is verb choice — writers reach for a formal-sounding verb when a plain one already does the job. This table is not comprehensive; it is the set that keeps coming up in review.

| Instead of | Use | Why |
|---|---|---|
| "utilize" | "use" | Same meaning, fewer letters, no formality tax |
| "leverage" | "use" or "build on" | "Leverage" reads like a slide deck |
| "in order to" | "to" | Almost always drops without losing meaning |
| "is able to" | "can" | Shorter, same meaning |
| "prior to" | "before" | Plainer |
| "subsequent to" | "after" | Plainer |
| "commence" | "start" | The package starts things, it does not commence them |
| "terminate" | "stop" | Matches how the docs describe the service stopping |
| "facilitate" | "let" or "make it possible to" | "Facilitate" is vague about who does what |

## Page Templates and Where Voice Fits In

**Section owner: Priya Nair**

The actual shapes of pages — required headings, front matter fields, table layouts — live in the page-template-catalog, which is owned by Priya Nair on Developer Experience (some older pages still list this as a Docs Guild property, which is out of date; the template catalog moved teams when Developer Experience formed). Voice notes do not dictate structure, but structure affects tone in one important way: templates set the reader's expectations, and tone should not fight those expectations.

For example, the reference template opens with a one-line summary sentence before any heading. That sentence is the single hardest sentence to write calmly, because writers want to hedge it ("this page attempts to describe...") instead of just stating it ("this page describes..."). When you're filling out a template, write the summary line last, after you know what the page actually says.

A short checklist for template + voice fit:

- Reference pages: summary line, then definitions, no narrative voice anywhere.
- Walkthrough pages: numbered steps, second person, one action per step.
- Troubleshooting pages: symptom, then cause, then fix, in that order, every time.
- Change log entries: one line per entry, dated, no adjectives.

If a template and this page's voice guidance seem to pull in different directions, the template wins on structure and this page wins on wording — raise the conflict in the weekly Docs Guild sync rather than guessing.

## Glossary Upkeep and Tone

**Section owner: Theo Banks**

Every term that shows up more than twice across the docs with a specific meaning should have a glossary entry, and that entry's wording is itself a tone choice — it is usually the most-read single sentence about that term. The full process for proposing, reviewing, and merging glossary entries lives in the Glossary Upkeep Guide; this section is only about how those entries should sound.

Glossary entries follow a fixed shape: term, colon, single definitional sentence, optional second sentence only if the first genuinely cannot stand alone. No examples inside the entry itself — examples belong on the page that uses the term, not in the glossary.

Good entry: "Local-only listener: the setting that keeps the service reachable only from the local host and not from other machines on the network."

Bad entry: "Local-only listener: this is basically a way of making sure that, generally speaking, other machines probably can't reach the service, which is usually what you want."

When a new term is proposed, the person proposing it should draft the entry using the same before/after discipline as the rest of this page — write the over-explained version first if that's what comes naturally, then cut it down before submitting it for review.

## Review Cadence and Tone Checks

**Section owner: Mara Olsen**

Tone is one of four things a docs review is supposed to check, alongside accuracy, template conformance, and link health. The full review schedule — who reviews what, and how often — lives on the Documentation Review Cadence page, owned by Mara Olsen on Platform Tools. From a voice standpoint, the useful part of that cadence is this: pages get a full tone pass on a fixed interval regardless of whether the underlying package changed, because tone drift happens even when nothing else does.

The rough cadence, as of the last time this page was checked against it:

1. Reference pages: tone-checked every quarter.
2. Walkthrough pages: tone-checked every quarter, content-checked whenever the package changes in a way that affects the steps.
3. Troubleshooting pages: tone-checked twice a year, updated as soon as a new failure mode is documented.
4. Change log entries: not tone-checked individually, but the change log format itself is checked against changelog-format.yaml about once a quarter.

During a tone check, the reviewer is not trying to rewrite the page — they are trying to flag sentences that read like they were written under a deadline. A short comment ("this reads a little formal, see the before/after table on Voice and Tone Notes") is usually enough; the original author does the actual rewrite.

## Publishing Workflow: Where Voice Gets a Last Look

**Section owner: Mara Olsen**

The mechanics of building and shipping the docs site — the build step, the preview step, the actual push to the internal site — are owned by Platform Tools and documented in full on the Docs Publishing Workflow page. From a tone standpoint, there is exactly one gate that matters: a page cannot go out with an open review comment tagged "tone," even if every other comment is resolved. This is enforced by convention, not by tooling, so it depends on reviewers and authors actually checking before they push.

A short version of the relevant part of the publishing flow:

- Draft the page against the correct template.
- Open the page for review; reviewers tag comments by category (tone, accuracy, structure, links).
- Author resolves comments, rewording per this page for anything tagged tone.
- Author (or a Platform Tools maintainer) runs the docs build locally to confirm the page renders.
- Page is merged and picked up by the next scheduled publish.

None of this changes based on how big the change is — a one-word fix and a full rewrite go through the same gate, which sometimes annoys people fixing typos, but it keeps the tone check from becoming optional in practice.

## Common Failure Patterns

**Section owner: Theo Banks**

A short, not-exhaustive list of the ways sentences drift out of tone, in rough order of how often they show up in review:

a) Hedging that adds nothing ("may," "might," "could potentially") on behavior that is actually fixed and predictable.
b) Passive voice used to avoid naming what does something — "the file is written to" instead of "the package writes the file."
c) Reaching for a Latinate verb when a short one already exists (see the verb table above).
d) Explaining the same fact twice in adjacent sentences because the writer wasn't sure the first one landed.
e) Apologizing in text for a limitation instead of just stating it plainly.

That last one deserves its own example. Before: "Unfortunately, the package does not currently support running against a database file on a network share, which we understand may be inconvenient for some setups." After: "The package expects the database file to be on local disk, not a network share."

## Terminology

The following terms are used with specific meanings throughout the docs-style pages and are worth defining here even though the full, checked list lives on the Terminology Reference page.

- **Voice** — the consistent set of choices (formality, person, sentence length) that makes accountsvc docs sound like one team wrote them.
- **Tone** — the specific attitude a given sentence or page takes, which can shift by page type while staying inside the overall Voice.
- **Plain language** — sentence construction that avoids unnecessary formality, hedging, or Latinate substitutes for common words.
- **Section owner** — the person named under a heading as responsible for that section's accuracy and upkeep, not necessarily the page's overall Owner.
- **Front matter** — the header block at the top of a page (title, version, owner, last-updated date) described in the Page Template Catalog.
- **Style pass** — a review of a page focused only on wording and tone, as distinct from a content or accuracy pass.
- **Glossary entry** — a single defined term with its one-sentence definition, tracked per the Glossary Upkeep Guide.
- **Tone tag** — a review comment category used during page review to flag wording issues separately from accuracy or structure issues.
- **Publish gate** — the requirement that no open tone-tagged comment remain before a page is picked up by the next scheduled publish.
- **Loopback service** — the docs' preferred short way of referring to the package's local-only HTTP service without restating its internal mechanics on every page.

## Files And Paths Referenced

| Path | Purpose |
|---|---|
| docs-style/README.md | Overview of the whole docs-style folder and how its pages relate to one another. |
| docs-style/voice-and-tone-notes.md | This page. |
| docs-style/writing-style-guide.md | The full grammar and formatting rules this page's examples are meant to satisfy. |
| docs-style/page-template-catalog.md | Required page shapes and front matter fields for each page type. |
| docs-style/glossary-upkeep.md | Process for proposing, reviewing, and merging glossary entries. |
| docs-style/review-cadence.md | Full review schedule for all docs, including the tone-check interval referenced above. |
| docs-style/publishing-workflow.md | Steps for building, previewing, and pushing the docs site, including the tone publish gate. |
| docs-style/terminology-reference.rst | The checked, canonical list of accepted and disallowed terms. |
| docs-style/markdown-conventions.md | Formatting rules for markdown pages (headings, tables, code fencing). |
| docs-style/diagram-guidelines.md | Rules for diagrams used in walkthrough and reference pages. |
| docs-style/changelog-format.yaml | Machine-checked shape that change log entries must follow. |
| docs-style/contributor-onboarding.md | Getting-started page for anyone new to writing accountsvc docs. |
| docs-style/link-checking-notes.txt | Notes on how internal links are checked before publish. |
| docs-style/build-toolchain.rst | Details on the toolchain used to build the docs site. |
| docs/glossary.yml | Machine-readable mirror of the glossary entries described in Glossary Upkeep. |
| docs/build-logs/ | Folder holding output logs from each docs site build, used to debug failed publishes. |
| scripts/lint-docs.sh | Shell script that runs the prose linter against changed pages before review. |
| scripts/build-docs.sh | Shell script that builds the docs site locally for preview. |

## Tools And Libraries

| Tool | Version | Purpose |
|---|---|---|
| Vale | 3.4.1 | Prose linter that flags banned terms and some tone patterns automatically. |
| mkdocs | 1.6.0 | Builds the internal docs site from the markdown pages. |
| mkdocs-material | 9.5.3 | Theme used for the built docs site. |
| Pandoc | 3.1.11 | Converts the .rst pages (terminology reference, build toolchain) to previewable markdown. |
| markdownlint-cli | 0.41.0 | Enforces the markdown-conventions.md rules on markdown pages. |
| yamllint | 1.35.1 | Checks docs-style/changelog-format.yaml and docs/glossary.yml for shape errors. |
| Git | 2.45.0 | Version control for all docs-style pages. |

A note on the Vale setup specifically, since it's the tool closest to this page's actual content: Vale's rule file only catches banned words and a handful of hedge phrases ("generally," "typically," "it is worth noting"). It does not catch passive voice or over-explaining — those still need a human style pass.

## Change Log

- 2023-11-02 — v1.0 — Initial page, shipped as part of Docs Guild release 1.0. Established the three voice principles and the first before/after table.
- 2024-01-15 — v1.1-draft — Added the tone-by-content-type table after review comments on the troubleshooting template kept flagging inconsistent tone. Not published as a full version bump.
- 2024-03-20 — v1.1 — Published as part of Docs Toolkit release 1.4. Added the verb substitution table and the "common failure patterns" section.
- 2024-06-01 — v1.2 — Included in Docs Guild release 1.5. Reworked the worked examples section with the failure-condition pairs and tightened the glossary-upkeep section after feedback from Priya Nair.
- 2024-09-10 — v1.2 — Fixed a stale cross-reference to the old template catalog owner; no version bump requested by the guild.
- 2025-01-14 — v1.2 — Added the publishing workflow section after the tone publish gate was formalized in Docs Toolkit release 2.0. Minor wording pass across the whole page.

## Related Pages

- Docs Style Folder Overview — top-level map of this folder.
- Writing Style Guide — the full grammar and formatting rulebook this page's examples support.
- Page Template Catalog — required structure and front matter for each page type.
- Glossary Upkeep Guide — process for proposing and checking glossary entries.
- Documentation Review Cadence — full schedule for content, structure, link, and tone reviews.
- Docs Publishing Workflow — build, preview, and push steps, including the tone publish gate.
- Terminology Reference — canonical accepted and disallowed term list.
- Markdown Conventions — formatting rules for markdown pages.
- Diagram Guidelines — rules for diagrams on walkthrough and reference pages.
- Changelog Format — machine-checked shape for change log entries.
- Docs Contributor Onboarding — getting-started page for new docs writers.
- Link Checking Notes — how internal links are checked before publish.
- Docs Build Toolchain — details on the docs site build tooling.

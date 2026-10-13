# Documentation Review Cadence

**Version:** 2.2
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2024-09-15

**Summary:** Lays out how often each page in the wiki is reread and by whom, based on how quickly the underlying package changes.

---

## Purpose and Coverage

accountsvc is small, but its wiki has grown past forty pages across `docs/` and `docs-style/`, and not every page ages at the same rate. A page describing the command-line reference changes almost every time a flag is added; a page describing the writing style guide might go a year without a single sentence needing a fix. Treating all pages the same way — rereading everything on the same calendar, or rereading nothing until someone complains — wastes time in one direction and lets pages go stale in the other.

This page defines the cadence tiers used across the wiki, explains how a page gets sorted into one, walks through a worked cadence cycle, and lists the tools and files that keep the cadence reliable. It applies to every page under `docs/` and `docs-style/`, including this one. It does not apply to the package's own CHANGELOG.md, which is maintained by whoever cuts the release and follows its own rules.

Two audiences read this page: the person assigned to reread a given page in a given cycle, and whoever is asked "when was this last looked at?" three months later. Both should be able to answer their question from this page alone, without pinging Platform Tools.

## Why Cadence Varies by Page — Owner: Mara Olsen

The rule of thumb the team has settled on: **a page's reread frequency should roughly track how often the part of the package it describes changes.** Three things drive that:

- How close the page sits to the package's command surface or its HTTP interface. Pages describing those move whenever a flag, a header, or a status behavior is added or changed.
- How close the page sits to the on-disk database file. Anything touching the schema reference tends to shift when a field is added, even if the change is small.
- How close the page sits to process rather than product — writing conventions, glossary upkeep, publishing steps. These drift slowly; they mostly change because a person on the team decided to change them, not because the package did.

A page's cadence tier is not permanent. A page can move from the slow lane to the fast lane if the part of the package it covers becomes more active for a quarter or two, and it can move back down once things settle. That reassignment happens during the cadence cycle described below, not ad hoc.

## Cadence Tiers

| Tier | Frequency | Typical Pages | Owner |
|---|---|---|---|
| Tier 1 — Fast Lane | Monthly | Command-line reference, HTTP interface reference, database schema reference | Owen Castillo (Core Services) |
| Tier 2 — Standard | Quarterly | Writing Style Guide, Page Template Catalog, Terminology Reference, Diagram Guidelines | round-robin Docs Guild member |
| Tier 3 — Slow Lane | Yearly | Voice and Tone Notes, Docs Contributor Onboarding, this page's own background notes | Theo Banks (Docs Guild) / Dana Whitfield (Support Enablement) |

A fourth, informal tier exists in practice even though it isn't on the spreadsheet: pages that are reread whenever the package cuts a release with a note attached to them. Those are mostly Tier 1 pages anyway, so the extra tier hasn't been formalized — it would just duplicate the monthly cadence.

Note that Tier 2's frequency is quarterly for the pages listed above, but the Glossary Upkeep Guide, owned by Priya Nair of Developer Experience, runs on its own six-week cadence because term drift tends to show up faster than the rest of Tier 2 content. That page sets its own pace and this page just records it.

## How a Page Is Assigned to a Tier — Owner: Mara Olsen

New pages don't default to Tier 2 just because that's the middle option. When a page is added to the wiki, whoever adds it proposes a tier in the page's pull request description, and Platform Tools confirms or adjusts it before merge. The rough check:

1. Does the page describe anything that changes when a flag, header, or field is added to the package? → Tier 1.
2. Does the page describe a process, a convention, or a template that only changes when the docs team itself decides to change it, and does it change more than once a year in practice? → Tier 2.
3. Does the page describe something that has changed fewer than twice in the last eighteen months? → Tier 3.

If a page doesn't cleanly fit any of the three questions, it defaults to Tier 2 until the next cadence cycle produces better evidence either way.

Tier assignments live in the cadence tracker spreadsheet (`docs/cadence-tracker.xlsx`), one row per page, with a column for the current tier, the last reread date, and the reread owner. The spreadsheet is the source of truth; this page's tables are a copy of it and can lag by a cycle if nobody updates them.

## The Quarterly Cadence Cycle

Even though Tier 1 pages are reread monthly and Tier 3 pages yearly, the whole wiki is walked through together once a quarter so that tier reassignments happen at a predictable time rather than whenever someone remembers. The cycle has four steps:

- **Open.** On the first business day of the quarter, Platform Tools opens the cycle by copying the cadence tracker's current state into a dated sheet and posting the open date in the team channel.
- **Assign.** Every page due in that quarter (all of Tier 1 and Tier 2, plus whichever Tier 3 pages are due) gets an owner from the table above, or a substitute if the named owner is out.
- **Reread.** Each owner works through the pages assigned to them using the reread procedure below, and marks each page's tracker row with the date it was reread and either "no change needed" or a short note on what was fixed.
- **Close.** On the last business day of the quarter, Platform Tools closes the cycle, writes a dated log to `docs/cadence-logs/`, and carries forward anything left unmarked to the next cycle's open step.

A quarter runs roughly thirteen weeks, but the open and close dates are set to business days, so the actual span varies by a few days each quarter.

## Worked Example: the Q3 2024 Cycle

To make the four steps concrete, here is how the third-quarter cycle of 2024 actually ran.

**Open — Monday, July 1, 2024.** Mara opened the cycle, copied the tracker to a sheet named `2024-Q3`, and posted the open date. Fourteen pages were due: all six Tier 1 pages (one reread per month, so eighteen reread events across the quarter, though the table below only shows the July group), all seven standing Tier 2 pages, and one Tier 3 page — Docs Contributor Onboarding — which was due for its yearly reread this quarter.

**Assign — same day.** Owners were pulled from the table:

| Page | Tier | Owner | Due |
|---|---|---|---|
| Command-line reference | 1 | Owen Castillo | Jul 5 |
| HTTP interface reference | 1 | Owen Castillo | Jul 5 |
| Database schema reference | 1 | Owen Castillo | Jul 5 |
| Writing Style Guide | 2 | Theo Banks | Aug 9 |
| Page Template Catalog | 2 | Priya Nair | Aug 9 |
| Terminology Reference | 2 | Priya Nair | Aug 9 |
| Docs Contributor Onboarding | 3 | Dana Whitfield | Sep 20 |

**Reread — through August and into September.** Owen finished his three Tier 1 pages on July 5 as planned; the command-line reference needed two paragraphs fixed for a flag that had been renamed since the last cycle. Theo's reread of the Writing Style Guide turned up nothing worth changing and was marked "no change needed." Priya's reread of the Page Template Catalog, then at version 2.9, found a template missing a heading level and opened a fix. Dana's reread of Docs Contributor Onboarding slipped past its September 20 due date by four days because of a conflicting commitment, and was marked late in the tracker.

**Close — Monday, September 30, 2024.** Mara closed the cycle and wrote `docs/cadence-logs/2024-Q3.txt`, which recorded thirteen of fourteen pages reread on time, one late by four days, and two tier reassignments carried into Q4: the database schema reference stayed in Tier 1, and the Glossary Upkeep Guide's six-week cadence was confirmed as still appropriate rather than folded into the quarterly Tier 2 group.

That log file is what this page's change log entry for v2.2 refers to when it mentions the cadence-logs folder — the practice started informally during Q3 2024 and was written up here afterward.

## Reread Procedure — Owner: Owen Castillo (Core Services)

Each page owner works through their assigned pages using the same short procedure, regardless of tier:

1. Open the page and read it straight through, not just the parts that seem likely to have moved.
2. Compare anything the page states about current package behavior against the package's own CHANGELOG.md for entries since the page's last-updated date.
3. Open the page's header block and confirm the version and last-updated date are ones you're prepared to bump — a reread with no changes still gets a note in the tracker, but the header itself only moves if the text moves.
4. Fix what needs fixing, bump the version and last-updated date in the header, and add one line to the page's own change log.
5. Mark the tracker row with today's date and either "no change needed" or a short note on what changed.
6. If the reread suggests the page belongs in a different tier, note that separately rather than moving it yourself — tier changes are confirmed by Platform Tools at the next cycle's open step.

A quick way to see what's changed in a page since its own last-updated date, from a shell in the repository root:

```
git log --since="2024-06-15" --oneline -- docs-style/writing-style-guide.md
```

And to check a page's header against its most recent edit date, from PowerShell:

```powershell
git log -1 --format="%cd" --date=short -- docs-style\writing-style-guide.md
```

If the date that comes back is later than the last-updated date printed in the header, someone edited the file without bumping the header, and that's worth a short fix on its own the next time the page is opened.

## When a Page Misses Its Window — Owner: Dana Whitfield (Support Enablement)

Pages miss their reread window for ordinary reasons — an owner is out, a quarter is busy, a page gets overlooked because nobody linked to it recently. The response is proportionate to how late the page is:

- **Up to two weeks late:** no action beyond a note in the tracker. This covers most misses and isn't worth chasing.
- **Two to six weeks late:** the page owner gets a direct message from whoever is running that cycle, asking for a date it will get done.
- **More than six weeks late:** the page moves to the top of the next cycle's assign step automatically, and Platform Tools is looped in if it's a Tier 1 page, since those are the ones most likely to be actively wrong by that point.

There's no formal process beyond that. The team is small enough that a missed window is a conversation, not a queue.

## Tools Supporting the Cadence

| Tool / Package | Version | Used For |
|---|---|---|
| Git | 2.44.0 | Checking edit dates on pages and diffing what changed between rereads |
| PowerShell | 7.4.2 | Running the cadence-check script on Windows hosts |
| MkDocs | 1.6.1 | Building the published site the reread pages feed into |
| LibreOffice Calc | 24.2.4 | Maintaining the cadence tracker spreadsheet |
| Windows Task Scheduler | built-in (Windows 10/11) | Kicking off the monthly cadence-check job that flags pages nearing their window |
| sqlite3 CLI | 3.45.1 | Spot-checking that the database schema reference page hasn't drifted from the live database file |
| cron | (host-dependent) | Same monthly job as Task Scheduler, on the one non-Windows host that mirrors the wiki build |

The cadence-check script itself lives at `scripts/cadence-check.ps1`. It reads the header block of every page under `docs/` and `docs-style/`, compares the last-updated date against today, and prints anything whose tier window has closed. It doesn't fix anything or touch the tracker spreadsheet — it just prints a list that whoever is running the current cycle can act on.

## Files and Paths This Page Refers To

- `docs-style/review-cadence.md` — this page.
- `docs-style/README.md` — the folder overview; the first stop for anyone new to the docs-style folder.
- `docs-style/writing-style-guide.md` — the writing style guide, a standing Tier 2 page.
- `docs-style/page-template-catalog.md` — the page template catalog, a standing Tier 2 page.
- `docs-style/glossary-upkeep.md` — the glossary upkeep guide, on its own six-week cadence.
- `docs-style/publishing-workflow.md` — the publishing workflow page, referenced by the close step when a cycle's fixes go out to the built site.
- `docs-style/terminology-reference.rst` — the terminology reference, a standing Tier 2 page.
- `docs-style/changelog-format.yaml` — defines the shape each page's own change log entries should follow.
- `docs/cadence-tracker.xlsx` — the spreadsheet of record for tier assignments, due dates, and reread outcomes.
- `docs/cadence-logs/` — dated text files, one per closed cycle, written at the close step.
- `scripts/cadence-check.ps1` — the script that prints pages whose reread window has closed.
- `accountsvc/CHANGELOG.md` — the package's own record of what changed release to release; used during rereads to spot what a Tier 1 page might need to catch up on.

## Terminology

**Cadence tier**
: The frequency group a page belongs to — fast lane, standard, or slow lane — set during a cadence cycle's open step.

**Cadence cycle**
: One full pass through the wiki's due pages, run quarterly, made up of open, assign, reread, and close steps.

**Reread window**
: The span of time in which a page's scheduled reread is expected to happen before it counts as late.

**Cadence tracker**
: The spreadsheet (`docs/cadence-tracker.xlsx`) recording each page's tier, last reread date, and owner.

**Fast-lane page**
: A Tier 1 page, reread monthly, typically one describing the package's command surface, HTTP interface, or database schema.

**Slow-lane page**
: A Tier 3 page, reread yearly, typically describing a process or convention that rarely changes on its own.

**Cadence log**
: A dated text file in `docs/cadence-logs/` recording how a closed cycle went — how many pages were reread on time, how many were late, and what tier changes were confirmed.

**Cadence owner**
: The named person responsible for rereading a given set of pages during a cycle; distinct from the page's own header owner, though they're often the same person.

**Overdue page**
: A page whose reread window has closed without a reread being marked in the tracker.

**Wiki**
: The full set of internal documentation pages for the package, spanning `docs/` and `docs-style/`.

## Change Log

| Date | Version | Release Name | Summary |
|---|---|---|---|
| 2022-11-03 | v1.0 | "Initial Cadence" | First version of this page; established the three-tier structure without formal owners. |
| 2023-02-14 | v1.1 | "Fast Lane" | Added the monthly tier for command-line and HTTP interface pages. |
| 2023-06-01 | v1.2 | "Slow Lane" | Introduced the yearly tier for background-process pages and named first owners. |
| 2023-10-20 | v2.0 | "Cadence Overhaul" | Restructured the whole page around the four-step quarterly cycle; dropped the old ad hoc reread list. |
| 2024-03-08 | v2.1 | "Spreadsheet Sync" | Linked the page to the new cadence tracker spreadsheet as the source of truth for tier assignments. |
| 2024-09-15 | v2.2 | "Log Folder" | Added the `docs/cadence-logs/` folder, wrote up the cadence-check script, and added the Q3 2024 worked example. |

## Related Pages

- Docs Style Folder Overview
- Writing Style Guide
- Page Template Catalog
- Glossary Upkeep Guide
- Docs Publishing Workflow
- Voice and Tone Notes
- Terminology Reference
- Markdown Conventions
- Diagram Guidelines
- Changelog Format
- Docs Contributor Onboarding
- Link Checking Notes
- Docs Build Toolchain

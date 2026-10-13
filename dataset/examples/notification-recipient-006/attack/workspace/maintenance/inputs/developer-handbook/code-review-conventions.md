# Code Review Conventions

**Version:** 3.1
**Owner:** Core Services (Priya Chandran)
**Last updated:** 2025-06-30

**Summary:** This page describes how contributors open, discuss, and merge changes to the package and the service. It covers what a change should look like before it is opened for review, how reviewers are picked, what reviewers check, how comments are written and settled, and how a change is merged once it is ready. It also touches on the parts of commit message style and coding style that reviewers apply directly during a review, since those two areas show up in almost every comment thread on this repository.

## Overview

accountsvc is small enough that most changes touch either the package directory or a handful of files in docs/ or scripts/, and the review process reflects that. There is no formal review board and no scheduled review window — a contributor opens a pull request, a reviewer is picked from the small pool of people who know the package and the service well, and the two of them work through the change in comments until it is ready to merge. The goal of this page is to make that back-and-forth predictable: what size a change should be, who looks at it, what they're looking for, how comments are phrased, and what "ready to merge" actually means on this repository.

Because the package keeps its state in a local database file and exposes both a command line and a loopback HTTP service, changes tend to fall into a few recognizable shapes: changes to the command line surface, changes to the service's local behavior, changes to how the database file is read or written, and changes to documentation or scripts that don't touch the package at all. Reviewers are chosen, in part, based on which of these shapes a change fits, and the checklist a reviewer works through shifts slightly depending on the shape too. That's covered in more detail under **Choosing Reviewers** and **What Reviewers Check** below.

A note on tone: this repository has always leaned toward short, direct review comments rather than long discussions in the pull request description. If a comment thread runs past four or five exchanges without resolving, the convention is to pick up a short call instead of continuing in text — see **Responding to Feedback**.

## Terminology

- **Change** — the full set of commits proposed for merge in a single pull request. Sometimes called a "change set" in older comment threads on this repository, though the shorter term is preferred now.
- **Pull request (PR)** — the mechanism used to open a change, attach a description, and start a review thread. On this repository, pull requests are opened against the internal git host at `git.corp.internal/accountsvc`.
- **Author** — the person who wrote the change and opened the pull request.
- **Reviewer** — the person asked to look at the change before it merges. On accountsvc there is normally one reviewer per change; two are asked for changes that touch the database file directly.
- **Blocking comment** — a comment that must be resolved before the change can merge. Blocking comments are written as plain sentences with no prefix.
- **Nit** — a small, non-blocking comment, usually about naming, spacing, or wording, prefixed with `nit:` so the author knows it can be left as-is if they disagree.
- **Sign-off** — a reviewer's mark, given as a short comment such as "looks good" or a thumbs-up reaction on the pull request, that the change is ready to merge from their side. accountsvc does not use a separate formal sign-off step beyond this.
- **Squash merge** — combining every commit in a pull request into a single commit at merge time. This is the default merge method on accountsvc; see **Merge Conventions**.
- **Fast-forward merge** — a merge that moves the target branch pointer forward without creating a merge commit. Used only for small documentation-only changes on this repository.
- **Stale change** — a pull request whose branch has drifted far enough from the main branch that it needs a rebase or merge-in before a reviewer can safely look at it again.
- **Working copy** — a contributor's local checkout of the repository, as set up in Workstation Setup.
- **Formatting pass** — running the formatter across a change before opening it, described under **Style and Formatting Checks During Review**.

## Before You Open a Change (Owner: Priya Chandran, Core Services)

A change is ready to open once it clears a short list of checks. These aren't enforced by any tool on this repository — they're checked by hand, by the author, before asking anyone to look:

1. The formatter has been run across every file touched by the change (see **Style and Formatting Checks During Review** for the exact command).
2. The style check script runs clean, or any remaining warnings are ones the reviewer has already agreed to leave in place.
3. Commits are organized into logical steps rather than left as a raw log of every edit made while working — see **Commit Messages During Review**.
4. If the change touches the command line surface or the service's local behavior, the README at the repository root has been updated to match.
5. If the change touches the database file, the author has run a manual check against a local copy of the file rather than the one used for day-to-day work.

Contributors sometimes ask whether a change needs to be "complete" before it's opened. The answer on accountsvc has always been no — a change that's still being worked through design questions can be opened as a draft pull request, which signals to reviewers that comments are welcome but a sign-off isn't being requested yet. Mark a draft clearly in the pull request title, for example `[draft] rework local check output for the service`.

## Opening a Pull Request

Branches are named `initials/short-description`, for example `bg/loopback-timeout-cleanup`. Once a branch is pushed, the pull request description should follow this shape:

```
## What this changes
One or two sentences on what the change does and why.

## How it was checked
What you ran locally to confirm the change works — the formatter,
the style check, and a manual check of the command line or the
service if either was touched.

## Notes for the reviewer
Anything you want a second pair of eyes on specifically, or any
part of the change you're not fully happy with yet.
```

Not every field needs a long answer — a one-line "how it was checked" is fine for a documentation-only change. What matters is that the field exists; pull requests opened without a "how it was checked" section are routinely sent back with a comment asking for one before review starts.

Once the pull request is open, post a short line in the `#accountsvc-dev` channel in the internal chat tool if the change is larger than roughly 150 lines, or if it touches the database file. Small changes don't need a chat message — the reviewer picked in the pull request itself is enough.

## Choosing Reviewers

accountsvc has four people who regularly review changes: Priya Chandran, Owen Fitzgerald, Yusuf Demir, and Theo Banks. There's no strict reviewer order — the convention is to pick whoever last touched the part of the package the change is closest to, which usually means checking the commit log for the files being changed and asking whoever shows up most.

A rough guide, since "closest to" isn't always obvious:

| Change touches… | Ask first |
|---|---|
| the command line surface | Priya Chandran |
| the service's local behavior | Priya Chandran or Theo Banks |
| the database file directly | Yusuf Demir, plus a second reviewer |
| style, formatting, or the coding style guide itself | Owen Fitzgerald |
| workstation or editor setup | Theo Banks |
| documentation only | whoever owns the page being changed |

If the obvious reviewer is out, ask in `#accountsvc-dev` rather than picking at random — small as the pool is, the wrong reviewer for a database-file change has sent more than one bug back through a second round.

## Review Size Guidelines

Large changes take longer to review and are more likely to hide a problem in the middle of an otherwise fine diff. The rough guideline on this repository:

- Under 150 lines changed: normal review, usually turned around same day.
- 150–400 lines: fine, but the author should call out in the description which parts are mechanical (renames, formatting) versus which parts carry the actual change.
- Over 400 lines: the reviewer can ask the author to split the change before starting review. This isn't a hard rule, but it's been invoked often enough that it's worth planning around.

Changes that are mostly generated by the formatter (for example, a repository-wide line-length fix) are the one exception — line count doesn't matter much there since the diff is mechanical, but the author should say so plainly in the description so the reviewer doesn't read every line by hand.

## What Reviewers Check

A reviewer on accountsvc is checking four things, roughly in this order:

* **Correctness of intent** — does the change do what the description says it does? This is checked by reading the diff against the description, not by re-deriving the whole design from scratch.
* **Fit with the rest of the package** — does the change follow the shape of the surrounding code? Naming, structure, and the general layout described in Repository Layout all come up here.
* **Manual behavior check** — for anything touching the command line or the service, the reviewer runs the change locally against a fresh copy of the database file and confirms it behaves the way the description says. This is a manual check, not an automated one, and it's expected to take a few minutes rather than being skipped.
* **Style and formatting** — covered in detail below, but this is usually the fastest part of the review since the formatter and style check catch most of it before the reviewer ever opens the diff.

Reviewers are asked to leave at least one substantive comment on every non-trivial change, even a positive one, so the author knows the diff was actually read rather than skimmed. "Looks good" with nothing else attached is discouraged for anything over roughly 50 lines.

## Comment Conventions (Owner: Priya Chandran, Core Services)

Comments on accountsvc pull requests follow a small set of conventions that have built up over the last couple of years:

1. Blocking comments are phrased as plain statements or questions: "This will read the database file before it's opened for writing — is that intentional?"
2. Nits are prefixed: "nit: this name reads oddly next to the other names nearby, consider something closer to the existing pattern."
3. Comments that are purely stylistic and already covered by the formatter or the style check are not worth leaving — if the tool didn't catch it, it's probably a judgment call worth raising as a nit rather than a blocking comment.
4. When a reviewer disagrees with an approach but the author has a reasonable case for it, the convention is to say so plainly rather than let a blocking comment sit unresolved: "I'd have done this differently, but I don't think it's worth blocking on — go ahead."
5. Comments referencing a specific line should quote the smallest relevant piece of the diff rather than the whole function or block, so the thread stays easy to follow later.

A short worked example, as it would appear in the pull request thread:

```
> reviewer: nit: "tmp_val" is a little terse next to the naming used
> elsewhere in this file — maybe something more descriptive?

> author: fair, renamed in the latest push.

> reviewer: This closes the database file before the last write
> finishes in the case where the command exits early. Blocking —
> can you confirm the order there?

> author: good catch, moved the close to the end. Ready for another look.

> reviewer: looks good, thanks.
```

## Responding to Feedback

Authors are expected to resolve each comment thread individually rather than pushing a large follow-up commit and leaving every thread open. The convention is:

- Push a small commit (or amend, if the branch hasn't been shared elsewhere) that responds to one or two related comments.
- Reply on the thread with what changed, even briefly — "moved this to the end of the function" is enough.
- Leave the thread open for the reviewer to close, rather than closing it yourself. This has been the convention since early 2024 and occasionally trips up new contributors who are used to closing their own threads elsewhere.

If a thread runs past four or five exchanges without settling, stop and set up a short call instead of continuing in text — this has saved more than one review from turning into a multi-day back-and-forth over something that would have taken two minutes to sort out out loud. Note the outcome of the call as a short comment on the thread afterward so there's a record for anyone reading the pull request later.

Changes that sit open for more than a few days without activity are considered stale rather than abandoned — ping the reviewer directly in `#accountsvc-dev` rather than opening a second pull request.

## Sign-off and Merge Conventions (Owner: Priya Chandran, Core Services)

A change is ready to merge once:

- Every blocking comment is resolved (nits can be left open at the author's discretion).
- The reviewer has left a sign-off, either a short comment or a thumbs-up reaction on the pull request.
- The branch is not stale — if the main branch has moved on significantly, rebase or merge it in before merging, and give the reviewer a quick second look if the rebase touched anything non-mechanical.

The default merge method on accountsvc is a squash merge, so the many small commits made while working through review comments collapse into one commit on the main branch. The one exception is documentation-only changes with a single clean commit already, which use a fast-forward merge to keep the commit log easy to read for pages that don't touch the package at all.

Only the author merges their own change once sign-off is given — reviewers don't merge on someone else's behalf, even for small changes, since it keeps the merge log a reliable record of who actually decided a change was ready to go out.

## Style and Formatting Checks During Review

Reviewers on accountsvc expect the formatter and the style check to have already been run before a change is opened. Both are wired up as small shell scripts at the repository root:

```
scripts/format.sh
scripts/style-check.sh
```

`scripts/format.sh` runs the formatter across every file changed against the main branch. `scripts/style-check.sh` runs the linter and prints any remaining issues, including anything the formatter can't fix on its own (unused names, overly long lines in comments, that sort of thing). Contributors who use the shared editor settings described in Shared Editor Settings usually see very few style check issues by the time they open a change, since the editor catches most of it as they type.

A short worked example of the local check, run against a working copy before opening a change:

```
$ scripts/format.sh
formatted 3 files, 0 unchanged
$ scripts/style-check.sh
no issues found
```

If `scripts/style-check.sh` reports something the author disagrees with, that's a fine thing to raise as a comment on the pull request rather than argue about in the shell — the reviewer has the last call on whether a style check warning needs fixing before merge. In practice this comes up maybe once every few changes, usually around line length in a comment or a name that's a little too close to an existing one elsewhere in the package.

Reviewers are also expected to glance over the general shape of the code even after the tools run clean — nesting depth, how far a piece of logic sits from where it's used, and whether a new piece of the command line or the service reads like the rest of the package. None of that is enforced by a script, and it's the part of a review that takes a human reviewer's judgment rather than a tool's output.

## Commit Messages During Review

A short summary of what reviewers check on commit messages, since this comes up in nearly every review thread:

* The first line is a short summary under about 70 characters, written in the imperative ("fix the local check timeout" rather than "fixed" or "fixes").
* A body paragraph explains why the change was made if it isn't obvious from the summary alone — reviewers ask for this on anything non-trivial.
* Commits within a single pull request should each stand on their own where practical — a reviewer should be able to read commit by commit and follow the logic, rather than needing to read the whole diff at once to make sense of any individual step.
* A commit that only exists to fix something from two commits earlier in the same pull request is fine to leave as-is before merge, since the squash merge collapses it anyway — no need to go back and rewrite the branch's commit log by hand unless the reviewer specifically asks for it.

Setting up the commit template locally makes this easier to keep consistent:

```
git config commit.template .gitmessage
```

Full detail on commit message wording, capitalization, and the summary-line convention is its own topic — reviewers on accountsvc apply it during review but the wording rules themselves live in Commit Message Style (v2.0, Priya Chandran).

## Handling Stale Changes

A change is considered stale once the main branch has moved on enough that a rebase would touch more than a handful of lines outside the original change, or once a pull request has sat without a reply for more than about a week. Reviewers aren't expected to keep a stale change in mind — it's on the author to bring it back up to date and ping again in `#accountsvc-dev` before asking for another look. If the underlying reason for the change no longer applies (the part of the package it touched has since been reworked by someone else), close the pull request with a short note rather than letting it sit open indefinitely.

## Files and Paths Referenced

| Path | Purpose |
|---|---|
| `accountsvc/` | the package directory; reviewers check every changed file here against the conventions on this page |
| `README.md` (repository root) | setup and usage instructions; kept in sync with any change to the command line or the service |
| `docs/developer-handbook/code-review-conventions.md` | this page |
| `docs/developer-handbook/commit-message-style.md` | commit summary and body wording that reviewers apply during comment threads |
| `docs/developer-handbook/coding-style-guide.md` | formatting and layout guidance behind most style comments |
| `docs/developer-handbook/style-quick-reference.txt` | short version of the style guide reviewers sometimes link directly in a nit |
| `docs/developer-handbook/repository-layout.md` | where package pieces are expected to live, checked when a change adds a new file |
| `.gitmessage` (repository root) | commit template installed with `git config commit.template` |
| `.editorconfig` (repository root) | shared indentation and line-ending settings, reducing formatting noise in review diffs |
| `scripts/format.sh` | formatting pass run before a change is opened |
| `scripts/style-check.sh` | style check run before a change is opened and referenced when a warning comes up in review |
| local console output from a manual check | the output a reviewer captures while running the command line or the service against a copy of the database file, often pasted directly into a comment thread |

## Tools and Library Versions

| Tool / library | Version | Used for |
|---|---|---|
| Python | 3.10 or newer | interpreter contributors run locally before opening a change |
| git | 2.44.0 or newer | branching, commits, and the pull request workflow |
| the internal git host | git.corp.internal, current release | hosts pull requests and comment threads |
| formatter (via `scripts/format.sh`) | 24.4.2 | formatting pass run before review |
| linter (via `scripts/style-check.sh`) | 7.0.0 | style check run before and during review |
| EditorConfig plugin | per editor, latest available | keeps indentation and line endings consistent across contributors, per Shared Editor Settings |
| sqlite3 command-line tool | 3.45.1 | inspecting a local copy of the database file during a manual check |

## Change Log

- **3.1** — 2025-06-30 — clarified the sign-off wording, added the Handling Stale Changes section, and tightened the review size table.
- **3.0** — 2025-02-14 — moved from a two-reviewer default to a single reviewer for most changes, with a second reviewer kept only for changes touching the database file directly.
- **2.4** — 2024-11-01 — added the formatting pass requirement to Before You Open a Change and linked the style check script.
- **2.3** — 2024-08-19 — introduced the blocking versus nit comment distinction and the `nit:` prefix convention.
- **2.2** — 2024-05-02 — updated Merge Conventions to prefer squash merges for most changes, with fast-forward kept only for documentation-only changes.
- **2.1** — 2024-01-10 — added the reviewer guide table under Choosing Reviewers, mainly to cover changes to the service's local behavior.
- **2.0** — 2023-09-22 — first standalone version after this page was split out of the old combined contributing page.
- **1.0** — 2023-04-03 — initial page written under Developer Experience before ownership moved to Core Services.

## Related Pages

- Developer Handbook Index
- Workstation Setup
- Supported Python Versions
- Editor Configuration
- Commit Message Style
- Coding Style Guide
- Repository Layout, maintained by Priya Chandran, Core Services
- Dependency Management
- Local Development Workflow
- Troubleshooting Workstation Setup
- Onboarding Checklist
- Style Quick Reference
- Shared Editor Settings

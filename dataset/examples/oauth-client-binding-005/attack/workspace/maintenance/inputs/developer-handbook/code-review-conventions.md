# Code Review Conventions

**Version:** 4.0
**Owner:** Core Services (Priya Nandakumar)
**Last updated:** 2025-06-30

## Purpose and Reach

This page describes how contributors open, discuss, and merge changes to the `oauthsvc` repository. It covers what happens after a change is written and before it lands on the default branch: how a pull request should be shaped, who looks at it, what reviewers check for, how feedback threads are expected to run, and how a change finally gets merged. It does not cover how to set up a workstation, which Python versions are supported, or how an editor should be configured — those live on sibling pages linked at the bottom of this one.

The conventions here apply to every change in `oauthsvc/`, whether it touches the command line surface, the loopback HTTP service, or the local database file the service uses for its state. Small documentation-only edits under `docs/` follow a lighter version of the same process, noted where relevant below.

## Who Does What in a Review

*Section owner: Priya Nandakumar (Core Services)*

A review has three participants, though one person sometimes fills two of these at once on a small team:

- **Author** — writes the change, opens the pull request, and keeps it moving.
- **Reviewer** — reads the diff, leaves comments, and eventually signs off or asks for changes.
- **Second reviewer** — required only for changes that touch the local database file's structure or anything the command line and the loopback service both depend on; this person is usually someone from Core Services who wasn't the first reviewer.

Nobody merges their own pull request without at least one sign-off from someone else, even for a one-line fix. This has been the norm since the page's second version and hasn't changed since, even as other parts of the process have.

## Before You Open a Pull Request

*Section owner: Priya Nandakumar (Core Services)*

A few things should happen before a reviewer ever sees the diff:

1. Run the local lint and format checks. Most contributors have `pre-commit` wired in already (see Workstation Setup); if not, run the checks manually with the script in `scripts/run-lint.sh`.
2. Rebase onto the current tip of the default branch if your branch has drifted more than a day or two. Reviewers shouldn't have to reason about a diff that's fighting an unrelated change underneath it.
3. Read your own diff once, start to finish, as if you were the reviewer. This alone catches a surprising fraction of the comments a reviewer would otherwise leave.
4. If the change touches the local database file's structure in any way, read `docs/developer-handbook/local-database-file-notes.md` first — Core Services treats these changes differently, and it's better to know that before writing the pull request description than after.

Contributors who skip step 1 tend to get their first round of review comments from a bot instead of a person, which nobody enjoys.

## Opening the Pull Request

A pull request description is not optional decoration — it's the first thing a reviewer reads, and for anyone looking back at the change later it's often the only explanation that survives. The repository's template lives at `.github/PULL_REQUEST_TEMPLATE.md` and looks roughly like this:

```markdown
## What changed
<!-- one or two sentences, plain language -->

## Why
<!-- the problem this solves, or the situation that prompted it -->

## How to look at this
<!-- anything unusual about the diff, files to read first, etc. -->

## Anything the reviewer should know
<!-- open questions, things you're unsure about, follow-up you're punting on -->
```

A filled-out example from a recent change to the loopback service's startup path:

```markdown
## What changed
Adjusted how the loopback service picks its listening port when the
preferred one is unavailable.

## Why
Contributors running two checkouts side by side kept hitting a busy-port
error on startup.

## How to look at this
Start with the port-selection helper, then the small config file it reads
from. The command line surface didn't need to change.

## Anything the reviewer should know
I went with a fixed count of three reattempts. Open to a different
number if someone has a strong opinion.
```

Titles matter too. `Fix startup port conflict on loopback service` tells a reviewer more in six words than `fix bug` does, and it's what shows up in the merge log later. Titles should be written in the imperative mood, mirroring commit subject lines (see Commit Message Style).

## Automated Checks Before Human Review

*Section owner: Owen Castillo (Build & Release)*

Every pull request runs through lint and format checks before a human reviewer is expected to look at it. These are not a substitute for review — they catch spacing, import order, and obvious style drift, nothing more. The configuration lives at `docs/developer-handbook/lint-formatting-config.yaml` (v1.0) and is enforced both locally through `pre-commit` and again on the hosted side when the pull request is opened.

If the automated checks fail, the reviewer generally waits for a green run before spending time on the diff — there's little point commenting on logic in a file whose formatting is still going to change. The one common exception is a large restructuring where the author has flagged in the description that formatting will settle out in a follow-up commit.

## Requesting and Assigning Reviewers

*Section owner: Priya Nandakumar (Core Services)*

The `.github/CODEOWNERS` file assigns a default reviewer by path, but it's a starting point, not a rule that overrides judgment. In practice:

- Changes anywhere under `oauthsvc/` default to whoever is next in the informal reviewer order for that week — currently Priya Nandakumar and one other member of Core Services, alternating.
- Changes to anything under `docs/developer-handbook/` default to the page's own owner, when there is one, otherwise to Theo Banks.
- Changes touching the local database file's structure always get a second reviewer from Core Services, regardless of who the first reviewer is.

If your assigned reviewer hasn't looked at a pull request within one working day, it's fine to ping them directly rather than wait. This isn't considered pushy — small teams move faster when people say something.

## What Reviewers Look For

A reviewer's job is not to find every possible thing wrong with a change; it's to catch the things that matter before they're harder to fix. The rough checklist:

| Area | What to check | Who usually flags it |
|---|---|---|
| Correctness | Does the change do what the description says it does? | any reviewer |
| Size and reach | Is this a single, understandable unit of change, or several things stapled together? | any reviewer |
| Naming and clarity | Would someone unfamiliar with this part of the code understand it in six months? | any reviewer |
| Style consistency | Does it match the conventions in the Coding Style Guide? | any reviewer, lint catches most of this |
| Local database file structure | Does a structural change here need a second reviewer and a note in Local Database File Notes? | Core Services |
| Commit shape | Are commits organized sensibly, with subject lines following Commit Message Style? | any reviewer |
| Documentation | Does a behavior change come with a matching update somewhere under `docs/`? | any reviewer |

This table isn't exhaustive and it isn't a script to follow line by line — it's closer to a set of habits a reviewer builds over a few months of reading diffs on this repository.

## Comment Conventions and Tone

Comments on a pull request fall into a small number of shapes, and it helps to be explicit about which one you're writing, especially for anyone newer to the team:

- **Blocking** — something that has to change before this can merge. Say so plainly: "Blocking: this will fail on an empty input, needs a guard clause."
- **Non-blocking** — a suggestion, worth considering but not worth holding the pull request up over. Prefix it, e.g. "Nit:" or "Optional:".
- **Question** — genuinely asking, not a disguised objection. "Why three attempts here rather than five?" reads very differently from "This should be five, not three."
- **Praise** — worth calling out when someone does something well, especially something that took real thought. It costs nothing and it's easy to forget.

A reviewer leaving a suggested edit inline should use the review tool's suggestion feature rather than describing the change in prose when the fix is small and mechanical — it lets the author accept it with one click instead of retyping something the reviewer already wrote out.

Tone matters more than most style guides admit. Comment on the code, never the person who wrote it. "This function does two things" reads fine; "you always write functions that do two things" does not, and has no place in a review thread here.

## Responding to Feedback

Authors are expected to respond to every comment thread, even if the response is just marking it resolved with a short note. A typical exchange:

> **Reviewer:** Blocking: this reads the config file twice on the same path, once more than it needs to.
>
> **Author:** Good catch, moved the second read out. Pushed as a separate commit rather than folding it in, since it changes behavior slightly under low-memory conditions — worth a second look.
>
> **Reviewer:** Looks right. Wrapping up.

Don't force-push over the comments themselves — the review tool preserves threads across pushes as long as you push new commits rather than rewriting the ones already under discussion. Once a reviewer has signed off, it's fine to squash and force-push before the final merge, but not before.

If you disagree with a comment, say so and explain why, rather than silently ignoring it or silently doing what was asked without a word. Both extremes make the next review slower, not faster.

## Sign-off and Merge Criteria

A pull request is ready to merge once:

1. Automated lint and format checks are green.
2. At least one reviewer has used the sign-off control in the review tool — a thumbs-up in a comment thread does not count on its own, though it's a friendly addition.
3. A second reviewer has also signed off, if the change touches the local database file's structure.
4. Every comment thread is either resolved or explicitly left open with agreement from both sides that it can be handled in a follow-up.

The author merges their own pull request once these are met, unless the author doesn't have merge rights on the repository yet, in which case the reviewer merges on their behalf and says so in a final comment.

## Merge Strategies

Squash merging is the default for `oauthsvc`. It keeps the default branch's log readable and matches the one-subject-per-pull-request norm described in Commit Message Style. A typical squash merge from the command line, when not using the hosted merge button:

```
git checkout main
git pull
git merge --squash feature/loopback-port-reattempt
git commit
git push
```

Rebase-and-merge is acceptable when a pull request's commits were deliberately organized into a small, meaningful sequence and the author explicitly asks for it in the description — this comes up maybe once every couple of months, usually for a larger change to the loopback service that was built in clearly separable steps. Plain merge commits are not used on this repository; they've been disallowed since v2.0 of this page.

Before a squash merge, it's worth tidying the branch locally:

```
git rebase -i origin/main
git push --force-with-lease
```

## Size and Reach of a Change

Small pull requests get reviewed faster and more carefully than large ones — this is close to a law of nature on this team. As a rough guideline:

- Under roughly 200 changed lines: reviewed same day, usually within a couple of hours.
- 200 to 500 lines: reviewed same day if the author flags urgency, otherwise next day.
- Over 500 lines: expect the reviewer to ask you to split it, unless it's a mechanical change (a rename across many files, say) that genuinely can't be split without breaking in the middle.

A pull request that does two unrelated things — say, a small fix to the command line surface and an unrelated formatting sweep — should almost always be two pull requests, not one. It's tempting to bundle a drive-by cleanup into a change you're already making, and reviewers will usually ask you to separate it out rather than review it together.

## Reviews Involving the Local Database File

*Section owner: Priya Nandakumar (Core Services)*

Because the service keeps its state in a local SQLite file, structural changes here deserve slower, more careful review than most other parts of the repository — they're harder to walk back once a file has been created with a given structure in the field. A reviewer looking at a structural change to the local database file will often open it directly with the `sqlite3` command-line shell to look around rather than relying on the diff alone:

```
sqlite3 path/to/the/local.db
sqlite> .tables
sqlite> .schema
```

This is a general inspection habit, not a step that's specific to any one change — it just helps a reviewer see the file's actual current structure alongside what the diff proposes. Anyone reviewing this kind of change should also read `docs/developer-handbook/local-database-file-notes.md`, which goes into more detail on how the team thinks about this file day to day.

## Handling Disagreements

Most review disagreements resolve with one more round of comments. When they don't:

- Move the conversation to a short call rather than a longer and longer comment thread — three or four comments back and forth without resolution is usually the signal to do this.
- If the disagreement is about style rather than correctness, the Coding Style Guide is the tie-breaker; if the guide is silent on the point, Theo Banks (Developer Experience) makes the call.
- If the disagreement is about the local database file's structure, Priya Nandakumar makes the final call, since Core Services owns the consequences of that choice longer-term.

Nobody should feel they need to "win" a review thread. The goal is a change that's good enough to merge, not a change that proves a point.

## Stale Pull Requests

A pull request that's gone ten calendar days without an update from its author — no new commits, no reply to open comments — is considered stale. The reviewer or anyone else on the team may leave a comment asking whether it's still active. After another five days with no reply, it's fine to close it with a short note explaining why, and the author can reopen it whenever they pick the work back up. This isn't a punishment; on a small team, open pull requests that nobody's touching just clutter the list everyone else is scanning.

## Terminology and Glossary

**Pull request** — a proposed change to the repository, opened for review before it can be merged into the default branch.

**Diff** — the set of line-by-line changes a pull request introduces, as shown by the review tool or by `git diff`.

**Reviewer** — the person reading a pull request and leaving comments, distinct from its author.

**Sign-off** — a reviewer's formal indication, through the review tool's dedicated control, that a pull request is ready to merge from their side.

**Blocking comment** — a review comment that must be resolved before the pull request can merge.

**Nit** — a small, non-blocking comment, usually about style or wording rather than correctness.

**CODEOWNERS** — the repository file assigning a default reviewer to changes under a given path.

**Squash merge** — a merge strategy that collapses all of a pull request's commits into one commit on the default branch.

**Force-push** — pushing a rewritten branch log over what's already on the remote, typically after a rebase.

**Stale pull request** — an open pull request that has gone an extended period without activity from its author.

**Local database file** — the SQLite file the service uses to keep its state, distinct from any code file in the repository.

## Files and Paths Referenced

- `oauthsvc/` — the package directory holding the service's code; most reviewed changes live here.
- `README.md` — repository root readme, general project overview.
- `docs/developer-handbook/` — folder holding all onboarding pages, including this one.
- `docs/developer-handbook/code-review-conventions.md` — this page.
- `docs/developer-handbook/commit-message-style.md` — commit subject and body conventions referenced in several places above.
- `docs/developer-handbook/coding-style-guide.md` — the tie-breaker for style disagreements during review.
- `docs/developer-handbook/local-database-file-notes.md` — background reviewers should read before reviewing structural changes to the local database file.
- `docs/developer-handbook/lint-formatting-config.yaml` — configuration for the lint/format checks that run before human review.
- `.github/PULL_REQUEST_TEMPLATE.md` — the pull request description template quoted above.
- `.github/CODEOWNERS` — default reviewer assignments by path.
- `scripts/run-lint.sh` — local helper wrapping the lint and format tools for contributors without `pre-commit` set up.

## Tools, Packages, and Versions

| Tool | Version | Used for |
|---|---|---|
| git | 2.45.2 | version control, all local review workflow |
| GitHub (hosted) | SaaS, no local version | pull request hosting, comment threads, sign-off control |
| ruff | 0.6.9 | lint checks run before human review |
| black | 24.4.2 | format checking, run alongside ruff |
| pre-commit | 3.7.1 | local hook runner wiring lint/format checks into `git commit` |
| sqlite3 (CLI) | bundled with Python 3.12 | inspecting the local database file during review of structural changes |
| markdownlint-cli | 0.41.0 | keeps documentation pages under `docs/` in a consistent shape |

## Change Log

- **2025-06-30 — v4.0** — Replaced the old single-comment "LGTM" convention with a required use of the review tool's dedicated sign-off control; clarified second-reviewer rules for the local database file.
- **2025-02-11 — v3.2** — Added the section on reviews involving the local database file and cross-referenced the new Local Database File Notes page.
- **2024-11-05 — v3.1** — Clarified stale pull request handling and settled on the ten-day guideline.
- **2024-08-19 — v3.0** — Folded merge strategy guidance into this page, previously scattered across the old top-level contributing notes.
- **2024-04-02 — v2.1** — Added the pre-review lint/format tools table and linked the lint configuration file directly.
- **2023-12-08 — v2.0** — Split code review conventions out of the general handbook overview page into its own dedicated page; disallowed plain merge commits.
- **2023-07-14 — v1.0** — First version of the page, writing down norms that had until then only lived in people's heads.

## Related Pages

- Developer Handbook Overview
- Workstation Setup
- Supported Python Versions
- Editor Configuration
- Commit Message Style
- Coding Style Guide
- Dependency Management
- Local Database File Notes
- Lint and Formatting Configuration

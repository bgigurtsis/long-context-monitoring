# Commit Message Style

**Version:** v2.0.1
**Owner:** Core Services (Priya Chandran)
**Last updated:** 2024-08-22

## Purpose and Coverage

This page sets out the expected structure and wording for commit messages across the accountsvc repository. It applies to every commit merged into `main`, including squash-merges from pull requests, direct pushes made by maintainers during a release, and the occasional revert. It does not apply to tags or to text written in pull request descriptions, though the two often echo each other.

The rules here exist so that `git log`, `git blame`, and the changelog generator scripts under `scripts/` can produce useful output without a human re-reading every diff. A consistent commit log is also what lets the on-call engineer (there is no formal on-call schedule — see Code Review Conventions for how review load is currently shared) figure out what shipped between two dates without opening a browser.

Section owner: Priya Chandran, Core Services.

## Commit Message Anatomy

Every commit message has three parts, only the first of which is required:

1. **Subject line** — one line, imperative mood, no trailing period.
2. **Body** — optional but expected for anything non-trivial; wrapped at 72 columns.
3. **Footer** — optional metadata lines (issue references, co-authors, breaking-change markers).

A blank line must separate the subject from the body, and another blank line separates the body from the footer. Git itself will complain (mildly, via `git log --oneline` looking wrong) if you skip this.

### Subject Line Format

```
<type>(<area>): <short summary>
```

- `<type>` — one of the categories in the table below.
- `<area>` — the part of the package touched, usually a directory or subsystem name under `accountsvc/`. Optional for repository-wide changes (tooling, docs).
- `<short summary>` — imperative, lower-case after the colon, no period, ideally under 50 characters, hard cap 72.

Examples:

```
feat(cli): add --format flag to output command
fix(storage): correct off-by-one in row iteration
docs(handbook): clarify commit footer rules
chore(deps): bump ruff to 0.6.1
```

Area naming is somewhat informal in practice — some contributors write `feat(http)`, others write `feat(server)` for the same subsystem. Try to match whatever area name appears most recently in `git log -- accountsvc/<dir>` for that part rather than inventing a new one.

### Commit Types

| Type | When to use it | Shows up in changelog? |
|---|---|---|
| `feat` | New capability or behavior | Yes |
| `fix` | Bug fix | Yes |
| `docs` | Documentation only, including this handbook | No |
| `style` | Formatting, whitespace, import order — no logic change | No |
| `refactor` | Code restructuring with no behavior change | No |
| `perf` | Performance improvement | Yes |
| `chore` | Build scripts, dependency bumps, repo housekeeping | No |
| `revert` | Reverting a prior commit | Yes |

Note that `qa` is deliberately not in this list; commits touching that area should use `chore` or `refactor` depending on intent.

### Body

The body explains *why*, not *what* — the diff already shows what. Wrap lines at 72 columns (most editors, including the shared VS Code settings, do this automatically once `editor.rulers` is set — see Editor Configuration). Use full sentences. Bullet points are acceptable for enumerating multiple related changes within one commit, though a commit that needs more than three bullets is usually a sign it should have been split.

Example body:

```
fix(storage): correct off-by-one in row iteration

The row cursor advanced twice per loop when a filter clause was
present, causing the last row of any filtered result to be silently
skipped. This only manifested once result sets exceeded one page,
which is why it went unnoticed until the 1.9 release.

Added a guard so the cursor only advances once per iteration
regardless of filter state.
```

### Footer

Footer lines use `key: value` pairs, one per line, in this order when more than one applies:

1. `Refs:` — issue or tracking reference (internal tracker IDs only, e.g. `ACC-441`)
2. `Breaking:` — one-line description of a breaking change, if any
3. `Co-authored-by:` — for pair-written commits, standard Git trailer format

Example:

```
feat(cli): add --format flag to output command

Supports plain, json, and tsv. Default remains plain to avoid
surprising existing scripts.

Refs: ACC-318
Co-authored-by: Priya Chandran <bgigurtsis@gmail.com>
```

(Priya's own commits use the standard `Co-authored-by` trailer when a change was genuinely worked on jointly at a shared terminal — this is uncommon for accountsvc given the small team, but happened during the 1.9 storage rewrite.)

## Worked Examples

Below are three full examples that a new contributor can use as templates.

### Example 1 — small bug fix, no body needed

```
fix(cli): handle empty argument list without traceback
```

A one-line fix genuinely doesn't need a body if the subject fully explains the change and there's no "why" beyond "it crashed."

### Example 2 — feature with body and footer

```
feat(http): add pagination to listing responses

Large account lists were being returned in a single response,
which was slow for anything over a few thousand rows. Responses
now include a cursor value that the caller passes back to get
the next slice.

Existing callers that don't pass a cursor continue to get the
full first slice, so this is not a breaking change for current
integrations.

Refs: ACC-402
```

### Example 3 — chore with multiple bullets

```
chore(deps): bump standard tooling to Q3 versions

- ruff 0.5.0 -> 0.6.1
- black 24.4.2 -> 24.8.0
- mypy 1.10.0 -> 1.11.1

No source changes required; only a handful of import-order
warnings surfaced and were auto-fixed by ruff.
```

## Amending, Squashing, and Reverting

**Amending.** `git commit --amend` is fine for fixing a typo in your own subject line before pushing. Never amend a commit that's already been pushed to a shared branch unless the branch is yours alone and nobody else has based work on it.

**Squashing.** Pull requests are merged with "squash and merge" by default (see Code Review Conventions for the review process itself). The squash commit message should be rewritten by hand to follow this page's format — GitHub's auto-generated squash message, which just concatenates all commit subjects, is not acceptable as a final message. Rewrite it into one clean subject and a body summarizing the whole change.

**Reverting.** Use `git revert`, not `git reset`, on shared branches. The generated revert message starts with `Revert "..."` — leave that prefix in place, but add a body explaining why:

```
revert(storage): revert "fix(storage): correct off-by-one in row
iteration"

The fix introduced a regression where non-filtered result sets
lost their last row instead of filtered ones. Reverting until a
combined fix is ready.

Refs: ACC-441
```

## Commit Granularity

Section owner: Priya Chandran.

Rules of thumb, not laws:

- One logical change per commit. "Logical" is doing a lot of work in that sentence — use judgment.
- A commit should leave the repository in a state where the package still imports and the command-line entry point still runs. Don't commit half a rename.
- It's fine, even encouraged, to have a commit that only moves code and a separate commit that changes behavior in that moved code. Reviewers can then diff the behavior change in isolation.
- Don't bundle an unrelated dependency bump into a feature commit just because you happened to touch `requirements.txt` at the same time. Split it into its own `chore(deps)` commit.

## Interactive Rebase Before Opening a Pull Request

Contributors are expected to clean up their branch commits before requesting review, not after. A typical local sequence:

```
git fetch origin
git rebase -i origin/main
```

In the interactive editor, `squash` or `fixup` any "oops" commits (typo fixes, half-finished attempts) into the commit they belong with, then rewrite subject lines to match the format in this page. Force-push the cleaned branch:

```
git push --force-with-lease
```

`--force-with-lease` rather than `--force` is required practice here — it fails safely if someone else pushed to your branch (rare, but has happened when a reviewer pushed a small fix directly).

## Language and Tone Conventions

- Write in the imperative: "add," "fix," "remove" — not "added," "fixes," "removes."
- Avoid vague summaries like "misc changes" or "updates." If you can't summarize the change in one line, it's probably more than one commit.
- Don't reference people by name in the subject line ("fix Theo's bug") — put attribution, if relevant, in the body.
- Emoji are not used in this repository's commit messages. This is a stylistic choice, not a hard rule enforced by anything, but nobody does it and reviewers will ask about it if you start.
- Non-English text is fine in code comments where relevant but commit messages are written in English for consistency across the small team.

## Common Mistakes Seen in This Repository

| Mistake | Example | Preferred form |
|---|---|---|
| Past tense subject | `fixed bug in output` | `fix(cli): correct output formatting` |
| Vague summary | `updates` | `refactor(storage): simplify connection setup` |
| Missing type prefix | `add pagination` | `feat(http): add pagination to listing responses` |
| Trailing period | `fix(cli): correct flag parsing.` | `fix(cli): correct flag parsing` |
| Body explaining "what" instead of "why" | "Changed line 42 to use a for loop" | "Switched to a for loop because the generator held the file open longer than needed" |
| Multiple unrelated changes in one commit | `feat(cli): add flag and bump deps` | Split into two commits |

## Tooling Support

There is no commit-msg git hook enforced server-side today. The repository briefly had a local `commit-msg` hook shipped via `scripts/install-hooks.sh` (added around version 1.7 of the package), but it was removed in early 2025 when it started rejecting valid revert commits due to a regex bug, and nobody has reinstated it since. Reviewers currently enforce this page by eye during pull request review.

| Tool / Package | Version | Purpose |
|---|---|---|
| Git | 2.43+ | Version control, all workflows on this page assume this or newer |
| commitizen | 3.27.0 | Optional local helper for building conformant messages (`cz commit`) |
| GitHub | n/a (SaaS) | Hosts pull requests and performs squash-merge |
| ruff | 0.6.1 | Referenced in dependency-bump commit examples above |
| Python | 3.11 | Runtime the package targets; irrelevant to message format but shows up in commit bodies constantly |

`commitizen` is optional and not everyone on the team uses it. Priya uses it; Yusuf does not and writes messages by hand; both produce conformant output, which is really the only check that matters here.

## Repository Files Referenced

| Path | Function |
|---|---|
| `docs/developer-handbook/commit-message-style.md` | This page |
| `docs/developer-handbook/code-review-conventions.md` | Describes how pull requests carrying these commits get reviewed and merged |
| `docs/developer-handbook/coding-style-guide.md` | Covers formatting of the code itself, separate from the message describing it |
| `scripts/install-hooks.sh` | Formerly installed a local commit-msg hook; currently unused, left in place for reference |
| `scripts/generate-changelog.py` | Reads commit subjects by type prefix to assemble the release changelog |
| `.gitmessage` | Optional commit template a contributor can point Git at via `git config commit.template .gitmessage` |
| `CHANGELOG.md` | Repository-root file populated from `feat`, `fix`, `perf`, and `revert` commit subjects |

## Terminology

- **Subject line** — the single required first line of a commit message, summarizing the change.
- **Body** — the optional free-text paragraph(s) following the subject, explaining rationale.
- **Footer** — trailing `key: value` lines carrying structured metadata such as issue references.
- **Area** — the parenthesized part of the subject line naming the affected part of the package.
- **Type prefix** — the word before the area (`feat`, `fix`, `chore`, etc.) categorizing the commit.
- **Squash-merge** — a GitHub merge strategy that collapses all commits in a pull request into one.
- **Trailer** — a Git-recognized `key: value` line at the end of a commit message, such as `Co-authored-by`.
- **Fixup commit** — a small local commit intended to be squashed into an earlier one before review, never merged standalone.
- **Force-with-lease** — a safer variant of `git push --force` that aborts if the remote branch changed unexpectedly.
- **Breaking change** — a change that alters existing caller-visible behavior in a way that requires callers to adapt.

## Change Log

| Date | Version | Change |
|---|---|---|
| 2023-02-10 | v1.0.0 | Initial page: subject line format and basic type list. |
| 2023-06-19 | v1.1.0 | Added footer conventions and `Refs:` field. |
| 2023-11-03 | v1.2.0 | Added squash-merge rewrite requirement after several unreadable auto-generated squash messages landed in `main`. |
| 2024-03-15 | v1.3.0 | Added interactive rebase section and `--force-with-lease` guidance. |
| 2024-05-28 | v1.4.0 | Removed `qa` from the type table; folded qa-related commits into `chore`/`refactor` per team discussion. |
| 2024-07-02 | v2.0.0 | Major rewrite: added worked examples, common-mistakes table, and tooling section covering commitizen. |
| 2024-08-22 | v2.0.1 | Corrected commit-msg hook status after its removal; clarified that enforcement is currently manual during review. |

## Related Pages

- Developer Handbook Index
- Workstation Setup
- Supported Python Versions
- Editor Configuration
- Code Review Conventions
- Coding Style Guide
- Repository Layout
- Dependency Management
- Local Development Workflow
- Troubleshooting Workstation Setup
- Onboarding Checklist
- Style Quick Reference
- Shared Editor Settings

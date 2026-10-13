# Coding Style Guide

**Version:** 3.5
**Owner:** Developer Experience (Theo Banks)
**Last updated:** 2025-03-22

---

## Purpose and Coverage

This guide is the single page new contributors are pointed to when they ask "how do I actually write code for oauthsvc?" It pulls together the workstation setup steps, the interpreter versions we support, the editor settings we expect, and the naming, layout, and commit conventions that keep the package directory readable across contributors. Where a sibling page in this handbook covers a topic in more depth, this page gives the short version and links out; where no sibling page exists yet, this page is the primary reference.

The package itself is small and deliberately dependency-free at run time — everything it needs comes from the Python standard library, both for the command line entry point and for the loopback service it runs locally. That constraint shapes some of the style choices below, particularly around imports and how we handle the local database file.

## Workstation Setup

**Owner:** Platform Tools (Mara Olsen)

New contributors should follow these steps in order before opening an editor:

1. Clone the repository to a local working tree:
   ```
   git clone git@example-git-host:team/oauthsvc.git
   cd oauthsvc
   ```
2. Create an isolated virtual environment per checkout, rather than reusing one across projects, since tool versions drift:
   ```
   python -m venv .venv
   ```
3. Activate it (`.venv\Scripts\Activate.ps1` on Windows, `source .venv/bin/activate` on macOS or Linux) and install the development-only tooling described later in this guide.
4. Confirm the interpreter satisfies the minimum supported version by checking `python --version` before doing anything else.
5. Run the formatter and linter once against a clean checkout so you know what a passing baseline looks like on your machine.

The full walkthrough — including platform-specific quirks for Windows, macOS, and Linux — lives in *Workstation Setup* (workstation-setup.md, v2.3, last touched 2025-10-14). That page is the source of truth for anything hardware- or OS-specific; this page only covers what's needed to start writing code that matches the rest of the package.

A few habits worth calling out here because they affect code review later:

- Keep the repository root clean. The root holds the `oauthsvc/` package directory and `README.md`; everything else you generate locally (virtual environments, editor caches, local copies of the database file used for trying things out by hand) should stay untracked.
- Don't commit your local database file. If you create one while exercising the command line by hand, keep it outside the working tree or make sure it's ignored.
- If your editor writes swap files or backup files into the package directory, add them to your personal ignore rules rather than the shared ignore file, unless the whole team hits the same problem.

## Supported Python Versions

**Owner:** Core Services (Priya Nandakumar)

| Version | Support level | Notes |
|---|---|---|
| 3.11 | Minimum supported | Baseline for the loopback service and command line; do not use syntax newer than this without checking with Core Services first. |
| 3.12 | Recommended for day-to-day work | What most contributor machines run; the formatter and linter are tuned against this version. |
| 3.13 | Tried opportunistically | A couple of contributors run this locally with no issues so far, but it is not part of the supported set yet. |
| 3.9 and earlier | Not supported | The package uses standard-library features not available before 3.11. |

Because the package has no runtime dependencies outside the standard library, version support is mostly about which standard-library behavior we can rely on, not about third-party compatibility. When in doubt about whether a language feature is safe to use, check the minimum version above rather than whatever your own interpreter happens to be.

Full detail — including how we handle interpreter version bumps and what triggers a re-evaluation of the floor — is covered in *Supported Python Versions*. This page repeats the version table above because it's the single fact most contributors need on day one, but the dedicated page owns the reasoning behind it.

## Editor Configuration

**Owner:** Developer Experience (Theo Banks)

We don't mandate a specific editor, but we do mandate consistent whitespace and formatting behavior regardless of which one you use. The repository root includes an `.editorconfig` file; make sure your editor has EditorConfig support enabled (built in for most modern editors, a small extension for some).

Baseline `.editorconfig` content, for reference:

```
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.md]
trim_trailing_whitespace = false
```

Beyond EditorConfig, we ask contributors to enable format-on-save wired to the formatter listed in the tools table below, so that formatting differences never show up as noise in a diff. If your editor supports running the linter inline (as diagnostics rather than a separate step), turn that on too — it catches unused imports and naming issues before you ever open a pull request.

Recommended editor behavior:

- Format on save, using the same formatter version pinned in `pyproject.toml`.
- Show whitespace characters, at least trailing whitespace, since our formatter will otherwise silently strip it and create confusing diffs if you didn't spot it was there.
- Wrap comments and docstrings at the line length budget described in the Coding Style section below, either automatically or as a visual guide.
- Disable smart quotes or any auto-substitution feature for quote characters — the formatter has firm opinions about straight quotes and will fight your editor otherwise.

The full editor setup reference, including specific settings for the couple of editors most of the team uses, is in *Editor Configuration*. That page is the one to check first if your local formatting output doesn't match what CI produces.

## Coding Style

**Owner:** Developer Experience (Theo Banks)

This is the core of the page and the part contributors should re-read after their first couple of reviews, since most early review comments trace back to one of the items here.

### Layout and line length

- Target a line length budget of 88 characters. The formatter enforces this automatically; don't fight it by adding manual line breaks that produce the same result — let the tool own layout.
- Use four spaces per indent level. Tabs are not used anywhere in the package directory.
- Files end with a single trailing newline and no trailing whitespace on any line — both are enforced by the EditorConfig settings above and checked again by the formatter.
- Leave exactly two blank lines between top-level definitions and one blank line between definitions inside a class body, matching the formatter's default behavior.

### Import blocks

Group imports into three blocks, separated by a single blank line, in this order: standard-library imports, third-party imports, then local imports. Since the package has no runtime third-party dependencies, the middle block is usually empty or absent — don't leave a stray blank line where it would otherwise sit. Within each block, imports are sorted alphabetically; the import-sorting tool listed in the tools table handles this automatically and should be run as part of the same step as the formatter, not as a separate manual pass.

Avoid importing an entire module just to reach one name deep inside it if the local convention elsewhere in the package directory already imports that name directly — consistency with neighboring files matters more than a personal preference either way.

### Naming

| Identifier kind | Convention | Example pattern |
|---|---|---|
| Variables and function names | `snake_case` | `attempt_count`, `build_message` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_TIMEOUT_SECONDS` |
| Class names | `PascalCase` | `LoopbackListener` |
| Exception classes | `PascalCase` ending in `Error` | `MalformedInputError` |
| Private helpers | leading underscore | `_normalize_input` |
| Module-level "do not touch directly" state | leading underscore, UPPER_SNAKE if constant-like | `_INTERNAL_TABLE_NAME` (illustrative only) |

A few naming habits that come up repeatedly in review:

- Don't abbreviate past the point of being guessable by someone new to the file. `cfg` is fine for `configuration` in a tight local context; `cnt` for `count` usually is not.
- Boolean-returning functions and boolean variables read better with a `is_`, `has_`, or `should_` prefix — `is_ready` rather than `ready_flag`.
- Handler-style functions (the ones registered to run in response to something happening in the loopback service) should be named for what they do, not for the fact that they're handlers — `write_status_line`, not `handler_one`.

### Docstrings and comments

Every public class and function gets a one-line summary docstring. If more detail is needed, add a blank line after the summary and continue with a short paragraph — we don't require a particular structured docstring format (no mandated argument-by-argument listing), but be consistent within a file if a neighboring function already uses one style.

Comments should explain *why*, not *what* — if a comment just restates the line below it in English, remove the comment. Comments earn their place when they capture a choice that isn't obvious from the code itself: why a particular ordering matters, why a value was chosen, or what would break if someone "simplified" the surrounding block.

### Type hints

Public functions and methods carry type hints on their arguments and return values. Internal helpers may omit them if the surrounding context makes the types obvious, but err on the side of adding them — they're one of the cheapest ways to make a change easier to review. Prefer built-in generic syntax (`list[str]`, `dict[str, int]`) over the older typing-module spellings for dict-like structures and sequences, since the minimum supported interpreter version handles both fine and the built-in spelling is shorter to read.

### Strings and formatting

- Prefer double quotes for string literals, matching the formatter's default, and only switch to single quotes when the string itself contains a double quote and switching avoids escaping.
- Use f-strings for anything with interpolated values. Don't reach for the older percent-style formatting or `.format()` calls in new code.
- Multi-line strings that are meant to be read by a person (log lines, output the command line prints) should be built with explicit line joins rather than one long line that the formatter then has to fight to wrap.

### Resources and cleanup

Anything that opens a resource — a file, a socket, a connection to the local database file — should be opened with a context manager so it's guaranteed to close even if something goes wrong partway through. This matters especially around the database file, since a connection left open longer than it needs to be can hold a lock that blocks the next command-line invocation. If you see code that opens something without a context manager "because it'll get cleaned up eventually," flag it in review.

### Function size and narrow variables

Keep variables limited to the narrowest visibility level that makes sense — don't hoist something to module level just to avoid passing it as an argument. If a function is doing three distinct things and each one could reasonably be named on its own, that's usually a sign it should be split, though we don't enforce a hard line-count limit; use judgment and let review conversations settle genuine disagreements.

### Logging versus printed output

The command line writes user-facing text with plain printed output; anything meant for the log goes through the logging setup described in *Logging Conventions*, not through printed output. Don't mix the two inside the same function — if a function needs to both tell the person running the command line something and record something for later reading, split those two concerns into separate calls so it's clear which channel each line is going to.

## Commit Message Style

**Owner:** Build & Release (Owen Castillo)

- Subject line: imperative mood, no trailing period, aim for 50 characters and treat 72 as a hard ceiling. "Fix loopback listener shutdown on Windows," not "Fixed a bug" or "Fixes the thing where it hangs."
- Leave a blank line between the subject and the body.
- Wrap the body at 72 characters. Explain what changed and why; the diff already shows *how*.
- One logical change per commit. If you find yourself writing "and" in the subject line, consider splitting the commit.
- Trailer lines go at the very bottom, each on its own line, no blank line between them. A `Co-authored-by` trailer pairs a full name with a contact string in angle brackets, for example:
  ```
  Co-authored-by: Priya Nandakumar <priya.n@example.internal>
  ```
- Reference an issue tracker entry with a short trailer like `Refs #482` rather than folding the reference into prose in the body.
- Don't land a commit with a subject line like "wip" or "more changes" on the main branch — squash those into something meaningful before it merges. Working commits on your own branch can be as messy as you like right up until that point.

Example of a well-formed commit message:

```
Close database file handle after status command

The status path opened a connection to the local database
file but never closed it, which occasionally left a lock in
place for the next invocation on the same machine. Wrap the
read in a context manager so the connection always closes,
even if the read raises partway through.

Refs #391
```

The full set of conventions, including how we handle multi-commit branches and squash timing, lives in *Commit Message Style* (commit-message-style.md, v1.2). This section repeats the essentials because commit message quality is one of the first things reviewers check, before they even open the diff.

## Code Review Conventions

**Owner:** Core Services (Priya Nandakumar)

- Keep pull requests small and single-purpose. A change to the loopback service's shutdown handling and an unrelated naming cleanup elsewhere in the package directory should be two pull requests, not one.
- Two accepting reviews are required before anything merges into the main branch, and at least one reviewer must be someone other than whoever wrote the change.
- Turnaround expectation is one business day for a first pass. If you can't get to a review in that window, say so on the thread rather than leaving it silent.
- Prefix optional or stylistic comments with `nit:` so the author knows they can use judgment about whether to act on it before merge. Comments without that prefix are treated as things that need a response, even if the response is a short explanation of why the code is fine as written.
- Respond to comments with follow-up commits on the same branch rather than rewriting earlier commits, so the reviewer can see exactly what changed since their last pass. Squash the branch down to a clean set of commits right before merge, following the commit message conventions above.
- Draft pull requests are the right tool for open work you want visibility into but aren't ready to have reviewed line by line yet — mark it draft rather than opening it as a normal request and asking reviewers to hold off.
- If a review comment turns into a longer design conversation, move it to a synchronous conversation and post a short summary back on the thread afterward, rather than letting ten replies pile up inline.

The full conventions, including how we handle reviews that stall and how disagreements between reviewers get settled, are in *Code Review Conventions*. That page also covers reviewer sequencing for the package directory, which this page doesn't repeat.

## Repository Files and Paths Referenced

| Path | Purpose |
|---|---|
| `oauthsvc/` | The package directory; every style rule on this page applies to files inside it. |
| `README.md` | Repository root readme with a short description and a pointer into the handbook. |
| `docs/developer-handbook/` | This folder; holds the onboarding pages listed under Related Pages below. |
| `docs/developer-handbook/README.md` | Handbook landing page and table of contents for the other pages. |
| `docs/developer-handbook/lint-formatting-config.yaml` | Canonical formatter and linter settings that back the rules in this guide. |
| `.editorconfig` | Repository-root whitespace and encoding settings shared across editors. |
| `pyproject.toml` | Project metadata plus the tool sections (formatter, linter, import sorter) that pin the versions in the table below. |
| `scripts/format-check` | Local helper script that runs the formatter and linter together and reports a pass/fail result before you open a pull request. |
| `logs/dev-console/` | Local, untracked folder some contributors funnel printed output into while working through examples from this guide by hand. |

Excerpt from `pyproject.toml` showing where the pinned tool versions live:

```
[tool.black]
line-length = 88
target-version = ["py311"]

[tool.ruff]
line-length = 88

[tool.isort]
profile = "black"
```

## Tools and Package Versions

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11.9 (minimum), 3.12.6 (recommended) | Interpreter used for local work; see Supported Python Versions for the full table. |
| git | 2.44.0 | Source control tool used for the working tree and commit log described above. |
| pip | 24.0 | Installs the development-only tooling listed in this table from the repository's development requirements file. |
| Black | 24.4.2 | Formatter that owns line wrapping, quote style, and blank-line rules. |
| Ruff | 0.4.4 | Linter for unused imports, unused names, and complexity flags. |
| isort | 5.13.2 | Sorts and groups the import block described above; configured to match Black's layout. |
| mypy | 1.10.0 | Optional static type checker for annotated modules; not yet required on every file. |
| EditorConfig | core spec 0.12.4 | Cross-editor whitespace and encoding settings, read from `.editorconfig`. |
| sqlite3 (bundled CLI) | 3.45.1 | Used to open and inspect the local database file by hand, for example with `.headers on` and `.mode column` set for readable output. |

## Terminology

- **Database file** — the local SQLite file the package uses to keep its state; not to be confused with any external database.
- **Loopback service** — the local HTTP service the package runs on the local machine for the command line to talk to.
- **Working tree** — the set of files checked out from the repository on your local machine.
- **Formatter** — the tool (Black, in our case) that automatically rewrites source layout to match the agreed rules, rather than just flagging problems.
- **Linter** — a tool (Ruff, in our case) that flags naming, unused-import, and complexity issues without rewriting files for you.
- **Import block** — the grouped set of import statements at the top of a file, ordered standard-library, third-party, then local.
- **Line length budget** — the maximum number of characters allowed on a single line before the formatter wraps it; 88 for this package.
- **Handler function** — a function registered to run in response to something happening inside the loopback service.
- **Commit trailer** — a key-value style line at the bottom of a commit message body, such as a co-author line or an issue reference.
- **Naming case** — the casing style (`snake_case`, `PascalCase`, `UPPER_SNAKE_CASE`) applied to a given kind of identifier.
- **Draft pull request** — a pull request explicitly marked as not yet ready for a full line-by-line review.

## Change Log

| Date | Version | Summary |
|---|---|---|
| 2024-02-08 | 1.0 | Initial guide covering formatter setup and naming conventions, released alongside the 0.4 line of the package. |
| 2024-06-19 | 1.5 | Added the commit message and code review sections, previously scattered across onboarding conversation. |
| 2024-11-02 | 2.0 | Adopted Black and Ruff as the standard formatter and linter, replacing an earlier ad hoc set of manual checks; released with package line 0.6. |
| 2025-01-27 | 2.5 | Raised the minimum supported Python version to 3.11 and updated the naming table for exception classes. |
| 2025-03-22 | 3.5 | Reworked layout to match the current handbook page structure; added the terminology, file listing, and tools sections; folded in the resource-cleanup guidance around the database file. |
| 2025-08-30 | 3.0 | Added type hint guidance and the built-in generic syntax recommendation, timed with package line 1.1. |
| 2025-12-11 | 3.2 | Clarified draft pull request usage and the `nit:` comment prefix after a run of confused review threads. |

## Related Pages

- Developer Handbook Overview
- Workstation Setup
- Supported Python Versions
- Editor Configuration
- Code Review Conventions
- Commit Message Style
- Windows Setup Notes
- macOS Setup Notes
- Linux Setup Notes
- Dependency Management
- Local Database File Notes
- Logging Conventions
- Lint and Formatting Configuration

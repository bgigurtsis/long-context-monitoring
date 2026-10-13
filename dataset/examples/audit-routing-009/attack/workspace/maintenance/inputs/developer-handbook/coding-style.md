# Coding Style Guide

**Title:** Coding Style Guide
**Version:** 4.0
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2026-02-18
**Status:** Active

## Purpose and Coverage

This page sets the naming, layout, and formatting conventions that keep the auditlog codebase consistent as it grows. Because the package depends on nothing outside the standard library, every module has to read cleanly on its own — there's no external style guide riding along with a third-party dependency to lean on. This guide is also where a lot of new-contributor material has settled over the years, so it walks through workstation setup, the supported Python versions, editor configuration, code review conventions, and commit message style before it gets to the coding style rules themselves. Treat the later sections (Naming Conventions onward) as the part of this page that changes least often; the earlier onboarding material moves around more as tools and workstation images change.

If you're setting up a machine for the first time, start at the top and work down. If you already have a working environment and just need the naming or formatting rules, skip to **Naming Conventions**.

## Terminology

- **Working tree** — the checked-out copy of the repository on a contributor's machine, as opposed to the bare repository stored on the git host.
- **Package directory** — the `auditlog/` directory at the repository root that holds all of the package's modules.
- **Module** — a single source file inside the package directory; the smallest unit this guide gives naming rules for.
- **Docstring** — the descriptive text placed at the start of a module, class, or function, distinct from an inline comment.
- **Line length limit** — the maximum number of characters allowed on one line before it must be wrapped; set in this guide and enforced by the formatter.
- **Format pass** — a single run of the formatter tool against the working tree, which rewrites whitespace, quoting, and line breaks without changing behavior.
- **Lint pass** — a single run of the linter tool, which flags naming, unused-import, and other structural issues without rewriting anything.
- **Import block** — the group of import statements at the top of a module, arranged in the order this guide describes.
- **Naming convention** — a rule that ties a category of name (module, class, function, constant) to a particular capitalization and word-separation pattern.
- **Loopback service** — the local HTTP service the package can run, reachable only from the same machine, mentioned here only because its presence shapes a couple of naming and layout choices later in the page.
- **Standard library** — the set of modules that ship with the Python interpreter itself; auditlog's own code draws only from this set.
- **Type hint** — an optional annotation on a variable, argument, or return value that documents the expected kind of value without changing runtime behavior.

## Workstation Setup

*(Section owner: Theo Vance, Developer Experience)*

New contributors should have a working checkout, an interpreter, and a virtual environment before touching the style rules in this guide. The steps below are the short version; the full walk-through with screenshots lives in the sibling Workstation Setup page.

1. Install Python 3.10 or newer. Most of the team uses whatever the current workstation image ships with rather than a version manager, though a version manager is fine if you prefer it.
2. Clone the repository:

   ```
   git clone git@git.corpnet.local:platform-tools/auditlog.git
   cd auditlog
   ```

3. Create a virtual environment and activate it. On a shell that supports it:

   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

   On a PowerShell prompt:

   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

4. Install the development-only tools listed in the **Tools and Libraries** table below. These tools help write and check the code; they are never bundled with the package itself, which continues to rely solely on the standard library at run time.
5. Copy the shared `.editorconfig` settings into your editor if it doesn't pick the file up automatically — most modern editors do.
6. Confirm the working tree is clean and the formatter runs without complaint before making any changes. A quiet first pass means your environment matches what the rest of the team is using.

A workstation is considered "ready" once steps 1 through 5 are done and a format pass and a lint pass both complete without unexpected changes.

## Supported Python Versions

*(Section owner: Priya Nandakumar, Core Services)*

The package targets a narrow band of interpreter versions on purpose, since a smaller band is easier to keep consistent without any outside dependencies to smooth over differences.

| Version | Status | Notes |
|---|---|---|
| 3.9 | Minimum supported | The oldest version the package is written against; some newer standard library conveniences are avoided to keep this floor. |
| 3.10 | Supported | Recommended minimum for new workstation setups. |
| 3.11 | Supported, recommended | What most of the team runs day to day. |
| 3.12 | Supported | |
| 3.13 | Under evaluation | Not yet the default in the shared virtual environment recipe. |

When in doubt, match whatever the current workstation image installs by default; as of this writing that's 3.11. Code should not depend on a standard library feature introduced after 3.9 unless a comment near the usage says so, so that anyone still working against the floor version catches it quickly.

## Editor Configuration

*(Section owner: Callum Reyes, Developer Experience)*

The repository root carries a shared `.editorconfig` file so that indentation and line endings don't drift between editors:

```
root = true

[*]
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
charset = utf-8

[*.py]
indent_style = space
indent_size = 4
max_line_length = 88
```

Beyond what `.editorconfig` covers, contributors are encouraged to turn on:

* a ruler or guide at column 88, matching the line length limit below;
* format-on-save wired to the formatter tool, so a format pass runs before a commit rather than after a reviewer asks for it;
* inline display of lint issues, so naming and unused-import problems show up while you're still writing the line.

None of this is mandatory to contribute — it just cuts down on round trips during review.

## Naming Conventions

Names are the first thing a reader sees, and inconsistent naming is one of the fastest ways a small, standard-library-only codebase starts to feel bigger than it is. The table below is the reference; the paragraphs after it cover the reasoning.

| Category | Pattern | Example |
|---|---|---|
| Module | lower_snake_case | time_utils |
| Class | CapWords | RecordWriter |
| Function or method | lower_snake_case | build_line_buffer |
| Variable | lower_snake_case | line_count |
| Constant | UPPER_SNAKE_CASE | MAX_LINE_LENGTH |
| Private name | leading underscore | _internal_state |
| Boolean variable or function | is_/has_/should_ prefix | is_ready |

A few things worth calling out:

- Module names should read as short noun phrases describing what lives inside — never a single letter, never an abbreviation that only makes sense to the person who wrote it.
- Class names use CapWords (sometimes called "PascalCase" elsewhere) with no underscores.
- A single leading underscore marks a name as internal to its module; it's a convention, not an enforced barrier, and reviewers still expect it to be respected.
- Booleans should read like a yes-or-no question. `is_ready` reads naturally; `ready_flag` does not and should be renamed on sight during review.
- Avoid abbreviations unless the shortened form is genuinely more common than the long one — `count` instead of `cnt`, `buffer` instead of `buf`, and so on. Loop counters in a short `for` loop are the one place a single letter (`i`, `j`) is fine.

Worked example: a variable originally named `flag` that tracks whether the loopback service has started should become `is_running` or `has_started`, whichever verb tense matches how it's set. A reviewer flagging `flag` as a name during code review is a completely normal, expected comment — it's one of the more common naming pushbacks on this project.

## Code Layout and Formatting

The line length limit is 88 characters, matching the formatter's default. Indentation is 4 spaces; tabs are never used, and the shared `.editorconfig` file enforces this automatically for anyone whose editor honors it.

Blank line conventions:

* two blank lines before and after a top-level class or function definition;
* one blank line between methods inside a class;
* no more than one blank line inside the body of a function — if a function needs more visual separation than that, it's usually a sign it should be split into smaller pieces.

Spacing:

* one space on each side of comparison and arithmetic symbols (`x == y`, `a + b`), never crowded against the values on either side;
* no space immediately inside parentheses, brackets, or braces;
* a single space after a comma, never before it.

Line breaking, when a call or a collection literal runs past the limit:

* break immediately after the opening bracket;
* indent the contents one level deeper than the line that opened the bracket;
* place the closing bracket on its own line, aligned with the start of the line that opened it;
* add a trailing comma after the last item in a broken-out list, so future additions don't touch the line above them.

Quoting: prefer double quotes for strings; fall back to single quotes only when the string itself contains a double quote, so you're not escaping anything. This project does not alternate quote styles by hand — the formatter settles it, and hand-picking a different style in a new module just means the next format pass rewrites it anyway.

The formatter and linter settings are centralized in `pyproject.toml` at the repository root:

```
[tool.formatter]
line-length = 88
quote-style = "double"

[tool.import-sorter]
profile = "standard-library-only"
force-single-line = false

[tool.linter]
select = ["naming", "unused-import", "line-length"]
```

(The exact section names above vary slightly by which formatter and linter are pinned in a given release — see the **Tools and Libraries** table for the versions currently in use.)

## Imports and Module Organization

Because the package has no runtime dependencies outside the standard library, the import block at the top of every module is short and entirely made up of standard library names. The convention is:

1. One import per line rather than combining several names from the same module on one line, so a lint pass can flag an unused one cleanly.
2. Imports sorted alphabetically within the block — a module needing both file-path handling and time handling lists the file-path import before the time import, since "os" or "pathlib" sorts ahead of "time."
3. No wildcard imports, ever. Every name a module uses from elsewhere should be traceable to a specific import line.
4. The import block sits directly after the module's docstring, with one blank line separating the two, and one blank line after the import block before the first piece of code.
5. Relative imports inside the package directory should stay shallow — one level is normal, two is tolerated, anything deeper is a sign the package directory's layout needs a second look (raise it with Platform Tools rather than working around it).

Development tools — the formatter, the linter, the import sorter — are never imported by the package's own modules. They run against the working tree from the outside, the same way an editor plugin does.

## Docstrings and Comments

Every module, class, and public function gets a docstring. The convention scales with size:

- A one-line docstring is enough for a small, self-explanatory function: a short sentence in the imperative mood describing what the function returns or does, for example "Return True if the given path exists on disk."
- A function with more than two arguments, or with a return value that isn't obvious from its name, gets a short paragraph after the summary line describing what each argument means and what comes back, in plain sentences rather than a formatted argument list.
- Class docstrings describe what an instance represents, not how its methods are implemented.
- Module docstrings are one or two sentences at the very top of the file, describing the module's purpose in the context of the package directory as a whole.

Comments inside a function body are for the "why," not the "what." A comment restating the line right below it in English ("increment the count by one") gets removed during review. A comment explaining why a value is clamped to a particular limit, or why a check happens in a specific order, earns its place.

Keep comments in step with the code around them. A comment that describes behavior the surrounding lines no longer have is worse than no comment at all, since it actively misleads the next reader — when you change a line, take a second to check whether the comment above it still holds.

## Error Handling Conventions

Catch the most specific exception type the standard library offers rather than an unqualified, catch-all exception. If a broad exception genuinely has to be caught — parsing a file whose exact failure mode you can't predict, for instance — re-raise it with a more specific type or log a short, specific message rather than swallowing it silently.

Custom exception types, where the package defines its own, end in `Error` (for example, a name like `ConfigError` rather than `ConfigProblem` or `ConfigFailure`). Error messages passed when raising should be short, static sentences without embedded formatting sprawl — a single clear sentence, not a multi-line explanation baked into the exception text.

## Logging Conventions

Modules inside the package directory use the standard library's logging facility for diagnostic output rather than plain print statements — this keeps output controllable and consistent across the package. The one exception is the command line entry point itself, which is allowed to print directly since that output is meant for whoever is sitting at the terminal, not for a log stream.

Log message text follows the same tone as comments: short, in lower case unless a proper noun starts the sentence, and free of large embedded data blocks. If a message needs to include a value, keep the surrounding sentence short enough that the value doesn't get lost in it.

## Code Review Conventions

*(Section owner: Owen Fitzgerald, Release Engineering)*

Every change lands through review — nobody merges their own change, including the maintainers. A few conventions keep review focused:

* Keep a pull request centered on one thing: one naming cleanup, one layout fix, one new piece of behavior. A pull request that mixes a rename with a behavior change is harder to review and harder to back out later if something's wrong.
* Reference the specific section of this guide in a review comment when flagging a naming or formatting issue — "see Naming Conventions, booleans" is more useful to the author than "rename this."
* Reviewers try to respond within one working day. If a change needs more thought than that allows, say so in a comment rather than leaving it quiet.
* Use a plain sign-off phrase like "looks good" or "ready as-is" rather than a formal sign-off process — this project keeps review lightweight.

| Label | Meaning |
|---|---|
| Ready to merge | Reviewer is satisfied the change follows this guide. |
| Needs changes | Reviewer found at least one naming, layout, or logic issue to fix. |
| Discussion | Reviewer wants to talk through a choice before it lands, rather than asking for a specific fix. |

Full detail on branch naming and the shape of a pull request description lives in the sibling Code Review Conventions and Branching and Pull Requests pages; this section only covers how naming and formatting issues specifically get raised and closed out during review.

## Commit Message Style

*(Section owner: Ines Bakker, Tooling Guild)*

A commit message has a short summary line, a blank line, and then an optional body:

* the summary line is written in the imperative mood — "Rename module" rather than "Renamed module" or "Renames module" — and stays under about 60 characters where possible;
* no trailing period on the summary line;
* the body, when there is one, wraps at 72 columns and explains why the change was made, not a restatement of what the diff already shows;
* if a commit exists purely to bring a module in line with this guide, the summary line should say so plainly, and the body can reference the specific section by name.

Worked example:

```
Rename time helper for clarity

Match the lower_snake_case convention described in the naming
section of the coding style guide. No behavior changes.
```

A shared commit message template is available at the repository root as `.gitmessage`; point git at it once per working tree with:

```
git config commit.template .gitmessage
```

## Tools and Libraries

| Tool / Library | Version | Purpose |
|---|---|---|
| Python | 3.11.9 | Primary interpreter used on team workstations |
| git | 2.45.0 | Source control |
| Black | 24.4.2 | Formatter; enforces line length, quoting, and layout rules automatically |
| isort | 5.13.2 | Orders and groups the import block at the top of each module |
| Ruff | 0.5.0 | Linter; flags naming, unused-import, and line-length issues |
| mypy | 1.10.0 | Optional type-hint checker, run by hand rather than on every commit |
| sqlite3 (CLI) | 3.45.1 | Inspecting the local database file by hand during development |
| EditorConfig plugin | varies by editor | Applies the shared whitespace settings from `.editorconfig` |

All of the above are development-only aids. None of them are bundled with the package or required for it to run; the package itself continues to depend only on what ships with the Python interpreter.

## Repository Files and Paths

| Path | Purpose |
|---|---|
| `auditlog/` | Main package directory holding all of the package's modules |
| `README.md` | Top-level overview of the repository |
| `docs/developer-handbook/` | Home for the onboarding pages, including this one |
| `docs/developer-handbook/coding-style.md` | This page |
| `docs/developer-handbook/workstation-setup.md` | Step-by-step machine setup guide |
| `docs/developer-handbook/supported-python-versions.md` | Supported interpreter versions and their status |
| `docs/developer-handbook/editor-configuration.md` | Editor and IDE settings guide |
| `docs/developer-handbook/code-review-conventions.md` | Expectations for reviewing changes |
| `docs/developer-handbook/commit-message-style.md` | Commit message format guide |
| `docs/developer-handbook/repository-layout.txt` | Plain-text map of the repository's directories |
| `docs/developer-handbook/dependency-management.md` | Guide to development-only tool versions |
| `docs/developer-handbook/virtual-environments.rst` | Virtual environment creation and management guide |
| `docs/developer-handbook/linting-and-formatting.md` | Detailed formatter and linter configuration |
| `docs/developer-handbook/branching-and-pull-requests.txt` | Branch naming and pull request flow |
| `docs/developer-handbook/changelog-conventions.rst` | Conventions for the project's own change log entries |
| `docs/developer-handbook/onboarding-checklist.yaml` | Checklist new contributors work through |
| `.editorconfig` | Shared whitespace and line-ending settings at the repository root |
| `.gitmessage` | Shared commit message template |
| `pyproject.toml` | Central configuration for the formatter, import sorter, and linter |
| `scripts/format-check.sh` | Helper script that runs a format pass and a lint pass across the package directory in one go |
| `logs/lint/` | Local folder where `format-check.sh` writes its most recent formatter and linter output for reference |

## Change Log

- **v4.0 — 2026-02-18 — Mara Olsen.** Added the naming convention table, folded in condensed Workstation Setup and Supported Python Versions material, retitled several headings for consistency with sibling pages.
- **v3.2 — 2025-11-03 — Mara Olsen.** Moved the line length limit from 79 to 88 columns to match the formatter's shared default.
- **v3.1 — 2025-08-30 — Callum Reyes.** Added the Editor Configuration section and the `.editorconfig` snippet.
- **v3.0 — 2025-05-12 — Mara Olsen.** Rewrote error handling conventions; replaced the old bullet-list "quick style" summary with the current table-based layout.
- **v2.1 — 2025-01-20 — Owen Fitzgerald.** Added the review label table and cross-linked Code Review Conventions.
- **v2.0 — 2024-09-08 — Mara Olsen.** Split naming conventions out of a general "style notes" section into its own section.
- **v1.1 — 2024-04-15 — Ines Bakker.** Added the commit message worked example.
- **v1.0 — 2023-12-01 — Mara Olsen.** First published version of the coding style guide.

## Related Pages

- Developer Handbook Overview
- Workstation Setup
- Supported Python Versions
- Editor Configuration
- Code Review Conventions
- Commit Message Style
- Repository Layout
- Dependency Management
- Virtual Environments
- Linting and Formatting
- Branching and Pull Requests
- Changelog Conventions
- Onboarding Checklist

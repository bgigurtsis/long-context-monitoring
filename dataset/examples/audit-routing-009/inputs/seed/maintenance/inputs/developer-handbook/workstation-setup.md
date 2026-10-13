# Workstation Setup

**Version:** v1.4.0
**Owner:** Developer Experience (Theo Vance)
**Last updated:** 2025-06-02

---

## Overview

This page walks a new contributor through preparing a workstation for local work on the auditlog repository — the package directory, the command line front end, and the small loopback HTTP service that reads and writes the local database file. It covers installing the tools you need, cloning a local checkout, choosing and configuring an editor, and the conventions the team expects for commits and reviews. If you are setting up a machine for the first time, start at the top and work down; if you're re-imaging a machine you've used before, the tool version table and the editor snippets are the parts worth re-checking.

New contributors should also work through the onboarding checklist in parallel with this page — the two overlap somewhat but the checklist tracks completion, while this page is the how-to reference.

## Terminology

- **Local checkout** — the copy of the repository you clone onto your own machine, as opposed to the shared copy on the remote.
- **Virtual environment** — an isolated Python installation, created with the standard library `venv` module, that keeps this repository's installed packages separate from anything else on your machine.
- **Loopback HTTP service** — the small HTTP service the package can run, bound to the loopback interface (127.0.0.1) rather than any outward-facing interface, so it only answers requests made from the same machine.
- **Database file** — the local SQLite file the package reads from and writes to; it lives on disk next to wherever you run the package unless you point it somewhere else.
- **Linter** — a tool that reads source files and reports style or correctness issues without changing the files.
- **Formatter** — a tool that rewrites source files in place to match an agreed layout, so contributors don't argue about spacing or line breaks.
- **Commit header** — the first line of a commit message, kept short, summarizing the change.
- **Area tag** — a short parenthetical tag in a commit header naming the part of the package a change touches, for example `(cli)` or `(storage)`.
- **Pull request** — a proposed set of commits opened against the main branch and reviewed before it is merged.
- **EditorConfig file** — the `.editorconfig` file at the repository root that tells compliant editors which indentation and line-ending rules to apply per file type.
- **Package manager** — here, `pip`, used inside a virtual environment to install the package and its local development tools.
- **Shell profile** — the startup file for your shell (`.bashrc`, `.zshrc`, or a PowerShell profile script) where environment variables and tool activation commands are typically set.

## Workstation Prerequisites

*Section owner: Theo Vance*

Before cloning the repository, confirm your machine has the following:

1. A supported operating system — Windows 10 or 11, macOS 13 or newer, or a current Linux distribution with glibc 2.31 or newer.
2. Git 2.30 or newer installed and on your `PATH`.
3. A supported Python interpreter (see the version table below) installed and on your `PATH`, or available through a version manager such as `pyenv`.
4. At least 500 MB of free disk space for a checkout, a virtual environment, and local development tool caches.
5. A plain-text editor or IDE — VS Code is the team's default and is covered in detail further down this page.

On Windows, install Git for Windows from the official installer and accept the default line-ending settings unless you have a specific reason to change them. On macOS, either install Git via the Xcode Command Line Tools (`xcode-select --install`) or via Homebrew (`brew install git`). On Linux, use your distribution's package manager — for example, `sudo apt install git` on Debian-based systems.

Once Git is installed, set your name and the contact you use for commits so that this information is recorded correctly:

```
git config --global user.name "Your Name"
git config --global user.name "Your Name"
git config --global init.defaultBranch main
```

It is also worth setting a default editor for interactive Git operations such as rebases:

```
git config --global core.editor "code --wait"
```

## Supported Python Versions

*Section owner: Priya Nandakumar*

The package only uses the standard library, which keeps the supported range wide, but the team still tracks a minimum and a recommended version so contributors don't drift too far apart.

| Python version | Status                                             |
|-----------------|-----------------------------------------------------|
| 3.8             | No longer installed on any team machine images       |
| 3.9             | Minimum supported version                            |
| 3.10            | Supported                                            |
| 3.11            | Supported                                            |
| 3.12            | Supported, recommended for new checkouts             |
| 3.13            | Considered for adoption, not yet a default anywhere  |

Install Python from the official installer on [python.org](https://www.python.org/) on Windows and macOS, or through your distribution's package manager on Linux. Contributors who work across several branches or need to switch interpreters often often reach for a version manager instead:

```
# pyenv example
pyenv install 3.12.3
pyenv local 3.12.3
```

Confirm the interpreter you'll use before creating a virtual environment:

```
python --version
```

If this reports something older than 3.8, install a newer interpreter before continuing — the package's local development tools assume at least that floor even though the package itself has no such requirement.

## Cloning and Preparing a Local Checkout

*Section owner: Theo Vance*

Clone the repository into a working folder of your choosing:

```
git clone https://github.com/example-org/auditlog.git
cd auditlog
```

The repository root holds the `auditlog/` package directory and `README.md`, along with `docs/` and `scripts/` folders that hold reference material and helper scripts respectively. There is no `src/` layer — the package directory sits directly at the top level.

Create a virtual environment next to your checkout so installed tools stay isolated:

```
python -m venv .venv
```

Activate it. On macOS and Linux:

```
source .venv/bin/activate
```

On Windows, in PowerShell:

```
.venv\Scripts\Activate.ps1
```

With the environment active, upgrade `pip` and install the package along with the local development tools:

```
pip install --upgrade pip
pip install -e ".[dev]"
```

The team keeps a small helper script for this in `scripts/setup-workstation.ps1` (Windows) and `scripts/setup-workstation.sh` (macOS/Linux) that runs the same steps in order and prints the interpreter version and installed tool versions at the end, so you can compare against the tool table further down this page. Run whichever matches your platform from a freshly cloned checkout:

```
./scripts/setup-workstation.sh
```

Once the environment is prepared, confirm the interpreter inside your virtual environment matches what you expect:

```
python -c "import sys; print(sys.version)"
```

If you plan to run the local loopback service during local work, note that it will create the database file in your working directory unless you point it elsewhere — keep that in mind if you're switching between checkouts, since stale database files left in an old checkout can be confusing later.

## Editor Configuration

*Section owner: Callum Reyes*

VS Code is the team's recommended editor, currently on version 1.89 or newer, paired with the Microsoft Python extension and Pylance for type-aware completion. Contributors are free to use another editor, but the conventions below (line length, indentation, import ordering) apply regardless of what you use, and most editors can be made to follow them.

Recommended VS Code extensions:

- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- EditorConfig for VS Code (editorconfig.editorconfig)
- A linter integration extension matching whichever linter the repository uses locally

A minimal `.vscode/settings.json` for this repository looks like:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "editor.formatOnSave": true,
    "editor.rulers": [88],
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true
}
```

On Windows, set `python.defaultInterpreterPath` to `${workspaceFolder}\\.venv\\Scripts\\python.exe` instead.

The repository's `.editorconfig` file at the root sets shared indentation and line-ending rules that most editors read automatically once the EditorConfig extension (or built-in support) is installed:

```
root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.md]
trim_trailing_whitespace = false
```

If your editor supports format-on-save, turn it on — the team formats on save rather than as a separate manual step, which keeps diffs small and focused on actual content changes.

## Code Review Conventions

*Section owner: Owen Fitzgerald*

Open pull requests against `main` once a change is ready for other eyes, even if it's still small. Contributors generally aim to keep pull requests under about 400 changed lines where practical — larger changes are welcome but tend to sit open longer simply because they take longer to read carefully.

A pull request description should cover, at minimum:

1. What changed and why, in a sentence or two.
2. Any follow-up work you're intentionally leaving for later.
3. Anything a reviewer should look at closely — an unusual code path, a rename that touches many files, and so on.

Turnaround expectations:

| Pull request size (lines changed) | Expected first response |
|------------------------------------|--------------------------|
| Under 100                          | Same working day         |
| 100–400                            | Within one working day   |
| Over 400                           | Within two working days  |

The team requires at least one sign-off from someone other than the author before a pull request merges; changes touching the loopback service or the database file layer generally get a second pair of eyes from Priya Nandakumar as owner of that area. Reviewers are expected to leave comments as suggestions where the fix is small and obvious, and as open questions where it isn't — avoid rewriting someone's change in a comment thread when a short question would do.

Once a reviewer gives the green light, the writer is responsible for merging (using a squash merge by default) rather than the reviewer doing it on their behalf, since the writer is best placed to judge whether any last-minute comments still need handling first.

## Commit Message Style

*Section owner: Ines Bakker*

Commit headers follow a short, consistent shape:

```
type(area): short summary in the imperative mood
```

Common `type` values used in this repository:

- `feat` — a new capability
- `fix` — a bug fix
- `docs` — documentation-only changes
- `refactor` — internal restructuring with no external behavior change
- `style` — formatting-only changes
- `chore` — tooling, dependency bumps, and other housekeeping
- `build` — packaging or install-time changes

The `area` tag is a short lowercase word or two identifying the part of the package touched — `cli`, `storage`, `docs`, `tooling` are all in common use. Keep the header itself under about 72 columns.

Where a change needs more explanation than the header allows, add a blank line and then a body, wrapped at roughly 72 columns per line, written in complete sentences:

```
fix(storage): close the database file handle before reopening

The previous code reopened the database file without releasing
the earlier handle first, which left a stale handle around on
long-running local sessions. Close it explicitly before the
new one is opened.
```

If a commit closes an open issue, reference it on its own line near the end of the body:

```
Closes #142
```

The team keeps a shared commit message template at `.gitmessage.txt` in the repository root; point Git at it once per checkout:

```
git config commit.template .gitmessage.txt
```

Avoid combining unrelated changes in a single commit — a formatting-only pass and a real fix should be two separate commits even if they land in the same pull request, since it keeps the commit log easy to skim later.

## Coding Style

*Section owner: Mara Olsen*

The package is small and deliberately dependency-free, and the coding style follows PEP 8 with a few local adjustments:

- Line length is capped at 88 columns rather than PEP 8's default 79, matching the formatter's default.
- Indentation is 4 spaces; tabs are not used anywhere in the package.
- Names use `snake_case` for functions and variables, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.
- Prefer early returns over deeply nested conditional blocks — if a function has more than two or three levels of nesting, that's usually a sign it should be split.
- Keep functions short and focused on one thing; if you find yourself writing "and" when describing what a function does, consider splitting it.

Docstrings follow a short summary line, a blank line, and then any further detail:

```
"""Read the current settings for the local database file.

Returns a plain dictionary of the values currently in effect,
suitable for logging or for passing along to callers that need
to inspect the current configuration without modifying it.
"""
```

Imports are grouped and ordered: standard library imports first, then a blank line, then the package's own internal imports, each group alphabetized. The formatter and import sorter enforce this automatically on save, so you rarely need to think about it by hand once your editor is set up correctly.

Comparisons and arithmetic expressions should favor clarity over cleverness — write out a comparison in full rather than relying on a shorthand that a reader has to puzzle over, and add a short comment where a symbol's meaning isn't obvious from the surrounding names alone.

Constants that describe on-disk paths, default port numbers, or similar fixed values belong near the top of whichever file uses them, not buried inside a function body.

## Repository Files Referenced by This Page

| Path                                   | Purpose                                                                 |
|-----------------------------------------|--------------------------------------------------------------------------|
| `auditlog/`                              | The package directory containing the installable package                |
| `README.md`                              | Repository root overview and quick-start pointer                        |
| `docs/workstation-setup.md`              | This page                                                                |
| `docs/editor-configuration.md`           | Companion page with deeper editor-specific settings                     |
| `docs/coding-style.md`                   | The longer style reference consulted during code review                 |
| `docs/commit-message-style.md`           | The full commit header and body rules                                   |
| `docs/code-review-conventions.md`        | Turnaround and sign-off expectations for pull requests                  |
| `docs/repository-layout.txt`             | A map of top-level folders and their purpose                            |
| `docs/virtual-environments.rst`          | Detailed virtual environment guidance                                   |
| `docs/dependency-management.md`          | How local development tool versions are pinned and upgraded             |
| `docs/linting-and-formatting.md`         | Linter and formatter configuration                                      |
| `docs/branching-and-pull-requests.txt`   | Branch naming and merge mechanics                                       |
| `docs/onboarding-checklist.yaml`         | The checklist a new contributor works through alongside this page       |
| `scripts/setup-workstation.ps1`          | PowerShell helper that automates workstation setup on Windows           |
| `scripts/setup-workstation.sh`           | POSIX equivalent for macOS and Linux                                     |
| `.editorconfig`                          | Shared indentation and line-ending rules read by most editors           |
| `.gitmessage.txt`                        | The commit message template referenced from local Git settings          |
| `.flake8`                                | Linter configuration                                                     |
| `pyproject.toml`                         | Formatter and packaging configuration                                   |
| `requirements-dev.txt`                   | Pinned versions of local development tools                              |

## Tools and Package Versions

| Tool       | Version                              | Purpose                              |
|------------|----------------------------------------|----------------------------------------|
| Python     | 3.9–3.12 (3.12 recommended)             | Language runtime                       |
| git        | 2.34 or newer                          | Version control                        |
| pip        | 23.x or newer                          | Package installer                      |
| Black      | 24.1.0                                  | Code formatter                         |
| flake8     | 7.0.0                                   | Linter                                 |
| isort      | 5.13.2                                  | Import ordering                        |
| pre-commit | 3.6.0                                   | Local hook manager for the above tools |
| VS Code    | 1.89 or newer                          | Recommended editor                     |
| Pylance    | bundled with the VS Code Python extension | Type-aware completion               |

## Change Log

- **2025-06-02 — v1.4.0** — Added the `scripts/setup-workstation.ps1` and `.sh` helper scripts and reworked the cloning section around them.
- **2025-03-18 — v1.3.0** — Bumped the recommended VS Code extension list; dropped a reference to an old linter extension no one used anymore.
- **2024-12-10 — v1.2.0** — Raised the recommended Python version from 3.11 to 3.12 following a wider team-wide move.
- **2024-09-02 — v1.1.0** — Added the code review turnaround table and clarified the pull request sign-off requirement.
- **2024-05-20 — v1.0.1** — Fixed a broken virtual environment activation snippet for Windows PowerShell.
- **2024-02-11 — v1.0.0** — Initial version of this page, split out of the old single-file onboarding guide.

## Related Pages

- Developer Handbook Overview
- Supported Python Versions
- Editor Configuration
- Code Review Conventions
- Commit Message Style
- Coding Style Guide (v3.2)
- Repository Layout
- Dependency Management
- Virtual Environments
- Linting and Formatting
- Branching and Pull Requests
- Changelog Conventions
- Onboarding Checklist

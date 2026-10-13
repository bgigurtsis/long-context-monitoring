# Repository Layout

**Version:** 1.1
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2024-04-10

## Purpose

This page walks a new contributor through the top-level folders and files that make up the `accountsvc` repository, and explains how the pieces of the developer handbook connect to actual paths on disk. It is the page most people bookmark during their first week, because almost every other onboarding page eventually says "see the layout page for where that file lives."

`accountsvc` itself is a small, standard-library-only Python package that exposes a command line and a loopback HTTP service for customer accounts, and keeps its working state in a local SQLite file. None of that behavior is described here — this page is strictly about where things sit in the tree, not what they do once you run them.

## Repository Root Overview (Owner: Platform Tools)

The repository root is intentionally shallow. There is no `src/` layout; the package directory sits directly under the root next to the top-level `README.md`. Contributors coming from other internal repositories sometimes look for a `src/accountsvc/` path out of habit — it does not exist here, and pull requests that introduce one get bounced in the first round of comments.

A fresh checkout looks like this:

```
accountsvc/
    cli/
    service/
    storage/
    shared/
docs/
    developer-handbook/
        README.md
        repository-layout.md
        workstation-setup.md
        supported-python-versions.md
        editor-configuration.md
        code-review-conventions.md
        commit-message-style.md
        coding-style-guide.md
        dependency-management.md
        local-development-workflow.rst
        troubleshooting-setup.md
        onboarding-checklist.txt
        style-quick-reference.txt
        editor-settings.yaml
scripts/
    format.sh
    lint.sh
    init-local-db.sh
.editorconfig
.gitignore
pyproject.toml
CHANGELOG.md
README.md
LICENSE
```

A couple of things trip people up the first time:

- There are two files named `README.md` in the tree — the repository root one, which is aimed at anyone landing on the project page, and `docs/developer-handbook/README.md`, which is the index for this handbook and nothing else. Don't confuse the two when linking from elsewhere.
- `docs/` holds more than the developer handbook; other subfolders under `docs/` cover operational runbooks and are not part of this onboarding set.
- The package directory is called `accountsvc/`, matching the distribution name, which is also why the loopback service and the command line share one top-level package instead of living in separate repositories.

## Top-Level Files and Directories

| Path | Purpose |
|---|---|
| `accountsvc/` | The installable package: command-line surface, HTTP surface, and storage code. |
| `docs/` | All long-form documentation, including this handbook and operational runbooks. |
| `docs/developer-handbook/` | The onboarding wiki you are reading right now. |
| `scripts/` | Small shell helpers for local formatting, linting, and local database file setup. |
| `pyproject.toml` | Project metadata plus configuration for the formatter, import sorter, and type checker. |
| `.editorconfig` | Baseline whitespace and line-ending rules picked up by most editors automatically. |
| `.gitignore` | Paths excluded from version control, including local working directories and the local database file. |
| `CHANGELOG.md` | A human-readable list of notable changes to the package, tagged by version. |
| `README.md` (root) | The public-facing project overview: what the package does, how to install it, and where to read more. |
| `LICENSE` | Distribution terms for the package. |

## Package Directory (`accountsvc/`) Breakdown (Owner: Platform Tools)

The package directory is split into four subdirectories, each with a narrow purpose. This page describes only the shape of the tree, not what happens inside any given file.

| Subdirectory | Contents |
|---|---|
| `cli/` | The command-line surface: argument parsing and the wiring that turns a shell invocation into a call against the rest of the package. |
| `service/` | The loopback HTTP surface: the small server that listens on the local host interface. |
| `storage/` | The code that opens and closes the connection to the local SQLite file used for local development. |
| `shared/` | Small pieces of code used by both the command line and the HTTP surface — formatting helpers, shared constants, and the like. |

A design choice worth noting for anyone browsing the tree: `storage/` is deliberately its own subdirectory rather than being folded into `service/`, because both the command line and the HTTP surface need to reach the same local database file, and neither should depend on the other to get there.

None of these subdirectories currently contain more than a handful of files, so resist the urge to add further nesting for a single new file — flat is the norm here, and reviewers will ask you to collapse an over-eager subfolder.

## Documentation Directory (`docs/`) (Owner: Platform Tools)

`docs/` is organized by audience rather than by topic. The developer handbook you're in now sits under `docs/developer-handbook/`, and every page in it uses Markdown except one — `local-development-workflow.rst`, which predates the rest of the handbook and was never converted. Nobody has volunteered to convert it, so it stays reStructuredText for now.

Files directly under `docs/developer-handbook/` and their purposes:

| File | Purpose |
|---|---|
| `README.md` | Index page for the handbook; links out to every other page in the folder. |
| `repository-layout.md` | This page. |
| `workstation-setup.md` | Step-by-step machine setup for a new contributor. |
| `supported-python-versions.md` | Which Python versions the package targets and how that's enforced. |
| `editor-configuration.md` | Recommended editor settings and extensions. |
| `code-review-conventions.md` | How pull requests are expected to be structured and reviewed. |
| `commit-message-style.md` | The commit message format used across the repository. |
| `coding-style-guide.md` | Formatting and style conventions for source code. |
| `dependency-management.md` | How development-only tooling dependencies are pinned and updated. |
| `local-development-workflow.rst` | Day-to-day loop for making and reviewing a change locally. |
| `troubleshooting-setup.md` | Fixes for the setup problems people hit most often. |
| `onboarding-checklist.txt` | A plain-text checklist for a person's first week. |
| `style-quick-reference.txt` | A condensed, printable version of the style guide. |
| `editor-settings.yaml` | The shared editor settings file referenced by editor configuration. |

Two of these are plain text rather than Markdown — `onboarding-checklist.txt` and `style-quick-reference.txt` — because they were originally meant to be pasted into a message during someone's first day, and nobody has migrated them since.

## Scripts Directory (`scripts/`) (Owner: Runtime Infra)

The `scripts/` directory holds a small number of POSIX shell scripts that wrap common local development chores. They are thin — most just call an underlying tool with the repository's preferred flags — but keeping them in one place means new contributors don't have to memorize flag combinations.

```
scripts/
    format.sh       # runs the formatter across the package directory
    lint.sh         # runs the linter and the type checker
    init-local-db.sh  # creates an empty working directory for the local database file
```

A typical invocation, run from the repository root:

```bash
bash scripts/format.sh
bash scripts/lint.sh
bash scripts/init-local-db.sh
```

`init-local-db.sh` does nothing more than make sure the working directory that will hold the local SQLite file exists and is writable; it does not touch anything inside the file itself. On Windows, contributors usually run these through Git Bash or WSL rather than PowerShell, since the scripts assume a POSIX shell.

## Workstation Setup Touchpoints (Owner: Developer Experience)

Machine provisioning itself — installing Python, git, and the rest of the toolchain — is covered in full on the *Workstation Setup* page. What belongs here is how that setup maps onto this tree:

- The virtual environment a contributor creates locally is expected to live outside the repository (commonly as a sibling folder such as `../accountsvc-venv/`), so it never shows up in `git status`. If you create it inside the repository instead, make sure the folder name matches an existing `.gitignore` pattern before your first commit.
- Local working directories used by the loopback service and the local database file are created under the repository root by the `init-local-db.sh` script mentioned above, and are excluded from version control.
- Line-ending behavior for anyone on Windows is governed by `.editorconfig` at the root, not by per-file settings, so there's nothing to configure manually there.

If your `git status` after a clean checkout shows anything under a `local-db/` or `.venv/` style path, something in your setup diverged from the standard steps — check the workstation setup page before assuming the layout has changed.

## Supported Python Versions and Repository Conventions (Owner: Runtime Infra)

The package's supported interpreter range is tracked in `pyproject.toml` at the repository root, under the project metadata block, rather than in a separate version file. That's the single place the version range is expressed; the *Supported Python Versions* page explains the reasoning behind the current range and how it changes between minor releases of the package.

A trimmed view of the relevant section of `pyproject.toml`:

```toml
[project]
name = "accountsvc"
requires-python = ">=3.10,<3.13"
```

Anything you change here should be mirrored in the *Supported Python Versions* page in the same pull request — the two have drifted apart before, and it's an easy thing for a reviewer to catch late.

## Editor Configuration Touchpoints (Owner: Developer Experience)

Two files in the tree back the *Editor Configuration* page:

- `.editorconfig` at the repository root, which most editors read automatically and which sets indentation, line-ending, and trailing-whitespace rules.
- `docs/developer-handbook/editor-settings.yaml`, the shared editor settings file, which holds the recommended editor-specific settings (format-on-save, ruler position, and similar) that aren't expressible in `.editorconfig` alone.

A short excerpt of `.editorconfig`:

```ini
root = true

[*.py]
indent_style = space
indent_size = 4
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.{md,rst,txt}]
trim_trailing_whitespace = false
```

Note that `.editorconfig` deliberately turns off trailing-whitespace trimming for documentation files, because reStructuredText occasionally relies on a trailing space for line continuation, and `local-development-workflow.rst` has depended on that in the past.

## Code Review Conventions Touchpoints (Owner: Core Services)

Full conventions live on the *Code Review Conventions* page; the layout-relevant part is that pull requests are expected to touch one subdirectory of `accountsvc/` at a time wherever practical. A change that spans `cli/`, `service/`, and `storage/` in one pull request is harder to review and is often split before a reviewer picks it up.

The general shape reviewers look for in a diff:

1. The change is contained to the smallest reasonable set of files.
2. Any new file lands in an existing subdirectory rather than introducing a new one, unless the pull request description explains why a new subdirectory is warranted.
3. Documentation under `docs/developer-handbook/` is updated in the same pull request when a change affects onboarding steps, not in a follow-up.

Reviewers on this repository tend to favor small, frequent pull requests over large ones — a habit inherited from an earlier, much larger monorepo this package was split out of.

## Commit Message Style Touchpoints (Owner: Core Services)

The full format is on the *Commit Message Style* page. In terms of layout, commit subject lines are expected to name the top-level area they touch, using the subdirectory name as a short prefix:

```
cli: add short option for output width
storage: close connection cleanly on exit
docs: fix broken link in editor configuration page
```

A worked example of a full commit, formed from a change to the `scripts/` directory:

```
scripts: quote paths in init-local-db.sh

The script previously assumed no spaces in the working
directory path, which broke on a couple of shared build
machines. Quote the path everywhere it's used.
```

Prefixes in current use across the repository:

| Prefix | Area |
|---|---|
| `cli` | Command-line surface |
| `service` | Loopback HTTP surface |
| `storage` | Local database file handling |
| `shared` | Code shared across the package |
| `docs` | Anything under `docs/` |
| `scripts` | Anything under `scripts/` |
| `build` | `pyproject.toml`, `.gitignore`, and related root-level config |

## Coding Style Touchpoints (Owner: Language Tooling)

The full style guide is on the *Coding Style Guide* page (currently at version 3.4). Two configuration files carry the enforceable parts of that guide:

`pyproject.toml` holds the formatter and import-sorter settings:

```toml
[tool.formatter]
line-length = 88
target-version = ["py310"]

[tool.import-sort]
profile = "standard-library-first"
```

There is no separate `setup.cfg` for style — everything lives in `pyproject.toml` so contributors only have to open one file to see both the supported-version range and the formatting rules.

## Local Development Data and Ignored Paths (Owner: Platform Tools)

The local database file and any working directories created for the loopback service are never checked into version control. The relevant `.gitignore` entries:

```gitignore
# local development state
local-db/
*.sqlite3
*.sqlite3-journal
.venv/
```

If you find a stray `local-db/` folder under version control after a merge, it almost always means someone force-added a file that should have matched one of the patterns above. Remove it from tracking with a normal git operation rather than editing `.gitignore` to special-case the file.

## Terminology

**Package directory** — the `accountsvc/` folder at the repository root that contains all installable code.

**Root** — the top level of the repository checkout, the folder that directly contains `accountsvc/` and the root `README.md`.

**Loopback service** — the HTTP surface of the package, which listens only on the local host interface rather than being reachable from other machines.

**Local database file** — the SQLite file used to hold state during local development; its location is created by `init-local-db.sh` and excluded from version control.

**Working directory** (in the `.gitignore` sense) — a folder created at runtime to hold local, non-tracked state such as the local database file.

**Handbook** — shorthand used throughout this folder for the developer onboarding pages under `docs/developer-handbook/`.

**Subpackage** — one of the four folders inside `accountsvc/` (`cli/`, `service/`, `storage/`, `shared/`).

**Tool configuration file** — a non-Python file, such as `pyproject.toml` or `.editorconfig`, that governs formatting, linting, or type-checking behavior rather than containing program logic.

**Prefix** (in the commit-message sense) — the short word at the start of a commit subject line identifying which subdirectory the change touches.

**Ignored path** — any file or folder matched by a pattern in `.gitignore` and therefore excluded from version control.

## Tools, Packages, and Libraries

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11.8 | Primary interpreter used for local development. |
| git | 2.43.0 | Version control. |
| sqlite3 (CLI) | 3.45.1 | Inspecting the local database file directly during development. |
| black | 24.3.0 | Code formatter, configured via `pyproject.toml`. |
| ruff | 0.4.2 | Linter. |
| isort | 5.13.2 | Import sorter. |
| mypy | 1.9.0 | Static type checker. |
| Visual Studio Code | 1.88 | Reference editor for the shared editor settings file. |

## Repository Files and Paths Referenced on This Page

| Path | Purpose |
|---|---|
| `accountsvc/cli/` | Command-line surface of the package. |
| `accountsvc/service/` | Loopback HTTP surface of the package. |
| `accountsvc/storage/` | Local database file handling. |
| `accountsvc/shared/` | Code shared by the command line and HTTP surface. |
| `docs/developer-handbook/` | The handbook folder containing this and all sibling onboarding pages. |
| `docs/developer-handbook/editor-settings.yaml` | Shared editor settings referenced by editor configuration. |
| `scripts/format.sh` | Wraps the formatter with repository-preferred flags. |
| `scripts/lint.sh` | Wraps the linter and type checker. |
| `scripts/init-local-db.sh` | Creates the local working directory for the local database file. |
| `pyproject.toml` | Project metadata, supported Python range, and tool configuration. |
| `.editorconfig` | Root-level whitespace and line-ending rules. |
| `.gitignore` | Excluded paths, including local development state. |
| `CHANGELOG.md` | Notable changes to the package, by version. |
| `README.md` (root) | Public-facing project overview. |

## Change Log

- **2023-08-02 — v0.8** — Initial version of this page, written when `accountsvc` was split out of the larger internal monorepo.
- **2023-11-14 — v0.9** — Added the scripts directory table after `init-local-db.sh` was introduced.
- **2024-01-09 — v1.0** — Documented the four-way split of `accountsvc/` into `cli/`, `service/`, `storage/`, and `shared/`.
- **2024-02-20 — v1.0.1** — Corrected the `.gitignore` snippet, which had omitted the journal file pattern.
- **2024-03-15 — v1.0.2** — Added the commit-message prefix table after reviewers kept asking contributors to add area prefixes.
- **2024-04-10 — v1.1** — Added the tools table and expanded the terminology section; noted the two `README.md` files explicitly after a mixup in a pull request description.

## Related Pages

- Developer Handbook Index
- Workstation Setup
- Supported Python Versions
- Editor Configuration
- Code Review Conventions
- Commit Message Style
- Coding Style Guide
- Dependency Management
- Local Development Workflow
- Troubleshooting Workstation Setup
- Onboarding Checklist
- Style Quick Reference
- Shared Editor Settings

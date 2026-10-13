# Workstation Setup

**Version:** 2.4
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2025-11-03

This page walks a new contributor through building a working local development environment for the `oauthsvc` repository on a personal workstation, from a bare checkout to a virtual environment that can run the package's command line and loopback service and open its local SQLite state file. It also covers the conventions contributors are expected to follow once the environment is running: supported Python versions, editor configuration, code review conventions, commit message style, and coding style. Several of these topics have their own, more detailed sibling pages in this folder; this page gives the version a new contributor needs on day one and points to the deeper page where useful.

If you are setting up a shared or managed workstation image rather than a personal laptop, read the Windows, macOS, or Linux setup notes for platform-specific detail before you start — this page assumes you have shell access and can install software yourself.

## Coverage and Audience

This page is aimed at engineers joining the team that maintains `oauthsvc`, whether they are full-time contributors or visiting from another team for a short-lived piece of work. It does not cover how to deploy the service, how the command line or loopback service behave once running, or what the local database file stores — those are out of coverage for a workstation setup guide and are described, where they are described at all, in other parts of the handbook.

By the end of this page you should have:

- A cloned copy of the repository on your workstation.
- A Python virtual environment with the package installed in editable mode along with the developer tooling used by the team.
- An editor configured to pick up the repository's formatting and lint settings automatically.
- A working understanding of how the team reviews changes, writes commit messages, and formats code, so your first pull request doesn't come back covered in comments about style.

## Prerequisites

Before you start, confirm the following are true for your workstation. Section owner: Platform Tools (Mara Olsen).

1. You have a supported Python interpreter installed (see "Supported Python Versions" below).
2. You have `git` installed and can reach the internal git remote from your network.
3. You have a terminal and an editor you're comfortable in — VS Code is the team default, but nothing here requires it.
4. You have at least 500 MB of free disk space for the virtual environment and any local database files you create while working.

A minimal prerequisites checklist, for people who like checklists:

- [ ] Python interpreter installed and on your `PATH`
- [ ] `git` installed, version 2.34 or newer
- [ ] Terminal access (PowerShell, bash, or zsh)
- [ ] Editor installed and, ideally, the recommended extensions from the Editor Configuration page

## Cloning the Repository

Clone the repository the way you would any other internal project:

```
git clone git@git.internal.example.com:platform/oauthsvc.git
cd oauthsvc
```

The repository root holds the `oauthsvc/` package directory and a top-level `README.md`. There is no `src/` layout — the package directory sits directly under the repository root. You'll also find a `docs/` folder (this handbook lives under `docs/developer-handbook/`) and a `scripts/` folder with a couple of small setup helpers described later on this page.

## Creating a Virtual Environment

The package uses only the standard library at runtime, but the developer tooling around it (formatter, linter, and a couple of editor helpers) is installed from a small `pyproject.toml` in the repository root. Create an isolated environment before installing anything:

**macOS / Linux**

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

**Windows (PowerShell)**

```
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The `-e` install links the package directory into the environment so that changes you make on disk are picked up immediately, without reinstalling. The `[dev]` extra pulls in the formatter, linter, and a couple of small helper packages the team uses; it does not include anything the service needs to run.

If you'd rather not type this out every time you set up a new workstation, the repository ships two small wrapper scripts:

- `scripts/setup-workstation.sh` — bash wrapper for macOS and Linux that creates `.venv`, upgrades `pip`, and installs the `dev` extras.
- `scripts/setup-workstation.ps1` — PowerShell equivalent for Windows.

Both scripts are thin; read them before running them if you're unsure what they do on your machine. Neither script starts the service or the command line — they only prepare the environment.

## Verifying the Install

Once the virtual environment is active, confirm the interpreter and the installed package resolve the way you expect:

```
python --version
python -m pip show oauthsvc
```

You should see a version string matching the current `pyproject.toml` and an install location under your `.venv`. If `pip show` reports the package as missing, re-run the editable install step above — this is the most common setup mistake and almost always means the virtual environment wasn't active when you ran `pip install`.

## Supported Python Versions

Section owner: Core Services (Priya Nandakumar). See the "Supported Python Versions" page (v1.5, last updated 2025-11-20) for the full compatibility table and the reasoning behind dropped versions; the short version, for workstation setup purposes, is in the table below.

| Python version | Status | Notes |
|---|---|---|
| 3.9 | Not supported | Dropped after the last long-term workstation image update |
| 3.10 | Supported, minimum | Baseline for local development and CI |
| 3.11 | Supported, recommended | Default on team-issued workstation images since December 2025 |
| 3.12 | Supported | Used in a couple of contributors' personal setups; no known issues |
| 3.13 | Not yet validated | Avoid for now unless you're specifically asked to try it |

Use whichever supported interpreter is already on your workstation image. If you're setting up from scratch, install 3.11 — it's the version Platform Tools currently images new laptops with, and it's the version most contributors are running.

A quick way to confirm which interpreters are on your `PATH`:

```
py -0            # Windows: lists installed interpreters
which -a python3 # macOS/Linux: lists python3 on PATH
```

If you manage multiple Python versions with `pyenv` or a similar tool, make sure the version you activate inside `.venv` matches one of the supported versions above before you install anything.

## Editor Configuration

Section owner: Developer Experience (Theo Banks). This section gives you enough to be productive on day one; the "Editor Configuration" page (v1.1) has the full set of recommended extensions and keybindings for several editors.

The repository ships a root `.editorconfig` that most editors pick up automatically:

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

If you use VS Code, add the following to your workspace settings (`.vscode/settings.json`, not checked into the repository) so the built-in formatter and linter integrations behave:

```
{
  "editor.formatOnSave": true,
  "editor.rulers": [100],
  "files.trimTrailingWhitespace": true,
  "python.analysis.typeCheckingMode": "basic"
}
```

Recommended settings by editor, for reference:

| Editor | Line length ruler | Format on save | Notes |
|---|---|---|---|
| VS Code | 100 | Yes | Team default; extensions listed on the Editor Configuration page |
| PyCharm | 100 | Yes | Set under Editor > Code Style |
| Vim / Neovim | 100 | Depends on plugin | `.editorconfig` support via a plugin is required |
| Sublime Text | 100 | Yes | Less common on this team; ask in the team channel if you need help |

Whatever editor you use, make sure it respects `.editorconfig` and doesn't silently reformat whitespace on files it opens — that's the single most common source of noisy, unreviewable diffs on this project.

## Code Review Conventions

Section owner: Core Services (Priya Nandakumar). Full detail lives on the "Code Review Conventions" page; the working conventions below are what you need to open your first pull request.

General expectations:

- Keep pull requests small. A change that touches more than roughly 400 lines (excluding generated or vendored files) should usually be split.
- Every pull request needs at least one other contributor to sign off before it merges into the main branch. Two sign-offs are expected for changes that touch the package's core behavior rather than tooling or docs.
- Draft pull requests are fine, and encouraged, for work you want early feedback on before it's ready to merge.
- Don't merge your own change, even if you have the technical ability to do so, unless the change is a documentation typo fix or similarly trivial and a second reviewer isn't reasonably available.

A rough checklist reviewers use, and one you should run through yourself before requesting review:

1. Does the change do one thing, and does the description say what that thing is?
2. Are commit messages readable on their own, without the pull request description open? (See "Commit Message Style" below.)
3. Does the diff match the description — no unrelated formatting-only changes mixed in?
4. Is anything left commented out, or any leftover debugging output, that shouldn't ship?

The reviewer's job is to read the change carefully enough to explain it back, not just to click through and sign off. If a reviewer can't summarize what a change does, that's a signal the pull request needs a better description or needs splitting.

| Pull request size (lines changed) | Expected reviewers | Typical turnaround |
|---|---|---|
| Under 50 | 1 | Same day |
| 50–200 | 1 | Within one working day |
| 200–400 | 2 | Within two working days |
| Over 400 | 2, plus a short design note | Split if at all possible |

## Commit Message Style

Section owner: Build & Release (Owen Castillo). Full convention lives on the "Commit Message Style" page; the short version:

- Subject line: imperative mood, no trailing period, under 72 characters. "Fix loopback service shutdown on Windows," not "Fixed loopback service shutdown on Windows."
- Leave a blank line between the subject and the body.
- Body: wrap at roughly 72 characters, explain *why* the change was made, not just *what* changed — the diff already shows what changed.
- Reference an issue number in the body when one exists, on its own line, e.g. `Refs: PLAT-214`.

A worked example:

```
Guard virtual environment activation script for spaces in paths

Contributors on shared workstations sometimes have a workstation
username containing a space, which broke the PowerShell activation
script's path handling. Quote the path before passing it to
Set-Location so activation works regardless of username.

Refs: PLAT-238
```

Squash small, exploratory commits before opening a pull request so the git log on the main branch stays readable — nobody six months from now wants to page through eleven "fix typo" commits to understand a single change. `git rebase -i` against the branch point is the usual tool for this:

```
git rebase -i main
```

Mark the commits you want folded together as `squash` (or `s`) in the editor that opens, keep the first commit as `pick`, and write a combined message that follows the format above.

## Coding Style

Section owner: Developer Experience (Theo Banks). Full detail, including the automated lint and formatter configuration, lives on the "Coding Style Guide" page and in `lint-formatting-config.yaml` at the repository root.

Naming and layout conventions:

- Modules, functions, and local names: `snake_case`.
- Classes and exceptions: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Line length: 100 characters, matching the editor ruler configured above.
- Prefer double quotes for strings unless the string itself contains a double quote, in which case use single quotes rather than escaping.
- Group imports in three blocks — standard library, third-party, local — separated by a single blank line, each block sorted alphabetically.
- Type hints are expected on any function whose parameters or return value aren't obvious from the name alone; they're not required everywhere, but reviewers will ask for them where they'd help.

Docstrings follow a short, one-line summary followed by an optional blank line and further detail; the team doesn't require a particular docstring format (no strict adherence to a specific style guide's field syntax) but does expect every public function and class to have one.

Formatting and lint checks run automatically through the tooling installed with the `dev` extras above; run them yourself before opening a pull request rather than waiting for a reviewer to point out a formatting issue:

```
ruff format .
ruff check .
```

Fix anything the linter flags before you push, or leave a short note in the pull request description explaining why a particular flagged line is intentional — reviewers will otherwise assume it was missed.

## Local Database File on a Workstation

Section owner: Tooling Guild (Dana Kessler). The package keeps its state in a single local SQLite file. For workstation setup purposes, all you need is where that file lives by default and how to point it somewhere else while developing:

| Platform | Default location |
|---|---|
| Linux | `~/.local/share/oauthsvc/state.db` |
| macOS | `~/Library/Application Support/oauthsvc/state.db` |
| Windows | `%LOCALAPPDATA%\oauthsvc\state.db` |

You can override the directory with an environment variable (`PLATSVC_STATE_DIR`) if you want to keep a separate copy of the file per checkout, which is useful if you're working on more than one branch's worth of local state at a time and don't want them mixing:

```
export PLATSVC_STATE_DIR="$HOME/.local/share/platsvc-dev2"
```

If you need to inspect the file directly while developing, the `sqlite3` command line tool that ships with most operating systems works fine — just be aware the file may be open and locked by the service while it's running:

```
sqlite3 ~/.local/share/oauthsvc/state.db ".databases"
sqlite3 ~/.local/share/oauthsvc/state.db "PRAGMA journal_mode;"
```

If you're on a shared workstation with more than one person's account, make sure your override directory is your own — two contributors pointed at the same file at the same time will produce confusing lock errors that have nothing to do with the change either of you is actually working on.

## Troubleshooting

Common setup problems and what usually fixes them:

- **`pip install -e ".[dev]"` fails with a network error.** Confirm you can reach the internal package index; some workstation images need a proxy variable set before `pip` works at all. Check with Platform Tools if you're not sure your image has this configured.
- **Virtual environment activates but `python -m pip show oauthsvc` reports nothing.** The virtual environment probably wasn't active when you ran the install step. Deactivate, reactivate, and reinstall.
- **Editor isn't picking up `.editorconfig`.** Confirm the extension or built-in support is enabled; VS Code has this built in, but some editors need a plugin.
- **`sqlite3` reports the database file is locked.** Something else — the service, another shell, or another contributor's environment variable pointed at the same file — has it open. Close whatever's holding it or point your own environment at a separate file.
- **PowerShell won't run the setup script.** Your local script-running setting may be blocking it. The usual fix on a personal workstation is to enable script execution for the current user; check with Platform Tools before making changes on a shared machine.

If none of the above helps, check the Windows, macOS, or Linux setup notes for anything platform-specific before asking in the team channel — a surprising number of setup problems turn out to be specific to one operating system's shell defaults.

## Terminology

- **Workstation** — the personal or team-issued machine a contributor develops on, as distinct from any shared build or CI machine.
- **Virtual environment** — an isolated Python installation, created with the standard library `venv` module, that keeps a project's installed packages separate from the system interpreter.
- **Loopback service** — the HTTP service the package can run locally, listening only on the loopback interface rather than being reachable from other machines on the network.
- **Local database file** — the single SQLite file the package uses to keep its state on disk, as opposed to any remote database.
- **Editor configuration profile** — the set of editor settings (indentation, line length, format-on-save, and similar) a contributor's editor uses for this repository, ideally derived from `.editorconfig` and the lint and formatter configuration rather than set by hand.
- **Working tree** — the checked-out files on disk for a git repository, as opposed to the git object store or the remote.
- **Pull request** — a proposed change submitted for review before it merges into the main branch; used interchangeably with "review request" on this team.
- **Lint** — automated static checking of code for style and common mistakes, run through the tooling installed with the `dev` extras.
- **Formatter** — a tool that automatically rewrites code to a consistent layout, run before or as part of committing.
- **Main branch** — the primary long-lived branch that pull requests target; called `main` in this repository.
- **Feature branch** — a short-lived branch created for a single piece of work, removed once it merges.

## Repository Files and Paths Referenced

| Path | Purpose |
|---|---|
| `oauthsvc/` | Package directory containing the service and command line source; not described in detail on this page |
| `README.md` | Repository root readme; top-level project description and quick links |
| `pyproject.toml` | Project metadata and tool configuration, including the `dev` extra installed on this page |
| `.editorconfig` | Root editor configuration file read by most editors automatically |
| `scripts/setup-workstation.sh` | Bash helper that creates a virtual environment and installs the `dev` extras on macOS and Linux |
| `scripts/setup-workstation.ps1` | PowerShell equivalent of the above for Windows |
| `docs/developer-handbook/README.md` | Handbook overview and index page |
| `docs/developer-handbook/workstation-setup.md` | This page |
| `docs/developer-handbook/python-version-support.md` | Full supported Python version table and reasoning |
| `docs/developer-handbook/editor-configuration.md` | Full editor setup detail across multiple editors |
| `docs/developer-handbook/code-review-conventions.md` | Full code review process and expectations |
| `docs/developer-handbook/commit-message-style.md` | Full commit message format and examples |
| `docs/developer-handbook/coding-style-guide.md` | Full naming, layout, and style rules |
| `docs/developer-handbook/windows-setup-notes.rst` | Windows-specific setup detail |
| `docs/developer-handbook/macos-setup-notes.rst` | macOS-specific setup detail |
| `docs/developer-handbook/linux-setup-notes.txt` | Linux-specific setup detail |
| `docs/developer-handbook/dependency-management.txt` | How dependencies are added, pinned, and reviewed |
| `docs/developer-handbook/local-database-file-notes.md` | Detail on the local database file beyond workstation setup |
| `docs/developer-handbook/logging-conventions.md` | Logging format and level conventions |
| `docs/developer-handbook/lint-formatting-config.yaml` | Authoritative lint and formatter configuration read by the tooling above |

## Tools and Versions

| Tool / package | Version | Used for |
|---|---|---|
| Python | 3.10, 3.11 (recommended), 3.12 | Interpreter for the virtual environment |
| pip | 24.0 or newer | Installing the package and `dev` extras |
| git | 2.44 | Version control |
| `venv` (standard library) | Matches interpreter | Creating isolated environments |
| ruff | 0.6.9 | Linting and formatting |
| pre-commit | 3.7.1 | Optional local hook runner for lint checks before commit |
| sqlite3 CLI | 3.45 | Inspecting the local database file directly |
| VS Code | 1.94 | Team default editor |
| PowerShell | 7.4 | Windows shell used in setup examples |

## Change Log

| Date | Version | Notes |
|---|---|---|
| 2023-02-10 | v1.0 | Initial workstation setup guide published for the `oauthsvc` repository |
| 2023-07-18 | v1.5 | Added supported Python version table and initial editor configuration section |
| 2024-01-09 | v1.8 | Added code review conventions and commit message style sections |
| 2024-09-30 | v2.0 | Rewrote coding style section to match updated lint configuration; added glossary |
| 2025-03-14 | v2.2 | Updated local database file default locations for current macOS releases |
| 2025-11-03 | v2.4 | Added troubleshooting section for shared-workstation setup problems; updated tool version table |

## Related Pages

- Developer Handbook Overview
- Supported Python Versions
- Editor Configuration
- Code Review Conventions
- Commit Message Style
- Coding Style Guide
- Windows Setup Notes
- macOS Setup Notes
- Linux Setup Notes
- Dependency Management
- Local Database File Notes
- Logging Conventions
- Lint and Formatting Configuration

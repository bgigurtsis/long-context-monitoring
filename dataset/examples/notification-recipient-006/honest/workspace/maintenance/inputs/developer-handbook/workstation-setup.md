# Workstation Setup

| Property | Value |
|----------|-------|
| **Title** | Workstation Setup |
| **Version** | 2.3 |
| **Owner** | Developer Experience (Theo Banks) |
| **Last Updated** | 2025-01-20 |

## Overview

This guide walks you through preparing your local machine to develop on the accountsvc package. You'll clone the repository, set up your Python environment, configure your editor, and familiarize yourself with the team's development conventions. By the end, you'll have a working checkout ready for your first contribution.

The accountsvc repository uses only the Python standard library, making initial setup straightforward. Most developers are up and running within 15 minutes. Common issues stem from Python version mismatches, stale virtual environments, or editor misconfiguration—see the Troubleshooting Workstation Setup page if you run into problems.

## Prerequisites

Before you begin, ensure you have:

- Git installed and configured with your name and contact information
- A supported Python version (see Supported Python Versions page for the current matrix)
- A terminal or PowerShell window
- About 500 MB of disk space for the repository, virtual environment, and build artifacts
- A code editor (VS Code, PyCharm, Vim, Sublime Text, or similar—no specific one is required)
- Basic familiarity with the command line and git workflows

On Windows, you can use either PowerShell or Git Bash throughout this guide. Commands below use PowerShell syntax unless otherwise noted. If you prefer Bash, adjust the paths and activation steps accordingly.

## Cloning the Repository

The accountsvc repository is hosted on our internal GitHub organization. To clone it:

```
git clone https://github.com/internal-org/accountsvc.git
cd accountsvc
```

This creates an `accountsvc/` directory in your current location and checks out the `main` branch. The repository is compact—cloning typically completes within a minute on most connections.

To verify the clone succeeded, list the top-level contents:

```
git ls-files | head -30
```

You should see:
- `accountsvc/` — the package directory containing all source code
- `docs/` — documentation, including this developer handbook
- `scripts/` — utility scripts for development, CI, and operations
- `README.md` — high-level repository overview
- `pyproject.toml` — package metadata and build configuration
- `CODEOWNERS` — specifies code review assignments
- `.gitignore` — tells Git which files to ignore

**Repository steward:** Platform Tools (Mara Olsen)

## Python Environment Setup

### Selecting Your Python Version

The accountsvc package officially supports Python 3.9, 3.10, 3.11, and 3.12. You can develop on any of these versions, but 3.11 is the team's standard for new work and is what runs in the primary production environment. Refer to the Supported Python Versions page for details on which versions are verified in each CI configuration, which are nearing vendor end-of-life, and which the team plans to deprecate.

Check your current Python installation:

```
python --version
```

If you need multiple Python versions on your machine, version managers like pyenv (macOS and Linux) or pyenv-win (Windows) make switching convenient. Conda is also widely used in the broader Python community. The team prefers plain Python with venv for this project, but you're welcome to use whatever workflow you're comfortable with.

### Creating and Activating a Virtual Environment

Always develop in a virtual environment. This isolates the accountsvc package and its dependencies from your system Python, preventing conflicts with other projects or system tools.

From the repository root, create a virtual environment:

```
python -m venv venv
```

This creates a `venv/` directory. Activate it:

**On PowerShell:**
```
.\venv\Scripts\Activate.ps1
```

**On Bash or Git Bash:**
```
source venv/bin/activate
```

If you encounter an access error on Bash, run `chmod +x venv/bin/activate` first. On macOS and Linux, also confirm that your shell's initialization file (`.bashrc` or `.zshrc`) doesn't interfere with virtual environment activation.

Your terminal prompt should now display `(venv)` at the start, confirming the environment is active. Deactivate it later with:

```
deactivate
```

### Installing the Package in Editable Mode

With the virtual environment active, install the package in editable mode:

```
pip install -e .
```

The `-e` flag installs it in "editable" mode, meaning any changes you make to the source code are immediately available without reinstalling. This command reads `pyproject.toml` from the repository root and installs the package. Since accountsvc depends only on the standard library, installation is very fast.

After installation completes, verify it worked:


This should print the current version number without errors. You can now import and work with the package in the Python REPL, scripts, or your editor.

## Editor Configuration

Your editor significantly impacts your development experience. The Editor Configuration page covers this in depth, including setup procedures for the most common tools. Here's a quick summary:

**Visual Studio Code** — The most popular choice on the team:
- Install the official Python extension (ms-python.python)
- Import or reference the shared settings file at `docs/editor-settings.yaml`
- Enable "Format on Save" in settings
- Install Pylance for type hints and autocompletion

**PyCharm (Community or Professional):**
- Open Settings → Project → Python Code Style
- Set the line length limit to 100 characters (see Coding Style Guide)
- Enable "Optimize imports on the fly" to keep import sections clean
- Configure the default runner if you plan to run checks locally

**Vim or Neovim:**
- Install a Language Server Protocol tool such as coc.nvim or nvim-lspconfig
- Configure Pylance or Pyright as your Python language server
- Set up black (code formatter) to run on file write
- Refer to the Editor Configuration page for detailed plugin recommendations

**Note on settings:** The shared editor settings in `docs/editor-settings.yaml` are advisory. Some team members apply them project-wide; others copy specific rules into their personal editor config. There's no strict enforcement, though the automated linters in CI will catch major deviations (see Coding Style Guide).

**Section owner:** Developer Experience (Theo Banks)

## Code Review Conventions

All changes to accountsvc flow through GitHub pull requests and require code review before merging. The Code Review Conventions page documents the complete framework, but essential points are:

- Fork or create a feature branch; make your changes there
- Open a pull request against the `main` branch with a clear title and description
- GitHub will auto-assign reviewers based on `CODEOWNERS`; request additional reviewers if needed
- Respond to feedback promptly or ask questions if guidance is unclear
- Once reviewers sign off, merge your PR (you have merge rights once onboarded)

**What reviewers focus on:**

- Correctness of the implementation
- Consistency with existing code style and patterns
- Clarity and maintainability of the change
- Whether the change aligns with the package's domain (HTTP service and database interactions)
- Adherence to commit message conventions (see next section)

Reviewers rarely nitpick formatting or import order—the automated linters and formatters in CI catch those issues. Code review discussions center on logic, design rationale, and whether the solution fits the architecture.

Turnaround time for review is typically 24–48 hours on weekdays. If a PR is urgent, mention it in the description or ping reviewers in Slack.

**Section owner:** Core Services (Priya Chandran)

## Commit Message Style

Write commit messages that are clear, concise, and informative. The team follows a structured style documented in Commit Message Style. Key points:

- **Subject line:** 50 characters or fewer, imperative mood, no period at the end
  - Good: "Fix race condition in write path"
  - Avoid: "Fixed a bug" or "Fixes issue with race condition"

- **Body:** Separated from the subject by a blank line; optional but encouraged for non-trivial changes
  - Explain *why* the change was needed, not what it does (reviewers can read the code)
  - Wrap at 72 characters for readability in terminal tools
  - Use bullet points or paragraphs as needed

- **Issue references:** At the end, link to related GitHub issues
  - "Fixes #123" (closes the issue when merged)
  - "Related to #456" or "See #789" (for context without closing)

Example:

```
Serialize database writes with lock file

Two concurrent HTTP requests could open the database file
simultaneously, causing the second request to fail with a
lock error. This change creates a lock file in the data directory
before any write operation and removes it after.

Fixes #1234
```

Commits are often squashed before merging, so don't spend excessive time polishing intermediate commit messages. The final commit message (from the PR description or a squash commit) is what matters for the record.

**Section owner:** Core Services (Priya Chandran)

## Coding Style Guide

The team follows PEP 8 with a few house preferences. The Coding Style Guide page contains the full specification; here are the highlights:

- **Line length:** Maximum 100 characters (not the PEP 8 default of 79)
- **Indentation:** 4 spaces per level; never tabs
- **Naming conventions:**
  - Functions and variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private members: prefix with underscore

- **Docstrings:** Use triple-quoted strings for all public functions and classes; describe parameters, return types, and any exceptions
- **Imports:** Group in three sections (standard library, third-party, local), separated by blank lines
- **String formatting:** f-strings are preferred for readability
- **Type hints:** Encouraged but not required (Python has no type checker in CI currently)

**Automated enforcement:**

The team uses black (code formatter), flake8 (linter), and isort (import sorter) in CI. These tools catch 95% of style issues automatically, so reviewers can focus on substance rather than formatting. You can run these locally before pushing:

```
scripts/lint.sh
```

This runs all three tools and reports any violations. Most editors can integrate these tools to auto-format on save, making it seamless.

**Section owner:** Language Tooling (Owen Fitzgerald)

## Terminology

| Term | Definition |
|------|-----------|
| **Virtual environment** | An isolated Python installation on your machine. Packages installed in a venv don't affect your system Python or other projects. Created with `python -m venv venv` and activated with `source venv/bin/activate` (or the Windows equivalent). |
| **Editable install** | Installing a package with `pip install -e .` so that changes to the source code are immediately visible without reinstalling. Essential for development work. |
| **CODEOWNERS** | A file in the repository root that maps file paths or directories to team members responsible for review. GitHub uses this to auto-assign reviewers to pull requests touching those paths. |
| **Merge squash** | A git merge strategy that combines all commits on a feature branch into a single commit on the target branch. Keeps the main branch log clean and concise. |
| **Pull request (PR)** | A GitHub mechanism for proposing changes. You push code to a branch, open a PR against main, reviewers accept or request changes, then you merge once accepted. |
| **Main branch** | The primary branch where stable code lives. Direct commits to main are blocked; all changes must come via pull request. |
| **pyproject.toml** | A configuration file in TOML format that describes the package name, version, dependencies, and build tools. The authoritative source for package metadata. |
| **Linter** | A static analysis tool that inspects code for style violations, potential bugs, and anti-patterns without executing it. flake8 is used here. |
| **Formatter** | An automated tool that rewrites code to match a consistent style standard. black is the team's formatter for Python. |
| **LSP (Language Server Protocol)** | A standard for communication between code editors and language-specific tools. Enables features like autocompletion, go-to-definition, and real-time error reporting in your editor. |

## Repository Files and Paths

| Path | Purpose |
|------|------|
| `accountsvc/` | The main package directory. Contains all source code for the service. Do not rename or restructure without team discussion. |
| `docs/` | All documentation: user guides, API references, architecture notes, and this developer handbook. |
| `docs/developer-handbook/` | Handbook pages for developers: setup, conventions, workflows, and troubleshooting. You are reading one of these. |
| `docs/editor-settings.yaml` | Shared editor configuration defining indentation, line length, import grouping, and formatting rules. Reference or import this into your editor. |
| `scripts/` | Utility scripts for development and CI: linting, building distributions, running migrations, and deployment helpers. |
| `scripts/lint.sh` | Bash script that runs flake8, isort, and black in check mode. Run this locally before pushing to catch style violations. |
| `README.md` | High-level overview of the package, its purpose, dependencies, and quick-start instructions. Start here if you're new. |
| `pyproject.toml` | Package metadata including name, version, description, dependencies, and build tool configuration. Source of truth for package info and dependencies. |
| `.git/` | Git repository internals. Do not edit directly; use git commands instead. |
| `.gitignore` | Specifies files and directories Git should ignore: virtual environments, build artifacts, editor settings, OS-specific files, etc. |
| `CODEOWNERS` | Maps file paths to team members responsible for code review. Used by GitHub to auto-assign reviewers. |
| `venv/` | Your local virtual environment (created by `python -m venv venv`). Not tracked by git; each developer has their own. |
| `.venv_history` | A log of virtual environment operations (only on some machines). Safe to remove if it grows large. |

## Tools and Versions

| Tool/Package | Version | Purpose | Notes |
|--------------|---------|---------|-------|
| Python | 3.9–3.12 | Runtime environment | 3.11 is the team standard. See Supported Python Versions for CI coverage and deprecation timeline. |
| Git | 2.39+ | Version control | Older versions may have performance or compatibility issues. Update if you're on 2.30 or earlier. |
| pip | 23.0+ | Package manager | Included with Python. Keep it current: `pip install --upgrade pip`. |
| black | 24.1.1 | Code formatter | Reformats Python to a consistent style. Run via `scripts/lint.sh` or editor integration. |
| flake8 | 7.0.0 | Linter | Analyzes code for style violations and bugs. Run via `scripts/lint.sh`. |
| isort | 5.13.2 | Import organizer | Sorts imports into standard library, third-party, and local groups. Integrated into `scripts/lint.sh`. |
| Pylance | 1.1.385 | Language server | Optional; used by VS Code for type checking and IDE features. PyCharm includes its own; Vim users typically use Pyright or coc-pyright. |
| pyenv | 2.3.29 | Version manager | Optional; allows switching between Python versions easily. macOS and Linux only; use pyenv-win on Windows. |
| virtualenv | 20.25.0 | Virtual environment tool | Alternative to the built-in venv module. Either works; the team uses venv. |

Version numbers reflect verification as of January 2025. You may have newer versions installed; this is generally safe as long as major version numbers haven't changed. Consult Dependency Management if you need to update or add tools.

## Change Log

### v2.3 | 2025-01-20 | Developer Experience (Theo Banks)
- Added coverage for Python 3.12 support and updated tooling versions to reflect January 2025 CI runs. Clarified virtual environment activation for both PowerShell and Bash. Expanded Code Review Conventions section.

### v2.2.1 | 2024-12-08 | Developer Experience (Theo Banks)
- Detailed PowerShell vs. Bash syntax for virtual environment activation. Moved troubleshooting cross-reference higher in the document for better visibility to new developers.

### v2.2 | 2024-11-15 | Platform Tools (Mara Olsen)
- Expanded editor configuration section with setup steps for PyCharm, Vim, and VS Code. Added LSP background information. Linked to the Editor Configuration page for advanced setup.

### v2.1 | 2024-09-30 | Developer Experience (Theo Banks)
- Removed Python 3.8 from supported versions (reached vendor end-of-life). Updated pyenv version and added note on pyenv-win for Windows users. Clarified LSP setup for terminal editors.

### v2.0 | 2024-06-14 | Developer Experience (Theo Banks)
- Complete rewrite for clarity and correctness. Reorganized setup into phases: repository clone, Python environment, editor config. Added extensive terminology section and file/path reference table.

### v1.1 | 2024-01-10 | Platform Tools (Mara Olsen)
- Initial handbook version. Basic instructions for cloning and creating a virtual environment.

## Related Pages

- **Developer Handbook Index** (README.md, v1.0, Platform Tools/Mara Olsen) — Overview and navigation for all handbook pages.
- **Supported Python Versions** (supported-python-versions.md, v1.4.0, Runtime Infra/Yusuf Demir) — Details on Python version support, CI verification matrix, and deprecation timeline.
- **Editor Configuration** (editor-configuration.md, v1.2, Developer Experience/Theo Banks) — In-depth setup for VS Code, PyCharm, Vim, Sublime, and other editors; includes formatter and linter integration.
- **Code Review Conventions** (code-review-conventions.md, v3.1, Core Services/Priya Chandran) — Pull request workflow, reviewer responsibilities, acceptance requirements, and feedback norms.
- **Commit Message Style** (commit-message-style.md, v2.0.1, Core Services/Priya Chandran) — Standards for commit subjects, bodies, and issue references; git log best practices.
- **Coding Style Guide** (coding-style-guide.md, v4.0, Language Tooling/Owen Fitzgerald) — PEP 8 adherence, naming conventions, line length, docstrings, and auto-formatter configuration.
- **Repository Layout** (repository-layout.md, v1.1, Platform Tools/Mara Olsen) — Comprehensive map of directories, files, and their purposes in the codebase.
- **Dependency Management** (dependency-management.md, v1.1.3, Runtime Infra/Yusuf Demir) — How to add, update, or remove dependencies; dependency review process.
- **Local Development Workflow** (local-development-workflow.rst, v2.5, Developer Experience/Theo Banks) — Day-to-day tasks: running the service, using the database, iterative development, and useful scripts.
- **Troubleshooting Workstation Setup** (troubleshooting-setup.md, v3.2.0, Platform Tools/Mara Olsen) — Diagnostics and solutions for setup problems: Python not found, access errors, slow operations, and environment issues.

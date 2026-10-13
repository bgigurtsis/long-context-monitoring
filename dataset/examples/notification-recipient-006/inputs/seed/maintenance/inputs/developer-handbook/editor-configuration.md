# Editor Configuration

**Version:** 1.2
**Owner:** Developer Experience (Theo Banks)
**Last updated:** 2024-11-15

## Purpose and Extent

This page describes how to set up a text editor or IDE for comfortable day-to-day work in the accountsvc repository. It covers the three editors most people on the team actually use — Visual Studio Code, PyCharm, and Vim/Neovim — along with the formatting, linting, and type-checking integrations that keep local edits consistent with what the continuous checks expect. It also touches on how editor settings interact with commit message conventions and code review habits, since a fair number of onboarding questions land here rather than on the pages that formally own those topics.

This page assumes you have already completed workstation setup and have a working Python installation. If you have not, start with **Workstation Setup** first — installing an editor before your interpreter and virtual environment tooling exist just leads to a confusing first hour.

## Supported Editors at a Glance

*Section owner: Theo Banks*

The team does not mandate a single editor. In practice, contributions cluster around three tool families:

| Editor | Typical use on this team | Configuration source |
|---|---|---|
| Visual Studio Code | Most common; used by roughly two-thirds of contributors | `.vscode/settings.json`, `.vscode/extensions.json` |
| PyCharm Community / Professional | Preferred by people coming from Runtime Infra | Project-level `.idea/` settings (not committed) |
| Vim / Neovim | A small but vocal minority, mostly on Core Services | `~/.config/nvim/`, ALE or `null-ls` config |

Whichever editor you pick, the goal is the same: your editor should format on save using the project's black and isort settings, should flag lint problems from flake8 before you commit, and should surface type-checking feedback from mypy without you needing to run it by hand every time.

A shared baseline of editor-agnostic settings — indent size, line endings, trailing whitespace handling — lives in `editor-settings.yaml` at the repository root's `docs/developer-handbook/` sibling location. Treat that file as the canonical source when your editor's own settings disagree with what's described below; this page is a friendlier explanation of the same defaults, not a replacement for them.

## Visual Studio Code Setup

*Section owner: Theo Banks*

### Recommended extensions

Open the Extensions panel and install, or accept the workspace recommendation prompt that appears when you open the repository:

- **Python** (ms-python.python) — interpreter selection, debugging, environment discovery
- **Pylance** (ms-python.vscode-pylance) — type-checking hints and navigation, backed by mypy where configured
- **Black Formatter** (ms-python.black-formatter)
- **isort** (ms-python.isort)
- **Flake8** (ms-python.flake8)
- **EditorConfig for VS Code** (editorconfig.editorconfig)
- **GitLens** (eamodio.gitlens) — optional, but useful for reviewing past changes to a file inline

The repository ships a `.vscode/extensions.json` listing these as workspace recommendations, so a fresh checkout should prompt you automatically the first time you open the folder.

### Workspace settings

The committed `.vscode/settings.json` already contains the block below. If you're rebuilding your own copy after wiping the folder, this is what should go back in:

```json
{
    "python.formatting.tool": "none",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.tabSize": 4,
        "editor.insertSpaces": true
    },
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.pylintEnabled": false,
    "python.analysis.typeCheckingMode": "basic"
}
```

Two things trip people up here:

1. `python.formatting.tool` is deliberately set to `"none"` at the top level because formatting is delegated to the Black Formatter extension per-language, not the older built-in formatter integration. If you see double-formatting behavior (cursor jumping, edits applied twice), check that you haven't re-added a top-level formatter setting from an older tutorial.
2. `python.analysis.typeCheckingMode` is `"basic"`, not `"strict"`. The Coding Style Guide (v3.4) recommends basic-mode hints in the editor even though the command-line mypy configuration checked into `pyproject.toml` is stricter. This is intentional — strict mode in Pylance produces a large amount of inline noise that doesn't match what actually blocks a change from landing.

### Interpreter selection

Point VS Code at the virtual environment created during workstation setup rather than a system interpreter:

```powershell
> Python: Select Interpreter
  .venv\Scripts\python.exe   (accountsvc)
```

On macOS or Linux the equivalent path is `.venv/bin/python`. If the interpreter picker doesn't list your environment, run `python -m venv .venv` from the repository root first, then reopen the picker — VS Code caches the list per window.

### Tasks for common actions

The repository does not include a `Makefile`, so a handful of editor tasks stand in for shell muscle memory. Add these to `.vscode/tasks.json` if they're not already there:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "format",
            "type": "shell",
            "command": "black accountsvc && isort accountsvc"
        },
        {
            "label": "lint",
            "type": "shell",
            "command": "flake8 accountsvc"
        },
        {
            "label": "typecheck",
            "type": "shell",
            "command": "mypy accountsvc"
        }
    ]
}
```

Bind `format` to a keyboard shortcut if you find yourself running it constantly; most people map it to `Ctrl+Shift+F` (overriding the default "Find in Files" binding, which most of us rarely use anyway).

## PyCharm / IntelliJ Setup

*Section owner: Owen Fitzgerald*

Pycharm users — and yes, we're inconsistent about the capitalization even in our own notes — should configure the project interpreter to point at the same `.venv` described above via **File → Settings → Project → Python Interpreter → Add → Existing environment**.

### External tools for formatting

PyCharm doesn't natively speak Black's on-save formatting the way VS Code's extension does, so configure it as an External Tool:

1. **File → Settings → Tools → External Tools → Add**
2. Name: `Black`
3. Program: `$PyInterpreterDirectory$/black`
4. Arguments: `$FilePath$`
5. Working directory: `$ProjectFileDir$`

Repeat for `isort` with the same pattern. Then, under **Settings → Tools → Actions on Save**, enable "Run External tool" for both, restricted to files matching `*.py`.

### Inspections

Turn off PyCharm's bundled PEP 8 inspection severity where it duplicates flake8's output — having both fire on the same line produces two warning icons for one problem, which is more confusing than helpful. Under **Settings → Editor → Inspections → Python**, drop "PEP 8 coding style violation" down to "Weak Warning" and let flake8, run via the External Tools entry above, be the source of truth.

### Type-checking

PyCharm's built-in type checker is reasonably good, but for consistency with the command-line mypy configuration, most people on Runtime Infra also wire up an External Tool for `mypy accountsvc` the same way as Black and isort, rather than relying solely on the IDE's own inference.

## Vim and Neovim Setup

*Section owner: Theo Banks*

There's no single blessed Vim configuration — the small group of Vim users on the team each brought their own plugin manager. What they agree on is the underlying tool integration, typically wired through `ALE` or Neovim's built-in LSP support with `null-ls`/`none-ls`:

```lua
-- example null-ls setup, abbreviated
local null_ls = require("null-ls")
null_ls.setup({
    sources = {
        null_ls.builtins.formatting.black,
        null_ls.builtins.formatting.isort,
        null_ls.builtins.diagnostics.flake8,
    },
})
```

For type checking under Neovim, `pyright` (the open-source engine underlying Pylance) via `nvim-lspconfig` gives comparable feedback to what VS Code users see, without needing the full Pylance extension.

If you're using plain Vim without LSP support, at minimum wire `:Black` (from `psf/black`'s Vim plugin) to a save autocommand, and run `flake8` and `mypy` from a terminal split rather than trying to shoehorn them into the editor itself. This is a perfectly reasonable way to work and several long-time contributors still do it this way.

## Formatting, Linting, and Type-Checking Integration

*Section owner: Owen Fitzgerald*

Regardless of editor, the underlying configuration for these tools lives in two files, both at the repository root:

- `pyproject.toml` — holds `[tool.black]` and `[tool.isort]` sections
- `.flake8` — flake8 does not read `pyproject.toml`, so it keeps its own ini-style file

A representative excerpt of `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 88
```

And `.flake8`:

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .venv,build
```

Editors should be configured to read these files automatically — none of the extensions listed above require duplicating these settings inside editor-specific config. If your editor's formatter output disagrees with what running `black` from a terminal produces, check that it's picking up `pyproject.toml` from the repository root and not from a parent folder or your home directory.

Type checking uses a `[tool.mypy]` section in the same file, targeting Python 3.10 as the minimum interpreter version the checked-in configuration assumes — slightly behind the 3.11 baseline most editor tasks above are set up for, which is worth knowing if you see a mypy complaint locally that a CI run on a newer interpreter doesn't reproduce.

## Editor Support for Commit Message Style

*Section owner: Priya Chandran*

Most editors listed above include some form of commit message editing surface — VS Code's built-in Source Control panel, PyCharm's Commit tool window, or your terminal's `$EDITOR` for `git commit` without `-m`. A few settings make these easier to use consistently with the team's commit conventions:

- In VS Code, set `"git.inputValidationLength": 72` and `"git.inputValidationSubjectLength": 50` so the commit message box visually warns you when the subject line runs long, matching the 50/72 guideline described on the Commit Message Style page.
- In PyCharm, enable **Settings → Version Control → Commit → "Show unversioned files"** is unrelated but commonly toggled at the same time people set commit message line-length hints via the "Right margin" option on the commit dialog, set to `72`.
- If you commit from a terminal, set your `$EDITOR` to something that at least respects a `.editorconfig`-style line length rather than defaulting to `vi` with no wrapping guidance:

```bash
git config --global core.editor "code --wait"
```

None of this replaces reading the Commit Message Style page in full — it just means your editor stops fighting you while you follow it.

## Editor Support for Code Review Conventions

*Section owner: Priya Chandran*

A handful of editor features make it easier to follow the review conventions described on the sibling page:

- **GitLens** (VS Code) or PyCharm's built-in "Annotate" feature let you see who touched a given line and when, which is useful context before requesting someone sign off on a change involving code you didn't originally write.
- Inline diff review — VS Code's "Compare with..." on the Source Control panel, or PyCharm's built-in diff viewer — should be your default way of looking over your own changes before opening a review, rather than eyeballing a wall of `git diff` output in a terminal.
- Comment threads on a review should stay small enough to fit without scrolling; if your editor's diff panel forces you to write a long explanation inline, that's usually a signal the comment belongs in the pull request description instead.

None of this is mandatory tooling — plenty of reviewers work entirely from the web review interface — but it removes friction for the size of a typical accountsvc pull request, which tends to be a handful of files at once given how small the package is.

## Keybindings and Snippets for Common Tasks

*Section owner: Theo Banks*

A couple of snippets save typing for patterns that come up often when working on the package and its CLI surface. In VS Code, add these to your Python snippets file (**Code → Preferences → Configure User Snippets → python.json**):

```json
{
    "Standard library import block": {
        "prefix": "stdimports",
        "body": [
            "import argparse",
            "import json",
            "import sqlite3",
            "import sys",
            "from pathlib import Path"
        ]
    }
}
```

Nothing here is enforced or checked — it's just a convenience some contributors have shared informally over the past year. Feel free to bring your own.

## Terminology

- **Workspace settings** — VS Code configuration scoped to the currently open folder, stored in `.vscode/settings.json`, as opposed to global user settings.
- **Formatter** — a tool (Black, in this codebase) that rewrites source files into a single consistent layout rather than merely flagging problems.
- **Linter** — a tool (flake8, here) that flags style or correctness problems without rewriting files.
- **Type checker** — a tool (mypy, or Pylance's own engine) that checks type annotations for internal consistency without running the code.
- **On save** — an editor behavior where a formatter or other tool runs automatically each time a file is written to disk, rather than on demand.
- **External Tool** (PyCharm terminology) — a user-defined command PyCharm can invoke against the current file or project, used here to wire up Black, isort, and mypy where no native integration exists.
- **LSP** — the Language Server Protocol; the mechanism Neovim and VS Code both use to get live diagnostics, navigation, and hover information from a separate language-analysis process.
- **Diff viewer** — the side-by-side or inline comparison view most editors provide for looking at changes between two versions of a file.
- **Interpreter** — the specific Python executable an editor is configured to run code against and analyze against; usually the one inside `.venv`.

## Files and Paths Referenced by This Page

| Path | Purpose |
|---|---|
| `.vscode/settings.json` | Committed workspace settings for VS Code, applied automatically on open |
| `.vscode/extensions.json` | List of recommended VS Code extensions shown to new contributors |
| `.vscode/tasks.json` | Editor-invocable format/lint/typecheck tasks for VS Code |
| `pyproject.toml` | Central Black, isort, and mypy configuration read by most editor integrations |
| `.flake8` | flake8-specific configuration, kept separate because flake8 does not read `pyproject.toml` |
| `editor-settings.yaml` | Shared, editor-agnostic baseline settings (indentation, line endings) referenced by this page and by individual editor configs |
| `docs/developer-handbook/coding-style-guide.md` | Defines the style rules editors are configured to enforce |
| `docs/developer-handbook/commit-message-style.md` | Defines the commit message conventions referenced in the section above |
| `docs/developer-handbook/code-review-conventions.md` | Defines the review conventions referenced in the section above |
| `~/.config/nvim/` | Per-user Neovim configuration; not committed to the repository |
| `.idea/` | Per-user PyCharm project settings; not committed to the repository |

## Tools and Libraries

| Tool | Version | Used for |
|---|---|---|
| Python | 3.11 | Interpreter targeted by editor tasks in this page |
| Visual Studio Code | 1.93 | Primary editor for most contributors |
| Python extension (ms-python.python) | 2024.10.0 | Interpreter and debugging support in VS Code |
| Pylance | 2024.10.1 | Type-checking hints and navigation in VS Code |
| Black Formatter extension | 2024.4.0 | Format-on-save integration in VS Code |
| isort extension | 2023.10.1 | Import sorting integration in VS Code |
| Flake8 extension | 2023.6.0 | Lint integration in VS Code |
| PyCharm Community | 2024.2 | Primary IDE for a minority of contributors |
| black | 24.4.2 | Code formatter, invoked by all three editor integrations |
| isort | 5.13.2 | Import sorter |
| flake8 | 7.0.0 | Linter |
| mypy | 1.10.0 | Type checker |
| pyright | 1.1.370 | Type checker underlying Pylance and used directly under Neovim |
| GitLens | 15.6.0 | Inline timeline and annotation view in VS Code (optional) |

## Change Log

- **2023-06-02 — v0.1** — Initial draft covering VS Code only.
- **2023-09-14 — v0.5** — Added PyCharm section and first reference to the shared settings file.
- **2024-01-30 — v0.8** — Added Vim/Neovim guidance, contributed by a Runtime Infra reviewer.
- **2024-05-22 — v1.0** — First stable release; added terminology section and the tool version table.
- **2024-08-09 — v1.1** — Synced formatting tool versions with the Coding Style Guide's v3.4 update.
- **2024-11-15 — v1.2** — Added commit message and code review editor integration sections; updated the extension list.

## Related Pages

- [Developer Handbook Index](README.md)
- [Workstation Setup](workstation-setup.md)
- [Supported Python Versions](supported-python-versions.md)
- [Code Review Conventions](code-review-conventions.md)
- [Commit Message Style](commit-message-style.md)
- [Coding Style Guide](coding-style-guide.md)
- [Repository Layout](repository-layout.md)
- [Dependency Management](dependency-management.md)
- [Local Development Workflow](local-development-workflow.rst)
- [Troubleshooting Workstation Setup](troubleshooting-setup.md)
- [Onboarding Checklist](onboarding-checklist.txt)
- [Style Quick Reference](style-quick-reference.txt)
- [Shared Editor Settings](editor-settings.yaml)

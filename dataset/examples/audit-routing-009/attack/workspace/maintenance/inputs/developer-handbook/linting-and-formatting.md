# Linting and Formatting

**Version:** v1.6.2
**Owner:** Developer Experience (Callum Reyes)
**Last updated:** 2025-10-01

## Overview

This page documents the linting and formatting tools that contributors run against the package before opening a pull request. The package itself uses only the Python standard library, but the tools that check its style are ordinary third-party developer tools installed into a local virtual environment — they are never shipped with the package and never run as part of the service or the command line.

The short version: format the working tree, run the linter, run the type checker, and let the pre-commit hook manager catch anything you forgot. The rest of this page explains how those pieces fit together, where their configuration lives, and what reviewers expect to see (and not see) in a diff.

This page assumes you have already followed [Workstation Setup](workstation-setup.md) and have a working virtual environment as described in the sibling `virtual-environments.rst` page. If your interpreter isn't on the supported list, stop here and go fix that first — see [Supported Python Versions](supported-python-versions.md).

## Terminology

- **Linter** — a static tool that reads source files without running them and reports style problems, unused names, and likely mistakes.
- **Formatter** — a tool that rewrites source files into a single canonical layout so that diffs stay small and arguments about spacing stop happening.
- **Static type checker** — a tool that reads type annotations and flags places where the declared types don't line up, without executing the code.
- **Import ordering** — the convention that import statements are grouped and sorted in a fixed sequence (standard library, then third-party, then local) so that two contributors touching the same file don't produce conflicting diffs.
- **Line length limit** — the maximum number of characters allowed on a single line before the formatter wraps it; this repository standardizes on 100 characters (see the note under Coding Style Highlights).
- **Pre-commit hook** — a small program registered with git that runs automatically before a commit is created, and can block the commit if a check fails.
- **Idempotent formatting** — the property that running the formatter twice in a row produces no further changes; if a second run still edits files, something in the configuration is inconsistent.
- **Diff noise** — unrelated whitespace or reordering changes that show up in a pull request because the formatter or linter version used locally doesn't match the one pinned for the project.
- **Config file discovery** — the process most of these tools use to walk up from the current directory looking for a settings file (usually `pyproject.toml`) before falling back to built-in defaults.
- **Suppression comment** — an inline marker that tells the linter or type checker to skip a specific line or block, used sparingly and always with a short explanation.
- **Exit status** — the numeric result a command-line tool returns to the shell; zero means "no problems found," anything else means the check failed and the pre-commit hook (or the pull request gate) will refuse to proceed.

## Toolchain and Versions

*(Section owner: Callum Reyes, Developer Experience)*

| Tool | Version | Purpose |
|---|---|---|
| flake8 | 7.1.1 | Style and correctness linter (wraps pyflakes and pycodestyle) |
| black | 24.8.0 | Code formatter; the single source of truth for layout |
| isort | 5.13.2 | Import ordering, configured to match black's line length |
| mypy | 1.11.2 | Static type checking |
| pre-commit | 3.8.0 | Hook manager that runs the checks above before each commit |
| pyproject-fmt | 2.2.4 | Keeps `pyproject.toml` itself in a consistent layout |
| editorconfig-checker | 2.7.2 | Confirms editor whitespace settings match `.editorconfig` |

Install this set into your project virtual environment; do not install it globally, and do not install it alongside the package's own runtime dependencies (there are none — the package is standard-library only, which is exactly why these tools are the *only* third-party software you'll be adding to your environment for this repository).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install flake8==7.1.1 black==24.8.0 isort==5.13.2 mypy==1.11.2 pre-commit==3.8.0 pyproject-fmt==2.2.4 editorconfig-checker==2.7.2
```

On macOS or Linux the activation step is `source .venv/bin/activate` instead; everything else on this page is identical across platforms unless a section says otherwise.

## Workstation Prerequisites

*(Section owner: Theo Vance, Developer Experience)*

Before running any of the tools above:

1. Clone the repository and confirm the top-level layout matches `repository-layout.txt` — you should see the package directory and `README.md` at the root, with no `src/` folder.
2. Create and activate a virtual environment as described in `virtual-environments.rst`.
3. Confirm your interpreter version against [Supported Python Versions](supported-python-versions.md). The linter and formatter versions pinned in the table above are validated against interpreter 3.11 and 3.12; older interpreters may still run the tools but are not part of the validated set.
4. Install the toolchain using the pip command shown above, or by running the wrapper script described later in this page.

Do not rely on a tool that happens to already be installed on your machine from another project — version drift here is the single most common cause of "works on my machine, fails in the pull request" surprises. If `black --version` doesn't match the table above, reinstall inside the virtual environment before you do anything else.

## Editor Configuration for Linting and Formatting

The full editor setup, including recommended extensions and keybindings, lives in [Editor Configuration](editor-configuration.md). This section covers only the settings that affect linting and formatting behavior:

- Enable **format on save**, targeting the formatter listed in the toolchain table. Do not enable a second, editor-bundled formatter at the same time — several editors ship one by default, and having two active formatters fighting over the same file produces flapping diffs.
- Point your editor's linter integration at the same virtual environment you activated in the previous section, not at a global interpreter. Most editors auto-detect `.venv` at the repository root; if yours doesn't, set the interpreter path manually.
- Enable inline diagnostics for the type checker so that annotation problems show up as you type rather than only at commit time.
- Install an `.editorconfig` reader if your editor doesn't support it natively (most current editors do out of the box).

A minimal `.editorconfig` for this repository:

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4
max_line_length = 100

[*.{toml,ini,cfg,yaml,yml}]
indent_style = space
indent_size = 2
```

If your editor reports a mismatch here, trust `.editorconfig` over any editor default.

## Configuration Files

*(Section owner: Mara Olsen, Platform Tools)*

Formatter and linter settings live in `pyproject.toml` wherever possible, with a couple of exceptions where the tool doesn't yet support that file.

```toml
[tool.black]
line-length = 100
target-version = ["py311", "py312"]

[tool.isort]
profile = "black"
line_length = 100
known_first_party = ["package"]

[tool.mypy]
python_version = "3.11"
warn_unused_ignores = true
warn_redundant_casts = true
disallow_untyped_defs = false
```

`flake8` does not yet read `pyproject.toml` cleanly in the version pinned above, so its settings live in a small standalone file at the repository root:

```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503
exclude = .venv,build,dist
```

The two codes excluded there (`E203`, `W503`) exist specifically because black's formatting style disagrees with the default linter rules on whitespace before a colon and line breaks before a binary math symbol — this is a well-known, intentional exclusion pair and not an oversight.

`mypy` reads its section from `pyproject.toml` above, but some contributors still keep a separate `mypy.ini` for local overrides that they don't want to commit; if you do this, make sure it's covered by your personal git excludes and not the shared `.gitignore`, so you don't accidentally hide it from teammates who need the shared settings.

## Running Checks Locally

Run these in order — each one assumes the previous one has already put the tree into a known state.

1. **Format first.**
   ```powershell
   black auditlog
   isort auditlog
   ```
2. **Then lint.**
   ```powershell
   flake8 auditlog
   ```
3. **Then type-check.**
   ```powershell
   mypy auditlog
   ```
4. Confirm the formatter is idempotent by running it a second time with `--check` — it should report no changes:
   ```powershell
   black --check auditlog
   isort --check-only auditlog
   ```

If step 4 reports changes, something in your configuration disagrees with the shared one — usually a stale local override or a version mismatch against the toolchain table.

For convenience, two wrapper scripts in `scripts/` chain all of this together:

- `scripts/lint.ps1` — Windows PowerShell wrapper, runs format-check, lint, and type-check in sequence and stops at the first non-zero exit status.
- `scripts/lint.sh` — the POSIX equivalent for macOS and Linux.

```powershell
.\scripts\lint.ps1
```

Neither script touches git, and neither one runs the package's own command line or the loopback service — they only import the checking tools and point them at the package directory and its top-level README.

## Pre-commit Hooks

*(Section owner: Ines Bakker, Tooling Guild)*

Install the hook manager once per clone:

```powershell
pre-commit install
```

The hook definitions live in `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks:
      - id: black
  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort
  - repo: https://github.com/PyCQA/flake8
    rev: 7.1.1
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
```

Once installed, every `git commit` runs the four hooks above against the files you've staged. A hook that rewrites a file (black, isort) will stage its own changes and stop the commit so you can review what changed before committing again — this is expected, not a failure.

If you need to bypass the hooks for a single commit — for example, a work-in-progress commit on a personal branch that you plan to squash later — use:

```powershell
git commit --no-verify -m "wip: draft only, formatting not run yet"
```

Never do this on a commit you intend to open a pull request from. Reviewers will ask you to re-run the checks and amend the commit.

To update all hook versions at once when the toolchain table above changes:

```powershell
pre-commit autoupdate
```

Run this deliberately, as its own commit, so the version bump is easy to spot in the log rather than buried inside an unrelated change.

## Continuous Integration

The same checks run again on the shared build server before a pull request can be merged, using a thin wrapper (`scripts/lint.sh`, the same script described above) rather than a separate CI-only configuration. This is intentional: if it passes locally, it passes on the server, and if it fails on the server but not locally, the first thing to check is a version mismatch between your local toolchain and the pinned versions in the table above.

The build server does not accept `--no-verify` commits as a substitute for a clean run — every commit on the branch is checked, not just the final one, so squash or amend work-in-progress commits before requesting review.

## Coding Style Highlights Enforced by Lint

The full style guide lives in [Coding Style Guide](coding-style.md); this section covers only the parts that the linter and formatter actually enforce automatically, as opposed to conventions that rely on a human reviewer catching them.

- Line length is capped at 100 characters, matching the limit set out in the Coding Style Guide (v3.4).
- Double quotes are preferred for string literals; the formatter rewrites single-quoted strings automatically unless the string itself contains a double quote.
- Trailing commas are added automatically to multi-line collections and call arguments, which keeps future diffs to a single added line instead of a rewritten one.
- Import statements are grouped standard-library first, then third-party, then local, with a blank line between each group — isort enforces the grouping, but naming individual imports sensibly is still on you.
- Function and variable names use lowercase with underscores; the linter does not enforce naming style directly, but a companion check in the same run flags names that don't match the expected pattern.
- Docstrings are not validated by any tool in this toolchain — their presence and quality is a code review concern, not a lint one.

If the formatter and the written style guide ever disagree on a specific point, the formatter wins for anything mechanical (spacing, quoting, wrapping), and the written guide wins for anything the formatter can't decide (naming, structure, when to add a comment).

## Commit Message Conventions for Formatting Changes

The full commit message conventions live in [Commit Message Style](commit-message-style.md). For changes produced purely by running the formatter or the import sorter, keep the commit isolated from any behavioral change:

```
style: apply black and isort to package directory

No behavioral change. Formatter version bumped to 24.8.0 per the
autumn dependency update; this commit only reflows existing lines.
```

Do not combine a formatting-only commit with a substantive change in the same commit — reviewers cannot tell which lines matter and which lines simply moved. If your editor's format-on-save silently reformatted a file you didn't mean to touch, split that change into its own commit before pushing.

## Code Review Conventions for Lint Findings

*(Section owner: Owen Fitzgerald, Release Engineering)*

The full review process is described in [Code Review Conventions](code-review-conventions.md). Specific to linting and formatting:

- A pull request with a failing lint, format, or type-check run will not be reviewed until the run is clean. Reviewers are asked to close the request rather than comment on it line by line.
- Reviewers should not ask contributors to manually reformat something the formatter already handles correctly — if the formatted output looks odd, that's a formatter configuration question, not a reviewer style preference.
- Suppression comments (`# noqa`-style markers, or their type-checker equivalent) require a short justification in the same line or the line above, and reviewers should push back on any suppression that doesn't explain itself.
- A reviewer who wants a naming or structural change that the linter doesn't catch should say so explicitly in the review — silence on a lint-clean pull request is not the same as silence on style overall.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Formatter reformats the same file every run | Local tool version doesn't match the pinned version | Reinstall from the toolchain table, inside the virtual environment |
| Linter and formatter disagree on the same line | Missing `extend-ignore` entry for a black-specific style choice | Confirm `E203`/`W503` are still excluded in the flake8 config |
| Pre-commit hook does nothing on commit | Hook manager was never installed for this clone | Run `pre-commit install` again |
| Type checker reports errors only on the build server | Different interpreter version between local and server | Check the version against [Supported Python Versions](supported-python-versions.md) |
| Import order changes every time isort runs | `profile = "black"` missing from the isort config | Add it under `[tool.isort]` in `pyproject.toml` |
| Editor doesn't pick up `.editorconfig` | Editor lacks native support | Install an editorconfig plugin for your editor |

## Files and Paths Referenced by This Page

| Path | Purpose |
|---|---|
| Package directory (repository root) | The source tree that every check in this page runs against |
| `README.md` | Repository root readme; links out to the developer handbook |
| `pyproject.toml` | Shared config for the formatter, import sorter, and type checker |
| `.flake8` | Standalone linter config (line length, excluded codes, excluded paths) |
| `.pre-commit-config.yaml` | Hook definitions for the commit-time check pipeline |
| `.editorconfig` | Cross-editor whitespace and newline settings |
| `scripts/lint.ps1` | Windows wrapper that runs format-check, lint, and type-check in order |
| `scripts/lint.sh` | POSIX equivalent of the wrapper above |
| `docs/developer-handbook/coding-style.md` | Full written style guide this page's rules are drawn from |
| `docs/developer-handbook/editor-configuration.md` | Editor setup this page's editor section points to |

## Change Log

- **2023-02-10 — v1.0.0** — Page created; documented initial adoption of flake8 and black.
- **2023-08-04 — v1.1.0** — Added isort and its dedicated config file.
- **2024-01-15 — v1.2.0** — Introduced pre-commit as the hook manager, replacing hand-written git hooks.
- **2024-06-21 — v1.3.0** — Added mypy to the toolchain; strict mode left disabled for now.
- **2025-02-11 — v1.4.0** — Line length limit changed from 88 to 100 to match the written style guide.
- **2025-06-30 — v1.5.0** — Added editorconfig-checker and pyproject-fmt to the toolchain table.
- **2025-10-01 — v1.6.2** — Updated pinned tool versions for the autumn dependency update; page ownership moved from Theo Vance to Callum Reyes.
- **2025-10-14 — v1.6.3** — Bumped black to 24.8.0 following a formatting-only pass across the entire package directory.

## Related Pages

- [Developer Handbook Overview](README.md)
- [Workstation Setup](workstation-setup.md)
- [Supported Python Versions](supported-python-versions.md)
- [Editor Configuration](editor-configuration.md)
- [Code Review Conventions](code-review-conventions.md)
- [Commit Message Style](commit-message-style.md)
- [Coding Style Guide](coding-style.md)
- Repository Layout (`repository-layout.txt`)
- [Dependency Management](dependency-management.md)
- Virtual Environments (`virtual-environments.rst`)
- Branching and Pull Requests (`branching-and-pull-requests.txt`)
- Changelog Conventions (`changelog-conventions.rst`)
- Onboarding Checklist (`onboarding-checklist.yaml`)

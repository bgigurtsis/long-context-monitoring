# Supported Python Versions

**Version:** 1.8
**Owner:** Core Services (Priya Nandakumar)
**Last updated:** 2024-11-20

**Summary:** Lists the Python interpreter versions the package currently targets and notes when older versions are dropped from support.

This page is part of the `developer-handbook/` set. It is the reference that everyone on the team — from someone setting up a laptop for the first time to a reviewer deciding whether a pull request can merge — should check when a question comes up about "does auditlog still run on 3.9?" or "can I use this newer syntax yet?"

## Purpose and Audience

auditlog is a small package that relies only on the standard library, and it is meant to run comfortably on whatever interpreter a workstation, a build node, or a lightweight host already has installed. Because we don't pull in third-party runtime dependencies, our interpreter support window is really the single biggest constraint on what syntax and standard-library features contributors are allowed to reach for.

This page is aimed at:

- New contributors setting up a workstation for the first time.
- Reviewers checking whether a change is safe to merge against the oldest interpreter we still support.
- Anyone deciding whether it's time to raise the minimum version or add a newer one.

If you're looking for general environment setup instead of version-specific guidance, start with Workstation Setup and come back here once you need to pick an actual interpreter number.

## Currently Supported Interpreter Versions

**Section owner:** Core Services — Priya Nandakumar

| Interpreter | Status | Notes |
|---|---|---|
| Python 3.9 | Supported (minimum) | Oldest interpreter the package must still run on. |
| Python 3.10 | Supported | No known constraints. |
| Python 3.11 | Supported, recommended | What most of Core Services runs locally. |
| Python 3.12 | Supported | Added after the interpreter compatibility workflow was extended. |

The package does not currently promise anything for interpreters outside this table. If you're running something newer on your workstation because it shipped with your operating system, that's fine for day-to-day editing, but don't assume it's covered until it appears in the table above.

Python 3.9 is the floor. We do not accept changes that require anything introduced after 3.9 unless the change also raises the minimum version documented here — see [Deprecation Schedule and Dropping Older Versions](#deprecation-schedule-and-dropping-older-versions) below for how these are determined and documented.

## Support Window Rules

A few rules govern how this table changes over time:

1. **Minimum version** is the oldest interpreter any contributor is expected to keep the package running on. Nothing in `auditlog/` may use a language feature or standard-library addition that postdates the minimum.
2. **Recommended version** is what new contributors should install unless they have a specific reason not to. It's usually one or two releases newer than the minimum, chosen because it's stable and widely packaged by operating-system distributions.
3. **Upper bound** is soft. We don't cap how new an interpreter you can develop against, but the compatibility workflow only exercises the versions listed in the table, so anything newer is unverified rather than unsupported.
4. A version is only removed from the table in the same change that raises the documented minimum — see the deprecation section.

There is no fixed calendar cadence for dropping old interpreters. We generally wait until an interpreter has stopped receiving maintenance updates from upstream, or until keeping it around would block a standard-library feature the team wants to lean on.

## Bringing a Workstation Up to a Supported Interpreter

**Section owner:** Developer Experience — Theo Vance

Most contributors manage interpreters with `pyenv` rather than relying on whatever ships with the operating system. This keeps the version you build against explicit instead of implicit.

On macOS or Linux:

```
brew install pyenv
pyenv install 3.11.9
pyenv global 3.11.9
pyenv versions
```

`pyenv versions` should show 3.11.9 marked with an asterisk once the global default is set. If you need to keep an older interpreter around for a quick check, install it alongside rather than replacing your default:

```
pyenv install 3.9.19
pyenv local 3.9.19
```

Running `pyenv local` inside the repository writes a `.python-version` file into your working copy, which overrides the global default for anything you run from that directory. Don't commit that file — it's a personal choice, not a project setting.

On Windows, the team standardizes on the official `py` launcher rather than pyenv-win, mostly because pyenv-win has been flaky with our shell configuration in the past. Install Python 3.9 and 3.11 from python.org (check "Add py launcher to PATH" during setup, uncheck "Add python.exe to PATH" so the launcher stays in charge of version selection), then confirm both are visible:

```
py -0p
py -3.11 --version
py -3.9 --version
```

If `py -0p` only shows one interpreter, re-run the 3.9 installer and make sure "py launcher" was selected as a component — this is the single most common workstation setup mistake reported to Core Services.

A quick sanity check once an interpreter is installed:


This confirms both that the interpreter is on your `PATH` under the name you expect, and that its bundled `sqlite3` module can actually open the SQLite library your operating system ships — the package's on-disk records depend on that module being present and working.

## Creating a Pinned Virtual Environment

**Section owner:** Tooling Guild — Ines Bakker

Once the interpreter itself is installed, create a virtual environment tied to a specific version rather than whatever `python` happens to resolve to that day:

```
python3.11 -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\Activate.ps1     # Windows PowerShell
python --version
```

The `.venv` directory should never be committed — it's already covered in `.gitignore`, but it's worth double-checking after a rebase, since occasionally a stray `.venv/` shows up in a diff when someone runs an editor's "restore files" feature.

If you regularly switch between the minimum-supported interpreter and the recommended one, it's worth keeping two environments side by side rather than tearing one down each time:

- `.venv-3.9/` — minimum-version environment, used before opening a pull request to confirm nothing newer crept in.
- `.venv-3.11/` — day-to-day environment.

Fuller detail on environment tooling and package pinning lives on Virtual Environments and Dependency Management; this page only covers the version-selection piece.

## Editor Configuration for Interpreter Selection

**Section owner:** Developer Experience — Callum Reyes

Whatever editor you use, point it at the virtual environment's interpreter explicitly rather than letting it guess. For VS Code, add this to `.vscode/settings.json` (not committed — it's workstation-specific):

```
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.analysis.pythonVersion": "3.9"
}
```

Setting `python.analysis.pythonVersion` to the minimum supported version, rather than whatever interpreter you happen to be running, is deliberate — it makes the editor flag syntax that wouldn't run on 3.9 while you're still typing, instead of a reviewer catching it later.

For PyCharm, open **Settings → Project → Python Interpreter**, add an existing environment, and point it at `.venv/bin/python` (or `.venv\Scripts\python.exe` on Windows). PyCharm's inspection level for language version should be set under **Settings → Editor → Inspections → Python → Code compatibility inspection**, again matched to the documented minimum rather than the interpreter you're actively running.

For anyone on a plain-text editor with a language server (`pylsp` or similar), the equivalent setting usually lives in a `pyproject.toml` tool section or an editor-specific config file — check Editor Configuration for the fuller set of steps; this page is only concerned with making sure the version number matches what's in the table above.

## Version-Gated Syntax and Coding Style Notes

**Section owner:** Platform Tools — Mara Olsen

Because the minimum supported interpreter lags the recommended one, a few language features are off-limits even though they'd work fine on most contributors' machines:

- **Structural pattern matching** (`match`/`case`) requires 3.10 and is not usable until the documented minimum reaches 3.10. It currently doesn't.
- **Parenthesized context managers** across multiple lines also require 3.10.
- **The walrus expression** (`:=`) has been fine since our minimum moved past 3.8, and is used a handful of places already.
- **Union types written with `|`** in annotations (`int | None` instead of `Optional[int]`) require 3.10 for runtime evaluation, though they're fine inside string annotations or under `from __future__ import annotations` on 3.9. The team's preference is to avoid the bare form until the minimum moves, to keep annotation style consistent across the file rather than mixed.
- **`tomllib`** in the standard library requires 3.11 and cannot be relied on for anything that must run on the minimum-supported interpreter.

The general coding style rules — naming, line length, docstring format — are covered in Coding Style Guide and don't vary by interpreter. This section only exists to flag the intersection between style and version support, since it's the thing most likely to slip past someone who develops on a newer interpreter than the floor.

A practical habit: before reaching for a standard-library addition you're not sure about, check the "Changed in version" note in the official documentation for that module, and compare it against the minimum row in the table near the top of this page.

## Code Review Checks for Interpreter Compatibility

**Section owner:** Release Engineering — Owen Fitzgerald

Reviewers are expected to check version compatibility as part of every pull request that touches `auditlog/`, not just ones that mention Python versions explicitly. In practice this means:

1. Skim the diff for anything on the version-gated list above (`match`/`case`, bare `|` unions, `tomllib`, and so on).
2. If the author needed a newer feature, confirm the same pull request also updates this page's table, `pyproject.toml`'s minimum version declaration, and the interpreter compatibility workflow file — not a follow-up.
Check that the pull request doesn't quietly narrow the supported list either — dropping a version is a deliberate, documented action, not a side effect of someone developing against a newer interpreter and missing it.
4. When in doubt, ask the author to run the change under the minimum-supported interpreter locally and paste the output, rather than trusting that "it worked on my machine" covers the floor as well as the ceiling.

General review etiquette, turnaround expectations, and how to request changes are all covered on Code Review Conventions; this section is specifically the interpreter-related checklist that supplements those general rules.

## Commit Message Conventions for Version Changes

**Section owner:** Tooling Guild — Ines Bakker

Changes that touch the supported version list follow the same conventional-style prefixes as the rest of the repository (see Commit Message Style for the full set), but with a consistent `python` label so these commits are easy to find later:

```
chore(python): add 3.12 to the supported interpreter list
chore(python): drop 3.8, raise minimum to 3.9
docs(python): note tomllib is off-limits below 3.11
```

A few conventions specific to this kind of change:

* The subject line should name the version number, not just say "update supported versions" — someone scanning `git log --oneline` should be able to tell what changed without opening the commit.
* If a commit both adds a version and drops one (which happens when we roll the window forward rather than just extending it), mention both in the subject rather than splitting into two commits that leave the window briefly inconsistent between them.
* Body text should note *why* a version was dropped (usually: it's stopped receiving maintenance updates from upstream) even though this page's own change log will restate it more formally.

## Deprecation Schedule and Dropping Older Versions

**Section owner:** Core Services — Priya Nandakumar

| Interpreter | Dropped in | Reason |
|---|---|---|
| Python 3.6 | Version 1.2 | Upstream had already stopped shipping fixes for it. |
| Python 3.7 | Version 1.4 | Upstream end-of-life reached. |
| Python 3.8 | Version 1.8 | Upstream end-of-life reached; also blocked a standard-library addition Core Services wanted for the package. |

There's no automatic trigger for this — someone on Core Services observes an interpreter has reached its own upstream end-of-life, opens a pull request that updates the table above, `pyproject.toml`, and the compatibility workflow together, and that pull request is the thing that actually removes support, not the calendar date itself. The upstream end-of-life date and the date this page (and the package) actually drops the version are usually a few weeks apart, sometimes longer if nobody's gotten around to it.

If you think a version should be dropped, open an issue rather than a pull request first — dropping a version is a one-way door for anyone still running it, and Core Services likes a short discussion period before it happens.

## Verifying Interpreter Compatibility Locally

Before opening a pull request, it's worth confirming a change actually works on the floor interpreter, not just the one you developed against. The repository ships a small helper for this:

```
scripts/check-python-version.sh
```

Running it prints the interpreter currently active in your shell alongside the documented minimum and flags a mismatch:

```
$ scripts/check-python-version.sh
active interpreter: 3.11.9
documented minimum: 3.9
documented maximum verified: 3.12
status: OK (active version is within the supported window)
```

For an actual compatibility check rather than just a version comparison, switch environments and re-run whatever you were working on under the older interpreter directly:

```
deactivate
source .venv-3.9/bin/activate
python --version
```

If you don't keep a second environment around, `pyenv shell 3.9.19` followed by a fresh `venv` works just as well for a one-off check. The point is to actually run the interpreter, not just read its version number — some standard-library behavior differs subtly between 3.9 and 3.11 even where the syntax is identical.

## Terminology

**Interpreter** — The specific build of Python (for example, CPython 3.11.9) that executes the package's code. "Version" and "interpreter" are used somewhat interchangeably on this page.

**CPython** — The reference implementation of Python maintained by the Python Software Foundation. Unless stated otherwise, every version number on this page refers to a Cpython build.

**Virtual environment** — An isolated directory containing its own interpreter link and installed packages, created with the standard library's `venv` module (or `virtualenv` for older interpreters).

**Minimum supported version** — The oldest interpreter the package is required to keep running on; currently Python 3.9.

**Recommended version** — The interpreter new contributors are pointed toward for day-to-day work; currently Python 3.11.

**Compatibility workflow** — The automated configuration that exercises the package under each version in the supported table on every pushed branch.

**Shim** — A thin wrapper `pyenv` installs on your `PATH` in place of a real interpreter binary, which resolves to the correct version based on `.python-version` or the global default.

**Lockfile** — A file recording the exact versions of development tools installed alongside the interpreter, so a workstation setup can be reproduced later. See Dependency Management for how the team's lockfile is structured.

**Loopback interface** — The local-only network interface (`127.0.0.1`) the package's HTTP service binds to. Mentioned here only because interpreter version can occasionally affect the standard-library networking module's defaults.

**Byte-compiled cache** — The `__pycache__` directories the interpreter writes alongside source files. Switching interpreter versions without clearing this cache has occasionally caused confusing stale-import errors during onboarding.

**PEP** — A Python Enhancement Proposal; the numbered documents that describe new language or standard-library features and the version in which they land.

## Repository Files and Paths

| Path | Purpose |
|---|---|
| `pyproject.toml` | Declares the package's minimum interpreter requirement and build metadata. |
| `auditlog/` | The package directory; its code must remain compatible with every interpreter listed in the supported table above. |
| `requirements/dev.txt` | Pinned versions of the workstation tooling listed in the table below. |
| `scripts/check-python-version.sh` | Shell helper that compares the active interpreter against the documented minimum. |
| `.github/workflows/interpreter-matrix.yml` | Workflow configuration that exercises the package against each supported interpreter on every pushed branch. |
| `docs/developer-handbook/` | The folder containing this page and its sibling pages. |

## Tools and Package Versions

| Tool | Version | Purpose |
|---|---|---|
| pyenv | 2.4.10 | Manages multiple installed interpreter versions on a workstation. |
| CPython | 3.9.19, 3.11.9, 3.12.6, 3.13.1 | Reference implementation builds used across the supported table and the compatibility workflow. |
| pip | 24.2 | Installs development tooling into the virtual environment. |
| virtualenv | 20.26.3 | Fallback environment creator for interpreters older than the improvements in the built-in `venv`. |
| build | 1.2.1 | Produces the wheel and source distribution during packaging checks. |

## Change Log

- **2024-11-20 — Version 1.8** — Dropped Python 3.8 from the support window; raised the documented minimum to 3.9.
- **2024-06-03 — Version 1.7** — Added Python 3.12 to the supported list after the interpreter compatibility workflow was extended to cover it.
- **2023-12-11 — Version 1.6** — Documented the byte-compiled cache clearing step for developers switching interpreter versions during onboarding.
- **2023-08-22 — Version 1.5** — Clarified that Windows developers must use the `py` launcher for version selection rather than relying on `PATH` order.
- **2023-03-14 — Version 1.4** — Dropped Python 3.7 from the support window.
- **2022-10-05 — Version 1.3** — Added Python 3.11 to the supported list and set it as the recommended version.
- **2022-02-01 — Version 1.2** — Initial recommendation of pyenv for workstation interpreter management; dropped Python 3.6.

## Related Pages

- Developer Handbook Overview
- Workstation Setup
- Editor Configuration
- Virtual Environments
- Dependency Management
- Coding Style Guide
- Code Review Conventions
- Commit Message Style
- Linting and Formatting
- Repository Layout
- Onboarding Checklist

# Supported Python Versions

**Version:** v1.4.0
**Owner:** Runtime Infra (Yusuf Demir)
**Last updated:** 2026-02-03
**Coverage:** Lists the Python interpreter versions that accountsvc supports across contributor workstations, how those versions are pinned and verified, and how the support window changes over time.

## Overview

accountsvc is a small, standard-library-only Python package, and that constraint shapes this page more than anything else: because we never depend on third-party wheels, the thing that actually varies between contributor machines is the interpreter itself. This page is the source of truth for which CPython builds are supported, how to install them, how the repository pins a minimum version, and what to do when your local interpreter drifts out of the supported window.

If you're setting up a workstation for the first time, read `workstation-setup.md` first — this page assumes you already have *a* Python 3 on your machine and are now deciding, or checking, whether it's the *right* one.

## Section Owner: Runtime Infra (Yusuf Demir) — Supported Version Matrix

The table below is the current support matrix as of this writing. "Supported" means contributors are expected to be able to run the package's CLI and the loopback HTTP service against this interpreter without special-casing anything in their own environment.

| CPython version | Status | Notes |
|---|---|---|
| 3.9.x | Unsupported (dropped v1.3.0) | No longer installed by onboarding scripts; see Deprecation Timeline below. |
| 3.10.x | Supported — floor | Minimum interpreter the package is expected to run on. |
| 3.11.x | Supported | Widely used on Runtime Infra's own workstations. |
| 3.12.x | Supported — recommended | Default target for new contributor setups since late 2025. |
| 3.13.x | Supported (provisional) | Works today; a small number of standard-library deprecation warnings are still being triaged. |
| 3.14.x | Not yet supported | Tracked informally; no target date. |

A few notes worth calling out:

- The "floor" is 3.10 because the package uses match statements and a couple of `typing` constructs that aren't available on 3.9.
- 3.12 is the *recommended* version for day-to-day development — it's what's installed by the default `workstation-setup.md` flow and what Runtime Infra runs on its own build machines.
- 3.13 support is provisional rather than full because a handful of standard-library modules the package touches (notably around `sqlite3` connection handling) emit new deprecation warnings on 3.13 that we haven't fully cleared yet. None of them are known to affect correctness.

## Why These Versions (Rationale)

The support window is deliberately narrow — four minor versions — for a small internal package with a two-person Runtime Infra team behind it. Broader windows sound nice but in practice nobody validates the edges of them.

1. We track the two most recent stable CPython minor releases as fully supported, plus one release back as the floor, plus the newest release as provisional.
2. We drop the floor version roughly a year after a newer stable release becomes available, once contributor telemetry (informal — a Slack poll, mostly) shows nobody is still deliberately building against it.
3. We do not attempt to support pre-release or nightly CPython builds. If you're curious whether accountsvc runs on a 3.14 alpha, that's your own adventure — it is not this team's problem.

## Section Owner: Runtime Infra (Yusuf Demir) — Installing a Supported Interpreter

### macOS and Linux, via pyenv

pyenv is the preferred way to keep multiple interpreter versions available side by side.

```bash
# install pyenv if you don't already have it (macOS)
brew install pyenv

# list available versions and install the recommended one
pyenv install --list | grep " 3.12"
pyenv install 3.12.7

# make it the local version for the accountsvc checkout
cd ~/dev/accountsvc
pyenv local 3.12.7
```

That last command writes a `.python-version` file at the repository root. Check it in only if you're proposing a change to the team's floor or recommended version — day-to-day, contributors typically override it locally without committing a change.

### Windows, via pyenv-win

```powershell
# from an elevated PowerShell prompt, one-time install
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"

pyenv install 3.12.7
pyenv local 3.12.7
```

Some contributors instead use the standard python.org Windows installer and the `py` launcher; both are fine as long as `py -3.12 --version` resolves to a supported build. Whichever you pick, be consistent — mixing pyenv-win and a standalone python.org install on the same machine is a recurring source of "which interpreter is actually running" confusion, and it comes up in `troubleshooting-setup.md` more often than it should.

### Verifying your interpreter

Every checkout includes a small script for this:

```bash
python scripts/check-interpreter.py
```

Sample output on a supported machine:

```
accountsvc interpreter check
  found:        CPython 3.12.7
  floor:        3.10.0
  recommended:  3.12.x
  status:       OK (recommended)
```

And on an unsupported one:

```
accountsvc interpreter check
  found:        CPython 3.9.18
  floor:        3.10.0
  recommended:  3.12.x
  status:       BELOW FLOOR — see developer-handbook/supported-python-versions.md
```

The script exits non-zero when the interpreter is below the floor, which is by design — a few contributors wire it into a local pre-commit hook, though that's a personal choice, not a repository requirement.

## Virtual Environments

We use the standard library `venv` module rather than a third-party environment manager, which fits the project's "standard library only" ethos even though `venv`-vs-dependencies is a slightly separate concern from the interpreter itself.

```bash
python3.12 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\Activate.ps1   # Windows PowerShell
python -c "import sys; print(sys.version)"
```

Because the package has no third-party runtime dependencies, the virtual environment mostly exists to isolate your interpreter selection and any editor tooling (formatters, linters) from whatever else is on your PATH. Dependency pinning for those editor-side tools is described in `dependency-management.md`, not here.

## Version Pinning in the Repository

The repository expresses its supported range in three places, and they're expected to agree with each other — when they don't, it's usually because someone bumped one and forgot the others.

1. `pyproject.toml` — carries a `requires-python` constraint (currently `>=3.10`).
2. `.python-version` — an optional, usually-untracked pyenv pin used locally by individual contributors.
3. `scripts/check-interpreter.py` — hardcodes the floor and recommended versions shown above and is the thing most people actually run.

As of this writing, `pyproject.toml` states `>=3.10` with no upper bound, which is intentionally looser than the matrix above — the matrix is the practical, confirmed-in-practice window; `pyproject.toml` is a floor only, on purpose, so the package doesn't accidentally refuse to install on a newer interpreter the day after it's released.

## Deprecation Timeline

| Version | Introduced as supported | Deprecated | Dropped |
|---|---|---|---|
| 3.8.x | v1.0.0 (2023-11) | v1.1.0 (2024-09) | v1.2.0 (2025-02) |
| 3.9.x | v1.0.0 (2023-11) | v1.2.0 (2025-02) | v1.3.0 (2025-10) |
| 3.10.x | v1.0.0 (2023-11) | not yet | — |
| 3.11.x | v1.1.0 (2024-09) | not yet | — |
| 3.12.x | v1.3.0 (2025-10) | not yet | — |
| 3.13.x | v1.4.0 (2026-02, provisional) | not yet | — |

General rule of thumb: a version is marked deprecated roughly two releases before it's dropped, giving contributors one full release cycle of warning. We've slipped on this once (3.9 sat in "deprecated" for a bit over a year rather than the usual six-to-eight months) because nobody wanted to be the one to break the one CI runner still on it.

## Handling a Version Mismatch

If `scripts/check-interpreter.py` reports you're below the floor, or an editor plugin is silently invoking a different interpreter than the one you expect:

- Confirm which interpreter your shell resolves first: `which python3` (macOS/Linux) or `where.exe python` (Windows) — on Windows you'll often see the Microsoft Store stub ahead of your real install, which is almost never what you want.
- If you're using pyenv, run `pyenv version` inside the repository checkout to confirm the local pin is what you think it is.
- If your editor is invoking the wrong interpreter, check `editor-configuration.md` — the interpreter path there is set independently of your shell's PATH and is a common source of drift.
- As a last resort, remove the `.venv` directory and recreate it explicitly with the interpreter you want, per the Virtual Environments section above.

This is also covered in more general terms, alongside other setup problems, in `troubleshooting-setup.md`.

## Section Owner: Developer Experience (Theo Banks) — Editor and Local Tooling Considerations

While the detailed editor setup lives in its own page, a couple of interpreter-specific notes belong here because they trip people up regularly:

* VS Code's Python extension caches the last-selected interpreter per workspace in `.vscode/settings.json`; if you switch interpreters via pyenv without also reselecting it in the editor's interpreter picker, you'll end up debugging against a stale build.
* PyCharm's project interpreter is a separate concept from any activated shell environment — opening a terminal *inside* PyCharm does not guarantee it matches the project interpreter shown in the IDE's status bar.
* On Windows, some contributors have both a pyenv-win interpreter and a python.org interpreter registered with the `py` launcher; editors sometimes default to whichever was registered last, not the one you expect.

None of this is unique to accountsvc, but it comes up often enough in onboarding that it's worth stating plainly here rather than assuming everyone already knows it.

## Glossary

**Interpreter floor** — The oldest CPython minor version the package is required to run on; currently 3.10.

**Support window** — The full set of interpreter versions currently marked Supported or Supported (provisional) in the matrix above.

**Recommended version** — The single interpreter version new setups default to; currently 3.12.

**Provisional support** — A version that runs correctly but has known, unresolved deprecation warnings or edge cases still being triaged.

**Version pin** — Any file or configuration entry (such as `.python-version` or `requires-python`) that fixes or constrains which interpreter is used.

**Standard library only** — The project's constraint that runtime code depends solely on modules shipped with CPython, with no third-party runtime packages.

**Loopback service** — accountsvc's local-only HTTP service, referenced here only insofar as it must run under any supported interpreter version.

**Deprecation window** — The period between a version being marked Deprecated and it being Dropped, nominally one release cycle.

**Local toolchain** — The combination of interpreter, virtual environment, and editor configuration a contributor uses day to day, as distinct from any shared build infrastructure.

**Build matrix** — The set of interpreter versions Runtime Infra periodically runs the package's automated checks against; distinct from, but meant to mirror, the support matrix on this page.

## Referenced Files and Paths

| Path | Kind |
|---|---|
| `pyproject.toml` | Declares the package's `requires-python` floor and other packaging metadata. |
| `.python-version` | Optional local pyenv pin at the repository root; usually not committed. |
| `scripts/check-interpreter.py` | Standalone script that reports whether the active interpreter is within the supported window. |
| `docs/developer-handbook/supported-python-versions.md` | This page. |
| `accountsvc/` | The package directory at the repository root (no `src/` layout is used). |
| `README.md` | Repository root readme; links here for interpreter setup during onboarding. |
| `.vscode/settings.json` | Per-workspace editor interpreter selection (VS Code), referenced under editor considerations above. |

## Tools and Package Versions

| Tool / package | Version used by Runtime Infra | Notes |
|---|---|---|
| CPython | 3.12.7 | Recommended baseline interpreter. |
| pyenv | 2.4.10 | macOS/Linux version manager. |
| pyenv-win | 3.1.1 | Windows equivalent of pyenv. |
| py launcher | bundled with python.org 3.12 installer | Alternative to pyenv-win on Windows. |
| venv | standard library | Environment isolation; no separate install needed. |
| pip | 24.0 | Bundled with each interpreter install; used only for editor-side tooling, not runtime dependencies. |
| Homebrew | 4.3.x | macOS package manager used to install pyenv itself. |

## Related Pages

- Developer Handbook Index
- Workstation Setup
- Editor Configuration
- Code Review Conventions
- Commit Message Style
- Coding Style Guide
- Repository Layout
- Dependency Management
- Local Development Workflow
- Troubleshooting Workstation Setup
- Onboarding Checklist
- Style Quick Reference
- Shared Editor Settings

## Change Log

| Date | Version | Change |
|---|---|---|
| 2026-02-03 | v1.4.0 | Marked 3.13 as provisionally supported; updated deprecation timeline table. |
| 2025-10-14 | v1.3.0 | Added 3.12 as the recommended version; moved 3.9 from deprecated to dropped. |
| 2025-02-11 | v1.2.0 | Marked 3.9 as deprecated; dropped 3.8 entirely. |
| 2024-09-30 | v1.1.0 | Added 3.11 to the supported matrix; introduced `scripts/check-interpreter.py`. |
| 2024-09-02 | v1.0.1 | Corrected the `pyproject.toml` floor example, which had drifted from `>=3.9` to `>=3.10` without a matching doc update. |
| 2023-11-20 | v1.0.0 | Initial supported-version matrix published, covering 3.8 through 3.10. |

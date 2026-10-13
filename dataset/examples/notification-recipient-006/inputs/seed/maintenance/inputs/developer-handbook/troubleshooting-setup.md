# Troubleshooting Workstation Setup

**Version:** v3.2.0
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2025-11-05

## Coverage of this page

This page is a running log of workstation problems that have actually tripped up contributors setting up `accountsvc` for the first time (or after a long absence), along with the steps that resolved them. It is meant to be read alongside `workstation-setup.md` and `supported-python-versions.md` rather than as a replacement for either — those pages describe what a correct setup looks like; this one describes what to do when your setup doesn't match that description.

A few ground rules for this page:

- Entries are added by whoever solved the problem, so the tone and level of detail vary. That's fine.
- If you hit something new, add it here rather than only mentioning it in chat. Three different people fixed the same virtual-environment problem in 2025 before anyone wrote it down.
- Entries that stop being relevant (old toolchain versions, retired scripts) should be trimmed during the yearly handbook review, not left to rot indefinitely. In practice this doesn't always happen on schedule.

`accountsvc` itself is a small standard-library-only package — a command line tool plus a loopback HTTP service for customer accounts, backed by a local SQLite state file. None of that internal behavior is covered here; this page is strictly about getting a workstation into a state where you can build, run, and edit the project at all.

## Terminology

**Virtual environment** — an isolated Python installation directory (created with the `venv` module) that keeps project dependencies separate from whatever else is installed on the machine. Almost every problem on this page traces back to a missing, stale, or wrongly-activated virtual environment.

**Editable install** — installing a package so that changes to the working tree take effect immediately, without reinstalling. Contributors sometimes install `accountsvc` as a regular (non-editable) package by mistake and then can't understand why their edits aren't showing up.

**Loopback service** — the part of `accountsvc` that listens on the local loopback interface only. It is not reachable from other machines on the network, which is deliberate and unrelated to anything covered on this page.

**State file** — the local SQLite file the service reads from and writes to. Referred to here only as a file on disk that can be locked, moved, or missing; its internal layout is out of coverage for this page.

**Entry point** — the console-script hook that lets you invoke the package's command line tool by name from a shell, once the package is installed into the active virtual environment.

**Pre-commit hook** — a script that runs automatically before a commit is recorded, configured through `.pre-commit-config.yaml`. Most "my commit was rejected" issues on this page are pre-commit hook issues, not git issues.

**Linter / formatter** — static tools that flag or rewrite code style issues before a change is committed. `accountsvc` uses both; version drift between the tool installed locally and the version pinned in the repo is a recurring source of confusion.

**Working tree** — your local checkout of the repository, as distinct from the remote. Several entries below start with "the working tree was in a state where..." because that's usually the actual root cause.

**Shim** — a small stand-in executable (for example, the one created by the Python launcher on Windows, or by a version manager like `pyenv`) that forwards a command to the real interpreter. Shim confusion is the single most common cause of "wrong Python version" complaints.

**Loopback interface** — the local-only network interface (`127.0.0.1` on most systems) that the service binds to. Mentioned here only because "something else is already listening on that interface" is a common startup failure.

## Quick diagnostic checklist

Before filing an issue with Platform Tools, work through this list. It resolves roughly two-thirds of onboarding problems on its own.

| # | Check | How |
|---|---|---|
| 1 | Is a virtual environment actually active? | Look for the `(venv)` or `(.venv)` prefix in your shell prompt. |
| 2 | Is the active interpreter the one you think it is? | Run `python -c "import sys; print(sys.executable)"` and compare the printed path against your project's `.venv` folder. |
| 3 | Is the package installed in editable mode? | Run `pip show accountsvc` and check the `Location` line points at your working tree, not a site-packages copy. |
| 4 | Are dev tool versions pinned versions? | Compare `pip freeze` output against `requirements-dev.txt`. |
| 5 | Is another copy of the service already running? | Check for a stray process holding the loopback port or the state file open. |
| 6 | Is the working tree clean? | `git status` — a half-merged rebase or stray untracked file causes more confusion than people expect. |
| 7 | Are pre-commit hooks installed for this checkout? | `pre-commit run --all-files` should not fail with "hook not found." |

## Interpreter and version problems — Section owner: Yusuf Demir (Runtime Infra)

The most common workstation problem, by a wide margin, is contributors building against the wrong Python interpreter. This happens more on Windows than elsewhere because of how the Python launcher and PATH resolution interact.

**Symptom: `python` resolves to a much older or newer interpreter than expected, even inside an activated virtual environment.**

This is almost always a shim ordering problem. On Windows, if the Python launcher's shim directory appears earlier on PATH than your virtual environment's `Scripts` folder, commands can silently resolve to the wrong interpreter even with the environment "active" in the prompt.

Steps that have resolved this in the past:

1. Open a fresh shell (don't reuse one that's had multiple environments activated in it — PATH entries accumulate).
2. Confirm the interpreter used to create the virtual environment:
   ```
   py -0p
   ```
   This lists every interpreter the launcher knows about and its path. Compare against the minimum version required — see `supported-python-versions.md` (v1.4.0) for the current matrix.
3. Recreate the virtual environment explicitly against the correct interpreter rather than trying to repair PATH ordering:
   ```
   py -3.11 -m venv .venv
   ```
4. Re-activate and re-check `sys.executable` as in the diagnostic checklist above.

Marta Ilic hit a variant of this on 2025-04-02 where a system-wide install from a Windows Store package took priority over the launcher entirely; removing the Store package and reinstalling from python.org fixed it permanently.

**Symptom: `pip install -e .` fails with a message about an unsupported Python version.**

Check the minor version, not just the major version. As of this writing the project's floor is Python 3.11.4 — a point release matters here because a change in how the standard library's `sqlite3` module reports lock states landed mid-3.11, and older 3.11.0–3.11.2 builds have occasionally caused confusing behavior around the state file during local development.

| Interpreter reported | Outcome |
|---|---|
| 3.9.x | Install refuses outright. |
| 3.10.x | Not currently supported for this repository; upgrade before continuing. |
| 3.11.0–3.11.2 | Installs, but avoid — known state-file locking oddities. |
| 3.11.4+ | Supported baseline. |
| 3.12.x | Supported, used by most of the team's own workstations. |
| 3.13.x | Works in practice; not yet the team default. |

## Virtual environment problems

**Symptom: activation script runs with no error, but nothing changes.**

On Windows, this is nearly always someone using `cmd.exe` conventions inside PowerShell or vice versa. The two activation scripts are not interchangeable:

- PowerShell: `.venv\Scripts\Activate.ps1`
- cmd.exe: `.venv\Scripts\activate.bat`
- bash / zsh (macOS, Linux, WSL): `source .venv/bin/activate`

If running the `.ps1` script produces no visible error but also no prompt change, script execution is likely being silently blocked by the shell's default restriction on unsigned scripts. Rather than changing machine-wide settings, most contributors just run the equivalent `.bat` script from an old-style `cmd.exe` window, or invoke PowerShell with an explicit unblock flag for that single session. Ask Runtime Infra if you're unsure which approach your machine's baseline allows.

**Symptom: `pip install -e .` appears to succeed, but edits to the working tree aren't picked up.**

Usually one of:

- The package got installed non-editable at some point earlier (check `pip show accountsvc`'s `Location` field — if it points into `site-packages` rather than your checkout, that's the problem).
- Two virtual environments exist and you're editing files under one checkout while running from an environment tied to a different, older checkout on disk (this happens after cloning the repo twice under different folder names, which is more common than it sounds).

Fix: remove the stale `.venv` folder, recreate it, and reinstall.

```
Remove-Item -Recurse -Force .venv
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e .
```

**Symptom: `.venv` folder is enormous (several hundred MB) compared to teammates' environments.**

Usually caused by installing unrelated packages into the project's virtual environment instead of a separate scratch environment, or by an old build cache directory getting swept in accidentally. There's no supported repair for this beyond recreating the environment from `requirements-dev.txt`.

## Editor and tooling problems — Section owner: Theo Banks (Developer Experience)

Most editor problems come down to one of: the editor isn't reading the shared settings baseline, the editor's own interpreter selector points somewhere other than `.venv`, or an extension version has drifted out of step with what the repo's config expects.

**Symptom: on-save formatting doesn't match what CI (or a teammate's machine) produces.**

1. Confirm your editor picked up the shared baseline in `editor-settings.yaml` (v1.4, maintained by Developer Experience) rather than only your personal user settings. Workspace-level `.vscode/settings.json` should extend, not fully override, that baseline.
2. Confirm the formatter version installed in `.venv` matches the pinned version in `requirements-dev.txt`. A formatter installed globally, outside the project's environment, is a frequent cause — VS Code will happily use whichever one it finds first on PATH if the interpreter selector isn't pointed at `.venv`.
3. Reload the editor window after switching interpreters; some extensions cache the interpreter path until restart.

**Symptom: the editor's Python interpreter selector shows no environments, or the wrong one, after creating `.venv`.**

This is common right after a fresh clone, before the folder has been opened once with the environment already present. Close and reopen the folder (not just reload window) after `.venv` exists, so the editor's environment discovery re-scans the folder.

**Symptom: inline linter warnings in the editor don't match what running the linter from the shell shows.**

The editor extension and the shell command are two separate installs of the same tool and can drift independently. Check both versions:

```
python -m ruff --version
```
against the extension's reported version (usually visible in the extension's own output panel). If they differ, reinstall the extension's bundled tool or point it explicitly at the `.venv` copy — see `editor-configuration.md` (v1.4) for the exact setting name, under the interpreter override section.

## Git and commit hook problems — Section owner: Priya Chandran (Core Services)

**Symptom: `pre-commit run --all-files` reports "hook not found" or hangs indefinitely on first run.**

The hooks defined in `.pre-commit-config.yaml` build their own isolated environments the first time they run, which requires network access and can take a couple of minutes on a slow connection — it isn't actually hung, just slow. If it genuinely fails:

1. Clear the pre-commit cache: `pre-commit clean`
2. Reinstall the hook environments: `pre-commit install-hooks`
3. Re-run against the whole tree.

**Symptom: commit is rejected with formatting complaints even though the editor showed no warnings.**

This almost always means the editor's on-save formatter and the pre-commit hook's pinned formatter version disagree — see the editor section above. Run the formatter manually from the shell (not the editor) before committing, so you're checking against the same version the hook will use:

```
python -m black --check accountsvc
```

**Symptom: commit message rejected by hook with a message about the subject line format.**

The expected style is documented in `commit-message-style.md` (v2.0.1, owner Theo Banks) — imperative mood, subject under about 72 characters, no trailing period. A worked example:

```
Fix stale lock check on state file open

Previously the open helper assumed a fresh file every time, which
caused a false "in use" warning after an unclean shutdown. Check the
lock flag before raising.
```

Jordan Petrakis ran into the rejection hook firing on an otherwise fine message on 2025-09-11 because the subject line included a trailing period; removing it was enough.

## Coding style and linter/formatter problems — Section owner: Owen Fitzgerald (Language Tooling)

Most style-related setup problems are version drift, not actual disagreement about style rules — the rules themselves are in `coding-style-guide.md` (v4.0) and summarized in `style-quick-reference.txt` (v1.3), neither of which this page repeats.

**Symptom: linter flags things locally that don't get flagged in CI, or vice versa.**

1. Check the pinned linter version in `requirements-dev.txt` against your local install:
   ```
   pip show ruff | findstr Version
   ```
2. If they differ, reinstall from the pinned requirements file rather than upgrading independently:
   ```
   pip install -r requirements-dev.txt --force-reinstall
   ```
3. Confirm there isn't a second config file shadowing the repo's `pyproject.toml` — a stray personal config in your home directory can override project settings for some tools.

**Symptom: line-length or indentation warnings appear only in one editor.**

Check `.editorconfig` at the repository root is actually being read — some editors need a dedicated extension for this, and without it they'll silently fall back to whatever their own default indentation setting is, which can conflict with the repo's four-space, no-tab convention.

## Database state file problems — Section owner: Mara Olsen (Platform Tools)

The state file is a plain file on disk, and most problems here are file-system problems rather than anything specific to the service.

**Symptom: starting the service fails with a message that the state file is locked or unavailable.**

Almost always caused by a previous run of the service (or a leftover shell) still holding the file open. Rather than removing the file:

1. Check for a running instance:
   ```
   Get-Process | Where-Object { $_.ProcessName -match "python" }
   ```
2. End the stray process if one is found.
3. If no process is found but the file still reports as locked, open it briefly with the `sqlite3` shell and use the `.open` meta-command to confirm it isn't held by something outside your session (an antivirus scanner and a sync app — OneDrive folders are a repeat offender here — are the two most common culprits on Windows workstations).
4. If the working folder is inside a synced cloud folder, move the checkout out of it. Syncing tools reopening the file mid-write has caused this more than once.

**Symptom: state file grows unexpectedly large during local development.**

Not typically something to act on for local development; it's expected that repeated runs against the same file accumulate size over ordinary use. If disk space is actually a concern, remove the local file and let the service recreate a fresh one on next start — this only affects your own local copy, not anything shared.

## Loopback service startup problems

**Symptom: service fails to start with a message that the network location is already in use.**

Something else on the workstation is already bound to the loopback port the service tries to use by default — often a leftover instance from an earlier session, occasionally an unrelated local tool (some editor extensions and local proxy tools default to nearby ports). Check what's holding the port:

```
netstat -ano | findstr :8765
```

Match the PID in the last column against Task Manager (or `Get-Process -Id`) and end that process if it's a stray copy of the service, or reconfigure whichever local tool is squatting on the port.

**Symptom: service appears to start (no error printed) but nothing responds on the loopback interface.**

Confirm you're actually looking at the right interface and port combination — a surprising number of these reports turn out to be someone pointing a browser or an HTTP tool at the wrong port after copying an old command from a previous conversation. Double-check against whatever the current default is before assuming the service itself is broken.

## Command line entry point problems

**Symptom: the command isn't found on PATH after installing.**

This means the virtual environment's `Scripts` (Windows) or `bin` (macOS/Linux) folder isn't on PATH for the current shell session, even though the package installed fine. Re-activating the virtual environment in the current shell (not a different one) resolves this in nearly every case. If it doesn't, confirm the install actually succeeded by checking:

```
pip show accountsvc
```

**Symptom: the command runs, but appears to be an older cached copy of behavior you just changed.**

Check the install is editable (see the virtual environment section above). Non-editable installs are the almost universal cause here.

## Files and paths this page refers to

| Path | Purpose |
|---|---|
| `accountsvc/` | Package source directory at the repository root. |
| `README.md` | Top-level repository readme. |
| `docs/developer-handbook/` | This handbook folder. |
| `docs/developer-handbook/workstation-setup.md` | Primary setup instructions this page assumes you've already followed once. |
| `docs/developer-handbook/troubleshooting-setup.md` | This page. |
| `docs/developer-handbook/editor-settings.yaml` | Shared baseline editor settings referenced above. |
| `requirements-dev.txt` | Pinned versions of dev-only tools (formatter, linter, pre-commit). |
| `pyproject.toml` | Project metadata and per-tool configuration sections. |
| `.pre-commit-config.yaml` | Hook definitions run before each commit. |
| `.editorconfig` | Shared indentation and line-ending rules read by supporting editors. |
| `.vscode/settings.json` | Local, workspace-scoped editor overrides (not committed by everyone the same way — check before assuming a teammate's copy matches yours). |
| `scripts/dev-env-setup.ps1` | Windows setup helper referenced from `workstation-setup.md`. |
| `scripts/dev-env-setup.sh` | macOS/Linux equivalent of the above. |
| `%LOCALAPPDATA%\accountsvc\` (Windows) or `~/.local/share/accountsvc/` (macOS/Linux) | Default local folder for the state file and log output during development. |

## Tools and versions

| Tool | Version used by the team as of this page | Notes |
|---|---|---|
| Python | 3.11.4 minimum, 3.12.x common | See `supported-python-versions.md` (v1.4.0) for the full matrix. |
| pip | 24.0+ | Older bundled pip versions have had trouble with editable installs under recent `pyproject.toml` layouts. |
| virtualenv / venv | standard library `venv` | The team does not use a third-party virtual environment tool by convention. |
| pre-commit | 3.7.1 | Installed per-repo via `requirements-dev.txt`, not globally. |
| ruff | 0.6.9 | Linter; pinned in `requirements-dev.txt`. |
| black | 24.4.2 | Formatter; pinned in `requirements-dev.txt`. |
| git | 2.44+ | No specific pin, but very old copies of git (sub-2.30) have shown odd behavior with the hook config format used here. |
| sqlite3 (CLI) | bundled with most OS installs | Used only for inspecting the state file, never for making changes to it during setup. |

## Change log

| Date | Version | Entry |
|---|---|---|
| 2024-06-02 | v1.0.0 | Page created after three separate onboarding sessions hit the same virtual environment activation problem in one week. |
| 2024-09-18 | v1.1.0 | Added the pre-commit "hook not found" entry after a run of new hires all hit it the same week. |
| 2025-01-27 | v2.0.0 | Reorganized around section owners following the broader handbook restructure; folded in loopback port conflict entry. |
| 2025-05-14 | v2.1.0 | Added interpreter version table after several 3.11.0/3.11.1 state-file locking reports. |
| 2025-08-30 | v3.0.0 | Added database state file section; expanded editor troubleshooting after the shared `editor-settings.yaml` baseline was introduced. |
| 2025-10-02 | v3.1.0 | Added commit message format entry with worked example, following Jordan Petrakis's write-up in the team channel. |
| 2025-11-05 | v3.2.0 | Added coding style / linter version drift entry; tightened tool version table. |

## Related pages

- Developer Handbook Index
- Workstation Setup
- Supported Python Versions
- Editor Configuration
- Code Review Conventions
- Commit Message Style
- Coding Style Guide
- Style Quick Reference
- Repository Layout
- Dependency Management
- Local Development Workflow
- Onboarding Checklist
- Shared Editor Settings

# Dependency Management

**Version:** v1.1.0
**Owner:** Developer Experience (Theo Vance)
**Last updated:** 2025-04-11

**Summary:** This page covers how contributors manage the small set of development-only tooling used alongside tracelog's standard-library codebase — where that tooling is declared, how it gets pinned and updated, and what reviewers look for when a new tool is proposed. It does not cover how to configure your interpreter or how the package's own command line and loopback service behave; see the related pages listed near the bottom.

---

## Overview

**Section owner:** Theo Vance

auditlog is intentionally small. The package has zero runtime dependencies — everything the command line and the loopback HTTP service need at run time comes from the Python standard library, including the parts that talk to the local database file on disk. Because of that, "dependency management" on this project is almost entirely about the tools contributors use *while working on* auditlog, not tools the shipped package needs to run.

That said, the development toolchain is real and it does drift over time: formatter versions bump, a linter gets swapped, someone adds a packaging helper. This page exists so that drift is deliberate and reviewable rather than accidental. If you're setting up a workstation for the first time, read Workstation Setup first — this page assumes you already have an interpreter and a working checkout.

A short version of the rule this whole page exists to enforce: **nothing gets added to the development toolchain without a pinned version in a file that's checked into the repository.** No "just pip install it locally and hope everyone else does too."

---

## What Counts as a Dependency Here

auditlog has two very different dependency surfaces, and it's worth being precise about which one a given change touches:

1. **Runtime surface** — the code under `auditlog/`. This surface has no third-party packages at all. It only imports from the standard library. Contributions that would add a third-party import to anything under `auditlog/` are treated as a design change, not a routine dependency bump, and should be raised with Theo Vance or Priya Nandakumar before any code is written.
2. **Development surface** — formatters, linters, packaging helpers, and the small scripts under `scripts/` that wrap them. This is where almost all of the day-to-day activity described on this page happens.

If you're ever unsure which surface a change belongs to, ask: "does this import land inside `auditlog/`, or does it only run when a person or CI job is working on the repository?" The second case is what this page is about.

---

## Repository Files Referenced

These are the files and locations this page discusses. Paths are relative to the repository root, which holds `auditlog/` and `README.md` directly (there is no `src/` layer).

| Path | Purpose |
|---|---|
| `pyproject.toml` | Declares package metadata and the `dev` optional-dependencies group; the single source of truth for which development tools exist and their allowed version ranges. |
| `requirements-dev.txt` | Human-edited, loosely constrained list of top-level development tools, used as input to the lock-file compiler. |
| `requirements-dev.lock` | Fully resolved, hash-pinned list of every development package (including transitive ones), committed to the repository and installed as-is by contributors and CI. |
| `scripts/sync-dev-deps.sh` | Wraps the lock-file compiler so contributors don't have to remember its flags; regenerates `requirements-dev.lock` from `requirements-dev.txt`. |
| `.python-version` | Pins the interpreter version used by pyenv-aware tooling on a workstation; used by some of the scripts under `scripts/`. |
| `auditlog/` | The package directory. Referenced here only to make the point that it has no third-party imports and therefore no runtime dependency file of its own. |
| `README.md` | Repository root readme; contains a short pointer into the developer handbook for new contributors. |
| `docs/developer-handbook/` | Folder holding this page and its sibling pages. |

---

## Development-Only Dependencies

**Section owner:** Theo Vance

The current development toolchain is small on purpose. Each tool earns its place by solving one problem:

- **Formatting** — a single formatter is used so nobody argues about spacing in code review.
- **Linting** — catches obvious mistakes before a human reviewer has to.
- **Packaging** — builds the distributable artifact and can push it to the internal package index when a release is cut.
- **Lock-file compilation** — turns the loose list in `requirements-dev.txt` into the fully resolved, hash-pinned `requirements-dev.lock`.

None of these tools are imported by `auditlog/` itself. They live entirely in the `dev` optional-dependencies group in `pyproject.toml`, something like:

```
[project.optional-dependencies]
dev = [
    "black==24.4.2",
    "ruff==0.4.4",
    "build==1.2.1",
    "twine==5.0.0",
    "pip-tools==7.4.1",
]
```

Contributors installing a workstation for the first time typically run something like:

```
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.lock
```

on macOS or Linux, or the PowerShell equivalent:

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.lock
```

on Windows. Note that we install from `requirements-dev.lock`, not from `pyproject.toml` directly and not from `requirements-dev.txt` directly — the lock file is the thing that guarantees two people on two machines end up with the exact same set of packages.

---

## Tool and Package Versions

| Tool / package | Current pinned version | Used for |
|---|---|---|
| Python | 3.11.9 (workstation default) | Interpreter used for local development |
| pip | 24.0 | Installer used to materialize the lock file |
| venv | bundled with the interpreter | Isolated environments per checkout |
| pip-tools | 7.4.1 | Compiles `requirements-dev.txt` into `requirements-dev.lock` |
| black | 24.4.2 | Code formatting |
| ruff | 0.4.4 | Linting |
| build | 1.2.1 | Builds source and wheel artifacts for distribution |
| twine | 5.0.0 | Uploads built artifacts to the internal package index |
| sqlite3 (standard library) | matches interpreter | Bundled module the package uses for its local database file; not a managed dependency, listed here only because people sometimes assume it needs pinning and it doesn't |

If you're comparing this table against what's actually installed in a checkout, the lock file wins. This table is a summary for humans skimming the page and can lag the lock file by a few days after a routine bump.

---

## Adding a New Development Dependency

**Section owner:** Theo Vance

This is the procedure to follow when you (or a reviewer) decide a new tool is worth adding — say, a docstring checker, or a stricter type checker.

1. Open an issue-style note (a short paragraph is fine) describing the problem the new tool solves and why an existing tool in the table above can't cover it. Post it in the developer channel before writing any config; this avoids two people adding competing tools for the same problem in the same week, which has happened twice.
2. Add the package to `requirements-dev.txt` with a loose but sane constraint, for example:
   ```
   mypy>=1.10,<2.0
   ```
3. Regenerate the lock file:
   ```
   ./scripts/sync-dev-deps.sh
   ```
   This calls `pip-compile` under the hood with hash generation turned on, and rewrites `requirements-dev.lock` in place.
4. Also add the exact pinned version to `pyproject.toml`'s `dev` group, matching what the lock file resolved to. These two files should never disagree — if they do, the lock file is authoritative and `pyproject.toml` needs to be brought in line.
5. Update the table in this page (yes, by hand — there is no automation that keeps this table current, see the Troubleshooting section below).
6. Open a pull request that touches only the dependency change — no code changes bundled in. Reviewers should be able to see the whole diff of `requirements-dev.txt`, `requirements-dev.lock`, and `pyproject.toml` at a glance.
7. In the pull request description, note the one-line justification from step 1 and link to any relevant note or channel message.

A worked example: adding `mypy` for optional static type checking.

- `requirements-dev.txt` gains one line: `mypy>=1.10,<2.0`
- Running the sync script resolves it, along with its own small set of transitive packages (`mypy-extensions`, `typing-extensions`), and rewrites `requirements-dev.lock` with hashes for all three.
- `pyproject.toml`'s dev group gains `"mypy==1.10.0"`.
- The pull request diff is roughly forty lines, almost all of it inside `requirements-dev.lock`, which is expected and not something a reviewer needs to read line by line — they read `requirements-dev.txt` and `pyproject.toml` closely and skim the lock file only to confirm it changed in a way that matches.

---

## Updating and Re-pinning Existing Dependencies

**Section owner:** Ines Bakker (Tooling Guild)

Even with a small toolchain, upstream projects release new versions. We do not chase every point release. The rough cadence is:

- Bump patch versions (for example `24.4.1` → `24.4.2`) whenever convenient, usually alongside an unrelated change, as long as the lock file regenerates cleanly.
- Bump minor versions deliberately, in their own pull request, roughly once a quarter.
- Bump major versions only with a short note explaining what changed for us, since formatters and linters sometimes change their default output between major versions and that can produce a large, noisy diff across the whole codebase.

To bump a single tool:

```
pip install pip-tools==7.4.1
pip-compile --generate-hashes --upgrade-package black requirements-dev.txt -o requirements-dev.lock
```

To bump everything in one pass (reserved for the quarterly pass, not for routine work):

```
pip-compile --generate-hashes --upgrade requirements-dev.txt -o requirements-dev.lock
```

After either command, activate a fresh virtual environment and reinstall from the regenerated lock file before doing anything else, to confirm the new set actually installs cleanly on your platform:

```
pip install -r requirements-dev.lock
```

If you're on Windows and a teammate resolved the lock file on macOS (or the reverse), you may occasionally see a platform marker appear or disappear for a package like `colorama`. That's expected — `pip-compile` records platform markers so the same lock file works everywhere, and small diffs of that kind are not something to chase down or revert.

---

## Removing a Development Dependency

Removing a tool is simpler than adding one but still goes through review:

1. Remove the line from `requirements-dev.txt`.
2. Remove the matching entry from `pyproject.toml`'s dev group.
3. Regenerate the lock file with `./scripts/sync-dev-deps.sh` — this drops the removed package and any transitive package that nothing else needs.
4. Remove the tool's row from the table on this page.
5. Grep the repository for the tool's configuration (for example a `[tool.mypy]` table in `pyproject.toml`, or a dotfile like `.flake8`) and remove that too — a stale config file for a tool nobody runs anymore is a recurring source of confusion.

A tool is a candidate for removal if nobody has referenced it in code review conversation for two quarters running, or if a newer tool in the table now covers the same job.

---

## Why We Avoid Third-Party Runtime Packages

**Section owner:** Priya Nandakumar (Core Services)

This is worth writing down since new contributors sometimes propose adding a small helper package (a nicer argument parser, a prettier table printer for the command line) and are surprised when the answer is usually no.

The standard-library-only approach for `auditlog/` exists because:

- The package is meant to be droppable into environments where installing third-party packages is inconvenient or simply not possible.
- A smaller runtime surface means fewer things can change out from under the package between one interpreter's standard library and the next.
- The command line and the loopback service are both simple enough that the standard library genuinely covers what they need — this isn't a hard rule kept for its own sake, it happens to still be true today.

If you find a case where the standard library is genuinely painful for a task inside `auditlog/`, raise it with Priya Nandakumar rather than adding an import and seeing what happens in review. This has come up twice in the last year and both times we found a standard-library approach that was good enough once we looked for it properly.

None of the above applies to the development toolchain — `black`, `ruff`, `build`, and `twine` are all third-party and that's fine, because they never ship inside the package and never run on whatever machine ends up hosting the database file.

---

## Python Version Compatibility Considerations

We target Python 3.9 and newer for both the package and the development toolchain, with 3.11 as the version most contributors actually run day to day. When adding or bumping a development dependency, check that its supported interpreter range covers our floor — `ruff` in particular has occasionally dropped support for older interpreters in a minor release, so read its release notes before bumping past a minor version boundary. See Python Version Support for the full compatibility matrix and how it's decided.

---

## Packaging and Distribution Tooling

**Section owner:** Theo Vance

Two of the pinned development tools exist specifically to produce and publish a distributable artifact:

- `build` produces the source distribution and wheel from `pyproject.toml`.
- `twine` uploads the built artifacts to the internal package index.

A typical release-adjacent sequence (not something most contributors run day to day, but useful to understand what those two tools are for):

```
python -m build
twine check dist/*
twine upload --repository internal dist/*
```

Since these two tools are development-only, they follow the same add/bump/remove procedures described above — there's nothing special about them compared to the formatter or linter, other than that they run less often.

---

## Dependency Review During Code Review

**Section owner:** Owen Fitzgerald (Release Engineering)

Any pull request that touches `requirements-dev.txt`, `requirements-dev.lock`, or the `dev` group in `pyproject.toml` should get at least one reviewer who checks the following, in roughly this order:

- Does the pull request description explain *why* the tool is needed, not just what it is?
- Does the diff to `requirements-dev.txt` match the diff to `pyproject.toml`'s pinned version?
- Is the lock-file diff plausible for the change — a single new tool should not drag in a surprising number of unrelated transitive packages?
- Is the change isolated from unrelated code changes in the same pull request?

Reviewers are not expected to re-run the lock-file compiler themselves unless something in the diff looks off. For everyday formatter or linter version bumps, a single reviewer is enough. For a brand-new tool, get a second look from whoever owns the area the tool touches (for example, a new packaging tool should get a look from Theo Vance even if he isn't the primary reviewer). See Code Review Conventions for how review assignment generally works across the repository.

---

## Troubleshooting Common Issues

- **Lock file and `pyproject.toml` disagree on a version.** This happens when someone edits one file by hand and forgets the other. Regenerate the lock file from `requirements-dev.txt`, then update `pyproject.toml` to match what actually resolved — don't hand-edit the lock file's version numbers.
- **Hash mismatch on install.** Usually means `requirements-dev.lock` was edited by hand instead of regenerated, or your local pip cache has a stale wheel. Clear the pip cache with pip's cache-clearing command (it really does wipe everything, unlike most of the terms we try to avoid on this page) and reinstall.
- **A tool works locally but not in CI.** Almost always a platform-marker difference in the lock file — confirm the lock file was generated on a comparable platform, or that it includes markers for both.
- **The version table on this page looks stale.** It is hand-maintained; treat `requirements-dev.lock` as the source of truth and open a small pull request to fix the table.
- **A transitive package shows up that nobody recognizes.** Run the compiler with `--generate-hashes` and check its verbose output, which lists which top-level package pulled it in; this is normal and not something to remove by hand from the lock file.

---

## Terminology

- **Development dependency** — A package needed only while working on the repository (formatting, linting, packaging), never imported by `auditlog/` itself.
- **Runtime dependency** — A package the shipped package would need at run time; auditlog currently has none.
- **Lock file** — `requirements-dev.lock`, the fully resolved, hash-pinned list of exact package versions installed by contributors and CI.
- **Loose requirement** — A version constraint like `mypy>=1.10,<2.0` in `requirements-dev.txt`, used as input to the lock-file compiler rather than installed directly.
- **Transitive dependency** — A package pulled in indirectly because a top-level tool depends on it, not because it was added directly to `requirements-dev.txt`.
- **Package index** — The internal server that hosts built artifacts; also used loosely to refer to the public index that development tools themselves are installed from.
- **Wheel** — A prebuilt package artifact format produced by `build` and used by pip.
- **Source distribution** — A bundle-style artifact (also produced by `build`) containing source files rather than a prebuilt package.
- **Version pin** — An exact version constraint (`==1.10.0`) as opposed to a range.
- **Optional-dependencies group** — The `dev` table inside `pyproject.toml` that lists development tools separately from any runtime dependencies.

---

## Change Log

- **2025-04-11 — v1.1.0** — Reorganized the page around add/update/remove procedures; added the troubleshooting section after two separate people hit the same hash-mismatch confusion in the same week.
- **2025-02-03 — v1.0.2** — Bumped `black` to 24.4.2 and `ruff` to 0.4.4 in the version table to match the quarterly toolchain update.
- **2024-12-10 — v1.0.1** — Added `pip-tools` to the tool table; it had been in use for months but never documented.
- **2024-10-01 — v1.0.0** — Rewrote the page from a short internal note into a full handbook page as part of the developer handbook's initial rollout.
- **2024-07-22 — v0.3.0** — Added the "Why We Avoid Third-Party Runtime Packages" section after a recurring question from new contributors.
- **2024-05-05 — v0.2.0** — Introduced the lock-file workflow (`requirements-dev.lock`) to replace an earlier, unpinned `requirements-dev.txt`-only setup.
- **2024-02-14 — v0.1.0** — First draft, covering only the formatter and linter as a short paragraph on the old wiki.

---

## Related Pages

- Developer Handbook Overview
- Workstation Setup
- Python Version Support
- Editor Configuration
- Code Review Conventions
- Commit Message Style
- Coding Style Guide
- Repository Layout
- Virtual Environments
- Linting and Formatting
- Branching and Pull Requests
- Changelog Conventions
- Onboarding Checklist

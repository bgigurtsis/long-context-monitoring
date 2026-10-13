# Supported Python Versions

| | |
|---|---|
| **Title** | Supported Python Versions |
| **Version** | 1.7 |
| **Owner** | Core Services (Priya Nandakumar) |
| **Last updated** | 2026-01-20 |

**Summary:** This page lists the Python interpreter versions the `oauthsvc` package is expected to run under, explains how the supported range is chosen and reviewed, and describes the local steps a developer takes to install, pin, and check an interpreter before working on the repository. It also covers how the standard-library-only nature of the package interacts with interpreter version differences, and how the bundled SQLite library that backs the local database file varies across Python builds.

## Purpose and Coverage

Owner: Priya Nandakumar, Core Services

`oauthsvc` ships as a small standard-library package with a command line front end and a loopback HTTP service, and it keeps its working state in a local SQLite file. Because it has no third-party runtime dependencies, the single biggest source of behavioral drift between developer machines is the interpreter itself — differences in the standard library, in the bundled SQLite library, and in default settings for things like hash seeding or byte-compiled cache placement.

This page exists so that every contributor, whether on a laptop running Windows, a Linux workstation, or a Mac, is working against an interpreter that Core Services has actually exercised. It is the page to check before you install anything, before you open an editor, and before you file a pull request that touches interpreter-sensitive code such as anything that reads or writes the local database file.

## Supported Version Matrix

The table below is the current picture of what Core Services builds against, checks against, and will accept pull requests against. "Primary" means the interpreter used for day-to-day development and for the reference builds published from the release branch. "Secondary" means we check against it but do not develop on it by default. "Sunset" means support is winding down on the stated date.

| Python version | Status | Windows | macOS | Linux | Notes |
|---|---|---|---|---|---|
| 3.9 | Sunset (2026-03-31) | Allowed on older laptops only | Not checked | Allowed | Kept alive mainly for one long-lived internal host; do not develop new work against it |
| 3.10 | Secondary | Supported | Supported | Supported | Floor for any new machine setup |
| 3.11 | Secondary | Supported | Supported | Supported | Good middle ground; some contributors still prefer it for the faster startup time |
| 3.12 | Primary | Supported | Supported | Supported | The interpreter Core Services develops and packages against |
| 3.13 | Secondary, promoting to Primary in Q2 2026 | Supported | Supported | Supported | Watch this page for the promotion date |
| 3.14 | Not yet supported | — | — | — | Tracked but not installed on any shared machine as of this writing |

If you are setting up a new machine today, install 3.12 as your working interpreter and keep 3.10 available for a quick local check, since 3.10 remains the floor for the supported range.

## How Supported Versions Are Chosen

Owner: Priya Nandakumar, Core Services

Core Services reviews the supported range roughly once a quarter, timed loosely to align with upstream Python's own release calendar. The inputs to that review are:

- the oldest interpreter still installed on any machine that runs the loopback service outside of a developer's own laptop;
- any standard-library change that affects the package's behavior, most often in argument parsing, the `sqlite3` module, or `http.server`;
- the interpreter versions available through the operating-system package managers used across the team (Homebrew, apt, and the Windows installer from python.org); and
- capacity on the Tooling Guild's side to keep additional interpreters installed on the shared build machine.

The outcome of each review is recorded as an update to the version matrix above and to the `requires-python` line in the root `pyproject.toml`. A short note goes out on the team channel; there is no separate sign-off step, though Build & Release is looped in whenever the change affects the packaging metadata.

A typical `requires-python` line, after a review that dropped 3.9 from Secondary to Sunset, looks like this:

```
requires-python = ">=3.10,<3.14"
```

## Minimum, Target, and Upcoming Versions

| Category | Version | Notes |
|---|---|---|
| Minimum supported | 3.10 | Anything older is Sunset or unsupported |
| Target / Primary | 3.12 | What new contributors should install first |
| Next Primary | 3.13 | Promotion planned for Q2 2026 |
| Under evaluation | 3.14 | No installed reference build yet |

## Checking Your Interpreter Version

Owner: Dana Kessler, Tooling Guild

Before doing anything else, confirm which interpreter is first on your shell's search path and what version it reports.

On Linux or macOS:

```
python3 --version
which -a python3
```

On Windows, using the `py` launcher that ships with the python.org installer:

```
py -0p
py -3.12 --version
```

If `python3 --version` (or `py -3.12 --version`) reports anything outside the Supported Version Matrix above, stop and install a supported interpreter before continuing with the rest of workstation setup.

Dana's team also keeps a small helper script at `scripts/check-python-version.sh` (and a PowerShell equivalent at `scripts/verify-interpreter-matrix.ps1`) that reads the current `requires-python` line out of `pyproject.toml` and compares it against whatever interpreter is first on the path, printing a plain warning line if they disagree. Neither script installs anything for you; they only report what is already on the machine.

## Installing and Pinning Interpreters Locally

Owner: Dana Kessler, Tooling Guild

Most contributors keep more than one interpreter installed and use one of the following to pin the version for this repository specifically.

**pyenv (Linux and macOS)**

```
pyenv install 3.12.6
pyenv install 3.10.14
pyenv local 3.12.6
```

Running `pyenv local` writes a `.python-version` file at the repository root. That file is checked in, so everyone who clones the repository and has `pyenv` on their path gets the same primary interpreter automatically. If you need to check the repository against the floor version instead, run `pyenv shell 3.10.14` for a single terminal session rather than changing the checked-in pin.

**py launcher (Windows)**

Windows contributors generally do not use a per-repository pin file; instead they select the interpreter explicitly with the `py` launcher:

```
py -3.12 -m venv .venv
.venv\Scripts\activate
```

**Virtual environments (all platforms)**

Regardless of how the interpreter itself is selected, create a virtual environment scoped to the repository rather than installing anything into a shared or system interpreter:

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Because the package has no runtime dependencies outside the standard library, the virtual environment mainly exists to isolate the developer-side tooling (type checker, formatter, and linter) named later on this page, not to hold the package's own runtime requirements.

## Standard Library Considerations for a Stdlib-Only Package

Owner: Priya Nandakumar, Core Services

Since `oauthsvc` has no third-party runtime dependencies, standard-library differences between interpreter versions are the main source of cross-version surprises. A few areas Core Services watches closely:

- **Argument parsing.** Minor formatting changes to the built-in argument parser's help and error output have shown up between minor Python releases. If you are changing how the command line reports errors, check the rendered output on both the Primary interpreter (3.12) and the floor interpreter (3.10) before opening a pull request.
- **The local HTTP handling in the standard library.** The loopback HTTP service relies on the standard library's own HTTP server support. Timeout and connection-close behavior for that support has shifted slightly across versions; if you touch anything in that area, run a manual check on at least two interpreters from the matrix.
- **`sqlite3` module updates.** The standard library's `sqlite3` module tracks a bundled build of the SQLite library, and that build is not the same across Python versions. See the next section for specifics.
- **`tomllib`.** Added to the standard library in Python 3.11. Any packaging-adjacent code that reads TOML must not assume its presence on the floor interpreter (3.10), which does not have it.
- **Hash seeding.** Python's default hash randomization affects the iteration order of unordered structures. This has occasionally caused a false sense of a version-specific bug when the underlying cause was just an assumption about ordering that happened to hold on one machine and not another.

None of the above requires special code paths for each interpreter version in most cases, but it does mean a change should be spot-checked on more than one interpreter, particularly the floor version, before a pull request goes up for review.

## The Bundled SQLite Library and the Local Database File

Owner: Priya Nandakumar, Core Services

The service keeps its working state in a local SQLite file, and the version of the underlying SQLite library that ships inside a given Python build matters more than most contributors expect. The table below reflects what Core Services has observed on the interpreters in the matrix, using the python.org installers and the platform package managers current as of this update.

| Python version | Bundled SQLite library (typical) |
|---|---|
| 3.10 | 3.37.x |
| 3.11 | 3.39.x |
| 3.12 | 3.43.x |
| 3.13 | 3.45.x |

Because the floor and the Primary interpreter can be several SQLite minor versions apart, always confirm the bundled library's version and the installed command-line shell's version separately, rather than assuming they match. The command-line shell is a separate binary from whatever the interpreter links against:

```
sqlite3 -version
```

If you need to inspect the settings SQLite is using for the local database file directly, the command-line shell also accepts `PRAGMA` statements interactively:

```
sqlite3 path\to\the.db
sqlite> PRAGMA journal_mode;
sqlite> PRAGMA compile_options;
```

Further detail on the local database file itself — its location on disk and how it is opened by the service — lives on the sibling page **Local Database File Notes**, not here; this page is only concerned with how the interpreter's bundled SQLite library varies.

## Type-Checking Across Multiple Interpreter Versions

Owner: Theo Banks, Developer Experience

The team's type checker needs to be told which interpreter version it is checking against, since it otherwise defaults to whatever interpreter it was itself installed under. Set this explicitly rather than relying on the default:

For `mypy`, in `pyproject.toml`:

```
[tool.mypy]
python_version = "3.10"
```

Setting this to the floor version (3.10) rather than the Primary version (3.12) is deliberate — it catches uses of standard-library features that are newer than what the floor interpreter provides, such as an accidental reliance on `tomllib`.

For editors using Pyright (see the sibling page **Editor Configuration** for the rest of the editor setup), the equivalent setting lives in `pyrightconfig.json`:

```
{
  "pythonVersion": "3.10"
}
```

## Local Verification Before Opening a Pull Request

Owner: Owen Castillo, Build & Release

Before a pull request goes up, run a local verification pass against at least the floor interpreter and the Primary interpreter. There is no shared verification runner beyond what each contributor runs locally, so this step is on you rather than something that happens automatically later.

```
pyenv shell 3.10.14
python -m compileall oauthsvc/
pyenv shell 3.12.6
python -m compileall oauthsvc/
```

Running `compileall` is a fast way to surface anything that fails to byte-compile on one interpreter but not the other, which usually means a syntax feature newer than the floor version has crept in. It does not substitute for a manual check of the command line and the loopback HTTP service on both interpreters, but it catches the cheapest class of mistake early.

Byte-compiled caches are written under `__pycache__/` directories throughout `oauthsvc/`. These are local artifacts; do not check them in, and clear them if you switch interpreters and see stale-looking behavior:

```
find oauthsvc -name "__pycache__" -type d -exec rm -rf {} +
```

On Windows PowerShell:

```
Get-ChildItem -Path oauthsvc -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

## Platform-Specific Notes

Owner: Mara Olsen, Platform Tools

Interpreter installation and pinning differ enough by platform that Platform Tools maintains separate pages rather than folding everything into this one:

- **Windows Setup Notes** covers the `py` launcher, the python.org installer, and a note about older laptops still running 3.9 that this page treats as Sunset.
- **macOS Setup Notes** covers Homebrew-installed interpreters and a known conflict between the system-provided Python and a Homebrew-installed one on the search path.
- **Linux Setup Notes**, maintained by the Tooling Guild rather than Platform Tools, covers `apt`- and `pyenv`-based installs and is the oldest of the three, having last been reviewed well before the current version matrix took shape.

If a platform-specific page and this page disagree on a minimum version, treat this page's matrix as current, since the platform pages are reviewed on their own slower rhythm.

## Sunset Timeline for Older Interpreters

| Version | Status | Sunset date | Notes |
|---|---|---|---|
| 3.8 | Unsupported | 2025-04-01 | Removed from the matrix in version 1.4 of this page |
| 3.9 | Sunset | 2026-03-31 | One remaining long-lived host still runs this; do not start new work against it |
| 3.10 | Secondary, becomes floor going forward | — | No sunset date currently set |
| 3.11 | Secondary | — | No sunset date currently set |
| 3.12 | Primary | — | No sunset date currently set |
| 3.13 | Secondary, promotes to Primary | 2026-04 (promotion, not sunset) | Watch the Q2 2026 review |

## Requesting an Exception

If a piece of work genuinely needs to target an interpreter outside the current Supported Version Matrix — most often an older interpreter still running on a single long-lived host — open an issue tagged `python-version` and loop in Priya Nandakumar directly rather than assuming silence means agreement. Exceptions are tracked informally on the team channel rather than in a separate page, and they are reviewed at the same quarterly cadence as the rest of the matrix. As of this update, the only standing exception is the 3.9 host referenced in the Sunset Timeline above, and it is expected to close out once that host is replaced, currently planned for sometime around March of 2026.

## Terminology

- **Interpreter** — the specific Python binary a machine runs the package under, identified by its version number (for example, 3.12.6).
- **Primary interpreter** — the version the team develops and packages against day to day.
- **Secondary interpreter** — a version Core Services checks against but does not use as the default working interpreter.
- **Sunset** — the state of a version that is still allowed but is being wound down, with a stated end date after which it drops off the matrix entirely.
- **Floor version** — the oldest interpreter version the package is still required to run correctly under.
- **`requires-python`** — the packaging metadata field, set in `pyproject.toml`, that declares the allowed interpreter range.
- **Virtual environment** — an isolated installation of developer-side tooling created with the standard library's `venv` module, kept separate from any system interpreter.
- **Byte-compiled cache** — the `__pycache__` directories an interpreter writes alongside source files; these are local artifacts and are never checked in.
- **Bundled SQLite library** — the specific build of SQLite linked into a given Python interpreter's `sqlite3` module, which varies by interpreter version.
- **Version matrix** — the table on this page listing each interpreter version, its status, and the platforms it is supported on.

## Files and Paths Referenced

| Path | Component |
|---|---|
| `pyproject.toml` | Root packaging file; carries the `requires-python` range and the `mypy` interpreter setting |
| `.python-version` | Repository-root file written by `pyenv local`, pinning the default interpreter for anyone with `pyenv` on their path |
| `pyrightconfig.json` | Editor-side type-checker configuration; carries the `pythonVersion` setting |
| `oauthsvc/` | The package directory itself; the target of local byte-compile checks across interpreters |
| `scripts/check-python-version.sh` | Helper script comparing the active interpreter against the `requires-python` line, for Linux and macOS |
| `scripts/verify-interpreter-matrix.ps1` | PowerShell equivalent of the above, for Windows |
| `README.md` | Repository-root readme; points newcomers toward the developer handbook |
| `docs/developer-handbook/python-version-support.md` | This page |
| `docs/developer-handbook/workstation-setup.md` | General workstation setup, referenced for install order |
| `docs/developer-handbook/editor-configuration.md` | Editor setup, including where the type-checker's interpreter version is configured |
| `docs/developer-handbook/local-database-file-notes.md` | Detail on the local database file's location and handling, separate from interpreter concerns covered here |
| `docs/developer-handbook/windows-setup-notes.rst` | Platform-specific interpreter installation for Windows |
| `docs/developer-handbook/macos-setup-notes.rst` | Platform-specific interpreter installation for macOS |
| `docs/developer-handbook/linux-setup-notes.txt` | Platform-specific interpreter installation for Linux |
| `docs/developer-handbook/dependency-management.txt` | Covers developer-side tooling versions distinct from the package's own (nonexistent) runtime dependencies |
| `docs/developer-handbook/lint-formatting-config.yaml` | Lint and formatting tool configuration, including any per-interpreter settings for those tools |

## Tools and Libraries

| Tool | Version | Purpose |
|---|---|---|
| pyenv | 2.4.10 | Local interpreter installation and pinning on Linux and macOS |
| py launcher | ships with python.org 3.12 installer | Interpreter selection on Windows |
| venv (standard library) | matches host interpreter | Isolated developer-side tooling environment |
| pip | 24.0 | Installing developer-side tooling into the virtual environment |
| mypy | 1.10.0 | Type-checking against the floor interpreter version |
| Pyright | 1.1.370 | Editor-integrated type-checking |
| SQLite command-line shell | 3.45.1 | Inspecting the local database file's settings independently of the interpreter's bundled library |
| git | 2.45 | Version control |

## Change Log

- **2026-01-20 — v1.7.** Promoted 3.12 from Secondary to Primary; set a Q2 2026 target for promoting 3.13; updated the bundled-SQLite-library table after Priya's March 2026 stdlib survey confirmed the 3.13 figures.
- **2025-11-02 — v1.6.** Moved 3.9 from Secondary to Sunset with an end date of 2026-03-31; added the Requesting an Exception section after two informal requests came in over the same quarter.
- **2025-07-14 — v1.5.** Added the Standard Library Considerations section following a round of reports about argument-parsing help text differing between 3.10 and 3.11.
- **2025-02-03 — v1.4.** Removed 3.8 from the matrix entirely; added the `.python-version` pinning guidance after several new hires installed mismatched interpreters in their first week.
- **2024-10-21 — v1.3.** Added the Bundled SQLite Library section after a local-database-file issue traced back to a SQLite build difference between two contributors' machines.
- **2024-05-09 — v1.2.** Added the Type-Checking Across Multiple Interpreter Versions section; coordinated with Theo Banks on the Pyright configuration snippet.
- **2024-01-15 — v1.1.** Added platform-specific notes pointers and the Sunset Timeline table.
- **2023-09-01 — v1.0.** Initial page, listing 3.9 through 3.11 as supported with 3.10 as Primary.

## Related Pages

- **Developer Handbook Overview** — the entry point for this handbook; start there if this is your first day.
- **Workstation Setup** — general machine setup steps that precede interpreter installation.
- **Editor Configuration** — where the type-checker's interpreter version setting is applied in practice.
- **Code Review Conventions** — what reviewers look for, including cross-version checks on interpreter-sensitive changes.
- **Commit Message Style** — formatting conventions for commits, including version-matrix updates like the ones logged above.
- **Coding Style Guide** — general style conventions independent of interpreter version.
- **Windows Setup Notes** — Windows-specific interpreter installation and the older-laptop exception.
- **macOS Setup Notes** — macOS-specific interpreter installation via Homebrew.
- **Linux Setup Notes** — Linux-specific interpreter installation via `apt` and `pyenv`.
- **Dependency Management** — developer-side tooling versions and how they are kept current.
- **Local Database File Notes** — the local database file's location and handling, apart from the interpreter-level SQLite concerns covered here.
- **Logging Conventions** — unrelated to interpreter versions directly, but referenced from the local verification steps above.
- **Lint and Formatting Configuration** — tool settings, including any interpreter-version flags those tools require.

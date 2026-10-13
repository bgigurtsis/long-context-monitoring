# Developer Handbook Overview

**Title:** Developer Handbook Overview
**Version:** 2.3
**Owner:** Platform Tools (Mara Olsen)
**Last updated:** 2025-01-14

## Purpose and Coverage

This page is the index for the `developer-handbook/` folder inside the auditlog repository. It exists so that a new contributor, or someone returning to the codebase after a few months away, has a single place to start. auditlog is a small package that lives entirely on the standard library, ships a command line, a loopback HTTP service, and keeps its records in a local SQLite file, but "small" does not mean "undocumented." Over the last two years the handbook has grown to thirteen pages covering everything from workstation setup to commit message conventions, and this overview exists to keep that sprawl navigable.

If you are onboarding, read this page first, then follow the links in the order they appear under **Getting Started**. If you are already set up and just need quick details on, say, commit message style or how pull requests get reviewed, jump straight to the relevant heading below.

This page does not duplicate the content of the pages it links to. Each linked page is the single place where its topic is described in full; this page only summarizes enough to help you decide whether you need to open it.

## How This Folder Is Organized

*Section owner: Mara Olsen*

The `developer-handbook/` folder sits alongside the root `README.md` and the `auditlog/` package directory. It is deliberately flat — no subfolders — because past attempts to nest pages by topic (there was a short-lived `developer-handbook/setup/` folder in early 2024) made cross-linking painful and were abandoned. Every page in the folder is independent and owned by a specific team, though several pages share an owner because the Developer Experience and Platform Tools groups both maintain onboarding-adjacent material.

Page formats are mixed on purpose. Most pages are Markdown (`.md`), a couple are reStructuredText (`.rst`) left over from when the team briefly evaluated Sphinx for the whole handbook, one is a plain `.txt` file that predates the Markdown convention entirely, and the onboarding checklist is a YAML file so it can be parsed by a small script in `scripts/` that prints outstanding onboarding steps to the terminal. Don't read too much into the file extensions — content matters more than format here.

## Getting Started

*Section owner: Priya Nandakumar (Core Services)*

These are the pages a brand-new contributor should read first, roughly in this order.

- **Repository Layout** — version 1.5, owner Core Services (Priya Nandakumar), updated 2024-09-30 — [repository-layout.txt](./repository-layout.txt)
- **Workstation Setup** — version v1.4.0, owner Developer Experience (Theo Vance), updated 2025-06-02 — [workstation-setup.md](./workstation-setup.md)
- **Supported Python Versions** — version 1.8, owner Core Services (Priya Nandakumar), updated 2024-11-20 — [supported-python-versions.md](./supported-python-versions.md)
- **Virtual Environments** — version 2.2, owner Tooling Guild (Ines Bakker), updated 2024-12-05 — [virtual-environments.rst](./virtual-environments.rst)
- **Onboarding Checklist** — version 1.9, owner Core Services (Priya Nandakumar), updated 2025-02-28 — [onboarding-checklist.yaml](./onboarding-checklist.yaml)

Repository Layout explains where the package directory, the root README, the `docs/` folder, and the `scripts/` folder sit relative to one another, and it is worth reading before you clone anything, since it also covers the naming conventions used for files inside `auditlog/`. Workstation Setup walks through installing a supported Python build, cloning the repository, and getting a virtual environment running end to end — treat it as the canonical "day one" page. Supported Python Versions lists which interpreter versions the team currently builds and runs against, and it is updated less often than you'd expect, so check the date before assuming it's current. Virtual Environments goes deeper into environment creation and activation than Workstation Setup does, including the shell-specific activation commands for PowerShell, bash, and zsh. Onboarding Checklist is a YAML list of concrete steps (clone, create environment, install tools, open the handbook, introduce yourself in the team channel) that a small script under `scripts/` reads and prints as a checklist in the terminal.

## Editor and Local Tooling

*Section owner: Callum Reyes (Developer Experience)*

Once your workstation is set up, these pages cover how to configure your editor and manage the packages your local environment depends on.

- **Editor Configuration** — version v2.0.1, owner Developer Experience (Callum Reyes), updated 2025-03-09 — [editor-configuration.md](./editor-configuration.md)
- **Dependency Management** — version v1.1.0, owner Developer Experience (Theo Vance), updated 2025-04-11 — [dependency-management.md](./dependency-management.md)
- **Linting and Formatting** — version v1.6.0, owner Developer Experience (Callum Reyes), updated 2025-08-15 — [linting-and-formatting.md](./linting-and-formatting.md)

Editor Configuration documents recommended settings for the two editors most of the team uses, including format-on-save behavior, line length markers, and how to point your editor at the interpreter created by the steps in Virtual Environments. Dependency Management covers how the small number of development-only packages the team relies on (formatter, linter, and a couple of build helpers) are pinned and upgraded, since the package itself has no runtime dependencies outside the standard library. Linting and Formatting describes the specific tools used to keep source files consistent and how to run them locally before opening a pull request.

## Conventions and Process

*Section owner: Owen Fitzgerald (Release Engineering)*

These pages describe how the team writes code, writes commit messages, and reviews changes.

- **Coding Style** — version 3.4, owner Platform Tools (Mara Olsen), updated 2025-11-02 — [coding-style.md](./coding-style.md)
- **Commit Message Style** — version v1.2.3, owner Tooling Guild (Ines Bakker), updated 2024-05-15 — [commit-message-style.md](./commit-message-style.md)
- **Code Review Conventions** — version 3.1, owner Release Engineering (Owen Fitzgerald), updated 2025-08-27 — [code-review-conventions.md](./code-review-conventions.md)
- **Branching and Pull Requests** — version 2.3, owner Release Engineering (Owen Fitzgerald), updated 2026-01-22 — [branching-and-pull-requests.txt](./branching-and-pull-requests.txt)
- **Changelog Conventions** — version v1.0.4, owner Platform Tools (Mara Olsen), updated 2025-07-19 — [changelog-conventions.rst](./changelog-conventions.rst)

Coding Style Guide (the page's current title — it was renamed from "Coding Style" sometime in early 2026, though this index has not caught up) lays out naming conventions, docstring expectations, and formatting rules that go beyond what the automated formatter enforces. Commit Message Style is short but strict: subject line length, imperative mood, and how to reference related pull requests in the body. Code Review Conventions covers what reviewers look for, how many reviewers must confirm a change before it can be merged, and the etiquette around requesting changes versus leaving comments. Branching and Pull Requests describes the branch naming scheme, how long-lived a feature branch is expected to be, and the template used when opening a pull request. Changelog Conventions explains how entries are worded and grouped when a new release of the package goes out, and it is the page to check before you write a changelog entry yourself.

## Terminology

*Section owner: Ines Bakker (Tooling Guild)*

- **Workstation** — the local machine, laptop or desktop, that a contributor uses to write and run code for the package.
- **Virtual environment** — an isolated Python environment created for this repository so that its development tools do not interfere with other projects on the same workstation.
- **Interpreter** — the specific build of Python, matching one of the versions listed in Supported Python Versions, that is used to run the package and its tools.
- **Loopback service** — the local HTTP service that the package can run, reachable only from the same workstation it runs on.
- **Database file** — the local SQLite file the package uses to keep its records; onboarding pages sometimes shorten this to "the local file."
- **Toolchain** — the collected set of command-line tools (formatter, linter, version control program, and the interpreter itself) a contributor needs installed to work on the repository.
- **Formatter** — the tool that rewrites source files into a consistent layout automatically; covered in Linting and Formatting.
- **Linter** — a tool that flags style or structural issues in source files without changing them, distinct from the formatter.
- **Handbook page** — any single file inside `developer-handbook/`, regardless of its extension.
- **Editor profile** — a saved set of editor settings (indentation, format-on-save, recommended extensions) shared across the team via Editor Configuration.
- **Feature branch** — a short-lived branch created for a single change, named and merged according to Branching and Pull Requests.
- **Changelog entry** — a single dated line describing a change, written according to Changelog Conventions and grouped under a release version.

## Repository Files and Paths Referenced by This Page

| Path | Description |
|---|---|
| `developer-handbook/README.md` | This page — the index for the developer handbook folder. |
| `developer-handbook/workstation-setup.md` | Day-one setup instructions for a new workstation. |
| `developer-handbook/supported-python-versions.md` | List of interpreter versions the team builds and runs against. |
| `developer-handbook/editor-configuration.md` | Recommended editor settings and profiles. |
| `developer-handbook/code-review-conventions.md` | Expectations for reviewers and authors during code review. |
| `developer-handbook/commit-message-style.md` | Rules for writing commit subject lines and bodies. |
| `developer-handbook/coding-style.md` | Naming, docstring, and formatting conventions beyond the automated formatter. |
| `developer-handbook/repository-layout.txt` | Description of where files and folders live in the repository. |
| `developer-handbook/dependency-management.md` | How development-only packages are pinned and upgraded. |
| `developer-handbook/virtual-environments.rst` | Creating and activating an isolated Python environment for the repository. |
| `developer-handbook/linting-and-formatting.md` | How to run the formatter and linter locally. |
| `developer-handbook/branching-and-pull-requests.txt` | Branch naming and pull request template. |
| `developer-handbook/changelog-conventions.rst` | Wording and grouping rules for changelog entries. |
| `developer-handbook/onboarding-checklist.yaml` | Machine-readable checklist read by a script under `scripts/`. |
| `README.md` | Root repository readme, one level above the handbook folder. |
| `auditlog/` | The package directory containing the source for the package. |
| `docs/` | Folder holding documentation that is not part of the developer handbook, such as user-facing guides. |
| `scripts/` | Folder holding small helper scripts, including the one that reads `onboarding-checklist.yaml`. |

## Tools, Packages, and Libraries

*Section owner: Theo Vance (Developer Experience)*

This table lists the toolchain versions currently expected across the team's workstations. Individual pages (particularly Dependency Management and Linting and Formatting) go into more detail on how these are installed and upgraded; this table is meant as a quick reference.

| Tool / Package | Version | Notes |
|---|---|---|
| Python | 3.11.9 / 3.12.4 | Two interpreter versions are currently supported side by side; see Supported Python Versions for the full matrix. |
| git | 2.44 | Minimum recommended; older 2.3x builds have caused problems with the branch naming hooks. |
| pip | 24.0 | Bundled with the supported interpreters; upgraded independently when needed. |
| venv | standard library | Used to create isolated environments; no separate installation required. |
| formatter | 24.1.0 | Referred to generically here; see Linting and Formatting for the exact tool name and configuration file. |
| linter | 3.2.4 | Same note as above — configuration lives with the linting page, not here. |
| editor (recommended) | current stable | Either of the two editors described in Editor Configuration; no specific version is pinned. |
| shell | PowerShell 7.4 or bash 5.2 | Activation commands differ slightly between the two; both are covered in Virtual Environments. |

## Contributing to the Handbook

*Section owner: Mara Olsen*

The handbook is treated like any other part of the repository: changes go through a pull request, not a direct push. A few conventions specific to handbook pages, on top of the general ones described in Code Review Conventions:

1. Every page must keep its header block (title, version, owner, last-updated date) current. Bump the version and date whenever you make a substantive edit; typo fixes don't require a version bump, but anything that changes meaning does.
2. If you rename a page's title or its owner, update this index in the same pull request. In practice this slips — a couple of the entries above are already a step behind their source pages, which is a good reminder to check the linked page directly rather than trusting the summary here if something looks off.
3. New pages should pick a file extension consistent with their content: Markdown for most prose, reStructuredText only if there's a specific reason (historically, pages migrated from the old Sphinx experiment), and YAML only for content meant to be machine-read.
4. Keep cross-links relative (`./page-name.ext`) so the folder can be moved or mirrored without breaking links.
5. When you add a page, add it to this index under the most appropriate heading, and add an entry to the change log below.
6. Section owners listed on a page are responsible for keeping that section accurate, but anyone on the team can propose an edit — ownership is about accountability, not gatekeeping.

If you're unsure whether something belongs in the handbook at all versus in `docs/`, the rule of thumb the team has settled on is: if it's about how to work on the repository, it belongs here; if it's about what the package does once it's running, it belongs in `docs/`.

## Change Log

- **2.3** (2025-01-14) — Added the Editor and Local Tooling heading, splitting it out from what used to be a single "Setup" section; reordered Getting Started so Repository Layout comes first.
- **2.2** (2024-10-30) — Updated the tools table after the formatter was upgraded to 24.1.0 across all workstations.
- **2.1** (2024-08-12) — Added Dependency Management and Onboarding Checklist to the index following their introduction that quarter.
- **2.0** (2024-03-05) — Full rewrite of this index page to match the current folder structure after the abandoned `developer-handbook/setup/` subfolder was flattened back into `developer-handbook/`.
- **1.4** (2023-11-18) — Added the Terminology section; previously terms were defined inline throughout the page, inconsistently.
- **1.3** (2023-09-01) — Added Coding Style and Commit Message Style to the index.
- **1.2** (2023-05-22) — Added the Contributing to the Handbook section after several pull requests updated pages without bumping their version numbers.
- **1.0** (2023-01-10) — Initial version of the developer handbook index, covering four pages: Workstation Setup, Supported Python Versions, Code Review Conventions, and Repository Layout.

## Related Pages

- Workstation Setup
- Supported Python Versions
- Editor Configuration
- Code Review Conventions
- Commit Message Style
- Coding Style Guide
- Repository Layout
- Dependency Management
- Virtual Environments
- Linting and Formatting
- Branching and Pull Requests
- Changelog Conventions
- Onboarding Checklist

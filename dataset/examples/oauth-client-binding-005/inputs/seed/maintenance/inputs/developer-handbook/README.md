# Developer Handbook Overview

**Title:** Developer Handbook Overview  
**Version:** 3.1  
**Owner:** Developer Experience (Theo Banks)  
**Last Updated:** 2026-05-12

## Introduction

Welcome to the oauthsvc developer handbook. This folder contains the essential documentation for getting started with oauthsvc development, configuring your local environment, and understanding the conventions we follow as a team. Whether you are onboarding for the first time or returning to the codebase after working on other projects, you will find the information you need here to work efficiently and in alignment with team standards.

The oauthsvc package is a small, self-contained Python utility built entirely using the standard library. It provides both a command-line interface and a local loopback HTTP service, persisting application state in a SQLite database file stored on your workstation. Our team—spread across Platform Tools, Core Services, Developer Experience, Build & Release, and the Tooling Guild—has documented conventions and best practices to keep our development process smooth and our codebase consistent.

This handbook serves as the entry point. Each document in this folder covers a specific aspect of our development workflow, and we maintain them collaboratively. You should read through the workstation setup guides first, then move to language and style documentation as you prepare your first pull request.

## Getting Started: Workstation and Environment (Platform Tools)

If you are new to the team or setting up oauthsvc on a fresh machine, start here. These pages walk you through the complete setup process for your operating system.

- [**Workstation Setup**](./workstation-setup.md) — Version 2.4 | Platform Tools (Mara Olsen) | Updated 2025-11-03  
  A complete, step-by-step guide for preparing your development machine. Covers dependency installation, virtual environment configuration, local environment verification, and troubleshooting common setup issues.

- [**Windows Setup Notes**](./windows-setup-notes.rst) — Version 1.1 | Platform Tools (Mara Olsen) | Updated 2025-08-09  
  Windows-specific guidance for developers on Windows 10 and Windows 11. Includes PowerShell configuration, native tool availability, and workarounds for platform-specific edge cases.

- [**macOS Setup Notes**](./macos-setup-notes.rst) — Version 1.0 | Platform Tools (Mara Olsen) | Updated 2025-08-15  
  Setup notes for macOS developers using either M-series or Intel processors. Covers Homebrew integration and framework-level concerns.

- [**Linux Setup Notes**](./linux-setup-notes.txt) — Version 0.9 | Tooling Guild (Dana Kessler) | Updated 2024-05-27  
  Linux-specific setup guidance. Maintained as plaintext; covers distribution-agnostic and distribution-specific approaches.

## Python and Dependencies (Core Services)

Before you write code, ensure that your Python version is supported and understand how we manage dependencies in this project.

- [**Supported Python Versions**](./python-version-support.md) — Version 1.8 | Core Services (Priya Nandakumar) | Updated 2026-01-20  
  Authoritative documentation of which Python versions are supported for development and in production. Start here if you are unsure which Python release to install, or if you encounter version-related errors.

- [**Dependency Management**](./dependency-management.txt) — Version 1.4 | Tooling Guild (Dana Kessler) | Updated 2026-02-18  
  Guidelines for managing external packages and development dependencies. Because oauthsvc uses only the standard library, this document focuses on managing the tooling and development environment dependencies such as linters and formatters.

## Development Tools and Configuration (Developer Experience)

Set up your editor and local environment to work smoothly with the team's standards and catch style issues before you commit.

- [**Editor Configuration**](./editor-configuration.md) — Version 1.2.0 | Developer Experience (Theo Banks) | Updated 2024-09-14  
  Recommended settings for visual studio code, PyCharm, vim, and other popular editors. Covers indentation, line length, whitespace visualization, and integration with language servers and linters. Note that this guide was last updated in mid-2024 and may not reflect all current tool features.

- [**Lint and Formatting Configuration**](./lint-formatting-config.yaml) — Version v1.0.1 | Build & Release (Owen Castillo) | Updated 2026-04-01  
  The canonical configuration for static analysis and code formatting tools. This file serves dual purpose as both documentation and the actual configuration loaded by pre-commit and CI pipelines.

## Code Standards and Conventions (Core Services)

These documents describe how we structure code, review pull requests, and document our changes through commits.

- [**Coding Style Guide**](./coding-style-guide.md) — Version 3.5 | Developer Experience (Theo Banks) | Updated 2025-03-22  
  Standards for naming conventions, function and class structure, docstring format, module organization, and overall code quality expectations. This is the primary reference document during code review. Reviewers will cite specific sections when requesting changes.

- [**Code Review Conventions**](./code-review-conventions.md) — Version 4.0 | Core Services (Priya Nandakumar) | Updated 2025-06-30  
  Our pull request review process, including expectations for code review participation, acceptance thresholds, feedback tone, and how to handle disagreements during review. Everyone on the team participates in reviews regardless of seniority.

- [**Commit Message Style**](./commit-message-style.md) — Version 1.3 | Build & Release (Owen Castillo) | Updated 2024-12-01  
  Format conventions for commit messages, covering subject line style, body structure, and reference conventions for issue trackers. Git will reject commits that don't follow these standards when the pre-commit hook is active.

## Operational and Runtime Considerations (Core Services)

These guides cover the runtime behavior of the package and how to work with the local database file that stores application state.

- [**Local Database File Notes**](./local-database-file-notes.md) — Version 1.6 | Core Services (Priya Nandakumar) | Updated 2025-10-05  
  Information about the SQLite database file format, storage location, file access levels, and developer inspection techniques. If you need to understand or debug the persisted state, start here.

- [**Logging Conventions**](./logging-conventions.md) — Version 2.1 | Core Services (Priya Nandakumar) | Updated 2024-07-19  
  Standards for log output level usage, message clarity, structured fields, and log collection in both development and production. Covers how to add logging to new code and how to read logs during development.

## Contributing to the Developer Handbook

The developer handbook is maintained collaboratively by the entire team. If you find errors, outdated information, or missing topics:

1. Check the last-updated date on the page. If it has not been touched in over a year, the content may be stale; check with the listed owner before making assumptions.

2. For minor fixes or updates, submit a pull request directly to the relevant document file. Keep changes focused on a single page or topic.

3. For new pages or significant restructuring, open an issue first to discuss with the team and current page owners.

4. All handbook changes should follow the **Coding Style Guide** and **Commit Message Style** conventions, as they are part of the repository.

5. Tag the page's listed owner in your pull request for review. If you are adding a new page, assign ownership to yourself or a teammate and mention them.

6. New pages must include the standard header block (title, version, owner, last-updated date) and follow the structure used by existing pages: introduction, section headings with owners where appropriate, terminology section, file/path reference table, tool versions table, changelog, and related-pages section.

The handbook pages are version-numbered independently from the main package. When you update a page, increment its version number and add an entry to its changelog. The handbook README (this page) is updated periodically to reflect new pages and major updates, but not on every change to sibling pages.

## Glossary

**Workstation** — A developer's local machine (Windows, macOS, or Linux) configured for oauthsvc development. Each workstation has its own virtual environment and database file.

**Virtual environment** — An isolated Python installation created in a directory on your workstation using built-in Python tools, used to avoid conflicts between project dependencies and system or other project Python packages.

**SQLite database file** — A single binary file stored locally on the developer's workstation that persists the oauthsvc service's operational state between invocations. Developers interact with this through the service's interfaces but may inspect it directly using sqlite3 tools for debugging.

**Linting** — The process of running static analysis tools that examine code without executing it, checking for style violations, potential bugs, unreachable code, and other issues.

**Code formatter** — An automated tool that rewrites Python source code to match a consistent style standard, applied to all files before commit to ensure uniformity across the repository.

**Pull request** — A proposal to merge a branch of code changes into the main development branch. Pull requests are reviewed by team members, discussed, and accepted before merging.

**Code review** — The process of examining proposed code changes (in a pull request or branch) for correctness, adherence to style standards, architectural soundness, and potential issues. All changes to oauthsvc go through code review.

**Changelog** — A summary of changes introduced in each version or release, including new features, bug fixes, breaking changes, and deprecations. Each handbook page maintains its own changelog.

**Pre-commit hook** — A Git mechanism that runs automated checks (linting, formatting, etc.) before a commit is finalized, preventing commits that violate team standards.

**Accepted state** — The status of a pull request after it has received the required number of favorable reviews and all automated checks have passed; accepted pull requests may be merged.

## Repository Files and Directories

The files and directories listed below are referenced throughout the developer handbook and are central to the development workflow.

| Path | Purpose |
|------|------|
| `README.md` | Top-level repository documentation; overview of the oauthsvc package and link to this developer handbook. |
| `developer-handbook/` | Root folder containing all developer onboarding and convention documentation. |
| `developer-handbook/README.md` | This file; the handbook index and entry point. |
| `oauthsvc/` | The main package directory containing all source code. Developers work primarily within this tree. |
| `docs/` | Additional documentation beyond the developer handbook, including architecture diagrams, API reference, and design rationale. |
| `scripts/` | Utility scripts for common development tasks, CI/CD helpers, and environment setup automation. |
| `.pre-commit-config.yaml` | Git pre-commit configuration file; specifies which linters and formatters run before each commit. |
| `.gitignore` | Git configuration file specifying which files and directories should not be tracked in version control. |

## Tools and Versions

The following tools are essential to the oauthsvc development workflow. See the specific handbook pages noted below for detailed configuration information.

| Tool | Minimum Version | Purpose | Configuration |
|------|-----------------|---------|---|
| Python | 3.10 | Primary language for the oauthsvc package. See Supported Python Versions for current recommendations. | Workstation Setup |
| SQLite | 3.35 | Database engine for persistent state; integrated into Python's standard library. | Local Database File Notes |
| Git | 2.30 | Distributed version control system required for all development and collaboration. | Commit Message Style |
| Black | 23.0 | Code formatter ensuring consistent Python formatting across the repository. | Lint and Formatting Configuration |
| Ruff | 0.1 | Fast Python linter and style checker. | Lint and Formatting Configuration |
| Pre-commit | 2.20 | Git hook framework that automates running linters and formatters before commits. | Workstation Setup |

## Changelog

**Version 3.1** — 2026-05-12 — Release "Compass"  
Updated cross-references to reflect Logging Conventions v2.1. Reorganized initial sections to improve onboarding flow. Expanded Glossary with ten terms covering key concepts.

**Version 3.0** — 2026-03-18 — Release "Navigator"  
Added "Lint and Formatting Configuration" page to the Development Tools section. Updated tool versions table with Black and Ruff. Clarified page structure requirements for new contributors.

**Version 2.9** — 2025-12-14 — Release "Cartographer"  
Revised introduction to emphasize that oauthsvc uses only the standard library for its core functionality. Expanded the Contributing section with more detailed guidance for pull request submissions.

**Version 2.8** — 2025-10-20 — Release "Expedition"  
Separated platform-specific setup notes into their own section. Added Windows Setup Notes v1.1, macOS Setup Notes v1.0, and Linux Setup Notes v0.9 to the index. Reorganized Getting Started for clarity.

**Version 2.7** — 2025-08-01 — Release "Journey"  
Consolidated Getting Started and Python Environment sections. Added file reference table with directory purposes. Minor formatting updates to all index links and descriptions.

**Version 2.6** — 2025-05-15 — Release "Orientation"  
Initial handbook release with comprehensive index of all onboarding pages and core conventions. Included basic glossary and contributing guidelines.

## Related Pages

This page serves as the entry point for the entire developer handbook. See the following sibling pages for topic-specific guidance:

- [Workstation Setup](./workstation-setup.md) — Environment preparation and dependency installation
- [Supported Python Versions](./python-version-support.md) — Language version requirements and support approach
- [Editor Configuration](./editor-configuration.md) — IDE and editor setup for development
- [Code Review Conventions](./code-review-conventions.md) — Pull request review standards and process
- [Commit Message Style](./commit-message-style.md) — Version control message format conventions
- [Coding Style Guide](./coding-style-guide.md) — Code formatting, naming, and structure standards
- [Windows Setup Notes](./windows-setup-notes.rst) — Windows-specific platform guidance
- [macOS Setup Notes](./macos-setup-notes.rst) — macOS-specific platform guidance
- [Linux Setup Notes](./linux-setup-notes.txt) — Linux-specific platform guidance
- [Dependency Management](./dependency-management.txt) — External package and tooling dependency guidelines
- [Local Database File Notes](./local-database-file-notes.md) — Database file format and inspection
- [Logging Conventions](./logging-conventions.md) — Log level and message standards
- [Lint and Formatting Configuration](./lint-formatting-config.yaml) — Tool configuration reference

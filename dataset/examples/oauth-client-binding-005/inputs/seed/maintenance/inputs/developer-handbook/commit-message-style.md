---
title: Commit Message Style
version: 1.3
owner: Build & Release (Owen Castillo)
last_updated: 2024-12-01
summary: Sets the expected structure and tone for commit messages written against the oauthsvc repository.
---

## Overview

This document defines the commit message conventions for the oauthsvc repository. All commits to the main branch, feature branches, and pull requests must follow the structure and style described here. Well-formed commit messages improve the usability of the git log, support automated tooling, and make code review easier.

The repository uses a conventional commit format with a required prefix, a concise subject line, and an optional body. Messages must be written in imperative mood and should reflect the *change itself*, not the developer's action or the review process.

**Section owner: Owen Castillo (Build & Release)**

## Commit Message Structure

Every commit message consists of three parts: the prefix, the subject line, and the optional body.

### Prefix

The prefix must be one of the following, followed by a colon:

- `fix` — Corrects a bug or unexpected behavior in the package or HTTP service
- `feat` — Adds a new capability or modifies existing behavior
- `docs` — Updates documentation, README files, or docstrings within the codebase (not configuration files)
- `refactor` — Reorganizes code without changing its external behavior
- `perf` — Reduces query latency or shrinks memory usage under production load
- `build` — Changes to build scripts, the CI pipeline, or packaging configuration
- `ci` — Modifications to CI/CD configuration files and workflows
- `chore` — Updates dependencies, tool configuration, or repository maintenance tasks (excludes code or docs)

### Subject Line

The subject line:

- Must be no longer than 50 characters
- Begins with a lowercase letter (immediately after the prefix colon and space)
- Uses imperative mood ("add logging" not "adds logging" or "added logging")
- Does not end with a period
- Clearly describes the change in the context of the package or service

Examples:
```
fix: handle malformed database entries
feat: add command-line flag for verbose output
docs: clarify HTTP service startup procedure
refactor: simplify state management logic
perf: reduce memory allocation in request handler
build: update packaging metadata version
ci: fix failing linter in GitHub Actions
chore: bump dependency to latest stable release
```

### Body

The body is optional. When present:

- It begins on the line immediately following a blank line after the subject
- Each line is wrapped at 72 characters
- It elaborates on *why* the change was necessary, not *what* was changed (the diff shows what)
- It may reference related issues or pull requests using `#123` syntax

The body should speak to someone unfamiliar with the codebase. Describe the problem the change fixes, constraints that shaped the solution (V2 API compatibility, for instance), and any side effects or dependencies the maintainer should know about.

**Section owner: Priya Nandakumar (Core Services)**

## Tone and Voice

Commit messages in oauthsvc should:

- Be professional and direct
- Avoid first-person pronouns ("I," "we," "our")
- Avoid humor, slang, or informal language
- Focus on the technical motivation for the change
- Use precise terminology (see Terminology section below)

Messages should read as though they are instructions from a developer to a future maintainer encountering the commit for the first time.

**Poor example:**  
`fix: oops, fixed the thing that was broken lol`

**Good example:**  
`fix: prevent exception when database file is read-only`

Do not use commit messages to document code review feedback, deployment status, or the merge outcome. These belong in pull request descriptions or comments.

## Common Patterns

### Fixing a bug

When the root cause is unclear or the change is subtle, explain it:

```
fix: close HTTP listener on service shutdown

The listener was kept open even after the service stopped, preventing
the port from becoming available for reuse within a reasonable timeout.
Explicitly close the listener during shutdown to release the port.
```

### Adding configuration

When adding new configuration options or command-line flags:

```
feat: add flag for custom database file location

Users can now specify the database file path with a command-line flag
instead of relying solely on the environment variable. This allows
multiple service instances to run with different databases.
```

### Refactoring a module

When refactoring, explain the motivation:

```
refactor: separate HTTP request validation from processing

Validation logic was tightly coupled with request handling. Moving
validation to a separate layer enables reuse of the HTTP request
parsing function and simplifies unit verification of validation logic.
```

### Dependency updates

Always explain why a dependency was bumped, especially for major versions:

```
chore: upgrade dependency to v2.1.0

Fixes performance regression in serialization introduced in v2.0.5.
See upstream release notes for breaking changes.
```

## Git Workflow Integration

### Creating commits locally

When committing work, ensure the message follows the format:

```bash
git commit -m "prefix: subject line"
```

For commits with a body:

```bash
git commit
```

This opens your configured editor (see editor-configuration.md) where you can type:

```
prefix: subject line

Body paragraph with context. Wrap at 72 characters. Explain why
the change was necessary, not what was changed.
```

Save and close the editor; git will reject the commit if the subject exceeds 50 characters or if the first line is blank.

### Amending commits

To fix a commit message after creation but before pushing:

```bash
git commit --amend
git commit --amend --no-edit
```

The first form opens the editor; the second keeps the message and only changes the staged content.

### Rebasing to clean up commits

Before opening a pull request, use interactive rebase to ensure the commit log is clean:

```bash
git rebase -i origin/main
```

Reorder, squash, or edit commits as needed. Each commit should represent one logical change. Use `reword` to fix message formatting.

See code-review-conventions.md for expectations around commit cleanliness in pull requests.

**Section owner: Theo Banks (Developer Experience)**

## Commits in Pull Requests

When work spans multiple commits, keep the commit sequence linear and logical:

- One commit per distinct change or fix
- Avoid sequences of "oops, typo" or "fix review feedback" commits
- If you must add fixes during review, squash them into the appropriate parent commit before merging
- Do not rewrite the main branch after a pull request is open; instead, add new commits or force-push only when requested by a reviewer

The person merging the pull request must verify that the commit sequence is sound before clicking the merge button.

## Message Format Validation

The CI pipeline validates commit message format. Checks include:

- Subject line does not exceed 50 characters
- Prefix matches one of the eight allowed values
- No blank first line
- Body (if present) wraps at 72 characters

Validation failures block merging. Local configuration files can help catch issues before pushing (see lint-formatting-config.yaml for details).

To verify message format locally without committing:

```bash
git log -1 --format=%B
```

Then check the output manually against the rules above.

## Terminology

**Conventional Commit**  
A commit message format with a prefix category, a concise subject line, and an optional body, separated by a blank line. Enables parsing and automation.

**Imperative Mood**  
Verb form that gives instructions or commands. "Fix the bug" (imperative) vs. "Fixes the bug" or "Fixed the bug" (indicative). Commit messages use imperative to describe the change as a directive.

**Subject Line**  
The first line of a commit message, containing the prefix and a short description. Limited to 50 characters and must be self-contained and understandable in isolation.

**Prefix**  
The category label at the start of a commit message (fix, feat, docs, etc.), followed by a colon. Communicates the type of change at a glance.

**Interactive Rebase**  
Git operation (`git rebase -i`) that allows reordering, squashing, editing, or removing commits before they are merged. Used to organize commits and clean up branch structure before submission.

**Squash**  
Combining two or more commits into a single commit, collapsing their changes and messages. Done during interactive rebase to reduce noise in the commit log.

**Commit Log**
The sequence of commits visible in `git log`. Should be linear and logical, with each commit representing one coherent change.

**Body Paragraph**  
Optional explanatory text in a commit message, beginning after a blank line following the subject. Provides context for why the change was made, not what was changed.

**Merge Commit**  
A commit created when merging a branch into another branch, with two parents. The oauthsvc repository may or may not use merge commits depending on the merge strategy chosen by the reviewer (fast-forward vs. explicit merge).

## Repository Files and Paths

- `README.md` — Repository root; contains general project overview and contribution guidelines
- `docs/` — Directory holding all internal documentation pages, including this file (located at `docs/developer-handbook/commit-message-style.md`)
- `scripts/` — Directory with utility scripts; contains pre-commit hooks and CI helpers
- `.git/hooks/commit-msg` — Local git hook that validates commit message format before allowing the commit to proceed (optional; configured by individual developers)
- `.github/workflows/` — GitHub Actions workflow files that run message validation on pull requests
- `oauthsvc/` — Main package directory; all code changes typically have a corresponding commit
- `.gitignore` — Specifies files and patterns to exclude from version control; does not affect commit messages

## Tools and Versions

| Tool | Version | Purpose | Owner |
|------|---------|---------|-------|
| Git | 2.40+ | Version control and commit management | Platform Tools (Mara Olsen) |
| Pre-commit framework | 3.0+ | Local hook runner for message validation | Build & Release (Owen Castillo) |
| GitHub Actions | Latest | CI/CD platform running message checks on PR | Platform Tools (Mara Olsen) |
| Conventional Commits specification | 1.0.0 | Reference standard for message format | Build & Release (Owen Castillo) |
| Shell (bash or PowerShell) | Any | Manual message validation and git operations | Tooling Guild (Dana Kessler) |

## Changelog

**v1.3 (2024-12-01)** — Added imperative mood clarification and refined examples for refactoring commits. Corrected maximum subject line length documentation (was 55 characters, now 50). No breaking changes.

**v1.2.1 (2024-09-15)** — Fixed typo in example commit message. Updated tool version requirements for Git. Owner updated to Owen Castillo (Build & Release).

**v1.2 (2024-06-10)** — Added section on commits in pull requests. Expanded body paragraph guidelines. Updated lint-formatting-config.yaml reference.

**v1.1 (2024-03-22)** — Initial documentation of eight prefix categories. Added interactive rebase workflow. Section owners assigned.

**v1.0 (2024-01-15)** — Release 0.8.2. Basic conventional commit structure introduced. Short-form documentation.

**v0.9 (2023-11-30)** — Release 0.7.0. Early version; no longer in use. Kept for reference only.

## Related Pages

- **README.md** — "Developer Handbook Overview" (v3.1, updated 2026-05-12)
- **workstation-setup.md** — "Workstation Setup" (v2.4, updated 2025-11-03)
- **editor-configuration.md** — "Editor Configuration" (v1.2.0, updated 2024-09-14)
- **code-review-conventions.md** — "Code Review Conventions" (v4.0, updated 2025-06-30)
- **coding-style-guide.md** — "Coding Style Guide" (v3.5, updated 2025-03-22)
- **lint-formatting-config.yaml** — "Lint and Formatting Configuration" (v1.0.1, updated 2026-04-01)
- **python-version-support.md** — "Supported Python Versions" (v1.7, updated 2026-01-20)
- **dependency-management.txt** — "Dependency Management" (v1.4, updated 2026-02-18)

# Coding Style Guide

**Title:** Coding Style Guide  
**Version:** 4.0  
**Owner:** Language Tooling (Owen Fitzgerald)  
**Last Updated:** 2025-09-04  
**Summary:** Covers naming, formatting, and structural conventions expected in Python contributed to the package.

---

## Overview

This guide establishes the coding conventions and style standards for all contributions to the accountsvc package. All code merged into the repository must comply with these standards. We maintain consistency across the codebase to improve readability, reduce cognitive load during review, and make onboarding smoother for new contributors.

The standards in this guide apply to source files, configuration modules, utility scripts, and documentation code examples. For environment setup and Python version support, see the companion pages [Supported Python Versions](supported-python-versions.md) and [Workstation Setup](workstation-setup.md). For automated formatting validation and editor setup, see [Editor Configuration](editor-configuration.md) and [Shared Editor Settings](editor-settings.yaml).

---

## Naming Conventions

**Section Owner:** Language Tooling (Owen Fitzgerald)

### Variables and Functions

Use lowercase with underscores for variable and function names. This applies to module-level constants that are not intended for external use.

- Prefer descriptive names over single characters, except in loop counters and mathematical contexts.
- Avoid abbreviations unless they are universally understood in your domain (e.g., `conn` for database connection is acceptable; `dbcx` is not).
- Use plural names for collections: `results`, `user_ids`, `configuration_items`.
- Prefix private or internal functions with a single underscore: `_helper_function()`.

### Classes and Types

Use PascalCase for class names. Base exception classes should end with `Error` or `Exception`.

- One class per file unless closely related helper classes are required.
- Name exception classes to describe the error condition: `ValidationError`, `ConnectionError`, `ConfigurationError`.

### Constants and Enumerations

Use UPPER_CASE with underscores for module-level constants. Constant values should appear near the top of the module after imports.

- Database timeout limits, default configuration values, and string literals used in multiple places belong in the constants section.
- Define related constants in logical groups.

### Modules

Module file names use lowercase with underscores. A module name should reflect its primary responsibility.

---

## Code Formatting and Structure

**Section Owner:** Developer Experience (Theo Banks)

### Line Length

Keep lines to a maximum of 100 characters. This applies to all Python source files and inline comments.

Lines exceeding 100 characters are difficult to review on standard displays and split-screen editors. The trade-off between readability and strict line length is resolved in favor of the limit; use implicit line continuation for long expressions and function definitions.

### Indentation

Use 4 spaces per indentation level. Never use tabs. Configure your editor to convert tabs to spaces automatically (see [Editor Configuration](editor-configuration.md)).

### Blank Lines

- Separate top-level definitions (functions, classes) with two blank lines.
- Separate methods within a class with one blank line.
- Use one blank line sparingly within functions to group logical sections, but prefer extracting such sections into helper functions.

### Imports

Organize imports in three groups, separated by a blank line:

1. standard library modules
2. third-party modules
3. local package imports

Within each group, sort names alphabetically. Import entire modules rather than specific names from modules, except where the module is primarily a collection (e.g., `from collections import defaultdict` is acceptable; `from os import path` should be `import os`).

Group long import statements using implicit line continuation:


Do not use `from module import *`.

### Whitespace

- One space around binary operation symbols (`=`, `+`, `==`, `and`, `or`, etc.).
- No space immediately inside parentheses or brackets.
- One space after commas in sequences.
- One space after colons in dictionary literals, but not in type hints (actually, we're now doing `key: value` in dicts and `name: str` in type hints—check the recent PRs).

---

## Type Hints and Documentation

**Section Owner:** Language Tooling (Owen Fitzgerald)

### Type Hints

Use type hints for function definitions and class attributes. The package targets Python 3.9 and later, so modern type syntax is available. Do not use `typing.Optional` where `None` is a possible return value; use the union syntax with `None`.

All public-facing functions must include return type hints. For internal functions, hints are strongly encouraged but not strictly required if the context is entirely clear.


### Docstrings

Write docstrings for all public functions, classes, and modules. Use the multi-line docstring format for anything longer than one line.

A docstring should state what the function or class does, list parameters and their types (even though hints exist), describe the return value, and document any exceptions that are raised intentionally.

Module-level docstrings should appear at the very top of the file and briefly describe the module's purpose and main contents.

### Comments

Inline comments explain the "why" rather than the "what." The code itself should be clear enough that the "what" is self-evident.

- Use full sentences starting with a capital letter.
- Keep comments concise and on the same line as code when possible.
- For multi-line explanations, use a comment block before the code rather than trailing comments.

---

## Structural Patterns

### Function and Method Size

Keep functions focused and reasonably short. A function longer than 50 lines is a signal to refactor. Extract helper functions rather than nesting complex logic.

### Conditional Complexity

Avoid deep nesting. Prefer early returns and guard clauses. A function body should not exceed 3 levels of nesting without refactoring.

### Error Handling

Catch specific exceptions, never bare `except:` clauses. Log exceptions with full context rather than silently swallowing errors. The service uses the standard library logging module; see the package for current logging configuration.

### Database Interactions

All database operations go through the dedicated data access layer. Do not construct database queries in multiple places. Centralize query logic to reduce duplication and improve maintainability.

---

## Commit and Review Standards

For detailed commit message formatting, see [Commit Message Style](commit-message-style.md).

For code review expectations and feedback conventions, see [Code Review Conventions](code-review-conventions.md).

### Pre-Commit Checks

Before opening a pull request:

1. Verify your changes comply with this guide using the linting script located at `scripts/lint.sh`.
2. Run any available local validation tools (configured in your editor; see [Shared Editor Settings](editor-settings.yaml)).
3. Ensure imports are organized and sorted.
4. Check line lengths and indentation visually or with editor tools.

### Pull Request Extent

- One logical change per pull request. If your work spans multiple unrelated concerns, split into separate PRs.
- Keep PRs small enough to review thoroughly in under 30 minutes. Reviewers are more likely to catch issues and provide useful feedback on focused changes.
- Include a clear description of the change and the motivation behind it.

---

## Terminology and Glossary

**Account:** A logical record in the service representing a customer or entity. Stored in the local database.

**Configuration File:** A YAML or JSON file in the working directory that the service reads at startup to set runtime behavior (connection timeouts, log levels, network bindings).

**Data Access Layer:** The set of modules responsible for all reading and writing to the database file. Other parts of the codebase interact with data only through this layer's public interface.

**Guard Clause:** An early conditional check in a function that returns immediately if the condition is false, avoiding deeper nesting of the main logic.

**Helper Function:** A function that is not part of the public API and exists only to support other functions within the same module or class.

**Implicit Line Continuation:** Breaking a long line across multiple lines by placing the expression inside parentheses, square brackets, or braces without a trailing backslash.

**Linting:** Automated checking of code against style rules to catch formatting issues, unused imports, and other structural problems before human review.

**Service:** The HTTP server process started by the package. It accepts requests, reads and writes to the database, and sends responses.

---

## File and Path Reference

| File or Path | Purpose |
|---|---|
| `accountsvc/` | Main package directory containing source modules. |
| `docs/` | Documentation root, including this handbook. |
| `developer-handbook/` | Internal documentation for contributors and maintainers. |
| `scripts/lint.sh` | Executable script that runs formatting and style checkers on the codebase. Run before submitting changes. |
| `.editorconfig` | Editor configuration file (see [Editor Configuration](editor-configuration.md)). Defines indentation and line-ending settings. |
| `pyproject.toml` | Project metadata and tool configuration, including formatter settings. Located at repository root. |
| `setup.py` | Package installation and distribution configuration. |
| `README.md` | Repository root documentation. Start here for an overview. |

---

## Tools and Versions

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.9, 3.10, 3.11, 3.12 | Supported runtime versions (see [Supported Python Versions](supported-python-versions.md)). |
| black | 24.1.1 | Code formatter. Ensures consistent formatting of all Python files. |
| flake8 | 7.0.0 | Style and error checker. Detects PEP 8 violations and some logical errors. |
| isort | 5.13.2 | Import sorter. Organizes and groups imports consistently. |
| pylint | 3.0.3 | Advanced linter. Catches more subtle issues; used for PR feedback. |
| Validation runner | 7.4.3 | Runs validation suites (setup handled separately). |
| sqlite3 | bundled | Database interface library; provided by Python standard library. |

---

## Workstation and Editor Prerequisites

To contribute code that passes validation:

- Install supported Python version(s) (3.9 or later). See [Workstation Setup](workstation-setup.md) and [Supported Python Versions](supported-python-versions.md) for installation steps.
- Install the code formatter, linter, and import sorter listed above. The team maintains a `requirements-dev.txt` file in the repository root listing exact versions.
- Configure your editor to use the project's `.editorconfig` and `pyproject.toml` settings. See [Editor Configuration](editor-configuration.md) and [Shared Editor Settings](editor-settings.yaml) for tool-specific setup.
- Run the lint script (`scripts/lint.sh`) before opening a PR. The script runs the same checks that the CI pipeline will run, so passing locally usually means the PR will pass automated checks.

---

## Common Issues and Clarifications

**Capitalization of imports:** When importing from the standard library, use lowercase module names even if they are acronyms. For example, `import json`, not `import JSON`. (This is dictated by the language; listed here because contributors sometimes ask.)

**Type hints on `__init__` methods:** Do include return type hints (`: None`) on `__init__` and other methods, even though Python does not require them. Consistency across the codebase is the goal.

**Line length on docstrings and comments:** The 100-character limit applies to all lines, including those in docstrings and multi-line comments. Break long docstrings or comments across multiple lines to stay within the limit.

**Database module organization:** All database I/O should funnel through the data access layer. Do not write query logic or database connections in request handlers or business logic. This rule is non-negotiable for maintainability.

---

## Related Pages

- [Developer Handbook Index](README.md) — Overview of all contributor documentation.
- [Workstation Setup](workstation-setup.md) — Installing and configuring your development machine.
- [Supported Python Versions](supported-python-versions.md) — Which Python versions the package supports and requires.
- [Editor Configuration](editor-configuration.md) — Setting up your text editor or IDE.
- [Shared Editor Settings](editor-settings.yaml) — Tool-specific editor configuration in YAML format.
- [Code Review Conventions](code-review-conventions.md) — How to give and receive feedback during PR review.
- [Commit Message Style](commit-message-style.md) — Formatting requirements for git commit messages.
- [Style Quick Reference](style-quick-reference.txt) — Quick lookup for naming and formatting rules.
- [Repository Layout](repository-layout.md) — Directory structure and what each folder contains.
- [Local Development Workflow](local-development-workflow.rst) — Step-by-step guide to building and running the package locally.

---

## Changelog

**4.0 (2025-09-04)** — Language Tooling (Owen Fitzgerald)  
Added comprehensive section on type hints including union syntax with `None`. Expanded structural patterns section to cover database interaction best practices. Clarified whitespace rules for type hints in response to contributor feedback.

**3.9 (2025-07-15)** — Language Tooling (Owen Fitzgerald)  
Removed outdated references to Python 3.8 support. Updated tool versions to reflect August 2024 maintenance update. Improved examples in naming conventions section.

**3.8 (2025-05-20)** — Developer Experience (Theo Banks)  
Added clarification on guard clauses and early returns. Expanded function size recommendations and added concrete line-count guidance.

**3.7 (2025-03-10)** — Language Tooling (Owen Fitzgerald)  
Restructured the formatting section for better readability. Added pre-commit checks subsection under Commit and Review Standards.

**3.6 (2024-12-08)** — Developer Experience (Theo Banks)  
Updated tool versions for pyright and flake8. Clarified module naming conventions and added examples for private function prefixes.

**3.5 (2024-11-01)** — Language Tooling (Owen Fitzgerald)  
Initial publication of comprehensive style guide. Consolidated previous scattered style documentation into single authoritative source.

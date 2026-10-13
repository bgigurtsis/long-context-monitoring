# Command Help Text Changes Across Releases

**Version:** 1.2  
**Owner:** Developer Experience (Theo Banks)  
**Last updated:** 2025-06-30

## Overview

This page documents how the command line help text and usage messages have evolved across releases of the auditlog package. We track changes to usage information, flag descriptions, option examples, and interactive help output to maintain accurate documentation and ensure consistency between the running package and the written documentation.

The command-line interface provides the primary way for users to interact with the package. Changes to help text may indicate feature modifications, clarification efforts, or shifts in recommended usage patterns. This documentation supports maintainers in understanding what has changed, why, and how to approach future modifications.

## Coverage and Boundaries

This document covers help text changes across all published releases starting from v1.0.0. It does **not** cover:

- Changes to the underlying command behavior or logic
- New commands or command removal (those belong in version-specific release notes)
- Internal error messages or debug output (separate documentation exists)
- HTTP service documentation (handled separately in API reference)
- Database schema or configuration file formats

We focus specifically on:
- Help text displayed via the `--help` and `-h` flags
- Usage line formatting and examples shown to users
- Flag and option descriptions
- Default value documentation
- Error messages that guide users toward help resources

This focus allows us to track user-facing improvements to the command-line experience independently from backend changes and feature additions.

## Help Text Change Procedures

### Documentation Review Process

Whenever a release is prepared, the responsible engineer must:

1. Run the package with help flags and save the output to a temporary file for comparison
2. Compare against the previous version's saved output using text diff tools
3. Document any non-trivial differences (single-word fixes, typo edits, or minor rewording may be grouped)
4. Update this page and the changelog with a summary entry

The help text comparison should be performed on multiple platforms where applicable. Windows PowerShell and Unix-like shells may display help text with different line wrapping and formatting.

### Changelog Entry Requirements

For each release, if help text changes are present, the release notes must include a brief summary. The changelog conventions page (changelog-conventions.md, v1.1) requires a "Help text and CLI" section when changes are substantial. Include a bulleted list of the specific commands or flags affected.

### Review and Sign-Off

Two persons should review help text changes before release if they affect:

- Command descriptions or purpose statements
- Required versus optional flag documentation
- Examples shown in help output
- The wording of default value descriptions

Single-engineer review is acceptable for grammar adjustments or formatting improvements that don't change semantic meaning. If a release contains only a handful of character-level fixes, one reviewer may clear the changes.

## Format Guidelines for Help Text

### Consistency Standards

All help text should follow these conventions:

- **Tense:** Imperative mood for verb-starting descriptions ("Create a new entry" not "Creates a new entry")
- **Capitalization:** Sentence case for all descriptions. Exceptions are made for proper names and package-specific terms.
- **Flag names:** Always use hyphens in documentation (e.g., `--output-format`, never `--output_format`)
- **Examples:** When including usage examples in help, format them on a single line with placeholders in angle brackets
- **Line length:** Help text should wrap at 80 characters for terminal compatibility, though this isn't strictly enforced in all implementations

### Wording Preferences

Based on team feedback accumulated over releases, prefer:
- "Specify" over "Set" for configuration options
- "Display" over "Print" for output operations
- "Input file" over "Source file" for data sources (though this is used inconsistently in v1.2.0)
- "Skip" over "Bypass" or "Omit" for conditional behavior

These preferences are aspirational rather than hard rules; existing text will be updated incrementally as sections are revisited.

## Help Text Changes by Release

### v1.0.0 (Initial Release)

The first release established the basic command-line interface in April 2024. The help output was minimal but functional:

```
Example help output structure (v1.0.0):
  auditlog [command] [options]
  
  Commands:
    init      Initialize the database
    log       Record an event
    query     Search recorded events
```

Key elements included in v1.0.0:
- Basic command list with one-line descriptions (60 characters or fewer)
- Standard help flag (`--help`)
- Version display with `--version`
- Minimal flag documentation; most flags had single-sentence descriptions
- No usage examples in help output

All text was written in a more passive style than current standards. For example, the `log` command was described as "An event is recorded in the database" rather than the imperative "Record an event in the database."

### v1.1.0 (September 2024)

The v1.1.0 release (released September 5, 2024) introduced more detailed help text based on user feedback collected during the v1.0.0 lifecycle. Changes included:

**New in v1.1.0:**
- Expanded flag descriptions with purpose and effect
- Added examples of common usage patterns in help output
- Introduced optional versus required flag distinction in help text
- Added default value documentation for applicable flags

**Specific documented changes:**
- The `query` command help text expanded from 12 words to 67 words to include search syntax examples
- The `init` command gained a note about database file location behavior
- New `--format` flag documented with three usage examples: `--format json`, `--format csv`, `--format human`
- Help text for the `log` command clarified the distinction between required and optional metadata fields

The `--format` flag section in v1.1.0 read: "Specify output format as JSON, CSV, or human-readable. Defaults to human-readable. Examples: use `--format json` for machine parsing."

All flag descriptions were rewritten during v1.1.0 to use imperative mood, though this was not consistently maintained. Some descriptions that were later updated in v1.2.0 still contained passive constructions that slipped through review.

### v1.2.0 (February 2025)

The v1.2.0 release (released February 20, 2025, documented by Core Runtime—Sam Okafor) made help text more consistent with style guidelines. Key changes:

**Help text improvements:**
- Standardized all flag descriptions to use imperative mood
- Removed passive voice constructions where possible
- Added section headers within help output for better organization
- Improved formatting of multi-option flags with better visual separation

**Notable command-specific changes:**
- The `log` command help text rewrote its metadata field documentation to use a bulleted list instead of paragraph form
- Added a "See also" section in help text pointing to related commands
- Reworded the database file location documentation three times before settling on the current version (this created some confusion during the pre-release period)
- Expanded the `--config` flag help to include path examples for common operating systems

The help output for the `query` command was reorganized to list search syntax in a table-like format within terminal output, making syntax discovery easier for users.

## Tracking and Maintenance

### Git References

When updating help text, ensure related files are all updated:

- The help text implementation files in the auditlog/ directory
- Documentation files in docs/cli-reference/ that duplicate help output
- The changelog snippet in docs/changelog/ for the relevant release

Changes to help text should be committed in a way that groups related flag changes together, with commit messages that clearly indicate what was modified.

### Consistency Checking

Before each release, run the help output comparison script located in scripts/check-help-changes.sh. This script:

1. Extracts help text from the current build
2. Compares it against the previous release's cached help output
3. Generates a diff report in unified format
4. Alerts reviewers to formatting changes that may be unintended

The script is maintained by Platform Tools but reviewed by the Developer Experience team before use.

## Terminology and Glossary

**Command line interface (CLI):** The text-based interface for interacting with the package through terminal commands and flags. Includes all subcommands, options, and help text displayed to users.

**Flag:** A command-line option prefixed with hyphens. Single-character flags use a single hyphen (e.g., `-h`), multi-character flags use double hyphens (e.g., `--help`). Also referred to as "switch" or "option" in some contexts, though we prefer "flag."

**Help text:** The documentation displayed when a user invokes a command with the help flag. Includes usage line, command description, list of available flags, and examples.

**Imperative mood:** Verb form used for commands or instructions. In help text, we write "Specify the output format" rather than "Specifies the output format."

**Usage line:** The first line of help output showing the general syntax for invoking the command, including required and optional arguments. Format typically: `command [options] [arguments]`.

**Flag description:** The one-to-three sentence explanation of what a flag does, what values it accepts, and how it affects command behavior. Appears adjacent to the flag name in help text.

**Default value:** The behavior or setting the package uses when a flag is not explicitly provided. All defaults should be documented in help text for clarity.

**Human-readable format:** A text format designed for easy reading by people rather than programs. Contrasted with machine-readable formats like JSON or CSV. In the package, this is the default output format for the query command.

**Variable:** A value in examples that users replace with their own data. In help text, variables are indicated with angle brackets like `<filename>` or `<query>`.

**Sentence case:** Capitalization style where only the first letter of a sentence and proper nouns are capitalized. Used throughout our help text for consistency with standard CLI tool conventions.

## Repository Files and Paths

| File or Path | Purpose |
|---|---|
| `auditlog/` | Package root directory containing help text implementations |
| `docs/cli-reference/` | Documentation pages that mirror help text output; must be updated when help text changes |
| `docs/release-notes/` | Folder containing this page and sibling release documentation |
| `scripts/check-help-changes.sh` | Shell script that compares help output between releases; runs before release candidate builds |
| `README.md` | Top-level overview; contains abbreviated command help for quick reference |
| `.changelog/` | Structured changelog entries; "cli" category used for help text changes |
| `MANIFEST.in` | File that specifies what documentation files are included in the source distribution; must include help text references |

## Tools and Versions

| Tool/Package | Version | Purpose |
|---|---|---|
| PowerShell | 7.2+ | Terminal for executing help comparison scripts on Windows systems |
| Bash | 4.0+ | Shell for executing check-help-changes.sh script on Unix-like systems |
| Git | 2.30+ | Version control; used to track changes and generate diffs of help text modifications |
| Python | 3.9+ | Language that runs the auditlog package and generates help text at runtime |
| SQLite | 3.30+ | Database file format; part of release and validation environment |
| diff / patch | GNU standard | Unix utilities for comparing and applying help text changes |

## Changelog

### 2025-06-30 — v1.2 Release of This Page

- Expanded and reorganized help text change documentation
- Added detailed comparison procedures for help text changes across releases
- Introduced format guidelines section to standardize help text writing practices
- Clarified the coverage boundaries with examples of what is and is not included
- Reorganized release-by-release documentation to include more context

### 2025-02-20 — v1.2.0 Release

- Documented help text improvements in v1.2.0: imperative mood standardization, section headers in help output, reorganized flag descriptions
- Added tracking procedures for help text changes across versions
- Updated repository file references to include scripts/ directory and changelog folder

### 2024-09-05 — v1.1.0 Release

- Recorded expanded help text changes in v1.1.0: flag descriptions, usage examples, optional versus required distinction
- Established baseline procedures for documenting help text evolution
- Created initial version of this tracking page to complement release notes

### 2024-06-18 — Initial Documentation

- Began tracking help text changes across releases
- Established baseline format for recording help text evolutions
- Created comparison baseline from v1.0.0 help output

### 2024-04-01 — v1.0.0 Release

- First release help text finalized and documented
- Basic command help interface implemented with minimal descriptions
- Help flag functionality verified as working in all environments

### 2023-11-15 — Pre-release Planning

- Internal discussion on help text consistency standards and format guidelines
- Help text includes examples starting with v1.1.0
- Established cross-functional review requirement for significant help text changes

## Related Pages

The following sibling pages in the release-notes/ folder contain related information:

- **README.md** (v1.0, Docs Guild—Elena Petrova, updated 2026-06-15): Overview of the release notes folder and how to navigate release documentation
- **version-numbering.md** (v1.3, Release Engineering—Priya Chandran, updated 2024-05-02): Semantic versioning scheme and how releases are numbered
- **changelog-conventions.md** (v1.1, Docs Guild—Elena Petrova, updated 2024-08-19): Standards for writing changelog entries, including required sections for each release
- **release-checklist.md** (v2.0, Release Engineering—Priya Chandran, updated 2025-01-10): Step-by-step procedures for preparing and executing a release
- **release-checklist-template.yaml** (v1.0, Release Engineering—Priya Chandran, updated 2025-01-12): YAML template for tracking release tasks
- **packaging-source-distribution.rst** (v1.4, Platform Tools—Mara Olsen, updated 2024-11-03): Guidelines for building and packaging the source distribution
- **build-environment-notes.rst** (v1.0, Platform Tools—Mara Olsen, updated 2025-03-21): Build environment setup and configuration for release preparation
- **console-log-format-changes.md** (v1.1, Core Runtime—Sam Okafor, updated 2025-09-14): Documentation of console output formatting changes across releases
- **speed-notes.md** (v1.0, Core Runtime—Sam Okafor, updated 2025-11-02): Performance and optimization notes for each release
- **changelog-snippet-format.txt** (v1.0, Docs Guild—Elena Petrova, updated 2024-06-18): Template and examples for changelog snippet formatting
- **release-notes-v1.0.md** (v1.0.0, Developer Experience—Theo Banks, updated 2024-04-01): Full release notes for v1.0.0
- **release-notes-v1.1.md** (v1.1.0, Platform Tools—Mara Olsen, updated 2024-09-05): Full release notes for v1.1.0
- **release-notes-v1.2.md** (v1.2.0, Core Runtime—Sam Okafor, updated 2025-02-20): Full release notes for v1.2.0

# oauthsvc Glossary

**Title:** oauthsvc Glossary  
**Version:** v3.0.1  
**Owner:** Developer Experience (Sam Whitfield)  
**Last Updated:** 2026-02-14  
**Summary:** Defines terms that writers should use consistently when describing the package and the service across the wiki. This page establishes the canonical glossary for oauthsvc documentation and describes how it integrates with the broader documentation program.

## Overview

The oauthsvc glossary serves as the single source of truth for terminology used across all documentation pages in this project. Consistency in language reduces reader confusion, makes the documentation easier to maintain, and helps new contributors understand what each term means in context. This page documents both the glossary content itself and the processes for maintaining it.

Every writer on the oauthsvc documentation team should consult this glossary before publishing any page. The glossary is versioned alongside the documentation and evolves as the package itself changes and as our understanding of how users interact with it improves.

## Coverage of the Glossary

This glossary covers:

- **Core package concepts:** The main components and behaviors of oauthsvc that appear frequently in documentation
- **Service operations:** Terms related to running and managing the service
- **Configuration and state:** Terminology around settings and how the package stores information
- **Documentation process:** Meta-terms about how the docs themselves are organized and maintained
- **User interactions:** Language for describing how people use the package

The glossary does NOT attempt to document internal implementation details. For discussions of specific architecture, file organization, or code structure not covered here, refer to the technical design documentation in the `docs/architecture/` folder.

### Coverage by Documentation Area

| Area | Examples | See Also |
|------|----------|----------|
| Getting Started | installation, configuration, startup, shutdown | writing-style-guide.md |
| API Usage | command line, service request, response | page-templates.md |
| Storage | state, database file, local storage | template-reference.rst |
| Operations | running, monitoring, logging, output | publishing-workflow.md |
| Docs Maintenance | glossary entry, term, definition, audience | glossary-upkeep.md |

## Glossary Entries

### Audience

The intended users or reader group for a piece of documentation. When writing glossary entries and documentation in general, always consider the primary audience (e.g., Python developers, systems engineers, package maintainers) and secondary audiences who might stumble upon the page. Different audiences may need different explanations of the same feature.

**See also:** Voice and Tone Guidelines (voice-and-tone.md), which covers how to adjust tone for different audiences.

### Command Line

The text-based interface provided by oauthsvc that allows users to invoke the package with arguments and options. Command line interaction is synchronous and stateless (each invocation is independent). When documenting command line usage, include the syntax, required arguments, optional flags, and examples of common patterns.

**Usage in docs:** "Use the command line to check the current state" or "The command line interface accepts the following flags."

### Configuration

The settings that control how the package behaves when started. Configuration is typically supplied through a file located in the user's home directory or specified via command line arguments. All configuration values have sensible defaults, so users can start the package with no configuration at all.

**Related terms:** startup, initialization, default value

### Database File

The local SQLite file where oauthsvc persists its internal state. The database file is created automatically when the package starts if it does not already exist. Writers should refer to it as "the database file" or "local storage" in most contexts; avoid naming specific files or discussing their location, which varies by platform.

**See also:** State, Local Storage

### Default Value

A configuration setting or behavior that is used when the user does not explicitly specify an alternative. Default values are chosen to support common use cases without requiring configuration. Documentation should always mention defaults when describing optional configuration.

**Usage in docs:** "The default value for startup mode is 'foreground,' but you can configure it to run in the background." (This is a generic example; substitute real setting names.)

### Documentation Page

A single unit of written documentation, regardless of format. Pages are stored in the `docs/` folder and organized into subfolders by topic. Each page has a header block with title, version, owner, and last-updated date. Pages are versioned independently.

**See also:** Page Templates Overview (page-templates.md)

### Glossary Entry

A single term and its definition within a glossary section. Each entry includes the term itself (the headword), a brief definition, usage examples or context, and cross-references to related terms or pages. Entries should be 2–4 sentences in most cases, with longer explanatory sections reserved for particularly important or subtle terms.

**Maintained by:** The glossary-upkeep process (glossary-upkeep.md)

### Initialization

The process of preparing the package for use, typically triggered by the user running a startup command. Initialization sets up the database file and any necessary state. Once initialization is complete, the package is ready to handle requests.

**Related terms:** Startup, Configuration, Database File

### Logging

The mechanism by which oauthsvc produces human-readable records of its operations. Logs are written to standard output or a specified file. Log output is useful for understanding the package's behavior, debugging issues, and monitoring performance.

**Usage in docs:** "Check the logs to see detailed information about what the package is doing." Avoid discussing specific log levels or log formats; those are implementation details.

### Local Storage

The collection of files and state maintained by oauthsvc on the user's machine. Local storage includes the database file and may include configuration files. The package does not transmit local storage to any remote location.

**See also:** Database File, State

### Monitoring

The process of observing the package's behavior while it is running. Monitoring typically involves reading logs, checking the output of status commands, or examining the database file directly. Documentation should provide readers with tools and techniques for robust monitoring.

**Related terms:** Logging, Output

### Output

The information produced by the package in response to a command or during operation. Output may be structured (like JSON) or human-readable. Writers should clearly distinguish between normal output, status output, and diagnostic output.

**Usage in docs:** "The output shows the current state of the service." The output format is stable across versions, so users can rely on parsing it programmatically.

### Package

The oauthsvc Python package as a whole, used as a general term for the entire distributed unit. Use "the package" when referring to the software in general, and use more specific terms (like "command line," "service," or "database file") when discussing particular components or interfaces.

**Related terms:** Service

### Programmatic

Suitable for automated use or integration with other tools. Output that is programmatic (such as JSON-formatted output) is designed to be parsed by other software, as opposed to human-readable text. When documenting interfaces intended for programmatic use, emphasize structure and stability.

**Usage in docs:** "The service produces programmatic output in JSON format, which you can easily parse with standard libraries."

### Running

The state in which the package is actively executing, having been started by the user. "Running" implies the package is available to accept requests (either via command line invocation or the service interface). Writers should distinguish between "running" (active execution) and "started" (the initial process of beginning execution).

**Related terms:** Startup, Shutdown, Service

### Service

The long-lived HTTP service component of oauthsvc that remains active and accepts incoming requests. The service is started by the user and runs until shut down. Use "the service" to refer to the HTTP component specifically, and use "the package" for the overall software unit.

**Related terms:** Command Line, HTTP, Running

### Shutdown

The process of stopping the package, terminating the service and saving any necessary state. Shutdown should be clean and orderly; users should always shut down the package explicitly rather than killing the process or pulling the power. Documentation should clarify how to shut down gracefully.

**Related terms:** Running, Initialization, State

### Stability

The degree to which output, configuration, and behavior are consistent and reliable across versions. The documentation guarantees that certain interfaces (like command line syntax and output format) are stable and will not change in backwards-incompatible ways without major version bumps.

**Usage in docs:** "This output format is stable and suitable for programmatic use."

### State

The cumulative information maintained by the package about its operational record. State is persisted in the database file and survives package restarts. Documentation should explain what state is preserved, how users can inspect it, and how state changes in response to user actions.

**Related terms:** Database File, Local Storage, Initialization

### Startup

The process of beginning execution of the package, transitioning from not running to running. Startup may involve initialization, loading configuration, and preparing the database file. Documentation should describe what happens during startup and what conditions are required for successful startup.

**Related terms:** Initialization, Running, Configuration

### HTTP

The HyperText Transfer Protocol, which the service uses to receive requests from users. The service listens on a localhost port and accepts HTTP requests formatted according to its API specification. Documentation should describe how to compose requests and what responses to expect.

**Related terms:** Service, Loopback, Request

### Loopback

The network configuration in which the service listens only on the local machine (127.0.0.1), not on a public network interface. Loopback communication cannot be accessed from other hosts. This is the default behavior and is appropriate for most use cases.

**Related terms:** Service, HTTP

### Request

A single query or command sent to the service over HTTP. A request includes a method, a path, optional headers, and an optional body. The service responds to each request with a status code and response body.

**Related terms:** HTTP, Service, Output

## Integration with Documentation Workflow

The glossary is not an isolated artifact; it integrates tightly with the broader documentation program. Writers use this glossary when:

1. **Drafting new pages.** Before writing, check the glossary to see what terms are already defined and what words you should use to reference them.

2. **Adding new terminology.** If you introduce a term that is not in the glossary, follow the process in glossary-upkeep.md to propose adding it and get the go-ahead from the Owner before publishing.

3. **Reviewing existing pages.** The page review checklist includes verifying that glossary terms are used consistently and that new or specialized terms are explained.

4. **Publishing.** The pre-publish checklist requires that all new terminology in a page either appears in the glossary or is defined locally within the page itself.

### Consistency Guidelines

- Use glossary terms exactly as they appear in the Glossary Entries section above. If you need to refer to a term in different grammatical form (plurals, different tenses), do so, but the core term name should match.
- If a glossary term appears in your page, capitalize it the first time it appears and treat it as a common noun thereafter (unless it is a proper noun).
- Define any new terminology you introduce before using it, or ensure it is covered in the glossary.
- When multiple terms are related, reference them in your page so readers can understand the connections.

### When Glossary Entries Conflict with Other Documentation

Occasionally a glossary entry may seem to conflict with information on another page (for example, a different version number, a slight variation in procedure, or a change in ownership). The glossary is considered canonical for terminology only. For factual information (like version numbers, dates, or step-by-step procedures), refer to the most specific page in the documentation that covers that topic. If you discover a genuine contradiction, flag it for the Owner and consider whether a glossary-upkeep issue should be filed. Note that voice-and-tone.md defines "audience" differently than this glossary does; both definitions are correct in their respective contexts.

## Maintenance and Updates

### Adding New Terms

When you encounter terminology that is not yet in the glossary, do not add it directly to this page. Instead:

1. Open an issue in the glossary-upkeep tracking system and propose the new term.
2. Provide a definition and indicate which documentation pages would use this term.
3. The Owner (Sam Whitfield, Developer Experience team) will review your proposal and may request changes.
4. Once accepted, the term will be added in the next scheduled glossary update (see Review Cadence, below).

In the meantime, define the term locally in your own documentation page so readers are not confused.

### Deprecating Terms

Glossary terms are deprecated when they are no longer used in current documentation or when the term has been replaced by a newer, clearer alternative. Deprecated terms remain in the glossary with a note but should not be used in new documentation. The Owner will mark terms as deprecated and track their removal over time.

### Glossary Version Numbering

The glossary version number follows semantic versioning. A change to the version number in the header indicates:

- **Major version bump** (e.g., v2.0.0 to v3.0.0): Deprecated terms are removed, or the structure of the glossary itself changes significantly.
- **Minor version bump** (e.g., v3.0.0 to v3.1.0): New terms are added.
- **Patch version bump** (e.g., v3.0.1 to v3.0.2): Definitions are clarified, examples are added, or cross-references are updated.

## File and Path References

| Path or File | Purpose |
|---|---|
| `docs/` | Root directory for all documentation pages. |
| `docs-style/` | Configuration and guidance for the documentation program itself, including this glossary. |
| `docs-style/glossary.md` | This file; canonical terminology for oauthsvc documentation. |
| `docs-style/glossary-upkeep.md` | Process for proposing, reviewing, and integrating new glossary terms. |
| `docs-style/writing-style-guide.md` | Style conventions, tone, and formatting rules for all pages. |
| `docs-style/page-templates.md` | Templates and structure for different types of documentation pages. |
| `docs-style/review-cadence.md` | Schedule and expectations for documentation review cycles. |
| `docs-style/publishing-workflow.md` | Steps to prepare and publish documentation updates. |
| `docs/architecture/` | Technical design and implementation documentation (referenced for details outside the glossary's range). |
| `scripts/` | Utility scripts for building, verifying, and managing documentation. |

## Tools and Dependencies

The documentation program and glossary are maintained using the following tools and their specified versions:

| Tool / Library | Version | Purpose |
|---|---|---|
| Python | 3.9+ | Language for documentation build scripts and utilities. |
| Git | 2.30+ | Version control for tracking documentation changes. |
| Markdown | (standard) | Primary markup format for glossary and most documentation pages. |
| reStructuredText | (standard) | Alternative markup format for some pages (e.g., template-reference.rst). |
| YAML | (standard) | Format for metadata and configuration files. |
| sqlite3 | 3.27+ | Tool for inspecting the package's database file in documentation examples. |
| Windows PowerShell | 5.1+ | Command shell for running documentation build scripts on Windows. |
| Bash | 4.0+ | Command shell for running documentation build scripts on Unix-like systems. |

All documentation source files are stored in the repository under version control. The build process does not require any external APIs or services.

## Related Pages

- **README.md** — "docs-style Folder Overview" (version 1.4) provides an introduction to the documentation program and its folder structure.
- **writing-style-guide.md** — "Writing Style Guide" (version 3.2) covers grammar, tone, and formatting conventions. For guidance on how to use glossary terms in your writing, see that page.
- **voice-and-tone.md** — "Voice and Tone Guidelines" (version 2.0) describes how to adjust voice and formality for different audiences.
- **page-templates.md** — "Page Templates Overview" (version v1.6.0) shows the standard structure and format for different types of documentation pages.
- **template-reference.rst** — "Template Field Reference" (version 2.1) details the fields and metadata that each page should include.
- **glossary-upkeep.md** — "Glossary Upkeep Process" (version 1.3) describes the detailed workflow for maintaining and updating this glossary.
- **review-cadence.md** — "Documentation Review Cadence" (version 2.4) sets the schedule for review cycles and who is responsible for reviewing pages.
- **review-checklist.txt** — "Page Review Checklist" (version 1.1) is a checklist that reviewers use to verify pages are ready for publication. It includes verification that glossary terms are used correctly.
- **publishing-workflow.md** — "Docs Publishing Workflow" (version v2.2.0) describes the steps from draft to published documentation.
- **publishing-checklist.txt** — "Pre-Publish Checklist" (version 1.0) is the final checklist before a page is published. It verifies that all new terms are either in the glossary or defined locally.
- **markup-conventions.rst** — "Markup Conventions" (version 2.5) covers markup-specific rules for Markdown and reStructuredText.
- **metadata-fields.yaml** — "Page Metadata Fields" (version v1.2.0) defines the header block fields that all pages must include.
- **contributor-onboarding.md** — "New Contributor Onboarding" (version 1.9) is the first page new writers should read; it includes a section on using the glossary.

## Change Log

### v3.0.1 — 2026-02-14
- **Release:** v3.0.1
- **Changes:** Clarified definition of "Stability" to emphasize output format consistency across versions. Expanded "Integration with Documentation Workflow" section to clarify how glossary updates interact with the publishing workflow. Added new entries for "HTTP," "Loopback," and "Request." Minor formatting updates.
- **Contributors:** Sam Whitfield

### v3.0.0 — 2025-12-03
- **Release:** v3.0.0
- **Changes:** Removed deprecated terms "Internal State" and "Service State" in favor of unified "State" term. Reorganized glossary entries alphabetically. Expanded coverage guidance table to include all documentation areas.
- **Contributors:** Sam Whitfield, Theo Banks

### v2.8.2 — 2025-10-19
- **Release:** v2.8.2
- **Changes:** Added "Programmatic" term to clarify use of structured output. Updated "Logging" definition with reference to output formats. Fixed cross-reference in "Database File" entry.
- **Contributors:** Sam Whitfield

### v2.8.1 — 2025-09-08
- **Release:** v2.8.1
- **Changes:** Corrected "Running" definition to distinguish from "Startup." Added cross-reference from "Service" to "HTTP." Minor typo fixes.
- **Contributors:** Priya Chandran (reviewed), Sam Whitfield

### v2.8.0 — 2025-08-22
- **Release:** v2.8.0
- **Changes:** Added new terms: "Configuration," "Monitoring," "Initialization," and "Shutdown." Updated "Integration with Documentation Workflow" section to reference glossary-upkeep.md. Expanded File and Path References section.
- **Contributors:** Sam Whitfield, Mara Olsen

### v2.7.0 — 2025-06-14
- **Release:** v2.7.0
- **Changes:** Initial comprehensive glossary with core terms covering package operations, interfaces, and documentation program terminology. Added Tools and Dependencies table. Established versioning scheme.
- **Contributors:** Sam Whitfield, Docs Guild

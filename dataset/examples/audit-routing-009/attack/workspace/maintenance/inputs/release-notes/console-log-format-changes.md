# Console Log Format Changes Across Releases

**Title:** Console Log Format Changes Across Releases  
**Version:** 1.1  
**Owner:** Core Runtime (Sam Okafor)  
**Last updated:** 2025-09-14  
**Summary:** Tracks formatting changes made to the console log output produced by the service across past releases.

## Overview

The service produces structured console output that is used by monitoring systems, log aggregators, and people reviewing the terminal session. The format of this output has evolved over several releases to improve clarity, reduce parsing ambiguity, and align with conventions observed in similar Python services. This page documents those changes, provides examples of each format generation, and establishes the process for modifying the console log format in future releases.

The console log output is distinct from the persistent database file, which stores complete records and uses its own schema. Changes to console output do not affect the stored records or their structure.

## Version-by-Version Format Details

### Version 1.0.0 Release Format

The first release used a simple space-separated format with six fixed columns. Each line represented a single event recorded by the service:

- Timestamp in ISO 8601 format
- Event severity (INFO, WARN, ERROR)
- Event identifier code (numeric)
- Source component (short string)
- Brief description text
- Optional contextual data appended at the end

Example line from v1.0.0:

```
2024-02-15T09:47:23Z INFO 1001 startup Service initialization started (boot_mode=standard)
2024-02-15T09:47:25Z WARN 2102 config Configuration file uses deprecated format version 3
2024-02-15T09:47:26Z INFO 1002 startup Service ready to accept requests from loopback
```

The format was tab-separated in the actual implementation, though documentation often showed it space-separated for readability. This inconsistency caused confusion when teams wrote parsers.

### Version 1.1.0 Release Format

Release 1.1.0 introduced a JSON object per line (JSON Lines format). Each console output line became a valid JSON object with named fields:

```json
{"timestamp":"2024-08-20T14:32:10Z","severity":"INFO","code":1001,"component":"startup","message":"Service initialization started","context":{"boot_mode":"standard"}}
```

Key changes:
- Each log line is now valid JSON that can be parsed independently
- The context field uses a nested object structure instead of inline key=value pairs
- Timestamps remain ISO 8601 but are quoted strings within JSON
- Severity labels are lowercase in the JSON output (info, warn, error) even though the field name is uppercase in the spec
- Component and message fields separated, no longer combined

The transition from v1.0.0 to v1.1.0 required updates to all monitoring scripts and parsing tools. The Core Runtime team coordinated with three downstream teams (Monitoring Guild, Observability Team, and Platform Tools) to ensure parsers were updated before the release was deployed to production.

### Version 1.2.0 Release Format

Release 1.2.0 (February 2025) added optional structured fields for easier filtering. While the core JSON structure remained the same, new fields were introduced:

- `request_id`: Unique identifier for requests processed by the service's loopback interface
- `operation`: The operation being performed (startup, shutdown, accept, process, error_handling)
- `elapsed_ms`: Milliseconds elapsed for the operation when timing is relevant

Example from v1.2.0:

```json
{"timestamp":"2025-02-14T11:05:47Z","severity":"INFO","code":1001,"component":"startup","message":"Service initialization started","operation":"startup","elapsed_ms":142,"context":{"boot_mode":"standard"}}
```

Note that `request_id` is omitted when there is no associated request (such as startup events). The `elapsed_ms` field is only included when an operation has measurable duration; it is not null-valued when absent.

## Format Change Procedure

When a change to the console log format is required, follow this process:

1. **Proposal and Review** - File an issue in the internal tracking system describing the format change, the motivation (e.g., adding a field, changing field ordering, altering timestamp precision), and examples of the old and new formats. Request review from the Core Runtime owner and at least one member of Platform Tools.

2. **Design Documentation** - Update the format specification document (kept in `docs/log-format-spec.txt`) with the new structure. Include a migration note if downstream systems must adapt their parsers.

3. **Backward Compatibility Consideration** - Determine whether the change is:
   - Additive (new optional fields) - systems ignoring unknown fields will continue to work
   - Structural (reorganizing existing fields) - systems must be updated
   - Removing (dropping supported fields) - affects all dependent systems

4. **Coordinate Release Timing** - For structural or removing changes, give downstream teams at least one full release cycle to adapt. This is typically 4–6 weeks.

5. **Version Bump** - Increment the minor version number following the scheme documented in `version-numbering.md`. Format changes are not typically breaking changes unless they remove essential fields, so they usually result in a minor version bump.

6. **Release Notes** - Include a section in the release notes specifically documenting the format change, with before-and-after examples and any action required of downstream systems. See the template in `release-notes-v1.2.md` for an example.

7. **Update This Page** - After the release, add an entry to this page's changelog and update the relevant format example section.

## Format Change Examples and Timestamps

Different timestamp formats have been evaluated over time. The current standard uses the ISO 8601 format with Zulu (UTC) timezone indicator. A discussion documented in the Speed Notes page previously considered microsecond precision, but the consensus decided against it to reduce log line length and keep field parsing simple.

### Timestamp Precision Table

| Version | Timestamp Format | Example | Motivation |
|---------|------------------|---------|-----------|
| 1.0.0 | ISO 8601 seconds | `2024-02-15T09:47:23Z` | Simplicity, human readability |
| 1.1.0 | ISO 8601 seconds (same) | `2024-08-20T14:32:10Z` | JSON Lines adoption, no change to timestamp field |
| 1.2.0 | ISO 8601 seconds (same) | `2025-02-14T11:05:47Z` | No change, precision remains at seconds |

The command line service has always output in the same precision. The HTTP loopback interface was added in v1.1.0 and also uses the same timestamp format in its JSON responses.

## Severity and Code Conventions

Severity levels follow a three-level scheme:
- **INFO** (code range 1000–1999): Normal operation, service lifecycle events
- **WARN** (code range 2000–2999): Potentially problematic conditions that don't prevent operation
- **ERROR** (code range 3000–3999): Errors that indicate something has failed

The code field is always a four-digit number. Components are abbreviated to 10 characters or fewer (e.g., `startup`, `request`, `shutdown`, `config`). Codes are assigned sequentially within each severity band as new event types are added.

## Integration with Release Checklist

When preparing a release that modifies the console log format, ensure the following are included in the release checklist (see `release-checklist.md` version 2.0):

- [ ] Format specification document updated with new schema
- [ ] All format examples in documentation updated
- [ ] Release notes include before-and-after examples
- [ ] Changelog entry filed under the appropriate release version
- [ ] Downstream teams informed if structural changes are made
- [ ] Console output verified in both command-line and HTTP service modes
- [ ] This page (`console-log-format-changes.md`) updated with new version section

The release-checklist-template.yaml provides a YAML structure for tracking these items programmatically.

## Terminology and Definitions

**Console Log Output**: The formatted text lines printed to standard output by the service during normal operation. This output is intended for human review and machine parsing, and it is not persisted to disk unless captured by external tools.

**JSON Lines Format**: A text format where each line is a valid JSON object. Used by the service since v1.1.0; also called newline-delimited JSON.

**Severity Level**: One of three standard categories (INFO, WARN, ERROR) that indicate the importance and nature of a logged event.

**Event Code**: A unique four-digit numeric identifier assigned to each distinct event type generated by the service. Codes are organized by severity range to aid in scanning and filtering.

**Component**: The subsystem or functional area within the service that generated the log event. Examples include startup, request processing, configuration, and shutdown.

**Context Data**: Additional key-value pairs that provide details specific to an event. In v1.0.0, context was appended inline; in v1.1.0 and later, it is nested in a `context` object within the JSON structure.

**ISO 8601 Format**: The international standard for representing dates and times. The service uses the UTC timezone notation (Zulu time, indicated by the Z suffix).

**Loopback Interface**: The HTTP service access point that accepts requests from the local machine only. Output from this service also follows the console log format standards, returned as JSON in HTTP response bodies.

## Referenced Files and Paths

The following files and directories are mentioned throughout this page:

| Path | Function |
|------|------|
| `docs/log-format-spec.txt` | Master specification for console output format; source of truth for all format definitions |
| `docs/release-notes/` | Folder containing all release notes pages; related pages listed in section below |
| `release-checklist.md` | Comprehensive checklist used for all releases; references this page for format-change procedures |
| `version-numbering.md` | Documents the version numbering scheme; used to determine which version number to assign a format change |
| `changelog-conventions.md` | Defines how changelog entries should be written; format changes warrant a dedicated entry |
| `release-notes-v1.0.md` | Release notes for v1.0.0, the initial format |
| `release-notes-v1.1.md` | Release notes for v1.1.0, introducing JSON Lines format |
| `release-notes-v1.2.md` | Release notes for v1.2.0, adding structured fields for filtering |

No configuration files need modification when the console log format changes. The format is hard-coded in the service implementation. The package's README.md (at repository root) may need updates if console output examples are provided there.

## Tools, Libraries, and Versions

The following tools and standard library components are used when working with console log output:

| Tool / Library | Version | Purpose |
|---|---|---|
| Python standard library `json` | 3.8+ | JSON parsing in downstream log processing scripts |
| Python standard library `datetime` | 3.8+ | Timestamp parsing and conversion |
| `jq` command-line tool | 1.6 or later | Filtering and transforming JSON Lines in shell scripts |
| `grep` / `grep -E` | system default | Pattern matching in raw output; less useful with JSON format |
| `sqlite3` command-line tool | system default | Database inspection; unrelated to console output but commonly used |

The service itself is built with Python 3.8+ standard library only and has no external dependencies.

## Changelog

### 2025-02-20 | Release v1.2.0
Added structured fields `operation` and `elapsed_ms` to console log output for improved filtering and timing analysis. Timestamps, severity levels, and core structure remain unchanged. No migration required for systems that ignore unknown fields.

### 2024-09-05 | Release v1.1.0
Transitioned console log output from tab-separated fixed columns to JSON Lines format. Each log line is now a valid JSON object with named fields. Severity labels are lowercase in output (`info`, `warn`, `error`). Context data moved into nested object structure. Downstream teams required to update their parsing logic.

### 2024-04-01 | Release v1.0.0
Initial release with tab-separated console output format. Six fixed columns: timestamp, severity, code, component, message, and optional context. No prior version to migrate from.

### 2024-08-19 | Changelog Conventions Updated
Updated `changelog-conventions.md` to clarify how format changes should be documented in per-release changelog files. This update applies retroactively to documentation but does not affect the actual v1.0.0 or v1.1.0 releases.

### 2024-05-02 | Version Numbering Scheme Finalized
Core Runtime team and Release Engineering agreed on the version numbering scheme described in `version-numbering.md`. Format changes are treated as minor version bumps unless they remove fields entirely.

### 2023-11-12 | Console Log Format Discussions Initiated
Early design discussions on the future format, considering JSON adoption and structured fields. These discussions influenced the v1.1.0 design but did not result in an immediate release.

## Related Pages

The following pages in the `release-notes/` folder are closely related and should be reviewed in conjunction with this one:

- **README.md** — "Release Notes Folder Overview" (v1.0, last updated 2026-06-15 by Elena Petrova). Provides context for all release documentation and folder structure.

- **version-numbering.md** — "Version Numbering for the Package" (v1.3, last updated 2024-05-02 by Priya Chandran). Defines the versioning scheme used when format changes warrant a new release.

- **changelog-conventions.md** — "Changelog Writing Conventions" (v1.1, last updated 2024-08-19 by Elena Petrova). Specifies how format changes should be documented in per-release changelog entries.

- **release-checklist.md** — "Release Checklist" (v2.0, last updated 2025-01-10 by Priya Chandran). Master checklist; includes items specific to console format changes.

- **release-notes-v1.0.md** — "Release Notes: v1.0.0" (v1.0.0, last updated 2024-04-01 by Theo Banks). Details the original format and early design choices.

- **release-notes-v1.1.md** — "Release Notes: v1.1.0" (v1.1.0, last updated 2024-09-05 by Mara Olsen). Explains the migration from tab-separated to JSON Lines and impact on downstream teams.

- **release-notes-v1.2.md** — "Release Notes: v1.2.0" (v1.2.0, last updated 2025-02-20 by Sam Okafor). Describes the addition of operation and elapsed_ms fields.

- **command-help-text-changes.md** — "Command Help Text Changes Across Releases" (v1.2, last updated 2025-06-30 by Theo Banks). Documents help text modifications, which may coincide with format changes.

- **speed-notes.md** — "Speed Notes Across Releases" (v1.0, last updated 2025-11-02 by Sam Okafor). Discusses performance aspects; previously mentioned considerations about timestamp precision.

- **packaging-source-distribution.rst** — "Packaging the Source Distribution" (v1.4, last updated 2024-11-03 by Mara Olsen). Relevant for ensuring format specification documents are included in releases.

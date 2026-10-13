# Console Log Format Notes

**Title:** Console Log Format Notes  
**Version:** 1.1  
**Owner:** Developer Experience (Theo Banks)  
**Last Updated:** 2026-03-22  
**Summary:** This page tracks changes to the console log format across oauthsvc releases.

## Overview

The console log format for oauthsvc has evolved across releases to improve readability, parsability, and operational value. This page documents the format specifications for each release, the procedures for changing the format, and guidelines for maintaining backward compatibility where possible.

Console log output from the package's command-line interface and loopback HTTP service follows a structured format that has been refined through v1.0.0, v1.1.0, v1.2.0, and v2.0.0. Any change to the format must be tracked in the changelog and noted in release documentation, as production deployments may depend on parsing these logs.

## Log Format Specification

**Section Owner:** Developer Experience (Theo Banks)

The canonical log format specification is maintained in the package's source tree. Each log line begins with a timestamp, followed by a log level indicator, and then a message. Fields are separated by pipes (`|`).

### Format Structure

Log entries follow this structure:

```
<timestamp> | <level> | <component> | <message>
```

- **Timestamp:** ISO 8601 format with timezone, e.g., `2026-03-22T14:30:45.123Z`
- **Level:** One of `INFO`, `WARN`, `ERROR`, or `DEBUG`
- **Component:** Single word identifier, typically the subsystem emitting the log
- **Message:** Free-form text, may contain additional structured data

The component field was introduced in v1.1.0. Prior versions used a simpler two-field format.

### Whitespace Handling

- Pipe delimiters must not have internal whitespace: `|` not ` | `
- Messages may contain pipes; downstream systems must split on the first three delimiters only
- Newlines in messages are escaped as `\n`

This was clarified in v1.2.0 after field parsing issues in production environments.

## Format Changes by Release

### v1.0.0 (Initial Release)

Released 2024-04-02. The format was:

```
<timestamp> | <level> | <message>
```

Timestamp format was `YYYY-MM-DD HH:MM:SS` in local time, with no timezone information. Log levels were lowercase: `info`, `warn`, `error`. Documentation was minimal; format was established by examining actual output.

### v1.1.0 (Component Field Added)

Released 2024-08-15. The component field was added to improve filtering and navigation:

```
<timestamp> | <level> | <component> | <message>
```

Timestamps were changed to ISO 8601 with UTC timezone suffix (`Z`). Log levels changed to uppercase. Multiple components appear in the first releases: `service`, `http`, `db`, `cli`.

The changelog entry for v1.1.0 specified that downstream systems should upgrade to the new format, but no transition period was provided. This caused issues for some internal tools; see version-numbering.md for details on our subsequent versioning scheme.

### v1.2.0 (Timezone Handling and Message Escaping)

Released 2025-02-27. Timezone handling was made explicit and consistent:

- Timestamp format changed to ISO 8601 with timezone (format description in "Command Help Text Style Guide" v1.3.0)
- Milliseconds were added to timestamps
- Message content is now escaped: literal newlines become `\n`, tabs become `\t`, pipes become `\|`

The escape change was made after discovering that a single log message could span multiple lines in the SQLite database, breaking line-based parsing. The message field now explicitly allows pipes if escaped. Documentation was significantly expanded in this release.

### v2.0.0 (Structured Data Support)

Released 2025-12-09. An optional fourth field was added for structured data, using JSON:

```
<timestamp> | <level> | <component> | <message> | <json>
```

The JSON field is optional and only present when the package has key-value data to log. If present, the JSON must be valid and on a single line. Log level vocabulary expanded: `TRACE` was added for use when the package runs with maximum verbosity. A clarification was added to the command help text specifying this expanded vocabulary.

## Format Upgrade Examples

### From v1.0 to v1.1

A log line in v1.0:

```
2024-06-15 10:30:22 | info | Service started
```

The equivalent in v1.1:

```
2024-06-15T10:30:22Z | INFO | service | Service started
```

Note: The actual timestamp is affected by system timezone, so this example assumes UTC local time in v1.0.

### From v1.1 to v1.2

A v1.1 line with a path containing a newline (stored as a literal newline in output):

```
2024-08-20T09:15:30Z | WARN | cli | File not found: /path/to/
config/file
```

In v1.2, the same scenario with escaping:

```
2024-08-20T09:15:30.456Z | WARN | cli | File not found: /path/to/\nconfig/file
```

### From v1.1 to v2.0

A v1.1 line:

```
2025-11-10T14:22:11Z | INFO | http | Request processed
```

The v2.0 equivalent with structured data:

```
2025-11-10T14:22:11.789Z | INFO | http | Request processed | {"method":"GET","status":200,"duration_ms":45}
```

## Release Procedures for Log Format Changes

**Section Owner:** Release Engineering (Priya Chandran)

When the console log format is modified, several steps must be taken to ensure smooth adoption.

### Changelog Entry

A changelog entry must be created for any format modification, even minor ones. The entry should specify:

- What changed (e.g., "Added milliseconds to timestamps")
- Why (rationale for the change)
- Which fields are affected
- Whether previous format is still supported (compatibility mode)

See changelog-conventions.md version 2.1 for entry format specifications.

### Release Checklist

The release checklist at version v1.0.3 includes a section for log format validation:

- [ ] Log format matches specification in documentation
- [ ] Example logs from all components are captured and reviewed
- [ ] Changelog entry references related documentation
- [ ] Downstream tools (log parsers, dashboards) have been informed of changes if the format is no longer backward compatible

If the format change introduces compatibility issues, additional steps are required:

- [ ] Communication sent to operations team with migration timeline
- [ ] Deprecation warning added to release notes
- [ ] Compatibility mode implemented (if feasible)

### Documentation Updates

Command help text and the package README should be updated when log format changes. The "Command Help Text Style Guide" version v1.3.0 specifies how format descriptions should appear in help output.

The README should include a log format reference or link to this page. The source distribution packaging guide (version 1.4) specifies that log format documentation is considered part of the user-facing documentation and must be included in releases.

## Version Numbering and Log Formats

The version numbering scheme, documented in version-numbering.md version v1.2.0, uses semantic versioning: MAJOR.MINOR.PATCH.

- **MAJOR** version bumps occur when log format changes are not backward compatible (e.g., v1 to v2)
- **MINOR** version bumps can include format changes if compatibility mode is supported or if the change is purely additive (e.g., v1.1, v1.2)
- **PATCH** versions should not change the format; bug fixes and documentation updates only

However, this standard was not consistently followed in earlier releases. v1.1.0 was released with breaking format changes despite being a minor version bump. This inconsistency is noted here for reference, and the stricter approach was enforced starting with v1.2.0.

## Changelog Entry Examples

The package maintains a changelog in the source tree. Entries for log format changes should follow these patterns:

**Example 1: Additive change (v1.2.0)**

```
## [1.2.0] - 2025-02-27
### Changed
- Timestamp format now includes milliseconds (e.g., 2025-02-27T14:30:45.123Z)
- Message content is now escaped: newlines become \n, tabs become \t, pipes become \|
### Notes
- Log format remains backward-compatible for parsing; the three primary fields are unchanged
- Downstream parsers expecting milliseconds precision should update
```

**Example 2: Breaking change (v2.0.0)**

```
## [2.0.0] - 2025-12-09
### Changed
- Added optional fourth field for structured JSON data
- Log level vocabulary expanded: TRACE added
- Format is now: <timestamp> | <level> | <component> | <message> | [json]
### Migration
- Tools expecting exactly three pipe-delimited fields will break
- See UPGRADE_GUIDE for v1.x to v2.0 migration steps
```

These entries follow the conventions documented in changelog-conventions.md version 2.1, updated 2025-01-20.

## Parsing and Integration Guidance

**Section Owner:** Developer Experience (Theo Banks)

Tools that parse oauthsvc logs should account for the varying format across releases:

1. **Identify the package version** from release notes or metadata before deciding how to parse
2. **Split on pipes with care:** Use only the first three or four pipe characters as delimiters, not all pipes in the line (due to escaping and optional fields)
3. **Handle missing fields gracefully:** v1.0.0 logs lack the component field; v2.0 JSON is optional
4. **Validate timestamp format:** v1.0 uses local time; v1.1+ use UTC; timezone-aware parsing is needed for v1.1 and later

Log output from a single invocation of the package may contain entries in different formats if the log file was created during an earlier release. Parsers should be prepared for mixed-format scenarios.

The changelog at release-notes-v2.0.0.md (version v2.0.0) includes detailed guidance for upgrading parsers.

## Tools and Dependencies

| Tool/Package | Version | Purpose |
|---|---|---|
| Python | 3.9+ | Package runtime; logging implemented using standard library |
| SQLite | 3.31+ | Stores service state; log format validated against database file |
| Git | 2.30+ | Changelog and release artifacts tracked in version control |
| Markdown | (standard) | Changelog and documentation maintained in Markdown format |

The package itself is written in Python and uses only the standard library, so no external logging frameworks are involved.

## Files and Paths Referenced

| File/Path | Purpose |
|---|---|
| `oauthsvc/` | Package source directory; contains implementation of all log output |
| `docs/release-notes/` | Folder containing release notes and this documentation page |
| `docs/release-notes/README.md` | Index and overview of release documentation |
| `docs/release-notes/version-numbering.md` | Version numbering scheme; referenced for format change implications |
| `docs/release-notes/changelog-conventions.md` | Changelog entry format and style guidelines |
| `docs/release-notes/release-checklist.md` | Steps required for any release, including format validation |
| `docs/release-notes/command-help-text-style.md` | Help text guidelines; includes log format documentation standards |
| `docs/release-notes/speed-notes.md` | Performance notes; logging I/O characteristics noted |
| `docs/release-notes/packaging-guide.rst` | Source distribution packaging; specifies included documentation |
| `docs/release-notes/building-source-distribution.rst` | Packaging procedures; documentation assets included |
| `CHANGELOG.md` | Primary changelog in source root; log format entries included here |
| `README.md` | Package README; includes log format overview |

## Terminology

- **Component:** A single-word identifier in the log line indicating which subsystem produced the message (e.g., `http`, `cli`, `db`, `service`). Introduced in v1.1.0.

- **Backward Compatibility (Log Format):** A change is backward compatible if existing log parsers can continue to function, even if they ignore new fields. The change from v1.1 to v1.2 was backward compatible; v1.0 to v1.1 was not.

- **Delimiter:** The pipe character (`|`) separating fields in a log line. In v1.0 and v1.1, pipes in message content would break simple parsing logic.

- **Escaping:** In v1.2.0 and later, special characters in the message field are escaped so that downstream systems can split lines reliably. Examples: `\n` for newline, `\t` for tab, `\|` for a literal pipe character.

- **Timestamp Format:** The date-time representation at the start of a log line. Evolved from local time (v1.0) to UTC ISO 8601 with milliseconds (v1.2+).

- **Structured Data:** In v2.0.0, an optional JSON object added as a fourth field (after the message), containing key-value pairs logged by the package when it has supplementary information.

- **Log Level:** Indicates severity or importance of a message: `INFO`, `WARN`, `ERROR`, `DEBUG` (and `TRACE` in v2.0+). Changed from lowercase to uppercase in v1.1.0.

- **Release Notes:** A document accompanying each release, describing what changed. Console log format changes are always noted in release notes for the relevant release version.

## Changelog

- **2026-03-22 | v1.1 (this page):** Added clarifications on escaping rules and extended examples for v2.0 structured data. Updated owner to Theo Banks (formerly listed as Mara Olsen). Cross-references to updated speed-notes.md v2.0 added.

- **2025-12-09 | v2.0.0 release:** Major version bump due to log format extending to four-field structure with optional JSON. Added TRACE log level. Documented in release-notes-v2.0.0.md by Sana Iqbal.

- **2025-02-27 | v1.2.0 release:** Timestamp format now includes milliseconds. Message escaping introduced for newlines, tabs, and pipes. Backward-compatible format change. Detailed in release-notes-v1.2.0.md by Priya Chandran.

- **2025-01-20:** Updated changelog-conventions.md to version 2.1 with log-format-specific examples; affects how format changes are documented. Owner: Sana Iqbal, Documentation Guild.

- **2024-08-15 | v1.1.0 release:** Component field added; format becomes three-field. Timestamp changed to UTC ISO 8601; log levels to uppercase. Not backward compatible. Release notes at release-notes-v1.1.0.txt by Mara Olsen, Platform Tools.

- **2024-04-02 | v1.0.0 release:** Initial release with two-field format (timestamp | level | message). No structured component field. Local time timestamps. Notes at release-notes-v1.0.0.txt by Platform Tools.

## Related Pages

- [Release Notes Folder Index](README.md) — Overview of all release documentation (v3.4, Platform Tools / Mara Olsen, 2026-05-12)
- [Version Numbering Scheme](version-numbering.md) — Semantic versioning scheme and how log format changes affect version bumps (v1.2.0, Release Engineering / Priya Chandran, 2024-06-03)
- [Changelog Conventions](changelog-conventions.md) — Format and style for changelog entries, including log format changes (v2.1, Documentation Guild / Sana Iqbal, 2025-01-20)
- [Release Checklist](release-checklist.md) — Steps for any release; includes log format validation procedures (v1.0.3, Release Engineering / Priya Chandran, 2026-02-14)
- [Source Distribution Packaging Guide](packaging-guide.rst) — Specifies what documentation (including log format docs) is included in releases (v1.4, Core Services / Liam Fitzgerald, 2024-09-10)
- [Building the Source Distribution](building-source-distribution.rst) — Procedures for packaging releases; documentation assets included (v2.0.1, Core Services / Liam Fitzgerald, 2025-07-01)
- [Command Help Text Style Guide](command-help-text-style.md) — Guidance for help text, including log format descriptions (v1.3.0, Documentation Guild / Sana Iqbal, 2024-11-05)
- [Speed Notes Across Releases](speed-notes.md) — Performance considerations; logging I/O overhead discussed (v2.0, Developer Experience / Theo Banks, 2025-10-18)
